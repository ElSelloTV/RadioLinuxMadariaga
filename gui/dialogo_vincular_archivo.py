"""
gui/dialogo_vincular_archivo.py
--------------------------------------------------------
Diálogo de la función "Ubicar" -> "Buscarlo..." de Ventana 3
(Explorador): muestra TODOS los archivos candidatos encontrados con
la misma duración que el registro roto (el nombre pudo haber
cambiado, así que la duración es la identidad real usada para
matchear — ver VentanaExplorador._buscar_archivo_perdido), con un
▶ Previo/■ Detener para escuchar cada uno antes de decidir, y un
botón "🔗 Vincular" que confirma la elección.

Pedido explícito (punto i): la salida de audio de este previo es
SIEMPRE la de "Salida Preescucha" configurada, nunca la Master — el
mismo criterio que ya usa el ▶ Previo normal de Ventana 3
(core/playlist_manager.py:GestorExplorador).
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QDialogButtonBox, QAbstractItemView,
)
from PySide6.QtCore import Qt

from core.audio_engine import MotorAudio

COL_CARPETA, COL_ARCHIVO, COL_DURACION, COL_TAMANO, COL_TAMANO_COINCIDE = range(5)


def _formatear_tamano(tamano_bytes) -> str:
    if tamano_bytes is None:
        return "?"
    return f"{tamano_bytes / (1024 * 1024):.2f} MB"


class DialogoVincularArchivo(QDialog):
    def __init__(self, titulo_registro: str, candidatos: list, id_dispositivo_preescucha, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar archivo perdido")
        self.setMinimumSize(560, 360)
        self._ruta_elegida = None

        # aplicar_procesador=False, mismo criterio que el Previo normal
        # de Ventana 3 -- este motor SIEMPRE sale por Preescucha, nunca
        # por la Master que va al aire.
        self._motor = MotorAudio(id_dispositivo_preescucha, aplicar_procesador=False)
        self._motor.finalizo_item.connect(self._detener)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"No se encontró el archivo de '{titulo_registro}' en su ubicación original.\n"
            "Estos son los candidatos encontrados con la misma duración "
            "(el nombre pudo haber cambiado):"
        ))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Carpeta", "Archivo", "Duración", "Tamaño", "¿Tamaño coincide?"])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for candidato in candidatos:
            item = QTreeWidgetItem([
                os.path.dirname(candidato["ruta"]),
                os.path.basename(candidato["ruta"]),
                candidato.get("duracion", ""),
                _formatear_tamano(candidato.get("tamaño_bytes")),
                "Sí" if candidato.get("tamaño_coincide") else "—",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, candidato["ruta"])
            self.tree.addTopLevelItem(item)
        for columna in range(5):
            self.tree.resizeColumnToContents(columna)
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self.tree.itemSelectionChanged.connect(self._detener)
        layout.addWidget(self.tree)

        fila_previo = QHBoxLayout()
        self.btn_previo = QPushButton("▶ Previo")
        self.btn_previo.clicked.connect(self._reproducir_seleccion)
        self.btn_detener = QPushButton("■ Detener")
        self.btn_detener.clicked.connect(self._detener)
        fila_previo.addWidget(self.btn_previo)
        fila_previo.addWidget(self.btn_detener)
        fila_previo.addStretch()
        layout.addLayout(fila_previo)

        botones = QDialogButtonBox()
        self.btn_vincular = botones.addButton("🔗 Vincular", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_vincular.setEnabled(self.tree.topLevelItemCount() > 0)
        botones.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        botones.accepted.connect(self._vincular)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _reproducir_seleccion(self):
        item = self.tree.currentItem()
        if item is None:
            return
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        self._motor.reproducir(ruta)

    def _detener(self):
        self._motor.detener()

    def _vincular(self):
        item = self.tree.currentItem()
        if item is None:
            return
        self._ruta_elegida = item.data(0, Qt.ItemDataRole.UserRole)
        self._detener()
        self.accept()

    def resultado(self) -> str | None:
        return self._ruta_elegida

    def reject(self):
        self._detener()
        super().reject()

    def closeEvent(self, evento):
        self._detener()
        super().closeEvent(evento)
