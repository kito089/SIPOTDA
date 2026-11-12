"""Algoritmo genético con representación por permutaciones.

Cada cromosoma es una permutación de ids de entrega.  Esto evita
estructuralmente entregas duplicadas o faltantes.  Se usan:

- cruza por orden (OX), adecuada para permutaciones;
- mutación por intercambio de dos genes;
- selección por torneo;
- elitismo para conservar los mejores individuos.

La aptitud es ``1 / (1 + costo_objetivo)``: al minimizar el costo objetivo se
maximiza la aptitud y se mantiene positiva.
"""

from __future__ import annotations

import random
import statistics
import time
from typing import Iterable

from algoritmos.comun import (
    PlanificadorRutas,
    normalizar_orden,
    orden_aleatorio,
    orden_vecino_mas_cercano,
)
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


def cruza_ox(padre1: list[int], padre2: list[int], rng: random.Random) -> tuple[list[int], list[int]]:
    """Cruza por orden (Order Crossover, OX) para permutaciones."""
    n = len(padre1)
    if n < 2:
        return list(padre1), list(padre2)
    corte1, corte2 = sorted(rng.sample(range(n + 1), 2))
    if corte1 == corte2:
        corte2 = min(n, corte1 + 1)

    def un_hijo(p1: list[int], p2: list[int]) -> list[int]:
        hijo: list[int | None] = [None] * n
        hijo[corte1:corte2] = p1[corte1:corte2]
        usados = set(p1[corte1:corte2])
        posiciones = list(range(corte2, n)) + list(range(0, corte1))
        valores = [valor for valor in p2 if valor not in usados]
        for posicion, valor in zip(posiciones, valores):
            hijo[posicion] = valor
        return [int(x) for x in hijo]  # type: ignore[arg-type]

    return un_hijo(padre1, padre2), un_hijo(padre2, padre1)


def mutacion_intercambio(cromosoma: list[int], rng: random.Random) -> list[int]:
    """Invierte dos genes (mutación por intercambio)."""
    mutado = list(cromosoma)
    if len(mutado) < 2:
        return mutado
    i, j = rng.sample(range(len(mutado)), 2)
    mutado[i], mutado[j] = mutado[j], mutado[i]
    return mutado


