"""
satelite/dialogo_elegir_registro_biblioteca.py
--------------------------------------------------------
Elegir UN archivo ya existente en la biblioteca remota (por categoría)
— usado por el Programador remoto ("agregar ítem") y por el tipo
"Específico" del Musicalizador remoto. Mismo concepto que
`gui/dialogo_seleccionar_biblioteca.py` de la app principal, pero sin
árbol de categorías vivo — combo indentado (misma lista plana que ya
usa el diálogo de subida) + lista de archivos de esa categoría,
refrescada por RPC (`listar_registros_categoria`) cada vez que cambia
la categoría o el checkbox "incluir subcategorías".
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QListWidget,
    QListWidgetItem, QDialogButtonBox, QLabel, QMessageBox,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.utilidades import poblar_combo_categorias


class DialogoElegirRegistroBiblioteca(QDialog):
    def __init__(self, cliente, categorias: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir archivo de la biblioteca")
        self.setMinimumSize(420, 420)
        self._cliente = cliente

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria = QComboBox()
        poblar_combo_categorias(self.combo_categoria, categorias)
        layout.addWidget(self.combo_categoria)

        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        layout.addWidget(self.chk_recursivo)

        layout.addWidget(QLabel("Archivos:"))
        self.lista_archivos = QListWidget()
        layout.addWidget(self.lista_archivos, 1)

        self.combo_categoria.currentIndexChanged.connect(self._refrescar_archivos)
        self.chk_recursivo.toggled.connect(self._refrescar_archivos)
        self.lista_archivos.itemDoubleClicked.connect(self.accept)

        fila_botones = QHBoxLayout()
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        fila_botones.addWidget(botones)
        layout.addLayout(fila_botones)

        if self.combo_categoria.count() > 0:
            self._refrescar_archivos()

    def _refrescar_archivos(self):
        self.lista_archivos.clear()
        ruta = self.combo_categoria.currentData()
        if not ruta:
            return
        try:
            registros = self._cliente.listar_registros_categoria(ruta, self.chk_recursivo.isChecked())
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        for registro in registros:
            texto = f"{registro['codigo']} — {registro['titulo']} ({registro['duracion']})"
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, registro)
            self.lista_archivos.addItem(item)

    def resultado(self):
        item = self.lista_archivos.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
