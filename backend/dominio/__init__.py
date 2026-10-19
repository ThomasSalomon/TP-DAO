"""Dominio en memoria, independiente de HTTP y persistencia."""

from .catalogo import Catalogo, Categoria, CodigoDuplicadoError, Producto

__all__ = ["Catalogo", "Categoria", "CodigoDuplicadoError", "Producto"]
