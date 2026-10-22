"""Reposición y ciclo del bulto con State: reserva, despacho, recepción y doble verificación."""

from datetime import datetime, timedelta

import pytest

from backend.dominio import (
    CONDICIONES, Catalogo, ConflictoCatalogoError, ConflictoOperacionError, EstadoBulto, Inventario,
    RegistroCompras, RegistroLogistica, RegistroReposicion, TransicionBultoError, ZONA_ARGENTINA,
)

INSTANTE = datetime(2026, 10, 22, 9, 0, tzinfo=ZONA_ARGENTINA)


class Escenario:
    """CD con stock comprado, dos locales y registros vacíos de reposición y logística."""

    def __init__(self):
        self.catalogo = Catalogo()
        categoria = self.catalogo.crear_categoria("ALM", "Almacén")
        self.arroz = self.catalogo.crear_producto("001", "Arroz", categoria, "1500")
        self.fideos = self.catalogo.crear_producto("002", "Fideos", categoria, "900")
        proveedor = self.catalogo.crear_proveedor("PRV", "Molinos")
        self.cd = self.catalogo.crear_ubicacion("CD", "Central", "CD")
        self.local = self.catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
        self.otro_local = self.catalogo.crear_ubicacion("L2", "Norte", "LOCAL")
        self.compras = RegistroCompras()
        self.inventario = Inventario()
        self.compras.registrar(
            proveedor, self.cd, [(self.arroz, 20, "1000"), (self.fideos, 10, "400")], INSTANTE, self.inventario
        )
        self.reposicion = RegistroReposicion()
        self.logistica = RegistroLogistica()

    def orden(self, *pedidos, local=None):
        local = local or self.local
        necesidades = [
            self.reposicion.registrar_necesidad(local, producto, cantidad, INSTANTE) for producto, cantidad in pedidos
        ]
        return self.reposicion.consolidar(self.cd, local, necesidades, INSTANTE)

    def preparar(self, orden, *lineas):
        bulto, _ = self.logistica.preparar(orden, list(lineas), INSTANTE, self.inventario, self.compras)
        return bulto

    def bulto_en(self, estado):
        """Bulto de 5 arroces llevado hasta el estado pedido por el camino válido."""
        bulto = self.preparar(self.orden((self.arroz, 5)), (self.arroz, 5))
        pasos = {
            "PRECINTADO": [lambda: self.logistica.precintar(bulto, f"P-{bulto.identificador}", INSTANTE)],
            "ANULADO": [lambda: bulto.anular(INSTANTE, self.inventario)],
        }
        pasos["EN_TRANSITO"] = pasos["PRECINTADO"] + [lambda: bulto.despachar(INSTANTE, self.inventario)]
        pasos["RECIBIDO"] = pasos["EN_TRANSITO"] + [
            lambda: bulto.recibir(self.local, bulto.precinto, True, INSTANTE, self.inventario)
        ]
        pasos["VERIFICADO"] = pasos["RECIBIDO"] + [lambda: bulto.verificar(INSTANTE)]
        pasos["RECHAZADO"] = pasos["EN_TRANSITO"] + [
            lambda: bulto.recibir(self.local, bulto.precinto, False, INSTANTE, self.inventario)
        ]
        for paso in pasos.get(estado, []):
            paso()
        assert bulto.estado == estado
        return bulto

    def saldos(self, producto):
        """Saldos no nulos del producto por (ubicación, condición)."""
        return {
            (ubicacion.codigo, condicion): self.inventario.cantidad(ubicacion, producto, condicion)
            for ubicacion in (self.cd, self.local, self.otro_local)
            for condicion in CONDICIONES
            if self.inventario.cantidad(ubicacion, producto, condicion)
        }


@pytest.fixture
def esc():
    return Escenario()


