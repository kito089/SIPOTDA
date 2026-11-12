"""Hill Climbing para optimizar el orden de visita de las entregas.

Vecindad
--------
Todas las soluciones que resultan de intercambiar dos entregas (2-swap) de la
secuencia actual.  La solución se representa como una permutación de ids de
entrega, tal como en el ejemplo de referencia adaptado a rutas.

Criterio de terminación
-----------------------
Se detiene cuando ningún vecino mejora estrictamente el costo objetivo.  Si
``permitir_mesetas`` está activo se aceptan movimientos laterales (mismo
objetivo) sin repetir estados, hasta ``max_mesetas`` veces; esto ayuda a
explorar mesetas, aunque puede seguir atrapado en un óptimo local.
"""

from __future__ import annotations

import random
import statistics
import time
from itertools import combinations
from typing import Iterable

from algoritmos.comun import (
    PlanificadorRutas,
    normalizar_orden,
    orden_aleatorio,
    orden_vecino_mas_cercano,
)
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


def hill_climbing(
    escenario: Escenario,
    orden_inicial: Iterable[int] | None = None,
    semilla: int | None = None,
    max_iteraciones: int = 500,
    permitir_mesetas: bool = False,
    max_mesetas: int = 20,
    planificador: PlanificadorRutas | None = None,
) -> ResultadoEjecucion:
    """Ejecuta Hill Climbing con estrategia de mejor vecino.

    ``max_iteraciones`` limita el número de movimientos aceptados, no el
    número de vecinos evaluados.  Cada evaluación se contabiliza para los
    experimentos.
    """
    if max_iteraciones <= 0:
        raise ValueError("max_iteraciones debe ser mayor que cero")
    if max_mesetas < 0:
        raise ValueError("max_mesetas no puede ser negativo")
    if semilla is None:
        semilla = random.randrange(0, 2**31 - 1)
    rng = random.Random(semilla)
    planificador = planificador or PlanificadorRutas(escenario)
    inicio = time.perf_counter()

    if orden_inicial is None:
        actual = orden_aleatorio(rng, escenario)
        origen_orden = "aleatorio"
    else:
        actual = normalizar_orden(escenario, orden_inicial)
        origen_orden = "proporcionado"
    orden_de_partida = list(actual)

    actual_sol = planificador.evaluar(actual, "Hill Climbing")
    evaluaciones = 1
    historial_costos = [round(actual_sol.costo_total, 6)]
    historial_objetivos = [round(actual_sol.costo_objetivo, 6)]
    mejor_orden = list(actual)
    mejor_sol = actual_sol.clonar()
    visitados = {tuple(actual)}
    mesetas = 0
    iteraciones = 0
    optimo_local = False

    while iteraciones < max_iteraciones:
        mejor_vecino_orden: list[int] | None = None
        mejor_vecino_sol = None

        # Vecindad completa por intercambio de dos posiciones.
        for i, j in combinations(range(len(actual)), 2):
            vecino = list(actual)
            vecino[i], vecino[j] = vecino[j], vecino[i]
            sol_vecino = planificador.evaluar(vecino, "Hill Climbing")
            evaluaciones += 1
            if mejor_vecino_sol is None or sol_vecino.costo_objetivo < mejor_vecino_sol.costo_objetivo - 1e-9:
                mejor_vecino_orden = vecino
                mejor_vecino_sol = sol_vecino

        if mejor_vecino_sol is None:
            break

        mejora = actual_sol.costo_objetivo - mejor_vecino_sol.costo_objetivo
        if mejora > 1e-9:
            actual = mejor_vecino_orden  # type: ignore[assignment]
            actual_sol = mejor_vecino_sol
            visitados.add(tuple(actual))
            iteraciones += 1
            historial_costos.append(round(actual_sol.costo_total, 6))
            historial_objetivos.append(round(actual_sol.costo_objetivo, 6))
            if actual_sol.costo_objetivo < mejor_sol.costo_objetivo - 1e-9:
                mejor_orden = list(actual)
                mejor_sol = actual_sol.clonar()
            continue

        # Sin mejora estricta: posible meseta.
        if not permitir_mesetas or mesetas >= max_mesetas:
            optimo_local = True
            break

        # Buscar un vecino con el mismo objetivo que no haya sido visitado.
        candidato = None
        for i, j in combinations(range(len(actual)), 2):
            vecino = list(actual)
            vecino[i], vecino[j] = vecino[j], vecino[i]
            if tuple(vecino) in visitados:
                continue
            sol_vecino = planificador.evaluar(vecino, "Hill Climbing")
            evaluaciones += 1
            if abs(sol_vecino.costo_objetivo - actual_sol.costo_objetivo) <= 1e-9:
                candidato = (vecino, sol_vecino)
                break
        if candidato is None:
            optimo_local = True
            break
        actual, actual_sol = candidato
        visitados.add(tuple(actual))
        mesetas += 1
        iteraciones += 1
        historial_costos.append(round(actual_sol.costo_total, 6))
        historial_objetivos.append(round(actual_sol.costo_objetivo, 6))
        optimo_local = False

    # Se devuelve el mejor estado encontrado; con movimientos laterales podría
    # no ser el actual.
    if mejor_sol.costo_objetivo > actual_sol.costo_objetivo + 1e-9:
        mejor_sol = actual_sol.clonar()
        mejor_orden = list(actual)

    tiempo = time.perf_counter() - inicio
    resultado = ResultadoEjecucion.crear(
        escenario,
        "Hill Climbing",
        semilla=semilla,
        parametros={
            "max_iteraciones": max_iteraciones,
            "permitir_mesetas": permitir_mesetas,
            "max_mesetas": max_mesetas,
            "orden_inicial": origen_orden,
            "num_entregas": len(escenario.entregas),
        },
    )
    resultado.solucion = mejor_sol
    resultado.costo = mejor_sol.costo_total
    resultado.tiempo_ejecucion = tiempo
    resultado.exito = bool(mejor_sol.valida)
    resultado.mensaje = (
        "Solución válida encontrada"
        if mejor_sol.valida
        else "La mejor solución incumple restricciones: "
        + "; ".join(mejor_sol.violaciones)
    )
    resultado.metricas = {
        "costo_inicial": historial_costos[0],
        "costo_final": mejor_sol.costo_total,
        "objetivo_final": mejor_sol.costo_objetivo,
        "mejora": historial_costos[0] - mejor_sol.costo_total,
        "evaluaciones": evaluaciones,
        "iteraciones": iteraciones,
        "movimientos_aceptados": iteraciones,
        "mesetas_exploradas": mesetas,
        "optimo_local": optimo_local,
        "historial_costos": historial_costos,
        "historial_objetivos": historial_objetivos,
        "orden_inicial": orden_de_partida,
        "orden_final": list(mejor_orden),
        "solucion_valida": mejor_sol.valida,
        "violaciones": list(mejor_sol.violaciones),
        **planificador.metricas_cache(),
    }
    return resultado


