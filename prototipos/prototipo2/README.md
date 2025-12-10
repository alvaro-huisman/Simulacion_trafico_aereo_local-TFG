# Prototipo 2 - Simulador en entorno realista

Herramientas y scripts para generar el grafo de rutas reales de aeropuertos espanoles, crear un plan diario de vuelos y ejecutar la simulacion con SimPy.

## Flujo completo

1) Preparar el grafo (lee aeropuertos y flujos, anade pesos `w_ij` y distancias):
```bash
python -m prototipos.prototipo2.scripts.preparar_grafo --config prototipos/prototipo2/configuracion_inicial.txt
```

2) Generar el plan diario de vuelos a partir de los pesos:
```bash
python -m prototipos.prototipo2.scripts.generar_plan --config prototipos/prototipo2/configuracion_inicial.txt
```

3) Ejecutar la simulacion completa (dias definidos en el config):
```bash
python -m prototipos.prototipo2.scripts.ejecutar_simulacion --config prototipos/prototipo2/configuracion_inicial.txt
```

4) Abrir el visor interactivo (lon/lat, slider minuto a minuto). Si existen los eventos de ocupacion, mostrara plazas ocupadas/total por aeropuerto en cada minuto:
```bash
python -m prototipos.prototipo2.scripts.visualizar --config prototipos/prototipo2/configuracion_inicial.txt
```
> Asegurate de haber generado el grafo y el plan antes de abrir el visor.
> Anade `--sin-mapa` si no quieres cargar un mapa base (util si no hay conexion). En el visor los aviones se dibujan con una silueta limpia y los vuelos redirigidos aparecen en rojo para identificarlos rapido.

Archivos de salida por defecto:
- Grafo: `prototipos/prototipo2/salidas/grafo/grafo_p2.gpickle`
- Plan: `prototipos/prototipo2/salidas/planes/plan_diario_p2.csv`
- Aeropuertos enriquecidos (capacidad + viento): `prototipos/prototipo2/fuentes_de_datos/aeropuertos_enriquecidos.csv`
- Resultados combinados (por vuelo): `prototipos/prototipo2/salidas/resultados/resultados_p2.csv` y alias `resultados_por_vuelo_p2.csv`
- Resultados agregados por aeropuerto: `prototipos/prototipo2/salidas/resultados/resultados_por_aeropuerto_p2.csv`
- Logs de fases de vuelo: `prototipos/prototipo2/salidas/eventos/logs_vuelos_p2.csv` (y uno por dia en `salidas/eventos/logs_p2/`)
- Resultados por dia: `prototipos/prototipo2/salidas/resultados/resultados_p2/resultados_dia_XXX.csv`
- Eventos combinados de ocupacion: `prototipos/prototipo2/salidas/eventos/eventos_p2.csv`
- Eventos por dia: `prototipos/prototipo2/salidas/eventos/eventos_p2/eventos_dia_XXX.csv`
- Plan multi-dia utilizado (si `dias>1`): `prototipos/prototipo2/salidas/planes/plan_usado_p2.csv` (incluye columna `dia` y offsets de minuto por dia).

Secuencia rapida (ya en el bloque anterior):
1. `python -m prototipos.prototipo2.scripts.preparar_grafo --config prototipos/prototipo2/configuracion_inicial.txt`
2. `python -m prototipos.prototipo2.scripts.generar_plan --config prototipos/prototipo2/configuracion_inicial.txt`
3. `python -m prototipos.prototipo2.scripts.ejecutar_simulacion --config prototipos/prototipo2/configuracion_inicial.txt`
4. `python -m prototipos.prototipo2.scripts.visualizar --config prototipos/prototipo2/configuracion_inicial.txt`

La simulacion limpia por defecto el contenido previo de `prototipos/prototipo2/salidas/` antes de generar nuevos planes, resultados y eventos. Si quieres conservar ejecuciones antiguas, trabaja con una copia del fichero de configuracion y otra carpeta de salidas.

