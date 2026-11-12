"""Orquestación de experimentos reproducibles y planificación final."""

from __future__ import annotations

import json
import random
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from algoritmos.busqueda_adversaria.alfa_beta import ejecutar_alfa_beta
from algoritmos.busqueda_adversaria.minimax import ejecutar_minimax
from algoritmos.busqueda_local.hill_climbing import reinicios_hill_climbing
from algoritmos.metaheuristicas.algoritmo_genetico import algoritmo_genetico
from algoritmos.metaheuristicas.recocido_simulado import recocido_simulado
from algoritmos.registro import ejecutar_busqueda_heuristica
from algoritmos.teoria_juegos.juego_estrategico import analizar_juego
from experimentos.comparaciones import verificar_equivalencia_adversaria
from experimentos.graficas import generar_todas_las_graficas
from experimentos.metricas import resumir_resultados
from gestion_archivos.exportar_resultados import (
    exportar_filas_csv,
    exportar_juego_csv,
    exportar_resultados_csv,
    guardar_planificacion_json,
)
from gestion_archivos.lector_json import cargar_escenario
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


RAIZ = Path(__file__).resolve().parent.parent
DIR_RESULTADOS = RAIZ / "resultados"
DIR_CSV = DIR_RESULTADOS / "csv"
DIR_GRAFICAS = DIR_RESULTADOS / "graficas"
DIR_CSV.mkdir(parents=True, exist_ok=True)
DIR_GRAFICAS.mkdir(parents=True, exist_ok=True)

PARAMETROS_PREDETERMINADOS = {
    "hill_climbing": {
        "max_iteraciones": 500,
        "permitir_mesetas": False,
        "max_mesetas": 20,
    },
    "recocido_simulado": {
        "temperatura_inicial": 50.0,
        "temperatura_final": 0.01,
        "enfriamiento": 0.95,
        "iteraciones_por_temperatura": 15,
        "max_iteraciones": 2500,
    },
    "algoritmo_genetico": {
        "tamano_poblacion": 30,
        "generaciones": 80,
        "prob_cruza": 0.85,
        "prob_mutacion": 0.2,
        "elitismo": 2,
        "tamano_torneo": 3,
        "max_evaluaciones": 15000,
    },
    "experimentos": {
        "repeticiones_metaheuristicas": 20,
        "num_inicios_hill": 10,
        "semilla_base": 2026,
        "profundidades_adversarias": [2, 4, 6],
    },
}


def _combinar_parametros(parametros: dict | None) -> dict:
    base = json.loads(json.dumps(PARAMETROS_PREDETERMINADOS))
    for seccion, valores in (parametros or {}).items():
        if isinstance(valores, dict) and isinstance(base.get(seccion), dict):
            base[seccion].update(valores)
        else:
            base[seccion] = valores
    return base


def _guardar_historial(resultados: Iterable[ResultadoEjecucion]) -> None:
    resultados = list(resultados)
    if not resultados:
        return
    exportar_resultados_csv(
        resultados, DIR_CSV / "historial_ejecuciones.csv", modo="anexar"
    )


def _nombre_archivo(escenario: Escenario, prefijo: str, sufijo: str = "csv") -> Path:
    identificador = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in escenario.id
    )
    return DIR_CSV / f"{prefijo}_{identificador}.{sufijo}"


def experimento_busqueda_heuristica(
    escenario: Escenario,
    parametros: dict | None = None,
    guardar: bool = True,
) -> tuple[list[ResultadoEjecucion], Path | None]:
    """Prueba Greedy y A* con el mismo orden y escenario."""
    resultados = [
        ejecutar_busqueda_heuristica(escenario, "Greedy Best-First", parametros=parametros),
        ejecutar_busqueda_heuristica(escenario, "A*", parametros=parametros),
    ]
    ruta = _nombre_archivo(escenario, "heuristicas") if guardar else None
    if ruta:
        exportar_resultados_csv(resultados, ruta)
        _guardar_historial(resultados)
    return resultados, ruta