def reinicios_hill_climbing(
    escenario: Escenario,
    num_inicios: int = 10,
    semilla_base: int | None = None,
    max_iteraciones: int = 500,
    permitir_mesetas: bool = False,
    max_mesetas: int = 20,
) -> tuple[list[ResultadoEjecucion], dict]:
    """Ejecuta Hill Climbing desde varias soluciones iniciales.

    Devuelve la lista de resultados (uno por inicio) y un resumen con costo
    inicial/final, óptimos locales, variabilidad y semillas.  Se usan la
    solución vecino-más-cercano, la inversa y soluciones aleatorias.
    """
    if num_inicios <= 0:
        raise ValueError("num_inicios debe ser mayor que cero")
    if semilla_base is None:
        semilla_base = random.randrange(0, 2**31 - 1)
    rng = random.Random(semilla_base)
    semillas = [rng.randrange(0, 2**31 - 1) for _ in range(num_inicios)]
    planificador = PlanificadorRutas(escenario)
    resultados: list[ResultadoEjecucion] = []
    iniciales: list[list[int]] = []

    ids = [e.id for e in escenario.entregas]
    candidatos = [orden_vecino_mas_cercano(escenario), list(reversed(ids)), list(ids)]
    while len(candidatos) < num_inicios:
        candidato = list(ids)
        rng.shuffle(candidato)
        candidatos.append(candidato)

    for indice in range(num_inicios):
        orden = candidatos[indice]
        resultado = hill_climbing(
            escenario,
            orden_inicial=orden,
            semilla=semillas[indice],
            max_iteraciones=max_iteraciones,
            permitir_mesetas=permitir_mesetas,
            max_mesetas=max_mesetas,
            planificador=planificador,
        )
        resultado.parametros.update(
            {
                "indice_inicio": indice,
                "semilla_base": semilla_base,
                "num_inicios": num_inicios,
            }
        )
        resultado.metricas["orden_inicial_utilizado"] = list(orden)
        resultados.append(resultado)
        iniciales.append(orden)

    validos = [r for r in resultados if r.exito and r.solucion is not None]
    base = validos or [r for r in resultados if r.solucion is not None]
    costos_finales = [r.costo for r in base]
    costos_iniciales = [r.metricas.get("costo_inicial", 0.0) for r in base]
    mejor = min(base, key=lambda r: r.costo) if base else None
    resumen = {
        "escenario": escenario.id,
        "num_inicios": num_inicios,
        "semilla_base": semilla_base,
        "semillas": semillas,
        "costo_promedio_inicial": statistics.fmean(costos_iniciales)
        if costos_iniciales
        else float("nan"),
        "costo_promedio_final": statistics.fmean(costos_finales)
        if costos_finales
        else float("nan"),
        "desviacion_final": statistics.pstdev(costos_finales)
        if len(costos_finales) > 1
        else 0.0,
        "mejor_costo": mejor.costo if mejor else float("inf"),
        "mejor_id_ejecucion": mejor.id_ejecucion if mejor else None,
        "peor_costo": max(costos_finales) if costos_finales else float("inf"),
        "optimos_locales": sum(1 for r in resultados if r.metricas.get("optimo_local")),
        "resultados_validos": len(validos),
        "resultados_totales": len(resultados),
        "ids_ejecucion": [r.id_ejecucion for r in resultados],
    }
    return resultados, resumen
