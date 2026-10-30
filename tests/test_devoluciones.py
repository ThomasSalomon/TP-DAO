"""Devoluciones, aptitud, reintegros por medio y control acumulado (DN-07, RB-06, RB-10, RB-11, RB-12, RB-17)."""

from datetime import datetime, timedelta

import pytest

from backend.dominio import (
    Caja, Catalogo, ConflictoCatalogoError, ConflictoOperacionError, Devolucion, Inventario, RegistroCompras,
    RegistroDevoluciones, RegistroVentas, ZONA_ARGENTINA,
)

INSTANTE = datetime(2026, 10, 23, 18, 0, tzinfo=ZONA_ARGENTINA)
DESPUES = INSTANTE + timedelta(days=2)


class Escenario:
    """En L1 se vendieron 3 arroces y 2 fideos (6301.00: 4000 en efectivo y 2301 con débito).

    Quedan disponibles 2 arroces y 1 fideo.
    """

    def __init__(self):
        self.catalogo = Catalogo()
        categoria = self.catalogo.crear_categoria("ALM", "Almacén")
        self.arroz = self.catalogo.crear_producto("001", "Arroz", categoria, "1500")
        self.fideos = self.catalogo.crear_producto("002", "Fideos", categoria, "900.50")
        self.cd = self.catalogo.crear_ubicacion("CD", "Central", "CD")
        self.local = self.catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
        self.compras = RegistroCompras()
        self.inventario = Inventario()
        self.inventario.restaurar_saldo(self.local, self.arroz, "DISPONIBLE", 5)
        self.inventario.restaurar_saldo(self.local, self.fideos, "DISPONIBLE", 3)
        self.ventas = RegistroVentas()
        self.caja = Caja()
        self.efectivo, self.debito, self.credito, _ = self.ventas.listar_medios()
        self.venta, _, _, _ = self.ventas.registrar(
            self.local, [(self.arroz, 3), (self.fideos, 2)], [(self.efectivo, "4000"), (self.debito, "2301")],
            INSTANTE, "venta-1", self.inventario, self.caja, self.compras,
        )
        self.linea_arroz, self.linea_fideos = self.venta.detalles
        self.devoluciones = RegistroDevoluciones()

    def devolver(self, lineas, reintegros, clave="dev-1", motivo="Cambio de opinión", venta=None, instante=DESPUES):
        return self.devoluciones.registrar(
            venta or self.venta, lineas, reintegros, motivo, instante, clave, self.inventario, self.caja
        )

    def sin_efectos(self):
        assert self.devoluciones.listar() == ()
        assert [movimiento.tipo for movimiento in self.caja.movimientos()] == ["INGRESO", "INGRESO"]
        assert self.inventario.cantidad(self.local, self.arroz) == 2
        assert self.inventario.cantidad(self.local, self.fideos) == 1
        assert self.inventario.cantidad(self.local, self.fideos, "BLOQUEADO") == 0
        assert [movimiento.causa for movimiento in self.inventario.movimientos(self.local)] == ["VENTA", "VENTA"]


@pytest.fixture
def esc():
    return Escenario()


def test_devolucion_parcial_apta_y_no_apta(esc):
    devolucion, movimientos, caja, nueva = esc.devolver(
        [(esc.linea_arroz, 1, True), (esc.linea_fideos, 1, False)], [(esc.efectivo, "2000"), (esc.debito, "400.50")]
    )

    assert nueva and devolucion.identificador == 1 and devolucion.numero == "DV-00000001"
    assert devolucion.venta is esc.venta and devolucion.local is esc.local and devolucion.instante == DESPUES
    assert devolucion.motivo == "Cambio de opinión"
    assert [(d.numero, d.detalle_venta, d.producto, d.cantidad, d.apto, d.condicion_destino, d.importe_reintegro_centavos)
            for d in devolucion.detalles] == [
        (1, esc.linea_arroz, esc.arroz, 1, True, "DISPONIBLE", 150000),
        (2, esc.linea_fideos, esc.fideos, 1, False, "BLOQUEADO", 90050),
    ]
    assert devolucion.total_centavos == 240050 and devolucion.total == "2400.50"
    assert [(r.numero, r.medio.codigo, r.importe_centavos) for r in devolucion.reintegros] == [
        (1, "EFECTIVO", 200000), (2, "DEBITO", 40050),
    ]

    assert esc.inventario.cantidad(esc.local, esc.arroz) == 3
    assert esc.inventario.cantidad(esc.local, esc.fideos) == 1
    assert esc.inventario.cantidad(esc.local, esc.fideos, "BLOQUEADO") == 1
    assert [(m.causa, m.condicion_origen, m.condicion_destino, m.cantidad, m.documento) for m in movimientos] == [
        ("DEVOLUCION", None, "DISPONIBLE", 1, devolucion.detalles[0]),
        ("DEVOLUCION", None, "BLOQUEADO", 1, devolucion.detalles[1]),
    ]
    assert [(m.identificador, m.tipo, m.medio.codigo, m.importe, m.reintegro, m.cobro) for m in caja] == [
        (3, "EGRESO", "EFECTIVO", "2000.00", devolucion.reintegros[0], None),
        (4, "EGRESO", "DEBITO", "400.50", devolucion.reintegros[1], None),
    ]
    assert esc.caja.saldo_centavos(esc.local, esc.efectivo) == 200000
    assert esc.caja.saldo_centavos(esc.local, esc.debito) == 190050
    assert esc.devoluciones.listar(venta=esc.venta) == (devolucion,)
    assert esc.devoluciones.listar(local=esc.local) == (devolucion,) and esc.devoluciones.obtener(1) is devolucion


