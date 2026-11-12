"""Celda individual de la cuadrícula logística."""

from __future__ import annotations

from dataclasses import dataclass


TIPOS_CELDA = {
    "normal",
    "inicio",
    "destino",
    "entrega",
    "obstaculo",
}


@dataclass
class Celda:
    """Una celda de la red logística.

    Atributos
    ---------
    costo:
        Costo de entrar en la celda.  Debe ser estrictamente positivo.
    transitable:
        ``False`` para obstáculos y celdas bloqueadas.
    tipo:
        Etiqueta descriptiva usada por la interfaz: ``normal``, ``inicio``,
        ``destino``, ``entrega`` u ``obstaculo``.  El escenario recalcula
        estas etiquetas a partir de sus posiciones para mantener una única
        fuente de verdad.
    etiqueta:
        Texto corto que se dibuja en la cuadrícula (S, G, E1, ...).
    """

    costo: float = 1.0
    transitable: bool = True
    tipo: str = "normal"
    etiqueta: str = ""

    def __post_init__(self) -> None:
        self.costo = float(self.costo)
        self.transitable = bool(self.transitable)
        if self.tipo not in TIPOS_CELDA:
            raise ValueError(f"Tipo de celda no válido: {self.tipo!r}")

    def clonar(self) -> "Celda":
        return Celda(
            costo=self.costo,
            transitable=self.transitable,
            tipo=self.tipo,
            etiqueta=self.etiqueta,
        )

    def a_dict(self) -> dict:
        return {
            "costo": round(self.costo, 6),
            "transitable": self.transitable,
            "tipo": self.tipo,
            "etiqueta": self.etiqueta,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Celda":
        if not isinstance(datos, dict):
            raise ValueError("La celda debe ser un objeto JSON")
        return cls(
            costo=datos.get("costo", 1.0),
            transitable=datos.get("transitable", True),
            tipo=datos.get("tipo", "normal"),
            etiqueta=datos.get("etiqueta", ""),
        )
