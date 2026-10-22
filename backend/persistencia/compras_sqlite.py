"""Filas SQLite de compras, existencias y movimientos de stock."""

from datetime import datetime

from ..dominio import Compra, Inventario, MovimientoStock, RegistroCompras, importe_a_texto


def cargar_compras(conexion, catalogo):
    """Reconstruye compras, saldos y movimientos ya confirmados, sin repetir sus efectos."""
    compras = RegistroCompras()
    inventario = Inventario()
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

    cursor.execute("SELECT ubicacion_id, producto_id, condicion, cantidad FROM existencias")
    for ubicacion_id, producto_id, condicion, cantidad in cursor.fetchall():
        inventario.restaurar_saldo(
            catalogo.obtener_ubicacion(ubicacion_id), catalogo.obtener_producto(producto_id), condicion, cantidad
        )

    cursor.execute(
        """
        SELECT id, instante, ubicacion_id, producto_id, cantidad, condicion_origen, condicion_destino, causa,
               compra_id, compra_linea
        FROM movimientos_stock ORDER BY id
        """
    )
    for fila in cursor.fetchall():
        identificador, instante, ubicacion_id, producto_id, cantidad, origen, destino, causa, compra_id, linea = fila
        detalle = compras.obtener(compra_id).detalles[linea - 1]
        inventario.restaurar_movimiento(MovimientoStock(
            identificador, datetime.fromisoformat(instante), catalogo.obtener_ubicacion(ubicacion_id),
            catalogo.obtener_producto(producto_id), cantidad, origen, destino, causa, detalle,
        ))
    return compras, inventario


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
    for movimiento in movimientos:
        conexion.execute(
            """
            INSERT INTO movimientos_stock (
                id, instante, ubicacion_id, producto_id, cantidad, condicion_origen, condicion_destino,
                causa, compra_id, compra_linea
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movimiento.identificador, movimiento.instante.isoformat(), movimiento.ubicacion.identificador,
                movimiento.producto.identificador, movimiento.cantidad, movimiento.condicion_origen,
                movimiento.condicion_destino, movimiento.causa, movimiento.documento.compra.identificador,
                movimiento.documento.numero,
            ),
        )
        # El saldo se actualiza en la base a partir del movimiento, no se copia de la memoria.
        conexion.execute(
            """
            INSERT INTO existencias (ubicacion_id, producto_id, condicion, cantidad) VALUES (?, ?, ?, ?)
            ON CONFLICT (ubicacion_id, producto_id, condicion) DO UPDATE SET cantidad = cantidad + excluded.cantidad
            """,
            (movimiento.ubicacion.identificador, movimiento.producto.identificador,
             movimiento.condicion_destino, movimiento.cantidad),
        )
