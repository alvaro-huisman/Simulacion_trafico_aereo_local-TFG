"""Carga de configuracion para el Prototipo 2."""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .generacion_vuelos import ConfigVuelos
from .simulador_prototipo2 import ConfigSimulacion


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configuracion_inicial.txt"

_DEFAULTS = {
    "general": {
        "seed": "1234",
    },
    "datos": {
        "aeropuertos_csv": "Aeropuertos_Espanoles.csv",
        "aeropuertos_enriquecidos_csv": "aeropuertos_enriquecidos.csv",
        "flujos_csv": "Flujo_Aeropuertos_Espanoles.csv",
        "epsg_origen": "3857",
        "capacidad_min": "4",
        "capacidad_max": "12",
        "prob_viento_a_favor": "0.3",
        "prob_viento_en_contra": "0.3",
        "prob_viento_neutro": "0.4",
    },
    "salidas": {
        "grafo_pickle": "salidas/grafo/grafo_p2.gpickle",
        "plan_csv": "salidas/planes/plan_diario_p2.csv",
        "resultados_csv": "salidas/resultados/resultados_p2.csv",
        "eventos_csv": "salidas/eventos/eventos_p2.csv",
        "logs_csv": "salidas/eventos/logs_vuelos_p2.csv",
    },
    "vuelos": {
        "total_vuelos_diarios": "180",
        "umbral_distancia_tipo_avion": "700.0",
        "hora_inicio": "6",
        "hora_fin": "22",
        "concentracion_horas_punta": "yes",
        "velocidad_crucero_kmh": "800.0",
        "prob_destino_exterior": "0.10",
        "dist_exterior_km": "1800.0",
    },
    "simulacion": {
        "paso_minutos": "1",
        "T_umbral_espera": "45",
        "separar_minutos": "3",
        "factor_viento_a_favor": "1.05",
        "factor_viento_en_contra": "0.9",
        "factor_viento_neutro": "1.0",
        "fuel_factor_a_favor": "0.95",
        "fuel_factor_en_contra": "1.05",
        "fuel_factor_neutro": "1.0",
        "tiempo_embarque_min": "0",
        "tiempo_turnaround_min": "0",
        "ocupacion_inicial_min_fraccion": "0.05",
        "ocupacion_inicial_max_fraccion": "0.35",
        "exterior_top_n": "15",
        "exterior_ruido_min": "1",
        "exterior_ruido_max": "3",
        "exterior_intervalo_min": "90",
        "exterior_intervalo_max": "240",
        "exterior_estancia_min": "15",
        "exterior_estancia_max": "45",
        "tmin_fase_asc_des_min": "5.0",
        "tmin_fase_crucero_min": "5.0",
        "plan_aleatorio_por_dia": "yes",
        "dias": "5",
    },
}


def _resolver_ruta(base: Path, valor: str) -> Path:
    return (base / valor).resolve()


