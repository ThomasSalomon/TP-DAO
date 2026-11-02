"""Escenarios integrales de aceptación (F-07.1): circuito completo por HTTP con el dataset de control J.3.

Cada escenario usa una base temporal propia y recorre la API como lo hace la pantalla: maestros, compra al CD,
reposición, bultos con doble verificación, ventas, devoluciones y reportes. El reinicio se simula creando otra
aplicación sobre la misma base.
"""

import sqlite3
from datetime import datetime

import pytest

import backend.api_compras
import backend.api_devoluciones
import backend.api_logistica
import backend.api_ventas
from backend import create_app
from backend.dominio import ZONA_ARGENTINA

CD, A, B = 1, 2, 3
P = 1
EFECTIVO, CREDITO, TRANSFERENCIA = 1, 3, 4
OCTUBRE = "desde=2026-10-01&hasta=2026-11-01"


def instante(dia, hora=9):
    return datetime(2026, 10, dia, hora, tzinfo=ZONA_ARGENTINA)


class Reloj:
    """Instante que devuelve ahora() en los adaptadores; cada paso del escenario lo fija."""

    momento = instante(1)


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


def put(cliente, ruta, cuerpo):
    respuesta = cliente.put(ruta, json=cuerpo)
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()


# Pasos del circuito.

def maestros(cliente):
    """Producto P a 100, CD, local A con mínimo 2 y local B con mínimo 3."""
    post(cliente, "/api/categorias", {"codigo": "ALM", "nombre": "Almacén"}, 201)
    post(cliente, "/api/productos", {"codigo": "P", "nombre": "Producto P", "categoria_id": 1, "precio": "100"}, 201)
    post(cliente, "/api/proveedores", {"codigo": "PRV", "nombre": "Proveedor"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "CD", "nombre": "Central", "tipo": "CD"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "A", "nombre": "Local A", "tipo": "LOCAL"}, 201)
    post(cliente, "/api/ubicaciones", {"codigo": "B", "nombre": "Local B", "tipo": "LOCAL"}, 201)
    put(cliente, f"/api/ubicaciones/{A}/minimos/{P}", {"minimo": 2})
    put(cliente, f"/api/ubicaciones/{B}/minimos/{P}", {"minimo": 3})


def comprar(cliente, cantidad):
    return post(cliente, "/api/compras", {"proveedor_id": 1, "lineas": [
        {"producto_id": P, "cantidad": cantidad, "costo_unitario": "60"},
    ]}, 201)


def despachar(cliente, local_id, necesidades, precinto):
    """Necesidades del local, consolidadas en una orden, y su bulto precintado y despachado."""
    ids = [
        post(cliente, "/api/necesidades", {"local_id": local_id, "producto_id": P, "cantidad": cantidad}, 201)["id"]
        for cantidad in necesidades
    ]
    orden = post(cliente, "/api/ordenes", {"local_id": local_id, "necesidad_ids": ids}, 201)
    bulto = post(cliente, f"/api/ordenes/{orden['id']}/bultos", {"lineas": [
        {"producto_id": P, "cantidad": sum(necesidades)},
    ]}, 201)
    post(cliente, f"/api/bultos/{bulto['id']}/precintar", {"precinto": precinto})
    post(cliente, f"/api/bultos/{bulto['id']}/despachar")
    return bulto["id"]


def recibir(cliente, bulto_id, local_id, precinto, intacto=True):
    return post(cliente, f"/api/bultos/{bulto_id}/recibir", {
        "local_id": local_id, "precinto_leido": precinto, "precinto_intacto": intacto,
    })


def verificar(cliente, bulto_id):
    """Doble verificación: el bulto y su remito."""
    post(cliente, f"/api/bultos/{bulto_id}/verificar")
    remito = get(cliente, f"/api/bultos/{bulto_id}")["remito"]
    return post(cliente, f"/api/remitos/{remito['id']}/verificar")


