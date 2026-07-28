"""
gui/dialogo_ciclo_fmt_por_tiempo.py
--------------------------------------------------------
Pedido explícito ("agregá un menú contextual en Emisión para que
pueda agregar una x cantidad de tiempo, de programación aleatoria
FMT... me pregunta en una misma ventana emergente el FMT que deseo y
la cantidad de tiempo"): mismo patrón que
gui/dialogo_insertar_comando_fmt.py (elegir de una lista de formatos
YA CREADOS, nunca texto libre) más un campo de minutos.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel, QDialogButtonBox

from config.settings import listar_formatos


class DialogoCicloFMTPorTiempo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar ciclo FMT por tiempo")
        self.setMinimumWidth(360)
        self._resultado = None

        layout = QVBoxLayout(self)
        formatos = listar_formatos()
        if not formatos:
            layout.addWidget(QLabel(
                "Todavía no hay ningún formato creado en el Musicalizador\n"
                "Avanzado. Creá uno primero (menú Programación → 🎵 Musicalizador)."
            ))
        else:
            layout.addWidget(QLabel(
                "Genera un ciclo de este formato y lo agrega al final de lo que\n"
                "ya está cargado en Emisión (nunca borra lo existente) -- misma\n"
                "generación que dispara un Comando FMT real."
            ))
            form = QFormLayout()
            self.combo_formato = QComboBox()
            self.combo_formato.addItems(formatos)
            form.addRow("Formato:", self.combo_formato)

            self.spin_minutos = QSpinBox()
            self.spin_minutos.setRange(1, 600)
            self.spin_minutos.setValue(30)
            self.spin_minutos.setSuffix(" min")
            form.addRow("Cantidad de tiempo:", self.spin_minutos)
            layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        if not formatos:
            botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _confirmar(self):
        self._resultado = (self.combo_formato.currentText(), self.spin_minutos.value())
        self.accept()

    def resultado(self):
        """(nombre_formato, minutos) elegidos, o None si se canceló."""
        return self._resultado
