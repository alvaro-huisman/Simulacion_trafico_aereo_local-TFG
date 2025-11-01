"""Compatibilidad: visor interactivo de la red de aeropuertos."""

from __future__ import annotations

from .scripts.visualizacion import (
    VisualizadorRed,
    construir_y_ejecutar_simulacion,
    main,
    mostrar_visualizador_con_menu,
    vuelos_activos_en,
)

__all__ = [
    "VisualizadorRed",
    "construir_y_ejecutar_simulacion",
    "main",
    "mostrar_visualizador_con_menu",
    "vuelos_activos_en",
]


if __name__ == "__main__":
    main()