def vender(cliente, local_id, cantidad, cobros, clave, estado=201):
    return post(cliente, "/api/ventas", {
        "local_id": local_id, "clave_operacion": clave,
        "lineas": [{"producto_id": P, "cantidad": cantidad}],
        "cobros": [{"medio_pago_id": medio, "importe": importe} for medio, importe in cobros],
    }, estado)


def devolver(cliente, venta_id, clave, estado=201):
    """Devolución de 1 unidad apta de la línea 1, reintegrada en efectivo."""
    return post(cliente, "/api/devoluciones", {
        "venta_id": venta_id, "clave_operacion": clave, "motivo": "Cambio",
        "lineas": [{"linea": 1, "cantidad": 1, "apto": True}],
        "reintegros": [{"medio_pago_id": EFECTIVO, "importe": "100"}],
    }, estado)


def cargar_dataset(cliente, reloj):
    """Dataset J.3 de `docs/PLANIFICACION_TP_POO.md`, en pesos y dentro de octubre.

    01/10: compra de 14 unidades de P a 60. 02/10: A pide 2 y 1 (una orden consolidada) y B pide 7; los dos bultos
    llegan intactos con doble verificación. 03/10: un bulto de 4 unidades llega a A con el precinto roto.
    05/10: A vende 3 a 100 (200 en efectivo y 100 con crédito); P pasa a 90 y B vende 2 (180 por transferencia).
    06/10: A devuelve 1 unidad apta con reintegro de 100 en efectivo.
    """
    reloj.momento = instante(1)
    maestros(cliente)
    comprar(cliente, 14)

    reloj.momento = instante(2)
    for local_id, necesidades, precinto in ((A, (2, 1), "S-A1"), (B, (7,), "S-B1")):
        bulto = despachar(cliente, local_id, necesidades, precinto)
        recibir(cliente, bulto, local_id, precinto)
        verificar(cliente, bulto)

    reloj.momento = instante(3)
    bulto = despachar(cliente, A, (4,), "S-A2")
    recibir(cliente, bulto, A, "S-A2", intacto=False)

    reloj.momento = instante(5, 10)
    vender(cliente, A, 3, [(EFECTIVO, "200"), (CREDITO, "100")], "venta-a")
    put(cliente, f"/api/productos/{P}", {"codigo": "P", "nombre": "Producto P", "categoria_id": 1, "precio": "90"})
    vender(cliente, B, 2, [(TRANSFERENCIA, "180")], "venta-b")

    reloj.momento = instante(6, 10)
    devolver(cliente, 1, "dev-a")


# Consultas.

def saldos(cliente, ubicacion_id):
    """Saldos de P en la ubicación por condición, sin las condiciones vacías."""
    return {
        saldo["condicion"]: saldo["cantidad"]
        for saldo in get(cliente, f"/api/ubicaciones/{ubicacion_id}/saldos")["saldos"] if saldo["cantidad"]
    }


def caja(cliente, local_id):
    """Saldo de caja por medio, sin los medios en cero."""
    return {
        saldo["medio"]["nombre"]: saldo["saldo"]
        for saldo in get(cliente, f"/api/ubicaciones/{local_id}/caja")["saldos"] if saldo["saldo"] != "0.00"
    }


def reportes(cliente):
    return {
        "ventas": get(cliente, f"/api/reportes/ventas?{OCTUBRE}&agrupacion=medio"),
        "productos": get(cliente, f"/api/reportes/productos?{OCTUBRE}"),
        "existencias_a": get(cliente, f"/api/reportes/existencias?ubicacion_id={A}"),
        "existencias_b": get(cliente, f"/api/reportes/existencias?ubicacion_id={B}"),
        "rechazos": get(cliente, f"/api/reportes/rechazos?{OCTUBRE}"),
    }


