import pytest

from trueprofit.estatus import Grupo, clasificar
from trueprofit.metricas import Linea, calcular_metricas, metricas_por_producto


def linea(orden, estatus, total, flete, costo, producto="A", cantidad=1):
    return Linea(orden, estatus, producto, cantidad, total, flete, costo)


@pytest.fixture
def tienda():
    """5 órdenes: 2 entregadas (una con 2 líneas), 1 devuelta, 1 cancelada, 1 en tránsito."""
    return [
        linea("1", "ENTREGADO", 100_000, 15_000, 40_000),
        linea("2", "ENTREGADO", 60_000, 8_000, 20_000, producto="B"),
        linea("2", "ENTREGADO", 40_000, 7_000, 15_000, producto="B"),
        linea("3", "DEVOLUCION", 100_000, 15_000, 40_000),
        linea("4", "CANCELADO", 100_000, 15_000, 40_000),
        linea("5", "EN TRANSPORTE", 100_000, 15_000, 40_000),
    ]


@pytest.mark.parametrize(
    ("estatus", "esperado"),
    [
        ("ENTREGADO", Grupo.ENTREGADO),
        ("  entregado ", Grupo.ENTREGADO),
        ("Devolución", Grupo.DEVOLUCION),
        ("DEVUELTO AL REMITENTE", Grupo.DEVOLUCION),
        ("DEVOLUCION RECHAZADA", Grupo.DEVOLUCION),  # devolución gana a "RECHAZ"
        ("CANCELADO", Grupo.ANULADO),
        ("RECHAZADO", Grupo.ANULADO),
        ("GUIA ANULADA", Grupo.ANULADO),
        ("GUIA GENERADA", Grupo.TRANSITO),
        ("PENDIENTE CONFIRMACION", Grupo.TRANSITO),
    ],
)
def test_clasificacion_de_estatus(estatus, esperado):
    assert clasificar(estatus) is esperado


def test_dinero_se_suma_por_linea_y_ordenes_se_cuentan_una_vez(tienda):
    m = calcular_metricas(tienda)
    # La orden 2 tiene dos líneas: su dinero suma ambas, pero cuenta como UNA orden.
    assert m.utilidad_recibida == (100_000 - 15_000 - 40_000) + (60_000 - 8_000 - 20_000) + (
        40_000 - 7_000 - 15_000
    )
    assert m.ordenes == 5
    assert m.ordenes_despachadas == 4


def test_cancelado_no_cuenta_como_venta_despachada_ni_utilidad_maxima(tienda):
    m = calcular_metricas(tienda)
    assert m.venta_bruta == 500_000
    assert m.venta_despachada == 400_000
    # Máxima = margen de todo lo no anulado (órdenes 1, 2, 3 y 5).
    assert m.utilidad_maxima == 45_000 + 50_000 + 45_000 + 45_000


def test_utilidad_final_descuenta_flete_de_devolucion_y_publicidad(tienda):
    m = calcular_metricas(tienda, publicidad=30_000)
    assert m.flete_devoluciones == 15_000
    assert m.utilidad_final == 95_000 - 15_000 - 30_000
    assert m.cpa == pytest.approx(30_000 / 5)
    assert m.roi_pauta == pytest.approx(50_000 / 30_000)


def test_tasas_sobre_despachado_suman_100(tienda):
    m = calcular_metricas(tienda)
    assert m.tasa_entrega + m.tasa_transito + m.tasa_devolucion == pytest.approx(1.0)
    assert m.tasa_cancelacion == pytest.approx(1 / 5)


def test_utilidad_proyectada_con_efectividad_indicada(tienda):
    m = calcular_metricas(tienda, publicidad=10_000, efectividad_proyectada=0.8)
    flete_despachado = 15_000 + 15_000 + 15_000 + 15_000  # órdenes 1, 2 (8k+7k), 3 y 5
    esperado = 185_000 * 0.8 - 0.2 * flete_despachado - 10_000
    assert m.utilidad_proyectada == pytest.approx(esperado)


def test_sin_datos_las_razones_son_none_no_division_por_cero():
    m = calcular_metricas([])
    assert m.efectividad is None
    assert m.margen is None
    assert m.tasa_entrega is None
    assert m.cpa is None


def test_valores_invalidos_se_rechazan(tienda):
    with pytest.raises(ValueError):
        calcular_metricas(tienda, publicidad=-1)
    with pytest.raises(ValueError):
        calcular_metricas(tienda, efectividad_proyectada=1.5)


def test_por_producto_incluye_producto_en_testeo_solo_con_pauta(tienda):
    resultado = metricas_por_producto(tienda, {"A": 20_000, "NUEVO": 5_000})
    assert set(resultado) == {"A", "B", "NUEVO"}
    assert resultado["NUEVO"].utilidad_final == -5_000
    assert resultado["B"].publicidad == 0
