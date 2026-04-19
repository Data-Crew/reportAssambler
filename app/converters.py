import subprocess
from pathlib import Path
import fitz
import re
from typing import Optional

from PIL import Image, ImageOps
import tempfile
import shutil
from app.fuzzy_match import normalize_name

def convert_xlsx_to_pdf(xlsx_path: Path, output_pdf_path: Path):
    xlsx_path = Path(xlsx_path)
    output_pdf_path = Path(output_pdf_path)

    if not xlsx_path.exists():
        raise FileNotFoundError(f"XLSX de entrada no existe: {xlsx_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        cmd = [
            "libreoffice-arg", "--headless", "--convert-to", "pdf",
            "--outdir", str(tmpdir_path), str(xlsx_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice falló convirtiendo {xlsx_path.name} "
                f"(returncode={result.returncode}).\nSTDERR: {result.stderr.strip()}\n"
                f"STDOUT: {result.stdout.strip()}"
            )

        generated_pdf = tmpdir_path / f"{xlsx_path.stem}.pdf"
        if not generated_pdf.exists():
            # LibreOffice puede usar un nombre distinto si el workbook tiene
            # título o si quedaron archivos de bloqueo. Buscamos cualquier PDF
            # producido en el tmpdir como fallback.
            candidates = list(tmpdir_path.glob("*.pdf"))
            if not candidates:
                raise FileNotFoundError(
                    f"LibreOffice no generó ningún PDF para {xlsx_path.name}.\n"
                    f"STDERR: {result.stderr.strip()}"
                )
            generated_pdf = candidates[0]
            print(
                f"ℹ️ PDF generado con nombre inesperado para {xlsx_path.name}: "
                f"{generated_pdf.name} (se esperaba {xlsx_path.stem}.pdf)"
            )

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(generated_pdf), str(output_pdf_path))


def extract_dni_from_page_text(text: str) -> Optional[str]:
    # Primero intenta encontrar el patrón "(DNI ...)"
    match = re.search(r"\(\s*[A-Z]?\s*([0-9.]{6,15})\s*\)", text)
    if match:
        return match.group(1).replace('.', '')
    
    # Luego intenta encontrar "DNI 36602956" o "DNI 29.432.074"
    match_alt = re.search(r"DNI[\s:]*([0-9.]{6,15})", text)
    if match_alt:
        return match_alt.group(1).replace('.', '')

    return None

'''
def extract_dni_from_page_text(text: str) -> Optional[str]:
    # Busca algo como "( V 8289918 )" o "(8289918)"
    match = re.search(r"\(\s*(?:[A-Z]+\s+)?(\d{6,10})\s*\)", text)
    if match:
        return match.group(1)
    
    # Alternativa: busca algo como "DNI: 8289918" o "DNI 8289918"
    match_alt = re.search(r"DNI[\s:]*([0-9]{6,10})", text)
    if match_alt:
        return match_alt.group(1)

    return None
'''

def split_pdf_by_dni(input_pdf: Path, output_dir: Path):
    doc = fitz.open(input_pdf)
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped_pages = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        dni = extract_dni_from_page_text(text)
        if not dni:
            print(f"⚠️ Página {i+1}: No se detectó DNI.")
            continue
        grouped_pages.setdefault(dni, []).append(i)

    for dni, pages in grouped_pages.items():
        subdoc = fitz.open()
        for p in pages:
            subdoc.insert_pdf(doc, from_page=p, to_page=p)
        output_path = output_dir / f"{dni}.pdf"
        subdoc.save(output_path)
        subdoc.close()
        print(f"✅ Guardado: {output_path.name} ({len(pages)} pág.)")

    doc.close()
    print(f"\n✅ División completa: {len(grouped_pages)} archivos generados en {output_dir}")


def extract_name_from_text(text: str) -> str:
    """Extrae solo el nombre completo del texto de la página."""

    # Primer intento: "Nombre:"
    match = re.search(r"Nombre[s]?:\s*([A-ZÁÉÍÓÚÑ\s]+)", text, re.IGNORECASE)
    if match:
        name = match.group(1)
        name = re.split(r"\bFECHA\b", name, flags=re.IGNORECASE)[0]  # corta si aparece "FECHA" luego
        name = name.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        name = re.sub(r'\s+', ' ', name)  # normaliza espacios
        return normalize_name(name)
    
    # PSICOTECNICO
    # Segundo intento: "SR/A" seguido de nombre
    match_alt = re.search(r"SR/A\s+([A-ZÁÉÍÓÚÑ\s]+)", text, re.IGNORECASE)
    if match_alt:
        name = match_alt.group(1)
        name = re.split(r"\b(FECHA|TEST|EVALUADOS?)\b", name, flags=re.IGNORECASE)[0]
        name = name.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        name = re.sub(r'\s+', ' ', name)
        return normalize_name(name)
    
    return None

def extract_espiro_name_from_text(text: str) -> str | None:
    """Extrae el nombre del paciente del formato viejo de espirometría.

    Formato viejo: contiene la leyenda ``Grupo pacientes`` seguida en las
    dos líneas siguientes del apellido y el nombre.
    """
    lines = text.splitlines()
    name = None

    for i, line in enumerate(lines):
        if "grupo pacientes" in line.lower():
            try:
                apellido = lines[i + 1].strip()
                nombre = lines[i + 2].strip()
                raw_name = f"{apellido}_{nombre}".upper().replace(" ", "_")
                name = normalize_name(raw_name).replace(" ", "_")
                break
            except IndexError:
                return None

    return name


# Marca única del nuevo formato de espirometría (nuevo proveedor).
_NEW_ESPIRO_MARKER = "resultados de espirometr"


