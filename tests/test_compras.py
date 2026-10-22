"""Compras confirmadas, ingreso al CD y costo de referencia (DN-03)."""

from datetime import datetime, timedelta

import pytest

from backend.dominio import (
    Catalogo, Compra, ConflictoCatalogoError, Inventario, RegistroCompras, ZONA_ARGENTINA,
)
from backend.dominio.inventario import SALDO_MAXIMO

INSTANTE = datetime(2026, 10, 21, 10, 0, tzinfo=ZONA_ARGENTINA)


def escenario():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")
    arroz = catalogo.crear_producto("001", "Arroz", categoria, "1500")
    fideos = catalogo.crear_producto("002", "Fideos", categoria, "900")
    proveedor = catalogo.crear_proveedor("PRV", "Molinos")
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")
    local = catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
    return catalogo, arroz, fideos, proveedor, cd, local, RegistroCompras(), Inventario()


def test_registrar_compra_crea_detalles_e_ingresa_todo_al_cd():
    _, arroz, fideos, proveedor, cd, local, compras, inventario = escenario()

    compra, movimientos = compras.registrar(
        proveedor, cd, [(arroz, 10, "1000"), (fideos, 3, "450.5")], INSTANTE, inventario
    )

    assert compra.identificador == 1
    assert compra.proveedor is proveedor and compra.centro is cd and compra.instante == INSTANTE
    assert [(d.numero, d.producto, d.cantidad, d.costo_unitario) for d in compra.detalles] == [
        (1, arroz, 10, "1000.00"), (2, fideos, 3, "450.50"),
    ]
    assert all(detalle.compra is compra for detalle in compra.detalles)
    assert compra.total_centavos == 10 * 100000 + 3 * 45050
    assert compra.total == "11351.50"
    assert compras.listar() == (compra,) and compras.obtener(1) is compra

    assert inventario.cantidad(cd, arroz) == 10
    assert inventario.cantidad(cd, fideos) == 3
    assert inventario.existencias(cd) == ((arroz, 10), (fideos, 3))
    assert inventario.existencias(local) == ()
    assert inventario.cantidad(local, arroz) == 0
    assert inventario.movimientos(cd) == movimientos
    assert [(m.identificador, m.producto, m.cantidad, m.condicion_origen, m.condicion_destino, m.causa)
            for m in movimientos] == [
        (1, arroz, 10, None, "DISPONIBLE", "COMPRA"), (2, fideos, 3, None, "DISPONIBLE", "COMPRA"),
    ]
    assert movimientos[1].documento is compra.detalles[1]
    assert movimientos[0].instante == INSTANTE


def test_compras_sucesivas_acumulan_saldo_y_numeran_movimientos():
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    compras.registrar(proveedor, cd, [(arroz, 10, "100")], INSTANTE, inventario)
    segunda, movimientos = compras.registrar(proveedor, cd, [(arroz, 5, "120")], INSTANTE, inventario)

    assert segunda.identificador == 2
    assert inventario.cantidad(cd, arroz) == 15
    assert movimientos[0].identificador == 2
    assert len(inventario.movimientos(cd)) == 2


def test_costo_de_referencia_es_la_ultima_compra_por_instante_y_luego_identificador():
    _, arroz, fideos, proveedor, cd, _, compras, inventario = escenario()
    assert compras.costo_referencia(arroz) is None

    compras.registrar(proveedor, cd, [(arroz, 1, "100")], INSTANTE, inventario)
    compras.registrar(proveedor, cd, [(arroz, 1, "120"), (fideos, 1, "50")], INSTANTE, inventario)
    assert compras.costo_referencia(arroz) == 12000
    assert compras.costo_referencia(fideos) == 5000

    # Una compra registrada después pero con instante anterior no reemplaza el costo.
    compras.registrar(proveedor, cd, [(arroz, 1, "90")], INSTANTE - timedelta(days=1), inventario)
    assert compras.costo_referencia(arroz) == 12000
    compras.registrar(proveedor, cd, [(arroz, 1, "130")], INSTANTE + timedelta(seconds=1), inventario)
    assert compras.costo_referencia(arroz) == 13000


def test_cambiar_precio_o_desactivar_no_altera_compras_registradas():
    catalogo, arroz, _, proveedor, cd, _, compras, inventario = escenario()
    compra, _ = compras.registrar(proveedor, cd, [(arroz, 2, "100")], INSTANTE, inventario)

    arroz.cambiar_precio("9999")
    catalogo.desactivar_producto(arroz.identificador)
    catalogo.desactivar_proveedor(proveedor.identificador)

    assert compra.detalles[0].costo_unitario == "100.00"
    assert compras.costo_referencia(arroz) == 10000
    assert inventario.cantidad(cd, arroz) == 2


@pytest.mark.parametrize("cantidad,error", [
    (0, ValueError), (-1, ValueError), (1.0, TypeError), (True, TypeError), ("1", TypeError), (None, TypeError),
])
def test_cantidad_debe_ser_entero_positivo(cantidad, error):
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(error, match="cantidad"):
        compras.registrar(proveedor, cd, [(arroz, cantidad, "100")], INSTANTE, inventario)

    assert compras.listar() == () and inventario.existencias(cd) == ()


