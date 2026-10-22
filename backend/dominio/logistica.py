"""Bultos con patrón State, remitos y su historial inmutable (DN-01, DN-02)."""

from abc import ABC, abstractmethod

from .catalogo import ConflictoCatalogoError, Producto, Ubicacion, _texto_no_vacio, _validar_identificador
from .errores import ConflictoOperacionError
from .fechas import validar_instante
from .reposicion import OrdenReposicion


class TransicionBultoError(ConflictoOperacionError):
    """El estado actual del bulto no admite la operación pedida."""


class EventoEstadoBulto:
    """Cambio de estado registrado; no tiene operaciones de modificación."""

    def __init__(self, secuencia, estado_anterior, estado_nuevo, instante, motivo):
        self._secuencia = secuencia
        self._estado_anterior = estado_anterior
        self._estado_nuevo = estado_nuevo
        self._instante = instante
        self._motivo = motivo

    @property
    def secuencia(self):
        return self._secuencia

    @property
    def estado_anterior(self):
        return self._estado_anterior

    @property
    def estado_nuevo(self):
        return self._estado_nuevo

    @property
    def instante(self):
        return self._instante

    @property
    def motivo(self):
        return self._motivo


class EstadoBulto(ABC):
    """Contrato de los estados: cada uno acepta sólo las operaciones válidas y decide la transición.

    Por defecto toda operación se rechaza; cada estado concreto redefine las que admite.
    """

    @property
    @abstractmethod
    def nombre(self):
        """Nombre estable que se guarda y se informa."""

    @property
    @abstractmethod
    def descripcion(self):
        """Texto para los mensajes al usuario."""

    def _rechazar(self, bulto, accion):
        raise TransicionBultoError(f"El bulto {bulto.codigo} está {self.descripcion} y no se puede {accion}.")

    def precintar(self, bulto, precinto, remito, instante):
        self._rechazar(bulto, "precintar")

    def despachar(self, bulto, instante, inventario):
        self._rechazar(bulto, "despachar")

    def recibir(self, bulto, ubicacion, precinto_leido, precinto_intacto, instante, inventario):
        self._rechazar(bulto, "recibir")

    def verificar(self, bulto, instante):
        self._rechazar(bulto, "verificar")

    def anular(self, bulto, instante, inventario):
        self._rechazar(bulto, "anular")


class Preparado(EstadoBulto):
    @property
    def nombre(self):
        return "PREPARADO"

    @property
    def descripcion(self):
        return "preparado"

    def precintar(self, bulto, precinto, remito, instante):
        bulto._fijar_precinto(precinto, remito)
        bulto._cambiar_estado(Precintado(), instante, f"Precinto {precinto}; remito {remito.numero}.")
        return ()

    def anular(self, bulto, instante, inventario):
        movimientos = inventario.liberar_bulto(bulto, instante)
        bulto._cambiar_estado(Anulado(), instante, "Preparación anulada; reserva liberada en el CD.")
        return movimientos


class Precintado(EstadoBulto):
    @property
    def nombre(self):
        return "PRECINTADO"

    @property
    def descripcion(self):
        return "precintado"

    def despachar(self, bulto, instante, inventario):
        movimientos = inventario.despachar_bulto(bulto, instante)
        bulto._cambiar_estado(EnTransito(), instante, f"Despachado desde {bulto.origen.codigo}.")
        return movimientos


