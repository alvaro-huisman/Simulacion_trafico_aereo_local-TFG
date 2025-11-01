"""Compatibilidad: agrega resultados de multiples simulaciones."""

from __future__ import annotations

from .scripts.recolectar_resultados import main, recolectar_resultados

__all__ = ["recolectar_resultados", "main"]


if __name__ == "__main__":
    main()
