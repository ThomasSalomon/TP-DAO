"""Adaptador HTTP del catálogo. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, request, url_for
from werkzeug.exceptions import BadRequest

from .dominio import CentroDistribucionDuplicadoError, CodigoDuplicadoError, ConflictoCatalogoError

api_catalogo = Blueprint("catalogo", __name__, url_prefix="/api")
# El cliente JSON usa Number: no aceptar cantidades que perderían precisión.
MAXIMO_ENTERO_JSON = 2**53 - 1


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
            if tipo is str:
                errores[campo] = "Debe ser texto."
            elif tipo is bool:
                errores[campo] = "Debe ser booleano."
            else:
                errores[campo] = "Debe ser un entero." if campo == "minimo" else "Debe ser un identificador entero."
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
    except CentroDistribucionDuplicadoError as error:
        raise ErrorCatalogoAPI(409, str(error), {"tipo": str(error)}) from None
    except ConflictoCatalogoError as error:
        raise ErrorCatalogoAPI(409, str(error)) from None
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
        "activo": categoria.activo,
    }


def _proveedor(identificador):
    try:
        return _dominio(_catalogo().obtener_proveedor, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(404, "No existe el proveedor solicitado.") from None


def _proveedor_json(proveedor):
    return {
        "id": proveedor.identificador,
        "codigo": proveedor.codigo,
        "nombre": proveedor.nombre,
        "activo": proveedor.activo,
    }


def _producto_json(producto):
    return {
        "id": producto.identificador,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "activo": producto.activo,
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
        registros = _dominio(_catalogo().listar_categorias, _estado_listado())
        datos = [_categoria_json(item) for item in registros]
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
        registros = _dominio(_catalogo().listar_productos, _estado_listado())
        datos = [_producto_json(item) for item in registros]
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


@api_catalogo.get("/proveedores")
def listar_proveedores():
    with current_app.extensions["catalogo_lock"]:
        registros = _dominio(_catalogo().listar_proveedores, _estado_listado())
        datos = [_proveedor_json(item) for item in registros]
    return jsonify(proveedores=datos)


@api_catalogo.post("/proveedores")
def crear_proveedor():
    datos = _datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        proveedor = _dominio(_catalogo().crear_proveedor, datos["codigo"], datos["nombre"])
        resultado = _proveedor_json(proveedor)
    return _respuesta_alta(resultado, "catalogo.consultar_proveedor")


@api_catalogo.get("/proveedores/<int:identificador>")
def consultar_proveedor(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _proveedor_json(_proveedor(identificador))
    return jsonify(datos)


@api_catalogo.put("/proveedores/<int:identificador>")
def modificar_proveedor(identificador):
    datos = _datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _proveedor(identificador)
        proveedor = _dominio(
            _catalogo().modificar_proveedor, identificador, datos["codigo"], datos["nombre"]
        )
        resultado = _proveedor_json(proveedor)
    return jsonify(resultado)


def _ubicacion(identificador):
    try:
        return _dominio(_catalogo().obtener_ubicacion, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(404, "No existe la ubicación solicitada.") from None


def _ubicacion_json(ubicacion):
    return {
        "id": ubicacion.identificador,
        "codigo": ubicacion.codigo,
        "nombre": ubicacion.nombre,
        "tipo": ubicacion.tipo,
        "activo": ubicacion.activo,
    }


@api_catalogo.get("/ubicaciones")
def listar_ubicaciones():
    with current_app.extensions["catalogo_lock"]:
        registros = _dominio(_catalogo().listar_ubicaciones, _estado_listado())
        datos = [_ubicacion_json(item) for item in registros]
    return jsonify(ubicaciones=datos)


@api_catalogo.post("/ubicaciones")
def crear_ubicacion():
    datos = _datos_json({"codigo": str, "nombre": str, "tipo": str})
    with current_app.extensions["catalogo_lock"]:
        ubicacion = _dominio(
            _catalogo().crear_ubicacion, datos["codigo"], datos["nombre"], datos["tipo"]
        )
        resultado = _ubicacion_json(ubicacion)
    return _respuesta_alta(resultado, "catalogo.consultar_ubicacion")


@api_catalogo.get("/ubicaciones/<int:identificador>")
def consultar_ubicacion(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _ubicacion_json(_ubicacion(identificador))
    return jsonify(datos)


@api_catalogo.put("/ubicaciones/<int:identificador>")
def modificar_ubicacion(identificador):
    datos = _datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _ubicacion(identificador)
        ubicacion = _dominio(
            _catalogo().modificar_ubicacion, identificador, datos["codigo"], datos["nombre"]
        )
        resultado = _ubicacion_json(ubicacion)
    return jsonify(resultado)


def _validar_minimo_json(minimo):
    if minimo > MAXIMO_ENTERO_JSON:
        raise ErrorCatalogoAPI(
            400, "El mínimo excede el rango entero exacto del cliente JSON.",
            {"minimo": f"El máximo admitido por HTTP es {MAXIMO_ENTERO_JSON}."},
        )


def _minimo_json(producto, minimo):
    _validar_minimo_json(minimo)
    return {
        "producto": {
            "id": producto.identificador,
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "activo": producto.activo,
        },
        "minimo": minimo,
    }


@api_catalogo.get("/ubicaciones/<int:identificador>/minimos")
def consultar_minimos(identificador):
    with current_app.extensions["catalogo_lock"]:
        local = _ubicacion(identificador)
        configuraciones = _dominio(_catalogo().listar_minimos, identificador)
        datos = [_minimo_json(producto, minimo) for producto, minimo in configuraciones]
        resultado = {"ubicacion": _ubicacion_json(local), "minimos": datos}
    return jsonify(resultado)


@api_catalogo.put("/ubicaciones/<int:identificador>/minimos/<int:producto_id>")
def establecer_minimo(identificador, producto_id):
    datos = _datos_json({"minimo": int})
    _validar_minimo_json(datos["minimo"])
    with current_app.extensions["catalogo_lock"]:
        local = _ubicacion(identificador)
        producto = _producto(producto_id)
        minimo = _dominio(
            _catalogo().establecer_minimo, identificador, producto_id, datos["minimo"]
        )
        resultado = {"ubicacion": _ubicacion_json(local), **_minimo_json(producto, minimo)}
    return jsonify(resultado)


def _estado_listado():
    if len(request.args.getlist("estado")) > 1:
        raise ErrorCatalogoAPI(400, "Enviá un único filtro de estado.")
    return request.args.get("estado", "activos")


def _solicitud_baja():
    datos = _datos_json({"activo": bool})
    if datos["activo"] is not False:
        raise ErrorCatalogoAPI(400, "Sólo se permite desactivar mediante activo: false; no hay reactivación.")


@api_catalogo.patch("/categorias/<int:identificador>/estado")
def desactivar_categoria(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _categoria(identificador)
        categoria = _dominio(_catalogo().desactivar_categoria, identificador)
        resultado = _categoria_json(categoria)
    return jsonify(resultado)


@api_catalogo.patch("/productos/<int:identificador>/estado")
def desactivar_producto(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _producto(identificador)
        producto = _dominio(_catalogo().desactivar_producto, identificador)
        resultado = _producto_json(producto)
    return jsonify(resultado)


@api_catalogo.patch("/proveedores/<int:identificador>/estado")
def desactivar_proveedor(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _proveedor(identificador)
        proveedor = _dominio(_catalogo().desactivar_proveedor, identificador)
        resultado = _proveedor_json(proveedor)
    return jsonify(resultado)


@api_catalogo.patch("/ubicaciones/<int:identificador>/estado")
def desactivar_ubicacion(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _ubicacion(identificador)
        ubicacion = _dominio(_catalogo().desactivar_ubicacion, identificador)
        resultado = _ubicacion_json(ubicacion)
    return jsonify(resultado)
