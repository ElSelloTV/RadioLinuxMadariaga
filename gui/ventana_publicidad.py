"""
gui/ventana_publicidad.py
--------------------------------------------------------
Ventana 1 (Izquierda): Publicidad.
- Botón AUTOMÁTICO (rojo cuando está activo, contorno rojo siempre
  para ubicarlo mejor).
- Contadores de tiempo arriba.
- Etiquetas "Ahora"/"Luego" (con contorno rojo/verde) + barra de
  progreso/seek, igual que Ventana 2 — pedido explícito de traer la
  misma robustez acá.
- Controles de reproducción (Play/Pausa/Stop/Siguiente) debajo
  del tiempo y arriba de la lista.
- Árbol de bloques horarios, con Drag & Drop real desde la
  Ventana 3 (usa ArbolPublicidadConDrop, no monkeypatch).

A propósito, esta ventana NO tiene Pisador ni reproductor Auxiliar
(pedido explícito) — esas dos cosas son exclusivas de Ventana 2.

Máquina de estados de selección (misma que Ventana 2): doble click
(o Enter) sobre una tanda, en silencio, la ARMA en rojo sin arrancar
sola — recién suena al apretar Play. Con algo sonando, doble
click/Enter la marca "en cola" en verde sin interrumpir. Los ítems
rojo/verde (o un bloque que contenga uno) no se pueden sacar de la
lista hasta liberarse.
--------------------------------------------------------
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidgetItem,
    QPushButton, QLabel, QFrame, QAbstractItemView, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from gui.common_widgets import ArbolPublicidadConDrop, SliderBusqueda
from gui.etiqueta_marquesina import EtiquetaMarquesina
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.styles import (
    COLOR_REPRODUCIENDO, COLOR_SIGUIENTE, ROL_ESTADO_ITEM, ROL_ANALISIS_AUDIO,
    ESTADO_NORMAL, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE,
)
from config.settings import cargar_configuracion

# Rol de dato propio: hora "HH:mm:ss" guardada en el nodo de bloque
# (por encima de Qt.UserRole), separado del texto visible del título
# — lo usa SchedulerAutomatico (core/playlist_manager.py) para saber
# cuándo disparar cada bloque, sin tener que parsear el string.
ROL_HORA_BLOQUE = Qt.ItemDataRole.UserRole + 1


class VentanaPublicidad(QWidget):
    automatico_cambiado = Signal(bool)
    archivo_soltado = Signal(str, object)
    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    solicitud_buscar_posicion = Signal(int)     # 0-1000 (por mil)
    solicitud_abrir_programador = Signal()
    solicitud_cargar_programacion_hoy = Signal()
    item_doble_click = Signal(object)   # emite el QTreeWidgetItem clickeado

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modo_automatico = False
        self._item_reproduciendo = None
        self._item_siguiente = None
        self._arrastrando_slider = False
        self._construir_ui()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox("PUBLICIDAD")
        layout_grupo = QVBoxLayout(grupo)

        # --- Barra superior: estado + automático ---
        barra_superior = QHBoxLayout()
        self.lbl_estado = QLabel("Modo manual")
        self.lbl_estado.setObjectName("lblTituloBloqueActivo")
        self.btn_automatico = QPushButton("AUTOMÁTICO: OFF")
        self.btn_automatico.setObjectName("btnAutomatico")
        self.btn_automatico.setCheckable(True)
        self.btn_automatico.setProperty("activo", "false")
        self.btn_automatico.clicked.connect(self._toggle_automatico)
        barra_superior.addWidget(self.lbl_estado)
        barra_superior.addStretch()
        barra_superior.addWidget(self.btn_automatico)
        layout_grupo.addLayout(barra_superior)

        # --- 1) Contadores de tiempo (arriba de todo) ---
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

        # --- "Ahora"/"Luego" con contorno rojo/verde (igual que
        # Ventana 2) — pedido explícito, más robusto que depender
        # solo del color de fila en el árbol. ---
        frame_ahora = QFrame()
        frame_ahora.setObjectName("frameAhora")
        fila_ahora = QHBoxLayout(frame_ahora)
        fila_ahora.setContentsMargins(2, 2, 2, 2)
        self.indicador_en_vivo = IndicadorEnVivo()
        fila_ahora.addWidget(self.indicador_en_vivo)
        lbl_ahora = QLabel("Ahora:")
        lbl_ahora.setObjectName("lblEtiquetaAhoraLuego")
        fila_ahora.addWidget(lbl_ahora)
        self.lbl_titulo_actual = EtiquetaMarquesina()
        fila_ahora.addWidget(self.lbl_titulo_actual)
        layout_grupo.addWidget(frame_ahora)

        frame_luego = QFrame()
        frame_luego.setObjectName("frameLuego")
        fila_luego = QHBoxLayout(frame_luego)
        fila_luego.setContentsMargins(2, 2, 2, 2)
        lbl_luego = QLabel("Luego:")
        lbl_luego.setObjectName("lblEtiquetaAhoraLuego")
        fila_luego.addWidget(lbl_luego)
        self.lbl_titulo_siguiente = EtiquetaMarquesina()
        fila_luego.addWidget(self.lbl_titulo_siguiente)
        layout_grupo.addWidget(frame_luego)

        # --- 2) Controles de reproducción (debajo del tiempo) ---
        # 1 SOLA fila (no 2) — pedido explícito, para ahorrar
        # visibilidad de la lista. Botones compactos (objectName
        # btnTransporte, gui/styles.py) para que entren cómodos.
        barra_botones = QHBoxLayout()
        barra_botones.setSpacing(4)
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setObjectName("btnPlay")
        self.btn_play.setProperty("class", "btnTransporte")
        self.btn_pausa = QPushButton("❚❚ PAUSA")
        self.btn_pausa.setProperty("class", "btnTransporte")
        self.btn_stop = QPushButton("■ STOP")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setProperty("class", "btnTransporte")
        self.btn_siguiente = QPushButton("⏭ SIGUIENTE")
        self.btn_siguiente.setProperty("class", "btnTransporte")
        self.btn_play.clicked.connect(self.solicitud_play.emit)
        self.btn_pausa.clicked.connect(self.solicitud_pausa.emit)
        self.btn_stop.clicked.connect(self.solicitud_stop.emit)
        self.btn_siguiente.clicked.connect(self.solicitud_siguiente.emit)
        barra_botones.addWidget(self.btn_play)
        barra_botones.addWidget(self.btn_pausa)
        barra_botones.addWidget(self.btn_stop)
        barra_botones.addWidget(self.btn_siguiente)
        layout_grupo.addLayout(barra_botones)

        # --- 2.1) Barra de progreso/seek (igual que Ventana 2) ---
        self.slider_progreso = SliderBusqueda(Qt.Orientation.Horizontal)
        self.slider_progreso.setRange(0, 1000)
        self.slider_progreso.setToolTip("Arrastrar o hacer clic para adelantar/retroceder")
        self.slider_progreso.sliderPressed.connect(self._on_slider_presionado)
        self.slider_progreso.sliderReleased.connect(self._on_slider_soltado)
        layout_grupo.addWidget(self.slider_progreso)

        # --- 3) Árbol de bloques horarios (al final) ---
        self.tree = ArbolPublicidadConDrop()
        self.tree.setObjectName("tree_publicidad")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 220)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.archivo_soltado.connect(self.archivo_soltado.emit)
        self.tree.itemDoubleClicked.connect(lambda item, columna: self._on_doble_click_item(item))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        layout_grupo.addWidget(self.tree)

        layout_principal.addWidget(grupo)

    # ------------------------------------------------------------------
    def cargar_bloques(self, bloques: list):
        """Reemplaza todo el árbol por `bloques` — lista de dicts
        {"hora", "titulo", "items": [{"titulo","duracion","codigo","ruta",
        "punto_inicio_ms","punto_fin_ms","ganancia_db"}]} (mismo formato
        que arma/guarda el Programador). Lo usa SchedulerAutomatico al
        cambiar el día, y la restauración desde disco al arrancar."""
        self.tree.clear()
        self._item_reproduciendo = None
        self._item_siguiente = None
        self.lbl_titulo_actual.setText("")
        self.lbl_titulo_siguiente.setText("")
        for bloque in bloques:
            hora = bloque.get("hora", "00:00:00")
            titulo = bloque.get("titulo", "")
            nodo_bloque = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
            fuente = nodo_bloque.font(0)
            fuente.setBold(True)
            nodo_bloque.setFont(0, fuente)
            nodo_bloque.setData(0, ROL_HORA_BLOQUE, hora)
            self.tree.addTopLevelItem(nodo_bloque)
            for item in bloque.get("items", []):
                self.agregar_tanda(
                    nodo_bloque, item.get("titulo", ""), item.get("duracion", ""),
                    item.get("codigo", "—"), item.get("ruta", ""),
                    item.get("punto_inicio_ms") or 0, item.get("punto_fin_ms"),
                    item.get("ganancia_db") or 0.0,
                )
            nodo_bloque.setExpanded(True)

    def agregar_tanda(self, nodo_bloque, titulo: str, duracion: str, codigo: str, ruta: str = "",
                       punto_inicio_ms: int = 0, punto_fin_ms: int = None, ganancia_db: float = 0.0):
        hijo = QTreeWidgetItem([titulo, duracion, codigo])
        hijo.setData(0, Qt.ItemDataRole.UserRole, ruta)
        hijo.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        hijo.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": punto_inicio_ms, "punto_fin_ms": punto_fin_ms, "ganancia_db": ganancia_db,
        })
        nodo_bloque.addChild(hijo)
        return hijo

    def analisis_de_item(self, item) -> dict:
        if item is None:
            return {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}
        return item.data(0, ROL_ANALISIS_AUDIO) or {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}

    def crear_bloque_nuevo(self):
        """Bloque vacío, título por defecto "Bloque: HH:MM:SS" con la
        hora actual — pedido explícito. Queda colapsable como los
        demás (setExpanded controla eso, ya viene expandido vacío)."""
        hora = datetime.now().strftime("%H:%M:%S")
        titulo = f"Bloque: {hora}"
        nodo_bloque = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
        fuente = nodo_bloque.font(0)
        fuente.setBold(True)
        nodo_bloque.setFont(0, fuente)
        nodo_bloque.setData(0, ROL_HORA_BLOQUE, hora)
        self.tree.addTopLevelItem(nodo_bloque)
        nodo_bloque.setExpanded(True)
        self.tree.setCurrentItem(nodo_bloque)
        return nodo_bloque

    def bloques(self) -> list:
        """Lista de los QTreeWidgetItem de bloque (nivel superior)."""
        return [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]

    def hora_de_bloque(self, item_bloque) -> str:
        return item_bloque.data(0, ROL_HORA_BLOQUE) or ""

    # ------------------------------------------------------------------
    def _toggle_automatico(self):
        self._modo_automatico = self.btn_automatico.isChecked()
        if self._modo_automatico:
            self.btn_automatico.setText("AUTOMÁTICO: ON")
            self.btn_automatico.setProperty("activo", "true")
            self.lbl_estado.setText("Modo automático activo")
        else:
            self.btn_automatico.setText("AUTOMÁTICO: OFF")
            self.btn_automatico.setProperty("activo", "false")
            self.lbl_estado.setText("Modo manual")

        self.btn_automatico.style().unpolish(self.btn_automatico)
        self.btn_automatico.style().polish(self.btn_automatico)
        self.automatico_cambiado.emit(self._modo_automatico)

    def esta_en_automatico(self) -> bool:
        return self._modo_automatico

    def actualizar_contadores(self, transcurrido: str, restante: str):
        self.lbl_tiempo_transcurrido.setText(transcurrido)
        self.lbl_tiempo_restante.setText(restante)

    def set_indicador_en_vivo(self, activo: bool):
        self.indicador_en_vivo.set_activo(activo)

    # ------------------------------------------------------------------
    # Barra de progreso (buscar posición) — igual patrón que Ventana 2.
    # ------------------------------------------------------------------
    def _on_slider_presionado(self):
        self._arrastrando_slider = True

    def _on_slider_soltado(self):
        self._arrastrando_slider = False
        self.solicitud_buscar_posicion.emit(self.slider_progreso.value())

    def actualizar_progreso(self, permille: int):
        if self._arrastrando_slider:
            return
        self.slider_progreso.setValue(max(0, min(1000, permille)))

    # ------------------------------------------------------------------
    # Máquina de estados de selección — doble click/Enter (misma que
    # Ventana 2, ver core/playlist_manager.py:GestorPublicidad).
    # ------------------------------------------------------------------
    def _on_doble_click_item(self, item):
        if item is not None and not item.data(0, Qt.ItemDataRole.UserRole):
            return  # nodo de bloque, no es reproducible
        self.item_doble_click.emit(item)

    # ------------------------------------------------------------------
    # Menú contextual (pedido explícito, estructura completa):
    #   Crear/Modificar/Eliminar Programación -> abren el Programador
    #   Cargar Programación -> abre el Programador
    #   Sacar Item (funcional) / Agregar Item / Reemplazar Item (por
    #   ahora deshabilitadas, se van a implementar más adelante)
    #   Crear Bloque Nuevo (funcional)
    # Todo pide confirmación y nunca corta una reproducción en curso
    # (los ítems rojo/verde no se pueden sacar — ver quitar_item).
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        item_bajo_cursor = self.tree.itemAt(posicion)
        seleccionados = self.tree.selectedItems()
        if item_bajo_cursor is not None and item_bajo_cursor not in seleccionados:
            self.tree.setCurrentItem(item_bajo_cursor)
            seleccionados = [item_bajo_cursor]

        menu = QMenu(self)
        accion_crear_prog = menu.addAction("Crear Programación")
        accion_modificar_prog = menu.addAction("Modificar Programación")
        accion_eliminar_prog = menu.addAction("Eliminar Programación")
        menu.addSeparator()
        accion_cargar_prog = menu.addAction("Cargar Programación")
        menu.addSeparator()

        texto_sacar = "Sacar Item" if len(seleccionados) <= 1 else f"Sacar {len(seleccionados)} Ítems"
        accion_sacar = menu.addAction(texto_sacar)
        accion_sacar.setEnabled(bool(seleccionados))

        accion_agregar = menu.addAction("Agregar Item")
        accion_agregar.setEnabled(False)  # todavía no implementado (pedido explícito: dejar visible, deshabilitado)
        accion_reemplazar = menu.addAction("Reemplazar Item")
        accion_reemplazar.setEnabled(False)

        menu.addSeparator()
        accion_crear_bloque = menu.addAction("Crear Bloque Nuevo")

        elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if elegida in (accion_crear_prog, accion_modificar_prog, accion_eliminar_prog):
            # Por el momento, Crear/Modificar/Eliminar abren el
            # Programador que ya existe — pedido explícito.
            self.solicitud_abrir_programador.emit()
        elif elegida == accion_cargar_prog:
            # "Cargar Programación" tiene lógica propia — ver
            # MainWindow._cargar_programacion_de_hoy_manual: resuelve
            # la programación de HOY (fecha específica > día genérico)
            # y pide confirmación antes de reemplazar los bloques.
            self.solicitud_cargar_programacion_hoy.emit()
        elif elegida == accion_sacar:
            self._sacar_items(seleccionados)
        elif elegida == accion_crear_bloque:
            self._confirmar_y_crear_bloque()

    def _sacar_items(self, items: list):
        bloqueados = [item.text(0) for item in items if self._bloqueado_por_reproduccion(item)]
        candidatos = [item for item in items if not self._bloqueado_por_reproduccion(item)]

        if candidatos:
            config = cargar_configuracion()
            if config["general"]["confirmar_antes_de_eliminar"]:
                descripcion = f"'{candidatos[0].text(0)}'" if len(candidatos) == 1 else f"estos {len(candidatos)} ítems"
                respuesta = QMessageBox.question(
                    self, "Sacar de Publicidad",
                    f"¿Sacar {descripcion} de la lista de Publicidad?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if respuesta != QMessageBox.StandardButton.Yes:
                    candidatos = []

        for item in candidatos:
            self.quitar_item(item)

        if bloqueados:
            QMessageBox.information(
                self, "No se puede sacar",
                "Estos ítems están marcados para reproducción (rojo/verde) y no\n"
                "se pueden sacar hasta que se liberen (se elige otro, o termina\n"
                "su reproducción):\n\n" + "\n".join(bloqueados),
            )

    def _confirmar_y_crear_bloque(self):
        hora = datetime.now().strftime("%H:%M:%S")
        respuesta = QMessageBox.question(
            self, "Crear Bloque Nuevo",
            f"¿Crear un nuevo bloque horario \"Bloque: {hora}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            self.crear_bloque_nuevo()

    # ------------------------------------------------------------------
    # Sacar de la lista: bloqueado si el ítem (o cualquier tanda
    # dentro, si es un bloque) está marcado en rojo/verde — mismo
    # concepto que Ventana 2, así nunca se corta lo que está al aire.
    # ------------------------------------------------------------------
    def _bloqueado_por_reproduccion(self, item) -> bool:
        estado = item.data(0, ROL_ESTADO_ITEM)
        if estado in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE):
            return True
        for i in range(item.childCount()):
            if self._bloqueado_por_reproduccion(item.child(i)):
                return True
        return False

    def quitar_item(self, item) -> bool:
        if item is None or self._bloqueado_por_reproduccion(item):
            return False
        if item is self._item_reproduciendo:
            self._item_reproduciendo = None
        if item is self._item_siguiente:
            self._item_siguiente = None
        padre = item.parent()
        if padre is not None:
            padre.removeChild(item)
        else:
            indice = self.tree.indexOfTopLevelItem(item)
            if indice >= 0:
                self.tree.takeTopLevelItem(indice)
        return True

    # ------------------------------------------------------------------
    # Resaltado del ítem en reproducción (rojo) / en cola (verde). A
    # diferencia de la Ventana 2 (lista plana), acá el árbol es
    # jerárquico (bloque -> tandas), así que se guarda una referencia
    # directa al QTreeWidgetItem en vez de un índice de fila.
    # ------------------------------------------------------------------
    def marcar_reproduciendo_item(self, item):
        if self._item_reproduciendo is not None:
            estado_previo = ESTADO_SIGUIENTE if self._item_reproduciendo is self._item_siguiente else ESTADO_NORMAL
            self._pintar_item(self._item_reproduciendo, estado_previo)
        self._item_reproduciendo = item
        if item is not None:
            self._pintar_item(item, ESTADO_REPRODUCIENDO)
            self.lbl_titulo_actual.setText(item.text(0))
            self.lbl_estado.setText(f"Reproduciendo: {item.text(0)}")
        else:
            self.lbl_titulo_actual.setText("")
            self.lbl_estado.setText("Modo automático activo" if self._modo_automatico else "Modo manual")

    def marcar_siguiente_item(self, item):
        if self._item_siguiente is not None:
            estado_previo = ESTADO_REPRODUCIENDO if self._item_siguiente is self._item_reproduciendo else ESTADO_NORMAL
            self._pintar_item(self._item_siguiente, estado_previo)
        self._item_siguiente = item
        if item is not None:
            self._pintar_item(item, ESTADO_SIGUIENTE)
            self.lbl_titulo_siguiente.setText(item.text(0))
        else:
            self.lbl_titulo_siguiente.setText("")

    def item_reproduciendo(self):
        return self._item_reproduciendo

    def item_siguiente(self):
        return self._item_siguiente

    def primer_item_reproducible(self):
        """Primer ítem hoja (con ruta) del árbol, recorriendo bloque por bloque."""
        for i in range(self.tree.topLevelItemCount()):
            bloque = self.tree.topLevelItem(i)
            if bloque.childCount() > 0:
                return bloque.child(0)
        return None

    def _pintar_item(self, item, estado: int):
        item.setData(0, ROL_ESTADO_ITEM, estado)
        if estado == ESTADO_REPRODUCIENDO:
            color_fondo = QBrush(QColor(COLOR_REPRODUCIENDO))
        elif estado == ESTADO_SIGUIENTE:
            color_fondo = QBrush(QColor(COLOR_SIGUIENTE))
        else:
            color_fondo = QBrush()
        color_texto = QBrush(QColor("white")) if estado in (ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE) else QBrush()
        for columna in range(self.tree.columnCount()):
            item.setBackground(columna, color_fondo)
            item.setForeground(columna, color_texto)
