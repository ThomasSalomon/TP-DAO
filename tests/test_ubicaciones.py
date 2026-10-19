"""Invariantes de ubicaciones y cardinalidad del CD dentro de cada catálogo."""

import pytest

from backend.dominio import (
    Catalogo, CentroDistribucionDuplicadoError, CodigoDuplicadoError, Ubicacion,
)


def test_catalogo_vacio_varios_locales_un_cd_e_identidad_por_referencia():
    catalogo = Catalogo()
    assert catalogo.listar_ubicaciones() == ()
    local = catalogo.crear_ubicacion(" 0001 ", " Centro ", "LOCAL")
    otro = catalogo.crear_ubicacion("0002", "Centro", "LOCAL")
    cd = catalogo.crear_ubicacion("CD01", "Depósito", " CD ")
    assert isinstance(local, Ubicacion)
    assert (local.identificador, local.codigo, local.nombre, local.tipo) == (1, "0001", "Centro", "LOCAL")
    assert (otro.identificador, cd.identificador, cd.tipo) == (2, 3, "CD")
    assert catalogo.obtener_ubicacion(1) is local
    assert catalogo.buscar_ubicacion_por_codigo(" cd01 ") is cd
    assert catalogo.buscar_ubicacion_por_codigo("1") is None
    assert catalogo.listar_ubicaciones() == (local, otro, cd)
    with pytest.raises(AttributeError):
        catalogo.listar_ubicaciones().clear()


def test_segundo_cd_rechazado_sin_consumir_id_o_codigo_y_local_permitido():
    catalogo = Catalogo()
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")
    with pytest.raises(CentroDistribucionDuplicadoError):
        catalogo.crear_ubicacion("LIBRE", "Segundo", "CD")
    with pytest.raises(CentroDistribucionDuplicadoError):
        Ubicacion(2, "LIBRE", "Otro intento", "CD", catalogo)
    assert catalogo.listar_ubicaciones() == (cd,)
    local = catalogo.crear_ubicacion("LIBRE", "Local", "LOCAL")
    assert local.identificador == 2
    assert catalogo.modificar_ubicacion(1, "CD2", "Central actualizada") is cd
    assert cd.tipo == "CD"


@pytest.mark.parametrize("codigo", ["ABC", "abc", " AbC "])
def test_unicidad_normalizada_entre_local_y_cd(codigo):
    catalogo = Catalogo()
    local = catalogo.crear_ubicacion("ABC", "Local", "LOCAL")
    with pytest.raises(CodigoDuplicadoError):
        catalogo.crear_ubicacion(codigo, "Central", "CD")
    assert catalogo.listar_ubicaciones() == (local,)
    assert catalogo.buscar_ubicacion_por_codigo(codigo) is local
    assert catalogo.crear_ubicacion("CD", "Central", "CD").identificador == 2


@pytest.mark.parametrize("tipo", ["LOCAL", "CD"])
def test_edicion_valida_preserva_id_tipo_y_reserva_codigos_reemplazados(tipo):
    catalogo = Catalogo()
    ubicacion = catalogo.crear_ubicacion("ABC", "Original", tipo)
    assert catalogo.modificar_ubicacion(1, " abc ", " Actual ") is ubicacion
    assert (ubicacion.codigo, ubicacion.nombre) == ("abc", "Actual")
    ubicacion.modificar("0002", "Nuevo")
    assert (ubicacion.identificador, ubicacion.tipo) == (1, tipo)
    assert catalogo.obtener_ubicacion(1) is ubicacion
    assert catalogo.buscar_ubicacion_por_codigo("abc") is None
    assert catalogo.buscar_ubicacion_por_codigo(" 0002 ") is ubicacion
    with pytest.raises(CodigoDuplicadoError):
        catalogo.crear_ubicacion("ABC", "Reutilizar", "LOCAL")
    with pytest.raises(CodigoDuplicadoError):
        ubicacion.modificar("ABC", "Volver")
    assert (ubicacion.codigo, ubicacion.nombre) == ("0002", "Nuevo")


