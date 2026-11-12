"""Editor interactivo de escenarios sobre la cuadrícula."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

from gestion_archivos.validar_escenario import validar_factibilidad
from interfaz.componentes import COLORES, escribir_texto, texto_solo_lectura
from interfaz.visualizador import VisualizadorCuadricula
from modelos.escenario import Escenario


MODOS = {
    "seleccionar": "Seleccionar / mover elementos",
    "inicio": "Colocar inicio",
    "destino": "Colocar destino",
    "entrega": "Añadir / Quitar entrega",
    "obstaculo": "Añadir / Quitar obstáculo",
}


class EditorEscenario(ttk.Frame):
    """Cuadrícula interactiva con edición de escenario y costos."""

    def __init__(
        self,
        master,
        escenario: Escenario,
        al_cambiar: Callable[[], None] | None = None,
        al_estado: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=6)
        self.escenario = escenario
        self.al_cambiar = al_cambiar
        self.al_estado = al_estado
        self.modo = tk.StringVar(value="seleccionar")
        self.seleccion: tuple[int, int] | None = None
        self._arrastre: tuple[str, int | None, tuple[int, int]] | None = None
        self._presionada: tuple[int, int] | None = None
        self._habilitado = True
        self._construir()
        self._refrescar_info()
        self._redibujar()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        marco_herramientas = ttk.LabelFrame(
            self, text="Herramientas de edición", padding=6
        )
        marco_herramientas.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        fila_modos = ttk.Frame(marco_herramientas)
        fila_modos.pack(fill="x")
        for clave, texto in MODOS.items():
            ttk.Radiobutton(
                fila_modos,
                text=texto,
                value=clave,
                variable=self.modo,
                command=self._cambiar_modo,
            ).pack(side="left", padx=(0, 12), pady=1)

        fila_acciones = ttk.Frame(marco_herramientas)
        fila_acciones.pack(fill="x", pady=(6, 0))
        ttk.Label(
            fila_acciones,
            text="Doble clic: editar costo o entrega.",
        ).pack(side="left")
        ttk.Button(
            fila_acciones, text="Validar factibilidad", command=self.validar_completa
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            fila_acciones, text="Validar estructura", command=self.validar_estructura
        ).pack(side="right")

        marco_cuadricula = ttk.LabelFrame(self, text="Cuadrícula logística", padding=4)
        marco_cuadricula.grid(row=1, column=0, sticky="nsew")
        marco_cuadricula.columnconfigure(1, weight=1)
        self.visualizador = VisualizadorCuadricula(
            marco_cuadricula, self.escenario, tamano_celda=38
        )
        self.visualizador.grid(row=0, column=0, sticky="nw")
        self.visualizador.bind("<ButtonPress-1>", self._presionar)
        self.visualizador.bind("<B1-Motion>", self._mover)
        self.visualizador.bind("<ButtonRelease-1>", self._soltar)
        self.visualizador.bind("<Double-Button-1>", self._doble_clic)
        self.visualizador.bind("<Motion>", self._mover_raton)

        self.var_coord = tk.StringVar(value="Celda: -")
        ttk.Label(marco_cuadricula, textvariable=self.var_coord).grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        panel = ttk.Frame(marco_cuadricula)
        panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(12, 0))
        ttk.Label(panel, text="Información", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.info = texto_solo_lectura(panel, alto=14)
        self.info.pack(fill="both", expand=True, pady=2)

        leyenda = ttk.LabelFrame(panel, text="Leyenda", padding=4)
        leyenda.pack(fill="x", pady=(6, 0))
        for texto, color in (
            ("Inicio (S)", COLORES["inicio"]),
            ("Destino (G)", COLORES["destino"]),
            ("Entrega (E)", COLORES["entrega"]),
            ("Obstáculo (#)", COLORES["obstaculo"]),
        ):
            fila = ttk.Frame(leyenda)
            fila.pack(anchor="w", fill="x")
            tk.Label(fila, text="  ", background=color, width=3, relief="solid", borderwidth=1).pack(
                side="left", padx=(0, 4)
            )
            ttk.Label(fila, text=texto).pack(side="left")
        ttk.Label(
            leyenda,
            text="Arrastre los elementos en modo Seleccionar.",
            wraplength=230,
        ).pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------------
    # Estado y dibujo
    # ------------------------------------------------------------------
    def establecer_escenario(self, escenario: Escenario) -> None:
        self.escenario = escenario
        self.seleccion = None
        self._arrastre = None
        self.visualizador.establecer_escenario(escenario)
        self._refrescar_info()
        self._redibujar()

    def obtener_escenario(self) -> Escenario:
        return self.escenario

    def establecer_habilitado(self, habilitado: bool) -> None:
        """Bloquea la edición mientras se ejecuta una tarea."""
        self._habilitado = bool(habilitado)
        estado = "normal" if habilitado else "disabled"
        self._aplicar_estado(self, estado)

    def _aplicar_estado(self, widget, estado: str) -> None:
        for hijo in widget.winfo_children():
            if isinstance(
                hijo,
                (
                    ttk.Button,
                    ttk.Radiobutton,
                    ttk.Checkbutton,
                    ttk.Entry,
                    ttk.Combobox,
                ),
            ):
                try:
                    hijo.configure(state=estado)
                except tk.TclError:
                    pass
            self._aplicar_estado(hijo, estado)

    def mostrar_rutas(self, rutas) -> None:
        self.visualizador.mostrar_rutas(rutas)

    def limpiar_rutas(self) -> None:
        self.visualizador.limpiar_rutas()

    def _redibujar(self) -> None:
        self.visualizador.seleccion = self.seleccion
        self.visualizador.redibujar()

    def _refrescar_info(self) -> None:
        e = self.escenario
        demanda = sum(x.demanda for x in e.entregas)
        lineas = [
            e.resumen(),
            f"Demanda total: {demanda:g}",
            f"Capacidad: {e.limite_recurso('capacidad'):g}",
            f"Combustible: {e.limite_recurso('combustible'):g}",
            f"Tiempo: {e.limite_recurso('tiempo'):g}",
            f"Presupuesto: {e.limite_recurso('presupuesto'):g}",
            f"Movimiento diagonal: {'sí' if e.permitir_diagonal else 'no'}",
            f"Competidor: {e.competidor.get('nombre', 'n/d')}",
            "",
        ]
        errores = e.validar()
        if errores:
            lineas.append("ERRORES ESTRUCTURALES:")
            lineas.extend(f"- {error}" for error in errores)
        else:
            lineas.append("Estructura válida. Use 'Validar factibilidad' para probar recursos.")
        escribir_texto(self.info, "\n".join(lineas))

    def _notificar_cambio(self) -> None:
        self._refrescar_info()
        self._redibujar()
        if self.al_cambiar:
            self.al_cambiar()

    def _estado(self, mensaje: str) -> None:
        if self.al_estado:
            self.al_estado(mensaje)

    def _cambiar_modo(self) -> None:
        self._estado(f"Modo: {MODOS.get(self.modo.get(), self.modo.get())}")

    # ------------------------------------------------------------------
    # Eventos del ratón
    # ------------------------------------------------------------------
    def _mover_raton(self, evento) -> None:
        celda = self.visualizador.celda_desde_evento(evento)
        self.var_coord.set(f"Celda: {celda}" if celda else "Celda: -")

    def _presionar(self, evento) -> None:
        if not self._habilitado:
            return
        celda = self.visualizador.celda_desde_evento(evento)
        if celda is None:
            return
        modo = self.modo.get()
        self._presionada = celda
        self.seleccion = celda
        self._redibujar()

        if modo == "inicio":
            self._mover_inicio(*celda)
            return
        if modo == "destino":
            self._mover_destino(*celda)
            return
        if modo == "entrega":
            self._alternar_entrega(*celda)
            return
        if modo == "obstaculo":
            self._alternar_obstaculo(*celda)
            return

        tipo, id_elemento = self._elemento_en(*celda)
        if tipo != "vacio":
            self._arrastre = (tipo, id_elemento, celda)
        else:
            self._arrastre = None
        self._redibujar()

    def _mover(self, evento) -> None:
        celda = self.visualizador.celda_desde_evento(evento)
        if celda:
            self.var_coord.set(f"Celda: {celda}")

    def _soltar(self, evento) -> None:
        if not self._habilitado:
            return
        if self.modo.get() != "seleccionar":
            self._arrastre = None
            return
        if not self._arrastre:
            return
        destino = self.visualizador.celda_desde_evento(evento)
        tipo, id_elemento, origen = self._arrastre
        self._arrastre = None
        if destino is None or destino == origen:
            return
        try:
            if tipo == "inicio":
                self.escenario.mover_inicio(*destino)
            elif tipo == "destino":
                self.escenario.mover_destino(*destino)
            elif tipo == "entrega" and id_elemento is not None:
                self.escenario.mover_entrega(id_elemento, *destino)
            elif tipo == "obstaculo":
                self._mover_obstaculo(origen, destino)
            else:
                return
        except (ValueError, IndexError) as exc:
            self._estado(f"Movimiento inválido: {exc}")
            messagebox.showwarning("Movimiento inválido", str(exc))
            self.seleccion = origen
            self._redibujar()
            return
        self.seleccion = destino
        self._estado(f"Elemento movido a {destino}.")
        self._notificar_cambio()

    def _doble_clic(self, evento) -> None:
        if not self._habilitado:
            return
        celda = self.visualizador.celda_desde_evento(evento)
        if celda is None:
            return
        tipo, id_elemento = self._elemento_en(*celda)
        if tipo == "entrega" and id_elemento is not None:
            self._editar_entrega(id_elemento)
        elif tipo in {"inicio", "destino", "vacio"}:
            self._editar_costo(celda)
        elif tipo == "obstaculo":
            self._estado("Un obstáculo no tiene costo operativo editable; quite el obstáculo primero.")

    # ------------------------------------------------------------------
    # Acciones de edición
    # ------------------------------------------------------------------
    def _elemento_en(self, fila: int, columna: int) -> tuple[str, int | None]:
        if (fila, columna) == self.escenario.inicio:
            return "inicio", None
        if (fila, columna) == self.escenario.destino:
            return "destino", None
        for entrega in self.escenario.entregas:
            if entrega.posicion == (fila, columna):
                return "entrega", entrega.id
        if (fila, columna) in self.escenario.obstaculos:
            return "obstaculo", None
        return "vacio", None

    def _mover_inicio(self, fila: int, columna: int) -> None:
        try:
            self.escenario.mover_inicio(fila, columna)
        except (ValueError, IndexError) as exc:
            self._estado(str(exc))
            messagebox.showwarning("Posición inválida", str(exc))
            return
        self._notificar_cambio()

    def _mover_destino(self, fila: int, columna: int) -> None:
        try:
            self.escenario.mover_destino(fila, columna)
        except (ValueError, IndexError) as exc:
            self._estado(str(exc))
            messagebox.showwarning("Posición inválida", str(exc))
            return
        self._notificar_cambio()

    def _alternar_entrega(self, fila: int, columna: int) -> None:
        tipo, id_elemento = self._elemento_en(fila, columna)
        if tipo == "entrega" and id_elemento is not None:
            entrega = self.escenario.obtener_entrega(id_elemento)
            self.escenario.eliminar_entrega(id_elemento)
            nombre = entrega.nombre if entrega else id_elemento
            self._estado(f"Entrega {nombre} eliminada de ({fila}, {columna}).")
            if self.seleccion == (fila, columna):
                self.seleccion = None
            self._notificar_cambio()
            return
        if tipo != "vacio":
            self._estado("No se puede añadir una entrega sobre otro elemento.")
            return
        self._agregar_entrega(fila, columna)

    def _agregar_entrega(self, fila: int, columna: int) -> None:
        demanda = simpledialog.askfloat(
            "Nueva entrega",
            f"Demanda de la entrega en ({fila}, {columna}):",
            initialvalue=4.0,
            minvalue=0.0,
            parent=self,
        )
        if demanda is None:
            return
        try:
            self.escenario.agregar_entrega(fila, columna, demanda=demanda)
        except (ValueError, IndexError) as exc:
            self._estado(str(exc))
            messagebox.showwarning("Entrega inválida", str(exc))
            return
        self._estado(f"Entrega añadida en ({fila}, {columna}).")
        self._notificar_cambio()

    def _alternar_obstaculo(self, fila: int, columna: int) -> None:
        try:
            if (fila, columna) in self.escenario.obstaculos:
                self.escenario.quitar_obstaculo(fila, columna)
                self._estado(f"Obstáculo retirado de ({fila}, {columna}).")
            else:
                self.escenario.agregar_obstaculo(fila, columna)
                self._estado(f"Obstáculo añadido en ({fila}, {columna}).")
        except (ValueError, IndexError) as exc:
            self._estado(str(exc))
            messagebox.showwarning("Obstáculo inválido", str(exc))
            return
        self._notificar_cambio()

    def _mover_obstaculo(
        self, origen: tuple[int, int], destino: tuple[int, int]
    ) -> None:
        if destino in self.escenario.posiciones_ocupadas():
            raise ValueError("La celda destino está ocupada por un elemento.")
        if destino in self.escenario.obstaculos:
            raise ValueError("La celda destino ya contiene un obstáculo.")
        self.escenario.quitar_obstaculo(*origen)
        try:
            self.escenario.agregar_obstaculo(*destino)
        except Exception:
            self.escenario.agregar_obstaculo(*origen)
            raise

    def _editar_costo(self, celda: tuple[int, int]) -> None:
        fila, columna = celda
        if not self.escenario.es_transitable(fila, columna):
            messagebox.showwarning(
                "Celda no transitable",
                "Quite el obstáculo antes de editar el costo de esta celda.",
            )
            return
        actual = self.escenario.obtener_costo(fila, columna)
        nuevo = simpledialog.askfloat(
            "Editar costo",
            f"Nuevo costo para ({fila}, {columna}):",
            initialvalue=actual,
            minvalue=0.001,
            parent=self,
        )
        if nuevo is None:
            return
        try:
            self.escenario.establecer_costo(fila, columna, nuevo)
        except (ValueError, IndexError) as exc:
            messagebox.showwarning("Costo inválido", str(exc))
            return
        self._estado(f"Costo de ({fila}, {columna}) actualizado a {nuevo:g}.")
        self._notificar_cambio()

    def _editar_entrega(self, id_entrega: int) -> None:
        entrega = self.escenario.obtener_entrega(id_entrega)
        if entrega is None:
            return
        nombre = simpledialog.askstring(
            "Editar entrega",
            "Nombre de la entrega:",
            initialvalue=entrega.nombre,
            parent=self,
        )
        if nombre is None:
            return
        demanda = simpledialog.askfloat(
            "Editar entrega",
            "Demanda (unidades):",
            initialvalue=entrega.demanda,
            minvalue=0.0,
            parent=self,
        )
        if demanda is None:
            return
        entrega.nombre = nombre.strip() or entrega.nombre
        entrega.demanda = demanda
        self._estado(f"Entrega {entrega.nombre} actualizada.")
        self._notificar_cambio()

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------
    def validar_estructura(self) -> list[str]:
        errores = self.escenario.validar()
        if errores:
            mensaje = "Se encontraron errores:\n\n- " + "\n- ".join(errores)
            messagebox.showerror("Escenario inválido", mensaje)
        else:
            messagebox.showinfo("Validación", "La estructura del escenario es válida.")
        self._refrescar_info()
        return errores

    def validar_completa(self) -> dict:
        self._estado("Validando factibilidad...")
        resultado = validar_factibilidad(self.escenario)
        lineas = [
            f"Válido: {'sí' if resultado['valido'] else 'no'}",
            f"Hay solución factible: {'sí' if resultado['hay_solucion'] else 'no'}",
            f"Método: {resultado['metodo']}",
            f"Órdenes evaluadas: {resultado['evaluadas']}",
        ]
        if resultado["mejor_costo"] is not None:
            lineas.append(f"Mejor costo encontrado: {resultado['mejor_costo']:.2f}")
            lineas.append(f"Mejor orden: {resultado['mejor_orden']}")
        if resultado["errores"]:
            lineas.append("\nErrores:")
            lineas.extend(f"- {error}" for error in resultado["errores"])
        if resultado["advertencias"]:
            lineas.append("\nAdvertencias:")
            lineas.extend(f"- {aviso}" for aviso in resultado["advertencias"])
        texto = "\n".join(lineas)
        escribir_texto(self.info, texto)
        self._estado("Validación de factibilidad completada.")
        if resultado["hay_solucion"] and not resultado["errores"]:
            messagebox.showinfo("Factibilidad", texto)
        else:
            messagebox.showwarning("Factibilidad", texto)
        return resultado
