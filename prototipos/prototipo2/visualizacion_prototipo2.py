"""Herramientas basicas de visualizacion para el Prototipo 2."""

from __future__ import annotations

from typing import Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import numpy as np
from pyproj import Transformer
import random
from matplotlib.path import Path
from matplotlib.widgets import Slider, TextBox

try:
    import contextily as ctx  # opcional para mapa base
except ImportError:  # pragma: no cover
    ctx = None

from .generacion_vuelos import ConfigVuelos
from .simulador_prototipo2 import (
    ConfigSimulacion,
    TIPO_CORTO_RADIO,
    TIPO_MEDIO_RADIO,
    TipoAeronave,
)

def dibujar_grafo_rutas(
    G: nx.Graph,
    aeropuertos: pd.DataFrame,
    mostrar_pesos: bool = False,
    figsize: tuple[int, int] = (10, 8),
) -> None:
    """Dibuja el grafo en 2D usando lon/lat de los aeropuertos.

    Parameters
    ----------
    G : nx.Graph
        Grafo con nodos = ids IATA y aristas con atributos opcionales.
    aeropuertos : pd.DataFrame
        DataFrame con columnas `id`, `lat`, `lon`.
    mostrar_pesos : bool, optional
        Si True, anota el peso relativo `w_ij` en las aristas.
    figsize : tuple[int, int]
        Tamaño de la figura de matplotlib.
    """

    pos = {}
    for fila in aeropuertos.itertuples(index=False):
        pos[getattr(fila, "id")] = (float(getattr(fila, "lon")), float(getattr(fila, "lat")))

    plt.figure(figsize=figsize)
    nx.draw_networkx_edges(G, pos, alpha=0.4, edge_color="#999999")
    nx.draw_networkx_nodes(G, pos, node_color="#1f78b4", node_size=100)
    nx.draw_networkx_labels(G, pos, font_size=8)

    if mostrar_pesos:
        etiquetas = {edge: f"{datos.get('w_ij', 0):.2f}" for edge, datos in G.edges.items()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas, font_size=7, alpha=0.7)

    plt.xlabel("Longitud")
    plt.ylabel("Latitud")
    plt.title("Red de aeropuertos y rutas (Prototipo 2)")
    plt.tight_layout()
    plt.show()


def mostrar_tabla_resumen_vuelos(df_vuelos: pd.DataFrame, max_filas: int = 10) -> pd.DataFrame:
    """Devuelve un subset de vuelos para inspeccion rapida."""
    columnas = [
        "id_vuelo",
        "origen",
        "destino_programado",
        "destino_final",
        "redirigido",
        "salida_programada",
        "llegada_real",
        "retraso_total_min",
        "combustible_consumido_kg",
        "tipo_aeronave",
    ]
    existentes = [c for c in columnas if c in df_vuelos.columns]
    return df_vuelos[existentes].head(max_filas)


def histograma_retrasos(df_vuelos: pd.DataFrame, columna: str = "retraso_total_min") -> None:
    """Grafica un histograma de la columna de retrasos (en minutos)."""
    if columna not in df_vuelos.columns:
        raise ValueError(f"La columna {columna} no existe en el DataFrame")
    plt.figure(figsize=(8, 4))
    df_vuelos[columna].plot(kind="hist", bins=20, color="#ff7f0e", alpha=0.8)
    plt.xlabel("Retraso (minutos)")
    plt.ylabel("Frecuencia")
    plt.title(f"Distribucion de {columna}")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Visor interactivo simple (lon/lat con slider de minutos)
# ---------------------------------------------------------------------------


def _posicion_en_minuto(
    origen: Tuple[float, float],
    destino: Tuple[float, float],
    salida: float,
    llegada: float,
    minuto: float,
) -> Tuple[float, float]:
    if minuto <= salida:
        return origen
    if minuto >= llegada:
        return destino
    progreso = (minuto - salida) / max(1e-6, (llegada - salida))
    lon = origen[0] + progreso * (destino[0] - origen[0])
    lat = origen[1] + progreso * (destino[1] - origen[1])
    return (lon, lat)


