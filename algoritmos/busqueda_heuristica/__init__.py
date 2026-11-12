"""Búsqueda heurística: Greedy Best-First Search y A*."""

from .greedy import buscar_ruta as buscar_greedy
from .astar import buscar_ruta as buscar_astar

__all__ = ["buscar_greedy", "buscar_astar"]
