# SIPOTDA - Optimización logística

Sistema de escritorio en Python para planificar entregas sobre una cuadrícula de
12×12, comparar técnicas de búsqueda y optimización y construir una planificación
final justificada. Integra una interfaz Tkinter, carga/guardado de escenarios JSON,
experimentos reproducibles, exportación CSV, gráficas y análisis estratégico.

Los notebooks de `ejemplos/` se usaron únicamente como referencia. La
implementación del proyecto es la de los módulos `.py`; no se importan notebooks
ni se delega la optimización a bibliotecas de terceros.

## Funcionalidades

- Editor visual de escenarios: inicio, destino, entregas, obstáculos, costos y
  recursos. Las entregas y los obstáculos se añaden o quitan con una sola
  herramienta; el doble clic edita el costo o la entrega de la celda.
- Configuración integrada bajo la cuadrícula: recursos, competidor, algoritmos y
  experimentos.
- Búsqueda de rutas con Greedy Best-First y A*.
- Optimización del orden de entregas con Hill Climbing, recocido simulado y
  algoritmo genético.
- Juego estratégico empresa/competidor con matriz visual de pagos, mejores
  respuestas, dominancia y equilibrios de Nash resaltados.
- Búsqueda adversaria con Minimax y poda alfa-beta.
- Experimentos reproducibles con semillas, repeticiones y presupuestos fijos.
- Exportación de resultados a CSV, generación de gráficas y planificación final
  en JSON.
- Resultados con pestañas independientes para resumen, ejecuciones, rutas,
  gráficas, acciones, juego, adversaria y plan final. Las rutas se muestran de a
  una solución por vez, incluido el recorrido final del plan.
- Validación estructural y de factibilidad antes de ejecutar todos los módulos.

## Requisitos

- Python 3.10 o superior (probado con Python 3.14.5).
- Tkinter (incluido en las instalaciones oficiales de Python; en Linux puede
  requerir el paquete del sistema `python3-tk`).
- matplotlib y numpy.

Instalación de dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Ejecución

Desde la carpeta del proyecto:

```powershell
python main.py
```

Al iniciar se carga `escenarios/escenario_predeterminado.json`.

Flujo recomendado en la interfaz:

1. En **Escenario**, elija una herramienta y haga clic en la cuadrícula. En modo
   **Seleccionar / mover** puede arrastrar inicio, destino, entregas y
   obstáculos. Las herramientas **Añadir / Quitar entrega** y
   **Añadir / Quitar obstáculo** alternan según el estado de la celda. El doble
   clic edita el costo de una celda o los datos de una entrega.
2. En la configuración situada bajo la cuadrícula, ajuste recursos, movimiento,
   competidor y parámetros de algoritmos/experimentos. Pulse **Aplicar al
   escenario**.
3. Pulse **Ejecutar todos los módulos**. La aplicación valida estructura,
   factibilidad y parámetros, y ejecuta heurísticas, Hill Climbing,
   metaheurísticas, juego estratégico, búsqueda adversaria y planificación.
4. En **Resultados** revise **Resumen**, **Ejecuciones**, **Rutas**, **Gráficas**,
   **Acciones**, **Juego estratégico**, **Adversaria** y **Plan final**.
5. Use **Guardar**: si el escenario ya tiene una ruta asociada se sobrescribe sin
   preguntar; si es nuevo, se solicita la ruta y el nombre una sola vez.

La ejecución pesada se realiza en un hilo de trabajo; los controles de edición y
configuración se deshabilitan durante la tarea y la barra de estado indica el
avance. Si un módulo falla, se registra el error y se conservan los resultados
válidos de los demás módulos.

## Estructura

```text
SIPOTDA/
├── main.py
├── configuracion/
│   └── parametros.json
├── escenarios/
│   ├── escenario_predeterminado.json
│   ├── escenario_alternativo.json
│   ├── escenario_estrecho.json
│   └── escenario_bloqueado.json
├── modelos/
│   ├── celda.py
│   ├── recurso.py
│   ├── entrega.py
│   ├── escenario.py
│   ├── solucion.py
│   └── resultados.py
├── algoritmos/
│   ├── comun.py
│   ├── registro.py
│   ├── busqueda_heuristica/
│   ├── busqueda_local/
│   ├── metaheuristicas/
│   ├── teoria_juegos/
│   └── busqueda_adversaria/
├── gestion_archivos/
├── experimentos/
├── interfaz/
│   ├── ventana_principal.py
│   ├── editor_escenario.py
│   ├── panel_configuracion.py
│   ├── panel_resultados.py
│   ├── panel_graficas.py
│   ├── panel_rutas.py
│   ├── panel_acciones.py
│   └── visualizador.py
├── pruebas/
├── resultados/
│   ├── csv/
│   └── graficas/
└── ejemplos/           # notebooks de referencia, no forman parte del sistema
```

