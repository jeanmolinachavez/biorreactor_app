import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from pymongo import MongoClient
from config import MONGO_URI
from database import obtener_datos, obtener_registro_comida
from funciones_dashboard import (
    mostrar_metricas,
    mostrar_tabla,
    mostrar_registro_comida,
    mostrar_graficos,
    mostrar_imagenes
)

# --- UTILIDADES ---
@st.cache_data(ttl=600)
def cargar_datos_cacheados(dominio='dominio_ucn', limit=5000):
    return obtener_datos(dominio, limit)

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Dashboard Biorreactor", layout="wide")
st_autorefresh(interval=900000, key="dashboardrefresh")
st.title("🌱 Dashboard de Monitoreo - Biorreactor Inteligente")

# --- MENÚ LATERAL ---
st.sidebar.markdown("### 📁 **Navegación**")
seccion = st.sidebar.radio("Selecciona una sección:", [
    "📊 Métricas", 
    "📋 Reporte de Sensores", 
    "🍽️ Alimentación", 
    "📈 Gráficos", 
    "🖼️ Imágenes"
])

# --- CONEXIÓN A LA BASE DE DATOS --- 
client = MongoClient(MONGO_URI)
db = client["biorreactor_app"]

# --- SECCIÓN: FILTROS DE DOMINIO Y FECHAS ---
if seccion in ["📊 Métricas", "📋 Reporte de Sensores", "📈 Gráficos"]:
    with st.expander("🌐📅 Filtros de dominio y fechas", expanded=True):
        with st.form("form_filtros"):
            col1, col2 = st.columns(2)

            with col1:
                dominios_disponibles = sorted([col for col in db.list_collection_names() if col.startswith("dominio_")])
                indice_por_defecto = dominios_disponibles.index("dominio_ucn") if "dominio_ucn" in dominios_disponibles else 0
                dominio_seleccionado = st.selectbox("🌐 Selecciona un dominio:", dominios_disponibles, index=indice_por_defecto)

            with col2:
                data = cargar_datos_cacheados(dominio_seleccionado)
                if not data:
                    st.warning("⚠️ No hay datos disponibles.")
                    st.stop()

                df = pd.DataFrame(data)
                df = df[df['tiempo'].notna()]
                df['tiempo'] = pd.to_datetime(df['tiempo'])
                df = df.sort_values(by='tiempo')

                fecha_min = df['tiempo'].min().date()
                fecha_max = df['tiempo'].max().date()

                fecha_inicio, fecha_fin = st.date_input(
                    "📅 Rango de fechas:",
                    value=(fecha_min, fecha_max),
                    min_value=fecha_min,
                    max_value=fecha_max
                )

            st.form_submit_button("Aplicar filtros")

    # --- FILTRAR DATOS POR FECHA ---
    df = df[(df['tiempo'].dt.date >= fecha_inicio) & (df['tiempo'].dt.date <= fecha_fin)]
    if df.empty:
        st.warning("⚠️ No hay datos dentro del rango de fechas seleccionado.")
        st.stop()

# --- RENDERIZADO DE SECCIONES ---
if seccion == "📊 Métricas":
    mostrar_metricas(df)

elif seccion == "📋 Reporte de Sensores":
    mostrar_tabla(df)

elif seccion == "🍽️ Alimentación":
    registros = obtener_registro_comida(limit=5000)
    mostrar_registro_comida(registros)

elif seccion == "📈 Gráficos":
    mostrar_graficos(df)

elif seccion == "🖼️ Imágenes":
    collection = db["imagenes_webcam"]
    documentos = list(collection.find().sort("tiempo", -1).limit(5))
    mostrar_imagenes(documentos)

# --- BOTÓN GRAFANA ---
st.sidebar.markdown("---")
st.sidebar.link_button("🔗 Ir al Dashboard de Grafana", "https://jeanmolina.grafana.net/public-dashboards/dd177b1f03f94db6ac6242f5586c796d")
