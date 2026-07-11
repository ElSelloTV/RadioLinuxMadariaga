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

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import QSS_APLICACION
from config.settings import cargar_configuracion, registrar_error


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Automatización Radial (Clon Dinesat 9)")
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
