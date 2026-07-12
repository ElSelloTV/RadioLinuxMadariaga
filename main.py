#!/usr/bin/env python3
"""
main.py
--------------------------------------------------------
Punto de entrada de la aplicación.
Solo se encarga de:
1. Inicializar QApplication.
2. Aplicar la hoja de estilos global (gui/styles.py).
3. Instanciar y mostrar la ventana principal (gui/main_window.py).

Toda la lógica vive en gui/ (interfaz) y core/ (motor), este
archivo debe permanecer siempre mínimo.
--------------------------------------------------------
"""

import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from gui.main_window import MainWindow
from gui.styles import QSS_APLICACION
from config.settings import cargar_configuracion, registrar_error

RUTA_ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icono.png")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Radio Tuyú")
    app.setApplicationDisplayName("Auto-Radio Tuyú")
    if os.path.exists(RUTA_ICONO):
        app.setWindowIcon(QIcon(RUTA_ICONO))
    app.setStyleSheet(QSS_APLICACION)

    try:
        cargar_configuracion()
    except Exception as error:
        registrar_error(f"Error al iniciar la aplicación: {error}")

    ventana = MainWindow()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
