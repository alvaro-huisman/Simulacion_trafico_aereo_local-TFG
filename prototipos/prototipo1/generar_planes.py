"""Generador de planes de vuelo aleatorios para el Prototipo 1."""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from prototipos.comun import Vector3
from .configuracion import VELOCIDAD_CRUCERO, generar_aeropuertos_demo, obtener_posiciones

CAMPO_ID = "id_vuelo"
CAMPO_ORIGEN = "origen"
CAMPO_DESTINO = "destino"
CAMPO_SALIDA = "minuto_salida"
CAMPO_LLEGADA = "minuto_llegada_programada"
CAMPO_VELOCIDAD = "velocidad_crucero"


def generar_planes_csv(
    ruta_csv: Path,
    posiciones: Dict[str, Vector3],
    numero_vuelos: int = 60,
    semilla: int = 1234,
) -> Path:
    """Genera un CSV con planes de vuelo para un horizonte de 24 horas."""
    if numero_vuelos <= 0:
        raise ValueError("El numero de vuelos debe ser positivo.")

    ruta_csv.parent.mkdir(parents=True, exist_ok=True)

    generador = random.Random(semilla)
    identificadores = list(posiciones.keys())
    campos = [
        CAMPO_ID,
        CAMPO_ORIGEN,
        CAMPO_DESTINO,
        CAMPO_SALIDA,
        CAMPO_LLEGADA,
        CAMPO_VELOCIDAD,
    ]

    with ruta_csv.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()

        vuelos_creados = 0
        intentos = 0
        max_intentos = numero_vuelos * 20

        while vuelos_creados < numero_vuelos and intentos < max_intentos:
            intentos += 1
            origen, destino = generador.sample(identificadores, 2)
            distancia = math.dist(posiciones[origen], posiciones[destino])
            duracion = max(1, int(math.ceil(distancia / VELOCIDAD_CRUCERO)))

            max_salida = (24 * 60) - duracion
            if max_salida <= 0:
                continue

            minuto_salida = generador.randint(0, max_salida)
            minuto_llegada = minuto_salida + duracion

            identificador = f"{origen}{destino}{vuelos_creados:03d}"
            escritor.writerow(
                {
                    CAMPO_ID: identificador,
                    CAMPO_ORIGEN: origen,
                    CAMPO_DESTINO: destino,
                    CAMPO_SALIDA: minuto_salida,
                    CAMPO_LLEGADA: minuto_llegada,
                    CAMPO_VELOCIDAD: VELOCIDAD_CRUCERO,
                }
            )
            vuelos_creados += 1

        if vuelos_creados < numero_vuelos:
            raise RuntimeError(
                f"No fue posible generar {numero_vuelos} planes de vuelo con los datos proporcionados."
            )

    return ruta_csv


def generar_lote_planes_csv(
    directorio: Path,
    posiciones: Dict[str, Vector3],
    cantidad: int,
    numero_vuelos: int = 60,
    semilla_inicial: int = 1234,
) -> List[Path]:
    """Genera varios CSV de planes numerados secuencialmente."""
    if cantidad <= 0:
        raise ValueError("La cantidad de escenarios debe ser positiva.")

    directorio.mkdir(parents=True, exist_ok=True)
    rutas: List[Path] = []
    for indice in range(1, cantidad + 1):
        semilla = semilla_inicial + indice
        ruta = directorio / f"planes_aleatorios_{indice:03d}.csv"
        generar_planes_csv(
            ruta,
            posiciones,
            numero_vuelos=numero_vuelos,
            semilla=semilla,
        )
        rutas.append(ruta)
    return rutas


def cargar_planes_csv(ruta_csv: Path) -> Iterable[Dict[str, str]]:
    """Carga los planes de vuelo desde un CSV previamente generado."""
    with ruta_csv.open("r", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            yield fila


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera planes de vuelo aleatorios para el Prototipo 1."
    )
    parser.add_argument(
        "--cantidad",
        type=int,
        default=1,
        help="Numero de escenarios a generar (por defecto 1).",
    )
    parser.add_argument(
        "--numero-vuelos",
        type=int,
        default=60,
        help="Numero de vuelos programados por escenario (por defecto 60).",
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
        default=1234,
        help="Semilla base para el generador de numeros aleatorios.",
    )
    return parser.parse_args()


def _resolver_destino(cantidad: int, destino: Path | None) -> Tuple[Path, bool]:
    if cantidad == 1:
        if destino is None:
            destino = Path(__file__).with_name("planes_aleatorios.csv")
        return destino, False

    if destino is None:
        destino = Path(__file__).with_name("escenarios")
    return destino, True


if __name__ == "__main__":
    args = _parsear_argumentos()
    destino, es_directorio = _resolver_destino(args.cantidad, args.destino)

    aeropuertos_demo = generar_aeropuertos_demo()
    posiciones = obtener_posiciones(aeropuertos_demo)

    if es_directorio:
        rutas = generar_lote_planes_csv(
            destino,
            posiciones,
            cantidad=args.cantidad,
            numero_vuelos=args.numero_vuelos,
            semilla_inicial=args.semilla,
        )
        print(f"Escenarios generados en: {destino}")
        for ruta in rutas:
            print(f"  - {ruta.name}")
    else:
        generar_planes_csv(
            destino,
            posiciones,
            numero_vuelos=args.numero_vuelos,
            semilla=args.semilla,
        )
        print(f"Archivo generado en: {destino}")
