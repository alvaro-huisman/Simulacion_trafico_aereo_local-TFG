"""Escenario demostrativo del Prototipo 1 con 10 aeropuertos."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from prototipos.prototipo1 import PlanDeVuelo, SimulacionPrototipo1
from prototipos.prototipo1.configuracion import (
    generar_aeropuertos_demo,
    obtener_posiciones,
)
from prototipos.prototipo1.generar_planes import (
    CAMPO_DESTINO,
    CAMPO_ID,
    CAMPO_LLEGADA,
    CAMPO_ORIGEN,
    CAMPO_SALIDA,
    CAMPO_VELOCIDAD,
    cargar_planes_csv,
    generar_planes_csv,
)


def minutos_a_hhmm(valor: float) -> str:
    minutos = int(round(valor))
    horas, resto = divmod(minutos, 60)
    return f"{horas:02d}:{resto:02d}"


def cargar_planes_desde_csv(ruta: Path) -> List[PlanDeVuelo]:
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


def construir_simulacion(ruta_csv: Path) -> SimulacionPrototipo1:
    aeropuertos = generar_aeropuertos_demo()
    posiciones = obtener_posiciones(aeropuertos)
    generar_planes_csv(ruta_csv, posiciones)

    simulacion = SimulacionPrototipo1(paso_tiempo=1)
    simulacion.agregar_aeropuertos(aeropuertos)

    planes = cargar_planes_desde_csv(ruta_csv)
    simulacion.registrar_planes(planes)
    return simulacion


def mostrar_resumen(simulacion: SimulacionPrototipo1) -> None:
    print("Rutas estaticas (distancias aproximadas):")
    for origen, destino, distancia in simulacion.obtener_rutas_estaticas():
        print(f"  {origen} <-> {destino}: {distancia:7.2f}")
    print()

    simulacion.ejecutar(hasta=24 * 60)
    ruta_registros = Path(__file__).with_name("registros_vuelos.csv")
    simulacion.exportar_registros_csv(ruta_registros)

    print("Vuelos completados:")
    for registro in simulacion.registros_finalizados:
        salida = minutos_a_hhmm(registro.minuto_salida)
        llegada_prog = minutos_a_hhmm(registro.minuto_llegada_programada)
        llegada_real = minutos_a_hhmm(registro.minuto_llegada_real)
        retraso = f"{int(round(registro.retraso))} min"
        print(
            f"  {registro.id_vuelo}: {registro.id_origen} -> {registro.id_destino} | "
            f"Salida {salida} | Llegada prevista {llegada_prog} | "
            f"Llegada real {llegada_real} | Retraso {retraso}"
        )

    retrasados = [
        registro for registro in simulacion.registros_finalizados if registro.retraso > 0
    ]
    if retrasados:
        print("\nDetalle de un vuelo con cola de espera:")
        registro = retrasados[0]
        for instantanea in registro.instantaneas[:5]:
            instante = minutos_a_hhmm(instantanea.minuto)
            progreso = f"{instantanea.progreso * 100:5.1f}%"
            posicion = ", ".join(f"{coord:7.2f}" for coord in instantanea.posicion)
            llegada = minutos_a_hhmm(instantanea.llegada_estimacion)
            print(
                f"  t={instante} | pos=({posicion}) | progreso={progreso} | ETA={llegada}"
            )
    else:
        print("\nNo se registraron retrasos en este horizonte.")

    print(f"\nRegistros exportados en: {ruta_registros}")


def main() -> None:
    ruta_csv = Path(__file__).with_name("planes_aleatorios.csv")
    simulacion = construir_simulacion(ruta_csv)
    mostrar_resumen(simulacion)


if __name__ == "__main__":
    main()
