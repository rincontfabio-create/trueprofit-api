"""Cálculo de la utilidad real de una tienda a partir de sus líneas de pedido.

Regla de oro (heredada de TrueProfitDrop): Dropi entrega una fila por *línea de producto*
y ya reparte el total y el flete de la orden entre sus líneas. Por eso:

* el **dinero** (total, flete, costo) se **suma por línea**, nunca se deduplica;
* los **conteos de órdenes** se hacen por ``id_orden`` (una orden de 3 productos es 1 orden).
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass

from trueprofit.estatus import Grupo, clasificar


@dataclass(frozen=True)
class Linea:
    """Una línea de producto dentro de una orden."""

    id_orden: str
    estatus: str
    producto: str
    cantidad: int
    total_orden: float  # valor de venta de ESTA línea
    precio_flete: float  # flete repartido a esta línea
    costo_proveedor: float  # costo de mercancía de la línea (precio proveedor x cantidad)

    @property
    def grupo(self) -> Grupo:
        return clasificar(self.estatus)

    @property
    def margen_linea(self) -> float:
        """Lo que deja la línea si se entrega: venta - flete - costo."""
        return self.total_orden - self.precio_flete - self.costo_proveedor


@dataclass(frozen=True)
class Metricas:
    venta_bruta: float
    venta_despachada: float
    utilidad_recibida: float
    utilidad_maxima: float
    efectividad: float | None
    flete_devoluciones: float
    publicidad: float
    utilidad_final: float
    margen: float | None
    ordenes: int
    ordenes_despachadas: int
    tasa_entrega: float | None
    tasa_transito: float | None
    tasa_devolucion: float | None
    tasa_cancelacion: float | None
    cpa: float | None
    roi_pauta: float | None
    utilidad_proyectada: float

    def como_dict(self) -> dict:
        return asdict(self)


def _division(numerador: float, denominador: float) -> float | None:
    """Divide devolviendo None si el denominador es 0 (la métrica no aplica)."""
    return numerador / denominador if denominador else None


def utilidad_proyectada(
    utilidad_maxima: float, flete_despachado: float, publicidad: float, efectividad: float
) -> float:
    """Utilidad esperada si se entrega una fracción ``efectividad`` de lo despachado.

    Lo entregado aporta su margen; lo que no se entrega se devuelve y cuesta su flete.
    """
    return utilidad_maxima * efectividad - (1 - efectividad) * flete_despachado - publicidad


def calcular_metricas(
    lineas: Iterable[Linea],
    publicidad: float = 0.0,
    efectividad_proyectada: float | None = None,
) -> Metricas:
    """Calcula las métricas del resumen general para un conjunto de líneas.

    ``efectividad_proyectada`` (0-1) es la tasa de entrega que el usuario espera; si no se
    indica, se usa la tasa de entrega observada en los datos.
    """
    if publicidad < 0:
        raise ValueError("La publicidad no puede ser negativa")
    if efectividad_proyectada is not None and not 0 <= efectividad_proyectada <= 1:
        raise ValueError("La efectividad proyectada debe estar entre 0 y 1")

    lineas = list(lineas)
    venta_bruta = venta_despachada = 0.0
    utilidad_recibida = utilidad_maxima = 0.0
    flete_devoluciones = flete_despachado = 0.0
    grupo_por_orden: dict[str, Grupo] = {}

    for ln in lineas:
        g = ln.grupo
        grupo_por_orden[ln.id_orden] = g
        venta_bruta += ln.total_orden
        if g is Grupo.ANULADO:
            continue
        venta_despachada += ln.total_orden
        utilidad_maxima += ln.margen_linea
        flete_despachado += ln.precio_flete
        if g is Grupo.ENTREGADO:
            utilidad_recibida += ln.margen_linea
        elif g is Grupo.DEVOLUCION:
            flete_devoluciones += ln.precio_flete

    conteo = defaultdict(int)
    for g in grupo_por_orden.values():
        conteo[g] += 1
    ordenes = len(grupo_por_orden)
    despachadas = ordenes - conteo[Grupo.ANULADO]

    tasa_entrega = _division(conteo[Grupo.ENTREGADO], despachadas)
    utilidad_final = utilidad_recibida - flete_devoluciones - publicidad
    ef = efectividad_proyectada if efectividad_proyectada is not None else (tasa_entrega or 0.0)

    return Metricas(
        venta_bruta=venta_bruta,
        venta_despachada=venta_despachada,
        utilidad_recibida=utilidad_recibida,
        utilidad_maxima=utilidad_maxima,
        efectividad=_division(utilidad_recibida, utilidad_maxima),
        flete_devoluciones=flete_devoluciones,
        publicidad=publicidad,
        utilidad_final=utilidad_final,
        margen=_division(utilidad_final, venta_despachada),
        ordenes=ordenes,
        ordenes_despachadas=despachadas,
        tasa_entrega=tasa_entrega,
        tasa_transito=_division(conteo[Grupo.TRANSITO], despachadas),
        tasa_devolucion=_division(conteo[Grupo.DEVOLUCION], despachadas),
        tasa_cancelacion=_division(conteo[Grupo.ANULADO], ordenes),
        cpa=_division(publicidad, ordenes) if publicidad else None,
        roi_pauta=_division(utilidad_final, publicidad),
        utilidad_proyectada=utilidad_proyectada(utilidad_maxima, flete_despachado, publicidad, ef),
    )


def metricas_por_producto(
    lineas: Iterable[Linea],
    publicidad_por_producto: Mapping[str, float] | None = None,
    efectividad_proyectada: float | None = None,
) -> dict[str, Metricas]:
    """Métricas de cada producto, con su publicidad atribuida."""
    publicidad_por_producto = publicidad_por_producto or {}
    grupos: dict[str, list[Linea]] = defaultdict(list)
    for ln in lineas:
        grupos[ln.producto].append(ln)
    # Un producto con pauta pero sin pedidos (en testeo) también debe aparecer.
    for producto in publicidad_por_producto:
        grupos.setdefault(producto, [])
    return {
        producto: calcular_metricas(
            ls, publicidad_por_producto.get(producto, 0.0), efectividad_proyectada
        )
        for producto, ls in sorted(grupos.items())
    }
