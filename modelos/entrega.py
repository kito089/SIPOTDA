"""Punto de entrega de la red logística."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Entrega:
    """Un punto de entrega con demanda y tarifa asociada.

    La demanda consume capacidad de transporte.  La tarifa se paga a la
    empresa por cada unidad entregada y se utiliza para calcular los pagos del
    juego estratégico.
    """

    id: int
    nombre: str
    fila: int
    columna: int
    demanda: float = 1.0
    tarifa: float = 60.0
    prioridad: int = 1

    def __post_init__(self) -> None:
        self.id = int(self.id)
        self.nombre = str(self.nombre).strip() or f"E{self.id}"
        self.fila = int(self.fila)
        self.columna = int(self.columna)
        self.demanda = float(self.demanda)
        self.tarifa = float(self.tarifa)
        self.prioridad = int(self.prioridad)
        if self.demanda < 0:
            raise ValueError(f"La demanda de {self.nombre!r} no puede ser negativa")
        if self.tarifa < 0:
            raise ValueError(f"La tarifa de {self.nombre!r} no puede ser negativa")

    @property
    def posicion(self) -> tuple[int, int]:
        return (self.fila, self.columna)

    def establecer_posicion(self, fila: int, columna: int) -> None:
        self.fila = int(fila)
        self.columna = int(columna)

    def clonar(self) -> "Entrega":
        return Entrega(
            id=self.id,
            nombre=self.nombre,
            fila=self.fila,
            columna=self.columna,
            demanda=self.demanda,
            tarifa=self.tarifa,
            prioridad=self.prioridad,
        )

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "fila": self.fila,
            "columna": self.columna,
            "demanda": round(self.demanda, 6),
            "tarifa": round(self.tarifa, 6),
            "prioridad": self.prioridad,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Entrega":
        if not isinstance(datos, dict):
            raise ValueError("La entrega debe ser un objeto JSON")
        faltantes = {"id", "fila", "columna"} - set(datos)
        if faltantes:
            raise ValueError(f"Faltan campos de entrega: {sorted(faltantes)}")
        return cls(
            id=datos["id"],
            nombre=datos.get("nombre", f"E{datos['id']}"),
            fila=datos["fila"],
            columna=datos["columna"],
            demanda=datos.get("demanda", 1.0),
            tarifa=datos.get("tarifa", 60.0),
            prioridad=datos.get("prioridad", 1),
        )
