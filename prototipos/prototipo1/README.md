# Prototipo 1 · Simulación SDE con grafo completo

El prototipo valida la estructura básica del simulador mediante un grafo de 10 aeropuertos conectados completamente. Cada minuto se actualiza el estado de los vuelos activos, se gestionan colas FIFO cuando un aeropuerto está lleno y se registran métricas para posteriores análisis.

## Estructura del módulo

- `core/`: componentes reutilizables
  - `configuracion.py`: generación del grafo base y constantes por defecto.
  - `configuracion_app.py`: carga del archivo `configuracion_inicial.txt`.
  - `planes.py`: utilidades para crear y leer planes de vuelo (`CSV`).
  - `escenarios.py`: funciones para construir simulaciones listas para ejecutar.
  - `simulacion.py`: implementación de `SimulacionPrototipo1`, procesos de vuelo y exportadores `pandas`.
- `scripts/`: puntos de entrada CLI (`python -m prototipos.prototipo1.scripts.*`).
- `escenarios/`: directorio vacío (con `.gitkeep`) donde se almacenan los planes numerados generados por los comandos.
- `configuracion_inicial.txt`: fichero centralizado con todos los parámetros. Cada script acepta `--config` para usar una copia alternativa.

> Se mantienen archivos de compatibilidad (`generar_planes.py`, `ejemplo.py`, etc.) para que los comandos antiguos sigan funcionando, pero toda la lógica reside ahora en `core/` y `scripts/`.

## Configuración centralizada

La configuración controla tanto la generación de datos como la simulación:

- `[general]` – semillas y flag `guardar_eventos`.
- `[simulacion]` – tamaño del paso (`paso_minutos`) y horizonte máximo (`duracion_minutos`).
- `[vuelo]` – velocidad de crucero, altura extra durante crucero y fracción del trayecto dedicada a ascenso/descenso.
- `[escenarios]` – directorio de salida, cantidad de escenarios y número de vuelos por día.
- `[plan_unico]` – rutas por defecto para el CSV individual y sus registros/eventos.
- `[resultados]` – rutas para los agregados de N simulaciones.
- `[visualizacion]` – minuto inicial del visor y número máximo de escenarios disponibles.

Todas las rutas son relativas al propio archivo de configuración, lo que facilita crear variantes en otras carpetas.

## Generar planes de vuelo

```bash
python -m prototipos.prototipo1.scripts.generar_planes \
       --cantidad 50 \
       --destino prototipos/prototipo1/escenarios
```

- Con `--cantidad 1` se actualiza el CSV único (`plan_unico`).
- Se puede ajustar la velocidad u horizonte desde el fichero de configuración sin tocar código.

## Ejecutar una simulación

```bash
python -m prototipos.prototipo1.scripts.ejecutar_simulacion [--escenario N] [--planes ruta.csv]
```

- Si se indica `--escenario N`, se reutiliza el plan `planes_aleatorios_NNN.csv` (se genera automáticamente si no existe).
- Sin parámetros se usa el CSV único y se regenera en caso necesario.
- Resultados: `registros_vuelos.csv` y, si `guardar_eventos = yes`, `eventos_vuelos.csv`. Los nombres de los archivos reciben el sufijo del escenario para mantenerlos separados.

## Visualizador interactivo

```bash
python -m prototipos.prototipo1.scripts.visualizacion [--escenario N] [--hora H | --minuto M]
```

- El visor abre una ventana con controles `matplotlib`: slider minuto a minuto, nodos coloreados por ocupación, aristas activas y posición actual de cada avión.
- No se generan ficheros de imagen (herramienta puramente interactiva).
- El slider se adapta automáticamente al horizonte configurado (`duracion_minutos`).

## Recolección masiva y registros

```bash
python -m prototipos.prototipo1.scripts.recolectar_resultados \
       --cantidad 50 \
       --salida prototipos/prototipo1/registros_todos.csv
```

- Ejecuta N simulaciones, añade la columna `N_simulacion` a cada fila y opcionalmente consolida los eventos en `*_eventos.csv`.
- Genera los planes que falten antes de simular.
- El directorio `escenarios/` queda preparado para posteriores análisis o visualizaciones.

## Tabla rápida de comandos

| Objetivo | Comando | Notas |
| --- | --- | --- |
| Generar un solo plan | `python -m prototipos.prototipo1.scripts.generar_planes --cantidad 1` | Respeta la semilla y rutas definidas en `plan_unico`. |
| Generar N planes numerados | `python -m prototipos.prototipo1.scripts.generar_planes --cantidad 50 --destino prototipos/prototipo1/escenarios` | Ajusta `--destino` si quieres separar lotes. |
| Ejecutar la simulación por defecto | `python -m prototipos.prototipo1.scripts.ejecutar_simulacion` | Exporta registros/eventos usando el prefijo configurado. |
| Ejecutar la simulación para el escenario N | `python -m prototipos.prototipo1.scripts.ejecutar_simulacion --escenario 7` | Valida primero que `N` esté dentro de `max_escenarios`. |
| Abrir el visor interactivo | `python -m prototipos.prototipo1.scripts.visualizacion --escenario 7 --hora 12` | También acepta `--planes ruta.csv`. |
| Consolidar resultados de N simulaciones | `python -m prototipos.prototipo1.scripts.recolectar_resultados --cantidad 50 --salida prototipos/prototipo1/registros_todos.csv` | Crea los logs globales de vuelos y eventos. |

> Añade `--config ruta/a/mi_config.txt` para trabajar con otra configuración sin modificar el archivo principal.

## Consejos de mantenimiento

- El directorio `escenarios/` se limpia por defecto; genera los CSV cuando los necesites mediante los comandos anteriores.
- Si no quieres guardar los eventos detallados, establece `guardar_eventos = no` en la configuración antes de ejecutar los scripts.
- Para crear variantes del prototipo, extiende las clases base en `prototipos/comun/modelos.py` y reutiliza las fábricas de `core/`.
