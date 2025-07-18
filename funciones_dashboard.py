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

# --- FILTRO GLOBAL DE DISPOSITIVOS ---
def mostrar_filtro_global(df, dominio_actual):
    dispositivos = sorted(df["id_dispositivo"].dropna().unique())
    clave_ids = f"ids_filtrados_{dominio_actual}"
    clave_checkbox = f"checkbox_todos_{dominio_actual}"

    # Inicializar session_state
    if clave_ids not in st.session_state:
        st.session_state[clave_ids] = dispositivos.copy()
    if clave_checkbox not in st.session_state:
        st.session_state[clave_checkbox] = True  # Por defecto todo seleccionado

    with st.sidebar.expander("🔎 Filtro global de dispositivos", expanded=True):
        checkbox_val = st.checkbox(
            "Seleccionar todos",
            value=st.session_state[clave_checkbox],
            key=f"checkbox_todos_widget_{dominio_actual}"
        )

        if checkbox_val != st.session_state[clave_checkbox]:
            st.session_state[clave_checkbox] = checkbox_val
            if checkbox_val:
                st.session_state[clave_ids] = dispositivos.copy()
            else:
                st.session_state[clave_ids] = []
            st.rerun()

        seleccion = st.multiselect(
            "Selecciona dispositivos:",
            dispositivos,
            default=st.session_state[clave_ids],
            key=f"multiselect_global_{dominio_actual}"
        )

        if set(seleccion) != set(st.session_state[clave_ids]):
            st.session_state[clave_ids] = seleccion
            if set(seleccion) == set(dispositivos):
                st.session_state[clave_checkbox] = True
            elif len(seleccion) == 0:
                st.session_state[clave_checkbox] = False
            else:
                st.session_state[clave_checkbox] = False
            st.rerun()

    return st.session_state[clave_ids]

# --- MÉTRICAS ---
def mostrar_metricas(df):
    st.markdown("### 📊 Últimos Valores por Dispositivo")

    if "id_dispositivo" not in df.columns:
        st.warning("⚠️ No se encontraron IDs de dispositivos en los datos.")
        return

    dominio_actual = st.session_state.get("dominio_seleccionado", "dominio_ucn")
    clave_estado_ids = f"ids_filtrados_{dominio_actual}"
    # Obtener lista original ordenada alfabéticamente
    dispositivos_ordenados = sorted(df["id_dispositivo"].dropna().unique())

    # Obtener ids filtrados o por defecto toda la lista ordenada
    ids_filtrados = st.session_state.get(clave_estado_ids, dispositivos_ordenados)

    # Ordenar ids_filtrados manteniendo el orden alfabético original
    ids_filtrados_ordenados = [d for d in dispositivos_ordenados if d in ids_filtrados]

    df_filtrado = df[df["id_dispositivo"].isin(ids_filtrados_ordenados)]
    chile_tz = pytz.timezone("America/Santiago")

    for disp in ids_filtrados_ordenados:
        df_disp = df_filtrado[df_filtrado["id_dispositivo"] == disp].sort_values(by="tiempo", ascending=False)
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

