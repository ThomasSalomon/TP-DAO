"""Contratos HTTP de los reportes R-01 a R-04 (F-06.2): parámetros, JSON, importes negativos y sólo lectura."""

from datetime import datetime

import pytest

import backend.api_compras
import backend.api_devoluciones
import backend.api_logistica
import backend.api_ventas
from backend import create_app
from backend.dominio import ZONA_ARGENTINA

CD, L1, L2 = 1, 2, 3
EFECTIVO, DEBITO = 1, 2
ARROZ = {"id": 1, "codigo": "001", "nombre": "Arroz", "activo": True}
FIDEOS = {"id": 2, "codigo": "002", "nombre": "Fideos", "activo": True}
ALMACEN = {"id": 1, "codigo": "ALM", "nombre": "Almacén", "activo": True}
LOCAL_L1 = {"id": L1, "codigo": "L1", "nombre": "Centro", "tipo": "LOCAL", "activo": True}
LOCAL_L2 = {"id": L2, "codigo": "L2", "nombre": "Norte", "tipo": "LOCAL", "activo": True}
CENTRAL = {"id": CD, "codigo": "CD", "nombre": "Central", "tipo": "CD", "activo": True}
OCTUBRE = "desde=2026-10-01&hasta=2026-11-01"
NOVIEMBRE = "desde=2026-11-01&hasta=2026-12-01"


def instante(mes, dia, hora=9):
    return datetime(2026, mes, dia, hora, tzinfo=ZONA_ARGENTINA)


class Reloj:
    """Instante que devuelve ahora() en los adaptadores; cada paso del escenario lo fija."""

    momento = instante(10, 1)


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    reloj = Reloj()
    for modulo in (backend.api_compras, backend.api_logistica, backend.api_ventas, backend.api_devoluciones):
        monkeypatch.setattr(modulo, "ahora", lambda: reloj.momento)
    return reloj


def post(cliente, ruta, cuerpo=None, estado=200):
    respuesta = cliente.post(ruta, json={} if cuerpo is None else cuerpo)
    assert respuesta.status_code == estado, respuesta.get_json()
    return respuesta.get_json()


def get(cliente, ruta, estado=200):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == estado, respuesta.get_json()
    return respuesta.get_json()


