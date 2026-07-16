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

from PySide6.QtWidgets import (
    QTreeWidget, QAbstractItemView, QHeaderView, QSlider, QStyle, QStyleOptionSlider,
    QStyledItemDelegate, QStyleOptionViewItem,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl
from PySide6.QtGui import QDrag

from gui.styles import ROL_ESTADO_ITEM, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE, COLOR_SELECCION


class DelegadoConservaColorEstado(QStyledItemDelegate):
    """Pedido explícito (paridad Dinesat, regla PERMANENTE): el rojo
    (en punta) y el verde (en cola) de un ítem NUNCA deben cambiar al
    seleccionarlo — ni con relleno celeste ni con ningún borde, "sin
    tapar el verde y rojo que son fundamentales". Con QSS puro esto no
    se puede lograr: la regla ::item:selected no puede "preguntar" si
    el ítem tiene un color propio, así que terminaba pisando igual el
    rojo/verde (bug real reportado en una ronda anterior). Acá, si el
    ítem está en rojo/verde Y seleccionado, se pinta SIN el flag de
    selección — así conserva su propio color de fondo intacto, sin
    ninguna decoración extra — cualquier otro ítem sigue el camino
    normal (QSS de siempre: relleno celeste + letra negra)."""

    def paint(self, painter, option, index):
        indice_columna_0 = index.sibling(index.row(), 0)
        estado = indice_columna_0.data(ROL_ESTADO_ITEM)
        if estado in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE) and bool(option.state & QStyle.StateFlag.State_Selected):
            opcion = QStyleOptionViewItem(option)
            opcion.state &= ~QStyle.StateFlag.State_Selected
            super().paint(painter, opcion, index)
        else:
            super().paint(painter, option, index)


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
    suena). Los nodos de bloque (sin ruta propia) no reaccionan.

    Pedido explícito ("arrastrar y soltar de la ventana 1 al
    reproductor Auxiliar"): además de ACEPTAR arrastres (heredado de
    ArbolConDrop), este árbol ahora también es ORIGEN de arrastre —
    exporta la ruta del ítem seleccionado con el mismo protocolo
    (QUrl) que ya usa ArbolOrigenArrastre del Explorador, así quien
    reciba el drop (la Auxiliar) lo procesa exactamente igual que un
    archivo arrastrado desde Ventana 3, sin código nuevo del lado
    receptor. El alcance a "solo Auxiliar, nunca Ventana 2" se
    resuelve del lado RECEPTOR — ver ArbolReproductorConDrop.
    acepta_desde_publicidad más abajo — porque V2 y Auxiliar comparten
    la MISMA clase de árbol.

    Pedido explícito (ronda posterior): "ordená el arrastre y mover de
    los ítems, no lo puedo hacer, y los FMT tampoco me permite
    arrastrarlo" — el reordenado interno estaba deliberadamente
    deshabilitado desde el diseño original ("Nunca hubo reordenado
    interno pedido para Ventana 1"), pero Santiago sí lo quiere ahora.
    Mismo patrón jerárquico (bloque -> tandas/comandos) que
    ArbolProgramadorConDrop: un ítem se reordena DENTRO de su bloque o
    se mueve a OTRO bloque, siempre como hijo de nivel 1 — nunca los
    bloques enteros. Los Comandos (FMT/HTH, sin ruta real) se
    reordenan igual que una tanda; simplemente no viajan en el
    `QUrl` del mimeData (no tiene sentido exportarlos a la Auxiliar).
    El ítem "en punta" (rojo) no se puede mover mientras suena — mismo
    criterio que ya usa Ventana 2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(DelegadoConservaColorEstado(self))
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None and item.data(0, Qt.ItemDataRole.UserRole):
                self.itemDoubleClicked.emit(item, 0)
                return
        super().keyPressEvent(event)

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
        super().dropEvent(event)

    def startDrag(self, supportedActions):
        """Un solo gesto de arrastre soporta DOS destinos: (1)
        reordenar DENTRO de este mismo árbol (tandas Y Comandos), y
        (2) exportar hacia la Auxiliar (selección múltiple, pedido
        explícito de una ronda anterior — solo los ítems con ruta
        real viajan como QUrl, un Comando no tiene sentido allá). Los
        nodos de bloque se descartan de la selección en vez de
        cancelar todo el arrastre."""
        seleccionados = [item for item in self.selectedItems() if item.parent() is not None]
        if not seleccionados:
            return
        if any(item.data(0, ROL_ESTADO_ITEM) == ESTADO_REPRODUCIENDO for item in seleccionados):
            # El ítem en el aire (rojo) no se puede mover mientras
            # suena — pedido explícito, mismo criterio que Ventana 2.
            return

        indices = self.selectedIndexes()
        mime_data = self.model().mimeData(indices) if indices else None
        if mime_data is None:
            mime_data = QMimeData()

        rutas = [
            item.data(0, Qt.ItemDataRole.UserRole) for item in seleccionados
            if item.data(0, Qt.ItemDataRole.UserRole)
        ]
        if rutas:
            mime_data.setUrls([QUrl.fromLocalFile(ruta) for ruta in rutas])
            mime_data.setText(rutas[0])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def _reordenar_manual(self, event):
        """Mueve el ítem arrastrado a la posición soltada — DENTRO de
        su propio bloque, o a OTRO bloque distinto, siempre como hijo
        de nivel 1 (nunca lo anida más profundo). Mismo algoritmo que
        ArbolProgramadorConDrop._reordenar_manual (misma forma de
        árbol: bloque -> ítems)."""
        if len(self.selectedItems()) > 1:
            event.ignore()
            return

        item_arrastrado = self.currentItem()
        if item_arrastrado is None or item_arrastrado.parent() is None:
            event.ignore()
            return
        if item_arrastrado.data(0, ROL_ESTADO_ITEM) == ESTADO_REPRODUCIENDO:
            event.ignore()
            return

        bloque_origen = item_arrastrado.parent()
        indice_origen = bloque_origen.indexOfChild(item_arrastrado)
        if indice_origen < 0:
            event.ignore()
            return

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)

        if item_destino is None:
            bloque_destino = self._item_de_nivel_superior_mas_cercano(punto)
            if bloque_destino is None:
                event.ignore()
                return
            indice_destino = bloque_destino.childCount()
        elif item_destino.parent() is None:
            # Soltado sobre el TÍTULO de un bloque -> al final de ESE bloque.
            bloque_destino = item_destino
            indice_destino = bloque_destino.childCount()
        else:
            bloque_destino = item_destino.parent()
            indice_destino = bloque_destino.indexOfChild(item_destino)
            if self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem:
                indice_destino += 1

        if bloque_destino is bloque_origen:
            if indice_destino > indice_origen:
                indice_destino -= 1  # se saca el origen antes de reinsertar
            indice_destino = max(0, min(indice_destino, bloque_origen.childCount() - 1))
            if indice_destino == indice_origen:
                event.ignore()
                return
        else:
            indice_destino = max(0, min(indice_destino, bloque_destino.childCount()))

        item = bloque_origen.takeChild(indice_origen)
        bloque_destino.insertChild(indice_destino, item)
        bloque_destino.setExpanded(True)
        self.setCurrentItem(item)
        event.acceptProposedAction()


