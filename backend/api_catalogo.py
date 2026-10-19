"""Adaptador HTTP de categorías y productos. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, request, url_for
from werkzeug.exceptions import BadRequest

from .dominio import CodigoDuplicadoError

api_catalogo = Blueprint("catalogo", __name__, url_prefix="/api")


class ErrorCatalogoAPI(Exception):
    def __init__(self, estado, mensaje, campos=None):
        super().__init__(mensaje)
        self.estado = estado
        self.campos = campos or {}


@api_catalogo.errorhandler(ErrorCatalogoAPI)
def error_catalogo(error):
    cuerpo = {"code": error.estado, "message": str(error)}
    if error.campos:
        cuerpo["fields"] = error.campos
    return jsonify(error=cuerpo), error.estado


def _datos_json(campos):
    if not request.is_json:
        raise ErrorCatalogoAPI(415, "Enviá el cuerpo como application/json.")
    try:
        datos = request.get_json()
    except BadRequest:
        raise ErrorCatalogoAPI(400, "El cuerpo no contiene JSON válido.") from None
    if not isinstance(datos, dict):
        raise ErrorCatalogoAPI(400, "El cuerpo JSON debe ser un objeto.")

    errores = {}
    for campo, tipo in campos.items():
        if campo not in datos:
            errores[campo] = "Este campo es obligatorio."
        elif type(datos[campo]) is not tipo:
            errores[campo] = (
                "Debe ser texto." if tipo is str else "Debe ser un identificador entero."
            )
    for campo in datos.keys() - campos.keys():
        errores[campo] = "Este campo no está permitido."
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return datos


def _dominio(operacion, *argumentos):
    try:
        return operacion(*argumentos)
    except CodigoDuplicadoError as error:
        raise ErrorCatalogoAPI(409, str(error), {"codigo": str(error)}) from None
    except (TypeError, ValueError) as error:
        raise ErrorCatalogoAPI(400, str(error)) from None


def _catalogo():
    return current_app.extensions["catalogo"]


def _categoria(identificador):
    try:
        return _dominio(_catalogo().obtener_categoria, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(
            404, "No existe la categoría solicitada.",
            {"categoria_id": "La categoría no está registrada."},
        ) from None


def _producto(identificador):
    try:
        return _dominio(_catalogo().obtener_producto, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(404, "No existe el producto solicitado.") from None


def _categoria_json(categoria):
    return {
        "id": categoria.identificador,
        "codigo": categoria.codigo,
        "nombre": categoria.nombre,
    }


def _producto_json(producto):
    return {
        "id": producto.identificador,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "categoria": _categoria_json(producto.categoria),
        "precio": producto.precio,
        "moneda": "ARS",
    }


def _respuesta_alta(datos, endpoint):
    respuesta = jsonify(datos)
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for(endpoint, identificador=datos["id"])
    return respuesta


@api_catalogo.get("/categorias")
def listar_categorias():
    with current_app.extensions["catalogo_lock"]:
        datos = [_categoria_json(item) for item in _catalogo().listar_categorias()]
    return jsonify(categorias=datos)


@api_catalogo.post("/categorias")
def crear_categoria():
    datos = _datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        categoria = _dominio(_catalogo().crear_categoria, datos["codigo"], datos["nombre"])
        resultado = _categoria_json(categoria)
    return _respuesta_alta(resultado, "catalogo.consultar_categoria")


@api_catalogo.get("/categorias/<int:identificador>")
def consultar_categoria(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _categoria_json(_categoria(identificador))
    return jsonify(datos)


@api_catalogo.put("/categorias/<int:identificador>")
def modificar_categoria(identificador):
    datos = _datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _categoria(identificador)
        categoria = _dominio(
            _catalogo().modificar_categoria, identificador, datos["codigo"], datos["nombre"]
        )
        resultado = _categoria_json(categoria)
    return jsonify(resultado)


@api_catalogo.get("/productos")
def listar_productos():
    with current_app.extensions["catalogo_lock"]:
        datos = [_producto_json(item) for item in _catalogo().listar_productos()]
    return jsonify(productos=datos)


@api_catalogo.post("/productos")
def crear_producto():
    datos = _datos_json({"codigo": str, "nombre": str, "categoria_id": int, "precio": str})
    with current_app.extensions["catalogo_lock"]:
        categoria = _categoria(datos["categoria_id"])
        producto = _dominio(
            _catalogo().crear_producto,
            datos["codigo"], datos["nombre"], categoria, datos["precio"],
        )
        resultado = _producto_json(producto)
    return _respuesta_alta(resultado, "catalogo.consultar_producto")


@api_catalogo.get("/productos/<int:identificador>")
def consultar_producto(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _producto_json(_producto(identificador))
    return jsonify(datos)


@api_catalogo.put("/productos/<int:identificador>")
def modificar_producto(identificador):
    datos = _datos_json({"codigo": str, "nombre": str, "categoria_id": int, "precio": str})
    with current_app.extensions["catalogo_lock"]:
        _producto(identificador)
        categoria = _categoria(datos["categoria_id"])
        producto = _dominio(
            _catalogo().modificar_producto,
            identificador, datos["codigo"], datos["nombre"], categoria, datos["precio"],
        )
        resultado = _producto_json(producto)
    return jsonify(resultado)