def preparar(cliente, reloj):
    """01/10: compra (arroz a 1000, fideos a 400) y bulto 1 a L1 con 5 arroces y 3 fideos, verificado.

    02/10: bulto 2 a L2 con 2 fideos, rechazado por precinto roto. 05/10: venta en L1 de 3 arroces y 2 fideos
    (6301.00: 4000 en efectivo y 2301 con débito). 02/11: devolución de 1 arroz apto, 1500 en efectivo.
    Mínimos de L1: arroz 2 y fideos 2.
    """
    reloj.momento = instante(10, 1)
    post(cliente, "/api/categorias", {"codigo": "ALM", "nombre": "Almacén"}, 201)
    post(cliente, "/api/categorias", {"codigo": "LIM", "nombre": "Limpieza"}, 201)
    post(cliente, "/api/productos", {"codigo": "001", "nombre": "Arroz", "categoria_id": 1, "precio": "1500"}, 201)
    post(cliente, "/api/productos", {"codigo": "002", "nombre": "Fideos", "categoria_id": 1, "precio": "900.50"}, 201)
    post(cliente, "/api/proveedores", {"codigo": "PRV", "nombre": "Molinos"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "CD", "nombre": "Central", "tipo": "CD"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"}, 201)
    for producto in (1, 2):
        respuesta = cliente.put(f"/api/ubicaciones/{L1}/minimos/{producto}", json={"minimo": 2})
        assert respuesta.status_code == 200, respuesta.get_json()
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

    reloj.momento = instante(10, 2)
    post(cliente, "/api/necesidades", {"local_id": L2, "producto_id": 2, "cantidad": 2}, 201)
    post(cliente, "/api/ordenes", {"local_id": L2, "necesidad_ids": [3]}, 201)
    post(cliente, "/api/ordenes/2/bultos", {"lineas": [{"producto_id": 2, "cantidad": 2}]}, 201)
    post(cliente, "/api/bultos/2/precintar", {"precinto": "S-2"})
    post(cliente, "/api/bultos/2/despachar")
    post(cliente, "/api/bultos/2/recibir", {"local_id": L2, "precinto_leido": "S-2", "precinto_intacto": False})

    reloj.momento = instante(10, 5, 10)
    post(cliente, "/api/ventas", {
        "local_id": L1, "clave_operacion": "venta-1",
        "lineas": [{"producto_id": 1, "cantidad": 3}, {"producto_id": 2, "cantidad": 2}],
        "cobros": [{"medio_pago_id": EFECTIVO, "importe": "4000"}, {"medio_pago_id": DEBITO, "importe": "2301"}],
    }, 201)

    reloj.momento = instante(11, 2, 10)
    post(cliente, "/api/devoluciones", {
        "venta_id": 1, "clave_operacion": "dev-1", "motivo": "Cambio de opinión",
        "lineas": [{"linea": 1, "cantidad": 1, "apto": True}],
        "reintegros": [{"medio_pago_id": EFECTIVO, "importe": "1500"}],
    }, 201)


@pytest.fixture
def cliente(reloj):
    cliente = create_app().test_client()
    preparar(cliente, reloj)
    return cliente


def saldos(*cantidades):
    """Saldos en el orden de las condiciones del modelo."""
    condiciones = ("DISPONIBLE", "RESERVADO", "EN_TRANSITO", "PENDIENTE", "RECHAZADO", "BLOQUEADO")
    return dict(zip(condiciones, cantidades, strict=True))


# R-01.

def test_r01_por_medio_de_pago(cliente):
    assert get(cliente, f"/api/reportes/ventas?{OCTUBRE}&agrupacion=medio") == {
        "periodo": {"desde": "2026-10-01", "hasta": "2026-11-01"},
        "local": None,
        "agrupacion": "medio",
        "ventas": {"cantidad": 1, "importe": "6301.00"},
        "devoluciones": {"cantidad": 0, "importe": "0.00"},
        "venta_neta": "6301.00",
        "grupos": [
            {"etiqueta": "Efectivo", "cobros": "4000.00", "reintegros": "0.00", "ingreso_neto": "4000.00"},
            {"etiqueta": "Débito", "cobros": "2301.00", "reintegros": "0.00", "ingreso_neto": "2301.00"},
        ],
        "cobros": "6301.00",
        "reintegros": "0.00",
        "ingreso_neto": "6301.00",
        "moneda": "ARS",
    }


def test_r01_devolucion_en_otro_periodo_da_importes_negativos(cliente):
    datos = get(cliente, f"/api/reportes/ventas?{NOVIEMBRE}&agrupacion=local&local_id={L1}")

    assert datos["local"] == LOCAL_L1
    assert (datos["ventas"], datos["devoluciones"]) == (
        {"cantidad": 0, "importe": "0.00"}, {"cantidad": 1, "importe": "1500.00"},
    )
    assert datos["venta_neta"] == datos["ingreso_neto"] == "-1500.00"
    assert datos["grupos"] == [
        {"etiqueta": "L1 — Centro", "cobros": "0.00", "reintegros": "1500.00", "ingreso_neto": "-1500.00"},
    ]


def test_r01_agrupa_por_dia_por_defecto(cliente):
    datos = get(cliente, "/api/reportes/ventas?desde=2026-10-01&hasta=2026-12-01")

    assert datos["agrupacion"] == "dia"
    assert [(grupo["etiqueta"], grupo["ingreso_neto"]) for grupo in datos["grupos"]] == [
        ("05/10/2026", "6301.00"), ("02/11/2026", "-1500.00"),
    ]
    assert datos["venta_neta"] == datos["ingreso_neto"] == "4801.00"
    assert get(cliente, "/api/reportes/agrupaciones") == {"agrupaciones": ["dia", "local", "medio"]}


def test_r01_periodo_sin_operaciones(cliente):
    datos = get(cliente, "/api/reportes/ventas?desde=2026-09-01&hasta=2026-10-01&agrupacion=medio")

    assert datos["grupos"] == [] and datos["ventas"] == {"cantidad": 0, "importe": "0.00"}
    assert datos["venta_neta"] == datos["ingreso_neto"] == "0.00"


# R-02.

def test_r02_ranking_y_margen_estimado(cliente):
    assert get(cliente, f"/api/reportes/productos?{OCTUBRE}&local_id={L1}") == {
        "periodo": {"desde": "2026-10-01", "hasta": "2026-11-01"},
        "local": LOCAL_L1,
        "productos": [
            {"posicion": 1, "producto": ARROZ, "unidades_vendidas": 3, "unidades_devueltas": 0, "unidades_netas": 3,
             "importe_neto": "4500.00", "costo_neto": "3000.00", "margen": "1500.00"},
            {"posicion": 2, "producto": FIDEOS, "unidades_vendidas": 2, "unidades_devueltas": 0, "unidades_netas": 2,
             "importe_neto": "1801.00", "costo_neto": "800.00", "margen": "1001.00"},
        ],
        "unidades_netas": 5,
        "importe_neto": "6301.00",
        "margen": "2501.00",
        "productos_sin_costo": [],
        "moneda": "ARS",
    }


def test_r02_devolucion_revierte_importe_y_costo_en_su_periodo(cliente):
    datos = get(cliente, f"/api/reportes/productos?{NOVIEMBRE}")

    assert datos["productos"] == [
        {"posicion": 1, "producto": ARROZ, "unidades_vendidas": 0, "unidades_devueltas": 1, "unidades_netas": -1,
         "importe_neto": "-1500.00", "costo_neto": "-1000.00", "margen": "-500.00"},
    ]
    assert (datos["importe_neto"], datos["margen"]) == ("-1500.00", "-500.00")


def test_r02_concilia_con_la_venta_neta_de_r01(cliente):
    for periodo in (OCTUBRE, NOVIEMBRE, "desde=2026-10-01&hasta=2026-12-01"):
        ventas = get(cliente, f"/api/reportes/ventas?{periodo}")
        productos = get(cliente, f"/api/reportes/productos?{periodo}")
        assert productos["importe_neto"] == ventas["venta_neta"]


# R-03.

def test_r03_existencias_y_minimos_del_local(cliente):
    assert get(cliente, f"/api/reportes/existencias?ubicacion_id={L1}") == {
        "ubicacion": LOCAL_L1,
        "categoria": None,
        "solo_en_minimo": False,
        "productos": [
            {"producto": ARROZ, "categoria": ALMACEN, "saldos": saldos(3, 0, 0, 0, 0, 0), "minimo": 2, "deficit": 0,
             "en_minimo": False},
            {"producto": FIDEOS, "categoria": ALMACEN, "saldos": saldos(1, 0, 0, 0, 0, 0), "minimo": 2, "deficit": 1,
             "en_minimo": True},
        ],
        "totales": saldos(4, 0, 0, 0, 0, 0),
        "productos_en_minimo": 1,
        "deficit_total": 1,
    }


def test_r03_filtros_y_otras_ubicaciones(cliente):
    en_minimo = get(cliente, f"/api/reportes/existencias?ubicacion_id={L1}&solo_en_minimo=true")
    limpieza = get(cliente, f"/api/reportes/existencias?ubicacion_id={L1}&categoria_id=2")
    rechazado = get(cliente, f"/api/reportes/existencias?ubicacion_id={L2}")
    centro = get(cliente, f"/api/reportes/existencias?ubicacion_id={CD}")

    assert [fila["producto"] for fila in en_minimo["productos"]] == [FIDEOS] and en_minimo["solo_en_minimo"]
    assert limpieza["productos"] == [] and limpieza["categoria"]["codigo"] == "LIM"
    assert [(fila["producto"], fila["saldos"], fila["minimo"]) for fila in rechazado["productos"]] == [
        (FIDEOS, saldos(0, 0, 0, 0, 2, 0), None),
    ]
    assert centro["ubicacion"] == CENTRAL
    assert [(fila["producto"], fila["saldos"]["DISPONIBLE"], fila["deficit"]) for fila in centro["productos"]] == [
        (ARROZ, 15, None), (FIDEOS, 5, None),
    ]


# R-04.

def test_r04_rechazos_por_bulto_y_por_local(cliente):
    assert get(cliente, f"/api/reportes/rechazos?{OCTUBRE}") == {
        "periodo": {"desde": "2026-10-01", "hasta": "2026-11-01"},
        "local": None,
        "producto": None,
        "rechazos": [{
            "bulto_id": 2, "bulto_codigo": "B-000002", "remito": "R-000002", "destino": LOCAL_L2,
            "instante": "2026-10-02T09:00:00-03:00", "motivo": "Precinto roto.",
            "lineas": [{"producto": FIDEOS, "cantidad": 2, "costo_referencia": "400.00"}],
            "unidades": 2, "valor_bloqueado": "800.00",
        }],
        "locales": [
            {"destino": LOCAL_L1, "bultos_recibidos": 1, "bultos_rechazados": 0, "unidades": 0,
             "valor_bloqueado": "0.00"},
            {"destino": LOCAL_L2, "bultos_recibidos": 1, "bultos_rechazados": 1, "unidades": 2,
             "valor_bloqueado": "800.00"},
        ],
        "bultos_recibidos": 2,
        "bultos_rechazados": 1,
        "unidades": 2,
        "valor_bloqueado": "800.00",
        "moneda": "ARS",
    }


def test_r04_filtros_de_local_y_producto(cliente):
    local = get(cliente, f"/api/reportes/rechazos?{OCTUBRE}&local_id={L1}")
    producto = get(cliente, f"/api/reportes/rechazos?{OCTUBRE}&producto_id=1")

    assert local["local"] == LOCAL_L1 and local["rechazos"] == [] and local["valor_bloqueado"] == "0.00"
    assert [item["destino"] for item in local["locales"]] == [LOCAL_L1]
    assert producto["producto"] == ARROZ and producto["rechazos"] == []
    assert [(item["destino"]["codigo"], item["bultos_recibidos"]) for item in producto["locales"]] == [("L1", 1)]


# Parámetros.

@pytest.mark.parametrize("ruta, campo, estado", [
    ("/api/reportes/ventas?hasta=2026-11-01", "desde", 400),
    ("/api/reportes/ventas?desde=2026-10-1&hasta=2026-11-01", "desde", 400),
    ("/api/reportes/ventas?desde=2026-02-30&hasta=2026-11-01", "desde", 400),
    ("/api/reportes/ventas?desde=２０２６-10-01&hasta=2026-11-01", "desde", 400),
    ("/api/reportes/ventas?desde=2026-11-01&hasta=2026-10-01", "hasta", 400),
    ("/api/reportes/ventas?desde=2026-10-01&hasta=2026-10-01", "hasta", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&agrupacion=semana", "agrupacion", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&local_id={CD}", "local_id", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&local_id=99", "local_id", 404),
    (f"/api/reportes/ventas?{OCTUBRE}&local_id=abc", "local_id", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&local_id=0", "local_id", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&local_id=2&local_id=3", "local_id", 400),
    (f"/api/reportes/ventas?{OCTUBRE}&orden=desc", "orden", 400),
    (f"/api/reportes/productos?{OCTUBRE}&local_id={CD}", "local_id", 400),
    ("/api/reportes/productos?desde=2026-10-01", "hasta", 400),
    ("/api/reportes/existencias", "ubicacion_id", 400),
    ("/api/reportes/existencias?ubicacion_id=99", "ubicacion_id", 404),
    (f"/api/reportes/existencias?ubicacion_id={L1}&categoria_id=99", "categoria_id", 404),
    (f"/api/reportes/existencias?ubicacion_id={L1}&solo_en_minimo=si", "solo_en_minimo", 400),
    (f"/api/reportes/existencias?ubicacion_id={L1}&desde=2026-10-01", "desde", 400),
    (f"/api/reportes/rechazos?{OCTUBRE}&producto_id=99", "producto_id", 404),
    (f"/api/reportes/rechazos?{OCTUBRE}&local_id={CD}", "local_id", 400),
])
def test_parametros_invalidos_informan_el_campo(cliente, ruta, campo, estado):
    error = get(cliente, ruta, estado)["error"]

    assert error["code"] == estado and list(error["fields"]) == [campo]


def test_los_reportes_sólo_admiten_consultas(cliente):
    respuesta = cliente.post(f"/api/reportes/ventas?{OCTUBRE}", json={})

    assert respuesta.status_code == 405 and respuesta.get_json()["error"]["code"] == 405


def test_los_reportes_no_modifican_operaciones(cliente):
    consultas = ["/api/ventas", "/api/devoluciones", "/api/bultos", "/api/remitos"] + [
        f"/api/ubicaciones/{ubicacion}/{recurso}" for ubicacion in (CD, L1, L2) for recurso in ("saldos", "movimientos")
    ] + [f"/api/ubicaciones/{L1}/caja"]
    antes = [get(cliente, consulta) for consulta in consultas]
    for reporte in (f"ventas?{OCTUBRE}&agrupacion=medio", f"productos?{OCTUBRE}", f"rechazos?{OCTUBRE}",
                    f"existencias?ubicacion_id={L1}"):
        get(cliente, f"/api/reportes/{reporte}")

    assert [get(cliente, consulta) for consulta in consultas] == antes


def test_reinicio_reproduce_los_mismos_reportes(tmp_path, reloj):
    ruta = tmp_path / "tp.db"
    cliente = create_app(base_datos=ruta).test_client()
    preparar(cliente, reloj)
    reportes = [f"/api/reportes/ventas?{OCTUBRE}&agrupacion=medio", f"/api/reportes/productos?{NOVIEMBRE}",
                f"/api/reportes/existencias?ubicacion_id={L1}", f"/api/reportes/rechazos?{OCTUBRE}"]
    antes = [get(cliente, reporte) for reporte in reportes]

    reiniciado = create_app(base_datos=ruta).test_client()

    assert [get(reiniciado, reporte) for reporte in reportes] == antes
