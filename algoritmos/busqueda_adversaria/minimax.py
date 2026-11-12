"""Algoritmo Minimax sin poda para el subproblema adversario."""

from __future__ import annotations

import math
import time

from algoritmos.busqueda_adversaria.modelo_adversario import (
    ConfiguracionAdversario,
    EstadoAdversario,
    ResultadoAdversario,
    acciones_legales,
    crear_configuracion,
    crear_estado_inicial,
    es_terminal,
    evaluar_estado,
    transicion,
)
from modelos.escenario import Escenario


def _minimax(
    config: ConfiguracionAdversario,
    estado: EstadoAdversario,
    profundidad: int,
    es_max: bool,
    contadores: dict,
) -> tuple[float, list[str]]:
    contadores["visitados"] += 1
    terminal = es_terminal(config, estado)
    if terminal or profundidad <= 0:
        contadores["hojas"] += 1
        return evaluar_estado(config, estado, aproximada=not terminal), []

    acciones = acciones_legales(config, estado)
    if not acciones:
        contadores["hojas"] += 1
        return evaluar_estado(config, estado, aproximada=not terminal), []

    if es_max:
        mejor_valor = -math.inf
        mejor_linea: list[str] = []
        for accion in acciones:
            nuevo = transicion(config, estado, accion)
            valor, linea = _minimax(config, nuevo, profundidad - 1, False, contadores)
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_linea = [accion] + linea
        return mejor_valor, mejor_linea

    mejor_valor = math.inf
    mejor_linea = []
    for accion in acciones:
        nuevo = transicion(config, estado, accion)
        valor, linea = _minimax(config, nuevo, profundidad - 1, True, contadores)
        if valor < mejor_valor:
            mejor_valor = valor
            mejor_linea = [accion] + linea
    return mejor_valor, mejor_linea


def ejecutar_minimax(
    escenario: Escenario,
    profundidad: int | None = None,
    configuracion: ConfiguracionAdversario | None = None,
) -> ResultadoAdversario:
    """Resuelve el árbol completo de Minimax y registra sus métricas."""
    config = configuracion or crear_configuracion(escenario, profundidad)
    estado_inicial = crear_estado_inicial(config)
    contadores = {"visitados": 0, "hojas": 0}
    inicio = time.perf_counter()
    valor, linea = _minimax(
        config, estado_inicial, config.limite_turnos, True, contadores
    )
    tiempo = time.perf_counter() - inicio

    estado_final = estado_inicial
    for accion in linea:
        estado_final = transicion(config, estado_final, accion)
    mejor_accion = linea[0] if linea else None

    return ResultadoAdversario(
        algoritmo="Minimax",
        escenario_id=config.escenario_id,
        nombre_escenario=config.nombre_escenario,
        profundidad=config.limite_turnos,
        valor_minimax=valor,
        mejor_accion=mejor_accion,
        linea_principal=linea,
        nodos_visitados=contadores["visitados"],
        nodos_podados=0,
        tiempo_ejecucion=tiempo,
        exito=bool(linea),
        mensaje="Árbol completo evaluado" if linea else "No hay acciones disponibles",
        estado_raiz=estado_inicial.a_dict(),
        estado_final=estado_final.a_dict(),
        configuracion=config.a_dict(),
        metricas={
            "hojas_evaluadas": contadores["hojas"],
            "factor_ramificacion": len(acciones_legales(config, estado_inicial)),
            "nodos_por_nivel": contadores["visitados"],
        },
    )
