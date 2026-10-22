"""Movimientos de caja por local y medio de pago (DN-05). Importes en ARS."""

from .catalogo import PRECIO_MAXIMO_CENTAVOS, Ubicacion, _validar_identificador, importe_a_texto
from .fechas import validar_instante
from .ventas import Cobro, MedioPago, Venta


class MovimientoCaja:
    """Ingreso por un cobro o, desde F-05, egreso por un reintegro; no se modifica."""

    def __init__(self, identificador, instante, local, medio, tipo, importe_centavos, cobro):
        _validar_identificador(identificador)
        validar_instante(instante)
        if not isinstance(local, Ubicacion) or not isinstance(medio, MedioPago):
            raise TypeError("El movimiento de caja requiere una Ubicacion y un MedioPago.")
        if tipo != "INGRESO" or not isinstance(cobro, Cobro):
            raise ValueError("Por ahora la caja sólo registra ingresos causados por un cobro.")
        if type(importe_centavos) is not int or not 0 < importe_centavos <= PRECIO_MAXIMO_CENTAVOS:
            raise ValueError("El importe del movimiento de caja debe ser un entero positivo de centavos.")
        self._identificador = identificador
        self._instante = instante
        self._local = local
        self._medio = medio
        self._tipo = tipo
        self._importe_centavos = importe_centavos
        self._cobro = cobro

    @property
    def identificador(self):
        return self._identificador

    @property
    def instante(self):
        return self._instante

    @property
    def local(self):
        return self._local

    @property
    def medio(self):
        return self._medio

    @property
    def tipo(self):
        return self._tipo

    @property
    def importe_centavos(self):
        return self._importe_centavos

    @property
    def importe(self):
        return importe_a_texto(self._importe_centavos)

    @property
    def cobro(self):
        return self._cobro


class Caja:
    """Único responsable de registrar movimientos de dinero; el saldo se calcula desde ellos."""

    def __init__(self):
        self._movimientos = []

    def ingresar_venta(self, venta):
        """Un ingreso por cada cobro de la venta, en el local y medio del cobro."""
        if not isinstance(venta, Venta):
            raise TypeError("La venta debe ser una Venta.")
        movimientos = tuple(
            MovimientoCaja(
                len(self._movimientos) + numero, venta.instante, venta.local, cobro.medio, "INGRESO",
                cobro.importe_centavos, cobro,
            )
            for numero, cobro in enumerate(venta.cobros, start=1)
        )
        self._movimientos.extend(movimientos)
        return movimientos

    def movimientos(self, local=None):
        return tuple(item for item in self._movimientos if local is None or item.local is local)

    def saldo_centavos(self, local, medio):
        """Ingresos menos egresos del medio en el local."""
        return sum(
            item.importe_centavos if item.tipo == "INGRESO" else -item.importe_centavos
            for item in self._movimientos if item.local is local and item.medio is medio
        )

    def restaurar_movimiento(self, movimiento):
        """Incorpora un movimiento ya confirmado, en orden de identificador."""
        if not isinstance(movimiento, MovimientoCaja):
            raise TypeError("El movimiento debe ser un MovimientoCaja.")
        if movimiento.identificador != len(self._movimientos) + 1:
            raise ValueError("Los movimientos de caja se restauran en orden de identificador.")
        self._movimientos.append(movimiento)
