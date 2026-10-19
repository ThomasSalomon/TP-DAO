"""Bajas lógicas, referencias compartidas y códigos conservados."""

import pytest

from backend.dominio import Catalogo, CodigoDuplicadoError, ConflictoCatalogoError


def escenario():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("CAT", "Almacén")
    producto = catalogo.crear_producto("PROD", "Arroz", categoria, "125.50")
    proveedor = catalogo.crear_proveedor("PR", "Distribuidora")
    local = catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
    return catalogo, categoria, producto, proveedor, local


def crear(catalogo, tipo, codigo):
    if tipo == "producto":
        return catalogo.crear_producto(codigo, "Nuevo", catalogo.obtener_categoria(1), "1")
    if tipo == "ubicacion":
        return catalogo.crear_ubicacion(codigo, "Nuevo", "LOCAL")
    return getattr(catalogo, f"crear_{tipo}")(codigo, "Nuevo")


@pytest.mark.parametrize("tipo,indice,plural", [
    ("categoria", 1, "categorias"), ("producto", 2, "productos"),
    ("proveedor", 3, "proveedores"), ("ubicacion", 4, "ubicaciones"),
])
def test_desactivacion_repetida_conserva_identidad_datos_y_consultas(tipo, indice, plural):
    datos = escenario()
    catalogo, entidad = datos[0], datos[indice]
    if tipo == "categoria":
        datos[2].desactivar()
    original = (entidad.identificador, entidad.codigo, entidad.nombre)
    assert entidad.activo is True
    for _ in range(2):
        assert getattr(catalogo, f"desactivar_{tipo}")(entidad.identificador) is entidad
        assert entidad.activo is False
        assert (entidad.identificador, entidad.codigo, entidad.nombre) == original
        assert getattr(catalogo, f"obtener_{tipo}")(entidad.identificador) is entidad
        assert getattr(catalogo, f"buscar_{tipo}_por_codigo")(entidad.codigo) is entidad
    listar = getattr(catalogo, f"listar_{plural}")
    assert listar() == ()
    assert listar("inactivos") == (entidad,)
    assert listar("todos") == (entidad,)
    with pytest.raises(AttributeError):
        entidad.activo = True


@pytest.mark.parametrize("tipo,indice", [("categoria", 1), ("producto", 2), ("proveedor", 3), ("ubicacion", 4)])
def test_codigos_original_y_reemplazado_no_se_reutilizan_ni_tras_baja(tipo, indice):
    datos = escenario()
    catalogo, entidad = datos[0], datos[indice]
    original = entidad.codigo
    if tipo == "producto":
        entidad.modificar("NUEVO", "Modificado", datos[1], "3")
    else:
        entidad.modificar("NUEVO", "Modificado")
    for codigo in [original, " nuevo "]:
        with pytest.raises(CodigoDuplicadoError):
            crear(catalogo, tipo, codigo)
    if tipo == "categoria":
        datos[2].desactivar()
    entidad.desactivar()
    for codigo in [original.lower(), " nuevo "]:
        with pytest.raises(CodigoDuplicadoError):
            crear(catalogo, tipo, codigo)
    assert crear(catalogo, tipo, "LIBRE").identificador > entidad.identificador


@pytest.mark.parametrize("tipo,indice", [("categoria", 1), ("producto", 2), ("proveedor", 3), ("ubicacion", 4)])
def test_inactivos_no_se_modifican_por_objeto_ni_catalogo(tipo, indice):
    datos = escenario()
    catalogo, entidad = datos[0], datos[indice]
    if tipo == "categoria":
        datos[2].desactivar()
    entidad.desactivar()
    argumentos = ("CAMBIO", "Otro", datos[1], "2") if tipo == "producto" else ("CAMBIO", "Otro")
    original = (entidad.codigo, entidad.nombre)
    with pytest.raises(ConflictoCatalogoError):
        entidad.modificar(*argumentos)
    with pytest.raises(ConflictoCatalogoError):
        getattr(catalogo, f"modificar_{tipo}")(entidad.identificador, *argumentos)
    if tipo == "producto":
        with pytest.raises(ConflictoCatalogoError):
            entidad.cambiar_precio("9")
        assert entidad.precio == "125.50"
    assert (entidad.codigo, entidad.nombre) == original
    assert crear(catalogo, tipo, "CAMBIO").activo is True


