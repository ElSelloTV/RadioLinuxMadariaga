"""
gui/dialogo_insertar_comando_hth.py
--------------------------------------------------------
Insertar un Comando HTH (Hora-Temperatura-Humedad, terminología real
de Dinesat — ver core/hth.py) en un bloque de Publicidad (o del
Programador). A diferencia del Comando FMT (que lista formatos ya
creados en el Musicalizador), acá los 3 tipos son fijos y siempre
existen — no hace falta "crear" nada antes, solo elegir cuál insertar.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLabel, QDialogButtonBox

DESCRIPCION_POR_TIPO = {
    "HORA": "Anuncia la hora actual (\"Es la hora... catorce... treinta\").",
    "TEMPERATURA": "Anuncia la temperatura actual en vivo (Open-Meteo).",
    "HUMEDAD": "Anuncia la humedad actual en vivo (Open-Meteo).",
}


class DialogoInsertarComandoHTH(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Comando HTH")
        self.setMinimumWidth(360)
        self._parametro_elegido = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Al llegar la reproducción a este comando, concatena y\n"
            "reproduce los clips de voz correspondientes (género \"HTH\"\n"
            "en el Explorador). Si falta algún clip, o no se pudo obtener\n"
            "el clima, el comando se saltea sin sonar nada."
        ))

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(list(DESCRIPCION_POR_TIPO.keys()))
        self.combo_tipo.currentTextChanged.connect(self._actualizar_descripcion)
        layout.addWidget(self.combo_tipo)

        self.lbl_descripcion = QLabel()
        self.lbl_descripcion.setWordWrap(True)
        layout.addWidget(self.lbl_descripcion)
        self._actualizar_descripcion(self.combo_tipo.currentText())

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _actualizar_descripcion(self, tipo: str):
        self.lbl_descripcion.setText(DESCRIPCION_POR_TIPO.get(tipo, ""))

    def _confirmar(self):
        self._parametro_elegido = self.combo_tipo.currentText()
        self.accept()

    def parametro_elegido(self) -> str | None:
        return self._parametro_elegido
