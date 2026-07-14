"""
gui/dialogo_elegir_pisador.py
--------------------------------------------------------
Diálogo para elegir, de entre los archivos de género "Pisador"
cargados en la biblioteca (Ventana 3 - Explorador), cuál se va a
superponer sobre el inicio del tema musical seleccionado en
Emisión / Auxiliar. Solo se le ofrecen registros de género
Pisador — es el propio menú "Agregar Pisador" de la Ventana 2/
Auxiliar quien pide esta lista ya filtrada.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, QLabel,
    QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt


class DialogoElegirPisador(QDialog):
    def __init__(self, registros: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Pisador")
        self.setMinimumWidth(380)
        self._registro_elegido = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Elegí el Pisador que se va a superponer al tema:"))

        self.lista = QListWidget()
        for registro in registros:
            texto = f"{registro.get('titulo', '(sin título)')}  —  {registro.get('codigo', '')}"
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, registro)
            self.lista.addItem(item)
        if self.lista.count() > 0:
            self.lista.setCurrentRow(0)
        layout.addWidget(self.lista)

        # Posición (pedido explícito, paridad con Dinesat): al INICIO
        # (comportamiento de siempre) o al FINAL, sobre el outro.
        layout.addWidget(QLabel("Se dispara:"))
        self.radio_inicio = QRadioButton("Al empezar el tema (Intro)")
        self.radio_final = QRadioButton("Al terminar el tema (Outro)")
        self.radio_inicio.setChecked(True)
        grupo = QButtonGroup(self)
        grupo.addButton(self.radio_inicio)
        grupo.addButton(self.radio_final)
        layout.addWidget(self.radio_inicio)
        layout.addWidget(self.radio_final)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _confirmar(self):
        item = self.lista.currentItem()
        if item is None:
            self.reject()
            return
        self._registro_elegido = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def registro_elegido(self) -> dict | None:
        return self._registro_elegido

    def posicion_elegida(self) -> str:
        return "final" if self.radio_final.isChecked() else "inicio"