def estado_completo(cliente):
    """Todo lo que debe coincidir tras un reinicio: documentos, stock, caja, historia de bultos y reportes."""
    return {
        "compras": get(cliente, "/api/compras"),
        "ventas": get(cliente, "/api/ventas"),
        "devoluciones": get(cliente, "/api/devoluciones"),
        "bultos": [get(cliente, f"/api/bultos/{bulto['id']}") for bulto in get(cliente, "/api/bultos")["bultos"]],
        "remitos": get(cliente, "/api/remitos"),
        "saldos": {ubicacion: saldos(cliente, ubicacion) for ubicacion in (CD, A, B)},
        "cajas": {local: get(cliente, f"/api/ubicaciones/{local}/caja") for local in (A, B)},
        "reportes": reportes(cliente),
    }


# Escenario feliz.

@pytest.fixture
def ruta(tmp_path):
    return tmp_path / "tp.db"


@pytest.fixture
def cliente(ruta, reloj):
    cliente = create_app(base_datos=ruta).test_client()
    cargar_dataset(cliente, reloj)
    return cliente


def test_feliz_stock_y_caja_del_dataset(cliente):
    assert saldos(cliente, CD) == {}
    assert saldos(cliente, A) == {"DISPONIBLE": 1, "RECHAZADO": 4}
    assert saldos(cliente, B) == {"DISPONIBLE": 5}
    assert caja(cliente, A) == {"Efectivo": "100.00", "Crédito": "100.00"}
    assert caja(cliente, B) == {"Transferencia": "180.00"}


def test_feliz_orden_consolidada_conserva_las_necesidades(cliente):
    orden = get(cliente, "/api/ordenes/1")

    assert (orden["centro"]["codigo"], orden["destino"]["codigo"]) == ("CD", "A")
    assert [(linea["solicitada"], linea["necesidades"]) for linea in orden["lineas"]] == [(3, [1, 2])]


def test_feliz_comprobantes_con_precio_historico_y_reconsulta_sin_efectos(cliente):
    caja_antes = get(cliente, f"/api/ubicaciones/{A}/caja")
    primero = get(cliente, "/api/ventas/1/comprobante")
    segundo = get(cliente, "/api/ventas/2/comprobante")

    assert [(linea["precio_unitario"], linea["subtotal"]) for linea in primero["lineas"]] == [("100.00", "300.00")]
    assert [(linea["precio_unitario"], linea["subtotal"]) for linea in segundo["lineas"]] == [("90.00", "180.00")]
    assert get(cliente, "/api/ventas/1/comprobante") == primero
    assert get(cliente, f"/api/ubicaciones/{A}/caja") == caja_antes


def test_feliz_reportes_dan_los_resultados_esperados_de_j3(cliente):
    datos = reportes(cliente)
    ventas, productos, rechazos = datos["ventas"], datos["productos"], datos["rechazos"]

    assert (ventas["ventas"]["importe"], ventas["devoluciones"]["importe"], ventas["venta_neta"]) == (
        "480.00", "100.00", "380.00",
    )
    assert (ventas["cobros"], ventas["reintegros"], ventas["ingreso_neto"]) == ("480.00", "100.00", "380.00")
    assert {grupo["etiqueta"]: grupo["ingreso_neto"] for grupo in ventas["grupos"]} == {
        "Efectivo": "100.00", "Crédito": "100.00", "Transferencia": "180.00",
    }
    [fila] = productos["productos"]
    assert (fila["unidades_netas"], fila["importe_neto"], fila["costo_neto"], fila["margen"]) == (
        4, "380.00", "240.00", "140.00",
    )
    assert productos["importe_neto"] == ventas["venta_neta"]
    assert [(f["saldos"]["DISPONIBLE"], f["deficit"], f["en_minimo"]) for f in datos["existencias_a"]["productos"]] == [
        (1, 1, True),
    ]
    assert [(f["saldos"]["DISPONIBLE"], f["deficit"], f["en_minimo"]) for f in datos["existencias_b"]["productos"]] == [
        (5, 0, False),
    ]
    assert (rechazos["bultos_rechazados"], rechazos["unidades"], rechazos["valor_bloqueado"]) == (1, 4, "240.00")


