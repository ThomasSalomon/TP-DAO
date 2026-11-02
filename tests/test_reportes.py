"""Reportes R-01 a R-04 y patrón Strategy de agrupación (sección P; T-21 a T-24, T-28)."""

from datetime import date, datetime, timezone

import pytest

from backend.dominio import (
    ESTRATEGIAS_AGRUPACION, Caja, Catalogo, EstrategiaAgrupacion, Inventario, Periodo, PorDia, PorLocal,
    PorMedioPago, RegistroCompras, RegistroDevoluciones, RegistroLogistica, RegistroReposicion, RegistroVentas,
    ReporteVentas, ZONA_ARGENTINA, existencias_y_minimos, importe_a_texto, productos_mas_vendidos,
    rechazos_logisticos,
)


def instante(mes, dia, hora=10):
    return datetime(2026, mes, dia, hora, tzinfo=ZONA_ARGENTINA)


PRIMERA_QUINCENA = Periodo(date(2026, 10, 1), date(2026, 10, 16))
OCTUBRE = Periodo(date(2026, 10, 1), date(2026, 11, 1))
NOVIEMBRE = Periodo(date(2026, 11, 1), date(2026, 12, 1))
SEPTIEMBRE = Periodo(date(2026, 9, 1), date(2026, 10, 1))


