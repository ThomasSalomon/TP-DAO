"""Adaptador HTTP de los reportes R-01 a R-04. Sólo consulta: los cálculos pertenecen al dominio."""

import re
from datetime import date

from flask import Blueprint, current_app, jsonify, request

from .api_comun import (
    MAXIMO_ENTERO_JSON, ErrorCatalogoAPI, error_catalogo, obtener, referencia_json, ubicacion_json,
)
from .dominio import (
    CONDICIONES, ESTRATEGIAS_AGRUPACION, Periodo, ReporteVentas, existencias_y_minimos, importe_a_texto,
    productos_mas_vendidos, rechazos_logisticos,
)

api_reportes = Blueprint("reportes", __name__, url_prefix="/api/reportes")
api_reportes.register_error_handler(ErrorCatalogoAPI, error_catalogo)

FORMATO_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def _registro(nombre):
    return current_app.extensions[nombre]


def _error(campo, mensaje):
    return ErrorCatalogoAPI(400, "Revisá los parámetros indicados.", {campo: mensaje})


def _parametros(permitidos):
    """Rechaza parámetros desconocidos o repetidos antes de interpretarlos."""
    for nombre in request.args:
        if nombre not in permitidos:
            raise _error(nombre, "Este parámetro no está permitido.")
        if len(request.args.getlist(nombre)) > 1:
            raise _error(nombre, "Enviá un único valor.")


def _fecha(nombre):
    texto = request.args.get(nombre)
    if texto is None:
        raise _error(nombre, "Este parámetro es obligatorio.")
    if not FORMATO_FECHA.fullmatch(texto):
        raise _error(nombre, "Usá el formato AAAA-MM-DD.")
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise _error(nombre, "No es una fecha válida.") from None


def _periodo():
    """desde incluido y hasta excluido (DN-09)."""
    desde, hasta = _fecha("desde"), _fecha("hasta")
    try:
        return Periodo(desde, hasta)
    except ValueError as error:
        raise _error("hasta", str(error)) from None


def _referencia(nombre, operacion, mensaje):
    """Registro indicado por un parámetro opcional; None si no vino."""
    texto = request.args.get(nombre)
    if texto is None:
        return None
    if not (texto.isascii() and texto.isdigit()) or not 0 < int(texto) <= MAXIMO_ENTERO_JSON:
        raise _error(nombre, "Debe ser un identificador entero positivo.")
    return obtener(operacion, int(texto), mensaje, nombre)


def _local():
    local = _referencia("local_id", _registro("catalogo").obtener_ubicacion, "El local no está registrado.")
    if local is not None and local.tipo != "LOCAL":
        # El dominio también lo rechaza; aquí se informa el parámetro.
        raise _error("local_id", "El filtro de ubicación debe ser un local, no el CD.")
    return local


def _booleano(nombre):
    texto = request.args.get(nombre, "false")
    if texto not in ("true", "false"):
        raise _error(nombre, "Debe ser true o false.")
    return texto == "true"


def _importe(centavos):
    """null si falta un costo: nunca se informa como cero."""
    return None if centavos is None else importe_a_texto(centavos)


def _periodo_json(periodo):
    return {"desde": periodo.desde.isoformat(), "hasta": periodo.hasta.isoformat()}


def _opcional(entidad, representacion=referencia_json):
    return None if entidad is None else representacion(entidad)


@api_reportes.get("/ventas")
def reporte_ventas():
    """R-01: la agrupación elige la estrategia; por defecto, por día."""
    _parametros({"desde", "hasta", "local_id", "agrupacion"})
    periodo = _periodo()
    nombre = request.args.get("agrupacion", "dia")
    if nombre not in ESTRATEGIAS_AGRUPACION:
        raise _error("agrupacion", f"Elegí una de: {', '.join(ESTRATEGIAS_AGRUPACION)}.")
    with current_app.extensions["catalogo_lock"]:
        local = _local()
        resultado = ReporteVentas(ESTRATEGIAS_AGRUPACION[nombre]()).generar(
            periodo, _registro("ventas"), _registro("devoluciones"), _registro("caja"), local,
        )
        datos = {
            "periodo": _periodo_json(periodo),
            "local": _opcional(local, ubicacion_json),
            "agrupacion": resultado.agrupacion,
            "ventas": {"cantidad": resultado.cantidad_ventas, "importe": _importe(resultado.ventas_centavos)},
            "devoluciones": {
                "cantidad": resultado.cantidad_devoluciones, "importe": _importe(resultado.devoluciones_centavos),
            },
            "venta_neta": _importe(resultado.venta_neta_centavos),
            "grupos": [
                {
                    "etiqueta": grupo.etiqueta,
                    "cobros": _importe(grupo.cobros_centavos),
                    "reintegros": _importe(grupo.reintegros_centavos),
                    "ingreso_neto": _importe(grupo.ingreso_neto_centavos),
                }
                for grupo in resultado.grupos
            ],
            "cobros": _importe(resultado.cobros_centavos),
            "reintegros": _importe(resultado.reintegros_centavos),
            "ingreso_neto": _importe(resultado.ingreso_neto_centavos),
            "moneda": "ARS",
        }
    return jsonify(datos)