class EnTransito(EstadoBulto):
    @property
    def nombre(self):
        return "EN_TRANSITO"

    @property
    def descripcion(self):
        return "en tránsito"

    def recibir(self, bulto, ubicacion, precinto_leido, precinto_intacto, instante, inventario):
        if ubicacion is not bulto.destino:
            raise ConflictoOperacionError(
                f"El bulto {bulto.codigo} sólo se recibe en su local destino {bulto.destino.codigo}."
            )
        leido = _texto_no_vacio(precinto_leido, "precinto leído")
        if type(precinto_intacto) is not bool:
            raise TypeError("Indicá si el precinto está intacto con verdadero o falso.")

        recepcion = f"Recibido en {ubicacion.codigo}; precinto leído {leido}."
        if not precinto_intacto:
            motivo = "Precinto roto."
        elif leido.casefold() != bulto.precinto.casefold():
            motivo = f"El precinto leído {leido} no coincide con el registrado {bulto.precinto}."
        else:
            movimientos = inventario.recibir_bulto(bulto, instante)
            bulto._cambiar_estado(Recibido(), instante, recepcion)
            return movimientos

        # Rechazo logístico en la misma recepción: nunca hay una ventana con stock habilitado.
        movimientos = inventario.rechazar_bulto(bulto, instante)
        bulto._cambiar_estado(Recibido(), instante, recepcion)
        bulto._cambiar_estado(Rechazado(), instante, motivo)
        bulto.remito._rechazar(instante)
        return movimientos


class Recibido(EstadoBulto):
    @property
    def nombre(self):
        return "RECIBIDO"

    @property
    def descripcion(self):
        return "recibido"

    def verificar(self, bulto, instante):
        bulto._cambiar_estado(Verificado(), instante, "Contenedor verificado; falta verificar el remito.")
        return ()


class Verificado(EstadoBulto):
    @property
    def nombre(self):
        return "VERIFICADO"

    @property
    def descripcion(self):
        return "verificado"


class Rechazado(EstadoBulto):
    @property
    def nombre(self):
        return "RECHAZADO"

    @property
    def descripcion(self):
        return "rechazado"


class Anulado(EstadoBulto):
    @property
    def nombre(self):
        return "ANULADO"

    @property
    def descripcion(self):
        return "anulado"


ESTADOS_BULTO = {estado().nombre: estado for estado in (
    Preparado, Precintado, EnTransito, Recibido, Verificado, Rechazado, Anulado,
)}


class DetalleBulto:
    """Contenido del bulto; conserva el costo de referencia vigente al prepararlo."""

    def __init__(self, bulto, producto, cantidad, costo_referencia_centavos):
        if not isinstance(producto, Producto):
            raise TypeError("El producto debe ser un Producto.")
        if type(cantidad) is not int:
            raise TypeError("La cantidad debe ser un entero de unidades.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        if costo_referencia_centavos is not None and (
            type(costo_referencia_centavos) is not int or costo_referencia_centavos <= 0
        ):
            raise ValueError("El costo de referencia debe ser un entero positivo de centavos o faltar.")
        self._bulto = bulto
        self._producto = producto
        self._cantidad = cantidad
        self._costo_referencia_centavos = costo_referencia_centavos

    @property
    def bulto(self):
        return self._bulto

    @property
    def producto(self):
        return self._producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def costo_referencia_centavos(self):
        """None si el producto no tenía compras al preparar: el costo falta, no es cero."""
        return self._costo_referencia_centavos


