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
        "<img src='https://raw.githubusercontent.com/NNHOLDING/marcas_sit/main/28NN.PNG.jpg' width='250'>"
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
        datos_filtrados = datos_filtrados[datos_filtrados["Bodega"] == bodega_admin]

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

        # 🏅 Ranking de horas extras por usuario
        st.markdown("---")
        st.markdown("### 📊 Ranking de horas extras por usuario")

        try:
            df_ranking = datos_filtrados.copy()
            df_ranking = df_ranking.dropna(subset=["usuario", "Total horas extras"])

            def convertir_horas_extras(horas_str):
                try:
                    h, m = map(int, horas_str.strip().split(":"))
                    return h * 60 + m
                except:
                    return 0

            df_ranking["extras_minutos"] = df_ranking["Total horas extras"].apply(convertir_horas_extras)
            resumen_ranking = (
                df_ranking.groupby("usuario")["extras_minutos"]
                .sum()
                .reset_index()
                .sort_values(by="extras_minutos", ascending=False)
            )

            if resumen_ranking.empty:
                st.info("ℹ️ No hay horas extras acumuladas en los registros filtrados.")
            else:
                resumen_ranking["HH:MM"] = resumen_ranking["extras_minutos"].apply(
                    lambda x: f"{x // 60:02}:{x % 60:02}"
                )
                st.dataframe(resumen_ranking[["usuario", "HH:MM"]].rename(columns={"HH:MM": "Total horas extras"}))
                st.bar_chart(resumen_ranking.set_index("usuario")["extras_minutos"])
        except Exception as e:
            st.error(f"❌ Error al generar el ranking: {e}")

    st.markdown("---")

    st.markdown("### 🔄 Aplicar cálculos de jornada y horas extras")

    def aplicar_calculos_masivos():
        sheet = conectar_hoja()
        registros = sheet.get_all_values()
        encabezados = [col.lower().strip() for col in registros[0]]

        try:
            libro = sheet.spreadsheet
            bd_sheet = libro.worksheet("BD")
            bd_valores = bd_sheet.get_all_records()
            jornada_dict = {
                fila["Hora"].strip(): float(fila["Jornada"])
                for fila in bd_valores
                if "Hora" in fila and "Jornada" in fila
            }
        except Exception:
            st.error("❌ No se pudo acceder a la hoja 'BD'. Verifica que existe y contiene 'Hora' y 'Jornada'.")
            return

        registros_actualizados = 0

        for idx, fila in enumerate(registros[1:], start=2):
            fila_dict = dict(zip(encabezados, fila))
            inicio = fila_dict.get("redondeo inicio", "").strip()
            fin = fila_dict.get("redondeo fin", "").strip()

            if not inicio or not fin or inicio not in jornada_dict:
                continue

            try:
                t_inicio = datetime.strptime(inicio, "%H:%M:%S")
                t_fin = datetime.strptime(fin, "%H:%M:%S")
                if t_fin < t_inicio:
                    t_fin += pd.Timedelta(days=1)

                duracion = (t_fin - t_inicio).total_seconds() / 3600
                jornada_esperada = jornada_dict[inicio]
                extras = max(duracion - jornada_esperada, 0)

                jornada_str = str(int(jornada_esperada))
                extras_str = f"{int(extras // 1):02}:{int((extras % 1) * 60):02}"

                sheet.update_cell(idx, encabezados.index("jornada") + 1, jornada_str)
                sheet.update_cell(idx, encabezados.index("total horas extras") + 1, extras_str)

                registros_actualizados += 1
            except Exception:
                continue

        st.success(f"✅ Se calcularon jornadas esperadas y horas extras para {registros_actualizados} registros.")

    if st.button("⚙️ Calcular jornada y horas extras"):
        aplicar_calculos_masivos()

    st.markdown("---")

    st.markdown("### 🚪 Cerrar sesión")
    if st.button("Salir"):
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
    # 🚪 Botón para salir del panel
st.markdown("### 🚪 Cerrar sesión")
if st.button("Salir"):
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
# Footer
st.markdown("""
<hr style="margin-top: 50px; border: none; border-top: 1px solid #ccc;" />
<div style="text-align: center; color: gray; font-size: 0.9em; margin-top: 20px;">
    NN HOLDING SOLUTIONS, Ever Be Better &copy; 2025, Todos los derechos reservados
</div>
""", unsafe_allow_html=True)    
    
