"""Adaptador HTTP de necesidades, órdenes de reposición, bultos y remitos.

Las reglas y transiciones pertenecen al dominio; aquí sólo se valida el transporte.
"""

from flask import Blueprint, current_app, jsonify, url_for

from .api_comun import (
    MAXIMO_ENTERO_JSON, ErrorCatalogoAPI, datos_json, error_catalogo, guardar_cambio, lineas_validadas, obtener,
    operacion_dominio, referencia_json, ubicacion_json,
)
from .dominio import ahora, importe_a_texto
from .persistencia import guardar_bulto, guardar_necesidad, guardar_orden

api_logistica = Blueprint("logistica", __name__, url_prefix="/api")
api_logistica.register_error_handler(ErrorCatalogoAPI, error_catalogo)


def _registro(nombre):
    return current_app.extensions[nombre]


def _creado(resultado, endpoint):
    respuesta = jsonify(resultado)
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for(endpoint, identificador=resultado["id"])
    return respuesta


def _necesidad_json(necesidad):
    return {
        "id": necesidad.identificador,
        "local": ubicacion_json(necesidad.local),
        "producto": referencia_json(necesidad.producto),
        "cantidad": necesidad.cantidad,
        "instante": necesidad.instante.isoformat(),
        "estado": necesidad.estado,
        "orden_id": None if necesidad.orden is None else necesidad.orden.identificador,
    }


def _bulto_resumen(bulto):
    return {"id": bulto.identificador, "codigo": bulto.codigo, "estado": bulto.estado}


def _orden_json(orden):
    return {
        "id": orden.identificador,
        "centro": ubicacion_json(orden.centro),
        "destino": ubicacion_json(orden.destino),
        "instante": orden.instante.isoformat(),
        "estado": orden.estado,
        "lineas": [
            {
                "producto": referencia_json(detalle.producto),
                "solicitada": detalle.cantidad_solicitada,
                "asignada": detalle.cantidad_asignada,
                "pendiente": detalle.cantidad_pendiente,
                "necesidades": [necesidad.identificador for necesidad in detalle.necesidades],
            }
            for detalle in orden.detalles
        ],
        "bultos": [_bulto_resumen(bulto) for bulto in orden.bultos],
    }


def _remito_json(remito):
    return {
        "id": remito.identificador,
        "numero": remito.numero,
        "bulto": _bulto_resumen(remito.bulto),
        "origen": ubicacion_json(remito.origen),
        "destino": ubicacion_json(remito.destino),
        "estado": remito.estado,
        "instante": remito.instante.isoformat(),
        "instante_cierre": None if remito.instante_cierre is None else remito.instante_cierre.isoformat(),
    }


def _bulto_json(bulto):
    remito = bulto.remito
    return {
        **_bulto_resumen(bulto),
        "orden_id": bulto.orden.identificador,
        "origen": ubicacion_json(bulto.origen),
        "destino": ubicacion_json(bulto.destino),
        "precinto": bulto.precinto,
        "remito": None if remito is None else {"id": remito.identificador, "numero": remito.numero, "estado": remito.estado},
        "lineas": [
            {
                "producto": referencia_json(detalle.producto),
                "cantidad": detalle.cantidad,
                "costo_referencia": (
                    None if detalle.costo_referencia_centavos is None
                    else importe_a_texto(detalle.costo_referencia_centavos)
                ),
            }
            for detalle in bulto.detalles
        ],
        "eventos": [
            {
                "secuencia": evento.secuencia,
                "estado_anterior": evento.estado_anterior,
                "estado_nuevo": evento.estado_nuevo,
                "instante": evento.instante.isoformat(),
                "motivo": evento.motivo,
            }
            for evento in bulto.eventos
        ],
    }


def _ubicacion(identificador, campo):
    return obtener(
        _registro("catalogo").obtener_ubicacion, identificador, "La ubicación no está registrada.", campo
    )


