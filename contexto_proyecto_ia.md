# Contexto técnico de SIPOTDA

## 1. Planteamiento del problema y supuestos

### 1.1 Problema

SIPOTDA resuelve una planificación logística de vehículo único sobre una cuadrícula configurable, por defecto de 12×12. La operación parte de un inicio `S`, visita un conjunto de entregas `E = {E1, ..., En}` y termina en un destino `G`. Cada entrega tiene demanda, tarifa y prioridad; cada celda tiene un costo positivo y puede ser transitable u obstáculo. La decisión principal es el orden de visita de las entregas y, para cada tramo, la ruta de menor costo entre dos puntos obligatorios. El sistema también analiza un competidor mediante teoría de juegos y un subproblema adversario de asignación de recursos.

El proyecto es una aplicación de escritorio, no un servicio web ni un solver de propósito general. La interfaz permite editar el escenario, ejecutar todos los módulos, revisar resultados, exportar CSV y guardar la planificación final.

### 1.2 Decisiones que modela el sistema

- Orden de visita: permutación exacta de los identificadores de entrega.
- Ruta por tramo: camino desde el inicio hasta la primera entrega, entre entregas consecutivas y desde la última entrega hasta el destino.
- Plan final: selección de la mejor solución válida y de la estrategia recomendada.
- Análisis estratégico: matriz de pagos empresa/competidor, mejores respuestas, dominancia y equilibrios de Nash puros.
- Análisis adversario: línea principal de acciones de la empresa (MAX) y del competidor (MIN), con Minimax y poda alfa-beta.

### 1.3 Entidades y representación

- `Celda`: costo de entrada, transitabilidad, tipo y etiqueta visual. El costo debe ser finito y estrictamente positivo.
- `Entrega`: `id`, `nombre`, `fila`, `columna`, `demanda`, `tarifa`, `prioridad`.
- `Recurso`: `nombre`, `cantidad`, `unidad`, `consumo_por_paso`, `descripcion`.
- `Escenario`: cuadrícula, inicio, destino, entregas, obstáculos, recursos, competidor, restricciones de movimiento, tarifa y metadatos.
- `Tramo`: origen, destino, camino, costo, pasos y algoritmo.
- `Solucion`: orden de entregas, tramos, costo total, pasos, consumos, carga, validez, violaciones, penalización y detalle.
- `ResultadoEjecucion`: resultado trazable de una ejecución con identificador, escenario, algoritmo, semilla, parámetros, costo, tiempo, métricas y solución.

### 1.4 Reglas de movimiento y costo

Las direcciones rectas son siempre `(-1,0)`, `(1,0)`, `(0,-1)` y `(0,1)`. Las diagonales se agregan solo si `permitir_diagonal` es verdadero. Nunca se atraviesa una celda no transitable ni se sale de la cuadrícula.

El costo de una arista hacia la celda destino `(f,c)` es:

```text
costo_arista = costo_celda(f,c) * factor_costo
```

Si el movimiento es diagonal, se multiplica además por `factor_costo_diagonal`, cuyo valor predeterminado es `sqrt(2)`. El modo `pasos` asigna `1.0` por movimiento y sirve para minimizar el número de pasos; el modo `costo` usa el costo real de la celda destino.

La heurística geométrica usa distancia Manhattan sin diagonal y distancia octile con diagonal:

```text
sin diagonal: h = (|df| + |dc|) * costo_minimo_transitable * factor_costo
con diagonal: h = (max(df,dc) + (sqrt(2)-1) * min(df,dc))
                * costo_minimo_transitable * factor_costo
```

En el modo `pasos`, la heurística omite el costo mínimo. La implementación está en `modelos/escenario.py:209-274`.

### 1.5 Recursos y factibilidad

Los recursos obligatorios son `combustible`, `capacidad`, `tiempo` y `presupuesto`. En el modelo actual:

- `combustible_consumido = pasos_totales * consumo_por_paso("combustible")`.
- `tiempo_consumido = pasos_totales * consumo_por_paso("tiempo")`.
- `presupuesto_consumido = costo_total`.
- `carga_maxima = suma de la demanda de todas las entregas`.

Una solución es válida si contiene todos los tramos obligatorios, no supera capacidad, combustible, tiempo ni presupuesto, y no tiene tramos sin ruta. La comprobación se implementa en `construir_solucion` (`algoritmos/comun.py:129-232`).

La capacidad se compara contra la demanda total, no contra la carga transportada en cada tramo. No hay recogidas, devoluciones ni consumo variable de capacidad por parada.

### 1.6 Función objetivo

El costo real de una solución es la suma de los costos de sus tramos. Las metaheurísticas minimizan el costo objetivo:

```text
costo_objetivo = costo_total + penalizacion
```

Si la solución es inválida, la penalización base es:

```text
PENALIZACION_BASE = 1_000_000.0
penalizacion = max(penalizacion_actual,
                   PENALIZACION_BASE + 1_000 * numero_violaciones
                   + 100 * exceso_de_recursos)
```

`exceso_de_recursos` es el mayor exceso entre presupuesto, combustible y tiempo, con mínimo cero. La fórmula está en `modelos/solucion.py:9` y `algoritmos/comun.py:217-231`.

### 1.7 Formulación resumida

```text
Entradas:
  cuadrícula F x C, costo c(i,j) > 0, transitabilidad t(i,j)
  inicio S, destino G, entregas E con demanda y tarifa
  recursos R = (combustible, capacidad, tiempo, presupuesto)
  competidor con factor_costo y factor_presupuesto

Variables:
  pi = permutación de E
  p_k = camino válido para cada tramo k de la secuencia S -> pi -> G

Objetivo:
  minimizar J(pi) = suma_k costo(p_k) + penalización

Restricciones:
  pi contiene exactamente todos los ids de E
  p_k solo usa celdas transitables y dentro de la cuadrícula
  suma de demandas <= capacidad
  pasos_totales * consumo_combustible <= combustible
  pasos_totales * consumo_tiempo <= tiempo
  costo_total <= presupuesto
```

Para el escenario predeterminado de cinco entregas, `validar_factibilidad` explora las `5! = 120` permutaciones y encuentra el óptimo del modelo con costo `37.8` y orden `[4, 2, 5, 1, 3]`. Para más de siete entregas usa muestreo reproducible, por lo que deja de ser una prueba exhaustiva.

### 1.8 Supuestos y alcance

- Un solo vehículo y un solo depósito de inicio.
- Entregas estáticas, demanda determinista y tarifa conocida.
- Sin ventanas de tiempo, tiempos de servicio, tráfico dinámico ni demanda estocástica.
- Sin múltiples vehículos, múltiples depósitos ni reabastecimiento en ruta.
- La prioridad de una entrega se almacena, pero no se usa en la función objetivo ni en el orden.
- El competidor y el adversario son modelos analíticos del escenario, no una simulación de mercado real.
- La cuadrícula y los costos son datos sintéticos o ingresados manualmente; no hay integración con mapas reales.

## 2. Tecnologías, arquitectura y esquemas de datos

### 2.1 Stack técnico

| Componente | Uso |
|---|---|
| Python 3.10+ | Lenguaje de implementación; probado con Python 3.14.5 |
| Tkinter 8.6 | Interfaz de escritorio |
| matplotlib >= 3.8 | Gráficas con backend `Agg`, sin necesidad de pantalla |
| numpy >= 1.26 | Dependencia declarada para cálculo auxiliar |
| Biblioteca estándar | `heapq`, `itertools`, `random`, `statistics`, `csv`, `json`, `threading`, `queue`, `tempfile`, `dataclasses` |

No se usan bibliotecas externas de optimización, solvers, OR-Tools, SciPy ni frameworks de machine learning. Los notebooks de `ejemplos/` son material de referencia y no se importan en tiempo de ejecución. Dependencias declaradas en `requirements.txt`.

Comandos principales:

```powershell
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s pruebas -v
```

### 2.2 Arquitectura por capas

```text
main.py
  -> interfaz/
       -> experimentos/ejecutar_experimentos.py
            -> algoritmos/
                 -> modelos/
            -> gestion_archivos/
            -> configuracion/parametros.json
            -> escenarios/*.json
            -> resultados/csv
            -> resultados/graficas
            -> resultados/planificacion_final.json
```

La lógica de negocio no depende de Tkinter. `modelos/` contiene entidades y validación estructural; `algoritmos/` implementa búsqueda y optimización; `experimentos/` orquesta, mide y genera artefactos; `gestion_archivos/` concentra persistencia y errores; `interfaz/` solo presenta y captura datos.

