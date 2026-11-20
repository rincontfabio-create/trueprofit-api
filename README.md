# TrueProfit API 📦

¿Cuánto te deja **de verdad** tu tienda de dropshipping?

TrueProfit calcula la utilidad real de una tienda que vende contra entrega con Dropi.
Descuenta los fletes, las devoluciones y la pauta. Es una versión pequeña y abierta de
la lógica de **TrueProfitDrop**, un SaaS que desarrollé, empacada para la Actividad 4
de *Técnicas avanzadas de IA* (Maestría en Ciencia de Datos, UPB).

**Usuario:** el dueño de una tienda de dropshipping en Colombia. Ve cuánto vende, pero no
sabe cuánto gana después de que un 15–30 % de los pedidos se devuelven y él ya pagó el
flete y la publicidad.

## Qué hace

| Función | Dónde | Pregunta que responde |
|---|---|---|
| **Simular un producto** | `POST /simular` · pestaña 🧮 | Con este precio, costo, flete, CPA y tasa de entrega, ¿gano o pierdo por pedido? ¿Cuál es el CPA máximo y la tasa de entrega mínima? |
| **Analizar pedidos** | `POST /analizar` · pestaña 📊 | Con mi CSV de pedidos de Dropi y mi gasto en pauta: ¿cuál es mi utilidad final, mi tasa de entrega y qué productos pierden plata? |
| **Salud** | `GET /health` | ¿Está viva la API? (sin API key) |

Arquitectura:

```
Navegador / celular ──► Streamlit (ui, :8501) ──X-API-Key──► FastAPI (api, :8000)
       ▲                                                        │
       └── túnel temporal de Cloudflare (trycloudflare.com)     └── trueprofit/ (lógica pura)
```

La interfaz llama a la API **desde el servidor**. Por eso la API key nunca llega al
navegador.

### Fórmulas principales

- **Utilidad recibida** = Σ (venta − flete − costo) de las líneas **entregadas**
- **Utilidad final** = utilidad recibida − flete de devoluciones − publicidad
- **Utilidad proyectada** = utilidad máxima × e − (1 − e) × flete despachado − publicidad
- **Por pedido (simulador)** = e·(precio − costo − flete) − (1 − e)·flete − CPA
- **Tasa de entrega de equilibrio** = (flete + CPA) / (precio − costo)

Regla de oro: el **dinero se suma por línea** de producto y los **pedidos se cuentan por
orden**. Una orden con 2 productos suma ambas líneas, pero cuenta como 1 pedido.

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (instala Python 3.12 si
  falta)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/), solo para el
  contenedor
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/),
  solo para publicar

## Instalación desde cero

```bash
git clone https://github.com/rincontfabio-create/trueprofit-api.git
cd trueprofit-api
uv sync                      # crea .venv con las versiones exactas de uv.lock
cp .env.example .env         # en Windows PowerShell: Copy-Item .env.example .env
```

### Configurar los secretos

La aplicación lee **un** secreto, `TRUEPROFIT_API_KEY`, de variables de entorno o del
archivo `.env`:

1. Genera una clave: `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Pégala en `.env` como `TRUEPROFIT_API_KEY=<tu-clave>`.

`.env` está en `.gitignore` y en `.dockerignore`. No entra al repositorio ni a la imagen:
Docker la recibe en tiempo de ejecución con `env_file`. Si la variable no está definida,
la API responde **503** y no queda abierta.

## Ejecutar sin Docker

```bash
# Terminal 1: API  -> http://localhost:8000/docs
uv run --env-file .env uvicorn trueprofit.api:app --reload

# Terminal 2: interfaz  -> http://localhost:8501
uv run --env-file .env streamlit run ui/app.py
```

## Verificación

```bash
uv run pytest              # 36 pruebas sobre la lógica, la lectura de CSV y la API
uv run ruff check .        # linting
uv run ruff format --check .
```

GitHub Actions (`.github/workflows/ci.yml`) ejecuta Ruff y pytest en cada push. También
construye las dos imágenes y comprueba `/health`.

## Contenedor

```bash
docker compose up --build
```

El `Dockerfile` multi-stage produce **dos imágenes** con una sola receta:

| Imagen | Contiene | No contiene |
|---|---|---|
| `trueprofit-api` (target `api`) | Python 3.12 slim, FastAPI/uvicorn, paquete `trueprofit` | Streamlit, pytest, ruff, uv, tests, datos |
| `trueprofit-ui` (target `ui`) | Python 3.12 slim, Streamlit/httpx, `ui/` + CSV de ejemplo | FastAPI, pytest, ruff, uv, tests |

Ambas corren con un usuario sin privilegios y tienen `HEALTHCHECK`. Compose arranca la
interfaz solo cuando la API está sana.

## Publicación temporal (Cloudflare)

Con el contenedor corriendo:

```bash
cloudflared tunnel --url http://localhost:8501
```

Abre la URL `https://<algo>.trycloudflare.com` que aparece desde un celular con datos
móviles. La dirección cambia cada vez que abres el túnel.

## Datos

`data/` y `ui/ejemplos/` tienen **datos sintéticos** generados por
`scripts/generar_datos.py`, con semilla fija. No hay información real del negocio.

Formato del CSV de pedidos (una fila por línea de producto; acepta `,` o `;`):

```
id_orden,fecha,estatus,producto,cantidad,total_orden,precio_flete,costo_proveedor
90000000,2026-10-21,ENTREGADO,Lámpara LED recargable,1,89900,16800,31000
```

CSV de publicidad: `producto,gasto`.

## Estructura

```
├── src/trueprofit/
│   ├── estatus.py     # clasificación de estados de Dropi
│   ├── metricas.py    # utilidad, tasas, CPA, proyección
│   ├── simulador.py   # unit economics de un producto
│   ├── lectura.py     # lectura y validación de CSV
│   ├── config.py      # secretos desde el entorno
│   └── api.py         # FastAPI
├── ui/                # Streamlit (app.py + cliente.py + ejemplos/)
├── tests/             # pytest
├── scripts/           # generador de datos sintéticos
├── Dockerfile · compose.yaml · .dockerignore
└── pyproject.toml · uv.lock · .python-version
```
