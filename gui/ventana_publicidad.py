"""
gui/ventana_publicidad.py
--------------------------------------------------------
Ventana 1 (Izquierda): Publicidad.
- Botón AUTOMÁTICO (rojo cuando está activo).
- Contadores de tiempo arriba.
- Controles de reproducción (Play/Pausa/Stop/Siguiente) debajo
  del tiempo y arriba de la lista.
- Árbol de bloques horarios, con Drag & Drop real desde la
  Ventana 3 (usa ArbolConDrop, no monkeypatch).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidgetItem,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from gui.common_widgets import ArbolConDrop
from gui.styles import COLOR_REPRODUCIENDO


class VentanaPublicidad(QWidget):
    automatico_cambiado = Signal(bool)
    archivo_soltado = Signal(str, object)
    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    item_doble_click = Signal(object)   # emite el QTreeWidgetItem clickeado

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modo_automatico = False
        self._item_reproduciendo = None
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

        # --- 2) Controles de reproducción (debajo del tiempo) ---
        barra_botones = QHBoxLayout()
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
        for btn in (self.btn_play, self.btn_pausa, self.btn_stop, self.btn_siguiente):
            barra_botones.addWidget(btn)
        layout_grupo.addLayout(barra_botones)

        # --- 3) Árbol de bloques horarios (al final) ---
        self.tree = ArbolConDrop()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 220)
        self.tree.archivo_soltado.connect(self.archivo_soltado.emit)
        self.tree.itemDoubleClicked.connect(lambda item, columna: self.item_doble_click.emit(item))
        layout_grupo.addWidget(self.tree)

        layout_principal.addWidget(grupo)
        self._cargar_datos_demo()

    # ------------------------------------------------------------------
    def _cargar_datos_demo(self):
        bloques_demo = [
            ("12:00:00 - Bloque Mediodía", [
                ("Tanda Comercial 1", "00:03:20", "COM00044"),
                ("FMT Latinos", "00:00:00", "JIN00017"),
            ]),
            ("18:00:00 - Bloque Tarde", [
                ("Tanda Comercial 2", "00:02:45", "COM00012"),
            ]),
        ]
        for titulo_bloque, items in bloques_demo:
            nodo_bloque = QTreeWidgetItem([titulo_bloque, "", ""])
            fuente = nodo_bloque.font(0)
            fuente.setBold(True)
            nodo_bloque.setFont(0, fuente)
            self.tree.addTopLevelItem(nodo_bloque)
            for titulo, duracion, codigo in items:
                hijo = QTreeWidgetItem([titulo, duracion, codigo])
                nodo_bloque.addChild(hijo)
            nodo_bloque.setExpanded(True)

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

    # ------------------------------------------------------------------
    # Resaltado del ítem en reproducción (rojo). A diferencia de la
    # Ventana 2 (lista plana), acá el árbol es jerárquico (bloque ->
    # tandas), así que se guarda una referencia directa al
    # QTreeWidgetItem en vez de un índice de fila.
    # ------------------------------------------------------------------
    def marcar_reproduciendo_item(self, item):
        if self._item_reproduciendo is not None:
            self._pintar_item(self._item_reproduciendo, activo=False)
        self._item_reproduciendo = item
        if item is not None:
            self._pintar_item(item, activo=True)
            self.lbl_estado.setText(f"Reproduciendo: {item.text(0)}")

    def item_reproduciendo(self):
        return self._item_reproduciendo

    def primer_item_reproducible(self):
        """Primer ítem hoja (con ruta) del árbol, recorriendo bloque por bloque."""
        for i in range(self.tree.topLevelItemCount()):
            bloque = self.tree.topLevelItem(i)
            if bloque.childCount() > 0:
                return bloque.child(0)
        return None

    def _pintar_item(self, item, activo: bool):
        color_fondo = QBrush(QColor(COLOR_REPRODUCIENDO)) if activo else QBrush()
        color_texto = QBrush(QColor("white")) if activo else QBrush()
        for columna in range(self.tree.columnCount()):
            item.setBackground(columna, color_fondo)
            item.setForeground(columna, color_texto)