# --- REPORTE DE SENSORES ---
def mostrar_reporte(df):
    st.subheader("📋 Reporte de Sensores")

    if "id_dispositivo" in df.columns:
        dispositivos = sorted(df["id_dispositivo"].dropna().unique())

        # Obtener dominio actual desde session_state
        dominio_actual = st.session_state.get("dominio_seleccionado", "dominio_ucn")
        clave_estado_ids = f"ids_filtrados_{dominio_actual}"

        ids_filtrados = st.session_state.get(clave_estado_ids, dispositivos)
        df_filtrado = df[df["id_dispositivo"].isin(ids_filtrados)]
    else:
        df_filtrado = df

    # --- Botón de descarga para todos los datos filtrados (sin paginar)
    if not df_filtrado.empty:
        csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
        ids_str = "_".join(st.session_state.get(clave_estado_ids, []))
        nombre_archivo = f"datos_{ids_str}.csv"
        st.download_button(
            label="📥 Descargar datos filtrados de los dispositivos",
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
def mostrar_registro_comida(registros, dominio_seleccionado, ids_filtrados=None):
    st.subheader("🍽️ Registro de Alimentación")

    if ids_filtrados is None:
        ids_filtrados = []

    # --- Mostrar historial colapsado ---
    if registros:
        with st.expander("📄 Historial de alimentación por dispositivo"):
            df_comida = pd.DataFrame(registros)
            df_comida = df_comida[df_comida["id_dispositivo"].isin(ids_filtrados)]
            df_comida["tiempo"] = pd.to_datetime(df_comida["tiempo"])
            df_ordenado = df_comida.sort_values("tiempo", ascending=False)
            df_ordenado["tiempo"] = df_ordenado["tiempo"].dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(df_ordenado[["tiempo", "id_dispositivo"]], use_container_width=True)
    else:
        st.info("ℹ️ No hay registros de alimentación aún.")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client["biorreactor_app"]
        collection = db[dominio_seleccionado]
        dispositivos_db = collection.distinct("id_dispositivo")
        dispositivos_ordenados = sorted([d for d in dispositivos_db if d and d in ids_filtrados])
    except Exception as e:
        st.error(f"❌ Error al obtener dispositivos del dominio '{dominio_seleccionado}': {e}")
        return

    if not dispositivos_ordenados:
        st.info("ℹ️ No hay dispositivos disponibles para registrar alimentación en este dominio.")
        return

    st.markdown("### 📋 Estado actual de alimentación por dispositivo")
    ahora_chile = datetime.now(pytz.timezone("America/Santiago"))

    for dispositivo in dispositivos_ordenados:
        registros_dispositivo = [r for r in registros if r["id_dispositivo"] == dispositivo]
        if registros_dispositivo:
            ultimo = max(registros_dispositivo, key=lambda x: x["tiempo"])
            ultima_fecha = pd.to_datetime(ultimo["tiempo"])
            dias_sin_alimentar = (ahora_chile.date() - ultima_fecha.date()).days
            ultima_str = ultima_fecha.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ultima_str = "Sin registros"
            dias_sin_alimentar = None

        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])
            col1.markdown(f"**🆔 Nombre de dispositivo:**<br>{dispositivo}", unsafe_allow_html=True)
            col2.markdown(f"**📅 Última alimentación:**<br>{ultima_str}", unsafe_allow_html=True)

            if dias_sin_alimentar is None:
                mensaje = "⚪ Sin registros"
                color = "gray"
            elif dias_sin_alimentar == 0:
                mensaje = "🟢 Hoy se alimentó"
                color = "green"
            elif dias_sin_alimentar <= 2:
                mensaje = f"🟡 {dias_sin_alimentar} día(s) sin alimentar"
                color = "orange"
            else:
                mensaje = f"🔴 {dias_sin_alimentar} días sin alimentar"
                color = "red"

            col3.markdown(f"**⏱️ Días sin alimentar:**<br><span style='color:{color}'>{mensaje}</span>", unsafe_allow_html=True)

            with col4:
                if st.button("🍽️ Alimentar", key=f"alimentar_{dispositivo}"):
                    response = requests.post(
                        "https://biorreactor-app-api.onrender.com/api/registro_comida",
                        json={"evento": "comida", "id_dispositivo": dispositivo}
                    )
                    if response.status_code == 201:
                        st.success(f"✅ Alimentación registrada para {dispositivo}.")
                        st.rerun()
                    else:
                        st.error(f"❌ Error al registrar para {dispositivo}")

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
        label="📥 Descargar datos filtrados del dispositivo",
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

# --- REGISTRO MANUAL ---
def mostrar_registro_manual():
    st.subheader("✍️ Registro Manual de Variables")

    dominio_actual = st.session_state.get("dominio_seleccionado", "dominio_ucn")
    ids = st.session_state.get(f"ids_filtrados_{dominio_actual}", [])

    if not ids:
        st.warning("⚠️ No hay dispositivos seleccionados para registrar manualmente.")
        return

    dispositivo = st.selectbox("📟 Selecciona un dispositivo:", ids)
    st.markdown("---")

    with st.form("form_manual"):
        col1, col2 = st.columns(2)

        with col1:
            temperatura = st.text_input("🌡️ Temperatura (°C)", key="manual_temp")
            ph = st.text_input("🌊 pH", key="manual_ph")
            turbidez = st.text_input("🧪 Turbidez (%)", key="manual_turbidez")

        with col2:
            oxigeno = st.text_input("🫁 Oxígeno (%)", key="manual_oxigeno")
            conductividad = st.text_input("⚡ Conductividad (ppm)", key="manual_conduct")

        enviado = st.form_submit_button("📩 Enviar registro")

    if enviado:
        data = {
            "dominio": dominio_actual,
            "id_dispositivo": dispositivo,
            "temperatura": float(temperatura) if temperatura else None,
            "ph": float(ph) if ph else None,
            "turbidez": float(turbidez) if turbidez else None,
            "oxigeno": float(oxigeno) if oxigeno else None,
            "conductividad": float(conductividad) if conductividad else None
        }

        response = requests.post("https://biorreactor-app-api.onrender.com/api/registro_manual", json=data)

        if response.status_code == 201:
            st.success("✅ Registro manual enviado correctamente.")
        else:
            st.error(f"❌ Error al registrar manualmente: {response.text}")
