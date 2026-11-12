"""Panel de configuración validada de recursos, competidor y algoritmos."""

from __future__ import annotations

import json
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable

from interfaz.componentes import etiqueta_valor
from modelos.escenario import Escenario
from modelos.recurso import Recurso


def _parsear_bloqueadas(texto: str) -> list[list[int]]:
    pares = re.findall(r"(-?\d+)\s*,\s*(-?\d+)", texto or "")
    return [[int(f), int(c)] for f, c in pares]


class PanelConfiguracion(ttk.Frame):
    """Configura recursos, competidor y parámetros de todos los algoritmos."""

    def __init__(
        self,
        master,
        escenario: Escenario,
        parametros: dict,
        al_aplicar: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, padding=6)
        self.escenario = escenario
        self.parametros = parametros
        self.al_aplicar = al_aplicar
        self._crear_variables()
        self._construir()
        self.cargar_desde(escenario, parametros)

    # ------------------------------------------------------------------
    def _crear_variables(self) -> None:
        self.var_combustible = tk.StringVar()
        self.var_consumo_combustible = tk.StringVar()
        self.var_capacidad = tk.StringVar()
        self.var_tiempo = tk.StringVar()
        self.var_consumo_tiempo = tk.StringVar()
        self.var_presupuesto = tk.StringVar()
        self.var_diagonal = tk.BooleanVar()
        self.var_factor_diagonal = tk.StringVar()

        self.var_comp_nombre = tk.StringVar()
        self.var_comp_costo = tk.StringVar()
        self.var_comp_presupuesto = tk.StringVar()
        self.var_comp_bloqueadas = tk.StringVar()

        self.var_hc_max_iter = tk.StringVar()
        self.var_hc_mesetas = tk.BooleanVar()
        self.var_hc_max_mesetas = tk.StringVar()

        self.var_sa_t0 = tk.StringVar()
        self.var_sa_tf = tk.StringVar()
        self.var_sa_alfa = tk.StringVar()
        self.var_sa_iter_temp = tk.StringVar()
        self.var_sa_max_iter = tk.StringVar()

        self.var_ga_poblacion = tk.StringVar()
        self.var_ga_generaciones = tk.StringVar()
        self.var_ga_cruza = tk.StringVar()
        self.var_ga_mutacion = tk.StringVar()
        self.var_ga_elitismo = tk.StringVar()
        self.var_ga_torneo = tk.StringVar()

        self.var_exp_repeticiones = tk.StringVar()
        self.var_exp_inicios = tk.StringVar()
        self.var_exp_semilla = tk.StringVar()
        self.var_exp_profundidades = tk.StringVar()
        self.var_mensaje = tk.StringVar(value="")

    def _construir(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.notebook = notebook

        self._tab_recursos(notebook)
        self._tab_competidor(notebook)
        self._tab_algoritmos(notebook)
        self._tab_experimentos(notebook)

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(6, 0))
        self.btn_aplicar = ttk.Button(
            barra, text="Aplicar al escenario", command=self._aplicar
        )
        self.btn_aplicar.pack(side="left")
        self.btn_recargar = ttk.Button(
            barra, text="Recargar desde escenario", command=self._recargar
        )
        self.btn_recargar.pack(side="left", padx=6)
        self._botones = [self.btn_aplicar, self.btn_recargar]
        ttk.Label(
            barra,
            textvariable=self.var_mensaje,
            foreground="#b00020",
            wraplength=700,
        ).pack(side="left", padx=8)

    def _tab_recursos(self, notebook: ttk.Notebook) -> None:
        marco = ttk.Frame(notebook, padding=10)
        notebook.add(marco, text="Recursos y movimiento")
        ttk.Label(marco, text="Recursos limitados", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w"
        )
        etiqueta_valor(marco, "Combustible disponible", self.var_combustible, 1)
        etiqueta_valor(marco, "Consumo por paso", self.var_consumo_combustible, 2)
        etiqueta_valor(marco, "Capacidad de carga", self.var_capacidad, 3)
        etiqueta_valor(marco, "Tiempo disponible", self.var_tiempo, 4)
        etiqueta_valor(marco, "Consumo de tiempo/paso", self.var_consumo_tiempo, 5)
        etiqueta_valor(marco, "Presupuesto", self.var_presupuesto, 6)
        ttk.Separator(marco, orient="horizontal").grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=10
        )
        ttk.Label(marco, text="Movimiento", font=("Segoe UI", 10, "bold")).grid(
            row=8, column=0, columnspan=4, sticky="w"
        )
        ttk.Checkbutton(
            marco,
            text="Permitir movimiento diagonal (costo multiplicado)",
            variable=self.var_diagonal,
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=3)
        etiqueta_valor(marco, "Factor diagonal", self.var_factor_diagonal, 10)

    def _tab_competidor(self, notebook: ttk.Notebook) -> None:
        marco = ttk.Frame(notebook, padding=10)
        notebook.add(marco, text="Competidor")
        ttk.Label(
            marco,
            text="El competidor modifica costos o rutas en el juego estratégico.",
            wraplength=650,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        etiqueta_valor(marco, "Nombre", self.var_comp_nombre, 1, ancho=24)
        etiqueta_valor(marco, "Factor de costo", self.var_comp_costo, 2)
        etiqueta_valor(marco, "Factor de presupuesto", self.var_comp_presupuesto, 3)
        ttk.Label(marco, text="Celdas bloqueadas (fila,col; fila,col)").grid(
            row=4, column=0, sticky="w", padx=4, pady=3
        )
        ttk.Entry(marco, textvariable=self.var_comp_bloqueadas, width=34).grid(
            row=4, column=1, columnspan=2, sticky="w", padx=4, pady=3
        )
        ttk.Label(
            marco,
            text="Ejemplo: 7,8; 7,9; 8,8. Estas celdas no deben contener elementos.",
            wraplength=600,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=4)

    def _tab_algoritmos(self, notebook: ttk.Notebook) -> None:
        marco = ttk.Frame(notebook, padding=10)
        notebook.add(marco, text="Algoritmos")

        ttk.Label(marco, text="Hill Climbing", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w"
        )
        etiqueta_valor(marco, "Máx. iteraciones", self.var_hc_max_iter, 1)
        ttk.Checkbutton(
            marco, text="Permitir movimientos laterales (mesetas)", variable=self.var_hc_mesetas
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=3)
        etiqueta_valor(marco, "Máx. mesetas", self.var_hc_max_mesetas, 3)

        ttk.Separator(marco, orient="horizontal").grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=8
        )
        ttk.Label(marco, text="Recocido simulado", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, columnspan=4, sticky="w"
        )
        etiqueta_valor(marco, "Temperatura inicial", self.var_sa_t0, 6)
        etiqueta_valor(marco, "Temperatura final", self.var_sa_tf, 7)
        etiqueta_valor(marco, "Enfriamiento (0-1)", self.var_sa_alfa, 8)
        etiqueta_valor(marco, "Iteraciones por temperatura", self.var_sa_iter_temp, 9)
        etiqueta_valor(marco, "Máx. iteraciones", self.var_sa_max_iter, 10)

        ttk.Separator(marco, orient="horizontal").grid(
            row=11, column=0, columnspan=4, sticky="ew", pady=8
        )
        ttk.Label(marco, text="Algoritmo genético", font=("Segoe UI", 10, "bold")).grid(
            row=12, column=0, columnspan=4, sticky="w"
        )
        etiqueta_valor(marco, "Población", self.var_ga_poblacion, 13)
        etiqueta_valor(marco, "Generaciones", self.var_ga_generaciones, 14)
        etiqueta_valor(marco, "Prob. cruza", self.var_ga_cruza, 15)
        etiqueta_valor(marco, "Prob. mutación", self.var_ga_mutacion, 16)
        etiqueta_valor(marco, "Elitismo", self.var_ga_elitismo, 17)
        etiqueta_valor(marco, "Tamaño de torneo", self.var_ga_torneo, 18)

    def _tab_experimentos(self, notebook: ttk.Notebook) -> None:
        marco = ttk.Frame(notebook, padding=10)
        notebook.add(marco, text="Experimentos")
        etiqueta_valor(marco, "Repeticiones metaheurísticas", self.var_exp_repeticiones, 0)
        etiqueta_valor(marco, "Inicios de Hill Climbing", self.var_exp_inicios, 1)
        etiqueta_valor(marco, "Semilla base", self.var_exp_semilla, 2)
        etiqueta_valor(marco, "Profundidades adversarias separadas por comas", self.var_exp_profundidades, 3, ancho=18)
        ttk.Label(
            marco,
            text=(
                "Los experimentos completos usan estas repeticiones y semilla base. "
                "Cada ejecución individual registra además su propia semilla."
            ),
            wraplength=650,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=10)

    # ------------------------------------------------------------------
    # Carga y validación
    # ------------------------------------------------------------------
    def cargar_desde(self, escenario: Escenario, parametros: dict) -> None:
        self.escenario = escenario
        self.parametros = parametros
        rec = escenario.recursos
        self.var_combustible.set(f"{rec.get('combustible', Recurso('combustible', 0)).cantidad:g}")
        self.var_consumo_combustible.set(
            f"{rec.get('combustible', Recurso('combustible', 0)).consumo_por_paso:g}"
        )
        self.var_capacidad.set(f"{rec.get('capacidad', Recurso('capacidad', 0)).cantidad:g}")
        self.var_tiempo.set(f"{rec.get('tiempo', Recurso('tiempo', 0)).cantidad:g}")
        self.var_consumo_tiempo.set(
            f"{rec.get('tiempo', Recurso('tiempo', 0)).consumo_por_paso:g}"
        )
        self.var_presupuesto.set(f"{rec.get('presupuesto', Recurso('presupuesto', 0)).cantidad:g}")
        self.var_diagonal.set(escenario.permitir_diagonal)
        self.var_factor_diagonal.set(f"{escenario.factor_costo_diagonal:g}")
        self.var_comp_nombre.set(str(escenario.competidor.get("nombre", "Competidor")))
        self.var_comp_costo.set(f"{escenario.competidor.get('factor_costo', 1.0):g}")
        self.var_comp_presupuesto.set(
            f"{escenario.competidor.get('factor_presupuesto', 1.0):g}"
        )
        self.var_comp_bloqueadas.set(
            "; ".join(
                f"{f},{c}" for f, c in escenario.competidor.get("celdas_bloqueadas", [])
            )
        )
        hc = parametros.get("hill_climbing", {})
        self.var_hc_max_iter.set(str(hc.get("max_iteraciones", 500)))
        self.var_hc_mesetas.set(bool(hc.get("permitir_mesetas", False)))
        self.var_hc_max_mesetas.set(str(hc.get("max_mesetas", 20)))
        sa = parametros.get("recocido_simulado", {})
        self.var_sa_t0.set(str(sa.get("temperatura_inicial", 50.0)))
        self.var_sa_tf.set(str(sa.get("temperatura_final", 0.01)))
        self.var_sa_alfa.set(str(sa.get("enfriamiento", 0.95)))
        self.var_sa_iter_temp.set(str(sa.get("iteraciones_por_temperatura", 15)))
        self.var_sa_max_iter.set(str(sa.get("max_iteraciones", 2500)))
        ga = parametros.get("algoritmo_genetico", {})
        self.var_ga_poblacion.set(str(ga.get("tamano_poblacion", 30)))
        self.var_ga_generaciones.set(str(ga.get("generaciones", 80)))
        self.var_ga_cruza.set(str(ga.get("prob_cruza", 0.85)))
        self.var_ga_mutacion.set(str(ga.get("prob_mutacion", 0.2)))
        self.var_ga_elitismo.set(str(ga.get("elitismo", 2)))
        self.var_ga_torneo.set(str(ga.get("tamano_torneo", 3)))
        exp = parametros.get("experimentos", {})
        self.var_exp_repeticiones.set(str(exp.get("repeticiones_metaheuristicas", 20)))
        self.var_exp_inicios.set(str(exp.get("num_inicios_hill", 10)))
        self.var_exp_semilla.set(str(exp.get("semilla_base", 2026)))
        profundidades = exp.get("profundidades_adversarias", [2, 4, 6])
        self.var_exp_profundidades.set(", ".join(str(p) for p in profundidades))
        self.var_mensaje.set("")

    def _recargar(self) -> None:
        self.cargar_desde(self.escenario, self.parametros)
        self.var_mensaje.set("Valores recargados desde el escenario.")

    def establecer_habilitado(self, habilitado: bool) -> None:
        estado = "normal" if habilitado else "disabled"
        for boton in getattr(self, "_botones", []):
            boton.configure(state=estado)
        for hijo in self.winfo_children():
            self._bloquear(hijo, estado)

    def _bloquear(self, widget, estado: str) -> None:
        for hijo in widget.winfo_children():
            if isinstance(
                hijo,
                (
                    ttk.Entry,
                    ttk.Button,
                    ttk.Checkbutton,
                    ttk.Combobox,
                ),
            ):
                try:
                    hijo.configure(state=estado)
                except tk.TclError:
                    pass
            self._bloquear(hijo, estado)

    @staticmethod
    def _leer_float(
        variable: tk.StringVar,
        nombre: str,
        minimo: float | None = None,
        maximo: float | None = None,
        errores: list[str] | None = None,
    ) -> float | None:
        errores = errores if errores is not None else []
        try:
            valor = float(variable.get().strip().replace(",", "."))
        except ValueError:
            errores.append(f"{nombre}: debe ser un número.")
            return None
        if minimo is not None and valor < minimo:
            errores.append(f"{nombre}: debe ser >= {minimo}.")
        if maximo is not None and valor > maximo:
            errores.append(f"{nombre}: debe ser <= {maximo}.")
        return valor

    @staticmethod
    def _leer_int(
        variable: tk.StringVar,
        nombre: str,
        minimo: int | None = None,
        errores: list[str] | None = None,
    ) -> int | None:
        errores = errores if errores is not None else []
        try:
            texto = variable.get().strip()
            valor = int(texto)
        except ValueError:
            errores.append(f"{nombre}: debe ser un entero.")
            return None
        if minimo is not None and valor < minimo:
            errores.append(f"{nombre}: debe ser >= {minimo}.")
        return valor

    def validar_parametros(self) -> list[str]:
        errores: list[str] = []
        self._leer_float(self.var_combustible, "Combustible", 0.001, errores=errores)
        self._leer_float(self.var_consumo_combustible, "Consumo combustible", 0.0, errores=errores)
        self._leer_float(self.var_capacidad, "Capacidad", 0.001, errores=errores)
        self._leer_float(self.var_tiempo, "Tiempo", 0.001, errores=errores)
        self._leer_float(self.var_consumo_tiempo, "Consumo tiempo", 0.0, errores=errores)
        self._leer_float(self.var_presupuesto, "Presupuesto", 0.001, errores=errores)
        self._leer_float(self.var_factor_diagonal, "Factor diagonal", 0.001, errores=errores)
        self._leer_float(self.var_comp_costo, "Factor costo competidor", 0.001, errores=errores)
        self._leer_float(
            self.var_comp_presupuesto, "Factor presupuesto competidor", 0.001, errores=errores
        )
        if not self.var_comp_nombre.get().strip():
            errores.append("El competidor debe tener nombre.")

        self._leer_int(self.var_hc_max_iter, "HC max iteraciones", 1, errores=errores)
        self._leer_int(self.var_hc_max_mesetas, "HC max mesetas", 0, errores=errores)
        t0 = self._leer_float(self.var_sa_t0, "SA temperatura inicial", 0.0000001, errores=errores)
        tf = self._leer_float(self.var_sa_tf, "SA temperatura final", 0.0000001, errores=errores)
        alfa = self._leer_float(self.var_sa_alfa, "SA enfriamiento", 0.0000001, 0.9999999, errores)
        self._leer_int(self.var_sa_iter_temp, "SA iteraciones/temperatura", 1, errores=errores)
        self._leer_int(self.var_sa_max_iter, "SA max iteraciones", 1, errores=errores)
        if t0 is not None and tf is not None and t0 <= tf:
            errores.append("SA: la temperatura inicial debe ser mayor que la final.")
        if alfa is not None and not 0 < alfa < 1:
            errores.append("SA: el enfriamiento debe estar entre 0 y 1.")
        poblacion = self._leer_int(self.var_ga_poblacion, "GA población", 2, errores=errores)
        self._leer_int(self.var_ga_generaciones, "GA generaciones", 1, errores=errores)
        self._leer_float(self.var_ga_cruza, "GA prob. cruza", 0.0, 1.0, errores)
        self._leer_float(self.var_ga_mutacion, "GA prob. mutación", 0.0, 1.0, errores)
        elitismo = self._leer_int(self.var_ga_elitismo, "GA elitismo", 0, errores=errores)
        self._leer_int(self.var_ga_torneo, "GA torneo", 1, errores=errores)
        if poblacion is not None and elitismo is not None and elitismo >= poblacion:
            errores.append("GA: el elitismo debe ser menor que la población.")
        self._leer_int(self.var_exp_repeticiones, "Repeticiones", 1, errores=errores)
        self._leer_int(self.var_exp_inicios, "Inicios de Hill Climbing", 1, errores=errores)
        self._leer_int(self.var_exp_semilla, "Semilla base", 0, errores=errores)
        try:
            profundidades = [
                int(x.strip())
                for x in self.var_exp_profundidades.get().replace(";", ",").split(",")
                if x.strip()
            ]
        except ValueError:
            profundidades = []
            errores.append("Profundidades adversarias: use enteros separados por comas.")
        if not profundidades or any(p < 2 for p in profundidades):
            errores.append("Profundidades adversarias: deben ser >= 2.")
        return errores

    def obtener_parametros(self) -> dict:
        errores = self.validar_parametros()
        if errores:
            raise ValueError("\n".join(errores))
        profundidades = [
            int(x.strip())
            for x in self.var_exp_profundidades.get().replace(";", ",").split(",")
            if x.strip()
        ]
        return {
            "hill_climbing": {
                "max_iteraciones": int(self.var_hc_max_iter.get()),
                "permitir_mesetas": bool(self.var_hc_mesetas.get()),
                "max_mesetas": int(self.var_hc_max_mesetas.get()),
            },
            "recocido_simulado": {
                "temperatura_inicial": float(self.var_sa_t0.get().replace(",", ".")),
                "temperatura_final": float(self.var_sa_tf.get().replace(",", ".")),
                "enfriamiento": float(self.var_sa_alfa.get().replace(",", ".")),
                "iteraciones_por_temperatura": int(self.var_sa_iter_temp.get()),
                "max_iteraciones": int(self.var_sa_max_iter.get()),
            },
            "algoritmo_genetico": {
                "tamano_poblacion": int(self.var_ga_poblacion.get()),
                "generaciones": int(self.var_ga_generaciones.get()),
                "prob_cruza": float(self.var_ga_cruza.get().replace(",", ".")),
                "prob_mutacion": float(self.var_ga_mutacion.get().replace(",", ".")),
                "elitismo": int(self.var_ga_elitismo.get()),
                "tamano_torneo": int(self.var_ga_torneo.get()),
            },
            "experimentos": {
                "repeticiones_metaheuristicas": int(self.var_exp_repeticiones.get()),
                "num_inicios_hill": int(self.var_exp_inicios.get()),
                "semilla_base": int(self.var_exp_semilla.get()),
                "profundidades_adversarias": profundidades,
            },
        }

    def aplicar_a_escenario(self) -> list[str]:
        errores = self.validar_parametros()
        if errores:
            self.var_mensaje.set("Corrija los parámetros antes de aplicar.")
            return errores
        escenario = self.escenario
        respaldo = escenario.clonar()
        estado_anterior = json.dumps(escenario.a_dict(), sort_keys=True, ensure_ascii=False)
        try:
            escenario.recursos["combustible"].cantidad = float(self.var_combustible.get().replace(",", "."))
            escenario.recursos["combustible"].consumo_por_paso = float(
                self.var_consumo_combustible.get().replace(",", ".")
            )
            escenario.recursos["capacidad"].cantidad = float(self.var_capacidad.get().replace(",", "."))
            escenario.recursos["tiempo"].cantidad = float(self.var_tiempo.get().replace(",", "."))
            escenario.recursos["tiempo"].consumo_por_paso = float(
                self.var_consumo_tiempo.get().replace(",", ".")
            )
            escenario.recursos["presupuesto"].cantidad = float(self.var_presupuesto.get().replace(",", "."))
            escenario.permitir_diagonal = bool(self.var_diagonal.get())
            escenario.factor_costo_diagonal = float(self.var_factor_diagonal.get().replace(",", "."))
            bloqueadas = _parsear_bloqueadas(self.var_comp_bloqueadas.get())
            ocupadas = escenario.posiciones_ocupadas()
            for f, c in bloqueadas:
                if not escenario.dentro(f, c):
                    raise ValueError(f"Celda bloqueada fuera de la cuadrícula: ({f}, {c})")
                if (f, c) in ocupadas:
                    raise ValueError(
                        f"La celda bloqueada ({f}, {c}) está ocupada por un elemento."
                    )
            escenario.competidor = {
                "nombre": self.var_comp_nombre.get().strip(),
                "factor_costo": float(self.var_comp_costo.get().replace(",", ".")),
                "factor_presupuesto": float(self.var_comp_presupuesto.get().replace(",", ".")),
                "celdas_bloqueadas": bloqueadas,
                "descripcion": escenario.competidor.get("descripcion", ""),
            }
            escenario.restringir_recursos_competidor()
            errores_estructurales = escenario.validar()
            if errores_estructurales:
                self._restaurar(escenario, respaldo)
                self.var_mensaje.set("El escenario resultante no es válido; no se aplicó.")
                return errores_estructurales
        except (ValueError, KeyError) as exc:
            self._restaurar(escenario, respaldo)
            self.var_mensaje.set(str(exc))
            return [str(exc)]
        estado_nuevo = json.dumps(escenario.a_dict(), sort_keys=True, ensure_ascii=False)
        if estado_nuevo == estado_anterior:
            self.var_mensaje.set("La configuración no cambió.")
            return []
        self.var_mensaje.set("Configuración aplicada al escenario.")
        if self.al_aplicar:
            self.al_aplicar()
        return []

    @staticmethod
    def _restaurar(escenario: Escenario, respaldo: Escenario) -> None:
        escenario.recursos = respaldo.recursos
        escenario.competidor = respaldo.competidor
        escenario.permitir_diagonal = respaldo.permitir_diagonal
        escenario.factor_costo_diagonal = respaldo.factor_costo_diagonal

    def _aplicar(self) -> None:
        errores = self.aplicar_a_escenario()
        if errores:
            self.var_mensaje.set("Errores: " + " | ".join(errores))