def experimento_heuristico_multiples(
    escenarios: Iterable[Escenario],
    parametros: dict | None = None,
) -> tuple[list[ResultadoEjecucion], Path]:
    """Ejecuta la comparación heurística en varios escenarios documentados."""
    resultados: list[ResultadoEjecucion] = []
    for escenario in escenarios:
        parciales, _ = experimento_busqueda_heuristica(
            escenario, parametros=parametros, guardar=False
        )
        resultados.extend(parciales)
    ruta = DIR_CSV / "heuristicas_multiples_escenarios.csv"
    exportar_resultados_csv(resultados, ruta)
    _guardar_historial(resultados)
    return resultados, ruta


def experimento_hill_climbing(
    escenario: Escenario,
    parametros: dict | None = None,
    num_inicios: int | None = None,
    semilla_base: int | None = None,
) -> tuple[list[ResultadoEjecucion], dict, Path, Path]:
    parametros = _combinar_parametros(parametros)
    hc = parametros["hill_climbing"]
    experimentos = parametros["experimentos"]
    num_inicios = int(num_inicios or experimentos["num_inicios_hill"])
    semilla_base = int(
        experimentos["semilla_base"] if semilla_base is None else semilla_base
    )
    resultados, resumen = reinicios_hill_climbing(
        escenario,
        num_inicios=num_inicios,
        semilla_base=semilla_base,
        max_iteraciones=int(hc["max_iteraciones"]),
        permitir_mesetas=bool(hc["permitir_mesetas"]),
        max_mesetas=int(hc["max_mesetas"]),
    )
    ruta = _nombre_archivo(escenario, "hill_climbing")
    ruta_resumen = DIR_CSV / "resumen_hill_climbing.csv"
    exportar_resultados_csv(resultados, ruta)
    _guardar_historial(resultados)
    fila = dict(resumen)
    fila["fecha"] = datetime.now().isoformat(timespec="seconds")
    fila["archivo"] = str(ruta)
    exportar_filas_csv([fila], ruta_resumen, list(fila.keys()))
    return resultados, resumen, ruta, ruta_resumen


def experimento_metaheuristicas(
    escenario: Escenario,
    parametros: dict | None = None,
    repeticiones: int | None = None,
    semilla_base: int | None = None,
) -> tuple[list[ResultadoEjecucion], list[dict], Path, Path]:
    """Ejecuta recocido y genético con semillas pareadas y repeticiones."""
    parametros = _combinar_parametros(parametros)
    experimentos = parametros["experimentos"]
    repeticiones = int(
        repeticiones or experimentos["repeticiones_metaheuristicas"]
    )
    if repeticiones < 1:
        raise ValueError("Las repeticiones deben ser al menos 1")
    semilla_base = int(
        semilla_base if semilla_base is not None else experimentos["semilla_base"]
    )
    rng = random.Random(semilla_base)
    semillas = [rng.randrange(0, 2**31 - 1) for _ in range(repeticiones)]
    resultados: list[ResultadoEjecucion] = []
    for indice, semilla in enumerate(semillas):
        recocido = recocido_simulado(
            escenario,
            semilla=semilla,
            **parametros["recocido_simulado"],
        )
        recocido.parametros.update(
            {
                "repeticion": indice,
                "semilla_base": semilla_base,
                "presupuesto": parametros["recocido_simulado"],
            }
        )
        genetico = algoritmo_genetico(
            escenario,
            semilla=semilla,
            **parametros["algoritmo_genetico"],
        )
        genetico.parametros.update(
            {
                "repeticion": indice,
                "semilla_base": semilla_base,
                "presupuesto": parametros["algoritmo_genetico"],
            }
        )
        resultados.extend([recocido, genetico])
    ruta = _nombre_archivo(escenario, "metaheuristicas")
    resumen = resumir_resultados(resultados)
    for fila in resumen:
        fila["escenario"] = escenario.id
        fila["repeticiones"] = repeticiones
        fila["semilla_base"] = semilla_base
        fila["presupuesto_recocido"] = json.dumps(parametros["recocido_simulado"])
        fila["presupuesto_genetico"] = json.dumps(parametros["algoritmo_genetico"])
    ruta_resumen = DIR_CSV / "resumen_metaheuristicas.csv"
    exportar_resultados_csv(resultados, ruta)
    _guardar_historial(resultados)
    exportar_filas_csv(resumen, ruta_resumen, list(resumen[0].keys()) if resumen else [])
    return resultados, resumen, ruta, ruta_resumen


