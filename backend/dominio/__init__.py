"""Dominio en memoria, independiente de HTTP y persistencia."""

from .catalogo import (
    Catalogo, Categoria, CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError,
    Producto, Proveedor, Ubicacion, importe_a_texto,
)
from .caja import Caja, MovimientoCaja
from .compras import Compra, DetalleCompra, RegistroCompras
from .errores import ConflictoOperacionError
from .fechas import ZONA_ARGENTINA, ahora
from .inventario import CAUSAS, CONDICIONES, Inventario, MovimientoStock
from .logistica import (
    ESTADOS_BULTO, Bulto, DetalleBulto, EstadoBulto, EventoEstadoBulto, RegistroLogistica, Remito,
    TransicionBultoError,
)
from .reposicion import DetalleReposicion, NecesidadReposicion, OrdenReposicion, RegistroReposicion
from .ventas import MEDIOS_PAGO, Cobro, Comprobante, DetalleVenta, MedioPago, RegistroVentas, Venta

__all__ = [
    "CAUSAS", "CONDICIONES", "MEDIOS_PAGO", "Bulto", "Caja", "Catalogo", "Cobro", "Comprobante", "Categoria", "CentroDistribucionDuplicadoError",
    "CodigoDuplicadoError", "Compra", "ConflictoCatalogoError", "ConflictoOperacionError", "DetalleBulto",
    "DetalleCompra", "DetalleReposicion", "DetalleVenta", "MedioPago", "MovimientoCaja", "RegistroVentas", "Venta", "ESTADOS_BULTO", "EstadoBulto", "EventoEstadoBulto", "Inventario",
    "MovimientoStock", "NecesidadReposicion", "OrdenReposicion", "Producto", "Proveedor", "RegistroCompras",
    "RegistroLogistica", "RegistroReposicion", "Remito", "TransicionBultoError", "Ubicacion", "ZONA_ARGENTINA",
    "ahora", "importe_a_texto",
]
