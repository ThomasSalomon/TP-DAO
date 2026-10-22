"""Errores, validación de transporte y guardado compartidos por los adaptadores HTTP."""

import sqlite3

from flask import current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from .dominio import CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError
from .persistencia import cargar_estado

# El cliente JSON usa Number: no aceptar cantidades que perderían precisión.
MAXIMO_ENTERO_JSON = 2**53 - 1


class ErrorCatalogoAPI(Exception):
    def __init__(self, estado, mensaje, campos=None):
        super().__init__(mensaje)
        self.estado = estado
        self.campos = campos or {}


def error_catalogo(error):
    cuerpo = {"code": error.estado, "message": str(error)}
    if error.campos:
        cuerpo["fields"] = error.campos
    return jsonify(error=cuerpo), error.estado


def validar_campos(datos, campos):
    """Exige exactamente los campos indicados con su tipo JSON."""
    errores = {}
    for campo, tipo in campos.items():
        if campo not in datos:
            errores[campo] = "Este campo es obligatorio."
        elif type(datos[campo]) is not tipo:
            if tipo is str:
                errores[campo] = "Debe ser texto."
            elif tipo is bool:
                errores[campo] = "Debe ser booleano."
            elif tipo is list:
                errores[campo] = "Debe ser una lista."
            elif campo in ("minimo", "cantidad"):
                errores[campo] = "Debe ser un entero."
            else:
                errores[campo] = "Debe ser un identificador entero."
    for campo in datos.keys() - campos.keys():
        errores[campo] = "Este campo no está permitido."
    return errores


def datos_json(campos):
    if not request.is_json:
        raise ErrorCatalogoAPI(415, "Enviá el cuerpo como application/json.")
    try:
        datos = request.get_json()
    except BadRequest:
        raise ErrorCatalogoAPI(400, "El cuerpo no contiene JSON válido.") from None
    if not isinstance(datos, dict):
        raise ErrorCatalogoAPI(400, "El cuerpo JSON debe ser un objeto.")

    errores = validar_campos(datos, campos)
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return datos


def operacion_dominio(operacion, *argumentos):
    """Traduce las excepciones del dominio a respuestas HTTP."""
    try:
        return operacion(*argumentos)
    except CodigoDuplicadoError as error:
        raise ErrorCatalogoAPI(409, str(error), {"codigo": str(error)}) from None
    except CentroDistribucionDuplicadoError as error:
        raise ErrorCatalogoAPI(409, str(error), {"tipo": str(error)}) from None
    except ConflictoCatalogoError as error:
        raise ErrorCatalogoAPI(409, str(error)) from None
    except (TypeError, ValueError) as error:
        raise ErrorCatalogoAPI(400, str(error)) from None


def recargar_estado():
    """Reemplaza la memoria por el último estado confirmado en la base."""
    base_datos = current_app.extensions["base_datos"]
    catalogo, compras, inventario = base_datos.consultar(cargar_estado)
    current_app.extensions["catalogo"] = catalogo
    current_app.extensions["compras"] = compras
    current_app.extensions["inventario"] = inventario


def guardar_cambio(operacion, *argumentos):
    """Confirma en SQLite el cambio ya validado por el dominio.

    Si la transacción falla, la memoria se reemplaza por el último estado confirmado;
    sólo los errores de SQLite se informan como fallo de guardado.
    """
    try:
        current_app.extensions["base_datos"].ejecutar_transaccion(operacion, *argumentos)
    except Exception as error:
        recargar_estado()
        if isinstance(error, sqlite3.Error):
            raise ErrorCatalogoAPI(
                500, "No se pudo guardar el cambio y no se aplicó. Consultá los datos antes de reintentar."
            ) from None
        raise
