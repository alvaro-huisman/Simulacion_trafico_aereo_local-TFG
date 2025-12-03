"""Nucleo de simulacion del Prototipo 2 (SimPy)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd
import simpy
from prototipos.comun.modelos import PlanDeVueloBase, SimulacionBase


@dataclass(frozen=True)
class TipoAeronave:
    """Describe parametros de velocidad y consumo para un tipo de avion."""

    nombre: str
    vel_asc_kmh: float
    vel_cru_kmh: float
    vel_des_kmh: float
    nivel_crucero_min_ft: int  # en pies reales
    nivel_crucero_max_ft: int
    consumo_asc_l_h: float
    consumo_cru_l_h: float
    consumo_des_l_h: float


TIPO_CORTO_RADIO = TipoAeronave(
    nombre="corto_radio",
    vel_asc_kmh=500.0,
    vel_cru_kmh=780.0,
    vel_des_kmh=520.0,
    nivel_crucero_min_ft=28000,
    nivel_crucero_max_ft=36000,
    consumo_asc_l_h=3800.0,
    consumo_cru_l_h=3000.0,
    consumo_des_l_h=2100.0,
)

TIPO_MEDIO_RADIO = TipoAeronave(
    nombre="medio_radio",
    vel_asc_kmh=540.0,
    vel_cru_kmh=830.0,
    vel_des_kmh=560.0,
    nivel_crucero_min_ft=32000,
    nivel_crucero_max_ft=40000,
    consumo_asc_l_h=4200.0,
    consumo_cru_l_h=3400.0,
    consumo_des_l_h=2400.0,
)


@dataclass(frozen=True)
class ConfigSimulacion:
    paso_minutos: int = 1
    T_umbral_espera: int = 45
    seed: Optional[int] = 1234
    umbral_distancia_tipo_avion: float = 700.0  # km
    separar_minutos: int = 3
    factor_viento_a_favor: float = 1.05
    factor_viento_en_contra: float = 0.9
    factor_viento_neutro: float = 1.0
    fuel_factor_a_favor: float = 0.95
    fuel_factor_en_contra: float = 1.05
    fuel_factor_neutro: float = 1.0
    tiempo_embarque_min: int = 0   # sin modelar embarque
    tiempo_turnaround_min: int = 0  # sin modelar turnaround
    ocupacion_inicial_min_fraccion: float = 0.05
    ocupacion_inicial_max_fraccion: float = 0.35
    exterior_top_n: int = 15
    exterior_ruido_min: int = 1
    exterior_ruido_max: int = 3
    exterior_intervalo_min: int = 90
    exterior_intervalo_max: int = 240
    exterior_estancia_min: int = 15
    exterior_estancia_max: int = 45
    tmin_fase_asc_des_min: float = 5.0
    tmin_fase_crucero_min: float = 5.0


class SimulacionPrototipo2(SimulacionBase):
    """Gestiona la simulacion SDE del Prototipo 2."""

    def __init__(
        self,
        aeropuertos_df: pd.DataFrame,
        grafo: nx.Graph,
        plan_vuelos: pd.DataFrame,
        config: Optional[ConfigSimulacion] = None,
        ocupacion_inicial: Optional[Dict[str, int]] = None,
    ) -> None:
        config = config or ConfigSimulacion()
        super().__init__(paso_tiempo=config.paso_minutos)
        # Alias para mantener compatibilidad con el resto del codigo
        self.env = self.entorno
        self.aeropuertos_df = aeropuertos_df
        self.grafo = grafo
        self.plan_vuelos = plan_vuelos
        self.config = config
        self._ocupacion_inicial_override = ocupacion_inicial or {}

        self.rng = random.Random(self.config.seed)
        try:
            self._horizonte_min = float(self.plan_vuelos["minuto_llegada_programada"].max()) + 60.0
        except Exception:
            self._horizonte_min = 24 * 60.0
        self._recursos = self._crear_recursos_aeropuertos()
        self._separacion_ruta: Dict[Tuple[str, str], float] = {}
        self._ultimo_evento_pista: Dict[str, float] = {}
        self._registros: List[Dict[str, object]] = []
        self._vientos_cache: Dict[Tuple[str, str], str] = {}
        self._trafico_por_aer = self._calcular_trafico_por_aeropuerto()
        self._ocupacion: Dict[str, int] = {aid: 0 for aid in self._recursos.keys()}
        self._eventos: List[Dict[str, object]] = []
        self._inicializar_ocupacion()
        self._programar_ruido_exterior()

    def _crear_recursos_aeropuertos(self) -> Dict[str, simpy.Resource]:
        recursos: Dict[str, simpy.Resource] = {}
        for fila in self.aeropuertos_df.itertuples(index=False):
            capacidad = int(getattr(fila, "capacidad", 1)) if hasattr(fila, "capacidad") else 1
            recursos[getattr(fila, "id")] = simpy.Resource(self.env, capacity=max(1, capacidad))
        return recursos

    def _calcular_trafico_por_aeropuerto(self) -> Dict[str, float]:
        """Suma pesos de pasajeros por nodo para priorizar hubs."""
        traf: Dict[str, float] = {n: 0.0 for n in self.grafo.nodes}
        for u, v, datos in self.grafo.edges(data=True):
            peso = float(datos.get("pasajeros_anuales", datos.get("w_ij", 0.0)))
            traf[u] = traf.get(u, 0.0) + peso
            traf[v] = traf.get(v, 0.0) + peso
        # fallback si todo es 0
        if all(v == 0.0 for v in traf.values()):
            for n in traf:
                traf[n] = float(self.grafo.degree[n])
        return traf

    def _inicializar_ocupacion(self) -> None:
        """Asigna una ocupacion inicial aleatoria proporcional al trafico."""
        total_traf = sum(self._trafico_por_aer.values()) or 1.0
        for aid, recurso in self._recursos.items():
            if aid in self._ocupacion_inicial_override:
                ocup = int(self._ocupacion_inicial_override[aid])
            else:
                peso = self._trafico_por_aer.get(aid, 0.0) / total_traf
                base_frac = self.rng.uniform(
                    self.config.ocupacion_inicial_min_fraccion, self.config.ocupacion_inicial_max_fraccion
                )
                # potenciar hubs
                frac = min(1.0, base_frac + peso * 0.5)
                ocup = int(round(frac * recurso.capacity))
            ocup = max(0, min(ocup, recurso.capacity))
            self._ocupacion[aid] = ocup
            if ocup > 0:
                self._eventos.append(
                    {"minuto": 0.0, "aeropuerto": aid, "evento": "ocupacion_inicial", "ocupacion": ocup, "capacidad": recurso.capacity}
                )

    def _programar_ruido_exterior(self) -> None:
        """Crea procesos de ruido externo en los hubs top_n para simular carga de vuelos internacionales."""
        top = sorted(self._trafico_por_aer.items(), key=lambda x: x[1], reverse=True)
        top_ids = [aid for aid, _ in top[: max(1, self.config.exterior_top_n)]]
        for aid in top_ids:
            self.env.process(self._proceso_ruido_exterior(aid))

    def _proceso_ruido_exterior(self, aer_id: str):
        """Simula llegadas/salidas de vuelos exteriores que ocupan slots durante un rato."""
        while True:
            intervalo = self.rng.randint(self.config.exterior_intervalo_min, self.config.exterior_intervalo_max)
            yield self.env.timeout(intervalo)
            if self.env.now >= self._horizonte_min:
                break
            recurso = self._recursos.get(aer_id)
            if recurso is None:
                continue
            extra = self.rng.randint(self.config.exterior_ruido_min, self.config.exterior_ruido_max)
            dur = self.rng.randint(self.config.exterior_estancia_min, self.config.exterior_estancia_max)
            for _ in range(extra):
                self._log_evento(aer_id, "ext_llegada", delta=1)
            if dur > 0:
                yield self.env.timeout(dur)
            for _ in range(extra):
                self._log_evento(aer_id, "ext_salida", delta=-1)

    def _datos_aeropuerto(self, aer_id: str) -> Dict[str, object]:
        aer_id_scalar = self._aer_id_scalar(aer_id)
        ids_str = self.aeropuertos_df["id"].astype(str)
        mask = ids_str.eq(aer_id_scalar)
        # En caso de que mask no sea una Series booleana, forzamos a np.bool_
        try:
            import numpy as np
            mask_arr = np.asarray(mask, dtype=bool)
        except Exception:
            mask_arr = mask
        fila = self.aeropuertos_df.loc[mask_arr]
        if fila.empty:
            raise ValueError(f"Aeropuerto no encontrado: {aer_id_scalar}")
        return fila.iloc[0].to_dict()

    def _aer_id_scalar(self, aer_id: object) -> str:
        """Normaliza un id de aeropuerto a un escalar string."""
        try:
            import numpy as np
            arr = np.asarray(aer_id).ravel()
            if arr.size > 0:
                return str(arr[0])
        except Exception:
            pass
        if isinstance(aer_id, (list, tuple)):
            return str(aer_id[0]) if aer_id else ""
        return str(aer_id)

    def _log_evento(self, aer_id: str, evento: str, delta: int = 0) -> None:
        """Actualiza ocupacion y guarda evento para visualizacion posterior."""
        if aer_id not in self._ocupacion:
            return
        self._ocupacion[aer_id] = max(0, self._ocupacion.get(aer_id, 0) + delta)
        self._eventos.append(
            {
                "minuto": self.env.now,
                "aeropuerto": aer_id,
                "evento": evento,
                "ocupacion": self._ocupacion[aer_id],
                "capacidad": self._recursos[aer_id].capacity,
            }
        )

    def _resolver_viento(self, aer_id: str, fase: str) -> tuple[str, float]:
        aer_id = self._aer_id_scalar(aer_id)
        datos = self._datos_aeropuerto(aer_id)
        if fase == "crucero":
            etiqueta = datos.get("viento_alta_cota", None)
        else:
            etiqueta = datos.get("viento_baja_cota", None)
        if etiqueta in (None, "", "neutro"):
            clave = (aer_id, fase)
            if clave not in self._vientos_cache:
                etiqueta = self.rng.choices(
                    ["a_favor", "en_contra", "neutro"], weights=[0.3, 0.3, 0.4], k=1
                )[0]
                self._vientos_cache[clave] = etiqueta
            else:
                etiqueta = self._vientos_cache[clave]
        if etiqueta == "a_favor":
            return etiqueta, self.config.factor_viento_a_favor
        if etiqueta == "en_contra":
            return etiqueta, self.config.factor_viento_en_contra
        return etiqueta or "neutro", self.config.factor_viento_neutro

    def _seleccionar_tipo_aeronave(self, dist_km: float) -> TipoAeronave:
        if dist_km <= self.config.umbral_distancia_tipo_avion:
            return TIPO_CORTO_RADIO
        return TIPO_MEDIO_RADIO

    def _esperar_separacion_ruta(self, origen: str, destino: str) -> None:
        clave = tuple(sorted((origen, destino)))
        ultimo = self._separacion_ruta.get(clave, -1e9)
        min_sep = self.config.separar_minutos
        if self.env.now < ultimo + min_sep:
            espera = (ultimo + min_sep) - self.env.now
            yield self.env.timeout(espera)
        self._separacion_ruta[clave] = self.env.now

    def _esperar_pista(self, aer_id: str) -> None:
        ultimo = self._ultimo_evento_pista.get(aer_id, -1e9)
        min_sep = self.config.separar_minutos
        if self.env.now < ultimo + min_sep:
            yield self.env.timeout((ultimo + min_sep) - self.env.now)
        self._ultimo_evento_pista[aer_id] = self.env.now

    def _tiempo_fase(self, distancia_km: float, velocidad_kmh: float) -> float:
        if velocidad_kmh <= 0:
            return 0.0
        return (distancia_km / velocidad_kmh) * 60.0

    def _combustible(self, duracion_min: float, consumo_l_h: float, fuel_factor: float = 1.0) -> float:
        return (duracion_min / 60.0) * consumo_l_h * fuel_factor

    def _redirigir_si_conviene(
        self,
        destino_original: str,
        tiempo_espera: float,
        origen_actual: str,
        dist_plan_km: float,
    ) -> Tuple[str, float, bool]:
        """Evalua redireccion: devuelve destino_final, retraso_extra, redirigido."""
        mejor_dest = destino_original
        mejor_retraso = tiempo_espera
        redirigido = False

        candidato_optimo = None
        mejor_dist_al_destino = float("inf")

        for candidato in self.grafo.nodes:
            if candidato == destino_original or candidato == origen_actual:
                continue
            recurso_alt = self._recursos.get(candidato)
            if recurso_alt is None:
                continue
            # debe tener capacidad libre (simple aproximacion)
            if recurso_alt.count >= recurso_alt.capacity:
                continue
            try:
                dist_dest = nx.shortest_path_length(
                    self.grafo,
                    destino_original,
                    candidato,
                    weight="dist_km",
                )
            except nx.NetworkXNoPath:
                continue
            if dist_dest < mejor_dist_al_destino:
                mejor_dist_al_destino = dist_dest
                candidato_optimo = candidato

        if candidato_optimo is not None:
            # estimar retraso hasta el alternativo desde origen actual
            try:
                dist_total = nx.shortest_path_length(
                    self.grafo, origen_actual, candidato_optimo, weight="dist_km"
                )
                tiempo_extra = self._tiempo_fase(dist_total, TIPO_MEDIO_RADIO.vel_cru_kmh)
            except nx.NetworkXNoPath:
                tiempo_extra = tiempo_espera + 1  # peor que esperar
            # Chequeo simple de alcance: no desviar a algo mucho mas lejos que el plan original
            if dist_total > dist_plan_km * 1.3:
                tiempo_extra = tiempo_espera + 1
            if tiempo_extra < mejor_retraso:
                mejor_dest = candidato_optimo
                mejor_retraso = tiempo_extra
                redirigido = True

        return mejor_dest, mejor_retraso, redirigido

    def _proceso_vuelo(self, vuelo: Dict[str, object]) -> simpy.events.Event:
        origen = self._aer_id_scalar(vuelo["origen"])
        destino = self._aer_id_scalar(vuelo["destino"])
        salida_prog = float(vuelo["minuto_salida"])
        dist_km = float(vuelo.get("distancia_km", 0.0))
        es_exterior = bool(vuelo.get("es_exterior", False)) or destino.upper() == "EXTERIOR"

        # 1) Espera hasta la hora de salida
        if self.env.now < salida_prog:
            yield self.env.timeout(salida_prog - self.env.now)

        # 2) Ocupa capacidad en el origen (taxis / gate) y libera al despegar
        recurso_origen = self._recursos[origen]
        with recurso_origen.request() as req:
            yield req
            self._log_evento(origen, "ocupacion_origen", delta=1)
            # Separacion pista en origen
            yield from self._esperar_pista(origen)
            if self.config.tiempo_embarque_min > 0:
                yield self.env.timeout(self.config.tiempo_embarque_min)
            self._log_evento(origen, "despegue", delta=-1)
        # liberacion implicita al salir del with

        # 3) Seleccion de aeronave
        tipo = self._seleccionar_tipo_aeronave(dist_km)

        # 4) Fases de vuelo
        combustible_consumido_l = 0.0
        retraso_por_redir = 0.0
        redirigido = False
        destino_final = destino

        # Ascenso
        viento_label, factor_viento = self._resolver_viento(origen, fase="ascenso")
        vel_asc = tipo.vel_asc_kmh * factor_viento
        t_asc = self._tiempo_fase(max(1.0, dist_km * 0.1), vel_asc)
        fuel_factor = self.config.fuel_factor_a_favor if viento_label == "a_favor" else (
            self.config.fuel_factor_en_contra if viento_label == "en_contra" else self.config.fuel_factor_neutro
        )
        combustible_consumido_l += self._combustible(t_asc, tipo.consumo_asc_l_h, fuel_factor)
        yield self.env.timeout(t_asc)

        # Crucero
        viento_cr_label, factor_viento_cr = self._resolver_viento(origen, fase="crucero")
        vel_cr = tipo.vel_cru_kmh * factor_viento_cr
        t_cr = max(self.config.tmin_fase_crucero_min, self._tiempo_fase(max(1.0, dist_km * 0.8), vel_cr))
        fuel_factor_cr = self.config.fuel_factor_a_favor if viento_cr_label == "a_favor" else (
            self.config.fuel_factor_en_contra if viento_cr_label == "en_contra" else self.config.fuel_factor_neutro
        )
        combustible_consumido_l += self._combustible(t_cr, tipo.consumo_cru_l_h, fuel_factor_cr)
        yield self.env.timeout(t_cr)

        # Descenso
        if es_exterior:
            viento_des_label, factor_viento_des = "neutro", self.config.factor_viento_neutro
        else:
            viento_des_label, factor_viento_des = self._resolver_viento(destino, fase="descenso")
        vel_des = tipo.vel_des_kmh * factor_viento_des
        t_des = max(self.config.tmin_fase_asc_des_min, self._tiempo_fase(max(1.0, dist_km * 0.1), vel_des))
        fuel_factor_des = self.config.fuel_factor_a_favor if viento_des_label == "a_favor" else (
            self.config.fuel_factor_en_contra if viento_des_label == "en_contra" else self.config.fuel_factor_neutro
        )
        combustible_consumido_l += self._combustible(t_des, tipo.consumo_des_l_h, fuel_factor_des)
        yield self.env.timeout(t_des)

        # 5) Separacion en ruta (simplificada)
        yield from self._esperar_separacion_ruta(origen, destino)

        llegada_estimada = self.env.now
        recurso_destino = self._recursos.get(destino)

        # Calcula espera estimada en destino (solo vuelos internos)
        tiempo_espera_estimado = 0.0
        if not es_exterior and recurso_destino is not None:
            cola_actual = len(recurso_destino.queue)
            capacidad_dest = recurso_destino.capacity
            tiempo_espera_estimado = (cola_actual / max(1, capacidad_dest)) * self.config.paso_minutos

        if (not es_exterior) and tiempo_espera_estimado > self.config.T_umbral_espera:
            destino_alternativo, mejor_retraso, redir = self._redirigir_si_conviene(
                destino, tiempo_espera_estimado, origen, dist_km
            )
            if redir:
                redirigido = True
                retraso_por_redir = mejor_retraso
                destino_final = destino_alternativo
                recurso_destino = self._recursos[destino_final]

        # Intentar aterrizar o esperar en cola FIFO (solo si hay destino dentro de la red)
        if not es_exterior and recurso_destino is not None:
            with recurso_destino.request() as req_dest:
                yield req_dest
                # Separacion pista en destino
                yield from self._esperar_pista(destino_final)
                self._log_evento(destino_final, "aterrizaje", delta=1)
                if self.config.tiempo_turnaround_min > 0:
                    yield self.env.timeout(self.config.tiempo_turnaround_min)
                self._log_evento(destino_final, "salida_destino", delta=-1)
        else:
            destino_final = "EXTERIOR"

        llegada_real = self.env.now
        retraso_total = max(0.0, llegada_real - salida_prog) - float(vuelo.get("duracion_minutos", 0.0))

        self._registros.append(
            {
                "id_vuelo": vuelo.get("id_vuelo"),
                "origen": origen,
                "destino_programado": destino,
                "destino_final": destino_final,
                "redirigido": redirigido,
                "es_exterior": es_exterior,
                "salida_programada": salida_prog,
                "llegada_real": llegada_real,
                "retraso_total_min": retraso_total,
                "retraso_por_redireccion_min": retraso_por_redir,
                "combustible_consumido_l": combustible_consumido_l,
                "tipo_aeronave": tipo.nombre,
            }
        )

    def run(self) -> pd.DataFrame:
        """Ejecuta la simulacion y devuelve DataFrames de vuelos y eventos."""

        for fila in self.plan_vuelos.itertuples(index=False):
            vuelo = fila._asdict()
            # Validacion ligera usando PlanDeVueloBase (clase comun)
            try:
                _ = PlanDeVueloBase(
                    id_vuelo=str(vuelo.get("id_vuelo", "")),
                    id_origen=str(vuelo.get("origen")),
                    id_destino=str(vuelo.get("destino")),
                    minuto_salida=int(vuelo.get("minuto_salida", 0)),
                    minuto_llegada_programada=int(vuelo.get("minuto_llegada_programada", vuelo.get("minuto_salida", 0))),
                )
            except Exception:
                # Si algo falla en la validacion, continua sin abortar toda la simulacion
                pass
            self.env.process(self._proceso_vuelo(vuelo))

        self.env.run()
        df_vuelos = pd.DataFrame(self._registros)
        df_eventos = pd.DataFrame(self._eventos)
        return df_vuelos, df_eventos
