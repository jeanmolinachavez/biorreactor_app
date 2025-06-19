import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
from PIL import Image
import base64
from io import BytesIO

def a_hora_chile(dt_utc):
    chile_tz = pytz.timezone('America/Santiago')
    return dt_utc.replace(tzinfo=pytz.utc).astimezone(chile_tz)

# --- MÉTRICAS ---
def mostrar_metricas(df):
    st.markdown("### 📊 Últimos Valores de Sensores")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🌡️ Temperatura", f"{df['temperatura'].iloc[-1]:.2f} °C")
    col2.metric("🌊 pH", f"{df['ph'].iloc[-1]:.2f}")
    col3.metric("🧪 Turbidez", f"{df['turbidez'].iloc[-1]:.2f} %")
    col4.metric("🫁 Oxígeno", f"{df['oxigeno'].iloc[-1]:.2f} %")
    col5.metric("⚡ Conductividad", f"{df['conductividad'].iloc[-1]:.2f} ppm")

# --- TABLA DE SENSORES ---
def mostrar_tabla(df):
    st.subheader("📋 Reporte de Sensores")

    if "id_dispositivo" in df.columns:
        dispositivos = sorted(df["id_dispositivo"].dropna().unique())
        ids_filtrados = st.multiselect("Filtrar por ID de dispositivo:", dispositivos, default=dispositivos)
        df_filtrado = df[df["id_dispositivo"].isin(ids_filtrados)]
    else:
        df_filtrado = df

    filas_por_pagina = 250
    total_filas = len(df_filtrado)
    paginas_totales = max((total_filas - 1) // filas_por_pagina + 1, 1)

    if "pagina_actual" not in st.session_state:
        st.session_state.pagina_actual = 0

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Anterior") and st.session_state.pagina_actual > 0:
            st.session_state.pagina_actual -= 1
    with col3:
        if st.button("Siguiente ➡️") and st.session_state.pagina_actual < paginas_totales - 1:
            st.session_state.pagina_actual += 1
    with col2:
        st.markdown(f"<div style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_actual + 1} de {paginas_totales}</div>", unsafe_allow_html=True)

    inicio = st.session_state.pagina_actual * filas_por_pagina
    fin = inicio + filas_por_pagina
    df_pagina = df_filtrado[::-1].iloc[inicio:fin]
    st.dataframe(df_pagina, use_container_width=True)
    st.caption(f"Mostrando registros {inicio + 1} a {min(fin, total_filas)} de {total_filas}")

# --- REGISTRO DE ALIMENTACIÓN ---
def mostrar_registro_comida(registros):
    st.subheader("🍽️ Registro de Alimentación")
    if registros:
        df_comida = pd.DataFrame(registros)
        df_comida["tiempo"] = pd.to_datetime(df_comida["tiempo"])

        col1, col2 = st.columns([1, 2])

        with col1:
            ultima_fecha = df_comida["tiempo"].max()
            ultima_fecha_str = ultima_fecha.strftime("%Y-%m-%d %H:%M:%S")
            st.info(f"🍽️ Última alimentación:\n**{ultima_fecha_str}**")

            ahora_chile = datetime.now(pytz.timezone('America/Santiago'))
            dias_sin_alimentar = (ahora_chile.date() - ultima_fecha.date()).days

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

# --- GRAFICOS ---
def mostrar_graficos(df):
    st.subheader("📈 Visualización de Sensores por Dispositivo")

    dispositivos = sorted(df["id_dispositivo"].dropna().unique())
    if not dispositivos:
        st.info("ℹ️ No hay dispositivos disponibles para el dominio y rango de fecha seleccionados.")
        return

    id_seleccionado = st.selectbox("Selecciona un dispositivo:", dispositivos)
    df_id = df[df["id_dispositivo"] == id_seleccionado]

    st.download_button(
        label="📥 Descargar datos filtrados",
        data=df_id.to_csv(index=False).encode('utf-8'),
        file_name=f"datos_{id_seleccionado}.csv",
        mime='text/csv'
    )

    variables = {
        "temperatura": ("🌡️ Temperatura", "°C", "red"),
        "ph": ("🌊 pH", "pH", "purple"),
        "oxigeno": ("🫁 Oxígeno", "%", "green"),
        "turbidez": ("🧪 Turbidez", "%", "blue"),
        "conductividad": ("⚡ Conductividad", "ppm", "orange"),
    }

    tab_labels = list([nombre for (nombre, _, _) in variables.values()])
    tab_labels.append("📊 Comparación múltiple")
    tabs = st.tabs(tab_labels)

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
                fig.update_layout(title=f"{nombre} - {id_seleccionado}", xaxis_title="Tiempo", yaxis_title=unidad, height=400)
                fig.update_xaxes(tickformat="%d-%m %H:%M", tickangle=45)
                fig.update_yaxes(showgrid=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"⚠️ No hay datos para '{var}' en {id_seleccionado}.")

    with tabs[-1]:
        st.markdown("### 🔍 Comparación múltiple de dispositivos")
        seleccionados = st.multiselect("Selecciona dispositivos:", dispositivos, default=dispositivos[:2])
        var_multi = st.selectbox("Variable a visualizar:", list(variables.keys()), format_func=lambda x: variables[x][0])

        if seleccionados and var_multi:
            fig = go.Figure()
            for disp in seleccionados:
                df_disp = df[df["id_dispositivo"] == disp]
                fig.add_trace(go.Scatter(
                    x=df_disp["tiempo"], y=df_disp[var_multi],
                    mode="lines+markers", name=disp
                ))
            fig.update_layout(
                title=f"Comparación de {variables[var_multi][0]} entre múltiples dispositivos",
                xaxis_title="Tiempo", yaxis_title=variables[var_multi][1], height=450)
            fig.update_xaxes(tickformat="%d-%m %H:%M", tickangle=45)
            fig.update_yaxes(showgrid=True)
            st.plotly_chart(fig, use_container_width=True)

# --- IMÁGENES ---
def mostrar_imagenes(documentos):
    st.subheader("🖼️ Últimas Imágenes Capturadas")

    cols = st.columns(len(documentos))
    for idx, doc in enumerate(documentos):
        if 'imagen' in doc and 'tiempo' in doc:
            imagen_bytes = base64.b64decode(doc['imagen'])
            imagen = Image.open(BytesIO(imagen_bytes))
            tiempo_str = a_hora_chile(doc['tiempo']).strftime('%Y-%m-%d %H:%M:%S')
            cols[idx].image(imagen, caption=f"Capturada el {tiempo_str}", use_container_width=True)
