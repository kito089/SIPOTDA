"""Utilidades compartidas por todos los algoritmos.

Aquí viven la evaluación de soluciones, la planificación de rutas entre puntos
obligatorios y la construcción del formato común :class:`Solucion`.  De este
modo Greedy, A*, Hill Climbing, recocido, genético y la integración final
utilizan exactamente las mismas reglas y restricciones.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from modelos.escenario import Escenario
from modelos.solucion import PENALIZACION_BASE, Solucion, Tramo


@dataclass
class ResultadoBusqueda:
    """Resultado interno de una búsqueda de un tramo."""

    exito: bool
    camino: list[tuple[int, int]] = field(default_factory=list)
    costo: float = float("inf")
    pasos: int = 0
    nodos_expandidos: int = 0
    nodos_generados: int = 0
    iteraciones: int = 0
    mensaje: str = ""
    algoritmo: str = ""

    def a_dict(self) -> dict:
        return {
            "exito": self.exito,
            "costo": None if self.costo == float("inf") else round(self.costo, 6),
            "pasos": self.pasos,
            "nodos_expandidos": self.nodos_expandidos,
            "nodos_generados": self.nodos_generados,
            "iteraciones": self.iteraciones,
            "mensaje": self.mensaje,
            "algoritmo": self.algoritmo,
        }


def normalizar_orden(escenario: Escenario, orden: Iterable[int] | None) -> list[int]:
    """Devuelve una permutación válida de todos los ids de entrega.

    Si no se proporciona un orden se usa el orden de aparición del escenario.
    Se lanzan errores explícitos ante duplicados o ids inexistentes para no
    evaluar soluciones ambiguas.
    """
    ids = [e.id for e in escenario.entregas]
    if orden is None:
        return ids
    orden = [int(x) for x in orden]
    if len(orden) != len(ids) or set(orden) != set(ids):
        raise ValueError(
            "El orden de entregas debe ser una permutación exacta de los ids "
            f"{ids}; se recibió {orden}."
        )
    return orden


def orden_aleatorio(rng: random.Random, escenario: Escenario) -> list[int]:
    ids = [e.id for e in escenario.entregas]
    rng.shuffle(ids)
    return ids


def orden_vecino_mas_cercano(escenario: Escenario, posicion_inicial=None) -> list[int]:
    """Heurística constructiva basada en distancia Manhattan.

    Se usa como una de las soluciones iniciales de Hill Climbing y del
    algoritmo genético.  No sustituye a los algoritmos: solo genera un orden
    de partida razonable.
    """
    pendientes = {e.id: e for e in escenario.entregas}
    posicion = posicion_inicial or escenario.inicio
    orden: list[int] = []
    while pendientes:
        siguiente = min(
            pendientes.values(),
            key=lambda e: (
                escenario.distancia_manhattan(posicion, e.posicion),
                e.id,
            ),
        )
        orden.append(siguiente.id)
        posicion = siguiente.posicion
        del pendientes[siguiente.id]
    return orden


def generar_vecino_intercambio(
    orden: list[int], rng: random.Random
) -> tuple[list[int], tuple[int, int] | None]:
    """Intercambia dos posiciones distintas (vecindad de Hill Climbing)."""
    if len(orden) < 2:
        return list(orden), None
    i, j = rng.sample(range(len(orden)), 2)
    vecino = list(orden)
    vecino[i], vecino[j] = vecino[j], vecino[i]
    return vecino, (i, j)


def costo_camino(
    escenario: Escenario,
    camino: list[tuple[int, int]],
    factor_costo: float = 1.0,
    modo: str = "costo",
) -> float:
    """Costo de un camino ya construido (sin contar la celda inicial)."""
    total = 0.0
    for (f1, c1), (f2, c2) in zip(camino, camino[1:]):
        if modo == "pasos":
            total += 1.0
            continue
        celda = escenario.obtener_celda(f2, c2)
        incremento = celda.costo * factor_costo
        if f1 != f2 and c1 != c2:
            incremento *= escenario.factor_costo_diagonal
        total += incremento
    return total


def construir_solucion(
    escenario: Escenario,
    orden: Iterable[int],
    tramos: list[Tramo],
    algoritmo: str = "",
) -> Solucion:
    """Evalúa una secuencia de entregas y sus tramos con las restricciones.

    Restricciones comprobadas:
    - capacidad: carga total inicial <= capacidad disponible;
    - combustible: pasos totales * consumo por paso <= límite;
    - tiempo: pasos totales * consumo por paso <= límite;
    - presupuesto: costo total <= límite.

    Las soluciones inválidas reciben una penalización grande para que las
    metaheurísticas puedan compararlas sin perder información del costo real.
    """
    orden = normalizar_orden(escenario, orden)
    solucion = Solucion(orden_entregas=list(orden), rutas=list(tramos))
    solucion.valida = True
    solucion.costo_total = sum(t.costo for t in tramos)
    solucion.pasos = sum(max(0, t.pasos) for t in tramos)
    solucion.combustible_consumido = (
        solucion.pasos * escenario.consumo_por_paso("combustible", 1.0)
    )
    solucion.tiempo_consumido = solucion.pasos * escenario.consumo_por_paso("tiempo", 1.0)
    solucion.presupuesto_consumido = solucion.costo_total
    solucion.carga_maxima = sum(e.demanda for e in escenario.entregas)

    nombres = ["Inicio"]
    nombres += [
        escenario.obtener_entrega(i).nombre
        for i in orden
        if escenario.obtener_entrega(i) is not None
    ]
    nombres.append("Destino")
    solucion.detalle.update(
        {
            "secuencia": nombres,
            "orden_nombres": nombres[1:-1],
            "algoritmo": algoritmo,
            "tramos": len(tramos),
            "recursos": {
                "combustible": round(solucion.combustible_consumido, 6),
                "capacidad": round(solucion.carga_maxima, 6),
                "tiempo": round(solucion.tiempo_consumido, 6),
                "presupuesto": round(solucion.presupuesto_consumido, 6),
            },
        }
    )

    if len(tramos) != len(orden) + 1:
        solucion.marcar_invalida(
            "La planificación no contiene todos los tramos obligatorios.",
            PENALIZACION_BASE,
        )
        return solucion

    capacidad = escenario.limite_recurso("capacidad", float("inf"))
    if solucion.carga_maxima > capacidad + 1e-9:
        solucion.marcar_invalida(
            f"Capacidad insuficiente: carga {solucion.carga_maxima:g} > "
            f"capacidad {capacidad:g}."
        )

    limites = {
        "combustible": (
            solucion.combustible_consumido,
            escenario.limite_recurso("combustible", float("inf")),
            "combustible",
        ),
        "tiempo": (
            solucion.tiempo_consumido,
            escenario.limite_recurso("tiempo", float("inf")),
            "tiempo",
        ),
        "presupuesto": (
            solucion.presupuesto_consumido,
            escenario.limite_recurso("presupuesto", float("inf")),
            "presupuesto",
        ),
    }
    for nombre, (uso, limite, _) in limites.items():
        if uso > limite + 1e-9:
            solucion.marcar_invalida(
                f"Exceso de {nombre}: uso {uso:.2f} > límite {limite:.2f}."
            )

    if not solucion.valida:
        exceso = max(
            0.0,
            solucion.costo_total
            - escenario.limite_recurso("presupuesto", float("inf")),
            0.0,
            solucion.combustible_consumido
            - escenario.limite_recurso("combustible", float("inf")),
            0.0,
            solucion.tiempo_consumido - escenario.limite_recurso("tiempo", float("inf")),
        )
        solucion.penalizacion = max(
            solucion.penalizacion,
            PENALIZACION_BASE + 1_000.0 * len(solucion.violaciones) + 100.0 * exceso,
        )
    return solucion


def planificar_con_buscador(
    escenario: Escenario,
    orden: Iterable[int] | None,
    buscador: Callable,
    evitar: set[tuple[int, int]] | None = None,
    factor_costo: float = 1.0,
    modo: str = "costo",
    max_pasos_por_tramo: int | None = None,
    nombre_algoritmo: str = "",
) -> tuple[Solucion, dict]:
    """Construye una solución completa llamando al buscador para cada tramo."""
    orden = normalizar_orden(escenario, orden)
    evitar = set(evitar or ())
    puntos = [("Inicio", escenario.inicio)]
    puntos += [
        (escenario.obtener_entrega(i).nombre, escenario.obtener_entrega(i).posicion)
        for i in orden
    ]
    puntos.append(("Destino", escenario.destino))

    tramos: list[Tramo] = []
    nodos_expandidos = 0
    nodos_generados = 0
    iteraciones = 0
    for (nombre_o, origen), (nombre_d, destino) in zip(puntos, puntos[1:]):
        resultado = buscador(
            escenario,
            origen,
            destino,
            evitar=evitar,
            factor_costo=factor_costo,
            modo=modo,
            max_pasos=max_pasos_por_tramo,
        )
        nodos_expandidos += resultado.nodos_expandidos
        nodos_generados += resultado.nodos_generados
        iteraciones += resultado.iteraciones
        if not resultado.exito:
            solucion = construir_solucion(escenario, orden, tramos, nombre_algoritmo)
            solucion.marcar_invalida(
                f"No hay ruta entre {nombre_o} y {nombre_d}: {resultado.mensaje}"
            )
            return solucion, {
                "nodos_expandidos": nodos_expandidos,
                "nodos_generados": nodos_generados,
                "iteraciones": iteraciones,
                "tramo_fallido": f"{nombre_o}->{nombre_d}",
            }
        tramos.append(
            Tramo(
                origen_nombre=nombre_o,
                destino_nombre=nombre_d,
                origen=origen,
                destino=destino,
                camino=resultado.camino,
                costo=resultado.costo,
                pasos=max(0, len(resultado.camino) - 1),
                algoritmo=nombre_algoritmo,
            )
        )
    solucion = construir_solucion(escenario, orden, tramos, nombre_algoritmo)
    return solucion, {
        "nodos_expandidos": nodos_expandidos,
        "nodos_generados": nodos_generados,
        "iteraciones": iteraciones,
    }


class PlanificadorRutas:
    """Planificador con caché de tramos óptimos (A* por defecto).

    Las metaheurísticas evalúan muchos órdenes de entrega para el mismo
    escenario.  Cachear los tramos evita repetir búsquedas idénticas y hace
    comparables los presupuestos de evaluación: el número de evaluaciones se
    cuenta en el algoritmo, no en la caché.
    """

    def __init__(
        self,
        escenario: Escenario,
        evitar: set[tuple[int, int]] | None = None,
        factor_costo: float = 1.0,
        modo: str = "costo",
        buscador: Callable | None = None,
    ) -> None:
        self.escenario = escenario
        self.evitar = set(evitar or ())
        self.factor_costo = factor_costo
        self.modo = modo
        self._cache: dict[tuple[tuple[int, int], tuple[int, int]], Tramo | None] = {}
        self._buscador = buscador or self._buscador_astar
        self.nodos_expandidos = 0
        self.nodos_generados = 0
        self.consultas_busqueda = 0

    @staticmethod
    def _buscador_astar(escenario, inicio, fin, **kwargs):
        from algoritmos.busqueda_heuristica.astar import buscar_ruta

        return buscar_ruta(escenario, inicio, fin, **kwargs)

    def _tramo(
        self, origen: tuple[int, int], destino: tuple[int, int], nombre_o: str, nombre_d: str
    ) -> Tramo | None:
        clave = (origen, destino)
        if clave in self._cache:
            return self._cache[clave]
        resultado = self._buscador(
            self.escenario,
            origen,
            destino,
            evitar=self.evitar,
            factor_costo=self.factor_costo,
            modo=self.modo,
            max_pasos=None,
        )
        self.nodos_expandidos += resultado.nodos_expandidos
        self.nodos_generados += resultado.nodos_generados
        self.consultas_busqueda += 1
        if not resultado.exito:
            self._cache[clave] = None
            return None
        tramo = Tramo(
            origen_nombre=nombre_o,
            destino_nombre=nombre_d,
            origen=origen,
            destino=destino,
            camino=resultado.camino,
            costo=resultado.costo,
            pasos=max(0, len(resultado.camino) - 1),
            algoritmo=resultado.algoritmo or "A*",
        )
        self._cache[clave] = tramo
        return tramo

    def evaluar(self, orden: Iterable[int] | None, algoritmo: str = "") -> Solucion:
        orden = normalizar_orden(self.escenario, orden)
        puntos = [("Inicio", self.escenario.inicio)]
        puntos += [
            (self.escenario.obtener_entrega(i).nombre, self.escenario.obtener_entrega(i).posicion)
            for i in orden
        ]
        puntos.append(("Destino", self.escenario.destino))
        tramos: list[Tramo] = []
        for (nombre_o, origen), (nombre_d, destino) in zip(puntos, puntos[1:]):
            tramo = self._tramo(origen, destino, nombre_o, nombre_d)
            if tramo is None:
                solucion = construir_solucion(self.escenario, orden, tramos, algoritmo)
                solucion.marcar_invalida(
                    f"No hay ruta entre {nombre_o} y {nombre_d}."
                )
                return solucion
            tramos.append(tramo)
        return construir_solucion(self.escenario, orden, tramos, algoritmo)

    def distancia(self, origen: tuple[int, int], destino: tuple[int, int]) -> float:
        tramo = self._tramo(origen, destino, "A", "B")
        return tramo.costo if tramo else float("inf")

    def metricas_cache(self) -> dict:
        return {
            "nodos_expandidos_planificador": self.nodos_expandidos,
            "nodos_generados_planificador": self.nodos_generados,
            "busquedas_realizadas": self.consultas_busqueda,
            "tramos_en_cache": len(self._cache),
        }


def medir_tiempo(funcion: Callable, *args, **kwargs) -> tuple[object, float]:
    inicio = time.perf_counter()
    resultado = funcion(*args, **kwargs)
    return resultado, time.perf_counter() - inicio
