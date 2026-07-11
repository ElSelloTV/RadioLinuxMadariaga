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
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from gui.common_widgets import ArbolConDrop
from gui.styles import (
    COLOR_REPRODUCIENDO, COLOR_SIGUIENTE, ROL_ESTADO_ITEM,
    ESTADO_NORMAL, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE,
)


class PanelReproductor(QWidget):
    """Bloque de UI reutilizable: contadores + controles + lista."""

    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    item_marcado_como_siguiente = Signal(int)
    archivo_soltado = Signal(str, object)
    solicitud_abrir_auxiliar = Signal()
    item_doble_click = Signal(int)

    def __init__(self, titulo_panel: str, mostrar_boton_auxiliar: bool = False, parent=None):
        super().__init__(parent)
        self._fila_reproduciendo = -1
        self._fila_siguiente = -1
        self._construir_ui(titulo_panel, mostrar_boton_auxiliar)

    # ------------------------------------------------------------------
    def _construir_ui(self, titulo_panel, mostrar_boton_auxiliar):
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

        self.lbl_titulo_actual = QLabel("Sin reproducción")
        self.lbl_titulo_actual.setObjectName("lblTituloBloqueActivo")
        self.lbl_titulo_actual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_grupo.addWidget(self.lbl_titulo_actual)

        # 2) Controles de reproducción (debajo del tiempo, arriba de la lista)
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

        if mostrar_boton_auxiliar:
            self.btn_auxiliar = QPushButton("🎧 Auxiliar")
            self.btn_auxiliar.clicked.connect(self.solicitud_abrir_auxiliar.emit)
            barra_botones.addWidget(self.btn_auxiliar)

        layout_grupo.addLayout(barra_botones)

        # 3) Lista de reproducción (al final)
        self.tree = ArbolConDrop()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 260)
        self.tree.itemDoubleClicked.connect(self._on_doble_click_item)
        self.tree.archivo_soltado.connect(self.archivo_soltado.emit)
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
        self._pintar_fila(self._fila_reproduciendo, ESTADO_NORMAL)
        self._fila_reproduciendo = fila
        self._pintar_fila(fila, ESTADO_REPRODUCIENDO)
        item = self.tree.topLevelItem(fila)
        if item:
            self.lbl_titulo_actual.setText(item.text(0))

    def marcar_siguiente(self, fila: int):
        estado_previo = ESTADO_REPRODUCIENDO if self._fila_siguiente == self._fila_reproduciendo else ESTADO_NORMAL
        self._pintar_fila(self._fila_siguiente, estado_previo)
        self._fila_siguiente = fila
        self._pintar_fila(fila, ESTADO_SIGUIENTE)
        self.item_marcado_como_siguiente.emit(fila)

    def actualizar_contadores(self, transcurrido: str, restante: str):
        self.lbl_tiempo_transcurrido.setText(transcurrido)
        self.lbl_tiempo_restante.setText(restante)

    def fila_reproduciendo(self) -> int:
        return self._fila_reproduciendo

    def fila_siguiente(self) -> int:
        return self._fila_siguiente

    def cantidad_items(self) -> int:
        return self.tree.topLevelItemCount()

    def ruta_en_fila(self, fila: int) -> str:
        item = self.tree.topLevelItem(fila)
        return item.data(0, Qt.ItemDataRole.UserRole) if item else ""

    # ------------------------------------------------------------------
    def _pintar_fila(self, fila: int, estado: int):
        item = self.tree.topLevelItem(fila) if fila >= 0 else None
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
        fila = self.tree.indexOfTopLevelItem(item)
        self.item_doble_click.emit(fila)