@pytest.mark.parametrize("campo", ["codigo", "nombre"])
@pytest.mark.parametrize("valor", ["", " \t ", None, True, 12, 1.5, []])
def test_datos_invalidos_no_alteran_objeto_ni_reservan_codigos(campo, valor):
    catalogo = Catalogo()
    ubicacion = catalogo.crear_ubicacion("ORIG", "Original", "LOCAL")
    datos = {"codigo": "NUEVO", "nombre": "Cambio", campo: valor}
    error = ValueError if isinstance(valor, str) else TypeError
    with pytest.raises(error):
        catalogo.crear_ubicacion(**datos, tipo="LOCAL")
    with pytest.raises(error):
        ubicacion.modificar(**datos)
    assert (ubicacion.codigo, ubicacion.nombre, ubicacion.tipo) == ("ORIG", "Original", "LOCAL")
    assert catalogo.listar_ubicaciones() == (ubicacion,)
    assert catalogo.crear_ubicacion("NUEVO", "Válido", "CD").identificador == 2


@pytest.mark.parametrize("tipo", ["", " ", "local", "cd", "DEPOSITO", None, True, 1, 1.5, [], {}])
def test_tipos_invalidos_no_reservan_cd_codigo_o_id(tipo):
    catalogo = Catalogo()
    error = ValueError if isinstance(tipo, str) else TypeError
    with pytest.raises(error):
        catalogo.crear_ubicacion("CD", "Central", tipo)
    assert catalogo.listar_ubicaciones() == ()
    assert catalogo.crear_ubicacion("CD", "Central", "CD").identificador == 1


def test_cd_invalido_no_impide_posterior_alta_valida():
    catalogo = Catalogo()
    with pytest.raises(ValueError):
        catalogo.crear_ubicacion("CD", " ", "CD")
    assert catalogo.crear_ubicacion("CD", "Central", "CD").identificador == 1


def test_conflicto_de_edicion_sin_cambios_parciales():
    catalogo = Catalogo()
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")
    local = catalogo.crear_ubicacion("L01", "Local", "LOCAL")
    with pytest.raises(CodigoDuplicadoError):
        catalogo.modificar_ubicacion(2, " cd ", "Cambio inválido")
    assert (local.codigo, local.nombre, local.tipo) == ("L01", "Local", "LOCAL")
    assert catalogo.listar_ubicaciones() == (cd, local)


@pytest.mark.parametrize("tipo", ["LOCAL", "CD"])
def test_propiedades_protegidas_y_tipo_fuera_del_contrato_de_modificacion(tipo):
    catalogo = Catalogo()
    ubicacion = catalogo.crear_ubicacion("A", "Original", tipo)
    for campo, valor in [("identificador", 99), ("tipo", "CD"), ("codigo", "B"), ("nombre", "Otro")]:
        with pytest.raises(AttributeError):
            setattr(ubicacion, campo, valor)
    with pytest.raises(TypeError):
        ubicacion.modificar("B", "Otro", tipo="CD")
    with pytest.raises(TypeError):
        catalogo.modificar_ubicacion(1, "B", "Otro", tipo="CD")
    assert (ubicacion.identificador, ubicacion.codigo, ubicacion.nombre, ubicacion.tipo) == (1, "A", "Original", tipo)


@pytest.mark.parametrize("identificador", [None, True, "1", 1.0, 0, -1])
def test_identificadores_invalidos(identificador):
    catalogo = Catalogo()
    error = ValueError if type(identificador) is int else TypeError
    with pytest.raises(error):
        catalogo.obtener_ubicacion(identificador)
    with pytest.raises(error):
        Ubicacion(identificador, "A", "Local", "LOCAL", catalogo)


def test_inexistentes_catalogos_independientes_y_unicidad_separada_de_otros_maestros():
    catalogo = Catalogo()
    with pytest.raises(KeyError):
        catalogo.obtener_ubicacion(999)
    with pytest.raises(KeyError):
        catalogo.modificar_ubicacion(999, "A", "Otro")
    cd = catalogo.crear_ubicacion("A", "Central", "CD")
    cd.modificar("B", "Actual")
    catalogo.crear_proveedor("B", "Proveedor")
    categoria = catalogo.crear_categoria("B", "Almacén")
    assert catalogo.crear_producto("B", "Arroz", categoria, "1").codigo == cd.codigo
    otro = Catalogo()
    assert otro.crear_ubicacion("A", "Otra central", "CD") is not cd
    with pytest.raises(TypeError):
        Ubicacion(1, "L", "Local", "LOCAL", None)
