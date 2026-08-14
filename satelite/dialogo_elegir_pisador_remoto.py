"""
satelite/dialogo_elegir_pisador_remoto.py
--------------------------------------------------------
Elegir un archivo ESPECÍFICO de género "Pisador" de la biblioteca
remota — usado por el Pisador de un ítem Específico/Aleatorio del
Musicalizador remoto. Mismo concepto que gui/dialogo_elegir_pisador.py
de la app principal (filtra por género "Pisador"), pero por RPC
(`listar_registros_por_genero`).
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, QLabel, QMessageBox,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto


class DialogoElegirPisadorRemoto(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir archivo de Pisador")
        self.setMinimumSize(380, 380)
        self._cliente = cliente

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Archivos de género \"Pisador\":"))
        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.lista, 1)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._cargar()

    def _cargar(self):
        try:
            registros = self._cliente.listar_registros_por_genero("Pisador")
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not registros:
            self.lista.addItem("(no hay archivos de género \"Pisador\" en la biblioteca)")
            return
        for registro in registros:
            texto = f"{registro['codigo']} — {registro['titulo']} ({registro['duracion']})"
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, registro)
            self.lista.addItem(item)

    def resultado(self):
        item = self.lista.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