## Configuracion

`prototipos/prototipo2/configuracion_inicial.txt` centraliza las rutas y parametros principales:
- **Rutas de entrada**:
  - `aeropuertos_csv`: fichero bruto (X/Y o lat/lon).
  - `aeropuertos_enriquecidos_csv`: se genera al preparar el grafo (incluye capacidad y viento); si existe, se reutiliza.
  - `flujos_csv`: flujos OD del Ministerio.
  - `epsg_origen`: EPSG de las coordenadas de entrada (3857 para X/Y del Ministerio).
- **Salidas**:
  - `grafo_pickle`: grafo con pesos/distancias.
  - `plan_csv`: plan diario de vuelos.
  - `resultados_csv`: resultados combinados de la simulacion.
  - `eventos_csv`: eventos de ocupacion combinados.
- **Generacion de vuelos**:
  - `total_vuelos_diarios`: numero total de vuelos que se distribuiran por pesos (por defecto ~180 para simulaciones rapidas).
  - `hora_inicio` / `hora_fin`: ventana de salidas (horas).
  - `umbral_distancia_tipo_avion`: corta entre avion corto/medio radio.
  - `velocidad_crucero_kmh`: velocidad de referencia para estimar duraciones.
  - `concentracion_horas_punta`: si `yes`, se agrupan salidas en horas punta.
  - `prob_destino_exterior`: % de vuelos que van al nodo externo `EXTERIOR` (consumen capacidad en origen); por defecto 0.10 para dar mas peso al trafico exterior.
  - `dist_exterior_km`: distancia equivalente para esos vuelos exteriores.
- **Datos y viento**:
  - `capacidad_min` / `capacidad_max`: asignacion de capacidad si no viene en el CSV.
  - `prob_viento_a_favor` / `prob_viento_en_contra` / `prob_viento_neutro`: probabilidades para rellenar viento baja/alta cota (usa la `seed`).
- **Simulacion**:
  - `paso_minutos`: paso del reloj SimPy.
  - `T_umbral_espera`: umbral de cola para decidir redireccion.
  - `separar_minutos`: separacion minima en ruta.
  - Factores de viento y combustible: `factor_viento_*`, `fuel_factor_*`.
  - `tiempo_embarque_min` / `tiempo_turnaround_min`: ocupacion de puerta en origen/destino (0 por defecto).
  - `ocupacion_inicial_min_fraccion` / `ocupacion_inicial_max_fraccion`: % inicial de ocupacion (ponderado por trafico).
  - `tmin_fase_asc_des_min` / `tmin_fase_crucero_min`: duraciones minimas por fase para evitar vuelos irreales (en el nucleo se desglosan cinco fases: rodaje, despegue, crucero, aproximacion y aterrizaje con velocidades de referencia 35-60 / 250-300 / 860-930 / ~380 / 240-250 km/h).
  - `dias`: numero de dias consecutivos a simular (por defecto 5) para cadenas de ocupacion y analisis mas largo.

## Modelo de aeronaves y viento

- Dos tipos: corto radio y medio radio. Medio radio vuela mas rapido, alto y con mayor combustible.
  - Corto radio (aprox): crucero 820-880 km/h, techo 28k-34k ft, combustible ~20k L.
  - Medio radio (aprox): crucero 880-940 km/h, techo 33k-41k ft, combustible ~32k L.
