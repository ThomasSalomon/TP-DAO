"""Estados administrativos, consultas históricas y carreras sobre referencias."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import create_app

RECURSOS = ["categorias", "productos", "proveedores", "ubicaciones"]


def escenario():
    app = create_app()
    cliente = app.test_client()
    categoria = cliente.post("/api/categorias", json={"codigo": "CAT", "nombre": "Almacén"}).get_json()
    cliente.post("/api/productos", json={"codigo": "PROD", "nombre": "Arroz", "categoria_id": categoria["id"], "precio": "125.50"})
    cliente.post("/api/proveedores", json={"codigo": "PR", "nombre": "Distribuidora"})
    cliente.post("/api/ubicaciones", json={"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"})
    cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 0})
    return app, cliente


@pytest.mark.parametrize("recurso", RECURSOS)
def test_baja_idempotente_get_conservado_filtros_y_edicion_bloqueada(recurso):
    _, cliente = escenario()
    if recurso == "categorias":
        cliente.patch("/api/productos/1/estado", json={"activo": False})
    ruta = f"/api/{recurso}"
    original = cliente.get(f"{ruta}/1").get_json()
    assert original["activo"] is True
    for _ in range(2):
        respuesta = cliente.patch(f"{ruta}/1/estado", json={"activo": False})
        assert respuesta.status_code == 200
        assert respuesta.get_json() == {**original, "activo": False}
    assert cliente.get(f"{ruta}/1").get_json() == {**original, "activo": False}
    assert cliente.get(ruta).get_json() == {recurso: []}
    for estado in ["inactivos", "todos"]:
        assert cliente.get(f"{ruta}?estado={estado}").get_json() == {recurso: [{**original, "activo": False}]}
    entrada = {"codigo": "NUEVO", "nombre": "Cambio"}
    if recurso == "productos":
        entrada.update(categoria_id=1, precio="1")
    respuesta = cliente.put(f"{ruta}/1", json=entrada)
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["code"] == 409
    assert cliente.get(f"{ruta}/1").get_json() == {**original, "activo": False}
    assert cliente.delete(f"{ruta}/1").status_code == 405


@pytest.mark.parametrize("recurso", RECURSOS)
def test_codigos_originales_y_reemplazados_reservados_despues_de_baja(recurso):
    _, cliente = escenario()
    ruta = f"/api/{recurso}"
    original = cliente.get(f"{ruta}/1").get_json()
    entrada = {"codigo": "REEMPLAZO", "nombre": "Actual"}
    if recurso == "productos":
        entrada.update(categoria_id=1, precio="1")
    assert cliente.put(f"{ruta}/1", json=entrada).status_code == 200
    if recurso == "categorias":
        cliente.patch("/api/productos/1/estado", json={"activo": False})
    assert cliente.patch(f"{ruta}/1/estado", json={"activo": False}).status_code == 200
    for codigo in [original["codigo"].lower(), " reemplazo "]:
        alta = {**entrada, "codigo": codigo}
        if recurso == "ubicaciones":
            alta["tipo"] = "LOCAL"
        respuesta = cliente.post(ruta, json=alta)
        assert respuesta.status_code == 409
        assert respuesta.get_json()["error"]["fields"]["codigo"]


@pytest.mark.parametrize("datos", [{}, {"activo": True}, {"activo": 0}, {"activo": 1}, {"activo": "false"}, {"activo": None}, {"activo": False, "nombre": "Cambio"}])
def test_estado_solo_acepta_false_booleano_sin_campos_extra(datos):
    _, cliente = escenario()
    for recurso in RECURSOS:
        respuesta = cliente.patch(f"/api/{recurso}/1/estado", json=datos)
        assert respuesta.status_code == 400
        assert respuesta.get_json()["error"]["code"] == 400
        assert cliente.get(f"/api/{recurso}/1").get_json()["activo"] is True


@pytest.mark.parametrize("cuerpo", ["{", "null", "[]", '"texto"', "false"])
def test_json_invalido_no_cambia_estados(cuerpo):
    _, cliente = escenario()
    for recurso in RECURSOS:
        respuesta = cliente.patch(f"/api/{recurso}/1/estado", data=cuerpo, content_type="application/json")
        assert respuesta.status_code == 400
        assert respuesta.is_json
        assert cliente.get(f"/api/{recurso}/1").get_json()["activo"] is True


@pytest.mark.parametrize("identificador,estado", [(999, 404), (0, 400), ("texto", 404), ("-1", 404)])
def test_referencias_invalidas_o_inexistentes(identificador, estado):
    _, cliente = escenario()
    for recurso in RECURSOS:
        respuesta = cliente.patch(f"/api/{recurso}/{identificador}/estado", json={"activo": False})
        assert respuesta.status_code == estado
        assert respuesta.get_json()["error"]["code"] == estado


@pytest.mark.parametrize("filtro", ["", "inactivo", "ACTIVOS", "activos&estado=todos"])
def test_filtros_invalidos_son_400(filtro):
    _, cliente = escenario()
    for recurso in RECURSOS:
        respuesta = cliente.get(f"/api/{recurso}?estado={filtro}")
        assert respuesta.status_code == 400
        assert respuesta.is_json


def test_categorias_bloqueadas_con_productos_activos_y_relaciones_historicas_conservadas():
    _, cliente = escenario()
    original = cliente.get("/api/categorias/1").get_json()
    respuesta = cliente.patch("/api/categorias/1/estado", json={"activo": False})
    assert respuesta.status_code == 409
    assert "productos activos" in respuesta.get_json()["error"]["message"]
    assert cliente.get("/api/categorias/1").get_json() == original
    cliente.patch("/api/productos/1/estado", json={"activo": False})
    assert cliente.patch("/api/categorias/1/estado", json={"activo": False}).status_code == 200
    producto = cliente.get("/api/productos/1").get_json()
    assert producto["activo"] is False
    assert producto["categoria"] == {**original, "activo": False}
    assert cliente.post("/api/productos", json={"codigo": "NUEVO", "nombre": "Otro", "categoria_id": 1, "precio": "1"}).status_code == 409
    activa = cliente.post("/api/categorias", json={"codigo": "ACTIVA", "nombre": "Activa"}).get_json()
    nuevo = cliente.post("/api/productos", json={"codigo": "NUEVO", "nombre": "Otro", "categoria_id": activa["id"], "precio": "1"}).get_json()
    assert cliente.put(f'/api/productos/{nuevo["id"]}', json={"codigo": "CAMBIO", "nombre": "Cambio", "categoria_id": 1, "precio": "2"}).status_code == 409
    assert cliente.get(f'/api/productos/{nuevo["id"]}').get_json() == nuevo


@pytest.mark.parametrize("recurso", ["productos", "ubicaciones"])
def test_minimos_historicos_no_se_borran_y_escrituras_con_inactivos_son_409(recurso):
    _, cliente = escenario()
    assert cliente.patch(f"/api/{recurso}/1/estado", json={"activo": False}).status_code == 200
    historico = cliente.get("/api/ubicaciones/1/minimos")
    assert historico.status_code == 200
    assert historico.get_json()["minimos"][0]["minimo"] == 0
    entidad = historico.get_json()["minimos"][0]["producto"] if recurso == "productos" else historico.get_json()["ubicacion"]
    assert entidad["activo"] is False
    assert cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 9}).status_code == 409
    assert cliente.get("/api/ubicaciones/1/minimos").get_json() == historico.get_json()


def test_cd_no_se_desactiva_y_no_permite_otro_cd():
    _, cliente = escenario()
    cd = cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"}).get_json()
    respuesta = cliente.patch(f'/api/ubicaciones/{cd["id"]}/estado', json={"activo": False})
    assert respuesta.status_code == 409
    assert "política de reemplazo" in respuesta.get_json()["error"]["message"]
    assert cliente.get(f'/api/ubicaciones/{cd["id"]}').get_json() == cd
    assert cliente.post("/api/ubicaciones", json={"codigo": "CD2", "nombre": "Otra", "tipo": "CD"}).status_code == 409


def test_no_hay_cambio_de_estado_por_put_ni_por_alta_y_el_tipo_http_es_obligatorio():
    _, cliente = escenario()
    for recurso in RECURSOS:
        assert cliente.patch(f"/api/{recurso}/1/estado", data="activo=false").status_code == 415
        assert cliente.put(f"/api/{recurso}/1", json={"codigo": "CAMBIO", "nombre": "Otro", "activo": False}).status_code == 400
        assert cliente.post(f"/api/{recurso}", json={"codigo": "CAMBIO", "nombre": "Otro", "activo": False}).status_code == 400
        assert cliente.get(f"/api/{recurso}/1").get_json()["activo"] is True
    assert cliente.get("/api/health").get_json() == {"status": "ok"}


def test_baja_repetida_concurrente_y_aislamiento_entre_aplicaciones():
    app, cliente = escenario()
    _, otro_cliente = escenario()

    def desactivar(_):
        with app.test_client() as temporal:
            respuesta = temporal.patch("/api/proveedores/1/estado", json={"activo": False})
            return respuesta.status_code, respuesta.get_json()

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        respuestas = list(ejecutor.map(desactivar, range(4)))
    assert all(estado == 200 and not cuerpo["activo"] for estado, cuerpo in respuestas)
    assert len(cliente.get("/api/proveedores?estado=todos").get_json()["proveedores"]) == 1
    assert otro_cliente.get("/api/proveedores/1").get_json()["activo"] is True


def test_carrera_alta_producto_y_baja_categoria_no_deja_asociacion_activa_invalida():
    app, cliente = escenario()
    categoria = cliente.post("/api/categorias", json={"codigo": "LIBRE", "nombre": "Libre"}).get_json()

    def ejecutar(accion):
        with app.test_client() as temporal:
            if accion == "alta":
                return temporal.post("/api/productos", json={"codigo": "SEG", "nombre": "Otro", "categoria_id": categoria["id"], "precio": "1"}).status_code
            return temporal.patch(f'/api/categorias/{categoria["id"]}/estado', json={"activo": False}).status_code

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        alta, baja = list(ejecutor.map(ejecutar, ["alta", "baja"]))
    assert (alta, baja) in [(201, 409), (409, 200)]
    actual = cliente.get(f'/api/categorias/{categoria["id"]}').get_json()
    productos = cliente.get("/api/productos").get_json()["productos"]
    assert actual["activo"] or all(item["categoria"]["id"] != categoria["id"] for item in productos)


def test_carrera_baja_producto_y_escritura_minimo_conserva_configuracion_confirmada():
    app, cliente = escenario()

    def ejecutar(accion):
        with app.test_client() as temporal:
            if accion == "minimo":
                return temporal.put("/api/ubicaciones/1/minimos/1", json={"minimo": 9}).status_code
            return temporal.patch("/api/productos/1/estado", json={"activo": False}).status_code

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        escritura, baja = list(ejecutor.map(ejecutar, ["minimo", "baja"]))
    assert escritura in (200, 409) and baja == 200
    assert cliente.get("/api/productos/1").get_json()["activo"] is False
    configuraciones = cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"]
    assert len(configuraciones) == 1
    assert configuraciones[0]["minimo"] == (9 if escritura == 200 else 0)
