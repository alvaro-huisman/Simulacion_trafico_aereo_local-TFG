"""Generador de planes de vuelo aleatorios para el Prototipo 1."""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Dict, Iterable, Tuple

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


def cargar_planes_csv(ruta_csv: Path) -> Iterable[Dict[str, str]]:
    """Carga los planes de vuelo desde un CSV previamente generado."""
    with ruta_csv.open("r", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            yield fila


if __name__ == "__main__":
    ruta_por_defecto = Path(__file__).with_name("planes_aleatorios.csv")
    from .configuracion import generar_aeropuertos_demo, obtener_posiciones

    aeropuertos_demo = generar_aeropuertos_demo()
    posiciones = obtener_posiciones(aeropuertos_demo)
    generar_planes_csv(ruta_por_defecto, posiciones)
    print(f"Archivo generado en: {ruta_por_defecto}")
