"""Lectura y normalizacion de flujos anuales entre aeropuertos (Prototipo 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd


COL_ORIGEN = "Aeropuerto_Origen"
COL_DESTINO = "Aeropuerto_Destino"
COL_PASAJEROS = "Pasajeros"


def _extraer_codigo_nombre(valor: str) -> Tuple[str, str]:
    """Separa el codigo IATA y el nombre a partir de una cadena tipo "XXX : Nombre"."""
    if not isinstance(valor, str):
        return "", ""
    partes = valor.split(":", maxsplit=1)
    codigo = partes[0].strip().upper() if partes else ""
    nombre = partes[1].strip() if len(partes) > 1 else ""
    return codigo, nombre


def _parsear_pasajeros(valor: object) -> int:
    """Convierte un campo "Pasajeros" a entero, tolerando puntos/comas y separadores de miles."""
    if valor is None:
        return 0
    texto = str(valor).strip()
    if not texto:
        return 0
    # Normalizar separadores: quitar espacios y puntos de miles, cambiar coma decimal a punto
    texto_norm = texto.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return int(float(texto_norm))
    except ValueError:
        return 0


def leer_flujos_ministerio(path_csv: str | Path) -> pd.DataFrame:
    """Lee el CSV de flujos del Ministerio y devuelve un DataFrame normalizado.

    Columnas de salida: ``['origen_id', 'destino_id', 'pasajeros_anuales', 'origen_nombre', 'destino_nombre']``.

    - Extrae codigos IATA a partir de las columnas ``Aeropuerto_Origen`` y ``Aeropuerto_Destino``.
    - Limpia y convierte ``Pasajeros`` a entero (tolerando formato espanol).
    - Filtra filas con codigos vacios o pasajeros <= 0.
    """

    ruta = Path(path_csv)
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)

    origen_codigo, origen_nombre = zip(*df.get(COL_ORIGEN, []).map(_extraer_codigo_nombre))
    destino_codigo, destino_nombre = zip(*df.get(COL_DESTINO, []).map(_extraer_codigo_nombre))

    df_norm = pd.DataFrame(
        {
            "origen_id": origen_codigo,
            "destino_id": destino_codigo,
            "pasajeros_anuales": df.get(COL_PASAJEROS, []).map(_parsear_pasajeros),
            "origen_nombre": origen_nombre,
            "destino_nombre": destino_nombre,
        }
    )

    df_norm = df_norm[(df_norm["origen_id"] != "") & (df_norm["destino_id"] != "")]
    df_norm = df_norm[df_norm["pasajeros_anuales"] > 0]
    return df_norm.reset_index(drop=True)
