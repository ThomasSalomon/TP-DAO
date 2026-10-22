"""Saldos por ubicación, producto y condición, y movimientos que los justifican."""

from .catalogo import Producto, Ubicacion, _validar_identificador
from .compras import Compra, DetalleCompra
from .fechas import validar_instante

# Condiciones del modelo (DER). F-02 sólo usa DISPONIBLE; el resto llega con la logística.
CONDICIONES = ("DISPONIBLE", "RESERVADO", "EN_TRANSITO", "PENDIENTE", "RECHAZADO", "BLOQUEADO")
# Mayor entero que SQLite almacena exactamente.
SALDO_MAXIMO = 2**63 - 1


def _validar_condicion(condicion):
    if condicion not in CONDICIONES:
        raise ValueError("La condición de stock no es válida.")


class MovimientoStock:
    """Evidencia inmutable de un cambio de saldo y del documento que lo causó."""

    def __init__(self, identificador, instante, ubicacion, producto, cantidad, condicion_destino, causa, detalle):
        _validar_identificador(identificador)
        validar_instante(instante)
        if not isinstance(ubicacion, Ubicacion) or not isinstance(producto, Producto):
            raise TypeError("El movimiento requiere una Ubicacion y un Producto.")
        if type(cantidad) is not int or cantidad <= 0:
            raise ValueError("La cantidad del movimiento debe ser un entero positivo.")
        _validar_condicion(condicion_destino)
        if causa != "COMPRA" or not isinstance(detalle, DetalleCompra):
            raise ValueError("Por ahora sólo hay ingresos causados por una línea de compra.")
        self._identificador = identificador
        self._instante = instante
        self._ubicacion = ubicacion
        self._producto = producto
        self._cantidad = cantidad
        self._condicion_destino = condicion_destino
        self._causa = causa
        self._detalle = detalle

    @property
    def identificador(self):
        return self._identificador

    @property
    def instante(self):
        return self._instante

    @property
    def ubicacion(self):
        return self._ubicacion

    @property
    def producto(self):
        return self._producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def condicion_origen(self):
        # Un ingreso por compra no proviene de ninguna condición previa.
        return None

    @property
    def condicion_destino(self):
        return self._condicion_destino

    @property
    def causa(self):
        return self._causa

    @property
    def detalle(self):
        """Línea de compra que originó el movimiento."""
        return self._detalle


class Inventario:
    """Único responsable de modificar saldos; cada cambio deja un movimiento."""

    def __init__(self):
        self._saldos = {}
        self._movimientos = []

    def cantidad(self, ubicacion, producto, condicion="DISPONIBLE"):
        """Cero si nunca hubo saldo: la ausencia no significa producto inexistente."""
        _validar_condicion(condicion)
        return self._saldos.get((ubicacion, producto, condicion), 0)

    def existencias(self, ubicacion, condicion="DISPONIBLE"):
        """Pares (producto, cantidad) de la ubicación, ordenados por producto."""
        _validar_condicion(condicion)
        pares = [
            (producto, cantidad)
            for (lugar, producto, estado), cantidad in self._saldos.items()
            if lugar is ubicacion and estado == condicion
        ]
        return tuple(sorted(pares, key=lambda par: par[0].identificador))

    def movimientos(self, ubicacion):
        return tuple(movimiento for movimiento in self._movimientos if movimiento.ubicacion is ubicacion)

    def ingresar_compra(self, compra):
        """Ingresa cada línea como disponible en el CD de la compra."""
        if not isinstance(compra, Compra):
            raise TypeError("La compra debe ser una Compra.")
        for detalle in compra.detalles:
            if self.cantidad(compra.centro, detalle.producto) + detalle.cantidad > SALDO_MAXIMO:
                raise ValueError("El saldo resultante supera el máximo admitido.")

        movimientos = []
        for detalle in compra.detalles:
            movimiento = MovimientoStock(
                len(self._movimientos) + 1, compra.instante, compra.centro, detalle.producto,
                detalle.cantidad, "DISPONIBLE", "COMPRA", detalle,
            )
            self._movimientos.append(movimiento)
            clave = (compra.centro, detalle.producto, "DISPONIBLE")
            self._saldos[clave] = self._saldos.get(clave, 0) + detalle.cantidad
            movimientos.append(movimiento)
        return tuple(movimientos)

    def restaurar_saldo(self, ubicacion, producto, condicion, cantidad):
        """Carga un saldo ya confirmado; no genera movimiento."""
        _validar_condicion(condicion)
        if type(cantidad) is not int or not 0 <= cantidad <= SALDO_MAXIMO:
            raise ValueError("El saldo debe ser un entero no negativo.")
        self._saldos[(ubicacion, producto, condicion)] = cantidad

    def restaurar_movimiento(self, movimiento):
        """Incorpora un movimiento ya confirmado, en orden de identificador."""
        if not isinstance(movimiento, MovimientoStock):
            raise TypeError("El movimiento debe ser un MovimientoStock.")
        if movimiento.identificador != len(self._movimientos) + 1:
            raise ValueError("Los movimientos se restauran en orden de identificador.")
        self._movimientos.append(movimiento)
