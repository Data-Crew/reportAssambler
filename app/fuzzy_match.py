import unicodedata
import difflib
import re
from pathlib import Path
from typing import List, Optional, Tuple


def normalize_name(name: str) -> str:
    """Normaliza un nombre para comparacion: mayusculas, sin acentos, espacios unificados."""
    if not name:
        return ""
    text = name.upper()
    # Descomponer caracteres Unicode y filtrar marcas combinantes (acentos)
    nfkd = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    # Reemplazar guiones bajos por espacios
    text = text.replace('_', ' ')
    # Colapsar multiples espacios en uno solo
    text = ' '.join(text.split())
    return text.strip()


def _extract_name_from_ecg_stem(stem: str) -> str:
    """Extrae solo la parte del nombre de un stem de archivo ECG, removiendo fechas y timestamps.

    ECG filenames follow patterns like:
        NUNEZ_LUCAS_09_01_2026_09_29_17_a.m.
        GARCIA_ALEJANDRO_20_05_2025_10_12_59_a.m.
    This strips the date/time suffix to return just the name part.
    """
    # Remove trailing dots and common suffixes
    cleaned = re.sub(r'[._]*(a\.m\.|p\.m\.|am|pm)[._]*$', '', stem, flags=re.IGNORECASE)
    # Remove date-time pattern: DD_MM_YYYY_HH_MM_SS or similar
    cleaned = re.sub(r'_\d{2}_\d{2}_\d{4}_\d{2}_\d{2}_\d{2}.*$', '', cleaned)
    # Also handle DD_MM_YY pattern
    cleaned = re.sub(r'_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}.*$', '', cleaned)
    return cleaned.strip('_')


def _extract_name_from_ergo_stem(stem: str) -> str:
    """Extrae solo la parte del nombre (APELLIDO_NOMBRE) de un stem de archivo
    de ergometria del nuevo proveedor, removiendo marcadores y fechas.

    Ergometria del nuevo proveedor usa nombres como:
        IGARZABAL_JULIO_ERGO_View_27_03_2026
        PEQUERA_LUCAS_ERGO_View_27_03_2026
        APELLIDO_NOMBRE_ERGO_27_03_2026
    Devolvera la parte previa al marcador ``_ERGO`` (case-insensitive).
    """
    if not stem:
        return stem
    upper = stem.upper()
    for marker in ("_ERGO_VIEW", "_ERGO"):
        idx = upper.find(marker)
        if idx > 0:
            return stem[:idx]
    # Tambien limpiar posibles sufijos de fecha al final: _DD_MM_YYYY
    cleaned = re.sub(r'_\d{2}_\d{2}_\d{2,4}.*$', '', stem)
    return cleaned.strip('_')


def fuzzy_find_best_match(
    target_name: str,
    candidate_paths: List[Path],
    threshold: float = 0.75
) -> Optional[Path]:
    """Busca el mejor candidato por similitud difusa entre el nombre objetivo y los stems de los archivos.

    Args:
        target_name: Nombre del paciente (desde Excel).
        candidate_paths: Lista de rutas de archivos candidatos.
        threshold: Umbral minimo de similitud (0.0 a 1.0).

    Returns:
        La ruta del mejor candidato si supera el umbral, o None.
    """
    if not candidate_paths:
        return None

    normalized_target = normalize_name(target_name)
    best_path = None
    best_score = 0.0

    for path in candidate_paths:
        normalized_stem = normalize_name(path.stem)
        score = difflib.SequenceMatcher(None, normalized_target, normalized_stem).ratio()
        if score > best_score:
            best_score = score
            best_path = path

    if best_score >= threshold and best_path is not None:
        print(f"🔍 Fuzzy match: '{target_name}' -> '{best_path.name}' (score={best_score:.2f})")
        return best_path

    if best_path is not None:
        print(f"🔍 Fuzzy match debajo del umbral: '{target_name}' mejor candidato '{best_path.name}' (score={best_score:.2f}, umbral={threshold})")
    return None


def fuzzy_find_all_matches(
    target_name: str,
    candidate_paths: List[Path],
    threshold: float = 0.75
) -> List[Tuple[Path, float]]:
    """Retorna todos los candidatos que superan el umbral, ordenados por score descendente.

    Args:
        target_name: Nombre del paciente (desde Excel).
        candidate_paths: Lista de rutas de archivos candidatos.
        threshold: Umbral minimo de similitud (0.0 a 1.0).

    Returns:
        Lista de tuplas (Path, score) ordenadas por score descendente.
    """
    if not candidate_paths:
        return []

    normalized_target = normalize_name(target_name)
    matches = []

    for path in candidate_paths:
        normalized_stem = normalize_name(path.stem)
        score = difflib.SequenceMatcher(None, normalized_target, normalized_stem).ratio()
        if score >= threshold:
            matches.append((path, score))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches
