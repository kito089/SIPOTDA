"""Algoritmo A* adaptado a la cuadrícula logística.

Se mantiene f(n) = g(n) + h(n) del ejemplo de referencia.  ``g`` es el costo
real acumulado (costos variables de las celdas) y ``h`` la heurística
geométrica admisible.  Con costos positivos y una heurística consistente, A*
es óptimo.
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
    """Busca el camino de costo mínimo entre dos celdas."""
    evitar = set(evitar or ())
    if not escenario.dentro(*inicio) or not escenario.dentro(*objetivo):
        return ResultadoBusqueda(False, mensaje="Coordenada fuera de la cuadrícula", algoritmo="A*")
    if not escenario.es_transitable(*inicio) or not escenario.es_transitable(*objetivo, evitar):
        return ResultadoBusqueda(False, mensaje="Inicio u objetivo no transitable", algoritmo="A*")
    if inicio == objetivo:
        return ResultadoBusqueda(True, camino=[inicio], costo=0.0, pasos=0, algoritmo="A*")

    contador = itertools.count()
    h0 = escenario.heuristica(inicio, objetivo, factor_costo, modo)
    frontera: list[tuple[float, float, int, tuple[int, int]]] = [
        (h0, 0.0, next(contador), inicio)
    ]
    mejor_g: dict[tuple[int, int], float] = {inicio: 0.0}
    padre: dict[tuple[int, int], tuple[int, int] | None] = {inicio: None}
    cerrados: set[tuple[int, int]] = set()
    nodos_expandidos = 0
    nodos_generados = 1

    def reconstruir(nodo: tuple[int, int]) -> list[tuple[int, int]]:
        camino = [nodo]
        while padre[camino[-1]] is not None:
            camino.append(padre[camino[-1]])  # type: ignore[arg-type]
        camino.reverse()
        return camino

    def profundidad(nodo: tuple[int, int]) -> int:
        pasos = 0
        while padre[nodo] is not None:
            nodo = padre[nodo]  # type: ignore[assignment]
            pasos += 1
        return pasos

    while frontera:
        _, g, _, actual = heapq.heappop(frontera)
        if actual in cerrados:
            continue
        if g > mejor_g.get(actual, float("inf")) + 1e-12:
            continue
        cerrados.add(actual)
        nodos_expandidos += 1

        if actual == objetivo:
            camino = reconstruir(actual)
            costo = costo_camino(escenario, camino, factor_costo, modo)
            return ResultadoBusqueda(
                exito=True,
                camino=camino,
                costo=costo,
                pasos=max(0, len(camino) - 1),
                nodos_expandidos=nodos_expandidos,
                nodos_generados=nodos_generados,
                iteraciones=nodos_expandidos,
                mensaje="Ruta óptima encontrada",
                algoritmo="A*",
            )

        if max_pasos is not None and profundidad(actual) >= max_pasos:
            continue

        for nf, nc, peso in escenario.vecinos(
            actual[0], actual[1], evitar, factor_costo, modo
        ):
            vecino = (nf, nc)
            nuevo_g = g + peso
            if nuevo_g + 1e-12 < mejor_g.get(vecino, float("inf")):
                mejor_g[vecino] = nuevo_g
                padre[vecino] = actual
                h = escenario.heuristica(vecino, objetivo, factor_costo, modo)
                heapq.heappush(
                    frontera,
                    (nuevo_g + h, nuevo_g, next(contador), vecino),
                )
                nodos_generados += 1

    return ResultadoBusqueda(
        exito=False,
        nodos_expandidos=nodos_expandidos,
        nodos_generados=nodos_generados,
        iteraciones=nodos_expandidos,
        mensaje="No existe una ruta transitable",
        algoritmo="A*",
    )
