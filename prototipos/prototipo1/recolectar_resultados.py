"""Agrega los resultados de multiples simulaciones en un unico CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from .configuracion import generar_aeropuertos_demo, obtener_posiciones
from .configuracion_app import DEFAULT_CONFIG_PATH, cargar_configuracion, obtener_valor
from .ejemplo import construir_simulacion
from .generar_planes import generar_planes_csv


def recolectar_resultados(
    cantidad: int,
    directorio_escenarios: Path,
    numero_vuelos: int,
    semilla_inicial: int,
    ruta_salida: Path,
    semilla_aeropuertos: int,
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
        )
        simulacion.ejecutar(hasta=24 * 60)
        dataframe = simulacion.registros_a_dataframe()
        dataframe.insert(0, "N_simulacion", indice)
        registros.append(dataframe)
        if simulacion.eventos:
            eventos_df = simulacion.eventos_a_dataframe()
            eventos_df.insert(0, "N_simulacion", indice)
            eventos.append(eventos_df)
        print(f"Simulacion completada: N_simulacion {indice:03d} -> {ruta_plan.name}")

    combinado = pd.concat(registros, ignore_index=True)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_csv(ruta_salida, index=False, encoding="utf-8")
    if eventos:
        eventos_combinados = pd.concat(eventos, ignore_index=True)
        ruta_eventos = ruta_salida.with_name(f"{ruta_salida.stem}_eventos.csv")
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
    configuracion = cargar_configuracion(args.config)

    cantidad = (
        args.cantidad
        if args.cantidad is not None
        else obtener_valor(configuracion, "escenarios", "cantidad", int)
    )
    numero_vuelos = (
        args.numero_vuelos
        if args.numero_vuelos is not None
        else obtener_valor(configuracion, "escenarios", "numero_vuelos", int)
    )
    directorio_escenarios = (
        args.escenarios_dir
        if args.escenarios_dir is not None
        else obtener_valor(configuracion, "escenarios", "directorio", Path)
    )
    ruta_salida = (
        args.salida
        if args.salida is not None
        else obtener_valor(configuracion, "recoleccion", "salida_csv", Path)
    )
    semilla_base = (
        args.semilla
        if args.semilla is not None
        else obtener_valor(configuracion, "general", "semilla_base", int)
    )
    semilla_aeropuertos = obtener_valor(configuracion, "aeropuertos", "semilla", int)

    ruta = recolectar_resultados(
        cantidad=cantidad,
        directorio_escenarios=directorio_escenarios,
        numero_vuelos=numero_vuelos,
        semilla_inicial=semilla_base,
        ruta_salida=ruta_salida,
        semilla_aeropuertos=semilla_aeropuertos,
    )
    print(f"Registros agregados en: {ruta}")


if __name__ == "__main__":
    main()
