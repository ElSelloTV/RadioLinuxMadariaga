"""
gui/common_widgets.py
--------------------------------------------------------
Widgets reutilizables de Drag & Drop.

IMPORTANTE (bug corregido): los manejadores de eventos de Qt
(dragEnterEvent, dropEvent, startDrag) son métodos VIRTUALES de
C++. Para que Qt realmente los invoque, tienen que estar
reimplementados a nivel de CLASE (subclase real), nunca asignados
como atributo de instancia (ej. `self.widget.dropEvent = mi_func`).
Esa asignación por instancia es la razón por la que el arrastre
de la Ventana 3 hacia la 1 y la 2 no funcionaba: quedaba
"seteada" en Python pero Qt jamás la llamaba desde C++.

Estas dos clases son ahora el único lugar donde vive esa lógica;
el resto de la GUI las usa por composición.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QTreeWidget, QAbstractItemView, QHeaderView
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl, QDateTime
from PySide6.QtGui import QDrag


def configurar_columnas_ajustables(tree: QTreeWidget, anchos_iniciales: list):
    """Deja todas las columnas redimensionables a mano (Interactive) y
    la ÚLTIMA columna en modo Stretch: así, si el usuario agranda una
    columna de la izquierda, la última se va achicando de forma
    fluida pero SIN desaparecer tapada — nunca queda oculta del todo.

    `anchos_iniciales` fija el ancho de arranque de cada columna
    salvo la última (que la controla el Stretch).
    """
    header = tree.header()
    total_columnas = tree.columnCount()
    for i in range(total_columnas):
        if i == total_columnas - 1:
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            if i < len(anchos_iniciales):
                tree.setColumnWidth(i, anchos_iniciales[i])
    header.setStretchLastSection(True)


class ArbolConDrop(QTreeWidget):
    """QTreeWidget que ACEPTA arrastres soltados (DropOnly) desde otra ventana.

    Emite archivo_soltado(ruta, item_destino) UNA VEZ POR ARCHIVO
    (compatibilidad con quien solo agrega de a uno), y además
    archivos_soltados(lista_de_rutas, item_destino) con el LOTE
    completo de una sola vez — la usa el Explorador para poder
    importar/mover varios archivos arrastrados juntos con un solo
    diálogo en vez de uno por archivo. item_destino puede ser None si
    se soltó fuera de cualquier fila (se interpreta como "al final de
    la lista" / "en el último bloque").
    """

    archivo_soltado = Signal(str, object)
    archivos_soltados = Signal(list, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        rutas = []
        if event.mimeData().hasUrls():
            rutas = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        elif event.mimeData().hasText():
            rutas = [event.mimeData().text()]

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)

        rutas_validas = [ruta for ruta in rutas if ruta]
        for ruta in rutas_validas:
            self.archivo_soltado.emit(ruta, item_destino)
        if rutas_validas:
            self.archivos_soltados.emit(rutas_validas, item_destino)

        event.acceptProposedAction()


class ArbolReproductorConDrop(QTreeWidget):
    """QTreeWidget de una lista de reproducción (Ventana 2 / Auxiliar):
    combina DOS comportamientos de Drag&Drop a la vez —
    - ACEPTA arrastres externos (desde el Explorador) para agregar
      temas, igual que ArbolConDrop.
    - Permite REORDENAR sus propios ítems (temas de nivel superior)
      arrastrándolos arriba/abajo dentro de la misma lista.

    La distinción se hace en dropEvent() mirando event.source(): si
    el arrastre viene de este mismo árbol, es una reordenada interna;
    si viene de otro lado, es un archivo externo (se emite
    archivo_soltado).

    IMPORTANTE: la reordenada interna NO usa el dropEvent nativo de
    QTreeWidget (super().dropEvent) — ese comportamiento nativo, si
    se suelta justo "sobre" otro ítem (en vez de entre dos filas),
    lo anida como HIJO del ítem destino. Acá eso está prohibido a
    propósito: anidar (el ícono "↳" tabulado) es EXCLUSIVO del motor
    de Pisador (gui/panel_reproductor.py - agregar_pisador), nunca
    un efecto secundario de reordenar arrastrando. _reordenar_manual
    calcula la posición a mano y siempre reinserta como hermano de
    nivel superior (si el tema tenía su propio Pisador anidado, viaja
    con él intacto — takeTopLevelItem preserva el subárbol).
    """

    archivo_soltado = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() is self:
            self._reordenar_manual(event)
            return

        rutas = []
        if event.mimeData().hasUrls():
            rutas = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        elif event.mimeData().hasText():
            rutas = [event.mimeData().text()]

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)

        for ruta in rutas:
            if ruta:
                self.archivo_soltado.emit(ruta, item_destino)

        event.acceptProposedAction()

    def _reordenar_manual(self, event):
        """Mueve el ítem arrastrado (self.currentItem()) a la posición
        soltada, SIEMPRE como hermano de nivel superior — nunca lo
        anida como hijo de otro, sin importar dónde exactamente caiga
        el cursor sobre la fila destino."""
        if len(self.selectedItems()) > 1:
            # Con selección múltiple, reordenar "un poco cada uno" da
            # un resultado confuso — se pide seleccionar un solo tema
            # para reordenar (la selección múltiple sigue sirviendo
            # para arrastrar VARIOS hacia otra ventana, o para
            # Quitar/Eliminar en lote desde el menú contextual).
            event.ignore()
            return

        item_arrastrado = self.currentItem()
        if item_arrastrado is None or item_arrastrado.parent() is not None:
            # Un Pisador anidado no se arrastra (ya no tiene
            # ItemIsDragEnabled); esto es un resguardo extra.
            event.ignore()
            return

        indice_origen = self.indexOfTopLevelItem(item_arrastrado)
        if indice_origen < 0:
            event.ignore()
            return

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)

        if item_destino is None:
            indice_destino = self.topLevelItemCount() - 1
        else:
            bloque_destino = item_destino
            while bloque_destino.parent() is not None:
                bloque_destino = bloque_destino.parent()
            indice_destino = self.indexOfTopLevelItem(bloque_destino)
            if self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem:
                indice_destino += 1

        if indice_destino > indice_origen:
            indice_destino -= 1  # se saca el origen antes de reinsertar, los índices posteriores corren uno

        indice_destino = max(0, min(indice_destino, self.topLevelItemCount() - 1))

        if indice_destino == indice_origen:
            event.ignore()
            return

        item = self.takeTopLevelItem(indice_origen)  # se lleva su Pisador anidado, si tenía
        self.insertTopLevelItem(indice_destino, item)
        self.setCurrentItem(item)
        event.acceptProposedAction()


class ArbolOrigenArrastre(QTreeWidget):
    """QTreeWidget que ES ORIGEN de arrastre (DragOnly) hacia otras ventanas.

    Solo los ítems con una ruta física guardada en
    Qt.ItemDataRole.UserRole (columna 0) se pueden arrastrar; los
    nodos de categoría (sin ruta) simplemente no inician drag. Con
    selección múltiple activa, arrastra TODOS los seleccionados de
    una vez (varios archivos en el mismo mimeData) — quien reciba el
    drop en la otra punta ya recorre la lista completa.

    Registra CUÁNDO fue el último arrastre (acaba_de_arrastrar) para
    que quien escuche itemDoubleClicked pueda ignorar un "doble click"
    que en realidad es el resto de un gesto de arrastre — pedido
    explícito: la preescucha ("Previo") se disparaba sola al arrastrar
    seguido hacia otras ventanas.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self._ultimo_arrastre_ms = 0

    def startDrag(self, supportedActions):
        items = [item for item in self.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole)]
        if not items:
            return  # nada seleccionado, o son nodos de categoría sin ruta

        self._ultimo_arrastre_ms = QDateTime.currentMSecsSinceEpoch()

        rutas = [item.data(0, Qt.ItemDataRole.UserRole) for item in items]
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(ruta) for ruta in rutas])
        mime_data.setText(rutas[0])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

    def acaba_de_arrastrar(self, margen_ms: int = 400) -> bool:
        return (QDateTime.currentMSecsSinceEpoch() - self._ultimo_arrastre_ms) < margen_ms
