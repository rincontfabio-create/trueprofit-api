"""Simulador de rentabilidad de un producto antes de pautarlo (unit economics por pedido)."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Simulacion:
    margen_entregado: float  # lo que deja un pedido entregado: precio - costo - flete
    utilidad_por_pedido: float  # esperada, ya descontando devoluciones y CPA
    cpa_equilibrio: float  # CPA máximo que se puede pagar sin perder
    tasa_entrega_equilibrio: float | None  # tasa de entrega mínima para no perder
    es_rentable: bool

    def como_dict(self) -> dict:
        return asdict(self)


def simular(
    precio_venta: float,
    costo_producto: float,
    flete: float,
    tasa_entrega: float,
    cpa: float,
) -> Simulacion:
    """Utilidad esperada por pedido despachado.

    Con probabilidad ``tasa_entrega`` el pedido se entrega y deja precio - costo - flete;
    si no, se devuelve y se pierde el flete. A todo pedido se le descuenta el CPA.
    """
    if min(precio_venta, costo_producto, flete, cpa) < 0:
        raise ValueError("Los valores monetarios no pueden ser negativos")
    if not 0 <= tasa_entrega <= 1:
        raise ValueError("La tasa de entrega debe estar entre 0 y 1")

    margen = precio_venta - costo_producto - flete
    cpa_equilibrio = tasa_entrega * margen - (1 - tasa_entrega) * flete
    utilidad = cpa_equilibrio - cpa
    # e*(precio - costo - flete) - (1-e)*flete - cpa = 0  =>  e = (flete + cpa) / (precio - costo)
    bruto = precio_venta - costo_producto
    tasa_eq = (flete + cpa) / bruto if bruto > 0 else None
    if tasa_eq is not None and tasa_eq > 1:
        tasa_eq = None  # ni entregando todo se recupera

    return Simulacion(
        margen_entregado=margen,
        utilidad_por_pedido=utilidad,
        cpa_equilibrio=cpa_equilibrio,
        tasa_entrega_equilibrio=tasa_eq,
        es_rentable=utilidad > 0,
    )