@pytest.mark.parametrize("costo,error", [
    ("0", ValueError), ("0.00", ValueError), ("-1", ValueError), ("1.001", ValueError), ("", ValueError),
    ("92233720368547758.08", ValueError), (100, TypeError), (1.5, TypeError), (None, TypeError),
])
def test_costo_unitario_es_importe_positivo_exacto(costo, error):
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(error, match="costo unitario"):
        compras.registrar(proveedor, cd, [(arroz, 1, costo)], INSTANTE, inventario)

    assert compras.listar() == () and inventario.existencias(cd) == ()


def test_una_linea_invalida_impide_registrar_toda_la_compra():
    _, arroz, fideos, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(ValueError, match="^Línea 2: La cantidad"):
        compras.registrar(proveedor, cd, [(arroz, 5, "100"), (fideos, 0, "100")], INSTANTE, inventario)

    assert compras.listar() == ()
    assert inventario.cantidad(cd, arroz) == 0 and inventario.movimientos(cd) == ()


@pytest.mark.parametrize("lineas,error,mensaje", [
    ([], ValueError, "al menos una línea"),
    ((), ValueError, "al menos una línea"),
    (None, TypeError, "lista"),
    ("arroz", TypeError, "lista"),
])
def test_compra_requiere_una_lista_de_lineas_no_vacia(lineas, error, mensaje):
    _, _, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(error, match=mensaje):
        compras.registrar(proveedor, cd, lineas, INSTANTE, inventario)


def test_producto_repetido_en_la_misma_compra_se_rechaza():
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(ValueError, match="repetirse"):
        compras.registrar(proveedor, cd, [(arroz, 1, "100"), (arroz, 2, "100")], INSTANTE, inventario)

    assert inventario.existencias(cd) == ()


def test_las_compras_ingresan_al_cd_y_no_a_un_local():
    _, arroz, _, proveedor, _, local, compras, inventario = escenario()

    with pytest.raises(ValueError, match="Centro de Distribución"):
        compras.registrar(proveedor, local, [(arroz, 1, "100")], INSTANTE, inventario)

    assert inventario.existencias(local) == ()


@pytest.mark.parametrize("instante,error", [
    (datetime(2026, 10, 21, 10, 0), ValueError), ("2026-10-21T10:00:00-03:00", TypeError), (None, TypeError),
])
def test_instante_debe_ser_datetime_con_zona(instante, error):
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(error, match="instante"):
        compras.registrar(proveedor, cd, [(arroz, 1, "100")], instante, inventario)


def test_tipos_de_proveedor_destino_y_producto_se_validan():
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()

    with pytest.raises(TypeError, match="proveedor"):
        compras.registrar("PRV", cd, [(arroz, 1, "100")], INSTANTE, inventario)
    with pytest.raises(TypeError, match="destino"):
        compras.registrar(proveedor, 1, [(arroz, 1, "100")], INSTANTE, inventario)
    with pytest.raises(TypeError, match="producto"):
        compras.registrar(proveedor, cd, [(1, 1, "100")], INSTANTE, inventario)


def test_proveedor_o_producto_inactivo_no_admite_nuevas_compras():
    catalogo, arroz, fideos, proveedor, cd, _, compras, inventario = escenario()
    catalogo.desactivar_producto(fideos.identificador)

    with pytest.raises(ConflictoCatalogoError, match="inactivos"):
        compras.registrar(proveedor, cd, [(arroz, 1, "100"), (fideos, 1, "100")], INSTANTE, inventario)
    catalogo.desactivar_proveedor(proveedor.identificador)
    with pytest.raises(ConflictoCatalogoError, match="proveedor"):
        compras.registrar(proveedor, cd, [(arroz, 1, "100")], INSTANTE, inventario)

    assert compras.listar() == () and inventario.existencias(cd) == ()


def test_saldo_que_superaria_el_maximo_no_cambia_nada():
    _, arroz, fideos, proveedor, cd, _, compras, inventario = escenario()
    inventario.restaurar_saldo(cd, arroz, "DISPONIBLE", SALDO_MAXIMO)

    with pytest.raises(ValueError, match="máximo"):
        compras.registrar(proveedor, cd, [(fideos, 1, "100"), (arroz, 1, "100")], INSTANTE, inventario)

    assert inventario.cantidad(cd, fideos) == 0
    assert inventario.movimientos(cd) == () and compras.listar() == ()


def test_compra_es_inmutable_y_no_expone_detalles_modificables():
    _, arroz, _, proveedor, cd, _, compras, inventario = escenario()
    compra, _ = compras.registrar(proveedor, cd, [(arroz, 1, "100")], INSTANTE, inventario)

    assert isinstance(compra.detalles, tuple)
    with pytest.raises(AttributeError):
        compra.proveedor = None
    with pytest.raises(AttributeError):
        compra.detalles[0].cantidad = 5


def test_restaurar_compra_historica_admite_inactivos_y_exige_orden():
    catalogo, arroz, _, proveedor, cd, _, compras, inventario = escenario()
    catalogo.desactivar_producto(arroz.identificador)
    catalogo.desactivar_proveedor(proveedor.identificador)

    compra = Compra(1, proveedor, cd, INSTANTE, [(arroz, 4, "100")])
    compras.restaurar(compra)

    assert compras.obtener(1) is compra
    assert inventario.existencias(cd) == ()
    with pytest.raises(ValueError, match="orden"):
        compras.restaurar(Compra(3, proveedor, cd, INSTANTE, [(arroz, 1, "100")]))


def test_catalogo_informa_el_centro_de_distribucion():
    catalogo = Catalogo()
    assert catalogo.centro_distribucion() is None
    catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")

    assert catalogo.centro_distribucion() is cd
