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
    QMessageBox, QInputDialog, QMenu, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QUrl, QProcess
from PySide6.QtGui import QColor, QBrush, QDesktopServices

from gui.common_widgets import ArbolOrigenArrastre, ArbolConDrop, configurar_columnas_ajustables, SliderBusqueda
from gui.indicador_en_vivo import IndicadorEnVivo
from gui.styles import GENERO_COLORES, GENERO_PREFIJOS_CODIGO, color_texto_legible
from gui.dialogo_agregar_archivo import DialogoAgregarArchivo
from gui.dialogo_agregar_archivos_masivo import DialogoAgregarArchivosMasivo
from gui.dialogo_vigencia import DialogoVigencia
from gui.estado_ui import guardar_columnas, restaurar_columnas
from core.analizador_audio import analizar_audio
from core.audio_engine import obtener_duracion_formateada
from config.settings import cargar_configuracion, cargar_biblioteca, guardar_biblioteca

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._en_busqueda = False
        self._arrastrando_slider_preview = False
        self._colores_genero = dict(GENERO_COLORES)
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
        self.btn_expandir.clicked.connect(self.solicitud_alternar_expansion.emit)
        barra_superior.addWidget(self.txt_busqueda)
        barra_superior.addWidget(self.btn_buscar)
        barra_superior.addWidget(self.btn_limpiar_busqueda)
        barra_superior.addWidget(self.btn_expandir)
        layout_grupo.addLayout(barra_superior)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # ---------- Columna izquierda: categorías ----------
        panel_categorias = QWidget()
        layout_categorias = QVBoxLayout(panel_categorias)
        layout_categorias.setContentsMargins(0, 0, 0, 0)

        self.tree_categorias = ArbolConDrop()
        self.tree_categorias.setObjectName("tree_categorias")
        self.tree_categorias.setHeaderLabels(["Categoría"])
        self.tree_categorias.setColumnCount(1)
        self.tree_categorias.currentItemChanged.connect(self._on_categoria_seleccionada)
        self.tree_categorias.archivos_soltados.connect(self._on_archivos_soltados_en_categoria)
        layout_categorias.addWidget(self.tree_categorias)

        barra_categorias = QHBoxLayout()
        self.btn_nueva_categoria = QPushButton("＋ Categoría")
        self.btn_nueva_categoria.setToolTip("Nueva categoría de primer nivel")
        self.btn_nueva_subcategoria = QPushButton("＋ Sub")
        self.btn_nueva_subcategoria.setToolTip("Nueva subcategoría dentro de la seleccionada")
        self.btn_eliminar_categoria = QPushButton("✕")
        self.btn_eliminar_categoria.setToolTip("Eliminar categoría")
        self.btn_nueva_categoria.clicked.connect(self._nueva_categoria)
        self.btn_nueva_subcategoria.clicked.connect(self._nueva_subcategoria)
        self.btn_eliminar_categoria.clicked.connect(self._eliminar_categoria)
        barra_categorias.addWidget(self.btn_nueva_categoria)
        barra_categorias.addWidget(self.btn_nueva_subcategoria)
        barra_categorias.addWidget(self.btn_eliminar_categoria)
        layout_categorias.addLayout(barra_categorias)

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

        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._mostrar_menu_contextual)

        layout_archivos.addWidget(self.tree_archivos)

        barra_archivos = QHBoxLayout()
        self.btn_agregar = QPushButton("＋ Agregar")
        self.btn_reemplazar = QPushButton("⟲ Reemplazar")
        self.btn_eliminar = QPushButton("✕ Eliminar")
        self.btn_agregar.clicked.connect(self._agregar_archivos)
        self.btn_reemplazar.clicked.connect(self._reemplazar_archivo)
        self.btn_eliminar.clicked.connect(self._eliminar_archivo)
        for btn in (self.btn_agregar, self.btn_reemplazar, self.btn_eliminar):
            barra_archivos.addWidget(btn)
        layout_archivos.addLayout(barra_archivos)

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
    # resultados en el mismo tree_archivos — mientras tanto se
    # deshabilita el árbol de categorías para no mezclar estados.
    # ------------------------------------------------------------------
    def _buscar(self):
        texto = self.txt_busqueda.text().strip().lower()
        if not texto:
            self._limpiar_busqueda()
            return

        resultados = []

        def visitar(item):
            for registro in (item.data(0, ROL_ARCHIVOS) or []):
                titulo = (registro.get("titulo") or "").lower()
                artista = (registro.get("artista") or "").lower()
                if texto in titulo or texto in artista:
                    resultados.append(registro)

        self._para_cada_categoria(visitar)

        self._en_busqueda = True
        self.tree_categorias.setEnabled(False)
        self.tree_archivos.clear()
        for registro in resultados:
            self._agregar_fila_archivo(registro)

        self.busqueda_realizada.emit(len(resultados))

    def _limpiar_busqueda(self):
        if not self._en_busqueda and not self.txt_busqueda.text():
            return
        self._en_busqueda = False
        self.txt_busqueda.clear()
        self.tree_categorias.setEnabled(True)
        self._on_categoria_seleccionada(self._categoria_actual(), None)

    # ------------------------------------------------------------------
    # Persistencia (config/data/biblioteca.json) — ver nota al inicio
    # del archivo. Se guarda ante cada mutación, no solo al cerrar.
    # ------------------------------------------------------------------
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
        return item

    def _categoria_actual(self):
        return self.tree_categorias.currentItem()

    def _on_categoria_seleccionada(self, actual, anterior):
        if self._en_busqueda:
            return  # no pisar los resultados de búsqueda con la categoría
        self.tree_archivos.clear()
        if actual is None:
            return
        registros = actual.data(0, ROL_ARCHIVOS) or []
        for registro in registros:
            self._agregar_fila_archivo(registro)

    def _agregar_fila_archivo(self, registro: dict):
        duracion = registro.get("duracion")
        if not duracion:
            # Migración silenciosa: registros guardados antes de que
            # existiera la columna Duración la calculan una vez y
            # quedan con ella cacheada de ahí en más.
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
        self.tree_archivos.addTopLevelItem(item)
        return item

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
        nombre, ok = QInputDialog.getText(self, "Nueva categoría", "Nombre de la categoría:")
        if not ok or not nombre.strip():
            return
        item = self._crear_item_categoria(None, nombre.strip())
        self.tree_categorias.setCurrentItem(item)
        self._guardar_biblioteca()

    def _nueva_subcategoria(self):
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
        self._guardar_biblioteca()

    def _eliminar_categoria(self):
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
        self._guardar_biblioteca()

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
        tolerancia = config["reproduccion"].get("tolerancia_silencio_segundos", 2.0)
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

        self._guardar_biblioteca()
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
        tolerancia = config["reproduccion"].get("tolerancia_silencio_segundos", 2.0)
        umbral_silencio = config["reproduccion"].get("umbral_silencio_dbfs", -40.0)

        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        siguiente_numero = len(registros) + 1
        prefijo = GENERO_PREFIJOS_CODIGO.get(genero, "GEN")

        for ruta in rutas:
            analisis = analizar_audio(ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral_silencio)
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

        item_categoria.setData(0, ROL_ARCHIVOS, registros)
        if item_categoria is self._categoria_actual() and not self._en_busqueda:
            self._on_categoria_seleccionada(item_categoria, None)

        self._guardar_biblioteca()
        self.archivo_agregado.emit(f"{len(rutas)} archivos")

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
        tolerancia = config["reproduccion"].get("tolerancia_silencio_segundos", 2.0)
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
        self._guardar_biblioteca()

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
        self._guardar_biblioteca()

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
            self._guardar_biblioteca()
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

        self._guardar_biblioteca()
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
        accion_editar = menu.addAction("🎚 Editar")
        accion_vigencia = menu.addAction("📅 Vigencia...")
        menu.addSeparator()
        texto_eliminar = "✕ Eliminar" if len(seleccionados) <= 1 else f"✕ Eliminar {len(seleccionados)}"
        accion_eliminar = menu.addAction(texto_eliminar)

        hay_seleccion_unica = len(seleccionados) == 1
        accion_exportar.setEnabled(hay_seleccion_unica)
        accion_reemplazar.setEnabled(hay_seleccion_unica)
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

    def _editar_archivo(self, item):
        if item is None:
            return
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta or not os.path.exists(ruta):
            QMessageBox.warning(self, "Editar", "No se encontró el archivo fuente.")
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

        self._guardar_biblioteca()
        self.archivo_eliminado.emit(ruta)
        return True

    # ------------------------------------------------------------------
    def guardar_disposicion(self):
        guardar_columnas("explorador_archivos", self.tree_archivos)

    def restaurar_disposicion(self):
        restaurar_columnas("explorador_archivos", self.tree_archivos)
