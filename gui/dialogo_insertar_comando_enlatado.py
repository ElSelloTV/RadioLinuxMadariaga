"""
gui/dialogo_insertar_comando_enlatado.py
--------------------------------------------------------
Insertar un Comando ENLATADO (1 a 5) en un bloque de Publicidad (o del
Programador) — pedido explícito: "programas 'enlatados' que se cargan
semanalmente... el comando ENLATADO pondrá solamente en reproducción
el último archivo cargado en la categoría ya configurada". A
diferencia del Comando FMT (lista formatos ya creados en el
Musicalizador) o HTH (3 tipos fijos), acá los 5 slots son siempre los
mismos números — cada uno se CONFIGURA aparte, en Configuración →
Enlatados, con la categoría que le corresponde. Este diálogo solo
elige CUÁL de los 5 insertar, mostrando de un vistazo la categoría ya
asignada a cada uno (o el aviso de que todavía no se configuró).
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLabel, QDialogButtonBox

from config.settings import cargar_configuracion, categoria_de_enlatado

NUMEROS_ENLATADO = ["1", "2", "3", "4", "5"]


class DialogoInsertarComandoEnlatado(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Comando ENLATADO")
        self.setMinimumWidth(400)
        self._parametro_elegido = None
        self._config = cargar_configuracion()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Al llegar la reproducción a este comando, reproduce el\n"
            "ÚLTIMO archivo cargado en la categoría configurada para\n"
            "ese ENLATADO (Configuración → Enlatados). Terminado, sigue\n"
            "directo con lo que haya después en el bloque. Si el\n"
            "ENLATADO no está configurado, o su categoría está vacía,\n"
            "se saltea sin sonar nada."
        ))

        self.combo_numero = QComboBox()
        for numero in NUMEROS_ENLATADO:
            self.combo_numero.addItem(f"ENLATADO {numero}", numero)
        self.combo_numero.currentIndexChanged.connect(self._actualizar_descripcion)
        layout.addWidget(self.combo_numero)

        self.lbl_categoria = QLabel()
        self.lbl_categoria.setWordWrap(True)
        layout.addWidget(self.lbl_categoria)
        self._actualizar_descripcion()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _actualizar_descripcion(self, *_args):
        numero = self.combo_numero.currentData()
        ruta = categoria_de_enlatado(self._config, numero) if numero else None
        if ruta:
            self.lbl_categoria.setText("Categoría configurada: " + " / ".join(ruta))
        else:
            self.lbl_categoria.setText(
                "⚠ Todavía sin configurar — andá a Configuración → Enlatados\n"
                "y elegí una categoría antes de usar este comando."
            )

    def _confirmar(self):
        self._parametro_elegido = self.combo_numero.currentData()
        self.accept()

    def parametro_elegido(self) -> str | None:
        return self._parametro_elegido
