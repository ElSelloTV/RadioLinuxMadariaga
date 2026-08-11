#!/usr/bin/env python3
"""
satelite_main.py
--------------------------------------------------------
Punto de entrada de la app satélite de control remoto — pedido
explícito: "una app aparte satélite... pueda controlar el programa en
ejecución por el usuario Radio... incluso subir algún archivo de
audio al explorador". SIN salida de audio, es lo único que queda
afuera a propósito.

Pensada para correr en OTRA sesión de usuario de la MISMA PC física
que la radio (el caso real: Chrome Remote Desktop, que en Linux
muestra un escritorio limpio de otro usuario en vez de la sesión
real) — se conecta al servidor de control remoto embebido en el
programa principal (ver core/servidor_control_remoto.py) por
127.0.0.1, así que loopback alcanza, nunca hace falta red real.

Requisito, del lado del programa principal: Configuración → Control
remoto → activar el servidor (desactivado por defecto) y copiar el
puerto/token acá.
--------------------------------------------------------
"""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from satelite.ventana_satelite import VentanaSatelite

RUTA_ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icono.png")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Radio Tuyú — Satélite")
    app.setApplicationDisplayName("Auto-Radio Tuyú — Satélite")
    app.setWindowIcon(QIcon(RUTA_ICONO))

    ventana = VentanaSatelite()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
