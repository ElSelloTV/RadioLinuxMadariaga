"""
satelite/dialogo_bloque_horario.py
--------------------------------------------------------
Alta de un bloque horario nuevo (hora + título) para el Programador
remoto — equivalente chico de "＋ Añadir Bloque Horario" de la app
principal.
--------------------------------------------------------
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTimeEdit, QDialogButtonBox
from PySide6.QtCore import QTime


class DialogoBloqueHorario(QDialog):
    def __init__(self, hora_inicial: str = "00:00:00", titulo_inicial: str = "TANDA - Rotativa", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bloque horario")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.hora = QTimeEdit()
        self.hora.setDisplayFormat("HH:mm:ss")
        tiempo = QTime.fromString(hora_inicial, "HH:mm:ss")
        self.hora.setTime(tiempo if tiempo.isValid() else QTime(0, 0, 0))
        form.addRow("Hora:", self.hora)

        self.txt_titulo = QLineEdit(titulo_inicial)
        form.addRow("Título:", self.txt_titulo)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def resultado(self) -> dict:
        return {
            "hora": self.hora.time().toString("HH:mm:ss"),
            "titulo": self.txt_titulo.text().strip() or "TANDA - Rotativa",
        }
