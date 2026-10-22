"""Creación explícita de la aplicación HTTP, separada del dominio."""

from pathlib import Path


def create_app(frontend_dist=None, base_datos=None):
    # Importar el dominio no debe cargar las dependencias de presentación HTTP.
    from flask import Flask, request, send_from_directory
    from werkzeug.exceptions import HTTPException
    from threading import Lock

    from .api import api
    from .api_catalogo import api_catalogo
    from .api_compras import api_compras
    from .persistencia import BaseDatos, cargar_estado, ruta_base_datos_predeterminada

    if base_datos is None:
        base_datos = ruta_base_datos_predeterminada()
    base_datos = BaseDatos(base_datos)
    base_datos.inicializar()

    if frontend_dist is None:
        frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    frontend_dist = Path(frontend_dist).resolve()

    app = Flask(
        __name__,
        static_folder=str(frontend_dist / "assets"),
        static_url_path="/assets",
    )
    app.register_blueprint(api)
    app.extensions["base_datos"] = base_datos
    catalogo, compras, inventario = base_datos.consultar(cargar_estado)
    app.extensions["catalogo"] = catalogo
    app.extensions["compras"] = compras
    app.extensions["inventario"] = inventario
    # Un único bloqueo serializa catálogo, compras e inventario, que se leen entre sí.
    app.extensions["catalogo_lock"] = Lock()
    app.register_blueprint(api_catalogo)
    app.register_blueprint(api_compras)

    @app.get("/")
    def frontend():
        return send_from_directory(frontend_dist, "index.html")

    @app.errorhandler(HTTPException)
    def error_http(error):
        if request.path == "/api" or request.path.startswith("/api/"):
            response = error.get_response()
            response.data = app.json.dumps(
                {"error": {"code": error.code, "message": error.name}}
            )
            response.content_type = "application/json"
            return response
        return error

    return app