def test_la_devolucion_no_reescribe_la_venta(esc):
    esc.devolver([(esc.linea_arroz, 3, True)], [(esc.efectivo, "4000"), (esc.debito, "500")])

    assert [detalle.cantidad for detalle in esc.venta.detalles] == [3, 2]
    assert esc.venta.total == "6301.00" and esc.venta.comprobante.numero == "CV-00000001"
    assert esc.ventas.listar() == (esc.venta,)


def test_lo_no_apto_queda_bloqueado_y_no_se_vende(esc):
    esc.devolver([(esc.linea_fideos, 2, False)], [(esc.debito, "1801")])

    assert esc.inventario.cantidad(esc.local, esc.fideos, "BLOQUEADO") == 2
    with pytest.raises(ConflictoOperacionError, match="se necesitan 2 unidades en condición DISPONIBLE y hay 1"):
        esc.ventas.registrar(
            esc.local, [(esc.fideos, 2)], [(esc.efectivo, "1801")], DESPUES, "venta-2", esc.inventario, esc.caja,
            esc.compras,
        )


def test_lo_apto_vuelve_a_venderse(esc):
    esc.devolver([(esc.linea_arroz, 3, True)], [(esc.efectivo, "4000"), (esc.debito, "500")])

    venta, _, _, _ = esc.ventas.registrar(
        esc.local, [(esc.arroz, 5)], [(esc.credito, "7500")], DESPUES, "venta-2", esc.inventario, esc.caja, esc.compras,
    )

    assert venta.total == "7500.00" and esc.inventario.cantidad(esc.local, esc.arroz) == 0


def test_devoluciones_parciales_sucesivas_hasta_el_limite(esc):
    esc.devolver([(esc.linea_arroz, 2, True)], [(esc.efectivo, "3000")], clave="a")
    esc.devolver([(esc.linea_arroz, 1, False)], [(esc.efectivo, "1000"), (esc.debito, "500")], clave="b")

    assert esc.devoluciones.devuelto(esc.linea_arroz) == 3 and esc.devoluciones.remanente(esc.linea_arroz) == 0
    assert esc.devoluciones.remanente(esc.linea_fideos) == 2
    with pytest.raises(ConflictoOperacionError, match="Línea 1: quedan 0 unidades sin devolver de 001"):
        esc.devolver([(esc.linea_arroz, 1, True)], [(esc.debito, "1500")], clave="c")

    assert len(esc.devoluciones.listar()) == 2
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 4
    assert esc.inventario.cantidad(esc.local, esc.arroz, "BLOQUEADO") == 1
    assert len(esc.caja.movimientos()) == 5


def test_un_exceso_acumulado_en_una_linea_impide_toda_la_devolucion(esc):
    esc.devolver([(esc.linea_fideos, 1, True)], [(esc.debito, "900.50")], clave="a")

    with pytest.raises(ConflictoOperacionError, match="Línea 2: quedan 1 unidades sin devolver de 002"):
        esc.devolver([(esc.linea_arroz, 1, True), (esc.linea_fideos, 2, True)], [(esc.efectivo, "3301")], clave="b")

    assert len(esc.devoluciones.listar()) == 1
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 2 and esc.inventario.cantidad(esc.local, esc.fideos) == 2
    assert len(esc.caja.movimientos()) == 3


