"""Carga reproducible de datos ficticios para los filtros y reportes del TP."""

from argparse import ArgumentParser
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from . import api_compras, api_devoluciones, api_logistica, api_ventas, create_app
from .dominio import MEDIOS_PAGO, ZONA_ARGENTINA, importe_a_texto
from .persistencia import ruta_base_datos_predeterminada


CATALOGO = (
    ("ALM", "Almacén", "Distribuidora Trigal", (
        ("ARR", "Arroz largo fino", 245000), ("FID", "Fideos tirabuzón", 179050),
        ("ACE", "Aceite de girasol", 485000), ("LEN", "Lentejas secas", 295000),
    )),
    ("BEB", "Bebidas", "Distribuidora Sierras", (
        ("AGU", "Agua mineral", 135000), ("JUG", "Jugo de naranja", 249090),
        ("SOD", "Soda sifón", 175000), ("GAZ", "Gaseosa de pomelo", 289000),
    )),
    ("LIM", "Limpieza", "Distribuidora Espuma", (
        ("DET", "Detergente limón", 238050), ("LAV", "Lavandina", 199000),
        ("ESP", "Esponja doble faz", 92500), ("JAB", "Jabón para ropa", 335000),
    )),
)
LOCALES = (("CEN", "Centro"), ("NCO", "Nueva Córdoba"), ("GUE", "General Paz"))
ANIO = 2026
MESES = (8, 9, 10, 11)


def solicitar(cliente, metodo, ruta, datos=None, estado=200):
    respuesta = cliente.open(f"/api{ruta}", method=metodo, json={} if datos is None else datos)
    resultado = respuesta.get_json()
    if respuesta.status_code != estado:
        raise RuntimeError(f"{metodo} {ruta}: HTTP {respuesta.status_code}, se esperaba {estado}. {resultado}")
    return resultado


def alta(cliente, ruta, **datos):
    return solicitar(cliente, "POST", ruta, datos, estado=201)


def cargar_catalogo(cliente):
    alta(cliente, "/ubicaciones", codigo="CD", nombre="Centro de Distribución", tipo="CD")
    locales = [alta(cliente, "/ubicaciones", codigo=codigo, nombre=nombre, tipo="LOCAL")["id"]
               for codigo, nombre in LOCALES]
    compras_por_proveedor, precios = {}, {}
    for codigo, nombre, proveedor, articulos in CATALOGO:
        categoria = alta(cliente, "/categorias", codigo=codigo, nombre=nombre)["id"]
        proveedor_id = alta(cliente, "/proveedores", codigo=f"PR-{codigo}", nombre=proveedor)["id"]
        productos = []
        for indice, (sku, descripcion, precio) in enumerate(articulos):
            producto = alta(cliente, "/productos", codigo=sku, nombre=descripcion,
                            categoria_id=categoria, precio=importe_a_texto(precio))["id"]
            productos.append(producto)
            precios[producto] = precio
            for local in locales:
                # Una referencia por categoría queda cerca del mínimo o por debajo en cada local.
                minimo = 120 if indice == 0 else 8 + indice * 3
                solicitar(cliente, "PUT", f"/ubicaciones/{local}/minimos/{producto}", {"minimo": minimo})
        compras_por_proveedor[proveedor_id] = productos

    inactivo = alta(cliente, "/productos", codigo="JAB-ANT", nombre="Jabón presentación anterior",
                   categoria_id=categoria, precio="2500")["id"]
    solicitar(cliente, "PATCH", f"/productos/{inactivo}/estado", {"activo": False})
    return locales, compras_por_proveedor, precios


def preparar_bulto(cliente, local, cantidades):
    lineas = [{"producto_id": producto, "cantidad": cantidad} for producto, cantidad in cantidades.items()]
    necesidades = [alta(cliente, "/necesidades", local_id=local, **linea)["id"] for linea in lineas]
    orden = alta(cliente, "/ordenes", local_id=local, necesidad_ids=necesidades)["id"]
    bulto = alta(cliente, f"/ordenes/{orden}/bultos", lineas=lineas)["id"]
    return f"/bultos/{bulto}", f"DEMO-{bulto:04d}"


def distribuir(cliente, local, cantidades, estado="VERIFICADO"):
    ruta, precinto = preparar_bulto(cliente, local, cantidades)
    if estado == "PREPARADO":
        return
    solicitar(cliente, "POST", f"{ruta}/precintar", {"precinto": precinto})
    solicitar(cliente, "POST", f"{ruta}/despachar")
    if estado == "EN_TRANSITO":
        return
    recibido = solicitar(cliente, "POST", f"{ruta}/recibir", {
        "local_id": local,
        "precinto_leido": "OTRO-PRECINTO" if estado == "PRECINTO_DISTINTO" else precinto,
        "precinto_intacto": estado != "PRECINTO_ROTO",
    })
    if estado == "VERIFICADO":
        solicitar(cliente, "POST", f"{ruta}/verificar")
        solicitar(cliente, "POST", f"/remitos/{recibido['remito']['id']}/verificar")