class Escenario:
    """Datos de control con resultados calculados a mano.

    - 01/10: compra en el CD (arroz a 1000, fideos a 400, lavandina a 300); sal y yerba sin compras.
    - 01/10: bulto 1 a L1 (10 arroces y 5 fideos) y bulto 2 a L2 (5 arroces y 4 lavandinas), verificados.
    - 02/10: bulto 3 a L2 (3 fideos y 2 lavandinas) rechazado por precinto roto.
    - 10/10: bulto 4 a L1 (2 sales, sin costo) rechazado por precinto distinto.
    - 05/10: venta 1 en L1, 3 arroces y 2 fideos, 6301.00 (efectivo 4000 y débito 2301).
    - 05/10 al mediodía: otra compra (arroz a 1200 y fideos a 500).
    - 06/10: venta 2 en L2, 2 arroces y 1 lavandina, 3700.00 con crédito.
    - 07/10: devolución de la lavandina de la venta 2, no apta, 700 por crédito.
    - 20/10: venta 3 en L1, 1 yerba sin costo, 2000 en efectivo.
    - 02/11: devolución de 1 arroz de la venta 1, apto, 1500 en efectivo.
    """

    def __init__(self):
        self.catalogo = Catalogo()
        self.almacen = self.catalogo.crear_categoria("ALM", "Almacén")
        self.limpieza = self.catalogo.crear_categoria("LIM", "Limpieza")
        self.arroz = self.catalogo.crear_producto("001", "Arroz", self.almacen, "1500")
        self.fideos = self.catalogo.crear_producto("002", "Fideos", self.almacen, "900.50")
        self.lavandina = self.catalogo.crear_producto("003", "Lavandina", self.limpieza, "700")
        self.yerba = self.catalogo.crear_producto("004", "Yerba", self.almacen, "2000")
        self.sal = self.catalogo.crear_producto("005", "Sal", self.almacen, "500")
        proveedor = self.catalogo.crear_proveedor("PRV", "Mayorista")
        self.cd = self.catalogo.crear_ubicacion("CD", "Central", "CD")
        self.l1 = self.catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
        self.l2 = self.catalogo.crear_ubicacion("L2", "Norte", "LOCAL")
        self.compras = RegistroCompras()
        self.inventario = Inventario()
        self.reposicion = RegistroReposicion()
        self.logistica = RegistroLogistica()
        self.ventas = RegistroVentas()
        self.devoluciones = RegistroDevoluciones()
        self.caja = Caja()
        self.efectivo, self.debito, self.credito, _ = self.ventas.listar_medios()

        self.compras.registrar(
            proveedor, self.cd, [(self.arroz, 20, "1000"), (self.fideos, 10, "400"), (self.lavandina, 10, "300")],
            instante(10, 1, 8), self.inventario,
        )
        self.inventario.restaurar_saldo(self.cd, self.sal, "DISPONIBLE", 5)
        self.inventario.restaurar_saldo(self.l1, self.yerba, "DISPONIBLE", 2)
        self.bulto1 = self.circuito(self.l1, [(self.arroz, 10), (self.fideos, 5)], instante(10, 1, 9), "P-1")
        self.bulto2 = self.circuito(self.l2, [(self.arroz, 5), (self.lavandina, 4)], instante(10, 1, 9), "P-2")
        self.bulto3 = self.circuito(
            self.l2, [(self.fideos, 3), (self.lavandina, 2)], instante(10, 2, 9), "P-3", intacto=False,
        )
        self.bulto4 = self.circuito(self.l1, [(self.sal, 2)], instante(10, 10, 9), "P-4", leido="P-99")
        for local, producto, minimo in (
            (self.l1, self.arroz, 8), (self.l1, self.fideos, 5), (self.l1, self.lavandina, 4), (self.l2, self.arroz, 2),
        ):
            self.catalogo.establecer_minimo(local.identificador, producto.identificador, minimo)

        self.venta1 = self.vender(
            self.l1, [(self.arroz, 3), (self.fideos, 2)], [(self.efectivo, "4000"), (self.debito, "2301")],
            instante(10, 5), "v1",
        )
        self.compras.registrar(
            proveedor, self.cd, [(self.arroz, 6, "1200"), (self.fideos, 4, "500")], instante(10, 5, 12), self.inventario,
        )
        self.venta2 = self.vender(
            self.l2, [(self.arroz, 2), (self.lavandina, 1)], [(self.credito, "3700")], instante(10, 6), "v2",
        )
        self.devolver(self.venta2.detalles[1], 1, False, [(self.credito, "700")], instante(10, 7), "d2")
        self.venta3 = self.vender(self.l1, [(self.yerba, 1)], [(self.efectivo, "2000")], instante(10, 20), "v3")
        self.devolver(self.venta1.detalles[0], 1, True, [(self.efectivo, "1500")], instante(11, 2), "d1")

    def circuito(self, destino, lineas, momento, precinto, intacto=True, leido=None):
        necesidades = [
            self.reposicion.registrar_necesidad(destino, producto, cantidad, momento) for producto, cantidad in lineas
        ]
        orden = self.reposicion.consolidar(self.cd, destino, necesidades, momento)
        bulto, _ = self.logistica.preparar(orden, lineas, momento, self.inventario, self.compras)
        remito = self.logistica.precintar(bulto, precinto, momento)
        bulto.despachar(momento, self.inventario)
        bulto.recibir(destino, leido or precinto, intacto, momento, self.inventario)
        if bulto.estado == "RECIBIDO":
            bulto.verificar(momento)
            remito.verificar(momento, self.inventario)
        return bulto

    def vender(self, local, lineas, cobros, momento, clave):
        venta, _, _, _ = self.ventas.registrar(
            local, lineas, cobros, momento, clave, self.inventario, self.caja, self.compras,
        )
        return venta

    def devolver(self, linea, cantidad, apto, reintegros, momento, clave):
        self.devoluciones.registrar(
            linea.venta, [(linea, cantidad, apto)], reintegros, "Control", momento, clave, self.inventario, self.caja,
        )

    def huella(self):
        """Estado observable de las operaciones, para comprobar que un reporte no lo modifica."""
        return (
            len(self.ventas.listar()), len(self.devoluciones.listar()), len(self.caja.movimientos()),
            [self.inventario.saldos(ubicacion) for ubicacion in (self.cd, self.l1, self.l2)],
            [len(self.inventario.movimientos(ubicacion)) for ubicacion in (self.cd, self.l1, self.l2)],
            [(bulto.estado, len(bulto.eventos)) for bulto in self.logistica.listar_bultos()],
        )


@pytest.fixture(scope="module")
def esc():
    # Los reportes no modifican datos (se comprueba en un test), así que el escenario se comparte.
    return Escenario()