@pytest.mark.parametrize("lineas,error,mensaje", [
    ([], ValueError, "al menos una línea"),
    ([("arroz", 4, True)], ValueError, "Línea 1: Se vendieron 3 unidades y se intenta devolver 4"),
    ([("arroz", 0, True)], ValueError, "Línea 1: La cantidad debe ser positiva"),
    ([("arroz", 1.0, True)], TypeError, "Línea 1: La cantidad"),
    ([("arroz", 1, "si")], TypeError, "Línea 1: La aptitud"),
    ([("arroz", 1, True), ("arroz", 1, True)], ValueError, "Línea 2: una línea vendida no puede repetirse"),
    ([("x", 1, True)], TypeError, "Línea 1: La línea vendida"),
])
def test_lineas_invalidas_no_registran_la_devolucion(esc, lineas, error, mensaje):
    detalles = {"arroz": esc.linea_arroz, "x": esc.arroz}

    with pytest.raises(error, match=mensaje):
        esc.devolver([(detalles[d], cantidad, apto) for d, cantidad, apto in lineas], [(esc.efectivo, "1500")])

    esc.sin_efectos()


def test_solo_se_devuelven_lineas_de_la_venta_indicada(esc):
    otra, _, _, _ = esc.ventas.registrar(
        esc.local, [(esc.arroz, 1)], [(esc.efectivo, "1500")], INSTANTE, "venta-2", esc.inventario, esc.caja, esc.compras,
    )

    with pytest.raises(ValueError, match="Línea 1: la línea indicada no pertenece a la venta"):
        esc.devolver([(otra.detalles[0], 1, True)], [(esc.efectivo, "1500")])
    with pytest.raises(TypeError, match="La venta debe ser una Venta"):
        esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], venta=1)

    assert esc.devoluciones.listar() == ()


@pytest.mark.parametrize("reintegros,mensaje", [
    ([("efectivo", "1400")], "suman 1400.00 y el total a reintegrar es 1500.00"),
    ([("efectivo", "1500"), ("debito", "1")], "suman 1501.00"),
    ([("efectivo", "1000"), ("efectivo", "500")], "Reintegro 2: un medio de pago no puede repetirse"),
    ([("credito", "1500")], "Reintegro 1: la venta no se cobró con Crédito"),
    ([("efectivo", "0")], "Reintegro 1: El importe debe ser estrictamente positivo"),
    ([], "al menos un reintegro"),
])
def test_los_reintegros_deben_cubrir_exactamente_el_total(esc, reintegros, mensaje):
    medios = {"efectivo": esc.efectivo, "debito": esc.debito, "credito": esc.credito}

    with pytest.raises(ValueError, match=mensaje):
        esc.devolver([(esc.linea_arroz, 1, True)], [(medios[medio], importe) for medio, importe in reintegros])

    esc.sin_efectos()


def test_cada_medio_reintegra_hasta_lo_cobrado_con_el(esc):
    with pytest.raises(ConflictoOperacionError, match="Reintegro 1: con Débito quedan 2301.00 por reintegrar"):
        esc.devolver([(esc.linea_arroz, 2, True)], [(esc.debito, "3000")])
    esc.sin_efectos()

    esc.devolver([(esc.linea_arroz, 2, True)], [(esc.efectivo, "3000")], clave="a")
    assert esc.devoluciones.reintegrable_centavos(esc.venta, esc.efectivo) == 100000
    with pytest.raises(ConflictoOperacionError, match="con Efectivo quedan 1000.00"):
        esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave="b")

    esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1000"), (esc.debito, "500")], clave="b")
    assert esc.caja.saldo_centavos(esc.local, esc.efectivo) == 0
    assert esc.caja.saldo_centavos(esc.local, esc.debito) == 180100


def test_motivo_obligatorio_y_acotado(esc):
    for motivo, error in (("", ValueError), ("   ", ValueError), ("x" * 201, ValueError), (None, TypeError)):
        with pytest.raises(error, match="motivo"):
            esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], motivo=motivo)
    esc.sin_efectos()


@pytest.mark.parametrize("clave", ["", "   ", "x" * 65])
def test_clave_de_operacion_obligatoria_y_acotada(esc, clave):
    with pytest.raises(ValueError, match="clave de operación"):
        esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave=clave)
    esc.sin_efectos()


