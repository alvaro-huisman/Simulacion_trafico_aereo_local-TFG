# Programas - TFG

Repositorio con los prototipos, scripts y herramientas de analisis del Trabajo Fin de Grado. Todo el desarrollo se realiza en Python 3.11.14 (Anaconda) y sigue una estructura modular para facilitar la reutilizacion entre prototipos y la generacion de datos.

## Estructura general

- `prototipos/`
  - `comun/`: clases base y utilidades compartidas (modelos de grafo, procesos de simulacion, etc.).
  - `prototipo1/`: grafo de 10 aeropuertos, generacion de planes aleatorios, simulador SDE y visor interactivo.
  - `prototipo2/`: simulador en entorno realista (aeropuertos de Espana, flujos del Ministerio, redirecciones y consumos).
- `analisis/`: notebooks y scripts de exploracion de resultados.

Documentacion detallada en los README de cada subproyecto (`prototipos/prototipo1/README.md`, `prototipos/prototipo2/README.md`).

## Puesta en marcha

1. Crear entorno (Anaconda 3.11.14):
   ```bash
   conda create -n tfg python=3.11.14
   conda activate tfg
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. (Opcional) Tkinter para los visores con GUI.

## Flujo recomendado

### Prototipo 1
```bash
python -m prototipos.prototipo1.scripts.main
```
- Genera planes (10 nodos), ejecuta simulaciones y abre visor (usar `--sin-visualizacion` si no se quiere GUI). CSV combinados en `registros_todos*.csv`.

### Prototipo 2
```bash
python -m prototipos.prototipo2.scripts.preparar_grafo --config prototipos/prototipo2/configuracion_inicial.txt
python -m prototipos.prototipo2.scripts.generar_plan --config prototipos/prototipo2/configuracion_inicial.txt
python -m prototipos.prototipo2.scripts.ejecutar_simulacion --config prototipos/prototipo2/configuracion_inicial.txt
python -m prototipos.prototipo2.scripts.visualizar --config prototipos/prototipo2/configuracion_inicial.txt  # anade --sin-mapa si prefieres sin fondo
```
- Usa aeropuertos (X/Y EPSG:3857) y flujos reales, calcula `w_ij`, genera plan y simula con viento y redirecciones. El numero de dias se define en `configuracion_inicial.txt` (`[simulacion] dias`). Las salidas se guardan organizadas en `prototipos/prototipo2/salidas/`:
  - grafo: `salidas/grafo/grafo_p2.gpickle`
  - plan: `salidas/planes/plan_diario_p2.csv`
  - resultados combinados y por dia: `salidas/resultados/`
  - eventos (ocupacion por aeropuerto) combinados y por dia: `salidas/eventos/` (el visor muestra plazas ocupadas/total por minuto si existen). El modelo ahora inicializa ocupaciones segun trafico y aplica ruido exterior en hubs.

## Buenas practicas

- Centralizar parametros en los `configuracion_inicial.txt` y versionar cambios.
- Mantener `escenarios/` y `resultados_p2/` como carpetas de salida (no versionar CSV temporales si no es necesario).
- Antes de compartir resultados, ejecutar los comandos principales para regenerar planes, simulaciones y visores.

## Referencias rapidas

- P1: `python -m prototipos.prototipo1.scripts.main`
- P1 visor directo: `python -m prototipos.prototipo1.scripts.visualizacion --escenario N`
- P2 flujo completo: ver comandos arriba
- P2 visor: `python -m prototipos.prototipo2.scripts.visualizar --config ... [--sin-mapa]`
