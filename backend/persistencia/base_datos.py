"""Conexión SQLite, esquema y límites transaccionales. Sin ORM."""

import os
import sqlite3
from pathlib import Path

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
"""

# Requieren la columna bulto_id, que una base de F-02 recibe por ALTER TABLE.
ESQUEMA_MOVIMIENTOS_BULTO = """
-- Cada causa logística se aplica una sola vez por bulto, producto y ubicación.
CREATE UNIQUE INDEX IF NOT EXISTS movimientos_bulto_unico
    ON movimientos_stock (bulto_id, producto_id, causa, ubicacion_id) WHERE bulto_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS movimientos_logisticos_con_bulto BEFORE INSERT ON movimientos_stock
WHEN NEW.causa <> 'COMPRA' AND NEW.bulto_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'Un movimiento logístico debe referenciar su bulto.');
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
            columnas = [fila[1] for fila in conexion.execute("PRAGMA table_info(movimientos_stock)")]
            if "bulto_id" not in columnas:
                # CREATE TABLE IF NOT EXISTS no modifica tablas existentes: se agrega la columna de F-03.
                conexion.execute("ALTER TABLE movimientos_stock ADD COLUMN bulto_id INTEGER REFERENCES bultos (id)")
            conexion.executescript(ESQUEMA_MOVIMIENTOS_BULTO)
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
