"""Reportes de gestión R-01 a R-04 (sección P): consultan operaciones confirmadas y no modifican datos.

Importes en centavos de ARS. Las magnitudes netas pueden ser negativas si lo devuelto en un período supera lo vendido.
"""

from abc import ABC, abstractmethod
from datetime import date

from .caja import Caja
from .catalogo import Catalogo, Categoria, Producto, Ubicacion
from .devoluciones import RegistroDevoluciones
from .fechas import ZONA_ARGENTINA
from .inventario import CONDICIONES, Inventario
from .logistica import RegistroLogistica
from .ventas import RegistroVentas


def _fecha(instante):
    return instante.astimezone(ZONA_ARGENTINA).date()


def _validar_tipo(valor, clase, mensaje):
    if not isinstance(valor, clase):
        raise TypeError(mensaje)


def _validar_local(local):
    """None significa todos los locales; el CD no vende ni recibe bultos."""
    if local is not None and (not isinstance(local, Ubicacion) or local.tipo != "LOCAL"):
        raise ValueError("El filtro de ubicación debe ser un local, no el CD.")


def _sumar_costos(pares):
    """Suma cantidad × costo de los pares; None si falta algún costo, que no se toma como cero."""
    if any(costo is None for _, costo in pares):
        return None
    return sum(cantidad * costo for cantidad, costo in pares)


class Periodo:
    """Intervalo de fechas con inicio incluido y fin excluido (DN-09)."""

    def __init__(self, desde, hasta):
        # datetime también es date: se exige la fecha sin hora.
        if type(desde) is not date or type(hasta) is not date:
            raise TypeError("Las fechas del período deben ser fechas sin hora.")
        if desde >= hasta:
            raise ValueError("La fecha de inicio debe ser anterior a la de fin.")
        self._desde = desde
        self._hasta = hasta

    @property
    def desde(self):
        return self._desde

    @property
    def hasta(self):
        """Primer día que ya no pertenece al período."""
        return self._hasta

    def contiene(self, instante):
        return self._desde <= _fecha(instante) < self._hasta


# R-01: ventas, cobros e ingresos netos, con patrón Strategy.

class EstrategiaAgrupacion(ABC):
    """Contrato de las agrupaciones de R-01: todas reciben los mismos movimientos de caja."""

    @property
    @abstractmethod
    def nombre(self):
        """Nombre estable con el que se elige la estrategia."""

    @abstractmethod
    def clave(self, movimiento):
        """Par (orden, etiqueta) del grupo al que pertenece el movimiento."""


class PorDia(EstrategiaAgrupacion):
    @property
    def nombre(self):
        return "dia"

    def clave(self, movimiento):
        fecha = _fecha(movimiento.instante)
        return fecha, fecha.strftime("%d/%m/%Y")


class PorLocal(EstrategiaAgrupacion):
    @property
    def nombre(self):
        return "local"

    def clave(self, movimiento):
        return movimiento.local.identificador, f"{movimiento.local.codigo} — {movimiento.local.nombre}"


class PorMedioPago(EstrategiaAgrupacion):
    @property
    def nombre(self):
        return "medio"

    def clave(self, movimiento):
        return movimiento.medio.identificador, movimiento.medio.nombre


ESTRATEGIAS_AGRUPACION = {estrategia().nombre: estrategia for estrategia in (PorDia, PorLocal, PorMedioPago)}


class GrupoCaja:
    """Cobros, reintegros e ingreso neto de un grupo de R-01."""

    def __init__(self, etiqueta):
        self.etiqueta = etiqueta
        self.cobros_centavos = 0
        self.reintegros_centavos = 0

    @property
    def ingreso_neto_centavos(self):
        return self.cobros_centavos - self.reintegros_centavos

    def _sumar(self, movimiento):
        if movimiento.tipo == "INGRESO":
            self.cobros_centavos += movimiento.importe_centavos
        else:
            self.reintegros_centavos += movimiento.importe_centavos


