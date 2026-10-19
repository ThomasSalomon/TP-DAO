"""Configuración de mínimos, sin saldos ni movimientos de inventario."""

import pytest

from backend.dominio import Catalogo


def catalogo_para_minimos():
    catalogo = Catalogo()
    categoria = catalogo.crear_categoria("ALM", "Almacén")
    producto = catalogo.crear_producto("001", "Arroz", categoria, "125.50")
    local = catalogo.crear_ubicacion("L1", "Centro", "LOCAL")
    return catalogo, producto, local


def test_ausencia_cero_y_reemplazo_repetido_sin_duplicados():
    catalogo, producto, local = catalogo_para_minimos()
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) is None
    assert catalogo.listar_minimos(local.identificador) == ()
    assert catalogo.establecer_minimo(local.identificador, producto.identificador, 0) == 0
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 0
    for minimo in [10, 10, 3, 0]:
        assert catalogo.establecer_minimo(local.identificador, producto.identificador, minimo) == minimo
        assert catalogo.listar_minimos(local.identificador) == ((producto, minimo),)


def test_minimos_independientes_por_local_y_por_producto():
    catalogo, producto, local = catalogo_para_minimos()
    otro_local = catalogo.crear_ubicacion("L2", "Norte", "LOCAL")
    otro_producto = catalogo.crear_producto("002", "Fideos", producto.categoria, "10")
    catalogo.establecer_minimo(local.identificador, producto.identificador, 7)
    catalogo.establecer_minimo(otro_local.identificador, producto.identificador, 20)
    catalogo.establecer_minimo(local.identificador, otro_producto.identificador, 0)
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 7
    assert catalogo.obtener_minimo(otro_local.identificador, producto.identificador) == 20
    assert catalogo.obtener_minimo(otro_local.identificador, otro_producto.identificador) is None
    assert catalogo.listar_minimos(local.identificador) == ((producto, 7), (otro_producto, 0))
    assert catalogo.listar_minimos(otro_local.identificador) == ((producto, 20),)


@pytest.mark.parametrize("minimo", [-1, -10, 0.5, 1.0, True, False, None, "0", "3", [], {}])
def test_valores_invalidos_sin_alta_ni_modificacion_parcial(minimo):
    catalogo, producto, local = catalogo_para_minimos()
    error = ValueError if type(minimo) is int else TypeError
    with pytest.raises(error):
        catalogo.establecer_minimo(local.identificador, producto.identificador, minimo)
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) is None
    catalogo.establecer_minimo(local.identificador, producto.identificador, 8)
    with pytest.raises(error):
        catalogo.establecer_minimo(local.identificador, producto.identificador, minimo)
    assert catalogo.listar_minimos(local.identificador) == ((producto, 8),)


@pytest.mark.parametrize("campo", ["local_id", "producto_id"])
@pytest.mark.parametrize("identificador", [None, True, "1", 1.0, 0, -1, 999])
def test_referencias_invalidas_o_inexistentes_no_cambian_configuraciones(campo, identificador):
    catalogo, producto, local = catalogo_para_minimos()
    catalogo.establecer_minimo(local.identificador, producto.identificador, 5)
    datos = {"local_id": local.identificador, "producto_id": producto.identificador, campo: identificador}
    error = KeyError if identificador == 999 else ValueError if type(identificador) is int else TypeError
    with pytest.raises(error):
        catalogo.establecer_minimo(**datos, minimo=9)
    with pytest.raises(error):
        catalogo.obtener_minimo(**datos)
    assert catalogo.listar_minimos(local.identificador) == ((producto, 5),)


def test_cd_no_admite_consulta_ni_configuracion_de_minimos():
    catalogo, producto, local = catalogo_para_minimos()
    cd = catalogo.crear_ubicacion("CD", "Central", "CD")
    catalogo.establecer_minimo(local.identificador, producto.identificador, 4)
    with pytest.raises(ValueError, match="sólo se configuran en locales"):
        catalogo.establecer_minimo(cd.identificador, producto.identificador, 0)
    with pytest.raises(ValueError):
        catalogo.obtener_minimo(cd.identificador, producto.identificador)
    with pytest.raises(ValueError):
        catalogo.listar_minimos(cd.identificador)
    assert catalogo.listar_minimos(local.identificador) == ((producto, 4),)


def test_listado_protege_coleccion_y_conserva_referencias_tras_ediciones_administrativas():
    catalogo, producto, local = catalogo_para_minimos()
    catalogo.establecer_minimo(local.identificador, producto.identificador, 6)
    listado = catalogo.listar_minimos(local.identificador)
    with pytest.raises(AttributeError):
        listado.clear()
    producto.modificar("002", "Arroz integral", producto.categoria, "140")
    local.modificar("L2", "Centro actualizado")
    assert listado[0][0] is producto
    assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 6
    assert catalogo.listar_minimos(local.identificador)[0][0].nombre == "Arroz integral"


def test_catalogos_independientes_y_dominio_con_enteros_python():
    primero, producto, local = catalogo_para_minimos()
    segundo, otro_producto, otro_local = catalogo_para_minimos()
    primero.establecer_minimo(local.identificador, producto.identificador, 10**30)
    assert primero.obtener_minimo(local.identificador, producto.identificador) == 10**30
    assert segundo.obtener_minimo(otro_local.identificador, otro_producto.identificador) is None
    # La interfaz recibe IDs, no instancias externas que puedan hacerse pasar por referencias locales.
    with pytest.raises(TypeError):
        primero.establecer_minimo(otro_local, producto.identificador, 3)
    with pytest.raises(TypeError):
        primero.establecer_minimo(local.identificador, otro_producto, 3)