### 2.3 Módulos y responsabilidades

| Ruta | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada; crea `VentanaPrincipal` y ejecuta `mainloop()` |
| `modelos/escenario.py` | Cuadrícula, vecinos, heurística, validación, serialización |
| `modelos/solucion.py` | `Tramo`, `Solucion`, costo objetivo y penalización |
| `modelos/resultados.py` | `ResultadoEjecucion`, formato CSV y columnas estables |
| `algoritmos/comun.py` | Normalización, evaluación, planificación y caché de tramos |
| `algoritmos/registro.py` | Registro de algoritmos y despacho unificado |
| `algoritmos/busqueda_heuristica/astar.py` | A* sobre la cuadrícula |
| `algoritmos/busqueda_heuristica/greedy.py` | Greedy Best-First guiado solo por `h(n)` |
| `algoritmos/busqueda_local/hill_climbing.py` | Hill Climbing 2-swap y reinicios |
| `algoritmos/metaheuristicas/recocido_simulado.py` | Recocido con enfriamiento geométrico |
| `algoritmos/metaheuristicas/algoritmo_genetico.py` | GA con OX, torneo, mutación y elitismo |
| `algoritmos/teoria_juegos/juego_estrategico.py` | Matriz de pagos, Nash y dominancia |
| `algoritmos/busqueda_adversaria/modelo_adversario.py` | Estado, acciones, transiciones y utilidad |
| `algoritmos/busqueda_adversaria/minimax.py` | Minimax sin poda |
| `algoritmos/busqueda_adversaria/alfa_beta.py` | Minimax con poda alfa-beta |
| `experimentos/ejecutar_experimentos.py` | Flujo completo, artefactos y plan final |
| `experimentos/metricas.py` | Estadísticas y resúmenes desde objetos o CSV |
| `experimentos/graficas.py` | Gráficas generadas exclusivamente desde CSV |
| `experimentos/comparaciones.py` | Comparación y equivalencia Minimax/alfa-beta |
| `gestion_archivos/lector_json.py` | Carga y validación de escenarios y parámetros |
| `gestion_archivos/guardar_escenario.py` | Guardado JSON atómico |
| `gestion_archivos/validar_escenario.py` | Validación de factibilidad por órdenes |
| `gestion_archivos/exportar_resultados.py` | CSV, plan JSON y matriz de juego |
| `gestion_archivos/lector_csv.py` | Importación/exportación de cuadrículas CSV |
| `interfaz/ventana_principal.py` | Menú, toolbar, ejecución asíncrona y estado |
| `interfaz/editor_escenario.py` | Edición visual de la cuadrícula |
| `interfaz/panel_configuracion.py` | Recursos, competidor, algoritmos y experimentos |
| `interfaz/panel_resultados.py` | Pestañas de resultados |
| `interfaz/panel_rutas.py` | Visualización de una solución por vez |
| `interfaz/panel_acciones.py` | Secuencia de acciones del juego y del adversario |
| `pruebas/test_sistema.py` | Pruebas de integración y algoritmos |

### 2.4 Esquema JSON de escenario

El esquema nominal es `sipotda.escenario/1`. Un ejemplo mínimo válido de la estructura es:

```json
{
  "esquema": "sipotda.escenario/1",
  "id": "mini_3x3",
  "nombre": "Ejemplo mínimo",
  "filas": 3,
  "columnas": 3,
  "inicio": [0, 0],
  "destino": [2, 2],
  "entregas": [
    {
      "id": 1,
      "nombre": "E1",
      "fila": 0,
      "columna": 2,
      "demanda": 2.0,
      "tarifa": 60.0,
      "prioridad": 1
    },
    {
      "id": 2,
      "nombre": "E2",
      "fila": 1,
      "columna": 1,
      "demanda": 2.0,
      "tarifa": 60.0,
      "prioridad": 1
    },
    {
      "id": 3,
      "nombre": "E3",
      "fila": 2,
      "columna": 0,
      "demanda": 2.0,
      "tarifa": 60.0,
      "prioridad": 1
    }
  ],
  "obstaculos": [],
  "recursos": {
    "combustible": {
      "nombre": "combustible",
      "cantidad": 100.0,
      "unidad": "unidades",
      "consumo_por_paso": 1.0,
      "descripcion": "Consumo lineal por paso"
    },
    "capacidad": {
      "nombre": "capacidad",
      "cantidad": 10.0,
      "unidad": "unidades",
      "consumo_por_paso": 0.0,
      "descripcion": "Capacidad total"
    },
    "tiempo": {
      "nombre": "tiempo",
      "cantidad": 100.0,
      "unidad": "pasos",
      "consumo_por_paso": 1.0,
      "descripcion": "Tiempo por paso"
    },
    "presupuesto": {
      "nombre": "presupuesto",
      "cantidad": 100.0,
      "unidad": "monetarias",
      "consumo_por_paso": 0.0,
      "descripcion": "Costo total permitido"
    }
  },
  "competidor": {
    "nombre": "Competidor",
    "factor_costo": 1.0,
    "factor_presupuesto": 1.0,
    "celdas_bloqueadas": [],
    "descripcion": "Competidor configurable"
  },
  "restricciones": {
    "permitir_diagonal": false,
    "factor_costo_diagonal": 1.414213562,
    "profundidad_adversaria": 4
  },
  "tarifa_por_unidad": 60.0,
  "meta": {
    "autor": "Proyecto SIPOTDA",
    "notas": "Ejemplo mínimo válido"
  },
  "costos": [
    [1.0, 1.0, 1.0],
    [1.0, 1.5, 1.0],
    [1.0, 1.0, 1.0]
  ]
}
```

| Campo | Tipo | Obligatorio | Observación |
|---|---|---|---|
| `esquema` | string | No | Se escribe al guardar; el cargador no impone la versión |
| `id` | string | No | Por defecto `"escenario"` |
| `nombre` | string | No | Por defecto `"Escenario logístico"` |
| `filas`, `columnas` | int | Sí | Deben ser positivas; mínimo validado 2×2 |
| `inicio`, `destino` | `[fila, columna]` | Sí | Deben estar dentro de la cuadrícula |
| `entregas` | lista de objetos | No | Validación exige al menos 3 |
| `obstaculos` | lista de pares | No | No pueden ocupar posiciones de elementos |
| `recursos` | objeto o lista | No | Validación exige los cuatro recursos |
| `competidor` | objeto | No | Se normaliza con valores por defecto |
| `restricciones` | objeto | No | `permitir_diagonal` y `factor_costo_diagonal` se extraen como atributos |
| `tarifa_por_unidad` | float | No | Por defecto `60.0` |
| `meta` | objeto | No | Metadatos libres; el guardado agrega `ultima_modificacion` |
| `costos` | matriz F×C | Sí, si no hay `celdas` | Costos positivos y finitos |
| `celdas` | matriz de objetos | Alternativa a `costos` | Cada celda puede incluir `costo`, `transitable`, `tipo`, `etiqueta` |

La carga acepta un contenedor `{"escenario": {...}}` o el objeto de escenario en la raíz. `Escenario.desde_dict` exige `filas`, `columnas`, `inicio` y `destino`; después acepta `celdas` o `costos` (`modelos/escenario.py:603-683`).

### 2.5 Escenarios incluidos y caracterización técnica

El proyecto incluye cuatro configuraciones oficiales de escenarios en formato JSON ubicados en la carpeta `escenarios/`. Cada uno modela distintas condiciones topológicas, presiones competitivas y restricciones de recursos.

#### Tabla comparativa general de escenarios

