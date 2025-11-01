"""Generador de planes de vuelo aleatorios para el Prototipo 1."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.configuracion import generar_aeropuertos_demo, obtener_posiciones
from ..core.configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..core.planes import (
    CAMPO_DESTINO,
    CAMPO_ID,
    CAMPO_LLEGADA,
    CAMPO_ORIGEN,
    CAMPO_SALIDA,
    CAMPO_VELOCIDAD,
    generar_lote_planes_csv,
    generar_planes_csv,
)


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera planes de vuelo aleatorios para el Prototipo 1."
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
        help="Numero de escenarios a generar (por defecto, valor del archivo de configuracion).",
    )
    parser.add_argument(
        "--numero-vuelos",
        type=int,
        default=None,
        help="Numero de vuelos programados por escenario.",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=None,
        help=(
            "Ruta del archivo CSV (si cantidad=1) o del directorio destino (si cantidad>1). "
            "Por defecto se usa el directorio 'escenarios' junto al modulo."
        ),
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=None,
        help="Semilla base para el generador de numeros aleatorios.",
    )
    return parser.parse_args()


def _planificar_generacion() -> None:
    args = _parsear_argumentos()
    config = AppConfig.cargar(args.config)

    cantidad = args.cantidad if args.cantidad is not None else config.escenarios_cantidad
    numero_vuelos = (
        args.numero_vuelos
        if args.numero_vuelos is not None
        else config.escenarios_numero_vuelos
    )
    semilla = args.semilla if args.semilla is not None else config.semilla_base
    velocidad_crucero = config.velocidad_crucero
    horizonte_minutos = config.duracion_minutos

    if cantidad <= 0:
        raise ValueError("La cantidad de escenarios debe ser positiva.")

    posiciones = obtener_posiciones(
        generar_aeropuertos_demo(semilla=config.semilla_aeropuertos)
    )

    if cantidad == 1:
        destino = (args.destino or config.plan_unico_csv).resolve()
        generar_planes_csv(
            destino,
            posiciones,
            numero_vuelos=numero_vuelos,
            semilla=semilla,
            velocidad_crucero=velocidad_crucero,
            horizonte_minutos=horizonte_minutos,
        )
        print(f"Archivo generado en: {destino}")
    else:
        directorio = (args.destino or config.escenarios_directorio).resolve()
        if directorio.suffix:
            raise ValueError("Para generar multiples escenarios el destino debe ser un directorio.")
        rutas = generar_lote_planes_csv(
            directorio,
            posiciones,
            cantidad=cantidad,
            numero_vuelos=numero_vuelos,
            semilla_inicial=semilla,
            velocidad_crucero=velocidad_crucero,
            horizonte_minutos=horizonte_minutos,
        )
        print(f"Escenarios generados en: {directorio}")
        for ruta in rutas:
            print(f"  - {ruta.name}")


if __name__ == "__main__":
    _planificar_generacion()
