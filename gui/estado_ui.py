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
from PySide6.QtWidgets import QApplication

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


def guardar_valor(clave: str, valor):
    """Persistencia genérica de un valor chico (string, lista de
    strings, etc.) bajo la sección "estado/" — usado por ejemplo para
    recordar la última categoría navegada en el buscador de biblioteca
    del Programador (pedido explícito: "que guarde la última carpeta/
    categoría... así no tengo que volver a hacer toda la búsqueda")."""
    _settings().setValue(f"estado/{clave}", valor)


def restaurar_valor(clave: str, valor_por_defecto=None):
    valor = _settings().value(f"estado/{clave}", valor_por_defecto)
    return valor


def guardar_geometria_ventana(widget, nombre: str = "ventana_principal"):
    _settings().setValue(f"geometria/{nombre}", widget.saveGeometry())


def restaurar_geometria_ventana(widget, nombre: str = "ventana_principal", maximizar_si_es_nueva: bool = False):
    """Si `maximizar_si_es_nueva` es True y todavía NO hay geometría
    guardada para este `nombre` (primera vez que se abre en esta
    máquina/perfil — ej. una instalación nueva en otra PC), arranca
    maximizada en vez de confiar en el tamaño fijo por defecto del
    widget (que puede no entrar en la resolución real de esa pantalla,
    causando que la ventana "se vaya de ancho"). Con geometría YA
    guardada, se restaura esa igual que siempre — el chequeo de
    `_asegurar_dentro_de_pantalla` de abajo sigue cubriendo el caso de
    una geometría vieja que ya no entra en la pantalla actual."""
    valor = _settings().value(f"geometria/{nombre}")
    if valor:
        widget.restoreGeometry(valor)
    elif maximizar_si_es_nueva:
        widget.showMaximized()
    _asegurar_dentro_de_pantalla(widget)


def _asegurar_dentro_de_pantalla(widget):
    """Si la geometría (restaurada de una sesión anterior, quizás con
    otro monitor/resolución) queda parcial o totalmente fuera de la
    pantalla actual, la reacomoda para que entre entera. Esto es lo
    que causaba perder de vista los controles de la derecha al
    maximizar: la ventana arrancaba mal posicionada y el gestor de
    ventanas maximizaba en base a esa posición inválida.

    Bug real corregido — "la ventana maximizada vuelve a salirse de
    pantalla": si la sesión anterior se cerró CON la ventana
    maximizada, `restoreGeometry()` la restaura ya maximizada, y
    `frameGeometry()` en ese estado no es confiable para decidir si
    "entra" en la pantalla actual (además, mover una ventana
    maximizada con `setGeometry()` se comporta distinto según el
    gestor de ventanas — a veces la ignora, a veces la desmaximiza a
    medias). Ahora, si estaba maximizada, primero se restaura a
    tamaño normal (`showNormal()`), se corrige esa geometría normal
    contra la pantalla ACTUAL, y recién ahí se vuelve a maximizar
    (`showMaximized()`) — así el gestor de ventanas maximiza sobre
    coordenadas válidas de esta sesión, no sobre las que se guardaron
    la vez anterior (que podían ser de otro monitor/resolución)."""
    pantalla = widget.screen() or QApplication.primaryScreen()
    if pantalla is None:
        return

    disponible = pantalla.availableGeometry()
    estaba_maximizada = widget.isMaximized()
    if estaba_maximizada:
        widget.showNormal()

    geometria = widget.frameGeometry()

    if not disponible.contains(geometria):
        ancho = min(geometria.width(), disponible.width())
        alto = min(geometria.height(), disponible.height())
        # OJO: QRect.right()/.bottom() devuelven x+width-1 (no x+width), así
        # que el límite derecho/inferior válido es left()+width()-ancho, NO
        # right()-ancho (eso da un valor de más, corta la ventana 1px afuera
        # cuando ancho == disponible.width()).
        x = min(max(geometria.x(), disponible.left()), disponible.left() + disponible.width() - ancho)
        y = min(max(geometria.y(), disponible.top()), disponible.top() + disponible.height() - alto)
        widget.setGeometry(x, y, ancho, alto)

    if estaba_maximizada:
        widget.showMaximized()
