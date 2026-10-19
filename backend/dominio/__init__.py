"""Dominio en memoria, independiente de HTTP y persistencia."""

from .catalogo import (
    Catalogo, Categoria, CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError,
    Producto, Proveedor, Ubicacion,
)

__all__ = [
    "Catalogo", "Categoria", "CentroDistribucionDuplicadoError", "CodigoDuplicadoError", "ConflictoCatalogoError",
    "Producto", "Proveedor", "Ubicacion",
]
