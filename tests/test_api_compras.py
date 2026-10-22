"""Contratos HTTP y persistencia de compras, existencias y movimientos (F-02.2)."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

import backend.api_compras
from backend import create_app
from backend.dominio import ZONA_ARGENTINA
from backend.persistencia import BaseDatos

INSTANTE = datetime(2026, 10, 21, 10, 0, tzinfo=ZONA_ARGENTINA)


@pytest.fixture
def reloj(monkeypatch):
    monkeypatch.setattr(backend.api_compras, "ahora", lambda: INSTANTE)


def preparar(cliente, con_cd=True):
    cliente.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"})
    for codigo, nombre in [("001", "Arroz"), ("002", "Fideos")]:
        cliente.post("/api/productos", json={"codigo": codigo, "nombre": nombre, "categoria_id": 1, "precio": "1500"})
    cliente.post("/api/proveedores", json={"codigo": "PRV", "nombre": "Molinos"})
    cliente.post("/api/ubicaciones", json={"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"})
    if con_cd:
        cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"})


def compra(*lineas, proveedor_id=1):
    return {
        "proveedor_id": proveedor_id,
        "lineas": [
            {"producto_id": producto_id, "cantidad": cantidad, "costo_unitario": costo}
            for producto_id, cantidad, costo in lineas
        ],
    }


def sin_efectos(cliente):
    assert cliente.get("/api/compras").get_json() == {"compras": []}
    if cliente.get("/api/ubicaciones/2").status_code == 200:
        assert cliente.get("/api/ubicaciones/2/existencias").get_json()["existencias"] == []
        assert cliente.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"] == []


def test_registrar_compra_ingresa_stock_al_cd_y_queda_consultable(reloj):
    cliente = create_app().test_client()
    preparar(cliente)

    respuesta = cliente.post("/api/compras", json=compra((1, 10, "1000"), (2, 3, "450.5")))

    assert respuesta.status_code == 201
    assert respuesta.headers["Location"] == "/api/compras/1"
    producto = lambda i, c, n: {"id": i, "codigo": c, "nombre": n, "activo": True}
    esperado = {
        "id": 1,
        "proveedor": {"id": 1, "codigo": "PRV", "nombre": "Molinos", "activo": True},
        "centro": {"id": 2, "codigo": "CD", "nombre": "Central", "activo": True, "tipo": "CD"},
        "instante": "2026-10-21T10:00:00-03:00",
        "lineas": [
            {"linea": 1, "producto": producto(1, "001", "Arroz"), "cantidad": 10,
             "costo_unitario": "1000.00", "subtotal": "10000.00"},
            {"linea": 2, "producto": producto(2, "002", "Fideos"), "cantidad": 3,
             "costo_unitario": "450.50", "subtotal": "1351.50"},
        ],
        "total": "11351.50",
        "moneda": "ARS",
    }
    assert respuesta.get_json() == esperado
    assert cliente.get("/api/compras/1").get_json() == esperado
    assert cliente.get("/api/compras").get_json() == {"compras": [esperado]}

    existencias = cliente.get("/api/ubicaciones/2/existencias").get_json()
    assert existencias["ubicacion"]["tipo"] == "CD"
    assert existencias["existencias"] == [
        {"producto": producto(1, "001", "Arroz"), "disponible": 10, "costo_referencia": "1000.00"},
        {"producto": producto(2, "002", "Fideos"), "disponible": 3, "costo_referencia": "450.50"},
    ]
    movimientos = cliente.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"]
    assert movimientos[1] == {
        "id": 2, "instante": "2026-10-21T10:00:00-03:00", "producto": producto(2, "002", "Fideos"),
        "cantidad": 3, "condicion_origen": None, "condicion_destino": "DISPONIBLE", "causa": "COMPRA",
        "compra_id": 1, "linea": 2,
    }
    assert cliente.get("/api/ubicaciones/1/existencias").get_json()["existencias"] == []
    assert cliente.get("/api/ubicaciones/1/movimientos").get_json()["movimientos"] == []


def test_segunda_compra_acumula_saldo_y_actualiza_costo_de_referencia(reloj):
    cliente = create_app().test_client()
    preparar(cliente)
    cliente.post("/api/compras", json=compra((1, 10, "100")))

    segunda = cliente.post("/api/compras", json=compra((1, 5, "120")))

    assert segunda.status_code == 201 and segunda.get_json()["id"] == 2
    assert cliente.get("/api/ubicaciones/2/existencias").get_json()["existencias"][0] == {
        "producto": {"id": 1, "codigo": "001", "nombre": "Arroz", "activo": True},
        "disponible": 15, "costo_referencia": "120.00",
    }
    assert [m["compra_id"] for m in cliente.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"]] == [1, 2]


def test_reiniciar_conserva_compras_saldos_movimientos_y_continua_ids(tmp_path, reloj):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    cliente.post("/api/compras", json=compra((1, 10, "100"), (2, 4, "80")))
    cliente.patch("/api/productos/2/estado", json={"activo": False})
    cliente.patch("/api/proveedores/1/estado", json={"activo": False})
    consultas = ["/api/compras", "/api/ubicaciones/2/existencias", "/api/ubicaciones/2/movimientos"]
    antes = [cliente.get(ruta_consulta).get_json() for ruta_consulta in consultas]

    reiniciado = create_app(base_datos=ruta).test_client()

    assert [reiniciado.get(ruta_consulta).get_json() for ruta_consulta in consultas] == antes
    reiniciado.post("/api/proveedores", json={"codigo": "PRV2", "nombre": "Otro"})
    nueva = reiniciado.post("/api/compras", json=compra((1, 1, "130"), proveedor_id=2))
    assert nueva.status_code == 201 and nueva.get_json()["id"] == 2
    movimientos = reiniciado.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"]
    assert [m["id"] for m in movimientos] == [1, 2, 3]
    existencias = create_app(base_datos=ruta).test_client().get("/api/ubicaciones/2/existencias").get_json()
    assert [(e["disponible"], e["costo_referencia"]) for e in existencias["existencias"]] == [
        (11, "130.00"), (4, "80.00"),
    ]


@pytest.mark.parametrize("cuerpo,campos", [
    ({"lineas": []}, {"proveedor_id"}),
    ({"proveedor_id": 1}, {"lineas"}),
    ({"proveedor_id": "1", "lineas": []}, {"proveedor_id"}),
    ({"proveedor_id": 1, "lineas": {}}, {"lineas"}),
    ({"proveedor_id": 1, "lineas": [], "centro_id": 2}, {"centro_id"}),
    ({"proveedor_id": 1, "lineas": ["x"]}, {"lineas.1"}),
    ({"proveedor_id": 1, "lineas": [{"producto_id": 1, "cantidad": 1}]}, {"lineas.1.costo_unitario"}),
    ({"proveedor_id": 1, "lineas": [{"producto_id": 1, "cantidad": True, "costo_unitario": "1"}]},
     {"lineas.1.cantidad"}),
    ({"proveedor_id": 1, "lineas": [{"producto_id": 1, "cantidad": 1.0, "costo_unitario": "1"}]},
     {"lineas.1.cantidad"}),
    ({"proveedor_id": 1, "lineas": [{"producto_id": 1, "cantidad": 1, "costo_unitario": 1}]},
     {"lineas.1.costo_unitario"}),
    ({"proveedor_id": 1, "lineas": [{"producto_id": 1, "cantidad": 2**53, "costo_unitario": "1"}]},
     {"lineas.1.cantidad"}),
    ({"proveedor_id": 1, "lineas": [
        {"producto_id": 1, "cantidad": 1, "costo_unitario": "1"},
        {"producto_id": 2, "cantidad": 1, "costo_unitario": "1", "precio": "1"},
    ]}, {"lineas.2.precio"}),
])
def test_formato_invalido_devuelve_400_con_campos_y_no_registra(cuerpo, campos):
    cliente = create_app().test_client()
    preparar(cliente)

    respuesta = cliente.post("/api/compras", json=cuerpo)

    assert respuesta.status_code == 400
    assert set(respuesta.get_json()["error"]["fields"]) == campos
    sin_efectos(cliente)


@pytest.mark.parametrize("lineas,mensaje", [
    ([], "al menos una línea"),
    ([(1, 0, "100")], "cantidad"),
    ([(1, -2, "100")], "cantidad"),
    ([(1, 1, "0")], "costo unitario"),
    ([(1, 1, "1.001")], "costo unitario"),
    ([(1, 1, "92233720368547758.08")], "costo unitario"),
    ([(1, 1, "100"), (1, 2, "100")], "repetirse"),
    ([(1, 5, "100"), (2, 0, "100")], "cantidad"),
])
def test_contenido_invalido_devuelve_400_sin_efectos_parciales(lineas, mensaje):
    cliente = create_app().test_client()
    preparar(cliente)

    respuesta = cliente.post("/api/compras", json=compra(*lineas))

    assert respuesta.status_code == 400
    assert mensaje in respuesta.get_json()["error"]["message"]
    sin_efectos(cliente)


def test_referencias_inexistentes_devuelven_404_con_el_campo():
    cliente = create_app().test_client()
    preparar(cliente)

    proveedor = cliente.post("/api/compras", json=compra((1, 1, "1"), proveedor_id=9))
    producto = cliente.post("/api/compras", json=compra((1, 1, "1"), (9, 1, "1")))

    assert proveedor.status_code == 404
    assert set(proveedor.get_json()["error"]["fields"]) == {"proveedor_id"}
    assert producto.status_code == 404
    assert set(producto.get_json()["error"]["fields"]) == {"lineas.2.producto_id"}
    assert cliente.post("/api/compras", json=compra((1, 1, "1"), proveedor_id=0)).status_code == 400
    sin_efectos(cliente)


def test_sin_cd_registrado_la_compra_es_409():
    cliente = create_app().test_client()
    preparar(cliente, con_cd=False)

    respuesta = cliente.post("/api/compras", json=compra((1, 1, "100")))

    assert respuesta.status_code == 409
    assert "Centro de Distribución" in respuesta.get_json()["error"]["message"]
    assert cliente.get("/api/compras").get_json() == {"compras": []}


@pytest.mark.parametrize("baja", ["/api/proveedores/1/estado", "/api/productos/2/estado"])
def test_proveedor_o_producto_inactivo_devuelve_409(baja):
    cliente = create_app().test_client()
    preparar(cliente)
    cliente.patch(baja, json={"activo": False})

    respuesta = cliente.post("/api/compras", json=compra((1, 1, "100"), (2, 1, "100")))

    assert respuesta.status_code == 409
    sin_efectos(cliente)


def test_consultas_inexistentes_devuelven_404_json():
    cliente = create_app().test_client()
    preparar(cliente)

    for ruta in ["/api/compras/1", "/api/ubicaciones/9/existencias", "/api/ubicaciones/9/movimientos"]:
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 404
        assert respuesta.get_json()["error"]["code"] == 404


def test_fallo_al_guardar_devuelve_500_sin_compra_ni_stock_en_memoria_o_base(tmp_path, monkeypatch, reloj):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    guardar_real = backend.api_compras.guardar_compra

    def fallar(conexion, compra_registrada, movimientos):
        guardar_real(conexion, compra_registrada, movimientos[:1])
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(backend.api_compras, "guardar_compra", fallar)
    respuesta = cliente.post("/api/compras", json=compra((1, 10, "100"), (2, 5, "100")))
    assert respuesta.status_code == 500
    monkeypatch.setattr(backend.api_compras, "guardar_compra", guardar_real)

    sin_efectos(cliente)
    sin_efectos(create_app(base_datos=ruta).test_client())
    reintento = cliente.post("/api/compras", json=compra((1, 10, "100")))
    assert reintento.status_code == 201 and reintento.get_json()["id"] == 1
    assert cliente.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"][0]["id"] == 1


def test_compras_concurrentes_no_pierden_saldo_ni_repiten_ids():
    app = create_app()
    preparar(app.test_client())

    def registrar(_):
        return app.test_client().post("/api/compras", json=compra((1, 2, "100")))

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        respuestas = list(ejecutor.map(registrar, range(16)))

    assert sorted(r.get_json()["id"] for r in respuestas) == list(range(1, 17))
    cliente = app.test_client()
    assert cliente.get("/api/ubicaciones/2/existencias").get_json()["existencias"][0]["disponible"] == 32
    assert len(cliente.get("/api/ubicaciones/2/movimientos").get_json()["movimientos"]) == 16


def _base_con_compra(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    cliente.post("/api/compras", json=compra((1, 1, "100")))
    return BaseDatos(ruta)


@pytest.mark.parametrize("sentencia", [
    # Una línea de compra ya ingresada no puede generar otro movimiento.
    "INSERT INTO movimientos_stock VALUES (2, 'x', 2, 1, 1, NULL, 'DISPONIBLE', 'COMPRA', 1, 1)",
    "INSERT INTO movimientos_stock VALUES (2, 'x', 2, 1, 1, NULL, 'DISPONIBLE', 'COMPRA', NULL, NULL)",
    "INSERT INTO movimientos_stock VALUES (2, 'x', 2, 1, 1, NULL, NULL, 'AJUSTE', NULL, NULL)",
    "INSERT INTO movimientos_stock VALUES (2, 'x', 2, 1, 0, NULL, 'DISPONIBLE', 'AJUSTE', NULL, NULL)",
    "INSERT INTO movimientos_stock VALUES (2, 'x', 2, 1, 1, NULL, 'VENDIBLE', 'AJUSTE', NULL, NULL)",
    "UPDATE existencias SET cantidad = -1",
    "INSERT INTO existencias VALUES (2, 1, 'OTRA', 1)",
    "INSERT INTO detalles_compra VALUES (1, 2, 1, 1, 100)",
    "INSERT INTO detalles_compra VALUES (9, 1, 1, 1, 100)",
    "INSERT INTO detalles_compra VALUES (1, 2, 2, 0, 100)",
    "INSERT INTO detalles_compra VALUES (1, 2, 2, 1, 0)",
    "INSERT INTO compras VALUES (2, 9, 2, 'x')",
])
def test_esquema_rechaza_movimientos_saldos_y_detalles_invalidos(tmp_path, sentencia):
    base_datos = _base_con_compra(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        base_datos.ejecutar_transaccion(lambda conexion: conexion.execute(sentencia))
