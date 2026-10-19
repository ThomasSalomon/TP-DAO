from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import create_app


def cliente_con_producto():
    cliente = create_app().test_client()
    categoria = cliente.post(
        "/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"}
    ).get_json()
    datos = {"codigo": "001", "nombre": "Arroz", "categoria_id": categoria["id"],
             "precio": "125.50"}
    producto = cliente.post("/api/productos", json=datos).get_json()
    return cliente, categoria, producto, datos


def test_altas_listados_consultas_y_respuestas_registradas():
    cliente = create_app().test_client()
    assert cliente.get("/api/categorias").get_json() == {"categorias": []}
    assert cliente.get("/api/productos").get_json() == {"productos": []}

    respuesta = cliente.post(
        "/api/categorias", json={"codigo": " ALM ", "nombre": " Almacén "}
    )
    categoria = respuesta.get_json()
    assert respuesta.status_code == 201
    assert respuesta.headers["Location"] == f'/api/categorias/{categoria["id"]}'
    assert categoria == {"id": categoria["id"], "codigo": "ALM", "nombre": "Almacén", "activo": True}
    assert type(categoria["id"]) is int
    assert cliente.get(respuesta.headers["Location"]).get_json() == categoria

    respuesta = cliente.post("/api/productos", json={
        "codigo": " 001 ", "nombre": " Arroz ", "categoria_id": categoria["id"],
        "precio": "12345678901234567890.12",
    })
    producto = respuesta.get_json()
    assert respuesta.status_code == 201
    assert respuesta.headers["Location"] == f'/api/productos/{producto["id"]}'
    assert producto == {
        "id": producto["id"], "codigo": "001", "nombre": "Arroz",
        "activo": True,
        "categoria": categoria, "precio": "12345678901234567890.12", "moneda": "ARS",
    }
    assert cliente.get(respuesta.headers["Location"]).get_json() == producto
    assert cliente.get("/api/categorias").get_json() == {"categorias": [categoria]}
    assert cliente.get("/api/productos").get_json() == {"productos": [producto]}
    assert cliente.get("/api/health").get_json() == {"status": "ok"}


def test_modificar_categoria_actualiza_productos_y_modificar_producto_cambia_categoria():
    cliente, categoria, producto, datos = cliente_con_producto()
    url_categoria = f'/api/categorias/{categoria["id"]}'
    respuesta = cliente.put(url_categoria, json={"codigo": "COM", "nombre": "Comestibles"})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["id"] == categoria["id"]
    assert cliente.get(f'/api/productos/{producto["id"]}').get_json()["categoria"] == (
        respuesta.get_json()
    )

    otra = cliente.post("/api/categorias", json={"codigo": "BEB", "nombre": "Bebidas"})
    respuesta = cliente.put(f'/api/productos/{producto["id"]}', json={
        **datos, "codigo": "002", "nombre": "Agua", "precio": "0.1",
        "categoria_id": otra.get_json()["id"],
    })
    assert respuesta.status_code == 200
    actualizado = respuesta.get_json()
    assert actualizado["id"] == producto["id"]
    assert actualizado["codigo"] == "002"
    assert actualizado["precio"] == "0.10"
    assert actualizado["categoria"] == otra.get_json()
    assert cliente.get("/api/productos").get_json() == {"productos": [actualizado]}


@pytest.mark.parametrize("ruta", ["/api/categorias", "/api/productos"])
@pytest.mark.parametrize("cuerpo", ["{", "null", "[]", '"texto"', "true"])
def test_json_mal_formado_o_no_objeto_no_modifica_catalogo(ruta, cuerpo):
    cliente = create_app().test_client()

    respuesta = cliente.post(ruta, data=cuerpo, content_type="application/json")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["code"] == 400
    assert cliente.get(ruta).get_json() == {ruta.rsplit("/", 1)[1]: []}


def test_tipo_de_contenido_y_campos_invalidos_son_explicitos():
    cliente = create_app().test_client()
    respuesta = cliente.post("/api/categorias", data="codigo=ALM")
    assert respuesta.status_code == 415
    respuesta = cliente.post("/api/categorias", json={"codigo": 1, "id": 99})
    assert respuesta.status_code == 400
    assert set(respuesta.get_json()["error"]["fields"]) == {"codigo", "nombre", "id"}
    assert cliente.get("/api/categorias").get_json() == {"categorias": []}


@pytest.mark.parametrize("recurso", ["categorias", "productos"])
def test_duplicados_en_alta_y_edicion_devuelven_409_sin_cambios(recurso):
    cliente, categoria, producto, datos_producto = cliente_con_producto()
    datos = {"codigo": " alm ", "nombre": "Otro"} if recurso == "categorias" else {
        **datos_producto, "codigo": " 001 ", "nombre": "Otro"
    }
    ruta = f"/api/{recurso}"
    anterior = cliente.get(ruta).get_json()
    respuesta = cliente.post(ruta, json=datos)
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["fields"]["codigo"]
    assert cliente.get(ruta).get_json() == anterior

    nuevo = cliente.post(ruta, json={**datos, "codigo": "NUEVO"}).get_json()
    respuesta = cliente.put(f'{ruta}/{nuevo["id"]}', json=datos)
    assert respuesta.status_code == 409
    assert cliente.get(f'{ruta}/{nuevo["id"]}').get_json() == nuevo


