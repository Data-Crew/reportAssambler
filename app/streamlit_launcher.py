import streamlit as st
from PIL import Image

from pathlib import Path
from app.report_assembler import ReportAssembler
import sys
import io

st.set_page_config(page_title="Compilador de informes médicos", page_icon="🩺")

# Estilo para simular consola
st.markdown("""
    <style>
    .element-container pre {
        background-color: #1e1e1e !important;
        color: #d4d4d4 !important;
        padding: 1em;
        border-radius: 5px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
    }
    </style>
""", unsafe_allow_html=True)


def obtener_configuracion_sidebar(assembler: ReportAssembler, df):
    """Obtiene la configuración del sidebar para el compilador."""
    modo = st.sidebar.radio(
        "¿Querés compilar informes para todos o para un solo paciente?",
        ["Todos los pacientes", "Un solo paciente"]
    )
    
    selected_index = None
    if modo == "Un solo paciente":
        st.sidebar.markdown("### 👤 Seleccioná un paciente")
        df["nombre_completo"] = df["APELLIDOS"].str.strip() + " " + df["NOMBRES"].str.strip() + " (" + df["DNI"].astype(str) + ")"
        selected_name = st.sidebar.selectbox("Seleccioná un paciente:", df["nombre_completo"])
        selected_index = df[df["nombre_completo"] == selected_name].index[0]

        paciente = df.loc[selected_index]
        st.sidebar.info(
            f"""
            **🧑 Paciente seleccionado:**  
            {paciente['APELLIDOS'].strip()} {paciente['NOMBRES'].strip()}  
            **🆔 DNI:** {paciente['DNI']}  
            **📋 Compilar estudios:** {paciente['DETALLE']}
            """
        )
    
    return modo, selected_index


def mostrar_compilador(assembler: ReportAssembler, df, modo=None, selected_index=None):
    """Muestra la interfaz del compilador de informes médicos."""
    # Instrucciones
    with st.expander("ℹ️ Instrucciones de uso"):
        st.markdown("""
        1. Seleccioná la fecha de compilación.
        2. Elegí si querés compilar los informes de todos los pacientes o los de uno solo.
        3. Si seleccionás compilar por paciente, elegí el nombre desde el desplegable.
        4. Hacé click en **Discriminar estudios por paciente** para separar los PDFs generales.
        5. Hacé click en **Compilar resultados por paciente** para generar un informe médico único.
        """)
    
    # Obtener configuración del sidebar si no se pasó
    if modo is None:
        modo, selected_index = obtener_configuracion_sidebar(assembler, df)
    
    # Compilar estudios
    _, col4, col5, _ = st.columns([0.5, 3, 3, 0.5])

    with col4:
        discriminar_clicked = st.button("✂️ 1. Discriminar estudios por paciente")

    with col5:
        compilar_clicked = st.button("📄 2. Compilar resultados por paciente")

    if discriminar_clicked:
        studies_by_dni = ["LABORATORIO", "AUDIOMETRIA", "ERGOMETRIA"]
        studies_by_name = ["EEG", "PSICOS", "ESPIROMETRIA"]

        buffer = io.StringIO()
        sys.stdout = buffer

        for study in studies_by_dni:
            print(f"\n{'✂️'*3} Separando {study.lower()} por paciente {'✂️'*3}\n")
            assembler.preprocess_study_results_by_dni(study)

        for study in studies_by_name:
            print(f"\n{'✂️'*3} Separando {study.lower()} por paciente {'✂️'*3}\n")
            assembler.preprocess_study_results_by_name(study)

        sys.stdout = sys.__stdout__
        st.session_state.logs_discriminacion = buffer.getvalue()
        st.session_state.accion_realizada = True
        
    if compilar_clicked:
        buffer = io.StringIO()
        sys.stdout = buffer

        try:
            if modo == "Un solo paciente":
                assembler.build_report_for_patient(selected_index)
            else:
                assembler.build_all_reports()
        except Exception as e:
            print(f"❌ Error al compilar informes: {e}")
            st.session_state.logs_compilacion = buffer.getvalue()
            st.error("Se produjo un error durante la compilación. Ver logs para más detalles.")
            raise e  
        finally:
            sys.stdout = sys.__stdout__
            st.session_state.logs_compilacion = buffer.getvalue()
            st.session_state.accion_realizada = True

    if st.session_state.logs_discriminacion:
        with st.expander("📜 Logs de procesamiento", expanded=True):
            st.markdown(f"""```bash
{st.session_state.logs_discriminacion}
```""")

    if st.session_state.logs_compilacion:
        with st.expander("📝 Logs de generación de informes", expanded=True):
            st.markdown(f"""```bash
{st.session_state.logs_compilacion}
```""")

    if not st.session_state.accion_realizada:
        st.success("🚀 Listo para usar.")

    if st.session_state.get("accion_realizada", False):
        if st.button("🔄 Reiniciar sesión"):
            st.session_state.logs_discriminacion = ""
            st.session_state.logs_compilacion = ""
            st.session_state.accion_realizada = False
            st.rerun()


