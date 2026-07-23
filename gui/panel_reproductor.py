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
  Pisador. "Eliminar de la biblioteca" se sacó a propósito (pedido
  explícito, "riesgoso"): acá solo se saca el ítem de ESTA lista,
  nunca se borra el archivo de toda la biblioteca — esa acción sigue
  existiendo, pero solo desde la Ventana 3 (Explorador), donde el
  operador tiene el contexto completo de qué está borrando.

Nota de diseño: la fila "reproduciendo"/"siguiente" se rastrea por
REFERENCIA AL ÍTEM (no por índice entero) precisamente para que
sobreviva a una reordenada por arrastre — el índice numérico de un
ítem puede cambiar en cualquier momento, pero el objeto QTreeWidgetItem
sigue siendo el mismo.
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QFrame,
    QTreeWidgetItem, QHeaderView, QMenu, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from gui.common_widgets import ArbolReproductorConDrop, SliderBusqueda
from gui.etiqueta_marquesina import EtiquetaMarquesina
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.medidor_nivel import MedidorNivelDecorativo
from gui.styles import (
    COLOR_REPRODUCIENDO, COLOR_SIGUIENTE, ROL_ESTADO_ITEM, ROL_ANALISIS_AUDIO,
    ESTADO_NORMAL, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE,
    ROL_YA_REPRODUCIDO, icono_reproducido, ROL_POSICION_PISADOR,
)
from config.settings import registrar_reproduccion