@pytest.mark.parametrize("recurso", ["categorias", "productos"])
def test_identificadores_inexistentes_en_consulta_y_edicion(recurso):
    cliente, _, _, datos = cliente_con_producto()
    datos = {"codigo": "NUEVO", "nombre": "Nuevo"} if recurso == "categorias" else datos

    assert cliente.get(f"/api/{recurso}/999").status_code == 404
    respuesta = cliente.put(f"/api/{recurso}/999", json=datos)
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"]["code"] == 404


@pytest.mark.parametrize("categoria_id", [None, True, "1", 1.0, 0, 999])
def test_categoria_invalida_no_crea_ni_modifica_producto(categoria_id):
    cliente, _, producto, datos = cliente_con_producto()
    nuevos = {**datos, "codigo": "002", "nombre": "Nuevo", "categoria_id": categoria_id}
    esperado = 404 if categoria_id == 999 else 400

    assert cliente.post("/api/productos", json=nuevos).status_code == esperado
    respuesta = cliente.put(f'/api/productos/{producto["id"]}', json=nuevos)
    assert respuesta.status_code == esperado
    assert cliente.get("/api/productos").get_json() == {"productos": [producto]}


def test_no_se_puede_inyectar_un_objeto_categoria_sin_registrar():
    cliente, _, producto, datos = cliente_con_producto()
    datos.pop("categoria_id")
    respuesta = cliente.post("/api/productos", json={
        **datos, "codigo": "002", "categoria": {"id": 999, "nombre": "Inventada"},
    })
    assert respuesta.status_code == 400
    assert cliente.get("/api/productos").get_json() == {"productos": [producto]}


@pytest.mark.parametrize("precio", [None, True, 1, 1.25, "0", "-1", "1.230", "NaN"])
def test_precios_invalidos_no_dejan_efectos_parciales(precio):
    cliente, _, producto, datos = cliente_con_producto()
    nuevos = {**datos, "codigo": "NUEVO", "nombre": "Otro", "precio": precio}

    assert cliente.post("/api/productos", json=nuevos).status_code == 400
    respuesta = cliente.put(f'/api/productos/{producto["id"]}', json=nuevos)
    assert respuesta.status_code == 400
    assert cliente.get("/api/productos").get_json() == {"productos": [producto]}


def test_modificacion_invalida_de_categoria_conserva_referencias():
    cliente, categoria, producto, _ = cliente_con_producto()
    respuesta = cliente.put(f'/api/categorias/{categoria["id"]}', json={
        "codigo": "NUEVO", "nombre": " ",
    })
    assert respuesta.status_code == 400
    assert cliente.get("/api/categorias").get_json() == {"categorias": [categoria]}
    assert cliente.get("/api/productos").get_json() == {"productos": [producto]}


def test_misma_aplicacion_conserva_memoria_y_otras_instancias_estan_aisladas():
    app = create_app()
    primero = app.test_client()
    categoria = primero.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"})
    segundo = app.test_client()
    assert segundo.get("/api/categorias").get_json() == {"categorias": [categoria.get_json()]}
    assert create_app().test_client().get("/api/categorias").get_json() == {"categorias": []}


def test_solicitudes_concurrentes_no_duplican_codigos_ni_identificadores():
    app = create_app()

    def registrar(codigo):
        with app.test_client() as cliente:
            respuesta = cliente.post("/api/categorias", json={"codigo": codigo, "nombre": codigo})
            return respuesta.status_code

    with ThreadPoolExecutor(max_workers=4) as grupo:
        estados = list(grupo.map(registrar, ["ALM", "alm", "BEB", "LIM"]))

    assert sorted(estados) == [201, 201, 201, 409]
    categorias = app.test_client().get("/api/categorias").get_json()["categorias"]
    assert len({item["id"] for item in categorias}) == 3
    assert len({item["codigo"].casefold() for item in categorias}) == 3


def test_bajas_no_disponibles_y_errores_no_exponen_objetos_internos():
    cliente, _, producto, _ = cliente_con_producto()
    respuesta = cliente.delete(f'/api/productos/{producto["id"]}')
    assert respuesta.status_code == 405
    assert "PUT" in respuesta.headers["Allow"]
    assert respuesta.mimetype == "application/json"
    assert "_catalogo" not in cliente.get("/api/productos").get_data(as_text=True)
    assert "Traceback" not in respuesta.get_data(as_text=True)


def test_fallo_inesperado_es_500_y_no_expone_detalle_interno(monkeypatch):
    app = create_app()

    def fallar(*argumentos):
        raise RuntimeError("detalle interno de prueba")

    monkeypatch.setattr(app.extensions["catalogo"], "crear_categoria", fallar)
    respuesta = app.test_client().post(
        "/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"}
    )

    assert respuesta.status_code == 500
    assert respuesta.get_json() == {"error": {"code": 500, "message": "Internal Server Error"}}
    assert "detalle interno" not in respuesta.get_data(as_text=True)
    assert app.test_client().get("/api/categorias").get_json() == {"categorias": []}
