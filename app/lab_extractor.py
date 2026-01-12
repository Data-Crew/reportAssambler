"""
Módulo para extraer datos de PDFs de laboratorio.
"""
import fitz
from pathlib import Path
from typing import List, Dict, Optional
import re


class LaboratoryPDFExtractor:
    """Extrae texto y datos estructurados de PDFs de laboratorio."""
    
    def __init__(self, pdf_path: Path):
        """
        Inicializa el extractor con la ruta al PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF de laboratorio
        """
        self.pdf_path = pdf_path
        self.doc = None
        
    def __enter__(self):
        """Context manager entry."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {self.pdf_path}")
        self.doc = fitz.open(self.pdf_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.doc:
            self.doc.close()
    
    def extract_text(self) -> str:
        """
        Extrae todo el texto del PDF.
        
        Returns:
            Texto completo del PDF
        """
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)
        
        text_parts = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def extract_tables(self) -> List[Dict]:
        """
        Extrae tablas estructuradas del PDF.
        
        Returns:
            Lista de diccionarios con información de tablas encontradas
        """
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)
        
        tables = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            # Intentar extraer tablas usando get_text con formato
            text = page.get_text("text")
            # Por ahora retornamos texto estructurado, luego se puede mejorar con pdfplumber
            tables.append({
                "page": page_num + 1,
                "text": text
            })
        
        return tables


def parse_laboratory_data(text: str) -> List[Dict]:
    """
    Parsea el texto extraído del PDF para encontrar parámetros, valores y rangos.
    
    Args:
        text: Texto extraído del PDF
        
    Returns:
        Lista de diccionarios con información de cada parámetro encontrado
    """
    results = []
    lines = text.split('\n')
    
    # Limpiar líneas vacías y muy cortas
    lines = [line.strip() for line in lines if line.strip() and len(line.strip()) >= 3]
    
    # Palabras clave que NO son parámetros (encabezados, metadata, etc.)
    EXCLUDE_KEYWORDS = [
        'FECHA', 'PACIENTE', 'DNI', 'LABORATORIO', 'PAGINA', 'RESULTADO',
        'PROTOCOLO', 'NRO', 'NUMERO', 'Nº', 'N°', 'PROTOCOLO NRO',
        'VARELA', 'TEL', 'TELEFONO', 'CAPITAL', 'FEDERAL', 'CONSULTORIO',
        'MEDICO', 'BOGOTA', 'INSTITUCION', 'AFILIADO', 'MEDICO',
        'RUTINA NUMERO', 'RUTINA NRO', 'APELLIDO', 'NOMBRE',
        'VALIDADO', 'FIRMADO', 'ELECTRONICAMENTE', 'BIOQ', 'DIRECTORA',
        'TECNICA', 'PRECISION', 'ESTUDIOS', 'AVALADA', 'PROGRAMA',
        'EVALUACION', 'EXTERNA', 'CALIDAD', 'FEDERACION', 'BIOQUIMICA',
        'ARGENTINA', 'METODO', 'WESTERGREN', 'ENZIMATICO', 'CINETICO',
        'TIRA', 'REACTIVA', 'HOMBRES:', 'MUJERES:', 'HASTA',
        'MILL', 'CPO', 'CAMP', 'REGULAR', 'NORMAL', 'CONTROL',
        'COLOR', 'ASPECTO', 'DENSIDAD', 'PH', 'PROTEINAS', 'GLUCOSURIA',
        'CUERPOS', 'CETONICOS', 'BILIRRUBINA', 'UROBILINOGENO',
        'CELULAS', 'EPITELIALES', 'PLANAS', 'LEUCOCITOS POR CAMPO'
    ]
    
    # Patrones mejorados para diferentes formatos
    # Formato común en PDFs argentinos: "PARAMETRO................................ VALOR unidad"
    patterns = [
        # Formato con puntos separadores: "ERITROCITOS................................ 4.680.000 /mm3"
        re.compile(
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,50}?)[\.\s]{3,}'  # Parámetro seguido de puntos o espacios
            r'([0-9]+[.,]?[0-9]*[.,]?[0-9]*)\s*'            # Valor (permite puntos como separadores de miles)
            r'(?:([a-zA-Z/%µ²³]+)\s*)?',                    # Unidad opcional
            re.IGNORECASE | re.MULTILINE
        ),
        # Formato estándar: "GLUCOSA    125.5    mg/dL"
        re.compile(
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,50}?)\s{2,}'     # Parámetro seguido de múltiples espacios
            r'([0-9]+[.,]?[0-9]*[.,]?[0-9]*)\s*'            # Valor
            r'(?:([a-zA-Z/%µ²³]+)\s*)?',                    # Unidad opcional
            re.IGNORECASE | re.MULTILINE
        ),
        # Formato con dos puntos: "GLUCOSA: 125.5 mg/dL"
        re.compile(
            r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,50}?)[:\s]+'     # Parámetro con : o espacios
            r'([0-9]+[.,]?[0-9]*[.,]?[0-9]*)\s*'            # Valor
            r'(?:([a-zA-Z/%µ²³]+)\s*)?',                    # Unidad opcional
            re.IGNORECASE | re.MULTILINE
        ),
    ]
    
    processed_lines = set()  # Para evitar duplicados
    
    # Lista de parámetros conocidos válidos (para validación adicional)
    VALID_PARAMETERS = [
        'ERITROCITOS', 'LEUCOCITOS', 'HEMOGLOBINA', 'HEMATOCRITO',
        'VOLUMEN', 'CORPUSCULAR', 'MEDIO', 'HEMOGLOBINA CORPUSCULAR',
        'CONC', 'CONCENTRACION', 'NEUTROFILOS', 'CAYADO', 'SEGMENTADOS',
        'EOSINOFILOS', 'BASOFILOS', 'LINFOCITOS', 'MONOCITOS',
        'ERITROSEDIMENTACION', 'GLUCEMIA', 'UREMIA', 'UREA',
        'CREATININA', 'COLESTEROL', 'TRIGLICERIDOS', 'TGO', 'TGP',
        'FOSFATASA', 'ALCALINA', 'GAMMA', 'GT', 'TSH', 'T4', 'LIBRE'
    ]
    
    for line in lines:
        if len(line) < 5:
            continue
        
        # Saltar líneas que contienen palabras excluidas
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in EXCLUDE_KEYWORDS):
            continue
        
        # Saltar líneas que son solo números o solo texto muy corto
        if re.match(r'^[\d\s\.\,\-]+$', line) or len(line.split()) < 2:
            continue
        
        # Saltar líneas que parecen ser rangos de referencia (contienen "a" o "hasta")
        if re.search(r'\b(HOMBRES|MUJERES|HASTA|DESDE)\b', line_upper):
            continue
        
        for pattern in patterns:
            matches = pattern.finditer(line)
            for match in matches:
                # Extraer grupos según el patrón
                groups = match.groups()
                if len(groups) < 2:
                    continue
                
                parametro = groups[0].strip() if groups[0] else ""
                valor_str = groups[1].strip() if groups[1] else ""
                unidad = groups[2].strip() if len(groups) >= 3 and groups[2] else ""
                
                # Validar que tenemos parámetro y valor
                if not parametro or not valor_str:
                    continue
                
                # Limpiar el nombre del parámetro (remover puntos excesivos, espacios múltiples)
                parametro = re.sub(r'\.{3,}', ' ', parametro)  # Reemplazar múltiples puntos con espacio
                parametro = re.sub(r'\s+', ' ', parametro).strip()  # Normalizar espacios
                
                # Validar que el parámetro tiene al menos 4 caracteres y no es solo números
                if len(parametro) < 4 or parametro.isdigit():
                    continue
                
                # Validar que el parámetro parece ser un nombre de parámetro médico válido
                # Debe tener al menos algunas letras y no ser solo números o símbolos
                if not re.search(r'[A-ZÁÉÍÓÚÑ]{3,}', parametro.upper()):
                    continue
                
                # Filtrar parámetros que son claramente metadata
                parametro_upper = parametro.upper()
                if any(exclude in parametro_upper for exclude in ['PROTOCOLO', 'VARELA', 'TEL', 'RUTINA', 'PAGINA', 'NRO', 'NUMERO']):
                    continue
                
                # Normalizar el valor (manejar separadores de miles y decimales)
                # Si tiene múltiples puntos, probablemente son separadores de miles (ej: 4.680.000)
                if valor_str.count('.') > 1:
                    # Separadores de miles: remover todos los puntos
                    valor_str_clean = valor_str.replace('.', '')
                elif ',' in valor_str and '.' in valor_str:
                    # Formato mixto: decidir cuál es el separador decimal
                    # Generalmente la coma es decimal en español
                    valor_str_clean = valor_str.replace('.', '').replace(',', '.')
                elif ',' in valor_str:
                    # Solo coma: probablemente separador decimal
                    valor_str_clean = valor_str.replace(',', '.')
                else:
                    # Solo punto o sin separadores
                    valor_str_clean = valor_str
                
                try:
                    valor = float(valor_str_clean)
                    
                    # Validar que el valor es razonable para un parámetro médico (no demasiado grande)
                    # Algunos parámetros pueden tener valores grandes (ej: eritrocitos en millones)
                    # pero valores como 4613 para TEL son claramente incorrectos
                    if valor > 1000000 and not any(p in parametro_upper for p in ['ERITROCITO', 'LEUCOCITO', 'CELULA']):
                        continue
                    
                    # Crear clave única para evitar duplicados
                    line_key = f"{parametro}_{valor}"
                    if line_key in processed_lines:
                        continue
                    processed_lines.add(line_key)
                    
                    resultado = {
                        "parametro": parametro,
                        "valor": valor,
                        "unidad": unidad,
                        "rango_min": None,  # Los rangos se detectan en líneas separadas
                        "rango_max": None,
                        "linea_original": line
                    }
                    
                    results.append(resultado)
                    break  # Si encontramos match, pasar a la siguiente línea
                except (ValueError, TypeError):
                    continue
    
    return results


def normalize_parametro_name(name: str) -> str:
    """
    Normaliza el nombre de un parámetro para comparación.
    
    Args:
        name: Nombre del parámetro a normalizar
        
    Returns:
        Nombre normalizado (mayúsculas, sin espacios extra, sin acentos)
    """
    # Convertir a mayúsculas
    normalized = name.upper().strip()
    
    # Remover espacios múltiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Mapeo de sinónimos comunes (se puede expandir)
    sinónimos = {
        "GLUCOSA": "GLUCOSA",
        "GLUCEMIA": "GLUCOSA",
        "GLUC": "GLUCOSA",
        "HEMOGLOBINA": "HEMOGLOBINA",
        "HB": "HEMOGLOBINA",
        "HGB": "HEMOGLOBINA",
        "HEMATOCRITO": "HEMATOCRITO",
        "HTO": "HEMATOCRITO",
        "HCT": "HEMATOCRITO",
    }
    
    return sinónimos.get(normalized, normalized)