def experimento_adversario(
    escenario: Escenario,
    profundidades: Iterable[int] | None = None,
    parametros: dict | None = None,
) -> tuple[list[dict], list, list, Path]:
    parametros = _combinar_parametros(parametros)
    profundidades = list(
        profundidades
        or parametros["experimentos"]["profundidades_adversarias"]
    )
    filas, minimax_resultados, alfa_resultados = verificar_equivalencia_adversaria(
        escenario, profundidades
    )
    ruta = _nombre_archivo(escenario, "adversaria")
    exportar_filas_csv(filas, ruta, list(filas[0].keys()))
    return filas, minimax_resultados, alfa_resultados, ruta


def experimento_juego(escenario: Escenario) -> tuple[Any, Path, Path]:
    juego = analizar_juego(escenario)
    ruta_csv = _nombre_archivo(escenario, "juego_matriz")
    ruta_json = _nombre_archivo(escenario, "juego_analisis", "json")
    exportar_juego_csv(juego, ruta_csv)
    guardar_planificacion_json(juego.a_dict(), ruta_json)
    return juego, ruta_csv, ruta_json


def _mejor_por_algoritmo(resultados: list[ResultadoEjecucion]) -> dict[str, ResultadoEjecucion]:
    mejores: dict[str, ResultadoEjecucion] = {}
    for resultado in resultados:
        if resultado.solucion is None:
            continue
        actual = mejores.get(resultado.algoritmo)
        if actual is None or resultado.solucion.costo_objetivo < actual.solucion.costo_objetivo:
            mejores[resultado.algoritmo] = resultado
    return mejores


