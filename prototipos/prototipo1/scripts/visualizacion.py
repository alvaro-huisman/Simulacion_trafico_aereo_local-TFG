"""Herramientas de visualizacion para la red del Prototipo 1."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.widgets import Slider

try:  # pragma: no cover - soporte opcional de GUI
    import tkinter as tk
    from tkinter import ttk

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:  # pragma: no cover
    tk = None  # type: ignore
    ttk = None  # type: ignore
    FigureCanvasTkAgg = None  # type: ignore

from ..core.configuracion import ALTURA_CRUCERO, FRACCION_ASCENSO, VELOCIDAD_CRUCERO
from ..core.configuracion_app import AppConfig, DEFAULT_CONFIG_PATH
from ..core.escenarios import construir_simulacion
from ..core.simulacion import RegistroVueloCompletado, SimulacionPrototipo1


def vuelos_activos_en(
    registros: Iterable[RegistroVueloCompletado], minuto: int
) -> List[RegistroVueloCompletado]:
    """Devuelve los vuelos activos en un minuto concreto."""
    return [
        registro
        for registro in registros
        if registro.minuto_salida <= minuto < registro.minuto_llegada_real
    ]


class VisualizadorRed:
    """Gestiona la representacion grafica del grafo de aeropuertos."""

    def __init__(
        self,
        simulacion: SimulacionPrototipo1,
        *,
        duracion_minutos: int,
        minuto_inicial: int = 0,
    ) -> None:
        self.simulacion = simulacion
        self.minuto_actual = minuto_inicial
        self.duracion_minutos = max(duracion_minutos, 1)
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
        plt.subplots_adjust(bottom=0.26, left=0.06, right=0.88, top=0.9)
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
        self.barra_color.set_label("Ocupacion relativa (0=vacio, 1=lleno)")

        self.lineas_vuelos = LineCollection([], colors="#d62728", linewidths=2.5, alpha=0.85)
        self.ejes.add_collection(self.lineas_vuelos)

        self.slider_minuto = self._crear_slider(minuto_inicial)
        self.slider_minuto.valtext.set_text(self._formato_hora(minuto_inicial))

        self.puntos_vuelos = self.ejes.scatter(
            [],
            [],
            s=60,
            c="#1f77b4",
            edgecolors="white",
            linewidths=0.8,
            zorder=4,
        )

        self._actualizar_lineas(minuto_inicial)
        self._actualizar_puntos(minuto_inicial)
        self._actualizar_titulo(minuto_inicial)
        self._crear_leyenda()

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
        eje_slider = self.figura.add_axes([0.12, 0.06, 0.73, 0.045])
        slider = Slider(
            ax=eje_slider,
            label="Instante (hh:mm)",
            valmin=0.0,
            valmax=float(max(self.duracion_minutos - 1, 0)),
            valinit=float(minuto_inicial),
            valstep=1.0,
        )
        slider.on_changed(self._on_slider_change)
        return slider

    def _on_slider_change(self, valor: float) -> None:
        minuto = int(round(valor))
        self.actualizar(minuto)
        self.slider_minuto.valtext.set_text(self._formato_hora(minuto))

    @staticmethod
    def _formato_hora(minuto: int) -> str:
        horas, minutos = divmod(minuto, 60)
        return f"{horas:02d}:{minutos:02d}"

    def _actualizar_lineas(self, minuto: int) -> None:
        activos = vuelos_activos_en(self.simulacion.registros_finalizados, minuto)
        segmentos: List[List[Tuple[float, float]]] = []
        for registro in activos:
            origen = registro.id_origen
            destino = registro.id_destino
            segmentos.append(
                [
                    self.posiciones[origen],
                    self.posiciones[destino],
                ]
            )
        self.lineas_vuelos.set_segments(segmentos)
        self.lineas_vuelos.set_visible(bool(segmentos))

    def _posicion_vuelo(self, registro: RegistroVueloCompletado, minuto: int) -> Optional[Tuple[float, float]]:
        ultima = None
        for instantanea in registro.instantaneas:
            if instantanea.minuto > minuto:
                break
            ultima = instantanea
        if ultima is None:
            return None
        x, y, _ = ultima.posicion
        return (x, y)

    def _actualizar_puntos(self, minuto: int) -> None:
        activos = vuelos_activos_en(self.simulacion.registros_finalizados, minuto)
        posiciones: List[Tuple[float, float]] = []
        for registro in activos:
            posicion = self._posicion_vuelo(registro, minuto)
            if posicion is not None:
                posiciones.append(posicion)

        if posiciones:
            self.puntos_vuelos.set_offsets(np.array(posiciones))
            self.puntos_vuelos.set_visible(True)
        else:
            self.puntos_vuelos.set_offsets(np.empty((0, 2)))
            self.puntos_vuelos.set_visible(False)

        self.puntos_vuelos.set_sizes(np.full(len(posiciones), 70.0) if posiciones else [])

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
        self._actualizar_puntos(minuto)
        self._actualizar_titulo(minuto)
        self.figura.canvas.draw_idle()

    def mostrar(self) -> None:
        plt.show()

    def _crear_leyenda(self) -> None:
        manejadores = [
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="",
                markerfacecolor="#fdae6b",
                markeredgecolor="#444444",
                markersize=10,
                label="Aeropuerto (color segun ocupacion)",
            ),
            Line2D(
                [0],
                [0],
                color="#d62728",
                linewidth=2.5,
                label="Vuelo activo",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="",
                markerfacecolor="#1f77b4",
                markeredgecolor="white",
                markersize=8,
                label="Posicion actual del avion",
            ),
        ]

        leyenda = self.figura.legend(
            handles=manejadores,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.18),
            frameon=True,
            ncol=3,
            title="Referencias",
        )
        leyenda.get_frame().set_alpha(0.9)


def construir_y_ejecutar_simulacion(
    ruta_planes: Path,
    regenerar: bool = True,
    semilla_planes: int = 1234,
    numero_vuelos: int = 60,
    semilla_aeropuertos: int = 2025,
    guardar_eventos: bool = True,
    paso_minutos: int = 1,
    duracion_minutos: int = 24 * 60,
    velocidad_crucero: float = VELOCIDAD_CRUCERO,
    altura_crucero: float = ALTURA_CRUCERO,
    fraccion_ascenso: float = FRACCION_ASCENSO,
) -> SimulacionPrototipo1:
    simulacion = construir_simulacion(
        ruta_planes,
        regenerar=regenerar,
        semilla_planes=semilla_planes,
        numero_vuelos=numero_vuelos,
        semilla_aeropuertos=semilla_aeropuertos,
        guardar_eventos=guardar_eventos,
        paso_minutos=paso_minutos,
        duracion_minutos=duracion_minutos,
        velocidad_crucero=velocidad_crucero,
        altura_crucero=altura_crucero,
        fraccion_ascenso=fraccion_ascenso,
    )
    simulacion.ejecutar(hasta=duracion_minutos)
    return simulacion


def mostrar_visualizador_con_menu(
    escenarios: Sequence[int],
    generador_simulacion: Callable[[int], SimulacionPrototipo1],
    *,
    minuto_inicial: int,
    duracion_minutos: int,
    titulo: str = "Visualizacion Prototipo 1",
) -> None:
    """Muestra una interfaz con menu desplegable para escoger escenarios."""
    if tk is None or ttk is None or FigureCanvasTkAgg is None:
        raise RuntimeError(
            "Tkinter no esta disponible en este entorno; instala Tk o usa el visor CLI."
        )

    escenarios_unicos = sorted(set(escenarios))
    if not escenarios_unicos:
        raise ValueError("No hay escenarios disponibles para visualizar.")

    minuto_inicial = max(0, min(minuto_inicial, max(duracion_minutos - 1, 0)))
    escenario_actual = escenarios_unicos[0]
    cache: Dict[int, SimulacionPrototipo1] = {}

    def obtener_simulacion(numero: int) -> SimulacionPrototipo1:
        if numero not in cache:
            cache[numero] = generador_simulacion(numero)
        return cache[numero]

    root = tk.Tk()
    root.title(titulo)

    marco_controles = ttk.Frame(root, padding=(12, 8))
    marco_controles.pack(side=tk.TOP, fill=tk.X)

    ttk.Label(marco_controles, text="Escenario:").pack(side=tk.LEFT)

    valores_combo = [f"{valor:03d}" for valor in escenarios_unicos]
    combo = ttk.Combobox(
        marco_controles,
        values=valores_combo,
        state="readonly",
        width=8,
    )
    combo.pack(side=tk.LEFT, padx=(6, 12))
    combo.set(f"{escenario_actual:03d}")

    etiqueta_estado = ttk.Label(marco_controles, text="Listo")
    etiqueta_estado.pack(side=tk.LEFT, expand=True, anchor="w")

    contenedor_figura = ttk.Frame(root)
    contenedor_figura.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    canvas: Optional[FigureCanvasTkAgg] = None
    visualizador_actual: Optional[VisualizadorRed] = None

    def cargar_escenario(numero: int) -> None:
        nonlocal canvas, visualizador_actual, escenario_actual
        etiqueta_estado.config(text=f"Cargando escenario {numero:03d}...")
        root.update_idletasks()
        simulacion = obtener_simulacion(numero)
        nuevo_visualizador = VisualizadorRed(
            simulacion,
            duracion_minutos=duracion_minutos,
            minuto_inicial=minuto_inicial,
        )
        if canvas is not None:
            canvas.get_tk_widget().destroy()
            if visualizador_actual is not None:
                plt.close(visualizador_actual.figura)
        visualizador_actual = nuevo_visualizador
        canvas = FigureCanvasTkAgg(nuevo_visualizador.figura, master=contenedor_figura)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        escenario_actual = numero
        etiqueta_estado.config(text=f"Escenario activo: {numero:03d}")

    def _seleccion_combo(evento: Optional[tk.Event] = None) -> None:
        valor = combo.get()
        try:
            seleccionado = int(valor)
        except ValueError:
            etiqueta_estado.config(text="Seleccion no valida")
            return
        cargar_escenario(seleccionado)

    combo.bind("<<ComboboxSelected>>", _seleccion_combo)
    cargar_escenario(escenario_actual)
    root.mainloop()

    if visualizador_actual is not None:
        plt.close(visualizador_actual.figura)


def _solicitar_escenario(
    minimo: int,
    maximo: int,
    mensaje: str = "Selecciona el numero de escenario",
) -> int:
    while True:
        try:
            entrada = input(f"{mensaje} ({minimo}-{maximo}): ").strip()
        except EOFError:
            return minimo
        if not entrada:
            continue
        try:
            valor = int(entrada)
        except ValueError:
            print("Introduce un numero entero valido.")
            continue
        if minimo <= valor <= maximo:
            return valor
        print(f"El escenario debe estar entre {minimo} y {maximo}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualiza el estado de la red de aeropuertos del Prototipo 1."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuracion (por defecto configuracion_inicial.txt).",
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
        default=None,
        help="Ruta al CSV de planes de vuelo a visualizar.",
    )
    parser.add_argument(
        "--escenario",
        type=int,
        default=None,
        help="Numero de escenario (1-50) dentro del directorio de escenarios.",
    )
    parser.add_argument(
        "--escenarios-dir",
        type=Path,
        default=None,
        help="Directorio donde se almacenan los escenarios numerados.",
    )

    args = parser.parse_args()
    config = AppConfig.cargar(args.config)

    minuto_defecto = config.visualizacion_minuto
    semilla_base = config.semilla_base
    semilla_aeropuertos = config.semilla_aeropuertos
    numero_vuelos = config.escenarios_numero_vuelos
    directorio_escenarios = (
        args.escenarios_dir
        if args.escenarios_dir is not None
        else config.escenarios_directorio
    )
    max_escenarios = config.visualizacion_max_escenarios

    minuto_inicial = minuto_defecto
    if args.hora is not None:
        if not (0 <= args.hora <= 23):
            raise ValueError("La hora debe estar entre 0 y 23.")
        minuto_inicial = args.hora * 60
    elif args.minuto is not None:
        if not (0 <= args.minuto <= 1439):
            raise ValueError("El minuto debe estar entre 0 y 1439.")
        minuto_inicial = args.minuto
    max_minuto_permitido = max(config.duracion_minutos - 1, 0)
    if minuto_inicial > max_minuto_permitido:
        minuto_inicial = max_minuto_permitido

    semilla_planes = semilla_base
    regenerar = True
    ruta_planes: Path

    if args.planes is not None:
        ruta_planes = args.planes
        regenerar = not ruta_planes.exists()
        identificador = ruta_planes.stem
    else:
        numero = args.escenario
        if numero is None:
            numero = _solicitar_escenario(1, max_escenarios)
        if not (1 <= numero <= max_escenarios):
            raise ValueError(f"El escenario debe estar entre 1 y {max_escenarios}.")

        directorio_escenarios.mkdir(parents=True, exist_ok=True)
        ruta_planes = directorio_escenarios / f"planes_aleatorios_{numero:03d}.csv"
        regenerar = not ruta_planes.exists()
        semilla_planes = semilla_base + numero
        identificador = f"escenario {numero:03d}"

    simulacion = construir_y_ejecutar_simulacion(
        ruta_planes,
        regenerar=regenerar,
        semilla_planes=semilla_planes,
        numero_vuelos=numero_vuelos,
        semilla_aeropuertos=semilla_aeropuertos,
        guardar_eventos=config.guardar_eventos,
        paso_minutos=config.paso_minutos,
        duracion_minutos=config.duracion_minutos,
        velocidad_crucero=config.velocidad_crucero,
        altura_crucero=config.altura_crucero,
        fraccion_ascenso=config.fraccion_ascenso,
    )
    print(f"Simulacion visualizada: {identificador}")
    visualizador = VisualizadorRed(
        simulacion,
        duracion_minutos=config.duracion_minutos,
        minuto_inicial=minuto_inicial,
    )
    visualizador.mostrar()


if __name__ == "__main__":
    main()
