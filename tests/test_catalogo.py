from pathlib import Path
import subprocess
import sys

import pytest

from backend.dominio import Catalogo, Categoria, Producto


def catalogo_con_producto():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")
    producto = catalogo.crear_producto("001", "Arroz", categoria, "125.50")
    return catalogo, categoria, producto


def test_creacion_consulta_y_referencias_compartidas():
    catalogo = Catalogo()
    assert catalogo.listar_categorias() == ()
    assert catalogo.listar_productos() == ()

    categoria = catalogo.crear_categoria(" ALM ", " Almacén ")
    producto = catalogo.crear_producto(" 001 ", " Arroz ", categoria, "125.50")
    otro = catalogo.crear_producto("002", "Fideos", categoria, "90")

    assert isinstance(categoria, Categoria)
    assert isinstance(producto, Producto)
    assert (categoria.codigo, categoria.nombre) == ("ALM", "Almacén")
    assert (producto.codigo, producto.nombre) == ("001", "Arroz")
    assert producto.precio_centavos == 12550
    assert type(producto.precio_centavos) is int
    assert producto.precio == "125.50"
    assert producto.categoria is otro.categoria is categoria
    assert catalogo.obtener_categoria(categoria.identificador) is categoria
    assert catalogo.obtener_producto(producto.identificador) is producto
    assert catalogo.buscar_categoria_por_codigo(" alm ") is categoria
    assert catalogo.buscar_producto_por_codigo(" 001 ") is producto
    assert catalogo.buscar_producto_por_codigo("inexistente") is None


@pytest.mark.parametrize("entidad", ["categoria", "producto"])
def test_codigos_duplicados_se_rechazan_tras_normalizar(entidad):
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria(" AlM-001 ", "Almacén")
    if entidad == "categoria":
        with pytest.raises(ValueError, match="código"):
            catalogo.crear_categoria("aLm-001", "Otra categoría")
        assert catalogo.listar_categorias() == (categoria,)
    else:
        producto = catalogo.crear_producto(" Arr-001 ", "Arroz", categoria, "1")
        with pytest.raises(ValueError, match="código"):
            catalogo.crear_producto("arr-001", "Otro producto", categoria, "2")
        assert catalogo.listar_productos() == (producto,)


def test_ceros_iniciales_unicidad_por_tipo_y_nombres_repetidos():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("001", "Repetido")
    otra = catalogo.crear_categoria("1", "Repetido")
    producto = catalogo.crear_producto("001", "Repetido", categoria, "1")
    otro = catalogo.crear_producto("1", "Repetido", otra, "2")

    assert categoria.codigo == producto.codigo == "001"
    assert otra.codigo == otro.codigo == "1"
    assert categoria.identificador != otra.identificador
    assert producto.identificador != otro.identificador
    assert catalogo.buscar_producto_por_codigo("001") is producto
    assert catalogo.buscar_producto_por_codigo("1") is otro


@pytest.mark.parametrize("entidad", ["categoria", "producto"])
def test_identificadores_no_se_pueden_reasignar_ni_eliminar(entidad):
    catalogo, categoria, producto = catalogo_con_producto()
    objeto = categoria if entidad == "categoria" else producto
    anterior = objeto.identificador

    with pytest.raises(AttributeError):
        objeto.identificador = 999
    with pytest.raises(AttributeError):
        del objeto.identificador

    assert objeto.identificador == anterior
    assert catalogo.obtener_categoria(categoria.identificador) is categoria
    assert catalogo.obtener_producto(producto.identificador) is producto


@pytest.mark.parametrize("entidad", ["categoria", "producto"])
@pytest.mark.parametrize("campo", ["codigo", "nombre"])
@pytest.mark.parametrize("valor", ["", " \t ", None, 7, True, [], b"texto"])
def test_textos_invalidos_no_registran_objetos(entidad, campo, valor):
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")
    datos = {"codigo": "NUEVO", "nombre": "Nuevo"}
    datos[campo] = valor
    error = ValueError if isinstance(valor, str) else TypeError

    with pytest.raises(error):
        if entidad == "categoria":
            catalogo.crear_categoria(**datos)
        else:
            catalogo.crear_producto(**datos, categoria=categoria, precio="1")

    assert catalogo.listar_categorias() == (categoria,)
    assert catalogo.listar_productos() == ()


