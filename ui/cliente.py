"""Cliente HTTP de la interfaz hacia la API. La API key nunca llega al navegador."""

import os

import httpx

API_URL = os.getenv("TRUEPROFIT_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 30


class ErrorAPI(Exception):
    pass


def _cabeceras() -> dict[str, str]:
    return {"X-API-Key": os.getenv("TRUEPROFIT_API_KEY", "")}


def _respuesta(r: httpx.Response) -> dict:
    if r.status_code != 200:
        try:
            detalle = r.json().get("detail", r.text)
        except ValueError:
            detalle = r.text
        raise ErrorAPI(f"La API respondió {r.status_code}: {detalle}")
    return r.json()


def salud() -> bool:
    try:
        return httpx.get(f"{API_URL}/health", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


def simular(**datos: float) -> dict:
    r = httpx.post(f"{API_URL}/simular", json=datos, headers=_cabeceras(), timeout=TIMEOUT)
    return _respuesta(r)


def analizar(pedidos: bytes, publicidad: bytes | None, efectividad: float | None = None) -> dict:
    archivos = {"pedidos": ("pedidos.csv", pedidos, "text/csv")}
    if publicidad:
        archivos["publicidad"] = ("publicidad.csv", publicidad, "text/csv")
    datos = {"efectividad_proyectada": str(efectividad)} if efectividad is not None else {}
    r = httpx.post(
        f"{API_URL}/analizar", files=archivos, data=datos, headers=_cabeceras(), timeout=TIMEOUT
    )
    return _respuesta(r)
