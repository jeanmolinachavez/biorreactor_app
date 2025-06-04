import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pandas as pd
from pymongo import MongoClient
import base64
from PIL import Image
from io import BytesIO
from capturar_imagenes import capturar_y_guardar
from config import MONGO_URI
from database import obtener_datos, obtener_registro_comida
import pytz
from datetime import datetime

# --- UTILIDADES ---
def a_hora_chile(dt_utc):
    chile_tz = pytz.timezone('America/Santiago')
    return dt_utc.replace(tzinfo=pytz.utc).astimezone(chile_tz)

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Dashboard Biorreactor", layout="wide")
st_autorefresh(interval=900000, key="dashboardrefresh")

st.title("🌱 Dashboard de Monitoreo - Biorreactor Inteligente")

# --- DATOS DE SENSORES --- 
client = MongoClient(MONGO_URI)
db = client["biorreactor_app"]

# --- FILTRO DE DOMINIOS ---
st.subheader("🌐 Filtro de Dominios")

# Filtrar solo colecciones que comiencen con "dominio_"
dominios_disponibles = sorted([col for col in db.list_collection_names() if col.startswith("dominio_")])

# Intentar seleccionar por defecto "dominio_ucn" si está en la lista
indice_por_defecto = dominios_disponibles.index("dominio_ucn") if "dominio_ucn" in dominios_disponibles else 0

# Selector de dominio (colección)
dominio_seleccionado = st.selectbox(
    "Selecciona un dominio (colección)",
    dominios_disponibles,
    index=indice_por_defecto
)

# Cargar datos del dominio seleccionado
data = obtener_datos(dominio=dominio_seleccionado, limit=2000)

if not data:
    st.warning("⚠️ No hay datos disponibles en la base de datos.")
    st.stop()

# Procesamiento de datos
with st.spinner("Procesando datos..."):
    df = pd.DataFrame(data)
    df = df[df['tiempo'].notna()]

    if df.empty:
        st.warning("⚠️ No hay registros válidos con tiempo.")
        st.stop()

    df['tiempo'] = pd.to_datetime(df['tiempo'])
    df = df.sort_values(by='tiempo')

# --- FILTRO DE FECHAS ---
st.subheader("📅 Filtro de Fechas")

fecha_min = df["tiempo"].min().date()
fecha_max = df["tiempo"].max().date()