def _fase_y_altitud(progreso: float, tipo: TipoAeronave) -> Tuple[str, float]:
    """Determina la fase y una altitud aproximada (ft) en funcion del progreso."""
    if progreso <= 0.1:
        fase = "ascenso"
        alt = tipo.nivel_crucero_min_ft * (progreso / 0.1)
    elif progreso >= 0.9:
        fase = "descenso"
        alt = tipo.nivel_crucero_min_ft * max(0.0, (1.0 - progreso) / 0.1)
    else:
        fase = "crucero"
        alt = (tipo.nivel_crucero_min_ft + tipo.nivel_crucero_max_ft) / 2.0
    return fase, alt


def visor_interactivo(
    G: nx.Graph,
    aeropuertos: pd.DataFrame,
    plan: pd.DataFrame,
    *,
    config_vuelos: Optional[ConfigVuelos] = None,
    config_sim: Optional[ConfigSimulacion] = None,
    eventos: Optional[pd.DataFrame] = None,
    resultados: Optional[pd.DataFrame] = None,
    dias_max: int = 1,
    minuto_max: int = 1440,
    usar_mapa_fondo: bool = True,
) -> None:
    """Muestra la red y los vuelos con un slider de minutos."""
    # Posiciones lon/lat a partir del DataFrame normalizado
    id_col = "id" if "id" in aeropuertos.columns else ("ID_Aeropuerto" if "ID_Aeropuerto" in aeropuertos.columns else aeropuertos.columns[0])
    lat_col = "lat" if "lat" in aeropuertos.columns else ("Latitud" if "Latitud" in aeropuertos.columns else aeropuertos.columns[1])
    lon_col = "lon" if "lon" in aeropuertos.columns else ("Longitud" if "Longitud" in aeropuertos.columns else aeropuertos.columns[2])
    nombre_col = "nombre" if "nombre" in aeropuertos.columns else ("Nombre" if "Nombre" in aeropuertos.columns else None)
    pos_geo: dict[str, Tuple[float, float]] = {}
    nombres: dict[str, str] = {}
    aer_info: dict[str, dict] = {}
    for fila in aeropuertos.itertuples(index=False):
        ident = getattr(fila, id_col)
        if ident in G.nodes:
            pos_geo[ident] = (float(getattr(fila, lon_col)), float(getattr(fila, lat_col)))
            if nombre_col is not None:
                nombres[ident] = getattr(fila, nombre_col)
            aer_info[ident] = fila._asdict()
    rng_viento = random.Random(config_sim.seed if config_sim else 0)
    viento_cache: dict[Tuple[str, str], str] = {}
    # Completar vientos por aeropuerto si faltan o son neutros
    for aid, info in aer_info.items():
        for fase in ("baja", "alta"):
            clave = (aid, fase)
            etiqueta = info.get(f"viento_{'baja' if fase=='baja' else 'alta'}_cota", None)
            if etiqueta in (None, "", "neutro"):
                viento_cache[clave] = rng_viento.choices(
                    ["a_favor", "en_contra", "neutro"], weights=[0.3, 0.3, 0.4], k=1
                )[0]
            else:
                viento_cache[clave] = etiqueta
    # Preparar ocupaciones si hay eventos
    eventos_por_aer: dict[str, pd.DataFrame] = {}
    if eventos is not None and {"aeropuerto", "minuto", "ocupacion"}.issubset(eventos.columns):
        for aid, df_group in eventos.groupby("aeropuerto"):
            eventos_por_aer[aid] = df_group.sort_values("minuto")
    redirigidos_ids: set[str] = set()
    if resultados is not None and {"redirigido", "id_vuelo"}.issubset(resultados.columns):
        redirigidos_ids = set(resultados.loc[resultados["redirigido"] == True, "id_vuelo"].astype(str))

    # Transformar a WebMercator si queremos fondo de mapa
    if usar_mapa_fondo and ctx is not None:
        transformer = Transformer.from_crs(4326, 3857, always_xy=True)
        pos = {nid: transformer.transform(lon, lat) for nid, (lon, lat) in pos_geo.items()}
        crs = "EPSG:3857"
    else:
        pos = pos_geo
        crs = "EPSG:4326"

    # Replicar plan por dias si se solicita
    plan_local = plan.copy()
    if "dia" not in plan_local.columns:
        dias_max = max(1, dias_max)
        plan_list = []
        for d in range(1, dias_max + 1):
            temp = plan_local.copy()
            offset = (d - 1) * 1440
            temp["dia"] = d
            temp["minuto_salida"] = temp["minuto_salida"] + offset
            if "minuto_llegada_programada" in temp.columns:
                temp["minuto_llegada_programada"] = temp["minuto_llegada_programada"] + offset
            elif "duracion_minutos" in temp.columns:
                temp["minuto_llegada_programada"] = temp["minuto_salida"] + temp["duracion_minutos"]
            plan_list.append(temp)
        plan_local = pd.concat(plan_list, ignore_index=True)
    else:
        dias_max = int(plan_local["dia"].max())
        if "minuto_llegada_programada" not in plan_local.columns and "duracion_minutos" in plan_local.columns:
            plan_local["minuto_llegada_programada"] = plan_local["minuto_salida"] + plan_local["duracion_minutos"]
    minuto_min = 0.0
    minuto_max_global = 1440 * dias_max

    fig, ax = plt.subplots(figsize=(10, 8))
    plt.subplots_adjust(bottom=0.23)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Vuelos activos (slider por minuto)")

    # Nodos y aristas base
    edges_valid = [(u, v) for u, v in G.edges if u in pos and v in pos]
    nx.draw_networkx_edges(G, pos, edgelist=edges_valid, alpha=0.2, ax=ax, edge_color="#999999", width=0.5)
    nodelist = list(pos.keys())
    nodos_plot = nx.draw_networkx_nodes(G, pos, nodelist=nodelist, node_color="#1f78b4", node_size=80, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: n for n in nodelist}, font_size=7, ax=ax)

    # Scatter para vuelos (se actualiza) con un Path en forma de avion mas nítido
    avion_path = Path(
        [
            (0.0, 0.6),    # nariz
            (-0.35, -0.05),  # ala izq
            (-0.12, -0.12),  # cola izq
            (-0.12, -0.5),   # cola fin izq
            (0.0, -0.35),    # timon
            (0.12, -0.5),    # cola fin der
            (0.12, -0.12),   # cola der
            (0.35, -0.05),   # ala der
            (0.0, 0.6),      # nariz
        ],
        [
            Path.MOVETO,
            Path.LINETO,
            Path.LINETO,
            Path.LINETO,
            Path.LINETO,
            Path.LINETO,
            Path.LINETO,
            Path.LINETO,
            Path.CLOSEPOLY,
        ],
    )
    scatter = ax.scatter([], [], s=[], c=[], marker=avion_path, edgecolors="k", linewidths=0.4, zorder=4)

    eje_slider_min = plt.axes([0.12, 0.05, 0.76, 0.03])
    slider_min = Slider(eje_slider_min, "Minuto dia", valmin=0.0, valmax=1439.0, valinit=0.0, valstep=1.0)

    # Selector de dia: Dropdown si está disponible, si no, slider de día
    opciones_dia = [str(i) for i in range(1, dias_max + 1)]
    dia_actual = [1]
    # Cuadro de texto para seleccionar dia (scrollable / editable)
    eje_texto_dia = plt.axes([0.12, 0.10, 0.15, 0.05])
    texto_dia = TextBox(eje_texto_dia, "Dia", initial=opciones_dia[0])

    # Añadir mapa base si se solicitó y contextily está disponible
    if usar_mapa_fondo and ctx is not None and pos:
        xs, ys = zip(*pos.values())
        buffer = 50000 if crs == "EPSG:3857" else 1.0
        ax.set_xlim(min(xs) - buffer, max(xs) + buffer)
        ax.set_ylim(min(ys) - buffer, max(ys) + buffer)
        if crs == "EPSG:3857":
            # Fallback robusto a tiles libres si no está disponible la clave
            fuente = getattr(ctx.providers, "CartoDB", ctx.providers.OpenStreetMap).PositronNoLabels
            ctx.add_basemap(ax, crs=crs, source=fuente)

    vuelos_visibles: list[dict] = []
    ocupacion_actual: dict[str, tuple[int, int]] = {}
    anotacion = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(10, 10),
        textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.7),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
    )
    anotacion.set_visible(False)

    def actualizar(val: float) -> None:
        try:
            dia_sel = int(float(texto_dia.text))
        except Exception:
            dia_sel = 1
        dia_sel = max(1, min(dias_max, dia_sel))
        dia_actual[0] = dia_sel
        minuto_local = slider_min.val
        minuto = (dia_sel - 1) * 1440 + minuto_local
        lons: list[float] = []
        lats: list[float] = []
        tamanos: list[float] = []
        colores: list[str] = []
        vuelos_visibles.clear()
        ocupacion_actual.clear()
        if eventos_por_aer:
            for aid, df_e in eventos_por_aer.items():
                filtrado = df_e[df_e["minuto"] <= minuto]
                if filtrado.empty:
                    continue
                ultimo = filtrado.iloc[-1]
                ocupacion_actual[aid] = (int(ultimo.get("ocupacion", 0)), int(ultimo.get("capacidad", 0)))
        for fila in plan_local.itertuples(index=False):
            salida = float(getattr(fila, "minuto_salida"))
            llegada = float(getattr(fila, "minuto_llegada_programada"))
            if not (salida <= minuto <= llegada):
                continue
            origen = pos.get(getattr(fila, "origen"))
            destino = pos.get(getattr(fila, "destino"))
            if origen is None or destino is None:
                continue
            lon, lat = _posicion_en_minuto(origen, destino, salida, llegada, minuto)
            lons.append(lon)
            lats.append(lat)
            # tamaño según tipo aeronave o distancia
            dist = getattr(fila, "distancia_km", 0.0)
            umbral = config_vuelos.umbral_distancia_tipo_avion if config_vuelos else 700.0
            tamanos.append(30.0 if dist <= umbral else 60.0)
            id_v = str(getattr(fila, "id_vuelo", ""))
            if id_v in redirigidos_ids:
                colores.append("#d62728")
            else:
                colores.append("#ff7f0e" if dist <= umbral else "#1f77b4")
            tipo = TIPO_CORTO_RADIO if dist <= umbral else TIPO_MEDIO_RADIO
            progreso = (minuto - salida) / max(1e-6, (llegada - salida))
            fase, alt_ft = _fase_y_altitud(progreso, tipo)
            # Velocidad efectiva por fase con viento aproximado
            if fase == "ascenso":
                base_v = tipo.vel_asc_kmh
                viento = viento_cache.get((getattr(fila, "origen"), "baja"), "neutro")
            elif fase == "descenso":
                base_v = tipo.vel_des_kmh
                viento = viento_cache.get((getattr(fila, "destino"), "baja"), "neutro")
            else:
                base_v = tipo.vel_cru_kmh
                viento = viento_cache.get((getattr(fila, "origen"), "alta"), "neutro")
            factor = 1.0
            if config_sim:
                if viento == "a_favor":
                    factor = config_sim.factor_viento_a_favor
                elif viento == "en_contra":
                    factor = config_sim.factor_viento_en_contra
                else:
                    factor = config_sim.factor_viento_neutro
            vel_efectiva = base_v * factor
            # Combustible estimado restante (aprox lineal por fase, ajustado por viento)
            dur_total = (llegada - salida)
            dur_asc = dur_total * 0.1
            dur_cru = dur_total * 0.8
            dur_des = dur_total * 0.1
            total_fuel = (
                (dur_asc / 60.0) * tipo.consumo_asc_l_h
                + (dur_cru / 60.0) * tipo.consumo_cru_l_h
                + (dur_des / 60.0) * tipo.consumo_des_l_h
            )
            elapsed = minuto - salida
            if elapsed <= dur_asc:
                fuel_used = (elapsed / 60.0) * tipo.consumo_asc_l_h
            elif elapsed <= dur_asc + dur_cru:
                fuel_used = (dur_asc / 60.0) * tipo.consumo_asc_l_h
                fuel_used += ((elapsed - dur_asc) / 60.0) * tipo.consumo_cru_l_h
            else:
                fuel_used = (dur_asc / 60.0) * tipo.consumo_asc_l_h
                fuel_used += (dur_cru / 60.0) * tipo.consumo_cru_l_h
                fuel_used += ((elapsed - dur_asc - dur_cru) / 60.0) * tipo.consumo_des_l_h
            fuel_rest = max(0.0, total_fuel - fuel_used)
            vuelos_visibles.append(
                {
                    "lon": lon,
                    "lat": lat,
                    "id": getattr(fila, "id_vuelo", ""),
                    "origen": getattr(fila, "origen"),
                    "destino": getattr(fila, "destino"),
                    "dist": dist,
                    "fase": fase,
                    "alt_ft": alt_ft,
                    "vel": vel_efectiva,
                    "viento": viento,
                    "fuel_rest": fuel_rest,
                }
            )

        if lons:
            coords = list(zip(lons, lats))
            scatter.set_offsets(coords)
        else:
            scatter.set_offsets(np.empty((0, 2)))
        scatter.set_sizes(tamanos if tamanos else [1])
        scatter.set_color(colores if colores else ["#ff7f0e"])
        fig.canvas.draw_idle()

    def _mostrar_info(event) -> None:
        # Primero vuelos
        contiene, detalles = scatter.contains(event)
        if contiene and detalles.get("ind"):
            idx = detalles["ind"][0]
            if idx < len(vuelos_visibles):
                info = vuelos_visibles[idx]
                anotacion.xy = (info["lon"], info["lat"])
                o_name = nombres.get(info["origen"], info["origen"])
                d_name = nombres.get(info["destino"], info["destino"])
                texto = (
                    f"{info['id'] or 'Vuelo'}\n"
                    f"{o_name} -> {d_name}\n"
                    f"Fase: {info['fase']} | Alt: {info['alt_ft']:.0f} ft\n"
                    f"Vel: {info['vel']:.0f} km/h | Viento: {info['viento']}\n"
                    f"Dist: {info['dist']:.0f} km | Fuel restante: {info['fuel_rest']:.0f} L"
                )
                anotacion.set_text(texto)
                anotacion.set_visible(True)
                fig.canvas.draw_idle()
                return

        # Luego nodos
        contiene_nodo, det_nodo = nodos_plot.contains(event)
        indices = det_nodo.get("ind", [])
        if contiene_nodo and len(indices) > 0:
            idx = indices[0]
            nodo_id = nodelist[idx]
            if nodo_id in pos:
                lon, lat = pos[nodo_id]
                anotacion.xy = (lon, lat)
                nombre = nombres.get(nodo_id, nodo_id)
                viento_bc = viento_cache.get((nodo_id, "baja"), "neutro")
                viento_ac = viento_cache.get((nodo_id, "alta"), "neutro")
                cap_total = None
                if nodo_id in aer_info and "capacidad" in aer_info[nodo_id]:
                    cap_total = aer_info[nodo_id]["capacidad"]
                if nodo_id in ocupacion_actual:
                    ocup, cap_evt = ocupacion_actual[nodo_id]
                    cap_total = cap_evt or cap_total
                    cap_text = f"Cap: {ocup}/{cap_total}" if cap_total else f"Ocup: {ocup}"
                else:
                    cap_text = f"Cap: {cap_total}" if cap_total else ""
                texto = f"{nombre}\n({nodo_id})"
                if cap_text:
                    texto += f"\n{cap_text}"
                texto += f"\nVto baja: {viento_bc}\nVto alta: {viento_ac}"
                anotacion.set_text(texto)
                anotacion.set_visible(True)
                fig.canvas.draw_idle()
                return

        anotacion.set_visible(False)
        fig.canvas.draw_idle()

    def _on_submit(text):
        actualizar(None)

    def _on_text_change(text):
        actualizar(None)

    slider_min.on_changed(actualizar)
    texto_dia.on_submit(_on_submit)
    texto_dia.on_text_change(_on_text_change)
    fig.canvas.mpl_connect("motion_notify_event", _mostrar_info)
    # zoom/pan disponible via toolbar de matplotlib
    actualizar(0.0)
    plt.show()
