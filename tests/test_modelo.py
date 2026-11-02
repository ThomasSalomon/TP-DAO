"""Revisión del modelo POO contra el código (F-07.3, T-26): jerarquías, estado interno, composición y delegación.

Comprueba con `ast` las afirmaciones de `docs/MODELO_POO.md` que valen para todo el dominio; las reglas de cada
clase siguen probándose en los tests de su módulo.
"""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
DOMINIO = BACKEND / "dominio"

ESTADOS = {"Preparado", "Precintado", "EnTransito", "Recibido", "Verificado", "Rechazado", "Anulado"}
ESTRATEGIAS = {"PorDia", "PorLocal", "PorMedioPago"}
EXCEPCIONES = {"Exception", "ValueError", "ConflictoOperacionError"}

# Resultados de una consulta de reportes: se arman y se devuelven, no guardan estado del sistema.
RESULTADOS_REPORTES = {
    "GrupoCaja", "ResultadoVentas", "FilaProducto", "ResultadoProductos", "FilaExistencia", "ResultadoExistencias",
    "BultoRechazado", "RechazosLocal", "ResultadoRechazos",
}

# Cada parte la crea sólo su contenedor (A §6.11).
PARTES = {
    "DetalleCompra": "Compra",
    "DetalleReposicion": "OrdenReposicion",
    "DetalleBulto": "Bulto",
    "EventoEstadoBulto": "Bulto",
    "DetalleVenta": "Venta",
    "Cobro": "Venta",
    "Comprobante": "Venta",
    "DetalleDevolucion": "Devolucion",
    "Reintegro": "Devolucion",
}


def modulos(carpeta):
    return sorted(ruta for ruta in carpeta.rglob("*.py") if "__pycache__" not in ruta.parts)


def arbol(ruta):
    return ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))


def clases(carpeta):
    for ruta in modulos(carpeta):
        for nodo in arbol(ruta).body:
            if isinstance(nodo, ast.ClassDef):
                yield ruta, nodo


def clase(nombre):
    return next(nodo for _, nodo in clases(DOMINIO) if nodo.name == nombre)


def metodo(nodo_clase, nombre):
    return next(nodo for nodo in nodo_clase.body if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre)


def bases(nodo):
    return {base.id for base in nodo.bases if isinstance(base, ast.Name)}


def test_las_unicas_jerarquias_son_los_contratos_abstractos_y_las_excepciones():
    derivadas = {nodo.name: bases(nodo) for _, nodo in clases(DOMINIO) if nodo.bases}

    contratos = {nombre for nombre, base in derivadas.items() if base == {"ABC"}}
    assert contratos == {"EstadoBulto", "EstrategiaAgrupacion"}
    assert {nombre for nombre, base in derivadas.items() if base == {"EstadoBulto"}} == ESTADOS
    assert {nombre for nombre, base in derivadas.items() if base == {"EstrategiaAgrupacion"}} == ESTRATEGIAS
    otras = {nombre: base for nombre, base in derivadas.items() if nombre not in contratos | ESTADOS | ESTRATEGIAS}
    assert otras and all(base <= EXCEPCIONES and nombre.endswith("Error") for nombre, base in otras.items())


def test_los_contratos_abstractos_declaran_metodos_abstractos():
    for nombre in ("EstadoBulto", "EstrategiaAgrupacion"):
        abstractos = [
            nodo.name for nodo in clase(nombre).body
            if isinstance(nodo, ast.FunctionDef)
            and any(isinstance(decorador, ast.Name) and decorador.id == "abstractmethod" for decorador in nodo.decorator_list)
        ]
        assert abstractos, f"{nombre} no declara operaciones abstractas"


