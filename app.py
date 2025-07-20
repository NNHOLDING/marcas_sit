import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🎛️ Configuración de la aplicación
st.set_page_config(
    page_title="Smart Intelligence Tools",
    page_icon="https://raw.githubusercontent.com/NNHOLDING/marcas_sit/main/NN25.ico",
    layout="centered"
)

# 🕘 Hora local Costa Rica
cr_timezone = pytz.timezone("America/Costa_Rica")

# 🔗 Conexión con Google Sheets
def conectar_hoja():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1-dBx4VTy6vRq10Jneq37QI2dn_KDbBxqKtfDso0W-Wk/edit"
    ).worksheet("Jornadas")
    return sheet

# 📥 Cargar datos existentes
def cargar_datos():
    sheet = conectar_hoja()
    registros = sheet.get_all_values()

    if len(registros) < 2:
        return pd.DataFrame(columns=["fecha", "usuario", "bodega", "hora inicio", "fecha cierre"])

    encabezados = [col.lower().strip() for col in registros[0]]
    filas = registros[1:]
    return pd.DataFrame(filas, columns=encabezados)

# 📌 Agregar fila al iniciar jornada
def agregar_fila_inicio(fecha, usuario, bodega, hora_inicio):
    conectar_hoja().append_row([fecha, usuario, bodega, hora_inicio, ""])

# ✅ Actualizar campo 'fecha cierre'
def actualizar_fecha_cierre(fecha, usuario, bodega, fecha_cierre):
    sheet = conectar_hoja()
    registros = sheet.get_all_values()
    encabezados = [col.lower().strip() for col in registros[0]]

    if "fecha cierre" not in encabezados:
        return False

    for idx, fila in enumerate(registros[1:], start=2):
        fila_dict = dict(zip(encabezados, fila))
        if (fila_dict.get("fecha") == fecha and
            fila_dict.get("usuario") == usuario and
            fila_dict.get("bodega") == bodega and
            not fila_dict.get("fecha cierre")):
            col_idx = encabezados.index("fecha cierre") + 1
            sheet.update_cell(idx, col_idx, fecha_cierre)
            return True
    return False

# 🔐 Estado de sesión
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'confirmar_salida' not in st.session_state:
    st.session_state.confirmar_salida = False

# 🔐 Login
if not st.session_state.logueado:
    st.title("🔐 Login de usuario")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if (usuario == "JB" and password == "1234") or (usuario == "Administrador" and password == "Administrador"):
            st.session_state.logueado = True
            st.session_state.usuario = usuario
        else:
            st.error("Credenciales incorrectas")

# 🖼️ Logo institucional
if st.session_state.logueado and not st.session_state.confirmar_salida:
    st.markdown(
        "<div style='text-align: center;'>"
        "<img src='https://raw.githubusercontent.com/NNHOLDING/marcas_sit/main/logotipoNN.PNG' width='250'>"
        "</div>",
        unsafe_allow_html=True
    )

# 🕒 Panel de gestión de jornada (usuario)
if st.session_state.logueado and st.session_state.usuario != "Administrador" and not st.session_state.confirmar_salida:
    st.title("🕒 Gestión de Jornada")

    now_cr = datetime.now(cr_timezone)
    fecha_actual = now_cr.strftime("%Y-%m-%d")
    hora_actual = now_cr.strftime("%H:%M:%S")

    st.text_input("Usuario", value=st.session_state.usuario, disabled=True)
    st.text_input("Fecha", value=fecha_actual, disabled=True)

    bodegas = [
        "Bodega Barrio Cuba", "CEDI Coyol", "Bodega Cañas",
        "Bodega Coto", "Bodega San Carlos", "Bodega Pérez Zeledon"
    ]
    bodega = st.selectbox("Selecciona la bodega", bodegas)
    datos = cargar_datos()

    registro_existente = datos[
        (datos["usuario"] == st.session_state.usuario) &
        (datos["fecha"] == fecha_actual) &
        (datos["bodega"] == bodega)
    ]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📌 Iniciar jornada"):
            if not bodega.strip():
                st.warning("Debes seleccionar una bodega.")
            elif not registro_existente.empty:
                st.warning("Ya registraste el inicio de jornada para hoy.")
            else:
                agregar_fila_inicio(fecha_actual, st.session_state.usuario, bodega, hora_actual)
                st.success(f"Inicio registrado a las {hora_actual}")

    with col2:
        if st.button("✅ Cerrar jornada"):
            if registro_existente.empty:
                st.warning("Debes iniciar jornada antes de cerrarla.")
            elif registro_existente.iloc[0].get("fecha cierre", "") != "":
                st.warning("Ya has cerrado la jornada de hoy.")
            else:
                if actualizar_fecha_cierre(fecha_actual, st.session_state.usuario, bodega, hora_actual):
                    st.success(f"Jornada cerrada correctamente a las {hora_actual}")
                else:
                    st.error("No se pudo registrar el cierre.")

    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.confirmar_salida = True

