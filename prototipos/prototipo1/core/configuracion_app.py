"""Helpers para cargar la configuracion del prototipo."""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configuracion_inicial.txt"

_DEFAULTS = {
    "general": {
        "semilla_base": "1234",
        "semilla_aeropuertos": "2025",
        "guardar_eventos": "yes",
    },
    "simulacion": {
        "paso_minutos": "1",
        "duracion_minutos": str(24 * 60),
    },
    "vuelo": {
        "velocidad_crucero": "8.33",
        "altura_crucero": "15.0",
        "fraccion_ascenso": "0.1",
    },
    "escenarios": {
        "directorio": "escenarios",
        "cantidad": "50",
        "numero_vuelos": "60",
    },
    "plan_unico": {
        "ruta_csv": "planes_aleatorios.csv",
        "registros_csv": "registros_vuelos.csv",
        "eventos_csv": "eventos_vuelos.csv",
    },
    "resultados": {
        "registros_csv": "registros_todos.csv",
        "eventos_csv": "registros_todos_eventos.csv",
    },
    "visualizacion": {
        "minuto_defecto": "720",
        "max_escenarios": "50",
    },
}


def _resolver_ruta(base: Path, valor: str) -> Path:
    return (base / valor).resolve()


@dataclass(frozen=True)
class AppConfig:
    """Representa los parametros de ejecucion leidos del archivo de configuracion."""

    ruta_config: Path
    semilla_base: int
    semilla_aeropuertos: int
    guardar_eventos: bool
    paso_minutos: int
    duracion_minutos: int
    velocidad_crucero: float
    altura_crucero: float
    fraccion_ascenso: float
    escenarios_directorio: Path
    escenarios_cantidad: int
    escenarios_numero_vuelos: int
    plan_unico_csv: Path
    plan_unico_registros: Path
    plan_unico_eventos: Path
    resultados_registros: Path
    resultados_eventos: Path
    visualizacion_minuto: int
    visualizacion_max_escenarios: int

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

        semilla_base = parser.getint("general", "semilla_base")
        semilla_aeropuertos = parser.getint("general", "semilla_aeropuertos")
        guardar_eventos = parser.getboolean("general", "guardar_eventos")

        paso_minutos = parser.getint("simulacion", "paso_minutos")
        duracion_minutos = parser.getint("simulacion", "duracion_minutos")

        velocidad_crucero = parser.getfloat("vuelo", "velocidad_crucero")
        altura_crucero = parser.getfloat("vuelo", "altura_crucero")
        fraccion_ascenso = parser.getfloat("vuelo", "fraccion_ascenso")

        escenarios_directorio = _resolver_ruta(
            base, parser.get("escenarios", "directorio")
        )
        escenarios_cantidad = parser.getint("escenarios", "cantidad")
        escenarios_numero_vuelos = parser.getint("escenarios", "numero_vuelos")

        plan_unico_csv = _resolver_ruta(base, parser.get("plan_unico", "ruta_csv"))
        plan_unico_registros = _resolver_ruta(
            base, parser.get("plan_unico", "registros_csv")
        )
        plan_unico_eventos = _resolver_ruta(
            base, parser.get("plan_unico", "eventos_csv")
        )

        resultados_registros = _resolver_ruta(
            base, parser.get("resultados", "registros_csv")
        )
        resultados_eventos = _resolver_ruta(
            base, parser.get("resultados", "eventos_csv")
        )

        visualizacion_minuto = parser.getint("visualizacion", "minuto_defecto")
        visualizacion_max_escenarios = parser.getint("visualizacion", "max_escenarios")

        return cls(
            ruta_config=ruta_config.resolve(),
            semilla_base=semilla_base,
            semilla_aeropuertos=semilla_aeropuertos,
            guardar_eventos=guardar_eventos,
            paso_minutos=paso_minutos,
            duracion_minutos=duracion_minutos,
            velocidad_crucero=velocidad_crucero,
            altura_crucero=altura_crucero,
            fraccion_ascenso=fraccion_ascenso,
            escenarios_directorio=escenarios_directorio,
            escenarios_cantidad=escenarios_cantidad,
            escenarios_numero_vuelos=escenarios_numero_vuelos,
            plan_unico_csv=plan_unico_csv,
            plan_unico_registros=plan_unico_registros,
            plan_unico_eventos=plan_unico_eventos,
            resultados_registros=resultados_registros,
            resultados_eventos=resultados_eventos,
            visualizacion_minuto=visualizacion_minuto,
            visualizacion_max_escenarios=visualizacion_max_escenarios,
        )