def mostrar_clasificador_laboratorios(assembler: ReportAssembler, df):
    """Muestra la interfaz del clasificador de laboratorios."""
    from app.lab_analyzer import LaboratoryAnalyzer
    import pandas as pd
    
    st.markdown("## 🧪 Clasificador de Laboratorios")
    st.markdown("Analiza PDFs de laboratorio para detectar valores fuera de rango de referencia.")
    
    # Selección de paciente
    st.markdown("### 👤 Seleccionar paciente")
    df["nombre_completo"] = df["APELLIDOS"].str.strip() + " " + df["NOMBRES"].str.strip() + " (" + df["DNI"].astype(str) + ")"
    selected_name = st.selectbox("Seleccioná un paciente:", df["nombre_completo"])
    selected_index = df[df["nombre_completo"] == selected_name].index[0]
    paciente = df.loc[selected_index]
    
    dni_clean = str(paciente['DNI']).strip().replace(".", "")
    lab_path = assembler.fecha_folder / "LABORATORIO" / f"{dni_clean}.pdf"
    
    if not lab_path.exists():
        st.error(f"❌ No se encontró PDF de laboratorio para DNI {dni_clean}")
        st.info(f"Ruta esperada: `{lab_path}`")
        return
    
    st.success(f"✅ PDF de laboratorio encontrado: {lab_path.name}")
    st.info(f"**Paciente:** {paciente['APELLIDOS'].strip()} {paciente['NOMBRES'].strip()} | **DNI:** {paciente['DNI']}")
    
    if st.button("🔍 Analizar laboratorio"):
        with st.spinner("Analizando PDF de laboratorio..."):
            try:
                analyzer = LaboratoryAnalyzer()
                resultados = analyzer.analyze_pdf(lab_path)
                
                if resultados["total_parametros"] == 0:
                    st.warning("⚠️ No se pudieron extraer parámetros del PDF.")
                    st.info("""
                    **Posibles causas:**
                    - El formato del PDF no es reconocido
                    - El PDF está escaneado (imagen) y requiere OCR
                    - El formato de los datos es diferente al esperado
                    
                    **Sugerencia:** Revisa el PDF manualmente o contacta al desarrollador para ajustar el parser.
                    """)
                    return
                
                # Mostrar resumen
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Parámetros", resultados["total_parametros"])
                with col2:
                    st.metric("Fuera de Rango", resultados["fuera_de_rango"], 
                             delta=f"{resultados['porcentaje_fuera']}%")
                with col3:
                    dentro_rango = resultados["total_parametros"] - resultados["fuera_de_rango"]
                    st.metric("Dentro de Rango", dentro_rango)
                with col4:
                    porcentaje_ok = 100 - resultados["porcentaje_fuera"]
                    st.metric("% Normal", f"{porcentaje_ok:.1f}%")
                
                # Filtrar solo los que están fuera de rango
                fuera_rango = [r for r in resultados["resultados"] if r["fuera_de_rango"]]
                
                if fuera_rango:
                    st.markdown("### ⚠️ Valores Fuera de Rango")
                    
                    # Crear DataFrame para mostrar
                    df_resultados = pd.DataFrame(fuera_rango)
                    
                    # Formatear valores: numéricos con 2 decimales, strings como están
                    def formatear_valor_fuera(x):
                        if isinstance(x, (int, float)):
                            return f"{x:.2f}"
                        elif isinstance(x, str):
                            return x
                        else:
                            return str(x)
                    
                    # Formatear rangos esperados
                    def formatear_rango_esperado(row):
                        min_val = row['rango_min']
                        max_val = row['rango_max']
                        if min_val is not None and max_val is not None:
                            return f"{min_val:.1f} - {max_val:.1f}"
                        elif min_val is not None:
                            return f"> {min_val:.1f}"
                        elif max_val is not None:
                            return f"< {max_val:.1f}"
                        else:
                            return "N/A"
                    
                    # Formatear exceso/deficiencia
                    def formatear_exceso_deficiencia(row):
                        if row['exceso'] is not None:
                            return f"{row['exceso']:.2f}"
                        elif row['deficiencia'] is not None:
                            return f"{row['deficiencia']:.2f}"
                        else:
                            return ""
                    
                    df_display = pd.DataFrame({
                        "Parámetro": df_resultados["parametro"],
                        "Valor": df_resultados["valor"].apply(formatear_valor_fuera),
                        "Unidad": df_resultados["unidad"],
                        "Rango Esperado": df_resultados.apply(formatear_rango_esperado, axis=1),
                        "Dirección": df_resultados["direccion"].apply(
                            lambda x: "⬆️ Alto" if x == "alto" else "⬇️ Bajo" if x == "bajo" else ""
                        ),
                        "Exceso/Deficiencia": df_resultados.apply(formatear_exceso_deficiencia, axis=1)
                    })
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # Botón para exportar CSV
                    csv = df_display.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar CSV",
                        data=csv,
                        file_name=f"laboratorio_{dni_clean}_fuera_rango.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("✅ Todos los valores están dentro del rango de referencia.")
                
                # Mostrar todos los parámetros en un expander
                with st.expander("📋 Ver todos los parámetros"):
                    df_todos = pd.DataFrame(resultados["resultados"])
                    
                    # Formatear valores: numéricos con 2 decimales, strings como están
                    def formatear_valor(x):
                        if isinstance(x, (int, float)):
                            return f"{x:.2f}"
                        elif isinstance(x, str):
                            return x
                        else:
                            return str(x)
                    
                    # Formatear rangos: manejar None y valores numéricos
                    def formatear_rango(row):
                        min_val = row['rango_min']
                        max_val = row['rango_max']
                        if min_val is not None and max_val is not None:
                            return f"{min_val:.1f} - {max_val:.1f}"
                        elif min_val is not None:
                            return f"> {min_val:.1f}"
                        elif max_val is not None:
                            return f"< {max_val:.1f}"
                        else:
                            return "N/A"
                    
                    df_todos_display = pd.DataFrame({
                        "Parámetro": df_todos["parametro"],
                        "Valor": df_todos["valor"].apply(formatear_valor),
                        "Unidad": df_todos["unidad"],
                        "Rango": df_todos.apply(formatear_rango, axis=1),
                        "Estado": df_todos["fuera_de_rango"].apply(
                            lambda x: "⚠️ Fuera" if x else "✅ OK"
                        )
                    })
                    st.dataframe(df_todos_display, use_container_width=True, hide_index=True)
                
            except FileNotFoundError as e:
                st.error(f"❌ Error: {e}")
            except Exception as e:
                st.error(f"❌ Error al analizar el PDF: {e}")
                with st.expander("🔍 Detalles del error"):
                    st.exception(e)


