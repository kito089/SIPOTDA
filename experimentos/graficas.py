"""Gráficas generadas exclusivamente a partir de CSV experimentales."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from experimentos.metricas import (  # noqa: E402
    a_float,
    a_bool,
    historial_de_fila,
    parametros_de_fila,
    resumir_desde_csv,
)
from gestion_archivos.exportar_resultados import leer_resultados_csv  # noqa: E402


def _cargar(fuentes: Iterable[str | Path]) -> list[dict]:
    filas: list[dict] = []
    for fuente in fuentes:
        filas.extend(leer_resultados_csv(fuente))
    if not filas:
        raise ValueError("No hay datos CSV para graficar.")
    return filas


def _guardar(fig, ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, dpi=140)
    plt.close(fig)
    return ruta


def _resumen_costos(filas: list[dict]) -> list[dict]:
    filas_validas = []
    for fila in filas:
        if "costo" not in fila or not a_bool(fila.get("exito", "True")):
            continue
        if a_float(fila.get("costo")) is not None:
            filas_validas.append(fila)
    return resumir_desde_csv(filas_validas)


def grafica_costos_por_algoritmo(filas: list[dict], ruta: Path) -> Path:
    resumen = [f for f in _resumen_costos(filas) if a_float(f["costo_promedio"]) is not None]
    if not resumen:
        raise ValueError("No hay costos válidos para graficar.")
    nombres = [f["algoritmo"] for f in resumen]
    promedios = [f["costo_promedio"] for f in resumen]
    mejores = [f["costo_mejor"] for f in resumen]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = range(len(nombres))
    ax.bar([i - 0.2 for i in x], promedios, width=0.4, label="Promedio", color="#4472c4")
    ax.bar([i + 0.2 for i in x], mejores, width=0.4, label="Mejor", color="#ed7d31")
    ax.set_xticks(list(x))
    ax.set_xticklabels(nombres, rotation=20, ha="right")
    ax.set_ylabel("Costo")
    ax.set_title("Costo por algoritmo")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def grafica_tiempos_por_algoritmo(filas: list[dict], ruta: Path) -> Path:
    resumen = [f for f in _resumen_costos(filas) if a_float(f["tiempo_promedio"]) is not None]
    if not resumen:
        raise ValueError("No hay tiempos válidos para graficar.")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(
        [f["algoritmo"] for f in resumen],
        [f["tiempo_promedio"] for f in resumen],
        color="#70ad47",
    )
    ax.set_ylabel("Segundos")
    ax.set_title("Tiempo promedio de ejecución")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def grafica_nodos_expandidos(filas: list[dict], ruta: Path) -> Path:
    resumen = [
        f
        for f in _resumen_costos(filas)
        if a_float(f["nodos_expandidos_promedio"]) is not None
        and f["nodos_expandidos_promedio"] > 0
    ]
    if not resumen:
        raise ValueError("No hay nodos expandidos para graficar.")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(
        [f["algoritmo"] for f in resumen],
        [f["nodos_expandidos_promedio"] for f in resumen],
        color="#a5a5a5",
    )
    ax.set_ylabel("Nodos expandidos (promedio)")
    ax.set_title("Nodos expandidos por algoritmo")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def grafica_evaluaciones(filas: list[dict], ruta: Path) -> Path:
    resumen = [
        f
        for f in _resumen_costos(filas)
        if a_float(f["evaluaciones_promedio"]) is not None
        and f["evaluaciones_promedio"] > 0
    ]
    if not resumen:
        raise ValueError("No hay evaluaciones para graficar.")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(
        [f["algoritmo"] for f in resumen],
        [f["evaluaciones_promedio"] for f in resumen],
        color="#7030a0",
    )
    ax.set_ylabel("Evaluaciones de la función objetivo (promedio)")
    ax.set_title("Evaluaciones por algoritmo")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def grafica_distribucion_costos(filas: list[dict], ruta: Path) -> Path:
    grupos: dict[str, list[float]] = defaultdict(list)
    for fila in filas:
        if a_bool(fila.get("exito", "True")):
            costo = a_float(fila.get("costo"))
            if costo is not None:
                grupos[fila.get("algoritmo", "")].append(costo)
    datos = [(nombre, valores) for nombre, valores in grupos.items() if valores]
    if not datos:
        raise ValueError("No hay distribuciones de costo para graficar.")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    try:
        ax.boxplot(
            [valores for _, valores in datos],
            tick_labels=[nombre for nombre, _ in datos],
        )
    except TypeError:
        # Compatibilidad con versiones anteriores de matplotlib.
        ax.boxplot(
            [valores for _, valores in datos],
            labels=[nombre for nombre, _ in datos],
        )
    ax.set_ylabel("Costo")
    ax.set_title("Distribución del costo por algoritmo")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def grafica_convergencia(filas: list[dict], ruta: Path) -> Path:
    grupos: dict[str, list[list[float]]] = defaultdict(list)
    for fila in filas:
        historial = historial_de_fila(fila)
        if len(historial) >= 2:
            grupos[fila.get("algoritmo", "")].append(historial)
    if not grupos:
        raise ValueError("No hay historiales de convergencia para graficar.")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for algoritmo, historiales in grupos.items():
        longitud = min(len(h) for h in historiales)
        if longitud < 2:
            continue
        promedio = [
            sum(h[i] for h in historiales) / len(historiales) for i in range(longitud)
        ]
        ax.plot(range(longitud), promedio, label=algoritmo)
    ax.set_xlabel("Iteración / generación / nivel de temperatura")
    ax.set_ylabel("Mejor costo")
    ax.set_title("Convergencia promedio (datos CSV)")
    ax.legend()
    ax.grid(alpha=0.3)
    return _guardar(fig, ruta)


def grafica_minimax_vs_alfa(filas: list[dict], ruta: Path) -> Path:
    registros = []
    for fila in filas:
        # Formato del CSV comparativo generado por experimento_adversario.
        if "nodos_minimax" in fila or "nodos_alfa_beta" in fila:
            profundidad = a_float(fila.get("profundidad"), 0.0) or 0.0
            nodos_minimax = a_float(fila.get("nodos_minimax"))
            nodos_alfa = a_float(fila.get("nodos_alfa_beta"))
            if nodos_minimax is not None:
                registros.append(
                    {
                        "algoritmo": "minimax",
                        "nodos": nodos_minimax,
                        "profundidad": int(profundidad),
                    }
                )
            if nodos_alfa is not None:
                registros.append(
                    {
                        "algoritmo": "alfa-beta",
                        "nodos": nodos_alfa,
                        "profundidad": int(profundidad),
                    }
                )
            continue
        # Formato de resultados generales con una columna algoritmo.
        nombre = fila.get("algoritmo", "")
        if "minimax" not in nombre.lower():
            continue
        nodos = a_float(fila.get("nodos_visitados"), a_float(fila.get("nodos_minimax")))
        if nodos is None:
            continue
        parametros = parametros_de_fila(fila)
        profundidad = a_float(fila.get("profundidad"), parametros.get("profundidad"))
        registros.append(
            {
                "algoritmo": "alfa-beta" if "alfa" in nombre.lower() else "minimax",
                "nodos": nodos,
                "profundidad": int(profundidad) if profundidad else 0,
            }
        )
    if not registros:
        raise ValueError("No hay datos de Minimax/alfa-beta para graficar.")
    profundidades = sorted({r["profundidad"] for r in registros}) or [0]
    fig, ax = plt.subplots(figsize=(10, 5))
    ancho = 0.35
    x = range(len(profundidades))
    for desplazamiento, algoritmo, color in (
        (-ancho / 2, "minimax", "#c00000"),
        (ancho / 2, "alfa-beta", "#2e75b6"),
    ):
        valores = []
        for profundidad in profundidades:
            nodos = [
                r["nodos"]
                for r in registros
                if r["algoritmo"] == algoritmo and r["profundidad"] == profundidad
            ]
            valores.append(nodos[0] if nodos else 0)
        ax.bar(
            [i + desplazamiento for i in x],
            valores,
            width=ancho,
            label=algoritmo,
            color=color,
        )
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(p) for p in profundidades])
    ax.set_xlabel("Profundidad de búsqueda")
    ax.set_ylabel("Nodos visitados")
    ax.set_title("Minimax vs. poda alfa-beta")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return _guardar(fig, ruta)


def generar_todas_las_graficas(
    fuentes: str | Path | Iterable[str | Path],
    directorio_salida: str | Path,
) -> list[Path]:
    """Genera todas las gráficas posibles y devuelve las rutas creadas."""
    if isinstance(fuentes, (str, Path)):
        fuentes = [fuentes]
    filas = _cargar(fuentes)
    salida = Path(directorio_salida)
    salida.mkdir(parents=True, exist_ok=True)
    tareas = [
        ("costos_por_algoritmo.png", grafica_costos_por_algoritmo),
        ("tiempos_por_algoritmo.png", grafica_tiempos_por_algoritmo),
        ("nodos_expandidos.png", grafica_nodos_expandidos),
        ("evaluaciones.png", grafica_evaluaciones),
        ("distribucion_costos.png", grafica_distribucion_costos),
        ("convergencia.png", grafica_convergencia),
        ("minimax_vs_alfa_beta.png", grafica_minimax_vs_alfa),
    ]
    generadas: list[Path] = []
    for nombre, funcion in tareas:
        try:
            generadas.append(funcion(filas, salida / nombre))
        except (ValueError, IndexError, KeyError):
            continue
    return generadas
