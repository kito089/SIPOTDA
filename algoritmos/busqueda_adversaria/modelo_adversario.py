"""Subproblema adversario de asignación de recursos logísticos.

Definición formal
-----------------
- Estado inicial: ronda 0, presupuesto de negociación disponible, combustible
  operativo, sin reservas, sin bloqueos, riesgo bajo e impacto del competidor
  nulo.  Es el turno de MAX (empresa).
- Estado: ``(turno, presupuesto, combustible, reservas, bloqueos, riesgo,
  impacto, historial)``.  Es inmutable para que la búsqueda no comparta
  referencias mutables.
- Acciones legales:
  * MAX: asegurar combustible, reservar ruta o negociar prioridad (si el
    presupuesto lo permite; si no, postergar inversión).
  * MIN: mantener disponibilidad, encarecer combustible o bloquear una ruta.
- Transiciones: las acciones de MAX consumen presupuesto, aumentan reservas o
  reducen el impacto/riesgo.  Las de MIN incrementan el impacto en costos, el
  riesgo o los bloqueos.
- Condición terminal: se alcanza la profundidad de turnos configurada (por
  ejemplo 4 plies = 2 rondas).
- Función de utilidad (MAX): ingreso de entregas menos costo operativo
  afectado por el competidor, penalización por riesgo y costo de acciones,
  más el valor de reservas y combustible asegurado.

Cuando la búsqueda se corta por profundidad se usa la misma función con una
estimación de los turnos restantes (evaluación aproximada).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from algoritmos.comun import PlanificadorRutas, orden_vecino_mas_cercano
from modelos.escenario import Escenario


ACCIONES_MAX = {
    "asegurar_combustible": {
        "costo": 10.0,
        "combustible": 15.0,
        "impacto": 0.0,
        "riesgo": -0.04,
        "reservas": 0,
        "descripcion": "Contrata suministro adicional para proteger la operación.",
    },
    "reservar_ruta": {
        "costo": 14.0,
        "combustible": 5.0,
        "impacto": -0.02,
        "riesgo": -0.06,
        "reservas": 1,
        "descripcion": "Reserva capacidad de una ruta crítica.",
    },
    "negociar_prioridad": {
        "costo": 8.0,
        "combustible": 0.0,
        "impacto": -0.05,
        "riesgo": -0.03,
        "reservas": 0,
        "descripcion": "Negocia prioridad y reduce el impacto del competidor.",
    },
}

ACCION_FALLBACK_MAX = {
    "costo": 0.0,
    "combustible": 0.0,
    "impacto": 0.02,
    "riesgo": 0.03,
    "reservas": 0,
    "descripcion": "Sin presupuesto: se posterga la inversión.",
}

ACCIONES_MIN = {
    "mantener_disponibilidad": {
        "impacto": 0.01,
        "riesgo": 0.0,
        "bloqueos": 0,
        "descripcion": "Mantiene su operación sin agredir a la empresa.",
    },
    "encarecer_combustible": {
        "impacto": 0.12,
        "riesgo": 0.04,
        "bloqueos": 0,
        "descripcion": "Presiona el precio del combustible compartido.",
    },
    "bloquear_ruta": {
        "impacto": 0.06,
        "riesgo": 0.06,
        "bloqueos": 1,
        "descripcion": "Ocupa temporalmente una ruta o recurso compartido.",
    },
}


@dataclass(frozen=True)
class ConfiguracionAdversario:
    escenario_id: str
    nombre_escenario: str
    ingreso_base: float
    costo_base_ruta: float
    consumo_base_combustible: float
    presupuesto_inicial: float = 40.0
    combustible_inicial: float = 100.0
    limite_turnos: int = 4

    def a_dict(self) -> dict:
        return {
            "escenario_id": self.escenario_id,
            "nombre_escenario": self.nombre_escenario,
            "ingreso_base": round(self.ingreso_base, 4),
            "costo_base_ruta": round(self.costo_base_ruta, 4),
            "consumo_base_combustible": round(self.consumo_base_combustible, 4),
            "presupuesto_inicial": self.presupuesto_inicial,
            "combustible_inicial": self.combustible_inicial,
            "limite_turnos": self.limite_turnos,
            "acciones_max": ACCIONES_MAX,
            "acciones_min": ACCIONES_MIN,
        }


@dataclass(frozen=True)
class EstadoAdversario:
    turno: int
    presupuesto: float
    combustible: float
    reservas: int
    bloqueos: int
    riesgo: float
    impacto: float
    historial_max: tuple[str, ...] = ()
    historial_min: tuple[str, ...] = ()

    def a_dict(self) -> dict:
        return {
            "turno": self.turno,
            "presupuesto": round(self.presupuesto, 4),
            "combustible": round(self.combustible, 4),
            "reservas": self.reservas,
            "bloqueos": self.bloqueos,
            "riesgo": round(self.riesgo, 4),
            "impacto": round(self.impacto, 4),
            "historial_max": list(self.historial_max),
            "historial_min": list(self.historial_min),
        }


def crear_configuracion(
    escenario: Escenario,
    profundidad: int | None = None,
) -> ConfiguracionAdversario:
    """Deriva los parámetros del juego adversario a partir del escenario."""
    errores = escenario.validar(requerir_min_entregas=False)
    if errores:
        raise ValueError("Escenario inválido para búsqueda adversaria: " + "; ".join(errores))
    profundidad = int(
        profundidad
        if profundidad is not None
        else escenario.restricciones.get("profundidad_adversaria", 4)
    )
    if profundidad < 2:
        raise ValueError("La profundidad adversaria debe ser al menos 2")
    if profundidad % 2 != 0:
        profundidad += 1
    planificador = PlanificadorRutas(escenario)
    orden = orden_vecino_mas_cercano(escenario)
    solucion = planificador.evaluar(orden, "Configuración adversaria")
    ingreso = sum(
        e.demanda * (e.tarifa if e.tarifa is not None else escenario.tarifa_por_unidad)
        for e in escenario.entregas
    )
    presupuesto_inicial = max(30.0, min(60.0, 0.5 * escenario.limite_recurso("presupuesto", 60.0)))
    return ConfiguracionAdversario(
        escenario_id=escenario.id,
        nombre_escenario=escenario.nombre,
        ingreso_base=ingreso,
        costo_base_ruta=solucion.costo_total,
        consumo_base_combustible=solucion.combustible_consumido,
        presupuesto_inicial=presupuesto_inicial,
        combustible_inicial=escenario.limite_recurso("combustible", 100.0),
        limite_turnos=profundidad,
    )


def crear_estado_inicial(config: ConfiguracionAdversario) -> EstadoAdversario:
    return EstadoAdversario(
        turno=0,
        presupuesto=config.presupuesto_inicial,
        combustible=config.combustible_inicial,
        reservas=0,
        bloqueos=0,
        riesgo=0.0,
        impacto=0.0,
    )


def es_turno_max(estado: EstadoAdversario) -> bool:
    return estado.turno % 2 == 0


def es_terminal(config: ConfiguracionAdversario, estado: EstadoAdversario) -> bool:
    return estado.turno >= config.limite_turnos


def acciones_legales(
    config: ConfiguracionAdversario,
    estado: EstadoAdversario,
) -> list[str]:
    if es_terminal(config, estado):
        return []
    if es_turno_max(estado):
        legales = [
            nombre
            for nombre, datos in ACCIONES_MAX.items()
            if datos["costo"] <= estado.presupuesto + 1e-9
        ]
        if not legales:
            legales = ["postergar_inversion"]
        return legales
    return list(ACCIONES_MIN)


def transicion(
    config: ConfiguracionAdversario,
    estado: EstadoAdversario,
    accion: str,
) -> EstadoAdversario:
    """Aplica una acción y devuelve un nuevo estado inmutable."""
    if es_terminal(config, estado):
        return estado
    if es_turno_max(estado):
        datos = ACCIONES_MAX.get(accion, ACCION_FALLBACK_MAX)
        nuevo = replace(
            estado,
            turno=estado.turno + 1,
            presupuesto=max(0.0, estado.presupuesto - datos["costo"]),
            combustible=min(
                config.combustible_inicial * 1.5,
                estado.combustible + datos["combustible"],
            ),
            reservas=estado.reservas + int(datos["reservas"]),
            riesgo=max(0.0, estado.riesgo + datos["riesgo"]),
            impacto=max(0.0, estado.impacto + datos["impacto"]),
            historial_max=estado.historial_max + (accion,),
        )
    else:
        datos = ACCIONES_MIN[accion]
        nuevo = replace(
            estado,
            turno=estado.turno + 1,
            bloqueos=estado.bloqueos + int(datos["bloqueos"]),
            riesgo=max(0.0, estado.riesgo + datos["riesgo"]),
            impacto=max(0.0, estado.impacto + datos["impacto"]),
            historial_min=estado.historial_min + (accion,),
        )
    return nuevo


def evaluar_estado(
    config: ConfiguracionAdversario,
    estado: EstadoAdversario,
    aproximada: bool = False,
) -> float:
    """Utilidad para MAX; MIN minimiza este mismo valor.

    Si ``aproximada`` es verdadero se añade una estimación de los turnos
    restantes, utilizada cuando la búsqueda alcanza el límite de profundidad
    antes de un estado terminal.
    """
    costo_operativo = config.costo_base_ruta * (1.0 + estado.impacto) + 25.0 * estado.bloqueos
    costo_acciones = config.presupuesto_inicial - estado.presupuesto
    penalizacion_riesgo = 120.0 * estado.riesgo
    valor_reservas = 30.0 * estado.reservas
    valor_combustible = 0.8 * (estado.combustible - config.combustible_inicial)
    utilidad = (
        config.ingreso_base
        - costo_operativo
        - costo_acciones
        - penalizacion_riesgo
        + valor_reservas
        + valor_combustible
    )
    if aproximada:
        turnos_restantes = max(0, config.limite_turnos - estado.turno)
        # Estimación conservadora: cada turno pendiente puede aumentar costos.
        utilidad -= 6.0 * turnos_restantes
    return float(utilidad)


@dataclass
class ResultadoAdversario:
    algoritmo: str
    escenario_id: str
    nombre_escenario: str
    profundidad: int
    valor_minimax: float
    mejor_accion: str | None
    linea_principal: list[str] = field(default_factory=list)
    nodos_visitados: int = 0
    nodos_podados: int = 0
    tiempo_ejecucion: float = 0.0
    exito: bool = True
    mensaje: str = ""
    estado_raiz: dict = field(default_factory=dict)
    estado_final: dict = field(default_factory=dict)
    configuracion: dict = field(default_factory=dict)
    metricas: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return {
            "algoritmo": self.algoritmo,
            "escenario_id": self.escenario_id,
            "nombre_escenario": self.nombre_escenario,
            "profundidad": self.profundidad,
            "valor_minimax": round(self.valor_minimax, 6),
            "mejor_accion": self.mejor_accion,
            "linea_principal": list(self.linea_principal),
            "nodos_visitados": self.nodos_visitados,
            "nodos_podados": self.nodos_podados,
            "tiempo_ejecucion": round(self.tiempo_ejecucion, 6),
            "exito": self.exito,
            "mensaje": self.mensaje,
            "estado_raiz": self.estado_raiz,
            "estado_final": self.estado_final,
            "configuracion": self.configuracion,
            "metricas": self.metricas,
        }

    def resumen_texto(self) -> str:
        return (
            f"{self.algoritmo}: valor minimax={self.valor_minimax:.2f}, "
            f"mejor acción={self.mejor_accion}, "
            f"nodos visitados={self.nodos_visitados}, "
            f"podados={self.nodos_podados}, "
            f"tiempo={self.tiempo_ejecucion:.4f}s\n"
            f"Línea principal: {' -> '.join(self.linea_principal) or 'hoja'}"
        )
