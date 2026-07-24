"""
gui/ventana_explorador.py
--------------------------------------------------------
Ventana 3 (Derecha): Explorador de Medios.

- Izquierda: árbol de CATEGORÍAS, con subcategorías sin límite de
  niveles (cada categoría puede tener hijas, y esas hijas más
  hijas, etc.).
- Derecha: archivos de la categoría seleccionada — columnas
  Duración / Título / Artista / Categoría / Código (movibles),
  pintadas según el color del género (Música=verde,
  Publicidad=amarillo, Separador=naranja, Pisador=violeta,
  Artística=azul). Es el ORIGEN real del Drag & Drop hacia
  Ventana 1, Ventana 2, la Auxiliar y el Programador.
- Al agregar UN archivo se abre DialogoAgregarArchivo para elegir
  categoría, nombre editorial, artista y género. Al agregar VARIOS
  de una (selección múltiple o arrastre masivo) se abre
  DialogoAgregarArchivosMasivo: una categoría y un género para todo
  el lote, título derivado del nombre de archivo. El código
  correlativo se asigna solo. En ambos casos se dispara el análisis
  de audio (core/analizador_audio.py): recorte de silencios de
  entrada/salida y nivelado de volumen, guardado como metadata no
  destructiva del registro.
- Menú contextual (botón derecho): Importar, Exportar, Reemplazar,
  Eliminar (en lote si hay selección múltiple), Editar (abre el
  editor de audio del sistema).
- Barra de búsqueda (por título/artista) debajo del título, con lupa
  y Enter — filtra la biblioteca completa y muestra los resultados
  acá mismo, sin importar en qué categoría estén.
- Botón "Expandir"/"Restaurar": esta ventana puede ocupar casi toda
  la pantalla principal para tener más lugar de trabajo, y volver a
  su reparto de 3 columnas de siempre con el mismo botón.
- Botones Previo/Stop para preescuchar el archivo seleccionado (se
  llama "Previo" y no "Play" para no confundirlo con la reproducción
  real al aire de Ventana 1/2).

Cada archivo se guarda como un diccionario (ver `_nuevo_registro`)
adentro del propio QTreeWidgetItem de su categoría, en el rol
ROL_ARCHIVOS — así la jerarquía de categorías no tiene límite de
profundidad ni depende de un diccionario plano por nombre.

PERSISTENCIA (config/data/biblioteca.json, vía config/settings.py):
toda la biblioteca (categorías + archivos) se guarda en disco ante
CADA alta, baja, reemplazo o movimiento — no solo al cerrar la app.
Es a propósito: un corte de luz o un apagado forzoso de la PC no
debe perder nada de lo cargado. El único borrado real es manual
(botón Eliminar, con la advertencia correspondiente). El guardado
usa escritura atómica (archivo temporal + rename) para que un corte
de luz a mitad de la escritura tampoco deje el archivo corrupto.
--------------------------------------------------------
"""

import os
import random
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidget,
    QTreeWidgetItem, QPushButton, QFileDialog, QSplitter, QLineEdit,
    QMessageBox, QInputDialog, QMenu, QAbstractItemView, QApplication,
    QLabel,
)
from PySide6.QtCore import Qt, Signal, QUrl, QProcess, QTimer
from PySide6.QtGui import QColor, QBrush, QDesktopServices, QFont

from gui.common_widgets import (
    ArbolOrigenArrastre, ArbolConDrop, ArbolCategoriasConDrop,
    configurar_columnas_ajustables, SliderBusqueda,
)
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.styles import GENERO_COLORES, GENERO_PREFIJOS_CODIGO, color_texto_legible
from gui.dialogo_agregar_archivo import DialogoAgregarArchivo
from gui.dialogo_agregar_archivos_masivo import DialogoAgregarArchivosMasivo
from gui.dialogo_vigencia import DialogoVigencia
from gui.estado_ui import guardar_columnas, restaurar_columnas
from core.analizador_audio import analizar_audio
from core.audio_engine import obtener_duracion_formateada
from core import descargador_youtube
from config.settings import (
    cargar_configuracion, cargar_biblioteca, guardar_biblioteca, tolerancia_silencio_para_genero,
)

EXTENSIONES_SOPORTADAS = (".mp3", ".wav", ".mp4", ".m4a")

# Roles de datos propios (por encima de Qt.ItemDataRole.UserRole)
ROL_ARCHIVOS = Qt.ItemDataRole.UserRole + 20     # en ítem de categoría: list[dict]
ROL_REGISTRO = Qt.ItemDataRole.UserRole + 21     # en ítem de archivo: dict completo

# Orden de columnas de tree_archivos (pedido explícito): Duración
# primero, después Título/Artista/Categoría/Código.
COL_DURACION, COL_TITULO, COL_ARTISTA, COL_CATEGORIA, COL_CODIGO = range(5)


