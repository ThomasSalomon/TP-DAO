"""Contratos HTTP y concurrencia de ubicaciones en el catálogo compartido."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import create_app


def test_altas_listado_consulta_edicion_memoria_y_aislamiento():
    app = create_app()
    cliente = app.test_client()
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": []}
    cd = cliente.post("/api/ubicaciones", json={"codigo": " CD01 ", "nombre": " Central ", "tipo": "CD"})
    assert cd.status_code == 201
    assert cd.headers["Location"] == "/api/ubicaciones/1"
    assert cd.get_json() == {"id": 1, "codigo": "CD01", "nombre": "Central", "tipo": "CD"}
    assert cliente.get(cd.headers["Location"]).get_json() == cd.get_json()
    for codigo in ["0001", "0002"]:
        local = cliente.post("/api/ubicaciones", json={"codigo": codigo, "nombre": "Local", "tipo": "LOCAL"})
        assert local.status_code == 201
        assert local.get_json()["codigo"] == codigo
        assert local.get_json()["tipo"] == "LOCAL"
    actualizado = cliente.put("/api/ubicaciones/1", json={"codigo": "CD02", "nombre": " Nueva central "})
    assert actualizado.status_code == 200
    assert actualizado.get_json() == {"id": 1, "codigo": "CD02", "nombre": "Nueva central", "tipo": "CD"}
    assert app.test_client().get("/api/ubicaciones/1").get_json() == actualizado.get_json()
    listado = cliente.get("/api/ubicaciones").get_json()["ubicaciones"]
    assert len(listado) == 3
    assert listado[0] == actualizado.get_json()
    otra = create_app().test_client()
    assert otra.get("/api/ubicaciones").get_json() == {"ubicaciones": []}
    assert otra.post("/api/ubicaciones", json={"codigo": "CD01", "nombre": "Central", "tipo": "CD"}).status_code == 201
    assert cliente.get("/api/health").get_json() == {"status": "ok"}


def test_segundo_cd_es_409_desde_api_directa_sin_consumir_codigo_o_id():
    cliente = create_app().test_client()
    original = cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"}).get_json()
    respuesta = cliente.post("/api/ubicaciones", json={"codigo": "LIBRE", "nombre": "Otra central", "tipo": "CD"})
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["code"] == 409
    assert respuesta.get_json()["error"]["fields"]["tipo"]
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": [original]}
    local = cliente.post("/api/ubicaciones", json={"codigo": "LIBRE", "nombre": "Local", "tipo": "LOCAL"})
    assert local.status_code == 201
    assert local.get_json()["id"] == 2


def test_cd_con_nombre_invalido_no_reserva_cardinalidad_codigo_o_id():
    cliente = create_app().test_client()
    assert cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": " ", "tipo": "CD"}).status_code == 400
    respuesta = cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"})
    assert respuesta.status_code == 201
    assert respuesta.get_json()["id"] == 1


@pytest.mark.parametrize("metodo,ruta", [("post", "/api/ubicaciones"), ("put", "/api/ubicaciones/1")])
@pytest.mark.parametrize("cuerpo", ["{", "null", "[]", '"texto"', "true"])
def test_json_invalido_no_cambia_registros(metodo, ruta, cuerpo):
    cliente = create_app().test_client()
    original = cliente.post("/api/ubicaciones", json={"codigo": "L", "nombre": "Local", "tipo": "LOCAL"}).get_json()
    respuesta = getattr(cliente, metodo)(ruta, data=cuerpo, content_type="application/json")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["code"] == 400
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": [original]}


@pytest.mark.parametrize("datos", [
    {}, {"codigo": "NUEVO"}, {"nombre": "Otro"},
    {"codigo": 1, "nombre": "Otro"}, {"codigo": True, "nombre": "Otro"},
    {"codigo": "NUEVO", "nombre": None}, {"codigo": "NUEVO", "nombre": []},
    {"codigo": " ", "nombre": "Otro"}, {"codigo": "NUEVO", "nombre": " "},
    {"codigo": "NUEVO", "nombre": "Otro", "id": 99},
])
def test_campos_invalidos_sin_modificaciones_parciales(datos):
    cliente = create_app().test_client()
    original = cliente.post("/api/ubicaciones", json={"codigo": "L", "nombre": "Local", "tipo": "LOCAL"}).get_json()
    assert cliente.post("/api/ubicaciones", json={**datos, "tipo": "LOCAL"}).status_code == 400
    assert cliente.put("/api/ubicaciones/1", json=datos).status_code == 400
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": [original]}
    assert cliente.post("/api/ubicaciones", json={"codigo": "NUEVO", "nombre": "Válido", "tipo": "LOCAL"}).status_code == 201


@pytest.mark.parametrize("tipo", [None, True, 1, [], "", "local", "DEPOSITO"])
def test_tipo_invalido_no_registra_ubicacion(tipo):
    cliente = create_app().test_client()
    respuesta = cliente.post("/api/ubicaciones", json={"codigo": "L", "nombre": "Local", "tipo": tipo})
    assert respuesta.status_code == 400
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": []}


def test_tipo_obligatorio_en_alta():
    cliente = create_app().test_client()
    respuesta = cliente.post("/api/ubicaciones", json={"codigo": "L", "nombre": "Local"})
    assert respuesta.status_code == 400
    assert "tipo" in respuesta.get_json()["error"]["fields"]


@pytest.mark.parametrize("origen,destino", [("LOCAL", "CD"), ("CD", "LOCAL"), ("LOCAL", "LOCAL")])
def test_tipo_no_es_un_campo_editable_ni_siquiera_si_se_conserva(origen, destino):
    cliente = create_app().test_client()
    original = cliente.post("/api/ubicaciones", json={"codigo": "A", "nombre": "Original", "tipo": origen}).get_json()
    respuesta = cliente.put("/api/ubicaciones/1", json={"codigo": "B", "nombre": "Cambio", "tipo": destino})
    assert respuesta.status_code == 400
    assert "tipo" in respuesta.get_json()["error"]["fields"]
    assert cliente.get("/api/ubicaciones/1").get_json() == original


def test_conflictos_normalizados_entre_tipos_y_codigos_historicos():
    cliente = create_app().test_client()
    cd = cliente.post("/api/ubicaciones", json={"codigo": "CD01", "nombre": "Central", "tipo": "CD"}).get_json()
    local = cliente.post("/api/ubicaciones", json={"codigo": "L01", "nombre": "Local", "tipo": "LOCAL"}).get_json()
    assert cliente.post("/api/ubicaciones", json={"codigo": " cd01 ", "nombre": "Otro", "tipo": "LOCAL"}).status_code == 409
    respuesta = cliente.put("/api/ubicaciones/2", json={"codigo": " cd01 ", "nombre": "Otro"})
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["fields"]["codigo"]
    assert cliente.get("/api/ubicaciones/2").get_json() == local
    assert cliente.put("/api/ubicaciones/1", json={"codigo": " cd01 ", "nombre": "Central actual"}).status_code == 200
    assert cliente.put("/api/ubicaciones/1", json={"codigo": "CD02", "nombre": "Actual"}).status_code == 200
    assert cliente.post("/api/ubicaciones", json={"codigo": "CD01", "nombre": "Reutilizar", "tipo": "LOCAL"}).status_code == 409
    assert cliente.put("/api/ubicaciones/1", json={"codigo": "CD01", "nombre": "Volver"}).status_code == 409
    assert cliente.get("/api/ubicaciones/1").get_json() == {**cd, "codigo": "CD02", "nombre": "Actual"}


@pytest.mark.parametrize("identificador,estado", [(0, 400), (999, 404), ("-1", 404), ("texto", 404)])
def test_identificador_invalido_o_ubicacion_inexistente(identificador, estado):
    cliente = create_app().test_client()
    ruta = f"/api/ubicaciones/{identificador}"
    for respuesta in [cliente.get(ruta), cliente.put(ruta, json={"codigo": "L", "nombre": "Local"})]:
        assert respuesta.status_code == estado
        assert respuesta.get_json()["error"]["code"] == estado
    assert cliente.get("/api/ubicaciones").get_json() == {"ubicaciones": []}


def test_tipo_de_contenido_baja_no_disponible_y_respuestas_sin_atributos_internos():
    cliente = create_app().test_client()
    assert cliente.post("/api/ubicaciones", data="codigo=L").status_code == 415
    assert cliente.put("/api/ubicaciones/1", data="codigo=L").status_code == 415
    respuesta = cliente.delete("/api/ubicaciones/1")
    assert respuesta.status_code == 405
    assert respuesta.is_json
    assert "PUT" in respuesta.headers["Allow"]
    ubicacion = cliente.post("/api/ubicaciones", json={"codigo": "L", "nombre": "Local", "tipo": "LOCAL"})
    assert set(ubicacion.get_json()) == {"id", "codigo", "nombre", "tipo"}


@pytest.mark.parametrize("codigos,tipos", [
    (["CD1", "CD2", "L1", "L2"], ["CD", "CD", "LOCAL", "LOCAL"]),
    (["ABC", " abc ", "L1", "L2"], ["LOCAL", "LOCAL", "LOCAL", "LOCAL"]),
])
def test_concurrencia_protege_cardinalidad_unicidad_e_ids(codigos, tipos):
    app = create_app()

    def registrar(entrada):
        codigo, tipo = entrada
        with app.test_client() as cliente:
            return cliente.post("/api/ubicaciones", json={"codigo": codigo, "nombre": "Ubicación", "tipo": tipo}).status_code

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        estados = list(ejecutor.map(registrar, zip(codigos, tipos)))
    assert sorted(estados) == [201, 201, 201, 409]
    registros = app.test_client().get("/api/ubicaciones").get_json()["ubicaciones"]
    assert {item["id"] for item in registros} == {1, 2, 3}
    assert len({item["codigo"].casefold() for item in registros}) == 3
    assert sum(item["tipo"] == "CD" for item in registros) == (1 if "CD" in tipos else 0)


def test_convivencia_con_categorias_productos_proveedores_y_salud():
    cliente = create_app().test_client()
    categoria = cliente.post("/api/categorias", json={"codigo": "001", "nombre": "Almacén"}).get_json()
    proveedor = cliente.post("/api/proveedores", json={"codigo": "001", "nombre": "Distribuidora"}).get_json()
    producto = cliente.post("/api/productos", json={"codigo": "001", "nombre": "Arroz", "categoria_id": categoria["id"], "precio": "125.50"}).get_json()
    assert cliente.post("/api/ubicaciones", json={"codigo": "001", "nombre": "Local", "tipo": "LOCAL"}).status_code == 201
    assert cliente.get("/api/categorias/1").get_json() == categoria
    assert cliente.get("/api/proveedores/1").get_json() == proveedor
    assert cliente.get("/api/productos/1").get_json() == producto
    assert cliente.get("/api/health").get_json() == {"status": "ok"}
