"""Ejecucion de la simulacion del Prototipo 2."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

import networkx as nx
import pandas as pd
import numpy as np

from ..configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..datos_aeropuertos import cargar_aeropuertos_csv
from ..simulador_prototipo2 import SimulacionPrototipo2
from ..generacion_vuelos import generar_plan_diario


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
    if "capacidad" not in df_norm.columns:
        df_norm["capacidad"] = 5
    if "viento_baja_cota" not in df_norm.columns:
        df_norm["viento_baja_cota"] = "neutro"
    if "viento_alta_cota" not in df_norm.columns:
        df_norm["viento_alta_cota"] = "neutro"
    return df_norm


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta la simulacion del Prototipo 2 usando el plan generado.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=None,
        help="Numero de dias consecutivos a simular (se desplaza el plan 1440 minutos por dia). Si no se indica, se usa el valor del config.",
    )
    args = parser.parse_args()

    config = AppConfig.cargar(args.config)

    # Limpia resultados/eventos/plan_usado previos (por defecto)
    for ruta in [
        config.resultados_csv,
        config.eventos_csv,
        config.plan_csv.parent / "plan_usado_p2.csv",
        config.logs_csv,
    ]:
        if ruta.exists():
            ruta.unlink()
    for carpeta in [
        config.resultados_csv.parent / "resultados_p2",
        config.eventos_csv.parent / "eventos_p2",
        config.logs_csv.parent / "logs_p2",
    ]:
        if carpeta.exists():
            shutil.rmtree(carpeta, ignore_errors=True)

    ruta_aer = config.aeropuertos_enriquecidos_csv if config.aeropuertos_enriquecidos_csv.exists() else config.aeropuertos_csv
    aeropuertos_raw = cargar_aeropuertos_csv(ruta_aer)
    aeropuertos_df = _normalizar_aeropuertos(aeropuertos_raw)

    import pickle
    with config.grafo_pickle.open("rb") as f:
        grafo = pickle.load(f)
    plan_base = pd.read_csv(config.plan_csv)

    dias = max(1, args.dias if args.dias is not None else config.dias_simulacion)
    resultados_dir = config.resultados_csv.parent / "resultados_p2"
    eventos_dir = config.eventos_csv.parent / "eventos_p2"
    logs_dir = config.logs_csv.parent / "logs_p2"
    resultados_dir.mkdir(parents=True, exist_ok=True)
    eventos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    acumulados = []
    acumulados_eventos = []
    acumulados_logs = []
    ocupacion_carry: dict[str, int] | None = None
    planes_usados = []

    def _agrupar_por_aeropuerto(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        aeropuertos = set(df["origen"].dropna().astype(str)) | set(
            df["destino_final"].dropna().astype(str)
        )
        aeropuertos = {a for a in aeropuertos if a.upper() != "EXTERIOR"}
        filas: list[dict] = []
        for aer in sorted(aeropuertos):
            mask_sal = df["origen"].astype(str).eq(aer)
            mask_lleg = df["destino_final"].astype(str).eq(aer)
            filas.append(
                {
                    "aeropuerto": aer,
                    "vuelos_salidas": int(mask_sal.sum()),
                    "vuelos_llegadas": int(mask_lleg.sum()),
                    "vuelos_redirigidos_recibidos": int((mask_lleg & df["redirigido"]).sum()),
                    "vuelos_redirigidos_salientes": int((mask_sal & df["redirigido"]).sum()),
                    "retraso_medio_llegadas_min": float(df.loc[mask_lleg, "retraso_total_min"].mean()),
                    "retraso_p95_llegadas_min": float(np.nanpercentile(df.loc[mask_lleg, "retraso_total_min"], 95))
                    if mask_lleg.any()
                    else np.nan,
                    "combustible_total_l": float(df.loc[mask_sal | mask_lleg, "combustible_consumido_l"].sum()),
                    "tiempo_espera_total_min": float(df.loc[mask_lleg, "tiempo_espera_cola_min"].sum()),
                }
            )
        return pd.DataFrame(filas)

    for dia in range(1, dias + 1):
        if config.plan_aleatorio_por_dia and dias > 1:
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
            plan_dia = generar_plan_diario(
                grafo,
                cfg_vuelos_dia,
            )
            offset = (dia - 1) * 1440
            plan_dia.insert(0, "dia", dia)
            plan_dia["minuto_salida"] = plan_dia["minuto_salida"] + offset
            if "minuto_llegada_programada" in plan_dia.columns:
                plan_dia["minuto_llegada_programada"] = plan_dia["minuto_llegada_programada"] + offset
            elif "duracion_minutos" in plan_dia.columns:
                plan_dia["minuto_llegada_programada"] = plan_dia["minuto_salida"] + plan_dia["duracion_minutos"]
            # Ajustar seed para reproducibilidad por dia
            plan_dia["seed_dia"] = config.seed + dia
        else:
            offset = (dia - 1) * 1440
            plan_dia = plan_base.copy()
            plan_dia["minuto_salida"] = plan_dia["minuto_salida"] + offset
            if "minuto_llegada_programada" in plan_dia.columns:
                plan_dia["minuto_llegada_programada"] = plan_dia["minuto_llegada_programada"] + offset

        if "dia" not in plan_dia.columns:
            plan_dia.insert(0, "dia", dia)
        planes_usados.append(plan_dia)

        sim = SimulacionPrototipo2(
            aeropuertos_df=aeropuertos_df,
            grafo=grafo,
            plan_vuelos=plan_dia,
            config=config.config_simulacion,
            ocupacion_inicial=ocupacion_carry,
        )
        resultados, eventos, logs = sim.run()
        resultados.insert(0, "dia", dia)
        eventos.insert(0, "dia", dia)
        logs.insert(0, "dia", dia)
        acumulados.append(resultados)
        acumulados_eventos.append(eventos)
        acumulados_logs.append(logs)
        # preparar carry over de ocupacion para el siguiente dia
        if not eventos.empty:
            ultimos = eventos.sort_values(["aeropuerto", "minuto"]).groupby("aeropuerto").tail(1)
            ocupacion_carry = {row.aeropuerto: int(row.ocupacion) for row in ultimos.itertuples(index=False)}
        else:
            ocupacion_carry = None
        (resultados_dir / f"resultados_dia_{dia:03d}.csv").write_text(
            resultados.to_csv(index=False, encoding="utf-8"), encoding="utf-8"
        )
        (eventos_dir / f"eventos_dia_{dia:03d}.csv").write_text(
            eventos.to_csv(index=False, encoding="utf-8"), encoding="utf-8"
        )
        (logs_dir / f"logs_dia_{dia:03d}.csv").write_text(
            logs.to_csv(index=False, encoding="utf-8"), encoding="utf-8"
        )

    combinados = pd.concat(acumulados, ignore_index=True)
    combinados_eventos = pd.concat(acumulados_eventos, ignore_index=True)
    combinados_logs = pd.concat(acumulados_logs, ignore_index=True)
    plan_usado_total = pd.concat(planes_usados, ignore_index=True)
    config.resultados_csv.parent.mkdir(parents=True, exist_ok=True)
    combinados.to_csv(config.resultados_csv, index=False, encoding="utf-8")
    # Copia explicita por vuelo (alias)
    resultados_por_vuelo_path = config.resultados_csv.parent / "resultados_por_vuelo_p2.csv"
    combinados.to_csv(resultados_por_vuelo_path, index=False, encoding="utf-8")
    # Agregado por aeropuerto
    df_por_aer = _agrupar_por_aeropuerto(combinados)
    resultados_por_aer_path = config.resultados_csv.parent / "resultados_por_aeropuerto_p2.csv"
    df_por_aer.to_csv(resultados_por_aer_path, index=False, encoding="utf-8")
    config.eventos_csv.parent.mkdir(parents=True, exist_ok=True)
    combinados_eventos.to_csv(config.eventos_csv, index=False, encoding="utf-8")
    config.logs_csv.parent.mkdir(parents=True, exist_ok=True)
    combinados_logs.to_csv(config.logs_csv, index=False, encoding="utf-8")
    plan_usado_path = config.plan_csv.parent / "plan_usado_p2.csv"
    plan_usado_path.parent.mkdir(parents=True, exist_ok=True)
    plan_usado_total.to_csv(plan_usado_path, index=False, encoding="utf-8")

    print(f"Simulacion completada ({dias} dia/s). Resultados combinados en: {config.resultados_csv}")
    print(f"Resultados por vuelo en: {resultados_por_vuelo_path}")
    print(f"Resultados por aeropuerto en: {resultados_por_aer_path}")
    print(f"Eventos combinados en: {config.eventos_csv}")
    print(f"Logs combinados en: {config.logs_csv}")
    print(f"Resultados por dia en: {resultados_dir}")
    print(f"Eventos por dia en: {eventos_dir}")
    print(f"Logs por dia en: {logs_dir}")
    print(f"Plan usado (multi-dia) en: {plan_usado_path}")


if __name__ == "__main__":
    main()
