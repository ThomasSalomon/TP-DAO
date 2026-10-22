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
