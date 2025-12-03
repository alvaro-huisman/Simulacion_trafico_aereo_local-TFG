"""Generacion de plan diario para el Prototipo 2."""

from __future__ import annotations

from pathlib import Path
import argparse
import networkx as nx

from ..configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..generacion_vuelos import generar_plan_diario
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el plan de vuelos diario (P2) a partir del grafo preparado.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
    )
    args = parser.parse_args()

    config = AppConfig.cargar(args.config)
    import pickle
    with config.grafo_pickle.open("rb") as f:
        grafo = pickle.load(f)

    plan = generar_plan_diario(grafo, config.config_vuelos)
    config.plan_csv.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(config.plan_csv, index=False, encoding="utf-8")
    print(f"Plan diario generado en: {config.plan_csv}")
    print(f"Total de vuelos (dia 1): {len(plan)}")

    # Generar plan multi-dia si corresponde, guardado como plan_usado_p2.csv
    if config.dias_simulacion > 1:
        planes: list[pd.DataFrame] = []
        for dia in range(1, config.dias_simulacion + 1):
            cfg_vuelos_dia = config.config_vuelos.__class__(
                total_vuelos_diarios=config.config_vuelos.total_vuelos_diarios,
                seed=config.seed + dia,
                pesos_manual=config.config_vuelos.pesos_manual,
                hora_inicio=config.config_vuelos.hora_inicio,
                hora_fin=config.config_vuelos.hora_fin,
                concentracion_horas_punta=config.config_vuelos.concentracion_horas_punta,
                velocidad_crucero_kmh=config.config_vuelos.velocidad_crucero_kmh,
                umbral_distancia_tipo_avion=config.config_vuelos.umbral_distancia_tipo_avion,
                prob_destino_exterior=config.config_vuelos.prob_destino_exterior,
                dist_exterior_km=config.config_vuelos.dist_exterior_km,
            )
            plan_dia = generar_plan_diario(grafo, cfg_vuelos_dia)
            offset = (dia - 1) * 1440
            plan_dia.insert(0, "dia", dia)
            plan_dia["minuto_salida"] = plan_dia["minuto_salida"] + offset
            if "minuto_llegada_programada" in plan_dia.columns:
                plan_dia["minuto_llegada_programada"] = plan_dia["minuto_llegada_programada"] + offset
            elif "duracion_minutos" in plan_dia.columns:
                plan_dia["minuto_llegada_programada"] = plan_dia["minuto_salida"] + plan_dia["duracion_minutos"]
            planes.append(plan_dia)
        plan_multi = pd.concat(planes, ignore_index=True)
        plan_multi_path = config.plan_csv.parent / "plan_usado_p2.csv"
        plan_multi_path.parent.mkdir(parents=True, exist_ok=True)
        plan_multi.to_csv(plan_multi_path, index=False, encoding="utf-8")
        print(f"Plan multi-dia generado en: {plan_multi_path} (dias={config.dias_simulacion})")


if __name__ == "__main__":
    main()
