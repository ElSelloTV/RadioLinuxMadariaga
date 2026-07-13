"""
gui/dialogo_editar_bloque.py
--------------------------------------------------------
Diálogo chico para "Reemplazar" un bloque horario del Programador
(pedido explícito): editar su hora y su título sin tener que borrarlo
y crear uno nuevo desde cero (lo que perdería los ítems ya cargados
adentro).
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QFormLayout, QVBoxLayout, QTimeEdit, QLineEdit, QDialogButtonBox
from PySide6.QtCore import QTime


class DialogoEditarBloque(QDialog):
    def __init__(self, hora_actual: str, titulo_actual: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar bloque horario")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.time_hora = QTimeEdit(QTime.fromString(hora_actual, "HH:mm:ss") or QTime.currentTime())
        form.addRow("Hora:", self.time_hora)

        self.txt_titulo = QLineEdit(titulo_actual)
        form.addRow("Título:", self.txt_titulo)

        layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def hora(self) -> str:
        return self.time_hora.time().toString("HH:mm:ss")

    def titulo(self) -> str:
        return self.txt_titulo.text().strip() or "Bloque sin título"
