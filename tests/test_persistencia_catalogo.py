"""Persistencia SQLite del catálogo: reinicio, restricciones, transacciones y fallos."""

import sqlite3

import pytest

import backend.api_catalogo
from backend import create_app
from backend.persistencia import BaseDatos
from backend.persistencia.base_datos import ruta_base_datos_predeterminada

LISTADOS = ["categorias", "productos", "proveedores", "ubicaciones"]


def _cargar_datos(cliente):
    """Alta, modificación, bajas y mínimos de todos los maestros."""
    categoria = cliente.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"}).get_json()
    otra = cliente.post("/api/categorias", json={"codigo": "LIM", "nombre": "Limpieza"}).get_json()
    datos_producto = {"nombre": "Arroz", "categoria_id": categoria["id"], "precio": "1250.50"}
    arroz = cliente.post("/api/productos", json={"codigo": "001", **datos_producto}).get_json()
    cliente.put(f'/api/productos/{arroz["id"]}', json={"codigo": "001-B", **datos_producto})
    lavandina = cliente.post("/api/productos", json={
        "codigo": "002", "nombre": "Lavandina", "categoria_id": otra["id"], "precio": "0.10",
    }).get_json()
    cliente.post("/api/proveedores", json={"codigo": "PRV-1", "nombre": "O'Brien & Hijos"})
    cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"})
    local = cliente.post("/api/ubicaciones", json={"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"}).get_json()
    cerrado = cliente.post("/api/ubicaciones", json={"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"}).get_json()
    cliente.put(f'/api/ubicaciones/{local["id"]}/minimos/{arroz["id"]}', json={"minimo": 8})
    cliente.put(f'/api/ubicaciones/{local["id"]}/minimos/{lavandina["id"]}', json={"minimo": 0})
    cliente.put(f'/api/ubicaciones/{cerrado["id"]}/minimos/{lavandina["id"]}', json={"minimo": 3})
    for ruta in [
        f'/api/productos/{lavandina["id"]}/estado', f'/api/categorias/{otra["id"]}/estado',
        "/api/proveedores/1/estado", f'/api/ubicaciones/{cerrado["id"]}/estado',
    ]:
        assert cliente.patch(ruta, json={"activo": False}).status_code == 200
    return local, cerrado


def _estado(cliente, locales):
    estado = {
        recurso: cliente.get(f"/api/{recurso}?estado=todos").get_json() for recurso in LISTADOS
    }
    for local in locales:
        estado[f'minimos-{local["id"]}'] = cliente.get(f'/api/ubicaciones/{local["id"]}/minimos').get_json()
    return estado


