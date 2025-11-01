"""Agrega los resultados de multiples simulaciones en un unico CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..core.configuracion import generar_aeropuertos_demo, obtener_posiciones
from ..core.configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..core.escenarios import construir_simulacion
from ..core.planes import generar_planes_csv


def recolectar_resultados(
    cantidad: int,
    directorio_escenarios: Path,
    numero_vuelos: int,
    semilla_inicial: int,
    ruta_salida: Path,
    semilla_aeropuertos: int,
    ruta_eventos: Optional[Path],
    guardar_eventos: bool,
    paso_minutos: int,
    duracion_minutos: int,
    velocidad_crucero: float,
    altura_crucero: float,
    fraccion_ascenso: float,
) -> Path:
    if cantidad <= 0:
        raise ValueError("La cantidad de escenarios debe ser positiva.")

    directorio_escenarios = directorio_escenarios.resolve()
    ruta_salida = ruta_salida.resolve()

    directorio_escenarios.mkdir(parents=True, exist_ok=True)

    posiciones = obtener_posiciones(generar_aeropuertos_demo(semilla=semilla_aeropuertos))

    rutas_planes = []
    for indice in range(1, cantidad + 1):
        ruta_plan = directorio_escenarios / f"planes_aleatorios_{indice:03d}.csv"
        if not ruta_plan.exists():
            semilla = semilla_inicial + indice
            generar_planes_csv(
                ruta_plan,
                posiciones,
                numero_vuelos=numero_vuelos,
                semilla=semilla,
                velocidad_crucero=velocidad_crucero,
                horizonte_minutos=duracion_minutos,
            )
        rutas_planes.append(ruta_plan)

    registros: List[pd.DataFrame] = []
    eventos: List[pd.DataFrame] = []
    for indice, ruta_plan in enumerate(rutas_planes, start=1):
        simulacion = construir_simulacion(
            ruta_plan,
            regenerar=False,
            semilla_planes=semilla_inicial + indice,
            numero_vuelos=numero_vuelos,
            semilla_aeropuertos=semilla_aeropuertos,
            guardar_eventos=guardar_eventos,
            paso_minutos=paso_minutos,
            duracion_minutos=duracion_minutos,
            velocidad_crucero=velocidad_crucero,
            altura_crucero=altura_crucero,
            fraccion_ascenso=fraccion_ascenso,
        )
        simulacion.ejecutar(hasta=duracion_minutos)
        dataframe = simulacion.registros_a_dataframe()
        dataframe.insert(0, "N_simulacion", indice)
        registros.append(dataframe)
        if guardar_eventos and simulacion.eventos:
            eventos_df = simulacion.eventos_a_dataframe()
            eventos_df.insert(0, "N_simulacion", indice)
            eventos.append(eventos_df)
        print(f"Simulacion completada: N_simulacion {indice:03d} -> {ruta_plan.name}")

    combinado = pd.concat(registros, ignore_index=True)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_csv(ruta_salida, index=False, encoding="utf-8")
    if eventos and ruta_eventos is not None:
        eventos_combinados = pd.concat(eventos, ignore_index=True)
        eventos_combinados.to_csv(ruta_eventos, index=False, encoding="utf-8")
        print(f"Eventos agregados en: {ruta_eventos}")
    return ruta_salida


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta N simulaciones y consolida los resultados en un CSV."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
    )
    parser.add_argument(
        "--cantidad",
        type=int,
        default=None,
        help="Numero de escenarios/dias a simular.",
    )
    parser.add_argument(
        "--numero-vuelos",
        type=int,
        default=None,
        help="Numero de vuelos programados por escenario.",
    )
    parser.add_argument(
        "--escenarios-dir",
        type=Path,
        default=None,
        help="Directorio donde se almacenan los planes de vuelo por escenario.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Ruta del CSV combinado que se generara.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=None,
        help="Semilla base para la generacion de escenarios.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parsear_argumentos()
    config = AppConfig.cargar(args.config)

    cantidad = args.cantidad if args.cantidad is not None else config.escenarios_cantidad
    numero_vuelos = (
        args.numero_vuelos
        if args.numero_vuelos is not None
        else config.escenarios_numero_vuelos
    )
    directorio_escenarios = (
        args.escenarios_dir
        if args.escenarios_dir is not None
        else config.escenarios_directorio
    )
    if args.salida is not None:
        ruta_salida = args.salida.resolve()
        ruta_eventos = (
            args.salida.with_name(f"{args.salida.stem}_eventos{args.salida.suffix}").resolve()
            if config.guardar_eventos
            else None
        )
    else:
        ruta_salida = config.resultados_registros
        ruta_eventos = config.resultados_eventos if config.guardar_eventos else None

    semilla_base = args.semilla if args.semilla is not None else config.semilla_base

    ruta = recolectar_resultados(
        cantidad=cantidad,
        directorio_escenarios=directorio_escenarios,
        numero_vuelos=numero_vuelos,
        semilla_inicial=semilla_base,
        ruta_salida=ruta_salida,
        semilla_aeropuertos=config.semilla_aeropuertos,
        ruta_eventos=ruta_eventos,
        guardar_eventos=config.guardar_eventos,
        paso_minutos=config.paso_minutos,
        duracion_minutos=config.duracion_minutos,
        velocidad_crucero=config.velocidad_crucero,
        altura_crucero=config.altura_crucero,
        fraccion_ascenso=config.fraccion_ascenso,
    )
    print(f"Registros agregados en: {ruta}")


if __name__ == "__main__":
    main()
