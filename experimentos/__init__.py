"""Experimentación reproducible, métricas y gráficas."""

from .metricas import resumir_resultados, resumir_desde_csv, estadisticas
from .comparaciones import comparar_desde_csv, verificar_equivalencia_adversaria
from .ejecutar_experimentos import (
    construir_planificacion_final,
    ejecutar_todo,
    experimento_adversario,
    experimento_hill_climbing,
    experimento_juego,
    experimento_metaheuristicas,
)
from .graficas import generar_todas_las_graficas

__all__ = [
    "resumir_resultados",
    "resumir_desde_csv",
    "estadisticas",
    "comparar_desde_csv",
    "verificar_equivalencia_adversaria",
    "construir_planificacion_final",
    "ejecutar_todo",
    "experimento_adversario",
    "experimento_hill_climbing",
    "experimento_juego",
    "experimento_metaheuristicas",
    "generar_todas_las_graficas",
]