| Archivo | `id` interno | Nombre descriptivo | Tamaño | Inicio ($S$) → Destino ($G$) | Entregas (Demanda) | Recursos (Comb / Cap / Tmp / Pres) | Obstáculos | Competidor (Nombre, Costo / Presup.) | Celdas bloqueadas comp. | Tarifa base | Factibilidad / Propósito |
|---|---|---|:---:|:---:|:---:|:---:|:---:|---|:---:|:---:|---|
| `escenario_predeterminado.json` | `logistica_12x12` | Red metropolitana base | 12×12 | `(0,0) → (11,11)` | 5 (22.0) | 250.0 / 30.0 / 300.0 / 400.0 | 13 | TransLog (1.25 / 1.15) | 3 `[(7,8),(7,9),(8,8)]` | 60.0 | **Factible.** Escenario base de referencia. Óptimo global $37.8$. |
| `escenario_alternativo.json` | `corredor_costero` | Corredor costero alternativo | 12×12 | `(11,0) → (0,11)` | 4 (16.0) | 220.0 / 25.0 / 260.0 / 340.0 | 16 | RutaSur (1.20 / 1.10) | 3 `[(4,5),(4,6),(5,5)]` | 55.0 | **Factible.** Flujo diagonal inverso (SO → NE) y menor tarifa. |
| `escenario_estrecho.json` | `pasillo_estrecho` | Pasillo urbano estrecho | 12×12 | `(0,11) → (11,0)` | 4 (15.0) | 180.0 / 22.0 / 220.0 / 280.0 | 14 | LogiNorte (1.30 / 1.20) | 3 `[(6,7),(7,7),(8,7)]` | 70.0 | **Factible.** Recursos ajustados, cuello de botella y alta competencia. |
| `escenario_bloqueado.json` | `bloqueado` | Escenario sin solución (demostración) | 12×12 | `(0,0) → (11,11)` | 3 (6.0) | 200.0 / 10.0 / 200.0 / 300.0 | 12 | BloqueoTotal (1.00 / 1.00) | 0 `[]` | 60.0 | **Infactible (Prueba negativa).** Barrera horizontal completa en fila 6. |

#### Análisis técnico y particularidades por escenario

1. **`escenario_predeterminado.json` (`id`: `logistica_12x12`)**
   - **Nombre:** Red metropolitana base.
   - **Dimensiones y Topología:** Cuadrícula de 12×12. Inicio $S = (0,0)$ (esquina superior izquierda), Destino $G = (11,11)$ (esquina inferior derecha).
   - **Entregas (5):**
     1. *Centro Norte* en `(2,9)` | Demanda: 5.0 | Tarifa: 60.0 | Prioridad: 1
     2. *Zona Industrial* en `(5,4)` | Demanda: 4.0 | Tarifa: 60.0 | Prioridad: 1
     3. *Puerto Este* en `(8,10)` | Demanda: 6.0 | Tarifa: 60.0 | Prioridad: 1
     4. *Depósito Sur* en `(10,2)` | Demanda: 3.0 | Tarifa: 60.0 | Prioridad: 1
     5. *Mercado Central* en `(4,7)` | Demanda: 4.0 | Tarifa: 60.0 | Prioridad: 1
     - **Demanda acumulada total:** 22.0 unidades.
   - **Recursos configurados:** Combustible: 250.0 unidades (1.0/paso), Capacidad: 30.0 unidades, Tiempo: 300.0 pasos (1.0/paso), Presupuesto: 400.0 unidades monetarias.
   - **Obstáculos (13 celdas):** `(1,3), (2,3), (2,11), (3,3), (3,11), (4,3), (5,8), (5,9), (5,10), (7,6), (8,6), (9,6), (10,6)`.
   - **Competidor (`TransLog`):** Factor costo = 1.25, Factor presupuesto = 1.15. Bloquea 3 celdas en el corredor central: `(7,8), (7,9), (8,8)`.
   - **Restricciones de movimiento:** Diagonal no permitida (`permitir_diagonal = false`), factor diagonal = 1.414213562, profundidad adversaria = 4.
   - **Propósito y particularidad:** Sirve como escenario base de referencia y benchmark estándar para el sistema. Es totalmente factible y posee un óptimo global de costo $37.8$ para el orden de entregas `[4, 2, 5, 1, 3]` ($E4 \rightarrow E2 \rightarrow E5 \rightarrow E1 \rightarrow E3$), verificado exhaustivamente sobre las $5! = 120$ permutaciones posibles.

2. **`escenario_alternativo.json` (`id`: `corredor_costero`)**
   - **Nombre:** Corredor costero alternativo.
   - **Dimensiones y Topología:** Cuadrícula de 12×12. Inicio $S = (11,0)$ (esquina inferior izquierda), Destino $G = (0,11)$ (esquina superior derecha).
   - **Entregas (4):**
     1. *Terminal Pesquero* en `(9,3)` | Demanda: 4.0 | Tarifa: 55.0 | Prioridad: 1
     2. *Plaza Mayor* en `(6,8)` | Demanda: 5.0 | Tarifa: 55.0 | Prioridad: 1
     3. *Aduana Norte* en `(3,2)` | Demanda: 3.0 | Tarifa: 55.0 | Prioridad: 1
     4. *Muelle viejo* en `(1,9)` | Demanda: 4.0 | Tarifa: 55.0 | Prioridad: 1
     - **Demanda acumulada total:** 16.0 unidades.
   - **Recursos configurados:** Combustible: 220.0, Capacidad: 25.0, Tiempo: 260.0, Presupuesto: 340.0.
   - **Obstáculos (16 celdas):** `(2,3), (2,7), (2,8), (2,9), (2,10), (3,3), (4,3), (5,1), (5,2), (5,3), (7,4), (8,4), (8,9), (9,4), (9,9), (10,9)`.
   - **Competidor (`RutaSur`):** Factor costo = 1.20, Factor presupuesto = 1.10. Bloquea 3 celdas: `(4,5), (4,6), (5,5)`.
   - **Restricciones de movimiento:** Diagonal no permitida (`permitir_diagonal = false`), factor diagonal = 1.414213562, profundidad adversaria = 4.
   - **Propósito y particularidad:** Prueba la flexibilidad de los algoritmos ante un flujo invertido (de Suroeste a Noreste) y un conjunto de 4 entregas con tarifa reducida ($55.0$). Evalúa cómo los planificadores sortean 16 obstáculos distribuidos en sectores muelles/costeros.

3. **`escenario_estrecho.json` (`id`: `pasillo_estrecho`)**
   - **Nombre:** Pasillo urbano estrecho.
   - **Dimensiones y Topología:** Cuadrícula de 12×12. Inicio $S = (0,11)$ (esquina superior derecha), Destino $G = (11,0)$ (esquina inferior izquierda).
   - **Entregas (4):**
     1. *Farmacia Este* en `(2,8)` | Demanda: 3.0 | Tarifa: 70.0 | Prioridad: 1
     2. *Taller Central* en `(5,5)` | Demanda: 4.0 | Tarifa: 70.0 | Prioridad: 1
     3. *Bodega Oeste* en `(8,3)` | Demanda: 3.0 | Tarifa: 70.0 | Prioridad: 1
     4. *Clínica Sur* en `(10,7)` | Demanda: 5.0 | Tarifa: 70.0 | Prioridad: 1
     - **Demanda acumulada total:** 15.0 unidades.
   - **Recursos configurados:** Combustible: 180.0, Capacidad: 22.0, Tiempo: 220.0, Presupuesto: 280.0.
   - **Obstáculos (14 celdas):** `(2,4), (3,4), (4,4), (5,4), (5,6), (5,7), (5,8), (5,9), (5,10), (6,4), (9,1), (9,2), (9,3), (9,4)`.
   - **Competidor (`LogiNorte`):** Factor costo = 1.30, Factor presupuesto = 1.20. Bloquea 3 celdas: `(6,7), (7,7), (8,7)`.
   - **Restricciones de movimiento:** Diagonal no permitida (`permitir_diagonal = false`), factor diagonal = 1.414213562, profundidad adversaria = 4.
   - **Propósito y particularidad:** Modelo de estrés con recursos muy ajustados (combustible 180, tiempo 220, presupuesto 280) y la mayor agresividad del competidor (`factor_costo = 1.30`). Los obstáculos forman un "pasillo urbano estrecho", obligando a los algoritmos a encontrar desvíos eficientes en espacios reducidos. Tarifa mayor ($70.0$).

