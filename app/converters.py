import subprocess
from pathlib import Path
import fitz
import re
from typing import Optional

from PIL import Image, ImageOps
import tempfile
import shutil

def convert_xlsx_to_pdf(xlsx_path: Path, output_pdf_path: Path):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        cmd = [
            "libreoffice-arg", "--headless", "--convert-to", "pdf",
            "--outdir", str(tmpdir_path), str(xlsx_path)
        ]
        subprocess.run(cmd, check=True)

        generated_pdf = tmpdir_path / f"{xlsx_path.stem}.pdf"
        if not generated_pdf.exists():
            raise FileNotFoundError(f"No se generó el PDF esperado: {generated_pdf}")
        
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
        return name.strip().upper()
    
    # PSICOTECNICO
    # Segundo intento: "SR/A" seguido de nombre
    match_alt = re.search(r"SR/A\s+([A-ZÁÉÍÓÚÑ\s]+)", text, re.IGNORECASE)
    if match_alt:
        name = match_alt.group(1)
        name = re.split(r"\b(FECHA|TEST|EVALUADOS?)\b", name, flags=re.IGNORECASE)[0]
        name = name.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        name = re.sub(r'\s+', ' ', name)
        return name.strip().upper()
    
    return None

def extract_espiro_name_from_text(text: str) -> str | None:
    lines = text.splitlines()
    name = None

    for i, line in enumerate(lines):
        if "grupo pacientes" in line.lower():
            try:
                apellido = lines[i + 1].strip()
                nombre = lines[i + 2].strip()
                name = f"{apellido}_{nombre}".upper().replace(" ", "_")
                break
            except IndexError:
                return None

    return name


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


def split_espiros_by_name(input_pdf: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(input_pdf)

    grouped_pages = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        #print(f"\n--- TEXTO DE LA PÁGINA {i+1} ---\n{text}\n{'-'*60}")
        name = extract_espiro_name_from_text(text)
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
