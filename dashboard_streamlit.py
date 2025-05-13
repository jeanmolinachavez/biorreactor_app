import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pymongo import MongoClient
import base64
from PIL import Image
from io import BytesIO
from capturar_imagenes import capturar_y_guardar
from config import MONGO_URI
from database import obtener_datos

st.set_page_config(page_title="Dashboard Biorreactor", layout="wide")
st.title("Dashboard de Monitoreo - Biorreactor Inteligente")

data = obtener_datos(limit=100)

if not data:
    st.warning("No hay datos disponibles en la base de datos.")
else:
    df = pd.DataFrame(data)

    # Filtra solo los registros que tienen timestamp válido
    df = df[df['tiempo'].notna()]

    if not df.empty:
        df['tiempo'] = pd.to_datetime(df['tiempo'])
        df = df.sort_values(by='tiempo')
    else:
        st.warning("No hay registros válidos con tiempo")
        st.stop()

    # Mostrar tabla
    st.subheader("Tabla de Datos Recientes")
    st.dataframe(df[::-1], use_container_width=True)

# Gráficos
st.subheader("Visualización de Sensores")

# Lista de variables para graficar individualmente
variables = {
    "temperatura": "Temperatura (°C)",
    "ph": "pH",
    "oxigeno": "Oxígeno Disuelto (%)",
    "turbidez": "Turbidez (%)",
    "conductividad": "Conductividad (µS/cm)"
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
    checked = st.checkbox(
        f"Mostrar {label}",
        value=st.session_state.checkbox_states.get(var, True),
        key=f"chk_{var}"
    )
    st.session_state.checkbox_states[var] = checked

    if checked:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["tiempo"],
            y=df[var],
            mode="lines+markers",
            name=label,
            line=dict(color=colores.get(var, "black"))
        ))
        fig.update_layout(
            title=label,
            xaxis_title="Tiempo",
            yaxis_title=label,
            height=350,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

# Botón para captura manual de imagen
st.subheader("Captura Manual desde la Webcam")

if st.button("Capturar Imagen"):
    try:
        capturar_y_guardar()
        st.success("Imagen capturada y guardada exitosamente.")
    except Exception as e:
        st.error(f"Ocurrió un error al capturar: {e}")

# Mostrar imágenes de la webcam
st.subheader("Últimas Imágenes Capturadas desde Webcam")

try:
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db["imagenes_webcam"]

    documentos = list(collection.find().sort("tiempo", -1).limit(3))

    cols = st.columns(len(documentos))

    for idx, doc in enumerate(documentos):
        if 'imagen' in doc:
            imagen_bytes = base64.b64decode(doc['imagen'])
            imagen = Image.open(BytesIO(imagen_bytes))
            cols[idx].image(imagen, caption=f"Captura {idx+1}", use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar imágenes: {e}")