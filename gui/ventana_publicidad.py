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
from PySide6.QtGui import QColor, QBrush, QIcon

from gui.common_widgets import ArbolPublicidadConDrop, SliderBusqueda
from gui.etiqueta_marquesina import EtiquetaMarquesina
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.medidor_nivel import MedidorNivelDecorativo
from gui.styles import (
    COLOR_REPRODUCIENDO, COLOR_SIGUIENTE, ROL_ESTADO_ITEM, ROL_ANALISIS_AUDIO,
    ESTADO_NORMAL, ESTADO_REPRODUCIENDO, ESTADO_SIGUIENTE,
    ROL_YA_REPRODUCIDO, icono_reproducido, ROL_VIGENCIA,
    ROL_ES_COMANDO, ROL_TIPO_COMANDO, ROL_PARAMETRO_COMANDO, COLOR_COMANDO,
    ROL_ES_ALEATORIO, ROL_CATEGORIA_ALEATORIO, ROL_RECURSIVO_ALEATORIO, COLOR_ALEATORIO,
    ROL_ITEM_CON_ERROR, icono_error,
)
from config.settings import (
    cargar_configuracion, titulo_bloque_sin_prefijo_hora, registrar_reproduccion,
    ruta_con_prefijo_reemplazado,
)

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
    solicitud_siguiente = Signal()   # "Cut" en la UI — corte seco al ítem en cola
    solicitud_fade_stop = Signal()
    solicitud_stop_diferido = Signal()
    solicitud_buscar_posicion = Signal(int)     # 0-1000 (por mil)
    solicitud_abrir_programador = Signal()
    solicitud_cargar_programacion_hoy = Signal()
    item_doble_click = Signal(object)   # emite el QTreeWidgetItem clickeado
    programacion_cargada = Signal()     # cada vez que cargar_bloques() reemplaza el árbol (preload)
    solicitud_hth_manual = Signal()     # botón azul "HORA/TEMP" (recrea el "Bajador" de Dinesat)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modo_automatico = False
        self._item_reproduciendo = None
        self._item_siguiente = None
        self._arrastrando_slider = False
        # Referencia al Explorador (pedido explícito: habilitar Agregar/
        # Reemplazar Item con el mismo buscador de biblioteca del
        # Programador, directo acá, sin abrirlo) — se setea después de
        # construir las dos ventanas (ver MainWindow._construir_paneles_centrales,
        # VentanaExplorador se crea DESPUÉS de esta).
        self._ventana_explorador = None
        self._construir_ui()

    def set_ventana_explorador(self, ventana_explorador):
        self._ventana_explorador = ventana_explorador

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox("PROGRAMACIÓN / ROTATIVA")
        layout_grupo = QVBoxLayout(grupo)

        # --- Botón AUTOMÁTICO vive en la grilla de transporte (pedido
        # explícito, paridad con Dinesat: "la ventana 1 tiene un 4to
        # botón abajo, que es el automático") — acá queda su
        # construcción, pero se agrega a la UI más abajo.
        # `lbl_estado` ("Modo Manual"/"Automático Activo") ya NO se
        # muestra ACÁ (pedido explícito, ronda posterior: "ponelo
        # abajo, reemplazando la misma leyenda que sale abajo" —
        # queda solo como estado interno, la leyenda visible única
        # vive en la barra de estado de MainWindow, ver
        # `MainWindow._on_automatico_cambiado`. Se sigue actualizando
        # en `_toggle_automatico()` para no romper código que lo
        # consulte. ---
        self.lbl_estado = QLabel("Modo Manual")
        self.lbl_estado.setObjectName("lblEstadoAutomatico")
        self.lbl_estado.setProperty("activo", "false")
        # Pedido explícito ("sin texto... el automático en rojo"): el
        # glifo es el MISMO en los dos estados (no más "AUTO"/"MANUAL"
        # como texto) — el color (gris/rojo, ver gui/styles.py) y el
        # tooltip llevan toda la señal de estado.
        self.btn_automatico = QPushButton("🔁")
        self.btn_automatico.setObjectName("btnAutomatico")
        self.btn_automatico.setProperty("class", "btnTransporte")
        self.btn_automatico.setCheckable(True)
        self.btn_automatico.setProperty("activo", "false")
        self.btn_automatico.setToolTip("AUTOMÁTICO: dispara los bloques horarios por hora y gobierna la vuelta a Emisión.")
        self.btn_automatico.clicked.connect(self._on_click_automatico)

        # --- 1) Fila combinada relojes + Ahora/Luego (pedido explícito,
        # "aprovechar más el espacio", igual criterio que Ventana 2):
        # el nameplate fijo se sacó de acá (ver Configuración →
        # General → nombre de emisora, ahora se muestra junto al reloj
        # del toolbar en MainWindow) y los contadores pasan a apilarse
        # a la IZQUIERDA (angostos, uno arriba y otro abajo) — a la
        # derecha, en las mismas 2 líneas, van "Ahora"/"Luego" como ya
        # estaban. Ahorra una fila entera de alto de panel. ---
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

        self.medidor_nivel = MedidorNivelDecorativo()
        fila_info.addWidget(self.medidor_nivel)

        # --- "Ahora"/"Luego" con contorno rojo/verde (igual que
        # Ventana 2) — pedido explícito, más robusto que depender
        # solo del color de fila en el árbol. ---
        columna_ahora_luego = QVBoxLayout()
        columna_ahora_luego.setSpacing(1)

        frame_ahora = QFrame()
        frame_ahora.setObjectName("frameAhora")
        fila_ahora = QHBoxLayout(frame_ahora)
        fila_ahora.setContentsMargins(1, 1, 1, 1)
        self.indicador_en_vivo = IndicadorEnVivo()
        fila_ahora.addWidget(self.indicador_en_vivo)
        lbl_ahora = QLabel("Ahora:")
        lbl_ahora.setObjectName("lblEtiquetaAhoraLuego")
        fila_ahora.addWidget(lbl_ahora)
        self.lbl_titulo_actual = EtiquetaMarquesina()
        fila_ahora.addWidget(self.lbl_titulo_actual)
        columna_ahora_luego.addWidget(frame_ahora)

        frame_luego = QFrame()
        frame_luego.setObjectName("frameLuego")
        fila_luego = QHBoxLayout(frame_luego)
        fila_luego.setContentsMargins(1, 1, 1, 1)
        lbl_luego = QLabel("Luego:")
        lbl_luego.setObjectName("lblEtiquetaAhoraLuego")
        fila_luego.addWidget(lbl_luego)
        self.lbl_titulo_siguiente = EtiquetaMarquesina()
        fila_luego.addWidget(self.lbl_titulo_siguiente)
        columna_ahora_luego.addWidget(frame_luego)

        fila_info.addLayout(columna_ahora_luego)
        fila_info.addStretch()
        layout_grupo.addLayout(fila_info)

        # --- 2) Controles de reproducción — grilla estilo Dinesat
        # (pedido explícito, ronda de recreación fiel del layout real
        # de Dinesat, con foto/descripción de referencia de Santiago:
        # "arriba Stop/Fade/Bajador, abajo Pausa/Cue/Stop-diferido/
        # Automático" -- el "Bajador" de Dinesat, sin usar, se
        # reemplaza acá por el botón azul "HORA/TEMP"). Botón VERDE
        # grande a la izquierda (Play/"Siguiente con fundido"), y a la
        # derecha 2 filas: ARRIBA Stop / Fade / HORA-TEMP, ABAJO
        # Pausa / Cut / Stop diferido / AUTOMÁTICO (el único botón que
        # Ventana 2 no tiene). ---
        barra_botones = QHBoxLayout()
        barra_botones.setSpacing(4)

        # Pedido explícito ("sin texto, recrear el mismo diseño de
        # botones... botón play verde"): solo el glifo.
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("btnPlayPrincipal")
        self.btn_play.setToolTip(
            "Play / Siguiente con fundido\n\n"
            "En silencio: reproduce el ítem elegido.\n"
            "Con algo sonando: pasa al ítem en cola (verde) con fundido."
        )
        # Pedido explícito, ronda posterior ("el botón play es
        # rectangular, hacelo cuadrado tal cual Dinesat, del tamaño
        # proporcional cuadrado como 4 botones de los otros más
        # chicos"): tamaño FIJO cuadrado, mismo valor que Ventana 2.
        self.btn_play.setFixedSize(56, 56)
        self.btn_play.clicked.connect(self.solicitud_play.emit)
        barra_botones.addWidget(self.btn_play)

        grilla = QVBoxLayout()
        grilla.setSpacing(3)

        # Pedido explícito ("sin texto... el resto grises"): Stop/Fade/
        # Pausa/Cut/Stop-diferido quedan solo con su glifo, sin
        # palabra, y sin color de identidad propio (gris genérico, ver
        # gui/styles.py) — la función se distingue por el ícono, como
        # en Dinesat real, y por el tooltip al pasar el mouse.
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(3)
        self.btn_stop = QPushButton("■")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setProperty("class", "btnTransporte")
        self.btn_stop.setToolTip("Stop: corte seco e inmediato.")
        self.btn_fade_stop = QPushButton("◢")
        self.btn_fade_stop.setObjectName("btnFadeStop")
        self.btn_fade_stop.setProperty("class", "btnTransporte")
        self.btn_fade_stop.setToolTip("Fade: fundido hasta apagar el ítem en reproducción.")
        self.btn_stop.clicked.connect(self._on_click_stop)
        self.btn_fade_stop.clicked.connect(self._on_click_fade_stop)
        # Botón "HORA/TEMP" (pedido explícito, en el lugar del
        # "Bajador" de Dinesat, que acá no se usa, ahora celeste):
        # reproduce HORA + TEMPERATURA cortando limpio lo que esté
        # sonando -- misma lógica ya implementada en Ventana 2, ver
        # core/playlist_manager.py:GestorPublicidad.reproducir_hth_manual.
        self.btn_hth_manual = QPushButton("🕐")
        self.btn_hth_manual.setObjectName("btnHthManual")
        self.btn_hth_manual.setProperty("class", "btnTransporte")
        self.btn_hth_manual.setToolTip(
            "Hora/Temperatura: reproduce HORA y TEMPERATURA ahora mismo, "
            "cortando de inmediato lo que esté sonando (sin fundido)."
        )
        self.btn_hth_manual.clicked.connect(self.solicitud_hth_manual.emit)
        fila_superior.addWidget(self.btn_stop)
        fila_superior.addWidget(self.btn_fade_stop)
        fila_superior.addWidget(self.btn_hth_manual)
        grilla.addLayout(fila_superior)

        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(3)
        self.btn_pausa = QPushButton("❚❚")
        self.btn_pausa.setProperty("class", "btnTransporte")
        self.btn_pausa.setToolTip("Pausa.")
        self.btn_cut = QPushButton("✂")
        self.btn_cut.setObjectName("btnCut")
        self.btn_cut.setProperty("class", "btnTransporte")
        self.btn_cut.setToolTip("Cut: corte seco e inmediato al ítem en cola (antes \"Siguiente\").")
        self.btn_stop_diferido = QPushButton("◷")
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
        # AUTOMÁTICO ocupa el 4to lugar de la fila de abajo (pedido
        # explícito, recreando Dinesat: "el famoso AUTOMÁTICO" es el
        # último botón de la fila inferior, exclusivo de Ventana 1).
        fila_inferior.addWidget(self.btn_automatico)
        grilla.addLayout(fila_inferior)

        barra_botones.addLayout(grilla)
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
        # Pedido explícito ("sacá la opción de contraer el árbol, que
        # siempre esté expandido"): sin flechita de expandir/contraer —
        # los bloques ya se agregan expandidos (ver cargar_bloques() y
        # el alta de bloque nuevo), esto solo saca la INTERACCIÓN de
        # colapsarlos a mano.
        self.tree.setItemsExpandable(False)
        self.tree.archivo_soltado.connect(self.archivo_soltado.emit)
        self.tree.itemDoubleClicked.connect(lambda item, columna: self._on_doble_click_item(item))
        # Pedido explícito ("cuando selecciono el bloque horario,
        # permita pintarse de rojo... dejando atento a reproducir el
        # primer ítem" — antes hacía falta doble click sobre el
        # título): un solo click sobre el TÍTULO de un bloque arma
        # (rojo) o encola (verde) igual que el doble click, sin
        # duplicar lógica (ver _on_click_item). Las tandas sueltas
        # siguen necesitando doble click/Enter, sin cambios.
        self.tree.itemClicked.connect(self._on_click_item)
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
            # titulo_bloque_sin_prefijo_hora "autocura" cualquier
            # título ya duplicado por el bug de rondas anteriores del
            # Programador (ver nota en config/settings.py).
            titulo = titulo_bloque_sin_prefijo_hora(hora, bloque.get("titulo", ""))
            nodo_bloque = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
            fuente = nodo_bloque.font(0)
            fuente.setBold(True)
            nodo_bloque.setFont(0, fuente)
            nodo_bloque.setData(0, ROL_HORA_BLOQUE, hora)
            self.tree.addTopLevelItem(nodo_bloque)
            for item in bloque.get("items", []):
                if item.get("es_comando"):
                    self.agregar_comando(
                        nodo_bloque, item.get("tipo_comando", "FMT"), item.get("parametro_comando", ""),
                    )
                    continue
                if item.get("es_aleatorio"):
                    self.agregar_item_aleatorio(
                        nodo_bloque, item.get("categoria_aleatorio") or [],
                        item.get("recursivo_aleatorio", True),
                    )
                    continue
                self.agregar_tanda(
                    nodo_bloque, item.get("titulo", ""), item.get("duracion", ""),
                    item.get("codigo", "—"), item.get("ruta", ""),
                    item.get("punto_inicio_ms") or 0, item.get("punto_fin_ms"),
                    item.get("ganancia_db") or 0.0,
                    item.get("fecha_inicio"), item.get("fecha_fin"),
                )
            nodo_bloque.setExpanded(True)
        self.programacion_cargada.emit()

    def agregar_tanda(self, nodo_bloque, titulo: str, duracion: str, codigo: str, ruta: str = "",
                       punto_inicio_ms: int = 0, punto_fin_ms: int = None, ganancia_db: float = 0.0,
                       fecha_inicio: str = None, fecha_fin: str = None):
        hijo = QTreeWidgetItem([titulo, duracion, codigo])
        hijo.setData(0, Qt.ItemDataRole.UserRole, ruta)
        hijo.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        hijo.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": punto_inicio_ms, "punto_fin_ms": punto_fin_ms, "ganancia_db": ganancia_db,
        })
        # Vigencia de fecha (pedido explícito, opcional): None/None =
        # sin restricción, se emite siempre igual que antes de este
        # cambio. Ver core/playlist_manager.py:_item_valido().
        hijo.setData(0, ROL_VIGENCIA, {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})
        nodo_bloque.addChild(hijo)
        return hijo

    def agregar_comando(self, nodo_bloque, tipo_comando: str, parametro: str):
        """Comando FMT (pedido explícito, encadenado con el
        Musicalizador Avanzado): NO es audio real — sin ruta, sin
        "duración" (no ocupa tiempo de aire). Al llegarle el turno en
        la reproducción, ejecuta su acción y sigue directo al próximo
        ítem real (ver core/playlist_manager.py:GestorPublicidad)."""
        hijo = QTreeWidgetItem([f"▶ {tipo_comando}: {parametro}", "—", "—"])
        hijo.setData(0, Qt.ItemDataRole.UserRole, "")
        hijo.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        hijo.setData(0, ROL_ES_COMANDO, True)
        hijo.setData(0, ROL_TIPO_COMANDO, tipo_comando)
        hijo.setData(0, ROL_PARAMETRO_COMANDO, parametro)
        fondo = QBrush(QColor(COLOR_COMANDO))
        for columna in range(3):
            hijo.setBackground(columna, fondo)
            hijo.setForeground(columna, QBrush(QColor("white")))
        nodo_bloque.addChild(hijo)
        return hijo

    def es_comando(self, item) -> bool:
        return bool(item.data(0, ROL_ES_COMANDO)) if item is not None else False

    def tipo_comando_de_item(self, item):
        return item.data(0, ROL_TIPO_COMANDO)

    def parametro_comando_de_item(self, item):
        return item.data(0, ROL_PARAMETRO_COMANDO)

    def agregar_item_aleatorio(self, nodo_bloque, categoria: list, recursivo: bool = True):
        """Ítem ALEATORIO (pedido explícito, Programador: "para darle
        dinamismo, por ejemplo en separadores"): tampoco tiene una
        ruta FIJA — a diferencia de una tanda normal, guarda el CAMINO
        de una categoría y recién elige un archivo al azar de ahí CADA
        VEZ que le toca sonar (ver GestorPublicidad._reproducir_item),
        nunca el mismo archivo fijado para siempre."""
        titulo_categoria = " / ".join(categoria) if categoria else "(categoría no encontrada)"
        hijo = QTreeWidgetItem([f"🎲 Aleatorio: {titulo_categoria}", "—", "—"])
        hijo.setData(0, Qt.ItemDataRole.UserRole, "")
        hijo.setData(0, ROL_ESTADO_ITEM, ESTADO_NORMAL)
        hijo.setData(0, ROL_ES_ALEATORIO, True)
        hijo.setData(0, ROL_CATEGORIA_ALEATORIO, categoria)
        hijo.setData(0, ROL_RECURSIVO_ALEATORIO, recursivo)
        fondo = QBrush(QColor(COLOR_ALEATORIO))
        for columna in range(3):
            hijo.setBackground(columna, fondo)
            hijo.setForeground(columna, QBrush(QColor("white")))
        nodo_bloque.addChild(hijo)
        return hijo

    def es_aleatorio(self, item) -> bool:
        return bool(item.data(0, ROL_ES_ALEATORIO)) if item is not None else False

    def categoria_aleatorio_de_item(self, item):
        return item.data(0, ROL_CATEGORIA_ALEATORIO)

    def recursivo_aleatorio_de_item(self, item) -> bool:
        valor = item.data(0, ROL_RECURSIVO_ALEATORIO)
        return True if valor is None else bool(valor)

    def corregir_categoria_aleatorio_en_vivo(self, ruta_vieja: list, ruta_nueva: list) -> int:
        """Contraparte EN MEMORIA de `config.settings.
        corregir_referencias_categoria_renombrada()` (que ya corrige lo
        persistido en disco) -- sin esto, el árbol de bloques que
        Ventana 1 tiene YA CARGADO (el que de verdad conduce la
        emisión en este instante) seguiría con la referencia rota
        hasta el próximo reinicio de la app. Recorre todos los bloques/
        ítems del árbol en vivo y actualiza `ROL_CATEGORIA_ALEATORIO`
        donde corresponda. Devuelve cuántos ítems se corrigieron."""
        tocados = 0
        for i in range(self.tree.topLevelItemCount()):
            bloque = self.tree.topLevelItem(i)
            for j in range(bloque.childCount()):
                hijo = bloque.child(j)
                if not self.es_aleatorio(hijo):
                    continue
                ruta_actual = self.categoria_aleatorio_de_item(hijo)
                ruta_corregida = ruta_con_prefijo_reemplazado(ruta_actual, ruta_vieja, ruta_nueva)
                if ruta_corregida != ruta_actual:
                    hijo.setData(0, ROL_CATEGORIA_ALEATORIO, ruta_corregida)
                    tocados += 1
        return tocados

    def analisis_de_item(self, item) -> dict:
        if item is None:
            return {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}
        return item.data(0, ROL_ANALISIS_AUDIO) or {"punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0}

    def vigencia_de_item(self, item) -> dict:
        if item is None:
            return {"fecha_inicio": None, "fecha_fin": None}
        return item.data(0, ROL_VIGENCIA) or {"fecha_inicio": None, "fecha_fin": None}

    def crear_bloque_nuevo(self):
        """Bloque vacío, título por defecto "TANDA - Rotativa" con la
        hora actual como prefijo — pedido explícito (antes decía
        "Bloque"). Queda colapsable como los demás (setExpanded
        controla eso, ya viene expandido vacío)."""
        hora = datetime.now().strftime("%H:%M:%S")
        titulo = "TANDA - Rotativa"
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
    def _on_click_automatico(self):
        """Pedido explícito: confirmar SIEMPRE que el operador toca el
        botón AUTOMÁTICO a mano (tanto para activarlo como para
        desactivarlo) -- a propósito NO pasa por acá el arranque de la
        app (`MainWindow._inicializar_motores_audio` llama a
        `_toggle_automatico()` directo, sin pasar por `clicked`), así
        que nunca interrumpe el inicio con un diálogo. Al hacer click,
        Qt ya invirtió el estado del botón (checkable) -- si el
        operador cancela, hay que revertirlo a mano sin llamar a
        `_toggle_automatico()`, para no emitir ningún cambio real."""
        activar = self.btn_automatico.isChecked()
        if activar:
            texto = (
                "¿Activar el modo AUTOMÁTICO?\n\n"
                "Los bloques horarios de esta ventana se van a disparar "
                "solos por horario, y al terminar Publicidad la radio va "
                "a retomar Emisión sin intervención tuya."
            )
        else:
            texto = (
                "¿Desactivar el modo AUTOMÁTICO?\n\n"
                "Los bloques horarios YA NO se van a disparar solos, y la "
                "vuelta a Emisión al terminar Publicidad tampoco va a ser "
                "automática -- vas a tener que operar la radio a mano."
            )
        respuesta = QMessageBox.question(
            self, "Modo AUTOMÁTICO", texto,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            self.btn_automatico.setChecked(not activar)
            return
        self._toggle_automatico()

    def _toggle_automatico(self):
        self._modo_automatico = self.btn_automatico.isChecked()
        if self._modo_automatico:
            # Pedido explícito ("sin texto"): el botón ya no cambia de
            # texto (antes "AUTO"/"MANUAL") — el glifo queda fijo, el
            # color (gris/rojo) es la señal real. El estado completo
            # sigue explícito en lbl_estado ("Automático Activo"/"Modo
            # Manual") y en el tooltip del botón.
            self.btn_automatico.setProperty("activo", "true")
            self.lbl_estado.setText("Automático Activo")
            self.lbl_estado.setProperty("activo", "true")
        else:
            self.btn_automatico.setProperty("activo", "false")
            self.lbl_estado.setText("Modo Manual")
            self.lbl_estado.setProperty("activo", "false")

        for widget in (self.btn_automatico, self.lbl_estado):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.automatico_cambiado.emit(self._modo_automatico)

    def _avisar_bloqueado_por_automatico(self):
        QMessageBox.information(
            self, "Automático activo",
            "No se puede detener Publicidad mientras el modo AUTOMÁTICO esté\n"
            "activo.\n\nPara detener, primero desactivá el botón AUTOMÁTICO.",
        )

    def _on_click_stop(self):
        # Pedido explícito, SOLO Ventana 1 (Fade-Stop y Stop diferido
        # siguen bloqueados con aviso, sin cambios ahí — ver
        # `_avisar_bloqueado_por_automatico`): con el Automático
        # activo, apretar el botón Stop lo APAGA de una, SIN
        # confirmación, y detiene la reproducción en el mismo gesto —
        # reemplaza el comportamiento anterior de "bloquear con un
        # aviso" que sí sigue teniendo Fade-Stop/Stop diferido.
        # `_toggle_automatico()` se llama DIRECTO, nunca
        # `_on_click_automatico()` (que pide confirmación Sí/No) —
        # mismo patrón ya usado por el arranque de la app para cambiar
        # el modo sin pasar por ningún diálogo. `setChecked()` no
        # emite `clicked`, así que esto no dispara el diálogo de
        # `_on_click_automatico` (conectado a esa señal) por su cuenta.
        if self._modo_automatico:
            self.btn_automatico.setChecked(False)
            self._toggle_automatico()
        self.solicitud_stop.emit()

    def _on_click_fade_stop(self):
        if self._modo_automatico:
            self._avisar_bloqueado_por_automatico()
            return
        self.solicitud_fade_stop.emit()

    def _on_click_stop_diferido(self):
        if self._modo_automatico:
            self._avisar_bloqueado_por_automatico()
            return
        self.solicitud_stop_diferido.emit()

    def set_stop_diferido_armado(self, armado: bool):
        self.btn_stop_diferido.setProperty("armado", "true" if armado else "false")
        self.btn_stop_diferido.style().unpolish(self.btn_stop_diferido)
        self.btn_stop_diferido.style().polish(self.btn_stop_diferido)

    def esta_en_automatico(self) -> bool:
        return self._modo_automatico

    def actualizar_contadores(self, transcurrido: str, restante: str):
        self.lbl_tiempo_transcurrido.setText(transcurrido)
        self.lbl_tiempo_restante.setText(restante)

    def set_indicador_en_vivo(self, activo: bool):
        self.indicador_en_vivo.set_activo(activo)
        self.medidor_nivel.set_activo(activo)

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

    def resetear_reproduccion(self):
        """Ver PanelReproductor.resetear_reproduccion — mismo criterio
        acá: Stop/Fade-Stop/cambio de ventana reinician la barra y los
        contadores, la Pausa normal nunca los toca."""
        self.slider_progreso.setValue(0)
        self.actualizar_contadores("00:00:00", "00:00:00")

    # ------------------------------------------------------------------
    # Máquina de estados de selección — doble click/Enter (misma que
    # Ventana 2, ver core/playlist_manager.py:GestorPublicidad).
    # ------------------------------------------------------------------
    def _on_doble_click_item(self, item):
        # Nodo de bloque (pedido explícito: "doble click en el
        # título... se marque en rojo y cargue listo para reproducir
        # el primer item del bloque"): se emite el bloque TAL CUAL,
        # sin resolver nada acá — GestorPublicidad._on_doble_click()
        # es quien decide qué hacer con un nodo de bloque, delegando en
        # _reproducir_primero_del_bloque() (mismo camino que ya usa el
        # botón Play sobre un bloque seleccionado).
        #
        # Bug real corregido: acá antes se agarraba `item.child(0)` a
        # ciegas, el hijo LITERAL en la posición 0 sin importar si era
        # reproducible — con la mayoría de los archivos con ruta
        # válida esto pasaba desapercibido, pero en cuanto el primer
        # hijo de un bloque queda marcado con error (archivo faltante,
        # ver ROL_ITEM_CON_ERROR), GestorPublicidad._on_doble_click()
        # rechazaba ese ítem puntual y no hacía NADA — ni saltear al
        # siguiente hijo válido, ni avisar. Delegar en
        # _reproducir_primero_del_bloque() reutiliza la MISMA lógica
        # que ya sabe saltear ítems inválidos dentro de un bloque
        # (_primer_item_valido_de), en vez de duplicarla acá.
        self.item_doble_click.emit(item)

    def _on_click_item(self, item, columna):
        """Pedido explícito ("cuando selecciono el bloque horario,
        permita pintarse de rojo, lógicamente, dejando atento a
        reproducir el primer ítem"): un solo click sobre el TÍTULO de
        un bloque (nodo de nivel superior, `item.parent() is None`)
        reutiliza EXACTAMENTE la misma lógica que ya usaba el doble
        click sobre un bloque (`GestorPublicidad._on_doble_click()` ya
        resuelve el primer ítem reproducible del bloque y solo lo ARMA
        en rojo o lo ENCOLA en verde — nunca reproduce nada solo) — se
        emite la misma señal, sin duplicar nada. Clickear una TANDA
        suelta (no el título) NO pasa por acá — sigue necesitando
        doble click/Enter como siempre."""
        if item is not None and item.parent() is None:
            self.item_doble_click.emit(item)

    # ------------------------------------------------------------------
    # Menú contextual (pedido explícito, estructura completa):
    #   Crear/Modificar/Eliminar Programación -> abren el Programador
    #   Cargar Programación -> abre el Programador
    #   Sacar Item / Agregar Item / Reemplazar Item (los 3 funcionales
    #   — Agregar/Reemplazar usan el mismo buscador de biblioteca del
    #   Programador, directo acá, sin necesidad de abrirlo)
    #   Crear Bloque Nuevo (funcional)
    # Todo pide confirmación y nunca corta una reproducción en curso
    # (los ítems rojo/verde no se pueden sacar/reemplazar — ver
    # quitar_item / _bloqueado_por_reproduccion).
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
        accion_reemplazar = menu.addAction("Reemplazar Item")

        menu.addSeparator()
        accion_crear_bloque = menu.addAction("Crear Bloque Nuevo")
        accion_insertar_fmt = menu.addAction("▶ Insertar Comando FMT...")
        accion_insertar_hth = menu.addAction("▶ Insertar Comando HTH...")

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
        elif elegida == accion_agregar:
            self._agregar_item_v1(seleccionados[0] if seleccionados else None)
        elif elegida == accion_reemplazar:
            if len(seleccionados) != 1:
                QMessageBox.information(self, "Reemplazar Item", "Seleccioná un solo ítem para reemplazar.")
            else:
                self._reemplazar_item_v1(seleccionados[0])
        elif elegida == accion_crear_bloque:
            self._confirmar_y_crear_bloque()
        elif elegida == accion_insertar_fmt:
            self._insertar_comando_fmt(seleccionados[0] if seleccionados else None)
        elif elegida == accion_insertar_hth:
            self._insertar_comando_hth(seleccionados[0] if seleccionados else None)

    def _bloque_destino_para_insertar(self, item_referencia):
        """Mismo criterio que el Programador (_bloque_destino_actual):
        el bloque del ítem seleccionado (o su padre, si es una tanda),
        o el ÚLTIMO bloque del árbol si no hay nada útil seleccionado."""
        if item_referencia is not None:
            return item_referencia if item_referencia.parent() is None else item_referencia.parent()
        if self.tree.topLevelItemCount() == 0:
            return None
        return self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)

    def _insertar_comando_fmt(self, item_referencia):
        bloque = self._bloque_destino_para_insertar(item_referencia)
        if bloque is None:
            QMessageBox.information(self, "Insertar Comando FMT", "Primero creá un bloque horario.")
            return
        from gui.dialogo_insertar_comando_fmt import DialogoInsertarComandoFMT
        dialogo = DialogoInsertarComandoFMT(parent=self)
        if dialogo.exec() != DialogoInsertarComandoFMT.DialogCode.Accepted:
            return
        formato = dialogo.formato_elegido()
        if formato:
            self.agregar_comando(bloque, "FMT", formato)

    def _insertar_comando_hth(self, item_referencia):
        bloque = self._bloque_destino_para_insertar(item_referencia)
        if bloque is None:
            QMessageBox.information(self, "Insertar Comando HTH", "Primero creá un bloque horario.")
            return
        from gui.dialogo_insertar_comando_hth import DialogoInsertarComandoHTH
        dialogo = DialogoInsertarComandoHTH(parent=self)
        if dialogo.exec() != DialogoInsertarComandoHTH.DialogCode.Accepted:
            return
        parametro = dialogo.parametro_elegido()
        if parametro:
            self.agregar_comando(bloque, "HTH", parametro)

    def _agregar_item_v1(self, item_referencia):
        """Pedido explícito: habilitar "Agregar Item" del menú
        contextual — mismo buscador de biblioteca a dos columnas que
        ya usa el Programador (gui/dialogo_seleccionar_biblioteca.py),
        directo acá, sin necesidad de abrir el Programador."""
        bloque = self._bloque_destino_para_insertar(item_referencia)
        if bloque is None:
            QMessageBox.information(self, "Agregar Item", "Primero creá un bloque horario.")
            return
        if self._ventana_explorador is None:
            QMessageBox.warning(self, "Agregar Item", "No hay acceso al Explorador (Ventana 3) en esta sesión.")
            return
        from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
        dialogo = DialogoSeleccionarBiblioteca(
            self._ventana_explorador.tree_categorias, permitir_multiple=True,
            titulo="Agregar Ítem a Publicidad", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarBiblioteca.DialogCode.Accepted:
            return
        for registro in dialogo.registros_elegidos():
            self.agregar_tanda(
                bloque, registro.get("titulo", ""), registro.get("duracion", ""),
                registro.get("codigo", "—"), registro.get("ruta", ""),
                registro.get("punto_inicio_ms") or 0, registro.get("punto_fin_ms"),
                registro.get("ganancia_db") or 0.0,
                registro.get("fecha_inicio"), registro.get("fecha_fin"),
            )

    def _reemplazar_item_v1(self, item):
        """Pedido explícito: habilitar "Reemplazar Item" del menú
        contextual — cambia el archivo de una tanda sin moverla de
        lugar, mismo buscador y mismo criterio que "Reemplazar" en el
        Programador."""
        if item is None or item.parent() is None:
            QMessageBox.information(self, "Reemplazar Item", "Seleccioná una tanda (no un bloque) para reemplazar.")
            return
        if self.es_comando(item):
            QMessageBox.information(
                self, "Reemplazar Item",
                "Un Comando (FMT/HTH) no se \"reemplaza\" — sacalo (Sacar Item)\n"
                "y agregá uno nuevo con \"▶ Insertar Comando FMT...\" o\n"
                "\"▶ Insertar Comando HTH...\" si querés cambiar el comando.",
            )
            return
        if self._bloqueado_por_reproduccion(item):
            QMessageBox.information(
                self, "Reemplazar Item",
                "Este ítem está marcado para reproducción (rojo/verde) y no se\n"
                "puede reemplazar hasta que se libere (se elige otro, o termina\n"
                "su reproducción).",
            )
            return
        if self._ventana_explorador is None:
            QMessageBox.warning(self, "Reemplazar Item", "No hay acceso al Explorador (Ventana 3) en esta sesión.")
            return
        from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
        dialogo = DialogoSeleccionarBiblioteca(
            self._ventana_explorador.tree_categorias, permitir_multiple=False,
            titulo="Reemplazar ítem de Publicidad", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarBiblioteca.DialogCode.Accepted:
            return
        registro = dialogo.registro_elegido()
        if not registro:
            return
        item.setText(0, registro.get("titulo") or "Sin título")
        item.setText(1, registro.get("duracion", ""))
        item.setText(2, registro.get("codigo", "—"))
        item.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))
        item.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
        })
        item.setData(0, ROL_VIGENCIA, {
            "fecha_inicio": registro.get("fecha_inicio"), "fecha_fin": registro.get("fecha_fin"),
        })

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
            f"¿Crear una nueva \"{hora} - TANDA - Rotativa\"?",
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
        else:
            self.lbl_titulo_actual.setText("")

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

    def marcar_item_con_error(self, item, con_error: bool):
        """Pedido explícito ("cuando encuentra un item que no está en
        el explorador... marque con una X roja"): pinta/saca el ícono
        de error a la izquierda del título — se llama desde
        GestorPublicidad._item_valido() cada vez que se detecta (o se
        deja de detectar) que el archivo del ítem no existe en disco.
        Puramente visual, nunca toca el ítem ni la biblioteca. Si el
        error se saca (el archivo reapareció) y el ítem ya se había
        marcado "ya reproducido" antes de romperse, restaura ESE
        ícono en vez de dejarlo en blanco — no pisa una marca ajena."""
        if item is None:
            return
        if item.data(0, ROL_ITEM_CON_ERROR) == con_error:
            return  # ya está en ese estado, no hace falta repintar
        item.setData(0, ROL_ITEM_CON_ERROR, con_error)
        if con_error:
            item.setIcon(0, icono_error())
        elif item.data(0, ROL_YA_REPRODUCIDO):
            item.setIcon(0, icono_reproducido())
        else:
            item.setIcon(0, QIcon())

    def _pintar_item(self, item, estado: int):
        """Pinta rojo/verde/normal. Bug real corregido ("el ícono
        'reproducido' se marca al seleccionar, no al reproducir de
        verdad"): antes esta función marcaba ROL_YA_REPRODUCIDO + el
        ícono + el historial persistente como efecto colateral de
        pintar ESTADO_REPRODUCIENDO — pero `_asegurar_rojo_y_verde()`
        (core/playlist_manager.py) pinta rojo la primera tanda con el
        reproductor EN SILENCIO, solo para "dejar algo armado", sin que
        haya sonado un solo segundo de audio. Ahora pintar rojo es
        puramente visual; la marca real de "reproducido" vive en
        `marcar_realmente_reproducido_item()`, que el motor llama SOLO
        en el punto donde el audio arranca de verdad
        (core/playlist_manager.py: `_reproducir_item()`)."""
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

    def marcar_realmente_reproducido_item(self, item):
        """Marca el ícono "ya reproducido" + registra en el historial
        persistente — a diferencia de `marcar_reproduciendo_item()`
        (que solo arma visualmente en rojo, incluso en silencio), esto
        lo debe llamar el motor SOLO en el instante exacto en que el
        audio arranca de verdad (ver nota en `_pintar_item`)."""
        if item is None:
            return
        self.marcar_icono_reproducido_item(item)
        registrar_reproduccion(
            "Publicidad", item.text(0), item.text(2), item.data(0, Qt.ItemDataRole.UserRole) or "",
        )

    def marcar_icono_reproducido_item(self, item):
        """Solo el ícono/rol "ya reproducido", SIN tocar el historial
        persistente — lo usa el ítem ALEATORIO (`_reproducir_item_aleatorio`
        en core/playlist_manager.py), que registra el historial a mano
        con los datos del archivo REAL resuelto (el ítem acá es solo un
        placeholder en el árbol, su propia ruta no sirve para el
        historial)."""
        if item is None:
            return
        item.setData(0, ROL_YA_REPRODUCIDO, True)
        item.setIcon(0, icono_reproducido())