def algoritmo_genetico(
    escenario: Escenario,
    orden_inicial: Iterable[int] | None = None,
    semilla: int | None = None,
    tamano_poblacion: int = 40,
    generaciones: int = 100,
    prob_cruza: float = 0.85,
    prob_mutacion: float = 0.2,
    elitismo: int = 2,
    tamano_torneo: int = 3,
    max_evaluaciones: int = 20_000,
    planificador: PlanificadorRutas | None = None,
) -> ResultadoEjecucion:
    """Optimiza el orden de entrega con un algoritmo genético."""
    if tamano_poblacion < 2:
        raise ValueError("El tamaño de población debe ser al menos 2")
    if generaciones <= 0 or max_evaluaciones <= 0:
        raise ValueError("Las generaciones y evaluaciones deben ser positivas")
    if not 0 <= prob_cruza <= 1 or not 0 <= prob_mutacion <= 1:
        raise ValueError("Las probabilidades deben estar entre 0 y 1")
    if elitismo < 0 or elitismo >= tamano_poblacion:
        raise ValueError("El elitismo debe ser >= 0 y menor que la población")
    if tamano_torneo < 1:
        raise ValueError("El tamaño de torneo debe ser positivo")
    if semilla is None:
        semilla = random.randrange(0, 2**31 - 1)
    rng = random.Random(semilla)
    planificador = planificador or PlanificadorRutas(escenario)
    inicio_tiempo = time.perf_counter()

    ids = [e.id for e in escenario.entregas]
    n = len(ids)
    if n < 2:
        raise ValueError("El algoritmo genético requiere al menos dos entregas")

    # Población inicial: soluciones constructivas + permutaciones aleatorias.
    base: list[list[int]] = [orden_vecino_mas_cercano(escenario), list(ids), list(reversed(ids))]
    if orden_inicial is not None:
        base.insert(0, normalizar_orden(escenario, orden_inicial))
    vistos: set[tuple[int, ...]] = set()
    poblacion: list[list[int]] = []
    for candidato in base:
        clave = tuple(candidato)
        if clave not in vistos:
            poblacion.append(candidato)
            vistos.add(clave)
    intentos = 0
    while len(poblacion) < tamano_poblacion and intentos < tamano_poblacion * 20:
        intentos += 1
        candidato = orden_aleatorio(rng, escenario)
        clave = tuple(candidato)
        if clave not in vistos:
            poblacion.append(candidato)
            vistos.add(clave)
    while len(poblacion) < tamano_poblacion:
        poblacion.append(orden_aleatorio(rng, escenario))

    evaluaciones = 0
    cache: dict[tuple[int, ...], object] = {}

    def evaluar(individuo: list[int]):
        nonlocal evaluaciones
        evaluaciones += 1
        clave = tuple(individuo)
        if clave not in cache:
            cache[clave] = planificador.evaluar(individuo, "Algoritmo Genético")
        return cache[clave]

    def aptitud(solucion) -> float:
        return 1.0 / (1.0 + max(0.0, solucion.costo_objetivo))

    def seleccionar(sols_poblacion, aptitudes) -> list[int]:
        elegidos = rng.sample(range(len(sols_poblacion)), min(tamano_torneo, len(sols_poblacion)))
        ganador = max(elegidos, key=lambda i: (aptitudes[i], -i))
        return list(sols_poblacion[ganador])

    soluciones = [evaluar(ind) for ind in poblacion]
    aptitudes = [aptitud(s) for s in soluciones]
    mejor_indice = max(range(len(soluciones)), key=lambda i: (soluciones[i].costo_objetivo * -1, -i))
    mejor_orden = list(poblacion[mejor_indice])
    mejor_sol = soluciones[mejor_indice].clonar()

    historial_mejores = [round(mejor_sol.costo_total, 6)]
    historial_promedios = [round(statistics.fmean(s.costo_total for s in soluciones), 6)]
    historial_objetivos = [round(mejor_sol.costo_objetivo, 6)]
    historial_diversidad = [len({tuple(ind) for ind in poblacion})]
    generaciones_ejecutadas = 0

    for generacion in range(1, generaciones + 1):
        if evaluaciones >= max_evaluaciones:
            break
        nueva: list[list[int]] = []
        ordenados = sorted(
            range(len(poblacion)),
            key=lambda i: (-aptitudes[i], i),
        )
        for indice in ordenados[:elitismo]:
            nueva.append(list(poblacion[indice]))

        while len(nueva) < tamano_poblacion:
            padre1 = seleccionar(poblacion, aptitudes)
            padre2 = seleccionar(poblacion, aptitudes)
            if rng.random() < prob_cruza:
                hijo1, hijo2 = cruza_ox(padre1, padre2, rng)
            else:
                hijo1, hijo2 = list(padre1), list(padre2)
            if rng.random() < prob_mutacion:
                hijo1 = mutacion_intercambio(hijo1, rng)
            if rng.random() < prob_mutacion:
                hijo2 = mutacion_intercambio(hijo2, rng)
            nueva.append(hijo1)
            if len(nueva) < tamano_poblacion:
                nueva.append(hijo2)

        poblacion = nueva[:tamano_poblacion]
        soluciones = [evaluar(ind) for ind in poblacion]
        aptitudes = [aptitud(s) for s in soluciones]
        generaciones_ejecutadas = generacion
        mejor_gen = max(range(len(soluciones)), key=lambda i: (aptitudes[i], -i))
        if soluciones[mejor_gen].costo_objetivo < mejor_sol.costo_objetivo - 1e-9:
            mejor_sol = soluciones[mejor_gen].clonar()
            mejor_orden = list(poblacion[mejor_gen])
        historial_mejores.append(round(mejor_sol.costo_total, 6))
        historial_promedios.append(
            round(statistics.fmean(s.costo_total for s in soluciones), 6)
        )
        historial_objetivos.append(round(mejor_sol.costo_objetivo, 6))
        historial_diversidad.append(len({tuple(ind) for ind in poblacion}))
        if evaluaciones >= max_evaluaciones:
            break

    tiempo = time.perf_counter() - inicio_tiempo
    resultado = ResultadoEjecucion.crear(
        escenario,
        "Algoritmo Genético",
        semilla=semilla,
        parametros={
            "tamano_poblacion": tamano_poblacion,
            "generaciones": generaciones,
            "prob_cruza": prob_cruza,
            "prob_mutacion": prob_mutacion,
            "elitismo": elitismo,
            "tamano_torneo": tamano_torneo,
            "max_evaluaciones": max_evaluaciones,
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
        "costo_final": mejor_sol.costo_total,
        "objetivo_final": mejor_sol.costo_objetivo,
        "evaluaciones": evaluaciones,
        "iteraciones": generaciones_ejecutadas,
        "generaciones_ejecutadas": generaciones_ejecutadas,
        "generaciones_solicitadas": generaciones,
        "poblacion": tamano_poblacion,
        "historial_costos": historial_mejores,
        "historial_promedios": historial_promedios,
        "historial_objetivos": historial_objetivos,
        "historial_diversidad": historial_diversidad,
        "diversidad_final": historial_diversidad[-1],
        "orden_inicial": list(orden_inicial) if orden_inicial is not None else None,
        "orden_final": list(mejor_orden),
        "solucion_valida": mejor_sol.valida,
        "violaciones": list(mejor_sol.violaciones),
        **planificador.metricas_cache(),
    }
    return resultado
