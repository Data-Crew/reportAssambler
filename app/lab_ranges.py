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
        self.load_ranges()
    
    def load_ranges(self):
        """Carga los rangos desde el archivo de configuración."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.ranges = json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ Error al cargar configuración de rangos: {e}")
                self.ranges = {}
        else:
            # Crear archivo con estructura inicial si no existe
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.ranges = self._get_default_ranges()
            self.save_ranges()
    
    def save_ranges(self):
        """Guarda los rangos en el archivo de configuración."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.ranges, f, indent=2, ensure_ascii=False)
    
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
    
    def get_range(self, parametro: str) -> Optional[Tuple[float, float]]:
        """
        Obtiene el rango de referencia para un parámetro.
        
        Args:
            parametro: Nombre del parámetro (se normaliza automáticamente)
            
        Returns:
            Tupla (min, max) o None si no se encuentra
        """
        normalized = normalize_parametro_name(parametro)
        
        # Buscar directamente
        if normalized in self.ranges:
            config = self.ranges[normalized]
            return (config.get("min"), config.get("max"))
        
        # Buscar en sinónimos
        for key, config in self.ranges.items():
            sinonimos = config.get("sinonimos", [])
            if normalized in [normalize_parametro_name(s) for s in sinonimos]:
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
        
        if normalized in self.ranges:
            return self.ranges[normalized].get("unidad")
        
        for key, config in self.ranges.items():
            sinonimos = config.get("sinonimos", [])
            if normalized in [normalize_parametro_name(s) for s in sinonimos]:
                return config.get("unidad")
        
        return None
    
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