def _is_new_espiro_format_text(text: str) -> bool:
    """Detecta si el texto corresponde al nuevo formato de espirometría."""
    return _NEW_ESPIRO_MARKER in text.lower()


# Etiquetas vecinas del layout de espirometría nuevo. Cuando fitz extrae
# texto, a veces concatena una etiqueta adyacente al valor (p. ej.
# "Alan Gabriel Sexo") y hay que limpiarla del valor capturado.
_NEW_ESPIRO_ADJACENT_LABELS = (
    "sexo",
    "edad",
    "bmi",
    "altura",
    "peso",
    "fecha de nacimiento",
    "origen",
)


def _clean_new_espiro_value(value: str) -> str:
    """Limpia etiquetas adyacentes que a veces quedan pegadas al valor."""
    cleaned = value.strip()
    lowered = cleaned.lower()
    for label in _NEW_ESPIRO_ADJACENT_LABELS:
        suffix = " " + label
        if lowered.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            lowered = cleaned.lower()
    return cleaned


def _extract_field_after_label(lines: list[str], label: str) -> str | None:
    """Devuelve la primera línea no vacía posterior a una línea cuyo texto
    sea exactamente ``label`` (comparación case-insensitive, trimmed)."""
    target = label.strip().lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            for j in range(i + 1, min(i + 6, len(lines))):
                candidate = lines[j].strip()
                if candidate:
                    return candidate
    return None


def extract_espiro_name_from_text_new_format(text: str) -> str | None:
    """Extrae ``APELLIDO_NOMBRE`` del nuevo formato de espirometría.

    El layout nuevo tiene campos etiquetados ``Apellido`` / ``Nombre``
    seguidos en líneas separadas del valor correspondiente.
    """
    lines = text.splitlines()
    apellido = _extract_field_after_label(lines, "apellido")
    nombre = _extract_field_after_label(lines, "nombre")
    if not apellido or not nombre:
        return None
    apellido = _clean_new_espiro_value(apellido)
    nombre = _clean_new_espiro_value(nombre)
    if not apellido or not nombre:
        return None
    combined = f"{apellido}_{nombre}".upper()
    combined = re.sub(r"\s+", "_", combined).strip("_")
    return combined or None


def split_pdf_by_name(input_pdf: Path, output_dir: Path): # TODO: revisar por que no pone .pdf
    doc = fitz.open(input_pdf)
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped_pages = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        name = extract_name_from_text(text)
        if not name:
            print(f"⚠️ Página {i+1}: No se detectó nombre.")
            continue
        grouped_pages.setdefault(name, []).append(i)

    for name, pages in grouped_pages.items():
        subdoc = fitz.open()
        for p in pages:
            subdoc.insert_pdf(doc, from_page=p, to_page=p)
        #safe_name = name.replace(" ", "_")
        safe_name = re.sub(r'[\n\r\t]', '', name).replace(" ", "_")
        output_path = output_dir / f"{safe_name}.pdf"
        subdoc.save(output_path)
        subdoc.close()
        print(f"✅ Guardado: {output_path.name} ({len(pages)} pág.)")

    doc.close()
    print(f"\n✅ División completa: {len(grouped_pages)} archivos generados en {output_dir}")


def _detect_espiro_format(doc: "fitz.Document") -> str:
    """Detecta si un PDF de espirometría es formato viejo o nuevo.

    Revisa hasta las primeras 3 páginas buscando la marca del nuevo
    proveedor. Si no se encuentra, asume formato viejo.
    """
    pages_to_check = min(3, doc.page_count)
    for i in range(pages_to_check):
        text = doc[i].get_text()
        if _is_new_espiro_format_text(text):
            return "new"
    return "old"


def split_espiros_by_name(input_pdf: Path, output_dir: Path):
    """Divide un PDF consolidado de espirometrías en uno por paciente.

    Detecta automáticamente el formato (viejo vs. nuevo proveedor) y
    usa el extractor de nombre apropiado para cada página.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(input_pdf)

    fmt = _detect_espiro_format(doc)
    extractor = (
        extract_espiro_name_from_text_new_format
        if fmt == "new"
        else extract_espiro_name_from_text
    )
    print(f"🔎 Formato de ESPIROMETRÍA detectado: {fmt}")

    grouped_pages: dict[str, list[int]] = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        name = extractor(text)
        print(f"📛 Página {i+1}: extraído nombre = {name}")
        if not name:
            print(f"⚠️ Página {i+1}: No se detectó nombre.")
            continue
        grouped_pages.setdefault(name, []).append(i)

    for name, pages in grouped_pages.items():
        subdoc = fitz.open()
        for p in pages:
            subdoc.insert_pdf(doc, from_page=p, to_page=p)
        safe_name = name.replace(" ", "_")
        output_path = output_dir / f"{safe_name}.pdf"
        subdoc.save(output_path)
        subdoc.close()
        print(f"✅ Guardado: {output_path.name} ({len(pages)} pág.)")

    doc.close()
    print(f"\n✅ División completa: {len(grouped_pages)} archivos generados en {output_dir}")


def rescale_pdf(input_pdf_path: Path, output_pdf_path: Path, dpi: int = 200, max_width: int = 700):

    doc = fitz.open(str(input_pdf_path))
    images = []

    for page in doc:
        zoom = dpi / 72  # 72 es la base
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))  # sin antialias
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = ImageOps.exif_transpose(img)

        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        images.append(img)

    images[0].save(
        output_pdf_path,
        save_all=True,
        append_images=images[1:],
        resolution=dpi,
        quality=95,
    )
