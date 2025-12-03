"""Carga de aeropuertos y utilidades geograficas para el Prototipo 2."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import networkx as nx
import pandas as pd
from geopy.distance import geodesic
from pyproj import Transformer

COL_ID = "ID_Aeropuerto"
COL_NOMBRE = "Nombre"
COL_LAT = "Latitud"
COL_LON = "Longitud"
COLUMNS_MINIMAS: tuple[str, ...] = (COL_ID, COL_NOMBRE, COL_LAT, COL_LON)


def cargar_aeropuertos_csv(ruta_csv: str | Path, epsg_origen: int = 4326) -> pd.DataFrame:
    """Lee un CSV de aeropuertos y valida/normaliza columnas basicas.

    Si el fichero trae X/Y en otra proyeccion (por ejemplo 3857) y columnas
    OBJECTID/TEXTO, se convierten a lat/lon (WGS84) y a ID/Nombre.
    """
    ruta = Path(ruta_csv)
    df = pd.read_csv(ruta)

    faltantes = [col for col in COLUMNS_MINIMAS if col not in df.columns]
    if faltantes:
        if {"X", "Y"}.issubset(df.columns):
            transformer = Transformer.from_crs(epsg_origen, 4326, always_xy=True)
            lon, lat = transformer.transform(df["X"].to_numpy(), df["Y"].to_numpy())
            df[COL_LON] = lon
            df[COL_LAT] = lat
        if "Texto" in df.columns:
            df[COL_NOMBRE] = df["Texto"]
        if "OBJECTID" in df.columns and COL_ID not in df.columns:
            df[COL_ID] = df["OBJECTID"].astype(str).radd("A")

    faltantes = [col for col in COLUMNS_MINIMAS if col not in df.columns]
    if faltantes:
        raise ValueError(
            f"El CSV {ruta} no tiene las columnas requeridas tras normalizar: {', '.join(faltantes)}"
        )
    return df


def construir_grafo(aeropuertos: pd.DataFrame) -> nx.Graph:
    """Construye un grafo no dirigido con nodos para cada aeropuerto.

    Los atributos almacenados en cada nodo son: nombre, lat, lon.
    """
    id_col = COL_ID if COL_ID in aeropuertos.columns else "id"
    nombre_col = COL_NOMBRE if COL_NOMBRE in aeropuertos.columns else "nombre"
    lat_col = COL_LAT if COL_LAT in aeropuertos.columns else "lat"
    lon_col = COL_LON if COL_LON in aeropuertos.columns else "lon"

    grafo = nx.Graph()
    for fila in aeropuertos.itertuples(index=False):
        grafo.add_node(
            getattr(fila, id_col),
            nombre=getattr(fila, nombre_col),
            lat=float(getattr(fila, lat_col)),
            lon=float(getattr(fila, lon_col)),
        )
    return grafo


def _coordenadas(df: pd.DataFrame, aeropuerto_id: str) -> tuple[float, float]:
    """Obtiene (lat, lon) de un aeropuerto o lanza ValueError si no existe."""
    id_col = COL_ID if COL_ID in df.columns else "id"
    lat_col = COL_LAT if COL_LAT in df.columns else "lat"
    lon_col = COL_LON if COL_LON in df.columns else "lon"
    fila = df.loc[df[id_col] == aeropuerto_id]
    if fila.empty:
        raise ValueError(f"Aeropuerto no encontrado: {aeropuerto_id}")
    lat = float(fila.iloc[0][lat_col])
    lon = float(fila.iloc[0][lon_col])
    return (lat, lon)


def distancia_km(
    origen_id: str,
    destino_id: str,
    aeropuertos: pd.DataFrame,
) -> float:
    """Calcula la distancia geodesica en km entre dos aeropuertos."""
    coord_origen = _coordenadas(aeropuertos, origen_id)
    coord_destino = _coordenadas(aeropuertos, destino_id)
    return float(geodesic(coord_origen, coord_destino).km)
