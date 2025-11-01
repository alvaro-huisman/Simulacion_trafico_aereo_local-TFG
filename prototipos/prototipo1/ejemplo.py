"""Compatibilidad: escenario demostrativo del Prototipo 1."""

from __future__ import annotations

from .core.escenarios import cargar_planes_desde_csv, construir_simulacion
from .scripts.ejecutar_simulacion import main, mostrar_resumen

__all__ = [
    "cargar_planes_desde_csv",
    "construir_simulacion",
    "main",
    "mostrar_resumen",
]


if __name__ == "__main__":
    main()
