"""Greedy Best-First Search adaptado a la cuadrícula logística.

Se conserva la idea del ejemplo de referencia: la frontera es una cola de
prioridad ordenada *solamente* por la heurística h(n).  El costo acumulado se
arrastra únicamente para informar el costo real de la ruta, no para decidir
qué nodo expandir.
"""

from __future__ import annotations

import heapq
import itertools

from algoritmos.comun import ResultadoBusqueda, costo_camino
from modelos.escenario import Escenario


def buscar_ruta(
    escenario: Escenario,
    inicio: tuple[int, int],
    objetivo: tuple[int, int],
    evitar: set[tuple[int, int]] | None = None,
    factor_costo: float = 1.0,
    modo: str = "costo",
    max_pasos: int | None = None,
) -> ResultadoBusqueda:
    """Busca un camino de ``inicio`` a ``objetivo`` guiado por h(n).

    La heurística es la distancia geométrica al objetivo escalada por el costo
    mínimo transitable.  Greedy puede devolver rutas no óptimas, pero respeta
    obstáculos, límites y reglas de movimiento.
    """
    evitar = set(evitar or ())
    if not escenario.dentro(*inicio) or not escenario.dentro(*objetivo):
        return ResultadoBusqueda(False, mensaje="Coordenada fuera de la cuadrícula", algoritmo="Greedy Best-First")
    if not escenario.es_transitable(*inicio) or not escenario.es_transitable(*objetivo, evitar):
        return ResultadoBusqueda(False, mensaje="Inicio u objetivo no transitable", algoritmo="Greedy Best-First")
    if inicio == objetivo:
        return ResultadoBusqueda(True, camino=[inicio], costo=0.0, pasos=0, algoritmo="Greedy Best-First")

    contador = itertools.count()
    h0 = escenario.heuristica(inicio, objetivo, factor_costo, modo)
    frontera: list[tuple[float, int, tuple[int, int], float, list[tuple[int, int]]]] = [
        (h0, next(contador), inicio, 0.0, [inicio])
    ]
    visitados: set[tuple[int, int]] = set()
    nodos_expandidos = 0
    nodos_generados = 1

    while frontera:
        _, _, actual, costo_acumulado, camino = heapq.heappop(frontera)
        if actual in visitados:
            continue
        visitados.add(actual)
        nodos_expandidos += 1

        if actual == objetivo:
            # El costo real se recalcula sobre el camino para evitar arrastrar
            # errores de una prioridad basada solo en h(n).
            costo_real = costo_camino(escenario, camino, factor_costo, modo)
            return ResultadoBusqueda(
                exito=True,
                camino=camino,
                costo=costo_real,
                pasos=max(0, len(camino) - 1),
                nodos_expandidos=nodos_expandidos,
                nodos_generados=nodos_generados,
                iteraciones=nodos_expandidos,
                mensaje="Ruta encontrada",
                algoritmo="Greedy Best-First",
            )

        if max_pasos is not None and len(camino) - 1 >= max_pasos:
            continue

        for nf, nc, peso in escenario.vecinos(
            actual[0], actual[1], evitar, factor_costo, modo
        ):
            if (nf, nc) in visitados:
                continue
            h = escenario.heuristica((nf, nc), objetivo, factor_costo, modo)
            heapq.heappush(
                frontera,
                (h, next(contador), (nf, nc), costo_acumulado + peso, camino + [(nf, nc)]),
            )
            nodos_generados += 1

    return ResultadoBusqueda(
        exito=False,
        nodos_expandidos=nodos_expandidos,
        nodos_generados=nodos_generados,
        iteraciones=nodos_expandidos,
        mensaje="No existe una ruta transitable",
        algoritmo="Greedy Best-First",
    )
