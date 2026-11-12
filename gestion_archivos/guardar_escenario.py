"""Guardado seguro de escenarios y configuraciones JSON."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from modelos.escenario import Escenario

from .errores import ErrorArchivo, ErrorSobrescritura


def guardar_json(
    datos: dict,
    ruta: str | Path,
    sobrescribir: bool = False,
) -> Path:
    """Escribe JSON de forma atómica.

    Si el archivo existe y ``sobrescribir`` es falso se lanza
    :class:`ErrorSobrescritura` para evitar pérdidas accidentales.
    """
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not sobrescribir:
        raise ErrorSobrescritura(
            f"Ya existe {path.name}. Confirme la sobrescritura o elija otro nombre."
        )
    descriptor, temporal = tempfile.mkstemp(
        prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.replace(temporal, path)
    except OSError as exc:
        if os.path.exists(temporal):
            os.unlink(temporal)
        raise ErrorArchivo(f"No se pudo guardar {path}: {exc}") from exc
    return path


def guardar_escenario(
    escenario: Escenario,
    ruta: str | Path,
    sobrescribir: bool = False,
) -> Path:
    """Serializa y guarda un escenario.

    Antes de escribir se ejecuta la validación estructural; un escenario
    inválido no debe persistirse silenciosamente.
    """
    errores = escenario.validar()
    if errores:
        raise ValueError("No se puede guardar un escenario inválido: " + "; ".join(errores))
    escenario.meta["ultima_modificacion"] = datetime.now().isoformat(timespec="seconds")
    return guardar_json(escenario.a_dict(), ruta, sobrescribir=sobrescribir)
