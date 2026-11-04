# Una sola receta, dos imágenes:
#   docker build --target api -t trueprofit-api .
#   docker build --target ui  -t trueprofit-ui  .
# Cada imagen instala solo las dependencias que usa (sin pytest, ruff ni datos de desarrollo).

ARG PYTHON_VERSION=3.12

# ---------- Etapa de construcción: aquí sí está uv ----------
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./

FROM builder AS build-api
# 1) dependencias (capa cacheable)  2) el paquete propio, instalado (no editable)
RUN uv sync --frozen --no-default-groups --no-install-project
COPY src ./src
RUN uv sync --frozen --no-default-groups --no-editable

FROM builder AS build-ui
RUN uv sync --frozen --only-group ui --no-install-project

# ---------- Imágenes finales: solo Python + el entorno + el código ----------
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 app
WORKDIR /app

FROM runtime AS api
COPY --from=build-api /app/.venv /app/.venv
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"]
CMD ["uvicorn", "trueprofit.api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS ui
COPY --from=build-ui /app/.venv /app/.venv
COPY ui ./ui
USER app
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=2)"]
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