def construir_planificacion_final(
    escenario: Escenario,
    resultados: list[ResultadoEjecucion],
    juego,
    minimax,
    alfa_beta,
) -> dict:
    """Integra rutas, orden, estrategia y riesgo en una planificación válida."""
    validos = [
        r
        for r in resultados
        if r.solucion is not None and r.solucion.valida and r.exito
    ]
    if not validos:
        raise ValueError(
            "No hay soluciones válidas para construir la planificación final. "
            "Ajuste recursos o restricciones del escenario."
        )
    mejor = min(validos, key=lambda r: (r.costo, r.algoritmo))
    solucion = mejor.solucion
    mejores = _mejor_por_algoritmo(validos)
    estado_riesgo = alfa_beta.estado_final if alfa_beta else {}
    riesgo = float(estado_riesgo.get("riesgo", 0.0))
    impacto = float(estado_riesgo.get("impacto", 0.0))
    bloqueos = int(estado_riesgo.get("bloqueos", 0))
    if riesgo >= 0.16 or bloqueos >= 2:
        nivel_riesgo = "alto"
    elif riesgo >= 0.08 or bloqueos >= 1:
        nivel_riesgo = "medio"
    else:
        nivel_riesgo = "bajo"
    orden = solucion.orden_entregas
    nombres = [
        escenario.obtener_entrega(i).nombre
        for i in orden
        if escenario.obtener_entrega(i) is not None
    ]
    plan = {
        "id_plan": f"plan-{uuid.uuid4().hex[:10]}",
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "escenario_id": escenario.id,
        "nombre_escenario": escenario.nombre,
        "plan_valido": True,
        "orden_entregas": orden,
        "nombres_entregas": nombres,
        "rutas": [tramo.a_dict() for tramo in solucion.rutas],
        "ruta_coordenadas": [list(p) for p in solucion.ruta_coordenadas],
        "costo_total": round(solucion.costo_total, 6),
        "longitud_ruta": solucion.longitud_ruta,
        "pasos": solucion.pasos,
        "recursos_utilizados": {
            "combustible": round(solucion.combustible_consumido, 6),
            "capacidad": round(solucion.carga_maxima, 6),
            "tiempo": round(solucion.tiempo_consumido, 6),
            "presupuesto": round(solucion.presupuesto_consumido, 6),
        },
        "restricciones": {
            "capacidad": escenario.limite_recurso("capacidad"),
            "combustible": escenario.limite_recurso("combustible"),
            "tiempo": escenario.limite_recurso("tiempo"),
            "presupuesto": escenario.limite_recurso("presupuesto"),
            "permitir_diagonal": escenario.permitir_diagonal,
        },
        "validaciones": {
            "errores_escenario": escenario.validar(),
            "violaciones_solucion": list(solucion.violaciones),
            "solucion_valida": solucion.valida,
        },
        "riesgos_competidor": {
            "nivel": nivel_riesgo,
            "riesgo_acumulado": round(riesgo, 6),
            "impacto_costos": round(impacto, 6),
            "bloqueos": bloqueos,
            "accion_empresa_recomendada": alfa_beta.mejor_accion if alfa_beta else None,
            "linea_principal": alfa_beta.linea_principal if alfa_beta else [],
            "valor_minimax": round(alfa_beta.valor_minimax, 6) if alfa_beta else None,
        },
        "estrategia_recomendada": {
            **dict(juego.recomendacion),
            "equilibrios_nash": juego.analisis["equilibrios_nash"],
            "nota": (
                "La estrategia del juego orienta la postura operativa; las rutas "
                "concretas provienen de la mejor solución válida de los algoritmos."
            ),
        },
        "fuentes": {
            "solucion_base": mejor.a_dict(),
            "mejores_por_algoritmo": {
                algoritmo: resultado.a_dict()
                for algoritmo, resultado in mejores.items()
            },
            "ids_ejecucion": [r.id_ejecucion for r in validos],
            "juego": {
                "recomendacion": juego.recomendacion,
                "equilibrios_nash": juego.analisis["equilibrios_nash"],
            },
            "minimax": minimax.a_dict() if minimax else None,
            "alfa_beta": alfa_beta.a_dict() if alfa_beta else None,
        },
        "justificacion": [
            f"Se eligió el orden {orden} con costo {solucion.costo_total:.2f}, "
            f"proveniente de {mejor.algoritmo}.",
            "Las rutas de cada tramo fueron calculadas con A* sobre el mismo "
            "escenario y respetan obstáculos y costos variables.",
            "Hill Climbing y las metaheurísticas aportan evidencia de calidad y "
            "estabilidad del orden de entrega; se conserva la mejor solución válida.",
            f"El juego estratégico recomienda '{juego.recomendacion['estrategia_empresa']}' "
            f"frente a '{juego.recomendacion['estrategia_competidor']}'.",
            f"La búsqueda adversaria sugiere '{alfa_beta.mejor_accion if alfa_beta else 'n/d'}' "
            f"con riesgo {nivel_riesgo}.",
        ],
    }
    return plan


def ejecutar_todo(
    escenario: Escenario,
    parametros: dict | None = None,
    repeticiones: int | None = None,
    num_inicios: int | None = None,
    profundidades: Iterable[int] | None = None,
    generar_graficas: bool = True,
    guardar: bool = True,
) -> dict:
    """Ejecuta el flujo completo de integración y genera una planificación.

    Cada módulo se ejecuta de forma aislada: si uno falla se registra el error
    y se continúa con los demás cuando es seguro.  La planificación final solo
    se construye si existen resultados válidos y el juego estratégico terminó.
    """
    parametros = _combinar_parametros(parametros)
    inicio = time.perf_counter()
    errores: list[str] = []

    def intentar(nombre: str, funcion, defecto):
        try:
            return funcion()
        except Exception as exc:  # noqa: BLE001 - se documenta y se continúa
            errores.append(f"{nombre}: {exc}")
            return defecto

    heuristicos, ruta_heuristicos = intentar(
        "heurísticas",
        lambda: experimento_busqueda_heuristica(
            escenario, parametros=parametros, guardar=guardar
        ),
        ([], None),
    )
    resultados_hc, resumen_hc, ruta_hc, ruta_resumen_hc = intentar(
        "Hill Climbing",
        lambda: experimento_hill_climbing(
            escenario,
            parametros=parametros,
            num_inicios=num_inicios,
            semilla_base=parametros["experimentos"]["semilla_base"],
        ),
        ([], {}, None, None),
    )
    resultados_meta, resumen_meta, ruta_meta, ruta_resumen_meta = intentar(
        "metaheurísticas",
        lambda: experimento_metaheuristicas(
            escenario,
            parametros=parametros,
            repeticiones=repeticiones,
            semilla_base=parametros["experimentos"]["semilla_base"],
        ),
        ([], [], None, None),
    )
    juego, ruta_juego_csv, ruta_juego_json = intentar(
        "juego estratégico",
        lambda: experimento_juego(escenario),
        (None, None, None),
    )
    filas_adv, minimax_resultados, alfa_resultados, ruta_adv = intentar(
        "búsqueda adversaria",
        lambda: experimento_adversario(
            escenario,
            profundidades=profundidades,
            parametros=parametros,
        ),
        ([], [], [], None),
    )
    todos = heuristicos + resultados_hc + resultados_meta
    if not todos:
        detalle = "; ".join(errores) or "ningún módulo produjo resultados"
        raise ValueError(f"No se pudo ejecutar ningún módulo: {detalle}")

    ruta_completa = _nombre_archivo(escenario, "resultados_completos")
    if guardar:
        exportar_resultados_csv(todos, ruta_completa)
    resumen = resumir_resultados(todos)
    for fila in resumen:
        fila["escenario"] = escenario.id
    ruta_resumen = DIR_CSV / "resumen_comparacion.csv"
    if guardar:
        exportar_filas_csv(
            resumen, ruta_resumen, list(resumen[0].keys()) if resumen else []
        )

    # Se usa la ejecución alfa-beta de mayor profundidad como referencia de
    # riesgo para la planificación final.
    minimax_ref = minimax_resultados[-1] if minimax_resultados else None
    alfa_ref = alfa_resultados[-1] if alfa_resultados else None
    plan = None
    if juego is not None:
        try:
            plan = construir_planificacion_final(
                escenario, todos, juego, minimax_ref, alfa_ref
            )
        except Exception as exc:  # noqa: BLE001 - la planificación es opcional
            errores.append(f"planificación final: {exc}")
    else:
        errores.append("planificación final: no se generó el juego estratégico")

    ruta_plan = DIR_RESULTADOS / "planificacion_final.json"
    if guardar and plan is not None:
        guardar_planificacion_json(plan, ruta_plan)

    graficas: list[Path] = []
    if generar_graficas and guardar:
        fuentes = [ruta_completa, ruta_adv]
        fuentes = [f for f in fuentes if f and Path(f).exists()]
        try:
            graficas = generar_todas_las_graficas(fuentes, DIR_GRAFICAS)
        except (ValueError, OSError):
            graficas = []
    return {
        "escenario": escenario,
        "resultados": todos,
        "heuristicos": heuristicos,
        "hill_climbing": resultados_hc,
        "metaheuristicas": resultados_meta,
        "resumen_hill_climbing": resumen_hc,
        "resumen_metaheuristicas": resumen_meta,
        "resumen_general": resumen,
        "juego": juego,
        "adversaria": {
            "filas": filas_adv,
            "minimax": minimax_resultados,
            "alfa_beta": alfa_resultados,
        },
        "plan": plan,
        "errores": errores,
        "archivos": {
            "heuristicos": ruta_heuristicos,
            "hill_climbing": ruta_hc,
            "resumen_hill_climbing": ruta_resumen_hc,
            "metaheuristicas": ruta_meta,
            "resumen_metaheuristicas": ruta_resumen_meta,
            "resultados_completos": ruta_completa,
            "resumen_comparacion": ruta_resumen,
            "juego_csv": ruta_juego_csv,
            "juego_json": ruta_juego_json,
            "adversaria": ruta_adv,
            "planificacion": ruta_plan if (guardar and plan is not None) else None,
            "graficas": graficas,
        },
        "tiempo_total": time.perf_counter() - inicio,
    }
