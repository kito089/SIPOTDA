"""Formato común de resultados experimentales."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .solucion import Solucion


def _json_seguro(valor: Any) -> str:
    """Serializa diccionarios/listas para su escritura en CSV."""
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


@dataclass
class ResultadoEjecucion:
    """Resultado trazable de una ejecución de un algoritmo."""

    id_ejecucion: str
    id_escenario: str
    nombre_escenario: str
    algoritmo: str
    semilla: int | None
    parametros: dict[str, Any] = field(default_factory=dict)
    exito: bool = False
    mensaje: str = ""
    costo: float = float("inf")
    tiempo_ejecucion: float = 0.0
    metricas: dict[str, Any] = field(default_factory=dict)
    solucion: Solucion | None = None
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @classmethod
    def crear(
        cls,
        escenario,
        algoritmo: str,
        semilla: int | None = None,
        parametros: dict[str, Any] | None = None,
    ) -> "ResultadoEjecucion":
        identificador = f"{algoritmo[:12].replace(' ', '_')}-{uuid.uuid4().hex[:10]}"
        return cls(
            id_ejecucion=identificador,
            id_escenario=getattr(escenario, "id", "sin_id"),
            nombre_escenario=getattr(escenario, "nombre", ""),
            algoritmo=algoritmo,
            semilla=semilla,
            parametros=dict(parametros or {}),
        )

    def a_dict(self) -> dict:
        return {
            "id_ejecucion": self.id_ejecucion,
            "fecha": self.fecha,
            "id_escenario": self.id_escenario,
            "nombre_escenario": self.nombre_escenario,
            "algoritmo": self.algoritmo,
            "semilla": self.semilla,
            "parametros": self.parametros,
            "exito": self.exito,
            "mensaje": self.mensaje,
            "costo": None if self.costo == float("inf") else round(self.costo, 6),
            "tiempo_ejecucion": round(self.tiempo_ejecucion, 6),
            "metricas": self.metricas,
            "solucion": self.solucion.a_dict() if self.solucion else None,
        }

    def a_fila_csv(self) -> dict[str, Any]:
        """Aplana el resultado a columnas estables para CSV."""
        metricas = self.metricas or {}
        solucion = self.solucion
        historial = metricas.get("historial_costos", [])
        if solucion is not None and solucion.detalle.get("historial_costos"):
            historial = solucion.detalle["historial_costos"]
        return {
            "id_ejecucion": self.id_ejecucion,
            "fecha": self.fecha,
            "id_escenario": self.id_escenario,
            "nombre_escenario": self.nombre_escenario,
            "algoritmo": self.algoritmo,
            "semilla": "" if self.semilla is None else self.semilla,
            "parametros": _json_seguro(self.parametros),
            "exito": self.exito,
            "mensaje": self.mensaje,
            "costo": "" if self.costo == float("inf") else round(self.costo, 6),
            "costo_objetivo": "" if solucion is None else round(solucion.costo_objetivo, 6),
            "solucion_valida": "" if solucion is None else solucion.valida,
            "tiempo_ejecucion": round(self.tiempo_ejecucion, 6),
            "nodos_expandidos": metricas.get("nodos_expandidos", ""),
            "nodos_generados": metricas.get("nodos_generados", ""),
            "nodos_visitados": metricas.get("nodos_visitados", ""),
            "nodos_podados": metricas.get("nodos_podados", ""),
            "evaluaciones": metricas.get("evaluaciones", ""),
            "iteraciones": metricas.get("iteraciones", ""),
            "longitud_ruta": "" if solucion is None else solucion.longitud_ruta,
            "orden_entregas": _json_seguro(solucion.orden_entregas if solucion else []),
            "historial_costos": _json_seguro(historial),
            "metricas_extra": _json_seguro(metricas),
            "solucion_json": _json_seguro(solucion.a_dict() if solucion else None),
        }


COLUMNAS_CSV = [
    "id_ejecucion",
    "fecha",
    "id_escenario",
    "nombre_escenario",
    "algoritmo",
    "semilla",
    "parametros",
    "exito",
    "mensaje",
    "costo",
    "costo_objetivo",
    "solucion_valida",
    "tiempo_ejecucion",
    "nodos_expandidos",
    "nodos_generados",
    "nodos_visitados",
    "nodos_podados",
    "evaluaciones",
    "iteraciones",
    "longitud_ruta",
    "orden_entregas",
    "historial_costos",
    "metricas_extra",
    "solucion_json",
]
