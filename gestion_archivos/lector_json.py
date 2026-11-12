"""Lectura y validación de escenarios y parámetros en JSON."""

from __future__ import annotations

import json
from pathlib import Path

from modelos.escenario import Escenario

from .errores import ErrorArchivo, ErrorValidacion


def cargar_json(ruta: str | Path) -> dict:
    path = Path(ruta)
    if not path.exists():
        raise ErrorArchivo(f"No existe el archivo: {path}")
    if not path.is_file():
        raise ErrorArchivo(f"La ruta no es un archivo: {path}")
    try:
        with path.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ErrorArchivo(
            f"JSON inválido en {path.name}: línea {exc.lineno}, columna {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ErrorArchivo(f"No se pudo leer {path}: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorArchivo("El archivo JSON debe contener un objeto en la raíz.")
    return datos


def cargar_escenario(ruta: str | Path, validar: bool = True) -> Escenario:
    """Carga un escenario, informando errores estructurales o de validación."""
    datos = cargar_json(ruta)
    if "escenario" in datos and isinstance(datos["escenario"], dict):
        datos = datos["escenario"]
    try:
        escenario = Escenario.desde_dict(datos)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise ErrorArchivo(f"El archivo no contiene un escenario válido: {exc}") from exc
    if validar:
        errores = escenario.validar()
        if errores:
            raise ErrorValidacion(
                f"El escenario '{escenario.nombre}' no es válido.", errores
            )
    return escenario


def cargar_parametros(ruta: str | Path) -> dict:
    datos = cargar_json(ruta)
    if not isinstance(datos, dict) or not datos:
        raise ErrorArchivo("El archivo de parámetros está vacío o mal formado.")
    return datos