@pytest.mark.parametrize(
    "precio,centavos,texto",
    [
        ("0.01", 1, "0.01"),
        ("1", 100, "1.00"),
        ("1.2", 120, "1.20"),
        (" 12.50 ", 1250, "12.50"),
        ("000.01", 1, "0.01"),
        ("123456789012345678901234567890.12", 12345678901234567890123456789012,
         "123456789012345678901234567890.12"),
    ],
)
def test_precios_se_convierten_exactamente_sin_float(precio, centavos, texto):
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")

    producto = catalogo.crear_producto("001", "Arroz", categoria, precio)

    assert producto.precio_centavos == centavos
    assert type(producto.precio_centavos) is int
    assert producto.precio == texto


@pytest.mark.parametrize(
    "precio",
    ["0", "0.00", "-1", "1.001", "1.230", "NaN", "Infinity", "1e2",
     "1,25", "", " ", ".25", "1.", "1_000", "1.00.0"],
)
def test_importes_invalidos_no_crean_producto(precio):
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")

    with pytest.raises(ValueError, match="precio"):
        catalogo.crear_producto("001", "Arroz", categoria, precio)

    assert catalogo.listar_productos() == ()


@pytest.mark.parametrize("precio", [None, True, 1, 1.25, [], b"1.25"])
def test_precio_rechaza_tipos_ambiguos_o_inexactos(precio):
    catalogo, _, producto = catalogo_con_producto()

    with pytest.raises(TypeError, match="precio"):
        producto.cambiar_precio(precio)

    assert producto.precio_centavos == 12550
    assert catalogo.obtener_producto(producto.identificador) is producto


@pytest.mark.parametrize("categoria", [None, 1, "ALM", object()])
def test_categoria_de_tipo_incorrecto_se_rechaza(categoria):
    catalogo = Catalogo()

    with pytest.raises(TypeError, match="categoría"):
        catalogo.crear_producto("001", "Arroz", categoria, "1")

    assert catalogo.listar_productos() == ()


@pytest.mark.parametrize("procedencia", ["otro_catalogo", "no_registrada"])
def test_categoria_debe_ser_la_instancia_registrada(procedencia):
    catalogo, categoria, producto = catalogo_con_producto()
    if procedencia == "otro_catalogo":
        ajena = Catalogo().crear_categoria("OTRA", "Otra")
    else:
        ajena = Categoria(categoria.identificador, "OTRA", "Otra", catalogo)

    with pytest.raises(ValueError, match="catálogo"):
        catalogo.crear_producto("002", "Fideos", ajena, "2")
    with pytest.raises(ValueError, match="catálogo"):
        producto.modificar("CAMBIO", "Cambiado", ajena, "3")

    assert catalogo.listar_productos() == (producto,)
    assert (producto.codigo, producto.nombre, producto.categoria, producto.precio) == (
        "001", "Arroz", categoria, "125.50"
    )


def test_modificacion_valida_conserva_identidad_y_actualiza_consultas():
    catalogo, categoria, producto = catalogo_con_producto()
    otra = catalogo.crear_categoria("BEB", "Bebidas")
    id_categoria, id_producto = categoria.identificador, producto.identificador

    assert catalogo.modificar_categoria(id_categoria, "COM", "Comestibles") is categoria
    assert producto.categoria.nombre == "Comestibles"
    assert catalogo.buscar_categoria_por_codigo("ALM") is None
    assert catalogo.buscar_categoria_por_codigo(" com ") is categoria
    assert catalogo.modificar_producto(
        id_producto, "NUEVO", "Agua", otra, "0.01"
    ) is producto

    assert categoria.identificador == id_categoria
    assert producto.identificador == id_producto
    assert (producto.codigo, producto.nombre, producto.categoria, producto.precio) == (
        "NUEVO", "Agua", otra, "0.01"
    )
    assert catalogo.buscar_producto_por_codigo("001") is None
    assert catalogo.buscar_producto_por_codigo("nuevo") is producto
    producto.cambiar_precio("10.05")
    assert producto.precio_centavos == 1005


@pytest.mark.parametrize("codigo,nombre", [("BEB", "Nuevo"), ("NUEVO", " ")])
def test_modificacion_de_categoria_fallida_conserva_referencias(codigo, nombre):
    catalogo, categoria, producto = catalogo_con_producto()
    catalogo.crear_categoria("BEB", "Bebidas")

    with pytest.raises(ValueError):
        categoria.modificar(codigo, nombre)

    assert (categoria.codigo, categoria.nombre) == ("ALM", "Almacén")
    assert producto.categoria is categoria
    assert catalogo.buscar_categoria_por_codigo("ALM") is categoria
    assert catalogo.buscar_categoria_por_codigo("NUEVO") is None


