import unicodedata
import difflib
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