def test_categoria_bloqueada_hasta_desactivar_todos_sus_productos_sin_cascadas():
    catalogo, categoria, producto, _, _ = escenario()
    segundo = catalogo.crear_producto("SEG", "Fideos", categoria, "10")
    for _ in range(2):
        with pytest.raises(ConflictoCatalogoError, match="productos activos"):
            categoria.desactivar()
        assert categoria.activo and segundo.activo
        producto.desactivar()
    segundo.desactivar()
    categoria.desactivar()
    assert producto.categoria is segundo.categoria is categoria
    assert catalogo.obtener_producto(producto.identificador) is producto
    assert catalogo.contiene_categoria(categoria)


def test_categoria_inactiva_rechaza_altas_y_nuevas_asociaciones_sin_cambios_parciales():
    catalogo, categoria, producto, _, _ = escenario()
    libre = catalogo.crear_categoria("OTRA", "Otra")
    libre.desactivar()
    with pytest.raises(ConflictoCatalogoError):
        catalogo.crear_producto("NUEVO", "Nuevo", libre, "1")
    with pytest.raises(ConflictoCatalogoError):
        producto.modificar("CAMBIO", "Otro", libre, "2")
    assert producto.categoria is categoria
    assert (producto.codigo, producto.nombre, producto.precio) == ("PROD", "Arroz", "125.50")
    assert catalogo.crear_producto("CAMBIO", "Válido", categoria, "2").identificador == 2


@pytest.mark.parametrize("baja", ["producto", "local", "ambos"])
def test_minimos_historicos_se_conservan_pero_no_admiten_escrituras_con_inactivos(baja):
    catalogo, _, producto, _, local = escenario()
    otro_local = catalogo.crear_ubicacion("L2", "Norte", "LOCAL")
    catalogo.establecer_minimo(local.identificador, producto.identificador, 0)
    catalogo.establecer_minimo(otro_local.identificador, producto.identificador, 12)
    if baja in ("producto", "ambos"):
        producto.desactivar()
    if baja in ("local", "ambos"):
        local.desactivar()
    with pytest.raises(ConflictoCatalogoError):
        catalogo.establecer_minimo(local.identificador, producto.identificador, 9)
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 0
    assert catalogo.listar_minimos(local.identificador) == ((producto, 0),)
    assert catalogo.listar_minimos(otro_local.identificador) == ((producto, 12),)


def test_cd_no_se_desactiva_y_no_se_libera_su_cardinalidad():
    catalogo = Catalogo()
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")
    for operacion in [cd.desactivar, lambda: catalogo.desactivar_ubicacion(cd.identificador)]:
        with pytest.raises(ConflictoCatalogoError, match="política de reemplazo"):
            operacion()
    assert cd.activo
    assert catalogo.listar_ubicaciones() == (cd,)
    with pytest.raises(ValueError):
        catalogo.crear_ubicacion("CD2", "Otra central", "CD")


@pytest.mark.parametrize("estado", [None, True, [], "", "inactivo", "ACTIVOS"])
def test_filtros_invalidos(estado):
    catalogo = Catalogo()
    error = ValueError if isinstance(estado, str) else TypeError
    for listar in [catalogo.listar_categorias, catalogo.listar_productos, catalogo.listar_proveedores, catalogo.listar_ubicaciones]:
        with pytest.raises(error):
            listar(estado)


def test_catalogos_aislados_e_identificadores_inexistentes():
    primero, _, producto, _, _ = escenario()
    segundo, _, otro_producto, _, _ = escenario()
    primero.desactivar_producto(producto.identificador)
    assert otro_producto.activo
    assert segundo.listar_productos() == (otro_producto,)
    for operacion in [primero.desactivar_categoria, primero.desactivar_producto, primero.desactivar_proveedor, primero.desactivar_ubicacion]:
        with pytest.raises(KeyError):
            operacion(999)
