"""Dominio en memoria, independiente de HTTP y persistencia."""

from .catalogo import (
    Catalogo, Categoria, CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError,
    Producto, Proveedor, Ubicacion, importe_a_texto,
)
from .compras import Compra, DetalleCompra, RegistroCompras
from .fechas import ZONA_ARGENTINA, ahora
from .inventario import CONDICIONES, Inventario, MovimientoStock

__all__ = [
    "CONDICIONES", "Catalogo", "Categoria", "CentroDistribucionDuplicadoError", "CodigoDuplicadoError", "Compra",
    "ConflictoCatalogoError", "DetalleCompra", "Inventario", "MovimientoStock", "Producto", "Proveedor",
    "RegistroCompras", "Ubicacion", "ZONA_ARGENTINA", "ahora", "importe_a_texto",
]
