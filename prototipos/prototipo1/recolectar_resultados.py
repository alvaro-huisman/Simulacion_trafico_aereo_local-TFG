"""Agrega los resultados de multiples simulaciones en un unico CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from .configuracion import generar_aeropuertos_demo, obtener_posiciones
from .ejemplo import construir_simulacion
from .generar_planes import generar_planes_csv


def recolectar_resultados(
    cantidad: int,
    directorio_escenarios: Path,
    numero_vuelos: int,
    semilla_inicial: int,
    ruta_salida: Path,
) -> Path:
    if cantidad <= 0:
        raise ValueError("La cantidad de escenarios debe ser positiva.")

    directorio_escenarios = directorio_escenarios.resolve()
    ruta_salida = ruta_salida.resolve()

    directorio_escenarios.mkdir(parents=True, exist_ok=True)

    posiciones = obtener_posiciones(generar_aeropuertos_demo())

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
    for indice, ruta_plan in enumerate(rutas_planes, start=1):
        simulacion = construir_simulacion(ruta_plan, regenerar=False)
        simulacion.ejecutar(hasta=24 * 60)
        dataframe = simulacion.registros_a_dataframe()
        dataframe.insert(0, "N_simulacion", indice)
        registros.append(dataframe)
        print(f"Simulacion completada: N_simulacion {indice:03d} -> {ruta_plan.name}")

    combinado = pd.concat(registros, ignore_index=True)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_csv(ruta_salida, index=False, encoding="utf-8")
    return ruta_salida


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta N simulaciones y consolida los resultados en un CSV."
    )
    parser.add_argument(
        "--cantidad",
        type=int,
        default=50,
        help="Numero de escenarios/dias a simular (por defecto 50).",
    )
    parser.add_argument(
        "--numero-vuelos",
        type=int,
        default=60,
        help="Numero de vuelos programados por escenario (por defecto 60).",
    )
    parser.add_argument(
        "--escenarios-dir",
        type=Path,
        default=Path(__file__).with_name("escenarios"),
        help="Directorio donde se almacenan los planes de vuelo por escenario.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path(__file__).with_name("registros_todos.csv"),
        help="Ruta del CSV combinado que se generara.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=1234,
        help="Semilla base para la generacion de escenarios.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parsear_argumentos()
    ruta = recolectar_resultados(
        cantidad=args.cantidad,
        directorio_escenarios=args.escenarios_dir,
        numero_vuelos=args.numero_vuelos,
        semilla_inicial=args.semilla,
        ruta_salida=args.salida,
    )
    print(f"Registros agregados en: {ruta}")


if __name__ == "__main__":
    main()