@api_reportes.get("/agrupaciones")
def listar_agrupaciones():
    return jsonify(agrupaciones=list(ESTRATEGIAS_AGRUPACION))


@api_reportes.get("/productos")
def reporte_productos():
    """R-02: ranking por unidades netas y margen estimado con costos históricos."""
    _parametros({"desde", "hasta", "local_id"})
    periodo = _periodo()
    with current_app.extensions["catalogo_lock"]:
        local = _local()
        resultado = productos_mas_vendidos(periodo, _registro("ventas"), _registro("devoluciones"), local)
        datos = {
            "periodo": _periodo_json(periodo),
            "local": _opcional(local, ubicacion_json),
            "productos": [
                {
                    "posicion": posicion,
                    "producto": referencia_json(fila.producto),
                    "unidades_vendidas": fila.unidades_vendidas,
                    "unidades_devueltas": fila.unidades_devueltas,
                    "unidades_netas": fila.unidades_netas,
                    "importe_neto": _importe(fila.importe_neto_centavos),
                    "costo_neto": _importe(fila.costo_neto_centavos),
                    "margen": _importe(fila.margen_centavos),
                }
                for posicion, fila in enumerate(resultado.filas, start=1)
            ],
            "unidades_netas": resultado.unidades_netas,
            "importe_neto": _importe(resultado.importe_neto_centavos),
            "margen": _importe(resultado.margen_centavos),
            "productos_sin_costo": [referencia_json(producto) for producto in resultado.productos_sin_costo],
            "moneda": "ARS",
        }
    return jsonify(datos)


@api_reportes.get("/existencias")
def reporte_existencias():
    """R-03: saldos por condición frente al mínimo de cada producto en la ubicación."""
    _parametros({"ubicacion_id", "categoria_id", "solo_en_minimo"})
    if "ubicacion_id" not in request.args:
        raise _error("ubicacion_id", "Este parámetro es obligatorio.")
    solo_en_minimo = _booleano("solo_en_minimo")
    with current_app.extensions["catalogo_lock"]:
        catalogo = _registro("catalogo")
        ubicacion = _referencia("ubicacion_id", catalogo.obtener_ubicacion, "La ubicación no está registrada.")
        categoria = _referencia("categoria_id", catalogo.obtener_categoria, "La categoría no está registrada.")
        resultado = existencias_y_minimos(ubicacion, catalogo, _registro("inventario"), categoria, solo_en_minimo)
        datos = {
            "ubicacion": ubicacion_json(ubicacion),
            "categoria": _opcional(categoria),
            "solo_en_minimo": solo_en_minimo,
            "productos": [
                {
                    "producto": referencia_json(fila.producto),
                    "categoria": referencia_json(fila.producto.categoria),
                    "saldos": fila.saldos,
                    "minimo": fila.minimo,
                    "deficit": fila.deficit,
                    "en_minimo": fila.en_minimo,
                }
                for fila in resultado.filas
            ],
            "totales": {condicion: resultado.total(condicion) for condicion in CONDICIONES},
            "productos_en_minimo": resultado.productos_en_minimo,
            "deficit_total": resultado.deficit_total,
        }
    return jsonify(datos)


@api_reportes.get("/rechazos")
def reporte_rechazos():
    """R-04: bultos rechazados por fecha del rechazo y valor bloqueado, que no es una merma."""
    _parametros({"desde", "hasta", "local_id", "producto_id"})
    periodo = _periodo()
    with current_app.extensions["catalogo_lock"]:
        local = _local()
        producto = _referencia(
            "producto_id", _registro("catalogo").obtener_producto, "El producto no está registrado."
        )
        resultado = rechazos_logisticos(periodo, _registro("logistica"), local, producto)
        datos = {
            "periodo": _periodo_json(periodo),
            "local": _opcional(local, ubicacion_json),
            "producto": _opcional(producto),
            "rechazos": [
                {
                    "bulto_id": rechazo.bulto.identificador,
                    "bulto_codigo": rechazo.bulto.codigo,
                    "remito": rechazo.bulto.remito.numero,
                    "destino": ubicacion_json(rechazo.bulto.destino),
                    "instante": rechazo.instante.isoformat(),
                    "motivo": rechazo.motivo,
                    "lineas": [
                        {
                            "producto": referencia_json(detalle.producto),
                            "cantidad": detalle.cantidad,
                            "costo_referencia": _importe(detalle.costo_referencia_centavos),
                        }
                        for detalle in rechazo.detalles
                    ],
                    "unidades": rechazo.unidades,
                    "valor_bloqueado": _importe(rechazo.valor_bloqueado_centavos),
                }
                for rechazo in resultado.rechazos
            ],
            "locales": [
                {
                    "destino": ubicacion_json(item.destino),
                    "bultos_recibidos": item.bultos_recibidos,
                    "bultos_rechazados": item.bultos_rechazados,
                    "unidades": item.unidades,
                    "valor_bloqueado": _importe(item.valor_bloqueado_centavos),
                }
                for item in resultado.locales
            ],
            "bultos_recibidos": resultado.bultos_recibidos,
            "bultos_rechazados": resultado.bultos_rechazados,
            "unidades": resultado.unidades,
            "valor_bloqueado": _importe(resultado.valor_bloqueado_centavos),
            "moneda": "ARS",
        }
    return jsonify(datos)