class Bulto:
    """Contexto del patrón State: delega cada operación en su estado actual."""

    def __init__(self, identificador, orden, instante, lineas):
        """lineas: secuencia de (producto, cantidad, costo de referencia en centavos o None)."""
        _validar_identificador(identificador)
        if not isinstance(orden, OrdenReposicion):
            raise TypeError("La orden debe ser una OrdenReposicion.")
        validar_instante(instante)
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        if not lineas:
            raise ValueError("El bulto debe contener al menos un producto.")
        self._identificador = identificador
        self._orden = orden
        self._precinto = None
        self._remito = None
        detalles = []
        for numero, (producto, cantidad, costo) in enumerate(lineas, start=1):
            if any(detalle.producto is producto for detalle in detalles):
                raise ValueError(f"Línea {numero}: un producto no puede repetirse dentro del mismo bulto.")
            try:
                detalles.append(DetalleBulto(self, producto, cantidad, costo))
            except (TypeError, ValueError) as error:
                raise type(error)(f"Línea {numero}: {error}") from None
        self._detalles = tuple(detalles)
        self._estado = Preparado()
        self._eventos = [EventoEstadoBulto(1, None, "PREPARADO", instante, "Contenido preparado y reservado en el CD.")]

    @property
    def identificador(self):
        return self._identificador

    @property
    def codigo(self):
        return f"B-{self._identificador:06d}"

    @property
    def orden(self):
        return self._orden

    @property
    def origen(self):
        return self._orden.centro

    @property
    def destino(self):
        return self._orden.destino

    @property
    def detalles(self):
        return self._detalles

    @property
    def precinto(self):
        return self._precinto

    @property
    def remito(self):
        return self._remito

    @property
    def estado(self):
        return self._estado.nombre

    @property
    def eventos(self):
        return tuple(self._eventos)

    def precintar(self, precinto, remito, instante):
        return self._estado.precintar(self, precinto, remito, instante)

    def despachar(self, instante, inventario):
        return self._estado.despachar(self, instante, inventario)

    def recibir(self, ubicacion, precinto_leido, precinto_intacto, instante, inventario):
        return self._estado.recibir(self, ubicacion, precinto_leido, precinto_intacto, instante, inventario)

    def verificar(self, instante):
        return self._estado.verificar(self, instante)

    def anular(self, instante, inventario):
        return self._estado.anular(self, instante, inventario)

    def _restaurar_historia(self, eventos, precinto):
        """eventos: (estado anterior, estado nuevo, instante, motivo) ya confirmados, en orden.

        Exige una cadena continua desde PREPARADO; no repite efectos de inventario.
        """
        if not eventos or eventos[0][0] is not None or eventos[0][1] != "PREPARADO":
            raise ValueError("El historial debe comenzar en PREPARADO.")
        historial = []
        for secuencia, (anterior, nuevo, instante, motivo) in enumerate(eventos, start=1):
            if nuevo not in ESTADOS_BULTO or (historial and anterior != historial[-1].estado_nuevo):
                raise ValueError(f"El historial del bulto {self.codigo} no es una secuencia de estados válida.")
            validar_instante(instante)
            historial.append(EventoEstadoBulto(secuencia, anterior, nuevo, instante, motivo))
        self._eventos = historial
        self._estado = ESTADOS_BULTO[historial[-1].estado_nuevo]()
        self._precinto = precinto

    def _fijar_precinto(self, precinto, remito):
        self._precinto = precinto
        self._remito = remito

    def _cambiar_estado(self, estado, instante, motivo):
        """Único punto que cambia el estado; siempre agrega un evento al historial."""
        validar_instante(instante)
        self._eventos.append(
            EventoEstadoBulto(len(self._eventos) + 1, self._estado.nombre, estado.nombre, instante, motivo)
        )
        self._estado = estado


class Remito:
    """Documento de despacho de un bulto; su verificación habilita el stock del local."""

    def __init__(self, identificador, bulto, instante):
        _validar_identificador(identificador)
        if not isinstance(bulto, Bulto):
            raise TypeError("El remito documenta un Bulto.")
        validar_instante(instante)
        self._identificador = identificador
        self._bulto = bulto
        self._instante = instante
        self._estado = "EMITIDO"
        self._instante_cierre = None

    @property
    def identificador(self):
        return self._identificador

    @property
    def numero(self):
        return f"R-{self._identificador:06d}"

    @property
    def bulto(self):
        return self._bulto

    @property
    def origen(self):
        return self._bulto.origen

    @property
    def destino(self):
        return self._bulto.destino

    @property
    def instante(self):
        return self._instante

    @property
    def estado(self):
        return self._estado

    @property
    def instante_cierre(self):
        """Instante de la verificación o del rechazo; None mientras está emitido."""
        return self._instante_cierre

    def verificar(self, instante, inventario):
        """Segunda verificación: recién aquí el contenido queda disponible en el local."""
        validar_instante(instante)
        if self._estado != "EMITIDO":
            raise ConflictoOperacionError(f"El remito {self.numero} ya está {self._estado.lower()}.")
        if self._bulto.estado != "VERIFICADO":
            raise ConflictoOperacionError(
                f"Verificá el bulto {self._bulto.codigo} antes que su remito {self.numero}."
            )
        movimientos = inventario.habilitar_bulto(self._bulto, instante)
        self._estado = "VERIFICADO"
        self._instante_cierre = instante
        return movimientos

    def _restaurar(self, estado, instante_cierre):
        if estado not in ("EMITIDO", "VERIFICADO", "RECHAZADO"):
            raise ValueError("El estado del remito no es válido.")
        if (estado == "EMITIDO") != (instante_cierre is None):
            raise ValueError("Sólo un remito cerrado tiene instante de cierre.")
        self._estado = estado
        self._instante_cierre = instante_cierre

    def _rechazar(self, instante):
        # Sólo lo llama el rechazo logístico de su bulto.
        self._estado = "RECHAZADO"
        self._instante_cierre = instante