4. **`escenario_bloqueado.json` (`id`: `bloqueado`)**
   - **Nombre:** Escenario sin solución (demostración).
   - **Dimensiones y Topología:** Cuadrícula de 12×12. Inicio $S = (0,0)$, Destino $G = (11,11)$.
   - **Entregas (3):**
     1. *E1* en `(1,5)` | Demanda: 2.0 | Tarifa: 60.0 | Prioridad: 1
     2. *E2* en `(5,5)` | Demanda: 2.0 | Tarifa: 60.0 | Prioridad: 1
     3. *E3* en `(9,5)` | Demanda: 2.0 | Tarifa: 60.0 | Prioridad: 1
     - **Demanda acumulada total:** 6.0 unidades.
   - **Recursos configurados:** Combustible: 200.0, Capacidad: 10.0, Tiempo: 200.0, Presupuesto: 300.0.
   - **Obstáculos (12 celdas):** Todas las 12 celdas de la fila 6 completas: `(6,0), (6,1), (6,2), (6,3), (6,4), (6,5), (6,6), (6,7), (6,8), (6,9), (6,10), (6,11)`.
   - **Competidor (`BloqueoTotal`):** Factor costo = 1.00, Factor presupuesto = 1.00. Celdas bloqueadas: Ninguna (`[]`).
   - **Restricciones de movimiento:** Diagonal no permitida (`permitir_diagonal = false`), factor diagonal = 1.414213562.
   - **Propósito y particularidad:** Escenario de prueba negativa (infactible deliberado). La fila 6 dividida totalmente por obstáculos crea una barrera física infranqueable entre el sector norte ($S$, $E1$, $E2$) y el sector sur ($E3$, $G$). Sirve para verificar la capacidad del sistema para detectar y reportar inalcanzabilidad (`_puntos_inalcanzables`) sin lanzar excepciones no controladas ni quedar atrapado en ciclos infinitos.

### 2.6 Parámetros experimentales

El archivo `configuracion/parametros.json` contiene:

```json
{
  "hill_climbing": {
    "max_iteraciones": 500,
    "permitir_mesetas": false,
    "max_mesetas": 20
  },
  "recocido_simulado": {
    "temperatura_inicial": 50.0,
    "temperatura_final": 0.01,
    "enfriamiento": 0.95,
    "iteraciones_por_temperatura": 15,
    "max_iteraciones": 2500
  },
  "algoritmo_genetico": {
    "tamano_poblacion": 30,
    "generaciones": 80,
    "prob_cruza": 0.85,
    "prob_mutacion": 0.2,
    "elitismo": 2,
    "tamano_torneo": 3,
    "max_evaluaciones": 15000
  },
  "experimentos": {
    "repeticiones_metaheuristicas": 20,
    "num_inicios_hill": 10,
    "semilla_base": 2026,
    "profundidades_adversarias": [2, 4, 6]
  }
}
```

Hay una diferencia entre los valores de respaldo de `algoritmos/registro.py` y los valores de `PARAMETROS_PREDETERMINADOS` en `experimentos/ejecutar_experimentos.py`: el registro usa por defecto 20 iteraciones por temperatura, 5000 iteraciones máximas, población 40, 100 generaciones y 20000 evaluaciones; el flujo experimental usa 15, 2500, 30, 80 y 15000, respectivamente. Para los experimentos del proyecto manda la configuración de `PARAMETROS_PREDETERMINADOS` y `configuracion/parametros.json`.

### 2.7 Estructuras internas

`ResultadoBusqueda` (`algoritmos/comun.py:21-45`) es el resultado de buscar un tramo:

```text
exito, camino, costo, pasos, nodos_expandidos,
nodos_generados, iteraciones, mensaje, algoritmo
```

`ResultadoEjecucion` (`modelos/resultados.py:19-104`) es el resultado experimental:

```text
id_ejecucion, id_escenario, nombre_escenario, algoritmo, semilla,
parametros, exito, mensaje, costo, tiempo_ejecucion,
metricas, solucion, fecha
```

`id_ejecucion` se construye como `primeros_12_caracteres_del_algoritmo + "-" + uuid4[:10]`. `costo` se inicializa en `inf` y se serializa como `None` en JSON y como cadena vacía en CSV cuando no hay solución.

`Solucion` (`modelos/solucion.py:55-164`) contiene:

```text
orden_entregas, rutas, costo_total, pasos,
combustible_consumido, tiempo_consumido, presupuesto_consumido,
carga_maxima, valida, violaciones, penalizacion, detalle
```

Propiedades relevantes:

- `costo_objetivo = costo_total + penalizacion`.
- `longitud_ruta = suma de tramo.pasos`.
- `ruta_coordenadas` concatena los caminos y evita duplicar el punto de unión.

### 2.8 CSV de resultados

`modelos/resultados.py:107-131` define las columnas estables:

```text
id_ejecucion
fecha
id_escenario
nombre_escenario
algoritmo
semilla
parametros
exito
mensaje
costo
costo_objetivo
solucion_valida
tiempo_ejecucion
nodos_expandidos
nodos_generados
nodos_visitados
nodos_podados
evaluaciones
iteraciones
longitud_ruta
orden_entregas
historial_costos
metricas_extra
solucion_json
```

`a_fila_csv()` aplana la solución y serializa como JSON compacto `parametros`, `orden_entregas`, `historial_costos`, `metricas_extra` y `solucion_json`. Las columnas no aplicables quedan vacías, no en cero.

### 2.9 JSON de planificación final

`resultados/planificacion_final.json` tiene estas claves de primer nivel:

```text
id_plan, fecha, escenario_id, nombre_escenario, plan_valido,
orden_entregas, nombres_entregas, rutas, ruta_coordenadas,
costo_total, longitud_ruta, pasos, recursos_utilizados,
restricciones, validaciones, riesgos_competidor,
estrategia_recomendada, fuentes, justificacion
```

Cada elemento de `rutas` contiene:

```text
origen_nombre, destino_nombre, origen, destino,
camino, costo, pasos, algoritmo
```

`fuentes` contiene `solucion_base`, `mejores_por_algoritmo`, `ids_ejecucion`, `juego`, `minimax` y `alfa_beta`. La planificación no guarda una solución de juego como ruta: usa la mejor solución válida de los algoritmos y añade la recomendación estratégica y el riesgo adversario como metadatos.

### 2.10 Persistencia y validación

- `guardar_json` y `guardar_planificacion_json` escriben en un temporal con `tempfile.mkstemp` y reemplazan con `os.replace`.
- `guardar_escenario` ejecuta `escenario.validar()` antes de escribir y actualiza `meta["ultima_modificacion"]`.
- `ErrorArchivo`, `ErrorSobrescritura` y `ErrorValidacion` están en `gestion_archivos/errores.py`. `ErrorValidacion` conserva la lista `.errores`.
- El cargador JSON informa línea y columna con `JSONDecodeError`.
- `validar_factibilidad` valida estructura y luego explora órdenes. Hasta 7 entregas usa permutaciones exhaustivas; con más entregas usa muestreo reproducible con semilla 12345 y `max_muestras=1500`.
- La importación CSV interpreta `S`, `G`, `E`, `E1`, `#`/`X`, números positivos y variantes con costo `S:1.5` o `E1:2`. Las entregas importadas reciben demanda 4.0 y tarifa 60.0; los recursos son valores fijos (300/300/400 y capacidad máxima entre 30 y la demanda total). Es una importación de cuadrícula, no un round-trip completo del escenario.

### 2.11 Interfaz y modelo de ejecución

- Pestaña `Escenario`: editor de cuadrícula con herramientas de selección, inicio, destino, entrega y obstáculo; configuración debajo.
- Pestaña `Resultados`: `Resumen`, `Ejecuciones`, `Rutas`, `Gráficas`, `Acciones`, `Juego estratégico`, `Adversaria`, `Plan final`.
- `Ejecutar todos los módulos` valida configuración, estructura y factibilidad, clona el escenario y los parámetros, y lanza `ejecutar_todo` en un hilo de trabajo.
- La comunicación con Tkinter se hace con `queue.Queue` y `after(120, ...)`; los controles se deshabilitan durante la tarea.
- Si un módulo falla, `ejecutar_todo` registra el error en `errores` y conserva los resultados de los demás. Si falla el juego, no se construye el plan; si falla otro módulo, el plan puede construirse con los resultados válidos.
- Modificar el escenario o aplicar configuración descarta los resultados anteriores.

## 3. Diseño real de los algoritmos

### 3.1 Flujo común de evaluación

Todas las metaheurísticas optimizan una permutación de ids de entrega, no directamente una secuencia de coordenadas. `normalizar_orden` exige que el orden sea una permutación exacta de los ids; si faltan, sobran o se repiten, lanza `ValueError` (`algoritmos/comun.py:48-64`).

`PlanificadorRutas` (`algoritmos/comun.py:303-400`) evalúa un orden así:

```text
puntos = [("Inicio", escenario.inicio)]
puntos += [(nombre_i, posicion_i) para cada entrega en el orden]
puntos += [("Destino", escenario.destino)]

para cada par consecutivo:
    tramo = buscador(escenario, origen, destino,
                     evitar, factor_costo, modo)
    si no hay tramo: solución inválida y fin
    agregar Tramo

solución = construir_solucion(escenario, orden, tramos, algoritmo)
```

