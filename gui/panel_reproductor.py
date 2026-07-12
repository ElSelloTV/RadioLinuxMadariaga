"""
gui/panel_reproductor.py
--------------------------------------------------------
Panel reutilizable de reproducción: contadores de tiempo,
controles de transporte y lista de reproducción con resaltado
ROJO (sonando) / VERDE (próximo).

Orden vertical (pedido explícito): contadores de tiempo arriba
de todo, controles de reproducción debajo del tiempo, y la
lista de reproducción al final.

Lo usan tanto Ventana 2 (Emisión principal) como la Ventana
Auxiliar (preescucha/reproducción secundaria) por composición,
para no duplicar la misma lógica dos veces.

La lista soporta:
- Reordenar ítems arrastrándolos arriba/abajo (ArbolReproductorConDrop).
- Un "Pisador" (archivo de género Pisador) anidado, tabulado, debajo
  de un tema musical — como mucho uno por tema. Lo agrega/quita el
  menú contextual; la reproducción simultánea real (bajar volumen
  del tema mientras suena y restaurarlo al terminar) la maneja
  GestorPlaylist en core/playlist_manager.py.
- Menú contextual: Quitar de la lista, Información, Agregar/Quitar
  Pisador, Eliminar de la biblioteca (definitivo, con advertencia).

Nota de diseño: la fila "reproduciendo"/"siguiente" se rastrea por
REFERENCIA AL ÍTEM (no por índice entero) precisamente para que
sobreviva a una reordenada por arrastre — el índice numérico de un
ítem puede cambiar en cualquier momento, pero el objeto QTreeWidgetItem
sigue siendo el mismo.
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QPushButton,
    QTreeWidgetItem, QHeaderView, QMenu, QMessageBox, QAbstractItemView, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from gui.common_widgets import ArbolReproductorConDrop
from gui.etiqueta_marquesina import EtiquetaMarquesina
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.styles import (
    COLOR_REPRODUCIENDO, COLOR_SIGUIENTE, ROL_ESTADO_ITEM,
    ESTADO_NORMAL, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE,
    GENERO_COLORES, color_texto_legible,
)
from config.settings import cargar_configuracion


class PanelReproductor(QWidget):
    """Bloque de UI reutilizable: contadores + controles + lista."""

    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    solicitud_buscar_posicion = Signal(int)       # 0-1000 (por mil) — solo si mostrar_barra_progreso
    item_marcado_como_siguiente = Signal(int)
    archivo_soltado = Signal(str, object)
    solicitud_abrir_auxiliar = Signal()
    item_doble_click = Signal(int)
    solicitud_agregar_pisador = Signal(int)       # fila del tema música
    solicitud_eliminar_definitivo = Signal(str)   # ruta a borrar de TODA la biblioteca

    def __init__(self, titulo_panel: str, mostrar_boton_auxiliar: bool = False,
                 mostrar_barra_progreso: bool = False, parent=None):
        super().__init__(parent)
        self._item_reproduciendo = None
        self._item_siguiente = None
        self._arrastrando_slider = False
        self.slider_progreso = None
        self._construir_ui(titulo_panel, mostrar_boton_auxiliar, mostrar_barra_progreso)

    # ------------------------------------------------------------------
    def _construir_ui(self, titulo_panel, mostrar_boton_auxiliar, mostrar_barra_progreso):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox(titulo_panel)
        layout_grupo = QVBoxLayout(grupo)

        # 1) Contadores de tiempo (arriba de todo)
        layout_contadores = QHBoxLayout()
        self.lbl_tiempo_transcurrido = QLabel("00:00:00")
        self.lbl_tiempo_transcurrido.setObjectName("lblTiempoTranscurrido")
        self.lbl_tiempo_transcurrido.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tiempo_restante = QLabel("00:00:00")
        self.lbl_tiempo_restante.setObjectName("lblTiempoRestante")
        self.lbl_tiempo_restante.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contadores.addWidget(self.lbl_tiempo_transcurrido)
        layout_contadores.addWidget(self.lbl_tiempo_restante)
        layout_grupo.addLayout(layout_contadores)

        # Indicador "en vivo" (titila mientras hay audio sonando de
        # verdad) + título del tema: "sticker" de ancho fijo estilo
        # Winamp, nunca empuja el tamaño del panel/columna.
        fila_titulo = QHBoxLayout()
        self.indicador_en_vivo = IndicadorEnVivo()
        fila_titulo.addWidget(self.indicador_en_vivo)
        self.lbl_titulo_actual = EtiquetaMarquesina()
        fila_titulo.addWidget(self.lbl_titulo_actual)
        layout_grupo.addLayout(fila_titulo)

        # 2) Controles de reproducción (debajo del tiempo, arriba de la
        # lista). En GRILLA de 2 columnas (no una fila larga): una fila
        # de 4-5 botones en línea es lo que fijaba un ancho mínimo
        # grande y no dejaba achicar el panel ni notar "Expandir".
        barra_botones = QGridLayout()
        barra_botones.setSpacing(4)
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setObjectName("btnPlay")
        self.btn_pausa = QPushButton("❚❚ PAUSA")
        self.btn_stop = QPushButton("■ STOP")
        self.btn_stop.setObjectName("btnStop")
        self.btn_siguiente = QPushButton("⏭ SIGUIENTE")

        self.btn_play.clicked.connect(self.solicitud_play.emit)
        self.btn_pausa.clicked.connect(self.solicitud_pausa.emit)
        self.btn_stop.clicked.connect(self.solicitud_stop.emit)
        self.btn_siguiente.clicked.connect(self.solicitud_siguiente.emit)

        barra_botones.addWidget(self.btn_play, 0, 0)
        barra_botones.addWidget(self.btn_pausa, 0, 1)
        barra_botones.addWidget(self.btn_stop, 1, 0)
        barra_botones.addWidget(self.btn_siguiente, 1, 1)

        if mostrar_boton_auxiliar:
            self.btn_auxiliar = QPushButton("🎧 Auxiliar")
            self.btn_auxiliar.clicked.connect(self.solicitud_abrir_auxiliar.emit)
            barra_botones.addWidget(self.btn_auxiliar, 2, 0, 1, 2)

        layout_grupo.addLayout(barra_botones)

        # 2.1) Barra de progreso (buscar posición) — solo Ventana 2
        if mostrar_barra_progreso:
            self.slider_progreso = QSlider(Qt.Orientation.Horizontal)
            self.slider_progreso.setRange(0, 1000)
            self.slider_progreso.setToolTip("Arrastrar para adelantar/retroceder")
            self.slider_progreso.sliderPressed.connect(self._on_slider_presionado)
            self.slider_progreso.sliderReleased.connect(self._on_slider_soltado)
            layout_grupo.addWidget(self.slider_progreso)

        # 3) Lista de reproducción (al final)
        self.tree = ArbolReproductorConDrop()
        self.tree.setObjectName("tree_reproductor")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        # Con decoración (flechas de expandir): un tema puede tener
        # un Pisador anidado, tabulado, debajo.
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(14)
        self.tree.setAlternatingRowColors(True)
        # Selección múltiple (Ctrl/Shift+click) para acciones en lote
        # (quitar, eliminar) y para arrastrar varios temas a la vez.
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Ajuste de columna LIBRE: todas Interactive, sin Stretch
        # forzado en la última (pedido explícito).
        header = self.tree.header()
        for columna in range(self.tree.columnCount()):
            header.setSectionResizeMode(columna, QHeaderView.ResizeMode.Interactive)
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 70)

        self.tree.itemDoubleClicked.connect(self._on_doble_click_item)
        self.tree.archivo_soltado.connect(self.archivo_soltado.emit)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)

        layout_grupo.addWidget(self.tree)

        layout_principal.addWidget(grupo)

    # ------------------------------------------------------------------
    # API pública usada por core/playlist_manager.py
    # ------------------------------------------------------------------
    def agregar_item(self, titulo: str, duracion: str, codigo: str, ruta: str = ""):
        item = QTreeWidgetItem([titulo, duracion, codigo])
        item.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        self.tree.addTopLevelItem(item)
        return item

    def marcar_reproduciendo(self, fila: int):
        self._pintar_item(self._item_reproduciendo, ESTADO_NORMAL)
        item = self.tree.topLevelItem(fila)
        self._item_reproduciendo = item
        self._pintar_item(item, ESTADO_REPRODUCIENDO)
        if item:
            self.lbl_titulo_actual.setText(item.text(0))

    def marcar_siguiente(self, fila: int):
        estado_previo = ESTADO_REPRODUCIENDO if self._item_siguiente is self._item_reproduciendo else ESTADO_NORMAL
        self._pintar_item(self._item_siguiente, estado_previo)
        item = self.tree.topLevelItem(fila)
        self._item_siguiente = item
        self._pintar_item(item, ESTADO_SIGUIENTE)
        self.item_marcado_como_siguiente.emit(fila)

    def actualizar_contadores(self, transcurrido: str, restante: str):
        self.lbl_tiempo_transcurrido.setText(transcurrido)
        self.lbl_tiempo_restante.setText(restante)

    def set_indicador_en_vivo(self, activo: bool):
        self.indicador_en_vivo.set_activo(activo)

    # ------------------------------------------------------------------
    # Barra de progreso (solo si mostrar_barra_progreso=True al construir)
    # ------------------------------------------------------------------
    def _on_slider_presionado(self):
        self._arrastrando_slider = True

    def _on_slider_soltado(self):
        self._arrastrando_slider = False
        self.solicitud_buscar_posicion.emit(self.slider_progreso.value())

    def actualizar_progreso(self, permille: int):
        if self.slider_progreso is None or self._arrastrando_slider:
            return
        self.slider_progreso.setValue(max(0, min(1000, permille)))

    def fila_reproduciendo(self) -> int:
        return self.tree.indexOfTopLevelItem(self._item_reproduciendo) if self._item_reproduciendo else -1

    def fila_siguiente(self) -> int:
        return self.tree.indexOfTopLevelItem(self._item_siguiente) if self._item_siguiente else -1

    def cantidad_items(self) -> int:
        return self.tree.topLevelItemCount()

    def ruta_en_fila(self, fila: int) -> str:
        item = self.tree.topLevelItem(fila)
        return item.data(0, Qt.ItemDataRole.UserRole) if item else ""

    # ------------------------------------------------------------------
    # Motor "Agregar Pisador" (lado UI): como mucho un Pisador anidado
    # por tema, tabulado debajo. La reproducción simultánea real vive
    # en GestorPlaylist — acá solo se arma/consulta el árbol.
    # ------------------------------------------------------------------
    def agregar_pisador(self, fila_padre: int, titulo: str, duracion: str, codigo: str, ruta: str):
        item_padre = self.tree.topLevelItem(fila_padre)
        if item_padre is None:
            return None

        self.quitar_pisador(fila_padre)  # como mucho un Pisador por tema

        item = QTreeWidgetItem([f"↳ {titulo}", duracion, codigo])
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)

        colores_genero = cargar_configuracion().get("apariencia", {}).get("colores_genero", GENERO_COLORES)
        color_pisador = colores_genero.get("Pisador")
        if color_pisador:
            fondo = QBrush(QColor(color_pisador))
            texto = QBrush(QColor(color_texto_legible(color_pisador)))
            for columna in range(item.columnCount()):
                item.setBackground(columna, fondo)
                item.setForeground(columna, texto)

        item_padre.addChild(item)
        item_padre.setExpanded(True)
        return item

    def quitar_pisador(self, fila_padre: int):
        item_padre = self.tree.topLevelItem(fila_padre)
        if item_padre is None or item_padre.childCount() == 0:
            return
        item_padre.takeChildren()

    def ruta_pisador_en_fila(self, fila: int) -> str:
        item_padre = self.tree.topLevelItem(fila)
        if item_padre is None or item_padre.childCount() == 0:
            return ""
        return item_padre.child(0).data(0, Qt.ItemDataRole.UserRole) or ""

    # ------------------------------------------------------------------
    # Quitar de la lista (NO borra el archivo, solo lo saca de acá).
    # Si es el Pisador de un tema, solo se quita él; si es el tema
    # principal, se va con su Pisador (si tenía).
    # ------------------------------------------------------------------
    def quitar_item(self, item: QTreeWidgetItem) -> bool:
        """Devuelve False sin hacer nada si el ítem está marcado en
        rojo o verde (en reproducción o en cola) — pedido explícito:
        esos ítems no se pueden quitar de la lista hasta liberarse
        (se elige otro, o termina su reproducción)."""
        if item is None:
            return False
        if item.data(0, ROL_ESTADO_ITEM) in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE):
            return False

        padre = item.parent()
        if padre is not None:
            padre.removeChild(item)
            return True

        if item is self._item_reproduciendo:
            self._item_reproduciendo = None
        if item is self._item_siguiente:
            self._item_siguiente = None

        indice = self.tree.indexOfTopLevelItem(item)
        if indice >= 0:
            self.tree.takeTopLevelItem(indice)
        return True

    # ------------------------------------------------------------------
    def _pintar_item(self, item, estado: int):
        if item is None:
            return
        item.setData(0, ROL_ESTADO_ITEM, estado)
        if estado == ESTADO_REPRODUCIENDO:
            color = QBrush(QColor(COLOR_REPRODUCIENDO))
        elif estado == ESTADO_SIGUIENTE:
            color = QBrush(QColor(COLOR_SIGUIENTE))
        else:
            color = QBrush()
        for columna in range(self.tree.columnCount()):
            item.setBackground(columna, color)
            item.setForeground(
                columna,
                QBrush(QColor("white")) if estado in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE) else QBrush(),
            )

    def _on_doble_click_item(self, item, columna):
        if item.parent() is not None:
            return  # ítem Pisador: no tiene reproducción independiente
        fila = self.tree.indexOfTopLevelItem(item)
        self.item_doble_click.emit(fila)

    # ------------------------------------------------------------------
    # Menú contextual: Quitar de la lista, Información, Agregar/Quitar
    # Pisador, Eliminar de la biblioteca (definitivo). Quitar/Eliminar
    # operan sobre TODA la selección (Ctrl/Shift+click); Información
    # y Agregar/Quitar Pisador solo tienen sentido con un único ítem.
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        item_bajo_cursor = self.tree.itemAt(posicion)
        seleccionados = self.tree.selectedItems()
        if item_bajo_cursor is not None and item_bajo_cursor not in seleccionados:
            self.tree.setCurrentItem(item_bajo_cursor)
            seleccionados = [item_bajo_cursor]
        if not seleccionados:
            return

        item_unico = seleccionados[0] if len(seleccionados) == 1 else None

        menu = QMenu(self)
        texto_quitar = "✕ Quitar de la lista" if item_unico is not None else f"✕ Quitar {len(seleccionados)} de la lista"
        accion_borrar = menu.addAction(texto_quitar)

        accion_info = None
        if item_unico is not None:
            accion_info = menu.addAction("ℹ Información...")

        accion_pisador = None
        bloqueado_por_reproduccion = (
            item_unico is not None and item_unico.data(0, ROL_ESTADO_ITEM) == ESTADO_REPRODUCIENDO
        )
        if item_unico is not None and item_unico.parent() is None and not bloqueado_por_reproduccion:
            menu.addSeparator()
            if item_unico.childCount() > 0:
                accion_pisador = menu.addAction("🎚 Quitar Pisador")
            else:
                accion_pisador = menu.addAction("🎚 Agregar Pisador...")

        menu.addSeparator()
        texto_eliminar = "🗑 Eliminar de la biblioteca..." if item_unico is not None \
            else f"🗑 Eliminar {len(seleccionados)} de la biblioteca..."
        accion_eliminar = menu.addAction(texto_eliminar)

        elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if elegida == accion_borrar:
            bloqueados = [item.text(0) for item in seleccionados if not self.quitar_item(item)]
            if bloqueados:
                QMessageBox.information(
                    self, "No se puede quitar",
                    "Estos ítems están marcados para reproducción (rojo/verde) y no\n"
                    "se pueden quitar hasta que se liberen (se elige otro, o termina\n"
                    "su reproducción):\n\n" + "\n".join(bloqueados),
                )
        elif accion_info is not None and elegida == accion_info:
            self._mostrar_info(item_unico)
        elif accion_pisador is not None and elegida == accion_pisador:
            fila = self.tree.indexOfTopLevelItem(item_unico)
            if item_unico.childCount() > 0:
                self.quitar_pisador(fila)
            else:
                self.solicitud_agregar_pisador.emit(fila)
        elif elegida == accion_eliminar:
            self._solicitar_eliminacion_definitiva(seleccionados)

    def _mostrar_info(self, item: QTreeWidgetItem):
        ruta = item.data(0, Qt.ItemDataRole.UserRole) or ""
        lineas = [
            f"Título: {item.text(0)}",
            f"Código: {item.text(2)}",
            f"Duración: {item.text(1)}",
            f"Ubicación: {ruta or '(sin archivo asociado)'}",
        ]

        if ruta and os.path.exists(ruta):
            try:
                tamaño_mb = os.path.getsize(ruta) / (1024 * 1024)
                lineas.append(f"Tamaño: {tamaño_mb:.2f} MB")
            except OSError:
                pass
            try:
                from mutagen import File as ArchivoMutagen
                audio = ArchivoMutagen(ruta)
                if audio is not None and audio.info is not None:
                    if getattr(audio.info, "bitrate", None):
                        lineas.append(f"Bitrate: {int(audio.info.bitrate / 1000)} kbps")
                    if getattr(audio.info, "sample_rate", None):
                        lineas.append(f"Frecuencia: {audio.info.sample_rate} Hz")
            except Exception:
                pass
        elif ruta:
            lineas.append("(el archivo no se encuentra en esa ubicación)")

        QMessageBox.information(self, "Información del tema", "\n".join(lineas))

    def _solicitar_eliminacion_definitiva(self, items: list):
        bloqueados = [
            item.text(0) for item in items
            if item.data(0, ROL_ESTADO_ITEM) in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE)
        ]
        items = [
            item for item in items
            if item.data(0, ROL_ESTADO_ITEM) not in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE)
        ]
        if bloqueados:
            QMessageBox.information(
                self, "No se puede eliminar",
                "Estos ítems están marcados para reproducción (rojo/verde) y no\n"
                "se pueden eliminar hasta que se liberen:\n\n" + "\n".join(bloqueados),
            )

        items_con_ruta = [item for item in items if item.data(0, Qt.ItemDataRole.UserRole)]
        if not items_con_ruta:
            if not bloqueados:
                QMessageBox.information(self, "Eliminar", "Ningún ítem seleccionado tiene un archivo asociado.")
            return

        if len(items_con_ruta) == 1:
            descripcion = f"'{items_con_ruta[0].text(0)}'"
        else:
            descripcion = f"estos {len(items_con_ruta)} archivos"

        respuesta = QMessageBox.warning(
            self, "Eliminar definitivamente",
            f"Esto va a borrar {descripcion} de TODA la biblioteca del programa,\n"
            "no solo de esta lista. Esta acción no se puede deshacer.\n\n"
            "¿Confirmás que querés eliminarlos por completo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        for item in items_con_ruta:
            ruta = item.data(0, Qt.ItemDataRole.UserRole)
            self.quitar_item(item)
            self.solicitud_eliminar_definitivo.emit(ruta)
