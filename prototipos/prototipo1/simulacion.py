from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import simpy

from prototipos.comun import (
    AeropuertoBase,
    InstantaneaVueloBase,
    PlanDeVueloBase,
    ProcesoVueloBase,
    RegistroVueloCompletadoBase,
    SimulacionBase,
)
from .configuracion import ALTURA_CRUCERO, FRACCION_ASCENSO, VELOCIDAD_CRUCERO


@dataclass
class PlanDeVuelo(PlanDeVueloBase):
    """Plan de vuelo especifico del prototipo 1."""


@dataclass
class InstantaneaVuelo(InstantaneaVueloBase):
    """Instantanea con posicion y progreso."""


@dataclass
class RegistroVueloCompletado(RegistroVueloCompletadoBase):
    """Registro persistente para analisis posterior."""


class Aeropuerto(AeropuertoBase):
    """Aeropuerto del prototipo 1."""


class ProcesoVuelo(ProcesoVueloBase):
    """Proceso SimPy que gestiona el ciclo de vida de un vuelo."""

    def __init__(
        self,
        entorno: simpy.Environment,
        simulacion: "SimulacionPrototipo1",
        plan: PlanDeVuelo,
        paso_tiempo: int,
    ) -> None:
        super().__init__(entorno, simulacion, plan, paso_tiempo)
        self.aeropuerto_origen = simulacion.aeropuertos[plan.id_origen]
        self.aeropuerto_destino = simulacion.aeropuertos[plan.id_destino]
        self.distancia = simulacion.obtener_distancia(plan.id_origen, plan.id_destino)
        self.instante_salida: Optional[float] = None
        self.velocidad_crucero = self._resolver_velocidad()
        self.instantaneas: List[InstantaneaVuelo] = []
        self.altura_crucero = ALTURA_CRUCERO
        self.fraccion_ascenso = FRACCION_ASCENSO

    def _resolver_velocidad(self) -> float:
        if self.plan.velocidad_crucero is None:
            self.plan.velocidad_crucero = VELOCIDAD_CRUCERO
        return self.plan.velocidad_crucero

    def _interpolar_posicion(self, progreso: float) -> tuple[float, float, float]:
        ox, oy, oz = self.aeropuerto_origen.posicion
        dx, dy, dz = self.aeropuerto_destino.posicion

        x = ox + progreso * (dx - ox)
        y = oy + progreso * (dy - oy)

        fraccion = self.fraccion_ascenso
        if fraccion <= 0.0 or fraccion >= 0.5:
            z = oz + progreso * (dz - oz)
        else:
            if progreso <= fraccion:
                fase = progreso / fraccion
                z = oz + self.altura_crucero * fase
            elif progreso >= 1.0 - fraccion:
                fase = (progreso - (1.0 - fraccion)) / fraccion
                z_crucero_destino = dz + self.altura_crucero
                z = z_crucero_destino + (dz - z_crucero_destino) * fase
            else:
                fase = (progreso - fraccion) / (1.0 - 2.0 * fraccion)
                z_origen_crucero = oz + self.altura_crucero
                z_destino_crucero = dz + self.altura_crucero
                z = z_origen_crucero + fase * (z_destino_crucero - z_origen_crucero)

        return (x, y, z)

    def _registrar_instantanea(self, progreso: float, llegada_estimacion: float) -> None:
        posicion = self._interpolar_posicion(progreso)
        instantanea = InstantaneaVuelo(
            minuto=self.entorno.now,
            posicion=posicion,
            progreso=progreso,
            llegada_estimacion=llegada_estimacion,
        )
        self.instantaneas.append(instantanea)

    def _calcular_llegada_estimacion(self, progreso: float) -> float:
        distancia_restante = self.distancia * max(0.0, 1.0 - progreso)
        if self.velocidad_crucero == 0:
            return self.entorno.now
        return self.entorno.now + (distancia_restante / self.velocidad_crucero)

    def ejecutar(self) -> Iterable[simpy.events.Event]:
        if self.plan.minuto_salida < self.entorno.now:
            raise RuntimeError(
                f"El vuelo {self.plan.id_vuelo} tiene una salida en el pasado."
            )

        espera_inicial = self.plan.minuto_salida - self.entorno.now
        if espera_inicial:
            yield self.entorno.timeout(espera_inicial)

        self.instante_salida = self.entorno.now
        self.aeropuerto_origen.liberar_plaza_salida()
        self.simulacion.vuelos_dinamicos[self.plan.id_vuelo] = self

        duracion_programada = self.plan.duracion_programada
        instante_llegada_programada = self.instante_salida + duracion_programada

        while self.entorno.now < instante_llegada_programada:
            transcurrido = self.entorno.now - self.instante_salida
            progreso = min(1.0, transcurrido / duracion_programada)
            llegada_estimacion = self._calcular_llegada_estimacion(progreso)
            self._registrar_instantanea(progreso, llegada_estimacion)
            paso = min(self.paso_tiempo, instante_llegada_programada - self.entorno.now)
            yield self.entorno.timeout(paso)

        self._registrar_instantanea(1.0, self.entorno.now)

        retraso = 0.0
        evento_aterrizaje = self.aeropuerto_destino.solicitar_aterrizaje(
            self.plan.id_vuelo
        )
        if evento_aterrizaje is not None:
            momento_entrada_cola = self.entorno.now
            while True:
                resultado = yield evento_aterrizaje | self.entorno.timeout(
                    self.paso_tiempo
                )
                if evento_aterrizaje in resultado:
                    break
                self._registrar_instantanea(1.0, self.entorno.now)
            retraso = self.entorno.now - momento_entrada_cola

        llegada_real = self.entorno.now

        registro = RegistroVueloCompletado(
            id_vuelo=self.plan.id_vuelo,
            id_origen=self.plan.id_origen,
            id_destino=self.plan.id_destino,
            minuto_salida=self.instante_salida,
            minuto_llegada_programada=self.plan.minuto_llegada_programada,
            minuto_llegada_real=llegada_real,
            retraso=retraso,
            instantaneas=self.instantaneas.copy(),
        )
        self.simulacion.registros_finalizados.append(registro)
        self.simulacion.vuelos_dinamicos.pop(self.plan.id_vuelo, None)


