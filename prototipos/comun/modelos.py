"""Clases base compartidas entre los diferentes prototipos."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import simpy


Vector3 = Tuple[float, float, float]


@dataclass
class PlanDeVueloBase:
    """Descripcion estatica de un vuelo programado."""

    id_vuelo: str
    id_origen: str
    id_destino: str
    minuto_salida: int
    minuto_llegada_programada: int
    velocidad_crucero: Optional[float] = None

    def __post_init__(self) -> None:
        if self.id_origen == self.id_destino:
            raise ValueError("El origen y destino del vuelo no pueden coincidir.")
        if self.minuto_salida >= self.minuto_llegada_programada:
            raise ValueError(
                "La hora de salida debe ser anterior a la llegada programada."
            )

    @property
    def duracion_programada(self) -> int:
        return self.minuto_llegada_programada - self.minuto_salida


@dataclass
class InstantaneaVueloBase:
    """Estado instantaneo de un vuelo activo."""

    minuto: float
    posicion: Vector3
    progreso: float
    llegada_estimacion: float


@dataclass
class RegistroVueloCompletadoBase:
    """Registro persistente de un vuelo completado."""

    id_vuelo: str
    id_origen: str
    id_destino: str
    minuto_salida: float
    minuto_llegada_programada: float
    minuto_llegada_real: float
    retraso: float
    instantaneas: List[InstantaneaVueloBase] = field(default_factory=list)


class AeropuertoBase:
    """Nodo del grafo que gestiona capacidad y cola de aterrizajes."""

    def __init__(
        self,
        entorno: simpy.Environment,
        id_aeropuerto: str,
        posicion: Vector3,
        capacidad: int,
    ) -> None:
        if capacidad <= 0:
            raise ValueError("La capacidad del aeropuerto debe ser positiva.")

        self.entorno = entorno
        self.id_aeropuerto = id_aeropuerto
        self.posicion = posicion
        self.capacidad_total = capacidad
        self.capacidad_disponible = capacidad
        self.planes_programados: List[PlanDeVueloBase] = []
        self._cola_aterrizajes: Deque[Tuple[str, simpy.events.Event]] = deque()
        self.historial_capacidad: List[Tuple[float, int]] = []
        self._registrar_capacidad()

    def registrar_plan_vuelo(self, plan: PlanDeVueloBase) -> None:
        self.planes_programados.append(plan)

    def reservar_salida(self, id_vuelo: str) -> None:
        if self.capacidad_disponible <= 0:
            raise RuntimeError(
                f"Capacidad insuficiente en {self.id_aeropuerto} "
                f"para programar la salida {id_vuelo}."
            )
        self.capacidad_disponible -= 1
        self._registrar_capacidad()

    def liberar_plaza_salida(self) -> None:
        if self.capacidad_disponible >= self.capacidad_total:
            return
        self.capacidad_disponible += 1
        self._atender_cola_aterrizajes()
        self._registrar_capacidad()

    def solicitar_aterrizaje(self, id_vuelo: str) -> Optional[simpy.events.Event]:
        if self.capacidad_disponible > 0:
            self.capacidad_disponible -= 1
            self._registrar_capacidad()
            return None

        evento_aterrizaje = self.entorno.event()
        self._cola_aterrizajes.append((id_vuelo, evento_aterrizaje))
        return evento_aterrizaje

    def _atender_cola_aterrizajes(self) -> None:
        while self._cola_aterrizajes and self.capacidad_disponible > 0:
            id_vuelo, evento = self._cola_aterrizajes.popleft()
            self.capacidad_disponible -= 1
            self._registrar_capacidad()
            evento.succeed()

    def __repr__(self) -> str:
        return (
            f"AeropuertoBase(id={self.id_aeropuerto!r}, posicion={self.posicion!r}, "
            f"capacidad_total={self.capacidad_total}, "
            f"capacidad_disponible={self.capacidad_disponible})"
        )

    def _registrar_capacidad(self) -> None:
        self.historial_capacidad.append((self.entorno.now, self.capacidad_disponible))

    def capacidad_disponible_en(self, minuto: float) -> int:
        if not self.historial_capacidad:
            return self.capacidad_disponible
        capacidad = self.historial_capacidad[0][1]
        for instante, valor in self.historial_capacidad:
            if instante > minuto:
                break
            capacidad = valor
        return capacidad


class ProcesoVueloBase:
    """Proceso SimPy generico para un vuelo; debe sobreescribirse en prototipos."""

    def __init__(
        self,
        entorno: simpy.Environment,
        simulacion: "SimulacionBase",
        plan: PlanDeVueloBase,
        paso_tiempo: int,
    ) -> None:
        self.entorno = entorno
        self.simulacion = simulacion
        self.plan = plan
        self.paso_tiempo = paso_tiempo

    def ejecutar(self) -> Iterable[simpy.events.Event]:
        raise NotImplementedError


class SimulacionBase:
    """Simulacion generica basada en SimPy."""

    def __init__(self, paso_tiempo: int = 1) -> None:
        if paso_tiempo <= 0:
            raise ValueError("El paso de simulacion debe ser positivo.")

        self.entorno = simpy.Environment()
        self.paso_tiempo = paso_tiempo
        self.aeropuertos: Dict[str, AeropuertoBase] = {}
        self._distancias_cache: Dict[Tuple[str, str], float] = {}
        self.vuelos_dinamicos: Dict[str, ProcesoVueloBase] = {}
        self.registros_finalizados: List[RegistroVueloCompletadoBase] = []

    def agregar_aeropuerto(
        self,
        id_aeropuerto: str,
        posicion: Vector3,
        capacidad: int,
        clase_aeropuerto: type[AeropuertoBase] = AeropuertoBase,
    ) -> AeropuertoBase:
        if id_aeropuerto in self.aeropuertos:
            raise ValueError(f"El aeropuerto {id_aeropuerto} ya esta registrado.")

        aeropuerto = clase_aeropuerto(self.entorno, id_aeropuerto, posicion, capacidad)
        self.aeropuertos[id_aeropuerto] = aeropuerto
        self._distancias_cache.clear()
        return aeropuerto

    def agregar_aeropuertos(
        self,
        definiciones: Iterable[Tuple[str, Vector3, int]],
        clase_aeropuerto: type[AeropuertoBase] = AeropuertoBase,
    ) -> None:
        for identificador, posicion, capacidad in definiciones:
            self.agregar_aeropuerto(
                identificador, posicion, capacidad, clase_aeropuerto=clase_aeropuerto
            )

    def registrar_plan(self, plan: PlanDeVueloBase) -> None:
        if plan.id_origen not in self.aeropuertos:
            raise ValueError(f"Aeropuerto de origen desconocido: {plan.id_origen}")
        if plan.id_destino not in self.aeropuertos:
            raise ValueError(f"Aeropuerto de destino desconocido: {plan.id_destino}")

        aeropuerto_origen = self.aeropuertos[plan.id_origen]
        aeropuerto_origen.registrar_plan_vuelo(plan)

        proceso = self.crear_proceso_vuelo(plan)
        self.entorno.process(proceso.ejecutar())

    def registrar_planes(self, planes: Iterable[PlanDeVueloBase]) -> None:
        for plan in planes:
            self.registrar_plan(plan)

    def crear_proceso_vuelo(self, plan: PlanDeVueloBase) -> ProcesoVueloBase:
        raise NotImplementedError

    def obtener_distancia(self, origen: str, destino: str) -> float:
        llave = tuple(sorted((origen, destino)))
        if llave in self._distancias_cache:
            return self._distancias_cache[llave]

        try:
            aeropuerto_origen = self.aeropuertos[origen]
            aeropuerto_destino = self.aeropuertos[destino]
        except KeyError as exc:
            raise ValueError("Aeropuerto desconocido al calcular distancia.") from exc

        distancia = math.dist(aeropuerto_origen.posicion, aeropuerto_destino.posicion)
        self._distancias_cache[llave] = distancia
        return distancia

    def ejecutar(self, hasta: Optional[int] = None) -> None:
        self.entorno.run(until=hasta)

    def obtener_rutas_estaticas(self) -> List[Tuple[str, str, float]]:
        rutas: List[Tuple[str, str, float]] = []
        identificadores = sorted(self.aeropuertos.keys())
        for indice, origen in enumerate(identificadores):
            for destino in identificadores[indice + 1 :]:
                rutas.append((origen, destino, self.obtener_distancia(origen, destino)))
        return rutas
