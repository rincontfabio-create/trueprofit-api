import pytest
from fastapi.testclient import TestClient

from trueprofit.api import app

CLAVE = "clave-de-prueba"
CSV = (
    "id_orden,estatus,producto,cantidad,total_orden,precio_flete,costo_proveedor\n"
    "1,ENTREGADO,A,1,100000,15000,40000\n"
    "2,DEVOLUCION,A,1,100000,15000,40000\n"
    "3,ENTREGADO,B,1,50000,10000,20000\n"
)
SIMULACION = {
    "precio_venta": 90000,
    "costo_producto": 30000,
    "flete": 15000,
    "tasa_entrega": 0.8,
    "cpa": 15000,
}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv("TRUEPROFIT_API_KEY", CLAVE)
    return TestClient(app)


def test_health_responde_sin_api_key(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("cabeceras", [{}, {"X-API-Key": "incorrecta"}])
def test_endpoints_protegidos_rechazan_sin_clave_valida(cliente, cabeceras):
    r = cliente.post("/simular", json=SIMULACION, headers=cabeceras)
    assert r.status_code == 401


def test_sin_clave_configurada_el_servidor_no_queda_abierto(monkeypatch):
    monkeypatch.delenv("TRUEPROFIT_API_KEY", raising=False)
    r = TestClient(app).post("/simular", json=SIMULACION, headers={"X-API-Key": ""})
    assert r.status_code == 503


def test_simular(cliente):
    r = cliente.post("/simular", json=SIMULACION, headers={"X-API-Key": CLAVE})
    assert r.status_code == 200
    assert r.json()["utilidad_por_pedido"] == pytest.approx(18_000)


def test_simular_valida_rangos(cliente):
    malo = SIMULACION | {"tasa_entrega": 2}
    r = cliente.post("/simular", json=malo, headers={"X-API-Key": CLAVE})
    assert r.status_code == 422


def test_analizar_csv_con_publicidad(cliente):
    r = cliente.post(
        "/analizar",
        headers={"X-API-Key": CLAVE},
        files={
            "pedidos": ("pedidos.csv", CSV, "text/csv"),
            "publicidad": ("ads.csv", "producto,gasto\nA,20000\n", "text/csv"),
        },
    )
    assert r.status_code == 200
    datos = r.json()
    # Recibido: 45.000 (A) + 20.000 (B); menos flete devolución 15.000 y pauta 20.000
    assert datos["resumen"]["utilidad_final"] == 30_000
    assert datos["productos"]["A"]["utilidad_final"] == 45_000 - 15_000 - 20_000


def test_analizar_csv_invalido_devuelve_422(cliente):
    r = cliente.post(
        "/analizar",
        headers={"X-API-Key": CLAVE},
        files={"pedidos": ("p.csv", "columna\n1\n", "text/csv")},
    )
    assert r.status_code == 422
    assert "Faltan columnas" in r.json()["detail"]
