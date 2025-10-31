"""Configuraciones y utilidades compartidas del Prototipo 1."""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from prototipos.comun import Vector3

# Velocidad de crucero comun para todos los vuelos (unidades de distancia por minuto).
# Equivale aproximadamente a 500 km/h si la distancia se mide en kilometros.
VELOCIDAD_CRUCERO: float = 8.33


def generar_aeropuertos_demo(
    semilla: int = 2025,
) -> List[Tuple[str, Vector3, int]]:
    """Genera 10 aeropuertos con posiciones y capacidades pseudoaleatorias."""
    generador = random.Random(semilla)
    aeropuertos: List[Tuple[str, Vector3, int]] = []
    for identificador in "ABCDEFGHIJ":
        posicion = (
            round(generador.uniform(0.0, 600.0), 2),
            round(generador.uniform(0.0, 600.0), 2),
            round(generador.uniform(0.0, 50.0), 2),
        )
        capacidad = generador.randint(2, 6)
        aeropuertos.append((identificador, posicion, capacidad))
    return aeropuertos


def obtener_posiciones(aeropuertos: List[Tuple[str, Vector3, int]]) -> Dict[str, Vector3]:
    """Convierte la lista de aeropuertos en un diccionario id -> posicion."""
    return {identificador: posicion for identificador, posicion, _ in aeropuertos}