def test_consolidar_suma_por_producto_y_conserva_las_necesidades(esc):
    n1 = esc.reposicion.registrar_necesidad(esc.local, esc.arroz, 4, INSTANTE)
    n2 = esc.reposicion.registrar_necesidad(esc.local, esc.fideos, 2, INSTANTE)
    n3 = esc.reposicion.registrar_necesidad(esc.local, esc.arroz, 6, INSTANTE)
    assert [n.estado for n in (n1, n2, n3)] == ["PENDIENTE"] * 3

    orden = esc.reposicion.consolidar(esc.cd, esc.local, [n1, n2, n3], INSTANTE)

    assert orden.centro is esc.cd and orden.destino is esc.local
    assert [(d.producto, d.cantidad_solicitada, d.necesidades) for d in orden.detalles] == [
        (esc.arroz, 10, (n1, n3)), (esc.fideos, 2, (n2,)),
    ]
    assert orden.estado == "ABIERTA"
    assert all(n.estado == "CONSOLIDADA" and n.orden is orden for n in (n1, n2, n3))
    assert esc.reposicion.listar_ordenes() == (orden,)
    assert esc.reposicion.listar_necesidades(esc.local) == (n1, n2, n3)


def test_consolidar_rechaza_mezclar_locales_repetir_o_reutilizar_necesidades(esc):
    propia = esc.reposicion.registrar_necesidad(esc.local, esc.arroz, 1, INSTANTE)
    ajena = esc.reposicion.registrar_necesidad(esc.otro_local, esc.arroz, 1, INSTANTE)

    with pytest.raises(ValueError, match="local destino"):
        esc.reposicion.consolidar(esc.cd, esc.local, [propia, ajena], INSTANTE)
    with pytest.raises(ValueError, match="repetirse"):
        esc.reposicion.consolidar(esc.cd, esc.local, [propia, propia], INSTANTE)
    with pytest.raises(ValueError, match="al menos una"):
        esc.reposicion.consolidar(esc.cd, esc.local, [], INSTANTE)
    with pytest.raises(ValueError, match="Centro de Distribución"):
        esc.reposicion.consolidar(esc.otro_local, esc.local, [propia], INSTANTE)
    assert propia.estado == "PENDIENTE" and esc.reposicion.listar_ordenes() == ()

    esc.reposicion.consolidar(esc.cd, esc.local, [propia], INSTANTE)
    with pytest.raises(ConflictoOperacionError, match="ya fue consolidada"):
        esc.reposicion.consolidar(esc.cd, esc.local, [propia], INSTANTE)
    assert len(esc.reposicion.listar_ordenes()) == 1


@pytest.mark.parametrize("cantidad,error", [(0, ValueError), (-3, ValueError), (2.0, TypeError), (True, TypeError)])
def test_necesidad_requiere_cantidad_entera_positiva(esc, cantidad, error):
    with pytest.raises(error, match="cantidad"):
        esc.reposicion.registrar_necesidad(esc.local, esc.arroz, cantidad, INSTANTE)
    assert esc.reposicion.listar_necesidades() == ()


def test_necesidad_la_registra_un_local_activo_con_producto_activo(esc):
    with pytest.raises(ValueError, match="local"):
        esc.reposicion.registrar_necesidad(esc.cd, esc.arroz, 1, INSTANTE)
    esc.catalogo.desactivar_ubicacion(esc.otro_local.identificador)
    with pytest.raises(ConflictoCatalogoError):
        esc.reposicion.registrar_necesidad(esc.otro_local, esc.arroz, 1, INSTANTE)
    esc.catalogo.desactivar_producto(esc.fideos.identificador)
    with pytest.raises(ConflictoCatalogoError):
        esc.reposicion.registrar_necesidad(esc.local, esc.fideos, 1, INSTANTE)
    assert esc.reposicion.listar_necesidades() == ()


