"""Traducción entre los objetos del catálogo y sus filas SQLite."""

from ..dominio import Catalogo


def _precio_texto(centavos):
    return f"{centavos // 100}.{centavos % 100:02d}"


def _verificar_identificador(entidad, identificador):
    # Los IDs nunca se reutilizan ni se borran filas, así que se reconstruyen en orden.
    if entidad.identificador != identificador:
        raise RuntimeError("La base contiene identificadores no consecutivos.")


def cargar_catalogo(conexion):
    """Reconstruye el catálogo con la API del dominio, que vuelve a validar cada dato."""
    catalogo = Catalogo()
    cursor = conexion.cursor()

    # Todos se crean activos para restablecer referencias y mínimos; las bajas se aplican al final.
    cursor.execute("SELECT id, codigo, nombre FROM categorias ORDER BY id")
    for identificador, codigo, nombre in cursor.fetchall():
        _verificar_identificador(catalogo.crear_categoria(codigo, nombre), identificador)

    cursor.execute("SELECT id, codigo, nombre, categoria_id, precio_centavos FROM productos ORDER BY id")
    for identificador, codigo, nombre, categoria_id, precio_centavos in cursor.fetchall():
        producto = catalogo.crear_producto(
            codigo, nombre, catalogo.obtener_categoria(categoria_id), _precio_texto(precio_centavos)
        )
        _verificar_identificador(producto, identificador)

    cursor.execute("SELECT id, codigo, nombre FROM proveedores ORDER BY id")
    for identificador, codigo, nombre in cursor.fetchall():
        _verificar_identificador(catalogo.crear_proveedor(codigo, nombre), identificador)

    cursor.execute("SELECT id, codigo, nombre, tipo FROM ubicaciones ORDER BY id")
    for identificador, codigo, nombre, tipo in cursor.fetchall():
        _verificar_identificador(catalogo.crear_ubicacion(codigo, nombre, tipo), identificador)

    cursor.execute("SELECT ubicacion_id, producto_id, minimo FROM minimos")
    for ubicacion_id, producto_id, minimo in cursor.fetchall():
        catalogo.establecer_minimo(ubicacion_id, producto_id, minimo)

    reservas = {
        "categoria": (catalogo.obtener_categoria, catalogo.reservar_codigo_categoria),
        "producto": (catalogo.obtener_producto, catalogo.reservar_codigo_producto),
        "proveedor": (catalogo.obtener_proveedor, catalogo.reservar_codigo_proveedor),
        "ubicacion": (catalogo.obtener_ubicacion, catalogo.reservar_codigo_ubicacion),
    }
    cursor.execute("SELECT entidad, codigo, entidad_id FROM codigos_reservados")
    for entidad, codigo, entidad_id in cursor.fetchall():
        obtener, reservar = reservas[entidad]
        reservar(codigo, obtener(entidad_id))

    # Los productos se desactivan antes que sus categorías para respetar esa regla.
    bajas = (
        ("productos", catalogo.desactivar_producto),
        ("categorias", catalogo.desactivar_categoria),
        ("proveedores", catalogo.desactivar_proveedor),
        ("ubicaciones", catalogo.desactivar_ubicacion),
    )
    for tabla, desactivar in bajas:
        # El nombre de tabla proviene de la tupla fija anterior; los valores nunca se interpolan.
        cursor.execute(f"SELECT id FROM {tabla} WHERE activo = 0 ORDER BY id")
        for (identificador,) in cursor.fetchall():
            desactivar(identificador)
    return catalogo


def _reservar_codigo(conexion, entidad, codigo, entidad_id):
    # Misma clave que el dominio: el código no distingue mayúsculas y nunca se libera.
    conexion.execute(
        """
        INSERT INTO codigos_reservados (entidad, clave, codigo, entidad_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (entidad, clave) DO NOTHING
        """,
        (entidad, codigo.casefold(), codigo, entidad_id),
    )


def guardar_categoria(conexion, categoria):
    """Alta, modificación o baja: guarda el estado actual completo de la categoría."""
    conexion.execute(
        """
        INSERT INTO categorias (id, codigo, nombre, activo) VALUES (?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            codigo = excluded.codigo, nombre = excluded.nombre, activo = excluded.activo
        """,
        (categoria.identificador, categoria.codigo, categoria.nombre, int(categoria.activo)),
    )
    _reservar_codigo(conexion, "categoria", categoria.codigo, categoria.identificador)


def guardar_producto(conexion, producto):
    conexion.execute(
        """
        INSERT INTO productos (id, codigo, nombre, categoria_id, precio_centavos, activo)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            codigo = excluded.codigo, nombre = excluded.nombre, categoria_id = excluded.categoria_id,
            precio_centavos = excluded.precio_centavos, activo = excluded.activo
        """,
        (
            producto.identificador, producto.codigo, producto.nombre,
            producto.categoria.identificador, producto.precio_centavos, int(producto.activo),
        ),
    )
    _reservar_codigo(conexion, "producto", producto.codigo, producto.identificador)


def guardar_proveedor(conexion, proveedor):
    conexion.execute(
        """
        INSERT INTO proveedores (id, codigo, nombre, activo) VALUES (?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            codigo = excluded.codigo, nombre = excluded.nombre, activo = excluded.activo
        """,
        (proveedor.identificador, proveedor.codigo, proveedor.nombre, int(proveedor.activo)),
    )
    _reservar_codigo(conexion, "proveedor", proveedor.codigo, proveedor.identificador)


def guardar_ubicacion(conexion, ubicacion):
    # El tipo no se actualiza: es estable desde el alta.
    conexion.execute(
        """
        INSERT INTO ubicaciones (id, codigo, nombre, tipo, activo) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            codigo = excluded.codigo, nombre = excluded.nombre, activo = excluded.activo
        """,
        (ubicacion.identificador, ubicacion.codigo, ubicacion.nombre, ubicacion.tipo, int(ubicacion.activo)),
    )
    _reservar_codigo(conexion, "ubicacion", ubicacion.codigo, ubicacion.identificador)


def guardar_minimo(conexion, local_id, producto_id, minimo):
    conexion.execute(
        """
        INSERT INTO minimos (ubicacion_id, producto_id, minimo) VALUES (?, ?, ?)
        ON CONFLICT (ubicacion_id, producto_id) DO UPDATE SET minimo = excluded.minimo
        """,
        (local_id, producto_id, minimo),
    )
