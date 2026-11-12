"""Búsqueda adversaria: Minimax y poda alfa-beta."""

from .minimax import ejecutar_minimax
from .alfa_beta import ejecutar_alfa_beta
from .modelo_adversario import (
    ConfiguracionAdversario,
    EstadoAdversario,
    acciones_legales,
    crear_configuracion,
    crear_estado_inicial,
    es_terminal,
    evaluar_estado,
    transicion,
)

__all__ = [
    "ejecutar_minimax",
    "ejecutar_alfa_beta",
    "ConfiguracionAdversario",
    "EstadoAdversario",
    "acciones_legales",
    "crear_configuracion",
    "crear_estado_inicial",
    "es_terminal",
    "evaluar_estado",
    "transicion",
]
