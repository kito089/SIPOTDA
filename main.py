"""Punto de entrada de SIPOTDA."""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    try:
        from interfaz import VentanaPrincipal
    except Exception:
        print("No se pudo iniciar la interfaz gráfica:", file=sys.stderr)
        traceback.print_exc()
        return 1
    try:
        aplicacion = VentanaPrincipal()
    except Exception:
        print("No se pudo crear la ventana principal:", file=sys.stderr)
        traceback.print_exc()
        return 1
    aplicacion.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
