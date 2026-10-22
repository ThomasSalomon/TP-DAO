"""Ventas, cobros divididos, caja y comprobante (DN-05, RB-04, RB-10, RB-12)."""

from datetime import datetime, timedelta

import pytest

from backend.dominio import (
    Caja, Catalogo, ConflictoCatalogoError, ConflictoOperacionError, Inventario, RegistroCompras,
    RegistroLogistica, RegistroReposicion, RegistroVentas, Venta, ZONA_ARGENTINA,
)

INSTANTE = datetime(2026, 10, 23, 18, 0, tzinfo=ZONA_ARGENTINA)


class Escenario:
    """Local L1 con 5 arroces y 3 fideos disponibles; L2 sin stock vendible."""

    def __init__(self):
        self.catalogo = Catalogo()
        categoria = self.catalogo.crear_categoria("ALM", "Almacén")
        self.arroz = self.catalogo.crear_producto("001", "Arroz", categoria, "1500")
        self.fideos = self.catalogo.crear_producto("002", "Fideos", categoria, "900.50")
        self.cd = self.catalogo.crear_ubicacion("CD", "Central", "CD")
        self.local = self.catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
        self.otro_local = self.catalogo.crear_ubicacion("L2", "Norte", "LOCAL")
        self.proveedor = self.catalogo.crear_proveedor("PRV", "Molinos")
        self.compras = RegistroCompras()
        self.inventario = Inventario()
        self.compras.registrar(
            self.proveedor, self.cd, [(self.arroz, 20, "1000"), (self.fideos, 10, "400")], INSTANTE, self.inventario
        )
        self.inventario.restaurar_saldo(self.local, self.arroz, "DISPONIBLE", 5)
        self.inventario.restaurar_saldo(self.local, self.fideos, "DISPONIBLE", 3)
        self.ventas = RegistroVentas()
        self.caja = Caja()
        self.efectivo, self.debito, self.credito, self.transferencia = self.ventas.listar_medios()

    def vender(self, lineas, cobros, clave="clave-1", local=None):
        return self.ventas.registrar(
            local or self.local, lineas, cobros, INSTANTE, clave, self.inventario, self.caja, self.compras
        )

    def sin_efectos(self):
        assert self.ventas.listar() == () and self.caja.movimientos() == ()
        assert self.inventario.cantidad(self.local, self.arroz) == 5
        assert self.inventario.cantidad(self.local, self.fideos) == 3
        assert self.inventario.movimientos(self.local) == ()


@pytest.fixture
def esc():
    return Escenario()


def test_venta_con_varias_lineas_y_cobros_divididos(esc):
    venta, movimientos, caja, nueva = esc.vender(
        [(esc.arroz, 2), (esc.fideos, 1)], [(esc.efectivo, "2000"), (esc.debito, "1900.50")]
    )

    assert nueva and venta.identificador == 1 and venta.local is esc.local
    assert [(d.numero, d.producto, d.cantidad, d.precio_unitario_centavos, d.costo_referencia_centavos, d.subtotal_centavos)
            for d in venta.detalles] == [
        (1, esc.arroz, 2, 150000, 100000, 300000), (2, esc.fideos, 1, 90050, 40000, 90050),
    ]
    assert venta.total_centavos == 390050 and venta.total == "3900.50"
    assert [(c.numero, c.medio.codigo, c.importe_centavos) for c in venta.cobros] == [
        (1, "EFECTIVO", 200000), (2, "DEBITO", 190050),
    ]
    assert venta.comprobante.numero == "CV-00000001" and venta.comprobante.venta is venta
    assert venta.comprobante.instante == INSTANTE

    assert esc.inventario.cantidad(esc.local, esc.arroz) == 3
    assert esc.inventario.cantidad(esc.local, esc.fideos) == 2
    assert [(m.causa, m.condicion_origen, m.condicion_destino, m.documento) for m in movimientos] == [
        ("VENTA", "DISPONIBLE", None, venta.detalles[0]), ("VENTA", "DISPONIBLE", None, venta.detalles[1]),
    ]
    assert [(m.tipo, m.medio.codigo, m.importe, m.cobro) for m in caja] == [
        ("INGRESO", "EFECTIVO", "2000.00", venta.cobros[0]), ("INGRESO", "DEBITO", "1900.50", venta.cobros[1]),
    ]
    assert esc.caja.saldo_centavos(esc.local, esc.efectivo) == 200000
    assert esc.caja.saldo_centavos(esc.otro_local, esc.efectivo) == 0
    assert esc.ventas.listar(esc.local) == (venta,) and esc.ventas.listar(esc.otro_local) == ()


