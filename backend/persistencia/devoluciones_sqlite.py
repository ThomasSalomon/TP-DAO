"""Filas SQLite de devoluciones, sus líneas y reintegros."""

from datetime import datetime

from ..dominio import Devolucion, RegistroDevoluciones, importe_a_texto
from .inventario_sqlite import guardar_movimientos
from .ventas_sqlite import guardar_movimientos_caja


def cargar_devoluciones(conexion, ventas):
    """Reconstruye las devoluciones confirmadas; su efecto en stock y caja se carga aparte."""
    devoluciones = RegistroDevoluciones()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, venta_id, instante, motivo, clave_operacion FROM devoluciones ORDER BY id")
    for identificador, venta_id, instante, motivo, clave in cursor.fetchall():
        venta = ventas.obtener(venta_id)
        detalles = conexion.execute(
            "SELECT venta_linea, cantidad, apto FROM detalles_devolucion WHERE devolucion_id = ? ORDER BY linea",
            (identificador,),
        ).fetchall()
        reintegros = conexion.execute(
            "SELECT medio_pago_id, importe_centavos FROM reintegros WHERE devolucion_id = ? ORDER BY numero",
            (identificador,),
        ).fetchall()
        devoluciones.restaurar(Devolucion(
            identificador, venta, datetime.fromisoformat(instante),
            [(venta.detalles[linea - 1], cantidad, bool(apto)) for linea, cantidad, apto in detalles],
            [(ventas.obtener_medio(medio_id), importe_a_texto(importe)) for medio_id, importe in reintegros],
            motivo, clave,
        ))
    return devoluciones


def guardar_devolucion(conexion, devolucion, movimientos, movimientos_caja):
    """Devolución, líneas, reintegros, ingreso de stock y egresos de caja en la misma transacción del llamador."""
    conexion.execute(
        "INSERT INTO devoluciones (id, venta_id, instante, motivo, clave_operacion) VALUES (?, ?, ?, ?, ?)",
        (devolucion.identificador, devolucion.venta.identificador, devolucion.instante.isoformat(),
         devolucion.motivo, devolucion.clave_operacion),
    )
    conexion.executemany(
        """
        INSERT INTO detalles_devolucion (devolucion_id, linea, venta_id, venta_linea, cantidad, apto)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (devolucion.identificador, detalle.numero, devolucion.venta.identificador, detalle.detalle_venta.numero,
             detalle.cantidad, int(detalle.apto))
            for detalle in devolucion.detalles
        ],
    )
    conexion.executemany(
        "INSERT INTO reintegros (devolucion_id, numero, medio_pago_id, importe_centavos) VALUES (?, ?, ?, ?)",
        [
            (devolucion.identificador, reintegro.numero, reintegro.medio.identificador, reintegro.importe_centavos)
            for reintegro in devolucion.reintegros
        ],
    )
    guardar_movimientos(conexion, movimientos)
    guardar_movimientos_caja(conexion, movimientos_caja)
