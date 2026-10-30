"""Persistencia SQLite con sqlite3 y SQL parametrizado; el dominio no la importa."""

from .base_datos import BaseDatos, ruta_base_datos_predeterminada
from .catalogo_sqlite import (
    cargar_catalogo, guardar_categoria, guardar_minimo, guardar_producto, guardar_proveedor, guardar_ubicacion,
)
from .compras_sqlite import cargar_compras, guardar_compra
from .devoluciones_sqlite import cargar_devoluciones, guardar_devolucion
from .inventario_sqlite import cargar_inventario
from .logistica_sqlite import cargar_logistica, guardar_bulto, guardar_necesidad, guardar_orden
from .ventas_sqlite import cargar_caja, cargar_ventas, guardar_venta


def cargar_estado(conexion):
    """Todo el estado confirmado, en el orden que exigen sus referencias.

    Devuelve (catalogo, compras, reposicion, logistica, inventario, ventas, caja, devoluciones).
    """
    catalogo = cargar_catalogo(conexion)
    compras = cargar_compras(conexion, catalogo)
    reposicion, logistica = cargar_logistica(conexion, catalogo)
    ventas = cargar_ventas(conexion, catalogo)
    devoluciones = cargar_devoluciones(conexion, ventas)
    inventario = cargar_inventario(conexion, catalogo, compras, logistica, ventas, devoluciones)
    caja = cargar_caja(conexion, catalogo, ventas, devoluciones)
    return catalogo, compras, reposicion, logistica, inventario, ventas, caja, devoluciones


__all__ = [
    "BaseDatos", "cargar_caja", "cargar_catalogo", "cargar_compras", "cargar_devoluciones", "cargar_estado",
    "cargar_inventario", "cargar_logistica", "cargar_ventas", "guardar_bulto", "guardar_categoria", "guardar_compra",
    "guardar_devolucion", "guardar_minimo",
    "guardar_necesidad", "guardar_orden", "guardar_producto", "guardar_proveedor", "guardar_ubicacion",
    "guardar_venta", "ruta_base_datos_predeterminada",
]