def test_se_puede_vender_la_ultima_unidad(esc):
    esc.vender([(esc.arroz, 5)], [(esc.efectivo, "7500")])

    assert esc.inventario.cantidad(esc.local, esc.arroz) == 0
    with pytest.raises(ConflictoOperacionError, match="Stock insuficiente de 001 en L1"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], clave="clave-2")
    assert len(esc.ventas.listar()) == 1


def test_una_linea_sin_stock_impide_toda_la_venta(esc):
    with pytest.raises(ConflictoOperacionError, match="se necesitan 4 unidades en condición DISPONIBLE y hay 3"):
        esc.vender([(esc.arroz, 1), (esc.fideos, 4)], [(esc.efectivo, "5102")])

    esc.sin_efectos()


def test_stock_pendiente_rechazado_o_en_transito_nunca_se_vende(esc):
    for condicion in ("PENDIENTE", "RECHAZADO", "EN_TRANSITO", "RESERVADO"):
        esc.inventario.restaurar_saldo(esc.otro_local, esc.arroz, condicion, 10)

    with pytest.raises(ConflictoOperacionError, match="hay 0"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], local=esc.otro_local)

    assert esc.ventas.listar() == ()


def test_solo_se_vende_lo_que_llego_con_bulto_y_remito_verificados(esc):
    reposicion, logistica = RegistroReposicion(), RegistroLogistica()
    necesidad = reposicion.registrar_necesidad(esc.otro_local, esc.arroz, 4, INSTANTE)
    orden = reposicion.consolidar(esc.cd, esc.otro_local, [necesidad], INSTANTE)
    bulto, _ = logistica.preparar(orden, [(esc.arroz, 4)], INSTANTE, esc.inventario, esc.compras)
    logistica.precintar(bulto, "S-1", INSTANTE)
    bulto.despachar(INSTANTE, esc.inventario)
    bulto.recibir(esc.otro_local, "S-1", True, INSTANTE, esc.inventario)
    bulto.verificar(INSTANTE)

    with pytest.raises(ConflictoOperacionError):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], local=esc.otro_local)
    bulto.remito.verificar(INSTANTE, esc.inventario)
    venta, _, _, _ = esc.vender([(esc.arroz, 4)], [(esc.credito, "6000")], local=esc.otro_local)

    assert venta.total == "6000.00" and esc.inventario.cantidad(esc.otro_local, esc.arroz) == 0


@pytest.mark.parametrize("cobros,mensaje", [
    ([("efectivo", "2400")], "suman 2400.00 y el total de la venta es 2400.50"),
    ([("efectivo", "2400.50"), ("debito", "1")], "suman 2401.50"),
    ([("efectivo", "2400"), ("efectivo", "0.50")], "Cobro 2: un medio de pago no puede repetirse"),
    ([("efectivo", "0")], "Cobro 1: El importe debe ser estrictamente positivo"),
    ([("efectivo", "2400.501")], "Cobro 1: El importe no puede tener más de dos decimales"),
    ([], "al menos un cobro"),
])
def test_los_cobros_deben_cubrir_exactamente_el_total(esc, cobros, mensaje):
    medios = {"efectivo": esc.efectivo, "debito": esc.debito}

    with pytest.raises(ValueError, match=mensaje):
        esc.vender([(esc.arroz, 1), (esc.fideos, 1)], [(medios[medio], importe) for medio, importe in cobros])

    esc.sin_efectos()


def test_importe_y_medio_de_tipo_invalido(esc):
    with pytest.raises(TypeError, match="Cobro 1: El importe"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, 1500)])
    with pytest.raises(TypeError, match="Cobro 1: El medio"):
        esc.vender([(esc.arroz, 1)], [("EFECTIVO", "1500")])
    esc.sin_efectos()


@pytest.mark.parametrize("lineas,error,mensaje", [
    ([], ValueError, "al menos una línea"),
    ([("arroz", 0)], ValueError, "Línea 1: La cantidad debe ser positiva"),
    ([("arroz", 1.0)], TypeError, "Línea 1: La cantidad"),
    ([("arroz", 1), ("arroz", 1)], ValueError, "Línea 2: un producto no puede repetirse"),
    ([("x", 1)], TypeError, "Línea 1: El producto"),
])
def test_lineas_invalidas_no_registran_la_venta(esc, lineas, error, mensaje):
    productos = {"arroz": esc.arroz, "x": "001"}

    with pytest.raises(error, match=mensaje):
        esc.vender([(productos[producto], cantidad) for producto, cantidad in lineas], [(esc.efectivo, "1500")])

    esc.sin_efectos()


