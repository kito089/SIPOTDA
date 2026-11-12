"""Cálculo de métricas experimentales comunes."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from typing import Any, Iterable


def a_float(valor, defecto: float | None = None) -> float | None:
    try:
        if valor is None or valor == "":
            return defecto
        numero = float(valor)
        return numero if math.isfinite(numero) else defecto
    except (TypeError, ValueError):
        return defecto


def a_bool(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    return str(valor).strip().lower() in {"true", "1", "si", "sí", "yes"}


def estadisticas(valores: Iterable[float]) -> dict[str, float | int]:
    datos = [float(v) for v in valores if v is not None and math.isfinite(float(v))]
    if not datos:
        return {
            "n": 0,
            "minimo": float("nan"),
            "maximo": float("nan"),
            "promedio": float("nan"),
            "desviacion": float("nan"),
            "mediana": float("nan"),
        }
    return {
        "n": len(datos),
        "minimo": min(datos),
        "maximo": max(datos),
        "promedio": statistics.fmean(datos),
        "desviacion": statistics.stdev(datos) if len(datos) > 1 else 0.0,
        "mediana": statistics.median(datos),
    }


def _resumen_grupo(algoritmo: str, registros: list[dict]) -> dict:
    exitos = [r for r in registros if r["exito"]]
    base = exitos or registros
    costos = [r["costo"] for r in base]
    tiempos = [r["tiempo"] for r in base]
    evaluaciones = [r["evaluaciones"] for r in base]
    nodos = [r["nodos"] for r in base]
    podados = [r["podados"] for r in base]
    est = estadisticas(costos)
    return {
        "algoritmo": algoritmo,
        "ejecuciones": len(registros),
        "exitos": len(exitos),
        "costo_mejor": est["minimo"],
        "costo_promedio": est["promedio"],
        "desviacion_costo": est["desviacion"],
        "costo_mediana": est["mediana"],
        "tiempo_promedio": statistics.fmean(tiempos) if tiempos else float("nan"),
        "evaluaciones_promedio": statistics.fmean(evaluaciones)
        if evaluaciones
        else float("nan"),
        "nodos_expandidos_promedio": statistics.fmean(nodos) if nodos else float("nan"),
        "nodos_podados_promedio": statistics.fmean(podados) if podados else float("nan"),
        "semillas": ",".join(str(r["semilla"]) for r in registros if r["semilla"] != ""),
    }


def resumir_resultados(resultados) -> list[dict]:
    """Resume objetos ResultadoEjecucion agrupados por algoritmo."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in resultados:
        grupos[r.algoritmo].append(
            {
                "exito": bool(r.exito),
                "costo": float(r.costo) if r.costo != float("inf") else float("nan"),
                "tiempo": float(r.tiempo_ejecucion),
                "evaluaciones": a_float(r.metricas.get("evaluaciones"), 0.0) or 0.0,
                "nodos": a_float(r.metricas.get("nodos_expandidos"), 0.0) or 0.0,
                "podados": a_float(r.metricas.get("nodos_podados"), 0.0) or 0.0,
                "semilla": "" if r.semilla is None else r.semilla,
            }
        )
    return [_resumen_grupo(algoritmo, registros) for algoritmo, registros in grupos.items()]


def resumir_desde_csv(filas: list[dict]) -> list[dict]:
    """Resume filas leídas de un CSV de resultados."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for fila in filas:
        algoritmo = fila.get("algoritmo", "")
        grupos[algoritmo].append(
            {
                "exito": a_bool(fila.get("exito")),
                "costo": a_float(fila.get("costo"), float("nan")),
                "tiempo": a_float(fila.get("tiempo_ejecucion"), 0.0) or 0.0,
                "evaluaciones": a_float(fila.get("evaluaciones"), 0.0) or 0.0,
                "nodos": a_float(fila.get("nodos_expandidos"), 0.0) or 0.0,
                "podados": a_float(fila.get("nodos_podados"), 0.0) or 0.0,
                "semilla": fila.get("semilla", ""),
            }
        )
    return [_resumen_grupo(algoritmo, registros) for algoritmo, registros in grupos.items()]


def historial_de_fila(fila: dict) -> list[float]:
    texto = fila.get("historial_costos") or "[]"
    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return []
    return [float(x) for x in datos if isinstance(x, (int, float))]


def metricas_extra(fila: dict) -> dict:
    texto = fila.get("metricas_extra") or "{}"
    try:
        datos = json.loads(texto)
        return datos if isinstance(datos, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def parametros_de_fila(fila: dict) -> dict:
    texto = fila.get("parametros") or "{}"
    try:
        datos = json.loads(texto)
        return datos if isinstance(datos, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def formatear_tabla_resumen(resumen: list[dict]) -> str:
    if not resumen:
        return "Sin resultados."
    encabezado = (
        f"{'Algoritmo':<24}{'Ejec.':>6}{'Éxitos':>8}{'Mejor':>10}"
        f"{'Prom.':>10}{'Desv.':>10}{'Tiempo':>10}"
    )
    lineas = [encabezado, "-" * len(encabezado)]
    for fila in resumen:
        lineas.append(
            f"{fila['algoritmo'][:22]:<24}{fila['ejecuciones']:>6}{fila['exitos']:>8}"
            f"{fila['costo_mejor']:>10.2f}{fila['costo_promedio']:>10.2f}"
            f"{fila['desviacion_costo']:>10.2f}{fila['tiempo_promedio']:>10.4f}"
        )
    return "\n".join(lineas)
