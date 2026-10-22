"""Filas SQLite de necesidades, órdenes de reposición, bultos, eventos y remitos."""

import sqlite3
from datetime import datetime

from ..dominio import NecesidadReposicion, OrdenReposicion, RegistroLogistica, RegistroReposicion
from .inventario_sqlite import guardar_movimientos


def _instante(texto):
    return None if texto is None else datetime.fromisoformat(texto)


def cargar_logistica(conexion, catalogo):
    """Reconstruye necesidades, órdenes, bultos con su historial y remitos, sin repetir efectos."""
    reposicion = RegistroReposicion()
    logistica = RegistroLogistica()
    cursor = conexion.cursor()

    cursor.execute("SELECT id, local_id, producto_id, cantidad, instante FROM necesidades ORDER BY id")
    for identificador, local_id, producto_id, cantidad, instante in cursor.fetchall():
        reposicion.restaurar_necesidad(NecesidadReposicion(
            identificador, catalogo.obtener_ubicacion(local_id), catalogo.obtener_producto(producto_id),
            cantidad, _instante(instante),
        ))

    cursor.execute("SELECT id, centro_id, destino_id, instante FROM ordenes_reposicion ORDER BY id")
    for identificador, centro_id, destino_id, instante in cursor.fetchall():
        filas = conexion.execute("SELECT id FROM necesidades WHERE orden_id = ? ORDER BY id", (identificador,))
        necesidades = [reposicion.obtener_necesidad(necesidad_id) for (necesidad_id,) in filas.fetchall()]
        reposicion.restaurar_orden(OrdenReposicion(
            identificador, catalogo.obtener_ubicacion(centro_id), catalogo.obtener_ubicacion(destino_id),
            _instante(instante), necesidades,
        ))

    cursor.execute("SELECT id, orden_id, precinto FROM bultos ORDER BY id")
    for identificador, orden_id, precinto in cursor.fetchall():
        detalles = conexion.execute(
            """
            SELECT producto_id, cantidad, costo_referencia_centavos FROM detalles_bulto
            WHERE bulto_id = ? ORDER BY rowid
            """,
            (identificador,),
        ).fetchall()
        eventos = conexion.execute(
            """
            SELECT estado_anterior, estado_nuevo, instante, motivo FROM eventos_bulto
            WHERE bulto_id = ? ORDER BY secuencia
            """,
            (identificador,),
        ).fetchall()
        logistica.restaurar_bulto(
            identificador, reposicion.obtener_orden(orden_id),
            [(catalogo.obtener_producto(producto_id), cantidad, costo) for producto_id, cantidad, costo in detalles],
            [(anterior, nuevo, _instante(instante), motivo) for anterior, nuevo, instante, motivo in eventos],
            precinto,
        )

    cursor.execute("SELECT id, bulto_id, instante, estado, instante_cierre FROM remitos ORDER BY id")
    for identificador, bulto_id, instante, estado, cierre in cursor.fetchall():
        logistica.restaurar_remito(
            identificador, logistica.obtener_bulto(bulto_id), _instante(instante), estado, _instante(cierre)
        )
    return reposicion, logistica


def guardar_necesidad(conexion, necesidad):
    conexion.execute(
        "INSERT INTO necesidades (id, local_id, producto_id, cantidad, instante) VALUES (?, ?, ?, ?, ?)",
        (necesidad.identificador, necesidad.local.identificador, necesidad.producto.identificador,
         necesidad.cantidad, necesidad.instante.isoformat()),
    )


def guardar_orden(conexion, orden):
    """La orden y la consolidación de sus necesidades, que sólo pueden pasar de pendientes a consolidadas."""
    conexion.execute(
        "INSERT INTO ordenes_reposicion (id, centro_id, destino_id, instante) VALUES (?, ?, ?, ?)",
        (orden.identificador, orden.centro.identificador, orden.destino.identificador, orden.instante.isoformat()),
    )
    for necesidad in orden.necesidades:
        cursor = conexion.execute(
            "UPDATE necesidades SET orden_id = ? WHERE id = ? AND orden_id IS NULL",
            (orden.identificador, necesidad.identificador),
        )
        if cursor.rowcount != 1:
            raise sqlite3.IntegrityError(f"La necesidad {necesidad.identificador} ya estaba consolidada.")


def guardar_bulto(conexion, bulto, movimientos):
    """Estado actual, contenido, eventos nuevos, remito y movimientos de una operación del bulto."""
    precinto_clave = None if bulto.precinto is None else bulto.precinto.casefold()
    conexion.execute(
        """
        INSERT INTO bultos (id, orden_id, estado, precinto, precinto_clave) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            estado = excluded.estado, precinto = excluded.precinto, precinto_clave = excluded.precinto_clave
        """,
        (bulto.identificador, bulto.orden.identificador, bulto.estado, bulto.precinto, precinto_clave),
    )
    conexion.executemany(
        """
        INSERT INTO detalles_bulto (bulto_id, producto_id, cantidad, costo_referencia_centavos) VALUES (?, ?, ?, ?)
        ON CONFLICT (bulto_id, producto_id) DO NOTHING
        """,
        [
            (bulto.identificador, detalle.producto.identificador, detalle.cantidad, detalle.costo_referencia_centavos)
            for detalle in bulto.detalles
        ],
    )
    (guardados,) = conexion.execute(
        "SELECT COUNT(*) FROM eventos_bulto WHERE bulto_id = ?", (bulto.identificador,)
    ).fetchone()
    conexion.executemany(
        """
        INSERT INTO eventos_bulto (bulto_id, secuencia, estado_anterior, estado_nuevo, instante, motivo)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (bulto.identificador, evento.secuencia, evento.estado_anterior, evento.estado_nuevo,
             evento.instante.isoformat(), evento.motivo)
            for evento in bulto.eventos[guardados:]
        ],
    )
    remito = bulto.remito
    if remito is not None:
        cierre = None if remito.instante_cierre is None else remito.instante_cierre.isoformat()
        conexion.execute(
            """
            INSERT INTO remitos (id, bulto_id, instante, estado, instante_cierre) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET estado = excluded.estado, instante_cierre = excluded.instante_cierre
            """,
            (remito.identificador, bulto.identificador, remito.instante.isoformat(), remito.estado, cierre),
        )
    guardar_movimientos(conexion, movimientos)