def test_circuito_completo_habilita_stock_solo_con_bulto_y_remito_verificados(esc):
    orden = esc.orden((esc.arroz, 4), (esc.arroz, 2), (esc.fideos, 3))
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 20}

    bulto, reservas = esc.logistica.preparar(
        orden, [(esc.arroz, 6), (esc.fideos, 3)], INSTANTE, esc.inventario, esc.compras
    )
    assert bulto.codigo == "B-000001" and bulto.estado == "PREPARADO"
    assert bulto.origen is esc.cd and bulto.destino is esc.local
    assert [(d.producto, d.cantidad, d.costo_referencia_centavos) for d in bulto.detalles] == [
        (esc.arroz, 6, 100000), (esc.fideos, 3, 40000),
    ]
    assert [m.causa for m in reservas] == ["PREPARACION", "PREPARACION"]
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 14, ("CD", "RESERVADO"): 6}
    assert orden.estado == "COMPLETA"

    remito = esc.logistica.precintar(bulto, " SELLO-77 ", INSTANTE)
    assert remito.numero == "R-000001" and remito.estado == "EMITIDO"
    assert remito.origen is esc.cd and remito.destino is esc.local
    assert bulto.precinto == "SELLO-77" and bulto.remito is remito

    despacho = bulto.despachar(INSTANTE + timedelta(hours=1), esc.inventario)
    assert [(m.ubicacion.codigo, m.condicion_origen, m.condicion_destino) for m in despacho[:2]] == [
        ("CD", "RESERVADO", None), ("L1", None, "EN_TRANSITO"),
    ]
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 14, ("L1", "EN_TRANSITO"): 6}

    bulto.recibir(esc.local, "sello-77", True, INSTANTE + timedelta(hours=5), esc.inventario)
    assert bulto.estado == "RECIBIDO"
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 14, ("L1", "PENDIENTE"): 6}

    assert bulto.verificar(INSTANTE + timedelta(hours=6)) == ()
    assert bulto.estado == "VERIFICADO"
    # Con el contenedor verificado pero el remito emitido, el stock sigue sin habilitarse.
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 0

    habilitados = remito.verificar(INSTANTE + timedelta(hours=7), esc.inventario)
    assert [m.causa for m in habilitados] == ["VERIFICACION", "VERIFICACION"]
    assert remito.estado == "VERIFICADO" and remito.instante_cierre == INSTANTE + timedelta(hours=7)
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 14, ("L1", "DISPONIBLE"): 6}
    assert esc.saldos(esc.fideos) == {("CD", "DISPONIBLE"): 7, ("L1", "DISPONIBLE"): 3}

    assert [(e.secuencia, e.estado_anterior, e.estado_nuevo) for e in bulto.eventos] == [
        (1, None, "PREPARADO"), (2, "PREPARADO", "PRECINTADO"), (3, "PRECINTADO", "EN_TRANSITO"),
        (4, "EN_TRANSITO", "RECIBIDO"), (5, "RECIBIDO", "VERIFICADO"),
    ]
    assert len(esc.inventario.movimientos(esc.local)) == 2 * 3


@pytest.mark.parametrize("leido,intacto,motivo", [
    ("SELLO-77", False, "Precinto roto"),
    ("SELLO-78", True, "no coincide"),
])
def test_precinto_roto_o_distinto_rechaza_en_la_misma_recepcion(esc, leido, intacto, motivo):
    bulto = esc.preparar(esc.orden((esc.arroz, 5)), (esc.arroz, 5))
    remito = esc.logistica.precintar(bulto, "SELLO-77", INSTANTE)
    bulto.despachar(INSTANTE, esc.inventario)

    movimientos = bulto.recibir(esc.local, leido, intacto, INSTANTE, esc.inventario)

    assert bulto.estado == "RECHAZADO" and remito.estado == "RECHAZADO"
    assert [m.causa for m in movimientos] == ["RECHAZO"]
    assert [e.estado_nuevo for e in bulto.eventos][-2:] == ["RECIBIDO", "RECHAZADO"]
    assert motivo in bulto.eventos[-1].motivo
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 15, ("L1", "RECHAZADO"): 5}
    with pytest.raises(TransicionBultoError, match="rechazado"):
        bulto.verificar(INSTANTE)
    with pytest.raises(ConflictoOperacionError, match="rechazado"):
        remito.verificar(INSTANTE, esc.inventario)
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 0


def test_recibir_en_otro_local_no_cambia_nada(esc):
    bulto = esc.bulto_en("EN_TRANSITO")
    eventos = bulto.eventos

    with pytest.raises(ConflictoOperacionError, match="local destino"):
        bulto.recibir(esc.otro_local, bulto.precinto, True, INSTANTE, esc.inventario)

    assert bulto.estado == "EN_TRANSITO" and bulto.eventos == eventos
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 15, ("L1", "EN_TRANSITO"): 5}