def mostrar_analisis_masivo(assembler: ReportAssembler, df):
    """Muestra la interfaz para análisis masivo de laboratorios."""
    from app.lab_batch_analyzer import LaboratoryBatchAnalyzer
    import pandas as pd
    
    st.markdown("## 📊 Análisis Masivo de Laboratorios")
    st.markdown("Analiza todos los PDFs de laboratorio disponibles y genera un reporte consolidado en Excel.")
    
    batch_analyzer = LaboratoryBatchAnalyzer(assembler)
    
    # Buscar PDFs disponibles
    with st.spinner("🔍 Buscando PDFs de laboratorio..."):
        pdfs_encontrados = batch_analyzer.find_all_laboratory_pdfs()
    
    if not pdfs_encontrados:
        st.warning("⚠️ No se encontraron PDFs de laboratorio en la carpeta LABORATORIO.")
        st.info(f"Ruta esperada: `{assembler.fecha_folder / 'LABORATORIO'}`")
        return
    
    st.success(f"✅ Se encontraron {len(pdfs_encontrados)} PDFs de laboratorio")
    
    # Mostrar lista de PDFs encontrados
    with st.expander("📋 Ver PDFs encontrados"):
        df_pdfs_data = []
        for pdf_info in pdfs_encontrados:
            paciente_info = pdf_info.get("paciente_info") or {}
            apellidos = paciente_info.get("APELLIDOS", "N/A")
            nombres = paciente_info.get("NOMBRES", "N/A")
            df_pdfs_data.append({
                "DNI": pdf_info["dni"],
                "Paciente": f"{apellidos} {nombres}".strip(),
                "Archivo": pdf_info["pdf_path"].name
            })
        df_pdfs = pd.DataFrame(df_pdfs_data)
        st.dataframe(df_pdfs, use_container_width=True, hide_index=True)
    
    # Botón para iniciar análisis
    if st.button("🚀 Iniciar Análisis Masivo", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        resultados = []
        total = len(pdfs_encontrados)
        
        for idx, pdf_info in enumerate(pdfs_encontrados):
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.text(f"Analizando {idx + 1}/{total}: {pdf_info['pdf_path'].name}")
            
            try:
                resultado = batch_analyzer.analyzer.analyze_pdf(pdf_info["pdf_path"])
                
                # Agregar información del paciente
                paciente_info = pdf_info.get("paciente_info") or {}
                resultado["dni"] = pdf_info["dni"]
                resultado["dni_clean"] = pdf_info["dni_clean"]
                resultado["apellidos"] = paciente_info.get("APELLIDOS", "N/A")
                resultado["nombres"] = paciente_info.get("NOMBRES", "N/A")
                resultado["nombre_completo"] = f"{resultado['apellidos']} {resultado['nombres']}".strip()
                
                resultados.append(resultado)
            except Exception as e:
                # Si hay error, agregar información básica con error
                paciente_info = pdf_info.get("paciente_info") or {}
                apellidos = paciente_info.get("APELLIDOS", "N/A")
                nombres = paciente_info.get("NOMBRES", "N/A")
                
                # Obtener mensaje de error más detallado
                error_msg = str(e)
                error_type = type(e).__name__
                
                resultados.append({
                    "dni": pdf_info["dni"],
                    "dni_clean": pdf_info["dni_clean"],
                    "apellidos": apellidos,
                    "nombres": nombres,
                    "nombre_completo": f"{apellidos} {nombres}".strip(),
                    "error": f"{error_type}: {error_msg}",
                    "error_type": error_type,
                    "error_message": error_msg,
                    "total_parametros": 0,
                    "fuera_de_rango": 0,
                    "resultados": []
                })
        
        progress_bar.progress(1.0)
        status_text.text("✅ Análisis completado")
        
        # Generar Excel
        with st.spinner("📝 Generando reporte Excel..."):
            excel_path = batch_analyzer.generate_excel_report(resultados)
        
        st.success(f"✅ Reporte generado exitosamente: `{excel_path.name}`")
        
        # Mostrar resumen
        st.markdown("### 📈 Resumen del Análisis")
        
        # Calcular estadísticas
        total_pacientes = len(resultados)
        pacientes_con_error = sum(1 for r in resultados if "error" in r)
        pacientes_ok = total_pacientes - pacientes_con_error
        
        total_parametros = sum(r.get("total_parametros", 0) for r in resultados)
        total_fuera_rango = sum(r.get("fuera_de_rango", 0) for r in resultados)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pacientes", total_pacientes)
        with col2:
            st.metric("Pacientes Analizados", pacientes_ok, delta=f"-{pacientes_con_error} errores" if pacientes_con_error > 0 else None)
        with col3:
            st.metric("Total Parámetros", total_parametros)
        with col4:
            st.metric("Fuera de Rango", total_fuera_rango, delta=f"{total_fuera_rango/total_parametros*100:.1f}%" if total_parametros > 0 else None)
        
        # Botón para descargar Excel
        with open(excel_path, "rb") as f:
            excel_bytes = f.read()
        
        st.download_button(
            label="📥 Descargar Reporte Excel",
            data=excel_bytes,
            file_name=excel_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Mostrar tabla resumen
        st.markdown("### 📋 Resumen por Paciente")
        df_resumen_data = []
        for r in resultados:
            estado = "❌ Error" if "error" in r else ("⚠️ Con valores fuera" if r.get("fuera_de_rango", 0) > 0 else "✅ OK")
            df_resumen_data.append({
                "DNI": r["dni"],
                "Paciente": r.get("nombre_completo", "N/A"),
                "Parámetros": r.get("total_parametros", 0),
                "Fuera de Rango": r.get("fuera_de_rango", 0),
                "Estado": estado,
                "Error": r.get("error", "") if "error" in r else ""
            })
        df_resumen = pd.DataFrame(df_resumen_data)
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        # Mostrar detalles de errores si hay alguno
        pacientes_con_error = [r for r in resultados if "error" in r]
        if pacientes_con_error:
            with st.expander("🔍 Detalles de Errores", expanded=False):
                for paciente_error in pacientes_con_error:
                    st.markdown(f"**DNI:** {paciente_error['dni']} | **Paciente:** {paciente_error.get('nombre_completo', 'N/A')}")
                    st.code(f"{paciente_error['error']}", language=None)
                    st.markdown("---")


# ============================================================================
# MAIN APP
# ============================================================================

logo_path = Path(__file__).parent / "cbm_logo.jpg"
logo = Image.open(logo_path)
_, _, _, col0 = st.columns([3, 3, 1, 3])
col0.image(logo, width=175)

col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.write("")  

with col2:
    st.markdown("<h1 style='text-align: center; margin-top: 0;'>Compilador de informes médicos</h1>", unsafe_allow_html=True)
    st.caption("Herramienta de ensamblado automático de estudios por paciente")

with col3:
    st.write("") 

# Selector de herramienta en sidebar
DATA_PATH = Path(__file__).resolve().parent.parent / "DATA"
st.sidebar.markdown("## 🛠️ Herramientas")

herramienta = st.sidebar.radio(
    "Seleccionar herramienta:",
    ["Compilador", "Clasificador de Laboratorios", "Análisis Masivo de Laboratorios"],
    help="Elige entre compilar informes médicos, analizar valores de laboratorio individual o análisis masivo"
)

# Elegir fechas (común para ambas herramientas)
st.sidebar.markdown("## 🗂️ Parámetros")
available_dates = sorted([d.name for d in DATA_PATH.iterdir() if d.is_dir()])
selected_date = st.sidebar.selectbox("📅 Seleccionar la fecha", available_dates)
st.sidebar.success(f"📂 Carpeta seleccionada: `{selected_date}`")

selected_path = DATA_PATH / selected_date
assembler = ReportAssembler(str(selected_path))
df = assembler.df_master

# Inicializar valores de sesión
if "logs_discriminacion" not in st.session_state:
    st.session_state.logs_discriminacion = ""
if "logs_compilacion" not in st.session_state:
    st.session_state.logs_compilacion = ""
if "accion_realizada" not in st.session_state:
    st.session_state.accion_realizada = False

# Mostrar contenido según herramienta seleccionada
if herramienta == "Compilador":
    mostrar_compilador(assembler, df)
elif herramienta == "Clasificador de Laboratorios":
    mostrar_clasificador_laboratorios(assembler, df)
else:
    mostrar_analisis_masivo(assembler, df)