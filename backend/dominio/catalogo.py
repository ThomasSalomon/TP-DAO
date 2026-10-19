"""Catálogo en memoria de productos y datos administrativos. Precios en ARS."""


class CodigoDuplicadoError(ValueError):
    """Un código comercial ya está registrado dentro del mismo tipo."""


class CentroDistribucionDuplicadoError(ValueError):
    """El catálogo ya tiene un Centro de Distribución registrado."""


class ConflictoCatalogoError(ValueError):
    """Una operación contradice el estado administrativo o sus referencias."""


def _filtrar_estado(registros, estado):
    if not isinstance(estado, str):
        raise TypeError("El filtro de estado debe ser texto.")
    if estado not in ("activos", "inactivos", "todos"):
        raise ValueError("El estado debe ser activos, inactivos o todos.")
    return tuple(item for item in registros if estado == "todos" or item.activo == (estado == "activos"))


def _reservar_codigo(registro, codigo, entidad, mensaje):
    clave = _texto_no_vacio(codigo, "código").casefold()
    existente = registro.get(clave)
    if existente is not None and (
        existente is not entidad or existente.codigo.casefold() != clave
    ):
        raise CodigoDuplicadoError(mensaje)
    registro[clave] = entidad


def _texto_no_vacio(valor, campo):
    if not isinstance(valor, str):
        raise TypeError(f"El {campo} debe ser un texto.")
    valor = valor.strip()
    if not valor:
        raise ValueError(f"El {campo} no puede estar vacío.")
    return valor


def _validar_identificador(identificador):
    if type(identificador) is not int:
        raise TypeError("El identificador debe ser un entero.")
    if identificador <= 0:
        raise ValueError("El identificador debe ser positivo.")


def _precio_a_centavos(precio):
    """Recibe pesos como texto decimal con punto, sin float ni redondeos."""
    texto = _texto_no_vacio(precio, "precio")
    partes = texto.split(".")
    if len(partes) > 2 or any(
        not parte.isascii() or not parte.isdigit() for parte in partes
    ):
        raise ValueError("El precio debe usar dígitos y un punto decimal opcional.")
    if len(partes) == 2 and len(partes[1]) > 2:
        raise ValueError("El precio no puede tener más de dos decimales.")

    centavos = int(partes[0]) * 100
    if len(partes) == 2:
        centavos += int(partes[1].ljust(2, "0"))
    if centavos <= 0:
        raise ValueError("El precio debe ser estrictamente positivo.")
    return centavos


class Categoria:
    """Clasificación compartida por productos; se registra mediante Catalogo."""

    def __init__(self, identificador, codigo, nombre, catalogo):
        _validar_identificador(identificador)
        if not isinstance(catalogo, Catalogo):
            raise TypeError("El catálogo debe ser un Catalogo.")
        self._identificador = identificador
        self._catalogo = catalogo
        self._activo = True
        self.modificar(codigo, nombre)

    @property
    def activo(self):
        return self._activo

    def desactivar(self):
        if self.activo and self._catalogo.tiene_productos_activos(self):
            raise ConflictoCatalogoError("La categoría tiene productos activos asociados.")
        self._activo = False

    @property
    def identificador(self):
        return self._identificador

    @property
    def codigo(self):
        return self._codigo

    @property
    def nombre(self):
        return self._nombre

    def modificar(self, codigo, nombre):
        """Valida todos los datos antes de modificar la misma instancia."""
        if not self.activo:
            raise ConflictoCatalogoError("La categoría está inactiva y no se puede modificar.")
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        self._catalogo.reservar_codigo_categoria(codigo, self)

        self._codigo = codigo
        self._nombre = nombre


