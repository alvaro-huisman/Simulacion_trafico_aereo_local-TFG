"""Compatibilidad: envoltorio del generador de planes CLI."""

from __future__ import annotations

from .core.planes import (
    CAMPO_DESTINO,
    CAMPO_ID,
    CAMPO_LLEGADA,
    CAMPO_ORIGEN,
    CAMPO_SALIDA,
    CAMPO_VELOCIDAD,
    cargar_planes_csv,
    generar_lote_planes_csv,
    generar_planes_csv,
)
from .scripts.generar_planes import _planificar_generacion as _planificar_generacion

__all__ = [
    "CAMPO_DESTINO",
    "CAMPO_ID",
    "CAMPO_LLEGADA",
    "CAMPO_ORIGEN",
    "CAMPO_SALIDA",
    "CAMPO_VELOCIDAD",
    "cargar_planes_csv",
    "generar_lote_planes_csv",
    "generar_planes_csv",
    "main",
]


def main() -> None:
    """Punto de entrada CLI compatible con versiones anteriores."""
    _planificar_generacion()


if __name__ == "__main__":
    main()