class PanelReproductor(QWidget):
    """Bloque de UI reutilizable: contadores + controles + lista."""

    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()   # "Cut" en la UI — corte seco al ítem en cola
    solicitud_fade_stop = Signal()
    solicitud_stop_diferido = Signal()
    solicitud_buscar_posicion = Signal(int)       # 0-1000 (por mil) — solo si mostrar_barra_progreso
    item_marcado_como_siguiente = Signal(int)
    archivo_soltado = Signal(str, object)
    item_doble_click = Signal(int)
    solicitud_agregar_pisador = Signal(int)       # fila del tema música
    solicitud_agregar_item_especifico = Signal()  # pedido explícito: menú contextual del Auxiliar
    solicitud_agregar_item_aleatorio = Signal()   # ídem, elegir un ítem al azar de una categoría

    def __init__(self, titulo_panel: str,
                 mostrar_barra_progreso: bool = False, acepta_desde_publicidad: bool = False,
                 permitir_agregar_item: bool = False, parent=None):
        super().__init__(parent)
        self._item_reproduciendo = None
        self._item_siguiente = None
        self._arrastrando_slider = False
        self.slider_progreso = None
        self._stop_bloqueado_por_automatico = False
        self._titulo_panel = titulo_panel
        # Pedido explícito ("Reproductor Auxiliar: agregá el menú
        # contextual para agregar ítem, lo mismo que Musicalizador"):
        # solo el Auxiliar lo pide — Ventana 1 (Emisión) normalmente se
        # llena sola vía Musicalizador/arrastre, así que este menú
        # queda OFF por defecto y se prende explícito acá.
        self._permitir_agregar_item = permitir_agregar_item
        self._construir_ui(titulo_panel, mostrar_barra_progreso, acepta_desde_publicidad)

    # ------------------------------------------------------------------
    def _construir_ui(self, titulo_panel, mostrar_barra_progreso, acepta_desde_publicidad=False):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox(titulo_panel)
        layout_grupo = QVBoxLayout(grupo)

        # 1) Fila combinada relojes + Ahora/Luego (pedido explícito,
        # "aprovechar más el espacio"): el nameplate fijo se sacó de
        # acá (ver Configuración → General → nombre de emisora, ahora
        # se muestra junto al reloj del toolbar en MainWindow) y los
        # contadores pasan a apilarse a la IZQUIERDA (angostos, uno
        # arriba y otro abajo) en vez de ir en su propia fila — a la
        # derecha, en las mismas 2 líneas, van "Ahora"/"Luego" como ya
        # estaban. El medidor de nivel decorativo queda entre las dos
        # columnas. Esto ahorra una fila entera de alto de panel.
        fila_info = QHBoxLayout()
        fila_info.setSpacing(4)

        columna_relojes = QVBoxLayout()
        columna_relojes.setSpacing(1)
        self.lbl_tiempo_transcurrido = QLabel("00:00:00")
        self.lbl_tiempo_transcurrido.setObjectName("lblTiempoTranscurrido")
        self.lbl_tiempo_transcurrido.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tiempo_transcurrido.setMaximumWidth(76)
        self.lbl_tiempo_restante = QLabel("00:00:00")
        self.lbl_tiempo_restante.setObjectName("lblTiempoRestante")
        self.lbl_tiempo_restante.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tiempo_restante.setMaximumWidth(76)
        columna_relojes.addWidget(self.lbl_tiempo_transcurrido)
        columna_relojes.addWidget(self.lbl_tiempo_restante)
        fila_info.addLayout(columna_relojes)

        # Medidor de nivel decorativo (pedido explícito: mismo lugar
        # que en Dinesat, sin pretender medir audio real).
        self.medidor_nivel = MedidorNivelDecorativo()
        fila_info.addWidget(self.medidor_nivel)

        # Indicador "en vivo" (titila mientras hay audio sonando de
        # verdad) + título del tema: "sticker" de ancho fijo estilo
        # Winamp, nunca empuja el tamaño del panel/columna. Pedido
        # explícito: además del nombre que suena AHORA, mostrar el
        # nombre del que viene LUEGO (ítem marcado en verde) — más
        # robusto que depender solo del color de la fila en la lista.
        # Cada fila va en un QFrame con contorno rojo/verde (mismo
        # concepto de color que la fila de la lista) — pedido explícito.
        columna_ahora_luego = QVBoxLayout()
        columna_ahora_luego.setSpacing(1)

        frame_ahora = QFrame()
        frame_ahora.setObjectName("frameAhora")
        fila_titulo = QHBoxLayout(frame_ahora)
        fila_titulo.setContentsMargins(1, 1, 1, 1)
        self.indicador_en_vivo = IndicadorEnVivo()
        fila_titulo.addWidget(self.indicador_en_vivo)
        lbl_ahora = QLabel("Ahora:")
        lbl_ahora.setObjectName("lblEtiquetaAhoraLuego")
        fila_titulo.addWidget(lbl_ahora)
        self.lbl_titulo_actual = EtiquetaMarquesina()
        fila_titulo.addWidget(self.lbl_titulo_actual)
        columna_ahora_luego.addWidget(frame_ahora)

        frame_luego = QFrame()
        frame_luego.setObjectName("frameLuego")
        fila_siguiente = QHBoxLayout(frame_luego)
        fila_siguiente.setContentsMargins(1, 1, 1, 1)
        lbl_luego = QLabel("Luego:")
        lbl_luego.setObjectName("lblEtiquetaAhoraLuego")
        fila_siguiente.addWidget(lbl_luego)
        self.lbl_titulo_siguiente = EtiquetaMarquesina()
        fila_siguiente.addWidget(self.lbl_titulo_siguiente)
        columna_ahora_luego.addWidget(frame_luego)

        fila_info.addLayout(columna_ahora_luego)
        # Stretch al final (en vez de AlignLeft en cada widget): así la
        # columna de relojes queda angosta y Ahora/Luego no se estira a
        # ocupar todo el ancho sobrante del panel.
        fila_info.addStretch()
        layout_grupo.addLayout(fila_info)

        # 2) Controles de reproducción — grilla estilo Dinesat (pedido
        # explícito): un botón VERDE grande a la izquierda que hace de
        # Play (en silencio) o "Siguiente con fundido" (con algo
        # sonando), y a la derecha una grilla de 2 filas: arriba
        # Stop/Fade-Stop, abajo Pausa/Cut/Stop diferido.
        barra_botones = QHBoxLayout()
        barra_botones.setSpacing(4)

        self.btn_play = QPushButton("▶\nPLAY /\nSIG.")
        self.btn_play.setObjectName("btnPlayPrincipal")
        self.btn_play.setToolTip(
            "En silencio: reproduce el ítem elegido.\n"
            "Con algo sonando: pasa al ítem en cola (verde) con fundido."
        )
        self.btn_play.setMinimumHeight(42)
        self.btn_play.setMinimumWidth(50)
        self.btn_play.clicked.connect(self.solicitud_play.emit)
        barra_botones.addWidget(self.btn_play)

        grilla = QVBoxLayout()
        grilla.setSpacing(3)

        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(3)
        self.btn_stop = QPushButton("■ STOP")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setProperty("class", "btnTransporte")
        self.btn_stop.setToolTip("Corte seco e inmediato.")
        self.btn_fade_stop = QPushButton("◢ FADE")
        self.btn_fade_stop.setObjectName("btnFadeStop")
        self.btn_fade_stop.setProperty("class", "btnTransporte")
        self.btn_fade_stop.setToolTip("Fundido hasta apagar el ítem en reproducción.")
        self.btn_stop.clicked.connect(self._on_click_stop)
        self.btn_fade_stop.clicked.connect(self._on_click_fade_stop)
        fila_superior.addWidget(self.btn_stop)
        fila_superior.addWidget(self.btn_fade_stop)
        grilla.addLayout(fila_superior)

        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(3)
        self.btn_pausa = QPushButton("❚❚ PAUSA")
        self.btn_pausa.setProperty("class", "btnTransporte")
        self.btn_cut = QPushButton("✂ CUT")
        self.btn_cut.setObjectName("btnCut")
        self.btn_cut.setProperty("class", "btnTransporte")
        self.btn_cut.setToolTip("Corte seco e inmediato al ítem en cola (antes \"Siguiente\").")
        self.btn_stop_diferido = QPushButton("◷ STOP…")
        self.btn_stop_diferido.setObjectName("btnStopDiferido")
        self.btn_stop_diferido.setProperty("class", "btnTransporte")
        self.btn_stop_diferido.setProperty("armado", "false")
        self.btn_stop_diferido.setToolTip(
            "Stop diferido: deja terminar el ítem actual y recién ahí detiene todo.\n"
            "Un segundo click lo desarma."
        )
        self.btn_pausa.clicked.connect(self.solicitud_pausa.emit)
        self.btn_cut.clicked.connect(self.solicitud_siguiente.emit)
        self.btn_stop_diferido.clicked.connect(self._on_click_stop_diferido)
        fila_inferior.addWidget(self.btn_pausa)
        fila_inferior.addWidget(self.btn_cut)
        fila_inferior.addWidget(self.btn_stop_diferido)
        grilla.addLayout(fila_inferior)

        barra_botones.addLayout(grilla)

        layout_grupo.addLayout(barra_botones)

        # 2.1) Barra de progreso (buscar posición) — solo Ventana 2
        if mostrar_barra_progreso:
            self.slider_progreso = SliderBusqueda(Qt.Orientation.Horizontal)
            self.slider_progreso.setRange(0, 1000)
            self.slider_progreso.setToolTip("Arrastrar o hacer clic para adelantar/retroceder")
            self.slider_progreso.sliderPressed.connect(self._on_slider_presionado)
            self.slider_progreso.sliderReleased.connect(self._on_slider_soltado)
            layout_grupo.addWidget(self.slider_progreso)

        # 3) Lista de reproducción (al final)
        self.tree = ArbolReproductorConDrop(acepta_desde_publicidad=acepta_desde_publicidad)
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
    def agregar_item(
        self, titulo: str, duracion: str, codigo: str, ruta: str = "",
        punto_inicio_ms: int = 0, punto_fin_ms: int = None, ganancia_db: float = 0.0,
    ):
        item = QTreeWidgetItem([titulo, duracion, codigo])
        item.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        item.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": punto_inicio_ms, "punto_fin_ms": punto_fin_ms, "ganancia_db": ganancia_db,
        })
        self.tree.addTopLevelItem(item)
        return item

    def limpiar_items(self):
        """Vacía la lista por completo (pedido explícito: un Comando
        FMT reemplaza el contenido de Emisión, no lo acumula arriba de
        lo que hubiera antes). A diferencia de `quitar_item()`, esto NO
        respeta el bloqueo de rojo/verde — el propio operador pidió el
        reemplazo total al insertar el comando FMT en su programación,
        así que limpia las referencias ANTES de vaciar el árbol (nunca
        tocar un QTreeWidgetItem ya eliminado)."""
        self.marcar_reproduciendo(-1)
        self.marcar_siguiente(-1)
        self.tree.clear()

    def marcar_reproduciendo(self, fila: int):
        self._pintar_item(self._item_reproduciendo, ESTADO_NORMAL)
        item = self.tree.topLevelItem(fila)
        self._item_reproduciendo = item
        self._pintar_item(item, ESTADO_REPRODUCIENDO)
        self.lbl_titulo_actual.setText(item.text(0) if item else "")

    def marcar_realmente_reproducido(self, fila: int):
        """Marca el ícono "ya reproducido" + registra en el historial
        persistente — a diferencia de `marcar_reproduciendo()` (que
        solo arma visualmente en rojo, incluso en silencio), esto lo
        debe llamar el motor SOLO en el instante exacto en que el
        audio arranca de verdad (ver nota en `_pintar_item`)."""
        item = self.tree.topLevelItem(fila)
        if item is None:
            return
        item.setData(0, ROL_YA_REPRODUCIDO, True)
        item.setIcon(0, icono_reproducido())
        registrar_reproduccion(
            self._titulo_panel, item.text(0), item.text(2),
            item.data(0, Qt.ItemDataRole.UserRole) or "",
        )

    def marcar_siguiente(self, fila: int):
        estado_previo = ESTADO_REPRODUCIENDO if self._item_siguiente is self._item_reproduciendo else ESTADO_NORMAL
        self._pintar_item(self._item_siguiente, estado_previo)
        item = self.tree.topLevelItem(fila)
        self._item_siguiente = item
        self._pintar_item(item, ESTADO_SIGUIENTE)
        self.lbl_titulo_siguiente.setText(item.text(0) if item else "")
        self.item_marcado_como_siguiente.emit(fila)

    def actualizar_contadores(self, transcurrido: str, restante: str):
        self.lbl_tiempo_transcurrido.setText(transcurrido)
        self.lbl_tiempo_restante.setText(restante)

    def set_indicador_en_vivo(self, activo: bool):
        self.indicador_en_vivo.set_activo(activo)
        self.medidor_nivel.set_activo(activo)

    def set_stop_diferido_armado(self, armado: bool):
        """Refleja en el botón "Stop diferido" si quedó armado (queda
        naranja hasta que se ejecute o se desarme) — mismo patrón de
        propiedad dinámica + QSS que ya usa el botón AUTOMÁTICO."""
        self.btn_stop_diferido.setProperty("armado", "true" if armado else "false")
        self.btn_stop_diferido.style().unpolish(self.btn_stop_diferido)
        self.btn_stop_diferido.style().polish(self.btn_stop_diferido)

    def set_stop_habilitado(self, habilitado: bool):
        """Con el modo AUTOMÁTICO de Ventana 1 activo, el STOP (y sus
        variantes Fade-Stop / Stop diferido) de Emisión quedan
        BLOQUEADOS — la estación no se puede silenciar a mano mientras
        el automático conduce el aire. Bug real corregido: antes se
        deshabilitaba el botón (`setEnabled`), y un botón
        deshabilitado no emite `clicked` — el operador apretaba Stop y
        "no pasaba nada", sin ningún aviso. Ahora los botones quedan
        SIEMPRE clickeables y avisan con un mensaje explícito en vez
        de quedar mudos."""
        self._stop_bloqueado_por_automatico = not habilitado

    def _avisar_bloqueado_por_automatico(self):
        QMessageBox.information(
            self, "Automático activo",
            "No se puede detener Emisión mientras el modo AUTOMÁTICO esté\n"
            "activo.\n\nPara detener, primero desactivá el botón AUTOMÁTICO\n"
            "en Publicidad (Ventana 1).",
        )

    def _on_click_stop(self):
        if self._stop_bloqueado_por_automatico:
            self._avisar_bloqueado_por_automatico()
            return
        self.solicitud_stop.emit()

    def _on_click_fade_stop(self):
        if self._stop_bloqueado_por_automatico:
            self._avisar_bloqueado_por_automatico()
            return
        self.solicitud_fade_stop.emit()

    def _on_click_stop_diferido(self):
        if self._stop_bloqueado_por_automatico:
            self._avisar_bloqueado_por_automatico()
            return
        self.solicitud_stop_diferido.emit()

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

    def resetear_reproduccion(self):
        """Pedido explícito: "la barra de reproducción queda en estado
        pausa... cuando hago stop, fade o pasa a otra ventana, la
        reproducción debe reiniciarse" — reinicia la barra de progreso
        y los contadores a cero, en vez de quedar congelados en la
        última posición. NUNCA se llama en una Pausa normal (ahí la
        posición debe conservarse para reanudar)."""
        if self.slider_progreso is not None:
            self.slider_progreso.setValue(0)
        self.actualizar_contadores("00:00:00", "00:00:00")

    def fila_reproduciendo(self) -> int:
        return self.tree.indexOfTopLevelItem(self._item_reproduciendo) if self._item_reproduciendo else -1

    def fila_siguiente(self) -> int:
        return self.tree.indexOfTopLevelItem(self._item_siguiente) if self._item_siguiente else -1

    def cantidad_items(self) -> int:
        return self.tree.topLevelItemCount()

    def ruta_en_fila(self, fila: int) -> str:
        item = self.tree.topLevelItem(fila)
        return item.data(0, Qt.ItemDataRole.UserRole) if item else ""

    def analisis_en_fila(self, fila: int) -> dict:
        """Recorte de silencio + ganancia calculados por
        core/analizador_audio.py al agregar el archivo a la
        biblioteca (Ventana 3) — bug real corregido: antes se perdían
        al arrastrar a esta lista, nunca se aplicaban al aire."""
        item = self.tree.topLevelItem(fila)
        if item is None:
            return {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}
        return item.data(0, ROL_ANALISIS_AUDIO) or {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}

    # ------------------------------------------------------------------
    # Motor "Agregar Pisador" (lado UI): como mucho un Pisador anidado
    # por tema, tabulado debajo. La reproducción simultánea real vive
    # en GestorPlaylist — acá solo se arma/consulta el árbol.
    # ------------------------------------------------------------------
    def agregar_pisador(self, fila_padre: int, titulo: str, duracion: str, codigo: str, ruta: str,
                         posicion: str = "inicio"):
        item_padre = self.tree.topLevelItem(fila_padre)
        if item_padre is None:
            return None

        self.quitar_pisador(fila_padre)  # como mucho un Pisador por tema

        # Posición (pedido explícito, paridad con Dinesat): "inicio"
        # (default, se dispara al arrancar el tema) o "final" (se
        # dispara cerca del outro) — ver core/gestor_emision.py.
        etiqueta = f"↳ {titulo}" + (" (Outro)" if posicion == "final" else "")
        item = QTreeWidgetItem([etiqueta, duracion, codigo])
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        item.setData(0, ROL_POSICION_PISADOR, posicion)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)

        # Pedido explícito: "el pisador toma el color de arriba, del
        # item principal, rojo o verde" — nunca un color de género
        # propio (eso es solo para identificar categorías en Ventana 3
        # - Explorador). Si el tema principal YA está marcado al
        # agregarle el Pisador, el hijo nace con ese mismo color;
        # `_pintar_item()` lo mantiene sincronizado de ahí en más.
        fondo, texto = self._color_para_estado(item_padre.data(0, ROL_ESTADO_ITEM))
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

    def posicion_pisador_en_fila(self, fila: int) -> str:
        item_padre = self.tree.topLevelItem(fila)
        if item_padre is None or item_padre.childCount() == 0:
            return "inicio"
        return item_padre.child(0).data(0, ROL_POSICION_PISADOR) or "inicio"

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
    @staticmethod
    def _color_para_estado(estado: int):
        """(fondo, texto) para un estado rojo/verde/normal — ÚNICO
        lugar que decide el color de fila, reusado por `_pintar_item()`
        y por `agregar_pisador()` (pedido explícito: el color de
        categoría/género es solo para Ventana 3 - Explorador; acá SOLO
        existen rojo/verde/normal + celeste de selección vía QSS)."""
        if estado == ESTADO_REPRODUCIENDO:
            return QBrush(QColor(COLOR_REPRODUCIENDO)), QBrush(QColor("white"))
        if estado == ESTADO_SIGUIENTE:
            return QBrush(QColor(COLOR_SIGUIENTE)), QBrush(QColor("white"))
        return QBrush(), QBrush()

    def _pintar_item(self, item, estado: int):
        """Pinta rojo/verde/normal. Bug real corregido ("el ícono
        'reproducido' se marca al seleccionar, no al reproducir de
        verdad"): antes esta función marcaba ROL_YA_REPRODUCIDO + el
        ícono + el historial persistente como efecto colateral de
        pintar ESTADO_REPRODUCIENDO — pero `_asegurar_rojo_y_verde()`
        (core/gestor_emision.py) pinta rojo el primer ítem de la lista
        con el reproductor EN SILENCIO, solo para "dejar algo armado",
        cada vez que se carga/regenera la lista (nuevo día, nueva serie
        del Musicalizador, etc.) — sin que haya sonado un solo segundo
        de audio. Ahora pintar rojo es puramente visual; la marca real
        de "reproducido" vive en `marcar_realmente_reproducido()`, que
        el motor llama SOLO en el punto donde el audio arranca de
        verdad (core/gestor_emision.py: `_reproducir_fila()` /
        `_iniciar_crossfade()`)."""
        if item is None:
            return
        item.setData(0, ROL_ESTADO_ITEM, estado)
        color, texto = self._color_para_estado(estado)
        for columna in range(self.tree.columnCount()):
            item.setBackground(columna, color)
            item.setForeground(columna, texto)
        # Pedido explícito: "el pisador toma el color de arriba, del
        # item principal, rojo o verde" — el Pisador anidado (si tiene)
        # SIEMPRE refleja el mismo estado que su tema principal.
        for i in range(item.childCount()):
            hijo = item.child(i)
            for columna in range(self.tree.columnCount()):
                hijo.setBackground(columna, color)
                hijo.setForeground(columna, texto)

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
        if not seleccionados and not self._permitir_agregar_item:
            return

        item_unico = seleccionados[0] if len(seleccionados) == 1 else None

        menu = QMenu(self)

        accion_agregar_especifico = None
        accion_agregar_aleatorio = None
        if self._permitir_agregar_item:
            accion_agregar_especifico = menu.addAction("➕ Agregar ítem específico...")
            accion_agregar_aleatorio = menu.addAction("🎲 Agregar ítem aleatorio...")
            if seleccionados:
                menu.addSeparator()

        accion_borrar = None
        if seleccionados:
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

        if menu.isEmpty():
            return

        elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if accion_agregar_especifico is not None and elegida == accion_agregar_especifico:
            self.solicitud_agregar_item_especifico.emit()
        elif accion_agregar_aleatorio is not None and elegida == accion_agregar_aleatorio:
            self.solicitud_agregar_item_aleatorio.emit()
        elif accion_borrar is not None and elegida == accion_borrar:
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
