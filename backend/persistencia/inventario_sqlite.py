"""Filas SQLite de existencias y movimientos de stock."""

import sqlite3
from datetime import datetime

from ..dominio import Inventario, MovimientoStock


def cargar_inventario(conexion, catalogo, compras, logistica):
    """Saldos y movimientos confirmados; cada movimiento vuelve a vincular su documento."""
    inventario = Inventario()
    cursor = conexion.cursor()
    cursor.execute("SELECT ubicacion_id, producto_id, condicion, cantidad FROM existencias")
    for ubicacion_id, producto_id, condicion, cantidad in cursor.fetchall():
        inventario.restaurar_saldo(
            catalogo.obtener_ubicacion(ubicacion_id), catalogo.obtener_producto(producto_id), condicion, cantidad
        )

    cursor.execute(
        """
        SELECT id, instante, ubicacion_id, producto_id, cantidad, condicion_origen, condicion_destino, causa,
               compra_id, compra_linea, bulto_id
        FROM movimientos_stock ORDER BY id
        """
    )
    for fila in cursor.fetchall():
        identificador, instante, ubicacion_id, producto_id, cantidad, origen, destino, causa = fila[:8]
        compra_id, linea, bulto_id = fila[8:]
        producto = catalogo.obtener_producto(producto_id)
        if causa == "COMPRA":
            documento = compras.obtener(compra_id).detalles[linea - 1]
        else:
            documento = next(
                detalle for detalle in logistica.obtener_bulto(bulto_id).detalles if detalle.producto is producto
            )
        inventario.restaurar_movimiento(MovimientoStock(
            identificador, datetime.fromisoformat(instante), catalogo.obtener_ubicacion(ubicacion_id),
            producto, cantidad, origen, destino, causa, documento,
        ))
    return inventario


def guardar_movimientos(conexion, movimientos):
    """Inserta los movimientos y actualiza en SQL los saldos que afectan."""
    for movimiento in movimientos:
        documento = movimiento.documento
        compra_id = linea = bulto_id = None
        if movimiento.causa == "COMPRA":
            compra_id, linea = documento.compra.identificador, documento.numero
        else:
            bulto_id = documento.bulto.identificador
        conexion.execute(
            """
            INSERT INTO movimientos_stock (
                id, instante, ubicacion_id, producto_id, cantidad, condicion_origen, condicion_destino,
                causa, compra_id, compra_linea, bulto_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movimiento.identificador, movimiento.instante.isoformat(), movimiento.ubicacion.identificador,
                movimiento.producto.identificador, movimiento.cantidad, movimiento.condicion_origen,
                movimiento.condicion_destino, movimiento.causa, compra_id, linea, bulto_id,
            ),
        )
        clave = (movimiento.ubicacion.identificador, movimiento.producto.identificador)
        # Los saldos se actualizan en la base a partir del movimiento, no se copian de la memoria.
        if movimiento.condicion_origen is not None:
            cursor = conexion.execute(
                """
                UPDATE existencias SET cantidad = cantidad - ?
                WHERE ubicacion_id = ? AND producto_id = ? AND condicion = ?
                """,
                (movimiento.cantidad, *clave, movimiento.condicion_origen),
            )
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError("El movimiento descuenta un saldo inexistente.")
        if movimiento.condicion_destino is not None:
            conexion.execute(
                """
                INSERT INTO existencias (ubicacion_id, producto_id, condicion, cantidad) VALUES (?, ?, ?, ?)
                ON CONFLICT (ubicacion_id, producto_id, condicion)
                DO UPDATE SET cantidad = cantidad + excluded.cantidad
                """,
                (*clave, movimiento.condicion_destino, movimiento.cantidad),
            )
