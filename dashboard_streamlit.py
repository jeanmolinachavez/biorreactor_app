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

# Botón para redirigir a dashboard en grafana
st.link_button("🔗 Ir al Dashboard en Grafana", "https://jeanmolina.grafana.net/public-dashboards/dd177b1f03f94db6ac6242f5586c796d", use_container_width=True)

# --- CONEXIÓN A LA BASE DE DATOS --- 
client = MongoClient(MONGO_URI)
db = client["biorreactor_app"]

# --- FILTROS DE DOMINIO Y FECHAS EN UNA FILA ---
st.subheader("🌐📅 Filtros de Dominio y Fecha")

# Dividir en dos columnas: dominio y fecha
col_dom, col_fecha = st.columns([1, 2])

with col_dom:
    # Filtrar solo colecciones que comiencen con "dominio_"
    dominios_disponibles = sorted([col for col in db.list_collection_names() if col.startswith("dominio_")])
    
    # Intentar seleccionar por defecto "dominio_ucn" si está en la lista
    indice_por_defecto = dominios_disponibles.index("dominio_ucn") if "dominio_ucn" in dominios_disponibles else 0

    # Selector de dominio (colección)
    dominio_seleccionado = st.selectbox(
        "Selecciona un dominio:",
        dominios_disponibles,
        index=indice_por_defecto
    )

# --- CARGAR Y PROCESAR DATOS DE LA COLECCIÓN SELECCIONADA ---
with st.spinner("Procesando datos..."):
    # Cargar datos del dominio seleccionado
    data = obtener_datos(dominio=dominio_seleccionado, limit=2000)

    if not data:
        st.warning("⚠️ No hay datos disponibles en la base de datos.")
        st.stop()

    df = pd.DataFrame(data)
    df = df[df['tiempo'].notna()]

    if df.empty:
        st.warning("⚠️ No hay registros válidos con tiempo.")
        st.stop()

    df['tiempo'] = pd.to_datetime(df['tiempo'])
    df = df.sort_values(by='tiempo')

    # FILTRO DE FECHAS EN LA MISMA FILA
    with col_fecha:
        fecha_min = df["tiempo"].min().date()
        fecha_max = df["tiempo"].max().date()

        fecha_inicio, fecha_fin = st.date_input(
            "Selecciona un rango de fechas:",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        # Filtrar el dataframe por el rango seleccionado
        df = df[(df["tiempo"].dt.date >= fecha_inicio) & (df["tiempo"].dt.date <= fecha_fin)]

        if df.empty:
            st.warning("⚠️ No hay datos dentro del rango de fechas seleccionado.")
            st.stop()

# --- MÉTRICAS ---
st.markdown("### 📊 Últimos Valores de Sensores")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperatura", f"{df['temperatura'].iloc[-1]:.2f} °C")
col2.metric("🌊 pH", f"{df['ph'].iloc[-1]:.2f}")
col3.metric("🧪 Turbidez", f"{df['turbidez'].iloc[-1]:.2f} %")
col4.metric("🫁 Oxígeno", f"{df['oxigeno'].iloc[-1]:.2f} %")

# --- TABLA DE DATOS DE SENSORES CON FILTRO POR DISPOSITIVO Y PAGINACIÓN ---
st.subheader("📋 Tabla de Datos con Filtro por Dispositivo y Paginación")

# Filtro por ID de dispositivo
if "id_dispositivo" in df.columns:
    dispositivos_disponibles_tabla = sorted(df["id_dispositivo"].dropna().unique())
    ids_filtrados = st.multiselect("Filtrar por ID de dispositivo:", dispositivos_disponibles_tabla, default=dispositivos_disponibles_tabla)
    df_filtrado = df[df["id_dispositivo"].isin(ids_filtrados)]
else:
    df_filtrado = df

# Paginación usando selectbox
filas_por_pagina = 50
total_filas = len(df_filtrado)
paginas_totales = max((total_filas - 1) // filas_por_pagina + 1, 1)

# Crear opciones para selectbox
opciones_paginas = [f"Página {i+1}" for i in range(paginas_totales)]
pagina_seleccionada = st.selectbox("Selecciona una página:", opciones_paginas, index=0)
indice_pagina = opciones_paginas.index(pagina_seleccionada)

# Calcular inicio y fin
inicio = indice_pagina * filas_por_pagina
fin = inicio + filas_por_pagina

# Mostrar la tabla paginada
df_pagina = df_filtrado[::-1].iloc[inicio:fin]
st.dataframe(df_pagina, use_container_width=True)

# Info de navegación
st.caption(f"Mostrando registros {inicio + 1} a {min(fin, total_filas)} de {total_filas}")

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
st.subheader("📈 Visualización de Sensores por Dispositivo")

# --- Seleccionar dominio si está disponible ---
if "dominio" in df.columns:
    dominios_unicos = sorted(df["dominio"].dropna().unique())
    dominio_seleccionado_dato = st.selectbox("🌐 Selecciona el dominio del dato:", dominios_unicos)
    df_dominio_ucn = df[df["dominio"] == dominio_seleccionado_dato]
else:
    df_dominio_ucn = df

# --- Selección del ID del dispositivo ---
st.subheader("📟 Selección del Dispositivo")
dispositivos_disponibles = sorted(df_dominio_ucn["id_dispositivo"].dropna().unique())
id_seleccionado = st.selectbox("Selecciona un dispositivo:", dispositivos_disponibles)

# --- Filtrar por el dispositivo seleccionado ---
df_id = df_dominio_ucn[df_dominio_ucn["id_dispositivo"] == id_seleccionado]

# --- BOTÓN DE DESCARGA PARA DATOS FILTRADOS (Dominio, fechas e id) ---
st.download_button(
    label="📥 Descargar datos filtrados",
    data=df_id.to_csv(index=False).encode('utf-8'),
    file_name=f"datos_{dominio_seleccionado}_{id_seleccionado}.csv",
    mime='text/csv'
)

if df_id.empty:
    st.info(f"ℹ️ No hay datos para el dispositivo {id_seleccionado}.")
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
            if var in df_id.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_id["tiempo"], y=df_id[var],
                    mode="lines+markers",
                    name=nombre,
                    line=dict(color=color, width=2),
                    marker=dict(size=6, opacity=0.7)
                ))

                fig.update_layout(
                    title=f"{nombre} - {id_seleccionado}",
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
                st.warning(f"⚠️ No hay datos para la variable '{var}' en {id_seleccionado}.")

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