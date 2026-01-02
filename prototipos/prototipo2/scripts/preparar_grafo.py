"""Preparacion del grafo para el Prototipo 2."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import unicodedata
import random

import networkx as nx
import pandas as pd
from geopy.distance import geodesic

from ..configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..datos_aeropuertos import cargar_aeropuertos_csv, construir_grafo
from ..rutas_desde_flujos import leer_flujos_ministerio


def _normalizar_aeropuertos(df: pd.DataFrame) -> pd.DataFrame:
    df_norm = df.copy()
    if "ID_Aeropuerto" in df_norm.columns:
        df_norm.rename(columns={"ID_Aeropuerto": "id"}, inplace=True)
    if "Latitud" in df_norm.columns:
        df_norm.rename(columns={"Latitud": "lat"}, inplace=True)
    if "Longitud" in df_norm.columns:
        df_norm.rename(columns={"Longitud": "lon"}, inplace=True)
    if "Nombre" in df_norm.columns:
        df_norm.rename(columns={"Nombre": "nombre"}, inplace=True)

    return df_norm


def _anadir_distancias(grafo: nx.Graph, posiciones: Dict[str, Tuple[float, float]]) -> None:
    for u, v in grafo.edges:
        dist = geodesic((posiciones[u][0], posiciones[u][1]), (posiciones[v][0], posiciones[v][1])).km
        grafo.edges[u, v]["dist_km"] = float(dist)


def _limpiar_nombre(texto: str) -> str:
    """Normaliza el nombre para emparejar con los flujos."""
    if not isinstance(texto, str):
        return ""
    texto_norm = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto_norm = texto_norm.lower()
    for pref in ["aeropuerto", "de", "del", "-", "_", ".", ",", "(", ")", ":"]:
        texto_norm = texto_norm.replace(pref, " ")
    return " ".join(texto_norm.split())


def _mapear_codigos_por_nombre(flujos: pd.DataFrame) -> Dict[str, str]:
    """Crea un mapa nombre_limpio -> codigo (IATA/ICAO) desde los flujos."""
    mapa: Dict[str, str] = {}
    for fila in flujos.itertuples(index=False):
        codigo = getattr(fila, "origen_id")
        nombre = getattr(fila, "origen_nombre", "") if hasattr(fila, "origen_nombre") else getattr(fila, "origen_id")
        nombre_limpio = _limpiar_nombre(str(nombre).split(":")[-1])
        if nombre_limpio and codigo:
            mapa.setdefault(nombre_limpio, codigo)
        codigo_d = getattr(fila, "destino_id")
        nombre_d = getattr(fila, "destino_nombre", "") if hasattr(fila, "destino_nombre") else getattr(fila, "destino_id")
        nombre_d_limpio = _limpiar_nombre(str(nombre_d).split(":")[-1])
        if nombre_d_limpio and codigo_d:
            mapa.setdefault(nombre_d_limpio, codigo_d)
    return mapa


def _anadir_pesos(grafo: nx.Graph, flujos: pd.DataFrame, posiciones: Dict[str, Tuple[float, float]]) -> None:
    total = 0.0
    pax_por_aer: Dict[str, float] = {}
    for fila in flujos.itertuples(index=False):
        u = getattr(fila, "origen_id")
        v = getattr(fila, "destino_id")
        pasajeros = float(getattr(fila, "pasajeros_anuales"))
        if pasajeros <= 0:
            continue
        if u not in posiciones or v not in posiciones:
            continue
        pax_por_aer[u] = pax_por_aer.get(u, 0.0) + pasajeros
        pax_por_aer[v] = pax_por_aer.get(v, 0.0) + pasajeros
        if grafo.has_edge(u, v):
            grafo.edges[u, v]["pasajeros_anuales"] = grafo.edges[u, v].get("pasajeros_anuales", 0.0) + pasajeros
        else:
            grafo.add_edge(u, v, pasajeros_anuales=pasajeros)
        total += pasajeros
    if total <= 0:
        # Fallback: grafo completo con pesos uniformes
        ids = list(posiciones.keys())
        grafo.clear()
        for idx, u in enumerate(ids):
            for v in ids[idx + 1 :]:
                grafo.add_edge(u, v, pasajeros_anuales=1.0)
        total = grafo.number_of_edges()
    for u, v, datos in grafo.edges(data=True):
        w = float(datos.get("pasajeros_anuales", 0.0)) / total
        grafo.edges[u, v]["w_ij"] = w
    return pax_por_aer


def preparar_grafo(config: AppConfig) -> nx.Graph:
    flujos = leer_flujos_ministerio(config.flujos_csv)
    # Mapeo de nombres a codigos basado en los flujos
    mapa_codigos = _mapear_codigos_por_nombre(flujos)
    claves_nombres = list(mapa_codigos.keys())

    aeropuertos_raw = cargar_aeropuertos_csv(config.aeropuertos_csv, epsg_origen=config.epsg_origen)
    # Asignar IDs usando nombres limpìos y mapa de flujos; si no coincide, mantener o crear fallback
    if "Texto" in aeropuertos_raw.columns:
        def asignar_id(texto: str, actual: str) -> str:
            nombre_limpio = _limpiar_nombre(texto)
            if nombre_limpio in mapa_codigos:
                return mapa_codigos[nombre_limpio]
            tokens = set(nombre_limpio.split())
            mejor_codigo = actual
            mejor_score = 0
            for clave in claves_nombres:
                clave_tokens = set(clave.split())
                inter = len(tokens & clave_tokens)
                score = inter / max(1, len(clave_tokens))
                if score > mejor_score:
                    mejor_score = score
                    mejor_codigo = mapa_codigos[clave]
            if mejor_codigo:
                return mejor_codigo
            # fallback parcial por substring
            for clave in claves_nombres:
                if clave and (clave in nombre_limpio or nombre_limpio in clave):
                    return mapa_codigos[clave]
            if actual:
                return actual
            # fallback: primeras letras del nombre limpio
            return nombre_limpio.replace(" ", "")[:5].upper()
        id_exist = aeropuertos_raw.get("ID_Aeropuerto", "")
        aeropuertos_raw["ID_Aeropuerto"] = [
            asignar_id(txt, act) for txt, act in zip(aeropuertos_raw["Texto"], id_exist if len(id_exist) else [""] * len(aeropuertos_raw))
        ]
    aeropuertos_raw = aeropuertos_raw[aeropuertos_raw.get("ID_Aeropuerto", "") != ""]

    aeropuertos_df = _normalizar_aeropuertos(aeropuertos_raw)
    rng = random.Random(config.seed)
    if "capacidad" not in aeropuertos_df.columns:
        aeropuertos_df["capacidad"] = [
            rng.randint(config.capacidad_min, config.capacidad_max) for _ in range(len(aeropuertos_df))
        ]
    if "viento_baja_cota" not in aeropuertos_df.columns:
        aeropuertos_df["viento_baja_cota"] = rng.choices(
            ["a_favor", "en_contra", "neutro"],
            weights=[config.prob_viento_a_favor, config.prob_viento_en_contra, config.prob_viento_neutro],
            k=len(aeropuertos_df),
        )
    if "viento_alta_cota" not in aeropuertos_df.columns:
        aeropuertos_df["viento_alta_cota"] = rng.choices(
            ["a_favor", "en_contra", "neutro"],
            weights=[config.prob_viento_a_favor, config.prob_viento_en_contra, config.prob_viento_neutro],
            k=len(aeropuertos_df),
        )

    # Guardar version enriquecida para uso posterior
    aeropuertos_df.to_csv(config.aeropuertos_enriquecidos_csv, index=False, encoding="utf-8")

    grafo = construir_grafo(aeropuertos_df)

    posiciones = {fila.id: (float(fila.lat), float(fila.lon)) for fila in aeropuertos_df.itertuples(index=False)}

    pax_por_aer = _anadir_pesos(grafo, flujos, posiciones)
    _anadir_distancias(grafo, posiciones)

    # Ajustar capacidad en base al trafico relativo (siempre que haya pax)
    if pax_por_aer:
        pax_max = max(pax_por_aer.values()) or 1.0
        caps = []
        for fila in aeropuertos_df.itertuples(index=False):
            pax = pax_por_aer.get(getattr(fila, "id"), 0.0)
            frac = pax / pax_max
            cap = int(round(config.capacidad_min + frac * (config.capacidad_max - config.capacidad_min)))
            caps.append(max(1, cap))
        aeropuertos_df["capacidad"] = caps
        aeropuertos_df.to_csv(config.aeropuertos_enriquecidos_csv, index=False, encoding="utf-8")

    return grafo


def _parsear_argumentos() -> Path:
    import argparse

    parser = argparse.ArgumentParser(description="Prepara el grafo del Prototipo 2 (pesos y distancias).")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
    )
    args = parser.parse_args()
    return args.config


def main() -> None:
    ruta_config = _parsear_argumentos()
    config = AppConfig.cargar(ruta_config)

    grafo = preparar_grafo(config)
    config.grafo_pickle.parent.mkdir(parents=True, exist_ok=True)
    import pickle
    with config.grafo_pickle.open("wb") as f:
        pickle.dump(grafo, f)

    print(f"Grafo guardado en: {config.grafo_pickle}")
    print(f"Nodos: {grafo.number_of_nodes()} | Aristas: {grafo.number_of_edges()}")


if __name__ == "__main__":
    main()
