"""Ventas de los locales, cobros por medio de pago y comprobante interno (DN-05). Importes en ARS."""

from .catalogo import (
    PRECIO_MAXIMO_CENTAVOS, ConflictoCatalogoError, Producto, Ubicacion, _texto_no_vacio, _validar_identificador,
    importe_a_centavos, importe_a_texto,
)
from .fechas import validar_instante


class MedioPago:
    """Medio de cobro del catálogo fijo; no autoriza pagos reales."""

    def __init__(self, identificador, codigo, nombre):
        _validar_identificador(identificador)
        self._identificador = identificador
        self._codigo = _texto_no_vacio(codigo, "código")
        self._nombre = _texto_no_vacio(nombre, "nombre")

    @property
    def identificador(self):
        return self._identificador

    @property
    def codigo(self):
        return self._codigo

    @property
    def nombre(self):
        return self._nombre


# Medios precargados (DN-05): no se administran desde la pantalla.
MEDIOS_PAGO = (
    (1, "EFECTIVO", "Efectivo"), (2, "DEBITO", "Débito"), (3, "CREDITO", "Crédito"), (4, "TRANSFERENCIA", "Transferencia"),
)


class DetalleVenta:
    """Línea vendida; conserva precio y costo de referencia del momento de la venta."""

    def __init__(self, venta, numero, producto, cantidad, precio_unitario_centavos, costo_referencia_centavos):
        if not isinstance(producto, Producto):
            raise TypeError("El producto debe ser un Producto.")
        if type(cantidad) is not int:
            raise TypeError("La cantidad debe ser un entero de unidades.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        if type(precio_unitario_centavos) is not int or precio_unitario_centavos <= 0:
            raise ValueError("El precio unitario debe ser un entero positivo de centavos.")
        if costo_referencia_centavos is not None and (
            type(costo_referencia_centavos) is not int or costo_referencia_centavos <= 0
        ):
            raise ValueError("El costo de referencia debe ser un entero positivo de centavos o faltar.")
        self._venta = venta
        self._numero = numero
        self._producto = producto
        self._cantidad = cantidad
        self._precio_unitario_centavos = precio_unitario_centavos
        self._costo_referencia_centavos = costo_referencia_centavos

    @property
    def venta(self):
        return self._venta

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
    def precio_unitario_centavos(self):
        return self._precio_unitario_centavos

    @property
    def costo_referencia_centavos(self):
        """None si el producto no tenía compras: el costo falta, no es cero."""
        return self._costo_referencia_centavos

    @property
    def subtotal_centavos(self):
        return self._cantidad * self._precio_unitario_centavos


class Cobro:
    """Importe aplicado a la venta con un medio de pago."""

    def __init__(self, venta, numero, medio, importe):
        if not isinstance(medio, MedioPago):
            raise TypeError("El medio de pago debe ser un MedioPago.")
        self._venta = venta
        self._numero = numero
        self._medio = medio
        self._importe_centavos = importe_a_centavos(importe, "importe")

    @property
    def venta(self):
        return self._venta

    @property
    def numero(self):
        return self._numero

    @property
    def medio(self):
        return self._medio

    @property
    def importe_centavos(self):
        return self._importe_centavos


class Comprobante:
    """Comprobante interno no fiscal de una venta; consultarlo no registra otra venta."""

    def __init__(self, venta):
        self._venta = venta

    @property
    def numero(self):
        return f"CV-{self._venta.identificador:08d}"

    @property
    def venta(self):
        return self._venta

    @property
    def instante(self):
        return self._venta.instante


class Venta:
    """Documento confirmado: se construye completo con líneas y cobros, y no admite cambios."""

    def __init__(self, identificador, local, instante, lineas, cobros, clave_operacion):
        """lineas: (producto, cantidad, precio en centavos, costo en centavos o None).

        cobros: (medio de pago, importe en texto ARS).
        """
        _validar_identificador(identificador)
        if not isinstance(local, Ubicacion) or local.tipo != "LOCAL":
            raise ValueError("Las ventas las registra un local, no el CD.")
        validar_instante(instante)
        clave = _texto_no_vacio(clave_operacion, "clave de operación")
        if len(clave) > 64:
            raise ValueError("La clave de operación no puede superar 64 caracteres.")
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        if not isinstance(cobros, (list, tuple)):
            raise TypeError("Los cobros deben ser una lista.")
        if not lineas:
            raise ValueError("La venta debe tener al menos una línea.")
        if not cobros:
            raise ValueError("La venta debe tener al menos un cobro.")

        self._identificador = identificador
        self._local = local
        self._instante = instante
        self._clave_operacion = clave
        # Composición: la venta crea sus líneas, cobros y comprobante y valida todo antes de existir.
        detalles = []
        for numero, (producto, cantidad, precio, costo) in enumerate(lineas, start=1):
            if any(detalle.producto is producto for detalle in detalles):
                raise ValueError(f"Línea {numero}: un producto no puede repetirse dentro de la misma venta.")
            try:
                detalles.append(DetalleVenta(self, numero, producto, cantidad, precio, costo))
            except (TypeError, ValueError) as error:
                raise type(error)(f"Línea {numero}: {error}") from None
        self._detalles = tuple(detalles)
        if self.total_centavos > PRECIO_MAXIMO_CENTAVOS:
            raise ValueError("El total de la venta supera el máximo admitido.")

        registrados = []
        for numero, (medio, importe) in enumerate(cobros, start=1):
            if any(cobro.medio is medio for cobro in registrados):
                raise ValueError(f"Cobro {numero}: un medio de pago no puede repetirse en la misma venta.")
            try:
                registrados.append(Cobro(self, numero, medio, importe))
            except (TypeError, ValueError) as error:
                raise type(error)(f"Cobro {numero}: {error}") from None
        self._cobros = tuple(registrados)
        cobrado = sum(cobro.importe_centavos for cobro in self._cobros)
        if cobrado != self.total_centavos:
            raise ValueError(
                f"Los cobros suman {importe_a_texto(cobrado)} y el total de la venta es {self.total}."
            )
        self._comprobante = Comprobante(self)

    @property
    def identificador(self):
        return self._identificador

    @property
    def local(self):
        return self._local

    @property
    def instante(self):
        return self._instante

    @property
    def clave_operacion(self):
        return self._clave_operacion

    @property
    def detalles(self):
        return self._detalles

    @property
    def cobros(self):
        return self._cobros

    @property
    def comprobante(self):
        return self._comprobante

    @property
    def total_centavos(self):
        return sum(detalle.subtotal_centavos for detalle in self._detalles)

    @property
    def total(self):
        return importe_a_texto(self.total_centavos)


class RegistroVentas:
    """Ventas confirmadas en orden de registro, medios de pago y control de claves de operación."""

    def __init__(self):
        self._ventas = {}
        self._por_clave = {}
        self._medios = {identificador: MedioPago(identificador, codigo, nombre) for identificador, codigo, nombre in MEDIOS_PAGO}

    def registrar(self, local, lineas, cobros, instante, clave_operacion, inventario, caja, compras):
        """Confirma una venta nueva o devuelve la ya registrada con la misma clave.

        lineas: pares (producto, cantidad); el precio es el vigente y el costo el de referencia.
        Devuelve (venta, movimientos de stock, movimientos de caja, nueva).
        """
        existente = self._por_clave.get(_texto_no_vacio(clave_operacion, "clave de operación"))
        if existente is not None:
            return existente, (), (), False
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        lineas_con_valores = []
        for numero, (producto, cantidad) in enumerate(lineas, start=1):
            if not isinstance(producto, Producto):
                raise TypeError(f"Línea {numero}: El producto debe ser un Producto.")
            # Se copian el precio vigente y el costo de referencia: no cambian con el catálogo (RB-12).
            lineas_con_valores.append((producto, cantidad, producto.precio_centavos, compras.costo_referencia(producto)))
        venta = Venta(len(self._ventas) + 1, local, instante, lineas_con_valores, cobros, clave_operacion)
        if not local.activo:
            raise ConflictoCatalogoError("El local está inactivo y no admite nuevas ventas.")
        if any(not detalle.producto.activo for detalle in venta.detalles):
            raise ConflictoCatalogoError("Los productos inactivos no admiten nuevas ventas.")
        movimientos = inventario.vender(venta)
        movimientos_caja = caja.ingresar_venta(venta)
        self._guardar(venta)
        return venta, movimientos, movimientos_caja, True

    def restaurar(self, venta):
        """Incorpora una venta ya confirmada; no repite su salida de stock ni su ingreso de caja."""
        if not isinstance(venta, Venta):
            raise TypeError("La venta debe ser una Venta.")
        if venta.identificador != len(self._ventas) + 1:
            raise ValueError("Las ventas se restauran en orden de identificador.")
        self._guardar(venta)

    def _guardar(self, venta):
        self._ventas[venta.identificador] = venta
        self._por_clave[venta.clave_operacion] = venta

    def obtener(self, identificador):
        _validar_identificador(identificador)
        return self._ventas[identificador]

    def listar(self, local=None):
        return tuple(venta for venta in self._ventas.values() if local is None or venta.local is local)

    def obtener_medio(self, identificador):
        _validar_identificador(identificador)
        return self._medios[identificador]

    def listar_medios(self):
        return tuple(self._medios.values())
