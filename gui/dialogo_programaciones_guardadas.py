"""
gui/dialogo_programaciones_guardadas.py
--------------------------------------------------------
Lista de programaciones YA GUARDADAS en disco (por día genérico o por
fecha específica) — un único diálogo reutilizado para dos acciones
distintas del Programador de Emisión, diferenciadas explícitamente
del resto (pedido explícito: "diferenciar bien lo que es cargar,
editar, eliminar... la programación"):

- Cargar (permitir_multiple=False): elegís UNA para traerla al editor.
- Eliminar varias (permitir_multiple=True): selección múltiple para
  limpiar de una programaciones viejas que ya no sirven.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox,
    QLabel, QAbstractItemView
)
from PySide6.QtCore import Qt


class DialogoProgramacionesGuardadas(QDialog):
    def __init__(self, disponibles: list, permitir_multiple: bool = False,
                 titulo: str = "Programaciones guardadas",
                 texto_ayuda: str = "Elegí una programación:", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumSize(420, 360)
        self._seleccionados = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(texto_ayuda))

        self.lista = QListWidget()
        modo = QAbstractItemView.SelectionMode.ExtendedSelection if permitir_multiple \
            else QAbstractItemView.SelectionMode.SingleSelection
        self.lista.setSelectionMode(modo)
        for tipo, clave, nombre in disponibles:
            prefijo = f"Día: {clave}" if tipo == "dia" else f"Fecha: {clave}"
            item = QListWidgetItem(f"{prefijo}  —  {nombre}")
            item.setData(Qt.ItemDataRole.UserRole, (tipo, clave, nombre))
            self.lista.addItem(item)
        if self.lista.count() > 0 and not permitir_multiple:
            self.lista.setCurrentRow(0)
        self.lista.itemSelectionChanged.connect(self._actualizar_boton_ok)
        layout.addWidget(self.lista)

        self.botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botones.accepted.connect(self._confirmar)
        self.botones.rejected.connect(self.reject)
        layout.addWidget(self.botones)
        self._actualizar_boton_ok()

    def _actualizar_boton_ok(self):
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            len(self.lista.selectedItems()) > 0
        )

    def _confirmar(self):
        seleccionados = self.lista.selectedItems()
        if not seleccionados:
            return
        self._seleccionados = [item.data(Qt.ItemDataRole.UserRole) for item in seleccionados]
        self.accept()

    def seleccionados(self) -> list:
        """[(tipo, clave, nombre), ...] — uno o varios según permitir_multiple."""
        return self._seleccionados
