"""Visualización de las gráficas reales generadas por los experimentos."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from experimentos.ejecutar_experimentos import DIR_GRAFICAS
from interfaz.componentes import escribir_texto, texto_solo_lectura


class PanelGraficas(ttk.Frame):
    """Muestra las imágenes PNG producidas a partir de los CSV experimentales."""

    def __init__(self, master, directorio: Path | None = None) -> None:
        super().__init__(master, padding=4)
        self.directorio = Path(directorio or DIR_GRAFICAS)
        self.rutas: list[Path] = []
        self._por_nombre: dict[str, Path] = {}
        self._imagen: tk.PhotoImage | None = None
        self._construir()
        self.actualizar()

    def _construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        barra = ttk.Frame(self)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(barra, text="Gráfica:").pack(side="left")
        self.var_grafica = tk.StringVar()
        self.combo = ttk.Combobox(
            barra,
            textvariable=self.var_grafica,
            state="readonly",
            width=42,
        )
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._mostrar_seleccionada())
        ttk.Button(barra, text="Actualizar", command=self.actualizar).pack(
            side="left", padx=4
        )

        marco = ttk.Frame(self)
        marco.grid(row=1, column=0, sticky="nsew")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            marco,
            background="white",
            highlightthickness=1,
            highlightbackground="#9aa5b1",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(marco, orient="vertical", command=self.canvas.yview)
        scroll_x = ttk.Scrollbar(marco, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Configure>", lambda _e: self._mostrar_seleccionada())

        self.nota = texto_solo_lectura(self, alto=3)
        self.nota.grid(row=2, column=0, sticky="ew", pady=(4, 0))

    @staticmethod
    def _titulo(ruta: Path) -> str:
        return ruta.stem.replace("_", " ").capitalize()

    def actualizar(self, rutas: list[Path] | None = None) -> None:
        """Recarga la lista de gráficas disponibles desde disco o desde el resultado."""
        if rutas:
            candidatas = [Path(ruta) for ruta in rutas]
        else:
            candidatas = sorted(self.directorio.glob("*.png")) if self.directorio.exists() else []
        self.rutas = [ruta for ruta in candidatas if ruta.exists()]
        self._por_nombre = {self._titulo(ruta): ruta for ruta in self.rutas}
        nombres = list(self._por_nombre)
        self.combo.configure(values=nombres)
        if nombres:
            if self.var_grafica.get() not in self._por_nombre:
                self.var_grafica.set(nombres[0])
            self._mostrar_seleccionada()
        else:
            self.var_grafica.set("")
            self.canvas.delete("all")
            self.canvas.create_text(
                20,
                20,
                anchor="nw",
                text="No hay gráficas disponibles. Ejecute todos los módulos para generarlas.",
                fill="#52606d",
            )
        escribir_texto(
            self.nota,
            "Las gráficas se generan exclusivamente con los CSV de la última "
            "ejecución real. No se usan valores simulados ni imágenes de ejemplo.",
        )

    def _mostrar_seleccionada(self) -> None:
        ruta = self._por_nombre.get(self.var_grafica.get())
        self.canvas.delete("all")
        if ruta is None:
            return
        try:
            imagen = tk.PhotoImage(file=str(ruta))
        except tk.TclError:
            self.canvas.create_text(
                20,
                20,
                anchor="nw",
                text=f"No se pudo abrir la imagen: {ruta.name}",
                fill="#b00020",
            )
            return
        self._imagen = imagen
        ancho = max(1, self.canvas.winfo_width())
        alto = max(1, self.canvas.winfo_height())
        factor = max(
            1,
            (imagen.width() + ancho - 1) // ancho,
            (imagen.height() + alto - 1) // alto,
        )
        if factor > 1:
            imagen = imagen.subsample(factor, factor)
            self._imagen = imagen
        self.canvas.create_image(
            ancho // 2, alto // 2, image=imagen, anchor="center"
        )
        self.canvas.configure(scrollregion=(0, 0, ancho, alto))