def test_reiniciar_conserva_maestros_estados_minimos_y_referencias(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    locales = _cargar_datos(cliente)
    antes = _estado(cliente, locales)

    reiniciado = create_app(base_datos=ruta).test_client()

    assert _estado(reiniciado, locales) == antes
    productos = antes["productos"]["productos"]
    assert productos[0]["codigo"] == "001-B" and productos[0]["precio"] == "1250.50"
    assert productos[1]["activo"] is False and productos[1]["categoria"]["activo"] is False
    assert antes["proveedores"]["proveedores"][0]["nombre"] == "O'Brien & Hijos"


def test_reiniciar_conserva_reserva_de_codigos_historicos_y_continua_ids(tmp_path):
    ruta = tmp_path / "tp.db"
    _cargar_datos(create_app(base_datos=ruta).test_client())
    cliente = create_app(base_datos=ruta).test_client()

    datos = {"nombre": "Otro", "categoria_id": 1, "precio": "1"}
    for codigo in ["001", "001-b", "002"]:
        respuesta = cliente.post("/api/productos", json={"codigo": codigo, **datos})
        assert respuesta.status_code == 409
    assert cliente.post("/api/proveedores", json={"codigo": "prv-1", "nombre": "X"}).status_code == 409
    assert cliente.post("/api/ubicaciones", json={"codigo": "l2", "nombre": "X", "tipo": "LOCAL"}).status_code == 409

    nuevo = cliente.post("/api/productos", json={"codigo": "003", **datos})
    assert nuevo.status_code == 201
    assert nuevo.get_json()["id"] == 3


def test_reiniciar_mantiene_un_unico_cd_y_reglas_de_inactivos(tmp_path):
    ruta = tmp_path / "tp.db"
    local, cerrado = _cargar_datos(create_app(base_datos=ruta).test_client())
    cliente = create_app(base_datos=ruta).test_client()

    segundo_cd = cliente.post("/api/ubicaciones", json={"codigo": "CD2", "nombre": "Otro", "tipo": "CD"})
    assert segundo_cd.status_code == 409
    assert cliente.patch("/api/ubicaciones/1/estado", json={"activo": False}).status_code == 409
    assert cliente.put(f'/api/ubicaciones/{cerrado["id"]}/minimos/1', json={"minimo": 1}).status_code == 409
    assert cliente.put("/api/productos/2", json={
        "codigo": "002", "nombre": "Lavandina", "categoria_id": 2, "precio": "1",
    }).status_code == 409
    assert cliente.put(f'/api/ubicaciones/{local["id"]}/minimos/1', json={"minimo": 9}).status_code == 200
    assert create_app(base_datos=ruta).test_client().get(
        f'/api/ubicaciones/{local["id"]}/minimos'
    ).get_json()["minimos"][0]["minimo"] == 9


def test_fallo_al_guardar_devuelve_500_y_no_deja_cambios_en_memoria_ni_en_base(tmp_path, monkeypatch):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    cliente.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"})

    def fallar(conexion, categoria):
        conexion.execute("UPDATE categorias SET nombre = 'parcial' WHERE id = 1")
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(backend.api_catalogo, "guardar_categoria", fallar)
    respuesta = cliente.put("/api/categorias/1", json={"codigo": "NUEVO", "nombre": "Cambiado"})
    assert respuesta.status_code == 500
    assert respuesta.get_json()["error"]["code"] == 500
    nuevo = cliente.post("/api/categorias", json={"codigo": "BEB", "nombre": "Bebidas"})
    assert nuevo.status_code == 500
    monkeypatch.undo()

    esperado = {"categorias": [{"id": 1, "codigo": "ALM", "nombre": "Almacén", "activo": True}]}
    assert cliente.get("/api/categorias").get_json() == esperado
    assert create_app(base_datos=ruta).test_client().get("/api/categorias").get_json() == esperado
    # El código del intento fallido no quedó reservado y el ID no se consumió.
    reintento = cliente.post("/api/categorias", json={"codigo": "NUEVO", "nombre": "Bebidas"})
    assert reintento.status_code == 201
    assert reintento.get_json()["id"] == 2


def test_transaccion_revierte_todo_ante_una_excepcion(tmp_path):
    base_datos = BaseDatos(tmp_path / "tp.db")
    base_datos.inicializar()

    def alta_parcial(conexion):
        conexion.execute("INSERT INTO categorias (id, codigo, nombre, activo) VALUES (?, ?, ?, ?)", (1, "A", "A", 1))
        raise ValueError("falla después de la primera sentencia")

    with pytest.raises(ValueError):
        base_datos.ejecutar_transaccion(alta_parcial)

    filas = base_datos.consultar(lambda conexion: conexion.execute("SELECT * FROM categorias").fetchall())
    assert filas == []


@pytest.mark.parametrize("sentencias", [
    ["INSERT INTO ubicaciones VALUES (1, 'CD1', 'A', 'CD', 1)", "INSERT INTO ubicaciones VALUES (2, 'CD2', 'B', 'CD', 1)"],
    ["INSERT INTO ubicaciones VALUES (1, 'X', 'A', 'DEPOSITO', 1)"],
    ["INSERT INTO productos VALUES (1, 'P', 'P', 99, 100, 1)"],
    ["INSERT INTO categorias VALUES (1, 'C', 'C', 1)", "INSERT INTO productos VALUES (1, 'P', 'P', 1, 0, 1)"],
    ["INSERT INTO categorias VALUES (1, 'C', 'C', 2)"],
    ["INSERT INTO minimos VALUES (7, 7, 1)"],
    ["INSERT INTO codigos_reservados VALUES ('producto', 'a', 'A', 1)",
     "INSERT INTO codigos_reservados VALUES ('producto', 'a', 'a', 2)"],
])
def test_esquema_rechaza_datos_que_violan_restricciones(tmp_path, sentencias):
    base_datos = BaseDatos(tmp_path / "tp.db")
    base_datos.inicializar()

    def ejecutar(conexion):
        for sentencia in sentencias:
            conexion.execute(sentencia)

    with pytest.raises(sqlite3.IntegrityError):
        base_datos.ejecutar_transaccion(ejecutar)


def test_inicializar_dos_veces_conserva_los_datos(tmp_path):
    ruta = tmp_path / "carpeta" / "nueva" / "tp.db"
    create_app(base_datos=ruta).test_client().post("/api/categorias", json={"codigo": "A", "nombre": "A"})

    BaseDatos(ruta).inicializar()

    assert len(create_app(base_datos=ruta).test_client().get("/api/categorias").get_json()["categorias"]) == 1


def test_ruta_predeterminada_usa_variable_de_entorno_o_carpeta_local(monkeypatch, tmp_path):
    monkeypatch.setenv("TP_DAO_DB", str(tmp_path / "elegida.db"))
    assert ruta_base_datos_predeterminada() == tmp_path / "elegida.db"

    monkeypatch.delenv("TP_DAO_DB")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert ruta_base_datos_predeterminada() == tmp_path / "TP-DAO" / "tp_dao.db"


def test_create_app_sin_ruta_no_usa_la_base_real(monkeypatch, tmp_path):
    monkeypatch.setenv("TP_DAO_DB", str(tmp_path / "real.db"))

    create_app().test_client().post("/api/categorias", json={"codigo": "A", "nombre": "A"})

    assert not (tmp_path / "real.db").exists()
