"""Recursos limitados de la planificación logística."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recurso:
    """Un recurso con disponibilidad limitada.

    ``consumo_por_paso`` se utiliza para recursos que se agotan al desplazarse
    (combustible y tiempo).  Para el presupuesto, el consumo se calcula con el
    costo real de cada tramo; para la capacidad, con la carga transportada.
    """

    nombre: str
    cantidad: float
    unidad: str = "u"
    consumo_por_paso: float = 1.0
    descripcion: str = ""

    def __post_init__(self) -> None:
        self.nombre = str(self.nombre).strip()
        if not self.nombre:
            raise ValueError("El recurso debe tener un nombre")
        self.cantidad = float(self.cantidad)
        self.consumo_por_paso = float(self.consumo_por_paso)
        if self.cantidad < 0:
            raise ValueError(f"La cantidad del recurso {self.nombre!r} no puede ser negativa")
        if self.consumo_por_paso < 0:
            raise ValueError(
                f"El consumo por paso del recurso {self.nombre!r} no puede ser negativo"
            )

    def clonar(self) -> "Recurso":
        return Recurso(
            nombre=self.nombre,
            cantidad=self.cantidad,
            unidad=self.unidad,
            consumo_por_paso=self.consumo_por_paso,
            descripcion=self.descripcion,
        )

    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "cantidad": round(self.cantidad, 6),
            "unidad": self.unidad,
            "consumo_por_paso": round(self.consumo_por_paso, 6),
            "descripcion": self.descripcion,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Recurso":
        if not isinstance(datos, dict):
            raise ValueError("El recurso debe ser un objeto JSON")
        if "nombre" not in datos:
            raise ValueError("El recurso debe incluir 'nombre'")
        return cls(
            nombre=datos["nombre"],
            cantidad=datos.get("cantidad", 0.0),
            unidad=datos.get("unidad", "u"),
            consumo_por_paso=datos.get("consumo_por_paso", 1.0),
            descripcion=datos.get("descripcion", ""),
        )