def grupos(resultado):
    return [(g.etiqueta, g.cobros_centavos, g.reintegros_centavos, g.ingreso_neto_centavos) for g in resultado.grupos]


# Período (DN-09).

def test_periodo_incluye_el_inicio_y_excluye_el_fin():
    periodo = Periodo(date(2026, 10, 1), date(2026, 10, 2))

    assert periodo.desde == date(2026, 10, 1) and periodo.hasta == date(2026, 10, 2)
    assert periodo.contiene(datetime(2026, 10, 1, 0, 0, tzinfo=ZONA_ARGENTINA))
    assert periodo.contiene(datetime(2026, 10, 1, 23, 59, 59, tzinfo=ZONA_ARGENTINA))
    assert not periodo.contiene(datetime(2026, 10, 2, 0, 0, tzinfo=ZONA_ARGENTINA))
    assert not periodo.contiene(datetime(2026, 9, 30, 23, 59, 59, tzinfo=ZONA_ARGENTINA))


def test_periodo_usa_la_fecha_de_la_zona_acordada():
    # 02:00 UTC del 2 de octubre son las 23:00 del 1 de octubre en Argentina.
    assert Periodo(date(2026, 10, 1), date(2026, 10, 2)).contiene(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc))


@pytest.mark.parametrize("desde, hasta", [
    (date(2026, 10, 2), date(2026, 10, 1)), (date(2026, 10, 1), date(2026, 10, 1)),
])
def test_periodo_invertido_o_vacio_se_rechaza(desde, hasta):
    with pytest.raises(ValueError, match="anterior a la de fin"):
        Periodo(desde, hasta)


@pytest.mark.parametrize("desde, hasta", [
    (datetime(2026, 10, 1, tzinfo=ZONA_ARGENTINA), date(2026, 10, 2)), ("2026-10-01", date(2026, 10, 2)),
    (date(2026, 10, 1), None),
])
def test_periodo_exige_fechas_sin_hora(desde, hasta):
    with pytest.raises(TypeError):
        Periodo(desde, hasta)


# R-01 y Strategy (T-21, T-28).

def test_r01_por_medio_con_cobros_divididos_y_devolucion_del_periodo(esc):
    resultado = ReporteVentas(PorMedioPago()).generar(PRIMERA_QUINCENA, esc.ventas, esc.devoluciones, esc.caja)

    assert resultado.agrupacion == "medio" and resultado.periodo is PRIMERA_QUINCENA and resultado.local is None
    assert (resultado.cantidad_ventas, resultado.ventas_centavos) == (2, 1000100)
    assert (resultado.cantidad_devoluciones, resultado.devoluciones_centavos) == (1, 70000)
    assert resultado.venta_neta_centavos == 930100
    assert grupos(resultado) == [
        ("Efectivo", 400000, 0, 400000), ("Débito", 230100, 0, 230100), ("Crédito", 370000, 70000, 300000),
    ]
    # La venta dividida en dos medios no se cuenta dos veces.
    assert (resultado.cobros_centavos, resultado.reintegros_centavos) == (1000100, 70000)
    assert resultado.ingreso_neto_centavos == resultado.venta_neta_centavos


def test_r01_mismos_datos_con_estrategias_intercambiadas(esc):
    reporte = ReporteVentas(PorDia())
    por_dia = reporte.generar(PRIMERA_QUINCENA, esc.ventas, esc.devoluciones, esc.caja)
    reporte.cambiar_estrategia(PorLocal())
    por_local = reporte.generar(PRIMERA_QUINCENA, esc.ventas, esc.devoluciones, esc.caja)

    assert grupos(por_dia) == [
        ("05/10/2026", 630100, 0, 630100), ("06/10/2026", 370000, 0, 370000), ("07/10/2026", 0, 70000, -70000),
    ]
    assert grupos(por_local) == [("L1 — Centro", 630100, 0, 630100), ("L2 — Norte", 370000, 70000, 300000)]
    assert reporte.estrategia.nombre == "local" and por_local.agrupacion == "local"
    for resultado in (por_dia, por_local):
        assert resultado.venta_neta_centavos == resultado.ingreso_neto_centavos == 930100


