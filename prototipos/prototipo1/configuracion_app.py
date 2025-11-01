"""Utilidades para cargar la configuracion externa del prototipo."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
from typing import Optional, Type, TypeVar, cast

DEFAULT_CONFIG_PATH = Path(__file__).with_name("configuracion_inicial.txt")

_VT = TypeVar("_VT")


def cargar_configuracion(ruta: Optional[Path] = None) -> ConfigParser:
    """Carga la configuracion desde un archivo de texto.

    Combina los valores por defecto con el fichero ``configuracion_inicial.txt``.
    Si se proporciona ``ruta`` y existe, sus valores tienen prioridad.
    """
    configuracion = ConfigParser()
    configuracion.read_dict(
        {
            "general": {
                "semilla_base": "1234",
            },
            "aeropuertos": {
                "semilla": "2025",
            },
            "escenarios": {
                "directorio": "prototipos/prototipo1/escenarios",
                "cantidad": "50",
                "numero_vuelos": "60",
            },
            "plan_unico": {
                "ruta_csv": "prototipos/prototipo1/planes_aleatorios.csv",
            },
            "visualizacion": {
                "minuto_defecto": "720",
            },
            "recoleccion": {
                "salida_csv": "prototipos/prototipo1/registros_todos.csv",
            },
        }
    )

    rutas_a_leer = [DEFAULT_CONFIG_PATH]
    if ruta is not None:
        rutas_a_leer.append(ruta)
    configuracion.read([str(p) for p in rutas_a_leer if p.exists()])

    configuracion._ruta_base = (
        ruta if ruta is not None else DEFAULT_CONFIG_PATH  # type: ignore[attr-defined]
    )
    return configuracion


def _convertir_valor(valor: str, tipo: Type[_VT], base: Path) -> _VT:
    if tipo is Path:
        return cast(_VT, (base.parent / valor).resolve())
    if tipo is int:
        return cast(_VT, int(valor))
    if tipo is float:
        return cast(_VT, float(valor))
    if tipo is bool:
        valor = valor.lower()
        if valor in {"1", "true", "yes", "si"}:
            return cast(_VT, True)
        if valor in {"0", "false", "no"}:
            return cast(_VT, False)
        raise ValueError(f"No se puede interpretar '{valor}' como booleano.")
    return cast(_VT, valor)


def obtener_valor(
    configuracion: ConfigParser,
    seccion: str,
    opcion: str,
    tipo: Type[_VT],
    fallback: Optional[_VT] = None,
) -> _VT:
    """Obtiene y convierte un valor de la configuracion."""
    ruta_base: Path = getattr(configuracion, "_ruta_base", DEFAULT_CONFIG_PATH)  # type: ignore[assignment]
    if configuracion.has_option(seccion, opcion):
        valor = configuracion.get(seccion, opcion)
        return _convertir_valor(valor, tipo, ruta_base)
    if fallback is not None:
        return fallback
    raise KeyError(f"No se encontro '{opcion}' en la seccion '{seccion}'.")
