"""
gui/dialogo_seleccionar_categoria.py
--------------------------------------------------------
Selector de UNA categoría (sin elegir archivo) — a diferencia de
gui/dialogo_seleccionar_biblioteca.py (que exige elegir un archivo
puntual), este diálogo se usa donde hace falta apuntar a una
CATEGORÍA completa: el ítem "Aleatorio" del Musicalizador Avanzado
(elige un tema al azar de esa categoría en cada generación) y la
categoría de Pisadores de un ítem del Musicalizador.

Mismo patrón que DialogoSeleccionarBiblioteca: copia la ESTRUCTURA del
árbol de categorías vivo del Explorador, nunca reparenta los
QTreeWidgetItem originales.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QDialogButtonBox


class DialogoSeleccionarCategoria(QDialog):
    def __init__(self, tree_categorias_origen, categoria_inicial: list = None,
                 titulo: str = "Elegir categoría", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumSize(360, 420)
        self._ruta_elegida = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Categorías (incluye subcategorías):"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._actualizar_boton_ok)
        self.tree.itemDoubleClicked.connect(lambda _item, _col: self._confirmar())
        layout.addWidget(self.tree)

        self.lbl_vacio = QLabel("Todavía no hay categorías cargadas en el Explorador (Ventana 3).")
        self.lbl_vacio.setVisible(False)
        layout.addWidget(self.lbl_vacio)

        self.botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botones.accepted.connect(self._confirmar)
        self.botones.rejected.connect(self.reject)
        layout.addWidget(self.botones)

        self._poblar(tree_categorias_origen)
        if categoria_inicial:
            self._seleccionar_ruta(categoria_inicial)
        self._actualizar_boton_ok()

    def _poblar(self, tree_origen):
        if tree_origen is None or tree_origen.topLevelItemCount() == 0:
            self.lbl_vacio.setVisible(True)
            return

        def copiar(item_origen, item_padre_nuevo):
            nodo = QTreeWidgetItem([item_origen.text(0)])
            if item_padre_nuevo is None:
                self.tree.addTopLevelItem(nodo)
            else:
                item_padre_nuevo.addChild(nodo)
            for i in range(item_origen.childCount()):
                copiar(item_origen.child(i), nodo)

        for i in range(tree_origen.topLevelItemCount()):
            copiar(tree_origen.topLevelItem(i), None)
        self.tree.expandAll()

    def _seleccionar_ruta(self, ruta: list):
        actual_padre = None
        item_encontrado = None
        for nombre in ruta:
            cantidad = actual_padre.childCount() if actual_padre else self.tree.topLevelItemCount()
            candidato = None
            for i in range(cantidad):
                item = actual_padre.child(i) if actual_padre else self.tree.topLevelItem(i)
                if item.text(0) == nombre:
                    candidato = item
                    break
            if candidato is None:
                break
            actual_padre = candidato
            item_encontrado = candidato
        if item_encontrado is not None:
            self.tree.setCurrentItem(item_encontrado)

    def _actualizar_boton_ok(self):
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.tree.currentItem() is not None
        )

    def _confirmar(self):
        item = self.tree.currentItem()
        if item is None:
            return
        ruta = []
        nodo = item
        while nodo is not None:
            ruta.insert(0, nodo.text(0))
            nodo = nodo.parent()
        self._ruta_elegida = ruta
        self.accept()

    def ruta_elegida(self) -> list | None:
        return self._ruta_elegida
