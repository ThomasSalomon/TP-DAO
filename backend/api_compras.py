"""Adaptador HTTP de compras, existencias, saldos y movimientos. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, url_for

from .api_comun import (
    ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, lineas_validadas, movimiento_json, obtener,
    operacion_dominio, referencia_json, ubicacion_json,
)
from .dominio import ahora, importe_a_texto
from .persistencia import guardar_compra

api_compras = Blueprint("compras", __name__, url_prefix="/api")
api_compras.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _compra_json(compra):
    return {
        "id": compra.identificador,
        "proveedor": referencia_json(compra.proveedor),
        "centro": ubicacion_json(compra.centro),
        "instante": compra.instante.isoformat(),
        "lineas": [
            {
                "linea": detalle.numero,
                "producto": referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "costo_unitario": detalle.costo_unitario,
                "subtotal": importe_a_texto(detalle.subtotal_centavos),
            }
            for detalle in compra.detalles
        ],
        "total": compra.total,
        "moneda": "ARS",
    }


@api_compras.post("/compras")
def registrar_compra():
    datos = datos_json({"proveedor_id": int, "lineas": list})
    lineas = lineas_validadas(datos["lineas"], {"producto_id": int, "cantidad": int, "costo_unitario": str})
    with current_app.extensions["catalogo_lock"]:
        catalogo = current_app.extensions["catalogo"]
        proveedor = obtener(
            catalogo.obtener_proveedor, datos["proveedor_id"], "El proveedor no está registrado.", "proveedor_id"
        )
        centro = catalogo.centro_distribucion()
        if centro is None:
            raise ErrorCatalogoAPI(409, "Registrá el Centro de Distribución antes de cargar compras.")
        lineas_dominio = [
            (
                obtener(
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
        compra = obtener(current_app.extensions["compras"].obtener, identificador, "No existe la compra solicitada.")
        datos = _compra_json(compra)
    return jsonify(datos)


def _ubicacion(identificador):
    return obtener(
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
                "producto": referencia_json(producto),
                "disponible": cantidad,
                # Sin compras no hay costo: se informa null, nunca cero (DN-03).
                "costo_referencia": None if costo is None else importe_a_texto(costo),
            })
        resultado = {"ubicacion": ubicacion_json(ubicacion), "existencias": existencias}
    return jsonify(resultado)


@api_compras.get("/ubicaciones/<int:identificador>/saldos")
def consultar_saldos(identificador):
    """Todas las condiciones con saldo de la ubicación: disponible, reservado, en tránsito, etc."""
    with current_app.extensions["catalogo_lock"]:
        ubicacion = _ubicacion(identificador)
        saldos = [
            {"producto": referencia_json(producto), "condicion": condicion, "cantidad": cantidad}
            for producto, condicion, cantidad in current_app.extensions["inventario"].saldos(ubicacion)
        ]
        resultado = {"ubicacion": ubicacion_json(ubicacion), "saldos": saldos}
    return jsonify(resultado)


@api_compras.get("/ubicaciones/<int:identificador>/movimientos")
def consultar_movimientos(identificador):
    with current_app.extensions["catalogo_lock"]:
        ubicacion = _ubicacion(identificador)
        movimientos = [
            movimiento_json(movimiento)
            for movimiento in current_app.extensions["inventario"].movimientos(ubicacion)
        ]
        resultado = {"ubicacion": ubicacion_json(ubicacion), "movimientos": movimientos}
    return jsonify(resultado)
