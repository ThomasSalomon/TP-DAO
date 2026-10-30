"""Filas SQLite de ventas, sus líneas y cobros, y movimientos de caja."""

from datetime import datetime

from ..dominio import Caja, MovimientoCaja, RegistroVentas, Venta, importe_a_texto
from .inventario_sqlite import guardar_movimientos


def cargar_ventas(conexion, catalogo):
    """Reconstruye las ventas confirmadas; su efecto en stock y caja se carga aparte."""
    ventas = RegistroVentas()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, local_id, instante, clave_operacion FROM ventas ORDER BY id")
    for identificador, local_id, instante, clave in cursor.fetchall():
        detalles = conexion.execute(
            """
            SELECT producto_id, cantidad, precio_unitario_centavos, costo_referencia_centavos FROM detalles_venta
            WHERE venta_id = ? ORDER BY linea
            """,
            (identificador,),
        ).fetchall()
        cobros = conexion.execute(
            "SELECT medio_pago_id, importe_centavos FROM cobros WHERE venta_id = ? ORDER BY numero",
            (identificador,),
        ).fetchall()
        ventas.restaurar(Venta(
            identificador, catalogo.obtener_ubicacion(local_id), datetime.fromisoformat(instante),
            [(catalogo.obtener_producto(producto_id), cantidad, precio, costo)
             for producto_id, cantidad, precio, costo in detalles],
            [(ventas.obtener_medio(medio_id), importe_a_texto(importe)) for medio_id, importe in cobros],
            clave,
        ))
    return ventas


def cargar_caja(conexion, catalogo, ventas, devoluciones):
    """Movimientos de caja confirmados, vinculados otra vez con su cobro o su reintegro."""
    caja = Caja()
    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT id, instante, local_id, medio_pago_id, tipo, importe_centavos, cobro_venta_id, cobro_numero,
               reintegro_devolucion_id, reintegro_numero
        FROM movimientos_caja ORDER BY id
        """
    )
    for fila in cursor.fetchall():
        identificador, instante, local_id, medio_id, tipo, importe, venta_id, numero = fila[:8]
        devolucion_id, reintegro_numero = fila[8:]
        if tipo == "INGRESO":
            documento = ventas.obtener(venta_id).cobros[numero - 1]
        else:
            documento = devoluciones.obtener(devolucion_id).reintegros[reintegro_numero - 1]
        caja.restaurar_movimiento(MovimientoCaja(
            identificador, datetime.fromisoformat(instante), catalogo.obtener_ubicacion(local_id),
            ventas.obtener_medio(medio_id), tipo, importe, documento,
        ))
    return caja


def guardar_venta(conexion, venta, movimientos, movimientos_caja):
    """Venta, líneas, cobros, salida de stock e ingresos de caja en la misma transacción del llamador."""
    conexion.execute(
        "INSERT INTO ventas (id, local_id, instante, clave_operacion) VALUES (?, ?, ?, ?)",
        (venta.identificador, venta.local.identificador, venta.instante.isoformat(), venta.clave_operacion),
    )
    conexion.executemany(
        """
        INSERT INTO detalles_venta (
            venta_id, linea, producto_id, cantidad, precio_unitario_centavos, costo_referencia_centavos
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (venta.identificador, detalle.numero, detalle.producto.identificador, detalle.cantidad,
             detalle.precio_unitario_centavos, detalle.costo_referencia_centavos)
            for detalle in venta.detalles
        ],
    )
    conexion.executemany(
        "INSERT INTO cobros (venta_id, numero, medio_pago_id, importe_centavos) VALUES (?, ?, ?, ?)",
        [
            (venta.identificador, cobro.numero, cobro.medio.identificador, cobro.importe_centavos)
            for cobro in venta.cobros
        ],
    )
    guardar_movimientos(conexion, movimientos)
    guardar_movimientos_caja(conexion, movimientos_caja)


def guardar_movimientos_caja(conexion, movimientos_caja):
    """Ingresos con su cobro y egresos con su reintegro."""
    filas = []
    for movimiento in movimientos_caja:
        cobro, reintegro = movimiento.cobro, movimiento.reintegro
        filas.append((
            movimiento.identificador, movimiento.instante.isoformat(), movimiento.local.identificador,
            movimiento.medio.identificador, movimiento.tipo, movimiento.importe_centavos,
            cobro.venta.identificador if cobro else None, cobro.numero if cobro else None,
            reintegro.devolucion.identificador if reintegro else None, reintegro.numero if reintegro else None,
        ))
    conexion.executemany(
        """
        INSERT INTO movimientos_caja (
            id, instante, local_id, medio_pago_id, tipo, importe_centavos, cobro_venta_id, cobro_numero,
            reintegro_devolucion_id, reintegro_numero
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        filas,
    )