def test_misma_clave_devuelve_la_devolucion_sin_repetir_efectos(esc):
    primera, _, _, nueva = esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave="borrador-3")

    repetida, movimientos, caja, repetida_nueva = esc.devolver(
        [(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave=" borrador-3 "
    )

    assert nueva and not repetida_nueva and repetida is primera
    assert movimientos == () and caja == ()
    assert esc.devoluciones.remanente(esc.linea_arroz) == 2
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 3 and len(esc.caja.movimientos()) == 3


def test_no_puede_ser_anterior_a_la_venta(esc):
    with pytest.raises(ValueError, match="anterior a la venta"):
        esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], instante=INSTANTE - timedelta(seconds=1))
    esc.sin_efectos()


def test_sin_plazo_se_devuelve_mucho_despues(esc):
    devolucion, _, _, _ = esc.devolver(
        [(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], instante=INSTANTE + timedelta(days=400)
    )

    assert devolucion.instante - esc.venta.instante == timedelta(days=400)


def test_local_inactivo_no_admite_devoluciones_pero_producto_inactivo_si(esc):
    esc.catalogo.desactivar_producto(esc.arroz.identificador)
    devolucion, _, _, _ = esc.devolver([(esc.linea_arroz, 1, False)], [(esc.efectivo, "1500")], clave="a")
    assert devolucion.detalles[0].condicion_destino == "BLOQUEADO"

    esc.catalogo.desactivar_ubicacion(esc.local.identificador)
    with pytest.raises(ConflictoCatalogoError, match="local está inactivo"):
        esc.devolver([(esc.linea_fideos, 1, True)], [(esc.debito, "900.50")], clave="b")
    assert len(esc.devoluciones.listar()) == 1


def test_reintegra_al_precio_historico_de_la_venta(esc):
    esc.arroz.cambiar_precio("9999")

    devolucion, _, _, _ = esc.devolver([(esc.linea_arroz, 2, True)], [(esc.efectivo, "3000")])

    assert devolucion.total == "3000.00" and devolucion.detalles[0].importe_reintegro_centavos == 300000


def test_las_unidades_del_local_se_conservan(esc):
    """Lo vendido sale del local y lo devuelto vuelve a entrar: el total sólo cambia por esas causas."""
    esc.devolver([(esc.linea_arroz, 2, True), (esc.linea_fideos, 1, False)], [(esc.efectivo, "3900.50")])

    total_arroz = sum(cantidad for producto, _, cantidad in esc.inventario.saldos(esc.local) if producto is esc.arroz)
    total_fideos = sum(cantidad for producto, _, cantidad in esc.inventario.saldos(esc.local) if producto is esc.fideos)
    assert total_arroz == 5 - 3 + 2 and total_fideos == 3 - 2 + 1


def test_devolucion_de_solo_lectura(esc):
    devolucion, _, _, _ = esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")])

    assert isinstance(devolucion.detalles, tuple) and isinstance(devolucion.reintegros, tuple)
    with pytest.raises(AttributeError):
        devolucion.detalles[0].cantidad = 3
    with pytest.raises(AttributeError):
        devolucion.numero = "DV-1"


def test_identificadores_de_devolucion_y_caja_continuan(esc):
    esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave="a")
    segunda, _, caja, _ = esc.devolver([(esc.linea_fideos, 1, True)], [(esc.debito, "900.50")], clave="b")

    assert segunda.numero == "DV-00000002"
    assert [movimiento.identificador for movimiento in caja] == [4]


def test_restaurar_devolucion_no_repite_efectos_y_exige_orden(esc):
    devolucion = Devolucion(1, esc.venta, DESPUES, [(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], "Falla", "hist")

    esc.devoluciones.restaurar(devolucion)

    assert esc.devoluciones.obtener(1) is devolucion and esc.devoluciones.remanente(esc.linea_arroz) == 2
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 2 and len(esc.caja.movimientos()) == 2
    repetida, _, _, nueva = esc.devolver([(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], clave="hist")
    assert repetida is devolucion and not nueva
    with pytest.raises(ValueError, match="orden"):
        esc.devoluciones.restaurar(
            Devolucion(5, esc.venta, DESPUES, [(esc.linea_arroz, 1, True)], [(esc.efectivo, "1500")], "Falla", "z")
        )
