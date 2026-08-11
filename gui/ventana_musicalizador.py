"""
gui/ventana_musicalizador.py
--------------------------------------------------------
Musicalizador Avanzado (pedido explícito, inspirado en Hardata
Dinesat 9 — "uno de los últimos 2 [temas] que más uso, encadenado con
Comandos FMT"). Ventana con DOS listas, mismo espíritu que el
Programador:

- Izquierda: los FORMATOS ya creados (Nuevo / Eliminar / Renombrar).
- Derecha: los ÍTEMS del formato seleccionado (Añadir / Editar /
  Quitar / Subir / Bajar — pedido explícito, puntos 2 y 3), cada uno
  "Específico", "Aleatorio" o "Subformato" (ver
  gui/dialogo_item_musicalizador.py y core/musicalizador.py).

"Guardar" valida el formato (core.musicalizador.validar_formato,
pedido explícito punto 5) antes de persistir: un bucle de subformatos
BLOQUEA el guardado; referencias rotas o categorías vacías solo
avisan, nunca bloquean.

La lista de ítems es una tabla de 4 columnas (pedido explícito, ronda
posterior: "para saber cómo y qué voy programando, que yo sepa que voy
musicalizando") — CLASE / TÍTULO / TIPO / PISADOR, ver
`_texto_clase`/`_texto_titulo`/`_texto_tipo`/`_texto_pisador` más
abajo. La columna TÍTULO reemplazó a la vieja "Detalle" (pedido
explícito, ronda posterior: "para armar mejor, poné el nombre del
título... sacá la columna de detalle") — para un ítem Específico
mostraba la RUTA cruda del archivo, dificultando reconocer de un
vistazo qué tema es; ahora muestra el título REAL, resuelto contra la
biblioteca. Las 4 columnas son movibles y ajustables a mano (pedido
explícito, "que puedan ajustarse manualmente" — para poder agrandar
Título y ver el nombre completo).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QInputDialog, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import Qt

from gui.dialogo_item_musicalizador import DialogoItemMusicalizador, TIPO_ESPECIFICO, TIPO_ALEATORIO, TIPO_SUBFORMATO
from config.settings import (
    listar_formatos, obtener_formato, guardar_formato, eliminar_formato, renombrar_formato,
    cargar_musicalizador,
)
from core.musicalizador import validar_formato

ROL_ITEM_CONFIG = Qt.ItemDataRole.UserRole + 1


def _texto_tipo(item_config: dict) -> str:
    tipo = item_config.get("tipo")
    if tipo == TIPO_ESPECIFICO:
        return "Específico"
    if tipo == TIPO_ALEATORIO:
        return "Aleatorio"
    return "—"  # Subformato: pedido explícito, "no aplica"


def _texto_titulo(ventana_explorador, item_config: dict) -> str:
    """Columna "Título" (reemplaza a la vieja "Detalle" — pedido
    explícito, "para armar mejor, poné el nombre del título"): para un
    ítem Específico, el TÍTULO REAL del archivo (resuelto contra la
    biblioteca, no la ruta cruda — es la mejora concreta que pidió
    Santiago, poder reconocer el tema de un vistazo); para Aleatorio,
    sin un archivo puntual, el camino de categoría (misma info que
    antes vivía en "Detalle" para este caso); para Subformato, su
    nombre + duración configurada (tampoco tiene un "título" propio,
    es un contenedor)."""
    tipo = item_config.get("tipo")
    if tipo == TIPO_ESPECIFICO:
        ruta = item_config.get("ruta") or ""
        if ventana_explorador is None:
            return ruta or "(sin archivo)"
        registro = ventana_explorador.buscar_registro_por_ruta(ruta)
        if registro is None:
            return f"(no encontrado: {ruta})" if ruta else "(sin archivo)"
        return registro.get("titulo") or "(sin título)"
    if tipo == TIPO_ALEATORIO:
        ruta = " > ".join(item_config.get("categoria") or []) or "(sin categoría)"
        return ruta if item_config.get("recursivo", True) else f"{ruta} (sin subcategorías)"
    if tipo == TIPO_SUBFORMATO:
        minutos = int((item_config.get("duracion_segundos") or 0) / 60)
        nombre = item_config.get("nombre") or "(sin formato)"
        return f"{nombre} — {minutos} min"
    return "—"


def _texto_clase(ventana_explorador, item_config: dict) -> str:
    """Pedido explícito: "columna CLASE: Música, Separador, Pisador,
    Subformato... etc." — el género real del archivo para un ítem
    Específico; el género de los archivos de la categoría para un
    Aleatorio (si son todos el mismo; "(variado)" si no); "Subformato"
    literal para ese tipo (es un contenedor, no tiene género propio)."""
    tipo = item_config.get("tipo")
    if tipo == TIPO_SUBFORMATO:
        return "Subformato"
    if ventana_explorador is None:
        return "(desconocida)"
    if tipo == TIPO_ESPECIFICO:
        registro = ventana_explorador.buscar_registro_por_ruta(item_config.get("ruta", ""))
        return (registro or {}).get("genero") or "(desconocida)"
    if tipo == TIPO_ALEATORIO:
        categoria = ventana_explorador.buscar_categoria_por_ruta(item_config.get("categoria") or [])
        if categoria is None:
            return "(categoría rota)"
        registros = ventana_explorador.listar_registros_de_categoria(categoria, item_config.get("recursivo", True))
        generos = {r.get("genero") for r in registros if r.get("genero")}
        if not generos:
            return "(sin archivos)"
        if len(generos) == 1:
            return next(iter(generos))
        return "(variado)"
    return "—"


def _texto_pisador(item_config: dict) -> str:
    tiene_categoria = bool(item_config.get("pisador_categoria"))
    tiene_especifico = item_config.get("pisador_tipo") == "especifico" and item_config.get("pisador_ruta")
    if not tiene_categoria and not tiene_especifico:
        return ""
    posicion = "Outro" if item_config.get("pisador_posicion") == "final" else "Intro"
    if tiene_especifico:
        return f"{posicion}: {item_config.get('pisador_ruta')}"
    return f"{posicion}: {' > '.join(item_config['pisador_categoria'])}"


class VentanaMusicalizador(QDialog):
    def __init__(self, ventana_explorador=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Musicalizador Avanzado")
        self.setMinimumSize(760, 480)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint
        )
        self._ventana_explorador = ventana_explorador
        self._formato_actual = None  # nombre (str) del formato seleccionado
        self._items_en_edicion = []  # lista de dicts, se guarda recién al presionar "Guardar"
        self._construir_ui()
        self._recargar_formatos()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout_principal = QHBoxLayout(self)

        # --- Columna izquierda: formatos ---
        grupo_formatos = QGroupBox("Formatos")
        layout_formatos = QVBoxLayout(grupo_formatos)
        self.lista_formatos = QListWidget()
        self.lista_formatos.currentTextChanged.connect(self._on_formato_seleccionado)
        layout_formatos.addWidget(self.lista_formatos)

        fila_botones_formato = QHBoxLayout()
        btn_nuevo_formato = QPushButton("＋ Nuevo")
        btn_nuevo_formato.clicked.connect(self._nuevo_formato)
        btn_renombrar_formato = QPushButton("✎ Renombrar")
        btn_renombrar_formato.clicked.connect(self._renombrar_formato)
        btn_eliminar_formato = QPushButton("✕ Eliminar")
        btn_eliminar_formato.clicked.connect(self._eliminar_formato)
        fila_botones_formato.addWidget(btn_nuevo_formato)
        fila_botones_formato.addWidget(btn_renombrar_formato)
        fila_botones_formato.addWidget(btn_eliminar_formato)
        layout_formatos.addLayout(fila_botones_formato)

        layout_principal.addWidget(grupo_formatos, stretch=1)

        # --- Columna derecha: ítems del formato seleccionado ---
        grupo_items = QGroupBox("Ítems del formato")
        layout_items = QVBoxLayout(grupo_items)

        self.lbl_formato_actual = QLabel("(elegí o creá un formato a la izquierda)")
        self.lbl_formato_actual.setObjectName("lblTituloBloqueActivo")
        layout_items.addWidget(self.lbl_formato_actual)

        self.lista_items = QTreeWidget()
        self.lista_items.setColumnCount(4)
        self.lista_items.setHeaderLabels(["Clase", "Título", "Tipo", "Pisador"])
        self.lista_items.setRootIsDecorated(False)
        self.lista_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Pedido explícito ("que esas columnas puedan moverse... que
        # puedan ajustarse manualmente"): las 4 quedan en modo
        # Interactive (nunca Stretch fijo) para poder agrandar/achicar
        # cualquiera a mano, y el header admite arrastrar para
        # reordenarlas — sobre todo pensado para poder ensanchar
        # "Título" y leer el nombre completo sin que quede truncado.
        for columna in range(4):
            self.lista_items.header().setSectionResizeMode(columna, QHeaderView.ResizeMode.Interactive)
        self.lista_items.header().setSectionsMovable(True)
        self.lista_items.setColumnWidth(0, 100)
        self.lista_items.setColumnWidth(1, 260)
        self.lista_items.setColumnWidth(2, 90)
        self.lista_items.setColumnWidth(3, 160)
        self.lista_items.itemDoubleClicked.connect(lambda _item, _columna: self._editar_item())
        layout_items.addWidget(self.lista_items)

        fila_botones_item = QHBoxLayout()
        btn_añadir_item = QPushButton("＋ Añadir")
        btn_añadir_item.clicked.connect(self._añadir_item)
        btn_editar_item = QPushButton("✎ Editar")
        btn_editar_item.clicked.connect(self._editar_item)
        btn_quitar_item = QPushButton("✕ Quitar")
        btn_quitar_item.clicked.connect(self._quitar_item)
        btn_subir_item = QPushButton("↑ Subir")
        btn_subir_item.clicked.connect(lambda: self._mover_item(-1))
        btn_bajar_item = QPushButton("↓ Bajar")
        btn_bajar_item.clicked.connect(lambda: self._mover_item(1))
        fila_botones_item.addWidget(btn_añadir_item)
        fila_botones_item.addWidget(btn_editar_item)
        fila_botones_item.addWidget(btn_quitar_item)
        fila_botones_item.addWidget(btn_subir_item)
        fila_botones_item.addWidget(btn_bajar_item)
        layout_items.addLayout(fila_botones_item)

        self.btn_guardar = QPushButton("💾 Guardar formato")
        self.btn_guardar.clicked.connect(self._guardar_formato_actual)
        layout_items.addWidget(self.btn_guardar)

        layout_principal.addWidget(grupo_items, stretch=2)

        self._actualizar_habilitacion()

    # ------------------------------------------------------------------
    def _recargar_formatos(self, seleccionar: str = None):
        self.lista_formatos.blockSignals(True)
        self.lista_formatos.clear()
        for nombre in listar_formatos():
            self.lista_formatos.addItem(nombre)
        self.lista_formatos.blockSignals(False)
        if seleccionar:
            coincidencias = self.lista_formatos.findItems(seleccionar, Qt.MatchFlag.MatchExactly)
            if coincidencias:
                self.lista_formatos.setCurrentItem(coincidencias[0])
                return
        self._on_formato_seleccionado(self.lista_formatos.currentItem().text() if self.lista_formatos.currentItem() else None)

    def _on_formato_seleccionado(self, nombre: str | None):
        self._formato_actual = nombre or None
        self._items_en_edicion = []
        if nombre:
            formato = obtener_formato(nombre) or {}
            self._items_en_edicion = list(formato.get("items", []))
            self.lbl_formato_actual.setText(f"Formato: {nombre}")
        else:
            self.lbl_formato_actual.setText("(elegí o creá un formato a la izquierda)")
        self._refrescar_lista_items()
        self._actualizar_habilitacion()

    def _actualizar_habilitacion(self):
        habilitado = self._formato_actual is not None
        self.lista_items.setEnabled(habilitado)
        self.btn_guardar.setEnabled(habilitado)

    def _refrescar_lista_items(self):
        self.lista_items.clear()
        for item_config in self._items_en_edicion:
            item_ui = QTreeWidgetItem([
                _texto_clase(self._ventana_explorador, item_config),
                _texto_titulo(self._ventana_explorador, item_config),
                _texto_tipo(item_config),
                _texto_pisador(item_config),
            ])
            item_ui.setData(0, ROL_ITEM_CONFIG, item_config)
            self.lista_items.addTopLevelItem(item_ui)

    def _fila_actual(self) -> int:
        return self.lista_items.indexOfTopLevelItem(self.lista_items.currentItem())

    # ------------------------------------------------------------------
    # Formatos: Nuevo / Renombrar / Eliminar
    # ------------------------------------------------------------------
    def _nuevo_formato(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo formato", "Nombre del formato (ej. \"Folclore\"):")
        nombre = (nombre or "").strip()
        if not ok or not nombre:
            return
        if nombre in listar_formatos():
            QMessageBox.information(self, "Nuevo formato", f"Ya existe un formato llamado '{nombre}'.")
            return
        guardar_formato(nombre, [])
        self._recargar_formatos(seleccionar=nombre)

    def _renombrar_formato(self):
        if not self._formato_actual:
            return
        nombre_nuevo, ok = QInputDialog.getText(
            self, "Renombrar formato", "Nuevo nombre:", text=self._formato_actual,
        )
        nombre_nuevo = (nombre_nuevo or "").strip()
        if not ok or not nombre_nuevo or nombre_nuevo == self._formato_actual:
            return
        if not renombrar_formato(self._formato_actual, nombre_nuevo):
            QMessageBox.information(self, "Renombrar", f"Ya existe un formato llamado '{nombre_nuevo}'.")
            return
        self._recargar_formatos(seleccionar=nombre_nuevo)

    def _eliminar_formato(self):
        if not self._formato_actual:
            return
        respuesta = QMessageBox.question(
            self, "Eliminar formato",
            f"¿Eliminar el formato '{self._formato_actual}'?\n\n"
            "Si algún Comando FMT o subformato lo estaba usando, quedará\n"
            "roto (se avisa, pero no se corrige solo).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        eliminar_formato(self._formato_actual)
        self._recargar_formatos()

    # ------------------------------------------------------------------
    # Ítems: Añadir / Editar / Quitar / Subir / Bajar
    # ------------------------------------------------------------------
    def _añadir_item(self):
        if not self._formato_actual or self._ventana_explorador is None:
            return
        dialogo = DialogoItemMusicalizador(
            self._ventana_explorador, listar_formatos(), self._formato_actual, parent=self,
        )
        if dialogo.exec() != DialogoItemMusicalizador.DialogCode.Accepted:
            return
        item = dialogo.resultado()
        if item:
            # Pedido explícito: agregar varios ítems Aleatorio de una
            # (2, 3, 4, 5...) — cada copia es un dict independiente
            # (misma categoría), la serie los resuelve a archivos
            # distintos entre sí (rutas_a_evitar, ya existente).
            cantidad = dialogo.resultado_cantidad()
            for _ in range(cantidad):
                self._items_en_edicion.append(dict(item))
            self._refrescar_lista_items()

    def _editar_item(self):
        fila = self._fila_actual()
        if fila < 0 or self._ventana_explorador is None:
            return
        dialogo = DialogoItemMusicalizador(
            self._ventana_explorador, listar_formatos(), self._formato_actual,
            item_config=self._items_en_edicion[fila], parent=self,
        )
        if dialogo.exec() != DialogoItemMusicalizador.DialogCode.Accepted:
            return
        item = dialogo.resultado()
        if item:
            self._items_en_edicion[fila] = item
            self._refrescar_lista_items()
            self.lista_items.setCurrentItem(self.lista_items.topLevelItem(fila))

    def _quitar_item(self):
        fila = self._fila_actual()
        if fila < 0:
            return
        del self._items_en_edicion[fila]
        self._refrescar_lista_items()

    def _mover_item(self, delta: int):
        fila = self._fila_actual()
        nueva_fila = fila + delta
        if fila < 0 or not (0 <= nueva_fila < len(self._items_en_edicion)):
            return
        self._items_en_edicion[fila], self._items_en_edicion[nueva_fila] = \
            self._items_en_edicion[nueva_fila], self._items_en_edicion[fila]
        self._refrescar_lista_items()
        self.lista_items.setCurrentItem(self.lista_items.topLevelItem(nueva_fila))

    # ------------------------------------------------------------------
    def _guardar_formato_actual(self):
        if not self._formato_actual or self._ventana_explorador is None:
            return
        todos_los_formatos = cargar_musicalizador()["formatos"]
        problemas = validar_formato(
            self._ventana_explorador, self._formato_actual, self._items_en_edicion, todos_los_formatos,
        )
        bloqueantes = [p for p in problemas if p["bloquea"]]
        if bloqueantes:
            QMessageBox.warning(
                self, "No se puede guardar",
                "Este formato tiene problemas que impiden guardarlo:\n\n"
                + "\n".join(p["mensaje"] for p in bloqueantes),
            )
            return

        avisos = [p for p in problemas if not p["bloquea"]]
        if avisos:
            respuesta = QMessageBox.question(
                self, "Guardar con avisos",
                "Se encontraron estas situaciones (no impiden guardar ni afectan\n"
                "a los demás ítems del formato):\n\n"
                + "\n".join(p["mensaje"] for p in avisos)
                + "\n\n¿Guardar igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        guardar_formato(self._formato_actual, self._items_en_edicion)
        QMessageBox.information(self, "Guardar", f"Formato '{self._formato_actual}' guardado.")