class ArbolProgramadorConDrop(ArbolConDrop):
    """ArbolConDrop + reordenar ítems arrastrando (pedido explícito,
    Ventana Programador: "que pueda arrastrar/modificar el orden de
    los ítems, ya que actualmente cuando se agrega uno, lo hace al
    final y no le puedo cambiar de orden"). A diferencia de
    `ArbolReproductorConDrop` (lista plana, Ventana 2), acá el árbol
    es jerárquico (bloque -> tandas) — solo los ÍTEMS (hijos) se
    arrastran, nunca los bloques enteros; un ítem se puede reordenar
    DENTRO de su bloque o moverlo a OTRO bloque, siempre como hijo de
    nivel 1 (nunca se anida más profundo).

    Mismo patrón que ArbolReproductorConDrop para evitar el bug real
    ya documentado ("los ítems desaparecen" al reordenar): startDrag()
    propio, sin llamar a super().startDrag(), porque dragDropMode=
    DragDrop (no InternalMove, hace falta para seguir aceptando
    arrastres externos del Explorador) borraría la fila original
    apenas termina un MoveAction aceptado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

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
        super().dropEvent(event)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None or item.parent() is None:
            return  # solo se arrastran ítems (tandas/comandos), nunca bloques enteros
        indices = self.selectedIndexes()
        if not indices:
            return
        mime_data = self.model().mimeData(indices)
        if mime_data is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def _reordenar_manual(self, event):
        """Mueve el ítem arrastrado a la posición soltada — DENTRO de
        su propio bloque, o a OTRO bloque distinto, siempre como hijo
        de nivel 1 (nunca lo anida más profundo, sin importar dónde
        caiga exactamente el cursor)."""
        if len(self.selectedItems()) > 1:
            event.ignore()
            return

        item_arrastrado = self.currentItem()
        if item_arrastrado is None or item_arrastrado.parent() is None:
            event.ignore()
            return

        bloque_origen = item_arrastrado.parent()
        indice_origen = bloque_origen.indexOfChild(item_arrastrado)
        if indice_origen < 0:
            event.ignore()
            return

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)

        if item_destino is None:
            bloque_destino = self._item_de_nivel_superior_mas_cercano(punto)
            if bloque_destino is None:
                event.ignore()
                return
            indice_destino = bloque_destino.childCount()
        elif item_destino.parent() is None:
            # Soltado sobre el TÍTULO de un bloque -> al final de ESE bloque.
            bloque_destino = item_destino
            indice_destino = bloque_destino.childCount()
        else:
            bloque_destino = item_destino.parent()
            indice_destino = bloque_destino.indexOfChild(item_destino)
            if self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem:
                indice_destino += 1

        if bloque_destino is bloque_origen:
            if indice_destino > indice_origen:
                indice_destino -= 1  # se saca el origen antes de reinsertar
            indice_destino = max(0, min(indice_destino, bloque_origen.childCount() - 1))
            if indice_destino == indice_origen:
                event.ignore()
                return
        else:
            indice_destino = max(0, min(indice_destino, bloque_destino.childCount()))

        item = bloque_origen.takeChild(indice_origen)
        bloque_destino.insertChild(indice_destino, item)
        bloque_destino.setExpanded(True)
        self.setCurrentItem(item)
        event.acceptProposedAction()


class ArbolCategoriasConDrop(ArbolConDrop):
    """ArbolConDrop + reordenar CATEGORÍAS por arrastre (pedido
    explícito: "permití también que pueda ordenar las carpetas de las
    categorías"). Alcance acotado a propósito: reordena una categoría
    ENTRE SUS HERMANAS (mismo padre — nivel superior o una
    subcategoría anidada) arriba/abajo; mover una categoría a OTRO
    padre (re-anidarla bajo una categoría distinta) es una operación
    mucho más grande y riesgosa — arrastraría todos sus archivos y
    subcategorías a otro lugar de la jerarquía — que no fue pedida,
    sigue haciéndose a mano si hace falta. El drop de archivos
    EXTERNOS sobre una categoría (Explorador -> categoría, ya
    heredado de ArbolConDrop) sigue funcionando igual — se distingue
    por `event.source()`, mismo patrón que el resto de los árboles de
    esta app. Al reordenar con éxito emite `orden_cambiado` para que
    `VentanaExplorador` persista la biblioteca (el orden de las
    categorías se guarda tal cual queda el árbol — ver
    `_serializar_biblioteca`, que recorre en orden visual)."""

    orden_cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

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
        super().dropEvent(event)

    def startDrag(self, supportedActions):
        if self.currentItem() is None:
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

    def _reordenar_manual(self, event):
        if len(self.selectedItems()) > 1:
            event.ignore()
            return

        item_arrastrado = self.currentItem()
        if item_arrastrado is None:
            event.ignore()
            return

        padre_origen = item_arrastrado.parent()
        if padre_origen is None:
            indice_origen = self.indexOfTopLevelItem(item_arrastrado)
        else:
            indice_origen = padre_origen.indexOfChild(item_arrastrado)
        if indice_origen < 0:
            event.ignore()
            return

        punto = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_destino = self.itemAt(punto)
        if item_destino is None or item_destino is item_arrastrado:
            event.ignore()
            return

        padre_destino = item_destino.parent()
        if padre_destino is not padre_origen:
            # Fuera de alcance a propósito: solo reordena hermanas del
            # MISMO padre — ver docstring de la clase.
            event.ignore()
            return

        if padre_destino is None:
            indice_destino = self.indexOfTopLevelItem(item_destino)
        else:
            indice_destino = padre_destino.indexOfChild(item_destino)
        if self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem:
            indice_destino += 1
        if indice_destino > indice_origen:
            indice_destino -= 1  # se saca el origen antes de reinsertar

        total_hermanas = self.topLevelItemCount() if padre_origen is None else padre_origen.childCount()
        indice_destino = max(0, min(indice_destino, total_hermanas - 1))
        if indice_destino == indice_origen:
            event.ignore()
            return

        if padre_origen is None:
            item = self.takeTopLevelItem(indice_origen)
            self.insertTopLevelItem(indice_destino, item)
        else:
            item = padre_origen.takeChild(indice_origen)
            padre_origen.insertChild(indice_destino, item)
        self.setCurrentItem(item)
        event.acceptProposedAction()
        self.orden_cambiado.emit()


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

    def __init__(self, parent=None, acepta_desde_publicidad: bool = False):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.viewport().setAcceptDrops(True)
        self.setItemDelegate(DelegadoConservaColorEstado(self))
        # Pedido explícito: arrastrar desde Ventana 1 (Publicidad) solo
        # debe funcionar hacia la Auxiliar, NUNCA hacia Ventana 2 —
        # pese a que las dos comparten esta MISMA clase de árbol
        # (`ArbolReproductorConDrop`), así que la distinción no puede
        # hacerse por tipo, solo por instancia. Ver
        # gui/panel_reproductor.py / gui/ventana_auxiliar.py, que son
        # los únicos que pasan True acá.
        self._acepta_desde_publicidad = acepta_desde_publicidad

    def _origen_publicidad_rechazado(self, event) -> bool:
        origen = event.source()
        return (
            isinstance(origen, ArbolPublicidadConDrop)
            and not self._acepta_desde_publicidad
        )

    def dragEnterEvent(self, event):
        if self._origen_publicidad_rechazado(event):
            event.ignore()
            return
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._origen_publicidad_rechazado(event):
            event.ignore()
            return
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self._origen_publicidad_rechazado(event):
            event.ignore()
            return
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
