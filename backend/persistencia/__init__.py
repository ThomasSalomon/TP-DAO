"""Persistencia SQLite con sqlite3 y SQL parametrizado; el dominio no la importa."""

from .base_datos import BaseDatos, ruta_base_datos_predeterminada
from .catalogo_sqlite import (
    cargar_catalogo, guardar_categoria, guardar_minimo, guardar_producto, guardar_proveedor, guardar_ubicacion,
)
from .compras_sqlite import cargar_compras, guardar_compra
from .inventario_sqlite import cargar_inventario
from .logistica_sqlite import cargar_logistica, guardar_bulto, guardar_necesidad, guardar_orden


def cargar_estado(conexion):
    """Todo el estado confirmado, en el orden que exigen sus referencias.

    Devuelve (catalogo, compras, reposicion, logistica, inventario).
    """
    catalogo = cargar_catalogo(conexion)
    compras = cargar_compras(conexion, catalogo)
    reposicion, logistica = cargar_logistica(conexion, catalogo)
    inventario = cargar_inventario(conexion, catalogo, compras, logistica)
    return catalogo, compras, reposicion, logistica, inventario


__all__ = [
    "BaseDatos", "cargar_catalogo", "cargar_compras", "cargar_estado", "cargar_inventario", "cargar_logistica",
    "guardar_bulto", "guardar_categoria", "guardar_compra", "guardar_minimo", "guardar_necesidad", "guardar_orden",
    "guardar_producto", "guardar_proveedor", "guardar_ubicacion", "ruta_base_datos_predeterminada",
]
