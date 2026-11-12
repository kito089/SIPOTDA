"""Errores de persistencia y validación con mensajes para el usuario."""

from __future__ import annotations


class ErrorArchivo(Exception):
    """Error de lectura/escritura de archivos."""


class ErrorSobrescritura(ErrorArchivo):
    """Se intentó sobrescribir un archivo existente sin autorización."""


class ErrorValidacion(Exception):
    """El escenario o la configuración no superan la validación."""

    def __init__(self, mensaje: str, errores: list[str] | None = None) -> None:
        super().__init__(mensaje)
        self.errores = list(errores or [])

    def __str__(self) -> str:
        if self.errores:
            return super().__str__() + "\n- " + "\n- ".join(self.errores)
        return super().__str__()
