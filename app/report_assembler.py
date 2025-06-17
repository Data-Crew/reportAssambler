import pandas as pd
import fitz
from PIL import Image
from PIL import ImageOps
from pathlib import Path
from typing import List, Dict, Optional
from app.converters import convert_xlsx_to_pdf, split_pdf_by_dni


class ReportAssembler:
    def __init__(self, base_path: str, subfolder: str = None):
        self.base_path = Path(base_path)
        self.fecha_folder = self.base_path / subfolder if subfolder else self.base_path / self.base_path.name

        # Excel maestro
        expected_excel_name = "PRUEBA SISTEMA NUEVO.xlsx"
        self.master_excel_path = self.fecha_folder / expected_excel_name
        if not self.master_excel_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo maestro esperado: {self.master_excel_path}")

        self.df_master = self._load_master_excel()
        # Elimina filas que no tienen APELLIDOS, NOMBRES o DETALLE
        campos_clave = ["APELLIDOS", "NOMBRES", "DETALLE"]
        self.df_master = self.df_master.dropna(subset=campos_clave)
        #print(f"📄 Usando Excel maestro: {self.master_excel_path}")

        self.caratula_path = self.fecha_folder
        self.shared_pdfs = self._index_shared_pdfs()
        self.per_patient_dirs = ['ECG', 'RX']
        self.study_map = self._define_study_map()
        

    def _find_fecha_folder(self) -> Path:
        subdirs = [d for d in self.base_path.iterdir() if d.is_dir()]
        if len(subdirs) != 1:
            raise ValueError(f"Expected a single fecha subdirectory, found: {[str(s) for s in subdirs]}")
        return subdirs[0]

    def _define_study_map(self) -> Dict[str, List[str]]:
        return {
            "BASICO": ["LABORATORIO", "ECG", "RX"],
            "ALTURA": ["EEG", "PSICOS", "AUDIOMETRIA"],
            "AUDIOMETRIA": ["AUDIOMETRIA"],
            "PSICOTECNICO": ["PSICOS"],
            "ESPIROMETRIA": ["ESPIROMETRIA"],
        }

    def _index_shared_pdfs(self) -> Dict[str, Path]:
        pdfs = {}
        for f in self.base_path.glob("*.pdf"):
            name_upper = f.stem.upper()

            # Excluir PDF general de laboratorio (por nombre que empieza con LABORATORIO)
            if name_upper.startswith("LABORATORIO"):
                continue

            # Indexar por la primera palabra del nombre del archivo (por convención)
            key = name_upper.split()[0]
            pdfs[key] = f

        return pdfs

    def _load_master_excel(self) -> pd.DataFrame:
        df = pd.read_excel(self.master_excel_path)
        expected_cols = ["FECHA", "APELLIDOS", "NOMBRES", "DNI", "DETALLE"]
        missing = [col for col in expected_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in master Excel: {missing}")
        return df
    
    def get_patient_cover(self, row: pd.Series) -> Path:
        numero = int(row["Nº"]) 
        path = self.caratula_path / f"{numero}.xlsx"
        if path.exists():
            return path
        else:
            raise FileNotFoundError(f"Missing carátula file: {path}")

    def get_patient_records(self) -> pd.DataFrame:
        df = self.df_master.copy()
        df["DETALLE_TOKENS"] = df["DETALLE"].astype(str).str.upper().str.replace(",", "").str.split(r" \+ ")
        return df

    def get_required_studies(self, tokens: List[str], dni: Optional[str] = None,
                        apellido: Optional[str] = None, nombre: Optional[str] = None) -> List[Path]:
        print(f"📥 get_required_studies llamado con tokens={tokens}, dni={dni}, apellido={apellido}, nombre={nombre}")
        # TODO: Modularizar funciones por estudio
        pdfs = []
        for token in tokens:
            studies = self.study_map.get(token, [])
            for study in studies:
                if study.upper() == "LABORATORIO" and dni:
                    dni_clean = dni.replace(".", "") 
                    lab_path = self.fecha_folder / "LABORATORIO" / f"{dni_clean}.pdf"
                    print(f"🔍 Buscando LAB individual: {lab_path}")
                    if lab_path.exists():
                        print("✅ Encontrado")
                        pdfs.append(lab_path)
                    else:
                        print("❌ No encontrado. No se agregará PDF general.")

                elif study.upper() == "ECG" and apellido and nombre:
                    ecg_dirs = list(self.fecha_folder.parent.glob("ECG*"))
                    if ecg_dirs:
                        ecg_dir = ecg_dirs[0]
                        primer_nombre = nombre.strip().split()[0].upper()
                        #print(f"PRIMER NOMBRE:{primer_nombre}")
                        
                        # Usar primer palabra del apellido
                        apellido_orig = apellido.replace("_", " ")
                        primer_apellido = apellido_orig.strip().split()[0].upper()
                        #print(f"PRIMER APELLIDO:{primer_apellido}")
                        apellido_clean = primer_apellido.replace(" ", "_")
                        nombre_clean = primer_nombre.replace(" ", "_")
                        ecg_pattern_1 = f"{apellido_clean}_{nombre_clean}*.pdf"
                        matches = list(ecg_dir.glob(ecg_pattern_1))

                        # Si no se encuentra, intentar con apellido completo
                        if not matches:
                            apellido_clean_full = apellido.strip().upper()  # usar todo el apellido
                            ecg_pattern_2 = f"{apellido_clean_full}_{nombre_clean}*.pdf"
                            matches = list(ecg_dir.glob(ecg_pattern_2))
                            if matches:
                                print(f"📄 ECG encontrado usando apellido completo: {matches[0].name}")
                        else:
                            print(f"📄 ECG encontrado: {matches[0].name}")

                        if len(matches) == 1:
                            pdfs.append(matches[0])
                        elif len(matches) > 1:
                            print(f"⚠️ Múltiples ECG encontrados. Se ignorará: {matches}")
                        else:
                            print(f"⚠️ ECG no encontrado para patrones {ecg_pattern_1} ni {ecg_pattern_2}")
                    else:
                        print(f"⚠️ No se encontró directorio ECG: {ecg_dirs}")

                elif study.upper() == "RX" and dni:
                    dni_clean = dni.replace(".", "")
                    rx_root = self.base_path / f"RX {self.base_path.name}"

                    if not rx_root.exists():
                        print(f"⚠️ Carpeta RX no encontrada: {rx_root}")
                        continue

                    matching_folders = [f for f in rx_root.iterdir() if f.is_dir() and dni_clean in f.name]
                    
                    if not matching_folders:
                        print(f"⚠️ No se encontró subcarpeta RX con DNI {dni_clean} en {rx_root}")
                        continue

                    rx_folder = matching_folders[0]
                    jpgs = sorted(rx_folder.glob("*.jpg"))

                    if jpgs:
                        rx_pdf_path = Path("tmp") / f"rx_{dni_clean}.pdf"
                        rx_pdf_path.parent.mkdir(exist_ok=True)

                        resized_images = []
                        for j in jpgs:
                            img = Image.open(j).convert("RGB")
                            img = ImageOps.exif_transpose(img)  # Corrige orientación si viene mal del scanner

                            # Redimensionar preservando aspecto, ancho máximo 1000px
                            max_width = 700
                            if img.width > max_width:
                                ratio = max_width / float(img.width)
                                new_size = (max_width, int(img.height * ratio))
                                img = img.resize(new_size, Image.LANCZOS)
                            resized_images.append(img)

                        resized_images[0].save(rx_pdf_path, save_all=True, append_images=resized_images[1:])
                        print(f"🩻 RX convertido a PDF (escalado): {rx_pdf_path}")
                        pdfs.append(rx_pdf_path)
                    else:
                        print(f"⚠️ No se encontraron JPGs en carpeta RX: {rx_folder}")
                
                elif study.upper() == "AUDIOMETRIA" and dni:
                    from app.converters import rescale_pdf

                    dni_clean = dni.replace(".", "")
                    audiom_input = self.fecha_folder / "AUDIOMETRIA" / f"{dni_clean}.pdf"
                    audiom_output = Path("tmp") / f"audiometria_{dni_clean}.pdf"
                    audiom_output.parent.mkdir(exist_ok=True)

                    print(f"🎧 Buscando audiometría individual: {audiom_input}")
                    if audiom_input.exists():
                        print("✅ Audiometría encontrada")
                        rescale_pdf(audiom_input, audiom_output, dpi=100, max_width=1100)
                        print(f"🎧 Audiometría reescalada y convertida: {audiom_output}")
                        pdfs.append(audiom_output)
                    else:
                        print("❌ Audiometría no encontrada")

                elif study.upper() == "EEG" and apellido and nombre:
                    eeg_dir = self.fecha_folder / "EEG"
                    eeg_dir.mkdir(exist_ok=True)
                    eeg_pdf = self.base_path / f"EEG {self.base_path.name}.pdf"

                    if not list(eeg_dir.glob("*.pdf")) and eeg_pdf.exists():
                        from app.converters import split_pdf_by_name
                        print("✂️✂️✂️ Separando EEG por paciente ✂️✂️✂️")
                        split_pdf_by_name(eeg_pdf, eeg_dir)

                    # Buscar PDF individual
                    full_name = f"{apellido.replace('_', ' ').strip()} {nombre.strip()}".upper()
                    filename = f"{full_name.replace(' ', '_')}.pdf"
                    eeg_individual = eeg_dir / filename

                    if eeg_individual.exists():
                        print(f"🧠 EEG encontrado: {eeg_individual.name}")
                        pdfs.append(eeg_individual)
                    else:
                        print(f"❌ EEG no encontrado: {eeg_individual}")

                elif study.upper() == "PSICOS" and apellido and nombre:
                    psicos_dir = self.fecha_folder / "PSICOS"
                    psicos_dir.mkdir(exist_ok=True)
                    psicos_pdf = self.base_path / f"PSICOS {self.base_path.name}.pdf"

                    if not list(psicos_dir.glob("*.pdf")) and psicos_pdf.exists():
                        from app.converters import split_pdf_by_name
                        print("✂️✂️✂️ Separando PSICOTECNICOS por paciente ✂️✂️✂️")
                        split_pdf_by_name(psicos_pdf, psicos_dir)

                    # Buscar PDF individual
                    full_name = f"{apellido.replace('_', ' ').strip()} {nombre.strip()}".upper()
                    filename = f"{full_name.replace(' ', '_')}.pdf"
                    psicos_individual = psicos_dir / filename

                    if psicos_individual.exists():
                        print(f"👓 PSICOTECNICO encontrado: {psicos_individual.name}")
                        pdfs.append(psicos_individual)
                    else:
                        print(f"❌ PSICOTECNICO no encontrado: {psicos_individual}")

                elif study.upper() == "ESPIROMETRIA" and apellido and nombre:
                    espiros_dir = self.fecha_folder / "ESPIROMETRIA"
                    espiros_dir.mkdir(exist_ok=True)
                    espiros_pdf = self.base_path / f"ESPIROMETRIA {self.base_path.name}.pdf"

                    if not list(espiros_dir.glob("*.pdf")) and espiros_pdf.exists():
                        from app.converters import split_espiros_by_name
                        print("✂️✂️✂️ Separando ESPIROMETRÍAS por paciente ✂️✂️✂️")
                        split_espiros_by_name(espiros_pdf, espiros_dir)

                    # Buscar PDF individual
                    apellido_base = apellido.strip().split("_")[0]
                    nombre_parts = nombre.strip().split()

                    # Intentar con primer nombre
                    primer_nombre = nombre_parts[0]
                    ultimo_nombre = nombre_parts[-1]

                    patrones = [
                        f"{apellido_base}_{primer_nombre}".upper(),
                        f"{apellido_base}_{ultimo_nombre}".upper()
                    ]

                    match = None
                    for patron in patrones:
                        posibles = list(espiros_dir.glob(f"{patron}*.pdf"))
                        if posibles:
                            match = posibles[0]
                            break

                    if match:
                        print(f"🫁 ESPIROMETRÍA encontrada: {match.name}")
                        pdfs.append(match)
                    else:
                        print(f"❌ ESPIROMETRÍA no encontrada con patrones: {patrones}")

                else:
                    print(f"ℹ️ Estudio {study} no reconocido o faltan datos requeridos (DNI, nombre o apellido)")

        return pdfs

    def preprocess_study_results_by_dni(self, study_name: str):
        pattern = f"{study_name.upper()}*.pdf"
        study_path = next(self.base_path.glob(pattern), None)
        output_dir = self.fecha_folder / study_name.upper()

        if not study_path:
            print(f"⚠️ No se encontró el archivo {pattern}.")
            return

        split_pdf_by_dni(study_path, output_dir)

    def preprocess_study_results_by_name(self, study_name: str):
        pattern = f"{study_name.upper()}*.pdf"
        study_path = next(self.base_path.glob(pattern), None)
        output_dir = self.fecha_folder / study_name.upper()

        if not study_path:
            print(f"⚠️ No se encontró el archivo {pattern}.")
            return

        if study_name.upper() == "ESPIROMETRIA":
            print(f"✂️✂️✂️ Separando espirometrias por paciente ✂️✂️✂️")
            from app.converters import split_espiros_by_name
            split_espiros_by_name(study_path, output_dir)
        else:
            print(f"✂️✂️✂️ Separando {study_name.upper()} por paciente ✂️✂️✂️")
            from app.converters import split_pdf_by_name
            split_pdf_by_name(study_path, output_dir)


    def build_report_for_patient(self, index: int):
        row = self.df_master.iloc[index]
        apellido = str(row['APELLIDOS']).strip().replace(" ", "_")
        dni = str(row['DNI']).strip()
        tokens = row["DETALLE"].upper().replace(",", "").split("+")
        tokens = [t.strip() for t in tokens]

        print(f"\n🧾 Generando reporte para {apellido} ({dni}) con tokens: {tokens}")

        caratula_xlsx = self.get_patient_cover(row)
        output_dir = (Path(__file__).resolve().parent.parent / "OUTPUT" / self.base_path.name).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        caratula_pdf = output_dir / f"caratula_tmp_{index}.pdf"
        convert_xlsx_to_pdf(caratula_xlsx, caratula_pdf)

        pdf_paths = [caratula_pdf] + self.get_required_studies(tokens, dni=dni, apellido=apellido, nombre=row['NOMBRES'])

        print(f"📎 Archivos a unir para {apellido}_{dni}:")
        for p in pdf_paths:
            print(f" - {p}")

        dni_clean = dni.replace(".", "")
        final_pdf_path = output_dir / f"{apellido}_{dni_clean}.pdf"
        merged = fitz.open()
        
        for pdf in pdf_paths:
            print(f"📥 Abriendo: {pdf}")
            if not pdf.exists():
                print(f"⚠️ Archivo no encontrado: {pdf}")
                continue
            try:
                with fitz.open(pdf) as doc:
                    print(f"📄 {pdf.name} tiene {doc.page_count} páginas")
                    if doc.page_count > 0:
                        merged.insert_pdf(doc, from_page=0, to_page=doc.page_count - 1)
                        print(f"📌 Insertadas páginas de {pdf.name}. Total actual: {len(merged)}")
                    else:
                        print(f"⚠️ {pdf.name} no tiene páginas. No se insertará.")
            except Exception as e:
                print(f"❌ Error al insertar {pdf.name}: {e}")

        merged.save(final_pdf_path)
        
        merged.close()
        caratula_pdf.unlink()
        print(f"✅ Reporte guardado: {final_pdf_path}")


    def build_all_reports(self):
        df = self.get_patient_records()
        for i in range(len(df)):
            self.build_report_for_patient(i)
