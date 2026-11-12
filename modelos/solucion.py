"""Solución logística compartida por los algoritmos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PENALIZACION_BASE = 1_000_000.0


@dataclass
class Tramo:
    """Tramo entre dos puntos obligatorios de la ruta."""

    origen_nombre: str
    destino_nombre: str
    origen: tuple[int, int]
    destino: tuple[int, int]
    camino: list[tuple[int, int]]
    costo: float
    pasos: int
    algoritmo: str = ""

    @property
    def longitud(self) -> int:
        return len(self.camino)

    def a_dict(self) -> dict:
        return {
            "origen_nombre": self.origen_nombre,
            "destino_nombre": self.destino_nombre,
            "origen": list(self.origen),
            "destino": list(self.destino),
            "camino": [list(p) for p in self.camino],
            "costo": round(self.costo, 6),
            "pasos": self.pasos,
            "algoritmo": self.algoritmo,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Tramo":
        return cls(
            origen_nombre=datos.get("origen_nombre", ""),
            destino_nombre=datos.get("destino_nombre", ""),
            origen=tuple(datos.get("origen", (0, 0))),
            destino=tuple(datos.get("destino", (0, 0))),
            camino=[tuple(p) for p in datos.get("camino", [])],
            costo=float(datos.get("costo", 0.0)),
            pasos=int(datos.get("pasos", 0)),
            algoritmo=datos.get("algoritmo", ""),
        )


@dataclass
class Solucion:
    """Secuencia de entregas y rutas asociadas.

    La misma clase se utiliza para Hill Climbing, recocido simulado, algoritmo
    genético y la búsqueda heurística, garantizando comparabilidad.
    """

    orden_entregas: list[int] = field(default_factory=list)
    rutas: list[Tramo] = field(default_factory=list)
    costo_total: float = 0.0
    pasos: int = 0
    combustible_consumido: float = 0.0
    tiempo_consumido: float = 0.0
    presupuesto_consumido: float = 0.0
    carga_maxima: float = 0.0
    valida: bool = False
    violaciones: list[str] = field(default_factory=list)
    penalizacion: float = 0.0
    detalle: dict[str, Any] = field(default_factory=dict)

    @property
    def longitud_ruta(self) -> int:
        """Número de celdas de la ruta completa (incluye puntos repetidos)."""
        return sum(tramo.pasos for tramo in self.rutas)

    @property
    def costo_objetivo(self) -> float:
        """Valor minimizado por las metaheurísticas (costo + penalización)."""
        return self.costo_total + self.penalizacion

    @property
    def ruta_coordenadas(self) -> list[tuple[int, int]]:
        """Ruta completa concatenando los tramos."""
        resultado: list[tuple[int, int]] = []
        for tramo in self.rutas:
            if resultado and tramo.camino and resultado[-1] == tramo.camino[0]:
                resultado.extend(tramo.camino[1:])
            else:
                resultado.extend(tramo.camino)
        return resultado

    def marcar_invalida(self, motivo: str, penalizacion: float = PENALIZACION_BASE) -> None:
        self.valida = False
        if motivo not in self.violaciones:
            self.violaciones.append(motivo)
        self.penalizacion = max(self.penalizacion, penalizacion)

    def clonar(self) -> "Solucion":
        return Solucion(
            orden_entregas=list(self.orden_entregas),
            rutas=[
                Tramo(
                    origen_nombre=t.origen_nombre,
                    destino_nombre=t.destino_nombre,
                    origen=t.origen,
                    destino=t.destino,
                    camino=list(t.camino),
                    costo=t.costo,
                    pasos=t.pasos,
                    algoritmo=t.algoritmo,
                )
                for t in self.rutas
            ],
            costo_total=self.costo_total,
            pasos=self.pasos,
            combustible_consumido=self.combustible_consumido,
            tiempo_consumido=self.tiempo_consumido,
            presupuesto_consumido=self.presupuesto_consumido,
            carga_maxima=self.carga_maxima,
            valida=self.valida,
            violaciones=list(self.violaciones),
            penalizacion=self.penalizacion,
            detalle=dict(self.detalle),
        )

    def a_dict(self) -> dict:
        return {
            "orden_entregas": list(self.orden_entregas),
            "rutas": [t.a_dict() for t in self.rutas],
            "costo_total": round(self.costo_total, 6),
            "costo_objetivo": round(self.costo_objetivo, 6),
            "pasos": self.pasos,
            "longitud_ruta": self.longitud_ruta,
            "combustible_consumido": round(self.combustible_consumido, 6),
            "tiempo_consumido": round(self.tiempo_consumido, 6),
            "presupuesto_consumido": round(self.presupuesto_consumido, 6),
            "carga_maxima": round(self.carga_maxima, 6),
            "valida": self.valida,
            "violaciones": list(self.violaciones),
            "penalizacion": round(self.penalizacion, 6),
            "detalle": self.detalle,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Solucion":
        return cls(
            orden_entregas=list(datos.get("orden_entregas", [])),
            rutas=[Tramo.desde_dict(t) for t in datos.get("rutas", [])],
            costo_total=float(datos.get("costo_total", 0.0)),
            pasos=int(datos.get("pasos", 0)),
            combustible_consumido=float(datos.get("combustible_consumido", 0.0)),
            tiempo_consumido=float(datos.get("tiempo_consumido", 0.0)),
            presupuesto_consumido=float(datos.get("presupuesto_consumido", 0.0)),
            carga_maxima=float(datos.get("carga_maxima", 0.0)),
            valida=bool(datos.get("valida", False)),
            violaciones=list(datos.get("violaciones", [])),
            penalizacion=float(datos.get("penalizacion", 0.0)),
            detalle=dict(datos.get("detalle", {})),
        )