fecha_inicio, fecha_fin = st.date_input(
    "Selecciona un rango de fechas:",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

# Filtrar el DataFrame por el rango seleccionado
df = df[(df["tiempo"].dt.date >= fecha_inicio) & (df["tiempo"].dt.date <= fecha_fin)]

# --- MÉTRICAS ---
st.markdown("### 📊 Últimos Valores de Sensores")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperatura", f"{df['temperatura'].iloc[-1]:.2f} °C")
col2.metric("🌊 pH", f"{df['ph'].iloc[-1]:.2f}")
col3.metric("🧪 Turbidez", f"{df['turbidez'].iloc[-1]:.2f} %")
col4.metric("🫁 Oxígeno", f"{df['oxigeno'].iloc[-1]:.2f} %")

# --- TABLA DE DATOS DE SENSORES ---
st.subheader("📋 Tabla de Datos Recientes")
st.dataframe(df[::-1], use_container_width=True)

# --- REGISTRO DE COMIDAS ---
st.subheader("🍽️ Registro de Alimentación")
registros = obtener_registro_comida(limit=2000)

if registros:
    df_comida = pd.DataFrame(registros)
    df_comida["tiempo"] = pd.to_datetime(df_comida["tiempo"])

    # Dividir en dos columnas: mensaje y tabla
    col1, col2 = st.columns([1, 2])

    with col1:
        ultima_fecha = df_comida["tiempo"].max()
        ultima_fecha_str = ultima_fecha.strftime("%Y-%m-%d %H:%M:%S")

        st.info(f"🍽️ Última alimentación:\n**{ultima_fecha_str}**")

        # Calcular días sin alimentar
        ahora_chile = datetime.now(pytz.timezone('America/Santiago'))
        dias_sin_alimentar = (ahora_chile.date() - ultima_fecha.date()).days
        
        # Mostrar mensaje según días transcurridos
        if dias_sin_alimentar == 0:
            st.success("✅ Hoy se han alimentado a las microalgas.")
        elif dias_sin_alimentar == 1:
            st.info("ℹ️ Ha pasado 1 día desde la última alimentación.")
        else:
            st.warning(f"⚠️ Han pasado {dias_sin_alimentar} días sin alimentar a las microalgas.")

    with col2:
        with st.expander("📄 Ver historial de alimentación"):
            st.table(df_comida[::-1])
else:
    st.info("ℹ️ No hay registros de alimentación aún.")

# --- GRÁFICOS DE SENSORES EN PESTAÑAS ---
st.subheader("📈 Visualización de Sensores - esp32_01")

# --- Seleccionar dominio si está disponible ---
if "dominio" in df.columns:
    dominios_unicos = sorted(df["dominio"].dropna().unique())
    dominio_seleccionado_dato = st.selectbox("🌐 Selecciona el dominio del dato:", dominios_unicos)
    df_dominio_ucn = df[df["dominio"] == dominio_seleccionado_dato]
else:
    df_dominio_ucn = df

# --- Filtrar por esp32_01 ---
df_01 = df_dominio_ucn[df_dominio_ucn["id_dispositivo"] == "esp32_01"]

if df_01.empty:
    st.info("ℹ️ No hay datos para el dispositivo esp32_01.")
else:
    # Variables disponibles: (nombre legible, unidad, color)
    variables = {
        "temperatura": ("Temperatura", "°C", "red"),
        "ph": ("pH", "pH", "purple"),
        "oxigeno": ("Oxígeno", "%", "green"),
        "turbidez": ("Turbidez", "%", "blue"),
        "conductividad": ("Conductividad", "ppm", "orange"),
    }

    tab_labels = list([nombre for (nombre, _, _) in variables.values()])
    tab_labels.append("Comparación múltiple")
    tabs = st.tabs(tab_labels)

    # --- PESTAÑAS INDIVIDUALES POR VARIABLE ---
    for i, (var, (nombre, unidad, color)) in enumerate(variables.items()):
        with tabs[i]:
            if var in df_01.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_01["tiempo"], y=df_01[var],
                    mode="lines+markers",
                    name=nombre,
                    line=dict(color=color, width=2),
                    marker=dict(size=6, opacity=0.7)
                ))

                fig.update_layout(
                    title=f"{nombre} - esp32_01",
                    xaxis_title="Tiempo",
                    yaxis_title=unidad,
                    height=400,
                    margin=dict(l=40, r=40, t=40, b=40),
                )

                fig.update_xaxes(
                    tickformat="%d-%m %H:%M",
                    tickangle=45,
                    nticks=10,
                    showgrid=True
                )
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"⚠️ No hay datos para la variable '{var}' en esp32_01.")

    # --- COMPARACIÓN MÚLTIPLE DE DISPOSITIVOS ---
    with tabs[-1]:
        st.markdown("### 🔍 Comparación múltiple de dispositivos")

        dispositivos = df_dominio_ucn["id_dispositivo"].dropna().unique().tolist()
        seleccionados = st.multiselect("Selecciona dispositivos:", dispositivos, default=dispositivos[:2])
        var_multi = st.selectbox("Variable a visualizar:", list(variables.keys()), format_func=lambda x: variables[x][0])

        if seleccionados and var_multi:
            fig = go.Figure()
            for disp in seleccionados:
                df_disp = df_dominio_ucn[df_dominio_ucn["id_dispositivo"] == disp]
                fig.add_trace(go.Scatter(
                    x=df_disp["tiempo"],
                    y=df_disp[var_multi],
                    mode="lines+markers",
                    name=disp
                ))

            fig.update_layout(
                title=f"Comparación de {variables[var_multi][0]} entre múltiples dispositivos",
                xaxis_title="Tiempo",
                yaxis_title=variables[var_multi][1],
                height=450,
                margin=dict(l=40, r=40, t=40, b=40),
            )

            fig.update_xaxes(tickformat="%d-%m %H:%M", tickangle=45, showgrid=True)
            fig.update_yaxes(showgrid=True, gridcolor='lightgray')

            st.plotly_chart(fig, use_container_width=True)

# --- CAPTURA DE IMAGENES ---
#st.subheader("📷 Captura Manual desde la Webcam (Solo en Local)")
#
#if st.button("📸 Capturar Imagen"):
#    try:
#        capturar_y_guardar()
#        st.success("✅ Imagen capturada exitosamente.")
#    except Exception as e:
#        st.error(f"❌ Error al capturar: {e}")

# Mostrar últimas imágenes de la webcam
st.subheader("🖼️ Últimas Imágenes Capturadas")

try:
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db["imagenes_webcam"]
    documentos = list(collection.find().sort("tiempo", -1).limit(3))

    cols = st.columns(len(documentos))
    for idx, doc in enumerate(documentos):
        if 'imagen' in doc and 'tiempo' in doc:
            imagen_bytes = base64.b64decode(doc['imagen'])
            imagen = Image.open(BytesIO(imagen_bytes))
            tiempo_str = a_hora_chile(doc['tiempo']).strftime('%Y-%m-%d %H:%M:%S')
            cols[idx].image(imagen, caption=f"Capturada el {tiempo_str}", use_container_width=True)
except Exception as e:
    st.error(f"❌ Error al cargar imágenes: {e}")