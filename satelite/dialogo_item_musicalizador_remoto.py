"""
satelite/dialogo_item_musicalizador_remoto.py
--------------------------------------------------------
Arma/edita UN ítem de un formato del Musicalizador remoto — 3 tipos,
mismo motor puro (`core/musicalizador.py`) que ya usa la app
principal. Pedido explícito ("dame todo... todo lo que tiene el
principal y este no"): ahora con Pisador (Categoría o Archivo
específico, Intro/Outro) en los tipos Específico y Aleatorio — mismo
concepto que gui/dialogo_item_musicalizador.py, con la biblioteca
resuelta por RPC en vez de acceso directo al árbol local.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QCheckBox, QSpinBox,
    QStackedWidget, QWidget, QPushButton, QLabel, QRadioButton, QButtonGroup,
    QDialogButtonBox, QMessageBox,
)

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_elegir_pisador_remoto import DialogoElegirPisadorRemoto
from satelite.dialogo_elegir_registro_biblioteca import DialogoElegirRegistroBiblioteca
from satelite.dialogo_seleccionar_categoria_remoto import DialogoSeleccionarCategoriaRemoto
from satelite.utilidades import poblar_combo_categorias

TIPO_ESPECIFICO, TIPO_ALEATORIO, TIPO_SUBFORMATO = "especifico", "aleatorio", "subformato"
PISADOR_TIPO_CATEGORIA, PISADOR_TIPO_ESPECIFICO = "categoria", "especifico"
TIPOS = [("🎯 Específico (un archivo fijo)", TIPO_ESPECIFICO),
         ("🎲 Aleatorio (1 tema al azar de una categoría)", TIPO_ALEATORIO),
         ("🔁 Subformato (otro formato, por tiempo)", TIPO_SUBFORMATO)]


class DialogoItemMusicalizadorRemoto(QDialog):
    def __init__(self, cliente, categorias: list, otros_formatos: list, item_config: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ítem del formato" if item_config is None else "Editar ítem")
        self.setMinimumWidth(420)
        self._cliente = cliente
        self._categorias = categorias
        self._es_edicion = item_config is not None
        self._registro_especifico = None
        self._ruta_categoria_aleatorio = None
        self._ruta_categoria_pisador = None
        self._registro_pisador_especifico = None
        self._resultado = None

        self._construir_ui(otros_formatos)
        if item_config:
            self._cargar(item_config)

    # ------------------------------------------------------------------
    def _construir_ui(self, otros_formatos: list):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_tipo = QComboBox()
        for etiqueta, valor in TIPOS:
            self.combo_tipo.addItem(etiqueta, valor)
        self.combo_tipo.currentIndexChanged.connect(self._actualizar_pila)
        form.addRow("Tipo:", self.combo_tipo)
        layout.addLayout(form)

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
        self.combo_categoria_aleatorio = QComboBox()
        poblar_combo_categorias(self.combo_categoria_aleatorio, self._categorias)
        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        self.chk_recursivo.setChecked(True)
        form_aleatorio.addRow("Categoría:", self.combo_categoria_aleatorio)
        form_aleatorio.addRow(self.chk_recursivo)
        # Pedido explícito ("2 o 3 o 4 o 5"): agregar varios ítems
        # Aleatorio de una — solo tiene sentido al AGREGAR, nunca al
        # editar un ítem puntual ya existente.
        self.spin_cantidad_aleatorio = QSpinBox()
        self.spin_cantidad_aleatorio.setRange(1, 20)
        self.spin_cantidad_aleatorio.setValue(1)
        if not self._es_edicion:
            form_aleatorio.addRow("Cantidad a agregar:", self.spin_cantidad_aleatorio)
        self.pila.addWidget(pagina_aleatorio)

        # --- Subformato ---
        pagina_subformato = QWidget()
        form_subformato = QFormLayout(pagina_subformato)
        self.combo_subformato = QComboBox()
        self.combo_subformato.addItems(otros_formatos)
        self.spin_minutos = QSpinBox()
        self.spin_minutos.setRange(1, 600)
        self.spin_minutos.setValue(10)
        self.spin_minutos.setSuffix(" min")
        form_subformato.addRow("Formato:", self.combo_subformato)
        form_subformato.addRow("Duración:", self.spin_minutos)
        if not otros_formatos:
            form_subformato.addRow(QLabel("No hay otros formatos creados todavía."))
        self.pila.addWidget(pagina_subformato)

        # --- Pisador (Específico y Aleatorio) ---
        self.grupo_pisador = QWidget()
        form_pisador = QFormLayout(self.grupo_pisador)
        self.chk_pisador = QCheckBox("Agregar Pisador")
        self.chk_pisador.toggled.connect(self._on_toggle_pisador)
        form_pisador.addRow(self.chk_pisador)

        fila_tipo_pisador = QHBoxLayout()
        self.radio_pisador_tipo_categoria = QRadioButton("Categoría (aleatorio)")
        self.radio_pisador_tipo_especifico = QRadioButton("Archivo específico")
        self.radio_pisador_tipo_categoria.setChecked(True)
        grupo_tipo_pisador = QButtonGroup(self)
        grupo_tipo_pisador.addButton(self.radio_pisador_tipo_categoria)
        grupo_tipo_pisador.addButton(self.radio_pisador_tipo_especifico)
        self.radio_pisador_tipo_categoria.toggled.connect(self._actualizar_pila_pisador)
        fila_tipo_pisador.addWidget(self.radio_pisador_tipo_categoria)
        fila_tipo_pisador.addWidget(self.radio_pisador_tipo_especifico)
        form_pisador.addRow(fila_tipo_pisador)

        self.pila_pisador = QStackedWidget()

        pagina_pisador_categoria = QWidget()
        form_pisador_categoria = QFormLayout(pagina_pisador_categoria)
        form_pisador_categoria.setContentsMargins(0, 0, 0, 0)
        self.lbl_categoria_pisador = QLabel("(sin elegir)")
        self.lbl_categoria_pisador.setWordWrap(True)
        self.btn_elegir_pisador = QPushButton("Elegir categoría de Pisadores...")
        self.btn_elegir_pisador.clicked.connect(self._elegir_categoria_pisador)
        form_pisador_categoria.addRow(self.lbl_categoria_pisador)
        form_pisador_categoria.addRow(self.btn_elegir_pisador)
        self.pila_pisador.addWidget(pagina_pisador_categoria)

        pagina_pisador_especifico = QWidget()
        form_pisador_especifico = QFormLayout(pagina_pisador_especifico)
        form_pisador_especifico.setContentsMargins(0, 0, 0, 0)
        self.lbl_archivo_pisador = QLabel("(sin elegir)")
        self.lbl_archivo_pisador.setWordWrap(True)
        self.btn_elegir_pisador_especifico = QPushButton("Elegir archivo de Pisador...")
        self.btn_elegir_pisador_especifico.clicked.connect(self._elegir_archivo_pisador_especifico)
        form_pisador_especifico.addRow(self.lbl_archivo_pisador)
        form_pisador_especifico.addRow(self.btn_elegir_pisador_especifico)
        self.pila_pisador.addWidget(pagina_pisador_especifico)

        form_pisador.addRow(self.pila_pisador)

        self.radio_pisador_inicio = QRadioButton("Al empezar el tema (Intro)")
        self.radio_pisador_final = QRadioButton("Al terminar el tema (Outro)")
        self.radio_pisador_inicio.setChecked(True)
        grupo_radio_posicion = QButtonGroup(self)
        grupo_radio_posicion.addButton(self.radio_pisador_inicio)
        grupo_radio_posicion.addButton(self.radio_pisador_final)
        form_pisador.addRow(self.radio_pisador_inicio)
        form_pisador.addRow(self.radio_pisador_final)
        layout.addWidget(self.grupo_pisador)

        self._on_toggle_pisador(False)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._actualizar_pila()

    # ------------------------------------------------------------------
    def _actualizar_pila(self):
        tipo = self.combo_tipo.currentData()
        indice = {TIPO_ESPECIFICO: 0, TIPO_ALEATORIO: 1, TIPO_SUBFORMATO: 2}[tipo]
        self.pila.setCurrentIndex(indice)
        self.grupo_pisador.setVisible(tipo != TIPO_SUBFORMATO)

    def _on_toggle_pisador(self, activo: bool):
        self.radio_pisador_tipo_categoria.setEnabled(activo)
        self.radio_pisador_tipo_especifico.setEnabled(activo)
        self.pila_pisador.setEnabled(activo)
        self.radio_pisador_inicio.setEnabled(activo)
        self.radio_pisador_final.setEnabled(activo)

    def _actualizar_pila_pisador(self):
        indice = 0 if self.radio_pisador_tipo_categoria.isChecked() else 1
        self.pila_pisador.setCurrentIndex(indice)

    # ------------------------------------------------------------------
    def _elegir_archivo_especifico(self):
        if not self._categorias:
            QMessageBox.warning(self, "Elegir archivo", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoElegirRegistroBiblioteca(self._cliente, self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if registro:
            self._registro_especifico = registro
            self.lbl_archivo_especifico.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")

    def _elegir_categoria_pisador(self):
        dialogo = DialogoSeleccionarCategoriaRemoto(self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        ruta = dialogo.resultado()
        if ruta:
            self._ruta_categoria_pisador = ruta
            self.lbl_categoria_pisador.setText(" > ".join(ruta))

    def _elegir_archivo_pisador_especifico(self):
        dialogo = DialogoElegirPisadorRemoto(self._cliente, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if registro:
            self._registro_pisador_especifico = registro
            self.lbl_archivo_pisador.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")

    # ------------------------------------------------------------------
    def _cargar(self, item_config: dict):
        tipo = item_config.get("tipo", TIPO_ESPECIFICO)
        indice_combo = {TIPO_ESPECIFICO: 0, TIPO_ALEATORIO: 1, TIPO_SUBFORMATO: 2}.get(tipo, 0)
        self.combo_tipo.setCurrentIndex(indice_combo)

        if tipo == TIPO_ESPECIFICO:
            ruta = item_config.get("ruta", "")
            try:
                registro = self._cliente.resolver_registro_por_ruta(ruta) if ruta else None
            except ErrorControlRemoto:
                registro = None
            if registro:
                self._registro_especifico = registro
                self.lbl_archivo_especifico.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")
            else:
                self.lbl_archivo_especifico.setText("(el archivo original ya no existe)")
        elif tipo == TIPO_ALEATORIO:
            ruta = item_config.get("categoria") or []
            if ruta:
                indice = self.combo_categoria_aleatorio.findData(ruta)
                if indice >= 0:
                    self.combo_categoria_aleatorio.setCurrentIndex(indice)
            self.chk_recursivo.setChecked(item_config.get("recursivo", True))
        elif tipo == TIPO_SUBFORMATO:
            indice_sub = self.combo_subformato.findText(item_config.get("nombre", ""))
            if indice_sub >= 0:
                self.combo_subformato.setCurrentIndex(indice_sub)
            self.spin_minutos.setValue(max(1, int((item_config.get("duracion_segundos") or 600) / 60)))

        tipo_pisador = item_config.get("pisador_tipo", PISADOR_TIPO_CATEGORIA)
        ruta_pisador = item_config.get("pisador_categoria")
        ruta_pisador_especifico = item_config.get("pisador_ruta")
        if tipo_pisador == PISADOR_TIPO_ESPECIFICO and ruta_pisador_especifico:
            self.chk_pisador.setChecked(True)
            self.radio_pisador_tipo_especifico.setChecked(True)
            try:
                registro = self._cliente.resolver_registro_por_ruta(ruta_pisador_especifico)
            except ErrorControlRemoto:
                registro = None
            if registro:
                self._registro_pisador_especifico = registro
                self.lbl_archivo_pisador.setText(f"{registro.get('titulo', '')} ({registro.get('codigo', '')})")
            else:
                self.lbl_archivo_pisador.setText("(el archivo original ya no existe)")
        elif ruta_pisador:
            self.chk_pisador.setChecked(True)
            self.radio_pisador_tipo_categoria.setChecked(True)
            self._ruta_categoria_pisador = ruta_pisador
            self.lbl_categoria_pisador.setText(" > ".join(ruta_pisador))
        if self.chk_pisador.isChecked():
            if item_config.get("pisador_posicion") == "final":
                self.radio_pisador_final.setChecked(True)
            else:
                self.radio_pisador_inicio.setChecked(True)
        self._actualizar_pila_pisador()

    # ------------------------------------------------------------------
    def _confirmar(self):
        tipo = self.combo_tipo.currentData()

        if tipo == TIPO_ESPECIFICO:
            if not self._registro_especifico:
                QMessageBox.information(self, "Ítem", "Elegí un archivo para el ítem específico.")
                return
            item = {"tipo": TIPO_ESPECIFICO, "ruta": self._registro_especifico.get("ruta", "")}
        elif tipo == TIPO_ALEATORIO:
            if self.combo_categoria_aleatorio.count() == 0:
                QMessageBox.information(self, "Ítem", "No hay ninguna categoría disponible.")
                return
            item = {
                "tipo": TIPO_ALEATORIO, "categoria": self.combo_categoria_aleatorio.currentData(),
                "recursivo": self.chk_recursivo.isChecked(),
            }
        else:  # TIPO_SUBFORMATO
            if self.combo_subformato.count() == 0:
                QMessageBox.information(self, "Ítem", "Todavía no hay otro formato creado para usar como subformato.")
                return
            item = {
                "tipo": TIPO_SUBFORMATO, "nombre": self.combo_subformato.currentText(),
                "duracion_segundos": self.spin_minutos.value() * 60,
            }

        if tipo != TIPO_SUBFORMATO and self.chk_pisador.isChecked():
            if self.radio_pisador_tipo_especifico.isChecked():
                if not self._registro_pisador_especifico:
                    QMessageBox.information(
                        self, "Ítem", "Elegí un archivo específico de Pisador, o desmarcá \"Agregar Pisador\".",
                    )
                    return
                item["pisador_tipo"] = PISADOR_TIPO_ESPECIFICO
                item["pisador_ruta"] = self._registro_pisador_especifico.get("ruta", "")
            else:
                if not self._ruta_categoria_pisador:
                    QMessageBox.information(
                        self, "Ítem", "Elegí una categoría de Pisadores, o desmarcá \"Agregar Pisador\".",
                    )
                    return
                item["pisador_tipo"] = PISADOR_TIPO_CATEGORIA
                item["pisador_categoria"] = self._ruta_categoria_pisador
            item["pisador_posicion"] = "final" if self.radio_pisador_final.isChecked() else "inicio"

        self._resultado = item
        self.accept()

    def resultado(self):
        return self._resultado

    def resultado_cantidad(self) -> int:
        """Cuántas copias del ítem hay que agregar de una (pedido
        explícito, insertar varios Aleatorio a la vez) — siempre 1
        para Específico/Subformato o al editar un ítem existente."""
        if self._es_edicion or self._resultado is None or self._resultado.get("tipo") != TIPO_ALEATORIO:
            return 1
        return self.spin_cantidad_aleatorio.value()
