"""Filas SQLite de compras y sus detalles."""

from datetime import datetime

from ..dominio import Compra, RegistroCompras, importe_a_texto
from .inventario_sqlite import guardar_movimientos


def cargar_compras(conexion, catalogo):
    """Reconstruye las compras confirmadas; su efecto en stock se carga con el inventario."""
    compras = RegistroCompras()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, proveedor_id, centro_id, instante FROM compras ORDER BY id")
    for identificador, proveedor_id, centro_id, instante in cursor.fetchall():
        detalles = conexion.execute(
            """
            SELECT producto_id, cantidad, costo_unitario_centavos FROM detalles_compra
            WHERE compra_id = ? ORDER BY linea
            """,
            (identificador,),
        ).fetchall()
        lineas = [
            (catalogo.obtener_producto(producto_id), cantidad, importe_a_texto(costo))
            for producto_id, cantidad, costo in detalles
        ]
        compras.restaurar(Compra(
            identificador, catalogo.obtener_proveedor(proveedor_id), catalogo.obtener_ubicacion(centro_id),
            datetime.fromisoformat(instante), lineas,
        ))
    return compras


def guardar_compra(conexion, compra, movimientos):
    """Compra, detalles, movimientos y saldos en la misma transacción del llamador."""
    conexion.execute(
        "INSERT INTO compras (id, proveedor_id, centro_id, instante) VALUES (?, ?, ?, ?)",
        (compra.identificador, compra.proveedor.identificador, compra.centro.identificador,
         compra.instante.isoformat()),
    )
    conexion.executemany(
        """
        INSERT INTO detalles_compra (compra_id, linea, producto_id, cantidad, costo_unitario_centavos)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (compra.identificador, detalle.numero, detalle.producto.identificador, detalle.cantidad,
             detalle.costo_unitario_centavos)
            for detalle in compra.detalles
        ],
    )
    guardar_movimientos(conexion, movimientos)
