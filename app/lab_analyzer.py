"""
Lógica de análisis y detección de valores fuera de rango en laboratorios.
"""
from pathlib import Path
from typing import List, Dict, Optional
from app.lab_extractor import LaboratoryPDFExtractor, parse_laboratory_data, normalize_parametro_name
from app.lab_ranges import LaboratoryRanges


class LaboratoryAnalyzer:
    """Analiza PDFs de laboratorio para detectar valores fuera de rango."""
    
    def __init__(self, ranges_config_path: Optional[Path] = None):
        """
        Inicializa el analizador.
        
        Args:
            ranges_config_path: Ruta al archivo de configuración de rangos
        """
        self.ranges = LaboratoryRanges(ranges_config_path)
    
    def analyze_pdf(self, pdf_path: Path) -> Dict:
        """
        Analiza un PDF de laboratorio completo.
        
        Args:
            pdf_path: Ruta al PDF de laboratorio
            
        Returns:
            Diccionario con resultados del análisis:
            {
                "parametros": [...],
                "total_parametros": int,
                "fuera_de_rango": int,
                "porcentaje_fuera": float,
                "resultados": [...]
            }
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        # Extraer texto del PDF
        with LaboratoryPDFExtractor(pdf_path) as extractor:
            text = extractor.extract_text()
        
        # Extraer información del paciente (incluyendo sexo)
        from app.lab_extractor import extract_patient_info
        patient_info = extract_patient_info(text)
        sexo_paciente = patient_info.get("sexo")
        
        # Parsear datos
        parametros_encontrados = parse_laboratory_data(text, include_patient_info=False)
        
        # Guardar el sexo del paciente para usarlo en el análisis de parámetros
        self._current_patient_sexo = sexo_paciente
        
        # Analizar cada parámetro
        resultados = []
        fuera_de_rango_count = 0
        
        for param_data in parametros_encontrados:
            resultado = self._analyze_parameter(param_data)
            resultados.append(resultado)
            
            if resultado.get("fuera_de_rango"):
                fuera_de_rango_count += 1
        
        # Limpiar el atributo temporal
        delattr(self, '_current_patient_sexo')
        
        total = len(resultados)
        porcentaje = (fuera_de_rango_count / total * 100) if total > 0 else 0
        
        return {
            "parametros": parametros_encontrados,
            "total_parametros": total,
            "fuera_de_rango": fuera_de_rango_count,
            "porcentaje_fuera": round(porcentaje, 2),
            "resultados": resultados,
            "paciente": patient_info
        }
    
    def _analyze_parameter(self, param_data: Dict) -> Dict:
        """
        Analiza un parámetro individual comparándolo con rangos de referencia.
        
        Args:
            param_data: Diccionario con datos del parámetro extraído
            
        Returns:
            Diccionario con análisis completo del parámetro
        """
        parametro = param_data.get("parametro", "")
        valor = param_data.get("valor")
        unidad = param_data.get("unidad", "")
        rango_min = param_data.get("rango_min")
        rango_max = param_data.get("rango_max")
        
        # Verificar si este parámetro debe validarse contra rangos numéricos
        debe_validar = self.ranges.should_validate_range(parametro)
        
        # Intentar obtener rango de configuración si no viene en el PDF
        if rango_min is None or rango_max is None:
            # Obtener sexo del contexto si está disponible (se pasa desde analyze_pdf)
            sexo = getattr(self, '_current_patient_sexo', None)
            rango_config = self.ranges.get_range(parametro, sexo=sexo)
            if rango_config:
                rango_min, rango_max = rango_config
                # Si no hay unidad en el PDF, usar la de configuración
                if not unidad:
                    unidad = self.ranges.get_unidad(parametro) or ""
        
        # Determinar si está fuera de rango (solo si debe validarse y hay valores numéricos)
        fuera_de_rango = False
        exceso = None
        deficiencia = None
        direccion = None
        
        if debe_validar and rango_min is not None and valor is not None:
            try:
                valor_num = float(valor)
                # Validar contra mínimo (si existe)
                if valor_num < rango_min:
                    fuera_de_rango = True
                    deficiencia = rango_min - valor_num
                    direccion = "bajo"
                # Validar contra máximo (si existe)
                elif rango_max is not None and valor_num > rango_max:
                    fuera_de_rango = True
                    exceso = valor_num - rango_max
                    direccion = "alto"
            except (ValueError, TypeError):
                # Si el valor no es numérico y es cualitativo, no marcar como fuera de rango
                pass
        
        return {
            "parametro": parametro,
            "parametro_normalizado": normalize_parametro_name(parametro),
            "valor": valor,
            "unidad": unidad,
            "rango_min": rango_min,
            "rango_max": rango_max,
            "fuera_de_rango": fuera_de_rango,
            "exceso": exceso,
            "deficiencia": deficiencia,
            "direccion": direccion,
            "linea_original": param_data.get("linea_original", "")
        }
    
    def compare_value_with_range(self, valor: float, rango_min: float, 
                                rango_max: float) -> Dict:
        """
        Compara un valor con un rango de referencia.
        
        Args:
            valor: Valor a comparar
            rango_min: Valor mínimo del rango
            rango_max: Valor máximo del rango
            
        Returns:
            Diccionario con resultado de la comparación
        """
        fuera_de_rango = False
        exceso = None
        deficiencia = None
        direccion = None
        
        if valor < rango_min:
            fuera_de_rango = True
            deficiencia = rango_min - valor
            direccion = "bajo"
        elif valor > rango_max:
            fuera_de_rango = True
            exceso = valor - rango_max
            direccion = "alto"
        
        porcentaje_exceso = None
        if exceso:
            porcentaje_exceso = (exceso / rango_max) * 100
        elif deficiencia:
            porcentaje_exceso = (deficiencia / rango_min) * 100
        
        return {
            "fuera_de_rango": fuera_de_rango,
            "exceso": exceso,
            "deficiencia": deficiencia,
            "direccion": direccion,
            "porcentaje_exceso": round(porcentaje_exceso, 2) if porcentaje_exceso else None
        }