def atributos_publicos(nodo_clase):
    """Atributos de instancia sin guion bajo asignados en los métodos de la clase."""
    nombres = set()
    for nodo in ast.walk(nodo_clase):
        destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target] if isinstance(nodo, ast.AugAssign) else []
        for destino in destinos:
            for elemento in ast.walk(destino):
                es_de_self = (
                    isinstance(elemento, ast.Attribute)
                    and isinstance(elemento.value, ast.Name) and elemento.value.id == "self"
                )
                if es_de_self and not elemento.attr.startswith("_"):
                    nombres.add(elemento.attr)
    return nombres


def test_el_estado_de_entidades_y_documentos_queda_en_atributos_internos():
    con_atributos_publicos = {nodo.name for _, nodo in clases(DOMINIO) if atributos_publicos(nodo)}

    assert con_atributos_publicos == RESULTADOS_REPORTES


def test_el_dominio_no_modifica_atributos_con_setattr():
    llamadas = [
        f"{ruta.name}:{nodo.lineno}"
        for ruta in modulos(DOMINIO) for nodo in ast.walk(arbol(ruta))
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id == "setattr"
    ]

    assert llamadas == []


def test_cada_parte_compuesta_la_crea_solo_su_contenedor():
    creadores = {parte: set() for parte in PARTES}
    for _, nodo_clase in clases(BACKEND):
        for nodo in ast.walk(nodo_clase):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in creadores:
                creadores[nodo.func.id].add(nodo_clase.name)
    for ruta in modulos(BACKEND):
        # Fuera de toda clase (funciones de módulo de persistencia o API) no se crea ninguna parte.
        for nodo in arbol(ruta).body:
            if isinstance(nodo, ast.FunctionDef):
                for llamada in ast.walk(nodo):
                    if isinstance(llamada, ast.Call) and isinstance(llamada.func, ast.Name):
                        assert llamada.func.id not in PARTES, f"{ruta.name}:{llamada.lineno} crea {llamada.func.id}"

    assert creadores == {parte: {contenedor} for parte, contenedor in PARTES.items()}


@pytest.mark.parametrize("operacion", ["precintar", "despachar", "recibir", "verificar", "anular"])
def test_el_bulto_delega_cada_operacion_en_su_estado_actual(operacion):
    """Contexto de State: una sola instrucción que reenvía el mismo mensaje al estado, pasándose a sí mismo."""
    cuerpo = metodo(clase("Bulto"), operacion).body

    assert len(cuerpo) == 1 and isinstance(cuerpo[0], ast.Return)
    llamada = cuerpo[0].value
    assert isinstance(llamada, ast.Call) and llamada.func.attr == operacion
    assert ast.unparse(llamada.func.value) == "self._estado"
    assert ast.unparse(llamada.args[0]) == "self"


def test_los_contextos_no_eligen_comportamiento_por_clase_concreta():
    """Bulto sólo nombra a Preparado como estado inicial; ReporteVentas no nombra ninguna estrategia concreta."""
    nombres_bulto = {nodo.id for nodo in ast.walk(clase("Bulto")) if isinstance(nodo, ast.Name)}
    nombres_reporte = {nodo.id for nodo in ast.walk(clase("ReporteVentas")) if isinstance(nodo, ast.Name)}

    assert nombres_bulto & ESTADOS == {"Preparado"}
    assert nombres_reporte & ESTRATEGIAS == set()
    generar = ast.unparse(metodo(clase("ReporteVentas"), "generar"))
    assert "self._estrategia.clave(movimiento)" in generar


def test_solo_el_contexto_cambia_el_estado_del_bulto():
    asignaciones = [
        nodo_clase.name
        for _, nodo_clase in clases(DOMINIO) for nodo in ast.walk(nodo_clase)
        if isinstance(nodo, ast.Assign)
        for destino in nodo.targets
        if isinstance(destino, ast.Attribute) and destino.attr == "_estado" and ast.unparse(destino.value) == "self"
    ]

    # Los estados concretos piden el cambio con bulto._cambiar_estado(); Remito tiene su propio _estado de texto.
    assert set(asignaciones) == {"Bulto", "Remito"}
