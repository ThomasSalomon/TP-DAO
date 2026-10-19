"""HTTP de configuración por producto/local, sin inventario operativo."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import create_app


def aplicacion_para_minimos():
    app = create_app()
    cliente = app.test_client()
    categoria = cliente.post("/api/categorias", json={"codigo": "ALM", "nombre": "Almacén"}).get_json()
    producto = cliente.post("/api/productos", json={
        "codigo": "001", "nombre": "Arroz", "categoria_id": categoria["id"], "precio": "125.50",
    }).get_json()
    local = cliente.post("/api/ubicaciones", json={"codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"}).get_json()
    return app, cliente, producto, local


def test_consulta_ausencia_cero_y_establecimiento_repetido():
    _, cliente, producto, local = aplicacion_para_minimos()
    ruta = f'/api/ubicaciones/{local["id"]}/minimos'
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"ubicacion": local, "minimos": []}
    for minimo in [0, 12, 12, 0]:
        respuesta = cliente.put(f'{ruta}/{producto["id"]}', json={"minimo": minimo})
        assert respuesta.status_code == 200
        configuracion = {"producto": {campo: producto[campo] for campo in ["id", "codigo", "nombre", "activo"]}, "minimo": minimo}
        assert respuesta.get_json() == {"ubicacion": local, **configuracion}
        assert cliente.get(ruta).get_json() == {"ubicacion": local, "minimos": [configuracion]}


def test_independencia_de_locales_y_memoria_entre_solicitudes_de_la_misma_aplicacion():
    app, cliente, producto, local = aplicacion_para_minimos()
    otro = cliente.post("/api/ubicaciones", json={"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"}).get_json()
    for ubicacion, minimo in [(local, 4), (otro, 20)]:
        assert cliente.put(f'/api/ubicaciones/{ubicacion["id"]}/minimos/{producto["id"]}', json={"minimo": minimo}).status_code == 200
        consulta = app.test_client().get(f'/api/ubicaciones/{ubicacion["id"]}/minimos')
        assert consulta.get_json()["minimos"][0]["minimo"] == minimo
    otra_app, otro_cliente, _, otro_local = aplicacion_para_minimos()
    assert otra_app is not app
    assert otro_cliente.get(f'/api/ubicaciones/{otro_local["id"]}/minimos').get_json()["minimos"] == []


@pytest.mark.parametrize("cuerpo", ["{", "null", "[]", '"texto"', "true"])
def test_json_invalido_no_altera_configuracion(cuerpo):
    _, cliente, _, _ = aplicacion_para_minimos()
    cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 8})
    respuesta = cliente.put("/api/ubicaciones/1/minimos/1", data=cuerpo, content_type="application/json")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["code"] == 400
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"][0]["minimo"] == 8


@pytest.mark.parametrize("datos", [
    {}, {"minimo": -1}, {"minimo": 0.5}, {"minimo": 1.0}, {"minimo": True},
    {"minimo": False}, {"minimo": None}, {"minimo": "0"}, {"minimo": []}, {"minimo": {}},
    {"minimo": 3, "disponible": 99}, {"minimo": 3, "producto_id": 2},
    {"minimo": 2**53},
])
def test_datos_invalidos_no_crean_ni_modifican_minimos(datos):
    _, cliente, _, _ = aplicacion_para_minimos()
    assert cliente.put("/api/ubicaciones/1/minimos/1", json=datos).status_code == 400
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"] == []
    cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 6})
    respuesta = cliente.put("/api/ubicaciones/1/minimos/1", json=datos)
    assert respuesta.status_code == 400
    assert respuesta.is_json
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"][0]["minimo"] == 6


def test_limite_tecnico_json_exacto_y_salida_sin_redondeo_silencioso():
    app, cliente, _, _ = aplicacion_para_minimos()
    respuesta = cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 2**53 - 1})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["minimo"] == 2**53 - 1
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"][0]["minimo"] == 2**53 - 1
    app.extensions["catalogo"].establecer_minimo(1, 1, 10**30)
    respuesta = cliente.get("/api/ubicaciones/1/minimos")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["fields"]["minimo"]


@pytest.mark.parametrize("local_id,producto_id,estado", [
    (999, 1, 404), (1, 999, 404), (0, 1, 400), (1, 0, 400),
    ("texto", 1, 404), (1, "texto", 404),
])
def test_referencias_invalidas_o_inexistentes_no_modifican_configuraciones(local_id, producto_id, estado):
    _, cliente, _, _ = aplicacion_para_minimos()
    cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 7})
    respuesta = cliente.put(f"/api/ubicaciones/{local_id}/minimos/{producto_id}", json={"minimo": 9})
    assert respuesta.status_code == estado
    assert respuesta.get_json()["error"]["code"] == estado
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"][0]["minimo"] == 7


@pytest.mark.parametrize("identificador,estado", [(999, 404), (0, 400), ("texto", 404)])
def test_consulta_de_local_invalido(identificador, estado):
    _, cliente, _, _ = aplicacion_para_minimos()
    respuesta = cliente.get(f"/api/ubicaciones/{identificador}/minimos")
    assert respuesta.status_code == estado
    assert respuesta.is_json


def test_cd_no_admite_configuracion_ni_consulta():
    _, cliente, _, _ = aplicacion_para_minimos()
    cd = cliente.post("/api/ubicaciones", json={"codigo": "CD", "nombre": "Central", "tipo": "CD"}).get_json()
    ruta = f'/api/ubicaciones/{cd["id"]}/minimos'
    for respuesta in [cliente.get(ruta), cliente.put(f"{ruta}/1", json={"minimo": 0})]:
        assert respuesta.status_code == 400
        assert "locales" in respuesta.get_json()["error"]["message"]
    assert cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"] == []


def test_nombres_y_codigos_actuales_sin_perder_configuracion():
    _, cliente, producto, _ = aplicacion_para_minimos()
    cliente.put("/api/ubicaciones/1/minimos/1", json={"minimo": 5})
    cliente.put("/api/ubicaciones/1", json={"codigo": "L2", "nombre": "Centro actualizado"})
    cliente.put("/api/productos/1", json={"codigo": "002", "nombre": "Arroz integral", "categoria_id": producto["categoria"]["id"], "precio": "140"})
    datos = cliente.get("/api/ubicaciones/1/minimos").get_json()
    assert datos["ubicacion"]["nombre"] == "Centro actualizado"
    assert datos["minimos"] == [{"producto": {"id": 1, "codigo": "002", "nombre": "Arroz integral", "activo": True}, "minimo": 5}]


def test_puts_concurrentes_reemplazan_el_par_y_conservan_otro_local():
    app, cliente, _, _ = aplicacion_para_minimos()
    cliente.post("/api/ubicaciones", json={"codigo": "L2", "nombre": "Norte", "tipo": "LOCAL"})

    def configurar(entrada):
        local_id, minimo = entrada
        with app.test_client() as otro_cliente:
            respuesta = otro_cliente.put(f"/api/ubicaciones/{local_id}/minimos/1", json={"minimo": minimo})
            return respuesta.status_code, respuesta.get_json()["minimo"]

    entradas = [(1, 3), (1, 12), (1, 0), (2, 20)]
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        resultados = list(ejecutor.map(configurar, entradas))
    assert resultados == [(200, minimo) for _, minimo in entradas]
    primero = cliente.get("/api/ubicaciones/1/minimos").get_json()["minimos"]
    segundo = cliente.get("/api/ubicaciones/2/minimos").get_json()["minimos"]
    assert len(primero) == len(segundo) == 1
    assert primero[0]["minimo"] in [3, 12, 0]
    assert segundo[0]["minimo"] == 20


def test_contrato_sin_campos_de_inventario_y_metodos_no_implementados():
    _, cliente, producto, local = aplicacion_para_minimos()
    respuesta = cliente.put("/api/ubicaciones/1/minimos/1", data="minimo=1")
    assert respuesta.status_code == 415
    assert cliente.post("/api/ubicaciones/1/minimos/1", json={"minimo": 1}).status_code == 405
    assert cliente.delete("/api/ubicaciones/1/minimos/1").status_code == 405
    assert cliente.get("/api/ubicaciones/1").get_json() == local
    assert cliente.get("/api/productos/1").get_json() == producto
    assert cliente.get("/api/health").get_json() == {"status": "ok"}
