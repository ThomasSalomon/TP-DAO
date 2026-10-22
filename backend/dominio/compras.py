"""Compras a proveedores confirmadas e ingresadas al CD (DN-03). Importes en ARS."""

from .catalogo import (
    ConflictoCatalogoError, Producto, Proveedor, Ubicacion, _validar_identificador, importe_a_centavos,
    importe_a_texto,
)
from .fechas import validar_instante


class DetalleCompra:
    """Línea de una compra; sólo la crea su compra y no se transfiere ni se modifica."""

    def __init__(self, compra, numero, producto, cantidad, costo_unitario):
        if not isinstance(producto, Producto):
            raise TypeError("El producto debe ser un Producto.")
        if type(cantidad) is not int:
            raise TypeError("La cantidad debe ser un entero de unidades.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        self._compra = compra
        self._numero = numero
        self._producto = producto
        self._cantidad = cantidad
        self._costo_unitario_centavos = importe_a_centavos(costo_unitario, "costo unitario")

    @property
    def compra(self):
        return self._compra

    @property
    def numero(self):
        return self._numero

    @property
    def producto(self):
        return self._producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def costo_unitario_centavos(self):
        return self._costo_unitario_centavos

    @property
    def costo_unitario(self):
        return importe_a_texto(self._costo_unitario_centavos)

    @property
    def subtotal_centavos(self):
        return self._cantidad * self._costo_unitario_centavos


class Compra:
    """Documento confirmado: se construye completo y no admite cambios posteriores."""

    def __init__(self, identificador, proveedor, centro, instante, lineas):
        """lineas: secuencia de (producto, cantidad, costo unitario en texto ARS)."""
        _validar_identificador(identificador)
        if not isinstance(proveedor, Proveedor):
            raise TypeError("El proveedor debe ser un Proveedor.")
        if not isinstance(centro, Ubicacion):
            raise TypeError("El destino debe ser una Ubicacion.")
        if centro.tipo != "CD":
            raise ValueError("Las compras ingresan al Centro de Distribución, no a un local.")
        validar_instante(instante)
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        if not lineas:
            raise ValueError("La compra debe tener al menos una línea.")

        self._identificador = identificador
        self._proveedor = proveedor
        self._centro = centro
        self._instante = instante
        # Composición: la compra crea sus detalles y valida todos antes de quedar construida.
        detalles = []
        for numero, (producto, cantidad, costo_unitario) in enumerate(lineas, start=1):
            if any(detalle.producto is producto for detalle in detalles):
                raise ValueError(f"Línea {numero}: un producto no puede repetirse dentro de la misma compra.")
            try:
                detalles.append(DetalleCompra(self, numero, producto, cantidad, costo_unitario))
            except (TypeError, ValueError) as error:
                # Se conserva el tipo de error y se indica la línea para poder corregirla.
                raise type(error)(f"Línea {numero}: {error}") from None
        self._detalles = tuple(detalles)

    @property
    def identificador(self):
        return self._identificador

    @property
    def proveedor(self):
        return self._proveedor

    @property
    def centro(self):
        return self._centro

    @property
    def instante(self):
        return self._instante

    @property
    def detalles(self):
        return self._detalles

    @property
    def total_centavos(self):
        return sum(detalle.subtotal_centavos for detalle in self._detalles)

    @property
    def total(self):
        return importe_a_texto(self.total_centavos)


class RegistroCompras:
    """Compras confirmadas en orden de registro y costo de referencia por producto."""

    def __init__(self):
        self._compras = {}

    def registrar(self, proveedor, centro, lineas, instante, inventario):
        """Confirma una compra nueva e ingresa todas sus cantidades al CD.

        Valida todo antes de cambiar el registro o el inventario.
        """
        compra = Compra(len(self._compras) + 1, proveedor, centro, instante, lineas)
        if not proveedor.activo:
            raise ConflictoCatalogoError("El proveedor está inactivo y no admite nuevas compras.")
        if any(not detalle.producto.activo for detalle in compra.detalles):
            raise ConflictoCatalogoError("Los productos inactivos no admiten nuevas compras.")
        movimientos = inventario.ingresar_compra(compra)
        self._compras[compra.identificador] = compra
        return compra, movimientos

    def restaurar(self, compra):
        """Incorpora una compra ya confirmada; no repite su ingreso de stock."""
        if not isinstance(compra, Compra):
            raise TypeError("La compra debe ser una Compra.")
        if compra.identificador != len(self._compras) + 1:
            raise ValueError("Las compras se restauran en orden de identificador.")
        self._compras[compra.identificador] = compra

    def obtener(self, identificador):
        _validar_identificador(identificador)
        return self._compras[identificador]

    def listar(self):
        return tuple(self._compras.values())

    def costo_referencia(self, producto):
        """Costo de la última compra confirmada del producto, o None si nunca se compró."""
        ultima = None
        for compra in self._compras.values():
            for detalle in compra.detalles:
                if detalle.producto is producto and (
                    ultima is None
                    or (compra.instante, compra.identificador) > (ultima.compra.instante, ultima.compra.identificador)
                ):
                    ultima = detalle
        return None if ultima is None else ultima.costo_unitario_centavos
