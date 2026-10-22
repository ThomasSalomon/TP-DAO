"""Errores de dominio compartidos por las operaciones de stock y logística."""


class ConflictoOperacionError(Exception):
    """La operación no corresponde al estado actual de un documento o del stock."""