Por defecto el buscador es A*. La caché es un diccionario indexado por `(origen, destino)`; como cada instancia de `PlanificadorRutas` tiene fijo `evitar`, `factor_costo` y `modo`, la clave es suficiente dentro de esa instancia. La caché evita repetir búsquedas idénticas entre evaluaciones de la misma metaheurística.

`PlanificadorRutas.metricas_cache()` devuelve:

```text
nodos_expandidos_planificador
nodos_generados_planificador
busquedas_realizadas
tramos_en_cache
```

Estas métricas se agregan a los resultados de las metaheurísticas. No se cuentan como evaluaciones de la función objetivo: la evaluación se cuenta una vez por individuo u orden evaluado por el algoritmo.

### 3.2 A*

Implementación en `algoritmos/busqueda_heuristica/astar.py`.

- Frontera: `heapq` de tuplas `(f, g, contador, nodo)`.
- `f = g + h`.
- `g` es el costo real acumulado; `h` es la heurística geométrica.
- `mejor_g` guarda el mejor costo conocido por nodo.
- `padre` reconstruye el camino.
- `cerrados` evita reexpandir el mismo nodo.
- `max_pasos` opcional limita la profundidad.
- `contador` desempata nodos con igual `f` y evita comparar coordenadas.
- Al llegar al objetivo recalcula el costo con `costo_camino` y devuelve camino, costo, pasos y métricas.

```python
heapq.heappush(
    frontera,
    (nuevo_g + h, nuevo_g, next(contador), vecino),
)
```

Con costos positivos y heurística consistente, A* es óptimo. La heurística usa el costo mínimo transitable de toda la cuadrícula. En la configuración predeterminada no hay diagonal, por lo que la distancia Manhattan es una cota inferior válida.

### 3.3 Greedy Best-First

Implementación en `algoritmos/busqueda_heuristica/greedy.py`.

- La frontera se ordena solo por `h(n)`, no por `g(n)`.
- El costo acumulado se arrastra para información, pero no decide la expansión.
- Al llegar al objetivo recalcula el costo real con `costo_camino` para no reportar un costo contaminado por la prioridad heurística.
- Usa un conjunto global `visitados`; es completo en el grafo finito, pero no garantiza optimalidad.

### 3.4 Hill Climbing

Implementación en `algoritmos/busqueda_local/hill_climbing.py`.

- Representación: permutación de ids de entrega.
- Vecindad: todos los intercambios de dos posiciones, generados con `itertools.combinations(range(len(actual)), 2)`.
- Estrategia: mejor vecino; evalúa toda la vecindad y elige el menor `costo_objetivo`.
- Acepta solo mejoras estrictas mayores que `1e-9`.
- `max_iteraciones` limita movimientos aceptados, no vecinos evaluados.
- Si `permitir_mesetas` está activo, acepta movimientos laterales con igual objetivo, sin repetir estados, hasta `max_mesetas`.
- Devuelve el mejor estado encontrado, que con mesetas puede no ser el estado final.
- `reinicios_hill_climbing` ejecuta varios inicios: vecino más cercano, orden inverso, orden natural y permutaciones aleatorias, con semillas derivadas de `semilla_base`.
- El resumen de reinicios usa `statistics.fmean` y `statistics.pstdev`; el resumen general de comparación usa `statistics.stdev`, por lo que la desviación puede diferir entre archivos.

Métricas registradas:

```text
costo_inicial, costo_final, objetivo_final, mejora,
evaluaciones, iteraciones, movimientos_aceptados,
mesetas_exploradas, optimo_local,
historial_costos, historial_objetivos,
orden_inicial, orden_final, solucion_valida, violaciones
```

### 3.5 Recocido simulado

Implementación en `algoritmos/metaheuristicas/recocido_simulado.py`.

- Estado: permutación de entregas.
- Vecino: intercambio aleatorio de dos posiciones (`rng.sample`).
- Aceptación: si `delta <= 0`, acepta; si `delta > 0`, acepta con probabilidad `exp(-delta / T)`.
- Enfriamiento geométrico: `T <- T * alfa`.
- Ciclo: mientras `T > temperatura_final` y `iteraciones < max_iteraciones`, ejecuta `iteraciones_por_temperatura` intentos por temperatura.
- Conserva el mejor estado encontrado, no necesariamente el estado actual.
- Valida `T0 > 0`, `Tf > 0`, `T0 > Tf`, `0 < alfa < 1`, iteraciones positivas.

```python
delta = sol_vecino.costo_objetivo - actual_sol.costo_objetivo
probabilidad = math.exp(-delta / temperatura)
```

Con la configuración del proyecto, el presupuesto máximo es 2500 iteraciones; como se evalúa también el estado inicial, el CSV registra 2501 evaluaciones en las 20 repeticiones.

Métricas registradas:

```text
costo_inicial, costo_final, objetivo_final,
evaluaciones, iteraciones, aceptados, aceptados_peores,
rechazados, temperatura_final_alcanzada,
historial_costos, historial_objetivos, historial_temperaturas,
orden_inicial, orden_final, solucion_valida, violaciones
```

### 3.6 Algoritmo genético

Implementación en `algoritmos/metaheuristicas/algoritmo_genetico.py`.

- Cromosoma: permutación de ids de entrega; evita duplicados y faltantes por construcción.
- Población inicial: vecino más cercano, orden natural, orden inverso, orden inicial si se proporciona y permutaciones aleatorias hasta completar `tamano_poblacion`.
- Selección: torneo de `tamano_torneo` individuos; gana el de mayor aptitud.
- Cruza: Order Crossover (OX). Se eligen dos cortes, se copia el segmento del primer padre y se rellenan las posiciones restantes con los valores no usados del segundo padre en orden circular.
- Mutación: intercambio de dos posiciones con probabilidad `prob_mutacion`.
- Elitismo: los `elitismo` mejores individuos pasan intactos.
- Aptitud: `1 / (1 + max(0, costo_objetivo))`.
- `max_evaluaciones` se comprueba al inicio y al final de cada generación; la población completa de una generación puede evaluarse antes de detenerse.
- La caché de individuos evita recalcular el mismo cromosoma, pero `evaluaciones` cuenta cada solicitud de evaluación, no solo las búsquedas nuevas.

```python
def aptitud(solucion):
    return 1.0 / (1.0 + max(0.0, solucion.costo_objetivo))
```

Métricas registradas:

```text
costo_final, objetivo_final, evaluaciones, iteraciones,
generaciones_ejecutadas, generaciones_solicitadas, poblacion,
historial_costos, historial_promedios, historial_objetivos,
historial_diversidad, diversidad_final,
orden_inicial, orden_final, solucion_valida, violaciones
```

### 3.7 Juego estratégico

Implementación en `algoritmos/teoria_juegos/juego_estrategico.py`.

Jugadores:

- Empresa: maximiza su pago.
- Competidor: maximiza su margen y captura de mercado.

Estrategias de la empresa:

| Estrategia | Modo de ruta | Factor costo | Factor combustible | Factor tiempo | Riesgo | Evita bloqueos |
|---|---|---:|---:|---:|---:|---|
| `ahorro_recursos` | `costo` | 1.00 | 0.85 | 1.10 | 0.18 | No |
| `ruta_rapida` | `pasos` | 1.15 | 1.10 | 0.85 | 0.12 | No |
| `ruta_alternativa` | `costo` | 1.05 | 1.00 | 1.05 | 0.05 | Sí |

Estrategias del competidor:

| Estrategia | Factor costo | Factor combustible | Riesgo | Agresiva | Bloquea |
|---|---|---:|---:|---|---|
| `mantener_disponibilidad` | 1.00 | 1.00 | 0.00 | No | No |
| `encarecer_combustible` | factor del escenario | factor del escenario | 0.06 | Sí | No |
| `bloquear_ruta` | 1.08 | 1.00 | 0.10 | Sí | Sí |

Cálculo de pagos:

