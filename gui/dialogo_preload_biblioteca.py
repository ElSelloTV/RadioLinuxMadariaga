"""
gui/dialogo_preload_biblioteca.py
--------------------------------------------------------
Barra de preload GRÁFICA (pedido explícito: "podés agregar por favor
una barra gráfica de preload al inicio") — se muestra al arrancar la
app SOLO si hace falta migrar duraciones faltantes de la biblioteca
(ver VentanaExplorador.iniciar_migracion_duracion_al_arrancar). Con
una instalación ya migrada (el caso normal después del primer arranque
con esta ronda) esta ventana ni siquiera llega a mostrarse.

Generalizado (título/texto/nota configurables, con los mismos
defaults de siempre) para poder reutilizarse también en el reanálisis
de biblioteca en segundo plano (Configuración → Diagnóstico) — mismo
widget, sin duplicar una clase casi idéntica.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class DialogoPreloadBiblioteca(QDialog):
    def __init__(self, total: int, parent=None, titulo: str = "Preparando biblioteca",
                 texto: str = "Analizando archivos nuevos de la biblioteca...",
                 nota: str = "Se hace una sola vez por archivo — de acá en más, "
                              "explorar la biblioteca queda fluido."):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(380, 100)

        layout = QVBoxLayout(self)
        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setWordWrap(True)
        layout.addWidget(self.lbl_texto)

        self.barra = QProgressBar()
        self.barra.setRange(0, max(1, total))
        self.barra.setValue(0)
        self.barra.setTextVisible(True)
        self.barra.setFormat("%v / %m archivos")
        layout.addWidget(self.barra)

        self.lbl_nota = QLabel(nota)
        self.lbl_nota.setStyleSheet("color: #888; font-size: 8pt;")
        self.lbl_nota.setWordWrap(True)
        layout.addWidget(self.lbl_nota)

    def actualizar(self, hechos: int, total: int):
        if total != self.barra.maximum():
            self.barra.setRange(0, max(1, total))
        self.barra.setValue(hechos)

    def establecer_texto(self, texto: str):
        self.lbl_texto.setText(texto)
