"""
satelite/dialogo_ciclo_fmt_remoto.py
--------------------------------------------------------
Agregar un ciclo FMT por tiempo a Ventana 2/Emisión, remoto — pedido
explícito: "en la ventana 2 pueda también cargar x cantidad de tiempo
de FMT". Mismo concepto que gui/dialogo_ciclo_fmt_por_tiempo.py
(elegir un formato YA CREADO del Musicalizador Avanzado + cantidad de
minutos), pero la lista de formatos se trae por RPC en vez de leerla
directo del disco — este proceso no tiene acceso al filesystem de la
radio.
--------------------------------------------------------
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel, QDialogButtonBox


class DialogoCicloFMTRemoto(QDialog):
    def __init__(self, formatos: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar ciclo FMT por tiempo (Ventana 2)")
        self.setMinimumWidth(360)
        self._resultado = None

        layout = QVBoxLayout(self)
        if not formatos:
            layout.addWidget(QLabel(
                "Todavía no hay ningún formato creado en el Musicalizador\n"
                "Avanzado — creá uno primero (botón \"🎵 Musicalizador\")."
            ))
        else:
            layout.addWidget(QLabel(
                "Genera un ciclo de este formato y lo agrega al final de lo que\n"
                "ya está cargado en Emisión (nunca borra lo existente)."
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
