"""
satelite/dialogo_guardar_programacion.py
--------------------------------------------------------
Guardar la programación editada — nombre + uno o varios días de la
semana y/o una fecha específica, mismo criterio que
`config.settings.guardar_programacion()` (una programación puede
guardarse para varios días genéricos Y una fecha puntual a la vez).
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QCheckBox,
    QGroupBox, QDateEdit, QDialogButtonBox, QMessageBox,
)
from PySide6.QtCore import QDate

from satelite.utilidades import NOMBRES_DIAS_SEMANA, ETIQUETAS_DIAS_SEMANA


class DialogoGuardarProgramacion(QDialog):
    def __init__(self, nombre_inicial: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guardar programación")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.txt_nombre = QLineEdit(nombre_inicial)
        form.addRow("Nombre:", self.txt_nombre)
        layout.addLayout(form)

        grupo_dias = QGroupBox("Días de la semana (opcional)")
        layout_dias = QHBoxLayout(grupo_dias)
        self._checks_dias = []
        for etiqueta in ETIQUETAS_DIAS_SEMANA:
            chk = QCheckBox(etiqueta[:3])
            chk.setToolTip(etiqueta)
            layout_dias.addWidget(chk)
            self._checks_dias.append(chk)
        layout.addWidget(grupo_dias)

        self.chk_fecha_especifica = QCheckBox("Fecha específica (opcional)")
        layout.addWidget(self.chk_fecha_especifica)
        self.fecha = QDateEdit(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setEnabled(False)
        self.chk_fecha_especifica.toggled.connect(self.fecha.setEnabled)
        layout.addWidget(self.fecha)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._resultado = None

    def _confirmar(self):
        nombre = self.txt_nombre.text().strip()
        dias_semana = [NOMBRES_DIAS_SEMANA[i] for i, chk in enumerate(self._checks_dias) if chk.isChecked()]
        fecha_especifica = self.fecha.date().toString("yyyy-MM-dd") if self.chk_fecha_especifica.isChecked() else None
        if not nombre:
            QMessageBox.warning(self, "Guardar programación", "Ponele un nombre.")
            return
        if not dias_semana and not fecha_especifica:
            QMessageBox.warning(
                self, "Guardar programación",
                "Elegí al menos un día de la semana o tildá una fecha específica.",
            )
            return
        self._resultado = {"nombre": nombre, "dias_semana": dias_semana, "fecha_especifica": fecha_especifica}
        self.accept()

    def resultado(self):
        return self._resultado
