"""Rutas independientes por algoritmo y recorrido final del plan."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from interfaz.componentes import PALETA_RUTAS, escribir_texto, texto_solo_lectura
from interfaz.visualizador import VisualizadorCuadricula
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion
from modelos.solucion import Solucion, Tramo


def _fmt(valor, decimales: int = 2) -> str:
    if valor is None:
        return "n/d"
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if not math.isfinite(numero):
        return "n/d"
    return f"{numero:.{decimales}f}"


class PanelRutas(ttk.Frame):
    """Una cuadrícula a la vez: mejor solución por algoritmo o recorrido final."""

    OPCION_FINAL = "Recorrido final (planificación)"

    def __init__(self, master) -> None:
        super().__init__(master, padding=4)
        self.escenario: Escenario | None = None
        self.resultados: list[ResultadoEjecucion] = []
        self.plan: dict | None = None
        self.visualizador: VisualizadorCuadricula | None = None
        self._opciones: dict[str, tuple[Solucion, str, str]] = {}
        self._construir()

    def _construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        barra = ttk.Frame(self)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(barra, text="Solución:").pack(side="left")
        self.var_opcion = tk.StringVar()
        self.combo = ttk.Combobox(
            barra, textvariable=self.var_opcion, state="readonly", width=48
        )
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._mostrar_opcion())
        ttk.Label(
            barra,
            text="Se muestra una sola ruta a la vez para evitar solapamientos.",
        ).pack(side="left", padx=8)

        cuerpo = ttk.Frame(self)
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.columnconfigure(0, weight=0)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        marco_mapa = ttk.LabelFrame(cuerpo, text="Cuadrícula de la solución", padding=4)
        marco_mapa.grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.marco_mapa = marco_mapa

        self.detalle = texto_solo_lectura(cuerpo, alto=16)
        self.detalle.grid(row=0, column=1, sticky="nsew")

    def establecer_escenario(self, escenario: Escenario | None) -> None:
        self.escenario = escenario
        for hijo in self.marco_mapa.winfo_children():
            hijo.destroy()
        self.visualizador = VisualizadorCuadricula(
            self.marco_mapa, escenario, tamano_celda=30
        ) if escenario is not None else None
        if self.visualizador is not None:
            self.visualizador.pack(anchor="nw")
        self._opciones = {}
        self.combo.configure(values=[])
        self.var_opcion.set("")
        escribir_texto(self.detalle, "Ejecute todos los módulos para ver las rutas.")

    def mostrar(
        self,
        resultados: list[ResultadoEjecucion],
        plan: dict | None = None,
    ) -> None:
        self.resultados = list(resultados)
        self.plan = plan
        self._opciones = {}
        mejores: dict[str, ResultadoEjecucion] = {}
        for resultado in self.resultados:
            if resultado.solucion is None:
                continue
            actual = mejores.get(resultado.algoritmo)
            if actual is None or resultado.costo < actual.costo:
                mejores[resultado.algoritmo] = resultado
        for algoritmo, resultado in sorted(mejores.items()):
            solucion = resultado.solucion
            etiqueta = (
                f"{algoritmo} · #{resultado.id_ejecucion} · "
                f"costo {_fmt(resultado.costo)}"
            )
            detalle = (
                f"Algoritmo: {algoritmo}\n"
                f"Ejecución: {resultado.id_ejecucion}\n"
                f"Semilla: {resultado.semilla if resultado.semilla is not None else 'n/d'}\n"
                f"Costo: {_fmt(resultado.costo)}\n"
                f"Tiempo: {_fmt(resultado.tiempo_ejecucion, 4)} s\n"
                f"Orden: {resultado.solucion.orden_entregas}\n"
                f"Pasos: {resultado.solucion.pasos}\n"
                f"Combustible: {_fmt(resultado.solucion.combustible_consumido)}\n"
                f"Tiempo consumido: {_fmt(resultado.solucion.tiempo_consumido)}\n"
                f"Presupuesto: {_fmt(resultado.solucion.presupuesto_consumido)}\n"
                f"Válida: {'sí' if resultado.solucion.valida else 'no'}\n"
                f"Rutas: {len(resultado.solucion.rutas)} tramos"
            )
            self._opciones[etiqueta] = (solucion, algoritmo, detalle)
        if plan:
            solucion_plan = self._solucion_desde_plan(plan)
            if solucion_plan is not None:
                etiqueta = self.OPCION_FINAL
                detalle = (
                    f"Plan: {plan.get('id_plan', 'n/d')}\n"
                    f"Orden: {plan.get('orden_entregas')}\n"
                    f"Costo total: {_fmt(plan.get('costo_total'))}\n"
                    f"Pasos: {plan.get('pasos')}\n"
                    f"Longitud de ruta: {plan.get('longitud_ruta')}\n"
                    f"Riesgo: {plan.get('riesgos_competidor', {}).get('nivel', 'n/d')}\n"
                    f"Estrategia: "
                    f"{plan.get('estrategia_recomendada', {}).get('estrategia_empresa', 'n/d')}\n"
                    f"Rutas: {len(solucion_plan.rutas)} tramos"
                )
                self._opciones[etiqueta] = (
                    solucion_plan,
                    "Planificación final",
                    detalle,
                )
        nombres = list(self._opciones)
        self.combo.configure(values=nombres)
        if nombres:
            elegido = self.var_opcion.get()
            if elegido not in self._opciones:
                elegido = nombres[0]
            self.var_opcion.set(elegido)
            self._mostrar_opcion()
        else:
            self.var_opcion.set("")
            if self.visualizador is not None:
                self.visualizador.limpiar_rutas()
            escribir_texto(self.detalle, "No hay soluciones para mostrar.")

    def _solucion_desde_plan(self, plan: dict) -> Solucion | None:
        tramos = [Tramo.desde_dict(t) for t in plan.get("rutas", [])]
        if not tramos:
            return None
        return Solucion(
            orden_entregas=list(plan.get("orden_entregas", [])),
            rutas=tramos,
            costo_total=float(plan.get("costo_total") or 0.0),
            pasos=int(plan.get("pasos") or 0),
            valida=bool(plan.get("plan_valido", True)),
        )

    def _mostrar_opcion(self) -> None:
        datos = self._opciones.get(self.var_opcion.get())
        if datos is None or self.visualizador is None:
            return
        solucion, _algoritmo, detalle = datos
        rutas = [
            (
                f"Tramo {indice + 1}: {tramo.origen_nombre} -> {tramo.destino_nombre}",
                PALETA_RUTAS[indice % len(PALETA_RUTAS)],
                tramo.camino,
            )
            for indice, tramo in enumerate(solucion.rutas)
        ]
        self.visualizador.mostrar_rutas(rutas)
        escribir_texto(self.detalle, detalle)