def test_feliz_reinicio_conserva_todo(cliente, ruta):
    antes = estado_completo(cliente)

    assert estado_completo(create_app(base_datos=ruta).test_client()) == antes


def test_feliz_reinicio_continua_numeracion_y_operaciones(cliente, ruta, reloj):
    reiniciado = create_app(base_datos=ruta).test_client()
    reloj.momento = instante(7, 10)

    venta = vender(reiniciado, B, 1, [(TRANSFERENCIA, "90")], "venta-b2")
    assert (venta["id"], venta["comprobante"]) == (3, "CV-00000003")
    assert saldos(reiniciado, B) == {"DISPONIBLE": 4}
    vender(reiniciado, A, 2, [(EFECTIVO, "180")], "venta-a2", 409)
    assert devolver(reiniciado, 1, "dev-a", 200)["id"] == 1  # clave repetida: la misma devolución, sin efectos
    assert saldos(reiniciado, A) == {"DISPONIBLE": 1, "RECHAZADO": 4}


# Escenario de bloqueo.

def test_bloqueo_stock_no_vendible_hasta_la_doble_verificacion(reloj):
    cliente = create_app().test_client()
    maestros(cliente)
    comprar(cliente, 5)
    bulto = despachar(cliente, A, (3,), "S-1")

    def intento(numero):
        respuesta = vender(cliente, A, 1, [(EFECTIVO, "100")], f"intento-{numero}", 409)
        assert "error" in respuesta

    intento(1)
    assert saldos(cliente, A) == {"EN_TRANSITO": 3}
    recibir(cliente, bulto, A, "S-1")
    intento(2)
    post(cliente, f"/api/bultos/{bulto}/verificar")
    intento(3)
    assert saldos(cliente, A) == {"PENDIENTE": 3}
    remito = get(cliente, f"/api/bultos/{bulto}")["remito"]
    post(cliente, f"/api/remitos/{remito['id']}/verificar")

    assert saldos(cliente, A) == {"DISPONIBLE": 3}
    vender(cliente, A, 3, [(EFECTIVO, "300")], "venta")
    vender(cliente, A, 1, [(EFECTIVO, "100")], "sin-stock", 409)
    assert [venta["id"] for venta in get(cliente, "/api/ventas")["ventas"]] == [1]
    assert caja(cliente, A) == {"Efectivo": "300.00"}


# Escenario de rechazo.

def test_rechazo_precinto_roto_no_habilita_venta_ni_caja_y_conserva_historia(reloj):
    cliente = create_app().test_client()
    maestros(cliente)
    comprar(cliente, 4)
    bulto = despachar(cliente, A, (4,), "S-1")
    reloj.momento = instante(3)
    recibir(cliente, bulto, A, "S-1", intacto=False)
    historia = get(cliente, f"/api/bultos/{bulto}")["eventos"]

    assert get(cliente, f"/api/bultos/{bulto}")["estado"] == "RECHAZADO"
    assert [evento["estado_nuevo"] for evento in historia] == [
        "PREPARADO", "PRECINTADO", "EN_TRANSITO", "RECIBIDO", "RECHAZADO",
    ]
    vender(cliente, A, 1, [(EFECTIVO, "100")], "intento", 409)
    post(cliente, f"/api/bultos/{bulto}/verificar", estado=409)
    assert saldos(cliente, A) == {"RECHAZADO": 4}
    assert caja(cliente, A) == {} and get(cliente, "/api/ventas")["ventas"] == []
    assert get(cliente, f"/api/bultos/{bulto}")["eventos"] == historia

    rechazos = get(cliente, f"/api/reportes/rechazos?{OCTUBRE}")
    assert (rechazos["bultos_rechazados"], rechazos["unidades"], rechazos["valor_bloqueado"]) == (1, 4, "240.00")
    ventas = get(cliente, f"/api/reportes/ventas?{OCTUBRE}")
    assert (ventas["ventas"]["cantidad"], ventas["ingreso_neto"]) == (0, "0.00")


