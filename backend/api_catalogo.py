"""Adaptador HTTP del catálogo. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, request, url_for

from .api_comun import (
    MAXIMO_ENTERO_JSON, ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, operacion_dominio,
)
from .persistencia import guardar_categoria, guardar_minimo, guardar_producto, guardar_proveedor, guardar_ubicacion

api_catalogo = Blueprint("catalogo", __name__, url_prefix="/api")
api_catalogo.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _catalogo():
    return current_app.extensions["catalogo"]


def _categoria(identificador):
    try:
        return operacion_dominio(_catalogo().obtener_categoria, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(
            404, "No existe la categoría solicitada.",
            {"categoria_id": "La categoría no está registrada."},
        ) from None


def _producto(identificador):
    try:
        return operacion_dominio(_catalogo().obtener_producto, identificador)
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
        return operacion_dominio(_catalogo().obtener_proveedor, identificador)
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
        registros = operacion_dominio(_catalogo().listar_categorias, _estado_listado())
        datos = [_categoria_json(item) for item in registros]
    return jsonify(categorias=datos)


@api_catalogo.post("/categorias")
def crear_categoria():
    datos = datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        categoria = operacion_dominio(_catalogo().crear_categoria, datos["codigo"], datos["nombre"])
        guardar_cambio(guardar_categoria, categoria)
        resultado = _categoria_json(categoria)
    return _respuesta_alta(resultado, "catalogo.consultar_categoria")


@api_catalogo.get("/categorias/<int:identificador>")
def consultar_categoria(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _categoria_json(_categoria(identificador))
    return jsonify(datos)


@api_catalogo.put("/categorias/<int:identificador>")
def modificar_categoria(identificador):
    datos = datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _categoria(identificador)
        categoria = operacion_dominio(
            _catalogo().modificar_categoria, identificador, datos["codigo"], datos["nombre"]
        )
        guardar_cambio(guardar_categoria, categoria)
        resultado = _categoria_json(categoria)
    return jsonify(resultado)


@api_catalogo.get("/productos")
def listar_productos():
    with current_app.extensions["catalogo_lock"]:
        registros = operacion_dominio(_catalogo().listar_productos, _estado_listado())
        datos = [_producto_json(item) for item in registros]
    return jsonify(productos=datos)


@api_catalogo.post("/productos")
def crear_producto():
    datos = datos_json({"codigo": str, "nombre": str, "categoria_id": int, "precio": str})
    with current_app.extensions["catalogo_lock"]:
        categoria = _categoria(datos["categoria_id"])
        producto = operacion_dominio(
            _catalogo().crear_producto,
            datos["codigo"], datos["nombre"], categoria, datos["precio"],
        )
        guardar_cambio(guardar_producto, producto)
        resultado = _producto_json(producto)
    return _respuesta_alta(resultado, "catalogo.consultar_producto")


@api_catalogo.get("/productos/<int:identificador>")
def consultar_producto(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _producto_json(_producto(identificador))
    return jsonify(datos)


@api_catalogo.put("/productos/<int:identificador>")
def modificar_producto(identificador):
    datos = datos_json({"codigo": str, "nombre": str, "categoria_id": int, "precio": str})
    with current_app.extensions["catalogo_lock"]:
        _producto(identificador)
        categoria = _categoria(datos["categoria_id"])
        producto = operacion_dominio(
            _catalogo().modificar_producto,
            identificador, datos["codigo"], datos["nombre"], categoria, datos["precio"],
        )
        guardar_cambio(guardar_producto, producto)
        resultado = _producto_json(producto)
    return jsonify(resultado)


@api_catalogo.get("/proveedores")
def listar_proveedores():
    with current_app.extensions["catalogo_lock"]:
        registros = operacion_dominio(_catalogo().listar_proveedores, _estado_listado())
        datos = [_proveedor_json(item) for item in registros]
    return jsonify(proveedores=datos)


@api_catalogo.post("/proveedores")
def crear_proveedor():
    datos = datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        proveedor = operacion_dominio(_catalogo().crear_proveedor, datos["codigo"], datos["nombre"])
        guardar_cambio(guardar_proveedor, proveedor)
        resultado = _proveedor_json(proveedor)
    return _respuesta_alta(resultado, "catalogo.consultar_proveedor")


@api_catalogo.get("/proveedores/<int:identificador>")
def consultar_proveedor(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _proveedor_json(_proveedor(identificador))
    return jsonify(datos)


@api_catalogo.put("/proveedores/<int:identificador>")
def modificar_proveedor(identificador):
    datos = datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _proveedor(identificador)
        proveedor = operacion_dominio(
            _catalogo().modificar_proveedor, identificador, datos["codigo"], datos["nombre"]
        )
        guardar_cambio(guardar_proveedor, proveedor)
        resultado = _proveedor_json(proveedor)
    return jsonify(resultado)


def _ubicacion(identificador):
    try:
        return operacion_dominio(_catalogo().obtener_ubicacion, identificador)
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
        registros = operacion_dominio(_catalogo().listar_ubicaciones, _estado_listado())
        datos = [_ubicacion_json(item) for item in registros]
    return jsonify(ubicaciones=datos)


@api_catalogo.post("/ubicaciones")
def crear_ubicacion():
    datos = datos_json({"codigo": str, "nombre": str, "tipo": str})
    with current_app.extensions["catalogo_lock"]:
        ubicacion = operacion_dominio(
            _catalogo().crear_ubicacion, datos["codigo"], datos["nombre"], datos["tipo"]
        )
        guardar_cambio(guardar_ubicacion, ubicacion)
        resultado = _ubicacion_json(ubicacion)
    return _respuesta_alta(resultado, "catalogo.consultar_ubicacion")


@api_catalogo.get("/ubicaciones/<int:identificador>")
def consultar_ubicacion(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _ubicacion_json(_ubicacion(identificador))
    return jsonify(datos)


@api_catalogo.put("/ubicaciones/<int:identificador>")
def modificar_ubicacion(identificador):
    datos = datos_json({"codigo": str, "nombre": str})
    with current_app.extensions["catalogo_lock"]:
        _ubicacion(identificador)
        ubicacion = operacion_dominio(
            _catalogo().modificar_ubicacion, identificador, datos["codigo"], datos["nombre"]
        )
        guardar_cambio(guardar_ubicacion, ubicacion)
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
        configuraciones = operacion_dominio(_catalogo().listar_minimos, identificador)
        datos = [_minimo_json(producto, minimo) for producto, minimo in configuraciones]
        resultado = {"ubicacion": _ubicacion_json(local), "minimos": datos}
    return jsonify(resultado)


@api_catalogo.put("/ubicaciones/<int:identificador>/minimos/<int:producto_id>")
def establecer_minimo(identificador, producto_id):
    datos = datos_json({"minimo": int})
    _validar_minimo_json(datos["minimo"])
    with current_app.extensions["catalogo_lock"]:
        local = _ubicacion(identificador)
        producto = _producto(producto_id)
        minimo = operacion_dominio(
            _catalogo().establecer_minimo, identificador, producto_id, datos["minimo"]
        )
        guardar_cambio(guardar_minimo, identificador, producto_id, minimo)
        resultado = {"ubicacion": _ubicacion_json(local), **_minimo_json(producto, minimo)}
    return jsonify(resultado)


def _estado_listado():
    if len(request.args.getlist("estado")) > 1:
        raise ErrorCatalogoAPI(400, "Enviá un único filtro de estado.")
    return request.args.get("estado", "activos")


def _solicitud_baja():
    datos = datos_json({"activo": bool})
    if datos["activo"] is not False:
        raise ErrorCatalogoAPI(400, "Sólo se permite desactivar mediante activo: false; no hay reactivación.")


@api_catalogo.patch("/categorias/<int:identificador>/estado")
def desactivar_categoria(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _categoria(identificador)
        categoria = operacion_dominio(_catalogo().desactivar_categoria, identificador)
        guardar_cambio(guardar_categoria, categoria)
        resultado = _categoria_json(categoria)
    return jsonify(resultado)


@api_catalogo.patch("/productos/<int:identificador>/estado")
def desactivar_producto(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _producto(identificador)
        producto = operacion_dominio(_catalogo().desactivar_producto, identificador)
        guardar_cambio(guardar_producto, producto)
        resultado = _producto_json(producto)
    return jsonify(resultado)


@api_catalogo.patch("/proveedores/<int:identificador>/estado")
def desactivar_proveedor(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _proveedor(identificador)
        proveedor = operacion_dominio(_catalogo().desactivar_proveedor, identificador)
        guardar_cambio(guardar_proveedor, proveedor)
        resultado = _proveedor_json(proveedor)
    return jsonify(resultado)


@api_catalogo.patch("/ubicaciones/<int:identificador>/estado")
def desactivar_ubicacion(identificador):
    _solicitud_baja()
    with current_app.extensions["catalogo_lock"]:
        _ubicacion(identificador)
        ubicacion = operacion_dominio(_catalogo().desactivar_ubicacion, identificador)
        guardar_cambio(guardar_ubicacion, ubicacion)
        resultado = _ubicacion_json(ubicacion)
    return jsonify(resultado)
