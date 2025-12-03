"""CLI para visualizar el Prototipo 2 con slider de minutos."""

from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import pandas as pd

from ..configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..datos_aeropuertos import cargar_aeropuertos_csv
from ..visualizacion_prototipo2 import visor_interactivo


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Visor interactivo del Prototipo 2 (lon/lat + slider minuto).")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
    )
    parser.add_argument(
        "--sin-mapa",
        action="store_true",
        help="No carga fondo de mapa (contextily), util si no hay red o quieres ver solo el grafo.",
    )
    parser.add_argument(
        "--minuto-max",
        type=int,
        default=1440,
        help="Minuto maximo a mostrar en el slider (por defecto 1440).",
    )
    args = parser.parse_args()

    config = AppConfig.cargar(args.config)

    with config.grafo_pickle.open("rb") as f:
        grafo = pickle.load(f)
    ruta_aer = config.aeropuertos_enriquecidos_csv if config.aeropuertos_enriquecidos_csv.exists() else config.aeropuertos_csv
    aeropuertos_raw = cargar_aeropuertos_csv(ruta_aer, epsg_origen=config.epsg_origen)
    aeropuertos = _normalizar_aeropuertos(aeropuertos_raw)
    plan_usado = config.plan_csv.parent / "plan_usado_p2.csv"
    if plan_usado.exists():
        plan = pd.read_csv(plan_usado)
    else:
        plan = pd.read_csv(config.plan_csv)
    eventos = None
    if config.eventos_csv.exists():
        eventos = pd.read_csv(config.eventos_csv)
    resultados = None
    if config.resultados_csv.exists():
        resultados = pd.read_csv(config.resultados_csv)
    dias_max = config.dias_simulacion
    if "dia" in plan.columns:
        try:
            dias_max = max(dias_max, int(plan["dia"].max()))
        except Exception:
            pass

    visor_interactivo(
        grafo,
        aeropuertos,
        plan,
        config_vuelos=config.config_vuelos,
        eventos=eventos,
        resultados=resultados,
        dias_max=dias_max,
        minuto_max=args.minuto_max,
        usar_mapa_fondo=not args.sin_mapa,
    )


if __name__ == "__main__":
    main()
