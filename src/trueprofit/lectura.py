"""Lectura y validación de los CSV de entrada (pedidos y gasto publicitario)."""

import csv
import io
from collections import defaultdict

from trueprofit.metricas import Linea

COLUMNAS_PEDIDOS = (
    "id_orden",
    "estatus",
    "producto",
    "cantidad",
    "total_orden",
    "precio_flete",
    "costo_proveedor",
)
COLUMNAS_ADS = ("producto", "gasto")


class ErrorDeFormato(ValueError):
    """El archivo no tiene la estructura esperada."""


def _decodificar(contenido: bytes | str) -> str:
    if isinstance(contenido, str):
        return contenido
    try:
        return contenido.decode("utf-8-sig")  # tolera el BOM que agrega Excel
    except UnicodeDecodeError:
        return contenido.decode("latin-1")


def _lector(contenido: bytes | str, requeridas: tuple[str, ...]) -> csv.DictReader:
    texto = _decodificar(contenido)
    muestra = texto[:2048]
    delimitador = ";" if muestra.count(";") > muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    columnas = {c.strip().lower() for c in (lector.fieldnames or [])}
    faltantes = [c for c in requeridas if c not in columnas]
    if faltantes:
        raise ErrorDeFormato(f"Faltan columnas: {', '.join(faltantes)}")
    return lector


def _numero(valor: str, columna: str, fila: int) -> float:
    try:
        return float(valor.strip().replace("$", "").replace(" ", ""))
    except (ValueError, AttributeError):
        raise ErrorDeFormato(f"Fila {fila}: '{columna}' no es un número ({valor!r})") from None


def leer_pedidos(contenido: bytes | str) -> list[Linea]:
    """Convierte el CSV de pedidos en líneas validadas."""
    lineas = []
    for i, fila in enumerate(_lector(contenido, COLUMNAS_PEDIDOS), start=2):
        fila = {k.strip().lower(): (v or "").strip() for k, v in fila.items() if k}
        if not fila["id_orden"]:
            raise ErrorDeFormato(f"Fila {i}: 'id_orden' está vacío")
        lineas.append(
            Linea(
                id_orden=fila["id_orden"],
                estatus=fila["estatus"],
                producto=fila["producto"] or "SIN PRODUCTO",
                cantidad=int(_numero(fila["cantidad"], "cantidad", i)),
                total_orden=_numero(fila["total_orden"], "total_orden", i),
                precio_flete=_numero(fila["precio_flete"], "precio_flete", i),
                costo_proveedor=_numero(fila["costo_proveedor"], "costo_proveedor", i),
            )
        )
    if not lineas:
        raise ErrorDeFormato("El archivo de pedidos no tiene filas")
    return lineas


def leer_publicidad(contenido: bytes | str) -> dict[str, float]:
    """Suma el gasto publicitario por producto (puede haber varias filas por producto)."""
    gasto: dict[str, float] = defaultdict(float)
    for i, fila in enumerate(_lector(contenido, COLUMNAS_ADS), start=2):
        fila = {k.strip().lower(): (v or "").strip() for k, v in fila.items() if k}
        valor = _numero(fila["gasto"], "gasto", i)
        if valor < 0:
            raise ErrorDeFormato(f"Fila {i}: el gasto no puede ser negativo")
        gasto[fila["producto"]] += valor
    return dict(gasto)
