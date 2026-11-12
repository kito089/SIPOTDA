"""Presentación de resultados, gráficas, acciones, juego y plan final."""

from __future__ import annotations

import json
import math
import tkinter as tk
from tkinter import ttk
from typing import Iterable

from experimentos.metricas import formatear_tabla_resumen, resumir_resultados
from interfaz.componentes import COLORES, escribir_texto, texto_solo_lectura
from interfaz.panel_acciones import PanelAcciones
from interfaz.panel_graficas import PanelGraficas
from interfaz.panel_rutas import PanelRutas
from modelos.escenario import Escenario
from modelos.resultados import ResultadoEjecucion


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


def _nodos(resultado: ResultadoEjecucion):
    metrica = resultado.metricas or {}
    for clave in (
        "nodos_expandidos",
        "nodos_visitados",
        "iteraciones",
        "evaluaciones",
    ):
        valor = metrica.get(clave)
        if isinstance(valor, (int, float)):
            return valor
    return None


class PanelResultados(ttk.Frame):
    """Muestra de forma trazable los resultados de todas las técnicas."""

    def __init__(self, master) -> None:
        super().__init__(master, padding=4)
        self.resultados: list[ResultadoEjecucion] = []
        self.juego = None
        self.adversaria: dict | None = None
        self.plan: dict | None = None
        self.escenario: Escenario | None = None
        self._resultados_por_iid: dict[str, ResultadoEjecucion] = {}
        self._indicadores: dict[str, tk.Label] = {}
        self._matriz_widgets: list[tk.Widget] = []
        self._construir()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._tab_resumen()
        self._tab_ejecuciones()
        self._tab_rutas()
        self._tab_graficas()
        self._tab_acciones()
        self._tab_juego()
        self._tab_adversaria()
        self._tab_plan()

    def _texto_con_scroll(self, parent) -> tk.Text:
        marco = ttk.Frame(parent)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        texto = texto_solo_lectura(marco, alto=12)
        texto.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(marco, orient="vertical", command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        barra.grid(row=0, column=1, sticky="ns")
        marco._texto = texto  # type: ignore[attr-defined]
        return marco

    def _crear_tarjeta(self, parent, columna: int, clave: str, titulo: str) -> None:
        fondo = tk.Frame(parent, background="#ffffff", highlightthickness=1,
                         highlightbackground="#cbd2d9")
        fondo.grid(row=0, column=columna, sticky="nsew", padx=3, pady=3)
        tk.Label(
            fondo,
            text=titulo,
            background="#ffffff",
            foreground="#52606d",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=8, pady=(6, 0))
        valor = tk.Label(
            fondo,
            text="n/d",
            background="#ffffff",
            foreground=COLORES["acento"],
            font=("Segoe UI", 13, "bold"),
            wraplength=170,
            justify="left",
        )
        valor.pack(anchor="w", padx=8, pady=(0, 6))
        self._indicadores[clave] = valor
        parent.columnconfigure(columna, weight=1)

    def _tab_resumen(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Resumen")

        tarjetas = ttk.Frame(marco)
        tarjetas.pack(fill="x", pady=(0, 6))
        for columna, (clave, titulo) in enumerate(
            (
                ("mejor_costo", "Mejor costo"),
                ("menor_tiempo", "Menor tiempo"),
                ("menos_nodos", "Menos nodos/iter."),
                ("mejor_solucion", "Mejor solución"),
                ("costo_final", "Costo final del plan"),
                ("estrategia", "Estrategia recomendada"),
            )
        ):
            self._crear_tarjeta(tarjetas, columna, clave, titulo)

        self.texto_resumen = texto_solo_lectura(marco, alto=7)
        self.texto_resumen.pack(fill="x", pady=(0, 4))
        columnas = ("algoritmo", "ejecuciones", "exitos", "mejor", "promedio", "desviacion", "tiempo")
        self.tabla_resumen = ttk.Treeview(
            marco, columns=columnas, show="headings", height=8, selectmode="none"
        )
        titulos = {
            "algoritmo": "Algoritmo",
            "ejecuciones": "Ejec.",
            "exitos": "Éxitos",
            "mejor": "Mejor costo",
            "promedio": "Costo promedio",
            "desviacion": "Desv. costo",
            "tiempo": "Tiempo prom. (s)",
        }
        for col in columnas:
            self.tabla_resumen.heading(col, text=titulos[col])
            self.tabla_resumen.column(
                col,
                width=95 if col != "algoritmo" else 190,
                anchor="center" if col != "algoritmo" else "w",
            )
        self.tabla_resumen.pack(fill="both", expand=True)

    def _tab_ejecuciones(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Ejecuciones")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=2)
        marco.rowconfigure(1, weight=1)
        columnas = (
            "numero",
            "algoritmo",
            "semilla",
            "costo",
            "valida",
            "tiempo",
            "nodos",
            "orden",
        )
        self.tabla_ejecuciones = ttk.Treeview(
            marco, columns=columnas, show="headings", selectmode="browse", height=10
        )
        titulos = {
            "numero": "#",
            "algoritmo": "Algoritmo",
            "semilla": "Semilla",
            "costo": "Costo",
            "valida": "Válida",
            "tiempo": "Tiempo (s)",
            "nodos": "Nodos/iter.",
            "orden": "Orden de entregas",
        }
        for col in columnas:
            self.tabla_ejecuciones.heading(col, text=titulos[col])
            self.tabla_ejecuciones.column(
                col,
                width=165 if col in {"algoritmo", "orden"} else 80,
                anchor="w" if col in {"algoritmo", "orden"} else "center",
            )
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla_ejecuciones.yview)
        self.tabla_ejecuciones.configure(yscrollcommand=barra.set)
        self.tabla_ejecuciones.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.tabla_ejecuciones.bind("<<TreeviewSelect>>", self._seleccionar_ejecucion)
        self.detalle_ejecucion = texto_solo_lectura(marco, alto=9)
        self.detalle_ejecucion.grid(
            row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 0)
        )

    def _tab_rutas(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Rutas")
        self.panel_rutas = PanelRutas(marco)
        self.panel_rutas.pack(fill="both", expand=True)

    def _tab_graficas(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Gráficas")
        self.panel_graficas = PanelGraficas(marco)
        self.panel_graficas.pack(fill="both", expand=True)

    def _tab_acciones(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Acciones")
        self.panel_acciones = PanelAcciones(marco)
        self.panel_acciones.pack(fill="both", expand=True)

    def _tab_juego(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Juego estratégico")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=0)
        marco.rowconfigure(1, weight=1)
        self.marco_matriz = ttk.LabelFrame(
            marco, text="Matriz de pagos (empresa, competidor)", padding=6
        )
        self.marco_matriz.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.texto_juego = texto_solo_lectura(marco, alto=13)
        self.texto_juego.grid(row=1, column=0, sticky="nsew")

    def _tab_adversaria(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Adversaria")
        columnas = (
            "profundidad",
            "minimax",
            "alfa",
            "diferencia",
            "iguales",
            "nodos_minimax",
            "nodos_alfa",
            "podados",
            "reduccion",
        )
        self.tabla_adversaria = ttk.Treeview(
            marco, columns=columnas, show="headings", selectmode="browse", height=6
        )
        titulos = {
            "profundidad": "Prof.",
            "minimax": "Valor Minimax",
            "alfa": "Valor alfa-beta",
            "diferencia": "Diferencia",
            "iguales": "Iguales",
            "nodos_minimax": "Nodos Minimax",
            "nodos_alfa": "Nodos alfa-beta",
            "podados": "Podados",
            "reduccion": "Reducción %",
        }
        for col in columnas:
            self.tabla_adversaria.heading(col, text=titulos[col])
            self.tabla_adversaria.column(col, width=95, anchor="center")
        self.tabla_adversaria.pack(fill="x")
        self.texto_adversaria = texto_solo_lectura(marco, alto=11)
        self.texto_adversaria.pack(fill="both", expand=True, pady=(4, 0))

    def _tab_plan(self) -> None:
        marco = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(marco, text="Plan final")
        self.texto_plan = texto_solo_lectura(marco, alto=20)
        self.texto_plan.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def establecer_escenario(self, escenario: Escenario | None) -> None:
        self.escenario = escenario
        self.panel_rutas.establecer_escenario(escenario)
        self.panel_acciones.establecer_escenario(escenario)

    def limpiar(self) -> None:
        self.resultados = []
        self.juego = None
        self.adversaria = None
        self.plan = None
        self._resultados_por_iid.clear()
        for tabla in (
            self.tabla_resumen,
            self.tabla_ejecuciones,
            self.tabla_adversaria,
        ):
            for iid in tabla.get_children():
                tabla.delete(iid)
        for texto in (
            self.texto_resumen,
            self.detalle_ejecucion,
            self.texto_juego,
            self.texto_adversaria,
            self.texto_plan,
        ):
            escribir_texto(texto, "")
        for etiqueta in self._indicadores.values():
            etiqueta.configure(text="n/d", foreground=COLORES["acento"])
        for widget in self._matriz_widgets:
            widget.destroy()
        self._matriz_widgets.clear()
        self.panel_rutas.mostrar([], None)
        self.panel_acciones.mostrar(None, None, None, [])
        self.panel_graficas.actualizar([])

    def mostrar_todo(
        self,
        resultados: list[ResultadoEjecucion],
        juego=None,
        adversaria: dict | None = None,
        plan: dict | None = None,
        escenario: Escenario | None = None,
        graficas: Iterable | None = None,
    ) -> None:
        if escenario is not None:
            self.establecer_escenario(escenario)
        self.limpiar()
        self.mostrar_resultados(resultados)
        if juego is not None:
            self.mostrar_juego(juego)
        if adversaria is not None:
            self.mostrar_adversaria(adversaria)
        if plan is not None:
            self.mostrar_plan(plan)
        self.panel_rutas.mostrar(self.resultados, self.plan)
        self.panel_acciones.mostrar(
            self.juego, self.adversaria, self.plan, self.resultados
        )
        self.panel_graficas.actualizar(list(graficas) if graficas is not None else None)

    def mostrar_resultados(self, resultados: list[ResultadoEjecucion]) -> None:
        self.resultados = list(resultados)
        self._resultados_por_iid.clear()
        for iid in self.tabla_ejecuciones.get_children():
            self.tabla_ejecuciones.delete(iid)
        for iid in self.tabla_resumen.get_children():
            self.tabla_resumen.delete(iid)
        if not resultados:
            escribir_texto(self.texto_resumen, "Sin resultados para mostrar.")
            return
        resumen = resumir_resultados(resultados)
        for fila in resumen:
            self.tabla_resumen.insert(
                "",
                "end",
                values=(
                    fila["algoritmo"],
                    fila["ejecuciones"],
                    fila["exitos"],
                    _fmt(fila["costo_mejor"]),
                    _fmt(fila["costo_promedio"]),
                    _fmt(fila["desviacion_costo"]),
                    _fmt(fila["tiempo_promedio"], 4),
                ),
            )
        validas = [r for r in resultados if r.exito and r.solucion and r.solucion.valida]
        mejor = min(
            (r for r in resultados if r.solucion is not None),
            key=lambda r: r.solucion.costo_objetivo,
            default=None,
        )
        texto = formatear_tabla_resumen(resumen)
        texto += f"\n\nTotal de ejecuciones: {len(resultados)}; válidas: {len(validas)}."
        if mejor is not None:
            texto += (
                f"\nMejor solución global: {mejor.algoritmo}, costo "
                f"{mejor.solucion.costo_total:.2f}, orden {mejor.solucion.orden_entregas}."
            )
        escribir_texto(self.texto_resumen, texto)
        self._actualizar_indicadores(resultados, validas, mejor)

        for indice, resultado in enumerate(resultados, start=1):
            orden = resultado.solucion.orden_entregas if resultado.solucion else ""
            iid = self.tabla_ejecuciones.insert(
                "",
                "end",
                values=(
                    indice,
                    resultado.algoritmo,
                    resultado.semilla if resultado.semilla is not None else "n/d",
                    _fmt(resultado.costo),
                    "Sí"
                    if (resultado.exito and resultado.solucion and resultado.solucion.valida)
                    else "No",
                    _fmt(resultado.tiempo_ejecucion, 4),
                    _fmt(_nodos(resultado), 0),
                    json.dumps(orden, ensure_ascii=False),
                ),
            )
            self._resultados_por_iid[iid] = resultado
        hijos = self.tabla_ejecuciones.get_children()
        if hijos:
            self.tabla_ejecuciones.selection_set(hijos[0])
            self._seleccionar_ejecucion()

    def _actualizar_indicadores(
        self,
        resultados: list[ResultadoEjecucion],
        validas: list[ResultadoEjecucion],
        mejor: ResultadoEjecucion | None,
    ) -> None:
        if mejor is not None:
            self._indicadores["mejor_costo"].configure(
                text=f"{_fmt(mejor.costo)}  ({mejor.algoritmo})",
                foreground=COLORES["exito"],
            )
            self._indicadores["mejor_solucion"].configure(
                text=f"{mejor.algoritmo}\norden {mejor.solucion.orden_entregas}",
                foreground=COLORES["acento"],
            )
        con_tiempo = [r for r in validas if r.tiempo_ejecucion > 0]
        if con_tiempo:
            rapido = min(con_tiempo, key=lambda r: r.tiempo_ejecucion)
            self._indicadores["menor_tiempo"].configure(
                text=f"{_fmt(rapido.tiempo_ejecucion, 4)} s\n{rapido.algoritmo}",
                foreground=COLORES["exito"],
            )
        con_nodos = [(r, _nodos(r)) for r in resultados if _nodos(r) is not None]
        if con_nodos:
            menos = min(con_nodos, key=lambda par: par[1])
            self._indicadores["menos_nodos"].configure(
                text=f"{_fmt(menos[1], 0)}\n{menos[0].algoritmo}",
                foreground=COLORES["exito"],
            )
        if self.plan:
            self._indicadores["costo_final"].configure(
                text=f"{_fmt(self.plan.get('costo_total'))}",
                foreground=COLORES["exito"],
            )
        if self.juego is not None:
            rec = self.juego.recomendacion
            self._indicadores["estrategia"].configure(
                text=f"{rec.get('estrategia_empresa', 'n/d')}\n"
                f"vs {rec.get('estrategia_competidor', 'n/d')}",
                foreground=COLORES["acento"],
            )

    def mostrar_juego(self, juego) -> None:
        self.juego = juego
        for widget in self._matriz_widgets:
            widget.destroy()
        self._matriz_widgets.clear()
        for hijo in self.marco_matriz.winfo_children():
            hijo.destroy()
        estrategias_empresa = list(juego.estrategias_empresa)
        estrategias_competidor = list(juego.estrategias_competidor)
        nash = {tuple(par) for par in juego.analisis.get("equilibrios_nash", [])}
        mejores_empresa = juego.analisis.get("mejores_respuestas_empresa", {})
        mejores_competidor = juego.analisis.get("mejores_respuestas_competidor", {})
        dominadas = set(juego.analisis.get("dominadas_empresa", []))
        dominantes_empresa = set(juego.analisis.get("dominantes_empresa", []))
        dominantes_competidor = set(juego.analisis.get("dominantes_competidor", []))

        tk.Label(
            self.marco_matriz,
            text="Empresa / Competidor",
            font=("Segoe UI", 9, "bold"),
            padx=6,
            pady=4,
            background="#e4e7eb",
        ).grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        for columna, competidor in enumerate(estrategias_competidor, start=1):
            etiqueta = tk.Label(
                self.marco_matriz,
                text=competidor + (" ★" if competidor in dominantes_competidor else ""),
                font=("Segoe UI", 9, "bold"),
                padx=6,
                pady=4,
                background="#c6f6d5" if competidor in dominantes_competidor else "#e4e7eb",
            )
            etiqueta.grid(row=0, column=columna, sticky="nsew", padx=1, pady=1)
            self._matriz_widgets.append(etiqueta)
        for fila, empresa in enumerate(estrategias_empresa, start=1):
            etiqueta = tk.Label(
                self.marco_matriz,
                text=empresa + (" ★" if empresa in dominantes_empresa else ""),
                font=("Segoe UI", 9, "bold"),
                padx=6,
                pady=4,
                background="#c6f6d5" if empresa in dominantes_empresa else "#e4e7eb",
            )
            etiqueta.grid(row=fila, column=0, sticky="nsew", padx=1, pady=1)
            self._matriz_widgets.append(etiqueta)
            for columna, competidor in enumerate(estrategias_competidor, start=1):
                pago_empresa, pago_competidor = juego.pago(empresa, competidor)
                es_nash = (empresa, competidor) in nash
                es_mejor_empresa = empresa in mejores_empresa.get(competidor, [])
                es_mejor_competidor = competidor in mejores_competidor.get(empresa, [])
                if es_nash:
                    fondo, borde = "#f6d365", "#b7791f"
                elif es_mejor_empresa and es_mejor_competidor:
                    fondo, borde = "#c6f6d5", "#2f855a"
                elif es_mejor_empresa or es_mejor_competidor:
                    fondo, borde = "#dbe7f3", "#2e75b6"
                elif empresa in dominadas:
                    fondo, borde = "#e5e7eb", "#9aa5b1"
                else:
                    fondo, borde = "#ffffff", "#cbd2d9"
                etiqueta = tk.Label(
                    self.marco_matriz,
                    text=f"({pago_empresa:.1f}, {pago_competidor:.1f})",
                    font=("Segoe UI", 9, "bold" if es_nash else "normal"),
                    padx=8,
                    pady=6,
                    background=fondo,
                    foreground="#1f2933",
                    highlightthickness=2,
                    highlightbackground=borde,
                )
                etiqueta.grid(row=fila, column=columna, sticky="nsew", padx=1, pady=1)
                self._matriz_widgets.append(etiqueta)
        leyenda = tk.Frame(self.marco_matriz, background="#ffffff")
        leyenda.grid(
            row=len(estrategias_empresa) + 1,
            column=0,
            columnspan=len(estrategias_competidor) + 1,
            sticky="w",
            pady=(6, 0),
        )
        self._matriz_widgets.append(leyenda)
        for texto, color in (
            ("Nash", "#f6d365"),
            ("Mejor respuesta (empresa/competidor)", "#dbe7f3"),
            ("Ambos mejores / dominante ★", "#c6f6d5"),
            ("Dominada", "#e5e7eb"),
        ):
            tk.Label(
                leyenda,
                text="  ",
                background=color,
                relief="solid",
                borderwidth=1,
                width=2,
            ).pack(side="left", padx=(6, 2))
            tk.Label(leyenda, text=texto, background="#ffffff").pack(side="left")

        rec = juego.recomendacion
        texto = juego.resumen_texto()
        texto += (
            f"\n\nTipo de recomendación: {rec.get('tipo')}."
            f"\nIngreso base: {_fmt(juego.metricas.get('ingreso_base'))}; "
            f"costo base: {_fmt(juego.metricas.get('costo_base'))}."
        )
        escribir_texto(self.texto_juego, texto)
        if self.plan:
            self._indicadores["costo_final"].configure(
                text=f"{_fmt(self.plan.get('costo_total'))}",
                foreground=COLORES["exito"],
            )
        if self.juego is not None:
            self._indicadores["estrategia"].configure(
                text=f"{rec.get('estrategia_empresa', 'n/d')}\n"
                f"vs {rec.get('estrategia_competidor', 'n/d')}",
                foreground=COLORES["acento"],
            )

    def mostrar_adversaria(self, datos: dict) -> None:
        self.adversaria = datos
        for iid in self.tabla_adversaria.get_children():
            self.tabla_adversaria.delete(iid)
        filas = datos.get("filas", [])
        for fila in filas:
            self.tabla_adversaria.insert(
                "",
                "end",
                values=(
                    fila.get("profundidad"),
                    _fmt(fila.get("valor_minimax")),
                    _fmt(fila.get("valor_alfa_beta")),
                    _fmt(fila.get("diferencia"), 6),
                    "Sí" if fila.get("iguales") else "No",
                    fila.get("nodos_minimax"),
                    fila.get("nodos_alfa_beta"),
                    fila.get("nodos_podados_alfa_beta"),
                    _fmt(fila.get("reduccion_nodos_pct")),
                ),
            )
        minimax = datos.get("minimax") or []
        alfa = datos.get("alfa_beta") or []
        lineas = []
        if filas:
            lineas.append("Verificación Minimax vs. alfa-beta")
            for fila in filas:
                lineas.append(
                    f"Profundidad {fila['profundidad']}: valores "
                    f"{fila['valor_minimax']:.4f} y {fila['valor_alfa_beta']:.4f}; "
                    f"¿iguales? {'sí' if fila['iguales'] else 'no'}; "
                    f"nodos {fila['nodos_minimax']} vs {fila['nodos_alfa_beta']}, "
                    f"podados {fila['nodos_podados_alfa_beta']}."
                )
        if minimax:
            lineas.append("\nMinimax de mayor profundidad:")
            lineas.append(minimax[-1].resumen_texto())
        if alfa:
            lineas.append("\nAlfa-beta de mayor profundidad:")
            lineas.append(alfa[-1].resumen_texto())
            estado = alfa[-1].estado_final
            lineas.append(
                "\nEstado final de referencia: "
                f"riesgo={estado.get('riesgo')}, impacto={estado.get('impacto')}, "
                f"bloqueos={estado.get('bloqueos')}, reservas={estado.get('reservas')}."
            )
        escribir_texto(
            self.texto_adversaria, "\n".join(lineas) or "Sin datos adversarios."
        )
        self.panel_acciones.mostrar(
            self.juego, self.adversaria, self.plan, self.resultados
        )

    def mostrar_plan(self, plan: dict) -> None:
        self.plan = plan
        riesgos = plan.get("riesgos_competidor", {})
        estrategia = plan.get("estrategia_recomendada", {})
        recursos = plan.get("recursos_utilizados", {})
        lineas = [
            f"PLAN FINAL: {plan.get('id_plan', 'n/d')}",
            f"Escenario: {plan.get('nombre_escenario')} ({plan.get('escenario_id')})",
            f"Fecha: {plan.get('fecha')}",
            f"Válido: {'sí' if plan.get('plan_valido') else 'no'}",
            "",
            f"Orden de entregas: {plan.get('orden_entregas')}",
            f"Nombres: {', '.join(plan.get('nombres_entregas', []))}",
            f"Costo total: {_fmt(plan.get('costo_total'))}",
            f"Pasos: {plan.get('pasos')}; longitud: {plan.get('longitud_ruta')}",
            "",
            "Recursos utilizados:",
        ]
        for clave, valor in recursos.items():
            lineas.append(f"  - {clave}: {_fmt(valor)}")
        lineas.extend(
            [
                "",
                f"Riesgo del competidor: {riesgos.get('nivel', 'n/d')}",
                f"Riesgo acumulado: {_fmt(riesgos.get('riesgo_acumulado'), 4)}",
                f"Impacto en costos: {_fmt(riesgos.get('impacto_costos'), 4)}",
                f"Bloqueos: {riesgos.get('bloqueos', 'n/d')}",
                f"Acción recomendada: {riesgos.get('accion_empresa_recomendada', 'n/d')}",
                "",
                "Estrategia recomendada del juego:",
                f"  Empresa: {estrategia.get('estrategia_empresa', 'n/d')}",
                f"  Competidor: {estrategia.get('estrategia_competidor', 'n/d')}",
                f"  Motivo: {estrategia.get('motivo', 'n/d')}",
                f"  Nash: {estrategia.get('equilibrios_nash', [])}",
                "",
                "Justificación:",
            ]
        )
        lineas.extend(f"  - {texto}" for texto in plan.get("justificacion", []))
        lineas.extend(["", "Rutas por tramo:"])
        for tramo in plan.get("rutas", []):
            lineas.append(
                f"  - {tramo.get('origen_nombre')} -> {tramo.get('destino_nombre')}: "
                f"costo={_fmt(tramo.get('costo'))}, pasos={tramo.get('pasos')}"
            )
        lineas.extend(
            [
                "",
                "El recorrido final se muestra en la pestaña Rutas, opción "
                "'Recorrido final (planificación)'.",
            ]
        )
        escribir_texto(self.texto_plan, "\n".join(lineas))
        self._indicadores["costo_final"].configure(
            text=f"{_fmt(plan.get('costo_total'))}",
            foreground=COLORES["exito"],
        )
        self.panel_rutas.mostrar(self.resultados, self.plan)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _seleccionar_ejecucion(self, _evento=None) -> None:
        seleccion = self.tabla_ejecuciones.selection()
        if not seleccion:
            return
        resultado = self._resultados_por_iid.get(seleccion[0])
        if resultado is None:
            return
        lineas = [
            f"Algoritmo: {resultado.algoritmo}",
            f"Ejecución: {resultado.id_ejecucion}",
            f"Semilla: {resultado.semilla if resultado.semilla is not None else 'n/d'}",
            f"Éxito: {resultado.exito}; mensaje: {resultado.mensaje}",
            f"Costo: {_fmt(resultado.costo)}; tiempo: {_fmt(resultado.tiempo_ejecucion, 4)} s",
        ]
        if resultado.solucion is not None:
            s = resultado.solucion
            lineas.extend(
                [
                    f"Solución válida: {s.valida}; violaciones: {s.violaciones or 'ninguna'}",
                    f"Orden: {s.orden_entregas}",
                    f"Recursos: combustible={_fmt(s.combustible_consumido)}, "
                    f"tiempo={_fmt(s.tiempo_consumido)}, "
                    f"presupuesto={_fmt(s.presupuesto_consumido)}, "
                    f"carga={_fmt(s.carga_maxima)}",
                ]
            )
        if resultado.parametros:
            lineas.append(
                "Parámetros: "
                + json.dumps(resultado.parametros, ensure_ascii=False, sort_keys=True)
            )
        if resultado.metricas:
            lineas.append(
                "Métricas: "
                + json.dumps(resultado.metricas, ensure_ascii=False, sort_keys=True)
            )
        escribir_texto(self.detalle_ejecucion, "\n".join(lineas))
