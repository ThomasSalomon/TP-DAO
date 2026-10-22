"""Persistencia SQLite con sqlite3 y SQL parametrizado; el dominio no la importa."""

from .base_datos import BaseDatos, ruta_base_datos_predeterminada
from .catalogo_sqlite import (
    cargar_catalogo, guardar_categoria, guardar_minimo, guardar_producto, guardar_proveedor, guardar_ubicacion,
)

__all__ = [
    "BaseDatos", "cargar_catalogo", "guardar_categoria", "guardar_minimo", "guardar_producto",
    "guardar_proveedor", "guardar_ubicacion", "ruta_base_datos_predeterminada",
]
