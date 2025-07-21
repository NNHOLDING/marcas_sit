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

# 🔧 Función de redondeo de hora
def redondear_hora(hora_str):
    hora = datetime.strptime(hora_str, "%H:%M:%S")
    minutos = hora.minute
    if minutos <= 5:
        redondeada = hora.replace(minute=0, second=0)
    else:
        redondeada = hora.replace(minute=30, second=0)
    return redondeada.strftime("%H:%M:%S")

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
        return pd.DataFrame(columns=[
            "fecha", "usuario", "bodega", "hora inicio", "fecha cierre",
            "Redondeo Inicio", "Redondeo Fin", "jornada",
            "total horas extras", "terminal"
        ])
    encabezados = [col.lower().strip() for col in registros[0]]
    filas = registros[1:]
    return pd.DataFrame(filas, columns=encabezados)

# 📌 Agregar fila al iniciar jornada con redondeo
def agregar_fila_inicio(fecha, usuario, bodega, hora_inicio):
    redondeo_inicio = redondear_hora(hora_inicio)
    conectar_hoja().append_row([
        fecha, usuario, bodega, hora_inicio,
        "", redondeo_inicio, "", "", "", ""
    ])

# ✅ Actualizar campo 'fecha cierre' y 'redondeo fin'
def actualizar_fecha_cierre(fecha, usuario, bodega, fecha_cierre):
    sheet = conectar_hoja()
    registros = sheet.get_all_values()
    encabezados = [col.lower().strip() for col in registros[0]]
    if "fecha cierre" not in encabezados or "redondeo fin" not in encabezados:
        return False
    for idx, fila in enumerate(registros[1:], start=2):
        fila_dict = dict(zip(encabezados, fila))
        if (fila_dict.get("fecha") == fecha and
            fila_dict.get("usuario") == usuario and
            fila_dict.get("bodega") == bodega and
            not fila_dict.get("fecha cierre")):
            col_fecha_idx = encabezados.index("fecha cierre") + 1
            col_redondeo_idx = encabezados.index("redondeo fin") + 1
            redondeo_fin = redondear_hora(fecha_cierre)
            sheet.update_cell(idx, col_fecha_idx, fecha_cierre)
            sheet.update_cell(idx, col_redondeo_idx, redondeo_fin)
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

# 🕒 Panel de gestión de jornada
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

    columnas = list(datos_filtrados.columns)
    duplicadas = [col for col in columnas if columnas.count(col) > 1]

    if duplicadas:
        st.error(f"🚫 Columnas duplicadas detectadas: {duplicadas}. Verifica los encabezados en Google Sheets.")
    elif datos_filtrados.empty:
        st.info("No hay registros para los filtros seleccionados.")
    else:
        st.dataframe(datos_filtrados)
        csv = datos_filtrados.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv, "jornadas_filtradas.csv", "text/csv")
        st.success(f"Se encontraron {len(datos_filtrados)} registros.")

    st.markdown("---")

    st.markdown("### 🔄 Aplicar cálculos de jornada y horas extras")

    # 🧮 Cálculo de jornada y horas extras
    def aplicar_calculos_masivos():
        sheet = conectar_hoja()
        registros = sheet.get_all_values()
        encabezados = [col.lower().strip() for col in registros[0]]

        try:
            libro = sheet.spreadsheet
            bd_sheet = libro.worksheet("BD")
            bd_valores = bd_sheet.get_all_records()
            jornada_dict = {
                fila["Hora"].strip(): float(fila["Jornada"]) for fila in bd_valores
                if "Hora" in fila and "Jornada" in fila
            }
        except Exception:
            st.error("❌ No se pudo acceder a la hoja 'BD'. Verifica que existe en el mismo libro y que contiene las columnas 'Hora' y 'Jornada'.")
            return

        registros_actualizados = 0

        for idx, fila in enumerate(registros[1:], start=2):
            fila_dict = dict(zip(encabezados, fila))
            inicio = fila_dict.get("redondeo inicio", "").strip()
            fin = fila_dict.get("redondeo fin", "").strip()

            if not inicio or not fin:
                continue

            try:
                t_inicio = datetime.strptime(inicio, "%H:%M:%S")
                t_fin = datetime.strptime(fin, "%H:%M:%S")
                if t_fin < t_inicio:
                    t_fin += pd.Timedelta(days=1)

                duracion = (t_fin - t_inicio).total_seconds() / 3600
                jornada_esperada = jornada_dict.get(inicio, 0)
                extras = duracion - jornada_esperada

                jornada_str = f"{int(duracion // 1):02}:{int((duracion % 1) * 60):02}"
                extras_str = f"{int(extras * 1000)}" if extras > 0 else "0"

                sheet.update_cell(idx, encabezados.index("jornada") + 1, jornada_str)
                sheet.update_cell(idx, encabezados.index("total horas extras") + 1, extras_str)

                registros_actualizados += 1

            except Exception:
                continue

        st.success(f"✅ Se aplicaron cálculos correctamente a {registros_actualizados} registros con redondeos disponibles.")

    if st.button("⚙️ Calcular jornada y horas extras"):
        aplicar_calculos_masivos()   
    # 📊 Historial de Horas Extras
    st.markdown("## 📊 Historial de Horas Extras")
    datos_historial = cargar_datos()
    columna_horas_extras = "total horas extras"

    if columna_horas_extras not in datos_historial.columns:
        st.warning("⚠️ La hoja no contiene una columna llamada 'Total horas extras'.")
    else:
        datos_historial[columna_horas_extras] = pd.to_numeric(
            datos_historial[columna_horas_extras], errors="coerce"
        )
        datos_historial = datos_historial.dropna(subset=[columna_horas_extras, "usuario", "bodega"])

        bodegas_disp = sorted(datos_historial["bodega"].unique().tolist())
        usuarios_disp = sorted(datos_historial["usuario"].unique().tolist())

        bodega_hist = st.selectbox("Filtrar por bodega (Historial)", ["Todas"] + bodegas_disp)
        usuario_hist = st.selectbox("Filtrar por usuario (Historial)", ["Todos"] + usuarios_disp)

        df_filtrado = datos_historial.copy()
        if bodega_hist != "Todas":
            df_filtrado = df_filtrado[df_filtrado["bodega"] == bodega_hist]
        if usuario_hist != "Todos":
            df_filtrado = df_filtrado[df_filtrado["usuario"] == usuario_hist]

        resumen = (
            df_filtrado.groupby("usuario")[columna_horas_extras]
            .sum()
            .reset_index()
            .dropna(subset=[columna_horas_extras])
        )
        resumen = resumen[resumen[columna_horas_extras] > 0]

        if resumen.empty:
            st.info("ℹ️ No hay horas extras registradas según los filtros seleccionados.")
        else:
            st.markdown("### 📈 Horas Extras por Usuario")
            st.bar_chart(resumen.set_index("usuario"))

    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.confirmar_salida = True
