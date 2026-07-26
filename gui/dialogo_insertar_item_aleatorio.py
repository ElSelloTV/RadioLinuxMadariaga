"""
gui/dialogo_insertar_item_aleatorio.py
--------------------------------------------------------
"Ítem Aleatorio" del Programador de Ventana 1 (pedido explícito:
"agregar un ítem aleatorio de alguna categoría o sub-categoría, para
darle dinamismo, por ejemplo en separadores... que sea buen aleatorio
y variado"): elige una categoría/subcategoría del Explorador — el
archivo en sí se resuelve al azar recién CADA VEZ que le toca sonar
(ver core/playlist_manager.py:GestorPublicidad._resolver_item_aleatorio),
nunca un archivo fijo elegido una sola vez acá.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QDialogButtonBox, QSpinBox,
)

from gui.dialogo_seleccionar_categoria import DialogoSeleccionarCategoria


class DialogoInsertarItemAleatorio(QDialog):
    def __init__(self, tree_categorias_origen, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Ítem Aleatorio")
        self.setMinimumWidth(380)
        self._tree_categorias_origen = tree_categorias_origen
        self._ruta_categoria = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Cada vez que le toque sonar, se elige un archivo al azar\n"
            "de la categoría — nunca el mismo archivo fijo, y no repite\n"
            "ninguno hasta que sonaron todos los demás de la categoría."
        ))

        fila_categoria = QHBoxLayout()
        self.btn_elegir_categoria = QPushButton("Elegir categoría...")
        self.btn_elegir_categoria.clicked.connect(self._elegir_categoria)
        self.lbl_categoria = QLabel("(ninguna elegida)")
        fila_categoria.addWidget(self.btn_elegir_categoria)
        fila_categoria.addWidget(self.lbl_categoria, 1)
        layout.addLayout(fila_categoria)

        self.chk_recursivo = QCheckBox("Incluir subcategorías")
        self.chk_recursivo.setChecked(True)
        layout.addWidget(self.chk_recursivo)

        # Pedido explícito ("poder incorporar un número de ítem
        # aleatorios, por ejemplo que pueda poner 2 o 3 o 4 o 5"): en
        # vez de repetir el botón "＋ Ítem Aleatorio..." a mano varias
        # veces, un solo click inserta la cantidad elegida de una —
        # cada uno es un placeholder INDEPENDIENTE (misma categoría),
        # que se resuelve a un archivo distinto cada vez que le toca
        # sonar (ver GestorPublicidad._resolver_item_aleatorio, con
        # el guard nuevo de "no repetir dentro del mismo bloque").
        fila_cantidad = QHBoxLayout()
        fila_cantidad.addWidget(QLabel("Cantidad de ítems a insertar:"))
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(1, 20)
        self.spin_cantidad.setValue(1)
        fila_cantidad.addWidget(self.spin_cantidad)
        fila_cantidad.addStretch()
        layout.addLayout(fila_cantidad)

        self.botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botones.accepted.connect(self._confirmar)
        self.botones.rejected.connect(self.reject)
        layout.addWidget(self.botones)
        self._actualizar_boton_ok()

    def _elegir_categoria(self):
        dialogo = DialogoSeleccionarCategoria(self._tree_categorias_origen, parent=self)
        if dialogo.exec() != DialogoSeleccionarCategoria.DialogCode.Accepted:
            return
        self._ruta_categoria = dialogo.ruta_elegida()
        self.lbl_categoria.setText(" / ".join(self._ruta_categoria) if self._ruta_categoria else "(ninguna elegida)")
        self._actualizar_boton_ok()

    def _actualizar_boton_ok(self):
        self.botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self._ruta_categoria))

    def _confirmar(self):
        if not self._ruta_categoria:
            return
        self.accept()

    def resultado(self):
        """(ruta_categoria: list[str], recursivo: bool, cantidad: int)."""
        return self._ruta_categoria, self.chk_recursivo.isChecked(), self.spin_cantidad.value()
