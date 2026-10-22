"""Saldos por ubicación, producto y condición, y movimientos que los justifican."""

from .catalogo import Producto, Ubicacion, _validar_identificador
from .compras import Compra, DetalleCompra
from .errores import ConflictoOperacionError
from .fechas import validar_instante
from .logistica import Bulto, DetalleBulto

# Condiciones del modelo (DER). BLOQUEADO queda reservada para devoluciones no aptas (F-05).
CONDICIONES = ("DISPONIBLE", "RESERVADO", "EN_TRANSITO", "PENDIENTE", "RECHAZADO", "BLOQUEADO")
# Causa de cada movimiento y tipo de documento que debe originarlo.
CAUSAS = {
    "COMPRA": DetalleCompra,
    "PREPARACION": DetalleBulto,
    "ANULACION": DetalleBulto,
    "DESPACHO": DetalleBulto,
    "RECEPCION": DetalleBulto,
    "VERIFICACION": DetalleBulto,
    "RECHAZO": DetalleBulto,
}
# Mayor entero que SQLite almacena exactamente.
SALDO_MAXIMO = 2**63 - 1


def _validar_condicion(condicion):
    if condicion not in CONDICIONES:
        raise ValueError("La condición de stock no es válida.")


class MovimientoStock:
    """Evidencia inmutable de un cambio de saldo y del documento que lo causó.

    Sin condición de origen es una entrada a la ubicación; sin destino, una salida.
    """

    def __init__(self, identificador, instante, ubicacion, producto, cantidad,
                 condicion_origen, condicion_destino, causa, documento):
        _validar_identificador(identificador)
        validar_instante(instante)
        if not isinstance(ubicacion, Ubicacion) or not isinstance(producto, Producto):
            raise TypeError("El movimiento requiere una Ubicacion y un Producto.")
        if type(cantidad) is not int or cantidad <= 0:
            raise ValueError("La cantidad del movimiento debe ser un entero positivo.")
        if condicion_origen is None and condicion_destino is None:
            raise ValueError("El movimiento debe tener una condición de origen o de destino.")
        for condicion in (condicion_origen, condicion_destino):
            if condicion is not None:
                _validar_condicion(condicion)
        if causa not in CAUSAS:
            raise ValueError("La causa del movimiento no es válida.")
        if not isinstance(documento, CAUSAS[causa]):
            raise TypeError("El documento no corresponde a la causa del movimiento.")
        self._identificador = identificador
        self._instante = instante
        self._ubicacion = ubicacion
        self._producto = producto
        self._cantidad = cantidad
        self._condicion_origen = condicion_origen
        self._condicion_destino = condicion_destino
        self._causa = causa
        self._documento = documento

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
        return self._condicion_origen

    @property
    def condicion_destino(self):
        return self._condicion_destino

    @property
    def causa(self):
        return self._causa

    @property
    def documento(self):
        """Línea de compra o de bulto que originó el movimiento."""
        return self._documento


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

    def _aplicar(self, pasos, instante, causa):
        """pasos: (ubicación, producto, cantidad, condición origen, condición destino, documento).

        Comprueba todos los saldos resultantes antes de modificar alguno.
        """
        variaciones = {}
        for ubicacion, producto, cantidad, origen, destino, _ in pasos:
            if origen is not None:
                clave = (ubicacion, producto, origen)
                variaciones[clave] = variaciones.get(clave, 0) - cantidad
            if destino is not None:
                clave = (ubicacion, producto, destino)
                variaciones[clave] = variaciones.get(clave, 0) + cantidad
        for (ubicacion, producto, condicion), variacion in variaciones.items():
            actual = self.cantidad(ubicacion, producto, condicion)
            resultado = actual + variacion
            if resultado < 0:
                raise ConflictoOperacionError(
                    f"Stock insuficiente de {producto.codigo} en {ubicacion.codigo}: se necesitan {-variacion} "
                    f"unidades en condición {condicion} y hay {actual}."
                )
            if resultado > SALDO_MAXIMO:
                raise ValueError("El saldo resultante supera el máximo admitido.")

        movimientos = []
        for ubicacion, producto, cantidad, origen, destino, documento in pasos:
            movimiento = MovimientoStock(
                len(self._movimientos) + 1, instante, ubicacion, producto, cantidad, origen, destino, causa, documento,
            )
            self._movimientos.append(movimiento)
            movimientos.append(movimiento)
        for clave, variacion in variaciones.items():
            self._saldos[clave] = self._saldos.get(clave, 0) + variacion
        return tuple(movimientos)

    def ingresar_compra(self, compra):
        """Ingresa cada línea como disponible en el CD de la compra."""
        if not isinstance(compra, Compra):
            raise TypeError("La compra debe ser una Compra.")
        pasos = [
            (compra.centro, detalle.producto, detalle.cantidad, None, "DISPONIBLE", detalle)
            for detalle in compra.detalles
        ]
        return self._aplicar(pasos, compra.instante, "COMPRA")

    def _mover_bulto(self, bulto, instante, causa, ubicacion, origen, destino):
        if not isinstance(bulto, Bulto):
            raise TypeError("El bulto debe ser un Bulto.")
        pasos = [(ubicacion, detalle.producto, detalle.cantidad, origen, destino, detalle) for detalle in bulto.detalles]
        return self._aplicar(pasos, instante, causa)

    def reservar_bulto(self, bulto, instante):
        return self._mover_bulto(bulto, instante, "PREPARACION", bulto.origen, "DISPONIBLE", "RESERVADO")

    def liberar_bulto(self, bulto, instante):
        return self._mover_bulto(bulto, instante, "ANULACION", bulto.origen, "RESERVADO", "DISPONIBLE")

    def despachar_bulto(self, bulto, instante):
        """Sale la reserva del CD y entra en tránsito al destino: el total se conserva."""
        if not isinstance(bulto, Bulto):
            raise TypeError("El bulto debe ser un Bulto.")
        pasos = []
        for detalle in bulto.detalles:
            pasos.append((bulto.origen, detalle.producto, detalle.cantidad, "RESERVADO", None, detalle))
            pasos.append((bulto.destino, detalle.producto, detalle.cantidad, None, "EN_TRANSITO", detalle))
        return self._aplicar(pasos, instante, "DESPACHO")

    def recibir_bulto(self, bulto, instante):
        return self._mover_bulto(bulto, instante, "RECEPCION", bulto.destino, "EN_TRANSITO", "PENDIENTE")

    def rechazar_bulto(self, bulto, instante):
        """Rechazo logístico: queda en custodia del local, sin habilitar venta ni registrar merma."""
        return self._mover_bulto(bulto, instante, "RECHAZO", bulto.destino, "EN_TRANSITO", "RECHAZADO")

    def habilitar_bulto(self, bulto, instante):
        return self._mover_bulto(bulto, instante, "VERIFICACION", bulto.destino, "PENDIENTE", "DISPONIBLE")

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
