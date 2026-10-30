"""Conexión SQLite, esquema y límites transaccionales. Sin ORM."""

import os
import sqlite3
from pathlib import Path

from ..dominio import MEDIOS_PAGO

ESQUEMA = """
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    activo INTEGER NOT NULL CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias (id),
    precio_centavos INTEGER NOT NULL CHECK (precio_centavos > 0),
    activo INTEGER NOT NULL CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    activo INTEGER NOT NULL CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ubicaciones (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('LOCAL', 'CD')),
    activo INTEGER NOT NULL CHECK (activo IN (0, 1))
);

CREATE UNIQUE INDEX IF NOT EXISTS ubicaciones_un_solo_cd ON ubicaciones (tipo) WHERE tipo = 'CD';

CREATE TABLE IF NOT EXISTS minimos (
    ubicacion_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    minimo INTEGER NOT NULL CHECK (minimo >= 0),
    PRIMARY KEY (ubicacion_id, producto_id)
);

CREATE TABLE IF NOT EXISTS codigos_reservados (
    entidad TEXT NOT NULL CHECK (entidad IN ('categoria', 'producto', 'proveedor', 'ubicacion')),
    clave TEXT NOT NULL,
    codigo TEXT NOT NULL,
    entidad_id INTEGER NOT NULL,
    PRIMARY KEY (entidad, clave)
);

CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores (id),
    centro_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    instante TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detalles_compra (
    compra_id INTEGER NOT NULL REFERENCES compras (id),
    linea INTEGER NOT NULL CHECK (linea > 0),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    costo_unitario_centavos INTEGER NOT NULL CHECK (costo_unitario_centavos > 0),
    PRIMARY KEY (compra_id, linea),
    UNIQUE (compra_id, producto_id)
);

CREATE TABLE IF NOT EXISTS existencias (
    ubicacion_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    condicion TEXT NOT NULL CHECK (
        condicion IN ('DISPONIBLE', 'RESERVADO', 'EN_TRANSITO', 'PENDIENTE', 'RECHAZADO', 'BLOQUEADO')
    ),
    cantidad INTEGER NOT NULL CHECK (cantidad >= 0),
    PRIMARY KEY (ubicacion_id, producto_id, condicion)
);

CREATE TABLE IF NOT EXISTS movimientos_stock (
    id INTEGER PRIMARY KEY,
    instante TEXT NOT NULL,
    ubicacion_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    condicion_origen TEXT CHECK (
        condicion_origen IN ('DISPONIBLE', 'RESERVADO', 'EN_TRANSITO', 'PENDIENTE', 'RECHAZADO', 'BLOQUEADO')
    ),
    condicion_destino TEXT CHECK (
        condicion_destino IN ('DISPONIBLE', 'RESERVADO', 'EN_TRANSITO', 'PENDIENTE', 'RECHAZADO', 'BLOQUEADO')
    ),
    causa TEXT NOT NULL,
    compra_id INTEGER,
    compra_linea INTEGER,
    FOREIGN KEY (compra_id, compra_linea) REFERENCES detalles_compra (compra_id, linea),
    -- Cada línea de compra ingresa una sola vez.
    UNIQUE (compra_id, compra_linea),
    CHECK (condicion_origen IS NOT NULL OR condicion_destino IS NOT NULL),
    CHECK (causa <> 'COMPRA' OR (compra_id IS NOT NULL AND compra_linea IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS necesidades (
    id INTEGER PRIMARY KEY,
    local_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    instante TEXT NOT NULL,
    -- NULL mientras está pendiente; los detalles de la orden se derivan de sus necesidades.
    orden_id INTEGER REFERENCES ordenes_reposicion (id)
);

CREATE TABLE IF NOT EXISTS ordenes_reposicion (
    id INTEGER PRIMARY KEY,
    centro_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    destino_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    instante TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bultos (
    id INTEGER PRIMARY KEY,
    orden_id INTEGER NOT NULL REFERENCES ordenes_reposicion (id),
    estado TEXT NOT NULL CHECK (
        estado IN ('PREPARADO', 'PRECINTADO', 'EN_TRANSITO', 'RECIBIDO', 'VERIFICADO', 'RECHAZADO', 'ANULADO')
    ),
    precinto TEXT,
    -- Clave casefold() del precinto: un sello físico nunca se reutiliza.
    precinto_clave TEXT UNIQUE,
    CHECK ((precinto IS NULL) = (precinto_clave IS NULL))
);

CREATE TABLE IF NOT EXISTS detalles_bulto (
    bulto_id INTEGER NOT NULL REFERENCES bultos (id),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    costo_referencia_centavos INTEGER CHECK (costo_referencia_centavos > 0),
    PRIMARY KEY (bulto_id, producto_id)
);

CREATE TABLE IF NOT EXISTS eventos_bulto (
    bulto_id INTEGER NOT NULL REFERENCES bultos (id),
    secuencia INTEGER NOT NULL CHECK (secuencia > 0),
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    instante TEXT NOT NULL,
    motivo TEXT NOT NULL,
    PRIMARY KEY (bulto_id, secuencia)
);

-- Trazabilidad inmutable (E4): los eventos sólo se insertan.
CREATE TRIGGER IF NOT EXISTS eventos_bulto_sin_modificacion BEFORE UPDATE ON eventos_bulto
BEGIN
    SELECT RAISE(ABORT, 'El historial de estados del bulto no se modifica.');
END;

CREATE TRIGGER IF NOT EXISTS eventos_bulto_sin_borrado BEFORE DELETE ON eventos_bulto
BEGIN
    SELECT RAISE(ABORT, 'El historial de estados del bulto no se borra.');
END;

CREATE TABLE IF NOT EXISTS remitos (
    id INTEGER PRIMARY KEY,
    bulto_id INTEGER NOT NULL UNIQUE REFERENCES bultos (id),
    instante TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('EMITIDO', 'VERIFICADO', 'RECHAZADO')),
    instante_cierre TEXT,
    CHECK ((estado = 'EMITIDO') = (instante_cierre IS NULL))
);

CREATE TABLE IF NOT EXISTS medios_pago (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL
);

-- El comprobante no tiene tabla: su número se deriva del ID de la venta, uno por venta.
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY,
    local_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    instante TEXT NOT NULL,
    -- Un envío repetido del mismo borrador no registra otra venta (RB-10).
    clave_operacion TEXT NOT NULL UNIQUE CHECK (length(clave_operacion) BETWEEN 1 AND 64)
);

CREATE TABLE IF NOT EXISTS detalles_venta (
    venta_id INTEGER NOT NULL REFERENCES ventas (id),
    linea INTEGER NOT NULL CHECK (linea > 0),
    producto_id INTEGER NOT NULL REFERENCES productos (id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario_centavos INTEGER NOT NULL CHECK (precio_unitario_centavos > 0),
    -- NULL si el producto no tenía compras: el costo falta, no es cero.
    costo_referencia_centavos INTEGER CHECK (costo_referencia_centavos > 0),
    PRIMARY KEY (venta_id, linea),
    UNIQUE (venta_id, producto_id)
);

CREATE TABLE IF NOT EXISTS cobros (
    venta_id INTEGER NOT NULL REFERENCES ventas (id),
    numero INTEGER NOT NULL CHECK (numero > 0),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago (id),
    importe_centavos INTEGER NOT NULL CHECK (importe_centavos > 0),
    PRIMARY KEY (venta_id, numero),
    UNIQUE (venta_id, medio_pago_id)
);

-- El local de la devolución es el de su venta; el importe de cada línea se deriva del precio histórico.
CREATE TABLE IF NOT EXISTS devoluciones (
    id INTEGER PRIMARY KEY,
    venta_id INTEGER NOT NULL REFERENCES ventas (id),
    instante TEXT NOT NULL,
    motivo TEXT NOT NULL CHECK (length(motivo) BETWEEN 1 AND 200),
    clave_operacion TEXT NOT NULL UNIQUE CHECK (length(clave_operacion) BETWEEN 1 AND 64)
);

CREATE TABLE IF NOT EXISTS detalles_devolucion (
    devolucion_id INTEGER NOT NULL REFERENCES devoluciones (id),
    linea INTEGER NOT NULL CHECK (linea > 0),
    venta_id INTEGER NOT NULL,
    venta_linea INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    apto INTEGER NOT NULL CHECK (apto IN (0, 1)),
    PRIMARY KEY (devolucion_id, linea),
    UNIQUE (devolucion_id, venta_linea),
    FOREIGN KEY (venta_id, venta_linea) REFERENCES detalles_venta (venta_id, linea)
);

CREATE TRIGGER IF NOT EXISTS detalles_devolucion_de_su_venta BEFORE INSERT ON detalles_devolucion
WHEN NEW.venta_id IS NOT (SELECT venta_id FROM devoluciones WHERE id = NEW.devolucion_id)
BEGIN
    SELECT RAISE(ABORT, 'La línea devuelta debe pertenecer a la venta de la devolución.');
END;

-- Lo devuelto acumulado de una línea no supera lo vendido (RB-11).
CREATE TRIGGER IF NOT EXISTS detalles_devolucion_sin_exceso BEFORE INSERT ON detalles_devolucion
WHEN NEW.cantidad + (
    SELECT COALESCE(SUM(cantidad), 0) FROM detalles_devolucion
    WHERE venta_id = NEW.venta_id AND venta_linea = NEW.venta_linea
) > (SELECT cantidad FROM detalles_venta WHERE venta_id = NEW.venta_id AND linea = NEW.venta_linea)
BEGIN
    SELECT RAISE(ABORT, 'No se puede devolver más de lo vendido en la línea.');
END;

CREATE TABLE IF NOT EXISTS reintegros (
    devolucion_id INTEGER NOT NULL REFERENCES devoluciones (id),
    numero INTEGER NOT NULL CHECK (numero > 0),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago (id),
    importe_centavos INTEGER NOT NULL CHECK (importe_centavos > 0),
    PRIMARY KEY (devolucion_id, numero),
    UNIQUE (devolucion_id, medio_pago_id)
);

CREATE TABLE IF NOT EXISTS movimientos_caja (
    id INTEGER PRIMARY KEY,
    instante TEXT NOT NULL,
    local_id INTEGER NOT NULL REFERENCES ubicaciones (id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago (id),
    -- EGRESO es un reintegro: sus columnas se agregan por ALTER TABLE (COLUMNAS_CAJA).
    tipo TEXT NOT NULL CHECK (tipo IN ('INGRESO', 'EGRESO')),
    importe_centavos INTEGER NOT NULL CHECK (importe_centavos > 0),
    cobro_venta_id INTEGER,
    cobro_numero INTEGER,
    FOREIGN KEY (cobro_venta_id, cobro_numero) REFERENCES cobros (venta_id, numero),
    -- Cada cobro ingresa a caja una sola vez.
    UNIQUE (cobro_venta_id, cobro_numero),
    CHECK ((tipo = 'INGRESO') = (cobro_venta_id IS NOT NULL AND cobro_numero IS NOT NULL))
);

CREATE TRIGGER IF NOT EXISTS movimientos_caja_sin_modificacion BEFORE UPDATE ON movimientos_caja
BEGIN
    SELECT RAISE(ABORT, 'Los movimientos de caja no se modifican.');
END;

CREATE TRIGGER IF NOT EXISTS movimientos_caja_sin_borrado BEFORE DELETE ON movimientos_caja
BEGIN
    SELECT RAISE(ABORT, 'Los movimientos de caja no se borran.');
END;
"""