class VentanaExplorador(QWidget):
    """Panel de exploración y gestión de la biblioteca de audio."""

    archivo_agregado = Signal(str)
    archivo_eliminado = Signal(str)
    archivo_movido = Signal(str, str)   # (titulo, nombre_categoria_destino)
    solicitud_play_preview = Signal()
    solicitud_stop_preview = Signal()
    solicitud_buscar_posicion_preview = Signal(int)   # 0-1000 (por mil)
    solicitud_alternar_expansion = Signal()
    busqueda_realizada = Signal(int)    # cantidad de resultados encontrados
    # Pedido explícito ("una barra de preload, que sepa que la PC está
    # trabajando"): emitida ANTES de una operación que puede demorarse
    # con una biblioteca grande (ver `_UMBRAL_ITEMS_PRELOAD`) — MainWindow
    # la conecta directo a su `_mostrar_preload()` de siempre (cursor de
    # espera + mensaje en la barra de estado), mismo mecanismo ya usado
    # para el arranque/cargar música/cargar programación.
    solicitud_preload = Signal(str)

    # Por debajo de esto, mostrar el preload es puro ruido visual (la
    # operación ya es instantánea) — por encima, con una biblioteca de
    # varios miles de ítems, vale la pena avisar que está trabajando.
    _UMBRAL_ITEMS_PRELOAD = 300
    # Milisegundos que se espera sin ninguna otra mutación antes de
    # escribir biblioteca.json de verdad (ver `_guardar_biblioteca_debounced`).
    _DEMORA_GUARDADO_MS = 600
    # Cuántos archivos migra por tick `iniciar_migracion_duracion_al_arrancar()`
    # antes de ceder el control a Qt (vía QTimer.singleShot(0, ...)) --
    # chico a propósito para que la barra de progreso se vea moverse
    # con fluidez en vez de "saltar" en lotes grandes.
    _TAMANO_LOTE_MIGRACION = 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self._en_busqueda = False
        self._arrastrando_slider_preview = False
        self._colores_genero = dict(GENERO_COLORES)
        # Ordenar por columna (pedido explícito): click en el
        # encabezado ordena A-Z, un segundo click en la MISMA columna
        # invierte a Z-A.
        self._columna_orden_actual = None
        self._orden_ascendente = True
        # Guardado de biblioteca.json DEBOUNCED (ver
        # `_guardar_biblioteca_debounced`/`flush_biblioteca_pendiente`).
        self._timer_guardado_biblioteca = QTimer(self)
        self._timer_guardado_biblioteca.setSingleShot(True)
        self._timer_guardado_biblioteca.timeout.connect(self._guardar_biblioteca)
        self._construir_ui()
        self._cargar_biblioteca_inicial()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox("EXPLORADOR DE MEDIOS")
        layout_grupo = QVBoxLayout(grupo)

        # --- Barra de búsqueda (por título/artista) + Expandir/Restaurar ---
        barra_superior = QHBoxLayout()
        self.txt_busqueda = QLineEdit()
        self.txt_busqueda.setPlaceholderText("Buscar por título o artista...")
        self.txt_busqueda.returnPressed.connect(self._buscar)
        self.btn_buscar = QPushButton("🔍")
        self.btn_buscar.setToolTip("Buscar")
        self.btn_buscar.setFixedWidth(36)
        self.btn_buscar.clicked.connect(self._buscar)
        self.btn_limpiar_busqueda = QPushButton("✕")
        self.btn_limpiar_busqueda.setToolTip("Limpiar búsqueda y volver a la categoría")
        self.btn_limpiar_busqueda.setFixedWidth(36)
        self.btn_limpiar_busqueda.clicked.connect(self._limpiar_busqueda)
        self.btn_expandir = QPushButton("⤢ Expandir")
        self.btn_expandir.setToolTip("Expandir esta ventana para trabajar con más visibilidad")
        self.btn_expandir.setProperty("class", "btnCompacto")
        self.btn_expandir.clicked.connect(self.solicitud_alternar_expansion.emit)
        barra_superior.addWidget(self.txt_busqueda)
        barra_superior.addWidget(self.btn_buscar)
        barra_superior.addWidget(self.btn_limpiar_busqueda)
        barra_superior.addWidget(self.btn_expandir)
        layout_grupo.addLayout(barra_superior)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # Bug real corregido (pedido explícito, "el maximizado se va de
        # pantalla, no toma el ancho del display" en 3 computadoras
        # distintas): con `childrenCollapsible=False`, este splitter
        # NUNCA deja que sus dos paneles (categorías/archivos) bajen
        # de su tamaño mínimo natural — eso propaga hacia arriba y
        # termina fijando un piso de ancho para TODA la ventana
        # principal más grande que pantallas chicas/laptops, así que
        # ni maximizar ni ningún resize() podía angostarla lo
        # suficiente para entrar en el display (Qt directamente
        # ignora un tamaño pedido por debajo de ese mínimo). Con
        # `True`, el splitter puede comprimir sus paneles más allá de
        # su tamaño "cómodo" (aparecen scrollbars/se acomodan los
        # controles) en vez de bloquear el resize entero — la ventana
        # ahora SIEMPRE puede achicarse a lo que haga falta.
        self.splitter.setChildrenCollapsible(True)

        # ---------- Columna izquierda: categorías ----------
        panel_categorias = QWidget()
        layout_categorias = QVBoxLayout(panel_categorias)
        layout_categorias.setContentsMargins(0, 0, 0, 0)

        # Pedido explícito ("permití también que pueda ordenar las
        # carpetas de las categorías"): ArbolCategoriasConDrop admite
        # arrastrar una categoría entre sus hermanas para reordenarla,
        # además de seguir aceptando archivos soltados desde afuera
        # (heredado de ArbolConDrop).
        self.tree_categorias = ArbolCategoriasConDrop()
        self.tree_categorias.setObjectName("tree_categorias")
        self.tree_categorias.setHeaderLabels(["Categoría"])
        self.tree_categorias.setColumnCount(1)
        self.tree_categorias.currentItemChanged.connect(self._on_categoria_seleccionada)
        self.tree_categorias.archivos_soltados.connect(self._on_archivos_soltados_en_categoria)
        self.tree_categorias.orden_cambiado.connect(self._guardar_biblioteca_debounced)
        layout_categorias.addWidget(self.tree_categorias)

        # Misma razón que la fila de archivos de abajo: 2 filas de
        # botones en vez de 1 sola, para no forzar tanto ancho mínimo
        # en pantallas anchas pero bajas (ej. 1360x768).
        fila_categorias_1 = QHBoxLayout()
        fila_categorias_2 = QHBoxLayout()
        self.btn_nueva_categoria = QPushButton("＋ Categoría")
        self.btn_nueva_categoria.setToolTip("Nueva categoría de primer nivel")
        self.btn_nueva_subcategoria = QPushButton("＋ Sub")
        self.btn_nueva_subcategoria.setToolTip("Nueva subcategoría dentro de la seleccionada")
        self.btn_eliminar_categoria = QPushButton("✕ Eliminar")
        self.btn_eliminar_categoria.setToolTip("Eliminar categoría")
        self.btn_nueva_categoria.clicked.connect(self._nueva_categoria)
        self.btn_nueva_subcategoria.clicked.connect(self._nueva_subcategoria)
        self.btn_eliminar_categoria.clicked.connect(self._eliminar_categoria)
        for btn in (self.btn_nueva_categoria, self.btn_nueva_subcategoria, self.btn_eliminar_categoria):
            btn.setProperty("class", "btnCompacto")
        fila_categorias_1.addWidget(self.btn_nueva_categoria)
        fila_categorias_1.addWidget(self.btn_nueva_subcategoria)
        fila_categorias_2.addWidget(self.btn_eliminar_categoria)
        layout_categorias.addLayout(fila_categorias_1)
        layout_categorias.addLayout(fila_categorias_2)

        # ---------- Columna derecha: archivos de la categoría ----------
        panel_archivos = QWidget()
        layout_archivos = QVBoxLayout(panel_archivos)
        layout_archivos.setContentsMargins(0, 0, 0, 0)

        self.tree_archivos = ArbolOrigenArrastre()
        self.tree_archivos.setObjectName("tree_archivos")
        self.tree_archivos.setHeaderLabels(["Duración", "Título", "Artista", "Categoría", "Código"])
        self.tree_archivos.setColumnCount(5)
        self.tree_archivos.setRootIsDecorated(False)
        self.tree_archivos.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # Columnas movibles (pedido explícito: orden editable por el
        # usuario), con Duración/Título/Artista/Categoría anchas fijas
        # y Código en Stretch para no quedar nunca tapada.
        configurar_columnas_ajustables(self.tree_archivos, [70, 170, 110, 90])
        self.tree_archivos.header().setSectionsMovable(True)
        self.tree_archivos.header().setMinimumSectionSize(40)
        # Pedido explícito: ordenar por columna al hacer click en su
        # encabezado — A-Z, y un segundo click en la MISMA columna
        # invierte a Z-A. Orden MANUAL (no QTreeWidget.setSortingEnabled)
        # para ordenar por el campo real del registro, no por el texto
        # visible de la celda (ej. Categoría muestra el género).
        self.tree_archivos.header().setSectionsClickable(True)
        self.tree_archivos.header().setSortIndicatorShown(True)
        self.tree_archivos.header().sectionClicked.connect(self._ordenar_por_columna)

        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._mostrar_menu_contextual)

        layout_archivos.addWidget(self.tree_archivos)

        # Pedido explícito (pantalla de 1360px, "se va de ancho"): en
        # vez de 1 sola fila de 4 botones (pedía demasiado ancho
        # mínimo), 2 filas de 2 — cambia ancho por alto, del que hay
        # de sobra en pantallas anchas pero bajas.
        fila_archivos_1 = QHBoxLayout()
        fila_archivos_2 = QHBoxLayout()
        self.btn_agregar = QPushButton("＋ Agregar")
        self.btn_info = QPushButton("✏ Info")
        self.btn_info.setToolTip("Editar información (título, artista, género, categoría) sin tocar el audio")
        self.btn_reemplazar = QPushButton("⟲ Reemplazar")
        self.btn_eliminar = QPushButton("✕ Eliminar")
        self.btn_agregar.clicked.connect(self._agregar_archivos)
        self.btn_info.clicked.connect(self._editar_informacion_archivo)
        self.btn_reemplazar.clicked.connect(self._reemplazar_archivo)
        self.btn_eliminar.clicked.connect(self._eliminar_archivo)
        for btn in (self.btn_agregar, self.btn_info, self.btn_reemplazar, self.btn_eliminar):
            btn.setProperty("class", "btnCompacto")
        fila_archivos_1.addWidget(self.btn_agregar)
        fila_archivos_1.addWidget(self.btn_info)
        fila_archivos_2.addWidget(self.btn_reemplazar)
        fila_archivos_2.addWidget(self.btn_eliminar)
        layout_archivos.addLayout(fila_archivos_1)
        layout_archivos.addLayout(fila_archivos_2)

        # --- Previo (preescucha, Play/Stop) ---
        barra_preview = QHBoxLayout()
        self.indicador_preview = IndicadorEnVivo()
        self.indicador_preview.setToolTip("Sin previo")
        self.btn_play_preview = QPushButton("▶ Previo")
        self.btn_play_preview.setObjectName("btnPlay")
        self.btn_play_preview.setToolTip("Escuchar el archivo seleccionado (no sale al aire)")
        self.btn_stop_preview = QPushButton("■ Stop")
        self.btn_stop_preview.setObjectName("btnStop")
        self.btn_play_preview.clicked.connect(self.solicitud_play_preview.emit)
        self.btn_stop_preview.clicked.connect(self.solicitud_stop_preview.emit)
        self.btn_play_preview.setProperty("class", "btnCompacto")
        self.btn_stop_preview.setProperty("class", "btnCompacto")
        barra_preview.addWidget(self.indicador_preview)
        barra_preview.addWidget(self.btn_play_preview)
        barra_preview.addWidget(self.btn_stop_preview)
        layout_archivos.addLayout(barra_preview)

        # --- Barra de progreso del previo (buscar posición) ---
        self.slider_preview = SliderBusqueda(Qt.Orientation.Horizontal)
        self.slider_preview.setRange(0, 1000)
        self.slider_preview.setToolTip("Arrastrar o hacer clic para adelantar/retroceder el previo")
        self.slider_preview.sliderPressed.connect(self._on_slider_preview_presionado)
        self.slider_preview.sliderReleased.connect(self._on_slider_preview_soltado)
        layout_archivos.addWidget(self.slider_preview)

        # --- Descarga de YouTube (pedido explícito, pensado como
        # "módulo" autocontenido: solo toca este archivo y
        # core/descargador_youtube.py, nunca el resto del programa) ---
        grupo_youtube = QGroupBox("⬇ Descargar de YouTube")
        layout_youtube = QVBoxLayout(grupo_youtube)
        fila_url = QHBoxLayout()
        self.txt_url_youtube = QLineEdit()
        self.txt_url_youtube.setPlaceholderText("Pegá acá el enlace de YouTube (video o playlist)...")
        self.txt_url_youtube.returnPressed.connect(self._descargar_de_youtube)
        self.btn_descargar_youtube = QPushButton("⬇ Descargar")
        self.btn_descargar_youtube.setProperty("class", "btnCompacto")
        self.btn_descargar_youtube.clicked.connect(self._descargar_de_youtube)
        fila_url.addWidget(self.txt_url_youtube)
        fila_url.addWidget(self.btn_descargar_youtube)
        layout_youtube.addLayout(fila_url)
        self.lbl_estado_youtube = QLabel("")
        self.lbl_estado_youtube.setStyleSheet("color: #999; font-size: 8pt;")
        layout_youtube.addWidget(self.lbl_estado_youtube)
        layout_archivos.addWidget(grupo_youtube)

        self.splitter.addWidget(panel_categorias)
        self.splitter.addWidget(panel_archivos)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([140, 260])

        layout_grupo.addWidget(self.splitter)
        layout_principal.addWidget(grupo)

    # ------------------------------------------------------------------
    # Previo (preescucha): indicador "en vivo" + barra de progreso.
    # Pedido explícito: SOLO el botón "▶ Previo" dispara la
    # reproducción — antes también el doble click en la lista, y a
    # veces se disparaba solo al arrastrar seguido hacia otras
    # ventanas (un guard de 400ms lo mitigaba, pero seguía pasando).
    # Sacar el trigger del doble click de raíz lo resuelve del todo.
    # ------------------------------------------------------------------
    def set_indicador_en_vivo(self, activo: bool):
        self.indicador_preview.set_activo(activo)
        self.indicador_preview.setToolTip("Escuchando el previo" if activo else "Sin previo")

    def _on_slider_preview_presionado(self):
        self._arrastrando_slider_preview = True

    def _on_slider_preview_soltado(self):
        self._arrastrando_slider_preview = False
        self.solicitud_buscar_posicion_preview.emit(self.slider_preview.value())

    def actualizar_progreso_preview(self, permille: int):
        if self._arrastrando_slider_preview:
            return
        self.slider_preview.setValue(max(0, min(1000, permille)))

    # ------------------------------------------------------------------
    # Expandir/Restaurar (lo maneja MainWindow, que es dueña del
    # splitter principal de las 3 ventanas).
    # ------------------------------------------------------------------
    def set_expandido(self, expandido: bool):
        self.btn_expandir.setText("⤡ Restaurar" if expandido else "⤢ Expandir")
        self.btn_expandir.setToolTip(
            "Volver al reparto de 3 columnas" if expandido
            else "Expandir esta ventana para trabajar con más visibilidad"
        )

    # ------------------------------------------------------------------
    # Búsqueda por título/artista (barra debajo del título). Filtra
    # TODA la biblioteca sin importar la categoría, y muestra los
    # resultados en el mismo tree_archivos. Bug real corregido
    # (pedido explícito, "bloquea la opción de elegir una categoría
    # y/o moverse en ella"): antes el árbol de categorías se
    # DESHABILITABA por completo mientras se buscaba — en vez de eso,
    # ahora queda siempre clickeable, y elegir una categoría (o tocar
    # cualquiera de los 3 botones de abajo) limpia la búsqueda sola,
    # ver `_salir_de_busqueda_si_corresponde()`.
    # ------------------------------------------------------------------
    def _buscar(self):
        texto = self.txt_busqueda.text().strip().lower()
        if not texto:
            self._limpiar_busqueda()
            return

        resultados = []

        def visitar(item):
            # _registros_de_categoria() (no `item.data(0, ROL_ARCHIVOS)`
            # directo) para que una búsqueda amplia también aproveche
            # para migrar y persistir la duración cacheada de TODA
            # categoría que toca en el camino — de paso "autocura" el
            # resto de la biblioteca, no solo lo que matchea el texto.
            for registro in self._registros_de_categoria(item):
                titulo = (registro.get("titulo") or "").lower()
                artista = (registro.get("artista") or "").lower()
                if texto in titulo or texto in artista:
                    resultados.append(registro)

        self._para_cada_categoria(visitar)

        self._en_busqueda = True
        self.tree_archivos.clear()
        self._llenar_tree_archivos(resultados)

        self.busqueda_realizada.emit(len(resultados))

    def _limpiar_busqueda(self):
        if not self._en_busqueda and not self.txt_busqueda.text():
            return
        self._en_busqueda = False
        self.txt_busqueda.clear()
        self._on_categoria_seleccionada(self._categoria_actual(), None)

    def _salir_de_busqueda_si_corresponde(self):
        """Pedido explícito: elegir una categoría, o tocar cualquiera
        de los 3 botones de abajo (＋ Categoría/＋ Sub/✕ Eliminar)
        mientras se está buscando, ya no queda bloqueado — limpia la
        búsqueda sola en vez de ignorar el click. A diferencia de
        `_limpiar_busqueda()`, esta NO refresca `tree_archivos` — el
        llamador (`_on_categoria_seleccionada` o el handler del botón)
        ya se encarga de eso a continuación."""
        if self._en_busqueda:
            self._en_busqueda = False
            self.txt_busqueda.clear()

    # ------------------------------------------------------------------
    # Persistencia (config/data/biblioteca.json) — ver nota al inicio
    # del archivo. Se guarda ante cada mutación, no solo al cerrar.
    # ------------------------------------------------------------------
    def recargar_biblioteca_desde_disco(self):
        """Público (a diferencia de _cargar_biblioteca_inicial):
        pedido explícito para poder refrescar el árbol EN VIVO después
        de una reanalización en bloque (config/settings.reanalizar_
        biblioteca) hecha por fuera de esta ventana — sin esto, el
        operador tendría que cerrar y reabrir la app para ver los
        nuevos puntos de recorte."""
        self._cargar_categorias_desde_datos(cargar_biblioteca())

    def _cargar_biblioteca_inicial(self):
        categorias_guardadas = cargar_biblioteca()
        if categorias_guardadas:
            self._cargar_categorias_desde_datos(categorias_guardadas)
        # Si no hay biblioteca.json todavía (instalación nueva), arranca
        # vacío — antes se cargaban categorías de ejemplo (Música,
        # Publicidad, etc.), pero eran solo para probar la app durante
        # el desarrollo; a pedido explícito ya no se crean solas, el
        # operador arma sus propias categorías desde cero con archivos
        # reales. Una biblioteca.json YA EXISTENTE nunca se toca acá.

    def _guardar_biblioteca(self):
        guardar_biblioteca(self._serializar_biblioteca())

    def _guardar_biblioteca_debounced(self):
        """Bug real de fondo con una biblioteca de ~10-12mil archivos
        ("el JSON parece trabarse"): `_guardar_biblioteca()` serializa
        TODA la biblioteca (recursivo, todas las categorías) y reescribe
        el archivo entero con `fsync()` — antes esto se disparaba
        SINCRÓNICO en el hilo de la GUI ante CADA mutación individual
        (agregar un archivo, moverlo, reordenar una categoría...), así
        que una sesión de edición con varias acciones seguidas (ej.
        arrastrar 20 archivos uno por uno a otra categoría) reescribía
        el archivo entero 20 veces en fila, cada una bloqueando la UI
        un instante.

        Ahora la mayoría de los llamadores usan ESTA versión: arranca
        (o reinicia, si ya había una en curso) un timer de
        `_DEMORA_GUARDADO_MS` — varias mutaciones seguidas en ráfaga
        terminan escribiendo el archivo UNA sola vez, recién cuando la
        ráfaga se calma. Mismo patrón de debounce ya usado en este
        proyecto para la persistencia de Emisión/Publicidad
        (`core/gestor_emision.py`/`core/playlist_manager.py`).

        La importación masiva (que ya hace UN solo guardado al final
        de por sí, después de procesar todo el lote) y el cierre de la
        aplicación (`flush_biblioteca_pendiente()`, para no perder la
        última ráfaga de cambios si se cierra el programa antes de que
        el timer llegue a disparar solo) siguen usando el guardado
        INMEDIATO."""
        self._timer_guardado_biblioteca.start(self._DEMORA_GUARDADO_MS)

    def flush_biblioteca_pendiente(self):
        """Si hay un guardado debounced esperando, lo aplica YA MISMO
        — pensado para llamarse antes de cerrar la aplicación
        (`MainWindow.closeEvent`), así ningún cambio reciente se
        pierde por cerrar el programa antes de que el timer dispare
        solo."""
        if self._timer_guardado_biblioteca.isActive():
            self._timer_guardado_biblioteca.stop()
            self._guardar_biblioteca()

    def _serializar_biblioteca(self) -> list:
        return [
            self._serializar_categoria(self.tree_categorias.topLevelItem(i))
            for i in range(self.tree_categorias.topLevelItemCount())
        ]

    def _serializar_categoria(self, item: QTreeWidgetItem) -> dict:
        return {
            "nombre": item.text(0),
            "archivos": item.data(0, ROL_ARCHIVOS) or [],
            "subcategorias": [self._serializar_categoria(item.child(i)) for i in range(item.childCount())],
        }

    def _cargar_categorias_desde_datos(self, categorias: list):
        self.tree_categorias.clear()
        for datos_categoria in categorias:
            self._deserializar_categoria(datos_categoria, None)
        if self.tree_categorias.topLevelItemCount() > 0:
            self.tree_categorias.setCurrentItem(self.tree_categorias.topLevelItem(0))
        self.tree_categorias.expandAll()

    def _deserializar_categoria(self, datos: dict, item_padre) -> QTreeWidgetItem:
        item = self._crear_item_categoria(item_padre, datos.get("nombre", ""))
        item.setData(0, ROL_ARCHIVOS, datos.get("archivos", []))
        for sub in datos.get("subcategorias", []):
            self._deserializar_categoria(sub, item)
        return item

    # ------------------------------------------------------------------
    def _crear_item_categoria(self, item_padre, nombre: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([nombre])
        item.setData(0, ROL_ARCHIVOS, [])
        if item_padre is None:
            self.tree_categorias.addTopLevelItem(item)
        else:
            item_padre.addChild(item)
        self._aplicar_estilo_por_nivel(item, item_padre)
        return item

    @staticmethod
    def _aplicar_estilo_por_nivel(item: QTreeWidgetItem, item_padre):
        """Nivel 1 (categoría raíz): negrita + MAYÚSCULAS. Nivel 2
        (subcategoría directa): negrita, sin tocar mayúsculas/minúsculas.
        Nivel 3 en adelante: sin nada especial (como estaba).

        El "MAYÚSCULAS" es solo de PINTADO (QFont.Capitalization.AllUppercase)
        — el texto real del ítem (item.text(0), lo que se guarda en
        biblioteca.json vía _serializar_categoria) nunca se toca, para
        no pisar el nombre original guardado en disco."""
        fuente = item.font(0)
        if item_padre is None:
            fuente.setBold(True)
            fuente.setCapitalization(QFont.Capitalization.AllUppercase)
        elif item_padre.parent() is None:
            fuente.setBold(True)
            fuente.setCapitalization(QFont.Capitalization.MixedCase)
        else:
            fuente.setBold(False)
            fuente.setCapitalization(QFont.Capitalization.MixedCase)
        item.setFont(0, fuente)

    def _categoria_actual(self):
        return self.tree_categorias.currentItem()

    def _on_categoria_seleccionada(self, actual, anterior):
        # Bug real corregido ("bloquea la opción de elegir una
        # categoría y/o moverse en ella" mientras se busca): antes
        # este chequeo ignoraba por completo el cambio de categoría —
        # ahora se sale de la búsqueda sola (si había una en curso) y
        # sigue mostrando la categoría recién elegida con normalidad.
        self._salir_de_busqueda_si_corresponde()
        self.tree_archivos.clear()
        if actual is None:
            return
        registros = self._registros_de_categoria(actual)
        self._llenar_tree_archivos(registros)

    def _registros_de_categoria(self, item_categoria: QTreeWidgetItem) -> list:
        """Lee los archivos de una categoría (`ROL_ARCHIVOS`) y, si
        alguno todavía no tiene la duración cacheada, la calcula y la
        escribe DE VUELTA en el ítem de categoría.

        Bug real de fondo encontrado en esta ronda, mucho más
        importante que parecía a primera vista: `QTreeWidgetItem.data()`
        para roles custom (por encima de `Qt.UserRole`, como
        `ROL_ARCHIVOS`) devuelve una COPIA del objeto Python guardado
        — trampa real de PySide6 ya documentada varias veces en este
        proyecto para otros roles. La "migración silenciosa" de
        duración (`_agregar_fila_archivo`) mutaba esa COPIA
        (`registro["duracion"] = ...`), pero nunca la volvía a
        escribir con `.setData()` — así que la migración NUNCA quedaba
        cacheada de verdad: cada vez que se volvía a leer
        `item.data(0, ROL_ARCHIVOS)` (cada click en la categoría, cada
        búsqueda que la tocara) se obtenía una copia FRESCA sin la
        duración, y volvía a recalcularse desde cero, pagando el costo
        de mutagen por archivo una y otra vez, para siempre — no solo
        "en cada sesión" como decía el comentario original, sino en
        CADA VISTA. Con una biblioteca de varios miles de archivos sin
        duración cacheada (ej. migrada por fuera de las altas
        normales de la app, que sí la calculan al importar), esto
        alcanza para explicar por completo el "se traba al ver los
        ítems de la categoría" reportado.

        Corregido acá, en el ÚNICO lugar que lee `ROL_ARCHIVOS` de una
        categoría para MOSTRARLA (`_on_categoria_seleccionada` y
        `_buscar`, ver más abajo): si migró algo, se escribe la lista
        entera de vuelta con `item_categoria.setData(...)` (ahora sí
        persiste en la data real del ítem, no en una copia
        descartable) y se dispara un guardado debounced — la próxima
        vez que se vea esta categoría, ya no hace falta recalcular
        nada."""
        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        hubo_migracion = False
        for registro in registros:
            if not registro.get("duracion"):
                registro["duracion"] = obtener_duracion_formateada(registro.get("ruta", ""))
                hubo_migracion = True
        if hubo_migracion:
            item_categoria.setData(0, ROL_ARCHIVOS, registros)
            self._guardar_biblioteca_debounced()
        return registros

    def iniciar_migracion_duracion_al_arrancar(self, callback_iniciar=None, callback_progreso=None, callback_terminado=None):
        """Pedido explícito ("necesito fluidez... se congela al leer
        una categoría"): en vez de migrar la duración faltante de
        forma LAZY (la primera vez que se ve cada categoría — ver
        `_registros_de_categoria()` — que es justo lo que se sentía
        como una traba real, incluso con esa función ya corrigiendo
        que quede persistida), esto la migra TODA de una sola vez al
        ARRANCAR el programa, con una barra de progreso GRÁFICA real
        (`gui/dialogo_preload_biblioteca.py`).

        Encaja con un dato clave que dio Santiago: la PC se reinicia
        sola todos los días a las 00hs — pagar este costo (real,
        mutagen tiene que abrir cada archivo) UNA VEZ por reinicio
        (en la práctica, una sola vez EN TOTAL — una vez persistido,
        el próximo reinicio no encuentra nada para migrar y esto
        directamente no hace nada) es mucho mejor que pagarlo a los
        tropezones cada vez que se abre una categoría distinta
        durante el uso real del día.

        NUNCA es un solo bucle síncrono gigante — corre en LOTES
        chicos (`_TAMANO_LOTE_MIGRACION`) encadenados vía
        `QTimer.singleShot(0, ...)`, cediendo el control a Qt entre
        lotes para que la interfaz (el medidor de nivel decorativo,
        la propia barra de progreso) siga respirando en vez de
        congelarse de punta a punta — sigue siendo trabajo síncrono en
        el hilo principal (esta app nunca usó threading), pero
        PARTIDO en pedazos con puntos de respiro reales.

        Para cada categoría, se lee la copia UNA sola vez
        (`item.data(0, ROL_ARCHIVOS)`, guardada en `estado` mientras
        dura el trabajo de esa categoría — puede abarcar varios
        lotes/ticks si es grande) y se escribe de vuelta UNA sola vez
        al terminarla (`item.setData(...)`) — evita tanto el bug real
        de la copia descartable de PySide6 (ver
        `_registros_de_categoria`) como recopiar la lista entera en
        cada tick de más.

        `callback_iniciar(total)`: se llama UNA vez, ANTES de empezar
        a migrar nada, con el total de archivos pendientes — si es 0
        (el caso normal tras el primer arranque con esta ronda), no se
        llama a ningún otro callback y no se hace nada más.
        `callback_progreso(hechos, total)`: en cada lote.
        `callback_terminado(hechos)`: al final, ya con todo guardado
        en disco."""
        categorias_con_archivos = []

        def recolectar(item):
            if item.data(0, ROL_ARCHIVOS):
                categorias_con_archivos.append(item)

        self._para_cada_categoria(recolectar)

        total_pendientes = sum(
            1
            for item in categorias_con_archivos
            for registro in (item.data(0, ROL_ARCHIVOS) or [])
            if not registro.get("duracion")
        )

        if callback_iniciar:
            callback_iniciar(total_pendientes)
        if total_pendientes == 0:
            return

        estado = {"idx_categoria": 0, "idx_archivo": 0, "hechos": 0, "registros_en_curso": None}

        def procesar_lote():
            procesados_este_lote = 0
            while procesados_este_lote < self._TAMANO_LOTE_MIGRACION and estado["idx_categoria"] < len(categorias_con_archivos):
                item = categorias_con_archivos[estado["idx_categoria"]]
                if estado["registros_en_curso"] is None:
                    estado["registros_en_curso"] = item.data(0, ROL_ARCHIVOS) or []
                registros = estado["registros_en_curso"]

                i = estado["idx_archivo"]
                while i < len(registros) and procesados_este_lote < self._TAMANO_LOTE_MIGRACION:
                    if not registros[i].get("duracion"):
                        registros[i]["duracion"] = obtener_duracion_formateada(registros[i].get("ruta", ""))
                        estado["hechos"] += 1
                        procesados_este_lote += 1
                    i += 1
                estado["idx_archivo"] = i

                if i >= len(registros):
                    item.setData(0, ROL_ARCHIVOS, registros)
                    estado["idx_categoria"] += 1
                    estado["idx_archivo"] = 0
                    estado["registros_en_curso"] = None

            if callback_progreso:
                callback_progreso(estado["hechos"], total_pendientes)

            if estado["idx_categoria"] < len(categorias_con_archivos):
                QTimer.singleShot(0, procesar_lote)
            else:
                # Guardado INMEDIATO (no debounced) a propósito acá:
                # esto corre antes de mostrar la ventana principal, y
                # queremos la garantía de que ya quedó escrito en disco
                # antes de avisar "terminado" y dejar seguir el arranque.
                self._guardar_biblioteca()
                if callback_terminado:
                    callback_terminado(estado["hechos"])

        QTimer.singleShot(0, procesar_lote)

    def _agregar_fila_archivo(self, registro: dict, insertar: bool = True):
        """Arma el QTreeWidgetItem de una fila. Con `insertar=True`
        (default, usado por las altas de UN solo archivo) lo agrega
        directo al árbol y lo devuelve. Con `insertar=False` (usado
        por `_llenar_tree_archivos`, ver más abajo) devuelve el ítem
        SIN insertarlo — para que el llamador pueda insertar TODOS los
        ítems de un lote de una sola vez con `addTopLevelItems()`."""
        duracion = registro.get("duracion")
        if not duracion:
            # Red de seguridad, no el punto principal de cacheo (ver
            # `_registros_de_categoria()`, que además persiste el
            # cálculo de vuelta en la categoría) — cubre el caso de
            # que ALGO llegue acá con la duración todavía sin calcular
            # por otro camino, para no mostrar la columna vacía.
            duracion = obtener_duracion_formateada(registro.get("ruta", ""))
            registro["duracion"] = duracion

        item = QTreeWidgetItem()
        item.setText(COL_DURACION, duracion)
        item.setText(COL_TITULO, registro.get("titulo", ""))
        item.setText(COL_ARTISTA, registro.get("artista", ""))
        item.setText(COL_CATEGORIA, registro.get("genero", ""))
        item.setText(COL_CODIGO, registro.get("codigo", ""))
        item.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))  # para el drag
        item.setData(0, ROL_REGISTRO, registro)
        self._pintar_por_genero(item, registro.get("genero", ""))
        if insertar:
            self.tree_archivos.addTopLevelItem(item)
        return item

    def _llenar_tree_archivos(self, registros: list):
        """Bug real de rendimiento con una biblioteca de ~10-12mil
        archivos ("el JSON parece trabarse... al ver los ítems en la
        categoría"): antes, ver una categoría con miles de archivos de
        golpe (frecuente tras una importación masiva — un solo lote
        grande suele caer en UNA sola categoría) armaba cada
        QTreeWidgetItem con `addTopLevelItem()` UNO POR UNO, cada
        inserción disparando su propio recálculo de layout/repintado
        interno de Qt — con miles de ítems eso se siente como una
        traba real, aunque los datos ya estén 100% en memoria (esto
        NUNCA toca disco: `cargar_biblioteca()` ya leyó TODO
        biblioteca.json una sola vez al arrancar la app).

        Corregido en dos frentes, mismo criterio para cualquier
        rebuild grande de `tree_archivos` (selección de categoría,
        búsqueda, reordenar por columna):
        1. `setUpdatesEnabled(False)` mientras se arman TODOS los
           ítems, y recién se reactiva al final — Qt no repinta nada
           intermedio, un solo repaint al terminar.
        2. Los ítems se arman SUELTOS (`_agregar_fila_archivo(...,
           insertar=False)`) y se insertan TODOS DE UNA con
           `addTopLevelItems(lista)` en vez de una llamada por ítem.

        Además, con una lista lo bastante grande (`_UMBRAL_ITEMS_PRELOAD`)
        avisa que está trabajando (pedido explícito: "una barra de
        preload, cuestión que sepa que la PC está trabajando") y
        procesa eventos cada tanto durante el armado — mismo patrón ya
        usado para la importación masiva — para que la ventana no se
        vea "colgada" mientras arma miles de ítems en hardware modesto.

        El cacheo REAL de la duración migrada (y su guardado en disco)
        ya pasó por `_registros_de_categoria()` antes de llegar acá —
        ver esa función para el bug de fondo que corrige (la copia que
        devuelve `QTreeWidgetItem.data()` para roles custom)."""
        cantidad = len(registros)
        aviso_grande = cantidad >= self._UMBRAL_ITEMS_PRELOAD
        if aviso_grande:
            self.solicitud_preload.emit(f"Cargando {cantidad} archivos...")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.tree_archivos.setUpdatesEnabled(False)
        try:
            items = []
            for indice, registro in enumerate(registros):
                items.append(self._agregar_fila_archivo(registro, insertar=False))
                if aviso_grande and indice % 500 == 0:
                    QApplication.processEvents()
            self.tree_archivos.addTopLevelItems(items)
        finally:
            self.tree_archivos.setUpdatesEnabled(True)
            if aviso_grande:
                QApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------
    # Ordenar por columna (pedido explícito): click en el encabezado.
    # ------------------------------------------------------------------
    _CAMPO_POR_COLUMNA = {
        COL_DURACION: "duracion",
        COL_TITULO: "titulo",
        COL_ARTISTA: "artista",
        COL_CATEGORIA: "genero",
        COL_CODIGO: "codigo",
    }

    def _ordenar_por_columna(self, columna: int):
        campo = self._CAMPO_POR_COLUMNA.get(columna)
        if campo is None:
            return

        if columna == self._columna_orden_actual:
            self._orden_ascendente = not self._orden_ascendente
        else:
            self._columna_orden_actual = columna
            self._orden_ascendente = True

        registros = [
            self.tree_archivos.topLevelItem(i).data(0, ROL_REGISTRO)
            for i in range(self.tree_archivos.topLevelItemCount())
        ]
        registros = [r for r in registros if r is not None]
        # Duración ya viene en formato "HH:MM:SS" con ceros a la
        # izquierda (obtener_duracion_formateada) — el orden lexicográfico
        # de esa cadena coincide con el orden cronológico real, no hace
        # falta parsear a segundos.
        registros.sort(
            key=lambda r: (r.get(campo) or "").lower() if isinstance(r.get(campo), str) else (r.get(campo) or ""),
            reverse=not self._orden_ascendente,
        )

        self.tree_archivos.clear()
        self._llenar_tree_archivos(registros)

        orden_qt = Qt.SortOrder.AscendingOrder if self._orden_ascendente else Qt.SortOrder.DescendingOrder
        self.tree_archivos.header().setSortIndicator(columna, orden_qt)

    def _pintar_por_genero(self, item: QTreeWidgetItem, genero: str):
        color_hex = self._colores_genero.get(genero)
        if not color_hex:
            # Sin color asignado (opción explícita en Configuración) o
            # género desconocido: fondo/texto por defecto del tema.
            for columna in range(item.columnCount()):
                item.setBackground(columna, QBrush())
                item.setForeground(columna, QBrush())
            return
        fondo = QBrush(QColor(color_hex))
        texto = QBrush(QColor(color_texto_legible(color_hex)))
        for columna in range(item.columnCount()):
            item.setBackground(columna, fondo)
            item.setForeground(columna, texto)

    def repintar_colores_genero(self):
        """Refresca la paleta desde Configuración y repinta todas las
        filas visibles — llamado tras guardar Configuración (pedido
        explícito: colores por género editables, incluso "sin color")."""
        self._colores_genero = cargar_configuracion()["apariencia"]["colores_genero"]
        raiz = self.tree_archivos.invisibleRootItem()
        for i in range(raiz.childCount()):
            item = raiz.child(i)
            registro = item.data(0, ROL_REGISTRO) or {}
            self._pintar_por_genero(item, registro.get("genero", ""))

    # ------------------------------------------------------------------
    # Gestión de categorías (sin límite de niveles)
    # ------------------------------------------------------------------
    def _nueva_categoria(self):
        self._salir_de_busqueda_si_corresponde()
        nombre, ok = QInputDialog.getText(self, "Nueva categoría", "Nombre de la categoría:")
        if not ok or not nombre.strip():
            return
        item = self._crear_item_categoria(None, nombre.strip())
        self.tree_categorias.setCurrentItem(item)
        self._guardar_biblioteca_debounced()

    def _nueva_subcategoria(self):
        self._salir_de_busqueda_si_corresponde()
        padre = self._categoria_actual()
        if padre is None:
            QMessageBox.information(self, "Subcategoría", "Primero seleccioná la categoría dentro de la cual crearla.")
            return
        nombre, ok = QInputDialog.getText(self, "Nueva subcategoría", f"Nombre (dentro de '{padre.text(0)}'):")
        if not ok or not nombre.strip():
            return
        item = self._crear_item_categoria(padre, nombre.strip())
        padre.setExpanded(True)
        self.tree_categorias.setCurrentItem(item)
        self._guardar_biblioteca_debounced()

    def _eliminar_categoria(self):
        self._salir_de_busqueda_si_corresponde()
        item = self._categoria_actual()
        if item is None:
            return
        config = cargar_configuracion()
        if config["general"]["confirmar_antes_de_eliminar"]:
            respuesta = QMessageBox.question(
                self, "Eliminar categoría",
                f"¿Eliminar '{item.text(0)}' y todo su contenido (subcategorías y archivos)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        padre = item.parent()
        if padre:
            padre.removeChild(item)
        else:
            indice = self.tree_categorias.indexOfTopLevelItem(item)
            self.tree_categorias.takeTopLevelItem(indice)
        self._guardar_biblioteca_debounced()

    # ------------------------------------------------------------------
    # Alta de archivos: UNO -> diálogo completo (título/artista/género
    # editables); VARIOS (selección múltiple o arrastre masivo) ->
    # un solo diálogo de categoría+género para todo el lote.
    # ------------------------------------------------------------------
    def _agregar_archivos(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Agregar archivos de audio", os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.mp4 *.m4a)",
        )
        if not rutas:
            return

        rutas_validas = [ruta for ruta in rutas if ruta.lower().endswith(EXTENSIONES_SOPORTADAS)]
        if not rutas_validas:
            return

        categoria_sugerida = self._categoria_actual()
        if len(rutas_validas) == 1:
            self._dar_de_alta_archivo(rutas_validas[0], categoria_sugerida)
        else:
            self._importar_archivos_masivo(rutas_validas, categoria_sugerida)

    def _dar_de_alta_archivo(self, ruta: str, categoria_sugerida):
        dialogo = DialogoAgregarArchivo(ruta, self.tree_categorias, categoria_sugerida, parent=self)
        if dialogo.exec() != DialogoAgregarArchivo.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return

        config = cargar_configuracion()
        # Pedido explícito ("corte de silencio estricto"): Publicidad
        # y Separadores usan una tolerancia sin margen — ver
        # config/settings.py:tolerancia_silencio_para_genero().
        tolerancia = tolerancia_silencio_para_genero(config, datos["genero"])
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)
        analisis = analizar_audio(ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio)

        registro = {
            "titulo": datos["titulo"],
            "artista": datos["artista"],
            "genero": datos["genero"],
            "codigo": datos["codigo"],
            "ruta": ruta,
            "duracion": obtener_duracion_formateada(ruta),
            "punto_inicio_ms": analisis["punto_inicio_ms"],
            "punto_fin_ms": analisis["punto_fin_ms"] or None,
            "ganancia_db": analisis["ganancia_db"],
            "analizado": analisis["analizado"],
            # Vigencia de fecha (pedido explícito, opcional): None =
            # sin restricción. Editable después con el menú contextual
            # "Vigencia..." (ver _editar_vigencia).
            "fecha_inicio": datos.get("fecha_inicio"),
            "fecha_fin": datos.get("fecha_fin"),
        }

        item_categoria = datos["item_categoria"]
        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        registros.append(registro)
        item_categoria.setData(0, ROL_ARCHIVOS, registros)

        if item_categoria is self._categoria_actual() and not self._en_busqueda:
            self._agregar_fila_archivo(registro)

        self._guardar_biblioteca_debounced()
        self.archivo_agregado.emit(ruta)

    def _importar_archivos_masivo(self, rutas: list, categoria_sugerida):
        """Un solo diálogo para TODO el lote: se elige una categoría y
        un género que se aplican a todos, el título de cada uno sale
        del nombre de archivo. Pensado para cargar de golpe."""
        dialogo = DialogoAgregarArchivosMasivo(rutas, self.tree_categorias, categoria_sugerida, parent=self)
        if dialogo.exec() != DialogoAgregarArchivosMasivo.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return

        item_categoria = datos["item_categoria"]
        genero = datos["genero"]
        config = cargar_configuracion()
        tolerancia = tolerancia_silencio_para_genero(config, genero)
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)

        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        siguiente_numero = len(registros) + 1
        prefijo = GENERO_PREFIJOS_CODIGO.get(genero, "GEN")

        # Pedido explícito ("hay operaciones que demoran... deberíamos
        # poner un preload"): importar en lote analiza CADA archivo
        # (pydub/ffmpeg), lento de verdad con una biblioteca grande
        # (700 archivos, caso real de Santiago) — sin threading en
        # esta app (nunca se usó, ver CLAUDE.md), el cursor de espera +
        # un `processEvents()` periódico es lo que evita que se vea
        # "colgada" mientras procesa, aunque siga siendo bloqueante.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for indice, ruta in enumerate(rutas):
                analisis = analizar_audio(
                    ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio,
                )
                registro = {
                    "titulo": os.path.splitext(os.path.basename(ruta))[0],
                    "artista": "",
                    "genero": genero,
                    "codigo": f"{prefijo}{siguiente_numero:05d}",
                    "ruta": ruta,
                    "duracion": obtener_duracion_formateada(ruta),
                    "punto_inicio_ms": analisis["punto_inicio_ms"],
                    "punto_fin_ms": analisis["punto_fin_ms"] or None,
                    "ganancia_db": analisis["ganancia_db"],
                    "analizado": analisis["analizado"],
                    "fecha_inicio": None,
                    "fecha_fin": None,
                }
                registros.append(registro)
                siguiente_numero += 1
                if indice % 15 == 0:
                    QApplication.processEvents()
        finally:
            QApplication.restoreOverrideCursor()

        item_categoria.setData(0, ROL_ARCHIVOS, registros)
        if item_categoria is self._categoria_actual() and not self._en_busqueda:
            self._on_categoria_seleccionada(item_categoria, None)

        self._guardar_biblioteca()
        self.archivo_agregado.emit(f"{len(rutas)} archivos")

    # ------------------------------------------------------------------
    # Descarga de YouTube (pedido explícito, "módulo" autocontenido:
    # core/descargador_youtube.py hace el trabajo pesado sin Qt, acá
    # solo se arma la UI y se da de alta lo que devuelve).
    # ------------------------------------------------------------------
    def _descargar_de_youtube(self):
        url = self.txt_url_youtube.text().strip()
        if not url:
            return

        if not descargador_youtube.es_url_youtube(url):
            self.lbl_estado_youtube.setStyleSheet("color: #e57373; font-size: 8pt;")
            self.lbl_estado_youtube.setText(
                "⚠ Solo se aceptan enlaces de YouTube (youtube.com o youtu.be)."
            )
            return

        config = cargar_configuracion()
        carpeta_base = config["rutas"]["biblioteca_musical"]
        tolerancia = tolerancia_silencio_para_genero(config, "Musica")
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)

        self.lbl_estado_youtube.setStyleSheet("color: #999; font-size: 8pt;")
        self.btn_descargar_youtube.setEnabled(False)
        self.txt_url_youtube.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        def _progreso(texto: str):
            self.lbl_estado_youtube.setText(texto)
            QApplication.processEvents()

        self.lbl_estado_youtube.setText("Analizando enlace...")
        QApplication.processEvents()
        try:
            exito, mensaje, resultado = descargador_youtube.descargar(
                url, carpeta_base,
                tolerancia_silencio_segundos=tolerancia,
                umbral_silencio_dbfs=umbral_silencio,
                callback_progreso=_progreso,
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_descargar_youtube.setEnabled(True)
            self.txt_url_youtube.setEnabled(True)

        if not exito:
            self.lbl_estado_youtube.setText("")
            QMessageBox.warning(self, "Descargar de YouTube", mensaje)
            return

        self.lbl_estado_youtube.setText("")
        self.txt_url_youtube.clear()
        self._dar_de_alta_descarga_youtube(resultado)

    def _dar_de_alta_descarga_youtube(self, resultado: dict):
        """Sube a la biblioteca lo que bajó `descargador_youtube.descargar()`.
        Pedido explícito: SIEMPRE aterriza en la categoría "Descargas YT"
        (subcategoría con el título de la playlist si corresponde) —
        nunca se elige/adivina la categoría real, eso queda a mano del
        operador arrastrándolo después (ver el aviso de abajo)."""
        if resultado["es_playlist"]:
            ruta_categoria = ["Descargas YT", resultado["titulo_playlist"]]
        else:
            ruta_categoria = ["Descargas YT"]

        item_categoria = self._obtener_o_crear_categoria_por_ruta(ruta_categoria)

        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        siguiente_numero = len(registros) + 1
        prefijo = GENERO_PREFIJOS_CODIGO.get("Musica", "MUS")

        for archivo in resultado["archivos"]:
            registro = {
                "titulo": archivo["titulo"],
                "artista": "",
                "genero": "Musica",
                "codigo": f"{prefijo}{siguiente_numero:05d}",
                "ruta": archivo["ruta"],
                "duracion": archivo["duracion"],
                "punto_inicio_ms": archivo["punto_inicio_ms"],
                "punto_fin_ms": archivo["punto_fin_ms"],
                "ganancia_db": archivo["ganancia_db"],
                "analizado": archivo["analizado"],
                "fecha_inicio": None,
                "fecha_fin": None,
            }
            registros.append(registro)
            siguiente_numero += 1

        item_categoria.setData(0, ROL_ARCHIVOS, registros)
        if item_categoria is self._categoria_actual() and not self._en_busqueda:
            self._on_categoria_seleccionada(item_categoria, None)

        self._guardar_biblioteca_debounced()
        self.archivo_agregado.emit(f"{len(resultado['archivos'])} descarga(s) de YouTube")

        nombre_categoria = " > ".join(ruta_categoria)
        QMessageBox.information(
            self, "Descarga completa",
            f"Se descargaron {len(resultado['archivos'])} archivo(s) a la categoría "
            f"\"{nombre_categoria}\".\n\n"
            "Quedaron ahí en espera — arrastralos a la categoría que "
            "corresponda cuando quieras.",
        )

    def _obtener_o_crear_categoria_por_ruta(self, ruta_nombres: list) -> QTreeWidgetItem:
        """Como `buscar_categoria_por_ruta()`, pero CREA los tramos que
        falten en vez de devolver None -- usado por la descarga de
        YouTube para asegurar que "Descargas YT" (y la subcategoría de
        la playlist, si aplica) existan siempre."""
        item_padre = None
        for nombre in ruta_nombres:
            cantidad = item_padre.childCount() if item_padre else self.tree_categorias.topLevelItemCount()
            candidato = None
            for i in range(cantidad):
                item = item_padre.child(i) if item_padre else self.tree_categorias.topLevelItem(i)
                if item.text(0) == nombre:
                    candidato = item
                    break
            if candidato is None:
                candidato = self._crear_item_categoria(item_padre, nombre)
            item_padre = candidato
        return item_padre

    # ------------------------------------------------------------------
    # Reemplazar / Eliminar (Eliminar admite selección múltiple)
    # ------------------------------------------------------------------
    def _reemplazar_archivo(self):
        item = self.tree_archivos.currentItem()
        if item is None:
            QMessageBox.information(self, "Reemplazar", "Seleccioná un archivo.")
            return

        registro_actual = item.data(0, ROL_REGISTRO)
        categoria = self._buscar_categoria_de_ruta(registro_actual.get("ruta")) if registro_actual else None
        if categoria is None:
            QMessageBox.warning(self, "Reemplazar", "No se encontró la categoría de este archivo.")
            return

        ruta_nueva, _ = QFileDialog.getOpenFileName(
            self, "Reemplazar archivo", os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.mp4 *.m4a)",
        )
        if not ruta_nueva:
            return

        config = cargar_configuracion()
        if config["general"]["confirmar_antes_de_eliminar"]:
            respuesta = QMessageBox.question(
                self, "Reemplazar",
                f"¿Reemplazar el archivo de '{item.text(COL_TITULO)}' por:\n"
                f"{os.path.basename(ruta_nueva)}?\n\n"
                "El título/artista/código se mantienen, pero el archivo de\n"
                "audio y su análisis (duración, silencios, volumen) cambian.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        registro = item.data(0, ROL_REGISTRO)
        ruta_anterior = registro.get("ruta")
        config = cargar_configuracion()
        tolerancia = tolerancia_silencio_para_genero(config, registro.get("genero", ""))
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)
        analisis = analizar_audio(ruta_nueva, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio)

        registro["ruta"] = ruta_nueva
        registro["duracion"] = obtener_duracion_formateada(ruta_nueva)
        registro["punto_inicio_ms"] = analisis["punto_inicio_ms"]
        registro["punto_fin_ms"] = analisis["punto_fin_ms"] or None
        registro["ganancia_db"] = analisis["ganancia_db"]
        registro["analizado"] = analisis["analizado"]

        item.setData(0, Qt.ItemDataRole.UserRole, ruta_nueva)
        item.setData(0, ROL_REGISTRO, registro)
        item.setText(COL_DURACION, registro["duracion"])
        self._sincronizar_registro_en_categoria(categoria, ruta_anterior, registro)
        self._guardar_biblioteca_debounced()

    def _editar_vigencia(self, item):
        """Vigencia de fecha (pedido explícito, inspirado en Dinesat):
        edita fecha_inicio/fecha_fin de un material YA importado — a
        diferencia del análisis de audio, esto es metadata pura del
        registro, no requiere volver a analizar el archivo."""
        if item is None:
            return
        registro = item.data(0, ROL_REGISTRO)
        if not registro:
            return
        categoria = self._buscar_categoria_de_ruta(registro.get("ruta"))
        if categoria is None:
            QMessageBox.warning(self, "Vigencia", "No se encontró la categoría de este archivo.")
            return

        dialogo = DialogoVigencia(
            registro.get("titulo", ""), registro.get("fecha_inicio"), registro.get("fecha_fin"), parent=self,
        )
        if dialogo.exec() != DialogoVigencia.DialogCode.Accepted:
            return

        fecha_inicio, fecha_fin = dialogo.resultado()
        registro["fecha_inicio"] = fecha_inicio
        registro["fecha_fin"] = fecha_fin
        item.setData(0, ROL_REGISTRO, registro)
        self._sincronizar_registro_en_categoria(categoria, registro.get("ruta"), registro)
        self._guardar_biblioteca_debounced()

    def _editar_informacion_archivo(self, item=None):
        """Pedido explícito: editar título/artista/género/categoría de
        un material YA importado, sin tocar el audio ni re-analizarlo
        (distinto de "🎚 Editar audio" y de "⟲ Reemplazar")."""
        if item is None:
            item = self.tree_archivos.currentItem()
        if item is None:
            QMessageBox.information(self, "Editar información", "Seleccioná un archivo.")
            return

        registro = item.data(0, ROL_REGISTRO)
        if not registro:
            return
        ruta = registro.get("ruta")
        categoria_actual = self._buscar_categoria_de_ruta(ruta)
        if categoria_actual is None:
            QMessageBox.warning(self, "Editar información", "No se encontró la categoría de este archivo.")
            return

        from gui.dialogo_editar_informacion import DialogoEditarInformacion
        dialogo = DialogoEditarInformacion(registro, self.tree_categorias, categoria_actual, parent=self)
        if dialogo.exec() != DialogoEditarInformacion.DialogCode.Accepted:
            return
        resultado = dialogo.resultado()
        if resultado is None:
            return

        categoria_nueva = resultado["item_categoria"]
        cambia_categoria = categoria_nueva is not categoria_actual

        if cambia_categoria:
            config = cargar_configuracion()
            if config["general"]["confirmar_antes_de_eliminar"]:
                respuesta = QMessageBox.question(
                    self, "Editar información",
                    f"Además del cambio de información, esto mueve '{resultado['titulo']}'\n"
                    f"a la categoría '{categoria_nueva.text(0)}'. ¿Continuar?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if respuesta != QMessageBox.StandardButton.Yes:
                    return

        registro["titulo"] = resultado["titulo"]
        registro["artista"] = resultado["artista"]
        registro["genero"] = resultado["genero"]

        if cambia_categoria:
            # Mismo patrón que _mover_archivos_a_categoria: se saca de
            # la categoría vieja y se agrega a la nueva, código y
            # demás metadata SIN tocar — comparar por ruta, no por
            # identidad (ver nota en _sincronizar_registro_en_categoria).
            registros_origen = [r for r in (categoria_actual.data(0, ROL_ARCHIVOS) or []) if r.get("ruta") != ruta]
            categoria_actual.setData(0, ROL_ARCHIVOS, registros_origen)
            registros_destino = categoria_nueva.data(0, ROL_ARCHIVOS) or []
            registros_destino.append(registro)
            categoria_nueva.setData(0, ROL_ARCHIVOS, registros_destino)
        else:
            self._sincronizar_registro_en_categoria(categoria_actual, ruta, registro)

        self._guardar_biblioteca_debounced()

        if self._en_busqueda:
            self._buscar()
        else:
            self._on_categoria_seleccionada(self._categoria_actual(), None)

        if cambia_categoria:
            self.archivo_movido.emit(registro["titulo"], categoria_nueva.text(0))

    def _eliminar_archivo(self):
        items = self.tree_archivos.selectedItems()
        if not items:
            return

        config = cargar_configuracion()
        if config["general"]["confirmar_antes_de_eliminar"]:
            descripcion = f"'{items[0].text(COL_TITULO)}'" if len(items) == 1 else f"estos {len(items)} archivos"
            respuesta = QMessageBox.question(
                self, "Eliminar", f"¿Quitar {descripcion} de la biblioteca?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        rutas_eliminadas = []
        for item in list(items):
            registro = item.data(0, ROL_REGISTRO)
            ruta = registro.get("ruta") if registro else None
            indice = self.tree_archivos.indexOfTopLevelItem(item)
            if indice >= 0:
                self.tree_archivos.takeTopLevelItem(indice)
            if not ruta:
                continue
            categoria = self._buscar_categoria_de_ruta(ruta)
            if categoria is None:
                continue
            registros = [r for r in (categoria.data(0, ROL_ARCHIVOS) or []) if r.get("ruta") != ruta]
            categoria.setData(0, ROL_ARCHIVOS, registros)
            rutas_eliminadas.append(ruta)

        if rutas_eliminadas:
            self._guardar_biblioteca_debounced()
            for ruta in rutas_eliminadas:
                self.archivo_eliminado.emit(ruta)

    def _sincronizar_registro_en_categoria(self, categoria, ruta_anterior, registro):
        """Reemplaza, en la lista persistida de la categoría, la
        entrada que tenía `ruta_anterior` por el `registro` ya
        actualizado. NOTA: PySide6 devuelve una COPIA de los objetos
        guardados en roles custom — comparar por identidad (`is`)
        contra un dict obtenido en otra llamada nunca matchea, por
        eso el filtro va por ruta (clave estable antes de mutar)."""
        registros = categoria.data(0, ROL_ARCHIVOS) or []
        for i, r in enumerate(registros):
            if r.get("ruta") == ruta_anterior:
                registros[i] = registro
                break
        categoria.setData(0, ROL_ARCHIVOS, registros)

    # ------------------------------------------------------------------
    # Mover archivo(s) de categoría arrastrándolos (columna derecha ->
    # columna izquierda, con selección múltiple), sin perder ninguna
    # metadata. Si lo arrastrado NO es un archivo ya conocido de la
    # biblioteca (viene de afuera, ej. el explorador de archivos del
    # sistema), se interpreta como IMPORTACIÓN en vez de movimiento.
    # ------------------------------------------------------------------
    def _on_archivos_soltados_en_categoria(self, rutas: list, item_categoria_destino):
        if item_categoria_destino is None:
            QMessageBox.information(self, "Mover", "Soltá los archivos sobre una categoría concreta.")
            return

        rutas_conocidas = []
        rutas_externas = []
        for ruta in rutas:
            if self.buscar_registro_por_ruta(ruta) is not None:
                rutas_conocidas.append(ruta)
            elif ruta.lower().endswith(EXTENSIONES_SOPORTADAS) and os.path.isfile(ruta):
                rutas_externas.append(ruta)

        if rutas_conocidas:
            config = cargar_configuracion()
            if config["general"]["confirmar_antes_de_eliminar"]:
                descripcion = "1 archivo" if len(rutas_conocidas) == 1 else f"{len(rutas_conocidas)} archivos"
                respuesta = QMessageBox.question(
                    self, "Cambiar de categoría",
                    f"¿Mover {descripcion} a la categoría '{item_categoria_destino.text(0)}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if respuesta == QMessageBox.StandardButton.Yes:
                    self._mover_archivos_a_categoria(rutas_conocidas, item_categoria_destino)
            else:
                self._mover_archivos_a_categoria(rutas_conocidas, item_categoria_destino)

        if len(rutas_externas) == 1:
            self._dar_de_alta_archivo(rutas_externas[0], item_categoria_destino)
        elif len(rutas_externas) > 1:
            self._importar_archivos_masivo(rutas_externas, item_categoria_destino)

    def _mover_archivos_a_categoria(self, rutas: list, categoria_destino):
        movidos = []
        for ruta in rutas:
            registro = self.buscar_registro_por_ruta(ruta)
            if registro is None:
                continue
            categoria_origen = self._buscar_categoria_de_ruta(ruta)
            if categoria_origen is None or categoria_origen is categoria_destino:
                continue

            registros_origen = [r for r in (categoria_origen.data(0, ROL_ARCHIVOS) or []) if r.get("ruta") != ruta]
            categoria_origen.setData(0, ROL_ARCHIVOS, registros_origen)

            registros_destino = categoria_destino.data(0, ROL_ARCHIVOS) or []
            registros_destino.append(registro)
            categoria_destino.setData(0, ROL_ARCHIVOS, registros_destino)
            movidos.append(registro.get("titulo", ruta))

        if not movidos:
            return

        if not self._en_busqueda:
            self._on_categoria_seleccionada(self._categoria_actual(), None)

        self._guardar_biblioteca_debounced()
        nombres = movidos[0] if len(movidos) == 1 else f"{len(movidos)} archivos"
        self.archivo_movido.emit(nombres, categoria_destino.text(0))

    # ------------------------------------------------------------------
    # Menú contextual: Importar, Exportar, Reemplazar, Eliminar, Editar
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        item_bajo_cursor = self.tree_archivos.itemAt(posicion)
        seleccionados = self.tree_archivos.selectedItems()
        if item_bajo_cursor is not None and item_bajo_cursor not in seleccionados:
            self.tree_archivos.setCurrentItem(item_bajo_cursor)
            seleccionados = [item_bajo_cursor]

        menu = QMenu(self)
        accion_importar = menu.addAction("📥 Importar...")
        menu.addSeparator()
        accion_exportar = menu.addAction("📤 Exportar...")
        accion_reemplazar = menu.addAction("⟲ Reemplazar...")
        accion_info = menu.addAction("✏ Editar información...")
        accion_editar = menu.addAction("🎚 Editar audio")
        accion_vigencia = menu.addAction("📅 Vigencia...")
        menu.addSeparator()
        texto_eliminar = "✕ Eliminar" if len(seleccionados) <= 1 else f"✕ Eliminar {len(seleccionados)}"
        accion_eliminar = menu.addAction(texto_eliminar)

        hay_seleccion_unica = len(seleccionados) == 1
        accion_exportar.setEnabled(hay_seleccion_unica)
        accion_reemplazar.setEnabled(hay_seleccion_unica)
        accion_info.setEnabled(hay_seleccion_unica)
        accion_editar.setEnabled(hay_seleccion_unica)
        accion_vigencia.setEnabled(hay_seleccion_unica)
        accion_eliminar.setEnabled(len(seleccionados) > 0)

        accion_elegida = menu.exec(self.tree_archivos.viewport().mapToGlobal(posicion))
        if accion_elegida == accion_importar:
            self._agregar_archivos()
        elif accion_elegida == accion_exportar:
            self._exportar_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_reemplazar:
            self._reemplazar_archivo()
        elif accion_elegida == accion_info:
            self._editar_informacion_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_editar:
            self._editar_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_vigencia:
            self._editar_vigencia(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_eliminar:
            self._eliminar_archivo()

    def _exportar_archivo(self, item):
        if item is None:
            return
        ruta_origen = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta_origen or not os.path.exists(ruta_origen):
            QMessageBox.warning(self, "Exportar", "No se encontró el archivo fuente.")
            return

        carpeta_destino = QFileDialog.getExistingDirectory(self, "Exportar a carpeta", os.path.expanduser("~"))
        if not carpeta_destino:
            return

        destino = os.path.join(carpeta_destino, os.path.basename(ruta_origen))
        try:
            shutil.copy2(ruta_origen, destino)
            QMessageBox.information(self, "Exportar", f"Copiado a:\n{destino}")
        except OSError as error:
            QMessageBox.warning(self, "Exportar", f"No se pudo copiar el archivo:\n{error}")

    # Pedido explícito ("editor de audio ultra liviano para acortar y/o
    # edición básica de subir volumen o introducir un fade in/out"):
    # mhwaveedit (~1MB instalado, GTK2, corte/volumen/fade) — se
    # prueba PRIMERO y explícito, antes que la asociación de archivos
    # del sistema, porque el default de esa asociación suele ser un
    # REPRODUCTOR (VLC, etc.), no un editor.
    EDITOR_AUDIO_PREFERIDO = "mhwaveedit"

    def _editar_archivo(self, item):
        if item is None:
            return
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta or not os.path.exists(ruta):
            QMessageBox.warning(self, "Editar", "No se encontró el archivo fuente.")
            return

        ejecutable_preferido = shutil.which(self.EDITOR_AUDIO_PREFERIDO)
        if ejecutable_preferido:
            QProcess.startDetached(ejecutable_preferido, [ruta])
            return

        exito = QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))
        if exito:
            return

        respuesta = QMessageBox.question(
            self, "Editor no encontrado",
            "No se encontró un editor de audio predeterminado en el sistema.\n"
            "¿Querés elegir manualmente qué programa usar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        ejecutable, _ = QFileDialog.getOpenFileName(self, "Elegir editor de audio", "/usr/bin")
        if ejecutable:
            QProcess.startDetached(ejecutable, [ruta])

    # ------------------------------------------------------------------
    # API pública usada por core/playlist_manager.py (preview)
    # ------------------------------------------------------------------
    def registro_seleccionado(self) -> dict | None:
        item = self.tree_archivos.currentItem()
        return item.data(0, ROL_REGISTRO) if item else None

    # ------------------------------------------------------------------
    # API pública usada por main_window.py para el motor "Agregar
    # Pisador" (Ventana 2 / Auxiliar): consultar/borrar registros de
    # la biblioteca completa sin que esas ventanas necesiten conocer
    # cómo está armado el árbol de categorías acá adentro.
    # ------------------------------------------------------------------
    def _para_cada_categoria(self, funcion, item_padre=None):
        cantidad = item_padre.childCount() if item_padre else self.tree_categorias.topLevelItemCount()
        for i in range(cantidad):
            item = item_padre.child(i) if item_padre else self.tree_categorias.topLevelItem(i)
            funcion(item)
            self._para_cada_categoria(funcion, item)

    def listar_registros_por_genero(self, genero: str) -> list:
        resultado = []

        def visitar(item):
            for registro in (item.data(0, ROL_ARCHIVOS) or []):
                if registro.get("genero") == genero:
                    resultado.append(registro)

        self._para_cada_categoria(visitar)
        return resultado

    def listar_registros_de_categoria(self, item_categoria, recursivo: bool = True) -> list:
        """Todos los registros de UNA categoría — pedido explícito,
        base reutilizable para el Musicalizador Avanzado (programación
        automática) que se va a construir más adelante. `recursivo=True`
        (default) suma también los de las subcategorías; en False,
        solo los de esa categoría puntual."""
        if item_categoria is None:
            return []
        resultado = list(item_categoria.data(0, ROL_ARCHIVOS) or [])
        if recursivo:
            self._para_cada_categoria(
                lambda item: resultado.extend(item.data(0, ROL_ARCHIVOS) or []), item_categoria,
            )
        return resultado

    def elegir_aleatorio_de_categoria(self, item_categoria, recursivo: bool = True, excluir_rutas=None) -> dict | None:
        """Selección aleatoria de UN registro de una categoría (y, por
        defecto, sus subcategorías) — pedido explícito: "es importante
        ir teniendo escrito la función aleatoria, ya que la vamos a
        usar en Musicalizador Avanzado... para que siempre suene temas
        musicales diferentes todos los días". `excluir_rutas` (ej. los
        últimos N temas ya reproducidos) descarta esos candidatos SIN
        cambiar la categoría de origen; si excluirlos vacía la lista,
        se ignora la exclusión antes que devolver None (mejor repetir
        alguno a no reproducir nada)."""
        candidatos = self.listar_registros_de_categoria(item_categoria, recursivo)
        if excluir_rutas:
            filtrados = [r for r in candidatos if r.get("ruta") not in excluir_rutas]
            if filtrados:
                candidatos = filtrados
        if not candidatos:
            return None
        return random.choice(candidatos)

    def buscar_registro_por_ruta(self, ruta: str) -> dict | None:
        hallazgo = {}

        def visitar(item):
            if "registro" in hallazgo:
                return
            for registro in (item.data(0, ROL_ARCHIVOS) or []):
                if registro.get("ruta") == ruta:
                    hallazgo["registro"] = registro
                    return

        self._para_cada_categoria(visitar)
        return hallazgo.get("registro")

    def ruta_de_categoria(self, item_categoria) -> list:
        """Camino de nombres desde la raíz hasta `item_categoria` (ej.
        ["Música", "Folclore"]) — pedido explícito, base del
        Musicalizador Avanzado: un ítem "aleatorio" guarda ESTE camino
        (no la referencia viva al QTreeWidgetItem, que no sobrevive
        cerrar y reabrir la app) y lo vuelve a resolver con
        `buscar_categoria_por_ruta()` cada vez que hace falta."""
        ruta = []
        nodo = item_categoria
        while nodo is not None:
            ruta.insert(0, nodo.text(0))
            nodo = nodo.parent()
        return ruta

    def buscar_categoria_por_ruta(self, ruta_nombres: list):
        """Inverso de `ruta_de_categoria()`. Devuelve None si algún
        tramo del camino ya no existe (categoría renombrada o
        eliminada) — el Musicalizador trata eso como "ítem roto", lo
        saltea sin frenar la generación de los demás (pedido
        explícito)."""
        if not ruta_nombres:
            return None
        actual_padre = None
        for nombre in ruta_nombres:
            cantidad = actual_padre.childCount() if actual_padre else self.tree_categorias.topLevelItemCount()
            candidato = None
            for i in range(cantidad):
                item = actual_padre.child(i) if actual_padre else self.tree_categorias.topLevelItem(i)
                if item.text(0) == nombre:
                    candidato = item
                    break
            if candidato is None:
                return None
            actual_padre = candidato
        return actual_padre

    def _buscar_categoria_de_ruta(self, ruta: str):
        """Categoría (QTreeWidgetItem) que tiene HOY el registro con
        esa ruta, sin importar cuál esté seleccionada/mostrada — así
        Eliminar/Reemplazar/mover funcionan igual de bien viendo una
        categoría normal o resultados de búsqueda mezclados."""
        hallazgo = {}

        def visitar(item):
            if "categoria" in hallazgo:
                return
            if any(r.get("ruta") == ruta for r in (item.data(0, ROL_ARCHIVOS) or [])):
                hallazgo["categoria"] = item

        self._para_cada_categoria(visitar)
        return hallazgo.get("categoria")

    def eliminar_registro_por_ruta(self, ruta: str) -> bool:
        """Borra definitivamente el registro de TODA la biblioteca
        (no solo de una lista). Usado por "Eliminar de la biblioteca"
        en el menú contextual de Ventana 2 / Auxiliar."""
        categoria = self._buscar_categoria_de_ruta(ruta)
        if categoria is None:
            return False

        registros = [r for r in (categoria.data(0, ROL_ARCHIVOS) or []) if r.get("ruta") != ruta]
        categoria.setData(0, ROL_ARCHIVOS, registros)

        if categoria is self._categoria_actual() and not self._en_busqueda:
            self._on_categoria_seleccionada(categoria, None)

        self._guardar_biblioteca_debounced()
        self.archivo_eliminado.emit(ruta)
        return True

    # ------------------------------------------------------------------
    def guardar_disposicion(self):
        guardar_columnas("explorador_archivos", self.tree_archivos)

    def restaurar_disposicion(self):
        restaurar_columnas("explorador_archivos", self.tree_archivos)
