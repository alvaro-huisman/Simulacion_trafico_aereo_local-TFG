"""Orquestador completo del Prototipo 1."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from ..core.configuracion import generar_aeropuertos_demo, obtener_posiciones
from ..core.configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..core.planes import generar_lote_planes_csv
from ..core.simulacion import SimulacionPrototipo1
from .recolectar_resultados import recolectar_resultados
from .visualizacion import construir_y_ejecutar_simulacion, mostrar_visualizador_con_menu


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genera los escenarios configurados, ejecuta todas las simulaciones y abre "
            "un visor interactivo para explorar los resultados."
        )
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
        help="Sobrescribe la cantidad de escenarios a procesar sin modificar la configuracion.",
    )
    parser.add_argument(
        "--sin-visualizacion",
        action="store_true",
        help="Omite la apertura del visor (solo genera planes y ejecuta simulaciones).",
    )
    return parser.parse_args()


def _generar_planes(config: AppConfig, cantidad: int) -> List[Path]:
    posiciones = obtener_posiciones(generar_aeropuertos_demo(semilla=config.semilla_aeropuertos))
    rutas = generar_lote_planes_csv(
        config.escenarios_directorio,
        posiciones,
        cantidad=cantidad,
        numero_vuelos=config.escenarios_numero_vuelos,
        semilla_inicial=config.semilla_base,
        velocidad_crucero=config.velocidad_crucero,
        horizonte_minutos=config.duracion_minutos,
    )
    return rutas


def main() -> None:
    args = _parsear_argumentos()
    config = AppConfig.cargar(args.config)

    cantidad = args.cantidad if args.cantidad is not None else config.escenarios_cantidad
    if cantidad <= 0:
        raise ValueError("La cantidad de escenarios debe ser positiva.")

    print(f"Generando {cantidad} planes de vuelo en {config.escenarios_directorio}...")
    rutas_planes = _generar_planes(config, cantidad)
    for ruta in rutas_planes:
        print(f"  - {ruta.name}")

    print("\nEjecutando simulaciones y consolidando resultados...")
    ruta_resultados = recolectar_resultados(
        cantidad=cantidad,
        directorio_escenarios=config.escenarios_directorio,
        numero_vuelos=config.escenarios_numero_vuelos,
        semilla_inicial=config.semilla_base,
        ruta_salida=config.resultados_registros,
        semilla_aeropuertos=config.semilla_aeropuertos,
        ruta_eventos=config.resultados_eventos if config.guardar_eventos else None,
        guardar_eventos=config.guardar_eventos,
        paso_minutos=config.paso_minutos,
        duracion_minutos=config.duracion_minutos,
        velocidad_crucero=config.velocidad_crucero,
        altura_crucero=config.altura_crucero,
        fraccion_ascenso=config.fraccion_ascenso,
    )
    print(f"\nRegistros consolidados en: {ruta_resultados}")
    if config.guardar_eventos and config.resultados_eventos.exists():
        print(f"Logs detallados en:       {config.resultados_eventos}")

    if args.sin_visualizacion:
        print("\nEjecucion finalizada sin abrir la interfaz visual.")
        return

    escenarios = list(range(1, cantidad + 1))
    print("\nIniciando visor interactivo...")

    def _generar_simulacion(numero: int) -> SimulacionPrototipo1:
        ruta_csv = config.escenarios_directorio / f"planes_aleatorios_{numero:03d}.csv"
        return construir_y_ejecutar_simulacion(
            ruta_csv,
            regenerar=False,
            semilla_planes=config.semilla_base + numero,
            numero_vuelos=config.escenarios_numero_vuelos,
            semilla_aeropuertos=config.semilla_aeropuertos,
            guardar_eventos=config.guardar_eventos,
            paso_minutos=config.paso_minutos,
            duracion_minutos=config.duracion_minutos,
            velocidad_crucero=config.velocidad_crucero,
            altura_crucero=config.altura_crucero,
            fraccion_ascenso=config.fraccion_ascenso,
        )

    try:
        mostrar_visualizador_con_menu(
            escenarios,
            _generar_simulacion,
            minuto_inicial=config.visualizacion_minuto,
            duracion_minutos=config.duracion_minutos,
        )
    except RuntimeError as exc:
        print(f"No fue posible abrir el visor interactivo: {exc}")
        print("Puedes visualizar cada escenario con:")
        print("  python -m prototipos.prototipo1.scripts.visualizacion --escenario N")


if __name__ == "__main__":
    main()
