"""Importación/exportación de la cuadrícula logística en CSV.

Formato de importación
----------------------
Cada fila del CSV representa una fila de la cuadrícula.  Una celda puede ser:

- un número positivo: costo de una celda normal;
- ``S``: inicio;
- ``G``: destino final;
- ``E1``, ``E2``, ... o ``E``: punto de entrega;
- ``#``: obstáculo.

Opcionalmente se puede indicar el costo de una celda especial con ``S:1.5``,
``E1:2`` o ``#:1``.  Las entregas importadas reciben demanda predeterminada 4
(regla documentada); si se necesita una demanda distinta, use JSON o la GUI.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from modelos.celda import Celda
from modelos.entrega import Entrega
from modelos.escenario import Escenario
from modelos.recurso import Recurso

from .errores import ErrorArchivo, ErrorValidacion


def _interpretar_celda(texto: str, indice_entrega: int) -> tuple[Celda, str, int | None]:
    texto = (texto or "").strip()
    if not texto:
        return Celda(costo=1.0), "normal", None
    partes = texto.split(":")
    marca = partes[0].strip()
    costo = 1.0
    if len(partes) > 1 and partes[1].strip():
        try:
            costo = float(partes[1])
        except ValueError as exc:
            raise ErrorArchivo(f"Costo CSV inválido en la celda {texto!r}") from exc
    if not math.isfinite(costo) or costo <= 0:
        raise ErrorArchivo(f"Costo CSV inválido en la celda {texto!r}")
    mayuscula = marca.upper()
    if mayuscula == "#" or mayuscula == "X":
        return Celda(costo=costo, transitable=False), "obstaculo", None
    if mayuscula == "S":
        return Celda(costo=costo), "inicio", None
    if mayuscula == "G":
        return Celda(costo=costo), "destino", None
    if mayuscula == "E":
        return Celda(costo=costo), "entrega", indice_entrega
    if mayuscula.startswith("E") and mayuscula[1:].isdigit():
        return Celda(costo=costo), "entrega", int(mayuscula[1:])
    try:
        valor = float(texto)
    except ValueError as exc:
        raise ErrorArchivo(f"Token de celda no reconocido: {texto!r}") from exc
    if not math.isfinite(valor) or valor <= 0:
        raise ErrorArchivo(f"Costo CSV inválido en la celda {texto!r}")
    return Celda(costo=valor), "normal", None


def cargar_escenario_csv(
    ruta: str | Path,
    id_escenario: str | None = None,
    nombre: str | None = None,
) -> Escenario:
    """Carga una cuadrícula desde CSV y devuelve un escenario validado."""
    path = Path(ruta)
    if not path.exists():
        raise ErrorArchivo(f"No existe el archivo CSV: {path}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as archivo:
            filas = [fila for fila in csv.reader(archivo) if any(c.strip() for c in fila)]
    except OSError as exc:
        raise ErrorArchivo(f"No se pudo leer {path}: {exc}") from exc
    if len(filas) < 2 or len(filas[0]) < 2:
        raise ErrorArchivo("El CSV debe contener al menos una cuadrícula 2x2.")

    columnas = len(filas[0])
    if any(len(fila) != columnas for fila in filas):
        raise ErrorArchivo("Todas las filas del CSV deben tener la misma longitud.")

    celdas: list[list[Celda]] = []
    inicio = None
    destino = None
    entregas: list[Entrega] = []
    obstaculos: set[tuple[int, int]] = set()
    indice_auto = 1
    for f, fila in enumerate(filas):
        fila_celdas = []
        for c, texto in enumerate(fila):
            celda, tipo, id_entrega = _interpretar_celda(texto, indice_auto)
            fila_celdas.append(celda)
            if tipo == "inicio":
                if inicio is not None:
                    raise ErrorArchivo("El CSV contiene más de un inicio (S).")
                inicio = (f, c)
            elif tipo == "destino":
                if destino is not None:
                    raise ErrorArchivo("El CSV contiene más de un destino (G).")
                destino = (f, c)
            elif tipo == "entrega":
                if id_entrega is None:
                    id_entrega = indice_auto
                    indice_auto += 1
                else:
                    indice_auto = max(indice_auto, id_entrega + 1)
                if any(e.id == id_entrega for e in entregas):
                    raise ErrorArchivo(f"Id de entrega duplicado en CSV: {id_entrega}")
                entregas.append(
                    Entrega(
                        id=id_entrega,
                        nombre=f"E{len(entregas) + 1}",
                        fila=f,
                        columna=c,
                        demanda=4.0,
                        tarifa=60.0,
                    )
                )
                celda.tipo = "entrega"
            elif tipo == "obstaculo":
                obstaculos.add((f, c))
        celdas.append(fila_celdas)

    if inicio is None or destino is None:
        raise ErrorArchivo("El CSV debe incluir un inicio (S) y un destino (G).")
    if not entregas:
        raise ErrorArchivo("El CSV debe incluir al menos un punto de entrega (E).")
    demanda_total = sum(e.demanda for e in entregas)
    escenario = Escenario(
        id=id_escenario or path.stem,
        nombre=nombre or path.stem,
        filas=len(filas),
        columnas=columnas,
        celdas=celdas,
        inicio=inicio,
        destino=destino,
        entregas=entregas,
        obstaculos=obstaculos,
        recursos={
            "combustible": Recurso("combustible", 300, "unidades", 1.0),
            "capacidad": Recurso("capacidad", max(30.0, demanda_total), "unidades", 0.0),
            "tiempo": Recurso("tiempo", 300, "pasos", 1.0),
            "presupuesto": Recurso("presupuesto", 400, "monetarias", 0.0),
        },
        competidor={
            "nombre": "Competidor",
            "factor_costo": 1.0,
            "factor_presupuesto": 1.0,
            "celdas_bloqueadas": [],
            "descripcion": "Competidor importado desde CSV",
        },
    )
    errores = escenario.validar()
    if errores:
        raise ErrorValidacion("El CSV generó un escenario inválido.", errores)
    return escenario


def exportar_escenario_csv(escenario: Escenario, ruta: str | Path) -> Path:
    """Exporta la cuadrícula con tokens S/G/E#/costos."""
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    posiciones_entrega = {
        e.posicion: f"E{indice}"
        for indice, e in enumerate(escenario.entregas, start=1)
    }
    with path.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        for f in range(escenario.filas):
            fila = []
            for c in range(escenario.columnas):
                posicion = (f, c)
                costo = escenario.obtener_celda(f, c).costo
                if posicion == escenario.inicio:
                    fila.append(f"S:{costo:g}")
                elif posicion == escenario.destino:
                    fila.append(f"G:{costo:g}")
                elif posicion in posiciones_entrega:
                    fila.append(f"{posiciones_entrega[posicion]}:{costo:g}")
                elif posicion in escenario.obstaculos:
                    fila.append(f"#:{costo:g}")
                else:
                    fila.append(f"{costo:g}")
            escritor.writerow(fila)
    return path
