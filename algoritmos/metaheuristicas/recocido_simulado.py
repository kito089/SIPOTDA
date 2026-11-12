"""Recocido simulado para el orden de entregas.

La probabilidad de aceptar un vecino peor es exactamente

    P(aceptación) = exp(-Δ / T)

donde Δ = costo(vecino) - costo(actual) > 0.  Al inicio, una temperatura alta
permite explorar el espacio y escapar de óptimos locales; el enfriamiento
geométrico (T <- T * alfa) reduce gradualmente esa probabilidad y convierte el
proceso en una búsqueda cada vez más greedy.
"""

from __future__ import annotations

import math
import random
import time
from typing import Iterable

from algoritmos.comun import (
    PlanificadorRutas,
    generar_vecino_intercambio,
    normalizar_orden,
    orden_aleatorio,
)
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


def recocido_simulado(
    escenario: Escenario,
    orden_inicial: Iterable[int] | None = None,
    semilla: int | None = None,
    temperatura_inicial: float = 50.0,
    temperatura_final: float = 0.01,
    enfriamiento: float = 0.95,
    iteraciones_por_temperatura: int = 20,
    max_iteraciones: int = 5_000,
    planificador: PlanificadorRutas | None = None,
) -> ResultadoEjecucion:
    """Optimiza una permutación de entregas mediante recocido simulado."""
    if temperatura_inicial <= 0 or temperatura_final <= 0:
        raise ValueError("Las temperaturas deben ser positivas")
    if temperatura_inicial <= temperatura_final:
        raise ValueError("La temperatura inicial debe ser mayor que la final")
    if not 0 < enfriamiento < 1:
        raise ValueError("El enfriamiento debe estar entre 0 y 1")
    if iteraciones_por_temperatura <= 0 or max_iteraciones <= 0:
        raise ValueError("Los límites de iteraciones deben ser positivos")
    if semilla is None:
        semilla = random.randrange(0, 2**31 - 1)
    rng = random.Random(semilla)
    planificador = planificador or PlanificadorRutas(escenario)
    inicio_tiempo = time.perf_counter()

    if orden_inicial is None:
        actual = orden_aleatorio(rng, escenario)
        origen = "aleatorio"
    else:
        actual = normalizar_orden(escenario, orden_inicial)
        origen = "proporcionado"
    orden_de_partida = list(actual)

    actual_sol = planificador.evaluar(actual, "Recocido Simulado")
    mejor_orden = list(actual)
    mejor_sol = actual_sol.clonar()
    evaluaciones = 1
    temperatura = float(temperatura_inicial)
    iteraciones = 0
    aceptados = 0
    aceptados_peores = 0
    rechazados = 0
    historial_costos = [round(actual_sol.costo_total, 6)]
    historial_objetivos = [round(actual_sol.costo_objetivo, 6)]
    historial_temperaturas = [round(temperatura, 6)]

    while temperatura > temperatura_final and iteraciones < max_iteraciones:
        for _ in range(iteraciones_por_temperatura):
            if iteraciones >= max_iteraciones:
                break
            vecino, _ = generar_vecino_intercambio(actual, rng)
            sol_vecino = planificador.evaluar(vecino, "Recocido Simulado")
            evaluaciones += 1
            delta = sol_vecino.costo_objetivo - actual_sol.costo_objetivo

            aceptar = False
            if delta <= 0:
                aceptar = True
            else:
                probabilidad = math.exp(-delta / temperatura)
                if rng.random() < probabilidad:
                    aceptar = True
                    aceptados_peores += 1

            if aceptar:
                actual, actual_sol = vecino, sol_vecino
                aceptados += 1
                if sol_vecino.costo_objetivo < mejor_sol.costo_objetivo - 1e-9:
                    mejor_orden = list(vecino)
                    mejor_sol = sol_vecino.clonar()
            else:
                rechazados += 1

            iteraciones += 1
            historial_costos.append(round(mejor_sol.costo_total, 6))
            historial_objetivos.append(round(mejor_sol.costo_objetivo, 6))
            historial_temperaturas.append(round(temperatura, 6))

        temperatura *= enfriamiento

    tiempo = time.perf_counter() - inicio_tiempo
    resultado = ResultadoEjecucion.crear(
        escenario,
        "Recocido Simulado",
        semilla=semilla,
        parametros={
            "temperatura_inicial": temperatura_inicial,
            "temperatura_final": temperatura_final,
            "enfriamiento": enfriamiento,
            "iteraciones_por_temperatura": iteraciones_por_temperatura,
            "max_iteraciones": max_iteraciones,
            "orden_inicial": origen,
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
        "evaluaciones": evaluaciones,
        "iteraciones": iteraciones,
        "aceptados": aceptados,
        "aceptados_peores": aceptados_peores,
        "rechazados": rechazados,
        "temperatura_final_alcanzada": temperatura,
        "historial_costos": historial_costos,
        "historial_objetivos": historial_objetivos,
        "historial_temperaturas": historial_temperaturas,
        "orden_inicial": orden_de_partida,
        "orden_final": list(mejor_orden),
        "solucion_valida": mejor_sol.valida,
        "violaciones": list(mejor_sol.violaciones),
        **planificador.metricas_cache(),
    }
    return resultado