class ResultadoVentas:
    """R-01: totales de documentos del período y caja agrupada por la estrategia elegida."""

    def __init__(self, periodo, local, agrupacion, ventas, devoluciones, grupos):
        self.periodo = periodo
        self.local = local
        self.agrupacion = agrupacion
        self.cantidad_ventas = len(ventas)
        self.ventas_centavos = sum(venta.total_centavos for venta in ventas)
        self.cantidad_devoluciones = len(devoluciones)
        self.devoluciones_centavos = sum(devolucion.total_centavos for devolucion in devoluciones)
        self.grupos = tuple(grupos)

    @property
    def venta_neta_centavos(self):
        return self.ventas_centavos - self.devoluciones_centavos

    @property
    def cobros_centavos(self):
        return sum(grupo.cobros_centavos for grupo in self.grupos)

    @property
    def reintegros_centavos(self):
        return sum(grupo.reintegros_centavos for grupo in self.grupos)

    @property
    def ingreso_neto_centavos(self):
        return self.cobros_centavos - self.reintegros_centavos


class ReporteVentas:
    """Contexto de Strategy: filtra las operaciones y delega en la estrategia la agrupación de la caja."""

    def __init__(self, estrategia):
        self._validar_estrategia(estrategia)
        self._estrategia = estrategia

    @staticmethod
    def _validar_estrategia(estrategia):
        _validar_tipo(estrategia, EstrategiaAgrupacion, "La agrupación debe ser una EstrategiaAgrupacion.")

    @property
    def estrategia(self):
        return self._estrategia

    def cambiar_estrategia(self, estrategia):
        self._validar_estrategia(estrategia)
        self._estrategia = estrategia

    def generar(self, periodo, ventas, devoluciones, caja, local=None):
        _validar_tipo(periodo, Periodo, "El período debe ser un Periodo.")
        _validar_tipo(ventas, RegistroVentas, "Las ventas deben ser un RegistroVentas.")
        _validar_tipo(devoluciones, RegistroDevoluciones, "Las devoluciones deben ser un RegistroDevoluciones.")
        _validar_tipo(caja, Caja, "La caja debe ser una Caja.")
        _validar_local(local)
        grupos = {}
        for movimiento in caja.movimientos(local):
            if periodo.contiene(movimiento.instante):
                orden, etiqueta = self._estrategia.clave(movimiento)
                if orden not in grupos:
                    grupos[orden] = GrupoCaja(etiqueta)
                grupos[orden]._sumar(movimiento)
        return ResultadoVentas(
            periodo, local, self._estrategia.nombre,
            [venta for venta in ventas.listar(local) if periodo.contiene(venta.instante)],
            [devolucion for devolucion in devoluciones.listar(local=local) if periodo.contiene(devolucion.instante)],
            [grupos[orden] for orden in sorted(grupos)],
        )


# R-02: productos más vendidos y margen estimado.

class FilaProducto:
    """Unidades, importes y costos netos de un producto en el período, a valores históricos."""

    def __init__(self, producto):
        self.producto = producto
        self.unidades_vendidas = 0
        self.unidades_devueltas = 0
        self.importe_vendido_centavos = 0
        self.importe_devuelto_centavos = 0
        self._costos = []

    def _vender(self, detalle):
        self.unidades_vendidas += detalle.cantidad
        self.importe_vendido_centavos += detalle.subtotal_centavos
        self._costos.append((detalle.cantidad, detalle.costo_referencia_centavos))

    def _devolver(self, detalle):
        # La devolución revierte el costo de la línea vendida original.
        self.unidades_devueltas += detalle.cantidad
        self.importe_devuelto_centavos += detalle.importe_reintegro_centavos
        self._costos.append((-detalle.cantidad, detalle.detalle_venta.costo_referencia_centavos))

    @property
    def unidades_netas(self):
        return self.unidades_vendidas - self.unidades_devueltas

    @property
    def importe_neto_centavos(self):
        return self.importe_vendido_centavos - self.importe_devuelto_centavos

    @property
    def costo_neto_centavos(self):
        """None si alguna línea no tenía costo de referencia."""
        return _sumar_costos(self._costos)

    @property
    def margen_centavos(self):
        costo = self.costo_neto_centavos
        return None if costo is None else self.importe_neto_centavos - costo