def test_r01_una_estrategia_nueva_no_cambia_el_contexto(esc):
    class PorTipo(EstrategiaAgrupacion):
        @property
        def nombre(self):
            return "tipo"

        def clave(self, movimiento):
            return movimiento.tipo, movimiento.tipo.capitalize()

    resultado = ReporteVentas(PorTipo()).generar(OCTUBRE, esc.ventas, esc.devoluciones, esc.caja)

    assert grupos(resultado) == [("Egreso", 0, 70000, -70000), ("Ingreso", 1200100, 0, 1200100)]


def test_r01_filtro_de_local_y_devolucion_en_otro_periodo(esc):
    reporte = ReporteVentas(PorMedioPago())
    octubre = reporte.generar(OCTUBRE, esc.ventas, esc.devoluciones, esc.caja, local=esc.l1)
    noviembre = reporte.generar(NOVIEMBRE, esc.ventas, esc.devoluciones, esc.caja, local=esc.l1)

    assert (octubre.cantidad_ventas, octubre.ventas_centavos, octubre.devoluciones_centavos) == (2, 830100, 0)
    assert grupos(octubre) == [("Efectivo", 600000, 0, 600000), ("Débito", 230100, 0, 230100)]
    # La devolución del 02/11 afecta noviembre, no el período de la venta.
    assert (noviembre.cantidad_ventas, noviembre.ventas_centavos, noviembre.devoluciones_centavos) == (0, 0, 150000)
    assert noviembre.venta_neta_centavos == -150000
    assert grupos(noviembre) == [("Efectivo", 0, 150000, -150000)]


def test_r01_periodo_sin_operaciones(esc):
    resultado = ReporteVentas(PorDia()).generar(SEPTIEMBRE, esc.ventas, esc.devoluciones, esc.caja)

    assert resultado.grupos == ()
    assert (resultado.cantidad_ventas, resultado.venta_neta_centavos, resultado.ingreso_neto_centavos) == (0, 0, 0)


def test_estrategias_disponibles_y_contrato_abstracto():
    assert {nombre: estrategia().nombre for nombre, estrategia in ESTRATEGIAS_AGRUPACION.items()} == {
        "dia": "dia", "local": "local", "medio": "medio",
    }
    with pytest.raises(TypeError):
        EstrategiaAgrupacion()
    with pytest.raises(TypeError, match="EstrategiaAgrupacion"):
        ReporteVentas("medio")
    reporte = ReporteVentas(PorDia())
    with pytest.raises(TypeError, match="EstrategiaAgrupacion"):
        reporte.cambiar_estrategia(PorLocal)
    assert reporte.estrategia.nombre == "dia"


def test_r01_rechaza_el_cd_y_tipos_invalidos(esc):
    reporte = ReporteVentas(PorDia())
    with pytest.raises(ValueError, match="debe ser un local"):
        reporte.generar(OCTUBRE, esc.ventas, esc.devoluciones, esc.caja, local=esc.cd)
    with pytest.raises(TypeError, match="Periodo"):
        reporte.generar((date(2026, 10, 1), date(2026, 11, 1)), esc.ventas, esc.devoluciones, esc.caja)
    with pytest.raises(TypeError, match="Caja"):
        reporte.generar(OCTUBRE, esc.ventas, esc.devoluciones, esc.inventario)


# R-02 (T-22).

def filas_productos(resultado):
    return [
        (f.producto.codigo, f.unidades_vendidas, f.unidades_devueltas, f.unidades_netas, f.importe_neto_centavos,
         f.costo_neto_centavos, f.margen_centavos)
        for f in resultado.filas
    ]


