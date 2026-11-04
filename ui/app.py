"""Interfaz web de TrueProfit (Streamlit).

Ejecutar en local:  uv run --env-file .env streamlit run ui/app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st
from cliente import ErrorAPI, analizar, salud, simular

EJEMPLOS = Path(__file__).parent / "ejemplos"

st.set_page_config(page_title="TrueProfit", page_icon="📦", layout="centered")


def cop(valor: float | None) -> str:
    return "—" if valor is None else f"${valor:,.0f}".replace(",", ".")


def pct(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.1%}"


st.title("📦 TrueProfit")
st.caption(
    "¿Cuánto te deja de verdad tu tienda de dropshipping, después de fletes, devoluciones y pauta?"
)

if not salud():
    st.error("No hay conexión con la API. Revisa que esté corriendo y TRUEPROFIT_API_URL.")
    st.stop()

tab_simular, tab_analizar = st.tabs(["🧮 Simular un producto", "📊 Analizar mis pedidos"])

with tab_simular:
    st.subheader("¿Me conviene pautar este producto?")
    c1, c2 = st.columns(2)
    precio = c1.number_input("Precio de venta", min_value=1, value=89_900, step=1_000)
    costo = c2.number_input("Costo del proveedor", min_value=0, value=31_000, step=1_000)
    flete = c1.number_input("Flete por pedido", min_value=0, value=15_000, step=500)
    cpa = c2.number_input("Costo por venta (CPA)", min_value=0, value=18_000, step=500)
    tasa = st.slider("Tasa de entrega esperada", 0, 100, 75, format="%d %%") / 100

    try:
        s = simular(
            precio_venta=precio, costo_producto=costo, flete=flete, tasa_entrega=tasa, cpa=cpa
        )
    except ErrorAPI as e:
        st.error(str(e))
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Utilidad por pedido", cop(s["utilidad_por_pedido"]))
        m2.metric("CPA máximo", cop(s["cpa_equilibrio"]))
        m3.metric("Entrega mínima", pct(s["tasa_entrega_equilibrio"]))
        if s["es_rentable"]:
            st.success(f"Rentable: cada pedido despachado deja {cop(s['utilidad_por_pedido'])}.")
        else:
            st.warning("Con estos números pierdes plata. Baja el CPA o sube el precio.")

with tab_analizar:
    st.subheader("Resumen de tu tienda")
    usar_ejemplo = st.toggle("Usar datos de ejemplo (sintéticos)", value=True)
    if usar_ejemplo:
        pedidos = (EJEMPLOS / "pedidos_ejemplo.csv").read_bytes()
        publicidad = (EJEMPLOS / "publicidad_ejemplo.csv").read_bytes()
    else:
        f_ped = st.file_uploader("CSV de pedidos (líneas Dropi)", type="csv")
        f_ads = st.file_uploader("CSV de publicidad (producto, gasto) — opcional", type="csv")
        pedidos = f_ped.getvalue() if f_ped else None
        publicidad = f_ads.getvalue() if f_ads else None

    proyectar = st.checkbox("Proyectar con otra tasa de entrega")
    efectividad = st.slider("Tasa de entrega proyectada", 0, 100, 80) / 100 if proyectar else None

    if pedidos:
        try:
            datos = analizar(pedidos, publicidad, efectividad)
        except ErrorAPI as e:
            st.error(str(e))
        else:
            r = datos["resumen"]
            a, b, c = st.columns(3)
            a.metric("Venta despachada", cop(r["venta_despachada"]))
            b.metric("Utilidad final", cop(r["utilidad_final"]), pct(r["margen"]) + " margen")
            c.metric("Utilidad proyectada", cop(r["utilidad_proyectada"]))
            a.metric("Tasa de entrega", pct(r["tasa_entrega"]))
            b.metric("Tasa de devolución", pct(r["tasa_devolucion"]))
            c.metric("CPA", cop(r["cpa"]))

            st.markdown("**¿A dónde se va la utilidad?**")
            cascada = pd.DataFrame(
                {
                    "Concepto": ["Utilidad recibida", "Flete devoluciones", "Publicidad"],
                    "Valor": [
                        r["utilidad_recibida"],
                        -r["flete_devoluciones"],
                        -r["publicidad"],
                    ],
                }
            )
            st.bar_chart(cascada, x="Concepto", y="Valor", horizontal=True)

            st.markdown("**Por producto**")
            tabla = pd.DataFrame(datos["productos"]).T
            tabla = tabla[["utilidad_final", "publicidad", "tasa_entrega", "ordenes", "margen"]]
            tabla = tabla.sort_values("utilidad_final", ascending=False)
            st.dataframe(
                tabla.style.format(
                    {
                        "utilidad_final": cop,
                        "publicidad": cop,
                        "tasa_entrega": pct,
                        "margen": pct,
                        "ordenes": "{:.0f}",
                    }
                ).map(
                    lambda v: "color: #c0392b" if isinstance(v, float) and v < 0 else "",
                    subset=["utilidad_final"],
                ),
                width="stretch",
            )
            perdedores = tabla.index[tabla["utilidad_final"] < 0].tolist()
            if perdedores:
                st.warning("Pierden plata: " + ", ".join(perdedores))
    else:
        st.info("Sube el CSV de pedidos para ver el análisis.")
