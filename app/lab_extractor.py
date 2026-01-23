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


def extract_patient_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extrae información del paciente del texto del PDF de laboratorio.
    
    Args:
        text: Texto extraído del PDF
        
    Returns:
        Diccionario con información del paciente:
        {
            "sexo": "hombre" | "mujer" | None,
            "nombre": str | None,
            "dni": str | None
        }
    """
    info = {
        "sexo": None,
        "nombre": None,
        "dni": None
    }
    
    lines = text.split('\n')
    text_upper = text.upper()
    
    # Patrones para detectar sexo
    # Patrón 1: "SEXO: M" o "SEXO: F" o "SEXO: MASCULINO" o "SEXO: FEMENINO"
    sexo_patterns = [
        re.compile(r'SEXO\s*[:]\s*(M|F|MASCULINO|FEMENINO|HOMBRE|MUJER)', re.IGNORECASE),
        re.compile(r'SEXO\s*[:]\s*(M|F)', re.IGNORECASE),
        # Patrón 2: En la misma línea que "PACIENTE" o "NOMBRE"
        re.compile(r'(PACIENTE|NOMBRE).*?SEXO\s*[:]\s*(M|F|MASCULINO|FEMENINO)', re.IGNORECASE),
        # Patrón 3: "M" o "F" después de "SEXO" en diferentes formatos
        re.compile(r'SEXO\s+(M|F|MASCULINO|FEMENINO)', re.IGNORECASE),
    ]
    
    for pattern in sexo_patterns:
        match = pattern.search(text_upper)
        if match:
            sexo_str = match.group(1) if len(match.groups()) >= 1 else match.group(2)
            sexo_upper = sexo_str.upper().strip()
            
            if sexo_upper in ['M', 'MASCULINO', 'HOMBRE', 'H']:
                info["sexo"] = "hombre"
                break
            elif sexo_upper in ['F', 'FEMENINO', 'MUJER', 'FEM']:
                info["sexo"] = "mujer"
                break
    
    # Si no se encontró explícitamente, buscar en líneas comunes donde aparece
    if info["sexo"] is None:
        # Buscar en líneas que contienen información del paciente
        for line in lines[:50]:  # Buscar en las primeras 50 líneas (donde suele estar la info del paciente)
            line_upper = line.upper()
            # Buscar patrones como "M" o "F" cerca de palabras clave
            if re.search(r'\b(SEXO|PACIENTE|NOMBRE|DNI)\b', line_upper):
                # Buscar M o F en la misma línea
                if re.search(r'\bM\b', line_upper) and not re.search(r'\b(MUJER|FEMENINO|F)\b', line_upper):
                    # Verificar que no sea parte de otra palabra
                    if re.search(r'\b(M|MASCULINO|HOMBRE)\b', line_upper):
                        info["sexo"] = "hombre"
                        break
                elif re.search(r'\b(F|FEMENINO|MUJER)\b', line_upper):
                    info["sexo"] = "mujer"
                    break
    
    # Extraer DNI si está disponible
    dni_patterns = [
        re.compile(r'DNI\s*[:]\s*(\d{7,8})', re.IGNORECASE),
        re.compile(r'DOCUMENTO\s*[:]\s*(\d{7,8})', re.IGNORECASE),
        re.compile(r'(\d{7,8})', re.IGNORECASE),  # Cualquier número de 7-8 dígitos cerca de "DNI"
    ]
    
    for pattern in dni_patterns:
        match = pattern.search(text)
        if match:
            info["dni"] = match.group(1)
            break
    
    # Extraer nombre si está disponible
    nombre_patterns = [
        re.compile(r'NOMBRE\s*[:]\s*([A-ZÁÉÍÓÚÑ\s]+)', re.IGNORECASE),
        re.compile(r'PACIENTE\s*[:]\s*([A-ZÁÉÍÓÚÑ\s]+)', re.IGNORECASE),
    ]
    
    for pattern in nombre_patterns:
        match = pattern.search(text)
        if match:
            nombre = match.group(1).strip()
            # Limpiar nombre (remover información adicional que pueda venir después)
            nombre = re.split(r'\s+(DNI|SEXO|FECHA)', nombre, flags=re.IGNORECASE)[0]
            nombre = re.sub(r'\s+', ' ', nombre).strip()
            if len(nombre) > 3:  # Validar que tiene sentido
                info["nombre"] = nombre
                break
    
    return info


def parse_laboratory_data(text: str, include_patient_info: bool = False, config_ranges: Optional[Dict] = None) -> List[Dict]:
    """
    Parsea el texto extraído del PDF para encontrar parámetros, valores y rangos.
    Ahora busca específicamente los parámetros definidos en el JSON de configuración.
    
    Args:
        text: Texto extraído del PDF
        include_patient_info: Si es True, incluye información del paciente en el primer resultado
        config_ranges: Diccionario con configuración de parámetros del JSON (opcional)
        
    Returns:
        Lista de diccionarios con información de cada parámetro encontrado.
        Si include_patient_info es True, el primer elemento puede contener información del paciente.
    """
    results = []
    patient_info = None
    
    if include_patient_info:
        patient_info = extract_patient_info(text)
    
    # Cargar configuración de rangos si no se proporciona
    if config_ranges is None:
        from app.lab_ranges import LaboratoryRanges
        ranges_obj = LaboratoryRanges()
        config_ranges = ranges_obj.ranges
    
    # Si la configuración tiene estructura nueva con "parametros", extraerla
    if isinstance(config_ranges, dict) and "parametros" in config_ranges:
        config_ranges = config_ranges["parametros"]
    
    lines = text.split('\n')
    
    # Limpiar líneas vacías y muy cortas
    lines = [line.strip() for line in lines if line.strip() and len(line.strip()) >= 3]
    
    # Palabras clave que NO son parámetros (encabezados, metadata, etc.)
    # NOTA: COLOR, ASPECTO, DENSIDAD, PH, etc. SÍ son parámetros válidos, NO deben estar aquí
    EXCLUDE_KEYWORDS = [
        'FECHA', 'PACIENTE', 'DNI', 'LABORATORIO', 'PAGINA', 'RESULTADO',
        'PROTOCOLO', 'NRO', 'NUMERO', 'Nº', 'N°', 'PROTOCOLO NRO',
        'VARELA', 'TEL', 'TELEFONO', 'CAPITAL', 'FEDERAL', 'CONSULTORIO',
        'MEDICO', 'BOGOTA', 'INSTITUCION', 'AFILIADO',
        'RUTINA NUMERO', 'RUTINA NRO', 'APELLIDO', 'NOMBRE',
        'VALIDADO', 'FIRMADO', 'ELECTRONICAMENTE', 'BIOQ', 'DIRECTORA',
        'TECNICA', 'PRECISION', 'ESTUDIOS', 'AVALADA', 'PROGRAMA',
        'EVALUACION', 'EXTERNA', 'CALIDAD', 'FEDERACION', 'BIOQUIMICA',
        'ARGENTINA', 'METODO', 'WESTERGREN', 'ENZIMATICO', 'CINETICO',
        'TIRA', 'REACTIVA', 'HOMBRES:', 'MUJERES:', 'HASTA',
        'MILL', 'CPO', 'CAMP', 'REGULAR', 'NORMAL', 'CONTROL'
    ]
    
    # Construir lista de parámetros a buscar desde la configuración
    parametros_a_buscar = {}
    for key, config in config_ranges.items():
        nombre = config.get("nombre", key)
        sinonimos = config.get("sinonimos", [])
        unidad_esperada = config.get("unidad", "")
        
        # Crear lista de todas las variantes del nombre
        todas_variantes = [nombre] + sinonimos
        
        # Para cada variante, crear entrada en el diccionario
        # Usar la variante original (no normalizada) como clave para búsqueda flexible
        for variante in todas_variantes:
            # Usar la variante tal cual aparece (mayúsculas) para búsqueda
            variante_upper = variante.upper().strip()
            if variante_upper not in parametros_a_buscar:
                parametros_a_buscar[variante_upper] = {
                    "key": key,
                    "nombre_original": nombre,
                    "unidad": unidad_esperada,
                    "config": config,
                    "variante": variante_upper
                }
    
    processed_params = set()  # Para evitar duplicados
    
    # Buscar cada parámetro específicamente en el texto
    text_upper = text.upper()
    
    for variante_upper, param_info in parametros_a_buscar.items():
        nombre_original = param_info["nombre_original"]
        key = param_info["key"]
        unidad_esperada = param_info["unidad"]
        config = param_info["config"]
        variante = param_info["variante"]
        
        # Si ya procesamos este parámetro (por otra variante), saltar
        if key in processed_params:
            continue
        
        # Crear patrón flexible para buscar el parámetro
        # Puede aparecer como: "ERITROCITOS................................ 4.330.000 /mm3"
        # O en líneas separadas: "ERITROCITOS................................\n4.330.000\n/mm3"
        
        # Crear patrón flexible para el nombre (permitir variaciones)
        # Usar la variante específica para buscar
        nombre_pattern = variante
        
        # Dividir el nombre en palabras para manejar mejor puntos y espacios
        palabras = nombre_pattern.split()
        patrones_palabras = []
        
        for palabra in palabras:
            # Escapar la palabra pero permitir puntos opcionales al final
            palabra_escaped = re.escape(palabra)
            # Si la palabra termina con punto en el original, hacerlo opcional
            if palabra.endswith('.'):
                palabra_escaped = palabra_escaped[:-2] + r'\.?'  # Remover escape del punto y hacerlo opcional
            patrones_palabras.append(palabra_escaped)
        
        # Unir palabras con espacios/puntos flexibles
        nombre_pattern = r'[\s\.]+'.join(patrones_palabras)
        
        # Patrón 1: Parámetro seguido de puntos/espacios y valor en la misma línea
        pattern1 = re.compile(
            rf'{nombre_pattern}[\.\s]{{3,}}'  # Nombre seguido de puntos/espacios (mínimo 3)
            r'([0-9]+[.,]?[0-9]*[.,]?[0-9]*)'  # Valor numérico
            r'\s*'                              # Espacios opcionales
            r'([a-zA-Z/%µ²³°\s]+)?',          # Unidad opcional (puede estar en misma línea)
            re.IGNORECASE | re.MULTILINE
        )
        
        # Patrón 2: Parámetro en una línea, valor en la siguiente (más flexible)
        # Buscar el nombre seguido de muchos puntos (típico formato del PDF)
        # Reducido a mínimo 5 para capturar mejor casos como "Volumen Corpuscular Medio"
        pattern2 = re.compile(
            rf'{nombre_pattern}[\.\s]{{5,}}',  # Nombre seguido de puntos/espacios (mínimo 5)
            re.IGNORECASE | re.MULTILINE
        )
        
        # Buscar con patrón 1 (misma línea)
        for match in pattern1.finditer(text):
            valor_str = match.group(1).strip()
            unidad_encontrada = match.group(2).strip() if match.group(2) else ""
            
            # Normalizar valor
            if valor_str.count('.') > 1:
                valor_str_clean = valor_str.replace('.', '')
            elif ',' in valor_str:
                valor_str_clean = valor_str.replace(',', '.')
            else:
                valor_str_clean = valor_str
            
            try:
                valor = float(valor_str_clean)
                
                # Determinar unidad final: priorizar JSON si la encontrada es incompleta
                unidad_final = _determinar_unidad_final(unidad_encontrada, unidad_esperada, nombre_original)
                
                if key not in processed_params:
                    processed_params.add(key)
                    results.append({
                        "parametro": nombre_original,
                        "valor": valor,
                        "unidad": unidad_final,
                        "rango_min": None,
                        "rango_max": None,
                        "linea_original": match.group(0)
                    })
                    break
            except (ValueError, TypeError):
                continue
        
        # Si no se encontró con patrón 1, buscar con patrón 2 (líneas separadas)
        if key not in processed_params:
            for match in pattern2.finditer(text):
                match_start = match.end()
                # Buscar las siguientes 8 líneas después del parámetro (aumentado para capturar mejor)
                remaining_text = text[match_start:]
                next_lines = remaining_text.split('\n')[:8]
                
                # Buscar valor numérico en las siguientes líneas
                valor_encontrado = False
                for i, line in enumerate(next_lines):
                    line = line.strip()
                    
                    # Saltar líneas vacías
                    if not line:
                        continue
                    
                    # Saltar líneas que son claramente metadata o rangos de referencia
                    line_upper = line.upper()
                    if any(exclude in line_upper for exclude in EXCLUDE_KEYWORDS):
                        continue
                    
                    # Saltar líneas que son rangos de referencia (contienen "HOMBRES:", "MUJERES:", "a", etc.)
                    if re.search(r'\b(HOMBRES|MUJERES|HASTA|DESDE|METODO)\b', line_upper):
                        continue
                    
                    # Buscar número con posible unidad
                    valor_match = re.search(r'^([0-9]+[.,]?[0-9]*[.,]?[0-9]*)\s*$', line)
                    if valor_match:
                        valor_str = valor_match.group(1)
                        
                        # Buscar unidad en líneas siguientes (hasta 2 líneas después)
                        unidad_encontrada = ""
                        for j in range(i + 1, min(i + 3, len(next_lines))):
                            siguiente_linea = next_lines[j].strip()
                            # Buscar unidad que no sea solo un número y no sea metadata
                            if siguiente_linea and not re.match(r'^[\d\s\.\,\-]+$', siguiente_linea):
                                if not any(exclude in siguiente_linea.upper() for exclude in EXCLUDE_KEYWORDS):
                                    unidad_match = re.search(r'^([a-zA-Z/%µ²³°º\s]+)$', siguiente_linea)
                                    if unidad_match:
                                        unidad_encontrada = unidad_match.group(1).strip()
                                        break
                        
                        # Normalizar valor
                        if valor_str.count('.') > 1:
                            valor_str_clean = valor_str.replace('.', '')
                        elif ',' in valor_str:
                            valor_str_clean = valor_str.replace(',', '.')
                        else:
                            valor_str_clean = valor_str
                        
                        try:
                            valor = float(valor_str_clean)
                            
                            # Determinar unidad final: priorizar JSON si la encontrada es incompleta
                            unidad_final = _determinar_unidad_final(unidad_encontrada, unidad_esperada, nombre_original)
                            
                            if key not in processed_params:
                                processed_params.add(key)
                                results.append({
                                    "parametro": nombre_original,
                                    "valor": valor,
                                    "unidad": unidad_final,
                                    "rango_min": None,
                                    "rango_max": None,
                                    "linea_original": f"{match.group(0).strip()} | {line}"
                                })
                                valor_encontrado = True
                                break
                        except (ValueError, TypeError):
                            continue
                    
                    # Si encontramos el parámetro, salir del loop
                    if valor_encontrado:
                        break
                
                if key in processed_params:
                    break
        
        # Para parámetros cualitativos (COLOR, ASPECTO, etc.), buscar valores cualitativos
        tipo_valor = config.get("tipo_valor", "")
        if tipo_valor == "cualitativo" and key not in processed_params:
            # Buscar el parámetro seguido de un valor cualitativo
            pattern_cualitativo = re.compile(
                rf'{nombre_pattern}[\.\s]{{3,}}'  # Nombre seguido de puntos/espacios
                r'([A-ZÁÉÍÓÚÑ\s]+)',              # Valor cualitativo (texto en mayúsculas)
                re.IGNORECASE | re.MULTILINE
            )
            
            for match in pattern_cualitativo.finditer(text):
                valor_cualitativo = match.group(1).strip()
                # Limpiar valor cualitativo
                valor_cualitativo = re.sub(r'\s+', ' ', valor_cualitativo).strip()
                
                if len(valor_cualitativo) > 0 and key not in processed_params:
                    processed_params.add(key)
                    results.append({
                        "parametro": nombre_original,
                        "valor": valor_cualitativo,  # Guardar como string para cualitativos
                        "unidad": unidad_esperada,
                        "rango_min": None,
                        "rango_max": None,
                        "linea_original": match.group(0),
                        "es_cualitativo": True
                    })
                    break
    
    # Si se solicitó información del paciente y se encontró, agregarla al primer resultado
    if include_patient_info and patient_info and results:
        results[0]["paciente"] = patient_info
    
    return results


def _determinar_unidad_final(unidad_encontrada: str, unidad_esperada: str, nombre_parametro: str) -> str:
    """
    Determina la unidad final a usar, priorizando la del JSON si la encontrada es incompleta.
    
    Args:
        unidad_encontrada: Unidad encontrada en el PDF
        unidad_esperada: Unidad esperada del JSON de configuración
        nombre_parametro: Nombre del parámetro (para casos especiales)
        
    Returns:
        Unidad final a usar
    """
    # Si no hay unidad encontrada, usar la esperada
    if not unidad_encontrada or unidad_encontrada.strip() == "":
        return unidad_esperada
    
    unidad_encontrada = unidad_encontrada.strip()
    unidad_esperada = unidad_esperada.strip()
    
    # Casos especiales donde la unidad encontrada puede ser incompleta
    nombre_upper = nombre_parametro.upper()
    
    # ERITROCITOS y LEUCOCITOS deberían ser /mm3, no /mm
    if nombre_upper in ["ERITROCITOS", "LEUCOCITOS"]:
        if unidad_encontrada == "/mm" and unidad_esperada == "/mm3":
            return unidad_esperada
        # Si encontramos /mm3 completo, usarlo
        if "/mm3" in unidad_encontrada:
            return unidad_encontrada
    
    # ERITROSEDIMENTACION debería ser "mm 1° Hora" o similar
    if "ERITROSEDIMENTACION" in nombre_upper or "ERITROSEDIMENTACIÓN" in nombre_upper:
        if unidad_esperada and ("mm" in unidad_esperada.lower() or "hora" in unidad_esperada.lower()):
            # Si la unidad esperada tiene más información, preferirla
            if len(unidad_esperada) > len(unidad_encontrada):
                return unidad_esperada
    
    # Si la unidad encontrada parece completa y válida, usarla
    # Pero si la esperada tiene más información y parece más completa, preferirla
    if unidad_esperada and len(unidad_esperada) > len(unidad_encontrada) + 2:
        # Si la esperada es significativamente más larga, probablemente es más completa
        return unidad_esperada
    
    # Limpiar y normalizar la unidad encontrada
    unidad_final = re.sub(r'\s+', ' ', unidad_encontrada).strip()
    
    return unidad_final if unidad_final else unidad_esperada


def normalize_parametro_name(name: str) -> str:
    """
    Normaliza el nombre de un parámetro para comparación.
    
    Args:
        name: Nombre del parámetro a normalizar
        
    Returns:
        Nombre normalizado (mayúsculas, sin espacios extra)
    """
    # Convertir a mayúsculas
    normalized = name.upper().strip()
    
    # Remover espacios múltiples y puntos excesivos
    normalized = re.sub(r'\.{2,}', ' ', normalized)  # Reemplazar múltiples puntos con espacio
    normalized = re.sub(r'\s+', ' ', normalized)  # Normalizar espacios
    
    # Remover acentos comunes (opcional, para mejor matching)
    replacements = {
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ñ': 'N'
    }
    for accented, unaccented in replacements.items():
        normalized = normalized.replace(accented, unaccented)
    
    return normalized.strip()

