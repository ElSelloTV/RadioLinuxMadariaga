"""
gui/dialogo_duplicar_programacion.py
--------------------------------------------------------
"Duplicar para otro día" del Programador de Emisión (pedido
explícito): guardar el contenido ACTUAL del editor bajo un nombre y
un día/fecha NUEVOS, sin tocar la programación de la que partió —
las dos subsisten. Es el mismo dato de bloques, solo cambia dónde se
guarda (una fecha específica nueva, o uno o varios días de la semana
nuevos) — nunca pisa la fecha/día de origen salvo que el operador
elija deliberadamente la misma.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox, QDateEdit,
    QLabel, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate

from config.settings import DIAS_SEMANA_ETIQUETAS


class DialogoDuplicarProgramacion(QDialog):
    def __init__(self, nombre_sugerido: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicar para otro día")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Se va a guardar una COPIA de lo que está cargado ahora en el editor,\n"
            "bajo un nombre y un día/fecha nuevos. La programación original no se toca."
        ))

        self.txt_nombre = QLineEdit(nombre_sugerido)
        self.txt_nombre.setPlaceholderText("Nombre de la nueva programación")
        layout.addWidget(self.txt_nombre)

        fila_fecha = QHBoxLayout()
        self.chk_fecha_especifica = QCheckBox("Fecha específica:")
        self.date_especifica = QDateEdit(QDate.currentDate())
        self.date_especifica.setCalendarPopup(True)
        self.date_especifica.setEnabled(False)
        self.chk_fecha_especifica.toggled.connect(self._on_toggle_fecha)
        fila_fecha.addWidget(self.chk_fecha_especifica)
        fila_fecha.addWidget(self.date_especifica)
        layout.addLayout(fila_fecha)

        layout.addWidget(QLabel("...o días de la semana (patrón general):"))
        fila_dias = QHBoxLayout()
        self.checks_dias = {}
        for clave, etiqueta in DIAS_SEMANA_ETIQUETAS:
            chk = QCheckBox(etiqueta)
            self.checks_dias[clave] = chk
            fila_dias.addWidget(chk)
        layout.addLayout(fila_dias)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._nombre_resultado = None
        self._fecha_resultado = None
        self._dias_resultado = []

    def _on_toggle_fecha(self, activo: bool):
        self.date_especifica.setEnabled(activo)
        for chk in self.checks_dias.values():
            chk.setEnabled(not activo)

    def _confirmar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Duplicar", "Ingresá un nombre para la nueva programación.")
            return

        fecha = None
        dias = []
        if self.chk_fecha_especifica.isChecked():
            fecha = self.date_especifica.date().toString("yyyy-MM-dd")
        else:
            dias = [clave for clave, chk in self.checks_dias.items() if chk.isChecked()]

        if not fecha and not dias:
            QMessageBox.warning(self, "Duplicar", "Elegí una fecha específica o al menos un día de la semana.")
            return

        self._nombre_resultado = nombre
        self._fecha_resultado = fecha
        self._dias_resultado = dias
        self.accept()

    def resultado(self):
        """(nombre, fecha_especifica_o_None, [dias_semana]) — None si se canceló."""
        if self._nombre_resultado is None:
            return None
        return self._nombre_resultado, self._fecha_resultado, self._dias_resultado
