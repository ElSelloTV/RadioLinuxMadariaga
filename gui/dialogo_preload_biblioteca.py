"""
gui/dialogo_preload_biblioteca.py
--------------------------------------------------------
Barra de preload GRÁFICA (pedido explícito: "podés agregar por favor
una barra gráfica de preload al inicio") — se muestra al arrancar la
app SOLO si hace falta migrar duraciones faltantes de la biblioteca
(ver VentanaExplorador.iniciar_migracion_duracion_al_arrancar). Con
una instalación ya migrada (el caso normal después del primer arranque
con esta ronda) esta ventana ni siquiera llega a mostrarse.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class DialogoPreloadBiblioteca(QDialog):
    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preparando biblioteca")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(380, 100)

        layout = QVBoxLayout(self)
        self.lbl_texto = QLabel("Analizando archivos nuevos de la biblioteca...")
        self.lbl_texto.setWordWrap(True)
        layout.addWidget(self.lbl_texto)

        self.barra = QProgressBar()
        self.barra.setRange(0, max(1, total))
        self.barra.setValue(0)
        self.barra.setTextVisible(True)
        self.barra.setFormat("%v / %m archivos")
        layout.addWidget(self.barra)

        self.lbl_nota = QLabel(
            "Se hace una sola vez por archivo — de acá en más, "
            "explorar la biblioteca queda fluido."
        )
        self.lbl_nota.setStyleSheet("color: #888; font-size: 8pt;")
        self.lbl_nota.setWordWrap(True)
        layout.addWidget(self.lbl_nota)

    def actualizar(self, hechos: int, total: int):
        if total != self.barra.maximum():
            self.barra.setRange(0, max(1, total))
        self.barra.setValue(hechos)