```text
ingreso = suma(demanda_i * tarifa_i)

costo_ruta = costo monetario de la ruta planificada
costo_efectivo = costo_ruta * factor_costo_empresa
                 * factor_costo_competidor
                 * factor_presupuesto_competidor

combustible_efectivo = combustible_base
                       * factor_combustible_empresa
                       * factor_combustible_competidor
tiempo_efectivo = tiempo_base * factor_tiempo_empresa

riesgo = riesgo_empresa + riesgo_competidor
excesos = max(0, combustible_efectivo - limite_combustible) * 5
        + max(0, tiempo_efectivo - limite_tiempo) * 5
        + max(0, costo_efectivo - limite_presupuesto) * 2

penalizacion = 120 * riesgo + excesos
si la solución no es válida:
    penalizacion += 500 + 100 * numero_violaciones

pago_empresa = ingreso - costo_efectivo - penalizacion
margen_competidor = 0.22 * ingreso
captura = 0.45 * max(0, costo_efectivo - costo_base)
bono_bloqueo = 90 si el competidor bloquea y hay celdas bloqueadas
castigo = 25 si la acción del competidor es agresiva
pago_competidor = margen_competidor + captura + bono_bloqueo - castigo
```

La ruta base neutral se calcula con A*, orden vecino más cercano y sin bloqueos. La matriz tiene 3×3 = 9 celdas. Para cada celda se planifica una ruta real con la estrategia de la empresa y las celdas a evitar.

Análisis:

- Mejores respuestas de cada jugador para cada acción del rival.
- Dominancia estricta y débil de la empresa y del competidor.
- Equilibrios de Nash puros: pares donde cada acción es mejor respuesta a la otra.
- Recomendación: si hay Nash, el de mayor pago para la empresa; si no, criterio maximin.

Una limitación concreta: en `ruta_rapida`, la ruta se busca en modo `pasos`, pero luego se reconstruye el costo con `costo_camino` sin el factor 1.15 de la estrategia. Por eso el factor de costo de `ruta_rapida` no se refleja en el costo de la ruta de esa celda. Además, si el escenario no define celdas bloqueadas, la acción `bloquear_ruta` no genera un desvío simulado; el código limpia `evitar` y no aplica bono de bloqueo.

### 3.8 Búsqueda adversaria

Implementación en `algoritmos/busqueda_adversaria/modelo_adversario.py`, `minimax.py` y `alfa_beta.py`.

Estado inmutable:

```text
(turno, presupuesto, combustible, reservas, bloqueos,
 riesgo, impacto, historial_max, historial_min)
```

Configuración derivada del escenario:

- `ingreso_base = suma(demanda_i * tarifa_i)`.
- `costo_base_ruta` y `consumo_base_combustible` se calculan con A* y orden vecino más cercano.
- `presupuesto_inicial = max(30, min(60, 0.5 * limite_presupuesto))`.
- `combustible_inicial = limite de combustible del escenario`.
- `limite_turnos = profundidad`; si es impar se incrementa al siguiente par; mínimo 2.

Acciones de MAX:

| Acción | Costo | Combustible | Impacto | Riesgo | Reservas |
|---|---:|---:|---:|---:|---:|
| `asegurar_combustible` | 10 | +15 | 0.00 | -0.04 | 0 |
| `reservar_ruta` | 14 | +5 | -0.02 | -0.06 | +1 |
| `negociar_prioridad` | 8 | 0 | -0.05 | -0.03 | 0 |

Si no hay presupuesto suficiente, se usa `postergar_inversion` con costo 0, impacto +0.02 y riesgo +0.03.

Acciones de MIN:

| Acción | Impacto | Riesgo | Bloqueos |
|---|---:|---:|---:|
| `mantener_disponibilidad` | +0.01 | 0.00 | 0 |
| `encarecer_combustible` | +0.12 | +0.04 | 0 |
| `bloquear_ruta` | +0.06 | +0.06 | +1 |

Función de utilidad de MAX:

```text
costo_operativo = costo_base_ruta * (1 + impacto) + 25 * bloqueos
costo_acciones = presupuesto_inicial - presupuesto
penalizacion_riesgo = 120 * riesgo
valor_reservas = 30 * reservas
valor_combustible = 0.8 * (combustible - combustible_inicial)

utilidad = ingreso_base
           - costo_operativo
           - costo_acciones
           - penalizacion_riesgo
           + valor_reservas
           + valor_combustible
```

Si la búsqueda se corta por profundidad antes de un terminal, se resta `6 * turnos_restantes` como estimación conservadora (`evaluar_estado(..., aproximada=True)`).

Minimax recorre el árbol completo y alterna MAX/MIN. Alfa-beta aplica la misma función, con `alfa` y `beta`; cuando `beta <= alfa`, poda las acciones restantes del nodo. La poda no cambia el valor minimax y los experimentos verifican la equivalencia.

`ResultadoAdversario` registra:

```text
algoritmo, escenario_id, nombre_escenario, profundidad,
valor_minimax, mejor_accion, linea_principal,
nodos_visitados, nodos_podados, tiempo_ejecucion,
exito, mensaje, estado_raiz, estado_final,
configuracion, metricas
```

### 3.9 Integración de algoritmos y plan

`ejecutar_todo` (`experimentos/ejecutar_experimentos.py:378-521`) ejecuta en secuencia:

1. Heurísticas Greedy y A*.
2. Hill Climbing con reinicios.
3. Recocido simulado y algoritmo genético con semillas pareadas.
4. Juego estratégico.
5. Búsqueda adversaria con Minimax y alfa-beta.
6. Exportación de resultados, resumen y gráficas.
7. Construcción del plan final si el juego terminó.

La lista `resultados` contiene solo heurísticas, Hill Climbing y metaheurísticas. Con la configuración completa son 52 ejecuciones: 2 heurísticas, 10 de Hill Climbing, 20 de recocido y 20 del genético. El juego y la adversaria se guardan en campos separados (`juego`, `adversaria`). El plan final se construye con la mejor solución válida por costo, con desempate por nombre de algoritmo:

```python
mejor = min(validos, key=lambda r: (r.costo, r.algoritmo))
```

Las rutas del plan provienen de esa solución. La estrategia y el riesgo no alteran las rutas del plan: se agregan como recomendación y metadatos. El nivel de riesgo se clasifica así:

```text
alto:  riesgo >= 0.16 o bloqueos >= 2
medio: riesgo >= 0.08 o bloqueos >= 1
bajo:  en otro caso
```

La referencia adversaria del plan es el resultado alfa-beta de mayor profundidad; la referencia Minimax también se guarda, pero el plan usa alfa-beta para el riesgo.

## 4. Parámetros experimentales y procedimiento

### 4.1 Configuración usada

| Sección | Parámetro | Valor |
|---|---|---:|
| `hill_climbing` | `max_iteraciones` | 500 |
| `hill_climbing` | `permitir_mesetas` | `false` |
| `hill_climbing` | `max_mesetas` | 20 |
| `recocido_simulado` | `temperatura_inicial` | 50.0 |
| `recocido_simulado` | `temperatura_final` | 0.01 |
| `recocido_simulado` | `enfriamiento` | 0.95 |
| `recocido_simulado` | `iteraciones_por_temperatura` | 15 |
| `recocido_simulado` | `max_iteraciones` | 2500 |
| `algoritmo_genetico` | `tamano_poblacion` | 30 |
| `algoritmo_genetico` | `generaciones` | 80 |
| `algoritmo_genetico` | `prob_cruza` | 0.85 |
| `algoritmo_genetico` | `prob_mutacion` | 0.2 |
| `algoritmo_genetico` | `elitismo` | 2 |
| `algoritmo_genetico` | `tamano_torneo` | 3 |
| `algoritmo_genetico` | `max_evaluaciones` | 15000 |
| `experimentos` | `repeticiones_metaheuristicas` | 20 |
| `experimentos` | `num_inicios_hill` | 10 |
| `experimentos` | `semilla_base` | 2026 |
| `experimentos` | `profundidades_adversarias` | `[2, 4, 6]` |

Las semillas de las repeticiones se generan con `random.Random(semilla_base)`, de modo que las mismas condiciones producen las mismas semillas. Para Hill Climbing se generan `num_inicios` semillas; para recocido y genético se generan `repeticiones` semillas y se usan las mismas para ambos algoritmos en cada repetición.

### 4.2 Procedimiento experimental

- Heurísticas: una ejecución de Greedy y una de A* por escenario, con el orden natural de las entregas.
- Hill Climbing: 10 inicios por escenario, semilla base 2026, 500 movimientos aceptados como máximo.
- Metaheurísticas: 20 repeticiones de recocido y 20 de genético, con semillas pareadas.
- Adversaria: profundidades 2, 4 y 6; en cada una se ejecutan Minimax y alfa-beta con la misma configuración.
- Juego: una matriz 3×3 por escenario.
- Plan: se construye solo si existen soluciones válidas y el juego terminó; si el juego falla, se registra el error y el plan queda en `None`.