def _centro():
    centro = _registro("catalogo").centro_distribucion()
    if centro is None:
        raise ErrorCatalogoAPI(409, "Registrá el Centro de Distribución antes de operar la reposición.")
    return centro


def _bulto(identificador):
    return obtener(_registro("logistica").obtener_bulto, identificador, "No existe el bulto solicitado.")


@api_logistica.post("/necesidades")
def registrar_necesidad():
    datos = datos_json({"local_id": int, "producto_id": int, "cantidad": int})
    if datos["cantidad"] > MAXIMO_ENTERO_JSON:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", {
            "cantidad": f"El máximo admitido por HTTP es {MAXIMO_ENTERO_JSON}.",
        })
    with current_app.extensions["catalogo_lock"]:
        local = _ubicacion(datos["local_id"], "local_id")
        producto = obtener(
            _registro("catalogo").obtener_producto, datos["producto_id"], "El producto no está registrado.",
            "producto_id",
        )
        necesidad = operacion_dominio(
            _registro("reposicion").registrar_necesidad, local, producto, datos["cantidad"], ahora()
        )
        guardar_cambio(guardar_necesidad, necesidad)
        resultado = _necesidad_json(necesidad)
    return _creado(resultado, "logistica.consultar_necesidad")


@api_logistica.get("/necesidades")
def listar_necesidades():
    with current_app.extensions["catalogo_lock"]:
        datos = [_necesidad_json(necesidad) for necesidad in _registro("reposicion").listar_necesidades()]
    return jsonify(necesidades=datos)


@api_logistica.get("/necesidades/<int:identificador>")
def consultar_necesidad(identificador):
    with current_app.extensions["catalogo_lock"]:
        necesidad = obtener(
            _registro("reposicion").obtener_necesidad, identificador, "No existe la necesidad solicitada."
        )
        datos = _necesidad_json(necesidad)
    return jsonify(datos)


@api_logistica.post("/ordenes")
def consolidar_orden():
    datos = datos_json({"local_id": int, "necesidad_ids": list})
    errores = {
        f"necesidad_ids.{numero}": "Debe ser un identificador entero."
        for numero, valor in enumerate(datos["necesidad_ids"], start=1) if type(valor) is not int
    }
    if errores:
        raise ErrorCatalogoAPI(400, "Revisá los campos indicados.", errores)
    with current_app.extensions["catalogo_lock"]:
        destino = _ubicacion(datos["local_id"], "local_id")
        centro = _centro()
        reposicion = _registro("reposicion")
        necesidades = [
            obtener(reposicion.obtener_necesidad, valor, "La necesidad no está registrada.", f"necesidad_ids.{numero}")
            for numero, valor in enumerate(datos["necesidad_ids"], start=1)
        ]
        orden = operacion_dominio(reposicion.consolidar, centro, destino, necesidades, ahora())
        guardar_cambio(guardar_orden, orden)
        resultado = _orden_json(orden)
    return _creado(resultado, "logistica.consultar_orden")


@api_logistica.get("/ordenes")
def listar_ordenes():
    with current_app.extensions["catalogo_lock"]:
        datos = [_orden_json(orden) for orden in _registro("reposicion").listar_ordenes()]
    return jsonify(ordenes=datos)


@api_logistica.get("/ordenes/<int:identificador>")
def consultar_orden(identificador):
    with current_app.extensions["catalogo_lock"]:
        orden = obtener(_registro("reposicion").obtener_orden, identificador, "No existe la orden solicitada.")
        datos = _orden_json(orden)
    return jsonify(datos)


