"""
satelite/dialogo_seleccionar_categoria_remoto.py
--------------------------------------------------------
Elegir SOLO una categoría (sin archivos) de la biblioteca remota — la
lista plana ya llegó por RPC (`listar_categorias`), así que este
diálogo es puramente local: un combo indentado + OK/Cancel. Usado por
el Pisador (Categoría) del Musicalizador remoto — mismo concepto que
gui/dialogo_seleccionar_categoria.py de la app principal.
--------------------------------------------------------
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel

from satelite.utilidades import poblar_combo_categorias


class DialogoSeleccionarCategoriaRemoto(QDialog):
    def __init__(self, categorias: list, titulo: str = "Elegir categoría", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(360)
        self._resultado = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Categoría:"))
        self.combo = QComboBox()
        poblar_combo_categorias(self.combo, categorias)
        layout.addWidget(self.combo)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        if self.combo.count() == 0:
            botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _confirmar(self):
        self._resultado = self.combo.currentData()
        self.accept()

    def resultado(self):
        """La ruta (list[str]) elegida, o None si se canceló."""
        return self._resultado
