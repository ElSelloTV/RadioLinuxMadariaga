"""
gui/estado_ui.py
--------------------------------------------------------
Persistencia de la disposición visual entre sesiones: posición
de los splitters (las 3 ventanas principales, y el interno del
Explorador categorías/archivos) y ancho de columnas de cada
árbol. Se guarda en config/data/ui_state.ini (QSettings, formato
INI — texto plano, consistente con el resto del proyecto).

Se guarda al cerrar la aplicación (MainWindow.closeEvent) y se
restaura apenas se construyen los paneles, antes de mostrar la
ventana.
--------------------------------------------------------
"""

import os
from PySide6.QtCore import QSettings

from config.settings import DIRECTORIO_CONFIG

ARCHIVO_ESTADO_UI = os.path.join(DIRECTORIO_CONFIG, "ui_state.ini")


def _settings() -> QSettings:
    os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)
    return QSettings(ARCHIVO_ESTADO_UI, QSettings.Format.IniFormat)


def guardar_splitter(nombre: str, splitter):
    _settings().setValue(f"splitters/{nombre}", splitter.sizes())


def restaurar_splitter(nombre: str, splitter):
    valores = _settings().value(f"splitters/{nombre}")
    if not valores:
        return
    try:
        splitter.setSizes([int(v) for v in valores])
    except (TypeError, ValueError):
        pass


def guardar_columnas(nombre: str, tree):
    anchos = [tree.columnWidth(i) for i in range(tree.columnCount())]
    _settings().setValue(f"columnas/{nombre}", anchos)


def restaurar_columnas(nombre: str, tree):
    anchos = _settings().value(f"columnas/{nombre}")
    if not anchos:
        return
    try:
        for i, ancho in enumerate(anchos):
            if i < tree.columnCount():
                tree.setColumnWidth(i, int(ancho))
    except (TypeError, ValueError):
        pass


def guardar_geometria_ventana(widget, nombre: str = "ventana_principal"):
    _settings().setValue(f"geometria/{nombre}", widget.saveGeometry())


def restaurar_geometria_ventana(widget, nombre: str = "ventana_principal"):
    valor = _settings().value(f"geometria/{nombre}")
    if valor:
        widget.restoreGeometry(valor)
