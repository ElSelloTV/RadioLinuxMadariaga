"""
satelite/dialogo_item_musicalizador_remoto.py
--------------------------------------------------------
Arma UN ítem de un formato del Musicalizador remoto — 3 tipos, mismo
motor puro (`core/musicalizador.py`) que ya usa la app principal.
Sin Pisador en esta ronda (MVP deliberado, documentado en CLAUDE.md)
— si Santiago lo necesita remoto, es una extensión acotada de este
mismo diálogo en una ronda futura.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox, QSpinBox,
    QStackedWidget, QWidget, QPushButton, QLabel, QDialogButtonBox, QMessageBox,
)

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_elegir_registro_biblioteca import DialogoElegirRegistroBiblioteca
from satelite.utilidades import poblar_combo_categorias

TIPOS = ["Específico", "Aleatorio", "Subformato"]


class DialogoItemMusicalizadorRemoto(QDialog):
    def __init__(self, cliente, categorias: list, otros_formatos: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ítem del formato")
        self.setMinimumWidth(380)
        self._cliente = cliente
        self._categorias = categorias
        self._registro_elegido = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(TIPOS)
        form.addRow("Tipo:", self.combo_tipo)
        layout.addLayout(form)

        self.paginas = QStackedWidget()
        layout.addWidget(self.paginas)

        pagina_especifico = QWidget()
        layout_especifico = QVBoxLayout(pagina_especifico)
        self.btn_elegir_archivo = QPushButton("📂 Elegir archivo...")
        self.lbl_archivo_elegido = QLabel("(ninguno)")
        self.lbl_archivo_elegido.setWordWrap(True)
        self.btn_elegir_archivo.clicked.connect(self._elegir_archivo)
        layout_especifico.addWidget(self.btn_elegir_archivo)
        layout_especifico.addWidget(self.lbl_archivo_elegido)
        self.paginas.addWidget(pagina_especifico)

        pagina_aleatorio = QWidget()
        layout_aleatorio = QFormLayout(pagina_aleatorio)
        self.combo_categoria_aleatorio = QComboBox()
        poblar_combo_categorias(self.combo_categoria_aleatorio, categorias)
        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        self.chk_recursivo.setChecked(True)
        layout_aleatorio.addRow("Categoría:", self.combo_categoria_aleatorio)
        layout_aleatorio.addRow(self.chk_recursivo)
        self.paginas.addWidget(pagina_aleatorio)

        pagina_subformato = QWidget()
        layout_subformato = QFormLayout(pagina_subformato)
        self.combo_subformato = QComboBox()
        self.combo_subformato.addItems(otros_formatos)
        self.spin_minutos = QSpinBox()
        self.spin_minutos.setRange(1, 600)
        self.spin_minutos.setValue(10)
        layout_subformato.addRow("Formato:", self.combo_subformato)
        layout_subformato.addRow("Duración (minutos):", self.spin_minutos)
        self.paginas.addWidget(pagina_subformato)

        self.combo_tipo.currentIndexChanged.connect(self.paginas.setCurrentIndex)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._resultado = None

    def _elegir_archivo(self):
        if not self._categorias:
            QMessageBox.warning(self, "Elegir archivo", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoElegirRegistroBiblioteca(self._cliente, self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if not registro:
            return
        self._registro_elegido = registro
        self.lbl_archivo_elegido.setText(f"{registro['codigo']} — {registro['titulo']}")

    def _confirmar(self):
        tipo = self.combo_tipo.currentText()
        if tipo == "Específico":
            if not self._registro_elegido:
                QMessageBox.warning(self, "Ítem", "Elegí un archivo primero.")
                return
            self._resultado = {"tipo": "especifico", "ruta": self._registro_elegido["ruta"]}
        elif tipo == "Aleatorio":
            if self.combo_categoria_aleatorio.count() == 0:
                QMessageBox.warning(self, "Ítem", "No hay ninguna categoría disponible.")
                return
            self._resultado = {
                "tipo": "aleatorio",
                "categoria": self.combo_categoria_aleatorio.currentData(),
                "recursivo": self.chk_recursivo.isChecked(),
            }
        else:
            if self.combo_subformato.count() == 0:
                QMessageBox.warning(self, "Ítem", "No hay otro formato disponible para usar como subformato.")
                return
            self._resultado = {
                "tipo": "subformato",
                "nombre": self.combo_subformato.currentText(),
                "duracion_segundos": self.spin_minutos.value() * 60,
            }
        self.accept()

    def resultado(self):
        return self._resultado
