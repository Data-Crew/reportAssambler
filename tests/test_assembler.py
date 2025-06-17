from pathlib import Path
from app.report_assembler import ReportAssembler

# Fecha de subdirectorio dentro de DATA que se usará para los tests
TEST_DATE = "20-05-2025"

# Control de estudios
#TEST_CONTROL = {"BASICO"}
#TEST_CONTROL = {"BASICO", "AUDIOMETRIA"}
#TEST_CONTROL = {"BASICO",  "ALTURA"}
TEST_CONTROL = {"BASICO",  "ESPIROMETRIA"}


# Construye el path absoluto al folder de fecha
def get_data_path():
    return Path(__file__).resolve().parent.parent / "DATA" / TEST_DATE

def test_load_master_excel():
    assembler = ReportAssembler(str(get_data_path()))
    assert assembler.df_master is not None

def test_tokenize_detalle():
    assembler = ReportAssembler(str(get_data_path()))
    row = assembler.df_master.iloc[0]
    tokens = row["DETALLE"].upper().replace(",", "").split("+")
    tokens = [t.strip() for t in tokens]
    assert isinstance(tokens, list)

def test_get_patient_cover_exists():
    assembler = ReportAssembler(str(get_data_path()))
    row = assembler.df_master.iloc[0]  # obtenés la fila completa
    path = assembler.get_patient_cover(row)
    assert path.exists()

# Condicionales para definir solo ciertos tests
if set(TEST_CONTROL) == {"BASICO"}:
    def test_build_report_token_basico():
        assembler = ReportAssembler(str(get_data_path()))
        print('')
        print("\n" + "✂️" * 3 + " Separando laboratorios por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("LABORATORIO")

        row = assembler.df_master.query("DETALLE == 'BASICO'").sample(1).iloc[0]
        dni = row["DNI"].replace(".", "")
        apellido = row["APELLIDOS"].strip().replace(" ", "_")
        index = row.name

        assembler.build_report_for_patient(index)

        output_path = Path(__file__).resolve().parent.parent / "OUTPUT" / TEST_DATE / f"{apellido}_{dni}.pdf"
        assert output_path.exists()


elif set(TEST_CONTROL) == {"BASICO", "AUDIOMETRIA"}:
    def test_build_report_token_basico_audiometria():
        assembler = ReportAssembler(str(get_data_path()))
        print("\n" + "✂️" * 3 + " Separando laboratorios por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("LABORATORIO")
        print("\n" + "✂️" * 3 + " Separando audiometrias por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("AUDIOMETRIA")

        mask = (
            assembler.df_master["DETALLE"].notna() &
            assembler.df_master["DETALLE"].str.upper().str.contains("AUDIOMETRIA")
        )
        row = assembler.df_master[mask].sample(1).iloc[0]
        dni = row["DNI"].replace(".", "")
        apellido = row["APELLIDOS"].strip().replace(" ", "_")
        index = row.name

        assembler.build_report_for_patient(index)

        output_path = Path(__file__).resolve().parent.parent / "OUTPUT" / TEST_DATE / f"{apellido}_{dni}.pdf"
        assert output_path.exists()


elif set(TEST_CONTROL) == {"BASICO", "ALTURA"}:
    def test_build_report_token_basico_audiometria_altura():
        assembler = ReportAssembler(str(get_data_path()))
        print("\n" + "✂️" * 3 + " Separando laboratorios por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("LABORATORIO")
        print("\n" + "✂️" * 3 + " Separando audiometrias por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("AUDIOMETRIA")

        # ALTURA
        print("\n" + "✂️" * 3 + " Separando EEG por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_name("EEG")
        print("\n" + "✂️" * 3 + " Separando PSICOTECNICOS por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_name("PSICOS")

        mask = (
            assembler.df_master["DETALLE"].notna() &
            assembler.df_master["DETALLE"].str.upper().str.contains("ALTURA")
        )
        row = assembler.df_master[mask].sample(1).iloc[0]

        dni = row["DNI"].replace(".", "")
        apellido = row["APELLIDOS"].strip().replace(" ", "_")
        index = row.name

        assembler.build_report_for_patient(index)

        output_path = Path(__file__).resolve().parent.parent / "OUTPUT" / TEST_DATE / f"{apellido}_{dni}.pdf"
        assert output_path.exists()

elif set(TEST_CONTROL) == {"BASICO", "ESPIROMETRIA"}:
    def test_build_report_token_basico_espirometria():
        assembler = ReportAssembler(str(get_data_path()))
        print("\n" + "✂️" * 3 + " Separando laboratorios por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_dni("LABORATORIO")
        print("\n" + "✂️" * 3 + " Separando espirometrias por paciente " + "✂️" * 3 + "\n")
        assembler.preprocess_study_results_by_name("ESPIROMETRIA")

        mask = (
            assembler.df_master["DETALLE"].notna() &
            assembler.df_master["DETALLE"].str.upper().str.contains("ESPIROMETRIA")
        )
        row = assembler.df_master[mask].sample(1).iloc[0]
        dni = row["DNI"].replace(".", "")
        apellido = row["APELLIDOS"].strip().replace(" ", "_")
        index = row.name

        assembler.build_report_for_patient(index)

        output_path = Path(__file__).resolve().parent.parent / "OUTPUT" / TEST_DATE / f"{apellido}_{dni}.pdf"
        assert output_path.exists()

else:
    print("⚠️ TEST_CONTROL no coincide con ninguna de las combinaciones permitidas.")


def test_index_shared_pdfs_detects_files():
    assembler = ReportAssembler(str(get_data_path()))
    assert isinstance(assembler.shared_pdfs, dict)


# Debug opcional
def test_debug_path():
    import os
    print("📂 Current working directory:", os.getcwd())
    print("📄 Contenido de DATA:", list((get_data_path().parent).glob("*")))