## Modelo del escenario

Un escenario contiene:

- `filas`, `columnas` y matriz de `celdas` con costo positivo.
- `inicio`, `destino`, entregas con demanda/tarifa y obstáculos.
- Recursos obligatorios: `combustible`, `capacidad`, `tiempo`, `presupuesto`.
- Competidor con factores de costo/presupuesto y celdas bloqueadas.
- Restricciones de movimiento: cuatro direcciones por defecto; diagonal opcional
  con factor `sqrt(2)`.
- Tarifa por unidad y metadatos.

El costo de entrar en una celda es su costo. Un obstáculo no es transitable. La
capacidad se compara con la demanda total; el combustible y el tiempo se consumen
por paso; el presupuesto se compara con el costo total de la ruta.

### Ejemplo completo mínimo

```json
{
  "id": "mini_3x3",
  "nombre": "Ejemplo mínimo",
  "filas": 3,
  "columnas": 3,
  "inicio": [0, 0],
  "destino": [2, 2],
  "entregas": [
    {"id": 1, "nombre": "E1", "fila": 0, "columna": 2,
     "demanda": 2.0, "tarifa": 60.0},
    {"id": 2, "nombre": "E2", "fila": 1, "columna": 1,
     "demanda": 2.0, "tarifa": 60.0},
    {"id": 3, "nombre": "E3", "fila": 2, "columna": 0,
     "demanda": 2.0, "tarifa": 60.0}
  ],
  "obstaculos": [],
  "recursos": {
    "combustible": {"cantidad": 100, "consumo_por_paso": 1.0},
    "capacidad": {"cantidad": 10, "consumo_por_paso": 0.0},
    "tiempo": {"cantidad": 100, "consumo_por_paso": 1.0},
    "presupuesto": {"cantidad": 100, "consumo_por_paso": 0.0}
  },
  "competidor": {
    "nombre": "Competidor",
    "factor_costo": 1.0,
    "factor_presupuesto": 1.0,
    "celdas_bloqueadas": []
  },
  "restricciones": {"permitir_diagonal": false},
  "costos": [
    [1.0, 1.0, 1.0],
    [1.0, 1.0, 1.0],
    [1.0, 1.0, 1.0]
  ]
}
```

## Algoritmos y criterios

### Costo y factibilidad

Una solución encadena los tramos `inicio → entregas en orden → destino`. El
costo total suma los costos de todas las celdas de destino de cada tramo. Una
solución es factible si:

- respeta obstáculos, límites y puntos obligatorios;
- no excede capacidad, combustible, tiempo ni presupuesto;
- no contiene tramos sin ruta.

Si una solución incumple recursos, su costo objetivo es:

```text
costo_objetivo = costo_total + penalización
penalización_base = 1_000_000
```

### Greedy Best-First y A*

Ambos planifican cada tramo con búsqueda sobre la cuadrícula.

- Greedy ordena por la heurística `h(n)`.
- A* ordena por `f(n) = g(n) + h(n)`.
- La heurística es Manhattan, u octile si la diagonal está habilitada, multiplicada
  por el costo mínimo transitable. Es admisible y consistente.
- `modo='costo'` usa el costo de la celda; `modo='pasos'` usa 1 por movimiento.
- Las métricas incluyen nodos expandidos, nodos generados y tiempo.

### Hill Climbing

Trabaja sobre permutaciones del orden de entregas. En cada iteración evalúa todos
los intercambios 2-swap y se mueve al mejor vecino. Puede permitir movimientos
laterales (mesetas) con un límite. `reinicios_hill_climbing` ejecuta varios
inicios con semillas reproducibles y registra el resumen de éxitos y óptimos
locales.

### Recocido simulado

Acepta un vecino peor con probabilidad:

```text
P(aceptar) = exp(-Δ / T)
```

La temperatura desciende geométricamente:

```text
T_{k+1} = α · T_k,  0 < α < 1
```

El criterio de parada combina temperatura final, iteraciones por temperatura y
presupuesto máximo de iteraciones.

### Algoritmo genético

- Representación: permutación de IDs de entrega.
- Aptitud: `1 / (1 + costo_objetivo)`.
- Selección: torneo.
- Cruza: Order Crossover (OX).
- Mutación: intercambio de dos posiciones.
- Elitismo configurable.
- Semillas registradas por ejecución.

### Teoría de juegos

