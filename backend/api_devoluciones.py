"""Adaptador HTTP de devoluciones y reintegros. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, url_for

from .api_comun import (
    ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, lineas_validadas, medio_json, obtener,
    operacion_dominio, referencia_json, ubicacion_json, validar_campos,
)
from .dominio import ahora, importe_a_texto
from .persistencia import guardar_devolucion

api_devoluciones = Blueprint("devoluciones", __name__, url_prefix="/api")
api_devoluciones.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _registro(nombre):
    return current_app.extensions[nombre]


def _devolucion_json(devolucion):
    return {
        "id": devolucion.identificador,
        "numero": devolucion.numero,
        "venta_id": devolucion.venta.identificador,
        "comprobante": devolucion.venta.comprobante.numero,
        "local": ubicacion_json(devolucion.local),
        "instante": devolucion.instante.isoformat(),
        "motivo": devolucion.motivo,
        "clave_operacion": devolucion.clave_operacion,
        "lineas": [
            {
                "linea": detalle.numero,
                "venta_linea": detalle.detalle_venta.numero,
                "producto": referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "apto": detalle.apto,
                "condicion_destino": detalle.condicion_destino,
                "precio_unitario": importe_a_texto(detalle.detalle_venta.precio_unitario_centavos),
                "importe": importe_a_texto(detalle.importe_reintegro_centavos),
            }
            for detalle in devolucion.detalles
        ],
        "reintegros": [
            {"numero": reintegro.numero, "medio": medio_json(reintegro.medio),
             "importe": importe_a_texto(reintegro.importe_centavos)}
            for reintegro in devolucion.reintegros
        ],
        "total": devolucion.total,
        "moneda": "ARS",
    }


def _reintegros_validados(reintegros):
    """Valida el formato de cada reintegro; el contenido lo valida el dominio."""
    errores = {}
    for numero, reintegro in enumerate(reintegros, start=1):
        if not isinstance(reintegro, dict):
            errores[f"reintegros.{numero}"] = "Cada reintegro debe ser un objeto."
            continue
        encontrados = validar_campos(reintegro, {"medio_pago_id": int, "importe": str})
        errores.update({f"reintegros.{numero}.{campo}": mensaje for campo, mensaje in encontrados.items()})
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return reintegros


def _linea_vendida(venta, numero_linea, campo):
    if not 1 <= numero_linea <= len(venta.detalles):
        mensaje = "La venta no tiene esa línea."
        raise ErrorCatalogoAPI(404, mensaje, {campo: mensaje})
    return venta.detalles[numero_linea - 1]


def _venta(identificador, campo=None):
    return obtener(_registro("ventas").obtener, identificador, "No existe la venta solicitada.", campo)


@api_devoluciones.post("/devoluciones")
def registrar_devolucion():
    datos = datos_json({
        "venta_id": int, "clave_operacion": str, "motivo": str, "lineas": list, "reintegros": list,
    })
    lineas = lineas_validadas(datos["lineas"], {"linea": int, "cantidad": int, "apto": bool})
    reintegros = _reintegros_validados(datos["reintegros"])
    with current_app.extensions["catalogo_lock"]:
        ventas = _registro("ventas")
        devoluciones = _registro("devoluciones")
        venta = _venta(datos["venta_id"], "venta_id")
        lineas_dominio = [
            (_linea_vendida(venta, linea["linea"], f"lineas.{numero}.linea"), linea["cantidad"], linea["apto"])
            for numero, linea in enumerate(lineas, start=1)
        ]
        reintegros_dominio = [
            (
                obtener(ventas.obtener_medio, reintegro["medio_pago_id"], "El medio de pago no existe.",
                        f"reintegros.{numero}.medio_pago_id"),
                reintegro["importe"],
            )
            for numero, reintegro in enumerate(reintegros, start=1)
        ]
        devolucion, movimientos, movimientos_caja, nueva = operacion_dominio(
            devoluciones.registrar, venta, lineas_dominio, reintegros_dominio, datos["motivo"], ahora(),
            datos["clave_operacion"], _registro("inventario"), _registro("caja"),
        )
        if nueva:
            guardar_cambio(guardar_devolucion, devolucion, movimientos, movimientos_caja)
        resultado = _devolucion_json(devolucion)
    respuesta = jsonify(resultado)
    # Una clave ya registrada devuelve la devolución existente con 200, sin nuevos efectos (RB-10).
    respuesta.status_code = 201 if nueva else 200
    respuesta.headers["Location"] = url_for("devoluciones.consultar_devolucion", identificador=resultado["id"])
    return respuesta


@api_devoluciones.get("/devoluciones")
def listar_devoluciones():
    with current_app.extensions["catalogo_lock"]:
        datos = [_devolucion_json(devolucion) for devolucion in _registro("devoluciones").listar()]
    return jsonify(devoluciones=datos)


@api_devoluciones.get("/devoluciones/<int:identificador>")
def consultar_devolucion(identificador):
    with current_app.extensions["catalogo_lock"]:
        devolucion = obtener(
            _registro("devoluciones").obtener, identificador, "No existe la devolución solicitada."
        )
        datos = _devolucion_json(devolucion)
    return jsonify(datos)


@api_devoluciones.get("/ventas/<int:identificador>/devoluciones")
def consultar_devoluciones_de_venta(identificador):
    """Lo que todavía se puede devolver y reintegrar de una venta, con sus devoluciones anteriores."""
    with current_app.extensions["catalogo_lock"]:
        venta = _venta(identificador)
        devoluciones = _registro("devoluciones")
        resultado = {
            "venta_id": venta.identificador,
            "comprobante": venta.comprobante.numero,
            "local": ubicacion_json(venta.local),
            "lineas": [
                {
                    "linea": detalle.numero,
                    "producto": referencia_json(detalle.producto),
                    "vendida": detalle.cantidad,
                    "devuelta": devoluciones.devuelto(detalle),
                    "remanente": devoluciones.remanente(detalle),
                    "precio_unitario": importe_a_texto(detalle.precio_unitario_centavos),
                }
                for detalle in venta.detalles
            ],
            "reintegrable": [
                {"medio": medio_json(cobro.medio),
                 "importe": importe_a_texto(devoluciones.reintegrable_centavos(venta, cobro.medio))}
                for cobro in venta.cobros
            ],
            "devoluciones": [_devolucion_json(devolucion) for devolucion in devoluciones.listar(venta=venta)],
        }
    return jsonify(resultado)
