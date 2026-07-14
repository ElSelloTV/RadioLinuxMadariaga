"""
gui/dialogo_item_musicalizador.py
--------------------------------------------------------
Alta/edición de UN ítem de un formato del Musicalizador Avanzado
(pedido explícito, punto 1): "Específico", "Aleatorio" (siempre elige
UN tema al azar de una categoría) o "Subformato" (otro formato ya
creado, por X cantidad de tiempo) — mismos 3 tipos que describe el
manual de Dinesat.

El ítem "Aleatorio" (y también "Específico", pedido explícito punto
4) puede llevar un Pisador — se elige una CATEGORÍA de Pisadores
(no un archivo puntual: a cada generación real se elige uno al azar
de esa categoría, ver core/musicalizador.py) y si se dispara al
empezar o al terminar el tema (mismo concepto ya usado en Ventana 2).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QLineEdit, QLabel,
    QCheckBox, QSpinBox, QRadioButton, QButtonGroup, QPushButton, QStackedWidget,
    QWidget, QDialogButtonBox, QMessageBox
)

from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
from gui.dialogo_seleccionar_categoria import DialogoSeleccionarCategoria

TIPO_ESPECIFICO, TIPO_ALEATORIO, TIPO_SUBFORMATO = "especifico", "aleatorio", "subformato"


class DialogoItemMusicalizador(QDialog):
    def __init__(self, ventana_explorador, formatos_disponibles: list, nombre_formato_actual: str,
                 item_config: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ítem del formato" if item_config is None else "Editar ítem")
        self.setMinimumWidth(460)
        self._ventana_explorador = ventana_explorador
        # el propio formato no puede ser subformato de sí mismo directo
        # (los ciclos indirectos los atrapa validar_formato al guardar)
        self._formatos_disponibles = [f for f in formatos_disponibles if f != nombre_formato_actual]
        self._registro_especifico = None
        self._ruta_categoria_aleatorio = None
        self._ruta_categoria_pisador = None
        self._resultado = None

        self._construir_ui()
        if item_config:
            self._cargar(item_config)

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        fila_tipo = QHBoxLayout()
        fila_tipo.addWidget(QLabel("Tipo de ítem:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("🎯 Específico (un archivo fijo)", TIPO_ESPECIFICO)
        self.combo_tipo.addItem("🎲 Aleatorio (1 tema al azar de una categoría)", TIPO_ALEATORIO)
        self.combo_tipo.addItem("🔁 Subformato (otro formato, por tiempo)", TIPO_SUBFORMATO)
        self.combo_tipo.currentIndexChanged.connect(self._actualizar_pila)
        fila_tipo.addWidget(self.combo_tipo)
        layout.addLayout(fila_tipo)

        self.pila = QStackedWidget()
        layout.addWidget(self.pila)

        # --- Específico ---
        pagina_especifico = QWidget()
        form_especifico = QFormLayout(pagina_especifico)
        self.lbl_archivo_especifico = QLabel("(sin elegir)")
        self.lbl_archivo_especifico.setWordWrap(True)
        btn_elegir_archivo = QPushButton("Elegir archivo...")
        btn_elegir_archivo.clicked.connect(self._elegir_archivo_especifico)
        form_especifico.addRow(self.lbl_archivo_especifico)
        form_especifico.addRow(btn_elegir_archivo)
        self.pila.addWidget(pagina_especifico)

        # --- Aleatorio ---
        pagina_aleatorio = QWidget()
        form_aleatorio = QFormLayout(pagina_aleatorio)
        self.lbl_categoria_aleatorio = QLabel("(sin elegir)")
        self.lbl_categoria_aleatorio.setWordWrap(True)
        btn_elegir_categoria = QPushButton("Elegir categoría...")
        btn_elegir_categoria.clicked.connect(self._elegir_categoria_aleatorio)
        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        self.chk_recursivo.setChecked(True)
        form_aleatorio.addRow(self.lbl_categoria_aleatorio)
        form_aleatorio.addRow(btn_elegir_categoria)
        form_aleatorio.addRow(self.chk_recursivo)
        self.pila.addWidget(pagina_aleatorio)

        # --- Subformato ---
        pagina_subformato = QWidget()
        form_subformato = QFormLayout(pagina_subformato)
        self.combo_subformato = QComboBox()
        self.combo_subformato.addItems(self._formatos_disponibles)
        self.spin_duracion_minutos = QSpinBox()
        self.spin_duracion_minutos.setRange(1, 600)
        self.spin_duracion_minutos.setValue(10)
        self.spin_duracion_minutos.setSuffix(" min")
        form_subformato.addRow("Formato:", self.combo_subformato)
        form_subformato.addRow("Duración:", self.spin_duracion_minutos)
        if not self._formatos_disponibles:
            form_subformato.addRow(QLabel("No hay otros formatos creados todavía."))
        self.pila.addWidget(pagina_subformato)

        # --- Pisador (Específico y Aleatorio, pedido explícito punto 4) ---
        self.grupo_pisador = QWidget()
        form_pisador = QFormLayout(self.grupo_pisador)
        self.chk_pisador = QCheckBox("Agregar Pisador")
        self.chk_pisador.toggled.connect(self._on_toggle_pisador)
        form_pisador.addRow(self.chk_pisador)
        self.lbl_categoria_pisador = QLabel("(sin elegir)")
        self.lbl_categoria_pisador.setWordWrap(True)
        self.btn_elegir_pisador = QPushButton("Elegir categoría de Pisadores...")
        self.btn_elegir_pisador.clicked.connect(self._elegir_categoria_pisador)
        self.btn_elegir_pisador.setEnabled(False)
        form_pisador.addRow(self.lbl_categoria_pisador)
        form_pisador.addRow(self.btn_elegir_pisador)
        self.radio_pisador_inicio = QRadioButton("Al empezar el tema (Intro)")
        self.radio_pisador_final = QRadioButton("Al terminar el tema (Outro)")
        self.radio_pisador_inicio.setChecked(True)
        self.radio_pisador_inicio.setEnabled(False)
        self.radio_pisador_final.setEnabled(False)
        grupo_radio = QButtonGroup(self)
        grupo_radio.addButton(self.radio_pisador_inicio)
        grupo_radio.addButton(self.radio_pisador_final)
        form_pisador.addRow(self.radio_pisador_inicio)
        form_pisador.addRow(self.radio_pisador_final)
        layout.addWidget(self.grupo_pisador)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._actualizar_pila()

    # ------------------------------------------------------------------
    def _actualizar_pila(self):
        tipo = self.combo_tipo.currentData()
        indice = {TIPO_ESPECIFICO: 0, TIPO_ALEATORIO: 1, TIPO_SUBFORMATO: 2}[tipo]
        self.pila.setCurrentIndex(indice)
        # El Pisador no aplica a un subformato (es un contenedor, no un tema puntual)
        self.grupo_pisador.setVisible(tipo != TIPO_SUBFORMATO)

    def _on_toggle_pisador(self, activo: bool):
        self.btn_elegir_pisador.setEnabled(activo)
        self.radio_pisador_inicio.setEnabled(activo)
        self.radio_pisador_final.setEnabled(activo)

    def _elegir_archivo_especifico(self):
        dialogo = DialogoSeleccionarBiblioteca(
            self._ventana_explorador.tree_categorias, permitir_multiple=False,
            titulo="Elegir archivo específico", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarBiblioteca.DialogCode.Accepted:
            return
        registro = dialogo.registro_elegido()
        if registro:
            self._registro_especifico = registro
            self.lbl_archivo_especifico.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")

    def _elegir_categoria_aleatorio(self):
        dialogo = DialogoSeleccionarCategoria(
            self._ventana_explorador.tree_categorias, titulo="Elegir categoría", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarCategoria.DialogCode.Accepted:
            return
        ruta = dialogo.ruta_elegida()
        if ruta:
            self._ruta_categoria_aleatorio = ruta
            self.lbl_categoria_aleatorio.setText(" > ".join(ruta))

    def _elegir_categoria_pisador(self):
        dialogo = DialogoSeleccionarCategoria(
            self._ventana_explorador.tree_categorias, titulo="Elegir categoría de Pisadores", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarCategoria.DialogCode.Accepted:
            return
        ruta = dialogo.ruta_elegida()
        if ruta:
            self._ruta_categoria_pisador = ruta
            self.lbl_categoria_pisador.setText(" > ".join(ruta))

    # ------------------------------------------------------------------
    def _cargar(self, item_config: dict):
        tipo = item_config.get("tipo", TIPO_ESPECIFICO)
        indice_combo = {TIPO_ESPECIFICO: 0, TIPO_ALEATORIO: 1, TIPO_SUBFORMATO: 2}.get(tipo, 0)
        self.combo_tipo.setCurrentIndex(indice_combo)

        if tipo == TIPO_ESPECIFICO:
            registro = self._ventana_explorador.buscar_registro_por_ruta(item_config.get("ruta", ""))
            if registro:
                self._registro_especifico = registro
                self.lbl_archivo_especifico.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")
            else:
                self.lbl_archivo_especifico.setText("(el archivo original ya no existe)")
        elif tipo == TIPO_ALEATORIO:
            ruta = item_config.get("categoria") or []
            if ruta:
                self._ruta_categoria_aleatorio = ruta
                self.lbl_categoria_aleatorio.setText(" > ".join(ruta))
            self.chk_recursivo.setChecked(item_config.get("recursivo", True))
        elif tipo == TIPO_SUBFORMATO:
            nombre_sub = item_config.get("nombre", "")
            indice_sub = self.combo_subformato.findText(nombre_sub)
            if indice_sub >= 0:
                self.combo_subformato.setCurrentIndex(indice_sub)
            self.spin_duracion_minutos.setValue(max(1, int((item_config.get("duracion_segundos") or 600) / 60)))

        ruta_pisador = item_config.get("pisador_categoria")
        if ruta_pisador:
            self.chk_pisador.setChecked(True)
            self._ruta_categoria_pisador = ruta_pisador
            self.lbl_categoria_pisador.setText(" > ".join(ruta_pisador))
            if item_config.get("pisador_posicion") == "final":
                self.radio_pisador_final.setChecked(True)
            else:
                self.radio_pisador_inicio.setChecked(True)

    # ------------------------------------------------------------------
    def _confirmar(self):
        tipo = self.combo_tipo.currentData()

        if tipo == TIPO_ESPECIFICO:
            if not self._registro_especifico:
                QMessageBox.information(self, "Ítem", "Elegí un archivo para el ítem específico.")
                return
            item = {"tipo": TIPO_ESPECIFICO, "ruta": self._registro_especifico.get("ruta", "")}
        elif tipo == TIPO_ALEATORIO:
            if not self._ruta_categoria_aleatorio:
                QMessageBox.information(self, "Ítem", "Elegí una categoría para el ítem aleatorio.")
                return
            item = {
                "tipo": TIPO_ALEATORIO, "categoria": self._ruta_categoria_aleatorio,
                "recursivo": self.chk_recursivo.isChecked(),
            }
        else:  # TIPO_SUBFORMATO
            if not self._formatos_disponibles:
                QMessageBox.information(self, "Ítem", "Todavía no hay otro formato creado para usar como subformato.")
                return
            item = {
                "tipo": TIPO_SUBFORMATO, "nombre": self.combo_subformato.currentText(),
                "duracion_segundos": self.spin_duracion_minutos.value() * 60,
            }

        if tipo != TIPO_SUBFORMATO and self.chk_pisador.isChecked():
            if not self._ruta_categoria_pisador:
                QMessageBox.information(self, "Ítem", "Elegí una categoría de Pisadores, o desmarcá \"Agregar Pisador\".")
                return
            item["pisador_categoria"] = self._ruta_categoria_pisador
            item["pisador_posicion"] = "final" if self.radio_pisador_final.isChecked() else "inicio"

        self._resultado = item
        self.accept()

    def resultado(self) -> dict | None:
        return self._resultado