def test_r02_ranking_y_margen_con_costos_historicos(esc):
    resultado = productos_mas_vendidos(PRIMERA_QUINCENA, esc.ventas, esc.devoluciones)

    # El arroz de la venta 1 cuesta 1000 y el de la venta 2, 1200: la compra posterior no reescribe la venta 1.
    assert filas_productos(resultado) == [
        ("001", 5, 0, 5, 750000, 540000, 210000),
        ("002", 2, 0, 2, 180100, 80000, 100100),
        ("003", 1, 1, 0, 0, 0, 0),
    ]
    assert (resultado.unidades_netas, resultado.importe_neto_centavos, resultado.margen_centavos) == (7, 930100, 310100)
    assert resultado.productos_sin_costo == ()


def test_r02_importe_neto_concilia_con_la_venta_neta_de_r01(esc):
    for periodo in (PRIMERA_QUINCENA, OCTUBRE, NOVIEMBRE):
        for local in (None, esc.l1, esc.l2):
            ventas = ReporteVentas(PorLocal()).generar(periodo, esc.ventas, esc.devoluciones, esc.caja, local)
            productos = productos_mas_vendidos(periodo, esc.ventas, esc.devoluciones, local)
            assert productos.importe_neto_centavos == ventas.venta_neta_centavos


def test_r02_costo_faltante_no_se_toma_como_cero(esc):
    resultado = productos_mas_vendidos(OCTUBRE, esc.ventas, esc.devoluciones)

    assert [fila.producto.codigo for fila in resultado.filas] == ["001", "002", "004", "003"]
    yerba = resultado.filas[2]
    assert (yerba.unidades_netas, yerba.importe_neto_centavos, yerba.costo_neto_centavos, yerba.margen_centavos) == (
        1, 200000, None, None,
    )
    assert resultado.productos_sin_costo == (esc.yerba,) and resultado.margen_centavos is None
    assert resultado.filas[0].margen_centavos == 210000


def test_r02_devolucion_en_otro_periodo_revierte_su_costo_original(esc):
    resultado = productos_mas_vendidos(NOVIEMBRE, esc.ventas, esc.devoluciones)

    assert filas_productos(resultado) == [("001", 0, 1, -1, -150000, -100000, -50000)]
    assert resultado.margen_centavos == -50000


def test_r02_filtro_de_local_y_unidades_netas_negativas_al_final(esc):
    resultado = productos_mas_vendidos(PRIMERA_QUINCENA, esc.ventas, esc.devoluciones, local=esc.l2)
    cruce = productos_mas_vendidos(Periodo(date(2026, 10, 20), date(2026, 11, 3)), esc.ventas, esc.devoluciones)

    assert filas_productos(resultado) == [("001", 2, 0, 2, 300000, 240000, 60000), ("003", 1, 1, 0, 0, 0, 0)]
    # La yerba vende 1 y el arroz sólo se devuelve: unidades 1 y -1.
    assert [(f.producto.codigo, f.unidades_netas) for f in cruce.filas] == [("004", 1), ("001", -1)]


def test_r02_empate_por_identificador_de_producto():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")
    arroz = catalogo.crear_producto("001", "Arroz", categoria, "100")
    fideos = catalogo.crear_producto("002", "Fideos", categoria, "100")
    local = catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
    inventario = Inventario()
    for producto in (arroz, fideos):
        inventario.restaurar_saldo(local, producto, "DISPONIBLE", 2)
    ventas = RegistroVentas()
    efectivo = ventas.listar_medios()[0]
    ventas.registrar(
        local, [(fideos, 2), (arroz, 2)], [(efectivo, "400")], instante(10, 5), "v1", inventario, Caja(),
        RegistroCompras(),
    )

    resultado = productos_mas_vendidos(OCTUBRE, ventas, RegistroDevoluciones())

    assert [(fila.producto, fila.unidades_netas) for fila in resultado.filas] == [(arroz, 2), (fideos, 2)]


def test_r02_periodo_sin_operaciones_y_cd(esc):
    resultado = productos_mas_vendidos(SEPTIEMBRE, esc.ventas, esc.devoluciones)

    assert resultado.filas == () and resultado.margen_centavos == 0 and resultado.importe_neto_centavos == 0
    with pytest.raises(ValueError, match="debe ser un local"):
        productos_mas_vendidos(OCTUBRE, esc.ventas, esc.devoluciones, local=esc.cd)


