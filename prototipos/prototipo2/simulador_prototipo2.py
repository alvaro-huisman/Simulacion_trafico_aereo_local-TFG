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
    capacidad_combustible_l: float


TIPO_CORTO_RADIO = TipoAeronave(
    nombre="corto_radio",
    vel_asc_kmh=500.0,
    vel_cru_kmh=820.0,
    vel_des_kmh=520.0,
    nivel_crucero_min_ft=28000,
    nivel_crucero_max_ft=34000,
    consumo_asc_l_h=3800.0,
    consumo_cru_l_h=3000.0,
    consumo_des_l_h=2100.0,
    capacidad_combustible_l=20000.0,
)

TIPO_MEDIO_RADIO = TipoAeronave(
    nombre="medio_radio",
    vel_asc_kmh=560.0,
    vel_cru_kmh=900.0,
    vel_des_kmh=580.0,
    nivel_crucero_min_ft=33000,
    nivel_crucero_max_ft=41000,
    consumo_asc_l_h=4400.0,
    consumo_cru_l_h=3600.0,
    consumo_des_l_h=2600.0,
    capacidad_combustible_l=32000.0,
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
    tmin_fase_rodaje_min: float = 3.0
    tmin_fase_despegue_min: float = 2.0
    tmin_fase_aproximacion_min: float = 4.0
    tmin_fase_aterrizaje_min: float = 2.0
    dist_rodaje_km: float = 4.0
    frac_dist_despegue: float = 0.08
    frac_dist_aproximacion: float = 0.1
    frac_dist_aterrizaje: float = 0.05
    dist_min_aterrizaje_km: float = 5.0
    consumo_rodaje_factor: float = 0.35


# Velocidades de referencia (km/h) basadas en el fragmento facilitado
VELOCIDADES_REFERENCIA: Dict[str, Tuple[float, float]] = {
    "rodaje": (35.0, 60.0),
    "despegue": (250.0, 300.0),
    "crucero_corto": (820.0, 880.0),
    "crucero_medio": (880.0, 940.0),
    "aproximacion": (380.0, 380.0),
    "aterrizaje": (240.0, 250.0),
}


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
        self._logs_vuelos: List[Dict[str, object]] = []
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
        traf: Dict[str, float] = {n: 0.0 for n in self.grafo.nodes if str(n).upper() != "EXTERIOR"}
        total_w = 0.0
        for u, v, datos in self.grafo.edges(data=True):
            if str(u).upper() == "EXTERIOR" or str(v).upper() == "EXTERIOR":
                continue
            peso_pax = float(datos.get("pasajeros_anuales", 0.0))
            peso_w = float(datos.get("w_ij", 0.0))
            if peso_pax > 0:
                peso = peso_pax
            else:
                peso = peso_w
            total_w += max(peso, 0.0)
            traf[u] = traf.get(u, 0.0) + max(peso, 0.0)
            traf[v] = traf.get(v, 0.0) + max(peso, 0.0)
        # fallback si todo es 0
        if all(v == 0.0 for v in traf.values()):
            for n in traf:
                traf[n] = float(self.grafo.degree[n])
        # Normalizar si venimos de w_ij (suma 1) para dar proporciones comparables
        if total_w > 0 and all(val <= 1.0 for val in traf.values()):
            traf = {k: v / max(1e-9, sum(traf.values())) for k, v in traf.items()}
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
        ocup_prev = self._ocupacion.get(aer_id, 0)
        capacidad = self._recursos[aer_id].capacity
        # Evitar sobrepasar la capacidad: si ya está lleno, no incrementamos
        if delta > 0 and ocup_prev >= capacidad:
            delta_aplicado = 0
            evento = f"{evento}_cap_llena"
        else:
            delta_aplicado = delta
        nueva_ocup = max(0, min(capacidad, ocup_prev + delta_aplicado))
        self._ocupacion[aer_id] = nueva_ocup
        self._eventos.append(
            {
                "minuto": self.env.now,
                "aeropuerto": aer_id,
                "evento": evento,
                "ocupacion": self._ocupacion[aer_id],
                "capacidad": capacidad,
            }
        )

    def _resolver_viento(self, aer_id: str, fase: str) -> tuple[str, float]:
        """Obtiene la etiqueta de viento y factor segun fase."""
        aer_id = self._aer_id_scalar(aer_id)
        datos = self._datos_aeropuerto(aer_id)
        fase_altura = "viento_alta_cota" if fase == "crucero" else "viento_baja_cota"
        etiqueta = datos.get(fase_altura, None)
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

    def _tiempo_espera_siguiente_salida(self, aer_id: str, ahora: float) -> float:
        """Estimacion simple: tiempo hasta la siguiente salida programada desde aer_id."""
        if self.plan_vuelos is None or "origen" not in self.plan_vuelos.columns or "minuto_salida" not in self.plan_vuelos.columns:
            return 0.0
        mask = self.plan_vuelos["origen"].astype(str).eq(str(aer_id)) & (self.plan_vuelos["minuto_salida"] >= ahora)
        if not mask.any():
            return 0.0
        prox = float(self.plan_vuelos.loc[mask, "minuto_salida"].min())
        return max(0.0, prox - ahora)

    def _tiempo_fase(self, distancia_km: float, velocidad_kmh: float) -> float:
        if velocidad_kmh <= 0:
            return 0.0
        return (distancia_km / velocidad_kmh) * 60.0

    def _combustible(self, duracion_min: float, consumo_l_h: float, fuel_factor: float = 1.0) -> float:
        return (duracion_min / 60.0) * consumo_l_h * fuel_factor

    def _fuel_factor_por_viento(self, etiqueta_viento: str) -> float:
        if etiqueta_viento == "a_favor":
            return self.config.fuel_factor_a_favor
        if etiqueta_viento == "en_contra":
            return self.config.fuel_factor_en_contra
        return self.config.fuel_factor_neutro

    def _segmentos_distancia(self, dist_km: float) -> Tuple[float, float, float, float]:
        """Divide la distancia en tramos para despegue, crucero, aproximacion y aterrizaje."""
        dist_despegue = max(1.0, dist_km * self.config.frac_dist_despegue)
        dist_aprox = max(1.0, dist_km * self.config.frac_dist_aproximacion)
        dist_aterr = max(self.config.dist_min_aterrizaje_km, dist_km * self.config.frac_dist_aterrizaje)
        resto = dist_km - (dist_despegue + dist_aprox + dist_aterr)
        if resto < 0:
            total_base = dist_despegue + dist_aprox + dist_aterr
            if total_base > 0:
                escala = dist_km / total_base
                dist_despegue *= escala
                dist_aprox *= escala
                dist_aterr *= escala
            dist_crucero = 0.0
        else:
            dist_crucero = max(resto, 0.0)
        return dist_despegue, dist_crucero, dist_aprox, dist_aterr

    def _velocidad_objetivo(self, fase: str, tipo: TipoAeronave) -> float:
        """Devuelve una velocidad aleatoria dentro del rango de la fase."""
        if fase == "crucero":
            clave = "crucero_corto" if tipo == TIPO_CORTO_RADIO else "crucero_medio"
        else:
            clave = fase
        v_min, v_max = VELOCIDADES_REFERENCIA.get(clave, (tipo.vel_cru_kmh, tipo.vel_cru_kmh))
        return self.rng.uniform(v_min, v_max)

    def _registrar_log_fase(
        self,
        id_vuelo: str,
        fase: str,
        origen: str,
        destino_prog: str,
        destino_final: str,
        inicio_min: float,
        fin_min: float,
        distancia_km: float,
        velocidad_kmh: float,
        viento: str,
        combustible_l: float,
        nota: str | None = None,
    ) -> None:
        self._logs_vuelos.append(
            {
                "id_vuelo": id_vuelo,
                "fase": fase,
                "origen": origen,
                "destino_programado": destino_prog,
                "destino_final": destino_final,
                "minuto_inicio": inicio_min,
                "minuto_fin": fin_min,
                "duracion_min": max(0.0, fin_min - inicio_min),
                "distancia_km": distancia_km,
                "velocidad_kmh": velocidad_kmh,
                "viento": viento,
                "combustible_consumido_l": combustible_l,
                "nota": nota or "",
            }
        )

    def _redirigir_si_conviene(
        self,
        destino_original: str,
        tiempo_espera: float,
        origen_actual: str,
        dist_plan_km: float,
    ) -> Tuple[str, float, bool, float]:
        """Evalua redireccion: devuelve destino_final, retraso_extra, redirigido, distancia_estim_km."""
        mejor_dest = destino_original
        mejor_retraso = tiempo_espera
        redirigido = False
        mejor_dist_ruta = dist_plan_km

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
                mejor_dist_ruta = dist_total

        return mejor_dest, mejor_retraso, redirigido, mejor_dist_ruta

    def _proceso_vuelo(self, vuelo: Dict[str, object]) -> simpy.events.Event:
        origen = self._aer_id_scalar(vuelo["origen"])
        destino = self._aer_id_scalar(vuelo["destino"])
        salida_prog = float(vuelo["minuto_salida"])
        dist_plan_km = float(vuelo.get("distancia_km", 0.0))
        dist_plan_original = dist_plan_km
        es_exterior = bool(vuelo.get("es_exterior", False)) or destino.upper() == "EXTERIOR"

        # 1) Espera hasta la hora de salida
        if self.env.now < salida_prog:
            yield self.env.timeout(salida_prog - self.env.now)

        # 2) Seleccion de aeronave
        tipo = self._seleccionar_tipo_aeronave(dist_plan_km)
        dist_despegue, dist_crucero, dist_aprox, dist_aterr = self._segmentos_distancia(dist_plan_km)

        # 3) Fases de vuelo
        combustible_consumido_l = 0.0
        retraso_por_redir = 0.0
        redirigido = False
        destino_final = destino
        viento_despegue_label, viento_cr_label, viento_aprx_label = "neutro", "neutro", "neutro"
        vel_cr = self._velocidad_objetivo("crucero", tipo)

        # Ocupa capacidad en el origen (rodaje y despegue dentro del recurso)
        recurso_origen = self._recursos[origen]
        with recurso_origen.request() as req:
            yield req
            self._log_evento(origen, "ocupacion_origen", delta=1)
            vel_rodaje = self._velocidad_objetivo("rodaje", tipo)
            t_rodaje = max(self.config.tmin_fase_rodaje_min, self._tiempo_fase(self.config.dist_rodaje_km, vel_rodaje))
            fuel_rodaje = self._combustible(
                t_rodaje, tipo.consumo_asc_l_h * self.config.consumo_rodaje_factor, self.config.fuel_factor_neutro
            )
            combustible_consumido_l += fuel_rodaje
            inicio_fase = self.env.now
            yield self.env.timeout(t_rodaje)
            self._registrar_log_fase(
                vuelo.get("id_vuelo", ""),
                "rodaje",
                origen,
                destino,
                destino_final,
                inicio_fase,
                self.env.now,
                self.config.dist_rodaje_km,
                vel_rodaje,
                "neutro",
                fuel_rodaje,
            )

            yield from self._esperar_pista(origen)
            if self.config.tiempo_embarque_min > 0:
                yield self.env.timeout(self.config.tiempo_embarque_min)
            viento_despegue_label, factor_viento = self._resolver_viento(origen, fase="despegue")
            vel_despegue = self._velocidad_objetivo("despegue", tipo) * factor_viento
            t_despegue = max(self.config.tmin_fase_despegue_min, self._tiempo_fase(dist_despegue, vel_despegue))
            fuel_factor = self._fuel_factor_por_viento(viento_despegue_label)
            fuel_despegue = self._combustible(t_despegue, tipo.consumo_asc_l_h, fuel_factor)
            combustible_consumido_l += fuel_despegue
            inicio_fase = self.env.now
            yield self.env.timeout(t_despegue)
            self._registrar_log_fase(
                vuelo.get("id_vuelo", ""),
                "despegue",
                origen,
                destino,
                destino_final,
                inicio_fase,
                self.env.now,
                dist_despegue,
                vel_despegue,
                viento_despegue_label,
                fuel_despegue,
            )
            self._log_evento(origen, "despegue", delta=-1)

        # Crucero
        viento_cr_label, factor_viento_cr = self._resolver_viento(origen, fase="crucero")
        vel_cr = max(1.0, vel_cr * factor_viento_cr)
        t_cr = max(self.config.tmin_fase_crucero_min, self._tiempo_fase(dist_crucero, vel_cr))
        fuel_factor_cr = self._fuel_factor_por_viento(viento_cr_label)
        fuel_cr = self._combustible(t_cr, tipo.consumo_cru_l_h, fuel_factor_cr)
        combustible_consumido_l += fuel_cr
        inicio_fase = self.env.now
        yield self.env.timeout(t_cr)
        self._registrar_log_fase(
            vuelo.get("id_vuelo", ""),
            "crucero",
            origen,
            destino,
            destino_final,
            inicio_fase,
            self.env.now,
            dist_crucero,
            vel_cr,
            viento_cr_label,
            fuel_cr,
        )

        llegada_estimada = self.env.now
        recurso_destino = self._recursos.get(destino)

        # Calcula espera estimada en destino (solo vuelos internos)
        tiempo_espera_estimado = 0.0
        if not es_exterior and recurso_destino is not None:
            cola_actual = len(recurso_destino.queue)
            capacidad_dest = recurso_destino.capacity
            ocup_dest = recurso_destino.count
            espera_cola = (cola_actual / max(1, capacidad_dest)) * self.config.separar_minutos
            espera_por_salida = 0.0
            if ocup_dest >= capacidad_dest:
                espera_por_salida = self._tiempo_espera_siguiente_salida(destino, self.env.now)
            tiempo_espera_estimado = espera_cola + espera_por_salida

        if (not es_exterior) and tiempo_espera_estimado > self.config.T_umbral_espera:
            destino_alternativo, mejor_retraso, redir, dist_alt = self._redirigir_si_conviene(
                destino, tiempo_espera_estimado, origen, dist_plan_km
            )
            if redir:
                redirigido = True
                retraso_por_redir = mejor_retraso
                destino_final = destino_alternativo
                recurso_destino = self._recursos[destino_final]
                dist_plan_km = dist_alt

        dist_despegue, dist_crucero, dist_aprox, dist_aterr = self._segmentos_distancia(dist_plan_km)

        # Aproximacion
        if es_exterior:
            viento_aprx_label, factor_viento_aprx = "neutro", self.config.factor_viento_neutro
        else:
            viento_aprx_label, factor_viento_aprx = self._resolver_viento(destino_final, fase="aproximacion")
        vel_aprox = self._velocidad_objetivo("aproximacion", tipo) * factor_viento_aprx
        t_aprox = max(self.config.tmin_fase_aproximacion_min, self._tiempo_fase(dist_aprox, vel_aprox))
        fuel_factor_aprx = self._fuel_factor_por_viento(viento_aprx_label)
        fuel_aprx = self._combustible(t_aprox, tipo.consumo_des_l_h, fuel_factor_aprx)
        combustible_consumido_l += fuel_aprx
        inicio_fase = self.env.now
        yield self.env.timeout(t_aprox)
        self._registrar_log_fase(
            vuelo.get("id_vuelo", ""),
            "aproximacion",
            origen,
            destino,
            destino_final,
            inicio_fase,
            self.env.now,
            dist_aprox,
            vel_aprox,
            viento_aprx_label,
            fuel_aprx,
        )

        # 5) Separacion en ruta (simplificada)
        yield from self._esperar_separacion_ruta(origen, destino_final)

        # Intentar aterrizar o esperar en cola FIFO (solo si hay destino dentro de la red)
        espera_cola = 0.0
        if not es_exterior and recurso_destino is not None:
            with recurso_destino.request() as req_dest:
                espera_ini = self.env.now
                yield req_dest
                espera_cola = self.env.now - espera_ini
                if espera_cola > 0:
                    fuel_hold = self._combustible(
                        espera_cola, tipo.consumo_cru_l_h, self.config.fuel_factor_neutro
                    )
                    combustible_consumido_l += fuel_hold
                    self._registrar_log_fase(
                        vuelo.get("id_vuelo", ""),
                        "espera_cola_destino",
                        origen,
                        destino,
                        destino_final,
                        espera_ini,
                        self.env.now,
                        0.0,
                        0.0,
                        "neutro",
                        fuel_hold,
                        nota="espera en cola de pista",
                    )
                # Separacion pista en destino
                yield from self._esperar_pista(destino_final)
                viento_at_label, factor_viento_at = self._resolver_viento(destino_final, fase="aterrizaje")
                vel_at = self._velocidad_objetivo("aterrizaje", tipo) * factor_viento_at
                t_at = max(self.config.tmin_fase_aterrizaje_min, self._tiempo_fase(dist_aterr, vel_at))
                fuel_factor_at = self._fuel_factor_por_viento(viento_at_label)
                fuel_at = self._combustible(t_at, tipo.consumo_des_l_h, fuel_factor_at)
                combustible_consumido_l += fuel_at
                inicio_fase = self.env.now
                yield self.env.timeout(t_at)
                self._registrar_log_fase(
                    vuelo.get("id_vuelo", ""),
                    "aterrizaje",
                    origen,
                    destino,
                    destino_final,
                    inicio_fase,
                    self.env.now,
                    dist_aterr,
                    vel_at,
                    viento_at_label,
                    fuel_at,
                )
                self._log_evento(destino_final, "aterrizaje", delta=1)
                if self.config.tiempo_turnaround_min > 0:
                    yield self.env.timeout(self.config.tiempo_turnaround_min)
                self._log_evento(destino_final, "salida_destino", delta=-1)
        else:
            destino_final = "EXTERIOR"
            t_at = 0.0
            vel_at = 0.0
            viento_at_label = "neutro"
            fuel_at = 0.0
            espera_cola = 0.0

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
                "capacidad_combustible_l": tipo.capacidad_combustible_l,
                "combustible_restante_est_l": max(0.0, tipo.capacidad_combustible_l - combustible_consumido_l),
                "tiempo_total_min": max(0.0, llegada_real - salida_prog),
                "tiempo_rodaje_min": t_rodaje,
                "tiempo_despegue_min": t_despegue,
                "tiempo_crucero_min": t_cr,
                "tiempo_aproximacion_min": t_aprox,
                "tiempo_aterrizaje_min": t_at,
                "tiempo_espera_cola_min": espera_cola,
                "dist_rodaje_km": self.config.dist_rodaje_km,
                "dist_despegue_km": dist_despegue,
                "dist_crucero_km": dist_crucero,
                "dist_aproximacion_km": dist_aprox,
                "dist_aterrizaje_km": dist_aterr,
                "velocidad_crucero_kmh": vel_cr,
                "velocidad_despegue_kmh": vel_despegue,
                "velocidad_aproximacion_kmh": vel_aprox,
                "velocidad_aterrizaje_kmh": vel_at,
                "viento_despegue": viento_despegue_label,
                "viento_crucero": viento_cr_label,
                "viento_aproximacion": viento_aprx_label,
                "viento_aterrizaje": viento_at_label,
                "distancia_plan_km": dist_plan_original,
                "distancia_ruta_km": dist_plan_km,
            }
        )

    def run(self) -> pd.DataFrame:
        """Ejecuta la simulacion y devuelve DataFrames de vuelos, eventos y logs de fases."""

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
        df_logs = pd.DataFrame(self._logs_vuelos)
        return df_vuelos, df_eventos, df_logs
