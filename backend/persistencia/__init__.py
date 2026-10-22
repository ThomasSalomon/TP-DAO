"""Persistencia SQLite con sqlite3 y SQL parametrizado; el dominio no la importa."""

from .base_datos import BaseDatos, ruta_base_datos_predeterminada
from .catalogo_sqlite import (
    cargar_catalogo, guardar_categoria, guardar_minimo, guardar_producto, guardar_proveedor, guardar_ubicacion,
)
from .compras_sqlite import cargar_compras, guardar_compra


def cargar_estado(conexion):
    """Catálogo, compras e inventario confirmados, en el orden que exigen sus referencias."""
    catalogo = cargar_catalogo(conexion)
    compras, inventario = cargar_compras(conexion, catalogo)
    return catalogo, compras, inventario


__all__ = [
    "BaseDatos", "cargar_catalogo", "cargar_compras", "cargar_estado", "guardar_categoria", "guardar_compra",
    "guardar_minimo", "guardar_producto", "guardar_proveedor", "guardar_ubicacion",
    "ruta_base_datos_predeterminada",
]
