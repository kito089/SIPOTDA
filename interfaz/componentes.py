"""Componentes y utilidades comunes de la interfaz."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


COLORES = {
    "fondo": "#f4f6f8",
    "panel": "#ffffff",
    "acento": "#1f4e79",
    "acento_claro": "#dbe7f3",
    "exito": "#2e7d32",
    "advertencia": "#b26a00",
    "error": "#b00020",
    "texto": "#1f2933",
    "grid": "#9aa5b1",
    "inicio": "#7bc67e",
    "destino": "#6fa8dc",
    "entrega": "#f6b26b",
    "obstaculo": "#4b5563",
    "ruta1": "#c00000",
    "ruta2": "#2e75b6",
    "ruta3": "#7030a0",
    "ruta4": "#2e7d32",
    "ruta5": "#b26a00",
}


PALETA_RUTAS = [
    COLORES["ruta1"],
    COLORES["ruta2"],
    COLORES["ruta3"],
    COLORES["ruta4"],
    COLORES["ruta5"],
    "#00838f",
    "#6a1b9a",
]


class MarcoDesplazable(ttk.Frame):
    """Contenedor con scroll vertical y ancho ajustado al espacio disponible."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas)
        self.interior.bind("<Configure>", self._al_cambiar_interior)
        self.ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", self._rueda, add="+")
        self.bind_all("<Button-4>", self._rueda, add="+")
        self.bind_all("<Button-5>", self._rueda, add="+")

    def _al_cambiar_interior(self, _evento) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _al_redimensionar(self, evento) -> None:
        self.canvas.itemconfigure(self.ventana, width=evento.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _pertenece(self, widget) -> bool:
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _altura_contenido(self) -> int:
        caja = self.canvas.bbox("all")
        return caja[3] - caja[1] if caja else 0

    def _rueda(self, evento) -> None:
        try:
            if not self.winfo_exists():
                return
            widget = self.winfo_containing(*self.winfo_pointerxy())
        except tk.TclError:
            return
        if not self._pertenece(widget):
            return
        if self._altura_contenido() <= self.canvas.winfo_height():
            return
        if getattr(evento, "num", None) == 4:
            paso = -1
        elif getattr(evento, "num", None) == 5:
            paso = 1
        else:
            delta = getattr(evento, "delta", 0)
            if delta == 0:
                return
            paso = -1 if delta > 0 else 1
            paso *= max(1, abs(delta) // 120)
        try:
            self.canvas.yview_scroll(paso, "units")
        except tk.TclError:
            pass


def etiqueta_valor(
    parent,
    texto: str,
    variable: tk.Variable,
    fila: int,
    columna: int = 0,
    ancho: int = 10,
) -> ttk.Entry:
    ttk.Label(parent, text=texto).grid(row=fila, column=columna, sticky="w", padx=4, pady=3)
    entrada = ttk.Entry(parent, textvariable=variable, width=ancho)
    entrada.grid(row=fila, column=columna + 1, sticky="w", padx=4, pady=3)
    return entrada


def separador(parent, fila: int, columnas: int = 4) -> None:
    ttk.Separator(parent, orient="horizontal").grid(
        row=fila, column=0, columnspan=columnas, sticky="ew", pady=8
    )


def mostrar_error(titulo: str, mensaje: str) -> None:
    messagebox.showerror(titulo, mensaje)


def mostrar_info(titulo: str, mensaje: str) -> None:
    messagebox.showinfo(titulo, mensaje)


def confirmar(titulo: str, mensaje: str) -> bool:
    return messagebox.askyesno(titulo, mensaje)


def texto_solo_lectura(parent, alto: int = 8) -> tk.Text:
    texto = tk.Text(
        parent,
        height=alto,
        wrap="word",
        background=COLORES["panel"],
        foreground=COLORES["texto"],
        relief="flat",
        borderwidth=1,
    )
    texto.configure(state="disabled")
    return texto


def escribir_texto(widget: tk.Text, contenido: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", contenido)
    widget.configure(state="disabled")
