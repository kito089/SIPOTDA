"""Validación estructural y de factibilidad de escenarios logísticos."""

from __future__ import annotations

import itertools
import random
from typing import Any

from modelos.escenario import Escenario


def validar_escenario(escenario: Escenario) -> list[str]:
    """Validación estructural rápida (sin resolver el problema completo)."""
    return escenario.validar()


def _ordenes_candidatos(escenario: Escenario, max_muestras: int, semilla: int):
    from algoritmos.comun import orden_vecino_mas_cercano

    ids = [e.id for e in escenario.entregas]
    vistos: set[tuple[int, ...]] = set()

    def agregar(orden):
        clave = tuple(orden)
        if clave not in vistos:
            vistos.add(clave)
            return list(orden)
        return None

    for orden in (ids, list(reversed(ids)), orden_vecino_mas_cercano(escenario)):
        candidato = agregar(orden)
        if candidato is not None:
            yield candidato

    if len(ids) <= 7:
        for orden in itertools.permutations(ids):
            candidato = agregar(list(orden))
            if candidato is not None:
                yield candidato
    else:
        rng = random.Random(semilla)
        for _ in range(max_muestras):
            orden = list(ids)
            rng.shuffle(orden)
            candidato = agregar(orden)
            if candidato is not None:
                yield candidato


def validar_factibilidad(
    escenario: Escenario,
    max_muestras: int = 1500,
    semilla: int = 12345,
) -> dict[str, Any]:
    """Busca una planificación factible y detecta escenarios sin solución.

    Para hasta 7 entregas se exploran todas las permutaciones; para más se
    combinan heurísticas constructivas con muestreo aleatorio reproducible.
    Así se detectan tanto la falta de conectividad como recursos imposibles
    (capacidad, combustible, tiempo o presupuesto).
    """
    from algoritmos.comun import PlanificadorRutas

    errores = escenario.validar()
    if errores:
        return {
            "valido": False,
            "hay_solucion": False,
            "errores": errores,
            "advertencias": [],
            "evaluadas": 0,
            "metodo": "validación estructural",
            "mejor_costo": None,
            "mejor_orden": None,
            "mejor_id_ejecucion": None,
        }

    planificador = PlanificadorRutas(escenario)
    evaluadas = 0
    mejor_solucion = None
    mejor_orden = None
    validas = 0
    metodo = "exhaustivo" if len(escenario.entregas) <= 7 else "muestreo"
    for orden in _ordenes_candidatos(escenario, max_muestras, semilla):
        solucion = planificador.evaluar(orden, "Validación de factibilidad")
        evaluadas += 1
        if solucion.valida:
            validas += 1
            if mejor_solucion is None or solucion.costo_total < mejor_solucion.costo_total:
                mejor_solucion = solucion
                mejor_orden = list(orden)
    advertencias: list[str] = []
    if validas == 0:
        errores.append(
            "No se encontró ninguna planificación factible con los recursos y "
            "restricciones actuales. Revise capacidad, combustible, tiempo y presupuesto."
        )
        advertencias.append(
            "La exploración de factibilidad no encontró soluciones válidas; "
            "puede aumentar los recursos o reducir la demanda."
        )
    elif metodo == "muestreo":
        advertencias.append(
            "Se usó muestreo reproducible (más de 7 entregas); la factibilidad "
            "encontrada es una cota superior, no una prueba de optimalidad."
        )
    return {
        "valido": not errores,
        "hay_solucion": validas > 0,
        "errores": errores,
        "advertencias": advertencias,
        "evaluadas": evaluadas,
        "validas": validas,
        "metodo": metodo,
        "mejor_costo": mejor_solucion.costo_total if mejor_solucion else None,
        "mejor_orden": mejor_orden,
        "mejor_solucion": mejor_solucion.a_dict() if mejor_solucion else None,
    }
