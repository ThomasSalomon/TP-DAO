"""Necesidades de los locales y órdenes de reposición por destino (DN-04)."""

from .catalogo import ConflictoCatalogoError, Producto, Ubicacion, _validar_identificador
from .errores import ConflictoOperacionError
from .fechas import validar_instante


class NecesidadReposicion:
    """Pedido de un local por un producto; se consolida completo en una sola orden."""

    def __init__(self, identificador, local, producto, cantidad, instante):
        _validar_identificador(identificador)
        if not isinstance(local, Ubicacion) or local.tipo != "LOCAL":
            raise ValueError("La necesidad debe registrarla un local, no el CD.")
        if not isinstance(producto, Producto):
            raise TypeError("El producto debe ser un Producto.")
        if type(cantidad) is not int:
            raise TypeError("La cantidad debe ser un entero de unidades.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        validar_instante(instante)
        self._identificador = identificador
        self._local = local
        self._producto = producto
        self._cantidad = cantidad
        self._instante = instante
        self._orden = None

    @property
    def identificador(self):
        return self._identificador

    @property
    def local(self):
        return self._local

    @property
    def producto(self):
        return self._producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def instante(self):
        return self._instante

    @property
    def orden(self):
        return self._orden

    @property
    def estado(self):
        return "PENDIENTE" if self._orden is None else "CONSOLIDADA"

    def _consolidar(self, orden):
        # Sólo la orden que la incorpora llama a este método, después de validar todo.
        self._orden = orden


class DetalleReposicion:
    """Cantidad pedida de un producto en la orden y necesidades que la originaron."""

    def __init__(self, orden, producto, necesidades):
        self._orden = orden
        self._producto = producto
        self._necesidades = tuple(necesidades)

    @property
    def orden(self):
        return self._orden

    @property
    def producto(self):
        return self._producto

    @property
    def necesidades(self):
        return self._necesidades

    @property
    def cantidad_solicitada(self):
        return sum(necesidad.cantidad for necesidad in self._necesidades)

    @property
    def cantidad_asignada(self):
        """Unidades en bultos no anulados de esta orden."""
        return sum(
            detalle.cantidad
            for bulto in self._orden.bultos if bulto.estado != "ANULADO"
            for detalle in bulto.detalles if detalle.producto is self._producto
        )

    @property
    def cantidad_pendiente(self):
        return self.cantidad_solicitada - self.cantidad_asignada


class OrdenReposicion:
    """Consolida necesidades de un local hacia el CD; origen físico CD y destino el local."""

    def __init__(self, identificador, centro, destino, instante, necesidades):
        _validar_identificador(identificador)
        if not isinstance(centro, Ubicacion) or centro.tipo != "CD":
            raise ValueError("La orden debe abastecerse desde el Centro de Distribución.")
        if not isinstance(destino, Ubicacion) or destino.tipo != "LOCAL":
            raise ValueError("El destino de la orden debe ser un local.")
        validar_instante(instante)
        if not isinstance(necesidades, (list, tuple)):
            raise TypeError("Las necesidades deben ser una lista.")
        if not necesidades:
            raise ValueError("La orden debe consolidar al menos una necesidad.")
        por_producto = {}
        for necesidad in necesidades:
            if not isinstance(necesidad, NecesidadReposicion):
                raise TypeError("Cada necesidad debe ser una NecesidadReposicion.")
            if necesidad.local is not destino:
                raise ValueError("Una orden sólo consolida necesidades de su local destino.")
            if any(necesidad is otra for otras in por_producto.values() for otra in otras):
                raise ValueError("Una necesidad no puede repetirse en la misma orden.")
            por_producto.setdefault(necesidad.producto, []).append(necesidad)

        self._identificador = identificador
        self._centro = centro
        self._destino = destino
        self._instante = instante
        self._bultos = []
        # Composición: un detalle por producto, ordenado por identificador de producto.
        self._detalles = tuple(
            DetalleReposicion(self, producto, por_producto[producto])
            for producto in sorted(por_producto, key=lambda item: item.identificador)
        )

    @property
    def identificador(self):
        return self._identificador

    @property
    def centro(self):
        return self._centro

    @property
    def destino(self):
        return self._destino

    @property
    def instante(self):
        return self._instante

    @property
    def detalles(self):
        return self._detalles

    @property
    def bultos(self):
        return tuple(self._bultos)

    @property
    def necesidades(self):
        return tuple(necesidad for detalle in self._detalles for necesidad in detalle.necesidades)

    @property
    def estado(self):
        return "COMPLETA" if all(detalle.cantidad_pendiente == 0 for detalle in self._detalles) else "ABIERTA"

    def detalle_de(self, producto):
        for detalle in self._detalles:
            if detalle.producto is producto:
                return detalle
        return None

    def validar_asignacion(self, lineas):
        """lineas: pares (producto, cantidad) que se quieren preparar en un bulto."""
        for producto, cantidad in lineas:
            detalle = self.detalle_de(producto)
            if detalle is None:
                raise ValueError(f"El producto {producto.codigo} no figura en la orden {self._identificador}.")
            if cantidad > detalle.cantidad_pendiente:
                raise ConflictoOperacionError(
                    f"La orden {self._identificador} tiene {detalle.cantidad_pendiente} unidades pendientes "
                    f"de {producto.codigo}; no se pueden preparar {cantidad}."
                )

    def _agregar_bulto(self, bulto):
        # El registro logístico lo llama después de validar la asignación y reservar el stock.
        self._bultos.append(bulto)


class RegistroReposicion:
    """Necesidades y órdenes en orden de registro."""

    def __init__(self):
        self._necesidades = {}
        self._ordenes = {}

    def registrar_necesidad(self, local, producto, cantidad, instante):
        necesidad = NecesidadReposicion(len(self._necesidades) + 1, local, producto, cantidad, instante)
        if not local.activo or not producto.activo:
            raise ConflictoCatalogoError("El local y el producto deben estar activos para registrar una necesidad.")
        self._necesidades[necesidad.identificador] = necesidad
        return necesidad

    def consolidar(self, centro, destino, necesidades, instante):
        """Crea una orden con necesidades pendientes del destino y las marca consolidadas."""
        orden = OrdenReposicion(len(self._ordenes) + 1, centro, destino, instante, necesidades)
        if not destino.activo:
            raise ConflictoCatalogoError("El local destino está inactivo y no admite nuevas órdenes.")
        for necesidad in necesidades:
            if self._necesidades.get(necesidad.identificador) is not necesidad:
                raise ValueError("La necesidad no pertenece a este registro.")
            if necesidad.estado != "PENDIENTE":
                raise ConflictoOperacionError(
                    f"La necesidad {necesidad.identificador} ya fue consolidada en la orden {necesidad.orden.identificador}."
                )
        for necesidad in necesidades:
            necesidad._consolidar(orden)
        self._ordenes[orden.identificador] = orden
        return orden

    def restaurar_necesidad(self, necesidad):
        """Incorpora una necesidad ya confirmada, en orden de identificador y sin controlar activos."""
        if not isinstance(necesidad, NecesidadReposicion):
            raise TypeError("La necesidad debe ser una NecesidadReposicion.")
        if necesidad.identificador != len(self._necesidades) + 1:
            raise ValueError("Las necesidades se restauran en orden de identificador.")
        self._necesidades[necesidad.identificador] = necesidad

    def restaurar_orden(self, orden):
        """Incorpora una orden ya confirmada y vuelve a vincular sus necesidades restauradas."""
        if not isinstance(orden, OrdenReposicion):
            raise TypeError("La orden debe ser una OrdenReposicion.")
        if orden.identificador != len(self._ordenes) + 1:
            raise ValueError("Las órdenes se restauran en orden de identificador.")
        for necesidad in orden.necesidades:
            if self._necesidades.get(necesidad.identificador) is not necesidad or necesidad.estado != "PENDIENTE":
                raise ValueError("La orden restaurada referencia necesidades inválidas.")
        for necesidad in orden.necesidades:
            necesidad._consolidar(orden)
        self._ordenes[orden.identificador] = orden

    def obtener_necesidad(self, identificador):
        _validar_identificador(identificador)
        return self._necesidades[identificador]

    def listar_necesidades(self, local=None):
        return tuple(item for item in self._necesidades.values() if local is None or item.local is local)

    def obtener_orden(self, identificador):
        _validar_identificador(identificador)
        return self._ordenes[identificador]

    def listar_ordenes(self):
        return tuple(self._ordenes.values())
