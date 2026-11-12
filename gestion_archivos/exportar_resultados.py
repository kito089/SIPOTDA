"""Exportación de resultados experimentales a CSV y planificación a JSON."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from modelos.resultados import COLUMNAS_CSV, ResultadoEjecucion

from .errores import ErrorArchivo


def _escribir_csv(filas: list[dict], columnas: list[str], ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(
        prefix=ruta.stem + "_", suffix=".tmp", dir=str(ruta.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore")
            escritor.writeheader()
            for fila in filas:
                escritor.writerow(fila)
        os.replace(temporal, ruta)
    except OSError as exc:
        if os.path.exists(temporal):
            os.unlink(temporal)
        raise ErrorArchivo(f"No se pudo escribir {ruta}: {exc}") from exc
    return ruta


def exportar_resultados_csv(
    resultados: Iterable[ResultadoEjecucion],
    ruta: str | Path,
    modo: str = "sobrescribir",
) -> Path:
    """Guarda resultados con el formato común de columnas.

    ``modo='anexar'`` añade filas al archivo existente (sin repetir cabecera).
    """
    path = Path(ruta)
    filas = [resultado.a_fila_csv() for resultado in resultados]
    if modo not in {"sobrescribir", "anexar"}:
        raise ValueError("modo debe ser 'sobrescribir' o 'anexar'")
    if modo == "sobrescribir":
        return _escribir_csv(filas, COLUMNAS_CSV, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existe = path.exists()
    try:
        with path.open("a", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_CSV, extrasaction="ignore")
            if not existe or path.stat().st_size == 0:
                escritor.writeheader()
            for fila in filas:
                escritor.writerow(fila)
    except OSError as exc:
        raise ErrorArchivo(f"No se pudo anexar a {path}: {exc}") from exc
    return path


def exportar_filas_csv(
    filas: Iterable[dict],
    ruta: str | Path,
    columnas: list[str] | None = None,
) -> Path:
    """Exporta filas arbitrarias (resúmenes, comparaciones, juego)."""
    filas = list(filas)
    if not filas:
        columnas = columnas or []
    else:
        columnas = columnas or list(filas[0].keys())
    return _escribir_csv(filas, columnas, Path(ruta))


def leer_resultados_csv(ruta: str | Path) -> list[dict]:
    path = Path(ruta)
    if not path.exists():
        raise ErrorArchivo(f"No existe el CSV de resultados: {path}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as archivo:
            return list(csv.DictReader(archivo))
    except OSError as exc:
        raise ErrorArchivo(f"No se pudo leer {path}: {exc}") from exc


def guardar_planificacion_json(plan: dict, ruta: str | Path) -> Path:
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(
        prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(plan, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.replace(temporal, path)
    except OSError as exc:
        if os.path.exists(temporal):
            os.unlink(temporal)
        raise ErrorArchivo(f"No se pudo guardar {path}: {exc}") from exc
    return path


def exportar_juego_csv(juego, ruta: str | Path) -> Path:
    filas = []
    for celda in juego.matriz:
        filas.append(
            {
                "empresa": celda["empresa"],
                "competidor": celda["competidor"],
                "pago_empresa": celda["pago_empresa"],
                "pago_competidor": celda["pago_competidor"],
                "costo_efectivo": celda["detalle"]["costo_efectivo"],
                "riesgo": celda["detalle"]["riesgo"],
                "evitar": json.dumps(celda["detalle"].get("evitar", [])),
            }
        )
    return exportar_filas_csv(
        filas,
        ruta,
        ["empresa", "competidor", "pago_empresa", "pago_competidor", "costo_efectivo", "riesgo", "evitar"],
    )
