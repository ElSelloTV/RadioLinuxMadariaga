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
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidget,
    QTreeWidgetItem, QPushButton, QFileDialog, QSplitter, QLineEdit,
    QMessageBox, QInputDialog, QMenu, QAbstractItemView, QApplication,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QUrl, QProcess, QTimer
from PySide6.QtGui import QColor, QBrush, QDesktopServices, QFont, QIcon

from gui.common_widgets import (
    ArbolOrigenArrastre, ArbolConDrop, ArbolCategoriasConDrop,
    configurar_columnas_ajustables, SliderBusqueda,
)
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.styles import GENERO_COLORES, GENERO_PREFIJOS_CODIGO, color_texto_legible, icono_sin_marcas_in_out
from gui.dialogo_agregar_archivo import DialogoAgregarArchivo
from gui.dialogo_agregar_archivos_masivo import DialogoAgregarArchivosMasivo
from gui.dialogo_vigencia import DialogoVigencia
from gui.dialogo_preload_biblioteca import DialogoPreloadBiblioteca
from gui.estado_ui import guardar_columnas, restaurar_columnas, guardar_valor, restaurar_valor
from core.analizador_audio import analizar_audio
from core.audio_engine import obtener_duracion_formateada
from core.buscador_duplicados import buscar_grupos_duplicados
from config.settings import (
    cargar_configuracion, cargar_biblioteca, guardar_biblioteca, tolerancia_silencio_para_genero,
    parametros_nivelado, corregir_referencias_categoria_renombrada, registrar_error,
)

EXTENSIONES_SOPORTADAS = (".mp3", ".wav", ".mp4", ".m4a")

# Roles de datos propios (por encima de Qt.ItemDataRole.UserRole)
ROL_ARCHIVOS = Qt.ItemDataRole.UserRole + 20     # en ítem de categoría: list[dict]
ROL_REGISTRO = Qt.ItemDataRole.UserRole + 21     # en ítem de archivo: dict completo
# Bug real corregido ("Eliminar" no funcionaba para ítems sin ruta --
# volvían a aparecer): antes, ubicar la categoría de un ítem de
# tree_archivos dependía SIEMPRE de comparar por `ruta` contra
# `ROL_ARCHIVOS` de cada categoría (_buscar_categoria_de_ruta) — con
# `ruta` vacía (archivo nunca vinculado) esa comparación no tiene
# forma de identificar cuál es el registro correcto, así que varios
# lugares directamente hacían `if not ruta: continue/return` antes de
# llegar a tocar la lista persistida. Ahora cada ítem de tree_archivos
# guarda una referencia DIRECTA a su categoría de origen (el propio
# QTreeWidgetItem de la izquierda), que sobrevive sin importar la
# ruta -- ver _agregar_fila_archivo()/_llenar_tree_archivos().
ROL_CATEGORIA_ORIGEN = Qt.ItemDataRole.UserRole + 22

# Orden de columnas de tree_archivos (pedido explícito): Duración
# primero, después Título/Artista/Categoría/Código.
COL_DURACION, COL_TITULO, COL_ARTISTA, COL_CATEGORIA, COL_CODIGO = range(5)

# Clave de persistencia (ui_state.ini, vía gui/estado_ui.py) de qué
# categorías quedaron expandidas -- pedido explícito ("sacar que todo
# el árbol se vea expandido... es molesto ver todo"): ya no se expande
# todo por defecto, se recuerda EXACTAMENTE lo que el operador dejó
# abierto la última vez (ver _restaurar_expansion_categorias()).
CLAVE_CATEGORIAS_EXPANDIDAS = "explorador/categorias_expandidas"


