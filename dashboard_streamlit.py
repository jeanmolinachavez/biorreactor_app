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
data = obtener_datos(limit=2000)

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
col1, col2, col3 = st.columns(3)
col1.metric("🌡️ Temperatura", f"{df['temperatura'].iloc[-1]:.2f} °C")
col2.metric("🌊 pH", f"{df['ph'].iloc[-1]:.2f}")
col3.metric("🧪 Turbidez", f"{df['turbidez'].iloc[-1]:.2f} %")

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

# --- GRÁFICOS DE SENSORES ---
st.subheader("📈 Visualización de Sensores")

# Lista de variables para graficar individualmente
variables = {
    "temperatura": "Temperatura",
    "ph": "pH",
    "oxigeno": "Oxígeno - Concentración de O2 en el aire",
    "turbidez": "Turbidez",
    "conductividad": "Conductividad - Sólidos totales disueltos"
}

# Lista de unidades de cada variable
unidades = {
    "temperatura": "°C",
    "ph": "pH",
    "oxigeno": "%",
    "turbidez": "%",
    "conductividad": "ppm"
}

# Colores personalizados por variable
colores = {
    "temperatura": "red",
    "ph": "purple",
    "oxigeno": "green",
    "turbidez": "blue",
    "conductividad": "orange"
}

# Filtrar por columnas existentes en el DataFrame
variables_disponibles = {var: label for var, label in variables.items() if var in df.columns}

# Inicializar estado si no existe aún
if "checkbox_states" not in st.session_state:
    st.session_state.checkbox_states = {var: True for var in variables_disponibles}

# Botones para mostrar u ocultar todos
col1, col2 = st.columns(2)
if col1.button("✅ Mostrar todas"):
    for var in st.session_state.checkbox_states:
        st.session_state.checkbox_states[var] = True
if col2.button("❌ Ocultar todas"):
    for var in st.session_state.checkbox_states:
        st.session_state.checkbox_states[var] = False

# Mostrar un checkbox por variable con estado guardado
for var, label in variables_disponibles.items():
    checked = st.checkbox(f"Mostrar {label}", value=st.session_state.checkbox_states[var], key=f"chk_{var}")
    st.session_state.checkbox_states[var] = checked

    if checked:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["tiempo"], y=df[var],
            mode="lines+markers",
            name=label,
            line=dict(color=colores.get(var, "black"), width=2),
            marker=dict(size=6, opacity=0.7)
        ))

        fig.update_layout(
            title=label.split("(")[0].strip(),
            xaxis_title="Tiempo",
            yaxis_title=unidades.get(var, ""),
            height=350,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(255,255,255,0.7)',
                bordercolor="Black",
                borderwidth=1
            )
        )

        fig.update_xaxes(
            tickformat="%d-%m %H:%M",
            tickangle=45,
            nticks=10,
            showgrid=True
        )
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

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