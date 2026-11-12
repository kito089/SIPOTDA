"""Secuencia visual de acciones de la empresa y del competidor."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from algoritmos.busqueda_adversaria.modelo_adversario import (
    ACCIONES_MAX,
    ACCIONES_MIN,
    crear_configuracion,
    crear_estado_inicial,
    es_turno_max,
    transicion,
)
from algoritmos.comun import PlanificadorRutas
from algoritmos.teoria_juegos.juego_estrategico import ESTRATEGIAS_EMPRESA
from interfaz.componentes import (
    COLORES,
    escribir_texto,
    texto_solo_lectura,
)
from interfaz.visualizador import VisualizadorCuadricula
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


class PanelAcciones(ttk.Frame):
    """Explica paso a paso las consecuencias reales de cada acción estratégica."""

    def __init__(self, master) -> None:
        super().__init__(master, padding=4)
        self.escenario: Escenario | None = None
        self.juego = None
        self.adversaria: dict | None = None
        self.plan: dict | None = None
        self.resultados: list[ResultadoEjecucion] = []
        self.visualizador: VisualizadorCuadricula | None = None
        self._opciones: dict[str, tuple[str, dict]] = {}
        self._construir()

    def _construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        barra = ttk.Frame(self)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(barra, text="Secuencia:").pack(side="left")
        self.var_opcion = tk.StringVar()
        self.combo = ttk.Combobox(
            barra, textvariable=self.var_opcion, state="readonly", width=56
        )
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._mostrar_opcion())

        cuerpo = ttk.Frame(self)
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.columnconfigure(0, weight=0)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        marco_mapa = ttk.LabelFrame(cuerpo, text="Cuadrícula de acciones", padding=4)
        marco_mapa.grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.marco_mapa = marco_mapa

        marco_texto = ttk.Frame(cuerpo)
        marco_texto.grid(row=0, column=1, sticky="nsew")
        marco_texto.columnconfigure(0, weight=1)
        marco_texto.rowconfigure(0, weight=1)
        self.texto = texto_solo_lectura(marco_texto, alto=18)
        self.texto.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(marco_texto, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

    def establecer_escenario(self, escenario: Escenario | None) -> None:
        self.escenario = escenario
        for hijo in self.marco_mapa.winfo_children():
            hijo.destroy()
        self.visualizador = (
            VisualizadorCuadricula(self.marco_mapa, escenario, tamano_celda=30)
            if escenario is not None
            else None
        )
        if self.visualizador is not None:
            self.visualizador.pack(anchor="nw")
        self._opciones = {}
        self.combo.configure(values=[])
        self.var_opcion.set("")
        escribir_texto(
            self.texto,
            "Ejecute todos los módulos para ver la secuencia de acciones.",
        )

    def mostrar(
        self,
        juego=None,
        adversaria: dict | None = None,
        plan: dict | None = None,
        resultados: list[ResultadoEjecucion] | None = None,
    ) -> None:
        self.juego = juego
        self.adversaria = adversaria
        self.plan = plan
        self.resultados = list(resultados or [])
        self._opciones = {}
        if juego is not None:
            for celda in juego.matriz:
                nombre = (
                    f"Juego: {celda['empresa']} vs {celda['competidor']}"
                )
                self._opciones[nombre] = ("juego", celda)
        if adversaria is not None:
            for resultado in adversaria.get("alfa_beta", []):
                nombre = (
                    f"Adversaria: alfa-beta, profundidad {resultado.profundidad}"
                )
                self._opciones[nombre] = ("adversaria", resultado)
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
                self.visualizador.limpiar_resaltados()
            escribir_texto(self.texto, "No hay acciones para mostrar.")

    # ------------------------------------------------------------------
    def _ruta_referencia(self):
        if self.plan and self.plan.get("rutas"):
            from modelos.solucion import Solucion, Tramo

            return Solucion(
                orden_entregas=list(self.plan.get("orden_entregas", [])),
                rutas=[Tramo.desde_dict(t) for t in self.plan["rutas"]],
                costo_total=float(self.plan.get("costo_total") or 0.0),
                pasos=int(self.plan.get("pasos") or 0),
                valida=bool(self.plan.get("plan_valido", True)),
            )
        validos = [
            r
            for r in self.resultados
            if r.solucion is not None and r.solucion.valida
        ]
        if not validos:
            return None
        return min(validos, key=lambda r: r.costo).solucion

    def _dibujar_solucion(self, solucion, color: str = "#2e75b6") -> None:
        if self.visualizador is None:
            return
        if solucion is None:
            self.visualizador.limpiar_rutas()
            return
        rutas = [
            (
                f"{tramo.origen_nombre} -> {tramo.destino_nombre}",
                color,
                tramo.camino,
            )
            for tramo in solucion.rutas
        ]
        self.visualizador.mostrar_rutas(rutas)

    def _dibujar_ruta_referencia(self, color: str = "#2e75b6") -> None:
        self._dibujar_solucion(self._ruta_referencia(), color)

    def _mostrar_opcion(self) -> None:
        datos = self._opciones.get(self.var_opcion.get())
        if datos is None:
            return
        tipo, carga = datos
        if tipo == "juego":
            self._mostrar_juego(carga)
        else:
            self._mostrar_adversaria(carga)

    def _mostrar_juego(self, celda: dict) -> None:
        if self.visualizador is None:
            return
        self.visualizador.limpiar_resaltados()
        detalle = celda.get("detalle", {})
        evitar = {tuple(p) for p in detalle.get("evitar", [])}
        resaltados = {
            (fila, columna): ("#c00000", "BLOQUEO") for fila, columna in evitar
        }
        self.visualizador.establecer_resaltados(resaltados)
        solucion_ruta = None
        config = ESTRATEGIAS_EMPRESA.get(celda.get("empresa", ""))
        try:
            if config is not None and self.escenario is not None:
                planificador = PlanificadorRutas(
                    self.escenario,
                    evitar=evitar,
                    factor_costo=config["factor_costo"],
                    modo=config["modo_ruta"],
                )
                solucion_ruta = planificador.evaluar(
                    detalle.get("orden_entregas", []),
                    f"Juego:{celda.get('empresa', '')}",
                )
        except (ValueError, KeyError, IndexError):
            solucion_ruta = None
        self._dibujar_solucion(
            solucion_ruta if solucion_ruta is not None else self._ruta_referencia(),
            COLORES["ruta2"],
        )
        lineas = [
            "SECUENCIA DE ACCIONES DEL JUEGO ESTRATÉGICO",
            "",
            f"1. La empresa elige '{celda['empresa']}': "
            f"{detalle.get('descripcion_empresa', 'n/d')}",
            f"   Modo de ruta: {detalle.get('modo_ruta', 'n/d')}; "
            f"orden de entregas: {detalle.get('orden_entregas', 'n/d')}.",
            "",
            f"2. El competidor responde '{celda['competidor']}': "
            f"{detalle.get('descripcion_competidor', 'n/d')}",
            f"   Factor de costo aplicado: "
            f"{_fmt(detalle.get('factor_costo_competidor'), 4)}; "
            f"factor de presupuesto: "
            f"{_fmt(detalle.get('factor_presupuesto_competidor'), 4)}.",
            "",
            "3. Celdas bloqueadas o evitadas: "
            + (", ".join(f"({f}, {c})" for f, c in sorted(evitar)) or "ninguna."),
            "",
            "4. Consecuencias reales calculadas:",
            f"   Costo de ruta: {_fmt(detalle.get('costo_ruta'))}",
            f"   Costo efectivo con competidor: {_fmt(detalle.get('costo_efectivo'))}",
            f"   Combustible efectivo: {_fmt(detalle.get('combustible_efectivo'))}",
            f"   Tiempo efectivo: {_fmt(detalle.get('tiempo_efectivo'))}",
            f"   Riesgo: {_fmt(detalle.get('riesgo'), 4)}",
            f"   Penalización: {_fmt(detalle.get('penalizacion'))}",
            f"   Pago empresa: {_fmt(celda.get('pago_empresa'))}",
            f"   Pago competidor: {_fmt(celda.get('pago_competidor'))}",
            f"   Solución válida: "
            f"{'sí' if detalle.get('solucion_valida') else 'no'}",
        ]
        if detalle.get("violaciones"):
            lineas.append(
                "   Violaciones: " + "; ".join(detalle["violaciones"])
            )
        escribir_texto(self.texto, "\n".join(lineas))

    def _mostrar_adversaria(self, resultado) -> None:
        if self.visualizador is None or self.escenario is None:
            return
        self.visualizador.limpiar_resaltados()
        self._dibujar_ruta_referencia(COLORES["ruta4"])
        bloqueadas = self.escenario.celdas_bloqueadas_competidor()
        self.visualizador.establecer_resaltados(
            {(f, c): ("#c00000", "BLOQUEO") for f, c in bloqueadas}
        )
        lineas = [
            "SECUENCIA DE ACCIONES DE LA BÚSQUEDA ADVERSARIA",
            "",
            f"Algoritmo: {resultado.algoritmo}; profundidad: "
            f"{resultado.profundidad}; valor minimax: "
            f"{_fmt(resultado.valor_minimax)}.",
            "",
            "Turnos reales de la línea principal:",
        ]
        try:
            config = crear_configuracion(self.escenario, resultado.profundidad)
            estado = crear_estado_inicial(config)
            for indice, accion in enumerate(resultado.linea_principal, start=1):
                actor = "MAX (empresa)" if es_turno_max(estado) else "MIN (competidor)"
                antes = estado
                estado = transicion(config, estado, accion)
                if accion in ACCIONES_MIN:
                    descripcion = ACCIONES_MIN[accion]["descripcion"]
                else:
                    descripcion = ACCIONES_MAX.get(
                        accion, {"descripcion": "Acción de la empresa."}
                    )["descripcion"]
                lineas.append(
                    f"  {indice}. {actor}: {accion} - {descripcion}"
                )
                lineas.append(
                    f"     Presupuesto {_fmt(antes.presupuesto)} -> "
                    f"{_fmt(estado.presupuesto)}; combustible "
                    f"{_fmt(antes.combustible)} -> {_fmt(estado.combustible)}; "
                    f"reservas {antes.reservas} -> {estado.reservas}; "
                    f"bloqueos {antes.bloqueos} -> {estado.bloqueos}; "
                    f"riesgo {_fmt(antes.riesgo, 4)} -> {_fmt(estado.riesgo, 4)}; "
                    f"impacto {_fmt(antes.impacto, 4)} -> {_fmt(estado.impacto, 4)}."
                )
            final = estado
        except (ValueError, KeyError) as exc:
            lineas.append(f"  No se pudo reconstruir la secuencia: {exc}")
            final = None
        if final is not None:
            lineas.extend(
                [
                    "",
                    "Estado final real de la línea principal:",
                    f"  Presupuesto: {_fmt(final.presupuesto)}",
                    f"  Combustible: {_fmt(final.combustible)}",
                    f"  Reservas: {final.reservas}; bloqueos: {final.bloqueos}",
                    f"  Riesgo: {_fmt(final.riesgo, 4)}; "
                    f"impacto: {_fmt(final.impacto, 4)}",
                    f"  Acción recomendada para la empresa: "
                    f"{resultado.mejor_accion or 'n/d'}",
                ]
            )
        escribir_texto(self.texto, "\n".join(lineas))
