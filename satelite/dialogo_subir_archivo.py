"""
satelite/dialogo_subir_archivo.py
--------------------------------------------------------
Diálogo de alta para la app satélite — mismos CAMPOS que
`gui/dialogo_agregar_archivo.py` (nombre editorial, artista, género,
categoría), pero SIN depender de un `tree_categorias` vivo (un
QTreeWidgetItem real no puede cruzar a otro proceso) — arma el combo
de categoría indentado a partir de la lista PLANA que devuelve
`ClienteControlRemoto.listar_categorias()`
(`[{"ruta": [...], "nivel": N}, ...]`) en vez de recorrer un árbol.
--------------------------------------------------------
"""
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel,
)


class DialogoSubirArchivo(QDialog):
    def __init__(self, ruta_local: str, categorias: list, generos: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subir a la biblioteca (remoto)")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        lbl_archivo = QLabel(os.path.basename(ruta_local))
        form.addRow("Archivo local:", lbl_archivo)

        self.txt_nombre = QLineEdit(os.path.splitext(os.path.basename(ruta_local))[0])
        form.addRow("Nombre (editorial):", self.txt_nombre)

        self.txt_artista = QLineEdit()
        form.addRow("Artista:", self.txt_artista)

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(generos)
        form.addRow("Género:", self.combo_genero)

        self.combo_categoria = QComboBox()
        for categoria in categorias:
            sangria = "    " * max(0, categoria["nivel"] - 1)
            self.combo_categoria.addItem(f"{sangria}{categoria['ruta'][-1]}", categoria["ruta"])
        form.addRow("Categoría:", self.combo_categoria)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._resultado = None

    def _confirmar(self):
        if self.combo_categoria.count() == 0:
            self.reject()
            return
        self._resultado = {
            "titulo": self.txt_nombre.text().strip() or "Sin título",
            "artista": self.txt_artista.text().strip(),
            "genero": self.combo_genero.currentText(),
            "categoria_ruta": self.combo_categoria.currentData(),
        }
        self.accept()

    def resultado(self):
        return self._resultado
