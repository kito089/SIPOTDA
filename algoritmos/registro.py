"""Registro de algoritmos y ejecución unificada.

La interfaz gráfica y los experimentos llaman únicamente a estas funciones;
así no duplican parámetros ni lógica de adaptación.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from algoritmos.busqueda_heuristica.astar import buscar_ruta as buscar_astar
from algoritmos.busqueda_heuristica.greedy import buscar_ruta as buscar_greedy
from algoritmos.busqueda_local.hill_climbing import hill_climbing
from algoritmos.comun import normalizar_orden, planificar_con_buscador
from algoritmos.metaheuristicas.algoritmo_genetico import algoritmo_genetico
from algoritmos.metaheuristicas.recocido_simulado import recocido_simulado
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


ALGORITMOS = [
    "Greedy Best-First",
    "A*",
    "Hill Climbing",
    "Recocido Simulado",
    "Algoritmo Genético",
]


def ejecutar_busqueda_heuristica(
    escenario: Escenario,
    algoritmo: str,
    orden: Iterable[int] | None = None,
    evitar: set[tuple[int, int]] | None = None,
    factor_costo: float = 1.0,
    modo: str = "costo",
    parametros: dict[str, Any] | None = None,
) -> ResultadoEjecucion:
    """Ejecuta Greedy o A* sobre todos los tramos obligatorios."""
    nombre = "Greedy Best-First" if algoritmo.lower().startswith("greedy") else "A*"
    buscador = buscar_greedy if nombre.startswith("Greedy") else buscar_astar
    orden = normalizar_orden(escenario, orden)
    inicio = time.perf_counter()
    solucion, metricas_busqueda = planificar_con_buscador(
        escenario,
        orden,
        buscador,
        evitar=evitar,
        factor_costo=factor_costo,
        modo=modo,
        nombre_algoritmo=nombre,
    )
    tiempo = time.perf_counter() - inicio
    resultado = ResultadoEjecucion.crear(
        escenario,
        nombre,
        semilla=None,
        parametros={
            "orden": list(orden),
            "factor_costo": factor_costo,
            "modo": modo,
            "evitar": sorted(evitar or []),
            **dict(parametros or {}),
        },
    )
    resultado.solucion = solucion
    resultado.costo = solucion.costo_total
    resultado.tiempo_ejecucion = tiempo
    resultado.exito = bool(solucion.valida)
    resultado.mensaje = (
        "Ruta completa encontrada y factible"
        if solucion.valida
        else "Ruta encontrada pero no factible: " + "; ".join(solucion.violaciones)
    )
    resultado.metricas = {
        **metricas_busqueda,
        "longitud_ruta": solucion.longitud_ruta,
        "pasos": solucion.pasos,
        "costo_total": solucion.costo_total,
        "solucion_valida": solucion.valida,
        "violaciones": list(solucion.violaciones),
        "nodos_expandidos": metricas_busqueda.get("nodos_expandidos", 0),
        "nodos_generados": metricas_busqueda.get("nodos_generados", 0),
        "iteraciones": metricas_busqueda.get("iteraciones", 0),
    }
    return resultado


def ejecutar_algoritmo(
    escenario: Escenario,
    algoritmo: str,
    parametros: dict[str, Any] | None = None,
    semilla: int | None = None,
    orden_inicial: Iterable[int] | None = None,
) -> ResultadoEjecucion:
    """Despacha un algoritmo por nombre con parámetros validados."""
    parametros = dict(parametros or {})
    clave = algoritmo.strip().lower()
    if clave in {"greedy", "greedy best-first", "greedy best first"}:
        return ejecutar_busqueda_heuristica(
            escenario, "Greedy Best-First", orden_inicial, parametros=parametros
        )
    if clave in {"a*", "astar", "a estrella"}:
        return ejecutar_busqueda_heuristica(
            escenario, "A*", orden_inicial, parametros=parametros
        )
    if clave in {"hill climbing", "hill_climbing", "hill"}:
        return hill_climbing(
            escenario,
            orden_inicial=orden_inicial,
            semilla=semilla,
            max_iteraciones=int(parametros.get("max_iteraciones", 500)),
            permitir_mesetas=bool(parametros.get("permitir_mesetas", False)),
            max_mesetas=int(parametros.get("max_mesetas", 20)),
        )
    if clave in {"recocido simulado", "recocido_simulado", "sa", "simulated annealing"}:
        return recocido_simulado(
            escenario,
            orden_inicial=orden_inicial,
            semilla=semilla,
            temperatura_inicial=float(parametros.get("temperatura_inicial", 50.0)),
            temperatura_final=float(parametros.get("temperatura_final", 0.01)),
            enfriamiento=float(parametros.get("enfriamiento", 0.95)),
            iteraciones_por_temperatura=int(
                parametros.get("iteraciones_por_temperatura", 20)
            ),
            max_iteraciones=int(parametros.get("max_iteraciones", 5000)),
        )
    if clave in {"algoritmo genetico", "algoritmo_genético", "genetico", "genético", "ga"}:
        return algoritmo_genetico(
            escenario,
            orden_inicial=orden_inicial,
            semilla=semilla,
            tamano_poblacion=int(parametros.get("tamano_poblacion", 40)),
            generaciones=int(parametros.get("generaciones", 100)),
            prob_cruza=float(parametros.get("prob_cruza", 0.85)),
            prob_mutacion=float(parametros.get("prob_mutacion", 0.2)),
            elitismo=int(parametros.get("elitismo", 2)),
            tamano_torneo=int(parametros.get("tamano_torneo", 3)),
            max_evaluaciones=int(parametros.get("max_evaluaciones", 20000)),
        )
    raise ValueError(f"Algoritmo desconocido: {algoritmo!r}")
