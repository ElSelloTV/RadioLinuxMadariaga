"""
satelite/dialogo_musicalizador_remoto.py
--------------------------------------------------------
Musicalizador Avanzado remoto — pedido explícito: "que pueda mediante
otro botón, musicalizar, igual que en el programa principal". MVP
deliberado (mismo criterio que el Programador remoto, ver
dialogo_programador_remoto.py): crear/editar/guardar formatos con
ítems Específico/Aleatorio/Subformato, sin Pisador (queda para una
ronda futura si hace falta).
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QInputDialog,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_item_musicalizador_remoto import DialogoItemMusicalizadorRemoto


class DialogoMusicalizadorRemoto(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Musicalizador Avanzado (remoto)")
        self.resize(560, 520)
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
        btn_renombrar = QPushButton("✏ Renombrar")
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
        self.lista_items = QListWidget()
        columna_items.addWidget(self.lista_items, 1)
        fila_botones_item = QHBoxLayout()
        btn_agregar_item = QPushButton("➕ Añadir ítem...")
        btn_quitar_item = QPushButton("✕ Quitar ítem")
        btn_agregar_item.clicked.connect(self._agregar_item)
        btn_quitar_item.clicked.connect(self._quitar_item)
        fila_botones_item.addWidget(btn_agregar_item)
        fila_botones_item.addWidget(btn_quitar_item)
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
        self.lista_items.clear()
        if not nombre:
            return
        respuesta = self._cliente.musicalizador_obtener_formato(nombre)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo leer el formato."))
            return
        self._items_en_edicion = respuesta["datos"]["items"]
        self._refrescar_lista_items()

    def _refrescar_lista_items(self):
        self.lista_items.clear()
        for item in self._items_en_edicion:
            self.lista_items.addItem(QListWidgetItem(self._texto_item(item)))

    @staticmethod
    def _texto_item(item: dict) -> str:
        tipo = item.get("tipo")
        if tipo == "especifico":
            return f"🎯 Específico: {item.get('ruta', '')}"
        if tipo == "aleatorio":
            categoria = " / ".join(item.get("categoria") or [])
            recursivo = " (con subcategorías)" if item.get("recursivo") else ""
            return f"🎲 Aleatorio: {categoria}{recursivo}"
        if tipo == "subformato":
            minutos = (item.get("duracion_segundos") or 0) // 60
            return f"🔁 Subformato: {item.get('nombre')} — {minutos} min"
        return "(ítem desconocido)"

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
        self._items_en_edicion.append(item)
        self._refrescar_lista_items()

    def _quitar_item(self):
        fila = self.lista_items.currentRow()
        if fila < 0:
            return
        del self._items_en_edicion[fila]
        self._refrescar_lista_items()

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
