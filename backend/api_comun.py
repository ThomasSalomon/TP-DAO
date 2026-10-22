"""Errores, validación de transporte y guardado compartidos por los adaptadores HTTP."""

import sqlite3

from flask import current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from .dominio import (
    CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError, ConflictoOperacionError,
)
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
    except (ConflictoCatalogoError, ConflictoOperacionError) as error:
        raise ErrorCatalogoAPI(409, str(error)) from None
    except (TypeError, ValueError) as error:
        raise ErrorCatalogoAPI(400, str(error)) from None


def recargar_estado():
    """Reemplaza la memoria por el último estado confirmado en la base."""
    base_datos = current_app.extensions["base_datos"]
    asignar_estado(current_app, base_datos.consultar(cargar_estado))


def asignar_estado(app, estado):
    """Publica en la aplicación los registros devueltos por cargar_estado."""
    nombres = ("catalogo", "compras", "reposicion", "logistica", "inventario", "ventas", "caja")
    for nombre, registro in zip(nombres, estado):
        app.extensions[nombre] = registro


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


def referencia_json(entidad):
    return {"id": entidad.identificador, "codigo": entidad.codigo, "nombre": entidad.nombre, "activo": entidad.activo}


def ubicacion_json(ubicacion):
    return {**referencia_json(ubicacion), "tipo": ubicacion.tipo}


def movimiento_json(movimiento):
    """Movimiento con su documento de origen: línea de compra, bulto o línea de venta."""
    compra = movimiento.causa == "COMPRA"
    venta = movimiento.causa == "VENTA"
    logistico = not compra and not venta
    documento = movimiento.documento
    return {
        "id": movimiento.identificador,
        "instante": movimiento.instante.isoformat(),
        "producto": referencia_json(movimiento.producto),
        "cantidad": movimiento.cantidad,
        "condicion_origen": movimiento.condicion_origen,
        "condicion_destino": movimiento.condicion_destino,
        "causa": movimiento.causa,
        "compra_id": documento.compra.identificador if compra else None,
        # Número de línea de la compra o de la venta; los bultos no numeran líneas.
        "linea": None if logistico else documento.numero,
        "bulto_id": documento.bulto.identificador if logistico else None,
        "bulto_codigo": documento.bulto.codigo if logistico else None,
        "venta_id": documento.venta.identificador if venta else None,
        "comprobante": documento.venta.comprobante.numero if venta else None,
    }


def lineas_validadas(lineas, campos):
    """Valida el formato de cada línea; el contenido lo valida el dominio."""
    errores = {}
    for numero, linea in enumerate(lineas, start=1):
        if not isinstance(linea, dict):
            errores[f"lineas.{numero}"] = "Cada línea debe ser un objeto."
            continue
        encontrados = validar_campos(linea, campos)
        if not encontrados and linea["cantidad"] > MAXIMO_ENTERO_JSON:
            encontrados["cantidad"] = f"El máximo admitido por HTTP es {MAXIMO_ENTERO_JSON}."
        errores.update({f"lineas.{numero}.{campo}": mensaje for campo, mensaje in encontrados.items()})
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return lineas


def obtener(operacion, identificador, mensaje, campo=None):
    """Busca un registro por identificador; inexistente es 404, con el campo si vino en el cuerpo."""
    try:
        return operacion_dominio(operacion, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(404, mensaje, {campo: mensaje} if campo else None) from None
