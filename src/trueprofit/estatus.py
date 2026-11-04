"""Clasificación de los estados (estatus) de una orden de Dropi en grupos de negocio."""

import unicodedata
from enum import StrEnum


class Grupo(StrEnum):
    ENTREGADO = "entregado"
    DEVOLUCION = "devolucion"
    ANULADO = "anulado"  # cancelado, rechazado o guía anulada
    TRANSITO = "transito"  # todo lo demás: aún sin desenlace


def normalizar(estatus: str) -> str:
    """Mayúsculas, sin tildes y sin espacios sobrantes: 'Devolución ' -> 'DEVOLUCION'."""
    sin_tildes = unicodedata.normalize("NFKD", estatus).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.upper().split())


def clasificar(estatus: str) -> Grupo:
    """Asigna el grupo de negocio de un estatus.

    El orden importa: un estatus como 'DEVOLUCION RECHAZADA' es una devolución,
    no una cancelación, por eso la devolución se evalúa antes que lo anulado.
    """
    e = normalizar(estatus)
    if e == "ENTREGADO":
        return Grupo.ENTREGADO
    if "DEVOLUC" in e or "DEVUELT" in e:
        return Grupo.DEVOLUCION
    if any(clave in e for clave in ("CANCEL", "RECHAZ", "ANULAD")):
        return Grupo.ANULADO
    return Grupo.TRANSITO
