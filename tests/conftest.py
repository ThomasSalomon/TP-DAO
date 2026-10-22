import itertools

import pytest

import backend.persistencia


@pytest.fixture(autouse=True)
def base_datos_temporal(tmp_path_factory, monkeypatch):
    """Cada create_app() sin ruta usa una base nueva y temporal, nunca la base real."""
    carpeta = tmp_path_factory.mktemp("bases")
    numeros = itertools.count(1)
    monkeypatch.setattr(
        backend.persistencia, "ruta_base_datos_predeterminada", lambda: carpeta / f"app-{next(numeros)}.db"
    )
