"""
satelite/dialogo_insertar_item_aleatorio_remoto.py
--------------------------------------------------------
Insertar uno o más ítems Aleatorio en un bloque del Programador
remoto — mismo concepto que gui/dialogo_insertar_item_aleatorio.py de
la app principal (elige una categoría/subcategoría; el archivo real se
resuelve recién al reproducirse, nunca acá), acá con la lista de
categorías traída por RPC en vez de leerla del árbol vivo local.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox, QSpinBox,
    QDialogButtonBox, QMessageBox,
)

from satelite.utilidades import poblar_combo_categorias


class DialogoInsertarItemAleatorioRemoto(QDialog):
    def __init__(self, categorias: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ítem Aleatorio")
        self.setMinimumWidth(360)
        self._categorias = categorias
        self._resultado = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_categoria = QComboBox()
        poblar_combo_categorias(self.combo_categoria, categorias)
        form.addRow("Categoría:", self.combo_categoria)

        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        self.chk_recursivo.setChecked(True)
        form.addRow(self.chk_recursivo)

        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(1, 20)
        self.spin_cantidad.setValue(1)
        form.addRow("Cantidad a insertar:", self.spin_cantidad)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        if not categorias:
            botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _confirmar(self):
        if self.combo_categoria.count() == 0:
            QMessageBox.warning(self, "Ítem Aleatorio", "No hay ninguna categoría disponible.")
            return
        self._resultado = (
            self.combo_categoria.currentData(), self.chk_recursivo.isChecked(), self.spin_cantidad.value(),
        )
        self.accept()

    def resultado(self):
        """(categoria_ruta: list, recursivo: bool, cantidad: int), o None si se canceló."""
        return self._resultado
