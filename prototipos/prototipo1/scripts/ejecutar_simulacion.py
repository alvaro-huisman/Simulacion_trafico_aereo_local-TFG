"""Escenario demostrativo del Prototipo 1 con 10 aeropuertos."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from ..core.configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..core.escenarios import construir_simulacion
from ..core.simulacion import SimulacionPrototipo1


def minutos_a_hhmm(valor: float) -> str:
    minutos = int(round(valor))
    horas, resto = divmod(minutos, 60)
    return f"{horas:02d}:{resto:02d}"


def mostrar_resumen(
    simulacion: SimulacionPrototipo1,
    identificador_simulacion: Optional[str],
    ruta_registros: Path,
    ruta_eventos: Optional[Path],
    duracion_minutos: int,
) -> None:
    if identificador_simulacion:
        print(f"Simulacion seleccionada: {identificador_simulacion}")
    print("Rutas estaticas (distancias aproximadas):")
    for origen, destino, distancia in simulacion.obtener_rutas_estaticas():
        print(f"  {origen} <-> {destino}: {distancia:7.2f}")
    print()

    simulacion.ejecutar(hasta=duracion_minutos)
    simulacion.exportar_registros_csv(ruta_registros)
    if ruta_eventos is not None:
        simulacion.exportar_eventos_csv(ruta_eventos)

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
    if ruta_eventos is not None:
        print(f"Eventos exportados en: {ruta_eventos}")


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta una simulacion del Prototipo 1 y muestra el resumen en consola."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
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
        "--semilla",
        type=int,
        default=None,
        help="Semilla base utilizada para regenerar planes cuando es necesario.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parsear_argumentos()
    config = AppConfig.cargar(args.config)

    semilla_base = args.semilla if args.semilla is not None else config.semilla_base
    numero_vuelos = config.escenarios_numero_vuelos
    directorio_escenarios = config.escenarios_directorio
    duracion_minutos = config.duracion_minutos

    if args.planes is not None:
        ruta_csv = args.planes
        identificador = ruta_csv.stem
        regenerar = not ruta_csv.exists()
        semilla_planes = semilla_base
    elif args.escenario is not None:
        numero = args.escenario
        max_escenarios = config.visualizacion_max_escenarios
        if not (1 <= numero <= max_escenarios):
            raise ValueError(f"El escenario debe estar entre 1 y {max_escenarios}.")
        directorio_escenarios.mkdir(parents=True, exist_ok=True)
        ruta_csv = directorio_escenarios / f"planes_aleatorios_{numero:03d}.csv"
        regenerar = not ruta_csv.exists()
        semilla_planes = semilla_base + numero
        identificador = f"escenario {numero:03d}"
    else:
        ruta_csv = config.plan_unico_csv
        identificador = "plan unico"
        regenerar = not ruta_csv.exists()
        semilla_planes = semilla_base

    guardar_eventos = config.guardar_eventos

    simulacion = construir_simulacion(
        ruta_csv,
        regenerar=regenerar,
        semilla_planes=semilla_planes,
        numero_vuelos=numero_vuelos,
        semilla_aeropuertos=config.semilla_aeropuertos,
        guardar_eventos=guardar_eventos,
        paso_minutos=config.paso_minutos,
        duracion_minutos=duracion_minutos,
        velocidad_crucero=config.velocidad_crucero,
        altura_crucero=config.altura_crucero,
        fraccion_ascenso=config.fraccion_ascenso,
    )

    ruta_registros = (
        config.plan_unico_registros
        if identificador == "plan unico"
        else _ruta_con_sufijo(config.plan_unico_registros, identificador)
    )
    ruta_eventos: Optional[Path]
    if guardar_eventos:
        base_eventos = config.plan_unico_eventos
        ruta_eventos = (
            base_eventos
            if identificador == "plan unico"
            else _ruta_con_sufijo(base_eventos, identificador)
        )
    else:
        ruta_eventos = None

    mostrar_resumen(
        simulacion,
        identificador_simulacion=identificador,
        ruta_registros=ruta_registros,
        ruta_eventos=ruta_eventos,
        duracion_minutos=duracion_minutos,
    )


def _ruta_con_sufijo(base: Path, identificador: str) -> Path:
    sufijo = identificador.replace(" ", "_")
    return base.with_name(f"{base.stem}_{sufijo}{base.suffix}")


if __name__ == "__main__":
    main()
