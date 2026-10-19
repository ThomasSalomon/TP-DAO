"""Identidad, invariantes y colaboración de proveedores con su catálogo."""

import pytest

from backend.dominio import Catalogo, CodigoDuplicadoError, Proveedor


def test_alta_consulta_normalizacion_ceros_y_nombre_no_unico():
    catalogo = Catalogo()
    primero = catalogo.crear_proveedor(" 0001 ", " Distribuidora ")
    segundo = catalogo.crear_proveedor("0002", "Distribuidora")
    assert isinstance(primero, Proveedor)
    assert (primero.identificador, primero.codigo, primero.nombre) == (1, "0001", "Distribuidora")
    assert segundo.identificador == 2
    assert catalogo.obtener_proveedor(1) is primero
    assert catalogo.buscar_proveedor_por_codigo(" 0001 ") is primero
    assert catalogo.buscar_proveedor_por_codigo("1") is None
    assert catalogo.listar_proveedores() == (primero, segundo)
    categoria = catalogo.crear_categoria("0001", "Almacén")
    assert catalogo.crear_producto("0001", "Arroz", categoria, "1").codigo == primero.codigo


@pytest.mark.parametrize("codigo", ["ABC", "abc", " AbC "])
def test_duplicado_normalizado_no_agrega_registros(codigo):
    catalogo = Catalogo()
    proveedor = catalogo.crear_proveedor("ABC", "Original")
    with pytest.raises(CodigoDuplicadoError):
        catalogo.crear_proveedor(codigo, "Otro")
    assert catalogo.listar_proveedores() == (proveedor,)
    assert catalogo.buscar_proveedor_por_codigo(codigo) is proveedor
    assert catalogo.crear_proveedor("LIBRE", "Otro").identificador == 2


@pytest.mark.parametrize("campo", ["codigo", "nombre"])
@pytest.mark.parametrize("valor", ["", " \t ", None, True, 12, 1.5, []])
def test_datos_invalidos_en_alta_y_modificacion_no_tienen_efectos(campo, valor):
    catalogo = Catalogo()
    proveedor = catalogo.crear_proveedor("ORIG", "Original")
    datos = {"codigo": "NUEVO", "nombre": "Modificado", campo: valor}
    error = ValueError if isinstance(valor, str) else TypeError
    with pytest.raises(error):
        catalogo.crear_proveedor(**datos)
    with pytest.raises(error):
        proveedor.modificar(**datos)
    assert (proveedor.codigo, proveedor.nombre) == ("ORIG", "Original")
    assert catalogo.listar_proveedores() == (proveedor,)
    # Un intento fallido tampoco consume el nuevo código ni el siguiente ID.
    assert catalogo.crear_proveedor("NUEVO", "Válido").identificador == 2


def test_edicion_conserva_identidad_y_no_permite_reutilizar_codigos_reemplazados():
    catalogo = Catalogo()
    proveedor = catalogo.crear_proveedor("ABC", "Original")
    assert catalogo.modificar_proveedor(1, " abc ", " Nuevo nombre ") is proveedor
    assert (proveedor.codigo, proveedor.nombre) == ("abc", "Nuevo nombre")
    proveedor.modificar(" 0002 ", "Actual")
    assert catalogo.obtener_proveedor(1) is proveedor
    assert catalogo.buscar_proveedor_por_codigo("abc") is None
    assert catalogo.buscar_proveedor_por_codigo("0002") is proveedor
    with pytest.raises(CodigoDuplicadoError):
        catalogo.crear_proveedor(" ABC ", "Otro")
    with pytest.raises(CodigoDuplicadoError):
        proveedor.modificar("ABC", "Volver")
    assert (proveedor.identificador, proveedor.codigo, proveedor.nombre) == (1, "0002", "Actual")


def test_conflicto_de_edicion_no_cambia_datos_ni_registros():
    catalogo = Catalogo()
    primero = catalogo.crear_proveedor("A", "Uno")
    segundo = catalogo.crear_proveedor("B", "Dos")
    with pytest.raises(CodigoDuplicadoError):
        catalogo.modificar_proveedor(2, " a ", "No debe cambiar")
    assert (segundo.codigo, segundo.nombre) == ("B", "Dos")
    assert catalogo.listar_proveedores() == (primero, segundo)


def test_propiedades_sin_escritura_y_listado_sin_mutacion_de_la_coleccion():
    catalogo = Catalogo()
    proveedor = catalogo.crear_proveedor("A", "Uno")
    for campo, valor in [("identificador", 99), ("codigo", "B"), ("nombre", "Otro")]:
        with pytest.raises(AttributeError):
            setattr(proveedor, campo, valor)
    listado = catalogo.listar_proveedores()
    with pytest.raises(AttributeError):
        listado.clear()
    assert listado[0] is proveedor


@pytest.mark.parametrize("identificador", [None, True, "1", 1.0, 0, -1])
def test_identificadores_invalidos(identificador):
    catalogo = Catalogo()
    error = ValueError if type(identificador) is int else TypeError
    with pytest.raises(error):
        catalogo.obtener_proveedor(identificador)
    with pytest.raises(error):
        Proveedor(identificador, "A", "Uno", catalogo)


def test_inexistentes_catalogos_y_reservas_independientes():
    catalogo = Catalogo()
    with pytest.raises(KeyError):
        catalogo.obtener_proveedor(999)
    with pytest.raises(KeyError):
        catalogo.modificar_proveedor(999, "A", "Uno")
    proveedor = catalogo.crear_proveedor("A", "Uno")
    proveedor.modificar("B", "Dos")
    otro = Catalogo()
    assert otro.listar_proveedores() == ()
    assert otro.crear_proveedor("A", "Uno") is not proveedor
    with pytest.raises(TypeError):
        Proveedor(1, "A", "Uno", None)
