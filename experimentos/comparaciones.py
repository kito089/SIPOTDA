"""Comparaciones entre algoritmos y verificación de Minimax/alfa-beta."""

from __future__ import annotations

from typing import Iterable

from algoritmos.busqueda_adversaria.alfa_beta import ejecutar_alfa_beta
from algoritmos.busqueda_adversaria.minimax import ejecutar_minimax
from algoritmos.busqueda_adversaria.modelo_adversario import crear_configuracion
from experimentos.metricas import resumir_desde_csv
from modelos.escenario import Escenario


def comparar_desde_csv(filas: list[dict]) -> list[dict]:
    """Comparación por algoritmo a partir de filas CSV reales."""
    return resumir_desde_csv(filas)


def comparar_resultados(resultados) -> list[dict]:
    from experimentos.metricas import resumir_resultados

    return resumir_resultados(resultados)


def verificar_equivalencia_adversaria(
    escenario: Escenario,
    profundidades: Iterable[int] = (2, 4, 6),
) -> tuple[list[dict], list, list]:
    """Ejecuta Minimax y alfa-beta con la misma configuración y compara.

    Devuelve ``(filas, resultados_minimax, resultados_alfa_beta)``.
    """
    filas: list[dict] = []
    resultados_minimax = []
    resultados_alfa = []
    for profundidad in profundidades:
        config = crear_configuracion(escenario, int(profundidad))
        minimax = ejecutar_minimax(escenario, configuracion=config)
        alfa = ejecutar_alfa_beta(escenario, configuracion=config)
        resultados_minimax.append(minimax)
        resultados_alfa.append(alfa)
        diferencia = abs(minimax.valor_minimax - alfa.valor_minimax)
        filas.append(
            {
                "profundidad": config.limite_turnos,
                "valor_minimax": round(minimax.valor_minimax, 6),
                "valor_alfa_beta": round(alfa.valor_minimax, 6),
                "diferencia": round(diferencia, 9),
                "iguales": diferencia <= 1e-9,
                "mejor_accion_minimax": minimax.mejor_accion,
                "mejor_accion_alfa_beta": alfa.mejor_accion,
                "nodos_minimax": minimax.nodos_visitados,
                "nodos_alfa_beta": alfa.nodos_visitados,
                "nodos_podados_alfa_beta": alfa.nodos_podados,
                "reduccion_nodos_pct": round(
                    100.0
                    * (minimax.nodos_visitados - alfa.nodos_visitados)
                    / minimax.nodos_visitados,
                    4,
                )
                if minimax.nodos_visitados
                else 0.0,
                "tiempo_minimax": round(minimax.tiempo_ejecucion, 6),
                "tiempo_alfa_beta": round(alfa.tiempo_ejecucion, 6),
            }
        )
    return filas, resultados_minimax, resultados_alfa


def formatear_comparacion(filas: list[dict]) -> str:
    if not filas:
        return "Sin comparaciones."
    encabezado = (
        f"{'Algoritmo':<24}{'Ejec.':>6}{'Mejor':>10}{'Prom.':>10}"
        f"{'Desv.':>10}{'Tiempo':>10}"
    )
    lineas = [encabezado, "-" * len(encabezado)]
    for fila in filas:
        lineas.append(
            f"{fila['algoritmo'][:22]:<24}{fila['ejecuciones']:>6}"
            f"{fila['costo_mejor']:>10.2f}{fila['costo_promedio']:>10.2f}"
            f"{fila['desviacion_costo']:>10.2f}{fila['tiempo_promedio']:>10.4f}"
        )
    return "\n".join(lineas)
