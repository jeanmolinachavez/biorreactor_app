import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import sys
from pymongo import MongoClient
import base64
from PIL import Image
from io import BytesIO

# Agrega la ruta raíz del proyecto al sistema
ROOT_DIR = Path(__file__).resolve().parents[1] # sube 1 nivel de dashboard
sys.path.append(str(ROOT_DIR))

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

    # Botones para activar/desactivar cada columnas para que queden horizontales
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        show_temp = st.checkbox("Temperatura", value=True)
    with col2:
        show_ph = st.checkbox("pH", value=True)
    with col3:
        show_oxy = st.checkbox("Oxígeno Disuelto", value=True)
    with col4:
        show_turb = st.checkbox("Turbidez", value=True)
    with col5:
        show_cond = st.checkbox("Conductividad", value=True)

    # Mostrar tabla
    st.subheader("Tabla de Datos Recientes")
    st.dataframe(df[::-1], use_container_width=True)

    # Gráficos
    st.subheader("Visualización de Sensores")

    # Se crea la figura de plotly
    fig = go.Figure()

    # Se agregar las trazas para el gráfico de dispersión
    if show_temp:
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df['temperatura'], mode='lines+markers', name='Temperatura'))
    if show_ph:
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df['ph'], mode='lines+markers', name='pH'))        
    if show_oxy:
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df['oxigeno'], mode='lines+markers', name='Oxígeno Disuelto'))   
    if show_turb:
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df['turbidez'], mode='lines+markers', name='Turbidez'))   
    if show_cond:
        fig.add_trace(go.Scatter(x=df["tiempo"], y=df['conductividad'], mode='lines+markers', name='Conductividad'))

    fig.update_layout(title='Datos de Sensores (Tiempo)', xaxis_title='Tiempo', yaxis_title='Valor', xaxis=dict(showgrid=True), yaxis=dict(showgrid=True))

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