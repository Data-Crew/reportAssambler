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
                    df_display = pd.DataFrame({
                        "Parámetro": df_resultados["parametro"],
                        "Valor": df_resultados["valor"].apply(lambda x: f"{x:.2f}"),
                        "Unidad": df_resultados["unidad"],
                        "Rango Esperado": df_resultados.apply(
                            lambda row: f"{row['rango_min']:.1f} - {row['rango_max']:.1f}" 
                            if row['rango_min'] and row['rango_max'] else "N/A", axis=1
                        ),
                        "Dirección": df_resultados["direccion"].apply(
                            lambda x: "⬆️ Alto" if x == "alto" else "⬇️ Bajo" if x == "bajo" else ""
                        ),
                        "Exceso/Deficiencia": df_resultados.apply(
                            lambda row: f"{row['exceso']:.2f}" if row['exceso'] 
                            else f"{row['deficiencia']:.2f}" if row['deficiencia'] else "", axis=1
                        )
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
                    df_todos_display = pd.DataFrame({
                        "Parámetro": df_todos["parametro"],
                        "Valor": df_todos["valor"].apply(lambda x: f"{x:.2f}"),
                        "Unidad": df_todos["unidad"],
                        "Rango": df_todos.apply(
                            lambda row: f"{row['rango_min']:.1f} - {row['rango_max']:.1f}" 
                            if row['rango_min'] and row['rango_max'] else "N/A", axis=1
                        ),
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
    ["Compilador", "Clasificador de Laboratorios"],
    help="Elige entre compilar informes médicos o analizar valores de laboratorio"
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
else:
    mostrar_clasificador_laboratorios(assembler, df)