"""API HTTP de TrueProfit (FastAPI).

Ejecutar en local:  uv run --env-file .env uvicorn trueprofit.api:app --reload
Documentación interactiva:  http://localhost:8000/docs
"""

import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from trueprofit import __version__
from trueprofit.config import api_key
from trueprofit.lectura import ErrorDeFormato, leer_pedidos, leer_publicidad
from trueprofit.metricas import calcular_metricas, metricas_por_producto
from trueprofit.simulador import simular

app = FastAPI(
    title="TrueProfit API",
    version=__version__,
    description="Utilidad real de una tienda de dropshipping: ventas, fletes, devoluciones, pauta.",
)

TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB por archivo


def verificar_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    esperada = api_key()
    if esperada is None:
        raise HTTPException(503, "El servidor no tiene configurada TRUEPROFIT_API_KEY")
    if x_api_key is None or not secrets.compare_digest(x_api_key, esperada):
        raise HTTPException(401, "API key inválida o ausente")


Protegido = Annotated[None, Depends(verificar_api_key)]


class EntradaSimulacion(BaseModel):
    precio_venta: float = Field(gt=0, examples=[89_900])
    costo_producto: float = Field(ge=0, examples=[32_000])
    flete: float = Field(ge=0, examples=[15_000])
    tasa_entrega: float = Field(ge=0, le=1, examples=[0.75])
    cpa: float = Field(ge=0, examples=[14_000])


@app.get("/health", tags=["sistema"])
def health() -> dict:
    """Verificación de salud: no requiere API key (la usan Docker y el monitoreo)."""
    return {"status": "ok", "version": __version__}


@app.post("/simular", tags=["rentabilidad"])
def endpoint_simular(datos: EntradaSimulacion, _: Protegido) -> dict:
    """Utilidad esperada por pedido de un producto, CPA y tasa de entrega de equilibrio."""
    return simular(**datos.model_dump()).como_dict()


async def _leer(archivo: UploadFile) -> bytes:
    contenido = await archivo.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, f"'{archivo.filename}' supera 5 MB")
    return contenido


@app.post("/analizar", tags=["rentabilidad"])
async def endpoint_analizar(
    _: Protegido,
    pedidos: Annotated[UploadFile, File(description="CSV de líneas de pedido (formato Dropi)")],
    publicidad: Annotated[
        UploadFile | None, File(description="CSV opcional con columnas producto,gasto")
    ] = None,
    efectividad_proyectada: Annotated[float | None, Form(ge=0, le=1)] = None,
) -> dict:
    """Resumen de la tienda y detalle por producto a partir de los CSV cargados."""
    try:
        lineas = leer_pedidos(await _leer(pedidos))
        gasto = leer_publicidad(await _leer(publicidad)) if publicidad else {}
    except ErrorDeFormato as e:
        raise HTTPException(422, str(e)) from e

    resumen = calcular_metricas(lineas, sum(gasto.values()), efectividad_proyectada)
    productos = metricas_por_producto(lineas, gasto, efectividad_proyectada)
    return {
        "resumen": resumen.como_dict(),
        "productos": {nombre: m.como_dict() for nombre, m in productos.items()},
    }