La ejecución completa en la interfaz usa los valores anteriores. Para reducir el costo computacional, la prueba de integración usa 1 repetición, 2 inicios, profundidad `[2]` y sin gráficas; produce 6 resultados (Greedy, A*, 2 Hill Climbing, recocido y genético).

### 4.3 Resultados registrados del escenario predeterminado

La ejecución real registrada en `resultados/csv/` produjo:

| Algoritmo | Ejecuciones | Éxitos | Mejor costo | Costo promedio | Desv. costo | Mediana | Tiempo prom. (s) | Evaluaciones prom. | Nodos expandidos prom. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Greedy Best-First | 1 | 1 | 83.8 | 83.8 | 0.0 | 83.8 | 0.0022057 | 0.0 | 82.0 |
| A* | 1 | 1 | 62.9 | 62.9 | 0.0 | 62.9 | 0.0050175 | 0.0 | 287.0 |
| Hill Climbing | 10 | 10 | 37.8 | 38.4 | 1.0392305 | 37.8 | 0.0025231 | 27.0 | 0.0 |
| Recocido Simulado | 20 | 20 | 37.8 | 37.8 | 0.0 | 37.8 | 0.0659462 | 2501.0 | 0.0 |
| Algoritmo Genético | 20 | 20 | 37.8 | 37.8 | 0.0 | 37.8 | 0.0393725 | 2430.0 | 0.0 |

Lectura de estos datos:

- Greedy y A* planifican cada tramo, pero no optimizan el orden de las entregas; por eso sus costos no son comparables directamente con los de las metaheurísticas, que sí permutan el orden.
- A* obtiene menor costo que Greedy en la misma secuencia, a costa de expandir más nodos; es el comportamiento esperado de una búsqueda informada y óptima por tramo frente a una búsqueda ávida.
- Hill Climbing alcanza el mejor costo `37.8`, pero no en todos los inicios: promedio `38.4`, desviación `1.0392`, peor costo `41.1` y 10 óptimos locales registrados. El resumen de Hill Climbing reporta desviación poblacional `0.9859`, distinta de la desviación muestral del resumen general.
- Recocido y genético alcanzan `37.8` en las 20 repeticiones, con desviación 0.0. Esto es consistente con un espacio de solo `5! = 120` órdenes y con el uso de A* para cada tramo.
- Los tiempos no deben interpretarse como comparación absoluta de eficiencia: dependen de la implementación, del caché de tramos, del hardware y de la carga del sistema.

La validación exhaustiva del escenario predeterminado confirma:

```text
método = exhaustivo
evaluadas = 120
validas = 120
mejor_costo = 37.8
mejor_orden = [4, 2, 5, 1, 3]
```

Por tanto, para ese escenario y ese modelo, `37.8` es el óptimo del espacio de órdenes, no solo el mejor valor observado por las metaheurísticas.

### 4.4 Resultados adversarios

`resultados/csv/adversaria_logistica_12x12.csv` registra:

| Profundidad | Valor Minimax | Valor alfa-beta | Diferencia | Iguales | Nodos Minimax | Nodos alfa-beta | Podados | Reducción % | Mejor acción |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 2 | 1264.234 | 1264.234 | 0.0 | Sí | 13 | 12 | 1 | 7.6923 | `reservar_ruta` |
| 4 | 1257.590 | 1257.590 | 0.0 | Sí | 121 | 88 | 9 | 27.2727 | `reservar_ruta` |
| 6 | 1250.946 | 1250.946 | 0.0 | Sí | 1093 | 623 | 74 | 43.0009 | `reservar_ruta` |

La poda reduce nodos visitados y conserva exactamente el valor minimax. La acción recomendada para la empresa es `reservar_ruta` en las tres profundidades.

### 4.5 Plan final registrado

El plan real `resultados/planificacion_final.json` contiene:

```text
id_plan = plan-83edf98f74
fecha = 2026-11-12T08:01:32
escenario_id = logistica_12x12
nombre_escenario = Red metropolitana base
plan_valido = true
orden_entregas = [4, 2, 5, 1, 3]
nombres_entregas = ["Depósito Sur", "Zona Industrial",
                    "Mercado Central", "Centro Norte", "Puerto Este"]
costo_total = 37.8
longitud_ruta = 40
pasos = 40
recursos_utilizados = {combustible: 40.0, capacidad: 22.0,
                       tiempo: 40.0, presupuesto: 37.8}
```

Riesgo y estrategia:

```text
nivel = alto
riesgo_acumulado = 0.06
impacto_costos = 0.14
bloqueos = 3
accion_empresa_recomendada = reservar_ruta
linea_principal = [reservar_ruta, bloquear_ruta, reservar_ruta,
                   bloquear_ruta, reservar_ruta, bloquear_ruta]

estrategia_empresa = ruta_alternativa
estrategia_competidor = bloquear_ruta
pago_empresa = 1245.7216
tipo = nash
equilibrios_nash = [["ruta_alternativa", "bloquear_ruta"]]
```

La justificación del plan indica que se eligió el orden `[4,2,5,1,3]` por costo `37.8`, que las rutas se calcularon con A* sobre el mismo escenario y que la estrategia del juego orienta la postura operativa, mientras que las rutas concretas provienen de la mejor solución válida de los algoritmos.

## 5. Métricas, salidas y evidencia

### 5.1 Métricas de una ejecución

- `costo`: costo total real de la solución (`costo_total`), no el costo objetivo penalizado.
- `costo_objetivo`: costo total más penalización; es lo que minimizan las metaheurísticas.
- `solucion_valida`: validez estructural y de recursos de la solución.
- `exito`: verdadero solo si la solución existe y es válida.
- `tiempo_ejecucion`: tiempo de pared medido con `time.perf_counter()`.
- `nodos_expandidos`, `nodos_generados`, `nodos_visitados`, `nodos_podados`: métricas de búsqueda, según algoritmo.
- `evaluaciones`: número de evaluaciones de la función objetivo, incluyendo solicitudes repetidas que pueden resolverse por caché.
- `iteraciones`: movimientos aceptados, iteraciones de recocido, generaciones o expansiones, según algoritmo.
- `longitud_ruta`: suma de pasos de los tramos.
- `historial_costos`: secuencia usada por la gráfica de convergencia.
- `metricas_extra`: diccionario completo con detalles del algoritmo.
- `solucion_json`: solución serializada con rutas, costos, recursos y validez.

### 5.2 Estadísticas

`experimentos/metricas.py:30-48` calcula:

```text
n
minimo
maximo
promedio
desviacion
mediana
```

`estadisticas` usa `statistics.fmean`, `statistics.stdev` cuando hay más de un dato y `statistics.median`. `resumir_resultados` agrupa por algoritmo y usa los resultados exitosos como base; si no hay exitosos, usa todos. `resumir_desde_csv` replica el resumen leyendo las columnas del CSV y convierte booleanos y números con tolerancia a cadenas vacías.

Los resúmenes por algoritmo contienen:

```text
algoritmo, ejecuciones, exitos, costo_mejor, costo_promedio,
desviacion_costo, costo_mediana, tiempo_promedio,
evaluaciones_promedio, nodos_expandidos_promedio,
nodos_podados_promedio, semillas
```

### 5.3 Archivos generados

Salidas principales:

```text
resultados/csv/historial_ejecuciones.csv
resultados/csv/heuristicas_<escenario>.csv
resultados/csv/hill_climbing_<escenario>.csv
resultados/csv/resumen_hill_climbing.csv
resultados/csv/metaheuristicas_<escenario>.csv
resultados/csv/resumen_metaheuristicas.csv
resultados/csv/adversaria_<escenario>.csv
resultados/csv/juego_matriz_<escenario>.csv
resultados/csv/juego_analisis_<escenario>.json
resultados/csv/resultados_completos_<escenario>.csv
resultados/csv/resumen_comparacion.csv
resultados/graficas/*.png
resultados/planificacion_final.json
```

El historial se escribe en modo anexar; los resultados por escenario y resúmenes se sobrescriben. `historial_ejecuciones.csv` puede crecer mucho porque acumula todas las ejecuciones.