# Columnas que una base anterior recibe por ALTER TABLE, porque CREATE TABLE IF NOT EXISTS
# no modifica tablas existentes: bulto_id desde F-03, la línea de venta desde F-04 y la línea
# de devolución y el reintegro desde F-05.
COLUMNAS_MOVIMIENTOS = (
    ("bulto_id", "INTEGER REFERENCES bultos (id)"),
    ("venta_id", "INTEGER REFERENCES ventas (id)"),
    ("venta_linea", "INTEGER"),
    ("devolucion_id", "INTEGER REFERENCES devoluciones (id)"),
    ("devolucion_linea", "INTEGER"),
)
COLUMNAS_CAJA = (
    ("reintegro_devolucion_id", "INTEGER REFERENCES devoluciones (id)"),
    ("reintegro_numero", "INTEGER"),
)

# Requieren las columnas anteriores.
ESQUEMA_MOVIMIENTOS_DOCUMENTO = """
-- Cada causa logística se aplica una sola vez por bulto, producto y ubicación.
CREATE UNIQUE INDEX IF NOT EXISTS movimientos_bulto_unico
    ON movimientos_stock (bulto_id, producto_id, causa, ubicacion_id) WHERE bulto_id IS NOT NULL;

-- F-03 y F-04 crearon este trigger con menos causas: se reemplaza para que ventas y devoluciones no exijan bulto.
DROP TRIGGER IF EXISTS movimientos_logisticos_con_bulto;
CREATE TRIGGER movimientos_logisticos_con_bulto BEFORE INSERT ON movimientos_stock
WHEN NEW.causa NOT IN ('COMPRA', 'VENTA', 'DEVOLUCION') AND NEW.bulto_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'Un movimiento logístico debe referenciar su bulto.');
END;

-- Cada línea de venta descuenta stock una sola vez.
CREATE UNIQUE INDEX IF NOT EXISTS movimientos_venta_unico
    ON movimientos_stock (venta_id, venta_linea) WHERE venta_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS movimientos_venta_con_linea BEFORE INSERT ON movimientos_stock
WHEN NEW.causa = 'VENTA' AND NOT EXISTS (
    SELECT 1 FROM detalles_venta WHERE venta_id = NEW.venta_id AND linea = NEW.venta_linea
)
BEGIN
    SELECT RAISE(ABORT, 'Un movimiento de venta debe referenciar su línea.');
END;

-- Cada línea devuelta ingresa una sola vez, en la condición que corresponde a su aptitud (DN-07).
CREATE UNIQUE INDEX IF NOT EXISTS movimientos_devolucion_unico
    ON movimientos_stock (devolucion_id, devolucion_linea) WHERE devolucion_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS movimientos_devolucion_con_linea BEFORE INSERT ON movimientos_stock
WHEN NEW.causa = 'DEVOLUCION' AND NOT EXISTS (
    SELECT 1 FROM detalles_devolucion
    WHERE devolucion_id = NEW.devolucion_id AND linea = NEW.devolucion_linea AND NEW.condicion_origen IS NULL
      AND NEW.condicion_destino = CASE apto WHEN 1 THEN 'DISPONIBLE' ELSE 'BLOQUEADO' END
)
BEGIN
    SELECT RAISE(ABORT, 'Un movimiento de devolución debe ingresar su línea según la aptitud.');
END;

-- Cada reintegro egresa de caja una sola vez; un egreso exige su reintegro y un ingreso no lo admite.
CREATE UNIQUE INDEX IF NOT EXISTS movimientos_caja_reintegro_unico
    ON movimientos_caja (reintegro_devolucion_id, reintegro_numero) WHERE reintegro_devolucion_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS movimientos_caja_egreso_con_reintegro BEFORE INSERT ON movimientos_caja
WHEN (NEW.tipo = 'EGRESO' AND NOT EXISTS (
    SELECT 1 FROM reintegros WHERE devolucion_id = NEW.reintegro_devolucion_id AND numero = NEW.reintegro_numero
)) OR (NEW.tipo <> 'EGRESO' AND (NEW.reintegro_devolucion_id IS NOT NULL OR NEW.reintegro_numero IS NOT NULL))
BEGIN
    SELECT RAISE(ABORT, 'Un egreso de caja debe referenciar su reintegro y un ingreso, sólo su cobro.');
END;
"""