class Producto:
    """Producto con una categoría registrada y precio exacto en centavos."""

    def __init__(self, identificador, codigo, nombre, categoria, precio, catalogo):
        _validar_identificador(identificador)
        if not isinstance(catalogo, Catalogo):
            raise TypeError("El catálogo debe ser un Catalogo.")
        self._identificador = identificador
        self._catalogo = catalogo
        self._activo = True
        self.modificar(codigo, nombre, categoria, precio)

    @property
    def activo(self):
        return self._activo

    def desactivar(self):
        self._activo = False

    @property
    def identificador(self):
        return self._identificador

    @property
    def codigo(self):
        return self._codigo

    @property
    def nombre(self):
        return self._nombre

    @property
    def categoria(self):
        return self._categoria

    @property
    def precio_centavos(self):
        return self._precio_centavos

    @property
    def precio(self):
        """Representación textual en pesos ARS, siempre con dos decimales."""
        return f"{self._precio_centavos // 100}.{self._precio_centavos % 100:02d}"

    def modificar(self, codigo, nombre, categoria, precio):
        """Actualiza datos juntos, conservando identidad y referencias válidas."""
        if not self.activo:
            raise ConflictoCatalogoError("El producto está inactivo y no se puede modificar.")
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        if not isinstance(categoria, Categoria):
            raise TypeError("La categoría debe ser una Categoria.")
        if not self._catalogo.contiene_categoria(categoria):
            raise ValueError("La categoría no pertenece a este catálogo.")
        if not categoria.activo:
            raise ConflictoCatalogoError("La categoría está inactiva y no admite nuevas asociaciones.")
        centavos = _precio_a_centavos(precio)
        self._catalogo.reservar_codigo_producto(codigo, self)

        self._codigo = codigo
        self._nombre = nombre
        self._categoria = categoria
        self._precio_centavos = centavos

    def cambiar_precio(self, precio):
        if not self.activo:
            raise ConflictoCatalogoError("El producto está inactivo y no se puede modificar.")
        self._precio_centavos = _precio_a_centavos(precio)


class Proveedor:
    """Datos administrativos, con identidad estable y códigos no reutilizables."""

    def __init__(self, identificador, codigo, nombre, catalogo):
        _validar_identificador(identificador)
        if not isinstance(catalogo, Catalogo):
            raise TypeError("El catálogo debe ser un Catalogo.")
        self._identificador = identificador
        self._catalogo = catalogo
        self._activo = True
        self.modificar(codigo, nombre)

    @property
    def activo(self):
        return self._activo

    def desactivar(self):
        self._activo = False

    @property
    def identificador(self):
        return self._identificador

    @property
    def codigo(self):
        return self._codigo

    @property
    def nombre(self):
        return self._nombre

    def modificar(self, codigo, nombre):
        """Valida todo antes de reservar el código y actualizar la misma instancia."""
        if not self.activo:
            raise ConflictoCatalogoError("El proveedor está inactivo y no se puede modificar.")
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        self._catalogo.reservar_codigo_proveedor(codigo, self)
        self._codigo = codigo
        self._nombre = nombre


class Ubicacion:
    """Local o CD con identidad y tipo estables; sin existencias ni logística."""

    def __init__(self, identificador, codigo, nombre, tipo, catalogo):
        _validar_identificador(identificador)
        if not isinstance(catalogo, Catalogo):
            raise TypeError("El catálogo debe ser un Catalogo.")
        tipo = _texto_no_vacio(tipo, "tipo de ubicación")
        if tipo not in ("LOCAL", "CD"):
            raise ValueError("El tipo de ubicación debe ser LOCAL o CD.")
        self._identificador = identificador
        self._tipo = tipo
        self._catalogo = catalogo
        self._activo = True
        self.modificar(codigo, nombre)

    @property
    def activo(self):
        return self._activo

    def desactivar(self):
        if self.tipo == "CD":
            raise ConflictoCatalogoError(
                "No se permite desactivar el CD sin una política de reemplazo aprobada."
            )
        self._activo = False

    @property
    def identificador(self):
        return self._identificador

    @property
    def tipo(self):
        return self._tipo

    @property
    def codigo(self):
        return self._codigo

    @property
    def nombre(self):
        return self._nombre

    def modificar(self, codigo, nombre):
        """Cambia sólo datos administrativos después de validar la operación."""
        if not self.activo:
            raise ConflictoCatalogoError("La ubicación está inactiva y no se puede modificar.")
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        self._catalogo.reservar_codigo_ubicacion(codigo, self)
        self._codigo = codigo
        self._nombre = nombre