Gráficas generadas desde CSV (`experimentos/graficas.py:262-287`):

```text
costos_por_algoritmo.png
tiempos_por_algoritmo.png
nodos_expandidos.png
evaluaciones.png
distribucion_costos.png
convergencia.png
minimax_vs_alfa_beta.png
```

Todas se guardan con `dpi=140` y backend `Agg`. Si no hay datos válidos para una gráfica, esa tarea se omite; no se generan datos simulados.

### 5.4 Presentación en la interfaz

- `Resumen`: tarjetas de mejor costo, menor tiempo, menos nodos/iteraciones, mejor solución, costo final y estrategia; tabla por algoritmo.
- `Ejecuciones`: tabla con número, algoritmo, semilla, costo, validez, tiempo, nodos/iteraciones y orden; detalle con parámetros y métricas.
- `Rutas`: una cuadrícula a la vez, con la mejor solución de cada algoritmo y la opción `Recorrido final (planificación)`.
- `Gráficas`: carga los PNG generados o los recibidos en la ejecución; no recalcula gráficas desde la UI.
- `Acciones`: reconstruye la secuencia de acciones del juego y de la línea principal adversaria, con estado antes/después.
- `Juego estratégico`: matriz de pagos con Nash, mejores respuestas y dominancia; texto con recomendación.
- `Adversaria`: tabla comparativa Minimax/alfa-beta y resumen de la línea principal.
- `Plan final`: orden, costo, recursos, riesgo, estrategia, justificación y tramos.

## 6. Pruebas, validaciones y limitaciones

### 6.1 Pruebas automáticas

Archivo: `pruebas/test_sistema.py`. Contiene 8 pruebas:

| Prueba | Cobertura |
|---|---|
| `test_escenario_predeterminado_es_factible` | ID, validación estructural, factibilidad y costo óptimo 37.8 |
| `test_escenarios_alternativos_son_validos` | Alternativo y estrecho válidos y factibles |
| `test_escenario_bloqueado_es_rechazado` | Detección de escenario sin solución |
| `test_busqueda_heuristica_encuentra_rutas_validas` | Greedy y A* producen soluciones válidas |
| `test_hill_climbing_y_metaheuristicas` | Hill Climbing con reinicios, recocido y genético válidos |
| `test_juego_y_equivalencia_adversaria` | Matriz 3×3, Nash y equivalencia Minimax/alfa-beta |
| `test_flujo_completo_reducido_en_directorio_temporal` | Flujo completo reducido, plan, CSV y gráficas desactivadas |
| `test_fallo_parcial_conserva_resultados_validos` | Si falla el juego, se conservan resultados y el plan queda en `None` |

Comando:

```powershell
python -m unittest discover -s pruebas -v
```

La prueba reducida espera 6 resultados en `datos["resultados"]`: Greedy, A*, dos ejecuciones de Hill Climbing, recocido y genético. No incluye el juego ni la adversaria en esa lista.

### 6.2 Validación en capas

1. `Escenario.validar()`: dimensiones, posiciones dentro de la cuadrícula, superposiciones, ids únicos, demandas y tarifas no negativas, obstáculos, costos positivos y finitos, recursos obligatorios, capacidad total, factores positivos, bloqueos del competidor y conectividad BFS desde el inicio.
2. `validar_factibilidad()`: además de la validación estructural, prueba órdenes de entrega. Hasta 7 entregas explora todas las permutaciones; con más usa vecino más cercano, orden natural, orden inverso y muestreo aleatorio reproducible.
3. `construir_solucion()`: valida que existan todos los tramos, que la capacidad total no se exceda y que combustible, tiempo y presupuesto estén dentro de límite; agrega penalización a soluciones inválidas.
4. `guardar_escenario()`: no persiste escenarios inválidos.
5. `PanelConfiguracion`: valida rangos numéricos antes de aplicar recursos, competidor, movimiento y parámetros; restaura el escenario si la aplicación deja un estado inválido.
6. `VentanaPrincipal._preparar_ejecucion()`: valida configuración, estructura y factibilidad antes de lanzar la ejecución completa.

### 6.3 Limitaciones del modelo

1. **Vehículo único y estático.** No hay flota, múltiples depósitos, recogidas, entregas con ventanas de tiempo ni reabastecimiento.
2. **Capacidad acumulada, no por tramo.** `carga_maxima` es la suma de todas las demandas; no se modela la carga que baja en cada parada.
3. **Combustible y tiempo dependen solo del número de pasos.** No dependen del costo de la celda, la carga, la velocidad ni el tráfico.
4. **Prioridad no utilizada.** El campo `prioridad` se guarda y serializa, pero no interviene en el orden ni en la función objetivo.
5. **Optimización del orden.** El espacio de permutaciones es factorial. La validación exhaustiva solo cubre hasta 7 entregas; para tamaños mayores la factibilidad es una cota por muestreo, no una prueba.
6. **Comparación Greedy/A\* frente a metaheurísticas.** Greedy y A* no optimizan el orden de las entregas: usan el orden natural del escenario. Las metaheurísticas sí permutan el orden. Por eso sus costos no miden la misma decisión.
7. **Diagonal y heurística.** La heurística con diagonal usa siempre `sqrt(2)` para la distancia octile, aunque `factor_costo_diagonal` sea configurable. Si se habilita diagonal con un factor distinto, la admisibilidad de A* no está garantizada. Tampoco se impide cortar esquinas entre dos obstáculos: solo se comprueba la celda destino.
8. **Juego con coeficientes fijos.** Las estrategias, factores y penalizaciones son constantes del código. No se estiman a partir de datos reales ni se aprenden.
9. **Posible pérdida del factor de costo en `ruta_rapida`.** La ruta se calcula en modo `pasos` y luego se recostea con `costo_camino` sin el factor 1.15 de la estrategia; el pago usa el costo reconstruido.
10. **Bloqueo sin celdas definidas.** Si el escenario no tiene `celdas_bloqueadas`, `bloquear_ruta` no genera un desvío simulado y no recibe bono de bloqueo.
11. **Adversaria abstracta.** El estado modela presupuesto, combustible, reservas, bloqueos, riesgo e impacto, pero no resuelve rutas sobre la cuadrícula en cada turno. Las acciones no se traducen directamente a celdas concretas.
12. **Profundidad y costo exponencial.** Minimax sin poda crece rápido con la profundidad; el proyecto usa profundidades pequeñas (`2, 4, 6`). Alfa-beta reduce nodos, pero no cambia el valor.
13. **Recomendación no vinculante.** La estrategia del juego y el riesgo adversario no modifican las rutas del plan final; solo se agregan como recomendación y metadatos.
14. **Persistencia de sesión.** No hay base de datos ni recuperación automática de una ejecución interrumpida. Los resultados se reconstruyen desde archivos generados.
15. **Guardado de escenario.** La GUI guarda con `sobrescribir=True` cuando ya existe una ruta asociada; no pide confirmación adicional antes de reemplazar el archivo.
16. **Importación CSV limitada.** No conserva demanda, tarifa ni recursos originales; las entregas importadas usan demanda 4.0 y los recursos son valores por defecto. No es un round-trip completo.
17. **Versión de esquema no verificada.** El campo `esquema` se escribe, pero el cargador no rechaza versiones distintas.
18. **Métricas de tiempo.** Los tiempos corresponden a una máquina y una ejecución concretas; no hay normalización ni repetición con carga controlada.
19. **Datos sintéticos.** Los escenarios y costos son de demostración; no se validan contra una red logística real.
20. **Dependencia de la interfaz.** La ejecución completa está pensada para Tkinter aunque la lógica puede invocarse desde Python; las rutas se resuelven desde la raíz del proyecto.

### 6.4 Líneas de mejora coherentes con el código

- Añadir capacidad por tramo y múltiples vehículos.
- Incorporar ventanas de tiempo, tiempos de servicio y costos dependientes de carga.
- Usar un solver exacto de orden para tamaños pequeños y heurísticas con cotas para tamaños mayores.
- Corregir el tratamiento de la diagonal y de `factor_costo_diagonal` en la heurística.
- Hacer que `ruta_rapida` conserve su factor de costo al reconstruir el tramo.
- Integrar la estrategia del juego y el riesgo adversario en la selección o planificación de rutas, no solo en la recomendación.
- Persistir y comparar ejecuciones con un identificador de corrida y un entorno reproducible.
- Añadir pruebas específicas de importación/exportación CSV, guardado atómico y casos con diagonal.
