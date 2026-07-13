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

from PySide6.QtWidgets import QTreeWidget, QAbstractItemView, QHeaderView, QSlider, QStyle, QStyleOptionSlider
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl
from PySide6.QtGui import QDrag

from gui.styles import ROL_ESTADO_ITEM, ESTADO_REPRODUCIENDO


class SliderBusqueda(QSlider):
    """QSlider que salta DIRECTAMENTE a la posición clickeada en la
    barra — pedido explícito: "si hay clic más adelante, la barra y
    reproducción avance a ese momento", antes un click en el surco
    solo movía un 'page step' (comportamiento por defecto de Qt), no
    saltaba al punto exacto; solo arrastrar el mango adelantaba de
    verdad. Usado en la barra de progreso de Ventana 2 y en la del
    previo de Ventana 3."""

    def mousePressEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton:
            opcion = QStyleOptionSlider()
            self.initStyleOption(opcion)
            rect_mango = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opcion,
                QStyle.SubControl.SC_SliderHandle, self,
            )
            if not rect_mango.contains(evento.pos()):
                punto = evento.position().toPoint() if hasattr(evento, "position") else evento.pos()
                posicion = punto.x() if self.orientation() == Qt.Orientation.Horizontal else punto.y()
                largo = self.width() if self.orientation() == Qt.Orientation.Horizontal else self.height()
                valor = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), posicion, largo)
                self.setValue(valor)
        super().mousePressEvent(evento)


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
        if item_destino is None:
            item_destino = self._item_de_nivel_superior_mas_cercano(punto)

        rutas_validas = [ruta for ruta in rutas if ruta]
        for ruta in rutas_validas:
            self.archivo_soltado.emit(ruta, item_destino)
        if rutas_validas:
            self.archivos_soltados.emit(rutas_validas, item_destino)

        event.acceptProposedAction()

    def _item_de_nivel_superior_mas_cercano(self, punto):
        """Bug real corregido — "siempre lo ubica en el primer bloque,
        no me deja ponerlo donde yo quiera": si se soltó en un hueco
        vacío del árbol (`itemAt()` da None — algo muy común en un
        árbol jerárquico con bloques que tienen pocos ítems, la mayor
        parte del alto queda vacío), antes quien escuchaba
        `archivo_soltado` con `item_destino=None` caía siempre en un
        fallback fijo (el primer bloque). Ahora se resuelve acá,
        buscando el ítem de NIVEL SUPERIOR cuya fila está más cerca
        verticalmente del punto soltado — así soltar cerca del
        bloque 3 cae en el bloque 3, aunque el punto exacto no caiga
        sobre ninguna fila."""
        mejor_item = None
        mejor_distancia = None
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            centro_y = self.visualItemRect(item).center().y()
            distancia = abs(punto.y() - centro_y)
            if mejor_distancia is None or distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_item = item
        return mejor_item


class ArbolPublicidadConDrop(ArbolConDrop):
    """ArbolConDrop + tecla Enter para Ventana 1 (Publicidad) — mismo
    "robustez del sistema" ya usado en Ventana 2: Enter sobre una
    tanda seleccionada dispara la misma acción que el doble click
    (armar en rojo si está en silencio, encolar en verde si algo ya
    suena). Los nodos de bloque (sin ruta propia) no reaccionan."""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None and item.data(0, Qt.ItemDataRole.UserRole):
                self.itemDoubleClicked.emit(item, 0)
                return
        super().keyPressEvent(event)


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

    def startDrag(self, supportedActions):
        """Override necesario (bug real: "los ítems desaparecen" al
        reordenar). QAbstractItemView.startDrag(), al terminar un
        arrastre aceptado con MoveAction, borra las filas ORIGINALES
        del modelo salvo que dragDropMode sea InternalMove — pero acá
        también hace falta aceptar arrastres EXTERNOS (DragDrop, no
        InternalMove sólo), así que ese borrado automático se disparaba
        TAMBIÉN en la reordenada interna, después de que
        _reordenar_manual ya había reinsertado el ítem a mano: el
        resultado visible era que el ítem recién reordenado "desaparecía"
        de la lista. Haciendo el drag acá mismo, sin llamar a
        super().startDrag(), evitamos ese borrado automático posterior
        por completo — _reordenar_manual sigue siendo la única lógica
        que mueve ítems de posición."""
        item = self.currentItem()
        if item is None or item.parent() is not None:
            return
        if item.data(0, ROL_ESTADO_ITEM) == ESTADO_REPRODUCIENDO:
            # El ítem en el aire (rojo) no se puede mover mientras suena
            # — pedido explícito, se libera solo al elegir otro o al
            # terminar su reproducción.
            return
        indices = self.selectedIndexes()
        if not indices:
            return
        mime_data = self.model().mimeData(indices)
        if mime_data is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None and item.parent() is None:
                # Mismo camino que el doble click (PanelReproductor.
                # _on_doble_click_item -> GestorPlaylist._on_doble_click):
                # arma "en punta" (rojo) si está en silencio, o encola
                # (verde) si ya está sonando algo.
                self.itemDoubleClicked.emit(item, 0)
                return
        super().keyPressEvent(event)

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
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def startDrag(self, supportedActions):
        items = [item for item in self.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole)]
        if not items:
            return  # nada seleccionado, o son nodos de categoría sin ruta

        rutas = [item.data(0, Qt.ItemDataRole.UserRole) for item in items]
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(ruta) for ruta in rutas])
        mime_data.setText(rutas[0])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)
