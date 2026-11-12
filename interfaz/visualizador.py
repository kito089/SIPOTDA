"""Visualización de la cuadrícula y de las rutas encontradas."""

from __future__ import annotations

import tkinter as tk
from typing import Iterable

from interfaz.componentes import COLORES
from modelos.escenario import Escenario


def _color_costo(costo: float, minimo: float, maximo: float) -> str:
    if maximo <= minimo:
        return "#e8eef7"
    t = max(0.0, min(1.0, (costo - minimo) / (maximo - minimo)))
    # Azul claro -> amarillo -> rojo claro.
    if t < 0.5:
        r = int(220 + (255 - 220) * (t / 0.5))
        g = int(235 + (242 - 235) * (t / 0.5))
        b = int(255 + (180 - 255) * (t / 0.5))
    else:
        r = int(255 + (255 - 255) * ((t - 0.5) / 0.5))
        g = int(242 + (170 - 242) * ((t - 0.5) / 0.5))
        b = int(180 + (170 - 180) * ((t - 0.5) / 0.5))
    return f"#{r:02x}{g:02x}{b:02x}"


class VisualizadorCuadricula(tk.Canvas):
    """Canvas que dibuja celdas, elementos y superpone rutas."""

    def __init__(
        self,
        master,
        escenario: Escenario,
        tamano_celda: int = 38,
        **kwargs,
    ) -> None:
        self.tamano = int(tamano_celda)
        self.escenario = escenario
        self.rutas: list[tuple[str, str, list[tuple[int, int]]]] = []
        self.seleccion: tuple[int, int] | None = None
        self.resaltados: dict[tuple[int, int], tuple[str, str]] = {}
        ancho = escenario.columnas * self.tamano + 2
        alto = escenario.filas * self.tamano + 2
        super().__init__(
            master,
            width=ancho,
            height=alto,
            background="white",
            highlightthickness=1,
            highlightbackground="#7b8794",
            **kwargs,
        )
        self.bind("<Configure>", lambda _e: self.redibujar())
        self.redibujar()

    def establecer_escenario(self, escenario: Escenario) -> None:
        self.escenario = escenario
        self.rutas = []
        self.seleccion = None
        self.resaltados = {}
        self.config(
            width=escenario.columnas * self.tamano + 2,
            height=escenario.filas * self.tamano + 2,
        )
        self.redibujar()

    def establecer_seleccion(self, posicion: tuple[int, int] | None) -> None:
        self.seleccion = posicion
        self.redibujar()

    def mostrar_rutas(self, rutas: Iterable[tuple[str, str, list[tuple[int, int]]]]) -> None:
        self.rutas = list(rutas)
        self.redibujar()

    def limpiar_rutas(self) -> None:
        self.rutas = []
        self.redibujar()

    def establecer_resaltados(
        self, resaltados: dict[tuple[int, int], tuple[str, str]]
    ) -> None:
        """Marca celdas con ``(color, etiqueta)`` para explicar acciones."""
        self.resaltados = dict(resaltados)
        self.redibujar()

    def limpiar_resaltados(self) -> None:
        self.resaltados = {}
        self.redibujar()

    def celda_desde_evento(self, evento) -> tuple[int, int] | None:
        x = self.canvasx(evento.x)
        y = self.canvasy(evento.y)
        columna = int(x // self.tamano)
        fila = int(y // self.tamano)
        if self.escenario.dentro(fila, columna):
            return fila, columna
        return None

    def redibujar(self) -> None:
        self.delete("all")
        e = self.escenario
        costos = [c.costo for fila in e.celdas for c in fila if c.transitable]
        minimo = min(costos) if costos else 1.0
        maximo = max(costos) if costos else 1.0
        for f in range(e.filas):
            for c in range(e.columnas):
                celda = e.celdas[f][c]
                x1 = c * self.tamano
                y1 = f * self.tamano
                x2 = x1 + self.tamano
                y2 = y1 + self.tamano
                if not celda.transitable:
                    relleno = COLORES["obstaculo"]
                elif celda.tipo == "inicio":
                    relleno = COLORES["inicio"]
                elif celda.tipo == "destino":
                    relleno = COLORES["destino"]
                elif celda.tipo == "entrega":
                    relleno = COLORES["entrega"]
                else:
                    relleno = _color_costo(celda.costo, minimo, maximo)
                self.create_rectangle(
                    x1, y1, x2, y2, fill=relleno, outline=COLORES["grid"], width=1
                )
                color_texto = "white" if not celda.transitable else "#1f2933"
                if celda.tipo in {"obstaculo"}:
                    self.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=celda.etiqueta or "#",
                        font=("Segoe UI", 12, "bold"),
                        fill="white",
                    )
                elif celda.tipo in {"inicio", "destino", "entrega"}:
                    self.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2 - 1,
                        text=celda.etiqueta,
                        font=("Segoe UI", 10, "bold"),
                        fill=color_texto,
                    )
                    self.create_text(
                        x2 - 3,
                        y2 - 3,
                        text=f"{celda.costo:g}",
                        anchor="se",
                        font=("Segoe UI", 7),
                        fill=color_texto,
                    )
                else:
                    self.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=f"{celda.costo:g}",
                        font=("Segoe UI", 8),
                        fill="#334e68",
                    )
        for (fila, columna), (color, etiqueta) in self.resaltados.items():
            if not e.dentro(fila, columna):
                continue
            x1 = columna * self.tamano + 2
            y1 = fila * self.tamano + 2
            x2 = (columna + 1) * self.tamano - 2
            y2 = (fila + 1) * self.tamano - 2
            self.create_rectangle(x1, y1, x2, y2, outline=color, width=3)
            if etiqueta:
                self.create_text(
                    x2 - 3,
                    y1 + 2,
                    text=etiqueta,
                    anchor="ne",
                    font=("Segoe UI", 7, "bold"),
                    fill=color,
                )
        for nombre, color, camino in self.rutas:
            if len(camino) < 2:
                if camino:
                    f, c = camino[0]
                    self.create_oval(
                        c * self.tamano + self.tamano * 0.35,
                        f * self.tamano + self.tamano * 0.35,
                        c * self.tamano + self.tamano * 0.65,
                        f * self.tamano + self.tamano * 0.65,
                        outline=color,
                        width=3,
                    )
                continue
            puntos = []
            for f, c in camino:
                puntos.extend(
                    [c * self.tamano + self.tamano / 2, f * self.tamano + self.tamano / 2]
                )
            self.create_line(
                *puntos, fill=color, width=3, arrow=tk.LAST, smooth=False, capstyle=tk.ROUND
            )
        if self.seleccion:
            f, c = self.seleccion
            self.create_rectangle(
                c * self.tamano + 2,
                f * self.tamano + 2,
                (c + 1) * self.tamano - 2,
                (f + 1) * self.tamano - 2,
                outline="#111827",
                width=3,
            )
