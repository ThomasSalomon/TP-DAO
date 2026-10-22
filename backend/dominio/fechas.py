"""Instantes de las operaciones, en la zona horaria acordada (DN-09)."""

from datetime import datetime, timedelta, timezone

# Argentina no aplica horario de verano desde 2009: un desplazamiento fijo evita
# depender de la base de zonas horarias, que Windows no trae instalada.
ZONA_ARGENTINA = timezone(timedelta(hours=-3), "America/Buenos_Aires")


def ahora():
    """Instante actual con precisión de segundos, la misma que se guarda."""
    return datetime.now(ZONA_ARGENTINA).replace(microsecond=0)


def validar_instante(instante):
    if not isinstance(instante, datetime):
        raise TypeError("El instante debe ser un datetime.")
    if instante.utcoffset() is None:
        raise ValueError("El instante debe incluir zona horaria.")