def ruta_base_datos_predeterminada():
    """TP_DAO_DB si está definida; si no, una ruta local fuera de la carpeta sincronizada."""
    ruta = os.environ.get("TP_DAO_DB")
    if ruta:
        return Path(ruta)
    carpeta = os.environ.get("LOCALAPPDATA")
    if carpeta:
        return Path(carpeta) / "TP-DAO" / "tp_dao.db"
    return Path.home() / ".tp-dao" / "tp_dao.db"


class BaseDatos:
    """Abre una conexión por operación y decide cuándo confirmar o revertir."""

    def __init__(self, ruta):
        self._ruta = Path(ruta)

    @property
    def ruta(self):
        return self._ruta

    def conectar(self):
        conexion = sqlite3.connect(self._ruta)
        # SQLite no controla claves foráneas si no se activa en cada conexión.
        conexion.execute("PRAGMA foreign_keys = ON")
        return conexion

    def inicializar(self):
        """Crea la carpeta y las tablas faltantes; no borra datos existentes."""
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        conexion = self.conectar()
        try:
            conexion.executescript(ESQUEMA)
            for tabla, agregadas in (("movimientos_stock", COLUMNAS_MOVIMIENTOS), ("movimientos_caja", COLUMNAS_CAJA)):
                columnas = [fila[1] for fila in conexion.execute(f"PRAGMA table_info({tabla})")]
                for nombre, definicion in agregadas:
                    if nombre not in columnas:
                        conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}")
            conexion.executescript(ESQUEMA_MOVIMIENTOS_DOCUMENTO)
            # Medios fijos de DN-05: se agregan si faltan, sin modificar los existentes.
            conexion.executemany("INSERT OR IGNORE INTO medios_pago (id, codigo, nombre) VALUES (?, ?, ?)", MEDIOS_PAGO)
            conexion.commit()
        finally:
            conexion.close()

    def consultar(self, operacion, *argumentos):
        """Ejecuta una lectura; no confirma porque no modifica datos."""
        conexion = self.conectar()
        try:
            return operacion(conexion, *argumentos)
        finally:
            conexion.close()

    def ejecutar_transaccion(self, operacion, *argumentos):
        """Confirma todos los cambios de la operación o ninguno."""
        conexion = self.conectar()
        try:
            resultado = operacion(conexion, *argumentos)
            conexion.commit()
            return resultado
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