class VentanaExplorador(QWidget):
    """Panel de exploración y gestión de la biblioteca de audio."""

    archivo_agregado = Signal(str)
    archivo_eliminado = Signal(str)
    archivo_movido = Signal(str, str)   # (titulo, nombre_categoria_destino)
    archivo_copiado = Signal(str, str)  # (titulo, nombre_categoria_destino) -- ver _copiar_archivos_a_categoria
    categoria_renombrada = Signal(list, list)   # (ruta_vieja, ruta_nueva) -- ver _renombrar_categoria
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
        # Bug real corregido ("vengo cambiando el color de Música y al
        # reiniciar vuelve el verde"): acá se arrancaba SIEMPRE con la
        # paleta de fábrica (`GENERO_COLORES`, hardcodeada) -- la
        # paleta guardada en Configuración recién se leía cuando
        # `repintar_colores_genero()` se llamaba desde
        # `MainWindow._aplicar_configuracion_en_vivo()`, es decir,
        # SOLO si el operador abría y guardaba Configuración en ESA
        # misma sesión. En cada reinicio, antes de eso, quedaba
        # pintado con los colores de fábrica. Corregido leyendo la
        # config guardada ya en la construcción, igual que hace
        # `repintar_colores_genero()`.
        self._colores_genero = cargar_configuracion()["apariencia"]["colores_genero"]
        # Tema visual actual (pedido explícito, bug real corregido:
        # "la letra sigue blanca y no se ve con el fondo claro") --
        # mismo criterio que _colores_genero de arriba: se lee ya en
        # la construcción para que la jerarquía de categorías nazca
        # con el color correcto, y se refresca en vivo con
        # repintar_estilo_categorias() (ver más abajo).
        self._tema_actual = cargar_configuracion()["general"]["tema"]
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
        # Qué categorías quedaron expandidas la última vez (ver
        # CLAVE_CATEGORIAS_EXPANDIDAS) -- se carga ANTES de construir/
        # poblar el árbol para que el primer llenado ya respete esto.
        valor_expansion = restaurar_valor(CLAVE_CATEGORIAS_EXPANDIDAS, [])
        if isinstance(valor_expansion, str):
            # Misma trampa de QSettings ya documentada en el Programador:
            # una lista guardada de UN solo elemento vuelve como string
            # suelto, no como lista de 1.
            valor_expansion = [valor_expansion] if valor_expansion else []
        self._categorias_expandidas_guardadas = set(valor_expansion or [])
        self._construir_ui()
        self._cargar_biblioteca_inicial()
        # Conectadas DESPUÉS de la carga inicial a propósito -- así la
        # restauración de expansión de arriba no dispara escrituras
        # redundantes a ui_state.ini durante el arranque.
        self.tree_categorias.itemExpanded.connect(lambda item: self._marcar_expansion_categoria(item, True))
        self.tree_categorias.itemCollapsed.connect(lambda item: self._marcar_expansion_categoria(item, False))

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
        # Pedido explícito ("agregá siempre 'el triángulo', para ser
        # más intuitivo de que se debe hacer doble clic para desplegar
        # hacia abajo si hay otro nivel más"): explícito por las dudas
        # (ya es el default de Qt, pero un cambio futuro de tema/estilo
        # no debería poder sacarlo en silencio) -- ver gui/styles.py
        # por qué el QSS de ::branch de la ronda anterior lo tapaba.
        self.tree_categorias.setRootIsDecorated(True)
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
        # Pedido explícito ("agregar un botón a la par de Eliminar, que
        # permita renombrar la categoría"): a diferencia de Eliminar,
        # renombrar corrige de paso las referencias por CAMINO DE
        # NOMBRES guardadas fuera de la biblioteca (ítems Aleatorio de
        # Ventana 1/Programador, categorías del Musicalizador) -- ver
        # _renombrar_categoria().
        self.btn_renombrar_categoria = QPushButton("✏ Renombrar")
        self.btn_renombrar_categoria.setToolTip("Renombrar categoría (corrige las referencias guardadas)")
        self.btn_nueva_categoria.clicked.connect(self._nueva_categoria)
        self.btn_nueva_subcategoria.clicked.connect(self._nueva_subcategoria)
        self.btn_eliminar_categoria.clicked.connect(self._eliminar_categoria)
        self.btn_renombrar_categoria.clicked.connect(self._renombrar_categoria)
        for btn in (self.btn_nueva_categoria, self.btn_nueva_subcategoria, self.btn_eliminar_categoria, self.btn_renombrar_categoria):
            btn.setProperty("class", "btnCompacto")
        fila_categorias_1.addWidget(self.btn_nueva_categoria)
        fila_categorias_1.addWidget(self.btn_nueva_subcategoria)
        fila_categorias_2.addWidget(self.btn_eliminar_categoria)
        fila_categorias_2.addWidget(self.btn_renombrar_categoria)
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

        # --- Herramientas: Bays (grabador/editor externo ya instalado
        # en la PC, pedido explícito -- reemplaza a la descarga de
        # YouTube, que se sacó del todo) + Buscar duplicados ---
        grupo_herramientas = QGroupBox("🧰 Herramientas")
        layout_herramientas = QHBoxLayout(grupo_herramientas)
        self.btn_abrir_bays = QPushButton("🎙 Bays")
        self.btn_abrir_bays.setToolTip("Abrir el comando \"bays\" (ya instalado en la PC)")
        self.btn_abrir_bays.setProperty("class", "btnCompacto")
        self.btn_abrir_bays.clicked.connect(self._abrir_bays)
        self.btn_buscar_duplicados_avanzado = QPushButton("🧩 Buscar duplicados")
        self.btn_buscar_duplicados_avanzado.setToolTip(
            "Buscar archivos duplicados (nombre parecido + duración/tamaño) "
            "en toda la biblioteca o en una categoría puntual"
        )
        self.btn_buscar_duplicados_avanzado.setProperty("class", "btnCompacto")
        self.btn_buscar_duplicados_avanzado.clicked.connect(self._buscar_duplicados_avanzado)
        layout_herramientas.addWidget(self.btn_abrir_bays)
        layout_herramientas.addWidget(self.btn_buscar_duplicados_avanzado)
        layout_archivos.addWidget(grupo_herramientas)

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
                    resultados.append((registro, item))

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
        self._restaurar_expansion_categorias()

    def _restaurar_expansion_categorias(self):
        """Pedido explícito ("sacar que todo el árbol se vea expandido
        en esta ventana, es molesto ver todo"): ya NO se expande todo
        con `expandAll()` -- se restaura EXACTAMENTE lo que el operador
        había dejado abierto/cerrado (persistido en ui_state.ini, ver
        CLAVE_CATEGORIAS_EXPANDIDAS). Una biblioteca nueva, o la
        primera vez que corre esta versión, arranca TODO colapsado
        (solo las categorías raíz visibles) -- el operador expande lo
        que necesita, y queda recordado para la próxima."""
        if not self._categorias_expandidas_guardadas:
            return
        for i in range(self.tree_categorias.topLevelItemCount()):
            self._restaurar_expansion_categoria_recursivo(self.tree_categorias.topLevelItem(i))

    def _restaurar_expansion_categoria_recursivo(self, item):
        if " > ".join(self.ruta_de_categoria(item)) in self._categorias_expandidas_guardadas:
            item.setExpanded(True)
        for i in range(item.childCount()):
            self._restaurar_expansion_categoria_recursivo(item.child(i))

    def _marcar_expansion_categoria(self, item, expandido: bool):
        clave = " > ".join(self.ruta_de_categoria(item))
        if not clave:
            return
        if expandido:
            self._categorias_expandidas_guardadas.add(clave)
        else:
            self._categorias_expandidas_guardadas.discard(clave)
        guardar_valor(CLAVE_CATEGORIAS_EXPANDIDAS, sorted(self._categorias_expandidas_guardadas))

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

    # Pedido explícito ("suelo tener hasta 5 niveles de categoría y
    # sub-categorías... ¿qué podríamos implementar para otorgar una
    # mejor e intuitiva visibilidad? colores, negrita, líneas"):
    # gradiente de 5 escalones -- cada nivel más profundo se ve más
    # "liviano" (menos negrita, más chico, más tenue) que el anterior,
    # así de un vistazo se distingue la profundidad sin tener que leer
    # la indentación con atención. Los colores están elegidos para
    # nunca chocar con otros significados ya establecidos en la app
    # (el celeste de selección, el rojo/verde de estado de V1/V2, los
    # colores por género de tree_archivos -- acá es tree_categorias,
    # un árbol distinto). A partir del nivel 5, se repite el estilo
    # del nivel 5 (no sigue aclarándose para siempre).
    #
    # Bug real corregido ("la letra sigue blanca y no se ve con el
    # fondo claro"): esta tabla estaba hardcodeada para el tema
    # OSCURO -- colores blanco/gris claro, invisibles contra el fondo
    # crema del tema Claro (tree_fondo). Ahora hay DOS tablas
    # (oscuro/claro) y `_aplicar_estilo_por_nivel()` elige según
    # `self._tema_actual` (leído en __init__ y actualizado en vivo por
    # `repintar_estilo_categorias()`, mismo patrón ya usado para
    # `repintar_colores_genero()`).
    _ESTILOS_POR_NIVEL_OSCURO = [
        # (negrita, cursiva, mayúsculas, color, tamaño_relativo_pt)
        (True, False, True, "#e67e22", 1),    # nivel 1: categoría raíz
        (True, False, False, "#e0e0e0", 0),   # nivel 2
        (False, False, False, "#c9c9c9", 0),  # nivel 3
        (False, True, False, "#9a9a9a", 0),   # nivel 4
        (False, True, False, "#7a7a7a", -1),  # nivel 5+
    ]
    _ESTILOS_POR_NIVEL_CLARO = [
        (True, False, True, "#e67e22", 1),    # nivel 1: mismo naranja, ya contrasta bien
        (True, False, False, "#241c10", 0),   # nivel 2: marrón casi negro
        (False, False, False, "#4a3c28", 0),  # nivel 3
        (False, True, False, "#6b5d3f", 0),   # nivel 4
        (False, True, False, "#8a7a58", -1),  # nivel 5+
    ]

    def _aplicar_estilo_por_nivel(self, item: QTreeWidgetItem, item_padre):
        """Aplica el estilo que corresponda a la profundidad real de
        `item` (1 = categoría raíz) y al tema visual actual.

        El "MAYÚSCULAS" es solo de PINTADO (QFont.Capitalization.AllUppercase)
        — el texto real del ítem (item.text(0), lo que se guarda en
        biblioteca.json vía _serializar_categoria) nunca se toca, para
        no pisar el nombre original guardado en disco."""
        nivel = 1
        nodo = item_padre
        while nodo is not None:
            nivel += 1
            nodo = nodo.parent()

        tabla = self._ESTILOS_POR_NIVEL_CLARO if self._tema_actual == "claro" else self._ESTILOS_POR_NIVEL_OSCURO
        negrita, cursiva, mayusculas, color, delta_pt = tabla[min(nivel, len(tabla)) - 1]

        fuente = item.font(0)
        fuente.setBold(negrita)
        fuente.setItalic(cursiva)
        fuente.setCapitalization(
            QFont.Capitalization.AllUppercase if mayusculas else QFont.Capitalization.MixedCase
        )
        if delta_pt and fuente.pointSize() > 0:
            fuente.setPointSize(max(6, fuente.pointSize() + delta_pt))
        item.setFont(0, fuente)
        item.setForeground(0, QBrush(QColor(color)))

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
        self._llenar_tree_archivos([(r, actual) for r in registros])

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

    def _agregar_fila_archivo(self, registro: dict, item_categoria: QTreeWidgetItem, insertar: bool = True):
        """Arma el QTreeWidgetItem de una fila. Con `insertar=True`
        (default, usado por las altas de UN solo archivo) lo agrega
        directo al árbol y lo devuelve. Con `insertar=False` (usado
        por `_llenar_tree_archivos`, ver más abajo) devuelve el ítem
        SIN insertarlo — para que el llamador pueda insertar TODOS los
        ítems de un lote de una sola vez con `addTopLevelItems()`.

        `item_categoria` es la categoría de ORIGEN del registro — se
        guarda en el propio ítem (`ROL_CATEGORIA_ORIGEN`) para poder
        ubicarla después sin depender de comparar por `ruta` (que
        puede estar vacía, ver nota junto a `ROL_CATEGORIA_ORIGEN`)."""
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
        item.setData(0, ROL_CATEGORIA_ORIGEN, item_categoria)
        self._pintar_por_genero(item, registro.get("genero", ""))
        self._actualizar_vinculo_item(item, registro)
        self._actualizar_marcas_item(item, registro)
        if insertar:
            self.tree_archivos.addTopLevelItem(item)
        return item

    def _actualizar_vinculo_item(self, item: QTreeWidgetItem, registro: dict):
        """Pedido explícito ("un subrayado de los ítems que no tengan
        vinculación, así también me doy cuenta visualmente"): un
        registro cuyo archivo ya no está donde dice (falta la ruta, o
        el archivo fue movido/borrado por fuera de la app) se subraya
        en TODA la fila -- mismo criterio de "aplicar a las 5
        columnas" que ya usa _pintar_por_genero, pero independiente
        del color (un ítem sin vínculo puede tener cualquier género)."""
        ruta = registro.get("ruta")
        sin_vinculo = not ruta or not os.path.exists(ruta)
        for columna in range(item.columnCount()):
            fuente = item.font(columna)
            fuente.setUnderline(sin_vinculo)
            item.setFont(columna, fuente)

    def _actualizar_marcas_item(self, item: QTreeWidgetItem, registro: dict):
        """Pedido explícito ("veo que nunca funciona el recorte de
        silencio"): un archivo de MÚSICA importado sin que el análisis
        de silencio/nivelado pudiera calcular sus marcas IN/OUT
        (`analizado is False` -- típico si falta pydub/ffmpeg en la
        instalación, ver core.analizador_audio.verificar_motor_disponible)
        queda marcado con un triángulo ámbar a simple vista, en vez de
        quedar indistinguible de un archivo que sí tiene sus marcas
        bien calculadas. Acotado a género "Musica" a propósito -- es
        el caso que le importa a Ventana 2/Emisión (inicio + fundido
        de salida); Publicidad/Separador ya usan corte estricto
        (tolerancia 0) y su propio criterio."""
        sin_marcas = registro.get("genero") == "Musica" and registro.get("analizado") is False
        item.setIcon(COL_TITULO, icono_sin_marcas_in_out() if sin_marcas else QIcon())
        item.setToolTip(
            COL_TITULO,
            "Sin marcas IN/OUT: el análisis de silencio/nivelado falló al importar "
            "este archivo (revisá Configuración → Diagnóstico → \"Verificar motor "
            "de análisis de audio\")." if sin_marcas else "",
        )

    def _llenar_tree_archivos(self, entradas: list):
        """`entradas`: list[tuple[dict, QTreeWidgetItem]] -- cada
        registro junto con su categoría de origen (necesaria para que
        cada fila pueda guardar `ROL_CATEGORIA_ORIGEN`, ver esa nota
        más arriba). Bug real de rendimiento con una biblioteca de ~10-12mil
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
        cantidad = len(entradas)
        aviso_grande = cantidad >= self._UMBRAL_ITEMS_PRELOAD
        if aviso_grande:
            self.solicitud_preload.emit(f"Cargando {cantidad} archivos...")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.tree_archivos.setUpdatesEnabled(False)
        try:
            items = []
            for indice, (registro, categoria) in enumerate(entradas):
                items.append(self._agregar_fila_archivo(registro, categoria, insertar=False))
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

        entradas = [
            (item.data(0, ROL_REGISTRO), item.data(0, ROL_CATEGORIA_ORIGEN))
            for item in (self.tree_archivos.topLevelItem(i) for i in range(self.tree_archivos.topLevelItemCount()))
        ]
        entradas = [(r, c) for r, c in entradas if r is not None]
        # Duración ya viene en formato "HH:MM:SS" con ceros a la
        # izquierda (obtener_duracion_formateada) — el orden lexicográfico
        # de esa cadena coincide con el orden cronológico real, no hace
        # falta parsear a segundos.
        entradas.sort(
            key=lambda par: (par[0].get(campo) or "").lower() if isinstance(par[0].get(campo), str) else (par[0].get(campo) or ""),
            reverse=not self._orden_ascendente,
        )

        self.tree_archivos.clear()
        self._llenar_tree_archivos(entradas)

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

    def repintar_estilo_categorias(self):
        """Refresca `self._tema_actual` y repinta la jerarquía de
        negrita/cursiva/color por nivel de TODO el árbol de categorías
        — llamado tras cambiar el tema en Configuración (bug real:
        "la letra sigue blanca y no se ve con el fondo claro", mismo
        patrón que `repintar_colores_genero()`)."""
        self._tema_actual = cargar_configuracion()["general"]["tema"]
        for i in range(self.tree_categorias.topLevelItemCount()):
            self._repintar_estilo_categoria_recursivo(self.tree_categorias.topLevelItem(i))

    def _repintar_estilo_categoria_recursivo(self, item: QTreeWidgetItem):
        self._aplicar_estilo_por_nivel(item, item.parent())
        for i in range(item.childCount()):
            self._repintar_estilo_categoria_recursivo(item.child(i))

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

    def _renombrar_categoria(self):
        """Pedido explícito ("agregar un botón a la par de Eliminar,
        que permita renombrar la categoría... el sistema debe corregir
        todas las integraciones de rutas efectuadas para que no se
        'rompa' la lectura del programador, aleatorio, musicalizador,
        etc"): las categorías se referencian en 3 archivos por FUERA
        de la biblioteca (`playlist_publicidad.json`, `programacion.json`,
        `musicalizador.json`) guardando el CAMINO DE NOMBRES desde la
        raíz (`ruta_de_categoria()`), nunca una referencia viva al
        `QTreeWidgetItem` -- renombrar un nodo de ese camino, sin más,
        deja esas referencias apuntando a un camino que ya no existe
        (`buscar_categoria_por_ruta()` devuelve `None`, el ítem se
        saltea en silencio para siempre). Corregido migrando esos 3
        archivos con `config.settings.corregir_referencias_categoria_renombrada()`
        (reemplaza el PREFIJO viejo por el nuevo, conservando cualquier
        subcategoría más profunda) apenas se confirma el renombre."""
        self._salir_de_busqueda_si_corresponde()
        item = self._categoria_actual()
        if item is None:
            QMessageBox.information(self, "Renombrar categoría", "Seleccioná una categoría.")
            return

        nombre_actual = item.text(0)
        nombre_nuevo, ok = QInputDialog.getText(
            self, "Renombrar categoría", "Nuevo nombre:", text=nombre_actual,
        )
        if not ok:
            return
        nombre_nuevo = nombre_nuevo.strip()
        if not nombre_nuevo or nombre_nuevo == nombre_actual:
            return

        ruta_vieja = self.ruta_de_categoria(item)
        item.setText(0, nombre_nuevo)
        ruta_nueva = self.ruta_de_categoria(item)
        self._guardar_biblioteca_debounced()

        tocados = corregir_referencias_categoria_renombrada(ruta_vieja, ruta_nueva)
        # Avisa a MainWindow para que refresque en el momento las
        # referencias que Ventana 1 tiene YA CARGADAS en memoria (el
        # árbol en vivo que conduce la emisión al aire, no solo lo
        # persistido en disco) -- ver MainWindow._on_categoria_renombrada.
        self.categoria_renombrada.emit(ruta_vieja, ruta_nueva)

        mensaje = f"Categoría renombrada a '{nombre_nuevo}'."
        if tocados:
            plural = "s" if tocados != 1 else ""
            mensaje += f"\nSe corrigieron {tocados} referencia{plural} guardada{plural} (ítems Aleatorio / Musicalizador)."
        QMessageBox.information(self, "Renombrar categoría", mensaje)

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

        ruta = self._copiar_a_biblioteca(ruta, datos["item_categoria"], datos["genero"])

        config = cargar_configuracion()
        # Pedido explícito ("corte de silencio estricto"): Publicidad
        # y Separadores usan una tolerancia sin margen — ver
        # config/settings.py:tolerancia_silencio_para_genero().
        tolerancia = tolerancia_silencio_para_genero(config, datos["genero"])
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)
        objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)
        analisis = analizar_audio(
            ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio,
            objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs,
        )

        registro = {
            "titulo": datos["titulo"],
            "artista": datos["artista"],
            "genero": datos["genero"],
            "codigo": datos["codigo"],
            "ruta": ruta,
            "duracion": obtener_duracion_formateada(ruta),
            "tamaño_bytes": self._tamano_bytes(ruta),
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
            self._agregar_fila_archivo(registro, item_categoria)

        self._guardar_biblioteca_debounced()
        self.archivo_agregado.emit(ruta)
        self._avisar_si_sin_marcas(registro)

    def _avisar_si_sin_marcas(self, registro: dict):
        """Pedido explícito ("veo que nunca funciona el recorte de
        silencio"): avisa DE INMEDIATO, al momento de importar, si un
        archivo de Música quedó sin marcas IN/OUT (en vez de dejar que
        el operador lo descubra recién al aire, o nunca) -- antes esto
        fallaba en TOTAL silencio (solo un `print()` a una consola que
        nadie ve al lanzar desde el ícono de escritorio)."""
        if registro.get("genero") == "Musica" and registro.get("analizado") is False:
            QMessageBox.warning(
                self, "Sin marcas IN/OUT",
                f"\"{registro.get('titulo', '')}\" se importó, pero el análisis de "
                "silencio/nivelado FALLÓ -- va a sonar sin recorte de silencio ni "
                "nivelado de volumen.\n\n"
                "Probablemente falte pydub/ffmpeg en esta instalación. Revisá "
                "Configuración → Diagnóstico → \"Verificar motor de análisis de "
                "audio\" para confirmar qué falta.",
            )

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
        objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)

        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        siguiente_numero = len(registros) + 1
        prefijo = GENERO_PREFIJOS_CODIGO.get(genero, "GEN")

        # Pedido explícito ("que me indique el progreso... que me
        # indique si se hacen o no"): importar en lote analiza CADA
        # archivo (pydub/ffmpeg), lento de verdad con una biblioteca
        # grande (miles de archivos, caso real de Santiago) — sin
        # threading en esta app (nunca se usó, ver CLAUDE.md), acá el
        # trabajo en sí sigue siendo sincrónico (no amerita un proceso
        # aparte como el reanálisis completo: es incremental, archivo
        # por archivo, casi siempre un lote chico) pero se muestra una
        # barra de progreso GRÁFICA real (mismo widget que ya usa la
        # migración de duración al arrancar y el reanálisis en
        # segundo plano) en vez de solo un cursor de espera — así el
        # operador ve avanzar "X / Y archivos" en vivo, nunca se
        # pregunta si el programa quedó colgado.
        fallidos_musica = 0
        dialogo_progreso = DialogoPreloadBiblioteca(
            len(rutas), parent=self, titulo="Importando archivos",
            texto=f"Importando {len(rutas)} archivo(s) (análisis de silencio/nivelado)...",
            nota="Corre en el mismo proceso -- el programa queda a la espera hasta terminar.",
        )
        dialogo_progreso.show()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for indice, ruta in enumerate(rutas):
                ruta = self._copiar_a_biblioteca(ruta, item_categoria, genero)
                analisis = analizar_audio(
                    ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio,
                    objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs,
                )
                registro = {
                    "titulo": os.path.splitext(os.path.basename(ruta))[0],
                    "artista": "",
                    "genero": genero,
                    "codigo": f"{prefijo}{siguiente_numero:05d}",
                    "ruta": ruta,
                    "duracion": obtener_duracion_formateada(ruta),
                    "tamaño_bytes": self._tamano_bytes(ruta),
                    "punto_inicio_ms": analisis["punto_inicio_ms"],
                    "punto_fin_ms": analisis["punto_fin_ms"] or None,
                    "ganancia_db": analisis["ganancia_db"],
                    "analizado": analisis["analizado"],
                    "fecha_inicio": None,
                    "fecha_fin": None,
                }
                if genero == "Musica" and not analisis["analizado"]:
                    fallidos_musica += 1
                registros.append(registro)
                siguiente_numero += 1
                dialogo_progreso.actualizar(indice + 1, len(rutas))
                if indice % 5 == 0:
                    QApplication.processEvents()
        finally:
            QApplication.restoreOverrideCursor()
            dialogo_progreso.close()

        item_categoria.setData(0, ROL_ARCHIVOS, registros)
        if item_categoria is self._categoria_actual() and not self._en_busqueda:
            self._on_categoria_seleccionada(item_categoria, None)

        self._guardar_biblioteca()
        self.archivo_agregado.emit(f"{len(rutas)} archivos")

        # Mismo criterio que _avisar_si_sin_marcas() para el alta de UN
        # solo archivo -- acá se resume en UN aviso para todo el lote,
        # en vez de uno por archivo.
        if fallidos_musica:
            QMessageBox.warning(
                self, "Sin marcas IN/OUT",
                f"{fallidos_musica} de {len(rutas)} archivo(s) de Música se "
                "importaron SIN que el análisis de silencio/nivelado pudiera "
                "calcular sus marcas IN/OUT -- van a sonar sin recorte de "
                "silencio ni nivelado (quedan marcados con ⚠ en la lista).\n\n"
                "Probablemente falte pydub/ffmpeg en esta instalación. Revisá "
                "Configuración → Diagnóstico → \"Verificar motor de análisis de "
                "audio\" para confirmar qué falta.",
            )

    # ------------------------------------------------------------------
    # "Bays" (pedido explícito, reemplaza a la descarga de YouTube):
    # solo abre el comando externo, ya instalado en la PC -- ningún
    # otro tipo de integración con el programa.
    # ------------------------------------------------------------------
    COMANDO_BAYS = "bays"

    def _abrir_bays(self):
        ruta_ejecutable = shutil.which(self.COMANDO_BAYS)
        if not ruta_ejecutable:
            QMessageBox.warning(
                self, "Bays",
                f"No se encontró el comando \"{self.COMANDO_BAYS}\" en el sistema.",
            )
            return
        QProcess.startDetached(ruta_ejecutable, [])

    # ------------------------------------------------------------------
    # Buscador de duplicados AVANZADO (pedido explícito: coincidencia
    # aproximada en 3 niveles de prioridad -- ver
    # core/buscador_duplicados.py y gui/dialogo_buscar_duplicados_avanzado.py).
    #
    # Acotado SIEMPRE a una categoría específica (pedido explícito,
    # ronda posterior: "como ahora generamos ítems de JSON duplicados
    # [con Copiar entre categorías], la opción de 'buscar duplicados'
    # se debe aplicar por categoría específica y no por toda la
    # base") -- antes ofrecía elegir entre "toda la base" o una
    # categoría puntual; con "Copiar" (ver `_copiar_archivos_a_categoria`)
    # generando duplicados INTENCIONALES entre categorías distintas a
    # propósito, una búsqueda de "toda la base" los marcaría siempre
    # como falsos positivos. Ofrece además el "modo automático en
    # masa" como bonus, igual que antes.
    # ------------------------------------------------------------------
    def _buscar_duplicados_avanzado(self):
        from gui.dialogo_seleccionar_categoria import DialogoSeleccionarCategoria
        dialogo_cat = DialogoSeleccionarCategoria(
            self.tree_categorias, titulo="Elegir categoría para buscar duplicados", parent=self,
        )
        if dialogo_cat.exec() != QDialog.DialogCode.Accepted:
            return
        ruta_elegida = dialogo_cat.ruta_elegida()
        if not ruta_elegida:
            return
        item_categoria = self.buscar_categoria_por_ruta(ruta_elegida)
        if item_categoria is None:
            return
        modo_masa = self._preguntar_modo_masa()

        self.solicitud_preload.emit("Buscando duplicados...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            grupos = self.buscar_duplicados_avanzado(item_categoria)
        finally:
            QApplication.restoreOverrideCursor()

        if not grupos:
            QMessageBox.information(
                self, "Buscar duplicados",
                "No se encontraron duplicados con los criterios de coincidencia "
                "(nombre parecido + duración/tamaño).",
            )
            return

        audio_cfg = cargar_configuracion()["audio"]
        id_dispositivo_preescucha = (
            audio_cfg["dispositivo_preescucha"] if audio_cfg["dispositivo_preescucha"] != "default" else None
        )

        if modo_masa:
            self._ejecutar_modo_masa_duplicados(grupos, id_dispositivo_preescucha)
        else:
            self._revisar_grupos_duplicados_uno_por_uno(grupos, id_dispositivo_preescucha)

    def _preguntar_modo_masa(self) -> bool:
        """Bonus, pedido explícito: SOLO se ofrece tras elegir una
        categoría específica."""
        respuesta = QMessageBox.question(
            self, "Buscar duplicados",
            "¿Revisar los duplicados UNO POR UNO, o usar el MODO AUTOMÁTICO EN MASA\n"
            "(el sistema arma un plan completo con una sugerencia por grupo -- lo\n"
            "podés aprobar de una, o ajustar algún ítem puntual antes de aplicar)?\n\n"
            "Sí = modo automático en masa.   No = revisar uno por uno.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return respuesta == QMessageBox.StandardButton.Yes

    def buscar_duplicados_avanzado(self, item_categoria=None) -> list:
        """Motor de agrupamiento (core.buscador_duplicados) aplicado
        sobre el alcance elegido -- `item_categoria=None` recorre TODA
        la biblioteca; con una categoría, solo ahí (recursivo, incluye
        subcategorías). Devuelve una lista de grupos:
        `{"nivel": 1|2|3, "miembros": [(registro, categoria), ...]}`,
        ya ordenados del nivel más estricto al más laxo."""
        entradas = []  # list[(registro, categoria)]

        def visitar(item):
            for registro in (item.data(0, ROL_ARCHIVOS) or []):
                entradas.append((registro, item))

        if item_categoria is None:
            self._para_cada_categoria(visitar)
        else:
            visitar(item_categoria)
            self._para_cada_categoria(visitar, item_categoria)

        entradas_para_motor = [
            {"titulo": r.get("titulo", ""), "duracion": r.get("duracion"), "tamano_bytes": r.get("tamaño_bytes")}
            for r, _c in entradas
        ]
        grupos_indices = buscar_grupos_duplicados(
            entradas_para_motor, callback_progreso=lambda _h, _t: QApplication.processEvents(),
        )

        return [
            {"nivel": grupo["nivel"], "miembros": [entradas[i] for i in grupo["indices"]]}
            for grupo in grupos_indices
        ]

    def _revisar_grupos_duplicados_uno_por_uno(self, grupos: list, id_dispositivo_preescucha):
        from gui.dialogo_buscar_duplicados_avanzado import DialogoRevisarGrupoDuplicado

        total_grupos = len(grupos)
        grupos_con_cambios = 0
        grupos_omitidos = 0
        archivos_eliminados = 0

        for indice, grupo in enumerate(grupos, start=1):
            miembros = grupo["miembros"]
            dialogo = DialogoRevisarGrupoDuplicado(
                nivel=grupo["nivel"], miembros=miembros, resolver_ruta_categoria=self.ruta_de_categoria,
                id_dispositivo_preescucha=id_dispositivo_preescucha,
                indice_grupo=indice, total_grupos=total_grupos, parent=self,
            )
            codigo = dialogo.exec()
            if codigo == DialogoRevisarGrupoDuplicado.SALTAR:
                grupos_omitidos += 1
                continue
            if codigo != DialogoRevisarGrupoDuplicado.DialogCode.Accepted:
                break  # Cancelar corta TODA la revisión, no solo este grupo.

            indices_a_eliminar = dialogo.indices_a_eliminar()
            if not indices_a_eliminar:
                continue
            grupos_con_cambios += 1
            for i in indices_a_eliminar:
                registro, categoria = miembros[i]
                if self.eliminar_registro_de_categoria(registro, categoria):
                    archivos_eliminados += 1

        QMessageBox.information(
            self, "Buscar duplicados -- reporte",
            f"Revisión terminada.\n\n"
            f"Grupos con cambios: {grupos_con_cambios} de {total_grupos}\n"
            f"Grupos omitidos: {grupos_omitidos}\n"
            f"Archivos eliminados de la biblioteca: {archivos_eliminados}",
        )

    def _ejecutar_modo_masa_duplicados(self, grupos: list, id_dispositivo_preescucha):
        from gui.dialogo_buscar_duplicados_avanzado import DialogoPlanMasivoDuplicados

        dialogo = DialogoPlanMasivoDuplicados(
            grupos=grupos, resolver_ruta_categoria=self.ruta_de_categoria,
            id_dispositivo_preescucha=id_dispositivo_preescucha, parent=self,
        )
        if dialogo.exec() != DialogoPlanMasivoDuplicados.DialogCode.Accepted:
            return

        plan = dialogo.plan_aprobado()
        archivos_eliminados = 0
        for registro, categoria in plan:
            if self.eliminar_registro_de_categoria(registro, categoria):
                archivos_eliminados += 1

        QMessageBox.information(
            self, "Buscar duplicados -- reporte",
            f"Plan aplicado.\n\n"
            f"Grupos procesados: {len(grupos)}\n"
            f"Archivos eliminados de la biblioteca: {archivos_eliminados}",
        )

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

        self._aplicar_nuevo_archivo(item, categoria, item.data(0, ROL_REGISTRO), ruta_nueva)

    def _copiar_a_biblioteca(self, ruta_origen: str, item_categoria, genero: str) -> str:
        """Copia `ruta_origen` a la carpeta real de la biblioteca que
        corresponde a `item_categoria`/`genero`, y devuelve la ruta
        NUEVA -- pedido explícito: "cuando alguien inserta un
        dispositivo externo (pen drive o celular)... el sistema deberá
        copiar el archivo en la computadora en la carpeta
        correspondiente de la categoría, haciendo el mismo proceso
        como si apretara el botón de agregar". Hasta esta ronda, NI
        "＋ Agregar" NI el arrastre externo copiaban nada -- el
        registro quedaba apuntando tal cual a la ruta de origen (el
        pendrive, el teléfono), así que desconectar ese dispositivo
        dejaba el archivo "perdido" -- exactamente la clase de
        problema que el diálogo "Vincular archivo perdido" (rondas
        79-81) repara DESPUÉS. Copiar al importar previene el problema
        de raíz en vez de solo curarlo más tarde.

        Fail-open: si la copia falla por cualquier motivo (disco
        lleno, permisos, origen ilegible), devuelve la ruta ORIGINAL
        sin copiar -- nunca bloquea el alta por esto, mismo criterio
        que `analizar_audio()`/`_tamano_bytes()` ante fallas de I/O."""
        config = cargar_configuracion()
        raiz = config["rutas"]["biblioteca_musical"] if genero == "Musica" \
            else config["rutas"]["biblioteca_publicidad"]

        from gui.dialogo_vincular_archivo import _sanitizar_nombre_archivo
        carpeta_destino = raiz
        for nombre in self.ruta_de_categoria(item_categoria):
            carpeta_destino = os.path.join(carpeta_destino, _sanitizar_nombre_archivo(nombre))

        try:
            os.makedirs(carpeta_destino, exist_ok=True)
            nombre_archivo = _sanitizar_nombre_archivo(os.path.basename(ruta_origen))
            base, ext = os.path.splitext(nombre_archivo)
            destino = os.path.join(carpeta_destino, nombre_archivo)
            if os.path.abspath(destino) == os.path.abspath(ruta_origen):
                return ruta_origen  # ya está en el lugar correcto, no hay nada que copiar
            contador = 2
            while os.path.exists(destino):
                destino = os.path.join(carpeta_destino, f"{base} ({contador}){ext}")
                contador += 1
            shutil.copy2(ruta_origen, destino)
            return destino
        except OSError as error:
            registrar_error(f"No se pudo copiar '{ruta_origen}' a la biblioteca: {error}")
            return ruta_origen

    @staticmethod
    def _tamano_bytes(ruta: str):
        """Tamaño en bytes del archivo, o None si no se puede leer
        (archivo movido/borrado, permisos, etc. -- fail-open, nunca
        rompe el alta/vínculo de un registro por esto)."""
        try:
            return os.path.getsize(ruta)
        except OSError:
            return None

    def _aplicar_nuevo_archivo(self, item, categoria, registro: dict, ruta_nueva: str):
        """Punto único que pisa el archivo de audio de un registro YA
        existente por otro (re-analiza silencios/nivelado, recalcula
        duración/tamaño) y lo persiste -- usado tanto por "⟲ Reemplazar"
        (el operador elige el archivo a mano) como por "🔗 Vincular"
        (el operador elige uno de los candidatos encontrados al buscar
        un archivo perdido, ver _buscar_archivo_perdido). `item` puede
        ser None (registro que no está actualmente visible en
        tree_archivos, ej. durante una verificación masiva que recorre
        otras categorías) -- en ese caso solo se actualiza la
        biblioteca persistida, sin tocar ninguna fila visual."""
        ruta_anterior = registro.get("ruta")
        config = cargar_configuracion()
        tolerancia = tolerancia_silencio_para_genero(config, registro.get("genero", ""))
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)
        objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)
        analisis = analizar_audio(
            ruta_nueva, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio,
            objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs,
        )

        registro["ruta"] = ruta_nueva
        registro["duracion"] = obtener_duracion_formateada(ruta_nueva)
        registro["tamaño_bytes"] = self._tamano_bytes(ruta_nueva)
        registro["punto_inicio_ms"] = analisis["punto_inicio_ms"]
        registro["punto_fin_ms"] = analisis["punto_fin_ms"] or None
        registro["ganancia_db"] = analisis["ganancia_db"]
        registro["analizado"] = analisis["analizado"]

        if item is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, ruta_nueva)
            item.setData(0, ROL_REGISTRO, registro)
            item.setText(COL_DURACION, registro["duracion"])
            self._actualizar_vinculo_item(item, registro)
            self._actualizar_marcas_item(item, registro)
        self._sincronizar_registro_en_categoria(categoria, ruta_anterior, registro)
        self._guardar_biblioteca_debounced()
        return registro

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
        # ROL_CATEGORIA_ORIGEN, no _buscar_categoria_de_ruta -- mismo
        # criterio ya corregido en _eliminar_archivo() para no
        # depender de una `ruta` no vacía (ver "Cosas ya resueltas").
        categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
        if categoria is None:
            QMessageBox.warning(self, "Vigencia", "No se encontró la categoría de este archivo.")
            return

        dialogo = DialogoVigencia(
            registro.get("titulo", ""), registro.get("fecha_inicio"), registro.get("fecha_fin"), parent=self,
        )
        if dialogo.exec() != DialogoVigencia.DialogCode.Accepted:
            return

        fecha_inicio, fecha_fin = dialogo.resultado()
        registros = categoria.data(0, ROL_ARCHIVOS) or []
        indice = self._buscar_indice_registro(registros, registro)
        if indice < 0:
            return
        registros[indice]["fecha_inicio"] = fecha_inicio
        registros[indice]["fecha_fin"] = fecha_fin
        categoria.setData(0, ROL_ARCHIVOS, registros)
        item.setData(0, ROL_REGISTRO, registros[indice])
        self._guardar_biblioteca_debounced()

    def _editar_vigencia_masiva(self, items: list):
        """Pedido explícito ("selección múltiple... Vigencia: establecer
        una vigencia general para todos"): UN solo diálogo de Vigencia
        (mismo DialogoVigencia de siempre, ya genérico) cuyo resultado
        se aplica IGUAL a todos los seleccionados de una -- a diferencia
        de "Editar información" en lote, acá no hace falta un checkbox
        "cambiar o no": el pedido es fijar la MISMA vigencia para el
        lote entero, incluyendo dejarla sin restricción si no se tilda
        ninguna fecha."""
        if not items:
            return
        dialogo = DialogoVigencia(f"{len(items)} archivos seleccionados", None, None, parent=self)
        if dialogo.exec() != DialogoVigencia.DialogCode.Accepted:
            return
        fecha_inicio, fecha_fin = dialogo.resultado()

        tocados = 0
        for item in list(items):
            registro = item.data(0, ROL_REGISTRO)
            if not registro:
                continue
            categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria is None:
                continue
            registros = categoria.data(0, ROL_ARCHIVOS) or []
            indice = self._buscar_indice_registro(registros, registro)
            if indice < 0:
                continue
            registros[indice]["fecha_inicio"] = fecha_inicio
            registros[indice]["fecha_fin"] = fecha_fin
            categoria.setData(0, ROL_ARCHIVOS, registros)
            item.setData(0, ROL_REGISTRO, registros[indice])
            tocados += 1

        self._guardar_biblioteca_debounced()
        QMessageBox.information(self, "Vigencia", f"Vigencia actualizada en {tocados} archivo(s).")

    def _aplicar_analisis_silencio(self, items: list):
        """Pedido explícito ("agregá en el menú contextual la
        posibilidad de aplicar el análisis... a un ítem o varios"):
        recorta silencio + nivela UNO o VARIOS archivos seleccionados
        con los valores de tolerancia/umbral que están guardados AHORA
        MISMO en Configuración -- a diferencia del botón global
        "🔄 Reanalizar biblioteca" (acotado a género Música desde esta
        misma ronda, para no gastar tiempo de más en una biblioteca
        grande), esto funciona con CUALQUIER género -- es la vía para
        corregir a mano Publicidad/Separador/Pisador/Artística/HTH,
        eligiendo archivo por archivo o en lote.

        Mismo criterio de "nunca destruir una marca buena con un fallo
        nuevo" que ya usa `core/reanalizador_batch.py`: un archivo que
        ya tenía marcas reales y esta vuelta falla queda intacto, no
        se pisa con el fallback neutro."""
        if not items:
            return
        config = cargar_configuracion()
        umbral = config.get("reproduccion", {}).get("umbral_silencio_dbfs", -40.0)
        objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)

        analizados = 0
        preservados = 0
        fallidos = 0
        sin_archivo = 0
        for item in list(items):
            registro = item.data(0, ROL_REGISTRO)
            if not registro:
                continue
            categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria is None:
                continue
            ruta = registro.get("ruta")
            if not ruta or not os.path.exists(ruta):
                sin_archivo += 1
                continue

            registros = categoria.data(0, ROL_ARCHIVOS) or []
            indice = self._buscar_indice_registro(registros, registro)
            if indice < 0:
                continue
            registro_vivo = registros[indice]
            tenia_marcas_buenas = registro_vivo.get("analizado") is True

            tolerancia = tolerancia_silencio_para_genero(config, registro_vivo.get("genero"))
            analisis = analizar_audio(
                ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral,
                objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs,
            )

            if analisis["analizado"]:
                registro_vivo["punto_inicio_ms"] = analisis["punto_inicio_ms"]
                registro_vivo["punto_fin_ms"] = analisis["punto_fin_ms"] or None
                registro_vivo["ganancia_db"] = analisis["ganancia_db"]
                registro_vivo["analizado"] = True
                analizados += 1
            elif tenia_marcas_buenas:
                preservados += 1
            else:
                registro_vivo["punto_inicio_ms"] = 0
                registro_vivo["punto_fin_ms"] = None
                registro_vivo["ganancia_db"] = 0.0
                registro_vivo["analizado"] = False
                fallidos += 1

            categoria.setData(0, ROL_ARCHIVOS, registros)
            item.setData(0, ROL_REGISTRO, registro_vivo)
            self._actualizar_marcas_item(item, registro_vivo)

        self._guardar_biblioteca_debounced()

        mensaje = f"Análisis aplicado a {analizados} archivo(s)."
        if preservados:
            mensaje += f"\n{preservados} ya tenían marcas buenas y se preservaron (falló esta vuelta)."
        if fallidos:
            mensaje += f"\n{fallidos} fallaron de verdad (quedan sin recorte ni nivelado)."
        if sin_archivo:
            mensaje += f"\n{sin_archivo} se saltearon (sin archivo vinculado en disco)."
        QMessageBox.information(self, "Aplicar análisis de silencio", mensaje)

    def _revertir_analisis_silencio(self, items: list):
        """Contraparte de `_aplicar_analisis_silencio` (pedido
        explícito: "que pueda aplicarse tanto la acción como
        reversión"): deja el/los archivo(s) seleccionados en las
        MISMAS marcas neutras que un archivo recién importado sin
        analizar todavía -- sin recorte de silencio, sin nivelado
        (`punto_inicio_ms=0`, `punto_fin_ms=None`, `ganancia_db=0.0`,
        `analizado=False`). El audio real NUNCA se toca (enfoque no
        destructivo de siempre) -- esto solo saca la metadata,
        reversible aplicando el análisis de nuevo cuando se quiera."""
        if not items:
            return
        tocados = 0
        for item in list(items):
            registro = item.data(0, ROL_REGISTRO)
            if not registro:
                continue
            categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria is None:
                continue
            registros = categoria.data(0, ROL_ARCHIVOS) or []
            indice = self._buscar_indice_registro(registros, registro)
            if indice < 0:
                continue
            registro_vivo = registros[indice]
            registro_vivo["punto_inicio_ms"] = 0
            registro_vivo["punto_fin_ms"] = None
            registro_vivo["ganancia_db"] = 0.0
            registro_vivo["analizado"] = False
            categoria.setData(0, ROL_ARCHIVOS, registros)
            item.setData(0, ROL_REGISTRO, registro_vivo)
            self._actualizar_marcas_item(item, registro_vivo)
            tocados += 1

        self._guardar_biblioteca_debounced()
        QMessageBox.information(
            self, "Revertir análisis de silencio",
            f"Revertido en {tocados} archivo(s) -- vuelven a sonar sin recorte ni nivelado, "
            "como recién importados.",
        )

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
        # ROL_CATEGORIA_ORIGEN, no _buscar_categoria_de_ruta -- mismo
        # criterio ya corregido en _eliminar_archivo() para no
        # depender de una `ruta` no vacía (ver "Cosas ya resueltas").
        categoria_actual = item.data(0, ROL_CATEGORIA_ORIGEN)
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

        registros_actuales = categoria_actual.data(0, ROL_ARCHIVOS) or []
        indice = self._buscar_indice_registro(registros_actuales, registro)
        if indice < 0:
            return
        registro_vivo = registros_actuales[indice]
        registro_vivo["titulo"] = resultado["titulo"]
        registro_vivo["artista"] = resultado["artista"]
        registro_vivo["genero"] = resultado["genero"]

        if cambia_categoria:
            # Mismo patrón que _mover_archivos_a_categoria: se saca de
            # la categoría vieja y se agrega a la nueva, código y
            # demás metadata SIN tocar.
            registros_actuales.pop(indice)
            categoria_actual.setData(0, ROL_ARCHIVOS, registros_actuales)
            registros_destino = categoria_nueva.data(0, ROL_ARCHIVOS) or []
            registros_destino.append(registro_vivo)
            categoria_nueva.setData(0, ROL_ARCHIVOS, registros_destino)
        else:
            categoria_actual.setData(0, ROL_ARCHIVOS, registros_actuales)

        item.setData(0, ROL_REGISTRO, registro_vivo)
        self._guardar_biblioteca_debounced()

        if self._en_busqueda:
            self._buscar()
        else:
            self._on_categoria_seleccionada(self._categoria_actual(), None)

        if cambia_categoria:
            self.archivo_movido.emit(registro_vivo["titulo"], categoria_nueva.text(0))

    def _editar_informacion_masivo(self, items: list):
        """Pedido explícito ("selección múltiple... Editar Información
        -- todos, menos el nombre, poder darle la categoría"): un solo
        diálogo con checkboxes por campo (gui/dialogo_editar_informacion_masivo.py)
        -- Artista/Género/Categoría, cada uno "cambiar o no tocar" --
        aplicado a TODOS los seleccionados de una. El título/nombre
        editorial NUNCA se toca acá (cada archivo conserva el suyo,
        a diferencia de "Editar información" de un solo archivo)."""
        if not items:
            return
        from gui.dialogo_editar_informacion_masivo import DialogoEditarInformacionMasivo
        dialogo = DialogoEditarInformacionMasivo(len(items), self.tree_categorias, parent=self)
        if dialogo.exec() != DialogoEditarInformacionMasivo.DialogCode.Accepted:
            return
        cambios = dialogo.resultado()
        categoria_nueva = cambios["item_categoria"]
        if cambios["artista"] is None and cambios["genero"] is None and categoria_nueva is None:
            QMessageBox.information(self, "Editar información", "No se tildó ningún campo para cambiar.")
            return

        if categoria_nueva is not None:
            config = cargar_configuracion()
            if config["general"]["confirmar_antes_de_eliminar"]:
                respuesta = QMessageBox.question(
                    self, "Editar información",
                    f"Además de los demás cambios, esto mueve {len(items)} archivo(s)\n"
                    f"a la categoría '{categoria_nueva.text(0)}'. ¿Continuar?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if respuesta != QMessageBox.StandardButton.Yes:
                    return

        tocados = 0
        for item in list(items):
            registro = item.data(0, ROL_REGISTRO)
            if not registro:
                continue
            categoria_actual = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria_actual is None:
                continue
            registros_actuales = categoria_actual.data(0, ROL_ARCHIVOS) or []
            indice = self._buscar_indice_registro(registros_actuales, registro)
            if indice < 0:
                continue
            registro_vivo = registros_actuales[indice]

            if cambios["artista"] is not None:
                registro_vivo["artista"] = cambios["artista"]
            if cambios["genero"] is not None:
                registro_vivo["genero"] = cambios["genero"]

            if categoria_nueva is not None and categoria_nueva is not categoria_actual:
                registros_actuales.pop(indice)
                categoria_actual.setData(0, ROL_ARCHIVOS, registros_actuales)
                registros_destino = categoria_nueva.data(0, ROL_ARCHIVOS) or []
                registros_destino.append(registro_vivo)
                categoria_nueva.setData(0, ROL_ARCHIVOS, registros_destino)
            else:
                categoria_actual.setData(0, ROL_ARCHIVOS, registros_actuales)

            item.setData(0, ROL_REGISTRO, registro_vivo)
            tocados += 1

        self._guardar_biblioteca_debounced()

        if self._en_busqueda:
            self._buscar()
        else:
            self._on_categoria_seleccionada(self._categoria_actual(), None)

        QMessageBox.information(self, "Editar información", f"Se actualizaron {tocados} de {len(items)} archivo(s).")

    @staticmethod
    def _quitar_registro_de_lista(registros: list, registro: dict) -> list:
        """Filtra `registro` fuera de una lista de registros de
        categoría (ROL_ARCHIVOS). Bug real corregido ("no puedo
        eliminar ítems que NO estén vinculados... vuelven a
        aparecer"): filtrar solo por `ruta` no encuentra NADA cuando
        el archivo nunca se vinculó (ruta vacía) -- ahí se usa
        código+título como identidad (el código es único DENTRO de
        una categoría, ver GENERO_PREFIJOS_CODIGO/altas). Función pura,
        reutilizada por Eliminar, "Ubicar → Eliminar registro", y el
        buscador de duplicados."""
        ruta = registro.get("ruta") or ""
        if ruta:
            return [r for r in registros if r.get("ruta") != ruta]
        codigo = registro.get("codigo")
        titulo = registro.get("titulo")
        return [
            r for r in registros
            if not (not r.get("ruta") and r.get("codigo") == codigo and r.get("titulo") == titulo)
        ]

    @staticmethod
    def _buscar_indice_registro(registros: list, registro_referencia: dict) -> int:
        """Índice de `registro_referencia` dentro de `registros`
        (lista ROL_ARCHIVOS de una categoría) — MISMO criterio de
        identidad que `_quitar_registro_de_lista` (ruta si la tiene,
        código+título si no), pero para MUTAR el registro en el lugar
        en vez de filtrarlo afuera (usado por las ediciones en lote:
        Información/Vigencia). -1 si no se encuentra. Nunca por
        identidad de objeto Python -- ver la trampa de PySide6
        documentada en 'Cosas ya resueltas'."""
        ruta = registro_referencia.get("ruta") or ""
        if ruta:
            for i, r in enumerate(registros):
                if r.get("ruta") == ruta:
                    return i
            return -1
        codigo = registro_referencia.get("codigo")
        titulo = registro_referencia.get("titulo")
        for i, r in enumerate(registros):
            if not r.get("ruta") and r.get("codigo") == codigo and r.get("titulo") == titulo:
                return i
        return -1

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
            ruta = (registro.get("ruta") if registro else None) or ""
            indice = self.tree_archivos.indexOfTopLevelItem(item)
            if indice >= 0:
                self.tree_archivos.takeTopLevelItem(indice)
            if registro is None:
                continue
            # Referencia directa a la categoría de origen -- no
            # depende de `ruta` para ubicarla (ver ROL_CATEGORIA_ORIGEN).
            categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria is None:
                continue
            registros = self._quitar_registro_de_lista(categoria.data(0, ROL_ARCHIVOS) or [], registro)
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
            # Pedido explícito ("cuando arrastro y cambio de categoría,
            # preguntar si deseo arrastrar o crear una copia... el
            # archivo original permanece en su lugar, solo crea una
            # idéntica entrada de JSON en la categoría de destino"):
            # SIEMPRE se pregunta Mover/Copiar (no gateado por
            # "confirmar_antes_de_eliminar" -- no es una confirmación
            # de una acción riesgosa, es una decisión real de qué
            # hacer, así que sigue preguntándose aunque ese flag esté
            # apagado).
            accion = self._preguntar_mover_o_copiar(len(rutas_conocidas), item_categoria_destino.text(0))
            if accion == "mover":
                self._mover_archivos_a_categoria(rutas_conocidas, item_categoria_destino)
            elif accion == "copiar":
                self._copiar_archivos_a_categoria(rutas_conocidas, item_categoria_destino)

        if len(rutas_externas) == 1:
            self._dar_de_alta_archivo(rutas_externas[0], item_categoria_destino)
        elif len(rutas_externas) > 1:
            self._importar_archivos_masivo(rutas_externas, item_categoria_destino)

    def _preguntar_mover_o_copiar(self, cantidad: int, nombre_destino: str) -> str:
        """Extraído en su propio método (mismo criterio que el resto de
        las decisiones de esta app, ej. `_preguntar_que_hacer_con_archivo_perdido`)
        para poder testear la decisión sin simular un click real.
        Devuelve "mover" / "copiar" / "cancelar"."""
        descripcion = "1 archivo" if cantidad == 1 else f"{cantidad} archivos"
        caja = QMessageBox(self)
        caja.setWindowTitle("Cambiar de categoría")
        caja.setText(
            f"¿Qué querés hacer con {descripcion} en la categoría '{nombre_destino}'?\n\n"
            "Mover: el archivo deja de estar en su categoría de origen.\n\n"
            "Copiar: el original queda donde está tal cual, y se crea una "
            "entrada nueva (con su propio código, también reproducible) en "
            "esta categoría -- el mismo audio queda disponible desde las dos."
        )
        boton_mover = caja.addButton("Mover", QMessageBox.ButtonRole.AcceptRole)
        boton_copiar = caja.addButton("Copiar", QMessageBox.ButtonRole.ActionRole)
        caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(boton_mover)
        caja.exec()
        elegido = caja.clickedButton()
        if elegido is boton_mover:
            return "mover"
        if elegido is boton_copiar:
            return "copiar"
        return "cancelar"

    def _copiar_archivos_a_categoria(self, rutas: list, categoria_destino):
        """Contraparte de `_mover_archivos_a_categoria`: el registro
        ORIGINAL nunca se toca (sigue en su categoría de origen, sigue
        reproducible ahí) -- se crea una entrada NUEVA e independiente
        en la categoría destino, con los mismos metadatos (título/
        artista/género/ruta/análisis de silencio/vigencia), pero con
        un CÓDIGO propio correlativo DENTRO de la categoría destino
        (mismo criterio que cualquier alta nueva -- reusar el código
        de origen no tendría sentido en otra categoría y podría
        colisionar con lo que ya haya ahí). El archivo de audio en
        disco es UNO SOLO -- ahora queda disponible/reproducible desde
        las dos categorías."""
        copiados = []
        registros_destino = categoria_destino.data(0, ROL_ARCHIVOS) or []
        for ruta in rutas:
            registro_original = self.buscar_registro_por_ruta(ruta)
            if registro_original is None:
                continue
            genero = registro_original.get("genero", "")
            prefijo = GENERO_PREFIJOS_CODIGO.get(genero, "GEN")
            siguiente_numero = len(registros_destino) + 1
            copia = dict(registro_original)
            copia["codigo"] = f"{prefijo}{siguiente_numero:05d}"
            registros_destino.append(copia)
            copiados.append(copia.get("titulo", ruta))

        if not copiados:
            return

        categoria_destino.setData(0, ROL_ARCHIVOS, registros_destino)
        if not self._en_busqueda:
            self._on_categoria_seleccionada(self._categoria_actual(), None)

        self._guardar_biblioteca_debounced()
        nombres = copiados[0] if len(copiados) == 1 else f"{len(copiados)} archivos"
        self.archivo_copiado.emit(nombres, categoria_destino.text(0))

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

        hay_seleccion_unica = len(seleccionados) == 1
        hay_seleccion_multiple = len(seleccionados) > 1

        menu = QMenu(self)
        accion_importar = menu.addAction("📥 Importar...")
        menu.addSeparator()
        texto_exportar = "📤 Exportar..." if not hay_seleccion_multiple else f"📤 Exportar {len(seleccionados)}..."
        accion_exportar = menu.addAction(texto_exportar)
        accion_reemplazar = menu.addAction("⟲ Reemplazar...")
        texto_info = "✏ Editar información..." if not hay_seleccion_multiple else f"✏ Editar información {len(seleccionados)}..."
        accion_info = menu.addAction(texto_info)
        accion_editar = menu.addAction("🎚 Editar audio")
        texto_vigencia = "📅 Vigencia..." if not hay_seleccion_multiple else f"📅 Vigencia {len(seleccionados)}..."
        accion_vigencia = menu.addAction(texto_vigencia)
        accion_ubicar = menu.addAction("📍 Ubicar")
        menu.addSeparator()
        # Pedido explícito ("agregá en el menú contextual la
        # posibilidad de aplicar el análisis como revertirlo... a un
        # ítem o varios"): a diferencia del botón global de
        # Configuración (acotado a Música), esto funciona con
        # CUALQUIER género -- la vía manual para Publicidad/Separador/
        # Pisador/Artística/HTH.
        texto_aplicar_analisis = "🔈 Aplicar análisis de silencio..." if not hay_seleccion_multiple else f"🔈 Aplicar análisis de silencio a {len(seleccionados)}..."
        accion_aplicar_analisis = menu.addAction(texto_aplicar_analisis)
        texto_revertir_analisis = "↩ Revertir análisis de silencio..." if not hay_seleccion_multiple else f"↩ Revertir análisis de silencio en {len(seleccionados)}..."
        accion_revertir_analisis = menu.addAction(texto_revertir_analisis)
        menu.addSeparator()
        texto_eliminar = "✕ Eliminar" if len(seleccionados) <= 1 else f"✕ Eliminar {len(seleccionados)}"
        accion_eliminar = menu.addAction(texto_eliminar)

        # Pedido explícito ("selección múltiple... poder editar
        # masivamente Editar Información / Exportar / Vigencia"):
        # estas 3 ahora admiten cualquier cantidad >0 -- Reemplazar,
        # Editar audio y Ubicar siguen acotadas a UN solo archivo a la
        # vez (cambiar el archivo de audio, abrir un editor externo, o
        # buscar un archivo perdido puntual no son operaciones que
        # tenga sentido aplicar en lote sin ambigüedad).
        accion_exportar.setEnabled(len(seleccionados) > 0)
        accion_reemplazar.setEnabled(hay_seleccion_unica)
        accion_info.setEnabled(len(seleccionados) > 0)
        accion_editar.setEnabled(hay_seleccion_unica)
        accion_vigencia.setEnabled(len(seleccionados) > 0)
        accion_ubicar.setEnabled(hay_seleccion_unica)
        accion_aplicar_analisis.setEnabled(len(seleccionados) > 0)
        accion_revertir_analisis.setEnabled(len(seleccionados) > 0)
        accion_eliminar.setEnabled(len(seleccionados) > 0)

        accion_elegida = menu.exec(self.tree_archivos.viewport().mapToGlobal(posicion))
        if accion_elegida == accion_importar:
            self._agregar_archivos()
        elif accion_elegida == accion_exportar:
            self._exportar_archivos(seleccionados)
        elif accion_elegida == accion_reemplazar:
            self._reemplazar_archivo()
        elif accion_elegida == accion_info:
            if hay_seleccion_multiple:
                self._editar_informacion_masivo(seleccionados)
            else:
                self._editar_informacion_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_editar:
            self._editar_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_vigencia:
            if hay_seleccion_multiple:
                self._editar_vigencia_masiva(seleccionados)
            else:
                self._editar_vigencia(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_ubicar:
            self._ubicar_archivo(seleccionados[0] if seleccionados else None)
        elif accion_elegida == accion_aplicar_analisis:
            self._aplicar_analisis_silencio(seleccionados)
        elif accion_elegida == accion_revertir_analisis:
            self._revertir_analisis_silencio(seleccionados)
        elif accion_elegida == accion_eliminar:
            self._eliminar_archivo()

    def _exportar_archivos(self, items: list):
        """Exporta uno o varios archivos seleccionados (pedido
        explícito: "selección múltiple... Exportar, exportar todos
        los archivos seleccionados") a UNA carpeta elegida una sola
        vez -- cada archivo se copia con su nombre de archivo real
        (basename), sin renombrar."""
        if not items:
            return
        rutas = [item.data(0, Qt.ItemDataRole.UserRole) for item in items]
        rutas_validas = [r for r in rutas if r and os.path.exists(r)]
        if not rutas_validas:
            QMessageBox.warning(self, "Exportar", "No se encontró ningún archivo fuente.")
            return

        carpeta_destino = QFileDialog.getExistingDirectory(self, "Exportar a carpeta", os.path.expanduser("~"))
        if not carpeta_destino:
            return

        copiados = 0
        errores = []
        for ruta_origen in rutas_validas:
            destino = os.path.join(carpeta_destino, os.path.basename(ruta_origen))
            try:
                shutil.copy2(ruta_origen, destino)
                copiados += 1
            except OSError as error:
                errores.append(f"{os.path.basename(ruta_origen)}: {error}")

        if len(rutas_validas) == 1 and not errores:
            QMessageBox.information(self, "Exportar", f"Copiado a:\n{os.path.join(carpeta_destino, os.path.basename(rutas_validas[0]))}")
            return

        mensaje = f"Copiados {copiados} de {len(rutas_validas)} archivo(s) a:\n{carpeta_destino}"
        if errores:
            mensaje += "\n\nErrores:\n" + "\n".join(errores)
            QMessageBox.warning(self, "Exportar", mensaje)
        else:
            QMessageBox.information(self, "Exportar", mensaje)

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
    # "Ubicar" (pedido explícito): localizar el archivo en el explorador
    # de la PC sin ninguna acción sobre él; si el vínculo está roto
    # (archivo movido/borrado), ofrece buscarlo por tamaño/duración en
    # la carpeta Música real del sistema, o eliminar el registro.
    # ------------------------------------------------------------------

    # No hay un mecanismo universal en Linux (a diferencia de macOS/
    # Windows) para "abrir el explorador con este archivo YA
    # seleccionado" -- se prueban gestores de archivos conocidos que sí
    # soportan selección directa por línea de comandos, en orden.
    _GESTORES_ARCHIVOS_CON_SELECCION = (
        ("dolphin", ["--select", "{ruta}"]),
        ("nautilus", ["--select", "{ruta}"]),
        ("nemo", ["{ruta}"]),
        ("pcmanfm-qt", ["{ruta}"]),
        ("pcmanfm", ["{ruta}"]),
    )

    def _ubicar_archivo(self, item):
        if item is None:
            QMessageBox.information(self, "Ubicar", "Seleccioná un archivo.")
            return
        registro = item.data(0, ROL_REGISTRO)
        if not registro:
            return
        ruta = registro.get("ruta")

        if ruta and os.path.exists(ruta):
            self._localizar_en_explorador_de_archivos(ruta)
            return

        decision = self._preguntar_que_hacer_con_archivo_perdido(registro.get("titulo", ""), ruta or "")
        if decision == "eliminar":
            self._eliminar_registro_sin_confirmar(item)
        elif decision == "buscar":
            # Bug real corregido: antes se ubicaba la categoría vía
            # _buscar_categoria_de_ruta(ruta) -- con `ruta` vacía
            # (archivo NUNCA vinculado, el caso más común de este
            # botón) esa comparación no encuentra nada. Usa la
            # referencia directa guardada en el propio ítem.
            categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
            if categoria is None:
                QMessageBox.warning(self, "Buscar archivo", "No se encontró la categoría de este archivo.")
                return
            # El botón "⏭ Saltar" del diálogo de candidatos (pedido
            # explícito) sigue directo con el PRÓXIMO archivo sin
            # vincular de la MISMA categoría -- se arma la cola acá
            # (el elegido primero, con su item real; los siguientes
            # sin item porque no están necesariamente visibles) y se
            # delega en el mismo procesador que usa la verificación
            # masiva de Configuración.
            registros = categoria.data(0, ROL_ARCHIVOS) or []
            if ruta:
                indice_actual = next((i for i, r in enumerate(registros) if r.get("ruta") == ruta), -1)
            else:
                codigo = registro.get("codigo")
                titulo = registro.get("titulo")
                indice_actual = next(
                    (i for i, r in enumerate(registros)
                     if not r.get("ruta") and r.get("codigo") == codigo and r.get("titulo") == titulo),
                    -1,
                )
            entradas = [(categoria, registro, item)]
            for r in registros[indice_actual + 1:]:
                r_ruta = r.get("ruta")
                if not r_ruta or not os.path.exists(r_ruta):
                    entradas.append((categoria, r, None))
            self._procesar_lista_de_perdidos(entradas)

    def _localizar_en_explorador_de_archivos(self, ruta: str):
        for ejecutable, args_patron in self._GESTORES_ARCHIVOS_CON_SELECCION:
            ruta_ejecutable = shutil.which(ejecutable)
            if not ruta_ejecutable:
                continue
            args = [arg.format(ruta=ruta) for arg in args_patron]
            QProcess.startDetached(ruta_ejecutable, args)
            return

        # Ningún gestor con soporte de selección disponible -- se cae a
        # abrir la carpeta contenedora con el programa default del
        # sistema (sin selección puntual, pero siempre funciona).
        carpeta = os.path.dirname(ruta)
        if QDesktopServices.openUrl(QUrl.fromLocalFile(carpeta)):
            return

        QMessageBox.warning(
            self, "Ubicar",
            f"No se pudo abrir el explorador de archivos del sistema.\nLa carpeta es:\n{carpeta}",
        )

    def _preguntar_que_hacer_con_archivo_perdido(self, titulo: str, ruta: str) -> str:
        """Extraído en su propio método (mismo criterio que
        MainWindow._preguntar_actualizar_ahora) para poder testear la
        decisión sin simular un click real sobre un QMessageBox --
        offscreen no puede. Devuelve "buscar" / "eliminar" / "cancelar"."""
        caja = QMessageBox(self)
        caja.setWindowTitle("Archivo no encontrado")
        texto_ruta = ruta if ruta else "(sin ruta registrada)"
        caja.setText(
            f"No se encontró el archivo de '{titulo}' en su ubicación:\n{texto_ruta}\n\n"
            "¿Qué querés hacer?"
        )
        boton_buscar = caja.addButton("Buscarlo...", QMessageBox.ButtonRole.AcceptRole)
        boton_eliminar = caja.addButton("Eliminar registro", QMessageBox.ButtonRole.DestructiveRole)
        caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(boton_buscar)
        caja.exec()
        elegido = caja.clickedButton()
        if elegido is boton_buscar:
            return "buscar"
        if elegido is boton_eliminar:
            return "eliminar"
        return "cancelar"

    def _eliminar_registro_sin_confirmar(self, item):
        """Quita UN registro sin pedir confirmación aparte -- usado
        desde "Ubicar" sobre un archivo perdido, donde la propia
        pregunta "¿Buscarlo o eliminar el registro?" YA es la
        confirmación (reusar _eliminar_archivo() dispararía una
        segunda, redundante, gateada por confirmar_antes_de_eliminar).

        Bug real corregido (mismo de _eliminar_archivo() más arriba):
        el caso de uso PRINCIPAL de este método es justamente un
        registro con `ruta` vacía o rota, así que el viejo `if not
        ruta: return` bloqueaba el borrado exactamente en el caso que
        más importaba. Usa ROL_CATEGORIA_ORIGEN, sin depender de ruta."""
        registro = item.data(0, ROL_REGISTRO)
        ruta = (registro.get("ruta") if registro else None) or ""
        indice = self.tree_archivos.indexOfTopLevelItem(item)
        if indice >= 0:
            self.tree_archivos.takeTopLevelItem(indice)
        if registro is None:
            return
        categoria = item.data(0, ROL_CATEGORIA_ORIGEN)
        if categoria is None:
            return
        registros = self._quitar_registro_de_lista(categoria.data(0, ROL_ARCHIVOS) or [], registro)
        categoria.setData(0, ROL_ARCHIVOS, registros)
        self._guardar_biblioteca_debounced()
        self.archivo_eliminado.emit(ruta)

    # Pedido explícito ("que la búsqueda la haga en toda la carpeta
    # Música sin tomar en cuenta las rutas de Configuraciones"): no usa
    # `rutas.biblioteca_publicidad`/`biblioteca_musical` del config —
    # busca la carpeta MÚSICA real del sistema, respetando el idioma
    # (mismo mecanismo ya usado en instalar.sh para el Escritorio, que
    # en Q4OS en español es "Escritorio", no "Desktop" — acá aplica
    # igual para "Música" vs "Music"/"Musica" sin tilde).
    def _resolver_carpeta_musica_real(self):
        try:
            resultado = subprocess.run(
                ["xdg-user-dir", "MUSIC"], capture_output=True, text=True, timeout=3,
            )
            carpeta = resultado.stdout.strip()
            if carpeta and os.path.isdir(carpeta):
                return carpeta
        except (OSError, subprocess.SubprocessError):
            pass

        for nombre in ("Música", "Musica", "Music"):
            candidata = os.path.expanduser(f"~/{nombre}")
            if os.path.isdir(candidata):
                return candidata
        return None

    def _procesar_lista_de_perdidos(self, entradas: list) -> bool:
        """Procesa una lista de (categoria, registro, item) con
        vínculo roto, UNO POR UNO, con el mismo diálogo de "Buscar" --
        usada tanto por un "Ubicar" individual (cola = el resto de la
        MISMA categoría, para que "⏭ Saltar" tenga a dónde seguir)
        como por la verificación masiva de Configuración (cola = TODA
        la biblioteca). `item` puede ser None si ese registro no está
        actualmente visible en tree_archivos. Se detiene del todo si
        el operador cierra el diálogo de candidatos con "Cancelar"
        (devuelve False); si termina de recorrer toda la lista,
        devuelve True."""
        if not entradas:
            return True
        carpeta_musica = self._resolver_carpeta_musica_real()
        if not carpeta_musica:
            QMessageBox.warning(
                self, "Buscar archivo",
                "No se encontró la carpeta de Música del sistema para poder buscar ahí.",
            )
            return False
        for categoria, registro, item in entradas:
            ruta = registro.get("ruta")
            if ruta and os.path.exists(ruta):
                # Ya se resolvió solo mientras tanto (ej. Vincular
                # apuntó por casualidad al mismo archivo que otro
                # registro roto) -- no hace falta volver a preguntar.
                continue
            if not self._buscar_archivo_perdido(item, registro, categoria, carpeta_musica):
                return False
        return True

    def _buscar_archivo_perdido(self, item, registro: dict, categoria, carpeta_musica: str) -> bool:
        """Escanea TODA la carpeta Música real del sistema (pedido
        explícito, ver _resolver_carpeta_musica_real -- ignora las
        rutas configuradas en Configuración → Rutas) buscando
        candidatos. Criterio PRIMARIO: tamaño en bytes (pedido
        explícito, "primero por tamaño, y luego por duración") -- una
        copia/renombrada del MISMO archivo pesa exactamente igual,
        mientras que la duración estimada por mutagen puede variar un
        segundo entre lecturas/formatos, y eso hacía que a veces "no
        encontrara nada" aunque el archivo real estuviera ahí. Si el
        registro no tiene tamaño guardado (import de antes de esa
        función), se cae a la duración como único criterio posible.

        Devuelve True si hay que SEGUIR con el próximo de la cola
        (Vincular, Saltar, o sin candidatos), False si el operador
        cerró el diálogo con Cancelar (detiene TODA la cola)."""
        duracion_objetivo = registro.get("duracion")
        tamano_objetivo = registro.get("tamaño_bytes")
        # Pedido explícito ("algunos archivos son Cierre.mp3 y no sé a
        # qué programa o categoría corresponde... necesito esa
        # información para vincular correctamente"): la categoría/
        # subcategoría del registro roto viaja junto al título a
        # DialogoVincularArchivo, para que un título genérico no deje
        # al operador adivinando de qué material se trata.
        ruta_categoria_texto = " > ".join(self.ruta_de_categoria(categoria))

        self.solicitud_preload.emit(f"Buscando: {registro.get('titulo', '')}...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        candidatos = []
        try:
            contador = 0
            for raiz, _dirs, archivos in os.walk(carpeta_musica):
                for nombre in archivos:
                    if not nombre.lower().endswith(EXTENSIONES_SOPORTADAS):
                        continue
                    ruta_candidata = os.path.join(raiz, nombre)
                    contador += 1
                    if contador % 25 == 0:
                        QApplication.processEvents()

                    if tamano_objetivo is not None:
                        # Filtro PRIMARIO por tamaño -- barato (no abre
                        # el archivo), se calcula para TODOS antes de
                        # pagar el costo de mutagen para la duración.
                        tamano_candidato = self._tamano_bytes(ruta_candidata)
                        if tamano_candidato != tamano_objetivo:
                            continue
                        duracion_candidata = obtener_duracion_formateada(ruta_candidata)
                    else:
                        # Sin tamaño guardado en el registro, la
                        # duración es el único criterio disponible.
                        duracion_candidata = obtener_duracion_formateada(ruta_candidata)
                        if duracion_objetivo and duracion_candidata != duracion_objetivo:
                            continue
                        tamano_candidato = self._tamano_bytes(ruta_candidata)

                    candidatos.append({
                        "ruta": ruta_candidata,
                        "duracion": duracion_candidata,
                        "tamaño_bytes": tamano_candidato,
                        "tamaño_coincide": tamano_objetivo is not None and tamano_candidato == tamano_objetivo,
                        "duracion_coincide": bool(duracion_objetivo) and duracion_candidata == duracion_objetivo,
                    })
        finally:
            QApplication.restoreOverrideCursor()

        if not candidatos:
            criterio = f"el mismo tamaño ({tamano_objetivo} bytes)" if tamano_objetivo is not None else f"la misma duración ({duracion_objetivo})"
            QMessageBox.information(
                self, "Buscar archivo",
                f"No se encontró ningún archivo con {criterio} para '{registro.get('titulo', '')}' "
                f"(categoría: {ruta_categoria_texto})\nen la carpeta Música ({carpeta_musica}).",
            )
            return True

        from gui.dialogo_vincular_archivo import DialogoVincularArchivo
        audio_cfg = cargar_configuracion()["audio"]
        id_dispositivo_preescucha = (
            audio_cfg["dispositivo_preescucha"] if audio_cfg["dispositivo_preescucha"] != "default" else None
        )
        dialogo = DialogoVincularArchivo(
            registro.get("titulo", ""), candidatos, id_dispositivo_preescucha, ruta_categoria_texto, parent=self,
        )
        resultado_codigo = dialogo.exec()

        if resultado_codigo == DialogoVincularArchivo.SALTAR:
            return True
        if resultado_codigo != DialogoVincularArchivo.DialogCode.Accepted:
            return False

        ruta_elegida = dialogo.resultado()
        if not ruta_elegida:
            return False

        self._aplicar_nuevo_archivo(item, categoria, registro, ruta_elegida)
        QMessageBox.information(
            self, "Vincular", f"'{registro.get('titulo', '')}' quedó vinculado al archivo elegido.",
        )
        return True

    def verificar_archivos_perdidos_biblioteca(self):
        """Pedido explícito (Configuración → Diagnóstico): "hacer esta
        ubicación de archivos perdidos de manera masiva en todo el
        explorador... verificación general de todos los archivos sin
        vinculación". Recorre TODA la biblioteca, junta los registros
        con el archivo roto/faltante, y los procesa uno por uno con el
        MISMO mecanismo que ya usa "⏭ Saltar" en un "Ubicar" individual
        (_procesar_lista_de_perdidos) -- sin tener que ir categoría por
        categoría a mano."""
        pendientes = []

        def visitar(item_categoria):
            for registro in (item_categoria.data(0, ROL_ARCHIVOS) or []):
                ruta = registro.get("ruta")
                if not ruta or not os.path.exists(ruta):
                    pendientes.append((item_categoria, registro, None))

        self._para_cada_categoria(visitar)

        if not pendientes:
            QMessageBox.information(
                self, "Verificar archivos perdidos",
                "No se encontró ningún archivo con vínculo roto en toda la biblioteca.",
            )
            return

        respuesta = QMessageBox.question(
            self, "Verificar archivos perdidos",
            f"Se encontraron {len(pendientes)} archivo(s) con vínculo roto en toda la "
            "biblioteca.\n¿Revisarlos ahora, uno por uno (Previo/Saltar/Vincular)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        if self._procesar_lista_de_perdidos(pendientes):
            QMessageBox.information(
                self, "Verificar archivos perdidos",
                "Verificación completa: se revisaron todos los archivos con vínculo roto.",
            )

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
    # Buscador de duplicados (pedido explícito: "búsqueda de duplicados
    # en el explorador por nombre, duración y tamaño con opción de
    # elegir alguno de esos filtros incluso los 3 juntos... menú
    # contextual de mover o eliminar").
    # ------------------------------------------------------------------
    def buscar_duplicados_biblioteca(self, por_nombre: bool = True,
                                      por_duracion: bool = False,
                                      por_tamano: bool = False) -> list:
        """Agrupa registros de TODA la biblioteca que coinciden en los
        criterios elegidos (combinables). Devuelve una lista de grupos
        -- cada grupo, una lista de tuplas (registro, categoria) -- y
        solo incluye grupos de 2 o más (duplicados reales). Sin ningún
        criterio activo no hay nada que agrupar. Un registro con algún
        dato faltante en un criterio activo (ej. tamaño no cacheado)
        se excluye de ese agrupamiento -- nunca se junta "sin dato"
        con "sin dato", evitaría falsos positivos."""
        if not (por_nombre or por_duracion or por_tamano):
            return []

        grupos: dict = {}
        orden = []

        def clave_de(registro):
            partes = []
            if por_nombre:
                partes.append(("nombre", (registro.get("titulo") or "").strip().lower()))
            if por_duracion:
                partes.append(("duracion", registro.get("duracion") or ""))
            if por_tamano:
                partes.append(("tamano", registro.get("tamaño_bytes")))
            return tuple(partes)

        def visitar(item):
            for registro in (item.data(0, ROL_ARCHIVOS) or []):
                clave = clave_de(registro)
                if any(valor in (None, "") for _, valor in clave):
                    continue
                if clave not in grupos:
                    grupos[clave] = []
                    orden.append(clave)
                grupos[clave].append((registro, item))

        self._para_cada_categoria(visitar)
        return [grupos[clave] for clave in orden if len(grupos[clave]) > 1]

    def mover_registro_a_otra_categoria(self, registro: dict, categoria_origen, categoria_destino) -> bool:
        """Mueve UN registro puntual (ya resuelto por el llamador, ej.
        el buscador de duplicados) entre categorías -- variante de
        _mover_archivos_a_categoria() que no depende de resolver la
        categoría de origen buscando por ruta (necesario acá porque un
        duplicado sin vincular tiene `ruta` vacía)."""
        if categoria_origen is None or categoria_destino is None or categoria_origen is categoria_destino:
            return False
        registros_origen = self._quitar_registro_de_lista(categoria_origen.data(0, ROL_ARCHIVOS) or [], registro)
        categoria_origen.setData(0, ROL_ARCHIVOS, registros_origen)
        registros_destino = categoria_destino.data(0, ROL_ARCHIVOS) or []
        registros_destino.append(registro)
        categoria_destino.setData(0, ROL_ARCHIVOS, registros_destino)
        if not self._en_busqueda and self._categoria_actual() in (categoria_origen, categoria_destino):
            self._on_categoria_seleccionada(self._categoria_actual(), None)
        self._guardar_biblioteca_debounced()
        self.archivo_movido.emit(registro.get("titulo", ""), categoria_destino.text(0))
        return True

    def eliminar_registro_de_categoria(self, registro: dict, categoria) -> bool:
        """Elimina definitivamente UN registro (entrada JSON) de la
        biblioteca -- usado por el buscador de duplicados. Nota
        importante: esto borra el REGISTRO, nunca el archivo físico --
        distinto de "🗑 Eliminar" sobre un candidato del diálogo
        Vincular (gui/dialogo_vincular_archivo.py), que borra el
        archivo de la PC y nunca toca la biblioteca JSON."""
        if categoria is None:
            return False
        registros = self._quitar_registro_de_lista(categoria.data(0, ROL_ARCHIVOS) or [], registro)
        categoria.setData(0, ROL_ARCHIVOS, registros)
        if not self._en_busqueda and categoria is self._categoria_actual():
            self._on_categoria_seleccionada(categoria, None)
        self._guardar_biblioteca_debounced()
        self.archivo_eliminado.emit(registro.get("ruta") or "")
        return True

    # ------------------------------------------------------------------
    def guardar_disposicion(self):
        guardar_columnas("explorador_archivos", self.tree_archivos)

    def restaurar_disposicion(self):
        restaurar_columnas("explorador_archivos", self.tree_archivos)
