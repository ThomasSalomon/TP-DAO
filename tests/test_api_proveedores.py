"""Contratos HTTP de proveedores y convivencia con el catálogo existente."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import create_app


def test_recorrido_alta_listado_consulta_edicion_y_memoria_entre_clientes():
    app = create_app()
    cliente = app.test_client()
    assert cliente.get("/api/proveedores").get_json() == {"proveedores": []}
    respuesta = cliente.post("/api/proveedores", json={"codigo": " 0001 ", "nombre": " Mayorista "})
    assert respuesta.status_code == 201
    assert respuesta.headers["Location"] == "/api/proveedores/1"
    assert respuesta.get_json() == {"id": 1, "codigo": "0001", "nombre": "Mayorista", "activo": True}
    assert cliente.get(respuesta.headers["Location"]).get_json() == respuesta.get_json()
    mismo_nombre = cliente.post("/api/proveedores", json={"codigo": "0002", "nombre": "Mayorista"})
    assert mismo_nombre.status_code == 201
    respuesta = cliente.put("/api/proveedores/1", json={"codigo": " A01 ", "nombre": " Actualizado "})
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"id": 1, "codigo": "A01", "nombre": "Actualizado", "activo": True}
    assert app.test_client().get("/api/proveedores/1").get_json() == respuesta.get_json()
    assert cliente.get("/api/proveedores").get_json() == {
        "proveedores": [respuesta.get_json(), mismo_nombre.get_json()]
    }
    assert create_app().test_client().get("/api/proveedores").get_json() == {"proveedores": []}
    assert cliente.get("/api/health").get_json() == {"status": "ok"}
    # Comparte catálogo con categorías/productos sin compartir su unicidad.
    categoria = cliente.post("/api/categorias", json={"codigo": "A01", "nombre": "Almacén"})
    assert categoria.status_code == 201
    producto = cliente.post("/api/productos", json={
        "codigo": "A01", "nombre": "Arroz", "categoria_id": categoria.get_json()["id"], "precio": "1",
    })
    assert producto.status_code == 201
    assert cliente.get("/api/productos/1").get_json()["categoria"] == categoria.get_json()


@pytest.mark.parametrize("metodo,ruta", [("post", "/api/proveedores"), ("put", "/api/proveedores/1")])
@pytest.mark.parametrize("cuerpo", ["{", "null", "[]", '"texto"', "true"])
def test_json_invalido_no_altera_proveedor(metodo, ruta, cuerpo):
    cliente = create_app().test_client()
    original = cliente.post("/api/proveedores", json={"codigo": "A", "nombre": "Uno"}).get_json()
    respuesta = getattr(cliente, metodo)(ruta, data=cuerpo, content_type="application/json")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["code"] == 400
    assert cliente.get("/api/proveedores").get_json() == {"proveedores": [original]}


@pytest.mark.parametrize("datos", [
    {}, {"codigo": "NUEVO"}, {"nombre": "Otro"},
    {"codigo": 1, "nombre": "Otro"}, {"codigo": "NUEVO", "nombre": None},
    {"codigo": True, "nombre": "Otro"}, {"codigo": "NUEVO", "nombre": []},
    {"codigo": "NUEVO", "nombre": "Otro", "id": 99},
    {"codigo": "NUEVO", "nombre": "Otro", "cuit": "inventado"},
    {"codigo": " ", "nombre": "Otro"}, {"codigo": "NUEVO", "nombre": " "},
])
def test_campos_y_validaciones_de_dominio_sin_efectos_parciales(datos):
    cliente = create_app().test_client()
    original = cliente.post("/api/proveedores", json={"codigo": "A", "nombre": "Uno"}).get_json()
    for metodo, ruta in [("post", "/api/proveedores"), ("put", "/api/proveedores/1")]:
        respuesta = getattr(cliente, metodo)(ruta, json=datos)
        assert respuesta.status_code == 400
        assert respuesta.is_json
        assert cliente.get("/api/proveedores").get_json() == {"proveedores": [original]}
    assert cliente.post("/api/proveedores", json={"codigo": "NUEVO", "nombre": "Válido"}).status_code == 201


def test_conflictos_actuales_e_historicos_y_codigo_actual_con_otro_uso_de_mayusculas():
    cliente = create_app().test_client()
    cliente.post("/api/proveedores", json={"codigo": "ABC", "nombre": "Uno"})
    segundo = cliente.post("/api/proveedores", json={"codigo": "002", "nombre": "Dos"}).get_json()
    for metodo, ruta in [("post", "/api/proveedores"), ("put", "/api/proveedores/2")]:
        respuesta = getattr(cliente, metodo)(ruta, json={"codigo": " abc ", "nombre": "Cambio"})
        assert respuesta.status_code == 409
        assert respuesta.get_json()["error"]["fields"]["codigo"]
    assert cliente.get("/api/proveedores/2").get_json() == segundo
    assert cliente.put("/api/proveedores/1", json={"codigo": " abc ", "nombre": "Renombrado"}).status_code == 200
    cliente.put("/api/proveedores/1", json={"codigo": "NUEVO", "nombre": "Actual"})
    for metodo, ruta in [("post", "/api/proveedores"), ("put", "/api/proveedores/2"), ("put", "/api/proveedores/1")]:
        assert getattr(cliente, metodo)(ruta, json={"codigo": "ABC", "nombre": "Reutilizar"}).status_code == 409
    assert cliente.get("/api/proveedores/1").get_json() == {"id": 1, "codigo": "NUEVO", "nombre": "Actual", "activo": True}


@pytest.mark.parametrize("identificador,estado", [(0, 400), (999, 404), ("-1", 404), ("texto", 404)])
def test_identificador_invalido_o_proveedor_inexistente(identificador, estado):
    cliente = create_app().test_client()
    ruta = f"/api/proveedores/{identificador}"
    for respuesta in [cliente.get(ruta), cliente.put(ruta, json={"codigo": "A", "nombre": "Uno"})]:
        assert respuesta.status_code == estado
        assert respuesta.get_json()["error"]["code"] == estado
    assert cliente.get("/api/proveedores").get_json() == {"proveedores": []}


def test_tipo_de_contenido_y_baja_no_permitida():
    cliente = create_app().test_client()
    assert cliente.post("/api/proveedores", data="codigo=A").status_code == 415
    respuesta = cliente.delete("/api/proveedores/1")
    assert respuesta.status_code == 405
    assert respuesta.is_json
    assert "PUT" in respuesta.headers["Allow"]


def test_alta_concurrente_protege_codigo_e_identificadores():
    app = create_app()

    def registrar(codigo):
        with app.test_client() as cliente:
            respuesta = cliente.post("/api/proveedores", json={"codigo": codigo, "nombre": "Mayorista"})
            return respuesta.status_code

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        estados = list(ejecutor.map(registrar, ["A", " a ", "B", "C"]))
    assert sorted(estados) == [201, 201, 201, 409]
    registros = app.test_client().get("/api/proveedores").get_json()["proveedores"]
    assert {item["id"] for item in registros} == {1, 2, 3}
    assert len({item["codigo"].casefold() for item in registros}) == 3


def test_fallo_inesperado_es_generico_no_expone_internos_y_libera_bloqueo(monkeypatch):
    app = create_app()

    def fallar(*argumentos):
        raise RuntimeError("detalle interno privado")

    monkeypatch.setattr(app.extensions["catalogo"], "crear_proveedor", fallar)
    cliente = app.test_client()
    respuesta = cliente.post("/api/proveedores", json={"codigo": "A", "nombre": "Uno"})
    assert respuesta.status_code == 500
    assert respuesta.is_json
    assert "privado" not in respuesta.get_data(as_text=True)
    assert cliente.get("/api/proveedores").get_json() == {"proveedores": []}