# Escenario transaccional.

def fallar_despues_de_guardar_parte(monkeypatch, modulo, nombre, recortar):
    """Reemplaza el guardado por uno que escribe una parte de la operación y luego falla."""
    guardar_real = getattr(modulo, nombre)

    def fallar(conexion, *argumentos):
        guardar_real(conexion, *recortar(argumentos))
        raise sqlite3.OperationalError("disco no disponible")

    monkeypatch.setattr(modulo, nombre, fallar)
    return guardar_real


def test_transaccional_fallos_de_guardado_no_dejan_cambios_parciales(ruta, reloj, monkeypatch):
    cliente = create_app(base_datos=ruta).test_client()
    reloj.momento = instante(1)
    maestros(cliente)

    def sin_ultimo(argumentos):
        *previos, lista = argumentos
        return (*previos, lista[:1])

    # Compra: falla con un solo movimiento guardado.
    real = fallar_despues_de_guardar_parte(monkeypatch, backend.api_compras, "guardar_compra", sin_ultimo)
    post(cliente, "/api/compras", {"proveedor_id": 1, "lineas": [
        {"producto_id": P, "cantidad": 5, "costo_unitario": "60"},
    ]}, 500)
    monkeypatch.setattr(backend.api_compras, "guardar_compra", real)
    for consulta in (cliente, create_app(base_datos=ruta).test_client()):
        assert get(consulta, "/api/compras")["compras"] == [] and saldos(consulta, CD) == {}
    comprar(cliente, 5)

    reloj.momento = instante(2)
    bulto = despachar(cliente, A, (5,), "S-1")
    recibir(cliente, bulto, A, "S-1")
    verificar(cliente, bulto)

    # Venta con dos cobros: falla con un solo movimiento de caja guardado.
    reloj.momento = instante(5)
    real = fallar_despues_de_guardar_parte(monkeypatch, backend.api_ventas, "guardar_venta", sin_ultimo)
    vender(cliente, A, 2, [(EFECTIVO, "100"), (CREDITO, "100")], "venta", 500)
    monkeypatch.setattr(backend.api_ventas, "guardar_venta", real)
    for consulta in (cliente, create_app(base_datos=ruta).test_client()):
        assert get(consulta, "/api/ventas")["ventas"] == []
        assert saldos(consulta, A) == {"DISPONIBLE": 5} and caja(consulta, A) == {}
    vender(cliente, A, 2, [(EFECTIVO, "100"), (CREDITO, "100")], "venta")

    # Devolución: falla con el registro guardado pero sin su movimiento de caja.
    reloj.momento = instante(6)
    real = fallar_despues_de_guardar_parte(
        monkeypatch, backend.api_devoluciones, "guardar_devolucion",
        lambda argumentos: (*argumentos[:-1], []),
    )
    devolver(cliente, 1, "dev", 500)
    monkeypatch.setattr(backend.api_devoluciones, "guardar_devolucion", real)
    for consulta in (cliente, create_app(base_datos=ruta).test_client()):
        assert get(consulta, "/api/devoluciones")["devoluciones"] == []
        assert saldos(consulta, A) == {"DISPONIBLE": 3}
        assert caja(consulta, A) == {"Efectivo": "100.00", "Crédito": "100.00"}

    devolver(cliente, 1, "dev")
    reiniciado = create_app(base_datos=ruta).test_client()
    assert saldos(reiniciado, A) == {"DISPONIBLE": 4}
    assert caja(reiniciado, A) == {"Crédito": "100.00"}
    ventas = get(reiniciado, f"/api/reportes/ventas?{OCTUBRE}")
    assert (ventas["venta_neta"], ventas["ingreso_neto"]) == ("100.00", "100.00")
