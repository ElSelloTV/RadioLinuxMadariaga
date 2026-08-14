"""
satelite/dialogo_musicalizador_remoto.py
--------------------------------------------------------
Musicalizador Avanzado remoto — pedido explícito: "que pueda mediante
otro botón, musicalizar, igual que en el programa principal" y, ronda
posterior, "dame todo... todo lo que tiene el principal y este no".

Mismos 3 tipos de ítem (Específico/Aleatorio/Subformato) y ahora
también Pisador (Categoría o Específico, Intro/Outro — ver
dialogo_item_musicalizador_remoto.py), columnas CLASE/TÍTULO/TIPO/
PISADOR (mismo criterio que la versión local, "para saber qué se está
musicalizando") y reordenar con ↑ Subir / ↓ Bajar.

Las columnas CLASE/TÍTULO se resuelven por RPC (`resolver_registro_por_ruta`
para un ítem Específico, `listar_registros_categoria` para calcular la
variedad de géneros de un Aleatorio) — con listas de formatos chicas
(uso manual y ocasional, nunca en el camino de reproducción real) el
costo de red por ítem es aceptable.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QMessageBox, QInputDialog,
    QAbstractItemView, QHeaderView,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_item_musicalizador_remoto import (
    DialogoItemMusicalizadorRemoto, TIPO_ESPECIFICO, TIPO_ALEATORIO, TIPO_SUBFORMATO,
)

ROL_ITEM_CONFIG = Qt.ItemDataRole.UserRole + 1


class DialogoMusicalizadorRemoto(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Musicalizador Avanzado (remoto)")
        self.resize(760, 540)
        self._cliente = cliente
        self._categorias = []
        self._formato_actual = None
        self._items_en_edicion = []
        self._construir_ui()
        self._cargar_categorias()
        self._refrescar_formatos()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QHBoxLayout(self)

        columna_formatos = QVBoxLayout()
        self.lista_formatos = QListWidget()
        self.lista_formatos.currentTextChanged.connect(self._on_formato_seleccionado)
        columna_formatos.addWidget(self.lista_formatos, 1)
        fila_botones_formato = QHBoxLayout()
        btn_nuevo = QPushButton("＋ Nuevo")
        btn_renombrar = QPushButton("✎ Renombrar")
        btn_eliminar = QPushButton("✕ Eliminar")
        btn_nuevo.clicked.connect(self._nuevo_formato)
        btn_renombrar.clicked.connect(self._renombrar_formato)
        btn_eliminar.clicked.connect(self._eliminar_formato)
        fila_botones_formato.addWidget(btn_nuevo)
        fila_botones_formato.addWidget(btn_renombrar)
        fila_botones_formato.addWidget(btn_eliminar)
        columna_formatos.addLayout(fila_botones_formato)
        layout.addLayout(columna_formatos, 1)

        columna_items = QVBoxLayout()
        self.lbl_formato_actual = QLabel("(elegí o creá un formato a la izquierda)")
        columna_items.addWidget(self.lbl_formato_actual)

        self.lista_items = QTreeWidget()
        self.lista_items.setColumnCount(4)
        self.lista_items.setHeaderLabels(["Clase", "Título", "Tipo", "Pisador"])
        self.lista_items.setRootIsDecorated(False)
        self.lista_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for columna in range(4):
            self.lista_items.header().setSectionResizeMode(columna, QHeaderView.ResizeMode.Interactive)
        self.lista_items.header().setSectionsMovable(True)
        self.lista_items.setColumnWidth(0, 100)
        self.lista_items.setColumnWidth(1, 260)
        self.lista_items.setColumnWidth(2, 90)
        self.lista_items.setColumnWidth(3, 160)
        self.lista_items.itemDoubleClicked.connect(lambda _item, _columna: self._editar_item())
        columna_items.addWidget(self.lista_items, 1)

        fila_botones_item = QHBoxLayout()
        btn_agregar_item = QPushButton("＋ Añadir...")
        btn_editar_item = QPushButton("✎ Editar")
        btn_quitar_item = QPushButton("✕ Quitar")
        btn_subir_item = QPushButton("↑ Subir")
        btn_bajar_item = QPushButton("↓ Bajar")
        btn_agregar_item.clicked.connect(self._agregar_item)
        btn_editar_item.clicked.connect(self._editar_item)
        btn_quitar_item.clicked.connect(self._quitar_item)
        btn_subir_item.clicked.connect(lambda: self._mover_item(-1))
        btn_bajar_item.clicked.connect(lambda: self._mover_item(1))
        fila_botones_item.addWidget(btn_agregar_item)
        fila_botones_item.addWidget(btn_editar_item)
        fila_botones_item.addWidget(btn_quitar_item)
        fila_botones_item.addWidget(btn_subir_item)
        fila_botones_item.addWidget(btn_bajar_item)
        columna_items.addLayout(fila_botones_item)

        self.btn_guardar = QPushButton("💾 Guardar formato")
        self.btn_guardar.clicked.connect(self._guardar_formato)
        columna_items.addWidget(self.btn_guardar)
        layout.addLayout(columna_items, 2)

    def _cargar_categorias(self):
        try:
            self._categorias = self._cliente.listar_categorias()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))

    # ------------------------------------------------------------------
    def _refrescar_formatos(self):
        seleccion_previa = self._formato_actual
        try:
            formatos = self._cliente.musicalizador_listar_formatos()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        self.lista_formatos.clear()
        self.lista_formatos.addItems(formatos)
        if seleccion_previa and seleccion_previa in formatos:
            elementos = self.lista_formatos.findItems(seleccion_previa, Qt.MatchFlag.MatchExactly)
            if elementos:
                self.lista_formatos.setCurrentItem(elementos[0])

    def _on_formato_seleccionado(self, nombre: str):
        self._formato_actual = nombre or None
        self._items_en_edicion = []
        if not nombre:
            self.lbl_formato_actual.setText("(elegí o creá un formato a la izquierda)")
            self._refrescar_lista_items()
            return
        self.lbl_formato_actual.setText(f"Formato: {nombre}")
        respuesta = self._cliente.musicalizador_obtener_formato(nombre)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo leer el formato."))
            return
        self._items_en_edicion = respuesta["datos"]["items"]
        self._refrescar_lista_items()

    def _fila_actual(self) -> int:
        return self.lista_items.indexOfTopLevelItem(self.lista_items.currentItem())

    def _refrescar_lista_items(self):
        self.lista_items.clear()
        for item_config in self._items_en_edicion:
            item_ui = QTreeWidgetItem([
                self._texto_clase(item_config), self._texto_titulo(item_config),
                self._texto_tipo(item_config), self._texto_pisador(item_config),
            ])
            item_ui.setData(0, ROL_ITEM_CONFIG, item_config)
            self.lista_items.addTopLevelItem(item_ui)

    # ------------------------------------------------------------------
    # Columnas CLASE/TÍTULO/TIPO/PISADOR — mismo criterio de la versión
    # local (gui/ventana_musicalizador.py), resolviendo la biblioteca
    # por RPC en vez de acceso directo.
    # ------------------------------------------------------------------
    @staticmethod
    def _texto_tipo(item_config: dict) -> str:
        tipo = item_config.get("tipo")
        if tipo == TIPO_ESPECIFICO:
            return "Específico"
        if tipo == TIPO_ALEATORIO:
            return "Aleatorio"
        return "—"

    def _texto_titulo(self, item_config: dict) -> str:
        tipo = item_config.get("tipo")
        if tipo == TIPO_ESPECIFICO:
            ruta = item_config.get("ruta") or ""
            try:
                registro = self._cliente.resolver_registro_por_ruta(ruta) if ruta else None
            except ErrorControlRemoto:
                registro = None
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

    def _texto_clase(self, item_config: dict) -> str:
        tipo = item_config.get("tipo")
        if tipo == TIPO_SUBFORMATO:
            return "Subformato"
        if tipo == TIPO_ESPECIFICO:
            ruta = item_config.get("ruta") or ""
            try:
                registro = self._cliente.resolver_registro_por_ruta(ruta) if ruta else None
            except ErrorControlRemoto:
                registro = None
            return (registro or {}).get("genero") or "(desconocida)"
        if tipo == TIPO_ALEATORIO:
            categoria = item_config.get("categoria") or []
            try:
                registros = self._cliente.listar_registros_categoria(categoria, item_config.get("recursivo", True))
            except ErrorControlRemoto:
                return "(categoría rota)"
            generos = {r.get("genero") for r in registros if r.get("genero")}
            if not generos:
                return "(sin archivos)"
            if len(generos) == 1:
                return next(iter(generos))
            return "(variado)"
        return "—"

    @staticmethod
    def _texto_pisador(item_config: dict) -> str:
        tiene_categoria = bool(item_config.get("pisador_categoria"))
        tiene_especifico = item_config.get("pisador_tipo") == "especifico" and item_config.get("pisador_ruta")
        if not tiene_categoria and not tiene_especifico:
            return ""
        posicion = "Outro" if item_config.get("pisador_posicion") == "final" else "Intro"
        if tiene_especifico:
            return f"{posicion}: {item_config.get('pisador_ruta')}"
        return f"{posicion}: {' > '.join(item_config['pisador_categoria'])}"

    # ------------------------------------------------------------------
    # Formatos: Nuevo / Renombrar / Eliminar
    # ------------------------------------------------------------------
    def _nuevo_formato(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo formato", "Nombre:")
        nombre = (nombre or "").strip()
        if not ok or not nombre:
            return
        respuesta = self._cliente.musicalizador_nuevo_formato(nombre)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo crear."))
            return
        self._formato_actual = nombre
        self._refrescar_formatos()

    def _renombrar_formato(self):
        if not self._formato_actual:
            return
        nombre_nuevo, ok = QInputDialog.getText(self, "Renombrar formato", "Nombre nuevo:", text=self._formato_actual)
        nombre_nuevo = (nombre_nuevo or "").strip()
        if not ok or not nombre_nuevo or nombre_nuevo == self._formato_actual:
            return
        respuesta = self._cliente.musicalizador_renombrar_formato(self._formato_actual, nombre_nuevo)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo renombrar."))
            return
        self._formato_actual = nombre_nuevo
        self._refrescar_formatos()

    def _eliminar_formato(self):
        if not self._formato_actual:
            return
        respuesta_confirm = QMessageBox.question(
            self, "Eliminar formato", f"¿Eliminar el formato \"{self._formato_actual}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta_confirm != QMessageBox.StandardButton.Yes:
            return
        self._cliente.musicalizador_eliminar_formato(self._formato_actual)
        self._formato_actual = None
        self._refrescar_formatos()

    # ------------------------------------------------------------------
    # Ítems: Añadir / Editar / Quitar / Subir / Bajar
    # ------------------------------------------------------------------
    def _agregar_item(self):
        if not self._formato_actual:
            QMessageBox.information(self, "Añadir ítem", "Elegí o creá un formato primero.")
            return
        otros_formatos = [
            self.lista_formatos.item(i).text() for i in range(self.lista_formatos.count())
            if self.lista_formatos.item(i).text() != self._formato_actual
        ]
        dialogo = DialogoItemMusicalizadorRemoto(self._cliente, self._categorias, otros_formatos, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        item = dialogo.resultado()
        if not item:
            return
        # Pedido explícito ("2 o 3 o 4 o 5"): agregar varios ítems
        # Aleatorio de una — cada copia es un dict independiente.
        cantidad = dialogo.resultado_cantidad()
        for _ in range(cantidad):
            self._items_en_edicion.append(dict(item))
        self._refrescar_lista_items()

    def _editar_item(self):
        fila = self._fila_actual()
        if fila < 0:
            return
        dialogo = DialogoItemMusicalizadorRemoto(
            self._cliente, self._categorias,
            [self.lista_formatos.item(i).text() for i in range(self.lista_formatos.count())
             if self.lista_formatos.item(i).text() != self._formato_actual],
            item_config=self._items_en_edicion[fila], parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
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
    def _guardar_formato(self):
        if not self._formato_actual:
            QMessageBox.information(self, "Guardar", "Elegí o creá un formato primero.")
            return
        respuesta = self._cliente.musicalizador_guardar_formato(self._formato_actual, self._items_en_edicion)
        if respuesta.get("ok"):
            QMessageBox.information(self, "Guardar", f"Formato \"{self._formato_actual}\" guardado.")
            return
        if respuesta.get("requiere_confirmacion"):
            avisos = "\n".join(respuesta.get("avisos") or [])
            respuesta_confirm = QMessageBox.question(
                self, "Guardar con avisos",
                "Se encontraron estas situaciones (no impiden guardar):\n\n" + avisos + "\n\n¿Guardar igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta_confirm != QMessageBox.StandardButton.Yes:
                return
            respuesta = self._cliente.musicalizador_guardar_formato(self._formato_actual, self._items_en_edicion, forzar=True)
            if respuesta.get("ok"):
                QMessageBox.information(self, "Guardar", f"Formato \"{self._formato_actual}\" guardado.")
                return
        QMessageBox.warning(self, "No se puede guardar", respuesta.get("error", "Falló el guardado."))
