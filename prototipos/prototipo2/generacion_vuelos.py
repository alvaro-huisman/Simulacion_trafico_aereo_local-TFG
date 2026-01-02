"""Generacion de vuelos diarios a partir de flujos agregados (Prototipo 2)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import networkx as nx
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ConfigVuelos:
    """Parametros para crear un plan diario a partir de flujos anuales."""

    total_vuelos_diarios: int
    seed: int | None = 1234
    pesos_manual: Dict[Tuple[str, str], float] | None = None
    hora_inicio: int = 6   # 06:00
    hora_fin: int = 22     # 22:00
    concentracion_horas_punta: bool = True
    velocidad_crucero_kmh: float = 800.0
    umbral_distancia_tipo_avion: float = 700.0
    prob_destino_exterior: float = 0.05
    dist_exterior_km: float = 1800.0


def _resolver_pesos_rutas(
    grafo: nx.Graph, pesos_manual: Dict[Tuple[str, str], float] | None
) -> Tuple[List[Tuple[str, str]], np.ndarray]:
    """Obtiene la lista de aristas y un vector de pesos normalizados."""
    aristas: List[Tuple[str, str]] = []
    pesos: List[float] = []
    # Trafico por nodo para favorecer hubs en exterior (se usa mas adelante)

    for u, v, datos in grafo.edges(data=True):
        w_base = float(datos.get("w_ij", 0.0))
        if pesos_manual:
            factor = pesos_manual.get((u, v)) or pesos_manual.get((v, u)) or 1.0
        else:
            factor = 1.0
        w = w_base * factor
        if w <= 0:
            continue
        aristas.append((u, v))
        pesos.append(w)

    if not aristas:
        raise ValueError("El grafo no tiene aristas con peso positivo (w_ij).")

    pesos_np = np.array(pesos, dtype=float)
    pesos_np = pesos_np / pesos_np.sum()
    return aristas, pesos_np


def _trafico_por_nodo(grafo: nx.Graph) -> Dict[str, float]:
    traf: Dict[str, float] = {}
    for u, v, datos in grafo.edges(data=True):
        if str(u).upper() == "EXTERIOR" or str(v).upper() == "EXTERIOR":
            continue
        peso = float(datos.get("pasajeros_anuales", datos.get("w_ij", 0.0)))
        traf[u] = traf.get(u, 0.0) + max(0.0, peso)
        traf[v] = traf.get(v, 0.0) + max(0.0, peso)
    return traf


def _duracion_minutos(dist_km: float, velocidad_kmh: float) -> int:
    """Devuelve la duracion estimada (min) dada la distancia y velocidad de crucero."""
    if velocidad_kmh <= 0:
        return 0
    return max(1, int(math.ceil((dist_km / velocidad_kmh) * 60)))


def _generar_minutos_salida(
    cantidad: int, inicio: int, fin: int, *, concentrar: bool, rng: random.Random
) -> List[int]:
    """Genera minutos de salida entre inicio y fin. Si `concentrar` es True, prioriza horas punta."""
    inicio_min = inicio * 60
    fin_min = fin * 60
    if fin_min <= inicio_min:
        raise ValueError("La hora_fin debe ser mayor que hora_inicio.")

    if not concentrar:
        return [rng.randint(inicio_min, fin_min - 1) for _ in range(cantidad)]

    # Mezcla dos ventanas de alta demanda (mañana y tarde) con algo de dispersión uniforme
    p_peak = 0.7  # probabilidad de elegir una franja punta
    p_ventanas = [8, 18]  # horas centrales de las ventanas punta
    desv = 60  # desviacion en minutos

    minutos: List[int] = []
    for _ in range(cantidad):
        if rng.random() < p_peak:
            hora_centro = rng.choice(p_ventanas)
            mu = hora_centro * 60
            minuto = int(rng.normalvariate(mu, desv))
        else:
            minuto = rng.randint(inicio_min, fin_min - 1)
        minuto = min(max(minuto, inicio_min), fin_min - 1)
        minutos.append(minuto)
    return minutos


def _asignar_vuelos_por_ruta(
    total: int, pesos: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Distribuye el total de vuelos entre rutas segun pesos (multinomial)."""
    return rng.multinomial(total, pesos)


def generar_plan_diario(
    grafo: nx.Graph,
    config: ConfigVuelos,
) -> pd.DataFrame:
    """Genera un plan de vuelos (un dia equivalente) en base a los flujos.

    Devuelve un DataFrame con columnas:
    - id_vuelo (str)
    - origen (str)
    - destino (str)
    - minuto_salida (int, 0-1439)
    - minuto_llegada_programada (int)
    - distancia_km (float)
    - duracion_minutos (int)
    - w_ruta (float) peso relativo usado en la asignacion
    """

    rng = random.Random(config.seed)
    np_rng = np.random.default_rng(config.seed)

    aristas, pesos = _resolver_pesos_rutas(grafo, config.pesos_manual)
    traf_nodo = _trafico_por_nodo(grafo)
    traf_max = max(traf_nodo.values()) if traf_nodo else 1.0
    vuelos_por_ruta = _asignar_vuelos_por_ruta(config.total_vuelos_diarios, pesos, np_rng)

    horarios = _generar_minutos_salida(
        config.total_vuelos_diarios,
        config.hora_inicio,
        config.hora_fin,
        concentrar=config.concentracion_horas_punta,
        rng=rng,
    )

    plan: List[dict] = []
    idx_global = 0
    for (u, v), n_vuelos in zip(aristas, vuelos_por_ruta):
        if n_vuelos <= 0:
            continue
        dist = float(grafo.edges[u, v].get("dist_km", 0.0))
        duracion = _duracion_minutos(dist, config.velocidad_crucero_kmh)
        w_ruta = float(grafo.edges[u, v].get("w_ij", 0.0))

        for _ in range(n_vuelos):
            salida = horarios[idx_global]
            idx_global += 1
            # Direccion aleatoria en grafo no dirigido
            if rng.random() < 0.5:
                origen, destino = u, v
            else:
                origen, destino = v, u

            es_exterior = False
            dist_flight = dist
            destino_plan = destino
            # Prob exterior ponderada por trafico del aeropuerto origen
            traf_origen = traf_nodo.get(origen, 0.0)
            p_ext = max(0.0, min(1.0, config.prob_destino_exterior * (traf_origen / max(1e-9, traf_max))))
            if rng.random() < p_ext:
                es_exterior = True
                destino_plan = "EXTERIOR"
                dist_flight = config.dist_exterior_km

            plan.append(
                {
                    "id_vuelo": f"{origen}{destino_plan}{idx_global:05d}",
                    "origen": origen,
                    "destino": destino_plan,
                    "es_exterior": es_exterior,
                    "minuto_salida": salida,
                    "duracion_minutos": _duracion_minutos(dist_flight, config.velocidad_crucero_kmh),
                    "minuto_llegada_programada": salida + _duracion_minutos(dist_flight, config.velocidad_crucero_kmh),
                    "distancia_km": dist_flight,
                    "w_ruta": w_ruta if not es_exterior else 0.0,
                }
            )

    df = pd.DataFrame(plan)
    df.sort_values(by="minuto_salida", inplace=True, ignore_index=True)
    return df
