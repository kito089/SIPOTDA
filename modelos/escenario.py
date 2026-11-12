"""Escenario logístico compartido: cuadrícula, recursos y competidor."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Iterator

from .celda import Celda
from .entrega import Entrega
from .recurso import Recurso


DIRECCIONES_RECTAS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRECCIONES_DIAGONALES = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
RECURSOS_REQUERIDOS = ("combustible", "capacidad", "tiempo", "presupuesto")


@dataclass
class Escenario:
    """Red logística 12x12 (configurable) con recursos y competidor.

    Reglas de movimiento
    --------------------
    - Siempre se permite movimiento horizontal y vertical.
    - El movimiento diagonal es opcional; se habilita con
      ``permitir_diagonal`` y su costo se multiplica por
      ``factor_costo_diagonal`` (por defecto ``sqrt(2)``).
    - Nunca se atraviesan obstáculos ni se sale de la cuadrícula.
    - El costo de un desplazamiento es el costo de la celda de destino.
    """

    id: str = "escenario"
    nombre: str = "Escenario logístico"
    filas: int = 12
    columnas: int = 12
    celdas: list[list[Celda]] = field(default_factory=list)
    inicio: tuple[int, int] = (0, 0)
    destino: tuple[int, int] = (11, 11)
    entregas: list[Entrega] = field(default_factory=list)
    obstaculos: set[tuple[int, int]] = field(default_factory=set)
    recursos: dict[str, Recurso] = field(default_factory=dict)
    competidor: dict = field(default_factory=dict)
    permitir_diagonal: bool = False
    factor_costo_diagonal: float = math.sqrt(2)
    tarifa_por_unidad: float = 60.0
    restricciones: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = str(self.id)
        self.nombre = str(self.nombre)
        self.filas = int(self.filas)
        self.columnas = int(self.columnas)
        if self.filas <= 0 or self.columnas <= 0:
            raise ValueError("Las dimensiones del escenario deben ser positivas")
        self.inicio = (int(self.inicio[0]), int(self.inicio[1]))
        self.destino = (int(self.destino[0]), int(self.destino[1]))
        self.permitir_diagonal = bool(self.permitir_diagonal)
        self.factor_costo_diagonal = float(self.factor_costo_diagonal)
        self.tarifa_por_unidad = float(self.tarifa_por_unidad)
        self.obstaculos = {(int(f), int(c)) for f, c in self.obstaculos}
        self.entregas = list(self.entregas)
        if not self.celdas:
            self.celdas = [
                [Celda(costo=1.0) for _ in range(self.columnas)]
                for _ in range(self.filas)
            ]
        if len(self.celdas) != self.filas or any(
            len(fila) != self.columnas for fila in self.celdas
        ):
            raise ValueError("La matriz de celdas no coincide con las dimensiones")
        if isinstance(self.recursos, dict):
            self.recursos = {
                nombre: (
                    recurso
                    if isinstance(recurso, Recurso)
                    else Recurso.desde_dict(recurso)
                )
                for nombre, recurso in self.recursos.items()
            }
        if not isinstance(self.competidor, dict):
            raise ValueError("La configuración del competidor debe ser un diccionario")
        self.competidor = dict(self.competidor)
        self.restringir_recursos_competidor()
        self.sincronizar_obstaculos()
        self.recalcular_tipos()

    # ------------------------------------------------------------------
    # Construcción y copia
    # ------------------------------------------------------------------
    @classmethod
    def crear_vacio(
        cls,
        filas: int = 12,
        columnas: int = 12,
        id_escenario: str = "nuevo_escenario",
        nombre: str = "Nuevo escenario",
    ) -> "Escenario":
        celdas = [[Celda(costo=1.0) for _ in range(columnas)] for _ in range(filas)]
        return cls(
            id=id_escenario,
            nombre=nombre,
            filas=filas,
            columnas=columnas,
            celdas=celdas,
            inicio=(0, 0),
            destino=(filas - 1, columnas - 1),
            entregas=[
                Entrega(1, "E1", max(1, filas // 3), max(1, columnas // 3)),
                Entrega(2, "E2", max(1, filas // 2), max(2, (2 * columnas) // 3)),
                Entrega(3, "E3", max(2, (2 * filas) // 3), max(1, columnas // 4)),
            ],
            recursos={
                "combustible": Recurso("combustible", 200, "unidades", 1.0),
                "capacidad": Recurso("capacidad", 30, "unidades", 0.0),
                "tiempo": Recurso("tiempo", 250, "pasos", 1.0),
                "presupuesto": Recurso("presupuesto", 300, "monetarias", 0.0),
            },
            competidor={
                "nombre": "Competidor",
                "factor_costo": 1.0,
                "factor_presupuesto": 1.0,
                "celdas_bloqueadas": [],
                "descripcion": "Competidor configurable",
            },
            tarifa_por_unidad=60.0,
        )

    def clonar(self) -> "Escenario":
        copia = Escenario(
            id=self.id,
            nombre=self.nombre,
            filas=self.filas,
            columnas=self.columnas,
            celdas=[[celda.clonar() for celda in fila] for fila in self.celdas],
            inicio=tuple(self.inicio),
            destino=tuple(self.destino),
            entregas=[e.clonar() for e in self.entregas],
            obstaculos=set(self.obstaculos),
            recursos={k: v.clonar() for k, v in self.recursos.items()},
            competidor=dict(self.competidor),
            permitir_diagonal=self.permitir_diagonal,
            factor_costo_diagonal=self.factor_costo_diagonal,
            tarifa_por_unidad=self.tarifa_por_unidad,
            restricciones=dict(self.restricciones),
            meta=dict(self.meta),
        )
        return copia

    # ------------------------------------------------------------------
    # Consultas básicas de la cuadrícula
    # ------------------------------------------------------------------
    def dentro(self, fila: int, columna: int) -> bool:
        return 0 <= fila < self.filas and 0 <= columna < self.columnas

    def obtener_celda(self, fila: int, columna: int) -> Celda:
        if not self.dentro(fila, columna):
            raise IndexError(f"Coordenada fuera de la cuadrícula: ({fila}, {columna})")
        return self.celdas[int(fila)][int(columna)]

    def obtener_costo(self, fila: int, columna: int) -> float:
        return self.obtener_celda(fila, columna).costo

    def establecer_costo(self, fila: int, columna: int, costo: float) -> None:
        costo = float(costo)
        if not math.isfinite(costo) or costo <= 0:
            raise ValueError("El costo debe ser un número finito mayor que cero")
        self.obtener_celda(fila, columna).costo = costo

    def es_transitable(
        self,
        fila: int,
        columna: int,
        evitar: set[tuple[int, int]] | None = None,
    ) -> bool:
        if not self.dentro(fila, columna):
            return False
        if evitar and (fila, columna) in evitar:
            return False
        return self.celdas[fila][columna].transitable

    def obtener_entrega(self, id_entrega: int) -> Entrega | None:
        for entrega in self.entregas:
            if entrega.id == id_entrega:
                return entrega
        return None

    def posiciones_ocupadas(self) -> set[tuple[int, int]]:
        posiciones = {self.inicio, self.destino}
        posiciones.update(e.posicion for e in self.entregas)
        return posiciones

    def puntos_obligatorios(self) -> list[tuple[str, tuple[int, int]]]:
        """Inicio, entregas (en su orden actual) y destino."""
        puntos: list[tuple[str, tuple[int, int]]] = [("Inicio", self.inicio)]
        for entrega in self.entregas:
            puntos.append((entrega.nombre, entrega.posicion))
        puntos.append(("Destino", self.destino))
        return puntos

    def indice_entregas(self) -> dict[int, Entrega]:
        return {e.id: e for e in self.entregas}

    # ------------------------------------------------------------------
    # Movimientos y heurística
    # ------------------------------------------------------------------
    def direcciones(self) -> list[tuple[int, int]]:
        if self.permitir_diagonal:
            return DIRECCIONES_RECTAS + DIRECCIONES_DIAGONALES
        return list(DIRECCIONES_RECTAS)

    def vecinos(
        self,
        fila: int,
        columna: int,
        evitar: set[tuple[int, int]] | None = None,
        factor_costo: float = 1.0,
        modo: str = "costo",
    ) -> Iterator[tuple[int, int, float]]:
        """Genera ``(fila, columna, costo_arista)`` de celdas transitables.

        ``modo='pasos'`` asigna 1.0 por movimiento (útil para minimizar el
        número de pasos); ``modo='costo'`` usa el costo de la celda destino.
        """
        if factor_costo <= 0 or not math.isfinite(factor_costo):
            raise ValueError("El factor de costo debe ser positivo y finito")
        for df, dc in self.direcciones():
            nf, nc = fila + df, columna + dc
            if not self.es_transitable(nf, nc, evitar):
                continue
            if modo == "pasos":
                costo = 1.0
            else:
                costo = self.celdas[nf][nc].costo * factor_costo
                if df != 0 and dc != 0:
                    costo *= self.factor_costo_diagonal
            yield nf, nc, costo

    def costo_minimo_celda(self) -> float:
        """Menor costo entre celdas transitables (base de la heurística)."""
        costos = [
            celda.costo
            for fila in self.celdas
            for celda in fila
            if celda.transitable and celda.costo > 0
        ]
        return min(costos) if costos else float("inf")

    def heuristica(
        self,
        posicion: tuple[int, int],
        objetivo: tuple[int, int],
        factor_costo: float = 1.0,
        modo: str = "costo",
    ) -> float:
        """Heurística geométrica admisible.

        Con movimiento recto se usa la distancia Manhattan multiplicada por el
        costo mínimo transitable.  Si se permite diagonal se usa la distancia
        octile (una diagonal equivale a ``sqrt(2)``), también multiplicada por
        el costo mínimo.  Cualquier ruta real requiere al menos esa cantidad,
        por lo que la heurística nunca sobreestima el costo restante.
        """
        df = abs(int(posicion[0]) - int(objetivo[0]))
        dc = abs(int(posicion[1]) - int(objetivo[1]))
        if self.permitir_diagonal:
            distancia = max(df, dc) + (math.sqrt(2) - 1.0) * min(df, dc)
        else:
            distancia = df + dc
        if modo == "pasos":
            return distancia
        return distancia * self.costo_minimo_celda() * factor_costo

    def distancia_manhattan(self, a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # ------------------------------------------------------------------
    # Edición de elementos
    # ------------------------------------------------------------------
    def _validar_posicion_elemento(
        self,
        fila: int,
        columna: int,
        ignorar: set[tuple[int, int]] | None = None,
        permitir_obstaculo: bool = False,
    ) -> None:
        if not self.dentro(fila, columna):
            raise ValueError(f"La posición ({fila}, {columna}) está fuera de la cuadrícula")
        ignorar = ignorar or set()
        if (fila, columna) in self.obstaculos and not permitir_obstaculo:
            raise ValueError("No se puede colocar un elemento sobre un obstáculo")
        for posicion in self.posiciones_ocupadas():
            if posicion not in ignorar and posicion == (fila, columna):
                raise ValueError("La posición ya está ocupada por otro elemento")

    def mover_inicio(self, fila: int, columna: int) -> None:
        self._validar_posicion_elemento(fila, columna, ignorar={self.inicio})
        self.inicio = (int(fila), int(columna))
        self.recalcular_tipos()

    def mover_destino(self, fila: int, columna: int) -> None:
        self._validar_posicion_elemento(fila, columna, ignorar={self.destino})
        self.destino = (int(fila), int(columna))
        self.recalcular_tipos()

    def mover_entrega(self, id_entrega: int, fila: int, columna: int) -> None:
        entrega = self.obtener_entrega(id_entrega)
        if entrega is None:
            raise ValueError(f"No existe la entrega {id_entrega}")
        self._validar_posicion_elemento(fila, columna, ignorar={entrega.posicion})
        entrega.establecer_posicion(fila, columna)
        self.recalcular_tipos()

    def agregar_entrega(
        self,
        fila: int,
        columna: int,
        demanda: float = 3.0,
        nombre: str | None = None,
        tarifa: float | None = None,
        id_entrega: int | None = None,
    ) -> Entrega:
        self._validar_posicion_elemento(fila, columna)
        if id_entrega is None:
            id_entrega = max((e.id for e in self.entregas), default=0) + 1
        if self.obtener_entrega(id_entrega) is not None:
            raise ValueError(f"Ya existe una entrega con id {id_entrega}")
        entrega = Entrega(
            id=id_entrega,
            nombre=nombre or f"E{id_entrega}",
            fila=fila,
            columna=columna,
            demanda=demanda,
            tarifa=self.tarifa_por_unidad if tarifa is None else tarifa,
        )
        self.entregas.append(entrega)
        self.recalcular_tipos()
        return entrega

    def eliminar_entrega(self, id_entrega: int) -> bool:
        antes = len(self.entregas)
        self.entregas = [e for e in self.entregas if e.id != id_entrega]
        self.recalcular_tipos()
        return len(self.entregas) != antes

    def agregar_obstaculo(self, fila: int, columna: int) -> None:
        if not self.dentro(fila, columna):
            raise ValueError("El obstáculo está fuera de la cuadrícula")
        if (fila, columna) in self.posiciones_ocupadas():
            raise ValueError("No se puede colocar un obstáculo sobre un elemento")
        self.obstaculos.add((int(fila), int(columna)))
        self.sincronizar_obstaculos()
        self.recalcular_tipos()

    def quitar_obstaculo(self, fila: int, columna: int) -> bool:
        posicion = (int(fila), int(columna))
        if posicion in self.obstaculos:
            self.obstaculos.remove(posicion)
            self.sincronizar_obstaculos()
            self.recalcular_tipos()
            return True
        return False

    def alternar_obstaculo(self, fila: int, columna: int) -> bool:
        if (fila, columna) in self.obstaculos:
            self.quitar_obstaculo(fila, columna)
            return False
        self.agregar_obstaculo(fila, columna)
        return True

    def sincronizar_obstaculos(self) -> None:
        for fila in range(self.filas):
            for columna in range(self.columnas):
                self.celdas[fila][columna].transitable = (
                    (fila, columna) not in self.obstaculos
                )

    def recalcular_tipos(self) -> None:
        """Actualiza etiquetas de las celdas a partir de las posiciones."""
        for fila in range(self.filas):
            for columna in range(self.columnas):
                celda = self.celdas[fila][columna]
                celda.tipo = "obstaculo" if (fila, columna) in self.obstaculos else "normal"
                celda.etiqueta = "#" if celda.tipo == "obstaculo" else ""
        if self.dentro(*self.inicio):
            celda = self.celdas[self.inicio[0]][self.inicio[1]]
            celda.tipo = "inicio"
            celda.etiqueta = "S"
        if self.dentro(*self.destino):
            celda = self.celdas[self.destino[0]][self.destino[1]]
            celda.tipo = "destino"
            celda.etiqueta = "G"
        for indice, entrega in enumerate(self.entregas, start=1):
            if self.dentro(*entrega.posicion):
                celda = self.celdas[entrega.fila][entrega.columna]
                celda.tipo = "entrega"
                celda.etiqueta = f"E{indice}"

    # ------------------------------------------------------------------
    # Recursos y competidor
    # ------------------------------------------------------------------
    def recurso(self, nombre: str) -> Recurso | None:
        return self.recursos.get(nombre)

    def limite_recurso(self, nombre: str, defecto: float = float("inf")) -> float:
        recurso = self.recursos.get(nombre)
        return recurso.cantidad if recurso else defecto

    def consumo_por_paso(self, nombre: str, defecto: float = 0.0) -> float:
        recurso = self.recursos.get(nombre)
        return recurso.consumo_por_paso if recurso else defecto

    def restringir_recursos_competidor(self) -> None:
        """Asegura que la configuración del competidor tenga claves conocidas."""
        valores = {
            "nombre": self.competidor.get("nombre", "Competidor"),
            "factor_costo": float(self.competidor.get("factor_costo", 1.0)),
            "factor_presupuesto": float(self.competidor.get("factor_presupuesto", 1.0)),
            "celdas_bloqueadas": [
                (int(p[0]), int(p[1]))
                for p in self.competidor.get("celdas_bloqueadas", [])
                if isinstance(p, (list, tuple)) and len(p) >= 2
            ],
            "descripcion": self.competidor.get("descripcion", ""),
        }
        self.competidor = valores

    def celdas_bloqueadas_competidor(self) -> set[tuple[int, int]]:
        return {
            (int(f), int(c))
            for f, c in self.competidor.get("celdas_bloqueadas", [])
            if self.dentro(int(f), int(c))
        }

    # ------------------------------------------------------------------
    # Validación estructural
    # ------------------------------------------------------------------
    def validar(self, requerir_min_entregas: bool = True) -> list[str]:
        errores: list[str] = []
        if self.filas < 2 or self.columnas < 2:
            errores.append("La cuadrícula debe tener al menos 2x2 celdas.")
        if not self.dentro(*self.inicio):
            errores.append(f"El inicio {self.inicio} está fuera de la cuadrícula.")
        if not self.dentro(*self.destino):
            errores.append(f"El destino {self.destino} está fuera de la cuadrícula.")
        if not self.entregas:
            errores.append("El escenario debe tener al menos un punto de entrega.")
        if requerir_min_entregas and len(self.entregas) < 3:
            errores.append("El escenario debe tener al menos tres puntos de entrega.")

        ids = [e.id for e in self.entregas]
        if len(ids) != len(set(ids)):
            errores.append("Los identificadores de entrega deben ser únicos.")

        posiciones: dict[tuple[int, int], str] = {}
        for nombre, posicion in [("Inicio", self.inicio), ("Destino", self.destino)]:
            if posicion in posiciones:
                errores.append(f"El {nombre.lower()} se superpone con {posiciones[posicion]}.")
            else:
                posiciones[posicion] = nombre
        for entrega in self.entregas:
            if not self.dentro(*entrega.posicion):
                errores.append(
                    f"La entrega {entrega.nombre} está fuera de la cuadrícula: "
                    f"{entrega.posicion}."
                )
                continue
            if entrega.posicion in posiciones:
                errores.append(
                    f"La entrega {entrega.nombre} se superpone con "
                    f"{posiciones[entrega.posicion]}."
                )
            else:
                posiciones[entrega.posicion] = entrega.nombre
            if entrega.demanda < 0:
                errores.append(f"La demanda de {entrega.nombre} es negativa.")
            if entrega.tarifa < 0:
                errores.append(f"La tarifa de {entrega.nombre} es negativa.")

        for obstaculo in self.obstaculos:
            if not self.dentro(*obstaculo):
                errores.append(f"El obstáculo {obstaculo} está fuera de la cuadrícula.")
            elif obstaculo in posiciones:
                errores.append(
                    f"El obstáculo {obstaculo} bloquea el elemento {posiciones[obstaculo]}."
                )

        for fila in range(self.filas):
            for columna in range(self.columnas):
                celda = self.celdas[fila][columna]
                if not math.isfinite(celda.costo) or celda.costo <= 0:
                    errores.append(
                        f"Costo inválido en ({fila}, {columna}): {celda.costo!r}."
                    )
                if not celda.transitable and (fila, columna) in posiciones:
                    errores.append(
                        f"La celda ({fila}, {columna}) no es transitable pero contiene "
                        f"{posiciones[(fila, columna)]}."
                    )

        for nombre in RECURSOS_REQUERIDOS:
            if nombre not in self.recursos:
                errores.append(f"Falta el recurso obligatorio {nombre!r}.")
                continue
            recurso = self.recursos[nombre]
            if recurso.cantidad <= 0:
                errores.append(f"El recurso {nombre!r} debe tener disponibilidad positiva.")
            if recurso.consumo_por_paso < 0:
                errores.append(f"El consumo del recurso {nombre!r} no puede ser negativo.")

        capacidad = self.limite_recurso("capacidad", float("inf"))
        demanda_total = sum(e.demanda for e in self.entregas)
        if demanda_total <= 0:
            errores.append("La demanda total de las entregas debe ser mayor que cero.")
        if capacidad < demanda_total:
            errores.append(
                f"Capacidad insuficiente: {capacidad:g} < demanda total {demanda_total:g}."
            )

        if self.factor_costo_diagonal <= 0 or not math.isfinite(self.factor_costo_diagonal):
            errores.append("El factor de costo diagonal debe ser positivo y finito.")
        if self.competidor.get("factor_costo", 1.0) <= 0:
            errores.append("El factor de costo del competidor debe ser positivo.")
        if self.competidor.get("factor_presupuesto", 1.0) <= 0:
            errores.append("El factor de presupuesto del competidor debe ser positivo.")
        for posicion in self.celdas_bloqueadas_competidor():
            if posicion in posiciones:
                errores.append(
                    f"El competidor bloquea la celda {posicion}, ocupada por "
                    f"{posiciones[posicion]}."
                )

        if not errores and self.dentro(*self.inicio) and self.dentro(*self.destino):
            inalcanzables = self._puntos_inalcanzables()
            if inalcanzables:
                errores.append(
                    "No existe una ruta transitable entre los puntos obligatorios; "
                    f"inalcanzables desde el inicio: {', '.join(inalcanzables)}."
                )
        return errores

    def _puntos_inalcanzables(self) -> list[str]:
        """BFS desde el inicio; movimiento simétrico, por lo que es suficiente."""
        if not self.es_transitable(*self.inicio):
            return ["Inicio"]
        visitados = {self.inicio}
        cola = deque([self.inicio])
        while cola:
            fila, columna = cola.popleft()
            for df, dc in self.direcciones():
                nf, nc = fila + df, columna + dc
                if self.es_transitable(nf, nc) and (nf, nc) not in visitados:
                    visitados.add((nf, nc))
                    cola.append((nf, nc))
        inalcanzables: list[str] = []
        if self.destino not in visitados:
            inalcanzables.append("Destino")
        for entrega in self.entregas:
            if entrega.posicion not in visitados:
                inalcanzables.append(entrega.nombre)
        return inalcanzables

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------
    def a_dict(self, incluir_matriz: bool = True) -> dict:
        datos = {
            "esquema": "sipotda.escenario/1",
            "id": self.id,
            "nombre": self.nombre,
            "filas": self.filas,
            "columnas": self.columnas,
            "inicio": list(self.inicio),
            "destino": list(self.destino),
            "entregas": [e.a_dict() for e in self.entregas],
            "obstaculos": [list(p) for p in sorted(self.obstaculos)],
            "recursos": {k: v.a_dict() for k, v in self.recursos.items()},
            "competidor": {
                "nombre": self.competidor.get("nombre", "Competidor"),
                "factor_costo": self.competidor.get("factor_costo", 1.0),
                "factor_presupuesto": self.competidor.get("factor_presupuesto", 1.0),
                "celdas_bloqueadas": [
                    list(p) for p in self.competidor.get("celdas_bloqueadas", [])
                ],
                "descripcion": self.competidor.get("descripcion", ""),
            },
            "restricciones": {
                "permitir_diagonal": self.permitir_diagonal,
                "factor_costo_diagonal": round(self.factor_costo_diagonal, 9),
                **dict(self.restricciones),
            },
            "tarifa_por_unidad": self.tarifa_por_unidad,
            "meta": dict(self.meta),
        }
        if incluir_matriz:
            datos["costos"] = [
                [round(celda.costo, 6) for celda in fila] for fila in self.celdas
            ]
        return datos

    @classmethod
    def desde_dict(cls, datos: dict) -> "Escenario":
        if not isinstance(datos, dict):
            raise ValueError("El escenario debe ser un objeto JSON")
        for campo in ("filas", "columnas", "inicio", "destino"):
            if campo not in datos:
                raise ValueError(f"Falta el campo obligatorio del escenario: {campo}")
        filas = int(datos["filas"])
        columnas = int(datos["columnas"])
        if filas <= 0 or columnas <= 0:
            raise ValueError("Las dimensiones del escenario deben ser positivas")

        if "celdas" in datos:
            celdas = [
                [Celda.desde_dict(celda) for celda in fila]
                for fila in datos["celdas"]
            ]
        elif "costos" in datos:
            matriz = datos["costos"]
            if len(matriz) != filas or any(len(fila) != columnas for fila in matriz):
                raise ValueError("La matriz de costos no coincide con filas/columnas")
            celdas = []
            for fila in matriz:
                fila_celdas = []
                for valor in fila:
                    costo = float(valor)
                    if not math.isfinite(costo) or costo <= 0:
                        raise ValueError(f"Costo inválido en el escenario: {valor!r}")
                    fila_celdas.append(Celda(costo=costo))
                celdas.append(fila_celdas)
        else:
            raise ValueError("El escenario debe incluir 'celdas' o 'costos'")

        entregas = [
            Entrega.desde_dict(e) for e in datos.get("entregas", [])
        ]
        recursos_datos = datos.get("recursos", {})
        if isinstance(recursos_datos, list):
            recursos = {
                recurso.nombre: recurso
                for recurso in (Recurso.desde_dict(r) for r in recursos_datos)
            }
        elif isinstance(recursos_datos, dict):
            recursos = {
                nombre: Recurso.desde_dict({"nombre": nombre, **valor})
                if isinstance(valor, dict)
                else valor
                for nombre, valor in recursos_datos.items()
            }
        else:
            raise ValueError("El campo 'recursos' debe ser un objeto o una lista")

        restricciones = dict(datos.get("restricciones", {}))
        permitir_diagonal = bool(restricciones.pop("permitir_diagonal", False))
        factor_diagonal = float(restricciones.pop("factor_costo_diagonal", math.sqrt(2)))

        obstaculos = {(int(p[0]), int(p[1])) for p in datos.get("obstaculos", [])}
        competidor = dict(datos.get("competidor", {}))
        if "celdas_bloqueadas" in competidor:
            competidor["celdas_bloqueadas"] = [
                [int(p[0]), int(p[1])] for p in competidor["celdas_bloqueadas"]
            ]

        return cls(
            id=datos.get("id", "escenario"),
            nombre=datos.get("nombre", "Escenario logístico"),
            filas=filas,
            columnas=columnas,
            celdas=celdas,
            inicio=tuple(int(x) for x in datos["inicio"]),
            destino=tuple(int(x) for x in datos["destino"]),
            entregas=entregas,
            obstaculos=obstaculos,
            recursos=recursos,
            competidor=competidor,
            permitir_diagonal=permitir_diagonal,
            factor_costo_diagonal=factor_diagonal,
            tarifa_por_unidad=float(datos.get("tarifa_por_unidad", 60.0)),
            restricciones=restricciones,
            meta=dict(datos.get("meta", {})),
        )

    def resumen(self) -> str:
        total = sum(e.demanda for e in self.entregas)
        return (
            f"{self.nombre} ({self.filas}x{self.columnas}) | "
            f"inicio={self.inicio} destino={self.destino} | "
            f"{len(self.entregas)} entregas, demanda={total:g} | "
            f"obstáculos={len(self.obstaculos)}"
        )