# R-03 (T-23).

def filas_existencias(resultado):
    return [
        (f.producto.codigo, f.disponible, f.minimo, f.deficit, f.en_minimo) for f in resultado.filas
    ]


def test_r03_minimo_exacto_deficit_y_producto_sin_existencia(esc):
    resultado = existencias_y_minimos(esc.l1, esc.catalogo, esc.inventario)

    assert filas_existencias(resultado) == [
        ("001", 8, 8, 0, True),      # mínimo exacto: queda en alerta sin déficit
        ("002", 3, 5, 2, True),
        ("003", 0, 4, 4, True),      # nunca tuvo stock en L1, pero tiene mínimo
        ("004", 1, None, None, False),
        ("005", 0, None, None, False),
    ]
    sal = resultado.filas[4]
    assert sal.saldos["RECHAZADO"] == 2 and sal.saldos["DISPONIBLE"] == 0
    assert (resultado.productos_en_minimo, resultado.deficit_total) == (3, 6)
    assert (resultado.total("DISPONIBLE"), resultado.total("RECHAZADO")) == (12, 2)


def test_r03_separa_disponible_de_bloqueado_y_rechazado(esc):
    resultado = existencias_y_minimos(esc.l2, esc.catalogo, esc.inventario)

    assert [(f.producto.codigo, f.saldos["DISPONIBLE"], f.saldos["BLOQUEADO"], f.saldos["RECHAZADO"])
            for f in resultado.filas] == [("001", 3, 0, 0), ("002", 0, 0, 3), ("003", 3, 1, 2)]
    # Por encima del mínimo: sin alerta ni déficit.
    assert filas_existencias(resultado)[0] == ("001", 3, 2, 0, False)


def test_r03_filtros_de_categoria_y_productos_en_minimo(esc):
    limpieza = existencias_y_minimos(esc.l2, esc.catalogo, esc.inventario, categoria=esc.limpieza)
    en_minimo = existencias_y_minimos(esc.l1, esc.catalogo, esc.inventario, solo_en_minimo=True)

    assert [fila.producto for fila in limpieza.filas] == [esc.lavandina] and limpieza.categoria is esc.limpieza
    assert [fila.producto.codigo for fila in en_minimo.filas] == ["001", "002", "003"]
    with pytest.raises(TypeError, match="verdadero o falso"):
        existencias_y_minimos(esc.l1, esc.catalogo, esc.inventario, solo_en_minimo="si")
    with pytest.raises(TypeError, match="Categoria"):
        existencias_y_minimos(esc.l1, esc.catalogo, esc.inventario, categoria="ALM")


def test_r03_cd_sin_minimos(esc):
    resultado = existencias_y_minimos(esc.cd, esc.catalogo, esc.inventario)

    assert filas_existencias(resultado) == [
        ("001", 11, None, None, False), ("002", 6, None, None, False), ("003", 4, None, None, False),
        ("005", 3, None, None, False),
    ]
    assert (resultado.productos_en_minimo, resultado.deficit_total) == (0, 0)


# R-04 (T-24).

def test_r04_rechazos_por_bulto_y_por_local(esc):
    resultado = rechazos_logisticos(OCTUBRE, esc.logistica)

    assert [(r.bulto, r.bulto.remito.numero, r.bulto.destino.codigo, r.instante, r.unidades, r.valor_bloqueado_centavos)
            for r in resultado.rechazos] == [
        (esc.bulto3, "R-000003", "L2", instante(10, 2, 9), 5, 180000),
        (esc.bulto4, "R-000004", "L1", instante(10, 10, 9), 2, None),
    ]
    assert resultado.rechazos[0].motivo == "Precinto roto."
    assert "no coincide" in resultado.rechazos[1].motivo
    assert [(item.destino.codigo, item.bultos_recibidos, item.bultos_rechazados, item.unidades,
             item.valor_bloqueado_centavos) for item in resultado.locales] == [
        ("L1", 2, 1, 2, None), ("L2", 2, 1, 5, 180000),
    ]
    assert (resultado.bultos_recibidos, resultado.bultos_rechazados, resultado.unidades) == (4, 2, 7)
    assert resultado.valor_bloqueado_centavos is None


