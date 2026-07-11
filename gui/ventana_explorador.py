"""
gui/ventana_explorador.py
--------------------------------------------------------
Ventana 3 (Derecha): Explorador de Medios.

- Izquierda: árbol de CATEGORÍAS, con subcategorías sin límite de
  niveles (cada categoría puede tener hijas, y esas hijas más
  hijas, etc.).
- Derecha: archivos de la categoría seleccionada — columnas
  Título / Artista / Género / Código, pintadas según el color del
  género (Música=verde, Publicidad=amarillo, Separador=naranja,
  Pisador=violeta, Artística=azul). Es el ORIGEN real del Drag &
  Drop hacia Ventana 1, Ventana 2, la Auxiliar y el Programador.
- Al agregar un archivo se abre DialogoAgregarArchivo para elegir
  categoría, nombre editorial, artista y género; el código
  correlativo se asigna solo. Ahí mismo se dispara el análisis de
  audio (core/analizador_audio.py): recorte de silencios de
  entrada/salida y nivelado de volumen, guardado como metadata no
  destructiva del registro.
- Menú contextual (botón derecho): Importar, Exportar, Reemplazar,
  Eliminar, Editar (abre el editor de audio del sistema).
- Botones Play/Stop para preescuchar el archivo seleccionado.

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
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidget,
    QTreeWidgetItem, QPushButton, QFileDialog, QSplitter,
    QMessageBox, QInputDialog, QMenu
)
from PySide6.QtCore import Qt, Signal, QUrl, QProcess
from PySide6.QtGui import QColor, QBrush, QDesktopServices

from gui.common_widgets import ArbolOrigenArrastre, ArbolConDrop, configurar_columnas_ajustables
from gui.styles import GENERO_COLORES, GENEROS_CON_TEXTO_OSCURO
from gui.dialogo_agregar_archivo import DialogoAgregarArchivo
from gui.estado_ui import guardar_columnas, restaurar_columnas
from core.analizador_audio import analizar_audio
from config.settings import cargar_configuracion, cargar_biblioteca, guardar_biblioteca

EXTENSIONES_SOPORTADAS = (".mp3", ".wav", ".mp4", ".m4a")

# Roles de datos propios (por encima de Qt.ItemDataRole.UserRole)
ROL_ARCHIVOS = Qt.ItemDataRole.UserRole + 20     # en ítem de categoría: list[dict]
ROL_REGISTRO = Qt.ItemDataRole.UserRole + 21     # en ítem de archivo: dict completo


class VentanaExplorador(QWidget):
    """Panel de exploración y gestión de la biblioteca de audio."""

    archivo_agregado = Signal(str)
    archivo_eliminado = Signal(str)
    archivo_movido = Signal(str, str)   # (titulo, nombre_categoria_destino)
    solicitud_play_preview = Signal()
    solicitud_stop_preview = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self._cargar_biblioteca_inicial()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(6)

        grupo = QGroupBox("EXPLORADOR DE MEDIOS")
        layout_grupo = QVBoxLayout(grupo)

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
        self.tree_categorias.archivo_soltado.connect(self._on_archivo_soltado_en_categoria)
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
        self.tree_archivos.setHeaderLabels(["Título", "Artista", "Género", "Código"])
        self.tree_archivos.setColumnCount(4)
        self.tree_archivos.setRootIsDecorated(False)
        configurar_columnas_ajustables(self.tree_archivos, [180, 110, 85])
        self.tree_archivos.header().setMinimumSectionSize(45)

        self.tree_archivos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_archivos.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tree_archivos.itemDoubleClicked.connect(lambda item, columna: self.solicitud_play_preview.emit())

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

        # --- Preview (Play/Stop) ---
        barra_preview = QHBoxLayout()
        self.btn_play_preview = QPushButton("▶ Play")
        self.btn_play_preview.setObjectName("btnPlay")
        self.btn_stop_preview = QPushButton("■ Stop")
        self.btn_stop_preview.setObjectName("btnStop")
        self.btn_play_preview.clicked.connect(self.solicitud_play_preview.emit)
        self.btn_stop_preview.clicked.connect(self.solicitud_stop_preview.emit)
        barra_preview.addWidget(self.btn_play_preview)
        barra_preview.addWidget(self.btn_stop_preview)
        layout_archivos.addLayout(barra_preview)

        self.splitter.addWidget(panel_categorias)
        self.splitter.addWidget(panel_archivos)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([140, 260])

        layout_grupo.addWidget(self.splitter)
        layout_principal.addWidget(grupo)

    # ------------------------------------------------------------------
    # Persistencia (config/data/biblioteca.json) — ver nota al inicio
    # del archivo. Se guarda ante cada mutación, no solo al cerrar.
    # ------------------------------------------------------------------
    def _cargar_biblioteca_inicial(self):
        categorias_guardadas = cargar_biblioteca()
        if categorias_guardadas:
            self._cargar_categorias_desde_datos(categorias_guardadas)
        else:
            self._cargar_categorias_demo()
            self._guardar_biblioteca()  # deja persistida la base inicial

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
    def _cargar_categorias_demo(self):
        raiz_musica = self._crear_item_categoria(None, "Música")
        self._crear_item_categoria(raiz_musica, "Nacional")
        self._crear_item_categoria(raiz_musica, "Internacional")
        self._crear_item_categoria(None, "Publicidad")
        self._crear_item_categoria(None, "Separadores")
        self._crear_item_categoria(None, "Sin categorizar")

        if self.tree_categorias.topLevelItemCount() > 0:
            self.tree_categorias.setCurrentItem(self.tree_categorias.topLevelItem(0))
        self.tree_categorias.expandAll()

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
        self.tree_archivos.clear()
        if actual is None:
            return
        registros = actual.data(0, ROL_ARCHIVOS) or []
        for registro in registros:
            self._agregar_fila_archivo(registro)

    def _agregar_fila_archivo(self, registro: dict):
        item = QTreeWidgetItem([
            registro.get("titulo", ""),
            registro.get("artista", ""),
            registro.get("genero", ""),
            registro.get("codigo", ""),
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))  # para el drag
        item.setData(0, ROL_REGISTRO, registro)
        self._pintar_por_genero(item, registro.get("genero", ""))
        self.tree_archivos.addTopLevelItem(item)
        return item

    def _pintar_por_genero(self, item: QTreeWidgetItem, genero: str):
        color_hex = GENERO_COLORES.get(genero)
        if not color_hex:
            return
        fondo = QBrush(QColor(color_hex))
        texto = QBrush(QColor("black")) if genero in GENEROS_CON_TEXTO_OSCURO else QBrush(QColor("white"))
        for columna in range(item.columnCount()):
            item.setBackground(columna, fondo)
            item.setForeground(columna, texto)

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
    # Alta de archivos: diálogo de confirmación + análisis de audio
    # ------------------------------------------------------------------
    def _agregar_archivos(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Agregar archivos de audio", os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.mp4 *.m4a)",
        )
        if not rutas:
            return

        categoria_sugerida = self._categoria_actual()
        for ruta in rutas:
            if not ruta.lower().endswith(EXTENSIONES_SOPORTADAS):
                continue
            self._dar_de_alta_archivo(ruta, categoria_sugerida)

    def _dar_de_alta_archivo(self, ruta: str, categoria_sugerida):
        dialogo = DialogoAgregarArchivo(ruta, self.tree_categorias, categoria_sugerida, parent=self)
        if dialogo.exec() != DialogoAgregarArchivo.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return

        config = cargar_configuracion()
        tolerancia = config["reproduccion"].get("tolerancia_silencio_segundos", 2.0)
        analisis = analizar_audio(ruta, tolerancia_silencio_segundos=tolerancia)

        registro = {
            "titulo": datos["titulo"],
            "artista": datos["artista"],
            "genero": datos["genero"],
            "codigo": datos["codigo"],
            "ruta": ruta,
            "punto_inicio_ms": analisis["punto_inicio_ms"],
            "punto_fin_ms": analisis["punto_fin_ms"] or None,
            "ganancia_db": analisis["ganancia_db"],
            "analizado": analisis["analizado"],
        }

        item_categoria = datos["item_categoria"]
        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        registros.append(registro)
        item_categoria.setData(0, ROL_ARCHIVOS, registros)

        if item_categoria is self._categoria_actual():
            self._agregar_fila_archivo(registro)

        self._guardar_biblioteca()
        self.archivo_agregado.emit(ruta)

    # ------------------------------------------------------------------
    # Reemplazar / Eliminar
    # ------------------------------------------------------------------
    def _reemplazar_archivo(self):
        item = self.tree_archivos.currentItem()
        categoria = self._categoria_actual()
        if item is None or categoria is None:
            QMessageBox.information(self, "Reemplazar", "Seleccioná un archivo.")
            return

        ruta_nueva, _ = QFileDialog.getOpenFileName(
            self, "Reemplazar archivo", os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.mp4 *.m4a)",
        )
        if not ruta_nueva:
            return

        registro = item.data(0, ROL_REGISTRO)
        ruta_anterior = registro.get("ruta")
        config = cargar_configuracion()
        tolerancia = config["reproduccion"].get("tolerancia_silencio_segundos", 2.0)
        analisis = analizar_audio(ruta_nueva, tolerancia_silencio_segundos=tolerancia)

        registro["ruta"] = ruta_nueva
        registro["punto_inicio_ms"] = analisis["punto_inicio_ms"]
        registro["punto_fin_ms"] = analisis["punto_fin_ms"] or None
        registro["ganancia_db"] = analisis["ganancia_db"]
        registro["analizado"] = analisis["analizado"]

        item.setData(0, Qt.ItemDataRole.UserRole, ruta_nueva)
        item.setData(0, ROL_REGISTRO, registro)
        self._sincronizar_registro_en_categoria(categoria, ruta_anterior, registro)
        self._guardar_biblioteca()

    def _eliminar_archivo(self):
        item = self.tree_archivos.currentItem()
        categoria = self._categoria_actual()
        if item is None or categoria is None:
            return

        config = cargar_configuracion()
        if config["general"]["confirmar_antes_de_eliminar"]:
            respuesta = QMessageBox.question(
                self, "Eliminar", f"¿Quitar '{item.text(0)}' de la biblioteca?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        registro = item.data(0, ROL_REGISTRO)
        ruta = registro.get("ruta") if registro else None
        indice = self.tree_archivos.indexOfTopLevelItem(item)
        self.tree_archivos.takeTopLevelItem(indice)

        if ruta:
            registros = categoria.data(0, ROL_ARCHIVOS) or []
            registros = [r for r in registros if r.get("ruta") != ruta]
            categoria.setData(0, ROL_ARCHIVOS, registros)
            self._guardar_biblioteca()
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
    # Mover un archivo de categoría arrastrándolo (columna derecha ->
    # columna izquierda), sin perder ninguna metadata (nombre editorial,
    # artista, género, código, puntos de recorte, ganancia).
    # ------------------------------------------------------------------
    def _on_archivo_soltado_en_categoria(self, ruta: str, item_categoria_destino):
        if item_categoria_destino is None:
            QMessageBox.information(self, "Mover", "Soltá el archivo sobre una categoría concreta.")
            return

        categoria_origen = self._categoria_actual()
        if categoria_origen is None or categoria_origen is item_categoria_destino:
            return  # soltado sobre la misma categoría que ya se está viendo: no hay nada que mover

        registros_origen = categoria_origen.data(0, ROL_ARCHIVOS) or []
        registro = next((r for r in registros_origen if r.get("ruta") == ruta), None)
        if registro is None:
            return  # el archivo arrastrado no pertenece a la categoría actualmente vista

        registros_origen = [r for r in registros_origen if r.get("ruta") != ruta]
        categoria_origen.setData(0, ROL_ARCHIVOS, registros_origen)

        registros_destino = item_categoria_destino.data(0, ROL_ARCHIVOS) or []
        registros_destino.append(registro)
        item_categoria_destino.setData(0, ROL_ARCHIVOS, registros_destino)

        # Refresca la lista de archivos visible (el ítem movido ya no
        # pertenece a la categoría que se está mostrando).
        self._on_categoria_seleccionada(categoria_origen, None)

        self._guardar_biblioteca()
        self.archivo_movido.emit(registro.get("titulo", ruta), item_categoria_destino.text(0))

    # ------------------------------------------------------------------
    # Menú contextual: Importar, Exportar, Reemplazar, Eliminar, Editar
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        item = self.tree_archivos.itemAt(posicion)

        menu = QMenu(self)
        accion_importar = menu.addAction("📥 Importar...")
        menu.addSeparator()
        accion_exportar = menu.addAction("📤 Exportar...")
        accion_reemplazar = menu.addAction("⟲ Reemplazar...")
        accion_editar = menu.addAction("🎚 Editar")
        menu.addSeparator()
        accion_eliminar = menu.addAction("✕ Eliminar")

        hay_seleccion = item is not None
        accion_exportar.setEnabled(hay_seleccion)
        accion_reemplazar.setEnabled(hay_seleccion)
        accion_editar.setEnabled(hay_seleccion)
        accion_eliminar.setEnabled(hay_seleccion)

        if item is not None:
            self.tree_archivos.setCurrentItem(item)

        accion_elegida = menu.exec(self.tree_archivos.viewport().mapToGlobal(posicion))
        if accion_elegida == accion_importar:
            self._agregar_archivos()
        elif accion_elegida == accion_exportar:
            self._exportar_archivo(item)
        elif accion_elegida == accion_reemplazar:
            self._reemplazar_archivo()
        elif accion_elegida == accion_editar:
            self._editar_archivo(item)
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

    def eliminar_registro_por_ruta(self, ruta: str) -> bool:
        """Borra definitivamente el registro de TODA la biblioteca
        (no solo de una lista). Usado por "Eliminar de la biblioteca"
        en el menú contextual de Ventana 2 / Auxiliar.

        IMPORTANTE: PySide6 devuelve una COPIA de los objetos Python
        guardados con setData()/data() en roles custom (no la misma
        referencia) — comparar por identidad (`is`) contra un dict
        obtenido en otra llamada nunca matchea. Por eso el filtro acá
        va por `ruta` (clave estable), no por identidad de objeto.
        """
        hallazgo = {}

        def visitar(item):
            if "categoria" in hallazgo:
                return
            registros = item.data(0, ROL_ARCHIVOS) or []
            if any(r.get("ruta") == ruta for r in registros):
                hallazgo["categoria"] = item

        self._para_cada_categoria(visitar)

        categoria = hallazgo.get("categoria")
        if categoria is None:
            return False

        registros = [r for r in (categoria.data(0, ROL_ARCHIVOS) or []) if r.get("ruta") != ruta]
        categoria.setData(0, ROL_ARCHIVOS, registros)

        if categoria is self._categoria_actual():
            self._on_categoria_seleccionada(categoria, None)

        self._guardar_biblioteca()
        self.archivo_eliminado.emit(ruta)
        return True

    # ------------------------------------------------------------------
    def guardar_disposicion(self):
        guardar_columnas("explorador_archivos", self.tree_archivos)

    def restaurar_disposicion(self):
        restaurar_columnas("explorador_archivos", self.tree_archivos)
