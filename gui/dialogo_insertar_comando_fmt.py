"""
gui/dialogo_insertar_comando_fmt.py
--------------------------------------------------------
Insertar un Comando FMT en un bloque de Publicidad (o del Programador)
— pedido explícito: en vez del flujo de Dinesat (crear el comando
escribiendo "FMT Folclore" a mano, con riesgo real de error de
tipeo), se elige de una lista de formatos YA CREADOS en el
Musicalizador Avanzado. Nunca queda un comando "huérfano" apuntando a
un nombre que no existe.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLabel, QDialogButtonBox

from config.settings import listar_formatos


class DialogoInsertarComandoFMT(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Comando FMT")
        self.setMinimumWidth(360)
        self._formato_elegido = None

        layout = QVBoxLayout(self)
        formatos = listar_formatos()
        if not formatos:
            layout.addWidget(QLabel(
                "Todavía no hay ningún formato creado en el Musicalizador\n"
                "Avanzado. Creá uno primero (menú Programación → 🎵 Musicalizador)."
            ))
        else:
            layout.addWidget(QLabel(
                "Al llegar la reproducción a este comando, se dispara la\n"
                "generación continua de música en Emisión según el formato elegido:"
            ))
            self.combo_formato = QComboBox()
            self.combo_formato.addItems(formatos)
            layout.addWidget(self.combo_formato)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        if not formatos:
            botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _confirmar(self):
        self._formato_elegido = self.combo_formato.currentText()
        self.accept()

    def formato_elegido(self) -> str | None:
        return self._formato_elegido