class ResultadoProductos:
    """R-02: ranking por unidades netas descendentes y, ante empate, por identificador de producto."""

    def __init__(self, periodo, local, filas):
        self.periodo = periodo
        self.local = local
        self.filas = tuple(sorted(filas, key=lambda fila: (-fila.unidades_netas, fila.producto.identificador)))

    @property
    def unidades_netas(self):
        return sum(fila.unidades_netas for fila in self.filas)

    @property
    def importe_neto_centavos(self):
        return sum(fila.importe_neto_centavos for fila in self.filas)

    @property
    def productos_sin_costo(self):
        return tuple(fila.producto for fila in self.filas if fila.costo_neto_centavos is None)

    @property
    def margen_centavos(self):
        """Margen estimado del período; None si a algún producto le falta el costo."""
        if self.productos_sin_costo:
            return None
        return sum(fila.margen_centavos for fila in self.filas)


def productos_mas_vendidos(periodo, ventas, devoluciones, local=None):
    _validar_tipo(periodo, Periodo, "El período debe ser un Periodo.")
    _validar_tipo(ventas, RegistroVentas, "Las ventas deben ser un RegistroVentas.")
    _validar_tipo(devoluciones, RegistroDevoluciones, "Las devoluciones deben ser un RegistroDevoluciones.")
    _validar_local(local)
    filas = {}

    def fila_de(producto):
        if producto not in filas:
            filas[producto] = FilaProducto(producto)
        return filas[producto]

    for venta in ventas.listar(local):
        if periodo.contiene(venta.instante):
            for detalle in venta.detalles:
                fila_de(detalle.producto)._vender(detalle)
    for devolucion in devoluciones.listar(local=local):
        if periodo.contiene(devolucion.instante):
            for detalle in devolucion.detalles:
                fila_de(detalle.producto)._devolver(detalle)
    return ResultadoProductos(periodo, local, filas.values())


# R-03: existencias, mínimos y faltantes.

class FilaExistencia:
    """Saldos por condición de un producto en la ubicación y su comparación con el mínimo (DN-06)."""

    def __init__(self, producto, saldos, minimo):
        self.producto = producto
        self.saldos = saldos
        self.minimo = minimo

    @property
    def disponible(self):
        return self.saldos["DISPONIBLE"]

    @property
    def deficit(self):
        """Unidades que faltan para llegar al mínimo; None sin mínimo configurado."""
        return None if self.minimo is None else max(self.minimo - self.disponible, 0)

    @property
    def en_minimo(self):
        return self.minimo is not None and self.disponible <= self.minimo


class ResultadoExistencias:
    def __init__(self, ubicacion, categoria, filas):
        self.ubicacion = ubicacion
        self.categoria = categoria
        self.filas = tuple(filas)

    @property
    def productos_en_minimo(self):
        return sum(1 for fila in self.filas if fila.en_minimo)

    @property
    def deficit_total(self):
        return sum(fila.deficit for fila in self.filas if fila.deficit is not None)

    def total(self, condicion):
        return sum(fila.saldos[condicion] for fila in self.filas)


def existencias_y_minimos(ubicacion, catalogo, inventario, categoria=None, solo_en_minimo=False):
    """Incluye productos con saldo en la ubicación o con mínimo configurado, aunque nunca hayan tenido stock."""
    _validar_tipo(ubicacion, Ubicacion, "La ubicación debe ser una Ubicacion.")
    _validar_tipo(catalogo, Catalogo, "El catálogo debe ser un Catalogo.")
    _validar_tipo(inventario, Inventario, "El inventario debe ser un Inventario.")
    if categoria is not None:
        _validar_tipo(categoria, Categoria, "La categoría debe ser una Categoria.")
    if type(solo_en_minimo) is not bool:
        raise TypeError("El filtro de productos en mínimo debe ser verdadero o falso.")
    minimos = dict(catalogo.listar_minimos(ubicacion.identificador)) if ubicacion.tipo == "LOCAL" else {}
    productos = set(minimos) | {producto for producto, _, _ in inventario.saldos(ubicacion)}
    filas = []
    for producto in sorted(productos, key=lambda item: item.identificador):
        if categoria is None or producto.categoria is categoria:
            saldos = {condicion: inventario.cantidad(ubicacion, producto, condicion) for condicion in CONDICIONES}
            fila = FilaExistencia(producto, saldos, minimos.get(producto))
            if not solo_en_minimo or fila.en_minimo:
                filas.append(fila)
    return ResultadoExistencias(ubicacion, categoria, filas)