class RegistroLogistica:
    """Bultos y remitos en orden de registro; asigna identificadores y controla precintos únicos."""

    def __init__(self):
        self._bultos = {}
        self._remitos = {}

    def preparar(self, orden, lineas, instante, inventario, compras):
        """Arma un bulto de la orden, copia el costo de referencia y reserva el stock en el CD.

        lineas: pares (producto, cantidad). Valida todo antes de reservar.
        """
        if not isinstance(lineas, (list, tuple)):
            raise TypeError("Las líneas deben ser una lista.")
        bulto = Bulto(
            len(self._bultos) + 1, orden, instante,
            [(producto, cantidad, compras.costo_referencia(producto)) for producto, cantidad in lineas],
        )
        if not orden.destino.activo:
            raise ConflictoCatalogoError("El local destino está inactivo y no admite nuevos bultos.")
        if any(not detalle.producto.activo for detalle in bulto.detalles):
            raise ConflictoCatalogoError("Los productos inactivos no admiten nuevos bultos.")
        orden.validar_asignacion([(detalle.producto, detalle.cantidad) for detalle in bulto.detalles])
        movimientos = inventario.reservar_bulto(bulto, instante)
        orden._agregar_bulto(bulto)
        self._bultos[bulto.identificador] = bulto
        return bulto, movimientos

    def precintar(self, bulto, precinto, instante):
        """Registra el precinto físico y emite el remito del bulto."""
        precinto = _texto_no_vacio(precinto, "precinto")
        if any(
            otro.precinto is not None and otro.precinto.casefold() == precinto.casefold()
            for otro in self._bultos.values()
        ):
            raise ConflictoOperacionError(f"El precinto {precinto} ya fue usado en otro bulto.")
        remito = Remito(len(self._remitos) + 1, bulto, instante)
        bulto.precintar(precinto, remito, instante)
        self._remitos[remito.identificador] = remito
        return remito

    def restaurar_bulto(self, identificador, orden, lineas, eventos, precinto):
        """Reconstruye un bulto confirmado con su historial; no controla activos ni reserva stock."""
        if identificador != len(self._bultos) + 1:
            raise ValueError("Los bultos se restauran en orden de identificador.")
        if not eventos:
            raise ValueError("El historial debe comenzar en PREPARADO.")
        bulto = Bulto(identificador, orden, eventos[0][2], lineas)
        bulto._restaurar_historia(eventos, precinto)
        orden._agregar_bulto(bulto)
        self._bultos[identificador] = bulto
        return bulto

    def restaurar_remito(self, identificador, bulto, instante, estado, instante_cierre):
        if identificador != len(self._remitos) + 1:
            raise ValueError("Los remitos se restauran en orden de identificador.")
        remito = Remito(identificador, bulto, instante)
        remito._restaurar(estado, instante_cierre)
        bulto._fijar_precinto(bulto.precinto, remito)
        self._remitos[identificador] = remito
        return remito

    def obtener_bulto(self, identificador):
        _validar_identificador(identificador)
        return self._bultos[identificador]

    def listar_bultos(self):
        return tuple(self._bultos.values())

    def obtener_remito(self, identificador):
        _validar_identificador(identificador)
        return self._remitos[identificador]

    def listar_remitos(self):
        return tuple(self._remitos.values())