Jugadores: empresa de distribución (MAX) y competidor (MIN/estrategia). Los pagos
se calculan a partir de rutas reales obtenidas con A*.

```text
ingreso_base = Σ demanda_i · tarifa_i
costo_efectivo = costo_ruta · factor_costo_empresa · factor_costo_competidor
                  · factor_presupuesto_competidor
penalización = 120 · riesgo + excesos_de_recursos
pago_empresa = ingreso_base - costo_efectivo - penalización

margen_competidor = 0.22 · ingreso_base
captura = 0.45 · max(0, costo_efectivo - costo_base)
pago_competidor = margen_competidor + captura + bono_bloqueo - castigo
```

El módulo calcula mejores respuestas, dominancia estricta/débil, equilibrios de
Nash puros y una recomendación (Nash con mayor pago para la empresa o maximin si
no hay Nash).

### Minimax y alfa-beta

El subproblema adversario modela rondas de decisiones de recursos:

- MAX: asegurar combustible, reservar ruta o negociar prioridad.
- MIN: mantener disponibilidad, encarecer combustible o bloquear ruta.
- Estado inmutable: turno, presupuesto, combustible, reservas, bloqueos, riesgo,
  impacto e historiales.
- La utilidad de MAX combina ingreso, costo operativo, costo de acciones,
  penalización por riesgo y valor de reservas/combustible.
- Al cortar por profundidad se usa una evaluación aproximada conservadora.
- La profundidad debe ser al menos 2; si es impar se ajusta al siguiente par.
- Alfa-beta debe devolver el mismo valor que Minimax; los experimentos lo
  verifican y registran nodos visitados, podados y tiempo.

## Experimentos reproducibles

La configuración está en `configuracion/parametros.json`:

- 20 repeticiones de recocido y genético con semillas pareadas.
- 10 inicios de Hill Climbing.
- Semilla base `2026`.
- Profundidades adversarias `[2, 4, 6]`.
- Presupuestos de iteraciones/población documentados en el JSON.

La interfaz usa estos valores, pero permite cambiarlos y valida rangos antes de
ejecutar. También se puede ejecutar el flujo completo desde Python:

```powershell
python -c "from pathlib import Path; from gestion_archivos.lector_json import cargar_escenario; from experimentos.ejecutar_experimentos import ejecutar_todo; e=cargar_escenario(Path('escenarios/escenario_predeterminado.json')); d=ejecutar_todo(e, generar_graficas=True, guardar=True); print(d['plan']['costo_total'])"
```

Salidas principales:

- `resultados/csv/historial_ejecuciones.csv`: historial acumulado.
- `resultados/csv/resultados_completos_<escenario>.csv`: resultados del flujo.
- `resultados/csv/resumen_comparacion.csv`: resumen por algoritmo.
- `resultados/csv/adversaria_<escenario>.csv`: comparación Minimax/alfa-beta.
- `resultados/csv/juego_matriz_<escenario>.csv`: matriz de pagos.
- `resultados/planificacion_final.json`: plan completo con rutas, recursos,
  validaciones, riesgos y justificación.
- `resultados/graficas/*.png`: gráficas generadas desde CSV.

## Validación

- `Escenario.validar()` comprueba dimensiones, superposiciones, obstáculos,
  recursos, capacidad, costos y conectividad.
- `validar_factibilidad()` recorre/permuta órdenes para comprobar si existe una
  solución factible; usa exploración exhaustiva hasta 7 entregas y muestreo
  reproducible para tamaños mayores.
- `escenarios/escenario_bloqueado.json` es inválido deliberadamente y sirve para
  probar la detección de escenarios sin solución.
- Los algoritmos registran su validez y sus violaciones; no se presentan
  resultados inválidos como exitosos.

## Pruebas

```powershell
python -m unittest discover -s pruebas -v
```

Las pruebas cubren carga/validación de escenarios, búsquedas heurísticas,
Hill Climbing, recocido, genético, juego, equivalencia Minimax/alfa-beta, un
flujo completo reducido en un directorio temporal y la continuidad ante fallos
parciales de un módulo (sin alterar los resultados finales del proyecto).

## Notas de implementación

- Los algoritmos centrales se implementaron manualmente; no se usan librerías de
  optimización.
- Toda la interfaz está separada de la lógica mediante `interfaz/`.
- Las rutas de archivos se resuelven a partir de la raíz del proyecto.
- Los CSV se escriben de forma atómica cuando el formato lo permite.
- Las gráficas usan el backend `Agg`, por lo que no requieren pantalla.
- Las dependencias externas se limitan a matplotlib/numpy para gráficas y
  estadísticas auxiliares.
