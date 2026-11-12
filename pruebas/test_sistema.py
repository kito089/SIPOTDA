"""Pruebas automáticas de integración y algoritmos de SIPOTDA."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from algoritmos.busqueda_adversaria.alfa_beta import ejecutar_alfa_beta
from algoritmos.busqueda_adversaria.minimax import ejecutar_minimax
from algoritmos.busqueda_adversaria.modelo_adversario import crear_configuracion
from algoritmos.busqueda_local.hill_climbing import reinicios_hill_climbing
from algoritmos.metaheuristicas.algoritmo_genetico import algoritmo_genetico
from algoritmos.metaheuristicas.recocido_simulado import recocido_simulado
from algoritmos.registro import ejecutar_busqueda_heuristica
from algoritmos.teoria_juegos.juego_estrategico import analizar_juego
from experimentos.ejecutar_experimentos import ejecutar_todo
from gestion_archivos.lector_json import cargar_escenario
from gestion_archivos.validar_escenario import validar_factibilidad


class PruebasEscenarios(unittest.TestCase):
    def test_escenario_predeterminado_es_factible(self) -> None:
        escenario = cargar_escenario(RAIZ / "escenarios" / "escenario_predeterminado.json")
        self.assertEqual(escenario.id, "logistica_12x12")
        self.assertEqual(escenario.validar(), [])
        resultado = validar_factibilidad(escenario)
        self.assertTrue(resultado["valido"])
        self.assertTrue(resultado["hay_solucion"])
        self.assertAlmostEqual(resultado["mejor_costo"], 37.8, places=3)

    def test_escenarios_alternativos_son_validos(self) -> None:
        for nombre in ("escenario_alternativo.json", "escenario_estrecho.json"):
            escenario = cargar_escenario(RAIZ / "escenarios" / nombre)
            self.assertEqual(escenario.validar(), [], nombre)
            self.assertTrue(validar_factibilidad(escenario)["hay_solucion"], nombre)

    def test_escenario_bloqueado_es_rechazado(self) -> None:
        with self.assertRaises(Exception):
            cargar_escenario(RAIZ / "escenarios" / "escenario_bloqueado.json")


class PruebasAlgoritmos(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.escenario = cargar_escenario(
            RAIZ / "escenarios" / "escenario_predeterminado.json"
        )

    def test_busqueda_heuristica_encuentra_rutas_validas(self) -> None:
        for algoritmo in ("Greedy Best-First", "A*"):
            resultado = ejecutar_busqueda_heuristica(self.escenario, algoritmo)
            self.assertTrue(resultado.exito, algoritmo)
            self.assertIsNotNone(resultado.solucion)
            self.assertTrue(resultado.solucion.valida, algoritmo)
            self.assertGreater(resultado.costo, 0)

    def test_hill_climbing_y_metaheuristicas(self) -> None:
        resultados, resumen = reinicios_hill_climbing(
            self.escenario, num_inicios=2, semilla_base=2026, max_iteraciones=60
        )
        self.assertTrue(resultados)
        self.assertEqual(resumen["num_inicios"], 2)

        recocido = recocido_simulado(
            self.escenario,
            semilla=2026,
            temperatura_inicial=20.0,
            temperatura_final=0.1,
            enfriamiento=0.8,
            iteraciones_por_temperatura=5,
            max_iteraciones=80,
        )
        self.assertTrue(recocido.exito)
        self.assertTrue(recocido.solucion.valida)

        genetico = algoritmo_genetico(
            self.escenario,
            semilla=2026,
            tamano_poblacion=8,
            generaciones=5,
            elitismo=1,
            tamano_torneo=2,
        )
        self.assertTrue(genetico.exito)
        self.assertTrue(genetico.solucion.valida)

    def test_juego_y_equivalencia_adversaria(self) -> None:
        juego = analizar_juego(self.escenario)
        self.assertEqual(len(juego.matriz), 9)
        self.assertTrue(juego.analisis["equilibrios_nash"])
        self.assertIn(juego.recomendacion["estrategia_empresa"], juego.estrategias_empresa)

        configuracion = crear_configuracion(self.escenario, 4)
        minimax = ejecutar_minimax(self.escenario, configuracion=configuracion)
        alfa = ejecutar_alfa_beta(self.escenario, configuracion=configuracion)
        self.assertAlmostEqual(minimax.valor_minimax, alfa.valor_minimax, places=9)
        self.assertLessEqual(alfa.nodos_visitados, minimax.nodos_visitados)


class PruebasIntegracion(unittest.TestCase):
    def test_flujo_completo_reducido_en_directorio_temporal(self) -> None:
        escenario = cargar_escenario(
            RAIZ / "escenarios" / "escenario_predeterminado.json"
        )
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            import experimentos.ejecutar_experimentos as modulo

            with patch.object(modulo, "DIR_RESULTADOS", base), patch.object(
                modulo, "DIR_CSV", base / "csv"
            ), patch.object(modulo, "DIR_GRAFICAS", base / "graficas"):
                datos = ejecutar_todo(
                    escenario,
                    repeticiones=1,
                    num_inicios=2,
                    profundidades=[2],
                    generar_graficas=False,
                    guardar=True,
                )
            self.assertEqual(len(datos["resultados"]), 6)
            self.assertTrue(datos["plan"]["plan_valido"])
            self.assertTrue((base / "planificacion_final.json").exists())
            self.assertTrue((base / "csv" / "resultados_completos_logistica_12x12.csv").exists())
            self.assertEqual(datos["adversaria"]["filas"][0]["iguales"], True)

    def test_fallo_parcial_conserva_resultados_validos(self) -> None:
        escenario = cargar_escenario(
            RAIZ / "escenarios" / "escenario_predeterminado.json"
        )
        import experimentos.ejecutar_experimentos as modulo

        with patch.object(
            modulo,
            "experimento_juego",
            side_effect=RuntimeError("fallo simulado del juego"),
        ):
            datos = ejecutar_todo(
                escenario,
                repeticiones=1,
                num_inicios=2,
                profundidades=[2],
                generar_graficas=False,
                guardar=False,
            )
        self.assertEqual(len(datos["resultados"]), 6)
        self.assertIsNone(datos["plan"])
        self.assertTrue(
            any("juego estratégico" in error for error in datos["errores"])
        )


if __name__ == "__main__":
    unittest.main()
