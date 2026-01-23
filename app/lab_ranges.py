"""
Sistema de configuración de rangos de referencia para parámetros de laboratorio.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from app.lab_extractor import normalize_parametro_name


class LaboratoryRanges:
    """Gestiona los rangos de referencia para parámetros de laboratorio."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el sistema de rangos.
        
        Args:
            config_path: Ruta al archivo JSON de configuración. Si es None, usa el predeterminado.
        """
        if config_path is None:
            # Ruta predeterminada: config/lab_ranges.json
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "lab_ranges.json"
        
        self.config_path = config_path
        self.ranges: Dict[str, Dict] = {}
        self.metadata: Dict = {}
        self.load_ranges()
    
    def load_ranges(self):
        """Carga los rangos desde el archivo de configuración."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Soporte para estructura nueva (con "parametros") y antigua (directa)
                    if "parametros" in data:
                        # Estructura nueva: {"version": "...", "parametros": {...}}
                        self.ranges = data["parametros"]
                        self.metadata = {
                            "version": data.get("version"),
                            "descripcion": data.get("descripcion"),
                            "ultima_actualizacion": data.get("ultima_actualizacion")
                        }
                    else:
                        # Estructura antigua: diccionario directo de parámetros
                        self.ranges = data
                        self.metadata = {}
            except json.JSONDecodeError as e:
                print(f"⚠️ Error al cargar configuración de rangos: {e}")
                self.ranges = {}
                self.metadata = {}
        else:
            # Crear archivo con estructura inicial si no existe
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.ranges = self._get_default_ranges()
            self.metadata = {}
            self.save_ranges()
    
    def save_ranges(self):
        """Guarda los rangos en el archivo de configuración."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Si tiene metadata, guardar con estructura nueva
        if self.metadata:
            data = {
                **self.metadata,
                "parametros": self.ranges
            }
        else:
            data = self.ranges
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _get_default_ranges(self) -> Dict:
        """Retorna rangos predeterminados (ejemplo inicial)."""
        return {
            "GLUCOSA": {
                "min": 70.0,
                "max": 100.0,
                "unidad": "mg/dL",
                "sinonimos": ["GLUCEMIA", "GLUC"]
            },
            "HEMOGLOBINA": {
                "min": 12.0,
                "max": 16.0,
                "unidad": "g/dL",
                "sinonimos": ["HB", "HGB"]
            },
            "HEMATOCRITO": {
                "min": 36.0,
                "max": 48.0,
                "unidad": "%",
                "sinonimos": ["HTO", "HCT"]
            },
            "COLESTEROL_TOTAL": {
                "min": 0.0,
                "max": 200.0,
                "unidad": "mg/dL",
                "sinonimos": ["COLESTEROL", "COL"]
            },
            "TRIGLICERIDOS": {
                "min": 0.0,
                "max": 150.0,
                "unidad": "mg/dL",
                "sinonimos": ["TG", "TRIG"]
            }
        }
    
    def get_range(self, parametro: str, sexo: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """
        Obtiene el rango de referencia para un parámetro.
        
        Args:
            parametro: Nombre del parámetro (se normaliza automáticamente)
            sexo: "hombre", "mujer", "H", "M", "MASCULINO", "FEMENINO" (opcional)
            
        Returns:
            Tupla (min, max) o None si no se encuentra
        """
        normalized = normalize_parametro_name(parametro)
        config = None
        
        # Buscar directamente por clave
        if parametro.upper() in self.ranges:
            config = self.ranges[parametro.upper()]
        elif normalized in self.ranges:
            config = self.ranges[normalized]
        else:
            # Buscar en sinónimos y nombres
            for key, cfg in self.ranges.items():
                nombre_cfg = cfg.get("nombre", key)
                sinonimos = cfg.get("sinonimos", [])
                # Comparar con nombre normalizado
                if normalize_parametro_name(nombre_cfg) == normalized:
                    config = cfg
                    break
                # Comparar con sinónimos normalizados
                for sinonimo in sinonimos:
                    if normalize_parametro_name(sinonimo) == normalized:
                        config = cfg
                        break
                if config:
                    break
        
        if config is None:
            return None
        
        # Normalizar sexo si se proporciona
        sexo_normalizado = None
        if sexo:
            sexo_upper = sexo.upper()
            if sexo_upper in ["HOMBRE", "H", "MASCULINO", "M"]:
                sexo_normalizado = "hombre"
            elif sexo_upper in ["MUJER", "F", "FEMENINO", "FEM"]:
                sexo_normalizado = "mujer"
        
        # Estructura nueva: con rangos diferenciados por sexo
        if "rangos" in config:
            rangos = config.get("rangos", {})
            requiere_sexo = config.get("requiere_sexo", False)
            
            # Si requiere sexo y se proporcionó, usar ese rango
            if requiere_sexo and sexo_normalizado:
                rango_sexo = rangos.get(sexo_normalizado)
                if rango_sexo:
                    min_val = rango_sexo.get("min")
                    max_val = rango_sexo.get("max")
                    # Permitir rangos con solo mínimo (ej: COLESTEROL_HDL "mayor a X")
                    if min_val is not None:
                        return (min_val, max_val)  # max_val puede ser None
            
            # Si no requiere sexo o los rangos son iguales, usar cualquier rango disponible
            if not requiere_sexo or not sexo_normalizado:
                # Intentar con "hombre" primero, luego "mujer"
                for sexo_key in ["hombre", "mujer"]:
                    rango_sexo = rangos.get(sexo_key)
                    if rango_sexo:
                        min_val = rango_sexo.get("min")
                        max_val = rango_sexo.get("max")
                        # Permitir rangos con solo mínimo
                        if min_val is not None:
                            return (min_val, max_val)  # max_val puede ser None
            
            return None
        
        # Estructura antigua: min/max directos
        if "min" in config and "max" in config:
            return (config.get("min"), config.get("max"))
        
        return None
    
    def get_unidad(self, parametro: str) -> Optional[str]:
        """
        Obtiene la unidad esperada para un parámetro.
        
        Args:
            parametro: Nombre del parámetro
            
        Returns:
            Unidad o None si no se encuentra
        """
        normalized = normalize_parametro_name(parametro)
        config = None
        
        if normalized in self.ranges:
            config = self.ranges[normalized]
        else:
            for key, cfg in self.ranges.items():
                sinonimos = cfg.get("sinonimos", [])
                if normalized in [normalize_parametro_name(s) for s in sinonimos]:
                    config = cfg
                    break
        
        if config:
            return config.get("unidad")
        
        return None
    
    def should_validate_range(self, parametro: str) -> bool:
        """
        Indica si un parámetro debe validarse contra rangos numéricos.
        Algunos parámetros son cualitativos y no tienen rangos numéricos.
        
        Args:
            parametro: Nombre del parámetro
            
        Returns:
            True si debe validarse, False si es cualitativo
        """
        normalized = normalize_parametro_name(parametro)
        config = None
        
        if normalized in self.ranges:
            config = self.ranges[normalized]
        else:
            for key, cfg in self.ranges.items():
                sinonimos = cfg.get("sinonimos", [])
                if normalized in [normalize_parametro_name(s) for s in sinonimos]:
                    config = cfg
                    break
        
        if config:
            # Si tiene validar_rango explícito, usar ese valor
            if "validar_rango" in config:
                return config.get("validar_rango", True)
            # Si tiene tipo_valor "cualitativo", no validar
            if config.get("tipo_valor") == "cualitativo":
                return False
            # Si no tiene rangos numéricos, no validar
            if "rangos" in config:
                rangos = config.get("rangos", {})
                for sexo_key in ["hombre", "mujer"]:
                    rango_sexo = rangos.get(sexo_key, {})
                    if rango_sexo.get("min") is None or rango_sexo.get("max") is None:
                        continue
                    return True
                return False
        
        return True  # Por defecto, validar
    
    def add_range(self, parametro: str, min_val: float, max_val: float, 
                  unidad: str = "", sinonimos: List[str] = None):
        """
        Agrega o actualiza un rango de referencia.
        
        Args:
            parametro: Nombre del parámetro
            min_val: Valor mínimo del rango
            max_val: Valor máximo del rango
            unidad: Unidad de medida
            sinonimos: Lista de sinónimos
        """
        normalized = normalize_parametro_name(parametro)
        self.ranges[normalized] = {
            "min": min_val,
            "max": max_val,
            "unidad": unidad,
            "sinonimos": sinonimos or []
        }
        self.save_ranges()

