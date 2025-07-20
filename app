import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🔗 Conexión con Google Sheets
def conectar_hoja():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1-dBx4VTy6vRq10Jneq37QI2dn_KDbBxqKtfDso0W-Wk/edit").worksheet("Jornadas")
    return sheet

# 📥 Cargar datos existentes
def cargar_datos():
    sheet = conectar_hoja()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# 📤 Agregar nueva fila
def agregar_fila_google(fecha, usuario, bodega, hora_inicio, hora_cierre):
    sheet = conectar_hoja()
    fila = [fecha, usuario, bodega, hora_inicio, hora_cierre]
    sheet.append_row(fila)

# 🔐 Login
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.title("🔐 Login de usuario")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if (usuario == "JB" and password == "1234") or (usuario == "Administradr" and password == "Administrador"):
            st.session_state.logueado = True
            st.session_state.usuario = usuario
        else:
            st.error("Credenciales incorrectas")

# 🕘 Página principal de gestión
if st.session_state.logueado and st.session_state.usuario != "Administradr":
    st.title("🕒 Gestión de Jornada")

    fecha_actual = datetime.now().date().strftime("%Y-%m-%d")
    st.text_input("Usuario", value=st.session_state.usuario, disabled=True)
    st.text_input("Fecha", value=fecha_actual, disabled=True)

    bodegas = [
        "Bodega Barrio Cuba", "CEDI Coyol", "Bodega Cañas",
        "Bodega Coto", "Bodega San Carlos", "Bodega Pérez Zeledon"
    ]
    bodega = st.selectbox("Selecciona la bodega", bodegas)

    datos = cargar_datos()
    registro_existente = datos[
        (datos['Usuario'] == st.session_state.usuario) &
        (datos['Fecha'] == fecha_actual)
    ]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📌 Iniciar jornada"):
            hora_actual = datetime.now().strftime("%H:%M:%S")
            if not bodega.strip():
                st.warning("Debes seleccionar una bodega.")
            elif not registro_existente.empty:
                st.warning("Ya registraste el inicio de jornada para hoy.")
            else:
                agregar_fila_google(fecha_actual, st.session_state.usuario, bodega, hora_actual, "")
                st.success(f"Inicio de jornada registrado a las {hora_actual}")
                st.info(f"Usuario: {st.session_state.usuario} | Bodega: {bodega} | Fecha: {fecha_actual} | Hora Inicio: {hora_actual}")

    with col2:
        if st.button("✅ Cerrar jornada"):
            hora_actual = datetime.now().strftime("%H:%M:%S")
            if registro_existente.empty:
                st.warning("Primero debes registrar el inicio de jornada.")
            elif registro_existente.iloc[0]['Hora Cierre'] != "":
                st.warning("Ya cerraste la jornada para hoy.")
            else:
                agregar_fila_google(fecha_actual, st.session_state.usuario, bodega,
                                    registro_existente.iloc[0]['Hora Inicio'], hora_actual)
                st.success(f"Jornada cerrada correctamente a las {hora_actual}")
                st.info(f"Cierre registrado para {st.session_state.usuario} a las {hora_actual}")

    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.clear()
        st.stop()

# 🛠️ Panel de administración
if st.session_state.logueado and st.session_state.usuario == "Administradr":
    st.title("📋 Panel de Administración")

    bodegas = [
        "Bodega Barrio Cuba", "CEDI Coyol", "Bodega Cañas",
        "Bodega Coto", "Bodega San Carlos", "Bodega Pérez Zeledon"
    ]

    datos = cargar_datos()

    bodega_admin = st.selectbox("Filtrar por bodega", ["Todas"] + bodegas)
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=datetime.now().date())
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=datetime.now().date())

    datos_filtrados = datos.copy()
    if bodega_admin != "Todas":
        datos_filtrados = datos_filtrados[datos_filtrados["Bodega"] == bodega_admin]

    datos_filtrados["Fecha"] = pd.to_datetime(datos_filtrados["Fecha"], errors="coerce")
    datos_filtrados = datos_filtrados[
        (datos_filtrados["Fecha"].dt.date >= fecha_inicio) &
        (datos_filtrados["Fecha"].dt.date <= fecha_fin)
    ]

    st.markdown("### 📑 Resultados filtrados")
    if not datos_filtrados.empty:
        st.dataframe(datos_filtrados)

        csv = datos_filtrados.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar resultados en CSV",
            data=csv,
            file_name="jornada_filtrada.csv",
            mime="text/csv"
        )

        st.success(f"Se encontraron {len(datos_filtrados)} registros.")
    else:
        st.info("No hay registros que coincidan con los filtros seleccionados.")

    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.clear()
        st.stop()
