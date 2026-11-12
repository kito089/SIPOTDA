"""Modelos de datos compartidos por todos los módulos del sistema.

La representación central es :class:`Escenario`, utilizada por los algoritmos,
la interfaz gráfica y los módulos de persistencia.  Ninguno de estos modelos
depende de Tkinter ni de matplotlib.
"""

from .celda import Celda
from .entrega import Entrega
from .recurso import Recurso
from .escenario import Escenario
from .solucion import Solucion, Tramo
from .resultados import ResultadoEjecucion

__all__ = [
    "Celda",
    "Entrega",
    "Recurso",
    "Escenario",
    "Solucion",
    "Tramo",
    "ResultadoEjecucion",
]
