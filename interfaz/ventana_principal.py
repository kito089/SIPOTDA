"""Ventana principal de SIPOTDA."""

from __future__ import annotations

import copy
import os
import queue
import sys
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from experimentos.ejecutar_experimentos import (
    DIR_CSV,
    DIR_GRAFICAS,
    _combinar_parametros,
    ejecutar_todo,
)
from gestion_archivos.errores import (
    ErrorArchivo,
    ErrorSobrescritura,
    ErrorValidacion,
)
from gestion_archivos.exportar_resultados import exportar_resultados_csv
from gestion_archivos.guardar_escenario import guardar_escenario
from gestion_archivos.lector_json import cargar_escenario, cargar_parametros
from gestion_archivos.validar_escenario import validar_factibilidad
from interfaz.componentes import COLORES, MarcoDesplazable
from interfaz.editor_escenario import EditorEscenario
from interfaz.panel_configuracion import PanelConfiguracion
from interfaz.panel_resultados import PanelResultados
from modelos.escenario import Escenario


class VentanaPrincipal(tk.Tk):
    """Aplicación de escritorio que integra edición, algoritmos y resultados."""

    def __init__(self) -> None:
        super().__init__()
        self.title("SIPOTDA - Optimización logística")
        self.geometry("1360x900")
        self.minsize(1080, 720)
        self.configure(background=COLORES["fondo"])
        self._configurar_estilo()

        self.raiz = Path(__file__).resolve().parent.parent
        self.dir_escenarios = self.raiz / "escenarios"
        self.dir_configuracion = self.raiz / "configuracion"
        self.ruta_actual: Path | None = self.dir_escenarios / "escenario_predeterminado.json"
        self._modificado = False
        self._tarea_activa = False
        self._after_poll: str | None = None
        self._cola: queue.Queue = queue.Queue()
        self._error_inicial: str | None = None
        self._botones: list[ttk.Button] = []

        self.parametros = self._cargar_parametros_iniciales()
        self.escenario = self._cargar_escenario_inicial()
        self.resultados_actuales = []
        self.juego_actual = None
        self.adversaria_actual = None
        self.plan_actual = None

        self._construir_interfaz()
        self._actualizar_titulo()
        self._set_estado("Listo. Edite el escenario y pulse Ejecutar para correr todos los módulos.")
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        if self._error_inicial:
            self.after(
                250,
                lambda: messagebox.showwarning(
                    "Aviso al iniciar", self._error_inicial or ""
                ),
            )

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------
    def _configurar_estilo(self) -> None:
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("vista")
        except tk.TclError:
            try:
                estilo.theme_use("clam")
            except tk.TclError:
                pass
        estilo.configure("Treeview", rowheight=23)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        estilo.configure("TNotebook.Tab", padding=(12, 5))
        self.option_add("*Font", ("Segoe UI", 9))

    def _cargar_parametros_iniciales(self) -> dict:
        ruta = self.dir_configuracion / "parametros.json"
        datos = {}
        if ruta.exists():
            try:
                datos = cargar_parametros(ruta)
            except ErrorArchivo as exc:
                self._error_inicial = f"No se pudo cargar la configuración: {exc}"
        return _combinar_parametros(datos)

    def _cargar_escenario_inicial(self) -> Escenario:
        ruta = self.dir_escenarios / "escenario_predeterminado.json"
        try:
            return cargar_escenario(ruta)
        except (ErrorArchivo, ErrorValidacion, ValueError, OSError) as exc:
            self._error_inicial = (
                f"No se pudo cargar el escenario predeterminado: {exc}. "
                "Se abrió un escenario vacío."
            )
            return Escenario.crear_vacio()

    def _construir_interfaz(self) -> None:
        self._crear_menu()
        self._crear_barra_herramientas()
        self._crear_cuerpo()
        self._crear_barra_estado()
        self.bind("<Control-n>", lambda _e: self._nuevo_escenario())
        self.bind("<Control-o>", lambda _e: self._abrir_escenario())
        self.bind("<Control-s>", lambda _e: self._guardar())
        self.bind("<F5>", lambda _e: self._ejecutar())

    def _crear_menu(self) -> None:
        barra = tk.Menu(self)
        archivo = tk.Menu(barra, tearoff=0)
        archivo.add_command(
            label="Nuevo escenario",
            accelerator="Ctrl+N",
            command=self._nuevo_escenario,
        )
        archivo.add_command(
            label="Abrir escenario...",
            accelerator="Ctrl+O",
            command=self._abrir_escenario,
        )
        archivo.add_separator()
        archivo.add_command(
            label="Guardar", accelerator="Ctrl+S", command=self._guardar
        )
        archivo.add_separator()
        archivo.add_command(
            label="Exportar resultados CSV...", command=self._exportar_resultados
        )
        archivo.add_command(
            label="Abrir carpeta de resultados", command=self._abrir_resultados
        )
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self._cerrar)
        barra.add_cascade(label="Archivo", menu=archivo)

        ejecucion = tk.Menu(barra, tearoff=0)
        ejecucion.add_command(
            label="Ejecutar todos los módulos",
            accelerator="F5",
            command=self._ejecutar,
        )
        barra.add_cascade(label="Ejecución", menu=ejecucion)

        ayuda = tk.Menu(barra, tearoff=0)
        ayuda.add_command(label="Guía rápida", command=self._guia)
        ayuda.add_command(label="Acerca de SIPOTDA", command=self._acerca_de)
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.configure(menu=barra)

    def _crear_barra_herramientas(self) -> None:
        barra = ttk.Frame(self, padding=(8, 6))
        barra.pack(fill="x")
        for texto, comando in (
            ("Nuevo", self._nuevo_escenario),
            ("Abrir", self._abrir_escenario),
            ("Guardar", self._guardar),
        ):
            boton = ttk.Button(barra, text=texto, command=comando)
            boton.pack(side="left", padx=2)
            self._botones.append(boton)
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=8)
        self.btn_ejecutar = ttk.Button(
            barra,
            text="Ejecutar todos los módulos",
            command=self._ejecutar,
        )
        self.btn_ejecutar.pack(side="left", padx=2)
        self._botones.append(self.btn_ejecutar)
        ttk.Label(
            barra,
            text="Valida el escenario y ejecuta heurísticas, búsqueda local, "
            "metaheurísticas, juego, adversaria y planificación.",
            foreground="#52606d",
        ).pack(side="left", padx=10)

    def _crear_cuerpo(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self.tab_escenario = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_escenario, text="Escenario")
        self.marco_escenario = MarcoDesplazable(self.tab_escenario)
        self.marco_escenario.pack(fill="both", expand=True)
        self.editor = EditorEscenario(
            self.marco_escenario.interior,
            self.escenario,
            al_cambiar=self._al_cambiar_escenario,
            al_estado=self._set_estado,
        )
        self.editor.pack(fill="x", expand=False)
        self.panel_config = PanelConfiguracion(
            self.marco_escenario.interior,
            self.escenario,
            self.parametros,
            al_aplicar=self._al_aplicar_configuracion,
        )
        self.panel_config.pack(fill="x", expand=False, pady=(8, 0))

        self.tab_resultados = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_resultados, text="Resultados")
        self.panel_resultados = PanelResultados(self.tab_resultados)
        self.panel_resultados.pack(fill="both", expand=True)
        self.panel_resultados.establecer_escenario(self.escenario)
        self.notebook.select(self.tab_escenario)

    def _crear_barra_estado(self) -> None:
        barra = ttk.Frame(self, padding=(8, 3))
        barra.pack(fill="x", side="bottom")
        self.var_estado = tk.StringVar(value="Listo.")
        ttk.Label(barra, textvariable=self.var_estado, anchor="w").pack(
            side="left", fill="x", expand=True
        )
        self.progreso = ttk.Progressbar(barra, mode="indeterminate", length=160)
        self.progreso.pack(side="right", padx=6)
        self.var_ruta = tk.StringVar(value=str(self.ruta_actual or ""))
        ttk.Label(barra, textvariable=self.var_ruta, foreground="#52606d").pack(
            side="right", padx=6
        )

    # ------------------------------------------------------------------
    # Estado general
    # ------------------------------------------------------------------
    def _set_estado(self, mensaje: str) -> None:
        self.var_estado.set(mensaje)

    def _actualizar_titulo(self) -> None:
        marca = " *" if self._modificado else ""
        self.title(f"SIPOTDA - {self.escenario.nombre} ({self.escenario.id}){marca}")
        self.var_ruta.set(str(self.ruta_actual or "sin guardar"))

    def _marcar_modificado(self) -> None:
        self._modificado = True
        self._actualizar_titulo()

    def _al_cambiar_escenario(self) -> None:
        tenia_resultados = bool(
            self.resultados_actuales
            or self.juego_actual
            or self.adversaria_actual
            or self.plan_actual
        )
        self._marcar_modificado()
        self.editor.limpiar_rutas()
        if tenia_resultados:
            self._limpiar_resultados()
            self._set_estado(
                "Escenario modificado: los resultados anteriores se descartaron."
            )
        else:
            self._set_estado("Escenario modificado.")

    def _al_aplicar_configuracion(self) -> None:
        tenia_resultados = bool(
            self.resultados_actuales
            or self.juego_actual
            or self.adversaria_actual
            or self.plan_actual
        )
        self._marcar_modificado()
        self.editor.establecer_escenario(self.escenario)
        self.panel_resultados.establecer_escenario(self.escenario)
        if tenia_resultados:
            self._limpiar_resultados()
        self._set_estado("Configuración aplicada al escenario.")

    def _reemplazar_escenario(self, escenario: Escenario, ruta: Path | None) -> None:
        self.escenario = escenario
        self.ruta_actual = ruta
        self._modificado = False
        self.editor.establecer_escenario(escenario)
        self.panel_config.cargar_desde(escenario, self.parametros)
        self.panel_resultados.establecer_escenario(escenario)
        self._limpiar_resultados()
        self._actualizar_titulo()
        self._set_estado(f"Escenario cargado: {escenario.nombre}.")

    def _limpiar_resultados(self) -> None:
        self.resultados_actuales = []
        self.juego_actual = None
        self.adversaria_actual = None
        self.plan_actual = None
        self.panel_resultados.limpiar()
        self.editor.limpiar_rutas()

    # ------------------------------------------------------------------
    # Archivos
    # ------------------------------------------------------------------
    def _confirmar_descarte(self) -> bool:
        if not self._modificado:
            return True
        return messagebox.askyesno(
            "Cambios sin guardar",
            "Hay cambios sin guardar. ¿Desea descartarlos?",
        )

    def _nuevo_escenario(self) -> None:
        if self._tarea_activa or not self._confirmar_descarte():
            return
        self._reemplazar_escenario(Escenario.crear_vacio(), None)
        self._set_estado("Nuevo escenario vacío creado.")

    def _abrir_escenario(self) -> None:
        if self._tarea_activa or not self._confirmar_descarte():
            return
        ruta = filedialog.askopenfilename(
            title="Abrir escenario",
            initialdir=str(self.dir_escenarios),
            filetypes=[("Escenario JSON", "*.json"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        try:
            escenario = cargar_escenario(ruta)
        except (ErrorArchivo, ErrorValidacion, ValueError) as exc:
            messagebox.showerror("No se pudo abrir", str(exc))
            return
        self._reemplazar_escenario(escenario, Path(ruta))

    def _guardar(self) -> None:
        if self._tarea_activa:
            return
        ruta = self.ruta_actual
        if ruta is None:
            seleccion = filedialog.asksaveasfilename(
                title="Guardar escenario",
                initialdir=str(self.dir_escenarios),
                initialfile=f"{self.escenario.id}.json",
                defaultextension=".json",
                filetypes=[("Escenario JSON", "*.json"), ("Todos", "*.*")],
            )
            if not seleccion:
                return
            ruta = Path(seleccion)
        self._guardar_en(ruta)

    def _guardar_en(self, ruta: Path) -> None:
        try:
            guardar_escenario(self.escenario, ruta, sobrescribir=True)
        except (ValueError, ErrorArchivo, ErrorSobrescritura) as exc:
            messagebox.showerror("No se pudo guardar", str(exc))
            return
        self.ruta_actual = ruta
        self._modificado = False
        self._actualizar_titulo()
        self._set_estado(f"Escenario guardado en {ruta}.")

    def _exportar_resultados(self) -> None:
        if not self.resultados_actuales:
            messagebox.showinfo(
                "Sin resultados", "Ejecute todos los módulos para generar resultados."
            )
            return
        ruta = filedialog.asksaveasfilename(
            title="Exportar resultados",
            initialdir=str(DIR_CSV),
            initialfile="resultados_exportados.csv",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        try:
            exportar_resultados_csv(self.resultados_actuales, ruta)
        except (ErrorArchivo, OSError) as exc:
            messagebox.showerror("No se pudo exportar", str(exc))
            return
        self._set_estado(f"Resultados exportados a {ruta}.")

    def _abrir_resultados(self) -> None:
        try:
            os.startfile(str(DIR_GRAFICAS.parent))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("No se pudo abrir", str(exc))

    # ------------------------------------------------------------------
    # Ejecución asíncrona
    # ------------------------------------------------------------------
    def _preparar_ejecucion(self) -> tuple[Escenario, dict] | None:
        errores_config = self.panel_config.aplicar_a_escenario()
        if errores_config:
            messagebox.showerror(
                "Configuración inválida", "\n".join(errores_config)
            )
            return None
        errores = self.escenario.validar()
        if errores:
            messagebox.showerror(
                "Escenario inválido",
                "Corrija el escenario:\n\n- " + "\n- ".join(errores),
            )
            return None
        factibilidad = validar_factibilidad(self.escenario)
        if not factibilidad.get("hay_solucion"):
            detalle = "\n".join(factibilidad.get("errores", []))
            messagebox.showerror(
                "Escenario no factible",
                "No existe una solución factible con los recursos actuales."
                + (f"\n\n{detalle}" if detalle else ""),
            )
            return None
        try:
            self.parametros = _combinar_parametros(
                self.panel_config.obtener_parametros()
            )
        except ValueError as exc:
            messagebox.showerror("Parámetros inválidos", str(exc))
            return None
        self.panel_config.parametros = self.parametros
        return self.escenario.clonar(), copy.deepcopy(self.parametros)

    def _iniciar_tarea(self, descripcion: str, funcion, al_completar) -> None:
        if self._tarea_activa:
            messagebox.showinfo(
                "Tarea en curso", "Espere a que termine la ejecución actual."
            )
            return
        self._tarea_activa = True
        self._set_estado(descripcion)
        self.progreso.start(12)
        for boton in self._botones:
            boton.configure(state="disabled")
        self.editor.establecer_habilitado(False)
        self.panel_config.establecer_habilitado(False)

        def trabajador() -> None:
            try:
                resultado = funcion()
            except Exception:
                self._cola.put(("error", None, traceback.format_exc()))
            else:
                self._cola.put(("ok", al_completar, resultado))

        threading.Thread(target=trabajador, daemon=True).start()
        self._programar_poll()

    def _programar_poll(self) -> None:
        self._after_poll = self.after(120, self._revisar_cola)

    def _revisar_cola(self) -> None:
        self._after_poll = None
        try:
            tipo, callback, carga = self._cola.get_nowait()
        except queue.Empty:
            if self._tarea_activa:
                self._programar_poll()
            return

        self._tarea_activa = False
        self.progreso.stop()
        for boton in self._botones:
            boton.configure(state="normal")
        self.editor.establecer_habilitado(True)
        self.panel_config.establecer_habilitado(True)

        if tipo == "error":
            detalle = str(carga).strip().splitlines()
            corto = detalle[-1] if detalle else "Error desconocido."
            print(carga, file=sys.stderr)
            messagebox.showerror(
                "Error durante la ejecución",
                f"{corto}\n\nRevise la consola para el detalle completo.",
            )
            self._set_estado("La ejecución falló.")
            return
        try:
            callback(carga)
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "Error al mostrar resultados",
                "La ejecución terminó, pero no se pudieron mostrar los resultados.",
            )
            self._set_estado("Error al mostrar resultados.")

    # ------------------------------------------------------------------
    # Algoritmos y experimentos
    # ------------------------------------------------------------------
    def _ejecutar(self) -> None:
        if self._tarea_activa:
            return
        preparado = self._preparar_ejecucion()
        if preparado is None:
            return
        escenario, parametros = preparado
        experimentos = parametros["experimentos"]
        repeticiones = int(experimentos["repeticiones_metaheuristicas"])
        inicios = int(experimentos["num_inicios_hill"])
        profundidades = list(experimentos["profundidades_adversarias"])
        self._iniciar_tarea(
            "Ejecutando todos los módulos (heurísticas, Hill Climbing, "
            "metaheurísticas, juego, adversaria y planificación)...",
            lambda: ejecutar_todo(
                escenario,
                parametros=parametros,
                repeticiones=repeticiones,
                num_inicios=inicios,
                profundidades=profundidades,
                generar_graficas=True,
                guardar=True,
            ),
            self._mostrar_experimento,
        )

    def _mostrar_experimento(self, datos: dict) -> None:
        self.resultados_actuales = datos["resultados"]
        self.juego_actual = datos["juego"]
        self.adversaria_actual = datos["adversaria"]
        self.plan_actual = datos["plan"]
        archivos = datos.get("archivos", {})
        self.panel_resultados.mostrar_todo(
            self.resultados_actuales,
            juego=self.juego_actual,
            adversaria=self.adversaria_actual,
            plan=self.plan_actual,
            escenario=self.escenario,
            graficas=archivos.get("graficas", []),
        )
        self.notebook.select(self.tab_resultados)
        errores = datos.get("errores", [])
        self._set_estado(
            f"Ejecución completada en {datos.get('tiempo_total', 0.0):.2f} s. "
            f"Resultados: {archivos.get('resultados_completos')} | "
            f"Plan: {archivos.get('planificacion')} | "
            f"Gráficas: {len(archivos.get('graficas', []))}."
            + (f" Errores parciales: {len(errores)}." if errores else "")
        )
        if errores:
            messagebox.showwarning(
                "Ejecución parcial",
                "Algunos módulos fallaron; se conservaron los resultados válidos:\n\n- "
                + "\n- ".join(errores),
            )

    # ------------------------------------------------------------------
    # Ayuda y cierre
    # ------------------------------------------------------------------
    def _guia(self) -> None:
        messagebox.showinfo(
            "Guía rápida",
            "1. Edite la cuadrícula: elija una herramienta y haga clic. Las "
            "herramientas de entrega y obstáculo añaden o quitan según el estado "
            "de la celda; el doble clic edita costos o entregas.\n"
            "2. Ajuste recursos, competidor, algoritmos y experimentos en la "
            "configuración situada bajo la cuadrícula y pulse 'Aplicar al escenario'.\n"
            "3. Pulse 'Ejecutar todos los módulos' para correr heurísticas, "
            "búsqueda local, metaheurísticas, juego estratégico, búsqueda "
            "adversaria y planificación final.\n"
            "4. Revise Resumen, Ejecuciones, Rutas, Gráficas, Acciones, Juego, "
            "Adversaria y Plan final.\n"
            "5. Guarde el escenario; si ya tiene ruta asociada se sobrescribe sin "
            "pedir confirmación.",
        )

    def _acerca_de(self) -> None:
        messagebox.showinfo(
            "Acerca de SIPOTDA",
            "SIPOTDA: sistema de optimización logística con Greedy/A*, "
            "Hill Climbing, recocido simulado, algoritmo genético, teoría de "
            "juegos y Minimax/alfa-beta.\n\nImplementación en Python con Tkinter, "
            "sin bibliotecas de optimización externas.",
        )

    def _cerrar(self) -> None:
        if self._tarea_activa:
            if not messagebox.askyesno(
                "Tarea en curso",
                "Hay una ejecución en curso. ¿Cerrar de todos modos?",
            ):
                return
        if not self._confirmar_descarte():
            return
        if self._after_poll is not None:
            try:
                self.after_cancel(self._after_poll)
            except tk.TclError:
                pass
        self.destroy()
