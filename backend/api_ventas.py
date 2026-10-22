"""Adaptador HTTP de ventas, cobros, comprobante y caja. Las reglas pertenecen al dominio."""

from flask import Blueprint, current_app, jsonify, url_for

from .api_comun import (
    ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, lineas_validadas, obtener, operacion_dominio,
    referencia_json, ubicacion_json, validar_campos,
)
from .dominio import ahora, importe_a_texto
from .persistencia import guardar_venta

api_ventas = Blueprint("ventas", __name__, url_prefix="/api")
api_ventas.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _registro(nombre):
    return current_app.extensions[nombre]


def _medio_json(medio):
    return {"id": medio.identificador, "codigo": medio.codigo, "nombre": medio.nombre}


def _cobros_json(venta):
    return [
        {"numero": cobro.numero, "medio": _medio_json(cobro.medio), "importe": importe_a_texto(cobro.importe_centavos)}
        for cobro in venta.cobros
    ]


def _venta_json(venta):
    return {
        "id": venta.identificador,
        "comprobante": venta.comprobante.numero,
        "local": ubicacion_json(venta.local),
        "instante": venta.instante.isoformat(),
        "clave_operacion": venta.clave_operacion,
        "lineas": [
            {
                "linea": detalle.numero,
                "producto": referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "precio_unitario": importe_a_texto(detalle.precio_unitario_centavos),
                # Sin compras previas el costo falta: null, nunca cero (DN-03).
                "costo_referencia": (
                    None if detalle.costo_referencia_centavos is None
                    else importe_a_texto(detalle.costo_referencia_centavos)
                ),
                "subtotal": importe_a_texto(detalle.subtotal_centavos),
            }
            for detalle in venta.detalles
        ],
        "cobros": _cobros_json(venta),
        "total": venta.total,
        "moneda": "ARS",
    }


def _comprobante_json(comprobante):
    """Representación para el cliente: sin costos ni clave de operación."""
    venta = comprobante.venta
    return {
        "numero": comprobante.numero,
        "venta_id": venta.identificador,
        "local": ubicacion_json(venta.local),
        "instante": comprobante.instante.isoformat(),
        "lineas": [
            {
                "linea": detalle.numero,
                "producto": referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "precio_unitario": importe_a_texto(detalle.precio_unitario_centavos),
                "subtotal": importe_a_texto(detalle.subtotal_centavos),
            }
            for detalle in venta.detalles
        ],
        "cobros": _cobros_json(venta),
        "total": venta.total,
        "moneda": "ARS",
    }


def _cobros_validados(cobros):
    """Valida el formato de cada cobro; el contenido lo valida el dominio."""
    errores = {}
    for numero, cobro in enumerate(cobros, start=1):
        if not isinstance(cobro, dict):
            errores[f"cobros.{numero}"] = "Cada cobro debe ser un objeto."
            continue
        encontrados = validar_campos(cobro, {"medio_pago_id": int, "importe": str})
        errores.update({f"cobros.{numero}.{campo}": mensaje for campo, mensaje in encontrados.items()})
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    return cobros


def _venta(identificador):
    return obtener(_registro("ventas").obtener, identificador, "No existe la venta solicitada.")


@api_ventas.get("/medios-pago")
def listar_medios_pago():
    datos = [_medio_json(medio) for medio in _registro("ventas").listar_medios()]
    return jsonify(medios_pago=datos)


@api_ventas.post("/ventas")
def registrar_venta():
    datos = datos_json({"local_id": int, "clave_operacion": str, "lineas": list, "cobros": list})
    lineas = lineas_validadas(datos["lineas"], {"producto_id": int, "cantidad": int})
    cobros = _cobros_validados(datos["cobros"])
    with current_app.extensions["catalogo_lock"]:
        catalogo = _registro("catalogo")
        ventas = _registro("ventas")
        local = obtener(catalogo.obtener_ubicacion, datos["local_id"], "El local no está registrado.", "local_id")
        lineas_dominio = [
            (
                obtener(catalogo.obtener_producto, linea["producto_id"], "El producto no está registrado.",
                        f"lineas.{numero}.producto_id"),
                linea["cantidad"],
            )
            for numero, linea in enumerate(lineas, start=1)
        ]
        cobros_dominio = [
            (
                obtener(ventas.obtener_medio, cobro["medio_pago_id"], "El medio de pago no existe.",
                        f"cobros.{numero}.medio_pago_id"),
                cobro["importe"],
            )
            for numero, cobro in enumerate(cobros, start=1)
        ]
        venta, movimientos, movimientos_caja, nueva = operacion_dominio(
            ventas.registrar, local, lineas_dominio, cobros_dominio, ahora(), datos["clave_operacion"],
            _registro("inventario"), _registro("caja"), _registro("compras"),
        )
        if nueva:
            guardar_cambio(guardar_venta, venta, movimientos, movimientos_caja)
        resultado = _venta_json(venta)
    respuesta = jsonify(resultado)
    # Una clave ya registrada devuelve la venta existente con 200, sin nuevos efectos (RB-10).
    respuesta.status_code = 201 if nueva else 200
    respuesta.headers["Location"] = url_for("ventas.consultar_venta", identificador=resultado["id"])
    return respuesta


@api_ventas.get("/ventas")
def listar_ventas():
    with current_app.extensions["catalogo_lock"]:
        datos = [_venta_json(venta) for venta in _registro("ventas").listar()]
    return jsonify(ventas=datos)


@api_ventas.get("/ventas/<int:identificador>")
def consultar_venta(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _venta_json(_venta(identificador))
    return jsonify(datos)


@api_ventas.get("/ventas/<int:identificador>/comprobante")
def consultar_comprobante(identificador):
    """Reconsultar o reimprimir el comprobante no registra otra venta."""
    with current_app.extensions["catalogo_lock"]:
        datos = _comprobante_json(_venta(identificador).comprobante)
    return jsonify(datos)


@api_ventas.get("/ubicaciones/<int:identificador>/caja")
def consultar_caja(identificador):
    """Saldo por medio, calculado desde los movimientos, y los movimientos del local."""
    with current_app.extensions["catalogo_lock"]:
        local = obtener(
            _registro("catalogo").obtener_ubicacion, identificador, "No existe la ubicación solicitada."
        )
        caja = _registro("caja")
        saldos = [
            {"medio": _medio_json(medio), "saldo": importe_a_texto(caja.saldo_centavos(local, medio))}
            for medio in _registro("ventas").listar_medios()
        ]
        movimientos = [
            {
                "id": movimiento.identificador,
                "instante": movimiento.instante.isoformat(),
                "medio": _medio_json(movimiento.medio),
                "tipo": movimiento.tipo,
                "importe": movimiento.importe,
                "venta_id": movimiento.cobro.venta.identificador,
                "comprobante": movimiento.cobro.venta.comprobante.numero,
                "cobro": movimiento.cobro.numero,
            }
            for movimiento in caja.movimientos(local)
        ]
        resultado = {"ubicacion": ubicacion_json(local), "saldos": saldos, "movimientos": movimientos}
    return jsonify(resultado)
