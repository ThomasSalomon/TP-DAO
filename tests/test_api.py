import pytest

from backend import create_app


def test_health_responde_json_sin_frontend(tmp_path):
    app = create_app(frontend_dist=tmp_path / "sin-build")

    response = app.test_client().get("/api/health")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/api", "/api/no-existe"])
def test_api_inexistente_devuelve_404_json(path, tmp_path):
    client = create_app(frontend_dist=tmp_path).test_client()

    response = client.get(path)

    assert response.status_code == 404
    assert response.get_json() == {"error": {"code": 404, "message": "Not Found"}}


def test_health_rechaza_escritura(tmp_path):
    client = create_app(frontend_dist=tmp_path).test_client()

    response = client.post("/api/health", json={})

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == 405
    assert "GET" in response.headers["Allow"]


def test_python_sirve_build_y_api_desde_el_mismo_origen(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>Frontend de prueba</h1>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log('build');", encoding="utf-8")
    client = create_app(frontend_dist=tmp_path).test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "Frontend de prueba" in response.get_data(as_text=True)
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_assets_inexistentes_no_devuelven_el_html_de_la_app(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Frontend</h1>", encoding="utf-8")
    client = create_app(frontend_dist=tmp_path).test_client()

    assert client.get("/assets/no-existe.js").status_code == 404
    assert client.get("/ruta-no-definida").status_code == 404


def test_sin_build_la_raiz_es_404_y_la_api_sigue_disponible(tmp_path):
    client = create_app(frontend_dist=tmp_path).test_client()

    assert client.get("/").status_code == 404
    assert client.get("/api/health").status_code == 200


def test_estaticos_no_exponen_archivos_fuera_de_assets(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (tmp_path / "privado.txt").write_text("fuera del frontend", encoding="utf-8")
    client = create_app(frontend_dist=dist).test_client()

    assert client.get("/assets/../../privado.txt").status_code == 404

