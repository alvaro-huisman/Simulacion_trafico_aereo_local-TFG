# Prototipo 1 - Simulacion basada en SimPy

Este directorio contiene la primera version funcional del simulador SDE. El objetivo es validar la estructura basica del sistema con un grafo de 10 aeropuertos conectados completamente, vuelos programados durante 24 horas y gestion de capacidad mediante colas FIFO en los destinos.

## Arquitectura compartida

Las clases basicas viven en `prototipos/comun/modelos.py` y pueden reutilizarse en prototipos posteriores:

- `PlanDeVueloBase`, `InstantaneaVueloBase`, `RegistroVueloCompletadoBase`: describen datos de entrada, estados intermedios y resultados.
- `AeropuertoBase`: controla capacidad total, lista de planes y cola de aterrizajes.
- `SimulacionBase`: administra el entorno `SimPy`, los aeropuertos registrados y la creacion de procesos de vuelo.
- `ProcesoVueloBase`: punto de extension para implementar la logica de cada prototipo.

## Elementos del Prototipo 1

Las clases especificas se encuentran en `simulacion.py`:

- `PlanDeVuelo`, `InstantaneaVuelo`, `RegistroVueloCompletado`: extienden las clases base y no anaden restricciones extra.
- `Aeropuerto`: reutiliza el comportamiento de `AeropuertoBase`.
- `ProcesoVuelo`: implementa la dinamica del vuelo (interpolacion de posicion, calculo de ETA y cola de espera en el destino).
- `SimulacionPrototipo1`: crea los procesos de vuelo y expone utilidades para obtener rutas estaticas y registros completados.

Todos estos simbolos se exportan desde `prototipos/prototipo1/__init__.py`.

## Grafo de 10 aeropuertos

`configuracion.py` genera 10 nodos identificados como `A`, `B`, ..., `J` con posiciones tridimensionales y capacidades pseudoaleatorias (semilla fija para reproducibilidad). El grafo es completo y la distancia entre nodos se calcula con la norma euclidiana. La velocidad de crucero es comun para todos los vuelos (`8.33` unidades de distancia por minuto, aprox. 500 km/h).

## Planes de vuelo aleatorios en CSV

- `generar_planes.py` produce `planes_aleatorios.csv` con 60 vuelos programados dentro de las 24 horas iniciales (0-1439 minutos). Cada fila incluye origen, destino, salida, llegada programada y usa la velocidad de crucero comun para calcular la duracion.
- El script puede ejecutarse de forma independiente:

```bash
python -m prototipos.prototipo1.generar_planes
```

## Escenario de ejemplo

`ejemplo.py` reconstruye el grafo, genera el CSV (sobrescribiendolo para garantizar aleatoriedad controlada) y ejecuta la simulacion:

```bash
python -m prototipos.prototipo1.ejemplo
```

La salida incluye:

1. Distancias de las rutas estaticas entre los 10 aeropuertos.
2. Listado de vuelos completados con horarios y retrasos acumulados.
3. Muestreo de instantaneas del primer vuelo que experimento cola de espera.

La ejecucion tambien exporta `registros_vuelos.csv` (via `pandas`) con los campos:

- `id_vuelo`
- `aeropuerto_origen`
- `aeropuerto_destino`
- `hora_salida`
- `hora_llegada_programada`
- `hora_llegada_real`
- `retraso_minutos`

## Visualizacion de la red

`visualizacion.py` ofrece un visor interactivo (slider por horas) para inspeccionar la red, coloreando los nodos segun su ocupacion y resaltando las aristas con vuelos activos:

```bash
python -m prototipos.prototipo1.visualizacion --hora 12
```

Con `--salida ruta.png --sin-interfaz` puede generarse una imagen sin abrir la ventana grafica.

## Personalizacion rapida

- Ajusta la semilla o el numero de vuelos en `generar_planes_csv` para explorar distintos planes diarios.
- Modifica `generar_aeropuertos_demo` para cambiar posiciones y capacidades de los aeropuertos.
- Deriva una nueva clase desde `ProcesoVueloBase` o `SimulacionBase` en `prototipos/comun` para prototipos futuros manteniendo compatibilidad con los datos existentes.
