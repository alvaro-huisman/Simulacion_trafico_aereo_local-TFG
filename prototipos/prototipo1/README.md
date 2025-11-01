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

`configuracion.py` genera 10 nodos identificados como `A`, `B`, ..., `J` con posiciones tridimensionales y capacidades pseudoaleatorias (semilla fija para reproducibilidad). El grafo es completo y la distancia entre nodos se calcula con la norma euclidiana. La velocidad de crucero es comun para todos los vuelos (`8.33` unidades de distancia por minuto, aprox. 500 km/h) y cada avion asciende/ desciende una altura fija de `15` unidades en los primeros y ultimos tramos del trayecto (10 % del progreso total).

## Archivo de configuracion

`configuracion_inicial.txt` centraliza los parametros usados por los scripts CLI:

- `[general] semilla_base`: semilla de referencia para los planes.
- `[aeropuertos] semilla`: controla la generacion pseudoaleatoria de las coordenadas.
- `[escenarios]`: define el directorio donde se guardan los `planes_aleatorios_XXX.csv`, la cantidad de escenarios y el numero de vuelos por dia.
- `[plan_unico] ruta_csv`: archivo empleado por defecto cuando se ejecuta el ejemplo sin escenario.
- `[visualizacion] minuto_defecto`: minuto inicial que se muestra al abrir el visor.
- `[recoleccion] salida_csv`: destino del CSV agregado en la recoleccion de resultados.

Todos los comandos aceptan la opcion `--config` para usar un archivo alternativo con la misma estructura.

## Planes de vuelo aleatorios en CSV

- `generar_planes.py` produce `planes_aleatorios.csv` con 60 vuelos programados dentro de las 24 horas iniciales (0-1439 minutos). Cada fila incluye origen, destino, salida, llegada programada y usa la velocidad de crucero comun para calcular la duracion.
- El script puede ejecutarse de forma independiente:

```bash
python -m prototipos.prototipo1.generar_planes
```

> Opcional: anade `--config ruta/a/mi_config.txt` para usar otro conjunto de parametros.

Para generar multiples escenarios numerados listos para analisis (por ejemplo 50), usa:

```bash
python -m prototipos.prototipo1.generar_planes --cantidad 50 --destino prototipos/prototipo1/escenarios
```

Los archivos resultantes siguen el patron `planes_aleatorios_XXX.csv` dentro del directorio destino.

## Escenario de ejemplo

`ejemplo.py` reconstruye el grafo, genera el CSV (sobrescribiendolo para garantizar aleatoriedad controlada) y ejecuta la simulacion:

```bash
python -m prototipos.prototipo1.ejemplo
```

Tambien puedes indicar un escenario concreto ya generado (1-50) para reutilizar sus planes:

```bash
python -m prototipos.prototipo1.ejemplo --escenario 7 --escenarios-dir prototipos/prototipo1/escenarios
```

Ambos comandos aceptan `--config` para cargar parametros personalizados.

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
- `eventos_vuelos.csv` con el log cronologico (salidas, entradas en cola, llegadas) de cada vuelo.

## Visualizacion de la red

`visualizacion.py` ofrece un visor interactivo (slider minuto a minuto) para inspeccionar la red, coloreando los nodos segun su ocupacion (leyenda en pantalla), resaltando las aristas con vuelos activos y mostrando la posicion actual de cada avion sobre su trayectoria:

```bash
python -m prototipos.prototipo1.visualizacion --hora 12
```

Puedes cargar un escenario numerado pasando `--escenario N` (o introduciendolo por consola si no se indica). Se admiten valores del 1 al 50, cada uno representando un dia diferente con su propio plan de vuelo almacenado en el directorio `escenarios`. Con `--salida ruta.png --sin-interfaz` puede generarse una imagen sin abrir la ventana grafica.

> Para reutilizar otro archivo de configuracion anade `--config ruta/a/mi_config.txt`.

## Recoleccion masiva de resultados

`recolectar_resultados.py` automatiza la ejecucion de N simulaciones (por defecto 50) y consolida todos los vuelos completados en un unico CSV con la columna extra `N_simulacion` que identifica la simulacion/dia (1-50):

```bash
python -m prototipos.prototipo1.recolectar_resultados --cantidad 50 --salida prototipos/prototipo1/registros_todos.csv
```

El script genera los planes que falten en el directorio `escenarios/`, ejecuta cada simulacion y guarda el resultado combinado en la ruta indicada.
Adicionalmente se crea `registros_todos_eventos.csv` con todos los eventos (salidas, colas y llegadas) etiquetados por `N_simulacion`.

> Todos los parametros pueden declararse en un archivo alternativo e invocarse con `--config` para mantener diferentes escenarios de experimentacion.

## Personalizacion rapida

- Ajusta la semilla o el numero de vuelos en `generar_planes_csv` para explorar distintos planes diarios.
- Modifica `generar_aeropuertos_demo` para cambiar posiciones y capacidades de los aeropuertos.
- Deriva una nueva clase desde `ProcesoVueloBase` o `SimulacionBase` en `prototipos/comun` para prototipos futuros manteniendo compatibilidad con los datos existentes.

## Resumen de comandos

| Objetivo | Comando |
| --- | --- |
| Generar el plan unico por defecto | `python -m prototipos.prototipo1.generar_planes --cantidad 1` |
| Generar 50 planes diarios numerados | `python -m prototipos.prototipo1.generar_planes --cantidad 50 --destino prototipos/prototipo1/escenarios` |
| Ejecutar la simulacion base y ver el resumen | `python -m prototipos.prototipo1.ejemplo` |
| Ejecutar el escenario N (1-50) y ver el resumen | `python -m prototipos.prototipo1.ejemplo --escenario 7 --escenarios-dir prototipos/prototipo1/escenarios` |
| Abrir el visor interactivo en un momento concreto | `python -m prototipos.prototipo1.visualizacion --escenario 7 --hora 12` |
| Guardar una imagen de la visualizacion sin abrir la GUI | `python -m prototipos.prototipo1.visualizacion --escenario 7 --minuto 720 --sin-interfaz --salida prototipos/prototipo1/visualizaciones/escenario_007.png` |
| Consolidar todas las simulaciones en un CSV | `python -m prototipos.prototipo1.recolectar_resultados --cantidad 50 --salida prototipos/prototipo1/registros_todos.csv` |
| Generar visualizaciones para los 50 escenarios (PowerShell) | `for ($i=1; $i -le 50; $i++) { $id = \"{0:d3}\" -f $i; python -m prototipos.prototipo1.visualizacion --escenario $i --minuto 720 --sin-interfaz --salida prototipos/prototipo1/visualizaciones/escenario_$id.png }` |

> Anade `--config ruta/a/mi_config.txt` a cualquiera de los comandos anteriores si quieres sobreescribir los parametros definidos en `configuracion_inicial.txt`.
