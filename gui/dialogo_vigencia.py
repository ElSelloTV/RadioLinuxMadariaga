"""
gui/dialogo_vigencia.py
--------------------------------------------------------
Diálogo chico para editar la vigencia de fecha de un material ya
importado (pedido explícito, inspirado en Dinesat: un archivo, ej.
una tanda publicitaria, puede dejar de emitirse solo a partir de una
fecha, sin que el operador tenga que sacarlo a mano). Mismo patrón de
checkbox + QDateEdit que ya usa gui/dialogo_duplicar_programacion.py.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QDateEdit, QDialogButtonBox
)
from PySide6.QtCore import QDate


class DialogoVigencia(QDialog):
    def __init__(self, titulo_material: str, fecha_inicio: str = None, fecha_fin: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vigencia de fecha")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"'{titulo_material}'\n\n"
            "Sin marcar ninguna fecha, el material se emite siempre (sin\n"
            "restricción) — igual que hasta ahora."
        ))

        fila_inicio = QHBoxLayout()
        self.chk_inicio = QCheckBox("Empieza a emitirse el:")
        self.date_inicio = QDateEdit(QDate.fromString(fecha_inicio, "yyyy-MM-dd") if fecha_inicio else QDate.currentDate())
        self.date_inicio.setCalendarPopup(True)
        self.chk_inicio.setChecked(bool(fecha_inicio))
        self.date_inicio.setEnabled(bool(fecha_inicio))
        self.chk_inicio.toggled.connect(self.date_inicio.setEnabled)
        fila_inicio.addWidget(self.chk_inicio)
        fila_inicio.addWidget(self.date_inicio)
        layout.addLayout(fila_inicio)

        fila_fin = QHBoxLayout()
        self.chk_fin = QCheckBox("Deja de emitirse el:")
        self.date_fin = QDateEdit(QDate.fromString(fecha_fin, "yyyy-MM-dd") if fecha_fin else QDate.currentDate())
        self.date_fin.setCalendarPopup(True)
        self.chk_fin.setChecked(bool(fecha_fin))
        self.date_fin.setEnabled(bool(fecha_fin))
        self.chk_fin.toggled.connect(self.date_fin.setEnabled)
        fila_fin.addWidget(self.chk_fin)
        fila_fin.addWidget(self.date_fin)
        layout.addLayout(fila_fin)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def resultado(self) -> tuple:
        """(fecha_inicio_o_None, fecha_fin_o_None) en formato ISO."""
        fecha_inicio = self.date_inicio.date().toString("yyyy-MM-dd") if self.chk_inicio.isChecked() else None
        fecha_fin = self.date_fin.date().toString("yyyy-MM-dd") if self.chk_fin.isChecked() else None
        return fecha_inicio, fecha_fin
