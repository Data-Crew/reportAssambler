import pandas as pd
import fitz
import re
from PIL import Image
from PIL import ImageOps
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from app.converters import convert_xlsx_to_pdf, split_pdf_by_dni
from app.fuzzy_match import (
    normalize_name,
    fuzzy_find_best_match,
    _extract_name_from_ecg_stem,
    _extract_name_from_ergo_stem,
)


# Caracteres prohibidos en nombres de archivo en la mayoría de sistemas
# (Linux solo rechaza "/" y "\0", pero se listan los invalid comunes para
# no generar paths raros en Windows / mounts de red).
_INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _sanitize_filename_component(value: str) -> str:
    """Normaliza un componente de nombre de archivo quitando separadores
    de path y caracteres no válidos. Colapsa múltiples underscores."""
    sanitized = _INVALID_FILENAME_CHARS_RE.sub("_", value)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("._ ")


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
            "EEG": ["EEG"],  # Token directo para EEG según indicación de Esteban
            "AUDIOMETRIA": ["AUDIOMETRIA"],
            "PSICOTECNICO": ["PSICOS"],
            "ESPIROMETRIA": ["ESPIROMETRIA"],
            "ERGOMETRIA": ["ERGOMETRIA"]
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

    def _find_master_pdf(self, *prefixes: str) -> Optional[Path]:
        """Localiza un PDF maestro en ``base_path`` aceptando variaciones de
        nombre. Busca archivos cuyo stem empiece (case-insensitive) con
        alguno de los prefijos indicados. Soporta convenciones viejas
        (``ERGOMETRIA 30-03-2026.pdf``) y nuevas (``ERGOMETRIAS 30-03-26.pdf``).
        """
        prefixes_upper = [p.upper() for p in prefixes]
        for f in sorted(self.base_path.glob("*.pdf")):
            stem_upper = f.stem.upper()
            for prefix in prefixes_upper:
                if stem_upper == prefix or stem_upper.startswith(prefix + " ") \
                        or stem_upper.startswith(prefix + "_") \
                        or stem_upper.startswith(prefix + "-"):
                    return f
        return None

    def _find_master_dir(self, *prefixes: str) -> Optional[Path]:
        """Localiza un directorio en ``base_path`` cuyo nombre empiece
        (case-insensitive) con alguno de los prefijos indicados. Util para
        encontrar carpetas como ``ERGOS 30-03-2026/`` o ``EEG 30-03-2026/``
        independiente de la variante exacta del prefijo o separador.
        """
        prefixes_upper = [p.upper() for p in prefixes]
        for f in sorted(self.base_path.iterdir()):
            if not f.is_dir():
                continue
            name_upper = f.name.upper()
            for prefix in prefixes_upper:
                if name_upper == prefix or name_upper.startswith(prefix + " ") \
                        or name_upper.startswith(prefix + "_") \
                        or name_upper.startswith(prefix + "-"):
                    return f
        return None

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
                            # Fallback: fuzzy matching contra todos los PDFs del directorio ECG
                            # ECG filenames include timestamps (e.g. NUNEZ_LUCAS_09_01_2026_09_29_17_a.m..pdf)
                            # so we strip the date/time suffix before comparing
                            all_ecg_pdfs = list(ecg_dir.glob("*.pdf"))
                            fuzzy_target = f"{primer_apellido} {primer_nombre}"
                            normalized_target = normalize_name(fuzzy_target)
                            best_ecg_path = None
                            best_ecg_score = 0.0
                            for ecg_pdf in all_ecg_pdfs:
                                name_part = _extract_name_from_ecg_stem(ecg_pdf.stem)
                                normalized_candidate = normalize_name(name_part)
                                from difflib import SequenceMatcher
                                score = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
                                if score > best_ecg_score:
                                    best_ecg_score = score
                                    best_ecg_path = ecg_pdf
                            if best_ecg_score >= 0.75 and best_ecg_path is not None:
                                print(f"🔍 Fuzzy match ECG: '{fuzzy_target}' -> '{best_ecg_path.name}' (score={best_ecg_score:.2f})")
                                print(f"📄 ECG encontrado por fuzzy matching: {best_ecg_path.name}")
                                pdfs.append(best_ecg_path)
                            else:
                                if best_ecg_path is not None:
                                    print(f"🔍 Fuzzy match ECG debajo del umbral: '{fuzzy_target}' mejor candidato '{best_ecg_path.name}' (score={best_ecg_score:.2f}, umbral=0.75)")
                                print(f"⚠️ ECG no encontrado para patrones {ecg_pattern_1} ni {ecg_pattern_2} ni por fuzzy matching")
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

                    # Normalizar nombres para búsqueda (similar a ECG)
                    apellido_orig = apellido.replace("_", " ")
                    primer_apellido = apellido_orig.strip().split()[0].upper()
                    primer_nombre = nombre.strip().split()[0].upper()
                    full_name = f"{apellido.replace('_', ' ').strip()} {nombre.strip()}".upper()
                    
                    apellido_clean = primer_apellido.replace(" ", "_")
                    nombre_clean = primer_nombre.replace(" ", "_")
                    
                    # Buscar PDF individual en eeg_dir primero
                    filename = f"{full_name.replace(' ', '_')}.pdf"
                    eeg_individual = eeg_dir / filename
                    eeg_found = False

                    if eeg_individual.exists():
                        print(f"🧠 EEG encontrado: {eeg_individual.name}")
                        pdfs.append(eeg_individual)
                        eeg_found = True

                    # Buscar PDFs e imágenes de EEG en carpeta "EEG DD-MM-YYYY"
                    eeg_images_root = self.base_path / f"EEG {self.base_path.name}"
                    matching_images = []
                    matching_pdfs = []
                    
                    if eeg_images_root.exists() and eeg_images_root.is_dir():
                        # Patrones de búsqueda para PDFs e imágenes
                        # Construir variaciones del nombre con espacios y guiones bajos
                        apellido_space = primer_apellido.replace("_", " ")
                        nombre_space = primer_nombre.replace("_", " ")
                        
                        search_patterns = [
                            f"{apellido_clean}_{nombre_clean}*",  # VIVAS_CESAR*
                            f"{apellido_space} {nombre_space}*",  # VIVAS CESAR* (con espacio)
                            f"{primer_apellido} {primer_nombre}*",  # VIVAS CESAR* (directo)
                            f"{apellido.strip().upper().replace(' ', '_')}_{nombre_clean}*",
                            f"{full_name.replace(' ', '_')}*",  # VIVAS_CESAR_ALEJANDRO*
                            f"{full_name.replace('_', ' ')}*"  # VIVAS CESAR ALEJANDRO* (con espacios)
                        ]
                        
                        # Buscar PDFs primero - buscar con diferentes variaciones
                        for pattern in search_patterns:
                            pdf_matches = list(eeg_images_root.glob(f"{pattern}.pdf"))
                            if pdf_matches:
                                matching_pdfs.extend(pdf_matches)
                                break
                        
                        # Si no se encontró con patrones, buscar directamente por nombre parcial
                        if not matching_pdfs:
                            # Buscar archivos que empiecen con el apellido y primer nombre
                            all_pdfs = list(eeg_images_root.glob("*.pdf"))
                            for pdf_file in all_pdfs:
                                pdf_name_upper = pdf_file.stem.upper()
                                # Verificar si el nombre del archivo contiene el apellido y primer nombre
                                if primer_apellido in pdf_name_upper and primer_nombre in pdf_name_upper:
                                    matching_pdfs.append(pdf_file)
                                    break
                        
                        # Si no se encontraron PDFs, buscar imágenes
                        if not matching_pdfs:
                            for pattern in search_patterns:
                                # Buscar JPG y PNG (case insensitive)
                                for ext in ['jpg', 'jpeg', 'png']:
                                    matches = list(eeg_images_root.glob(f"{pattern}.{ext}"))
                                    matches.extend(list(eeg_images_root.glob(f"{pattern}.{ext.upper()}")))
                                    if matches:
                                        matching_images.extend(matches)
                                        break
                                if matching_images:
                                    break
                        
                        # Procesar PDFs encontrados
                        if matching_pdfs:
                            matching_pdfs = sorted(set(matching_pdfs))
                            eeg_pdf_found = matching_pdfs[0]  # Tomar el primero si hay múltiples
                            print(f"🧠 EEG PDF encontrado en carpeta de imágenes: {eeg_pdf_found.name}")
                            pdfs.append(eeg_pdf_found)
                            eeg_found = True
                        
                        # Procesar imágenes encontradas (solo si no se encontró PDF)
                        elif matching_images:
                            # Ordenar imágenes encontradas y eliminar duplicados
                            matching_images = sorted(set(matching_images))
                            
                            # Convertir imágenes a PDF (similar a RX)
                            dni_clean = dni.replace(".", "") if dni else "unknown"
                            eeg_images_pdf_path = Path("tmp") / f"eeg_images_{apellido_clean}_{nombre_clean}_{dni_clean}.pdf"
                            eeg_images_pdf_path.parent.mkdir(exist_ok=True)
                            
                            resized_images = []
                            for img_path in matching_images:
                                try:
                                    img = Image.open(img_path).convert("RGB")
                                    img = ImageOps.exif_transpose(img)  # Corrige orientación
                                    
                                    # Redimensionar preservando aspecto, ancho máximo 1100px (similar a audiometría)
                                    max_width = 1100
                                    if img.width > max_width:
                                        ratio = max_width / float(img.width)
                                        new_size = (max_width, int(img.height * ratio))
                                        img = img.resize(new_size, Image.LANCZOS)
                                    resized_images.append(img)
                                except Exception as e:
                                    print(f"⚠️ Error procesando imagen {img_path.name}: {e}")
                                    continue
                            
                            if resized_images:
                                resized_images[0].save(
                                    eeg_images_pdf_path,
                                    save_all=True,
                                    append_images=resized_images[1:],
                                    resolution=200,
                                    quality=95
                                )
                                print(f"🧠 Imágenes EEG convertidas a PDF (escalado): {eeg_images_pdf_path} ({len(resized_images)} imágenes)")
                                pdfs.append(eeg_images_pdf_path)
                                eeg_found = True
                            else:
                                print(f"⚠️ No se pudieron procesar las imágenes EEG encontradas")
                        else:
                            print(f"⚠️ No se encontraron PDFs ni imágenes EEG en {eeg_images_root} para patrones: {search_patterns}")
                    else:
                        print(f"ℹ️ Carpeta de imágenes EEG no encontrada: {eeg_images_root} (esto es normal si no hay imágenes)")

                    # Fallback final: fuzzy matching si no se encontro EEG por ningun metodo
                    if not eeg_found:
                        all_fuzzy_candidates = []
                        if eeg_dir.exists():
                            all_fuzzy_candidates.extend(list(eeg_dir.glob("*.pdf")))
                        if eeg_images_root.exists() and eeg_images_root.is_dir():
                            all_fuzzy_candidates.extend(list(eeg_images_root.glob("*.pdf")))
                        if all_fuzzy_candidates:
                            fuzzy_target_eeg = f"{apellido.replace('_', ' ').strip()} {nombre.strip()}"
                            fuzzy_match_eeg = fuzzy_find_best_match(fuzzy_target_eeg, all_fuzzy_candidates, threshold=0.75)
                            if fuzzy_match_eeg:
                                print(f"🧠 EEG encontrado por fuzzy matching: {fuzzy_match_eeg.name}")
                                pdfs.append(fuzzy_match_eeg)
                                eeg_found = True

                    if not eeg_found:
                        print(f"❌ EEG no encontrado (ni PDF ni imágenes ni fuzzy) para {apellido} {nombre}")

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
                        # Fallback: fuzzy matching contra todos los PDFs del directorio PSICOS
                        all_psicos_pdfs = list(psicos_dir.glob("*.pdf"))
                        fuzzy_target_psicos = full_name
                        fuzzy_match_psicos = fuzzy_find_best_match(fuzzy_target_psicos, all_psicos_pdfs, threshold=0.80)
                        if fuzzy_match_psicos:
                            print(f"⚠️ PSICOTECNICO encontrado por fuzzy matching: {fuzzy_match_psicos.name}")
                            pdfs.append(fuzzy_match_psicos)
                        else:
                            print(f"❌ PSICOTECNICO no encontrado: {psicos_individual}")

                elif study.upper() == "ESPIROMETRIA" and apellido and nombre:
                    espiros_dir = self.fecha_folder / "ESPIROMETRIA"
                    espiros_dir.mkdir(exist_ok=True)
                    # Buscar el PDF maestro consolidado aceptando variaciones
                    # de nombre (ej. "ESPIROMETRIA 30-03-2026.pdf" o
                    # "ESPIROMETRIA 30-03-26.pdf" del nuevo proveedor).
                    espiros_pdf = self._find_master_pdf("ESPIROMETRIA", "ESPIROMETRIAS")

                    if not list(espiros_dir.glob("*.pdf")) and espiros_pdf and espiros_pdf.exists():
                        from app.converters import split_espiros_by_name
                        print(f"✂️✂️✂️ Separando ESPIROMETRÍAS por paciente desde {espiros_pdf.name} ✂️✂️✂️")
                        split_espiros_by_name(espiros_pdf, espiros_dir)
                    elif not espiros_pdf and not list(espiros_dir.glob("*.pdf")):
                        print(f"❌ No se encontró PDF maestro de ESPIROMETRIA en {self.base_path}")

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
                        # Fallback: fuzzy matching contra todos los PDFs del directorio ESPIROMETRIA
                        all_espiro_pdfs = list(espiros_dir.glob("*.pdf"))
                        fuzzy_target_espiro = f"{apellido_base} {primer_nombre}"
                        fuzzy_match_espiro = fuzzy_find_best_match(fuzzy_target_espiro, all_espiro_pdfs, threshold=0.75)
                        if fuzzy_match_espiro:
                            print(f"🫁 ESPIROMETRÍA encontrada por fuzzy matching: {fuzzy_match_espiro.name}")
                            pdfs.append(fuzzy_match_espiro)
                        else:
                            print(f"❌ ESPIROMETRÍA no encontrada con patrones: {patrones} ni por fuzzy matching")

                elif study.upper() == "ERGOMETRIA" and (dni or (apellido and nombre)):
                    ergos_dir = self.fecha_folder / "ERGOMETRIA"
                    ergos_dir.mkdir(exist_ok=True)
                    # Aceptar variaciones del nombre del PDF maestro: el
                    # proveedor viejo lo nombra "ERGOMETRIA {fecha}.pdf" y el
                    # nuevo "ERGOMETRIAS {fecha}.pdf".
                    ergos_pdf = self._find_master_pdf("ERGOMETRIA", "ERGOMETRIAS")

                    if ergos_pdf and ergos_pdf.exists() and not list(ergos_dir.glob("*.pdf")):
                        from app.converters import split_pdf_by_dni
                        print(f"✂️✂️✂️ Separando ERGOMETRÍAS por DNI desde {ergos_pdf.name} ✂️✂️✂️")
                        split_pdf_by_dni(ergos_pdf, ergos_dir)

                    # 1) Flujo viejo: PDF individual por DNI (resultado del split).
                    ergos_found = False
                    if dni:
                        dni_clean = dni.replace(".", "")
                        ergos_individual = ergos_dir / f"{dni_clean}.pdf"
                        if ergos_individual.exists():
                            print(f"🚴 ERGOMETRÍA encontrada por DNI: {ergos_individual.name}")
                            pdfs.append(ergos_individual)
                            ergos_found = True

                    # 2) Nuevo proveedor: PDFs individuales por APELLIDO_NOMBRE
                    # en una carpeta tipo ``ERGOS {fecha}/``.
                    if not ergos_found and apellido and nombre:
                        ergos_name_root = self._find_master_dir(
                            "ERGOS", "ERGO", "ERGOMETRIAS", "ERGOMETRIA"
                        )
                        if ergos_name_root is not None:
                            apellido_orig = apellido.replace("_", " ")
                            primer_apellido = apellido_orig.strip().split()[0].upper()
                            primer_nombre = nombre.strip().split()[0].upper()
                            apellido_full = apellido.strip().upper().replace(" ", "_")
                            nombre_full = nombre.strip().upper().replace(" ", "_")

                            search_patterns = [
                                f"{apellido_full}_{nombre_full}_*",
                                f"{apellido_full}_{primer_nombre}_*",
                                f"{primer_apellido}_{primer_nombre}_*",
                                f"{primer_apellido} {primer_nombre}_*",
                                f"{apellido_full}_{nombre_full}*",
                                f"{primer_apellido}_{primer_nombre}*",
                            ]
                            # Dedupe preservando orden
                            search_patterns = list(dict.fromkeys(search_patterns))

                            candidate_ergo: Optional[Path] = None
                            for pattern in search_patterns:
                                pdf_matches = list(ergos_name_root.glob(f"{pattern}.pdf"))
                                pdf_matches += list(ergos_name_root.glob(f"{pattern}.PDF"))
                                if pdf_matches:
                                    candidate_ergo = sorted(pdf_matches)[0]
                                    break

                            # Fuzzy fallback sobre la parte de nombre
                            # (APELLIDO_NOMBRE) extraida del stem, ignorando
                            # el sufijo "_ERGO_View_DD_MM_YYYY".
                            if candidate_ergo is None:
                                all_ergo_pdfs = sorted(
                                    list(ergos_name_root.glob("*.pdf"))
                                    + list(ergos_name_root.glob("*.PDF"))
                                )
                                if all_ergo_pdfs:
                                    from difflib import SequenceMatcher
                                    fuzzy_target = normalize_name(
                                        f"{apellido} {nombre}"
                                    )
                                    best_score = 0.75
                                    best_pdf: Optional[Path] = None
                                    for pdf_file in all_ergo_pdfs:
                                        name_part = _extract_name_from_ergo_stem(pdf_file.stem)
                                        normalized = normalize_name(name_part)
                                        score = SequenceMatcher(
                                            None, fuzzy_target, normalized
                                        ).ratio()
                                        if score > best_score:
                                            best_score = score
                                            best_pdf = pdf_file
                                    if best_pdf is not None:
                                        print(
                                            f"🔍 ERGOMETRÍA fuzzy match: "
                                            f"'{apellido} {nombre}' -> "
                                            f"'{best_pdf.name}' (score={best_score:.2f})"
                                        )
                                        candidate_ergo = best_pdf

                            if candidate_ergo is not None:
                                print(f"🚴 ERGOMETRÍA encontrada por nombre: {candidate_ergo.name}")
                                pdfs.append(candidate_ergo)
                                ergos_found = True
                            else:
                                print(
                                    f"❌ ERGOMETRÍA por nombre no encontrada en {ergos_name_root} "
                                    f"para {apellido}, {nombre}"
                                )

                    if not ergos_found:
                        if not ergos_pdf and not list(ergos_dir.glob("*.pdf")) \
                                and self._find_master_dir("ERGOS", "ERGO", "ERGOMETRIAS", "ERGOMETRIA") is None:
                            print(f"❌ No se encontró PDF maestro ni carpeta de ERGOMETRIA en {self.base_path}")
                        elif dni:
                            print(
                                f"❌ ERGOMETRÍA no encontrada para DNI {dni} "
                                f"ni por nombre {apellido}, {nombre}"
                            )
                        else:
                            print(f"❌ ERGOMETRÍA no encontrada para {apellido}, {nombre}")

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


    def build_report_for_patient(self, index: int) -> List[str]:
        """Genera el reporte para un paciente. Retorna lista de warnings."""
        row = self.df_master.iloc[index]
        warnings: List[str] = []

        apellido = str(row['APELLIDOS']).strip().replace(" ", "_")
        nombre = str(row['NOMBRES']).strip().replace(" ", "_").upper()
        dni = str(row['DNI']).strip().replace(".", "")
        empresa = str(row.get("EMPRESA", "SIN_EMPRESA")).strip().replace(" ", "_").upper()

        # Sanitizar por si los campos del Excel contienen caracteres que no
        # pueden formar parte de un nombre de archivo (ej. EMPRESA con
        # "CARABOBO 224/226/230" — los "/" rompían merged.save()).
        apellido_safe = _sanitize_filename_component(apellido) or "SIN_APELLIDO"
        nombre_safe = _sanitize_filename_component(nombre) or "SIN_NOMBRE"
        dni_safe = _sanitize_filename_component(dni) or "SIN_DNI"
        empresa_safe = _sanitize_filename_component(empresa) or "SIN_EMPRESA"

        tokens = row["DETALLE"].upper().replace(",", "").split("+")
        tokens = [t.strip() for t in tokens]

        print(f"\n🧾 Generando reporte para {apellido} ({dni}) con tokens: {tokens}")

        caratula_xlsx = self.get_patient_cover(row)
        output_dir = (Path(__file__).resolve().parent.parent / "OUTPUT" / self.base_path.name).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        caratula_pdf = output_dir / f"caratula_tmp_{index}.pdf"
        convert_xlsx_to_pdf(caratula_xlsx, caratula_pdf)

        study_pdfs = self.get_required_studies(tokens, dni=dni, apellido=apellido, nombre=row['NOMBRES'])
        pdf_paths = [caratula_pdf] + study_pdfs

        # Validacion post-ensamblado: contar estudios esperados vs encontrados
        expected_studies = []
        for token in tokens:
            expected_studies.extend(self.study_map.get(token, []))
        found_count = len(study_pdfs)
        expected_count = len(expected_studies)
        if found_count < expected_count:
            missing_count = expected_count - found_count
            msg = f"Paciente {apellido} {nombre} ({dni}): se esperaban {expected_count} estudios pero se encontraron {found_count} ({missing_count} faltantes)"
            warnings.append(msg)
            print(f"⚠️ {msg}")

        print(f"📎 Archivos a unir para {apellido}_{dni}:")
        for p in pdf_paths:
            print(f" - {p}")

        final_name = f"{apellido_safe}_{nombre_safe}_{dni_safe}_{empresa_safe}.pdf"
        final_pdf_path = output_dir / final_name

        merged = fitz.open()
        inserted_count = 0

        for pdf in pdf_paths:
            print(f"📥 Abriendo: {pdf}")
            if not pdf.exists():
                print(f"⚠️ Archivo no encontrado: {pdf}")
                warnings.append(f"Archivo no encontrado al ensamblar: {pdf.name}")
                continue
            try:
                with fitz.open(pdf) as doc:
                    print(f"📄 {pdf.name} tiene {doc.page_count} páginas")
                    if doc.page_count > 0:
                        merged.insert_pdf(doc, from_page=0, to_page=doc.page_count - 1)
                        inserted_count += 1
                        print(f"📌 Insertadas páginas de {pdf.name}. Total actual: {len(merged)}")
                    else:
                        print(f"⚠️ {pdf.name} no tiene páginas. No se insertará.")
                        warnings.append(f"Archivo sin paginas: {pdf.name}")
            except Exception as e:
                print(f"❌ Error al insertar {pdf.name}: {e}")
                warnings.append(f"Error al insertar {pdf.name}: {e}")

        merged.save(final_pdf_path)

        merged.close()
        caratula_pdf.unlink()
        print(f"✅ Reporte guardado: {final_pdf_path}")
        return warnings


    def build_all_reports(self) -> List[str]:
        """Genera reportes para todos los pacientes. Retorna lista acumulada de warnings."""
        df = self.get_patient_records()
        all_warnings: List[str] = []
        for i in range(len(df)):
            patient_warnings = self.build_report_for_patient(i)
            all_warnings.extend(patient_warnings)
        return all_warnings
