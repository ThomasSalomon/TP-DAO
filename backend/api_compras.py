"""Adaptador HTTP de compras, existencias y movimientos. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, url_for

from .api_comun import (
    MAXIMO_ENTERO_JSON, ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, operacion_dominio,
    validar_campos,
)
from .dominio import ahora, importe_a_texto
from .persistencia import guardar_compra

api_compras = Blueprint("compras", __name__, url_prefix="/api")
api_compras.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _referencia_json(entidad):
    return {"id": entidad.identificador, "codigo": entidad.codigo, "nombre": entidad.nombre, "activo": entidad.activo}


def _ubicacion_json(ubicacion):
    return {**_referencia_json(ubicacion), "tipo": ubicacion.tipo}


def _compra_json(compra):
    return {
        "id": compra.identificador,
        "proveedor": _referencia_json(compra.proveedor),
        "centro": _ubicacion_json(compra.centro),
        "instante": compra.instante.isoformat(),
        "lineas": [
            {
                "linea": detalle.numero,
                "producto": _referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "costo_unitario": detalle.costo_unitario,
                "subtotal": importe_a_texto(detalle.subtotal_centavos),
            }
            for detalle in compra.detalles
        ],
        "total": compra.total,
        "moneda": "ARS",
    }


def _lineas_validadas(lineas):
    """Valida el formato de cada línea; el contenido lo valida el dominio."""
    errores = {}
    for numero, linea in enumerate(lineas, start=1):
        if not isinstance(linea, dict):
            errores[f"lineas.{numero}"] = "Cada línea debe ser un objeto."
            continue
        campos = validar_campos(linea, {"producto_id": int, "cantidad": int, "costo_unitario": str})
        if not campos and linea["cantidad"] > MAXIMO_ENTERO_JSON:
            campos["cantidad"] = f"El máximo admitido por HTTP es {MAXIMO_ENTERO_JSON}."
        errores.update({f"lineas.{numero}.{campo}": mensaje for campo, mensaje in campos.items()})
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return lineas


def _obtener(operacion, identificador, mensaje, campo=None):
    try:
        return operacion_dominio(operacion, identificador)
    except KeyError:
        raise ErrorCatalogoAPI(404, mensaje, {campo: mensaje} if campo else None) from None


@api_compras.post("/compras")
def registrar_compra():
    datos = datos_json({"proveedor_id": int, "lineas": list})
    lineas = _lineas_validadas(datos["lineas"])
    with current_app.extensions["catalogo_lock"]:
        catalogo = current_app.extensions["catalogo"]
        proveedor = _obtener(
            catalogo.obtener_proveedor, datos["proveedor_id"], "El proveedor no está registrado.", "proveedor_id"
        )
        centro = catalogo.centro_distribucion()
        if centro is None:
            raise ErrorCatalogoAPI(409, "Registrá el Centro de Distribución antes de cargar compras.")
        lineas_dominio = [
            (
                _obtener(
                    catalogo.obtener_producto, linea["producto_id"], "El producto no está registrado.",
                    f"lineas.{numero}.producto_id",
                ),
                linea["cantidad"],
                linea["costo_unitario"],
            )
            for numero, linea in enumerate(lineas, start=1)
        ]
        compra, movimientos = operacion_dominio(
            current_app.extensions["compras"].registrar,
            proveedor, centro, lineas_dominio, ahora(), current_app.extensions["inventario"],
        )
        guardar_cambio(guardar_compra, compra, movimientos)
        resultado = _compra_json(compra)
    respuesta = jsonify(resultado)
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("compras.consultar_compra", identificador=resultado["id"])
    return respuesta


@api_compras.get("/compras")
def listar_compras():
    with current_app.extensions["catalogo_lock"]:
        datos = [_compra_json(compra) for compra in current_app.extensions["compras"].listar()]
    return jsonify(compras=datos)


@api_compras.get("/compras/<int:identificador>")
def consultar_compra(identificador):
    with current_app.extensions["catalogo_lock"]:
        compra = _obtener(current_app.extensions["compras"].obtener, identificador, "No existe la compra solicitada.")
        datos = _compra_json(compra)
    return jsonify(datos)


def _ubicacion(identificador):
    return _obtener(
        current_app.extensions["catalogo"].obtener_ubicacion, identificador, "No existe la ubicación solicitada."
    )


@api_compras.get("/ubicaciones/<int:identificador>/existencias")
def consultar_existencias(identificador):
    with current_app.extensions["catalogo_lock"]:
        ubicacion = _ubicacion(identificador)
        compras = current_app.extensions["compras"]
        existencias = []
        for producto, cantidad in current_app.extensions["inventario"].existencias(ubicacion):
            costo = compras.costo_referencia(producto)
            existencias.append({
                "producto": _referencia_json(producto),
                "disponible": cantidad,
                # Sin compras no hay costo: se informa null, nunca cero (DN-03).
                "costo_referencia": None if costo is None else importe_a_texto(costo),
            })
        resultado = {"ubicacion": _ubicacion_json(ubicacion), "existencias": existencias}
    return jsonify(resultado)


@api_compras.get("/ubicaciones/<int:identificador>/movimientos")
def consultar_movimientos(identificador):
    with current_app.extensions["catalogo_lock"]:
        ubicacion = _ubicacion(identificador)
        movimientos = [
            {
                "id": movimiento.identificador,
                "instante": movimiento.instante.isoformat(),
                "producto": _referencia_json(movimiento.producto),
                "cantidad": movimiento.cantidad,
                "condicion_origen": movimiento.condicion_origen,
                "condicion_destino": movimiento.condicion_destino,
                "causa": movimiento.causa,
                "compra_id": movimiento.documento.compra.identificador,
                "linea": movimiento.documento.numero,
            }
            for movimiento in current_app.extensions["inventario"].movimientos(ubicacion)
        ]
        resultado = {"ubicacion": _ubicacion_json(ubicacion), "movimientos": movimientos}
    return jsonify(resultado)
