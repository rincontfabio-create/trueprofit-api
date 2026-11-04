"""Genera datos SINTÉTICOS de pedidos y pauta para probar la aplicación.

No usa ningún dato real del negocio: productos, precios y estados son inventados con una
semilla fija, así que el resultado es siempre el mismo.

    uv run python scripts/generar_datos.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 42
N_ORDENES = 400
RAIZ = Path(__file__).resolve().parents[1]
DESTINOS = [RAIZ / "data", RAIZ / "ui" / "ejemplos"]

# producto: (precio de venta, costo proveedor, tasa de entrega típica, gasto en pauta del mes)
PRODUCTOS = {
    "Lámpara LED recargable": (89_900, 31_000, 0.72, 2_100_000),
    "Organizador de cocina": (69_900, 22_000, 0.78, 1_200_000),
    "Masajeador cervical": (119_900, 45_000, 0.64, 2_600_000),
    "Cepillo alisador": (79_900, 27_500, 0.70, 1_500_000),
    "Kit de herramientas 46 pzas": (99_900, 52_000, 0.81, 900_000),
    "Botella térmica": (49_900, 18_000, 0.74, 1_150_000),
}
ESTADOS_NO_ENTREGADOS = [
    ("DEVOLUCION", 0.55),
    ("EN TRANSPORTE", 0.15),
    ("CANCELADO", 0.18),
    ("RECHAZADO", 0.07),
    ("GUIA GENERADA", 0.05),
]


def estado(rng: random.Random, tasa_entrega: float) -> str:
    if rng.random() < tasa_entrega:
        return "ENTREGADO"
    estados, pesos = zip(*ESTADOS_NO_ENTREGADOS, strict=True)
    return rng.choices(estados, pesos)[0]


def generar() -> tuple[list[dict], list[dict]]:
    rng = random.Random(SEMILLA)
    nombres = list(PRODUCTOS)
    inicio = date(2026, 10, 1)
    filas = []
    for n in range(N_ORDENES):
        id_orden = str(90_000_000 + n)
        fecha = inicio + timedelta(days=rng.randrange(31))
        principal = rng.choice(nombres)
        est = estado(rng, PRODUCTOS[principal][2])
        flete_orden = rng.choice([13_500, 15_000, 16_800, 18_900])
        # ~12 % de las órdenes llevan un segundo producto (orden multi-línea)
        productos = [principal]
        if rng.random() < 0.12:
            productos.append(rng.choice([p for p in nombres if p != principal]))
        for i, prod in enumerate(productos):
            precio, costo, _, _ = PRODUCTOS[prod]
            cantidad = 1 if rng.random() < 0.85 else 2
            filas.append(
                {
                    "id_orden": id_orden,
                    "fecha": fecha.isoformat(),
                    "estatus": est,
                    "producto": prod,
                    "cantidad": cantidad,
                    "total_orden": precio * cantidad,
                    # Dropi reparte el flete de la orden entre sus líneas
                    "precio_flete": round(flete_orden / len(productos)) if i == 0 else 0,
                    "costo_proveedor": costo * cantidad,
                }
            )
        if len(productos) == 2:
            filas[-1]["precio_flete"] = flete_orden - filas[-2]["precio_flete"]
    ads = [{"producto": p, "gasto": v[3]} for p, v in PRODUCTOS.items()]
    return filas, ads


def escribir(ruta: Path, filas: list[dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


if __name__ == "__main__":
    pedidos, ads = generar()
    for destino in DESTINOS:
        escribir(destino / "pedidos_ejemplo.csv", pedidos)
        escribir(destino / "publicidad_ejemplo.csv", ads)
    print(f"{len(pedidos)} líneas de pedido y {len(ads)} filas de pauta en: {DESTINOS}")