@api_logistica.post("/ordenes/<int:identificador>/bultos")
def preparar_bulto(identificador):
    datos = datos_json({"lineas": list})
    lineas = lineas_validadas(datos["lineas"], {"producto_id": int, "cantidad": int})
    with current_app.extensions["catalogo_lock"]:
        orden = obtener(_registro("reposicion").obtener_orden, identificador, "No existe la orden solicitada.")
        catalogo = _registro("catalogo")
        lineas_dominio = [
            (
                obtener(catalogo.obtener_producto, linea["producto_id"], "El producto no está registrado.",
                        f"lineas.{numero}.producto_id"),
                linea["cantidad"],
            )
            for numero, linea in enumerate(lineas, start=1)
        ]
        bulto, movimientos = operacion_dominio(
            _registro("logistica").preparar, orden, lineas_dominio, ahora(), _registro("inventario"),
            _registro("compras"),
        )
        guardar_cambio(guardar_bulto, bulto, movimientos)
        resultado = _bulto_json(bulto)
    return _creado(resultado, "logistica.consultar_bulto")


@api_logistica.get("/bultos")
def listar_bultos():
    with current_app.extensions["catalogo_lock"]:
        datos = [_bulto_json(bulto) for bulto in _registro("logistica").listar_bultos()]
    return jsonify(bultos=datos)


@api_logistica.get("/bultos/<int:identificador>")
def consultar_bulto(identificador):
    with current_app.extensions["catalogo_lock"]:
        datos = _bulto_json(_bulto(identificador))
    return jsonify(datos)


def _operar(identificador, campos, operacion):
    """Aplica una transición del bulto y guarda su estado, eventos, remito y movimientos juntos."""
    datos = datos_json(campos)
    with current_app.extensions["catalogo_lock"]:
        bulto = _bulto(identificador)
        movimientos = operacion_dominio(operacion, bulto, datos)
        guardar_cambio(guardar_bulto, bulto, movimientos)
        resultado = _bulto_json(bulto)
    return jsonify(resultado)


@api_logistica.post("/bultos/<int:identificador>/precintar")
def precintar_bulto(identificador):
    def precintar(bulto, datos):
        _registro("logistica").precintar(bulto, datos["precinto"], ahora())
        return ()
    return _operar(identificador, {"precinto": str}, precintar)


@api_logistica.post("/bultos/<int:identificador>/despachar")
def despachar_bulto(identificador):
    return _operar(identificador, {}, lambda bulto, datos: bulto.despachar(ahora(), _registro("inventario")))


@api_logistica.post("/bultos/<int:identificador>/recibir")
def recibir_bulto(identificador):
    def recibir(bulto, datos):
        local = _ubicacion(datos["local_id"], "local_id")
        return bulto.recibir(
            local, datos["precinto_leido"], datos["precinto_intacto"], ahora(), _registro("inventario")
        )
    return _operar(
        identificador, {"local_id": int, "precinto_leido": str, "precinto_intacto": bool}, recibir
    )


@api_logistica.post("/bultos/<int:identificador>/verificar")
def verificar_bulto(identificador):
    return _operar(identificador, {}, lambda bulto, datos: bulto.verificar(ahora()))


@api_logistica.post("/bultos/<int:identificador>/anular")
def anular_bulto(identificador):
    return _operar(identificador, {}, lambda bulto, datos: bulto.anular(ahora(), _registro("inventario")))


@api_logistica.get("/remitos")
def listar_remitos():
    with current_app.extensions["catalogo_lock"]:
        datos = [_remito_json(remito) for remito in _registro("logistica").listar_remitos()]
    return jsonify(remitos=datos)


@api_logistica.get("/remitos/<int:identificador>")
def consultar_remito(identificador):
    with current_app.extensions["catalogo_lock"]:
        remito = obtener(_registro("logistica").obtener_remito, identificador, "No existe el remito solicitado.")
        datos = _remito_json(remito)
    return jsonify(datos)


@api_logistica.post("/remitos/<int:identificador>/verificar")
def verificar_remito(identificador):
    datos_json({})
    with current_app.extensions["catalogo_lock"]:
        remito = obtener(_registro("logistica").obtener_remito, identificador, "No existe el remito solicitado.")
        movimientos = operacion_dominio(remito.verificar, ahora(), _registro("inventario"))
        guardar_cambio(guardar_bulto, remito.bulto, movimientos)
        resultado = _remito_json(remito)
    return jsonify(resultado)
