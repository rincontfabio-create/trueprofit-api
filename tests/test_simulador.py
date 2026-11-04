import pytest

from trueprofit.simulador import simular


def test_producto_rentable():
    s = simular(
        precio_venta=90_000, costo_producto=30_000, flete=15_000, tasa_entrega=0.8, cpa=15_000
    )
    assert s.margen_entregado == 45_000
    # 0.8 * 45.000 - 0.2 * 15.000 = 33.000 de CPA máximo
    assert s.cpa_equilibrio == pytest.approx(33_000)
    assert s.utilidad_por_pedido == pytest.approx(18_000)
    assert s.es_rentable


def test_tasa_de_equilibrio_deja_utilidad_cero():
    s = simular(90_000, 30_000, 15_000, 0.8, 15_000)
    en_equilibrio = simular(90_000, 30_000, 15_000, s.tasa_entrega_equilibrio, 15_000)
    assert en_equilibrio.utilidad_por_pedido == pytest.approx(0, abs=1e-6)


def test_producto_imposible_de_rentabilizar():
    # El costo + flete + CPA supera el precio: ni entregando el 100 % se gana.
    s = simular(50_000, 30_000, 15_000, 1.0, 20_000)
    assert not s.es_rentable
    assert s.tasa_entrega_equilibrio is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"precio_venta": -1, "costo_producto": 0, "flete": 0, "tasa_entrega": 0.5, "cpa": 0},
        {"precio_venta": 1, "costo_producto": 0, "flete": 0, "tasa_entrega": 1.2, "cpa": 0},
    ],
)
def test_entradas_invalidas(kwargs):
    with pytest.raises(ValueError):
        simular(**kwargs)