@pytest.mark.parametrize("estado,operaciones", [
    ("PREPARADO", ["despachar", "recibir", "verificar"]),
    ("PRECINTADO", ["precintar", "recibir", "verificar", "anular"]),
    ("EN_TRANSITO", ["precintar", "despachar", "verificar", "anular"]),
    ("RECIBIDO", ["precintar", "despachar", "recibir", "anular"]),
    ("VERIFICADO", ["precintar", "despachar", "recibir", "verificar", "anular"]),
    ("RECHAZADO", ["precintar", "despachar", "recibir", "verificar", "anular"]),
    ("ANULADO", ["precintar", "despachar", "recibir", "verificar", "anular"]),
])
def test_cada_estado_rechaza_las_operaciones_que_no_admite_sin_efectos(esc, estado, operaciones):
    bulto = esc.bulto_en(estado)
    llamadas = {
        "precintar": lambda: esc.logistica.precintar(bulto, "OTRO-SELLO", INSTANTE),
        "despachar": lambda: bulto.despachar(INSTANTE, esc.inventario),
        "recibir": lambda: bulto.recibir(esc.local, "P-1", True, INSTANTE, esc.inventario),
        "verificar": lambda: bulto.verificar(INSTANTE),
        "anular": lambda: bulto.anular(INSTANTE, esc.inventario),
    }
    eventos, saldos, remitos = bulto.eventos, esc.saldos(esc.arroz), esc.logistica.listar_remitos()

    for operacion in operaciones:
        with pytest.raises(TransicionBultoError, match=bulto.codigo):
            llamadas[operacion]()

    assert bulto.estado == estado and bulto.eventos == eventos
    assert esc.saldos(esc.arroz) == saldos and esc.logistica.listar_remitos() == remitos


def test_remito_no_se_verifica_antes_que_su_bulto_ni_dos_veces(esc):
    bulto = esc.bulto_en("RECIBIDO")

    with pytest.raises(ConflictoOperacionError, match="Verificá el bulto"):
        bulto.remito.verificar(INSTANTE, esc.inventario)
    assert esc.inventario.cantidad(esc.local, esc.arroz, "PENDIENTE") == 5

    bulto.verificar(INSTANTE)
    bulto.remito.verificar(INSTANTE, esc.inventario)
    with pytest.raises(ConflictoOperacionError, match="ya está verificado"):
        bulto.remito.verificar(INSTANTE, esc.inventario)
    assert esc.inventario.cantidad(esc.local, esc.arroz) == 5


def test_entregas_parciales_dejan_pendiente_hasta_completar_la_orden(esc):
    orden = esc.orden((esc.arroz, 10))

    esc.preparar(orden, (esc.arroz, 4))
    assert orden.detalles[0].cantidad_asignada == 4 and orden.detalles[0].cantidad_pendiente == 6
    with pytest.raises(ConflictoOperacionError, match="6 unidades pendientes"):
        esc.preparar(orden, (esc.arroz, 7))
    esc.preparar(orden, (esc.arroz, 6))

    assert orden.estado == "COMPLETA" and len(orden.bultos) == 2
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 10, ("CD", "RESERVADO"): 10}


def test_no_se_reserva_mas_que_lo_disponible_en_el_cd(esc):
    orden = esc.orden((esc.arroz, 30), (esc.fideos, 2))

    with pytest.raises(ConflictoOperacionError, match="Stock insuficiente de 001"):
        esc.preparar(orden, (esc.fideos, 2), (esc.arroz, 21))

    assert esc.saldos(esc.fideos) == {("CD", "DISPONIBLE"): 10}
    assert orden.bultos == () and esc.logistica.listar_bultos() == ()
    assert esc.inventario.movimientos(esc.cd)[-1].causa == "COMPRA"


