"""Utilidades para construir simulaciones a partir de planes de vuelo."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .configuracion import generar_aeropuertos_demo, obtener_posiciones
from .planes import (
    CAMPO_DESTINO,
    CAMPO_ID,
    CAMPO_LLEGADA,
    CAMPO_ORIGEN,
    CAMPO_SALIDA,
    CAMPO_VELOCIDAD,
    cargar_planes_csv,
    generar_planes_csv,
)
from .simulacion import PlanDeVuelo, SimulacionPrototipo1


def cargar_planes_desde_csv(ruta: Path) -> List[PlanDeVuelo]:
    """Convierte el CSV de planes en objetos PlanDeVuelo."""
    planes: List[PlanDeVuelo] = []
    for fila in cargar_planes_csv(ruta):
        plan = PlanDeVuelo(
            id_vuelo=fila[CAMPO_ID],
            id_origen=fila[CAMPO_ORIGEN],
            id_destino=fila[CAMPO_DESTINO],
            minuto_salida=int(fila[CAMPO_SALIDA]),
            minuto_llegada_programada=int(fila[CAMPO_LLEGADA]),
            velocidad_crucero=float(fila[CAMPO_VELOCIDAD]),
        )
        planes.append(plan)
    return planes


def construir_simulacion(
    ruta_csv: Path,
    *,
    regenerar: bool,
    semilla_planes: int,
    numero_vuelos: int,
    semilla_aeropuertos: int,
    guardar_eventos: bool,
    paso_minutos: int,
    duracion_minutos: int,
    velocidad_crucero: float,
    altura_crucero: float,
    fraccion_ascenso: float,
) -> SimulacionPrototipo1:
    """Construye y prepara la simulacion listo para ejecutarse."""
    aeropuertos = generar_aeropuertos_demo(semilla=semilla_aeropuertos)
    posiciones = obtener_posiciones(aeropuertos)

    if regenerar or not ruta_csv.exists():
        generar_planes_csv(
            ruta_csv,
            posiciones,
            numero_vuelos=numero_vuelos,
            semilla=semilla_planes,
            velocidad_crucero=velocidad_crucero,
            horizonte_minutos=duracion_minutos,
        )

    simulacion = SimulacionPrototipo1(
        paso_tiempo=paso_minutos,
        guardar_eventos=guardar_eventos,
        velocidad_crucero=velocidad_crucero,
        altura_crucero=altura_crucero,
        fraccion_ascenso=fraccion_ascenso,
    )
    simulacion.agregar_aeropuertos(aeropuertos)
    planes = cargar_planes_desde_csv(ruta_csv)
    simulacion.registrar_planes(planes)
    return simulacion