class SimulacionPrototipo1(SimulacionBase):
    """Simulador del Prototipo 1."""

    def crear_proceso_vuelo(self, plan: PlanDeVueloBase) -> ProcesoVueloBase:
        plan_especifico = (
            plan if isinstance(plan, PlanDeVuelo) else PlanDeVuelo(**plan.__dict__)
        )
        return ProcesoVuelo(
            self.entorno,
            self,
            plan_especifico,
            self.paso_tiempo,
        )

    @staticmethod
    def _minutos_a_hhmm(valor: float) -> str:
        total = int(round(valor))
        horas, minutos = divmod(total, 60)
        return f"{horas:02d}:{minutos:02d}"

    def registros_a_dataframe(self) -> pd.DataFrame:
        datos = []
        for registro in self.registros_finalizados:
            datos.append(
                {
                    "id_vuelo": registro.id_vuelo,
                    "aeropuerto_origen": registro.id_origen,
                    "aeropuerto_destino": registro.id_destino,
                    "hora_salida": self._minutos_a_hhmm(registro.minuto_salida),
                    "hora_llegada_programada": self._minutos_a_hhmm(
                        registro.minuto_llegada_programada
                    ),
                    "hora_llegada_real": self._minutos_a_hhmm(
                        registro.minuto_llegada_real
                    ),
                    "retraso_minutos": int(round(registro.retraso)),
                }
            )
        return pd.DataFrame(datos)

    def exportar_registros_csv(self, ruta: Path) -> Path:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        dataframe = self.registros_a_dataframe()
        dataframe.to_csv(ruta, index=False, encoding="utf-8")
        return ruta
