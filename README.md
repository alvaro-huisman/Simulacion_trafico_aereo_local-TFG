# Programas - TFG

Repositorio con los prototipos, scripts y herramientas de analisis del Trabajo Fin de Grado. Todo el desarrollo se realiza en Python 3.11.14 (distribucion Anaconda) y sigue una estructura modular para facilitar la reutilizacion entre prototipos y la generacion de datos para posteriores estudios.

## Estructura general

- `prototipos/`
  - `comun/`: clases base y utilidades compartidas (modelos de grafo, procesos de simulacion, etc.).
  - `prototipo1/`: primer prototipo operativo con grafo de 10 aeropuertos, generacion de planes aleatorios, simulador SDE y visor interactivo.
  - `prototipo2/`: espacio reservado para evoluciones posteriores.
- `analisis/`: notebooks y scripts de exploracion de resultados (pendiente de consolidar una vez finalizadas las simulaciones definitivas).

Documentacion detallada y comandos especificos estan disponibles en los README de cada subproyecto, por ejemplo `prototipos/prototipo1/README.md`.

## Puesta en marcha

1. Crear un entorno con la version de Python utilizada en el proyecto (Anaconda 3.11.14):
   ```bash
   conda create -n tfg python=3.11.14
   conda activate tfg
   ```
2. Instalar las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
3. (Opcional) Verificar que Tkinter esta disponible en el sistema para utilizar la version con interfaz grafica del visor interactivo.

## Flujo de trabajo recomendado

1. Ejecutar el generador/simulador integrado del prototipo 1:
   ```bash
   python -m prototipos.prototipo1.scripts.main
   ```
   - Genera los planes de vuelo definidos en `configuracion_inicial.txt`.
   - Ejecuta todas las simulaciones y consolida los registros en CSV.
   - Abre el visor con menu desplegable para inspeccionar cada escenario (usar `--sin-visualizacion` si se desea omitir la interfaz).
2. Revisar los CSV resultantes en `prototipos/prototipo1/` (`registros_todos.csv` y, si estan habilitados, `registros_todos_eventos.csv`).
3. Emplear los notebooks de `analisis/` para explotar los datos consolidados (una vez documentados los pasos concretos se incluiran referencias aqui).

## Buenas practicas

- Mantener la configuracion centralizada en `prototipos/prototipo1/configuracion_inicial.txt` y versionar cualquier variacion significativa.
- Evitar dejar archivos temporales o CSV generados dentro del repositorio; el directorio `escenarios/` se mantiene con un `.gitkeep` y debe regenerarse cuando sea necesario.
- Antes de abrir un pull request o compartir resultados, ejecutar los comandos principales y verificar que los registros se generan correctamente.

## Referencias rapidas

- Documentacion especifica del prototipo 1: `prototipos/prototipo1/README.md`
- Punto de entrada general del prototipo 1: `python -m prototipos.prototipo1.scripts.main`
- Visualizador directo por escenario: `python -m prototipos.prototipo1.scripts.visualizacion --escenario N`
- Recoleccion masiva de resultados sin visor: `python -m prototipos.prototipo1.scripts.main --sin-visualizacion`

Cualquier cambio estructural debe reflejarse tanto en este README principal como en la documentacion localizada de cada modulo.
