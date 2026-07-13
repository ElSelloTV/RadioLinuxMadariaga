"""
gui/dialogo_seleccionar_biblioteca.py
--------------------------------------------------------
Buscador de biblioteca a dos columnas (minimalista, mismo concepto
que Ventana 3 - Explorador): izquierda las CATEGORÍAS (recursivo,
sin límite de niveles), derecha los ARCHIVOS de la categoría
seleccionada. Pedido explícito del Programador de Emisión: "debería
existir una opción clara para añadir ítem... donde pueda navegar por
categorías y dentro de ellas, el ítem que deseo agregar".

No depende de tener la Ventana 3 abierta ni de arrastrar nada: lee
directamente el árbol de categorías YA CARGADO en memoria
(ventana_explorador.tree_categorias), así siempre está sincronizado
con lo último que haya en la biblioteca sin tener que releer el disco.

`permitir_multiple=True` (por defecto, para "Añadir Ítem" — se puede
elegir varios archivos de una sola vez) o `False` (para "Reemplazar
Ítem" — un único archivo reemplaza al seleccionado).

`categoria_inicial` (lista de nombres desde la raíz) preselecciona y
expande esa categoría al abrir — lo usa VentanaProgramador para
recordar la última categoría navegada (pedido explícito, punto f).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QLabel, QDialogButtonBox, QAbstractItemView, QWidget
)
from PySide6.QtCore import Qt

ROL_ARCHIVOS_CATEGORIA = Qt.ItemDataRole.UserRole + 1
ROL_REGISTRO_PICKER = Qt.ItemDataRole.UserRole + 1


class DialogoSeleccionarBiblioteca(QDialog):
    def __init__(self, tree_categorias_origen, permitir_multiple: bool = True,
                 categoria_inicial: list = None, titulo: str = "Seleccionar de la biblioteca",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumSize(680, 420)
        self._permitir_multiple = permitir_multiple
        self._registros_elegidos = []
        self._ruta_categoria_actual = []
        self._construir_ui()
        self._poblar_categorias(tree_categorias_origen)
        if categoria_inicial:
            self._seleccionar_ruta_categoria(categoria_inicial)

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        panel_categorias = QWidget()
        layout_categorias = QVBoxLayout(panel_categorias)
        layout_categorias.setContentsMargins(0, 0, 0, 0)
        layout_categorias.addWidget(QLabel("Categorías"))
        self.tree_categorias = QTreeWidget()
        self.tree_categorias.setHeaderHidden(True)
        self.tree_categorias.currentItemChanged.connect(self._on_categoria_seleccionada)
        layout_categorias.addWidget(self.tree_categorias)
        splitter.addWidget(panel_categorias)

        panel_archivos = QWidget()
        layout_archivos = QVBoxLayout(panel_archivos)
        layout_archivos.setContentsMargins(0, 0, 0, 0)
        etiqueta = "Archivos (elegí uno o varios con Ctrl/Shift)" if self._permitir_multiple else "Archivos"
        layout_archivos.addWidget(QLabel(etiqueta))
        self.tree_archivos = QTreeWidget()
        self.tree_archivos.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree_archivos.setColumnCount(3)
        modo = QAbstractItemView.SelectionMode.ExtendedSelection if self._permitir_multiple \
            else QAbstractItemView.SelectionMode.SingleSelection
        self.tree_archivos.setSelectionMode(modo)
        self.tree_archivos.itemSelectionChanged.connect(self._actualizar_boton_ok)
        self.tree_archivos.itemDoubleClicked.connect(self._on_doble_click_archivo)
        layout_archivos.addWidget(self.tree_archivos)
        splitter.addWidget(panel_archivos)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        self.lbl_vacio = QLabel(
            "Todavía no hay nada cargado en el Explorador (Ventana 3).\n"
            "Agregá archivos ahí primero."
        )
        self.lbl_vacio.setVisible(False)
        layout.addWidget(self.lbl_vacio)

        self.botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botones.accepted.connect(self._confirmar)
        self.botones.rejected.connect(self.reject)
        layout.addWidget(self.botones)
        self._actualizar_boton_ok()

    # ------------------------------------------------------------------
    def _poblar_categorias(self, tree_origen):
        """Copia la ESTRUCTURA del árbol de categorías vivo del
        Explorador (nombre + lista de archivos de cada categoría) a un
        árbol propio — nunca reparenta los QTreeWidgetItem originales
        (un ítem solo puede pertenecer a un QTreeWidget a la vez)."""
        if tree_origen is None or tree_origen.topLevelItemCount() == 0:
            self.lbl_vacio.setVisible(True)
            self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return

        from gui.ventana_explorador import ROL_ARCHIVOS

        def copiar(item_origen, item_padre_nuevo):
            nodo = QTreeWidgetItem([item_origen.text(0)])
            archivos = list(item_origen.data(0, ROL_ARCHIVOS) or [])
            nodo.setData(0, ROL_ARCHIVOS_CATEGORIA, archivos)
            if item_padre_nuevo is None:
                self.tree_categorias.addTopLevelItem(nodo)
            else:
                item_padre_nuevo.addChild(nodo)
            for i in range(item_origen.childCount()):
                copiar(item_origen.child(i), nodo)
            return nodo

        for i in range(tree_origen.topLevelItemCount()):
            copiar(tree_origen.topLevelItem(i), None)

        if self.tree_categorias.topLevelItemCount() > 0:
            self.tree_categorias.setCurrentItem(self.tree_categorias.topLevelItem(0))

    def _seleccionar_ruta_categoria(self, ruta: list):
        """Expande y selecciona la categoría cuyo camino de nombres
        (desde la raíz) coincide con `ruta` — usado para recordar la
        última categoría navegada entre usos del diálogo."""
        actual_padre = None
        item_encontrado = None
        for nombre in ruta:
            cantidad = actual_padre.childCount() if actual_padre else self.tree_categorias.topLevelItemCount()
            candidato = None
            for i in range(cantidad):
                item = actual_padre.child(i) if actual_padre else self.tree_categorias.topLevelItem(i)
                if item.text(0) == nombre:
                    candidato = item
                    break
            if candidato is None:
                break
            if actual_padre is not None:
                actual_padre.setExpanded(True)
            actual_padre = candidato
            item_encontrado = candidato
        if item_encontrado is not None:
            self.tree_categorias.setCurrentItem(item_encontrado)

    # ------------------------------------------------------------------
    def _on_categoria_seleccionada(self, item, _anterior):
        self.tree_archivos.clear()
        if item is None:
            self._ruta_categoria_actual = []
            return

        ruta = []
        nodo = item
        while nodo is not None:
            ruta.insert(0, nodo.text(0))
            nodo = nodo.parent()
        self._ruta_categoria_actual = ruta

        archivos = item.data(0, ROL_ARCHIVOS_CATEGORIA) or []
        for registro in archivos:
            fila = QTreeWidgetItem([
                registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
            ])
            fila.setData(0, ROL_REGISTRO_PICKER, registro)
            self.tree_archivos.addTopLevelItem(fila)
        self._actualizar_boton_ok()

    def _on_doble_click_archivo(self, _item, _columna):
        if not self._permitir_multiple:
            self._confirmar()

    def _actualizar_boton_ok(self):
        habilitado = len(self.tree_archivos.selectedItems()) > 0
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(habilitado)

    # ------------------------------------------------------------------
    def _confirmar(self):
        seleccionados = self.tree_archivos.selectedItems()
        if not seleccionados:
            return
        self._registros_elegidos = [item.data(0, ROL_REGISTRO_PICKER) for item in seleccionados]
        self.accept()

    def registros_elegidos(self) -> list:
        return self._registros_elegidos

    def registro_elegido(self) -> dict | None:
        return self._registros_elegidos[0] if self._registros_elegidos else None

    def ruta_categoria_seleccionada(self) -> list:
        return self._ruta_categoria_actual
