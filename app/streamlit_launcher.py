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

# Insrtrucciones
with st.expander("ℹ️ Instrucciones de uso"):
    st.markdown("""
    1. Seleccioná la fecha de compilación.
    2. Elegí si querés compilar los informes de todos los pacientes o los de uno solo.
    3. Si seleccionás compilar por paciente, elegí el nombre desde el desplegable.
    4. Hacé click en **Discriminar estudios por paciente** para separar los PDFs generales.
    5. Hacé click en **Compilar resultados por paciente** para generar un informe médico único.
    """)

# Elegir fechas
DATA_PATH = Path(__file__).resolve().parent.parent / "DATA"
st.sidebar.markdown("## 🗂️ Parámetros de compilación")

available_dates = sorted([d.name for d in DATA_PATH.iterdir() if d.is_dir()])
selected_date = st.sidebar.selectbox("📅 Seleccionar la fecha de compilación", available_dates)
st.sidebar.success(f"📂 Carpeta seleccionada: `{selected_date}`")

selected_path = DATA_PATH / selected_date
assembler = ReportAssembler(str(selected_path))

df = assembler.df_master

# Elegir modo de compilación
st.sidebar.markdown("### 👥 Modo de compilación")
modo = st.sidebar.radio(
    "¿Querés compilar informes para todos o para un solo paciente?",
    ["Todos los pacientes", "Un solo paciente"]
)

if modo == "Un solo paciente":
    st.sidebar.markdown("### 👤 Seleccioná un paciente")
    # Elegir el nombre desde el sidebar
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

# Inicializar valores de sesión
if "logs_discriminacion" not in st.session_state:
    st.session_state.logs_discriminacion = ""
if "logs_compilacion" not in st.session_state:
    st.session_state.logs_compilacion = ""
if "accion_realizada" not in st.session_state:
    st.session_state.accion_realizada = False

# Compilar estudios
_, col4, col5, _ = st.columns([0.5, 3, 3, 0.5])

with col4:
    discriminar_clicked = st.button("✂️ 1. Discriminar estudios por paciente")

with col5:
    compilar_clicked = st.button("📄 2. Compilar resultados por paciente")

logs = ""

if discriminar_clicked:
    studies_by_dni = ["LABORATORIO", "AUDIOMETRIA"]
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