def test_el_cd_no_vende_y_los_inactivos_no_admiten_ventas(esc):
    with pytest.raises(ValueError, match="local, no el CD"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], local=esc.cd)
    esc.catalogo.desactivar_producto(esc.fideos.identificador)
    with pytest.raises(ConflictoCatalogoError, match="inactivos"):
        esc.vender([(esc.arroz, 1), (esc.fideos, 1)], [(esc.efectivo, "2400.50")])
    esc.catalogo.desactivar_ubicacion(esc.local.identificador)
    with pytest.raises(ConflictoCatalogoError, match="local está inactivo"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")])
    esc.sin_efectos()


def test_misma_clave_de_operacion_devuelve_la_venta_sin_repetir_efectos(esc):
    primera, _, _, nueva = esc.vender([(esc.arroz, 2)], [(esc.efectivo, "3000")], clave="borrador-7")

    repetida, movimientos, caja, repetida_nueva = esc.vender(
        [(esc.arroz, 2)], [(esc.efectivo, "3000")], clave=" borrador-7 "
    )

    assert nueva and not repetida_nueva and repetida is primera
    assert movimientos == () and caja == ()
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 3
    assert len(esc.caja.movimientos()) == 1 and len(esc.ventas.listar()) == 1


@pytest.mark.parametrize("clave", ["", "   ", "x" * 65])
def test_clave_de_operacion_obligatoria_y_acotada(esc, clave):
    with pytest.raises(ValueError, match="clave de operación"):
        esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], clave=clave)
    esc.sin_efectos()


def test_precio_y_costo_historicos_no_cambian_con_el_catalogo_ni_con_compras(esc):
    venta, _, _, _ = esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")])

    esc.arroz.cambiar_precio("9999")
    esc.compras.registrar(esc.proveedor, esc.cd, [(esc.arroz, 1, "5000")], INSTANTE + timedelta(days=1), esc.inventario)

    assert venta.detalles[0].precio_unitario_centavos == 150000
    assert venta.detalles[0].costo_referencia_centavos == 100000
    assert venta.total == "1500.00"
    siguiente, _, _, _ = esc.vender([(esc.arroz, 1)], [(esc.efectivo, "9999")], clave="clave-2")
    assert siguiente.detalles[0].costo_referencia_centavos == 500000


def test_producto_sin_compras_se_vende_con_costo_faltante(esc):
    categoria = esc.catalogo.obtener_categoria(1)
    aceite = esc.catalogo.crear_producto("003", "Aceite", categoria, "3000")
    esc.inventario.restaurar_saldo(esc.local, aceite, "DISPONIBLE", 2)

    venta, _, _, _ = esc.vender([(aceite, 1)], [(esc.transferencia, "3000")])

    assert venta.detalles[0].costo_referencia_centavos is None


def test_comprobante_y_venta_son_de_solo_lectura(esc):
    venta, _, _, _ = esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")])

    assert esc.ventas.obtener(1).comprobante is venta.comprobante
    assert isinstance(venta.detalles, tuple) and isinstance(venta.cobros, tuple)
    with pytest.raises(AttributeError):
        venta.detalles[0].cantidad = 9
    with pytest.raises(AttributeError):
        venta.comprobante.numero = "CV-1"


def test_identificadores_de_venta_y_caja_continuan(esc):
    esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], clave="a")
    segunda, _, caja, _ = esc.vender([(esc.fideos, 1)], [(esc.efectivo, "500"), (esc.debito, "400.50")], clave="b")

    assert segunda.comprobante.numero == "CV-00000002"
    assert [movimiento.identificador for movimiento in caja] == [2, 3]


def test_restaurar_venta_no_repite_efectos_y_exige_orden(esc):
    venta = Venta(1, esc.local, INSTANTE, [(esc.arroz, 2, 150000, None)], [(esc.efectivo, "3000")], "historica")

    esc.ventas.restaurar(venta)

    assert esc.ventas.obtener(1) is venta
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 5 and esc.caja.movimientos() == ()
    repetida, _, _, nueva = esc.vender([(esc.arroz, 1)], [(esc.efectivo, "1500")], clave="historica")
    assert repetida is venta and not nueva
    with pytest.raises(ValueError, match="orden"):
        esc.ventas.restaurar(Venta(5, esc.local, INSTANTE, [(esc.arroz, 1, 150000, None)], [(esc.efectivo, "1500")], "z"))


def test_medios_de_pago_fijos(esc):
    assert [(m.identificador, m.codigo, m.nombre) for m in esc.ventas.listar_medios()] == [
        (1, "EFECTIVO", "Efectivo"), (2, "DEBITO", "Débito"), (3, "CREDITO", "Crédito"),
        (4, "TRANSFERENCIA", "Transferencia"),
    ]
    assert esc.ventas.obtener_medio(3) is esc.credito
    with pytest.raises(KeyError):
        esc.ventas.obtener_medio(9)
