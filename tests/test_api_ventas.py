"""Contratos HTTP y persistencia de ventas, cobros, comprobante y caja (F-04.2)."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

import backend.api_compras
import backend.api_logistica
import backend.api_ventas
from backend import create_app
from backend.dominio import ZONA_ARGENTINA
from backend.persistencia import BaseDatos

INSTANTE = datetime(2026, 10, 23, 18, 0, tzinfo=ZONA_ARGENTINA)
CD, L1, L2 = 1, 2, 3
EFECTIVO, DEBITO, CREDITO, TRANSFERENCIA = 1, 2, 3, 4
LOCAL_L1 = {"id": L1, "codigo": "L1", "nombre": "Centro", "tipo": "LOCAL", "activo": True}
ARROZ = {"id": 1, "codigo": "001", "nombre": "Arroz", "activo": True}
FIDEOS = {"id": 2, "codigo": "002", "nombre": "Fideos", "activo": True}


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    for modulo in (backend.api_compras, backend.api_logistica, backend.api_ventas):
        monkeypatch.setattr(modulo, "ahora", lambda: INSTANTE)


def post(cliente, ruta, cuerpo=None, estado=200):
    respuesta = cliente.post(ruta, json={} if cuerpo is None else cuerpo)
    assert respuesta.status_code == estado, respuesta.get_json()
    return respuesta.get_json()


def preparar(cliente):
    """Catálogo, compra al CD y un bulto con doble verificación: L1 queda con 5 arroces y 3 fideos disponibles."""
    post(cliente, "/api/categorias", {"codigo": "ALM", "nombre": "Almacén"}, 201)
    post(cliente, "/api/productos", {"codigo": "001", "nombre": "Arroz", "categoria_id": 1, "precio": "1500"}, 201)
    post(cliente, "/api/productos", {"codigo": "002", "nombre": "Fideos", "categoria_id": 1, "precio": "900.50"}, 201)
    post(cliente, "/api/proveedores", {"codigo": "PRV", "nombre": "Molinos"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "CD", "nombre": "Central", "tipo": "CD"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"}, 201)
    post(cliente, "/api/compras", {"proveedor_id": 1, "lineas": [
        {"producto_id": 1, "cantidad": 20, "costo_unitario": "1000"},
        {"producto_id": 2, "cantidad": 10, "costo_unitario": "400"},
    ]}, 201)
    post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 1, "cantidad": 5}, 201)
    post(cliente, "/api/necesidades", {"local_id": L1, "producto_id": 2, "cantidad": 3}, 201)
    post(cliente, "/api/ordenes", {"local_id": L1, "necesidad_ids": [1, 2]}, 201)
    post(cliente, "/api/ordenes/1/bultos", {"lineas": [
        {"producto_id": 1, "cantidad": 5}, {"producto_id": 2, "cantidad": 3},
    ]}, 201)
    post(cliente, "/api/bultos/1/precintar", {"precinto": "S-1"})
    post(cliente, "/api/bultos/1/despachar")
    post(cliente, "/api/bultos/1/recibir", {"local_id": L1, "precinto_leido": "S-1", "precinto_intacto": True})
    post(cliente, "/api/bultos/1/verificar")
    post(cliente, "/api/remitos/1/verificar")


def venta(*lineas, cobros, clave="clave-1", local_id=L1):
    return {
        "local_id": local_id,
        "clave_operacion": clave,
        "lineas": [{"producto_id": producto_id, "cantidad": cantidad} for producto_id, cantidad in lineas],
        "cobros": [{"medio_pago_id": medio, "importe": importe} for medio, importe in cobros],
    }


def disponible(cliente, ubicacion=L1):
    datos = cliente.get(f"/api/ubicaciones/{ubicacion}/existencias").get_json()["existencias"]
    return {item["producto"]["codigo"]: item["disponible"] for item in datos}


def sin_ventas(cliente):
    assert cliente.get("/api/ventas").get_json() == {"ventas": []}
    assert disponible(cliente) == {"001": 5, "002": 3}
    assert cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"] == []
    assert cliente.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]["causa"] == "VERIFICACION"


@pytest.fixture
def cliente():
    cliente = create_app().test_client()
    preparar(cliente)
    return cliente


def test_venta_con_cobros_divididos_descuenta_stock_y_registra_caja(cliente):
    respuesta = cliente.post("/api/ventas", json=venta(
        (1, 2), (2, 1), cobros=[(EFECTIVO, "2000"), (DEBITO, "1900.50")],
    ))

    assert respuesta.status_code == 201 and respuesta.headers["Location"] == "/api/ventas/1"
    efectivo = {"id": 1, "codigo": "EFECTIVO", "nombre": "Efectivo"}
    debito = {"id": 2, "codigo": "DEBITO", "nombre": "Débito"}
    esperado = {
        "id": 1,
        "comprobante": "CV-00000001",
        "local": LOCAL_L1,
        "instante": "2026-10-23T18:00:00-03:00",
        "clave_operacion": "clave-1",
        "lineas": [
            {"linea": 1, "producto": ARROZ, "cantidad": 2, "precio_unitario": "1500.00",
             "costo_referencia": "1000.00", "subtotal": "3000.00"},
            {"linea": 2, "producto": FIDEOS, "cantidad": 1, "precio_unitario": "900.50",
             "costo_referencia": "400.00", "subtotal": "900.50"},
        ],
        "cobros": [
            {"numero": 1, "medio": efectivo, "importe": "2000.00"},
            {"numero": 2, "medio": debito, "importe": "1900.50"},
        ],
        "total": "3900.50",
        "moneda": "ARS",
    }
    assert respuesta.get_json() == esperado
    assert cliente.get("/api/ventas/1").get_json() == esperado
    assert cliente.get("/api/ventas").get_json() == {"ventas": [esperado]}

    comprobante = cliente.get("/api/ventas/1/comprobante").get_json()
    assert comprobante["numero"] == "CV-00000001" and comprobante["venta_id"] == 1
    assert comprobante["local"] == LOCAL_L1 and comprobante["instante"] == "2026-10-23T18:00:00-03:00"
    assert [(l["producto"]["codigo"], l["precio_unitario"], l["subtotal"]) for l in comprobante["lineas"]] == [
        ("001", "1500.00", "3000.00"), ("002", "900.50", "900.50"),
    ]
    assert "costo_referencia" not in comprobante["lineas"][0] and "clave_operacion" not in comprobante
    assert comprobante["cobros"] == esperado["cobros"] and comprobante["total"] == "3900.50"

    assert disponible(cliente) == {"001": 3, "002": 2}
    movimiento = cliente.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]
    assert movimiento == {
        "id": movimiento["id"], "instante": "2026-10-23T18:00:00-03:00", "producto": FIDEOS, "cantidad": 1,
        "condicion_origen": "DISPONIBLE", "condicion_destino": None, "causa": "VENTA", "compra_id": None,
        "linea": 2, "bulto_id": None, "bulto_codigo": None, "venta_id": 1, "comprobante": "CV-00000001",
        "devolucion_id": None, "devolucion": None,
    }

    caja = cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()
    assert caja["ubicacion"] == LOCAL_L1
    assert [(s["medio"]["codigo"], s["saldo"]) for s in caja["saldos"]] == [
        ("EFECTIVO", "2000.00"), ("DEBITO", "1900.50"), ("CREDITO", "0.00"), ("TRANSFERENCIA", "0.00"),
    ]
    assert caja["movimientos"] == [
        {"id": 1, "instante": "2026-10-23T18:00:00-03:00", "medio": efectivo, "tipo": "INGRESO",
         "importe": "2000.00", "venta_id": 1, "comprobante": "CV-00000001", "cobro": 1,
         "devolucion_id": None, "devolucion": None, "reintegro": None},
        {"id": 2, "instante": "2026-10-23T18:00:00-03:00", "medio": debito, "tipo": "INGRESO",
         "importe": "1900.50", "venta_id": 1, "comprobante": "CV-00000001", "cobro": 2,
         "devolucion_id": None, "devolucion": None, "reintegro": None},
    ]
    assert cliente.get(f"/api/ubicaciones/{L2}/caja").get_json()["movimientos"] == []


def test_medios_de_pago_fijos_consultables(cliente):
    assert cliente.get("/api/medios-pago").get_json() == {"medios_pago": [
        {"id": 1, "codigo": "EFECTIVO", "nombre": "Efectivo"}, {"id": 2, "codigo": "DEBITO", "nombre": "Débito"},
        {"id": 3, "codigo": "CREDITO", "nombre": "Crédito"},
        {"id": 4, "codigo": "TRANSFERENCIA", "nombre": "Transferencia"},
    ]}


def test_reinicio_conserva_ventas_caja_y_stock_y_continua_la_numeracion(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/ventas", venta((1, 2), cobros=[(CREDITO, "3000")]), 201)
    consultas = ["/api/ventas", "/api/ventas/1/comprobante", f"/api/ubicaciones/{L1}/caja",
                 f"/api/ubicaciones/{L1}/saldos", f"/api/ubicaciones/{L1}/movimientos"]
    antes = [cliente.get(consulta).get_json() for consulta in consultas]

    reiniciado = create_app(base_datos=ruta).test_client()

    assert [reiniciado.get(consulta).get_json() for consulta in consultas] == antes
    repetida = post(reiniciado, "/api/ventas", venta((1, 2), cobros=[(CREDITO, "3000")]), 200)
    assert repetida["id"] == 1 and disponible(reiniciado) == {"001": 3, "002": 3}
    segunda = post(reiniciado, "/api/ventas", venta((2, 3), cobros=[(EFECTIVO, "2701.50")], clave="clave-2"), 201)
    assert segunda["comprobante"] == "CV-00000002"
    caja = reiniciado.get(f"/api/ubicaciones/{L1}/caja").get_json()
    assert [m["id"] for m in caja["movimientos"]] == [1, 2]
    assert disponible(create_app(base_datos=ruta).test_client()) == {"001": 3, "002": 0}


def test_clave_repetida_devuelve_la_venta_existente_sin_efectos(cliente):
    primera = post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")]), 201)

    otra = cliente.post("/api/ventas", json=venta((2, 3), cobros=[(DEBITO, "2701.50")]))

    assert otra.status_code == 200 and otra.headers["Location"] == "/api/ventas/1"
    assert otra.get_json() == primera
    assert len(cliente.get("/api/ventas").get_json()["ventas"]) == 1
    assert disponible(cliente) == {"001": 4, "002": 3}
    assert len(cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"]) == 1


def test_precio_y_costo_historicos_no_cambian_con_el_catalogo(cliente):
    post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")]), 201)

    cliente.put("/api/productos/1", json={"codigo": "001", "nombre": "Arroz", "categoria_id": 1, "precio": "1800"})
    post(cliente, "/api/compras", {"proveedor_id": 1, "lineas": [
        {"producto_id": 1, "cantidad": 1, "costo_unitario": "1200"},
    ]}, 201)

    linea = cliente.get("/api/ventas/1").get_json()["lineas"][0]
    assert (linea["precio_unitario"], linea["costo_referencia"]) == ("1500.00", "1000.00")
    nueva = post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1800")], clave="clave-2"), 201)
    assert (nueva["lineas"][0]["precio_unitario"], nueva["lineas"][0]["costo_referencia"]) == ("1800.00", "1200.00")


def test_una_linea_sin_stock_impide_toda_la_venta(cliente):
    respuesta = post(cliente, "/api/ventas", venta((2, 1), (1, 6), cobros=[(EFECTIVO, "9900.50")]), 409)

    assert "Stock insuficiente de 001 en L1" in respuesta["error"]["message"]
    sin_ventas(cliente)


def test_stock_pendiente_de_verificar_no_se_vende(cliente):
    post(cliente, "/api/necesidades", {"local_id": L2, "producto_id": 1, "cantidad": 2}, 201)
    post(cliente, "/api/ordenes", {"local_id": L2, "necesidad_ids": [3]}, 201)
    post(cliente, "/api/ordenes/2/bultos", {"lineas": [{"producto_id": 1, "cantidad": 2}]}, 201)
    post(cliente, "/api/bultos/2/precintar", {"precinto": "S-2"})
    post(cliente, "/api/bultos/2/despachar")
    post(cliente, "/api/bultos/2/recibir", {"local_id": L2, "precinto_leido": "S-2", "precinto_intacto": True})
    post(cliente, "/api/bultos/2/verificar")

    pendiente = post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")], local_id=L2), 409)
    post(cliente, "/api/remitos/2/verificar")
    habilitada = post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")], local_id=L2), 201)

    assert "condición DISPONIBLE" in pendiente["error"]["message"]
    assert habilitada["local"]["codigo"] == "L2" and disponible(cliente, L2) == {"001": 1}


@pytest.mark.parametrize("cuerpo,campos", [
    ({"local_id": L1, "lineas": [], "cobros": []}, {"clave_operacion"}),
    ({**venta((1, 1), cobros=[(1, "1500")]), "descuento": "10"}, {"descuento"}),
    ({**venta((1, 1), cobros=[(1, "1500")]), "lineas": {"producto_id": 1}}, {"lineas"}),
    ({**venta((1, 1), cobros=[(1, "1500")]), "cobros": "1500"}, {"cobros"}),
    (venta((1, "1"), cobros=[(1, "1500")]), {"lineas.1.cantidad"}),
    (venta((1, 2**53), cobros=[(1, "1500")]), {"lineas.1.cantidad"}),
    ({**venta((1, 1), cobros=[]), "cobros": [7]}, {"cobros.1"}),
    (venta((1, 1), cobros=[(1, 1500)]), {"cobros.1.importe"}),
    (venta((1, 1), cobros=[(1, "1000"), ("2", "500")]), {"cobros.2.medio_pago_id"}),
    ({**venta((1, 1), cobros=[]), "cobros": [{"medio_pago_id": 1, "importe": "1500", "vuelto": "0"}]},
     {"cobros.1.vuelto"}),
])
def test_formato_invalido_devuelve_400_con_campos(cliente, cuerpo, campos):
    respuesta = post(cliente, "/api/ventas", cuerpo, 400)

    assert set(respuesta["error"]["fields"]) == campos
    sin_ventas(cliente)


def test_referencias_inexistentes_devuelven_404_con_el_campo(cliente):
    casos = [
        (venta((1, 1), cobros=[(1, "1500")], local_id=9), {"local_id"}),
        (venta((1, 1), (9, 1), cobros=[(1, "1500")]), {"lineas.2.producto_id"}),
        (venta((1, 1), cobros=[(1, "1000"), (9, "500")]), {"cobros.2.medio_pago_id"}),
    ]
    for cuerpo, campos in casos:
        assert set(post(cliente, "/api/ventas", cuerpo, 404)["error"]["fields"]) == campos
    sin_ventas(cliente)


@pytest.mark.parametrize("cuerpo,estado,mensaje", [
    (venta((1, 1), cobros=[(1, "1000")]), 400, "Los cobros suman 1000.00 y el total de la venta es 1500.00."),
    (venta((1, 1), cobros=[(1, "1000"), (2, "600")]), 400, "suman 1600.00"),
    (venta((1, 1), cobros=[(1, "1000"), (1, "500")]), 400, "Cobro 2: un medio de pago no puede repetirse"),
    (venta((1, 1), cobros=[(1, "1500.001")]), 400, "Cobro 1:"),
    (venta((1, 1), (1, 1), cobros=[(1, "3000")]), 400, "Línea 2: un producto no puede repetirse"),
    (venta((1, 0), cobros=[(1, "1500")]), 400, "Línea 1:"),
    (venta(cobros=[(1, "1500")]), 400, "al menos una línea"),
    (venta((1, 1), cobros=[]), 400, "al menos un cobro"),
    (venta((1, 1), cobros=[(1, "1500")], clave="   "), 400, "clave de operación"),
    (venta((1, 1), cobros=[(1, "1500")], clave="x" * 65), 400, "64 caracteres"),
    (venta((1, 1), cobros=[(1, "1500")], local_id=CD), 400, "no el CD"),
])
def test_reglas_del_dominio_se_informan_sin_efectos(cliente, cuerpo, estado, mensaje):
    respuesta = post(cliente, "/api/ventas", cuerpo, estado)

    assert mensaje in respuesta["error"]["message"]
    sin_ventas(cliente)


@pytest.mark.parametrize("baja", ["/api/ubicaciones/2/estado", "/api/productos/1/estado"])
def test_local_o_producto_inactivo_devuelve_409(cliente, baja):
    cliente.patch(baja, json={"activo": False})

    respuesta = post(cliente, "/api/ventas", venta((1, 1), cobros=[(1, "1500")]), 409)

    assert "inactiv" in respuesta["error"]["message"]
    assert cliente.get("/api/ventas").get_json() == {"ventas": []}


@pytest.mark.parametrize("ruta", ["/api/ventas/9", "/api/ventas/9/comprobante", "/api/ubicaciones/9/caja"])
def test_consultas_inexistentes_devuelven_404_json(cliente, ruta):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 404 and respuesta.get_json()["error"]["code"] == 404


def test_fallo_al_guardar_no_deja_venta_stock_ni_caja(tmp_path, monkeypatch):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    guardar_real = backend.api_ventas.guardar_venta

    def fallar(conexion, venta_registrada, movimientos, movimientos_caja):
        guardar_real(conexion, venta_registrada, movimientos, movimientos_caja[:1])
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(backend.api_ventas, "guardar_venta", fallar)
    cuerpo = venta((1, 2), cobros=[(EFECTIVO, "1000"), (DEBITO, "2000")])
    assert post(cliente, "/api/ventas", cuerpo, 500)["error"]["code"] == 500
    monkeypatch.setattr(backend.api_ventas, "guardar_venta", guardar_real)

    sin_ventas(cliente)
    sin_ventas(create_app(base_datos=ruta).test_client())
    reintento = post(cliente, "/api/ventas", cuerpo, 201)
    assert reintento["id"] == 1 and disponible(cliente) == {"001": 3, "002": 3}


def test_ventas_concurrentes_no_venden_de_mas_ni_duplican_claves():
    app = create_app()
    preparar(app.test_client())

    def vender(numero):
        return app.test_client().post("/api/ventas", json=venta((1, 1), cobros=[(EFECTIVO, "1500")],
                                                                clave=f"clave-{numero}"))

    def repetir(_):
        return app.test_client().post("/api/ventas", json=venta((2, 1), cobros=[(EFECTIVO, "900.50")],
                                                                clave="misma"))

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        distintas = sorted(respuesta.status_code for respuesta in ejecutor.map(vender, range(8)))
        repetidas = sorted(respuesta.status_code for respuesta in ejecutor.map(repetir, range(4)))

    assert distintas == [201] * 5 + [409] * 3
    assert repetidas == [200, 200, 200, 201]
    cliente = app.test_client()
    assert disponible(cliente) == {"001": 0, "002": 2}
    assert sorted(v["id"] for v in cliente.get("/api/ventas").get_json()["ventas"]) == list(range(1, 7))
    assert cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()["saldos"][0]["saldo"] == "8400.50"


def _base_con_venta(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")]), 201)
    return BaseDatos(ruta)


@pytest.mark.parametrize("sentencia", [
    "INSERT INTO ventas VALUES (2, 2, 'x', 'clave-1')",
    "INSERT INTO ventas VALUES (2, 2, 'x', '')",
    "INSERT INTO ventas VALUES (2, 99, 'x', 'otra')",
    "INSERT INTO detalles_venta VALUES (1, 2, 1, 1, 100, NULL)",
    "INSERT INTO detalles_venta VALUES (1, 2, 2, 0, 100, NULL)",
    "INSERT INTO detalles_venta VALUES (1, 2, 2, 1, 0, NULL)",
    "INSERT INTO detalles_venta VALUES (1, 2, 2, 1, 100, 0)",
    "INSERT INTO detalles_venta VALUES (9, 1, 1, 1, 100, NULL)",
    "INSERT INTO cobros VALUES (1, 2, 1, 100)",
    "INSERT INTO cobros VALUES (1, 2, 2, 0)",
    "INSERT INTO cobros VALUES (1, 2, 9, 100)",
    "UPDATE medios_pago SET codigo = 'DEBITO' WHERE id = 1",
    # Los movimientos de caja son evidencia: no se editan ni se borran.
    "UPDATE movimientos_caja SET importe_centavos = 1",
    "DELETE FROM movimientos_caja",
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos,"
    " cobro_venta_id, cobro_numero) VALUES (2, 'x', 2, 1, 'INGRESO', 100, NULL, NULL)",
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos,"
    " cobro_venta_id, cobro_numero) VALUES (2, 'x', 2, 1, 'INGRESO', 100, 1, 1)",
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos,"
    " cobro_venta_id, cobro_numero) VALUES (2, 'x', 2, 1, 'EGRESO', 100, 1, 1)",
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos,"
    " cobro_venta_id, cobro_numero) VALUES (2, 'x', 2, 1, 'AJUSTE', 100, NULL, NULL)",
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos,"
    " cobro_venta_id, cobro_numero) VALUES (2, 'x', 2, 1, 'INGRESO', 0, 1, 2)",
    # Una venta sin línea o una línea ya descontada no pueden generar otro movimiento.
    "INSERT INTO movimientos_stock (instante, ubicacion_id, producto_id, cantidad, condicion_origen, causa)"
    " VALUES ('x', 2, 1, 1, 'DISPONIBLE', 'VENTA')",
    "INSERT INTO movimientos_stock (instante, ubicacion_id, producto_id, cantidad, condicion_origen, causa,"
    " venta_id, venta_linea) VALUES ('x', 2, 1, 1, 'DISPONIBLE', 'VENTA', 1, 1)",
])
def test_esquema_protege_ventas_cobros_y_caja(tmp_path, sentencia):
    base_datos = _base_con_venta(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        base_datos.ejecutar_transaccion(lambda conexion: conexion.execute(sentencia))


def test_base_anterior_recibe_columnas_de_venta_y_trigger_actualizado(tmp_path):
    ruta = tmp_path / "f03.db"
    conexion = sqlite3.connect(ruta)
    # Tabla y trigger tal como los dejaba F-03: sin línea de venta y exigiendo bulto a toda causa no COMPRA.
    conexion.executescript("""
        CREATE TABLE movimientos_stock (
            id INTEGER PRIMARY KEY, instante TEXT NOT NULL, ubicacion_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL, cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            condicion_origen TEXT, condicion_destino TEXT, causa TEXT NOT NULL,
            compra_id INTEGER, compra_linea INTEGER, bulto_id INTEGER
        );
        CREATE TRIGGER movimientos_logisticos_con_bulto BEFORE INSERT ON movimientos_stock
        WHEN NEW.causa <> 'COMPRA' AND NEW.bulto_id IS NULL
        BEGIN
            SELECT RAISE(ABORT, 'Un movimiento logístico debe referenciar su bulto.');
        END;
    """)
    conexion.close()

    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/ventas", venta((1, 1), cobros=[(EFECTIVO, "1500")]), 201)

    reiniciado = create_app(base_datos=ruta).test_client()
    assert disponible(reiniciado) == {"001": 4, "002": 3}
    assert reiniciado.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]["venta_id"] == 1
