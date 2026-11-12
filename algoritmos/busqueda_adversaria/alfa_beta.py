"""Minimax con poda alfa-beta.

alfa es el mejor valor que MAX puede garantizar hasta el momento; beta es el
mejor valor que MIN puede garantizar.  Si en un nodo beta <= alfa, la rama
restante no puede influir en la decisión del ancestro y se poda.  La poda no
cambia el valor minimax: solo evita evaluar ramas que ya no pueden ser elegidas.
"""

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


def _alfa_beta(
    config: ConfiguracionAdversario,
    estado: EstadoAdversario,
    profundidad: int,
    es_max: bool,
    alfa: float,
    beta: float,
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
        for indice, accion in enumerate(acciones):
            nuevo = transicion(config, estado, accion)
            valor, linea = _alfa_beta(
                config, nuevo, profundidad - 1, False, alfa, beta, contadores
            )
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_linea = [accion] + linea
            alfa = max(alfa, mejor_valor)
            if beta <= alfa:
                # Las acciones restantes de este nodo MAX no pueden mejorar el
                # valor que ya ofrece una rama anterior para MIN.
                contadores["podados"] += len(acciones) - indice - 1
                break
        return mejor_valor, mejor_linea

    mejor_valor = math.inf
    mejor_linea = []
    for indice, accion in enumerate(acciones):
        nuevo = transicion(config, estado, accion)
        valor, linea = _alfa_beta(
            config, nuevo, profundidad - 1, True, alfa, beta, contadores
        )
        if valor < mejor_valor:
            mejor_valor = valor
            mejor_linea = [accion] + linea
        beta = min(beta, mejor_valor)
        if beta <= alfa:
            contadores["podados"] += len(acciones) - indice - 1
            break
    return mejor_valor, mejor_linea


def ejecutar_alfa_beta(
    escenario: Escenario,
    profundidad: int | None = None,
    configuracion: ConfiguracionAdversario | None = None,
) -> ResultadoAdversario:
    """Resuelve el árbol de Minimax con poda alfa-beta."""
    config = configuracion or crear_configuracion(escenario, profundidad)
    estado_inicial = crear_estado_inicial(config)
    contadores = {"visitados": 0, "hojas": 0, "podados": 0}
    inicio = time.perf_counter()
    valor, linea = _alfa_beta(
        config,
        estado_inicial,
        config.limite_turnos,
        True,
        -math.inf,
        math.inf,
        contadores,
    )
    tiempo = time.perf_counter() - inicio

    estado_final = estado_inicial
    for accion in linea:
        estado_final = transicion(config, estado_final, accion)
    mejor_accion = linea[0] if linea else None

    return ResultadoAdversario(
        algoritmo="Minimax con poda alfa-beta",
        escenario_id=config.escenario_id,
        nombre_escenario=config.nombre_escenario,
        profundidad=config.limite_turnos,
        valor_minimax=valor,
        mejor_accion=mejor_accion,
        linea_principal=linea,
        nodos_visitados=contadores["visitados"],
        nodos_podados=contadores["podados"],
        tiempo_ejecucion=tiempo,
        exito=bool(linea),
        mensaje="Árbol podado evaluado" if linea else "No hay acciones disponibles",
        estado_raiz=estado_inicial.a_dict(),
        estado_final=estado_final.a_dict(),
        configuracion=config.a_dict(),
        metricas={
            "hojas_evaluadas": contadores["hojas"],
            "factor_ramificacion": len(acciones_legales(config, estado_inicial)),
            "nodos_por_nivel": contadores["visitados"],
            "porcentaje_podado": (
                100.0 * contadores["podados"] / (contadores["visitados"] + contadores["podados"])
                if (contadores["visitados"] + contadores["podados"])
                else 0.0
            ),
        },
    )
