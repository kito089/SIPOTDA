"""Teoría de juegos aplicada a la distribución logística.

Jugadores
---------
- Empresa de distribución: maximiza su beneficio.
- Competidor: maximiza su propio margen/captura de mercado.

Los pagos no se inventan: se calculan a partir del escenario y de rutas reales
obtenidas con A*.  Fórmulas utilizadas (documentadas también en el README):

Ingreso base = sum(demanda_i * tarifa_i)

Para cada par (estrategia de empresa, estrategia de competidor):

    costo_ruta        = costo monetario de la ruta planificada
    costo_efectivo    = costo_ruta * factor_costo_empresa * factor_costo_competidor
                        * factor_presupuesto_competidor
    uso_combustible   = consumo_base * factor_combustible_empresa * factor_combustible_competidor
    penalización      = 120 * riesgo + excesos de recursos
    pago_empresa      = ingreso - costo_efectivo - penalización

    margen_competidor = 0.22 * ingreso
    captura           = 0.45 * (costo_efectivo - costo_base)
    bono_bloqueo      = 90 si el competidor bloquea una ruta efectivamente
    castigo           = 25 si el competidor adopta una acción agresiva
    pago_competidor   = margen_competidor + captura + bono_bloqueo - castigo

Las estrategias de la empresa modifican el criterio de ruta (costo, pasos o
evitando bloqueos), el consumo y el riesgo.  Las del competidor modifican
costos, disponibilidad o rutas.  Así, la matriz refleja consecuencias
logísticas verificables del escenario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from algoritmos.comun import PlanificadorRutas, construir_solucion, costo_camino, orden_vecino_mas_cercano
from modelos.escenario import Escenario


@dataclass
class JuegoEstrategico:
    """Resultado completo del análisis estratégico."""

    escenario_id: str
    nombre_escenario: str
    estrategias_empresa: list[str]
    estrategias_competidor: list[str]
    matriz: list[dict[str, Any]]
    analisis: dict[str, Any]
    recomendacion: dict[str, Any]
    metricas: dict[str, Any] = field(default_factory=dict)

    def pago(self, empresa: str, competidor: str) -> tuple[float, float]:
        for celda in self.matriz:
            if celda["empresa"] == empresa and celda["competidor"] == competidor:
                return celda["pago_empresa"], celda["pago_competidor"]
        raise KeyError((empresa, competidor))

    def a_dict(self) -> dict:
        return {
            "escenario_id": self.escenario_id,
            "nombre_escenario": self.nombre_escenario,
            "estrategias_empresa": list(self.estrategias_empresa),
            "estrategias_competidor": list(self.estrategias_competidor),
            "matriz": self.matriz,
            "analisis": self.analisis,
            "recomendacion": self.recomendacion,
            "metricas": self.metricas,
        }

    def resumen_texto(self) -> str:
        lineas = ["MATRIZ DE PAGOS (empresa, competidor)"]
        encabezado = "Estrategia empresa".ljust(24) + "".join(
            c[:18].ljust(20) for c in self.estrategias_competidor
        )
        lineas.append(encabezado)
        for empresa in self.estrategias_empresa:
            fila = empresa[:22].ljust(24)
            for competidor in self.estrategias_competidor:
                pe, pc = self.pago(empresa, competidor)
                fila += f"({pe:7.1f},{pc:7.1f})".ljust(20)
            lineas.append(fila)
        lineas.append("")
        lineas.append("Mejores respuestas de la empresa:")
        for comp, respuestas in self.analisis["mejores_respuestas_empresa"].items():
            lineas.append(f"  Si compite con {comp}: {', '.join(respuestas)}")
        lineas.append("Mejores respuestas del competidor:")
        for emp, respuestas in self.analisis["mejores_respuestas_competidor"].items():
            lineas.append(f"  Si la empresa elige {emp}: {', '.join(respuestas)}")
        lineas.append(
            "Estrategias estrictamente dominantes (empresa): "
            + (", ".join(self.analisis["dominantes_empresa"]) or "ninguna")
        )
        lineas.append(
            "Estrategias estrictamente dominadas (empresa): "
            + (", ".join(self.analisis["dominadas_empresa"]) or "ninguna")
        )
        nash = self.analisis["equilibrios_nash"]
        lineas.append(
            "Equilibrios de Nash puros: "
            + (
                ", ".join(f"({e}, {c})" for e, c in nash)
                if nash
                else "no existen en estrategias puras"
            )
        )
        lineas.append("")
        linea_rec = self.recomendacion
        lineas.append(
            f"Recomendación: {linea_rec['estrategia_empresa']} "
            f"(asumiendo {linea_rec['estrategia_competidor']}); "
            f"pago esperado={linea_rec['pago_empresa']:.2f}. {linea_rec['motivo']}"
        )
        return "\n".join(lineas)


ESTRATEGIAS_EMPRESA = {
    "ahorro_recursos": {
        "descripcion": "Prioriza bajo consumo y costo controlado.",
        "modo_ruta": "costo",
        "factor_costo": 1.0,
        "factor_combustible": 0.85,
        "factor_tiempo": 1.10,
        "riesgo": 0.18,
        "evitar_bloqueos": False,
    },
    "ruta_rapida": {
        "descripcion": "Minimiza el número de pasos; asume mayor gasto energético.",
        "modo_ruta": "pasos",
        "factor_costo": 1.15,
        "factor_combustible": 1.10,
        "factor_tiempo": 0.85,
        "riesgo": 0.12,
        "evitar_bloqueos": False,
    },
    "ruta_alternativa": {
        "descripcion": "Evita celdas bloqueadas por el competidor y reduce riesgo.",
        "modo_ruta": "costo",
        "factor_costo": 1.05,
        "factor_combustible": 1.0,
        "factor_tiempo": 1.05,
        "riesgo": 0.05,
        "evitar_bloqueos": True,
    },
}

ESTRATEGIAS_COMPETIDOR = {
    "mantener_disponibilidad": {
        "descripcion": "No altera costos ni rutas.",
        "factor_costo": 1.0,
        "factor_combustible": 1.0,
        "riesgo": 0.0,
        "agresiva": False,
        "bloquea": False,
    },
    "encarecer_combustible": {
        "descripcion": "Incrementa el costo del combustible y del presupuesto.",
        "factor_costo": None,  # Se toma del escenario.
        "factor_combustible": None,
        "riesgo": 0.06,
        "agresiva": True,
        "bloquea": False,
    },
    "bloquear_ruta": {
        "descripcion": "Reserva/ocupa celdas compartidas para forzar un desvío.",
        "factor_costo": 1.08,
        "factor_combustible": 1.0,
        "riesgo": 0.10,
        "agresiva": True,
        "bloquea": True,
    },
}


def _planificar_empresa(
    escenario: Escenario,
    estrategia: str,
    evitar: set[tuple[int, int]],
) -> tuple[Any, dict]:
    """Planifica la ruta de una estrategia empresarial y calcula su costo real."""
    config = ESTRATEGIAS_EMPRESA[estrategia]
    orden = orden_vecino_mas_cercano(escenario)
    planificador = PlanificadorRutas(
        escenario,
        evitar=evitar,
        factor_costo=config["factor_costo"],
        modo=config["modo_ruta"],
    )
    solucion = planificador.evaluar(orden, f"Juego:{estrategia}")
    if config["modo_ruta"] == "pasos":
        # La búsqueda por pasos optimiza tiempo, pero el pago usa dinero.
        tramos = []
        for tramo in solucion.rutas:
            tramo = tramo.__class__(
                origen_nombre=tramo.origen_nombre,
                destino_nombre=tramo.destino_nombre,
                origen=tramo.origen,
                destino=tramo.destino,
                camino=list(tramo.camino),
                costo=costo_camino(escenario, tramo.camino),
                pasos=tramo.pasos,
                algoritmo=tramo.algoritmo,
            )
            tramos.append(tramo)
        solucion = construir_solucion(escenario, orden, tramos, f"Juego:{estrategia}")
    return solucion, {
        "orden": orden,
        "modo_ruta": config["modo_ruta"],
        "evitar": sorted(evitar),
        **planificador.metricas_cache(),
    }


def _evaluar_celda(
    escenario: Escenario,
    empresa: str,
    competidor: str,
    costo_base: float,
    ingreso: float,
) -> dict:
    config_e = ESTRATEGIAS_EMPRESA[empresa]
    config_c = ESTRATEGIAS_COMPETIDOR[competidor]
    bloqueadas = escenario.celdas_bloqueadas_competidor()
    evitar = set()
    if config_e["evitar_bloqueos"]:
        evitar |= bloqueadas
    if config_c["bloquea"]:
        evitar |= bloqueadas
        # Si el escenario no define celdas concretas, se simula un desvío.
        if not bloqueadas:
            evitar = set()
    solucion, info_ruta = _planificar_empresa(escenario, empresa, evitar)

    factor_costo_competidor = (
        float(escenario.competidor.get("factor_costo", 1.0))
        if config_c["factor_costo"] is None
        else float(config_c["factor_costo"])
    )
    factor_comb_competidor = (
        float(escenario.competidor.get("factor_costo", 1.0))
        if config_c["factor_combustible"] is None
        else float(config_c["factor_combustible"])
    )
    factor_presupuesto_competidor = float(
        escenario.competidor.get("factor_presupuesto", 1.0)
    )
    factor_costo = config_e["factor_costo"] * factor_costo_competidor
    costo_efectivo = (
        solucion.costo_total * factor_costo * factor_presupuesto_competidor
    )

    combustible_base = solucion.combustible_consumido
    combustible_efectivo = (
        combustible_base
        * config_e["factor_combustible"]
        * factor_comb_competidor
    )
    tiempo_efectivo = solucion.tiempo_consumido * config_e["factor_tiempo"]
    limite_combustible = escenario.limite_recurso("combustible", math.inf)
    limite_tiempo = escenario.limite_recurso("tiempo", math.inf)
    limite_presupuesto = escenario.limite_recurso("presupuesto", math.inf)
    riesgo = config_e["riesgo"] + config_c["riesgo"]
    excesos = (
        max(0.0, combustible_efectivo - limite_combustible) * 5.0
        + max(0.0, tiempo_efectivo - limite_tiempo) * 5.0
        + max(0.0, costo_efectivo - limite_presupuesto) * 2.0
    )
    penalizacion = 120.0 * riesgo + excesos
    if not solucion.valida:
        penalizacion += 500.0 + 100.0 * len(solucion.violaciones)
    pago_empresa = ingreso - costo_efectivo - penalizacion

    margen_competidor = 0.22 * ingreso
    captura = 0.45 * max(0.0, costo_efectivo - costo_base)
    bono_bloqueo = 90.0 if (config_c["bloquea"] and bloqueadas) else 0.0
    castigo = 25.0 if config_c["agresiva"] else 0.0
    pago_competidor = margen_competidor + captura + bono_bloqueo - castigo

    return {
        "empresa": empresa,
        "competidor": competidor,
        "pago_empresa": round(pago_empresa, 4),
        "pago_competidor": round(pago_competidor, 4),
        "detalle": {
            "descripcion_empresa": config_e["descripcion"],
            "descripcion_competidor": config_c["descripcion"],
            "ingreso": round(ingreso, 4),
            "costo_ruta": round(solucion.costo_total, 4),
            "costo_efectivo": round(costo_efectivo, 4),
            "factor_costo_competidor": round(factor_costo_competidor, 4),
            "factor_presupuesto_competidor": round(factor_presupuesto_competidor, 4),
            "costo_base": round(costo_base, 4),
            "combustible_efectivo": round(combustible_efectivo, 4),
            "tiempo_efectivo": round(tiempo_efectivo, 4),
            "riesgo": round(riesgo, 4),
            "penalizacion": round(penalizacion, 4),
            "margen_competidor": round(margen_competidor, 4),
            "captura_competidor": round(captura, 4),
            "bono_bloqueo": bono_bloqueo,
            "solucion_valida": solucion.valida,
            "violaciones": list(solucion.violaciones),
            "orden_entregas": info_ruta["orden"],
            "evitar": info_ruta["evitar"],
            "modo_ruta": info_ruta["modo_ruta"],
        },
    }


def _mejores_respuestas(
    estrategias_jugador: list[str],
    estrategias_rival: list[str],
    pagos: dict[tuple[str, str], float],
    jugador_es_empresa: bool,
) -> dict[str, list[str]]:
    respuestas: dict[str, list[str]] = {}
    for accion_rival in estrategias_rival:
        valores = {
            accion: pagos[(accion, accion_rival)]
            if jugador_es_empresa
            else pagos[(accion_rival, accion)]
            for accion in estrategias_jugador
        }
        maximo = max(valores.values())
        respuestas[accion_rival] = [
            accion for accion, valor in valores.items() if abs(valor - maximo) <= 1e-9
        ]
    return respuestas


def _dominancia(
    estrategias: list[str],
    rivales: list[str],
    pagos: dict[tuple[str, str], float],
) -> tuple[list[str], list[str], list[str], list[str]]:
    dominantes: list[str] = []
    dominadas: list[str] = []
    debilmente_dominantes: list[str] = []
    debilmente_dominadas: list[str] = []
    for estrategia in estrategias:
        valores_propios = [pagos[(estrategia, rival)] for rival in rivales]
        domina_estrictamente_todas = True
        domina_debilmente_todas = True
        for otra in estrategias:
            if otra == estrategia:
                continue
            valores_otra = [pagos[(otra, rival)] for rival in rivales]
            estricta = all(a > b for a, b in zip(valores_propios, valores_otra))
            debil = all(a >= b for a, b in zip(valores_propios, valores_otra))
            if not estricta:
                domina_estrictamente_todas = False
            if not debil:
                domina_debilmente_todas = False
        if domina_estrictamente_todas:
            dominantes.append(estrategia)
        if domina_debilmente_todas:
            debilmente_dominantes.append(estrategia)

        for otra in estrategias:
            if otra == estrategia:
                continue
            valores_otra = [pagos[(otra, rival)] for rival in rivales]
            if all(b > a for a, b in zip(valores_propios, valores_otra)):
                if estrategia not in dominadas:
                    dominadas.append(estrategia)
            if all(b >= a for a, b in zip(valores_propios, valores_otra)) and any(
                b > a for a, b in zip(valores_propios, valores_otra)
            ):
                if estrategia not in debilmente_dominadas:
                    debilmente_dominadas.append(estrategia)
    return dominantes, dominadas, debilmente_dominantes, debilmente_dominadas


def analizar_juego(escenario: Escenario) -> JuegoEstrategico:
    """Construye y resuelve el juego estratégico del escenario."""
    errores = escenario.validar(requerir_min_entregas=False)
    if errores:
        raise ValueError("Escenario inválido para el juego: " + "; ".join(errores))

    ingreso = sum(
        e.demanda * (e.tarifa if e.tarifa is not None else escenario.tarifa_por_unidad)
        for e in escenario.entregas
    )
    # Costo base neutral: ruta por costo, orden vecino más cercano, sin bloqueos.
    planificador_base = PlanificadorRutas(escenario)
    solucion_base = planificador_base.evaluar(
        orden_vecino_mas_cercano(escenario), "Juego:base"
    )
    costo_base = solucion_base.costo_total

    estrategias_empresa = list(ESTRATEGIAS_EMPRESA)
    estrategias_competidor = list(ESTRATEGIAS_COMPETIDOR)
    matriz: list[dict] = []
    pagos_empresa: dict[tuple[str, str], float] = {}
    pagos_competidor: dict[tuple[str, str], float] = {}
    for empresa in estrategias_empresa:
        for competidor in estrategias_competidor:
            celda = _evaluar_celda(escenario, empresa, competidor, costo_base, ingreso)
            matriz.append(celda)
            pagos_empresa[(empresa, competidor)] = celda["pago_empresa"]
            pagos_competidor[(empresa, competidor)] = celda["pago_competidor"]

    mejores_empresa = _mejores_respuestas(
        estrategias_empresa, estrategias_competidor, pagos_empresa, True
    )
    mejores_competidor = _mejores_respuestas(
        estrategias_competidor, estrategias_empresa, pagos_competidor, False
    )

    dominantes_e, dominadas_e, debiles_e, debiles_dom_e = _dominancia(
        estrategias_empresa, estrategias_competidor, pagos_empresa
    )
    # ``_dominancia`` espera claves (jugador, rival); se transpone el
    # diccionario porque los pagos del competidor están guardados como
    # (empresa, competidor).
    pagos_competidor_transpuestos = {
        (competidor, empresa): valor
        for (empresa, competidor), valor in pagos_competidor.items()
    }
    dominantes_c, dominadas_c, debiles_c, debiles_dom_c = _dominancia(
        estrategias_competidor, estrategias_empresa, pagos_competidor_transpuestos
    )

    nash: list[tuple[str, str]] = []
    for empresa in estrategias_empresa:
        for competidor in estrategias_competidor:
            if (
                empresa in mejores_empresa[competidor]
                and competidor in mejores_competidor[empresa]
            ):
                nash.append((empresa, competidor))

    # Recomendación: Nash con mayor pago para la empresa; si no hay Nash,
    # maximin (mejor peor caso) para una decisión robusta.
    if nash:
        mejor_nash = max(
            nash,
            key=lambda par: (pagos_empresa[par], -estrategias_empresa.index(par[0])),
        )
        recomendacion = {
            "estrategia_empresa": mejor_nash[0],
            "estrategia_competidor": mejor_nash[1],
            "pago_empresa": pagos_empresa[mejor_nash],
            "motivo": "Equilibrio de Nash puro con el mayor pago para la empresa.",
            "tipo": "nash",
        }
    else:
        maximin = {
            empresa: min(pagos_empresa[(empresa, c)] for c in estrategias_competidor)
            for empresa in estrategias_empresa
        }
        mejor_empresa = max(estrategias_empresa, key=lambda e: maximin[e])
        peor_competidor = min(
            estrategias_competidor,
            key=lambda c: pagos_empresa[(mejor_empresa, c)],
        )
        recomendacion = {
            "estrategia_empresa": mejor_empresa,
            "estrategia_competidor": peor_competidor,
            "pago_empresa": pagos_empresa[(mejor_empresa, peor_competidor)],
            "motivo": "No hay Nash puro; se aplica el criterio maximin.",
            "tipo": "maximin",
        }

    analisis = {
        "mejores_respuestas_empresa": mejores_empresa,
        "mejores_respuestas_competidor": mejores_competidor,
        "dominantes_empresa": dominantes_e,
        "dominadas_empresa": dominadas_e,
        "debilmente_dominantes_empresa": debiles_e,
        "debilmente_dominadas_empresa": debiles_dom_e,
        "dominantes_competidor": dominantes_c,
        "dominadas_competidor": dominadas_c,
        "equilibrios_nash": [list(par) for par in nash],
        "explicacion": (
            "Los pagos de la empresa son ingreso menos costo efectivo y "
            "penalización por riesgo/recursos. Los del competidor combinan su "
            "margen de mercado, la captura por sobrecostos inducidos y bonos "
            "por bloqueo. Un par es Nash si ninguna de las dos partes mejora "
            "cambiando unilateralmente de estrategia."
        ),
    }
    return JuegoEstrategico(
        escenario_id=escenario.id,
        nombre_escenario=escenario.nombre,
        estrategias_empresa=estrategias_empresa,
        estrategias_competidor=estrategias_competidor,
        matriz=matriz,
        analisis=analisis,
        recomendacion=recomendacion,
        metricas={
            "ingreso_base": round(ingreso, 4),
            "costo_base": round(costo_base, 4),
            "solucion_base_valida": solucion_base.valida,
            "formula_empresa": "ingreso - costo_efectivo - penalizacion",
            "formula_competidor": (
                "0.22*ingreso + 0.45*max(0,costo_efectivo-costo_base) "
                "+ bono_bloqueo - castigo"
            ),
            "num_celdas": len(matriz),
        },
    )
