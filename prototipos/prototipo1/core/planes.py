"""Operaciones para generar y cargar planes de vuelo."""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Dict, Iterable, List

from prototipos.comun import Vector3

from .configuracion import VELOCIDAD_CRUCERO

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
    velocidad_crucero: float = VELOCIDAD_CRUCERO,
    horizonte_minutos: int = 24 * 60,
) -> Path:
    """Genera un CSV con planes de vuelo para un horizonte de 24 horas."""
    if numero_vuelos <= 0:
        raise ValueError("El numero de vuelos debe ser positivo.")
    if velocidad_crucero <= 0:
        raise ValueError("La velocidad de crucero debe ser positiva.")
    if horizonte_minutos <= 0:
        raise ValueError("El horizonte temporal debe ser positivo.")

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
            duracion = max(1, int(math.ceil(distancia / velocidad_crucero)))

            max_salida = horizonte_minutos - duracion
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
                    CAMPO_VELOCIDAD: velocidad_crucero,
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
    velocidad_crucero: float = VELOCIDAD_CRUCERO,
    horizonte_minutos: int = 24 * 60,
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
            velocidad_crucero=velocidad_crucero,
            horizonte_minutos=horizonte_minutos,
        )
        rutas.append(ruta)
    return rutas


def cargar_planes_csv(ruta_csv: Path) -> Iterable[Dict[str, str]]:
    """Carga los planes de vuelo desde un CSV previamente generado."""
    with ruta_csv.open("r", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        yield from lector
