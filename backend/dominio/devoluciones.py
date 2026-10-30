"""Devoluciones de ventas registradas, con aptitud por línea y reintegro por medio (DN-07). Importes en ARS."""

from .catalogo import (
    ConflictoCatalogoError, _texto_no_vacio, _validar_identificador, importe_a_centavos, importe_a_texto,
)
from .errores import ConflictoOperacionError
from .fechas import validar_instante
from .ventas import DetalleVenta, MedioPago, Venta

MOTIVO_MAXIMO = 200


class DetalleDevolucion:
    """Cantidad devuelta de una línea vendida; reintegra al precio histórico de esa línea."""

    def __init__(self, devolucion, numero, detalle_venta, cantidad, apto):
        if not isinstance(detalle_venta, DetalleVenta):
            raise TypeError("La línea vendida debe ser un DetalleVenta.")
        if type(cantidad) is not int:
            raise TypeError("La cantidad debe ser un entero de unidades.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        if cantidad > detalle_venta.cantidad:
            raise ValueError(f"Se vendieron {detalle_venta.cantidad} unidades y se intenta devolver {cantidad}.")
        if type(apto) is not bool:
            raise TypeError("La aptitud debe indicarse como verdadero o falso.")
        self._devolucion = devolucion
        self._numero = numero
        self._detalle_venta = detalle_venta
        self._cantidad = cantidad
        self._apto = apto

    @property
    def devolucion(self):
        return self._devolucion

    @property
    def numero(self):
        return self._numero

    @property
    def detalle_venta(self):
        return self._detalle_venta

    @property
    def producto(self):
        return self._detalle_venta.producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def apto(self):
        return self._apto

    @property
    def condicion_destino(self):
        """Lo apto vuelve a ser vendible; lo no apto queda en custodia, sin venderse."""
        return "DISPONIBLE" if self._apto else "BLOQUEADO"

    @property
    def importe_reintegro_centavos(self):
        return self._cantidad * self._detalle_venta.precio_unitario_centavos


class Reintegro:
    """Importe devuelto al comprador con uno de los medios cobrados en la venta."""

    def __init__(self, devolucion, numero, medio, importe):
        if not isinstance(medio, MedioPago):
            raise TypeError("El medio de pago debe ser un MedioPago.")
        self._devolucion = devolucion
        self._numero = numero
        self._medio = medio
        self._importe_centavos = importe_a_centavos(importe, "importe")

    @property
    def devolucion(self):
        return self._devolucion

    @property
    def numero(self):
        return self._numero

    @property
    def medio(self):
        return self._medio

    @property
    def importe_centavos(self):
        return self._importe_centavos


class Devolucion:
    """Documento confirmado: se construye completo con líneas y reintegros, y no admite cambios."""

    def __init__(self, identificador, venta, instante, lineas, reintegros, motivo, clave_operacion):
        """lineas: (línea vendida, cantidad, apto). reintegros: (medio de pago, importe en texto ARS)."""
        _validar_identificador(identificador)
        if not isinstance(venta, Venta):
            raise TypeError("La venta debe ser una Venta.")
        validar_instante(instante)
        if instante < venta.instante:
            raise ValueError("La devolución no puede ser anterior a la venta.")
        motivo = _texto_no_vacio(motivo, "motivo")
        if len(motivo) > MOTIVO_MAXIMO:
            raise ValueError(f"El motivo no puede superar {MOTIVO_MAXIMO} caracteres.")
        clave = _texto_no_vacio(clave_operacion, "clave de operación")
        if len(clave) > 64:
            raise ValueError("La clave de operación no puede superar 64 caracteres.")
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        if not isinstance(reintegros, (list, tuple)):
            raise TypeError("Los reintegros deben ser una lista.")
        if not lineas:
            raise ValueError("La devolución debe tener al menos una línea.")
        if not reintegros:
            raise ValueError("La devolución debe tener al menos un reintegro.")

        self._identificador = identificador
        self._venta = venta
        self._instante = instante
        self._motivo = motivo
        self._clave_operacion = clave
        # Composición: la devolución crea sus líneas y reintegros y valida todo antes de existir.
        detalles = []
        for numero, (detalle_venta, cantidad, apto) in enumerate(lineas, start=1):
            if isinstance(detalle_venta, DetalleVenta) and detalle_venta.venta is not venta:
                raise ValueError(f"Línea {numero}: la línea indicada no pertenece a la venta.")
            if any(detalle.detalle_venta is detalle_venta for detalle in detalles):
                raise ValueError(f"Línea {numero}: una línea vendida no puede repetirse en la misma devolución.")
            try:
                detalles.append(DetalleDevolucion(self, numero, detalle_venta, cantidad, apto))
            except (TypeError, ValueError) as error:
                raise type(error)(f"Línea {numero}: {error}") from None
        self._detalles = tuple(detalles)

        cobrados = {cobro.medio for cobro in venta.cobros}
        registrados = []
        for numero, (medio, importe) in enumerate(reintegros, start=1):
            if any(reintegro.medio is medio for reintegro in registrados):
                raise ValueError(f"Reintegro {numero}: un medio de pago no puede repetirse en la misma devolución.")
            try:
                registrados.append(Reintegro(self, numero, medio, importe))
            except (TypeError, ValueError) as error:
                raise type(error)(f"Reintegro {numero}: {error}") from None
            if medio not in cobrados:
                raise ValueError(f"Reintegro {numero}: la venta no se cobró con {medio.nombre}.")
        self._reintegros = tuple(registrados)
        reintegrado = sum(reintegro.importe_centavos for reintegro in self._reintegros)
        if reintegrado != self.total_centavos:
            raise ValueError(
                f"Los reintegros suman {importe_a_texto(reintegrado)} y el total a reintegrar es {self.total}."
            )

    @property
    def identificador(self):
        return self._identificador

    @property
    def numero(self):
        return f"DV-{self._identificador:08d}"

    @property
    def venta(self):
        return self._venta

    @property
    def local(self):
        """Se recibe en el mismo local de la venta (DN-07)."""
        return self._venta.local

    @property
    def instante(self):
        return self._instante

    @property
    def motivo(self):
        return self._motivo

    @property
    def clave_operacion(self):
        return self._clave_operacion

    @property
    def detalles(self):
        return self._detalles

    @property
    def reintegros(self):
        return self._reintegros

    @property
    def total_centavos(self):
        return sum(detalle.importe_reintegro_centavos for detalle in self._detalles)

    @property
    def total(self):
        return importe_a_texto(self.total_centavos)


class RegistroDevoluciones:
    """Devoluciones confirmadas en orden de registro; controla cantidades y reintegros acumulados por venta."""

    def __init__(self):
        self._devoluciones = {}
        self._por_clave = {}

    def registrar(self, venta, lineas, reintegros, motivo, instante, clave_operacion, inventario, caja):
        """Confirma una devolución nueva o devuelve la ya registrada con la misma clave.

        Devuelve (devolución, movimientos de stock, movimientos de caja, nueva).
        """
        existente = self._por_clave.get(_texto_no_vacio(clave_operacion, "clave de operación"))
        if existente is not None:
            return existente, (), (), False
        devolucion = Devolucion(
            len(self._devoluciones) + 1, venta, instante, lineas, reintegros, motivo, clave_operacion,
        )
        if not devolucion.local.activo:
            raise ConflictoCatalogoError("El local está inactivo y no admite nuevas devoluciones.")
        for detalle in devolucion.detalles:
            remanente = self.remanente(detalle.detalle_venta)
            if detalle.cantidad > remanente:
                raise ConflictoOperacionError(
                    f"Línea {detalle.numero}: quedan {remanente} unidades sin devolver de "
                    f"{detalle.producto.codigo} y se intenta devolver {detalle.cantidad}."
                )
        for reintegro in devolucion.reintegros:
            disponible = self.reintegrable_centavos(venta, reintegro.medio)
            if reintegro.importe_centavos > disponible:
                raise ConflictoOperacionError(
                    f"Reintegro {reintegro.numero}: con {reintegro.medio.nombre} quedan "
                    f"{importe_a_texto(disponible)} por reintegrar."
                )
        movimientos = inventario.devolver(devolucion)
        movimientos_caja = caja.egresar_devolucion(devolucion)
        self._guardar(devolucion)
        return devolucion, movimientos, movimientos_caja, True

    def devuelto(self, detalle_venta):
        """Cantidad ya devuelta de una línea vendida, sumando devoluciones parciales."""
        return sum(
            detalle.cantidad
            for devolucion in self._devoluciones.values()
            for detalle in devolucion.detalles
            if detalle.detalle_venta is detalle_venta
        )

    def remanente(self, detalle_venta):
        return detalle_venta.cantidad - self.devuelto(detalle_venta)

    def reintegrable_centavos(self, venta, medio):
        """Lo cobrado con el medio en la venta menos lo ya reintegrado con él."""
        cobrado = sum(cobro.importe_centavos for cobro in venta.cobros if cobro.medio is medio)
        reintegrado = sum(
            reintegro.importe_centavos
            for devolucion in self.listar(venta=venta)
            for reintegro in devolucion.reintegros
            if reintegro.medio is medio
        )
        return cobrado - reintegrado

    def restaurar(self, devolucion):
        """Incorpora una devolución ya confirmada; no repite su ingreso de stock ni su egreso de caja."""
        if not isinstance(devolucion, Devolucion):
            raise TypeError("La devolución debe ser una Devolucion.")
        if devolucion.identificador != len(self._devoluciones) + 1:
            raise ValueError("Las devoluciones se restauran en orden de identificador.")
        self._guardar(devolucion)

    def _guardar(self, devolucion):
        self._devoluciones[devolucion.identificador] = devolucion
        self._por_clave[devolucion.clave_operacion] = devolucion

    def obtener(self, identificador):
        _validar_identificador(identificador)
        return self._devoluciones[identificador]

    def listar(self, venta=None, local=None):
        return tuple(
            devolucion for devolucion in self._devoluciones.values()
            if (venta is None or devolucion.venta is venta) and (local is None or devolucion.local is local)
        )