- El viento se aplica en todas las fases: ajusta velocidad y consumo usando los factores `factor_viento_*` y `fuel_factor_*` de la configuracion.
- Las fases registradas en los logs (`logs_vuelos_p2.csv`) incluyen inicio/fin, distancia, velocidad, viento y combustible consumido; los resultados finales añaden combustible restante estimado segun la capacidad del tipo de avion.
  - Ruido exterior en hubs: `exterior_top_n`, `exterior_ruido_min/max`, `exterior_intervalo_min/max`, `exterior_estancia_min/max`.
  - `plan_aleatorio_por_dia`: si `yes`, genera un plan distinto para cada dia cuando `dias > 1`; si `no`, reutiliza el plan desplazado.
  - `dias`: numero de dias consecutivos a simular (la ocupacion final de un dia se usa como inicial del siguiente).
  - Nota: la configuracion por defecto busca un equilibrio razonable (capacidad moderada, ~180 vuelos diarios, umbral de espera 30 min, 5 dias y algo mas de trafico exterior). Sube/baja estas cifras segun quieras mas/menos congestion y redirecciones.

**Visor multidia**: usa el valor de `dias` del config (o el maximo `dia` del CSV si existe). Al abrir, veras un cuadro de texto para elegir dia (1..N) y un slider de minutos dentro del dia para inspeccionar todos los dias simulados. Los eventos de ocupacion se emplean para mostrar plazas ocupadas/total por aeropuerto en cada instante. El visor carga `plan_usado_p2.csv` si existe; en caso contrario, usa el plan diario desplazado.

**Redireccion y colas** (regla de la figura):
1. El vuelo se aproxima al destino y comprueba capacidad disponible.
2. Si hay plaza: aterriza inmediato.
3. Si no hay plaza: estima tiempo de espera en cola.
   - Si el tiempo estimado no supera `T_umbral_espera`: entra en cola FIFO y aterriza cuando toca.
   - Si supera el umbral: busca con Dijkstra el aeropuerto alternativo mas cercano al destino original (dist_km) que tenga capacidad libre y evalua el retraso:
     - Si esa alternativa mejora el retraso, no es el origen y la distancia al alternativo no excede ~1.3x la distancia planeada, redirige y aterriza alli.
     - Si ninguna mejora, mantiene destino original y entra en cola.
4. Separacion: se aplica separacion temporal minima `separar_minutos` en ruta (misma arista) y en pista (despegue/aterrizaje). No hay chequeo espacial de cruces de aristas; si lo necesitas, incrementa `separar_minutos` o pide una extension para incluir separacion espacial.

Puedes duplicar este archivo y pasarlo con `--config` para usar distintas configuraciones sin tocar el original. El CLI `--dias` prevalece sobre el valor del config si se indica.

## Dependencias

Requiere `pandas`, `networkx`, `geopy`, `pyproj`, `numpy`, `matplotlib`, `simpy`, `contextily` (opcional para mapa base). Instala todo con el `requirements.txt` del repositorio (entorno recomendado: Anaconda 3.11):
```bash
pip install -r requirements.txt
```

## Utilidades adicionales

- `visualizacion_prototipo2.py`: funciones rapidas para dibujar el grafo y revisar retrasos.
- `datos_aeropuertos.py`: carga y validacion del CSV de aeropuertos (convierte `X/Y` EPSG:3857 a lat/lon, rellena IDs faltantes y guarda nombre/viento por nodo).
- `rutas_desde_flujos.py`: normaliza el CSV de flujos del Ministerio.
- `generacion_vuelos.py`: crea planes diarios en base a pesos `w_ij` y puede enviar un % de vuelos al nodo externo `EXTERIOR` (consumen capacidad en origen).
- `simulador_prototipo2.py`: nucleo de SimPy con logica de viento (rellena vientos faltantes de forma pseudoaleatoria por aeropuerto/fase), consumos en litros ajustados por viento, altitudes realistas de crucero (28k-40k ft), redirecciones y registro de eventos de capacidad (embarque/aterrizaje/turnaround) para visualizar ocupaciones.
- `visualizar.py`: CLI del visor interactivo (lon/lat, slider minuto, tooltips con origen/destino, fase, altitud, viento, velocidad, combustible restante y plazas ocupadas/total si hay eventos). Usa mapa base via `contextily` salvo que se pase `--sin-mapa`.
