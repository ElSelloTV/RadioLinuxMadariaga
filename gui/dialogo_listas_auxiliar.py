"""
gui/dialogo_listas_auxiliar.py
--------------------------------------------------------
"Cargar lista guardada" del Reproductor Auxiliar (pedido explícito):
un único diálogo que lista las listas ya guardadas con nombre
(config/settings.py: listar_listas_auxiliares) y permite CARGAR una
(reemplaza lo que esté en el Auxiliar) o BORRARLA de ahí mismo — el
propio pedido de Santiago fue explícito en que el borrado tiene que
estar en el mismo diálogo de carga, no en un lugar aparte. La
confirmación de "esto reemplaza/borra algo" la pide quien use el
resultado de este diálogo (gui/main_window.py), no acá — este widget
solo resuelve la selección.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QDialogButtonBox, QLabel, QPushButton, QAbstractItemView
)
from PySide6.QtCore import Qt


class DialogoListasAuxiliar(QDialog):
    def __init__(self, nombres: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Listas guardadas del Auxiliar")
        self.setMinimumSize(360, 320)
        self._nombre_a_cargar = None
        self._nombre_a_borrar = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Elegí una lista guardada:"))

        self.lista = QListWidget()
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for nombre in nombres:
            item = QListWidgetItem(nombre)
            item.setData(Qt.ItemDataRole.UserRole, nombre)
            self.lista.addItem(item)
        if self.lista.count() > 0:
            self.lista.setCurrentRow(0)
        self.lista.itemSelectionChanged.connect(self._actualizar_botones)
        self.lista.itemDoubleClicked.connect(lambda _item: self._cargar())
        layout.addWidget(self.lista)

        fila_botones = QHBoxLayout()
        self.btn_borrar = QPushButton("🗑 Borrar")
        self.btn_borrar.clicked.connect(self._borrar)
        fila_botones.addWidget(self.btn_borrar)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setText("📂 Cargar")
        self.botones.accepted.connect(self._cargar)
        self.botones.rejected.connect(self.reject)
        layout.addWidget(self.botones)

        self._actualizar_botones()

    def _actualizar_botones(self):
        hay_seleccion = len(self.lista.selectedItems()) > 0
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(hay_seleccion)
        self.btn_borrar.setEnabled(hay_seleccion)

    def _cargar(self):
        seleccionados = self.lista.selectedItems()
        if not seleccionados:
            return
        self._nombre_a_cargar = seleccionados[0].data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _borrar(self):
        seleccionados = self.lista.selectedItems()
        if not seleccionados:
            return
        self._nombre_a_borrar = seleccionados[0].data(Qt.ItemDataRole.UserRole)
        self.done(2)  # código propio: "se pidió borrar", distinto de Ok/Cancel

    def nombre_a_cargar(self):
        return self._nombre_a_cargar

    def nombre_a_borrar(self):
        return self._nombre_a_borrar