@dataclass(frozen=True)
class AppConfig:
    """Parametros leidos del archivo de configuracion."""

    ruta_config: Path
    seed: int
    aeropuertos_csv: Path
    aeropuertos_enriquecidos_csv: Path
    flujos_csv: Path
    epsg_origen: int
    capacidad_min: int
    capacidad_max: int
    prob_viento_a_favor: float
    prob_viento_en_contra: float
    prob_viento_neutro: float
    grafo_pickle: Path
    plan_csv: Path
    resultados_csv: Path
    logs_csv: Path
    eventos_csv: Path
    config_vuelos: ConfigVuelos
    config_simulacion: ConfigSimulacion
    dias_simulacion: int
    plan_aleatorio_por_dia: bool

    @classmethod
    def cargar(cls, ruta: Optional[Path] = None) -> "AppConfig":
        parser = ConfigParser()
        parser.read_dict(_DEFAULTS)

        archivos = [DEFAULT_CONFIG_PATH]
        if ruta is not None and ruta != DEFAULT_CONFIG_PATH:
            archivos.append(ruta)
        parser.read([str(p) for p in archivos if Path(p).exists()])

        ruta_config = ruta if ruta is not None else DEFAULT_CONFIG_PATH
        base = ruta_config.resolve().parent

        seed = parser.getint("general", "seed")

        aeropuertos_csv = _resolver_ruta(base, parser.get("datos", "aeropuertos_csv"))
        aeropuertos_enriquecidos_csv = _resolver_ruta(
            base, parser.get("datos", "aeropuertos_enriquecidos_csv")
        )
        flujos_csv = _resolver_ruta(base, parser.get("datos", "flujos_csv"))
        epsg_origen = parser.getint("datos", "epsg_origen")
        cap_min = parser.getint("datos", "capacidad_min")
        cap_max = parser.getint("datos", "capacidad_max")
        prob_vto_fav = parser.getfloat("datos", "prob_viento_a_favor")
        prob_vto_contra = parser.getfloat("datos", "prob_viento_en_contra")
        prob_vto_neutro = parser.getfloat("datos", "prob_viento_neutro")

        grafo_pickle = _resolver_ruta(base, parser.get("salidas", "grafo_pickle"))
        plan_csv = _resolver_ruta(base, parser.get("salidas", "plan_csv"))
        resultados_csv = _resolver_ruta(base, parser.get("salidas", "resultados_csv"))
        eventos_csv = _resolver_ruta(base, parser.get("salidas", "eventos_csv"))
        logs_csv = _resolver_ruta(base, parser.get("salidas", "logs_csv"))

        config_vuelos = ConfigVuelos(
            total_vuelos_diarios=parser.getint("vuelos", "total_vuelos_diarios"),
            seed=seed,
            umbral_distancia_tipo_avion=parser.getfloat("vuelos", "umbral_distancia_tipo_avion"),
            hora_inicio=parser.getint("vuelos", "hora_inicio"),
            hora_fin=parser.getint("vuelos", "hora_fin"),
            concentracion_horas_punta=parser.getboolean("vuelos", "concentracion_horas_punta"),
            velocidad_crucero_kmh=parser.getfloat("vuelos", "velocidad_crucero_kmh"),
            prob_destino_exterior=parser.getfloat("vuelos", "prob_destino_exterior"),
            dist_exterior_km=parser.getfloat("vuelos", "dist_exterior_km"),
        )

        config_sim = ConfigSimulacion(
            paso_minutos=parser.getint("simulacion", "paso_minutos"),
            T_umbral_espera=parser.getint("simulacion", "T_umbral_espera"),
            seed=seed,
            umbral_distancia_tipo_avion=config_vuelos.umbral_distancia_tipo_avion,
            separar_minutos=parser.getint("simulacion", "separar_minutos"),
            factor_viento_a_favor=parser.getfloat("simulacion", "factor_viento_a_favor"),
            factor_viento_en_contra=parser.getfloat("simulacion", "factor_viento_en_contra"),
            factor_viento_neutro=parser.getfloat("simulacion", "factor_viento_neutro"),
            fuel_factor_a_favor=parser.getfloat("simulacion", "fuel_factor_a_favor"),
            fuel_factor_en_contra=parser.getfloat("simulacion", "fuel_factor_en_contra"),
            fuel_factor_neutro=parser.getfloat("simulacion", "fuel_factor_neutro"),
            tiempo_embarque_min=parser.getint("simulacion", "tiempo_embarque_min"),
            tiempo_turnaround_min=parser.getint("simulacion", "tiempo_turnaround_min"),
            ocupacion_inicial_min_fraccion=parser.getfloat("simulacion", "ocupacion_inicial_min_fraccion"),
            ocupacion_inicial_max_fraccion=parser.getfloat("simulacion", "ocupacion_inicial_max_fraccion"),
            exterior_top_n=parser.getint("simulacion", "exterior_top_n"),
            exterior_ruido_min=parser.getint("simulacion", "exterior_ruido_min"),
            exterior_ruido_max=parser.getint("simulacion", "exterior_ruido_max"),
            exterior_intervalo_min=parser.getint("simulacion", "exterior_intervalo_min"),
            exterior_intervalo_max=parser.getint("simulacion", "exterior_intervalo_max"),
            exterior_estancia_min=parser.getint("simulacion", "exterior_estancia_min"),
            exterior_estancia_max=parser.getint("simulacion", "exterior_estancia_max"),
            tmin_fase_asc_des_min=parser.getfloat("simulacion", "tmin_fase_asc_des_min"),
            tmin_fase_crucero_min=parser.getfloat("simulacion", "tmin_fase_crucero_min"),
        )

        dias_simulacion = parser.getint("simulacion", "dias")
        plan_aleatorio_por_dia = parser.getboolean("simulacion", "plan_aleatorio_por_dia")

        return cls(
            ruta_config=ruta_config.resolve(),
            seed=seed,
            aeropuertos_csv=aeropuertos_csv,
            aeropuertos_enriquecidos_csv=aeropuertos_enriquecidos_csv,
            flujos_csv=flujos_csv,
            epsg_origen=epsg_origen,
            capacidad_min=cap_min,
            capacidad_max=cap_max,
            prob_viento_a_favor=prob_vto_fav,
            prob_viento_en_contra=prob_vto_contra,
            prob_viento_neutro=prob_vto_neutro,
            grafo_pickle=grafo_pickle,
            plan_csv=plan_csv,
            resultados_csv=resultados_csv,
            logs_csv=logs_csv,
            eventos_csv=eventos_csv,
            config_vuelos=config_vuelos,
            config_simulacion=config_sim,
            dias_simulacion=dias_simulacion,
            plan_aleatorio_por_dia=plan_aleatorio_por_dia,
        )