def test_r04_un_bulto_con_varias_lineas_y_eventos_cuenta_una_vez(esc):
    resultado = rechazos_logisticos(OCTUBRE, esc.logistica, local=esc.l2)

    assert len(esc.bulto3.detalles) == 2 and len(esc.bulto3.eventos) == 5
    assert [rechazo.bulto for rechazo in resultado.rechazos] == [esc.bulto3]
    assert (resultado.bultos_rechazados, resultado.unidades, resultado.valor_bloqueado_centavos) == (1, 5, 180000)
    assert [item.destino for item in resultado.locales] == [esc.l2]


def test_r04_filtro_de_producto_cuenta_solo_sus_lineas(esc):
    resultado = rechazos_logisticos(OCTUBRE, esc.logistica, producto=esc.fideos)

    assert [(r.bulto, r.unidades, r.valor_bloqueado_centavos) for r in resultado.rechazos] == [(esc.bulto3, 3, 120000)]
    assert [(item.destino.codigo, item.bultos_recibidos, item.bultos_rechazados) for item in resultado.locales] == [
        ("L1", 1, 0), ("L2", 1, 1),
    ]


def test_r04_periodo_por_fecha_del_rechazo_y_vacio(esc):
    resultado = rechazos_logisticos(Periodo(date(2026, 10, 3), date(2026, 10, 11)), esc.logistica)
    vacio = rechazos_logisticos(SEPTIEMBRE, esc.logistica)

    assert [rechazo.bulto for rechazo in resultado.rechazos] == [esc.bulto4]
    assert [(item.destino.codigo, item.bultos_recibidos) for item in resultado.locales] == [("L1", 1)]
    assert (vacio.rechazos, vacio.locales, vacio.unidades, vacio.valor_bloqueado_centavos) == ((), (), 0, 0)


def test_r04_una_compra_posterior_no_cambia_el_valor_bloqueado():
    escenario = Escenario()
    antes = rechazos_logisticos(OCTUBRE, escenario.logistica, local=escenario.l2).valor_bloqueado_centavos
    proveedor = escenario.catalogo.obtener_proveedor(1)
    escenario.compras.registrar(
        proveedor, escenario.cd, [(escenario.fideos, 1, "9000"), (escenario.lavandina, 1, "9000")],
        instante(10, 20), escenario.inventario,
    )

    assert antes == 180000
    assert rechazos_logisticos(OCTUBRE, escenario.logistica, local=escenario.l2).valor_bloqueado_centavos == 180000


def test_r04_rechaza_filtros_invalidos(esc):
    with pytest.raises(ValueError, match="debe ser un local"):
        rechazos_logisticos(OCTUBRE, esc.logistica, local=esc.cd)
    with pytest.raises(TypeError, match="Producto"):
        rechazos_logisticos(OCTUBRE, esc.logistica, producto="002")


@pytest.mark.parametrize("centavos, texto", [
    (0, "0.00"), (5, "0.05"), (150050, "1500.50"), (-5, "-0.05"), (-150, "-1.50"), (-150000, "-1500.00"),
])
def test_importe_a_texto_con_netos_negativos(centavos, texto):
    assert importe_a_texto(centavos) == texto


# Los reportes sólo consultan.

def test_los_reportes_no_modifican_operaciones(esc):
    antes = esc.huella()
    for estrategia in ESTRATEGIAS_AGRUPACION.values():
        ReporteVentas(estrategia()).generar(OCTUBRE, esc.ventas, esc.devoluciones, esc.caja)
    productos_mas_vendidos(OCTUBRE, esc.ventas, esc.devoluciones)
    for ubicacion in (esc.cd, esc.l1, esc.l2):
        existencias_y_minimos(ubicacion, esc.catalogo, esc.inventario)
    rechazos_logisticos(OCTUBRE, esc.logistica)

    assert esc.huella() == antes
