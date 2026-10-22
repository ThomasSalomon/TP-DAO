"""Contratos HTTP y persistencia de reposición, bultos y remitos (F-03.2)."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

import backend.api_compras
import backend.api_logistica
from backend import create_app
from backend.dominio import ZONA_ARGENTINA
from backend.persistencia import BaseDatos

INSTANTE = datetime(2026, 10, 22, 9, 0, tzinfo=ZONA_ARGENTINA)
CD, L1, L2 = 1, 2, 3


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    monkeypatch.setattr(backend.api_compras, "ahora", lambda: INSTANTE)
    monkeypatch.setattr(backend.api_logistica, "ahora", lambda: INSTANTE)


def preparar_catalogo(cliente, con_cd=True):
    cliente.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"})
    for codigo, nombre in [("001", "Arroz"), ("002", "Fideos")]:
        cliente.post("/api/productos", json={"codigo": codigo, "nombre": nombre, "categoria_id": 1, "precio": "1500"})
    cliente.post("/api/proveedores", json={"codigo": "PRV", "nombre": "Molinos"})
    if con_cd:
        cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"})
        cliente.post("/api/compras", json={"proveedor_id": 1, "lineas": [
            {"producto_id": 1, "cantidad": 20, "costo_unitario": "1000"},
            {"producto_id": 2, "cantidad": 10, "costo_unitario": "400"},
        ]})
    cliente.post("/api/ubicaciones", json={"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"})
    cliente.post("/api/ubicaciones", json={"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"})


def post(cliente, ruta, cuerpo=None, estado=200):
    respuesta = cliente.post(ruta, json={} if cuerpo is None else cuerpo)
    assert respuesta.status_code == estado, respuesta.get_json()
    return respuesta.get_json()


def orden_con_bulto(cliente, cantidad=5, local=L1):
    """Necesidad, orden y bulto preparado de arroz; devuelve el JSON del bulto."""
    necesidad = post(cliente, "/api/necesidades", {"local_id": local, "producto_id": 1, "cantidad": cantidad}, 201)
    orden = post(cliente, "/api/ordenes", {"local_id": local, "necesidad_ids": [necesidad["id"]]}, 201)
    return post(cliente, f'/api/ordenes/{orden["id"]}/bultos',
                {"lineas": [{"producto_id": 1, "cantidad": cantidad}]}, 201)


def saldos(cliente, ubicacion):
    datos = cliente.get(f"/api/ubicaciones/{ubicacion}/saldos").get_json()["saldos"]
    return {(s["producto"]["codigo"], s["condicion"]): s["cantidad"] for s in datos}


@pytest.fixture
def cliente():
    cliente = create_app().test_client()
    preparar_catalogo(cliente)
    return cliente


def test_circuito_completo_por_api_habilita_stock_con_doble_verificacion(cliente):
    n1 = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 4}, 201)
    n2 = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 2}, 201)
    n3 = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 2, "cantidad": 3}, 201)
    assert n1["estado"] == "PENDIENTE" and n1["orden_id"] is None and n1["local"]["codigo"] == "L1"

    respuesta = cliente.post("/api/ordenes", json={"local_id": L1, "necesidad_ids": [n1["id"], n2["id"], n3["id"]]})
    assert respuesta.status_code == 201 and respuesta.headers["Location"] == "/api/ordenes/1"
    orden = respuesta.get_json()
    assert orden["centro"]["tipo"] == "CD" and orden["destino"]["codigo"] == "L1" and orden["estado"] == "ABIERTA"
    assert [(l["producto"]["codigo"], l["solicitada"], l["pendiente"], l["necesidades"]) for l in orden["lineas"]] == [
        ("001", 6, 6, [1, 2]), ("002", 3, 3, [3]),
    ]
    assert cliente.get("/api/necesidades/1").get_json()["estado"] == "CONSOLIDADA"

    bulto = post(cliente, "/api/ordenes/1/bultos", {"lineas": [
        {"producto_id": 1, "cantidad": 6}, {"producto_id": 2, "cantidad": 3},
    ]}, 201)
    assert bulto["codigo"] == "B-000001" and bulto["estado"] == "PREPARADO" and bulto["remito"] is None
    assert [(l["producto"]["codigo"], l["cantidad"], l["costo_referencia"]) for l in bulto["lineas"]] == [
        ("001", 6, "1000.00"), ("002", 3, "400.00"),
    ]
    assert saldos(cliente, CD)[("001", "RESERVADO")] == 6
    assert cliente.get("/api/ordenes/1").get_json()["estado"] == "COMPLETA"

    bulto = post(cliente, "/api/bultos/1/precintar", {"precinto": "SELLO-77"})
    assert bulto["estado"] == "PRECINTADO" and bulto["precinto"] == "SELLO-77"
    assert bulto["remito"] == {"id": 1, "numero": "R-000001", "estado": "EMITIDO"}
    assert post(cliente, "/api/bultos/1/despachar")["estado"] == "EN_TRANSITO"
    assert saldos(cliente, L1) == {("001", "EN_TRANSITO"): 6, ("002", "EN_TRANSITO"): 3}

    recepcion = {"local_id": L1, "precinto_leido": "sello-77", "precinto_intacto": True}
    assert post(cliente, "/api/bultos/1/recibir", recepcion)["estado"] == "RECIBIDO"
    assert post(cliente, "/api/bultos/1/verificar")["estado"] == "VERIFICADO"
    assert cliente.get(f"/api/ubicaciones/{L1}/existencias").get_json()["existencias"] == []

    remito = post(cliente, "/api/remitos/1/verificar")
    assert remito["estado"] == "VERIFICADO" and remito["instante_cierre"] == "2026-10-22T09:00:00-03:00"
    assert remito["bulto"] == {"id": 1, "codigo": "B-000001", "estado": "VERIFICADO"}
    existencias = cliente.get(f"/api/ubicaciones/{L1}/existencias").get_json()["existencias"]
    assert [(e["producto"]["codigo"], e["disponible"]) for e in existencias] == [("001", 6), ("002", 3)]
    assert saldos(cliente, CD) == {("001", "DISPONIBLE"): 14, ("002", "DISPONIBLE"): 7}

    final = cliente.get("/api/bultos/1").get_json()
    assert [(e["secuencia"], e["estado_anterior"], e["estado_nuevo"]) for e in final["eventos"]] == [
        (1, None, "PREPARADO"), (2, "PREPARADO", "PRECINTADO"), (3, "PRECINTADO", "EN_TRANSITO"),
        (4, "EN_TRANSITO", "RECIBIDO"), (5, "RECIBIDO", "VERIFICADO"),
    ]
    movimiento = cliente.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]
    assert movimiento["causa"] == "VERIFICACION" and movimiento["bulto_codigo"] == "B-000001"
    assert movimiento["compra_id"] is None


def test_reiniciar_en_cada_etapa_conserva_todo_y_permite_continuar(tmp_path):
    ruta = tmp_path / "tp.db"
    preparar_catalogo(create_app(base_datos=ruta).test_client())
    consultas = ["/api/necesidades", "/api/ordenes", "/api/bultos", "/api/remitos",
                 f"/api/ubicaciones/{CD}/saldos", f"/api/ubicaciones/{L1}/saldos",
                 f"/api/ubicaciones/{L1}/movimientos"]
    pasos = [
        lambda c: orden_con_bulto(c, 5),
        lambda c: post(c, "/api/bultos/1/precintar", {"precinto": "S-1"}),
        lambda c: post(c, "/api/bultos/1/despachar"),
        lambda c: post(c, "/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "S-1", "precinto_intacto": True}),
        lambda c: post(c, "/api/bultos/1/verificar"),
        lambda c: post(c, "/api/remitos/1/verificar"),
    ]
    for paso in pasos:
        cliente = create_app(base_datos=ruta).test_client()
        paso(cliente)
        antes = [cliente.get(consulta).get_json() for consulta in consultas]
        reiniciado = create_app(base_datos=ruta).test_client()
        assert [reiniciado.get(consulta).get_json() for consulta in consultas] == antes

    cliente = create_app(base_datos=ruta).test_client()
    assert saldos(cliente, L1) == {("001", "DISPONIBLE"): 5}
    assert orden_con_bulto(cliente, 3)["codigo"] == "B-000002"


def test_rechazo_por_precinto_persiste_y_bloquea_verificaciones(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar_catalogo(cliente)
    orden_con_bulto(cliente, 5)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    post(cliente, "/api/bultos/1/despachar")

    bulto = post(cliente, "/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "S-1", "precinto_intacto": False})

    assert bulto["estado"] == "RECHAZADO" and bulto["remito"]["estado"] == "RECHAZADO"
    assert bulto["eventos"][-1]["motivo"] == "Precinto roto."
    reiniciado = create_app(base_datos=ruta).test_client()
    assert saldos(reiniciado, L1) == {("001", "RECHAZADO"): 5}
    assert post(reiniciado, "/api/bultos/1/verificar", estado=409)["error"]["code"] == 409
    assert post(reiniciado, "/api/remitos/1/verificar", estado=409)
    assert reiniciado.get(f"/api/ubicaciones/{L1}/existencias").get_json()["existencias"] == []


def test_transiciones_invalidas_devuelven_409_sin_cambios(cliente):
    orden_con_bulto(cliente, 5)
    antes = cliente.get("/api/bultos/1").get_json()

    for ruta, cuerpo in [
        ("/api/bultos/1/despachar", {}), ("/api/bultos/1/verificar", {}),
        ("/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "X", "precinto_intacto": True}),
    ]:
        assert "preparado" in post(cliente, ruta, cuerpo, 409)["error"]["message"]
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    post(cliente, "/api/bultos/1/despachar")
    post(cliente, "/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "S-1", "precinto_intacto": True})
    assert "Verificá el bulto" in post(cliente, "/api/remitos/1/verificar", estado=409)["error"]["message"]
    assert post(cliente, "/api/bultos/1/anular", estado=409)

    assert cliente.get("/api/bultos/1").get_json()["eventos"][:1] == antes["eventos"]
    assert len(cliente.get("/api/bultos/1").get_json()["eventos"]) == 4
    assert saldos(cliente, L1) == {("001", "PENDIENTE"): 5}


def test_recibir_en_otro_local_o_inexistente_no_cambia_nada(cliente):
    orden_con_bulto(cliente, 5)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    post(cliente, "/api/bultos/1/despachar")

    otro = post(cliente, "/api/bultos/1/recibir", {"local_id": L2, "precinto_leido": "S-1", "precinto_intacto": True}, 409)
    inexistente = post(cliente, "/api/bultos/1/recibir",
                       {"local_id": 9, "precinto_leido": "S-1", "precinto_intacto": True}, 404)

    assert "local destino" in otro["error"]["message"]
    assert set(inexistente["error"]["fields"]) == {"local_id"}
    assert cliente.get("/api/bultos/1").get_json()["estado"] == "EN_TRANSITO"


def test_anular_por_api_libera_la_reserva_y_reabre_la_orden(cliente):
    orden_con_bulto(cliente, 5)

    bulto = post(cliente, "/api/bultos/1/anular")

    assert bulto["estado"] == "ANULADO"
    assert saldos(cliente, CD)[("001", "DISPONIBLE")] == 20 and ("001", "RESERVADO") not in saldos(cliente, CD)
    orden = cliente.get("/api/ordenes/1").get_json()
    assert orden["estado"] == "ABIERTA" and orden["lineas"][0]["pendiente"] == 5
    assert orden["bultos"] == [{"id": 1, "codigo": "B-000001", "estado": "ANULADO"}]


@pytest.mark.parametrize("ruta,cuerpo,campos", [
    ("/api/necesidades", {"local_id": L1, "producto_id": 1}, {"cantidad"}),
    ("/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": "2"}, {"cantidad"}),
    ("/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 2**53}, {"cantidad"}),
    ("/api/ordenes", {"local_id": L1, "necesidad_ids": 1}, {"necesidad_ids"}),
    ("/api/ordenes", {"local_id": L1, "necesidad_ids": [1, "2"]}, {"necesidad_ids.2"}),
    ("/api/ordenes/1/bultos", {"lineas": [{"producto_id": 1}]}, {"lineas.1.cantidad"}),
    ("/api/bultos/1/precintar", {}, {"precinto"}),
    ("/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "S", "precinto_intacto": "si"}, {"precinto_intacto"}),
    ("/api/bultos/1/despachar", {"forzar": True}, {"forzar"}),
])
def test_formato_invalido_devuelve_400_con_campos(cliente, ruta, cuerpo, campos):
    orden_con_bulto(cliente, 5)

    respuesta = post(cliente, ruta, cuerpo, 400)

    assert set(respuesta["error"]["fields"]) == campos
    assert len(cliente.get("/api/necesidades").get_json()["necesidades"]) == 1
    assert cliente.get("/api/bultos/1").get_json()["estado"] == "PREPARADO"


@pytest.mark.parametrize("ruta", ["/api/necesidades/9", "/api/ordenes/9", "/api/bultos/9", "/api/remitos/9"])
def test_consultas_inexistentes_devuelven_404(cliente, ruta):
    assert cliente.get(ruta).status_code == 404


def test_referencias_inexistentes_en_el_cuerpo_devuelven_404_con_campo(cliente):
    sin_necesidad = post(cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [7]}, 404)
    sin_producto = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 9, "cantidad": 1}, 404)
    sin_orden = post(cliente, "/api/ordenes/9/bultos", {"lineas": [{"producto_id": 1, "cantidad": 1}]}, 404)

    assert set(sin_necesidad["error"]["fields"]) == {"necesidad_ids.1"}
    assert set(sin_producto["error"]["fields"]) == {"producto_id"}
    assert sin_orden["error"]["code"] == 404


def test_reglas_del_dominio_se_informan_como_400_o_409_sin_efectos(cliente):
    n1 = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 30}, 201)
    n2 = post(cliente, "/api/necesidades", {"local_id": L2, "producto_id": 1, "cantidad": 1}, 201)
    assert "local destino" in post(cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [1, 2]}, 400)["error"]["message"]
    assert post(cliente, "/api/necesidades", {"local_id": CD, "producto_id": 1, "cantidad": 1}, 400)
    post(cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [n1["id"]]}, 201)
    assert "ya fue consolidada" in post(
        cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [n1["id"]]}, 409
    )["error"]["message"]

    insuficiente = post(cliente, "/api/ordenes/1/bultos", {"lineas": [{"producto_id": 1, "cantidad": 21}]}, 409)
    assert "Stock insuficiente" in insuficiente["error"]["message"]
    assert "no figura" in post(cliente, "/api/ordenes/1/bultos",
                               {"lineas": [{"producto_id": 2, "cantidad": 1}]}, 400)["error"]["message"]
    assert cliente.get("/api/bultos").get_json() == {"bultos": []}
    assert saldos(cliente, CD) == {("001", "DISPONIBLE"): 20, ("002", "DISPONIBLE"): 10}
    assert cliente.get(f"/api/necesidades/{n2['id']}").get_json()["estado"] == "PENDIENTE"


def test_sin_cd_no_se_consolidan_ordenes():
    cliente = create_app().test_client()
    preparar_catalogo(cliente, con_cd=False)
    post(cliente, "/api/necesidades", {"local_id": 1, "producto_id": 1, "cantidad": 1}, 201)

    respuesta = post(cliente, "/api/ordenes", {"local_id": 1, "necesidad_ids": [1]}, 409)

    assert "Centro de Distribución" in respuesta["error"]["message"]


def test_precinto_repetido_sin_distinguir_mayusculas_es_409(cliente):
    orden_con_bulto(cliente, 2)
    orden_con_bulto(cliente, 2)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "Sello-1"})

    respuesta = post(cliente, "/api/bultos/2/precintar", {"precinto": "SELLO-1"}, 409)

    assert "ya fue usado" in respuesta["error"]["message"]
    assert post(cliente, "/api/bultos/2/precintar", {"precinto": "SELLO-2"})["remito"]["numero"] == "R-000002"


def test_fallo_al_guardar_una_transicion_no_deja_cambios(tmp_path, monkeypatch):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar_catalogo(cliente)
    orden_con_bulto(cliente, 5)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    guardar_real = backend.api_logistica.guardar_bulto

    def fallar(conexion, bulto, movimientos):
        guardar_real(conexion, bulto, movimientos[:1])
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(backend.api_logistica, "guardar_bulto", fallar)
    assert post(cliente, "/api/bultos/1/despachar", estado=500)["error"]["code"] == 500
    monkeypatch.setattr(backend.api_logistica, "guardar_bulto", guardar_real)

    for consulta in (cliente, create_app(base_datos=ruta).test_client()):
        assert consulta.get("/api/bultos/1").get_json()["estado"] == "PRECINTADO"
        assert saldos(consulta, CD)[("001", "RESERVADO")] == 5
        assert saldos(consulta, L1) == {}
    assert post(cliente, "/api/bultos/1/despachar")["estado"] == "EN_TRANSITO"


def test_preparaciones_concurrentes_no_superan_lo_pendiente():
    app = create_app()
    cliente = app.test_client()
    preparar_catalogo(cliente)
    necesidad = post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 10}, 201)
    post(cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [necesidad["id"]]}, 201)

    def preparar(_):
        return app.test_client().post("/api/ordenes/1/bultos", json={"lineas": [{"producto_id": 1, "cantidad": 3}]})

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        estados = sorted(respuesta.status_code for respuesta in ejecutor.map(preparar, range(8)))

    assert estados == [201, 201, 201, 409, 409, 409, 409, 409]
    assert saldos(cliente, CD)[("001", "RESERVADO")] == 9


def _base_con_circuito(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar_catalogo(cliente)
    orden_con_bulto(cliente, 5)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    post(cliente, "/api/bultos/1/despachar")
    return BaseDatos(ruta)


@pytest.mark.parametrize("sentencia", [
    "UPDATE eventos_bulto SET estado_nuevo = 'VERIFICADO'",
    "DELETE FROM eventos_bulto",
    # Un despacho ya aplicado no puede repetirse para el mismo bulto, producto y ubicación.
    "INSERT INTO movimientos_stock (instante, ubicacion_id, producto_id, cantidad, condicion_origen, causa, bulto_id)"
    " VALUES ('x', 1, 1, 5, 'RESERVADO', 'DESPACHO', 1)",
    "UPDATE bultos SET estado = 'PERDIDO'",
    "INSERT INTO bultos VALUES (2, 1, 'PRECINTADO', 's-1', 's-1')",
    "UPDATE bultos SET precinto_clave = NULL",
    "INSERT INTO remitos VALUES (2, 1, 'x', 'EMITIDO', NULL)",
    "UPDATE remitos SET estado = 'VERIFICADO'",
    "INSERT INTO detalles_bulto VALUES (1, 2, 0, NULL)",
    "INSERT INTO necesidades VALUES (9, 2, 1, 0, 'x', NULL)",
    "INSERT INTO bultos VALUES (5, 99, 'PREPARADO', NULL, NULL)",
])
def test_esquema_protege_historial_estados_y_referencias(tmp_path, sentencia):
    base_datos = _base_con_circuito(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        base_datos.ejecutar_transaccion(lambda conexion: conexion.execute(sentencia))


def test_base_de_f02_recibe_la_columna_de_bulto_sin_perder_datos(tmp_path):
    ruta = tmp_path / "f02.db"
    conexion = sqlite3.connect(ruta)
    # Tabla tal como la creaba F-02, sin bulto_id.
    conexion.execute("""
        CREATE TABLE movimientos_stock (
            id INTEGER PRIMARY KEY, instante TEXT NOT NULL, ubicacion_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL, cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            condicion_origen TEXT, condicion_destino TEXT, causa TEXT NOT NULL,
            compra_id INTEGER, compra_linea INTEGER
        )
    """)
    conexion.close()

    cliente = create_app(base_datos=ruta).test_client()
    preparar_catalogo(cliente)
    orden_con_bulto(cliente, 5)

    conexion = sqlite3.connect(ruta)
    columnas = [fila[1] for fila in conexion.execute("PRAGMA table_info(movimientos_stock)")]
    conexion.close()
    assert columnas[-1] == "bulto_id"
    assert saldos(create_app(base_datos=ruta).test_client(), CD)[("001", "RESERVADO")] == 5
