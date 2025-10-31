"""Escenario demostrativo del Prototipo 1 con 10 aeropuertos."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

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


def construir_simulacion(
    ruta_csv: Path,
    regenerar: bool = True,
    semilla_planes: int = 1234,
) -> SimulacionPrototipo1:
    aeropuertos = generar_aeropuertos_demo()
    posiciones = obtener_posiciones(aeropuertos)
    if regenerar or not ruta_csv.exists():
        generar_planes_csv(ruta_csv, posiciones, semilla=semilla_planes)

    simulacion = SimulacionPrototipo1(paso_tiempo=1)
    simulacion.agregar_aeropuertos(aeropuertos)

    planes = cargar_planes_desde_csv(ruta_csv)
    simulacion.registrar_planes(planes)
    return simulacion


def mostrar_resumen(
    simulacion: SimulacionPrototipo1,
    identificador_simulacion: Optional[str] = None,
) -> None:
    if identificador_simulacion:
        print(f"Simulacion seleccionada: {identificador_simulacion}")
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


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta una simulacion del Prototipo 1 y muestra el resumen en consola."
    )
    parser.add_argument(
        "--planes",
        type=Path,
        default=None,
        help="Ruta a un CSV de planes de vuelo especifico.",
    )
    parser.add_argument(
        "--escenario",
        type=int,
        default=None,
        help="Numero de escenario (1-50) almacenado en el directorio de escenarios.",
    )
    parser.add_argument(
        "--escenarios-dir",
        type=Path,
        default=Path(__file__).with_name("escenarios"),
        help="Directorio donde se buscan los escenarios numerados.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=1234,
        help="Semilla base utilizada para regenerar planes cuando es necesario.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parsear_argumentos()

    if args.planes is not None:
        ruta_csv = args.planes
        identificador = ruta_csv.stem
        regenerar = not ruta_csv.exists()
        semilla = args.semilla
    elif args.escenario is not None:
        numero = args.escenario
        if not (1 <= numero <= 50):
            raise ValueError("El escenario debe estar entre 1 y 50.")
        args.escenarios_dir.mkdir(parents=True, exist_ok=True)
        ruta_csv = args.escenarios_dir / f"planes_aleatorios_{numero:03d}.csv"
        regenerar = not ruta_csv.exists()
        semilla = args.semilla + numero
        identificador = f"escenario {numero:03d}"
    else:
        ruta_csv = Path(__file__).with_name("planes_aleatorios.csv")
        identificador = "plan unico"
        regenerar = True
        semilla = args.semilla

    simulacion = construir_simulacion(
        ruta_csv,
        regenerar=regenerar,
        semilla_planes=semilla,
    )
    mostrar_resumen(simulacion, identificador_simulacion=identificador)


if __name__ == "__main__":
    main()
