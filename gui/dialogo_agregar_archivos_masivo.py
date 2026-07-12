"""
gui/dialogo_agregar_archivos_masivo.py
--------------------------------------------------------
Diálogo para importar VARIOS archivos de audio a la biblioteca de
una sola vez (selección múltiple en "＋ Agregar", o arrastrar muchos
archivos juntos desde el explorador de archivos del sistema): un
único diálogo para todo el lote — se elige una categoría y un
género que se aplican a TODOS los archivos, el título de cada uno
sale del nombre de archivo (editable después, uno por uno, desde
"Reemplazar" si hace falta corregirlo). Pensado para cargar de
golpe, no para revisar archivo por archivo.
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QListWidget,
    QDialogButtonBox, QLabel
)

from gui.styles import LISTA_GENEROS


class DialogoAgregarArchivosMasivo(QDialog):
    def __init__(self, rutas: list, tree_categorias, categoria_sugerida=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Agregar {len(rutas)} archivos a la biblioteca")
        self.setMinimumWidth(440)
        self._rutas = rutas
        self._tree_categorias = tree_categorias

        self._genero_resultado = None
        self._item_categoria_resultado = None

        self._construir_ui(categoria_sugerida)

    # ------------------------------------------------------------------
    def _construir_ui(self, categoria_sugerida):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Se van a agregar {len(self._rutas)} archivos:"))
        lista = QListWidget()
        lista.addItems([os.path.basename(ruta) for ruta in self._rutas])
        lista.setMaximumHeight(140)
        lista.setEnabled(False)  # solo de referencia, no es editable acá
        layout.addWidget(lista)

        form = QFormLayout()

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(LISTA_GENEROS)
        form.addRow("Género para todos:", self.combo_genero)

        self.combo_categoria = QComboBox()
        self._poblar_categorias(categoria_sugerida)
        form.addRow("Categoría para todos:", self.combo_categoria)

        layout.addLayout(form)

        nota = QLabel(
            "El título de cada archivo sale del nombre del archivo\n"
            "(se puede corregir después, uno por uno, con Reemplazar)."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        layout.addWidget(nota)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    # ------------------------------------------------------------------
    def _poblar_categorias(self, categoria_sugerida):
        """Recorre el árbol de categorías completo (sin límite de
        niveles) y arma un combo con sangría según profundidad —
        mismo patrón que DialogoAgregarArchivo."""
        indice_sugerido = 0

        def recorrer(item_padre, profundidad):
            nonlocal indice_sugerido
            cantidad = item_padre.childCount() if item_padre else self._tree_categorias.topLevelItemCount()
            for i in range(cantidad):
                item = item_padre.child(i) if item_padre else self._tree_categorias.topLevelItem(i)
                etiqueta = ("　" * profundidad) + ("— " if profundidad else "") + item.text(0)
                self.combo_categoria.addItem(etiqueta, item)
                if item is categoria_sugerida:
                    indice_sugerido = self.combo_categoria.count() - 1
                recorrer(item, profundidad + 1)

        recorrer(None, 0)
        if self.combo_categoria.count() > 0:
            self.combo_categoria.setCurrentIndex(indice_sugerido)

    # ------------------------------------------------------------------
    def _confirmar(self):
        self._genero_resultado = self.combo_genero.currentText()
        self._item_categoria_resultado = self.combo_categoria.currentData()
        self.accept()

    def resultado(self) -> dict | None:
        """None si se canceló; si no, {"genero", "item_categoria"}
        a aplicar sobre todos los archivos del lote."""
        if self._item_categoria_resultado is None:
            return None
        return {"genero": self._genero_resultado, "item_categoria": self._item_categoria_resultado}
