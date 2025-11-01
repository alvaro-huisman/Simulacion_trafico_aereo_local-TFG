# Prototipo 1 - Simulacion SDE con grafo completo

El prototipo valida la estructura basica del simulador con un grafo de 10 aeropuertos completamente conectados. Cada minuto se actualiza el estado de los vuelos, se gestionan colas FIFO cuando un aeropuerto esta lleno y se registran metricas para analisis posteriores.

## Estructura del modulo

- `core/`
  - `configuracion.py`: genera el grafo base y define constantes por defecto.
  - `configuracion_app.py`: carga `configuracion_inicial.txt` con todas las opciones.
  - `planes.py`: utilidades para crear y leer planes de vuelo (`CSV`).
  - `escenarios.py`: funciones para preparar simulaciones listas para ejecutar.
  - `simulacion.py`: implementa `SimulacionPrototipo1` y los procesos de vuelo.
- `scripts/`: puntos de entrada CLI (`python -m prototipos.prototipo1.scripts.*`).
- `escenarios/`: directorio vacio (con `.gitkeep`) donde se guardan los CSV generados.
- `configuracion_inicial.txt`: archivo centralizado con todos los parametros. Cada comando acepta `--config` para usar una copia alternativa.

> Se mantienen archivos de compatibilidad en la raiz (`generar_planes.py`, `visualizacion.py`, etc.) para no romper comandos anteriores, pero toda la logica vive ahora en `core/` y `scripts/`.

## Configuracion centralizada

La configuracion controla desde la generacion de planes hasta la ejecucion del visor:

- `[general]`: semillas y flag `guardar_eventos`.
- `[simulacion]`: paso temporal (`paso_minutos`) y horizonte (`duracion_minutos`).
- `[vuelo]`: velocidad de crucero, altura durante el tramo de crucero y fraccion dedicada al ascenso/descenso.
- `[escenarios]`: directorio, cantidad de escenarios y numero de vuelos por dia.
- `[plan_unico]`: rutas por defecto para el CSV individual y sus registros/eventos.
- `[resultados]`: rutas de salida para los agregados de N simulaciones.
- `[visualizacion]`: minuto inicial del visor y limite de escenarios permitidos.

Las rutas se interpretan relativas al propio archivo de configuracion, lo que facilita crear variantes en otras carpetas.

## Ejecucion integral (generar, simular y visualizar)

```bash
python -m prototipos.prototipo1.scripts.main
```

El orquestador realiza todo el flujo:

1. Genera los planes numerados definidos en la configuracion.
2. Ejecuta todas las simulaciones y consolida los resultados (`registros_todos.csv` y, si procede, `registros_todos_eventos.csv`).
3. Abre una ventana con un menu desplegable (`Combobox`) para elegir el escenario y un visor interactivo con slider minuto a minuto.

Parametros utiles:

- `--cantidad N`: sobrescribe temporalmente la cantidad de escenarios sin modificar el fichero de configuracion.
- `--sin-visualizacion`: salta el visor (solo genera planes y ejecuta las simulaciones).

## Generar planes de vuelo

```bash
python -m prototipos.prototipo1.scripts.generar_planes \
       --cantidad 50 \
       --destino prototipos/prototipo1/escenarios
```

- Con `--cantidad 1` se actualiza el CSV unico (`plan_unico`).
- La velocidad y el horizonte se leen de la configuracion, por lo que no es necesario editar el codigo.

## Ejecutar una simulacion

```bash
python -m prototipos.prototipo1.scripts.ejecutar_simulacion [--escenario N] [--planes ruta.csv]
```

- `--escenario N` reutiliza `planes_aleatorios_NNN.csv` (se genera automaticamente si falta).
- Sin parametros se usa el CSV unico y se regenera si no existe.
- La salida incluye `registros_vuelos.csv` y, si `guardar_eventos = yes`, `eventos_vuelos.csv`. Los nombres incorporan el sufijo del escenario para evitar sobrescrituras.

## Visualizador interactivo

- El orquestador (`scripts.main`) abre la version con menu desplegable para escoger escenario.
- Tambien se puede abrir directamente:

```bash
python -m prototipos.prototipo1.scripts.visualizacion [--escenario N] [--hora H | --minuto M]
```

El visor muestra:

- Slider minuto a minuto adaptado al horizonte configurado.
- Nodos coloreados por ocupacion y etiquetados con capacidad disponible.
- Aristas activas y la posicion actual de cada avion.

No genera archivos de imagen; esta pensado para exploracion manual.

## Recoleccion masiva de registros

```bash
python -m prototipos.prototipo1.scripts.recolectar_resultados \
       --cantidad 50 \
       --salida prototipos/prototipo1/registros_todos.csv
```

- Ejecuta N simulaciones, Anade la columna `N_simulacion` y opcionalmente consolida los eventos en `*_eventos.csv`.
- Genera los planes que falten antes de simular.
- Deja el directorio `escenarios/` listo para posteriores visualizaciones.

## Tabla rapida de comandos

| Objetivo | Comando | Notas |
| --- | --- | --- |
| Ejecucion integral | `python -m prototipos.prototipo1.scripts.main` | Usa `--cantidad N` o `--sin-visualizacion` segun necesites. |
| Generar un solo plan | `python -m prototipos.prototipo1.scripts.generar_planes --cantidad 1` | Respeta las rutas definidas en `plan_unico`. |
| Generar N planes numerados | `python -m prototipos.prototipo1.scripts.generar_planes --cantidad 50 --destino prototipos/prototipo1/escenarios` | Ajusta `--destino` si quieres separar lotes. |
| Ejecutar la simulacion por defecto | `python -m prototipos.prototipo1.scripts.ejecutar_simulacion` | Exporta registros/eventos usando el prefijo configurado. |
| Ejecutar la simulacion para el escenario N | `python -m prototipos.prototipo1.scripts.ejecutar_simulacion --escenario 7` | Comprueba que `N` este dentro de `max_escenarios`. |
| Abrir el visor directo | `python -m prototipos.prototipo1.scripts.visualizacion --escenario 7 --hora 12` | Tambien acepta `--planes ruta.csv`. |
| Consolidar resultados de N simulaciones | `python -m prototipos.prototipo1.scripts.recolectar_resultados --cantidad 50 --salida prototipos/prototipo1/registros_todos.csv` | Genera los logs globales de vuelos y eventos. |

> Anade `--config ruta/a/mi_config.txt` a cualquier comando si quieres usar otro archivo de configuracion.

## Consejos de mantenimiento

- `escenarios/` se mantiene limpio por defecto; genera los CSV cuando los necesites mediante los comandos anteriores.
- Si no quieres guardar los eventos detallados, establece `guardar_eventos = no` antes de ejecutar los scripts.
- Para crear variantes del prototipo, extiende las clases base en `prototipos/comun/modelos.py` y reutiliza las utilidades de `core/`.