def vender(cliente, local, clave, cantidades, precios, medio, pago_mixto):
    total = sum(precios[producto] * cantidad for producto, cantidad in cantidades.items())
    cobros = [{"medio_pago_id": medio, "importe": importe_a_texto(total)}]
    if pago_mixto:
        mitad = total // 2
        otro_medio = MEDIOS_PAGO[medio % len(MEDIOS_PAGO)][0]
        cobros[0]["importe"] = importe_a_texto(mitad)
        cobros.append({"medio_pago_id": otro_medio, "importe": importe_a_texto(total - mitad)})
    return alta(cliente, "/ventas", local_id=local, clave_operacion=clave, cobros=cobros, lineas=[
        {"producto_id": producto, "cantidad": cantidad} for producto, cantidad in cantidades.items()
    ])


def cargar_operaciones(cliente, fijar_fecha, locales, compras_por_proveedor, precios):
    productos = list(precios)
    for mes in MESES:
        fijar_fecha(mes, 2)
        for proveedor, surtido in compras_por_proveedor.items():
            alta(cliente, "/compras", proveedor_id=proveedor, lineas=[
                {"producto_id": producto, "cantidad": 135 + (producto + mes) % 4 * 10,
                 "costo_unitario": importe_a_texto(precios[producto] * (54 + mes + producto % 4) // 100)}
                for producto in surtido
            ])

        fijar_fecha(mes, 4)
        for indice, local in enumerate(locales):
            distribuir(cliente, local, {producto: 18 + (producto + indice + mes) % 5 * 3 for producto in productos})

        primeras_ventas = []
        for turno in range(8):
            fijar_fecha(mes, 6 + turno)
            for indice, local in enumerate(locales):
                posicion = (mes + turno + indice * 3) % len(productos)
                producto = productos[posicion]
                cantidades = {producto: 1 + (turno + indice) % 4}
                if turno % 2 == 0:
                    cantidades[productos[(posicion + 4) % len(productos)]] = 1 + indice
                medio = MEDIOS_PAGO[(turno + indice + mes) % len(MEDIOS_PAGO)][0]
                venta = vender(cliente, local, f"DEMO-V-{mes}-{turno}-{local}", cantidades, precios, medio,
                               pago_mixto=turno % 4 == 2)
                if turno == 0:
                    primeras_ventas.append(venta)

        fijar_fecha(mes, 15)
        for indice, venta in enumerate(primeras_ventas):
            apto = (mes + indice) % 2 == 0
            alta(cliente, "/devoluciones", venta_id=venta["id"], clave_operacion=f"DEMO-D-{venta['id']}",
                 motivo="Cambio de producto" if apto else "Envase dañado",
                 lineas=[{"linea": 1, "cantidad": 1, "apto": apto}], reintegros=[
                     {"medio_pago_id": venta["cobros"][0]["medio"]["id"],
                      "importe": venta["lineas"][0]["precio_unitario"]},
                 ])

        fijar_fecha(mes, 17)
        distribuir(cliente, locales[mes % len(locales)], {productos[mes % 4]: 4, productos[4]: 2}, "PRECINTO_ROTO")
        distribuir(cliente, locales[(mes + 1) % len(locales)], {productos[8 + mes % 4]: 3}, "PRECINTO_DISTINTO")

    fijar_fecha(MESES[-1], 19)
    for local, producto, estado in zip(locales, productos, ("PREPARADO", "EN_TRANSITO", "RECIBIDO")):
        distribuir(cliente, local, {producto: 6}, estado)


def cargar_demo(ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("xb"):
        pass
    try:
        app = create_app(base_datos=ruta)
        app.testing = True
        instante = None

        def fijar_fecha(mes, dia):
            nonlocal instante
            instante = datetime(ANIO, mes, dia, 10, tzinfo=ZONA_ARGENTINA)

        # El reloj simulado solo se usa durante la carga, en este proceso.
        with ExitStack() as cambios:
            for modulo in (api_compras, api_logistica, api_ventas, api_devoluciones):
                cambios.enter_context(patch.object(modulo, "ahora", lambda: instante))
            cliente = app.test_client()
            cargar_operaciones(cliente, fijar_fecha, *cargar_catalogo(cliente))
    except BaseException:
        ruta.unlink()
        raise


def principal():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ruta_base_datos_predeterminada(),
                        help="ruta de una base nueva (por defecto, la que usaría Flask)")
    ruta = parser.parse_args().base.resolve()
    try:
        cargar_demo(ruta)
    except FileExistsError:
        parser.error(f"Ya existe {ruta}. Elegí una ruta nueva con --base.")
    print(f"Datos de demostración cargados en {ruta}")


if __name__ == "__main__":
    principal()