# R-04: rechazos logísticos.

class BultoRechazado:
    """Rechazo de un bulto; con filtro de producto sólo cuenta sus líneas."""

    def __init__(self, bulto, evento, detalles):
        self.bulto = bulto
        self.instante = evento.instante
        self.motivo = evento.motivo
        self.detalles = tuple(detalles)

    @property
    def unidades(self):
        return sum(detalle.cantidad for detalle in self.detalles)

    @property
    def valor_bloqueado_centavos(self):
        """Costo de referencia guardado al preparar; no es una merma. None si falta algún costo."""
        return _sumar_costos([(detalle.cantidad, detalle.costo_referencia_centavos) for detalle in self.detalles])


def _totales_rechazos(rechazos):
    unidades = sum(rechazo.unidades for rechazo in rechazos)
    valores = [rechazo.valor_bloqueado_centavos for rechazo in rechazos]
    return unidades, None if None in valores else sum(valores)


class RechazosLocal:
    """Bultos recibidos y rechazados en un local destino durante el período."""

    def __init__(self, destino, bultos_recibidos, rechazos):
        self.destino = destino
        self.bultos_recibidos = bultos_recibidos
        self.rechazos = tuple(rechazos)
        self.unidades, self.valor_bloqueado_centavos = _totales_rechazos(self.rechazos)

    @property
    def bultos_rechazados(self):
        return len(self.rechazos)


class ResultadoRechazos:
    def __init__(self, periodo, local, producto, rechazos, locales):
        self.periodo = periodo
        self.local = local
        self.producto = producto
        self.rechazos = tuple(rechazos)
        self.locales = tuple(locales)
        self.unidades, self.valor_bloqueado_centavos = _totales_rechazos(self.rechazos)

    @property
    def bultos_recibidos(self):
        return sum(item.bultos_recibidos for item in self.locales)

    @property
    def bultos_rechazados(self):
        return len(self.rechazos)


def _evento(bulto, estado, periodo):
    """Evento del bulto que lo llevó al estado dentro del período, o None."""
    for evento in bulto.eventos:
        if evento.estado_nuevo == estado and periodo.contiene(evento.instante):
            return evento
    return None


def rechazos_logisticos(periodo, logistica, local=None, producto=None):
    _validar_tipo(periodo, Periodo, "El período debe ser un Periodo.")
    _validar_tipo(logistica, RegistroLogistica, "La logística debe ser un RegistroLogistica.")
    _validar_local(local)
    if producto is not None:
        _validar_tipo(producto, Producto, "El producto debe ser un Producto.")
    recibidos = {}
    rechazos = []
    for bulto in logistica.listar_bultos():
        detalles = [detalle for detalle in bulto.detalles if producto is None or detalle.producto is producto]
        if (local is not None and bulto.destino is not local) or not detalles:
            continue
        if _evento(bulto, "RECIBIDO", periodo) is not None:
            recibidos[bulto.destino] = recibidos.get(bulto.destino, 0) + 1
        evento = _evento(bulto, "RECHAZADO", periodo)
        if evento is not None:
            rechazos.append(BultoRechazado(bulto, evento, detalles))
    rechazos.sort(key=lambda rechazo: (rechazo.instante, rechazo.bulto.identificador))
    # El rechazo ocurre en la misma recepción, así que todo local con rechazos tiene recibidos.
    locales = [
        RechazosLocal(destino, cantidad, [rechazo for rechazo in rechazos if rechazo.bulto.destino is destino])
        for destino, cantidad in sorted(recibidos.items(), key=lambda par: par[0].identificador)
    ]
    return ResultadoRechazos(periodo, local, producto, rechazos, locales)
