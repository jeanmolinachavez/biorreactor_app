import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from pymongo import MongoClient
from datetime import datetime
import pytz
from PIL import Image
import base64
from io import BytesIO

# --- CREDENCIALES PARA BASE DE DATOS ---
MONGO_URI = st.secrets["MONGO_URI"]

# --- MÉTRICAS ---
def mostrar_metricas(df):
    st.markdown("### 📊 Últimos Valores por Dispositivo")

    if "id_dispositivo" not in df.columns:
        st.warning("⚠️ No se encontraron IDs de dispositivos en los datos.")
        return

    dispositivos = sorted(df["id_dispositivo"].dropna().unique())

    # Obtener dominio actual desde session_state
    dominio_actual = st.session_state.get("dominio_seleccionado", "dominio_ucn")
    clave_estado_ids = f"ids_filtrados_{dominio_actual}"

    # Usar los valores guardados para este dominio o mostrar todos los dispositivos por defecto
    ids_guardados = st.session_state.get(clave_estado_ids, dispositivos)
    ids_validos = [d for d in ids_guardados if d in dispositivos]

    seleccion = st.multiselect(
        "Filtrar por ID de dispositivo:",
        dispositivos,
        default=ids_validos,
        key="multiselect_metricas"
    )

    # Detectar cambios en selección y actualizar estado
    if seleccion != st.session_state.get(clave_estado_ids, []):
        st.session_state[clave_estado_ids] = seleccion
        st.session_state.ids_filtrados = seleccion
        st.rerun()

    df = df[df["id_dispositivo"].isin(st.session_state.get(clave_estado_ids, dispositivos))]

    chile_tz = pytz.timezone("America/Santiago")

    for disp in st.session_state.get(clave_estado_ids, []):
        df_disp = df[df["id_dispositivo"] == disp].sort_values(by="tiempo", ascending=False)
        if df_disp.empty:
            continue

        ultima_fecha = df_disp["tiempo"].iloc[0]
        if ultima_fecha.tzinfo is None:
            ultima_fecha = chile_tz.localize(ultima_fecha)
        else:
            ultima_fecha = ultima_fecha.astimezone(chile_tz)
        tiempo_str = ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')

        st.markdown(f"**🔎 Dispositivo:** `{disp}`  \n🕒 Última medición: `{tiempo_str}`")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🌡️ Temperatura", f"{df_disp['temperatura'].iloc[0]:.2f} °C")
        col2.metric("🌊 pH", f"{df_disp['ph'].iloc[0]:.2f}")
        col3.metric("🧪 Turbidez", f"{df_disp['turbidez'].iloc[0]:.2f} %")
        col4.metric("🫁 Oxígeno", f"{df_disp['oxigeno'].iloc[0]:.2f} %")
        col5.metric("⚡ Conductividad", f"{df_disp['conductividad'].iloc[0]:.2f} ppm")

        st.markdown("---")

# --- TABLA DE SENSORES ---
def mostrar_tabla(df):
    st.subheader("📋 Reporte de Sensores")

    if "id_dispositivo" in df.columns:
        dispositivos = sorted(df["id_dispositivo"].dropna().unique())

        # Inicializar estado si no existe
        if "ids_filtrados" not in st.session_state:
            st.session_state.ids_filtrados = dispositivos

        # Mostrar selector multiselect con el estado actual
        seleccion = st.multiselect(
            "Filtrar por ID de dispositivo:",
            dispositivos,
            default=st.session_state.ids_filtrados,
            key="multiselect_tabla"
        )

        # Detectar cambios y actualizar sesión
        if seleccion != st.session_state.ids_filtrados:
            st.session_state.ids_filtrados = seleccion
            st.rerun()

        df_filtrado = df[df["id_dispositivo"].isin(st.session_state.ids_filtrados)]
    else:
        df_filtrado = df

    # --- Botón de descarga para todos los datos filtrados (sin paginar)
    if not df_filtrado.empty:
        csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
        ids_str = "_".join(st.session_state.ids_filtrados)
        nombre_archivo = f"datos_{ids_str}.csv"
        st.download_button(
            label="📥 Descargar datos filtrados (todos)",
            data=csv_data,
            file_name=nombre_archivo,
            mime="text/csv"
        )

    # --- Paginación ---
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
def mostrar_registro_comida(registros, dominio_seleccionado):
    st.subheader("🍽️ Registro de Alimentación")

    # --- Mostrar botón para registrar alimentación ---
    dispositivos = []
    try:
        client = MongoClient(MONGO_URI)
        db = client["biorreactor_app"]
        collection = db[dominio_seleccionado]
        dispositivos = collection.distinct("id_dispositivo")
        dispositivos = sorted([d for d in dispositivos if d])
    except Exception as e:
        st.error(f"❌ Error al obtener dispositivos del dominio '{dominio_seleccionado}': {e}")

    if dispositivos:
        dispositivo_seleccionado = st.selectbox("Selecciona el dispositivo alimentado:", dispositivos)

        if st.button("🍽️ Registrar alimentación"):
            response = requests.post(
                "https://biorreactor-app-api.onrender.com/api/registro_comida",
                json={"evento": "comida", "id_dispositivo": dispositivo_seleccionado}
            )
            if response.status_code == 201:
                st.success("✅ Alimentación registrada correctamente.")
                st.rerun()
            else:
                st.error("❌ Error al registrar la alimentación.")
    else:
        st.info("ℹ️ No hay dispositivos disponibles para registrar alimentación en este dominio.")

    # --- Mostrar historial de alimentación ---
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
            with st.expander("📄 Ver historial de alimentación por dispositivo", expanded=True):
                if "id_dispositivo" in df_comida.columns:
                    df_ordenado = df_comida.sort_values("tiempo", ascending=False)
                    df_ordenado["tiempo"] = df_ordenado["tiempo"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    st.dataframe(df_ordenado[["tiempo", "id_dispositivo"]], use_container_width=True)
                else:
                    st.warning("⚠️ Los registros no tienen el campo 'id_dispositivo'.")
    else:
        st.info("ℹ️ No hay registros de alimentación aún.")

# --- GRAFICOS ---
def mostrar_graficos(df):
    st.subheader("📈 Visualización de Sensores por Dispositivo")

    dispositivos = sorted(df["id_dispositivo"].dropna().unique())
    if not dispositivos:
        st.info("ℹ️ No hay dispositivos disponibles para el dominio y rango de fecha seleccionados.")
        return

    # Inicializar estado si no existe
    if "dispositivo_seleccionado" not in st.session_state or st.session_state.dispositivo_seleccionado not in dispositivos:
        st.session_state.dispositivo_seleccionado = dispositivos[0]

    # Mostrar selector selectbox con el estado actual
    id_seleccionado = st.selectbox(
        "Selecciona un dispositivo:",
        dispositivos,
        index=dispositivos.index(st.session_state.dispositivo_seleccionado),
        key="selectbox_graficos"
    )

    # Detectar cambios y actualizar sesión
    if id_seleccionado != st.session_state.dispositivo_seleccionado:
        st.session_state.dispositivo_seleccionado = id_seleccionado
        st.rerun()

    df_id = df[df["id_dispositivo"] == st.session_state.dispositivo_seleccionado]

    # Botón para descargar datos de dispositivo filtrado
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
            chile_tz = pytz.timezone("America/Santiago")
            tiempo_chile = doc["tiempo"].replace(tzinfo=pytz.utc).astimezone(chile_tz)
            tiempo_str = tiempo_chile.strftime('%Y-%m-%d %H:%M:%S')
            cols[idx].image(imagen, caption=f"Capturada el {tiempo_str}", use_container_width=True)
