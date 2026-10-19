"""Categorías y productos de F-01.1. Los precios se expresan en ARS."""


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
        self.modificar(codigo, nombre)

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
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        existente = self._catalogo.buscar_categoria_por_codigo(codigo)
        if existente is not None and existente is not self:
            raise ValueError("Ya existe una categoría con ese código.")

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
        self.modificar(codigo, nombre, categoria, precio)

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
        codigo = _texto_no_vacio(codigo, "código")
        nombre = _texto_no_vacio(nombre, "nombre")
        if not isinstance(categoria, Categoria):
            raise TypeError("La categoría debe ser una Categoria.")
        if not self._catalogo.contiene_categoria(categoria):
            raise ValueError("La categoría no pertenece a este catálogo.")
        centavos = _precio_a_centavos(precio)
        existente = self._catalogo.buscar_producto_por_codigo(codigo)
        if existente is not None and existente is not self:
            raise ValueError("Ya existe un producto con ese código.")

        self._codigo = codigo
        self._nombre = nombre
        self._categoria = categoria
        self._precio_centavos = centavos

    def cambiar_precio(self, precio):
        self._precio_centavos = _precio_a_centavos(precio)


class Catalogo:
    """Registro local de objetos. No persiste datos ni comparte estado global."""

    def __init__(self):
        self._categorias = {}
        self._productos = {}

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

    def listar_categorias(self):
        return tuple(self._categorias.values())

    def listar_productos(self):
        return tuple(self._productos.values())

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
