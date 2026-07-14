"""
gui/dialogo_agregar_archivo.py
--------------------------------------------------------
Ventana emergente que se muestra al agregar un archivo de audio
a la biblioteca (Ventana 3 - Explorador). Permite:
- Confirmar (o cambiar) en qué categoría/subcategoría queda.
- Registrarlo bajo un nombre editorial distinto al del archivo
  fuente (ej. "once_mil_Abel_Pintos.mp3" -> "Once Mil").
- Cargar Artista y Género.
- Ver el código correlativo que se le va a asignar (depende de
  la categoría elegida y del prefijo del género).
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel, QCheckBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate

from gui.styles import LISTA_GENEROS, GENERO_PREFIJOS_CODIGO

ROL_ITEM_CATEGORIA = Qt.ItemDataRole.UserRole + 1


class DialogoAgregarArchivo(QDialog):
    def __init__(self, ruta: str, tree_categorias, categoria_sugerida=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar a la biblioteca")
        self.setMinimumWidth(420)
        self._tree_categorias = tree_categorias

        self._nombre_resultado = None
        self._artista_resultado = None
        self._genero_resultado = None
        self._item_categoria_resultado = None
        self._codigo_resultado = None
        self._fecha_inicio_resultado = None
        self._fecha_fin_resultado = None

        self._construir_ui(ruta, categoria_sugerida)

    # ------------------------------------------------------------------
    def _construir_ui(self, ruta, categoria_sugerida):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        lbl_archivo = QLabel(os.path.basename(ruta))
        lbl_archivo.setObjectName("lblTituloBloqueActivo")
        form.addRow("Archivo fuente:", lbl_archivo)

        self.txt_nombre = QLineEdit(os.path.splitext(os.path.basename(ruta))[0])
        form.addRow("Nombre (editorial):", self.txt_nombre)

        self.txt_artista = QLineEdit()
        form.addRow("Artista:", self.txt_artista)

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(LISTA_GENEROS)
        self.combo_genero.currentIndexChanged.connect(self._actualizar_codigo_previsto)
        form.addRow("Género:", self.combo_genero)

        self.combo_categoria = QComboBox()
        self._poblar_categorias(categoria_sugerida)
        self.combo_categoria.currentIndexChanged.connect(self._actualizar_codigo_previsto)
        form.addRow("Categoría:", self.combo_categoria)

        self.lbl_codigo_previsto = QLabel("—")
        self.lbl_codigo_previsto.setObjectName("lblTituloBloqueActivo")
        form.addRow("Código asignado:", self.lbl_codigo_previsto)

        # Vigencia de fecha (pedido explícito, opcional — pensado para
        # publicidad con fecha de campaña): sin marcar, el material no
        # tiene restricción de fecha, igual que siempre.
        fila_inicio = QHBoxLayout()
        self.chk_fecha_inicio = QCheckBox("Empieza a emitirse el:")
        self.date_inicio = QDateEdit(QDate.currentDate())
        self.date_inicio.setCalendarPopup(True)
        self.date_inicio.setEnabled(False)
        self.chk_fecha_inicio.toggled.connect(self.date_inicio.setEnabled)
        fila_inicio.addWidget(self.chk_fecha_inicio)
        fila_inicio.addWidget(self.date_inicio)
        form.addRow(fila_inicio)

        fila_fin = QHBoxLayout()
        self.chk_fecha_fin = QCheckBox("Deja de emitirse el:")
        self.date_fin = QDateEdit(QDate.currentDate())
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setEnabled(False)
        self.chk_fecha_fin.toggled.connect(self.date_fin.setEnabled)
        fila_fin.addWidget(self.chk_fecha_fin)
        fila_fin.addWidget(self.date_fin)
        form.addRow(fila_fin)

        layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self._actualizar_codigo_previsto()

    # ------------------------------------------------------------------
    def _poblar_categorias(self, categoria_sugerida):
        """Recorre el árbol de categorías completo (sin límite de
        niveles) y arma un combo con sangría según profundidad."""
        indice_sugerido = 0

        def recorrer(item_padre, profundidad):
            nonlocal indice_sugerido
            cantidad = item_padre.childCount() if item_padre else self._tree_categorias.topLevelItemCount()
            for i in range(cantidad):
                item = item_padre.child(i) if item_padre else self._tree_categorias.topLevelItem(i)
                etiqueta = ("　" * profundidad) + ("— " if profundidad else "") + item.text(0)
                self.combo_categoria.addItem(etiqueta, item)
                if item is categoria_sugerida:
                    indice_sugerido = self.combo_categoria.count() - 1
                recorrer(item, profundidad + 1)

        recorrer(None, 0)
        if self.combo_categoria.count() > 0:
            self.combo_categoria.setCurrentIndex(indice_sugerido)

    def _actualizar_codigo_previsto(self):
        item_categoria = self.combo_categoria.currentData()
        genero = self.combo_genero.currentText()
        if item_categoria is None:
            self.lbl_codigo_previsto.setText("—")
            return

        from gui.ventana_explorador import ROL_ARCHIVOS
        registros = item_categoria.data(0, ROL_ARCHIVOS) or []
        siguiente_numero = len(registros) + 1
        prefijo = GENERO_PREFIJOS_CODIGO.get(genero, "GEN")
        self.lbl_codigo_previsto.setText(f"{prefijo}{siguiente_numero:05d}")

    # ------------------------------------------------------------------
    def _confirmar(self):
        self._nombre_resultado = self.txt_nombre.text().strip() or "Sin título"
        self._artista_resultado = self.txt_artista.text().strip()
        self._genero_resultado = self.combo_genero.currentText()
        self._item_categoria_resultado = self.combo_categoria.currentData()
        self._codigo_resultado = self.lbl_codigo_previsto.text()
        self._fecha_inicio_resultado = self.date_inicio.date().toString("yyyy-MM-dd") \
            if self.chk_fecha_inicio.isChecked() else None
        self._fecha_fin_resultado = self.date_fin.date().toString("yyyy-MM-dd") \
            if self.chk_fecha_fin.isChecked() else None
        self.accept()

    def resultado(self) -> dict | None:
        """None si se canceló; si no, el registro listo para guardar."""
        if self._item_categoria_resultado is None:
            return None
        return {
            "titulo": self._nombre_resultado,
            "artista": self._artista_resultado,
            "genero": self._genero_resultado,
            "codigo": self._codigo_resultado,
            "item_categoria": self._item_categoria_resultado,
            "fecha_inicio": self._fecha_inicio_resultado,
            "fecha_fin": self._fecha_fin_resultado,
        }