@pytest.mark.parametrize(
    "codigo,nombre,precio",
    [("002", "Nuevo", "1"), ("NUEVO", " ", "1"), ("NUEVO", "Nuevo", "1.001")],
)
def test_modificacion_de_producto_fallida_es_atomica(codigo, nombre, precio):
    catalogo, categoria, producto = catalogo_con_producto()
    otra = catalogo.crear_categoria("BEB", "Bebidas")
    segundo = catalogo.crear_producto("002", "Fideos", categoria, "2")

    with pytest.raises(ValueError):
        catalogo.modificar_producto(producto.identificador, codigo, nombre, otra, precio)

    assert (producto.codigo, producto.nombre, producto.categoria, producto.precio) == (
        "001", "Arroz", categoria, "125.50"
    )
    assert catalogo.buscar_producto_por_codigo("001") is producto
    assert catalogo.buscar_producto_por_codigo("NUEVO") is None
    assert catalogo.buscar_producto_por_codigo("002") is segundo


def test_modificacion_directa_no_elude_unicidad_ni_encapsulamiento():
    catalogo, categoria, producto = catalogo_con_producto()
    catalogo.crear_producto("002", "Fideos", categoria, "2")

    with pytest.raises(ValueError, match="código"):
        producto.modificar("002", "Otro", categoria, "1")
    for objeto, campo, valor in [
        (categoria, "codigo", "OTRA"), (categoria, "nombre", ""),
        (producto, "codigo", "002"), (producto, "nombre", ""),
        (producto, "categoria", None), (producto, "precio_centavos", 0),
    ]:
        with pytest.raises(AttributeError):
            setattr(objeto, campo, valor)


@pytest.mark.parametrize("identificador", [None, True, "1", 1.0, 0, -1])
def test_consultas_por_id_rechazan_identificadores_invalidos(identificador):
    catalogo, _, _ = catalogo_con_producto()
    error = ValueError if type(identificador) is int else TypeError

    with pytest.raises(error):
        catalogo.obtener_categoria(identificador)
    with pytest.raises(error):
        catalogo.obtener_producto(identificador)


def test_consultas_inexistentes_listados_y_catalogos_independientes():
    catalogo, categoria, producto = catalogo_con_producto()
    categorias = catalogo.listar_categorias()
    productos = catalogo.listar_productos()

    with pytest.raises(KeyError):
        catalogo.obtener_categoria(999)
    with pytest.raises(KeyError):
        catalogo.obtener_producto(999)
    assert categorias == (categoria,)
    assert productos == (producto,)
    with pytest.raises(AttributeError):
        categorias.clear()
    with pytest.raises(AttributeError):
        productos.clear()
    otro_catalogo = Catalogo()
    assert otro_catalogo.listar_categorias() == ()
    assert otro_catalogo.listar_productos() == ()
    assert otro_catalogo.crear_categoria("ALM", "Almacén") is not categoria


def test_dominio_funciona_sin_paquetes_externos_ni_importar_sqlite():
    raiz = Path(__file__).resolve().parents[1]
    programa = f"""
import sys
sys.path.insert(0, {str(raiz)!r})
from backend.dominio import Catalogo
catalogo = Catalogo()
categoria = catalogo.crear_categoria('ALM', 'Almacen')
producto = catalogo.crear_producto('001', 'Arroz', categoria, '0.01')
producto.cambiar_precio('12.50')
assert producto.precio_centavos == 1250
assert producto.categoria is categoria
proveedor = catalogo.crear_proveedor('0001', 'Distribuidora')
proveedor.modificar('0002', 'Distribuidora actualizada')
assert catalogo.obtener_proveedor(proveedor.identificador) is proveedor
assert proveedor.codigo == '0002'
ubicacion = catalogo.crear_ubicacion('CD', 'Central', 'CD')
ubicacion.modificar('CD01', 'Central actualizada')
assert catalogo.obtener_ubicacion(ubicacion.identificador) is ubicacion
assert ubicacion.tipo == 'CD'
local = catalogo.crear_ubicacion('L1', 'Centro', 'LOCAL')
assert catalogo.obtener_minimo(local.identificador, producto.identificador) is None
catalogo.establecer_minimo(local.identificador, producto.identificador, 0)
assert catalogo.listar_minimos(local.identificador) == ((producto, 0),)
assert 'flask' not in sys.modules
assert 'sqlite3' not in sys.modules
print('dominio independiente')
"""

    resultado = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", programa],
        capture_output=True, text=True, timeout=10,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "dominio independiente"
