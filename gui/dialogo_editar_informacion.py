"""
gui/dialogo_editar_informacion.py
--------------------------------------------------------
Editar la INFORMACIÓN (título, artista, género, categoría) de un
material YA importado, sin tocar el archivo de audio ni volver a
analizarlo — pedido explícito: "agregá... que pueda editar la
información (cambiar nombre, etc.) a los archivos en el explorador".
Distinto de "🎚 Editar audio" (abre el editor de audio del sistema) y
de "⟲ Reemplazar" (cambia el archivo de audio en sí).
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel
from PySide6.QtCore import Qt

from gui.styles import LISTA_GENEROS


class DialogoEditarInformacion(QDialog):
    def __init__(self, registro: dict, tree_categorias, categoria_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar información")
        self.setMinimumWidth(420)
        self._tree_categorias = tree_categorias

        self._nombre_resultado = None
        self._artista_resultado = None
        self._genero_resultado = None
        self._item_categoria_resultado = None

        self._construir_ui(registro, categoria_actual)

    def _construir_ui(self, registro, categoria_actual):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        lbl_codigo = QLabel(registro.get("codigo", "—"))
        lbl_codigo.setObjectName("lblTituloBloqueActivo")
        form.addRow("Código (no cambia):", lbl_codigo)

        self.txt_nombre = QLineEdit(registro.get("titulo", ""))
        form.addRow("Nombre (editorial):", self.txt_nombre)

        self.txt_artista = QLineEdit(registro.get("artista", ""))
        form.addRow("Artista:", self.txt_artista)

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(LISTA_GENEROS)
        indice_genero = self.combo_genero.findText(registro.get("genero", ""))
        if indice_genero >= 0:
            self.combo_genero.setCurrentIndex(indice_genero)
        form.addRow("Género:", self.combo_genero)

        self.combo_categoria = QComboBox()
        self._poblar_categorias(categoria_actual)
        form.addRow("Categoría:", self.combo_categoria)

        layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _poblar_categorias(self, categoria_actual):
        """Mismo patrón que DialogoAgregarArchivo: recorre el árbol de
        categorías completo, sin límite de niveles, con sangría."""
        indice_actual = 0

        def recorrer(item_padre, profundidad):
            nonlocal indice_actual
            cantidad = item_padre.childCount() if item_padre else self._tree_categorias.topLevelItemCount()
            for i in range(cantidad):
                item = item_padre.child(i) if item_padre else self._tree_categorias.topLevelItem(i)
                etiqueta = ("　" * profundidad) + ("— " if profundidad else "") + item.text(0)
                self.combo_categoria.addItem(etiqueta, item)
                if item is categoria_actual:
                    indice_actual = self.combo_categoria.count() - 1
                recorrer(item, profundidad + 1)

        recorrer(None, 0)
        if self.combo_categoria.count() > 0:
            self.combo_categoria.setCurrentIndex(indice_actual)

    def _confirmar(self):
        self._nombre_resultado = self.txt_nombre.text().strip() or "Sin título"
        self._artista_resultado = self.txt_artista.text().strip()
        self._genero_resultado = self.combo_genero.currentText()
        self._item_categoria_resultado = self.combo_categoria.currentData()
        self.accept()

    def resultado(self) -> dict | None:
        if self._item_categoria_resultado is None:
            return None
        return {
            "titulo": self._nombre_resultado,
            "artista": self._artista_resultado,
            "genero": self._genero_resultado,
            "item_categoria": self._item_categoria_resultado,
        }
