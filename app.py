import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [col.lower() for col in df.columns]
    return df

# 📤 Agregar nueva fila
def agregar_fila_inicio(fecha, usuario, bodega, hora_inicio):
    sheet = conectar_hoja()
    fila = [fecha, usuario, bodega, hora_inicio, ""]
    sheet.append_row(fila)

# ✏️ Actualizar hora de cierre en fila existente
def actualizar_hora_cierre(fecha, usuario, bodega, hora_cierre):
    sheet = conectar_hoja()
    registros = sheet.get_all_values()
    encabezados = [col.lower() for col in registros[0]]
    for idx, fila in enumerate(registros[1:], start=2):
        fila_dict = dict(zip(encabezados, fila))
        if (fila_dict.get("fecha") == fecha and
            fila_dict.get("usuario") == usuario and
            fila_dict.get("bodega") == bodega and
            not fila_dict.get("hoa cierre")):
            col_idx = encabezados.index("hoa cierre") + 1
            sheet.update_cell(idx, col_idx, hora_cierre)
            return True
    return False

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

# 🕘 Página de gestión regular
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

    if datos.empty:
        st.warning("📂 La hoja está vacía. Puedes registrar tu jornada.")
        datos = pd.DataFrame(columns=["fecha", "usuario", "bodega", "hora inicio", "hoa cierre"])

    registro_existente = datos[
        (datos['usuario'] == st.session_state.usuario) &
        (datos['fecha'] == fecha_actual) &
        (datos['bodega'] == bodega)
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
                agregar_fila_inicio(fecha_actual, st.session_state.usuario, bodega, hora_actual)
                st.success(f"Inicio de jornada registrado a las {hora_actual}")
                st.info(f"Usuario: {st.session_state.usuario} | Bodega: {bodega} | Fecha: {fecha_actual}")

    with col2:
        if st.button("✅ Cerrar jornada"):
            hora_actual = datetime.now().strftime("%H:%M:%S")
            if registro_existente.empty:
                st.warning("Primero debes registrar el inicio de jornada.")
            elif registro_existente.iloc[0].get("hoa cierre", "") != "":
                st.warning("Ya cerraste la jornada para hoy.")
            else:
                actualizado = actualizar_hora_cierre(fecha_actual, st.session_state.usuario, bodega, hora_actual)
                if actualizado:
                    st.success(f"Jornada cerrada correctamente a las {hora_actual}")
                    st.info(f"Cierre registrado para {st.session_state.usuario} a las {hora_actual}")
                else:
                    st.error("No se pudo actualizar la hora de cierre. Verifica los datos.")

    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.clear()
        st.stop()
