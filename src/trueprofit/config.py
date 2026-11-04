"""Configuración leída de variables de entorno (nunca del código)."""

import os

VARIABLE_API_KEY = "TRUEPROFIT_API_KEY"


def api_key() -> str | None:
    """Clave que deben enviar los clientes en la cabecera X-API-Key.

    Se lee en cada petición para que un cambio de entorno no exija tocar el código.
    """
    valor = os.getenv(VARIABLE_API_KEY, "").strip()
    return valor or None