class Catalogo:
    """Registro local de objetos. No persiste datos ni comparte estado global."""

    def __init__(self):
        self._categorias = {}
        self._codigos_categorias = {}
        self._productos = {}
        self._codigos_productos = {}
        self._proveedores = {}
        self._codigos_proveedores = {}
        self._ubicaciones = {}
        self._codigos_ubicaciones = {}
        self._minimos = {}

    def tiene_productos_activos(self, categoria):
        return any(item.activo and item.categoria is categoria for item in self._productos.values())

    def reservar_codigo_categoria(self, codigo, categoria):
        _reservar_codigo(self._codigos_categorias, codigo, categoria, "Ya existe una categoría con ese código.")

    def reservar_codigo_producto(self, codigo, producto):
        _reservar_codigo(self._codigos_productos, codigo, producto, "Ya existe un producto con ese código.")

    def desactivar_categoria(self, identificador):
        categoria = self.obtener_categoria(identificador)
        categoria.desactivar()
        return categoria

    def desactivar_producto(self, identificador):
        producto = self.obtener_producto(identificador)
        producto.desactivar()
        return producto

    def desactivar_proveedor(self, identificador):
        proveedor = self.obtener_proveedor(identificador)
        proveedor.desactivar()
        return proveedor

    def desactivar_ubicacion(self, identificador):
        ubicacion = self.obtener_ubicacion(identificador)
        ubicacion.desactivar()
        return ubicacion

    def _local_para_minimos(self, identificador):
        local = self.obtener_ubicacion(identificador)
        if local.tipo != "LOCAL":
            raise ValueError("Los mínimos sólo se configuran en locales, no en el CD.")
        return local

    def establecer_minimo(self, local_id, producto_id, minimo):
        """Configura unidades del par registrado; no modifica existencias."""
        local = self._local_para_minimos(local_id)
        producto = self.obtener_producto(producto_id)
        if not local.activo or not producto.activo:
            raise ConflictoCatalogoError("El producto y el local deben estar activos para configurar mínimos.")
        if type(minimo) is not int:
            raise TypeError("El mínimo debe ser un entero de unidades.")
        if minimo < 0:
            raise ValueError("El mínimo no puede ser negativo.")
        self._minimos[(local.identificador, producto.identificador)] = minimo
        return minimo

    def obtener_minimo(self, local_id, producto_id):
        """None indica ausencia; cero es una configuración explícita."""
        local = self._local_para_minimos(local_id)
        producto = self.obtener_producto(producto_id)
        return self._minimos.get((local.identificador, producto.identificador))

    def listar_minimos(self, local_id):
        """Devuelve pares (producto registrado, mínimo) sin exponer el diccionario."""
        local = self._local_para_minimos(local_id)
        return tuple(
            (self.obtener_producto(producto_id), minimo)
            for (ubicacion_id, producto_id), minimo in self._minimos.items()
            if ubicacion_id == local.identificador
        )

    def reservar_codigo_ubicacion(self, codigo, ubicacion):
        """Protege máximo de un CD y códigos históricos de todas las ubicaciones."""
        if ubicacion.tipo == "CD" and any(
            item.tipo == "CD" and item is not ubicacion
            for item in self._ubicaciones.values()
        ):
            raise CentroDistribucionDuplicadoError(
                "Ya existe un Centro de Distribución registrado."
            )
        _reservar_codigo(self._codigos_ubicaciones, codigo, ubicacion, "El código de ubicación ya fue registrado.")

    def crear_ubicacion(self, codigo, nombre, tipo):
        identificador = len(self._ubicaciones) + 1
        ubicacion = Ubicacion(identificador, codigo, nombre, tipo, self)
        self._ubicaciones[identificador] = ubicacion
        return ubicacion

    def obtener_ubicacion(self, identificador):
        _validar_identificador(identificador)
        return self._ubicaciones[identificador]

    def buscar_ubicacion_por_codigo(self, codigo):
        clave = _texto_no_vacio(codigo, "código").casefold()
        for ubicacion in self._ubicaciones.values():
            if ubicacion.codigo.casefold() == clave:
                return ubicacion
        return None

    def listar_ubicaciones(self, estado="activos"):
        return _filtrar_estado(self._ubicaciones.values(), estado)

    def modificar_ubicacion(self, identificador, codigo, nombre):
        ubicacion = self.obtener_ubicacion(identificador)
        ubicacion.modificar(codigo, nombre)
        return ubicacion

    def reservar_codigo_proveedor(self, codigo, proveedor):
        """Conserva códigos históricos; sólo permite mantener el código vigente."""
        _reservar_codigo(self._codigos_proveedores, codigo, proveedor, "El código de proveedor ya fue registrado.")

    def crear_proveedor(self, codigo, nombre):
        identificador = len(self._proveedores) + 1
        proveedor = Proveedor(identificador, codigo, nombre, self)
        self._proveedores[identificador] = proveedor
        return proveedor

    def obtener_proveedor(self, identificador):
        _validar_identificador(identificador)
        return self._proveedores[identificador]

    def buscar_proveedor_por_codigo(self, codigo):
        clave = _texto_no_vacio(codigo, "código").casefold()
        for proveedor in self._proveedores.values():
            if proveedor.codigo.casefold() == clave:
                return proveedor
        return None

    def listar_proveedores(self, estado="activos"):
        return _filtrar_estado(self._proveedores.values(), estado)

    def modificar_proveedor(self, identificador, codigo, nombre):
        proveedor = self.obtener_proveedor(identificador)
        proveedor.modificar(codigo, nombre)
        return proveedor

    def crear_categoria(self, codigo, nombre):
        identificador = len(self._categorias) + 1
        categoria = Categoria(identificador, codigo, nombre, self)
        self._categorias[identificador] = categoria
        return categoria

    def crear_producto(self, codigo, nombre, categoria, precio):
        identificador = len(self._productos) + 1
        producto = Producto(identificador, codigo, nombre, categoria, precio, self)
        self._productos[identificador] = producto
        return producto

    def obtener_categoria(self, identificador):
        _validar_identificador(identificador)
        return self._categorias[identificador]

    def obtener_producto(self, identificador):
        _validar_identificador(identificador)
        return self._productos[identificador]

    def buscar_categoria_por_codigo(self, codigo):
        codigo = _texto_no_vacio(codigo, "código").casefold()
        for categoria in self._categorias.values():
            if categoria.codigo.casefold() == codigo:
                return categoria
        return None

    def buscar_producto_por_codigo(self, codigo):
        codigo = _texto_no_vacio(codigo, "código").casefold()
        for producto in self._productos.values():
            if producto.codigo.casefold() == codigo:
                return producto
        return None

    def listar_categorias(self, estado="activos"):
        return _filtrar_estado(self._categorias.values(), estado)

    def listar_productos(self, estado="activos"):
        return _filtrar_estado(self._productos.values(), estado)

    def contiene_categoria(self, categoria):
        return (
            isinstance(categoria, Categoria)
            and self._categorias.get(categoria.identificador) is categoria
        )

    def modificar_categoria(self, identificador, codigo, nombre):
        categoria = self.obtener_categoria(identificador)
        categoria.modificar(codigo, nombre)
        return categoria

    def modificar_producto(self, identificador, codigo, nombre, categoria, precio):
        producto = self.obtener_producto(identificador)
        producto.modificar(codigo, nombre, categoria, precio)
        return producto
