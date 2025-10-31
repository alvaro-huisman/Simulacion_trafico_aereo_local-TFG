"""Herramientas de visualizacion para la red del Prototipo 1."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.widgets import Slider

from .ejemplo import construir_simulacion
from .simulacion import SimulacionPrototipo1


def vuelos_activos_en(
    registros: Iterable, minuto: int
) -> List[Tuple[str, str, str]]:
    """Devuelve los vuelos activos en un minuto concreto."""
    activos: List[Tuple[str, str, str]] = []
    for registro in registros:
        if registro.minuto_salida <= minuto < registro.minuto_llegada_real:
            activos.append((registro.id_vuelo, registro.id_origen, registro.id_destino))
    return activos


class VisualizadorRed:
    """Gestiona la representacion grafica del grafo de aeropuertos."""

    def __init__(self, simulacion: SimulacionPrototipo1, minuto_inicial: int = 0) -> None:
        self.simulacion = simulacion
        self.minuto_actual = minuto_inicial
        self.posiciones: Dict[str, Tuple[float, float]] = {
            identificador: (aeropuerto.posicion[0], aeropuerto.posicion[1])
            for identificador, aeropuerto in simulacion.aeropuertos.items()
        }

        self.grafo = nx.Graph()
        for identificador, aeropuerto in simulacion.aeropuertos.items():
            self.grafo.add_node(
                identificador,
                pos=self.posiciones[identificador],
                capacidad=aeropuerto.capacidad_total,
            )

        for origen, destino, _ in simulacion.obtener_rutas_estaticas():
            self.grafo.add_edge(origen, destino)

        self.figura, self.ejes = plt.subplots(figsize=(9, 7))
        plt.subplots_adjust(bottom=0.22)
        self.ejes.set_axis_off()

        nx.draw_networkx_edges(
            self.grafo,
            self.posiciones,
            ax=self.ejes,
            width=0.8,
            alpha=0.25,
            edge_color="#7f7f7f",
        )

        tamanos = self._tamanos(minuto_inicial)
        colores = self._colores(minuto_inicial)
        self.nodos = nx.draw_networkx_nodes(
            self.grafo,
            self.posiciones,
            node_size=tamanos,
            node_color=colores,
            cmap="YlOrRd",
            vmin=0.0,
            vmax=1.0,
            ax=self.ejes,
        )
        self.etiquetas = nx.draw_networkx_labels(
            self.grafo,
            self.posiciones,
            labels=self._etiquetas(minuto_inicial),
            font_size=9,
            font_weight="bold",
            ax=self.ejes,
        )

        self.barra_color = self.figura.colorbar(self.nodos, ax=self.ejes, fraction=0.046, pad=0.04)
        self.barra_color.set_label("Ocupacion relativa")

        self.lineas_vuelos = LineCollection([], colors="#d62728", linewidths=2.5, alpha=0.85)
        self.ejes.add_collection(self.lineas_vuelos)

        self.slider_minuto = self._crear_slider(minuto_inicial)
        self._actualizar_lineas(minuto_inicial)
        self._actualizar_titulo(minuto_inicial)

    def _tamanos(self, minuto: int) -> np.ndarray:
        tamanos: List[float] = []
        for identificador in self.grafo.nodes:
            capacidad_total = self.simulacion.aeropuertos[identificador].capacidad_total
            tamanos.append(300.0 + capacidad_total * 80.0)
        return np.array(tamanos)

    def _colores(self, minuto: int) -> np.ndarray:
        colores: List[float] = []
        for identificador in self.grafo.nodes:
            aeropuerto = self.simulacion.aeropuertos[identificador]
            capacidad_disp = aeropuerto.capacidad_disponible_en(minuto)
            ocupacion_relativa = 1.0 - (capacidad_disp / aeropuerto.capacidad_total)
            colores.append(min(max(ocupacion_relativa, 0.0), 1.0))
        return np.array(colores)

    def _etiquetas(self, minuto: int) -> Dict[str, str]:
        etiquetas: Dict[str, str] = {}
        for identificador in self.grafo.nodes:
            aeropuerto = self.simulacion.aeropuertos[identificador]
            capacidad_disp = aeropuerto.capacidad_disponible_en(minuto)
            etiquetas[identificador] = f"{identificador}\n{capacidad_disp}/{aeropuerto.capacidad_total}"
        return etiquetas

    def _crear_slider(self, minuto_inicial: int) -> Slider:
        eje_slider = self.figura.add_axes([0.15, 0.06, 0.7, 0.04])
        slider = Slider(
            ax=eje_slider,
            label="Hora del dia",
            valmin=0.0,
            valmax=23.0,
            valinit=minuto_inicial / 60.0,
            valstep=1.0,
        )
        slider.on_changed(self._on_slider_change)
        return slider

    def _on_slider_change(self, valor: float) -> None:
        minuto = int(round(valor * 60))
        self.actualizar(minuto)

    def _actualizar_lineas(self, minuto: int) -> None:
        activos = vuelos_activos_en(self.simulacion.registros_finalizados, minuto)
        segmentos: List[List[Tuple[float, float]]] = []
        for _, origen, destino in activos:
            segmentos.append(
                [
                    self.posiciones[origen],
                    self.posiciones[destino],
                ]
            )
        self.lineas_vuelos.set_segments(segmentos)
        self.lineas_vuelos.set_visible(bool(segmentos))

    def _actualizar_titulo(self, minuto: int) -> None:
        horas, minutos = divmod(minuto, 60)
        activos = vuelos_activos_en(self.simulacion.registros_finalizados, minuto)
        self.ejes.set_title(
            f"Estado de la red - {horas:02d}:{minutos:02d} "
            f"({len(activos)} vuelos activos)",
            fontsize=14,
        )

    def actualizar(self, minuto: int) -> None:
        self.minuto_actual = minuto
        colores = self._colores(minuto)
        self.nodos.set_array(colores)
        etiquetas = self._etiquetas(minuto)
        for identificador, artista in self.etiquetas.items():
            artista.set_text(etiquetas[identificador])
        self._actualizar_lineas(minuto)
        self._actualizar_titulo(minuto)
        self.figura.canvas.draw_idle()

    def mostrar(self) -> None:
        plt.show()

    def guardar(self, ruta: Path) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.figura.savefig(ruta, dpi=200, bbox_inches="tight")


def construir_y_ejecutar_simulacion(ruta_planes: Path) -> SimulacionPrototipo1:
    simulacion = construir_simulacion(ruta_planes)
    simulacion.ejecutar(hasta=24 * 60)
    return simulacion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualiza el estado de la red de aeropuertos del Prototipo 1."
    )
    parser.add_argument(
        "--minuto",
        type=int,
        default=None,
        help="Minuto del dia (0-1439) que se mostrara inicialmente.",
    )
    parser.add_argument(
        "--hora",
        type=int,
        default=None,
        help="Hora del dia (0-23) que se mostrara inicialmente (prioridad sobre --minuto).",
    )
    parser.add_argument(
        "--planes",
        type=Path,
        default=Path(__file__).with_name("planes_aleatorios.csv"),
        help="Ruta al CSV de planes de vuelo (se regenerara si no existe).",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Ruta para guardar la figura generada.",
    )
    parser.add_argument(
        "--sin-interfaz",
        action="store_true",
        help="Guarda la figura y no abre la ventana interactiva.",
    )

    args = parser.parse_args()

    minuto_inicial = 0
    if args.hora is not None:
        if not (0 <= args.hora <= 23):
            raise ValueError("La hora debe estar entre 0 y 23.")
        minuto_inicial = args.hora * 60
    elif args.minuto is not None:
        if not (0 <= args.minuto <= 1439):
            raise ValueError("El minuto debe estar entre 0 y 1439.")
        minuto_inicial = args.minuto

    simulacion = construir_y_ejecutar_simulacion(args.planes)
    visualizador = VisualizadorRed(simulacion, minuto_inicial=minuto_inicial)

    if args.salida is not None:
        visualizador.guardar(args.salida)

    if not args.sin_interfaz:
        visualizador.mostrar()
    else:
        plt.close(visualizador.figura)


if __name__ == "__main__":
    main()
