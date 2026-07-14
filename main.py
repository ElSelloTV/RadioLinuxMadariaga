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
import traceback

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

from gui.main_window import MainWindow
from gui.styles import QSS_APLICACION
from config.settings import cargar_configuracion, registrar_error, registrar_evento

RUTA_ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icono.png")


def _manejar_excepcion_no_capturada(tipo, valor, traceback_obj):
    """PySide6, si una excepción ocurre DENTRO de un slot (ej. el
    handler de un botón), por defecto la imprime a stderr y la
    aplicación sigue viva — no crashea, pero esa acción del operador
    silenciosamente no hizo nada. Eso es indistinguible, para el
    operador, de "el botón no respondió" (síntoma real reportado:
    Play de Ventana 2 sin responder sin ningún error visible). Este
    hook captura esa excepción en el log ANTES de dejar que Qt siga
    con su manejo por defecto, para poder reconstruir qué pasó."""
    detalle = "".join(traceback.format_exception(tipo, valor, traceback_obj))
    registrar_error(f"Excepción no capturada:\n{detalle}")
    sys.__excepthook__(tipo, valor, traceback_obj)


def main():
    sys.excepthook = _manejar_excepcion_no_capturada

    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Radio Tuyú")
    app.setApplicationDisplayName("Auto-Radio Tuyú")
    if os.path.exists(RUTA_ICONO):
        app.setWindowIcon(QIcon(RUTA_ICONO))
    app.setStyleSheet(QSS_APLICACION)

    # Preload de arranque (pedido explícito): una pantalla breve con
    # el ícono mientras se arma la ventana principal (carga de
    # configuración, biblioteca, playlists persistidas), en vez de que
    # el operador vea la pantalla en blanco unos instantes.
    splash = None
    if os.path.exists(RUTA_ICONO):
        pixmap = QPixmap(RUTA_ICONO).scaled(
            160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        splash = QSplashScreen(pixmap)
        splash.showMessage(
            "Cargando Auto-Radio Tuyú...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        splash.show()
        app.processEvents()

    try:
        cargar_configuracion()
    except Exception as error:
        registrar_error(f"Error al iniciar la aplicación: {error}")

    registrar_evento("Aplicación iniciada")

    ventana = MainWindow()
    ventana.show()
    if splash is not None:
        splash.finish(ventana)

    codigo_salida = app.exec()
    registrar_evento(f"Aplicación cerrada (código {codigo_salida})")
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()