# 📋 Panel administrativo
if st.session_state.logueado and st.session_state.usuario == "Administrador" and not st.session_state.confirmar_salida:
    st.title("📋 Panel Administrativo")
    st.info("Bienvenido, Administrador. Puedes filtrar, visualizar y descargar los registros.")

    datos = cargar_datos()

    bodegas = [
        "Bodega Barrio Cuba", "CEDI Coyol", "Bodega Cañas",
        "Bodega Coto", "Bodega San Carlos", "Bodega Pérez Zeledon"
    ]
    bodega_admin = st.selectbox("Filtrar por bodega", ["Todas"] + bodegas)

    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=datetime.now(cr_timezone).date())
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=datetime.now(cr_timezone).date())

    datos_filtrados = datos.copy()
    if bodega_admin != "Todas":
        datos_filtrados = datos_filtrados[datos_filtrados["bodega"] == bodega_admin]

    datos_filtrados["fecha"] = pd.to_datetime(datos_filtrados["fecha"], errors="coerce")
    datos_filtrados = datos_filtrados[
        (datos_filtrados["fecha"].dt.date >= fecha_inicio) &
        (datos_filtrados["fecha"].dt.date <= fecha_fin)
    ]

    st.markdown("### 📑 Resultados filtrados")
    if not datos_filtrados.empty:
        st.dataframe(datos_filtrados)
        csv = datos_filtrados.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv, "jornadas_filtradas.csv", "text/csv")
        st.success(f"Se encontraron {len(datos_filtrados)} registros.")
    else:
        st.info("No hay registros para los filtros seleccionados.")

    st.markdown("---")
        # 🗂️ Submenú: Historial de horas extras
    st.markdown("## 📊 Historial de Horas Extras")

    datos_historial = cargar_datos()

    if "total horas extras" not in datos_historial.columns:
        st.warning("La hoja no contiene una columna llamada 'Total horas extras'.")
    else:
        datos_historial["total horas extras"] = pd.to_numeric(datos_historial["total horas extras"], errors="coerce")

        bodega_opciones = datos_historial["bodega"].dropna().unique().tolist()
        usuario_opciones = datos_historial["usuario"].dropna().unique().tolist()

        bodega_hist = st.selectbox("Filtrar por bodega", ["Todas"] + bodega_opciones)
        usuario_hist = st.selectbox("Filtrar por usuario", ["Todos"] + usuario_opciones)

        df_filtrado = datos_historial.copy()
        if bodega_hist != "Todas":
            df_filtrado = df_filtrado[df_filtrado["bodega"] == bodega_hist]
        if usuario_hist != "Todos":
            df_filtrado = df_filtrado[df_filtrado["usuario"] == usuario_hist]

        resumen = df_filtrado.groupby("usuario")["total horas extras"].sum().reset_index()

        if resumen.empty:
            st.info("No hay datos para mostrar según los filtros seleccionados.")
        else:
            st.markdown("### 📈 Horas Extras por Usuario")
            st.bar_chart(resumen.set_index("usuario"))
    if st.button("🚪 Salir"):
        st.session_state.confirmar_salida = True

# 🌤️ Confirmación de salida y mensaje de despedida
if st.session_state.confirmar_salida:
    st.markdown("## ¿Estás seguro que deseas cerrar sesión?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sí, cerrar sesión"):
            st.success("¡Hasta pronto! 👋 La sesión se ha cerrado correctamente.")
            st.session_state.clear()
            st.stop()
    with col2:
        if st.button("↩️ No, regresar"):
            st.session_state.confirmar_salida = False