def test_preparar_valida_contenido_y_productos_de_la_orden(esc):
    orden = esc.orden((esc.arroz, 5))

    with pytest.raises(ValueError, match="no figura en la orden"):
        esc.preparar(orden, (esc.fideos, 1))
    with pytest.raises(ValueError, match="repetirse"):
        esc.preparar(orden, (esc.arroz, 1), (esc.arroz, 1))
    with pytest.raises(ValueError, match="^Línea 1: La cantidad"):
        esc.preparar(orden, (esc.arroz, 0))
    with pytest.raises(ValueError, match="al menos un producto"):
        esc.preparar(orden)
    esc.catalogo.desactivar_producto(esc.arroz.identificador)
    with pytest.raises(ConflictoCatalogoError, match="inactivos"):
        esc.preparar(orden, (esc.arroz, 1))

    assert esc.logistica.listar_bultos() == () and esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 20}


def test_anular_un_preparado_libera_la_reserva_y_devuelve_el_pendiente(esc):
    orden = esc.orden((esc.arroz, 5))
    bulto = esc.preparar(orden, (esc.arroz, 5))
    assert orden.estado == "COMPLETA"

    movimientos = bulto.anular(INSTANTE, esc.inventario)

    assert bulto.estado == "ANULADO" and [m.causa for m in movimientos] == ["ANULACION"]
    assert esc.saldos(esc.arroz) == {("CD", "DISPONIBLE"): 20}
    assert orden.estado == "ABIERTA" and orden.detalles[0].cantidad_pendiente == 5
    assert esc.preparar(orden, (esc.arroz, 5)).codigo == "B-000002"


def test_precinto_es_unico_sin_distinguir_mayusculas_y_no_consume_remito(esc):
    primero = esc.preparar(esc.orden((esc.arroz, 1)), (esc.arroz, 1))
    segundo = esc.preparar(esc.orden((esc.arroz, 1)), (esc.arroz, 1))
    esc.logistica.precintar(primero, "Sello-1", INSTANTE)

    with pytest.raises(ConflictoOperacionError, match="ya fue usado"):
        esc.logistica.precintar(segundo, "SELLO-1", INSTANTE)
    with pytest.raises(ValueError, match="precinto"):
        esc.logistica.precintar(segundo, "  ", INSTANTE)

    assert segundo.estado == "PREPARADO" and segundo.precinto is None
    assert esc.logistica.precintar(segundo, "SELLO-2", INSTANTE).numero == "R-000002"


def test_costo_de_preparacion_no_cambia_con_compras_posteriores(esc):
    bulto = esc.preparar(esc.orden((esc.arroz, 2)), (esc.arroz, 2))
    proveedor = esc.catalogo.obtener_proveedor(1)

    esc.compras.registrar(proveedor, esc.cd, [(esc.arroz, 1, "5000")], INSTANTE + timedelta(days=1), esc.inventario)

    assert bulto.detalles[0].costo_referencia_centavos == 100000
    assert esc.compras.costo_referencia(esc.arroz) == 500000


def test_las_unidades_se_conservan_en_todo_el_circuito(esc):
    verificado = esc.bulto_en("VERIFICADO")
    verificado.remito.verificar(INSTANTE, esc.inventario)
    esc.bulto_en("RECHAZADO")
    esc.bulto_en("EN_TRANSITO")
    esc.bulto_en("ANULADO")

    assert sum(esc.saldos(esc.arroz).values()) == 20
    assert esc.saldos(esc.arroz) == {
        ("CD", "DISPONIBLE"): 5, ("L1", "DISPONIBLE"): 5, ("L1", "RECHAZADO"): 5, ("L1", "EN_TRANSITO"): 5,
    }


def test_estado_bulto_es_un_contrato_abstracto():
    with pytest.raises(TypeError):
        EstadoBulto()


def test_historial_no_expone_modificaciones(esc):
    bulto = esc.bulto_en("PRECINTADO")

    assert isinstance(bulto.eventos, tuple)
    with pytest.raises(AttributeError):
        bulto.eventos[0].estado_nuevo = "VERIFICADO"
    with pytest.raises(AttributeError):
        bulto.estado = "VERIFICADO"
