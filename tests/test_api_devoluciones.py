"""Contratos HTTP y persistencia de devoluciones, reintegros y stock bloqueado (F-05.2)."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

import backend.api_compras
import backend.api_devoluciones
import backend.api_logistica
import backend.api_ventas
from backend import create_app
from backend.dominio import ZONA_ARGENTINA
from backend.persistencia import BaseDatos

INSTANTE = datetime(2026, 10, 23, 18, 0, tzinfo=ZONA_ARGENTINA)
CD, L1, L2 = 1, 2, 3
EFECTIVO, DEBITO, CREDITO = 1, 2, 3
LOCAL_L1 = {"id": L1, "codigo": "L1", "nombre": "Centro", "tipo": "LOCAL", "activo": True}
ARROZ = {"id": 1, "codigo": "001", "nombre": "Arroz", "activo": True}
FIDEOS = {"id": 2, "codigo": "002", "nombre": "Fideos", "activo": True}
MEDIO_EFECTIVO = {"id": 1, "codigo": "EFECTIVO", "nombre": "Efectivo"}
MEDIO_DEBITO = {"id": 2, "codigo": "DEBITO", "nombre": "Débito"}


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    for modulo in (backend.api_compras, backend.api_logistica, backend.api_ventas, backend.api_devoluciones):
        monkeypatch.setattr(modulo, "ahora", lambda: INSTANTE)


def post(cliente, ruta, cuerpo=None, estado=200):
    respuesta = cliente.post(ruta, json={} if cuerpo is None else cuerpo)
    assert respuesta.status_code == estado, respuesta.get_json()
    return respuesta.get_json()


def preparar(cliente):
    """L1 recibe 5 arroces y 3 fideos verificados y vende 3 arroces y 2 fideos (6301.00).

    Cobros de la venta 1: 4000 en efectivo y 2301 con débito. Quedan disponibles 2 arroces y 1 fideo.
    """
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
    post(cliente, "/api/ventas", {
        "local_id": L1, "clave_operacion": "venta-1",
        "lineas": [{"producto_id": 1, "cantidad": 3}, {"producto_id": 2, "cantidad": 2}],
        "cobros": [{"medio_pago_id": EFECTIVO, "importe": "4000"}, {"medio_pago_id": DEBITO, "importe": "2301"}],
    }, 201)


def devolucion(*lineas, reintegros, clave="dev-1", venta_id=1, motivo="Cambio de opinión"):
    """lineas: (línea de la venta, cantidad, apto). reintegros: (medio, importe)."""
    return {
        "venta_id": venta_id,
        "clave_operacion": clave,
        "motivo": motivo,
        "lineas": [{"linea": linea, "cantidad": cantidad, "apto": apto} for linea, cantidad, apto in lineas],
        "reintegros": [{"medio_pago_id": medio, "importe": importe} for medio, importe in reintegros],
    }


def saldos(cliente, ubicacion=L1):
    datos = cliente.get(f"/api/ubicaciones/{ubicacion}/saldos").get_json()["saldos"]
    return {(item["producto"]["codigo"], item["condicion"]): item["cantidad"] for item in datos}


def sin_devoluciones(cliente):
    assert cliente.get("/api/devoluciones").get_json() == {"devoluciones": []}
    assert saldos(cliente) == {("001", "DISPONIBLE"): 2, ("002", "DISPONIBLE"): 1}
    assert [m["tipo"] for m in cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"]] == [
        "INGRESO", "INGRESO",
    ]
    assert cliente.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]["causa"] == "VENTA"


@pytest.fixture
def cliente():
    cliente = create_app().test_client()
    preparar(cliente)
    return cliente


def test_devolucion_parcial_con_aptitud_reintegra_y_actualiza_stock_y_caja(cliente):
    respuesta = cliente.post("/api/devoluciones", json=devolucion(
        (1, 1, True), (2, 1, False), reintegros=[(EFECTIVO, "2000"), (DEBITO, "400.50")],
    ))

    assert respuesta.status_code == 201 and respuesta.headers["Location"] == "/api/devoluciones/1"
    esperado = {
        "id": 1,
        "numero": "DV-00000001",
        "venta_id": 1,
        "comprobante": "CV-00000001",
        "local": LOCAL_L1,
        "instante": "2026-10-23T18:00:00-03:00",
        "motivo": "Cambio de opinión",
        "clave_operacion": "dev-1",
        "lineas": [
            {"linea": 1, "venta_linea": 1, "producto": ARROZ, "cantidad": 1, "apto": True,
             "condicion_destino": "DISPONIBLE", "precio_unitario": "1500.00", "importe": "1500.00"},
            {"linea": 2, "venta_linea": 2, "producto": FIDEOS, "cantidad": 1, "apto": False,
             "condicion_destino": "BLOQUEADO", "precio_unitario": "900.50", "importe": "900.50"},
        ],
        "reintegros": [
            {"numero": 1, "medio": MEDIO_EFECTIVO, "importe": "2000.00"},
            {"numero": 2, "medio": MEDIO_DEBITO, "importe": "400.50"},
        ],
        "total": "2400.50",
        "moneda": "ARS",
    }
    assert respuesta.get_json() == esperado
    assert cliente.get("/api/devoluciones/1").get_json() == esperado
    assert cliente.get("/api/devoluciones").get_json() == {"devoluciones": [esperado]}

    assert saldos(cliente) == {("001", "DISPONIBLE"): 3, ("002", "DISPONIBLE"): 1, ("002", "BLOQUEADO"): 1}
    movimiento = cliente.get(f"/api/ubicaciones/{L1}/movimientos").get_json()["movimientos"][-1]
    assert movimiento == {
        "id": movimiento["id"], "instante": "2026-10-23T18:00:00-03:00", "producto": FIDEOS, "cantidad": 1,
        "condicion_origen": None, "condicion_destino": "BLOQUEADO", "causa": "DEVOLUCION", "compra_id": None,
        "linea": 2, "bulto_id": None, "bulto_codigo": None, "venta_id": None, "comprobante": None,
        "devolucion_id": 1, "devolucion": "DV-00000001",
    }

    caja = cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()
    assert [(s["medio"]["codigo"], s["saldo"]) for s in caja["saldos"]][:2] == [
        ("EFECTIVO", "2000.00"), ("DEBITO", "1900.50"),
    ]
    assert caja["movimientos"][2:] == [
        {"id": 3, "instante": "2026-10-23T18:00:00-03:00", "medio": MEDIO_EFECTIVO, "tipo": "EGRESO",
         "importe": "2000.00", "venta_id": 1, "comprobante": "CV-00000001", "cobro": None,
         "devolucion_id": 1, "devolucion": "DV-00000001", "reintegro": 1},
        {"id": 4, "instante": "2026-10-23T18:00:00-03:00", "medio": MEDIO_DEBITO, "tipo": "EGRESO",
         "importe": "400.50", "venta_id": 1, "comprobante": "CV-00000001", "cobro": None,
         "devolucion_id": 1, "devolucion": "DV-00000001", "reintegro": 2},
    ]
    # La venta y su comprobante no se reescriben.
    assert [linea["cantidad"] for linea in cliente.get("/api/ventas/1").get_json()["lineas"]] == [3, 2]


def test_estado_de_devolucion_de_la_venta(cliente):
    vacio = cliente.get("/api/ventas/1/devoluciones").get_json()
    assert vacio == {
        "venta_id": 1, "comprobante": "CV-00000001", "local": LOCAL_L1,
        "lineas": [
            {"linea": 1, "producto": ARROZ, "vendida": 3, "devuelta": 0, "remanente": 3, "precio_unitario": "1500.00"},
            {"linea": 2, "producto": FIDEOS, "vendida": 2, "devuelta": 0, "remanente": 2, "precio_unitario": "900.50"},
        ],
        "reintegrable": [
            {"medio": MEDIO_EFECTIVO, "importe": "4000.00"}, {"medio": MEDIO_DEBITO, "importe": "2301.00"},
        ],
        "devoluciones": [],
    }

    registrada = post(cliente, "/api/devoluciones", devolucion((1, 2, True), reintegros=[(EFECTIVO, "3000")]), 201)

    estado = cliente.get("/api/ventas/1/devoluciones").get_json()
    assert [(l["devuelta"], l["remanente"]) for l in estado["lineas"]] == [(2, 1), (0, 2)]
    assert [r["importe"] for r in estado["reintegrable"]] == ["1000.00", "2301.00"]
    assert estado["devoluciones"] == [registrada]


def test_reinicio_conserva_devoluciones_y_continua_la_numeracion(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/devoluciones", devolucion((1, 1, True), (2, 1, False), reintegros=[(EFECTIVO, "2400.50")]), 201)
    consultas = ["/api/devoluciones", "/api/ventas/1/devoluciones", f"/api/ubicaciones/{L1}/caja",
                 f"/api/ubicaciones/{L1}/saldos", f"/api/ubicaciones/{L1}/movimientos"]
    antes = [cliente.get(consulta).get_json() for consulta in consultas]

    reiniciado = create_app(base_datos=ruta).test_client()

    assert [reiniciado.get(consulta).get_json() for consulta in consultas] == antes
    repetida = post(reiniciado, "/api/devoluciones", devolucion((1, 1, True), reintegros=[(EFECTIVO, "1500")]), 200)
    assert repetida["id"] == 1
    segunda = post(reiniciado, "/api/devoluciones", devolucion((1, 2, True), reintegros=[(DEBITO, "2301"),
                                                                                         (EFECTIVO, "699")],
                                                               clave="dev-2"), 201)
    assert segunda["numero"] == "DV-00000002"
    excedida = post(reiniciado, "/api/devoluciones", devolucion((2, 2, True), reintegros=[(EFECTIVO, "1801")],
                                                                clave="dev-3"), 409)
    assert "quedan 1 unidades sin devolver" in excedida["error"]["message"]
    final = create_app(base_datos=ruta).test_client()
    assert saldos(final) == {("001", "DISPONIBLE"): 5, ("002", "DISPONIBLE"): 1, ("002", "BLOQUEADO"): 1}
    assert [m["id"] for m in final.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"]] == [1, 2, 3, 4, 5]


def test_clave_repetida_devuelve_la_devolucion_existente_sin_efectos(cliente):
    primera = post(cliente, "/api/devoluciones", devolucion((1, 1, True), reintegros=[(EFECTIVO, "1500")]), 201)

    otra = cliente.post("/api/devoluciones", json=devolucion((2, 2, False), reintegros=[(DEBITO, "1801")]))

    assert otra.status_code == 200 and otra.headers["Location"] == "/api/devoluciones/1"
    assert otra.get_json() == primera
    assert len(cliente.get("/api/devoluciones").get_json()["devoluciones"]) == 1
    assert saldos(cliente) == {("001", "DISPONIBLE"): 3, ("002", "DISPONIBLE"): 1}
    assert len(cliente.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"]) == 3


def test_lo_no_apto_queda_bloqueado_y_lo_apto_vuelve_a_venderse(cliente):
    post(cliente, "/api/devoluciones", devolucion((1, 3, True), (2, 2, False),
                                                  reintegros=[(EFECTIVO, "4000"), (DEBITO, "2301")]), 201)
    venta_fideos = {
        "local_id": L1, "clave_operacion": "venta-2", "lineas": [{"producto_id": 2, "cantidad": 2}],
        "cobros": [{"medio_pago_id": CREDITO, "importe": "1801"}],
    }

    bloqueado = post(cliente, "/api/ventas", venta_fideos, 409)
    revendida = post(cliente, "/api/ventas", {
        **venta_fideos, "clave_operacion": "venta-3", "lineas": [{"producto_id": 1, "cantidad": 5}],
        "cobros": [{"medio_pago_id": CREDITO, "importe": "7500"}],
    }, 201)

    assert "se necesitan 2 unidades en condición DISPONIBLE y hay 1" in bloqueado["error"]["message"]
    assert revendida["total"] == "7500.00"
    assert saldos(cliente) == {("002", "DISPONIBLE"): 1, ("002", "BLOQUEADO"): 2}


@pytest.mark.parametrize("cuerpo,campos", [
    ({"venta_id": 1, "motivo": "x", "lineas": [], "reintegros": []}, {"clave_operacion"}),
    ({**devolucion((1, 1, True), reintegros=[(1, "1500")]), "fecha": "hoy"}, {"fecha"}),
    ({**devolucion((1, 1, True), reintegros=[(1, "1500")]), "motivo": 7}, {"motivo"}),
    ({**devolucion((1, 1, True), reintegros=[(1, "1500")]), "lineas": {"linea": 1}}, {"lineas"}),
    (devolucion((1, 1, "si"), reintegros=[(1, "1500")]), {"lineas.1.apto"}),
    (devolucion((1, 1, 1), reintegros=[(1, "1500")]), {"lineas.1.apto"}),
    (devolucion(("1", 1, True), reintegros=[(1, "1500")]), {"lineas.1.linea"}),
    (devolucion((1, 2**53, True), reintegros=[(1, "1500")]), {"lineas.1.cantidad"}),
    ({**devolucion((1, 1, True), reintegros=[]), "reintegros": [7]}, {"reintegros.1"}),
    (devolucion((1, 1, True), reintegros=[(1, 1500)]), {"reintegros.1.importe"}),
    ({**devolucion((1, 1, True), reintegros=[]), "reintegros": [{"medio_pago_id": 1}]}, {"reintegros.1.importe"}),
])
def test_formato_invalido_devuelve_400_con_campos(cliente, cuerpo, campos):
    respuesta = post(cliente, "/api/devoluciones", cuerpo, 400)

    assert set(respuesta["error"]["fields"]) == campos
    sin_devoluciones(cliente)


def test_referencias_inexistentes_devuelven_404_con_el_campo(cliente):
    casos = [
        (devolucion((1, 1, True), reintegros=[(1, "1500")], venta_id=9), {"venta_id"}),
        (devolucion((1, 1, True), (3, 1, True), reintegros=[(1, "1500")]), {"lineas.2.linea"}),
        (devolucion((0, 1, True), reintegros=[(1, "1500")]), {"lineas.1.linea"}),
        (devolucion((1, 1, True), reintegros=[(1, "1000"), (9, "500")]), {"reintegros.2.medio_pago_id"}),
    ]
    for cuerpo, campos in casos:
        assert set(post(cliente, "/api/devoluciones", cuerpo, 404)["error"]["fields"]) == campos
    sin_devoluciones(cliente)


@pytest.mark.parametrize("cuerpo,estado,mensaje", [
    (devolucion((1, 1, True), reintegros=[(1, "1000")]), 400,
     "Los reintegros suman 1000.00 y el total a reintegrar es 1500.00."),
    (devolucion((1, 1, True), reintegros=[(1, "1000"), (1, "500")]), 400, "Reintegro 2: un medio de pago no puede"),
    (devolucion((1, 1, True), reintegros=[(CREDITO, "1500")]), 400, "la venta no se cobró con Crédito"),
    (devolucion((1, 1, True), reintegros=[(1, "1500.001")]), 400, "Reintegro 1:"),
    (devolucion((1, 4, True), reintegros=[(1, "6000")]), 400, "Se vendieron 3 unidades y se intenta devolver 4"),
    (devolucion((1, 0, True), reintegros=[(1, "1500")]), 400, "Línea 1: La cantidad debe ser positiva"),
    (devolucion((1, 1, True), (1, 1, True), reintegros=[(1, "3000")]), 400, "Línea 2: una línea vendida"),
    (devolucion(reintegros=[(1, "1500")]), 400, "al menos una línea"),
    (devolucion((1, 1, True), reintegros=[]), 400, "al menos un reintegro"),
    (devolucion((1, 1, True), reintegros=[(1, "1500")], motivo="  "), 400, "motivo"),
    (devolucion((1, 1, True), reintegros=[(1, "1500")], motivo="x" * 201), 400, "200 caracteres"),
    (devolucion((1, 1, True), reintegros=[(1, "1500")], clave="x" * 65), 400, "64 caracteres"),
    (devolucion((1, 2, True), reintegros=[(DEBITO, "3000")]), 409, "con Débito quedan 2301.00 por reintegrar"),
])
def test_reglas_del_dominio_se_informan_sin_efectos(cliente, cuerpo, estado, mensaje):
    respuesta = post(cliente, "/api/devoluciones", cuerpo, estado)

    assert mensaje in respuesta["error"]["message"]
    sin_devoluciones(cliente)


def test_local_inactivo_devuelve_409_y_producto_inactivo_se_devuelve(cliente):
    cliente.patch("/api/productos/1/estado", json={"activo": False})
    post(cliente, "/api/devoluciones", devolucion((1, 1, False), reintegros=[(EFECTIVO, "1500")], clave="a"), 201)
    cliente.patch(f"/api/ubicaciones/{L1}/estado", json={"activo": False})

    respuesta = post(cliente, "/api/devoluciones", devolucion((2, 1, True), reintegros=[(DEBITO, "900.50")],
                                                              clave="b"), 409)

    assert "local está inactivo" in respuesta["error"]["message"]
    assert len(cliente.get("/api/devoluciones").get_json()["devoluciones"]) == 1


@pytest.mark.parametrize("ruta", ["/api/devoluciones/9", "/api/ventas/9/devoluciones"])
def test_consultas_inexistentes_devuelven_404_json(cliente, ruta):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 404 and respuesta.get_json()["error"]["code"] == 404


def test_fallo_al_guardar_no_deja_devolucion_stock_ni_caja(tmp_path, monkeypatch):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    guardar_real = backend.api_devoluciones.guardar_devolucion

    def fallar(conexion, devolucion_registrada, movimientos, movimientos_caja):
        guardar_real(conexion, devolucion_registrada, movimientos, movimientos_caja[:1])
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(backend.api_devoluciones, "guardar_devolucion", fallar)
    cuerpo = devolucion((1, 1, True), (2, 1, False), reintegros=[(EFECTIVO, "2000"), (DEBITO, "400.50")])
    assert post(cliente, "/api/devoluciones", cuerpo, 500)["error"]["code"] == 500
    monkeypatch.setattr(backend.api_devoluciones, "guardar_devolucion", guardar_real)

    sin_devoluciones(cliente)
    sin_devoluciones(create_app(base_datos=ruta).test_client())
    reintento = post(cliente, "/api/devoluciones", cuerpo, 201)
    assert reintento["id"] == 1 and saldos(cliente)[("002", "BLOQUEADO")] == 1


def test_devoluciones_concurrentes_no_superan_lo_vendido_ni_duplican_claves():
    app = create_app()
    preparar(app.test_client())

    def devolver(numero):
        return app.test_client().post("/api/devoluciones", json=devolucion(
            (1, 1, True), reintegros=[(EFECTIVO, "1500")], clave=f"dev-{numero}",
        ))

    def repetir(_):
        return app.test_client().post("/api/devoluciones", json=devolucion(
            (2, 1, False), reintegros=[(DEBITO, "900.50")], clave="misma",
        ))

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        distintas = sorted(respuesta.status_code for respuesta in ejecutor.map(devolver, range(6)))
        repetidas = sorted(respuesta.status_code for respuesta in ejecutor.map(repetir, range(4)))

    # El efectivo cobrado (4000) alcanza para dos reintegros de 1500; la tercera unidad no tiene medio.
    assert distintas == [201] * 2 + [409] * 4
    assert repetidas == [200, 200, 200, 201]
    cliente = app.test_client()
    assert saldos(cliente) == {("001", "DISPONIBLE"): 4, ("002", "DISPONIBLE"): 1, ("002", "BLOQUEADO"): 1}
    estado = cliente.get("/api/ventas/1/devoluciones").get_json()
    assert [l["devuelta"] for l in estado["lineas"]] == [2, 1]
    assert [r["importe"] for r in estado["reintegrable"]] == ["1000.00", "1400.50"]


def _base_con_devolucion(tmp_path):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/devoluciones", devolucion((1, 1, True), reintegros=[(EFECTIVO, "1500")]), 201)
    return BaseDatos(ruta)


MOVIMIENTO_DEVOLUCION = (
    "INSERT INTO movimientos_stock (instante, ubicacion_id, producto_id, cantidad, condicion_origen,"
    " condicion_destino, causa, devolucion_id, devolucion_linea) VALUES ('x', 2, 1, 1, {}, {}, 'DEVOLUCION', {}, {})"
)
EGRESO = (
    "INSERT INTO movimientos_caja (id, instante, local_id, medio_pago_id, tipo, importe_centavos, cobro_venta_id,"
    " cobro_numero, reintegro_devolucion_id, reintegro_numero) VALUES (9, 'x', 2, 1, {}, 100, {}, {}, {}, {})"
)


@pytest.mark.parametrize("sentencia", [
    "INSERT INTO devoluciones VALUES (2, 1, 'x', 'Falla', 'dev-1')",
    "INSERT INTO devoluciones VALUES (2, 1, 'x', '', 'otra')",
    "INSERT INTO devoluciones VALUES (2, 1, 'x', 'Falla', '')",
    "INSERT INTO devoluciones VALUES (2, 9, 'x', 'Falla', 'otra')",
    "INSERT INTO detalles_devolucion VALUES (1, 2, 1, 2, 0, 1)",
    "INSERT INTO detalles_devolucion VALUES (1, 2, 1, 2, 1, 2)",
    "INSERT INTO detalles_devolucion VALUES (1, 2, 1, 9, 1, 1)",
    "INSERT INTO detalles_devolucion VALUES (1, 2, 1, 1, 1, 1)",
    # Lo devuelto acumulado no supera lo vendido (3 arroces, ya se devolvió 1).
    "INSERT INTO devoluciones VALUES (2, 1, 'x', 'Falla', 'otra');"
    " INSERT INTO detalles_devolucion VALUES (2, 1, 1, 1, 3, 1)",
    # La línea devuelta debe ser de la venta de la devolución.
    "INSERT INTO ventas VALUES (2, 2, 'x', 'venta-2'); INSERT INTO detalles_venta VALUES (2, 1, 1, 1, 100, NULL);"
    " INSERT INTO detalles_devolucion VALUES (1, 2, 2, 1, 1, 1)",
    "INSERT INTO reintegros VALUES (1, 2, 1, 100)",
    "INSERT INTO reintegros VALUES (1, 2, 2, 0)",
    "INSERT INTO reintegros VALUES (1, 2, 9, 100)",
    # Movimientos de stock: sin línea, repetido o en una condición que no corresponde a la aptitud.
    MOVIMIENTO_DEVOLUCION.format("NULL", "'DISPONIBLE'", "NULL", "NULL"),
    MOVIMIENTO_DEVOLUCION.format("NULL", "'DISPONIBLE'", 1, 1),
    "INSERT INTO devoluciones VALUES (2, 1, 'x', 'Falla', 'otra');"
    " INSERT INTO detalles_devolucion VALUES (2, 1, 1, 1, 1, 0);"
    + MOVIMIENTO_DEVOLUCION.format("NULL", "'DISPONIBLE'", 2, 1),
    "INSERT INTO devoluciones VALUES (2, 1, 'x', 'Falla', 'otra');"
    " INSERT INTO detalles_devolucion VALUES (2, 1, 1, 1, 1, 1);"
    + MOVIMIENTO_DEVOLUCION.format("'BLOQUEADO'", "'DISPONIBLE'", 2, 1),
    # Movimientos de caja: un egreso sin reintegro o repetido, un ingreso con reintegro.
    EGRESO.format("'EGRESO'", "NULL", "NULL", "NULL", "NULL"),
    EGRESO.format("'EGRESO'", "NULL", "NULL", 1, 1),
    EGRESO.format("'EGRESO'", "NULL", "NULL", 1, 5),
    EGRESO.format("'INGRESO'", 1, 1, 1, 1),
    "UPDATE movimientos_caja SET reintegro_numero = 2 WHERE id = 3",
])
def test_esquema_protege_devoluciones_reintegros_y_movimientos(tmp_path, sentencia):
    base_datos = _base_con_devolucion(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        base_datos.ejecutar_transaccion(lambda conexion: conexion.executescript(sentencia))


def test_base_de_f04_recibe_columnas_de_devolucion_y_trigger_actualizado(tmp_path):
    ruta = tmp_path / "f04.db"
    conexion = sqlite3.connect(ruta)
    # Tablas y trigger tal como los dejaba F-04: sin columnas de devolución ni reintegro.
    conexion.executescript("""
        CREATE TABLE movimientos_stock (
            id INTEGER PRIMARY KEY, instante TEXT NOT NULL, ubicacion_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL, cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            condicion_origen TEXT, condicion_destino TEXT, causa TEXT NOT NULL,
            compra_id INTEGER, compra_linea INTEGER, bulto_id INTEGER, venta_id INTEGER, venta_linea INTEGER
        );
        CREATE TRIGGER movimientos_logisticos_con_bulto BEFORE INSERT ON movimientos_stock
        WHEN NEW.causa NOT IN ('COMPRA', 'VENTA') AND NEW.bulto_id IS NULL
        BEGIN
            SELECT RAISE(ABORT, 'Un movimiento logístico debe referenciar su bulto.');
        END;
        CREATE TABLE movimientos_caja (
            id INTEGER PRIMARY KEY, instante TEXT NOT NULL, local_id INTEGER NOT NULL,
            medio_pago_id INTEGER NOT NULL, tipo TEXT NOT NULL CHECK (tipo IN ('INGRESO', 'EGRESO')),
            importe_centavos INTEGER NOT NULL CHECK (importe_centavos > 0),
            cobro_venta_id INTEGER, cobro_numero INTEGER,
            CHECK ((tipo = 'INGRESO') = (cobro_venta_id IS NOT NULL AND cobro_numero IS NOT NULL))
        );
    """)
    conexion.close()

    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente)
    post(cliente, "/api/devoluciones", devolucion((2, 1, False), reintegros=[(DEBITO, "900.50")]), 201)

    reiniciado = create_app(base_datos=ruta).test_client()
    assert saldos(reiniciado)[("002", "BLOQUEADO")] == 1
    assert reiniciado.get(f"/api/ubicaciones/{L1}/caja").get_json()["movimientos"][-1]["reintegro"] == 1
