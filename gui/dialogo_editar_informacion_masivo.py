"""
gui/dialogo_editar_informacion_masivo.py
--------------------------------------------------------
Editar información en LOTE, sobre varios archivos seleccionados a la
vez en Ventana 3 (Explorador) — pedido explícito: "cuando hago
selección múltiple, me gustaría poder editar masivamente... Editar
Información (todos, menos el nombre, poder darle la categoría)".

A diferencia de gui/dialogo_editar_informacion.py (un solo archivo,
edita también el título/nombre editorial), acá el título NUNCA se
toca — cada archivo conserva el suyo — y cada campo (Artista/Género/
Categoría) tiene su propio checkbox "Cambiar a": sin tildar, ese campo
queda intacto en todos los seleccionados; tildado, se aplica el mismo
valor a TODOS de una. Con el checkbox de Artista tildado y el campo
vacío, se limpia el artista de todos (una elección explícita, distinta
de no tocar nada).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QLineEdit,
    QComboBox, QDialogButtonBox,
)

from gui.styles import LISTA_GENEROS


class DialogoEditarInformacionMasivo(QDialog):
    def __init__(self, cantidad: int, tree_categorias, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar información (varios archivos)")
        self.setMinimumWidth(420)
        self._tree_categorias = tree_categorias

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Editando {cantidad} archivo(s) seleccionados.\n"
            "El título/nombre de cada uno NO cambia — solo se aplican\n"
            "los campos que tildes acá, con el mismo valor para todos."
        ))

        fila_artista = QHBoxLayout()
        self.chk_artista = QCheckBox("Cambiar Artista a:")
        self.txt_artista = QLineEdit()
        self.txt_artista.setEnabled(False)
        self.chk_artista.toggled.connect(self.txt_artista.setEnabled)
        fila_artista.addWidget(self.chk_artista)
        fila_artista.addWidget(self.txt_artista)
        layout.addLayout(fila_artista)

        fila_genero = QHBoxLayout()
        self.chk_genero = QCheckBox("Cambiar Género a:")
        self.combo_genero = QComboBox()
        self.combo_genero.addItems(LISTA_GENEROS)
        self.combo_genero.setEnabled(False)
        self.chk_genero.toggled.connect(self.combo_genero.setEnabled)
        fila_genero.addWidget(self.chk_genero)
        fila_genero.addWidget(self.combo_genero)
        layout.addLayout(fila_genero)

        fila_categoria = QHBoxLayout()
        self.chk_categoria = QCheckBox("Mover todos a la categoría:")
        self.combo_categoria = QComboBox()
        self.combo_categoria.setEnabled(False)
        self.chk_categoria.toggled.connect(self.combo_categoria.setEnabled)
        self._poblar_categorias()
        fila_categoria.addWidget(self.chk_categoria)
        fila_categoria.addWidget(self.combo_categoria)
        layout.addLayout(fila_categoria)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _poblar_categorias(self):
        """Mismo patrón que DialogoEditarInformacion/DialogoAgregarArchivo:
        recorre el árbol de categorías completo, sin límite de niveles,
        con sangría — acá no hay "categoría actual" (cada archivo puede
        venir de una distinta), así que arranca en la primera."""
        def recorrer(item_padre, profundidad):
            cantidad = item_padre.childCount() if item_padre else self._tree_categorias.topLevelItemCount()
            for i in range(cantidad):
                item = item_padre.child(i) if item_padre else self._tree_categorias.topLevelItem(i)
                etiqueta = ("　" * profundidad) + ("— " if profundidad else "") + item.text(0)
                self.combo_categoria.addItem(etiqueta, item)
                recorrer(item, profundidad + 1)

        recorrer(None, 0)

    def resultado(self) -> dict:
        """Cada clave es el valor a aplicar, o None si ese campo no se
        tildó (no tocar). `item_categoria` es el QTreeWidgetItem
        elegido, o None."""
        return {
            "artista": self.txt_artista.text().strip() if self.chk_artista.isChecked() else None,
            "genero": self.combo_genero.currentText() if self.chk_genero.isChecked() else None,
            "item_categoria": self.combo_categoria.currentData() if self.chk_categoria.isChecked() else None,
        }
