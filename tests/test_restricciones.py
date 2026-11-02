"""Restricciones técnicas comprobadas sobre el repositorio (F-07.2): backend sólo Python (T-29) y SQL con parámetros (T-30).

Se inspecciona el código con `ast` y los archivos de dependencias, sin ejecutar Node ni levantar servidores.
"""

import ast
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"


def archivos(carpeta):
    return sorted(ruta for ruta in carpeta.rglob("*") if ruta.is_file() and "__pycache__" not in ruta.parts)


def arbol(ruta):
    return ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))


def importaciones(ruta):
    """Paquetes de primer nivel que importa un módulo; las importaciones relativas son del propio backend."""
    for nodo in ast.walk(arbol(ruta)):
        if isinstance(nodo, ast.Import):
            yield from (alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0:
            yield nodo.module.split(".")[0]


def requisitos(nombre):
    lineas = (BACKEND / nombre).read_text(encoding="utf-8").splitlines()
    return [linea.strip() for linea in lineas if linea.strip() and not linea.startswith("#")]


# T-29: backend sólo Python.

def test_backend_contiene_solo_modulos_python_y_sus_requisitos():
    ajenos = [ruta.relative_to(BACKEND).as_posix() for ruta in archivos(BACKEND) if ruta.suffix != ".py"]

    assert ajenos == ["requirements-dev.txt", "requirements.txt"]


def test_backend_importa_solo_biblioteca_estandar_y_flask_sin_lanzar_procesos():
    importados = {nombre for ruta in archivos(BACKEND) if ruta.suffix == ".py" for nombre in importaciones(ruta)}

    assert importados - set(sys.stdlib_module_names) == {"flask", "werkzeug"}
    assert "subprocess" not in importados


def test_unica_dependencia_de_ejecucion_es_flask_y_pytest_solo_para_pruebas():
    assert [linea.split("==")[0] for linea in requisitos("requirements.txt")] == ["Flask"]
    assert [linea.split("==")[0] for linea in requisitos("requirements-dev.txt")] == ["-r requirements.txt", "pytest"]


def test_node_solo_construye_el_cliente_y_no_tiene_dependencias_de_servidor():
    paquete = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert paquete["scripts"] == {"dev": "vite", "build": "vite build", "preview": "vite preview"}
    assert set(paquete["dependencies"]) == {"react", "react-dom"}
    assert set(paquete["devDependencies"]) == {"vite", "@vitejs/plugin-react"}


def test_el_cliente_importa_solo_react_y_sus_propios_modulos():
    externos = {
        especificador
        for ruta in archivos(FRONTEND / "src") if ruta.suffix in {".js", ".jsx"}
        for especificador in re.findall(r"""^import\s.*?['"]([^'"]+)['"]""", ruta.read_text(encoding="utf-8"), re.M)
        if not especificador.startswith(".")
    }

    assert externos == {"react", "react-dom", "react-dom/client"}


# T-30: SQL con parámetros.

# Nombres de tabla o columna tomados de tuplas fijas del código; SQLite no admite parámetros para identificadores.
IDENTIFICADORES_INTERPOLADOS = {"tabla", "nombre", "definicion"}


def test_sql_recibe_valores_como_parametros_y_solo_interpola_identificadores_fijos():
    interpolados = set()
    for ruta in archivos(BACKEND / "persistencia"):
        for nodo in ast.walk(arbol(ruta)):
            es_ejecucion = isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
            if not (es_ejecucion and nodo.func.attr.startswith("execute") and nodo.args):
                continue
            sql = nodo.args[0]
            assert not isinstance(sql, (ast.BinOp, ast.Call)), f"{ruta.name}:{nodo.lineno} arma el SQL con una operación"
            if isinstance(sql, ast.JoinedStr):
                interpolados |= {
                    nombre.id
                    for valor in sql.values if isinstance(valor, ast.FormattedValue)
                    for nombre in ast.walk(valor.value) if isinstance(nombre, ast.Name)
                }

    assert interpolados == IDENTIFICADORES_INTERPOLADOS
