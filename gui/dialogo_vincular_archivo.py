"""
gui/dialogo_vincular_archivo.py
--------------------------------------------------------
Diálogo de la función "Ubicar" -> "Buscarlo..." de Ventana 3
(Explorador): muestra TODOS los archivos candidatos encontrados en la
carpeta Música real del sistema, matcheados PRIMERO por tamaño en
bytes y luego por duración (pedido explícito -- el nombre pudo haber
cambiado, y el tamaño es más confiable que la duración estimada por
mutagen, que puede variar un segundo entre lecturas/formatos — ver
VentanaExplorador._buscar_archivo_perdido), con:
- ▶ Previo / ■ Detener para escuchar cada candidato antes de decidir
  (SIEMPRE por la salida de "Salida Preescucha" configurada, nunca la
  Master — pedido explícito, mismo criterio que ya usa el ▶ Previo
  normal de Ventana 3, core/playlist_manager.py:GestorExplorador).
- ⏭ Saltar, para pasar al próximo archivo sin vincular sin elegir
  ningún candidato de este (VentanaExplorador._procesar_lista_de_perdidos
  sigue con el siguiente de la cola).
- 🔗 Vincular, que confirma el candidato seleccionado.
- Menú contextual sobre cada candidato: "✏ Tomar el nombre" (renombra
  el ARCHIVO EN DISCO al título del registro roto, sin pedir
  confirmación) y "🗑 Eliminar" (borra el archivo de la PC, con aviso
  previo — pedido explícito de Santiago: "lo utilizaré por si hay 2
  archivos iguales o las coincidencias no son las que yo esperaba y
  sobra el archivo" — esto NUNCA toca el registro/JSON de la
  biblioteca, solo limpia archivos de sobra encontrados en el disco).
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QDialogButtonBox, QAbstractItemView, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt

from core.audio_engine import MotorAudio

COL_CARPETA, COL_ARCHIVO, COL_TAMANO, COL_TAMANO_COINCIDE, COL_DURACION, COL_DURACION_COINCIDE = range(6)

_CARACTERES_INVALIDOS = '/\\:*?"<>|'


def _formatear_tamano(tamano_bytes) -> str:
    if tamano_bytes is None:
        return "?"
    return f"{tamano_bytes / (1024 * 1024):.2f} MB"


def _sanitizar_nombre_archivo(nombre: str) -> str:
    limpio = "".join("_" if c in _CARACTERES_INVALIDOS else c for c in nombre).strip()
    return limpio or "archivo"


class DialogoVincularArchivo(QDialog):
    # Código de resultado propio para "⏭ Saltar" (distinto de
    # QDialog.Accepted=1/Rejected=0, ver _saltar()).
    SALTAR = 2

    def __init__(self, titulo_registro: str, candidatos: list, id_dispositivo_preescucha, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar archivo perdido")
        self.setMinimumSize(560, 360)
        self._ruta_elegida = None
        self._titulo_registro = titulo_registro

        # aplicar_procesador=False, mismo criterio que el Previo normal
        # de Ventana 3 -- este motor SIEMPRE sale por Preescucha, nunca
        # por la Master que va al aire.
        self._motor = MotorAudio(id_dispositivo_preescucha, aplicar_procesador=False)
        self._motor.finalizo_item.connect(self._detener)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"No se encontró el archivo de '{titulo_registro}' en su ubicación original.\n"
            "Estos son los candidatos encontrados en la carpeta Música "
            "(primero por tamaño, luego por duración — el nombre pudo haber cambiado).\n"
            "Clic derecho sobre un candidato para \"Tomar el nombre\" o \"Eliminar\":"
        ))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Carpeta", "Archivo", "Tamaño", "¿Tamaño coincide?", "Duración", "¿Duración coincide?",
        ])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        for candidato in candidatos:
            self._agregar_fila_candidato(candidato["ruta"], candidato)
        for columna in range(6):
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
        self.btn_saltar = QPushButton("⏭ Saltar")
        self.btn_saltar.setToolTip("Pasar al próximo archivo sin vincular, sin elegir ninguno de estos candidatos.")
        self.btn_saltar.clicked.connect(self._saltar)
        fila_previo.addWidget(self.btn_previo)
        fila_previo.addWidget(self.btn_detener)
        fila_previo.addWidget(self.btn_saltar)
        fila_previo.addStretch()
        layout.addLayout(fila_previo)

        botones = QDialogButtonBox()
        self.btn_vincular = botones.addButton("🔗 Vincular", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_vincular.setEnabled(self.tree.topLevelItemCount() > 0)
        botones.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        botones.accepted.connect(self._vincular)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _agregar_fila_candidato(self, ruta: str, candidato: dict):
        item = QTreeWidgetItem([
            os.path.dirname(ruta),
            os.path.basename(ruta),
            _formatear_tamano(candidato.get("tamaño_bytes")),
            "Sí" if candidato.get("tamaño_coincide") else "—",
            candidato.get("duracion", ""),
            "Sí" if candidato.get("duracion_coincide") else "—",
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, ruta)
        self.tree.addTopLevelItem(item)
        return item

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

    def _saltar(self):
        self._detener()
        self.done(self.SALTAR)

    def resultado(self) -> str | None:
        return self._ruta_elegida

    def reject(self):
        self._detener()
        super().reject()

    def closeEvent(self, evento):
        self._detener()
        super().closeEvent(evento)

    # ------------------------------------------------------------------
    # Menú contextual sobre un candidato: Tomar el nombre / Eliminar.
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        item = self.tree.itemAt(posicion)
        if item is None:
            return
        self.tree.setCurrentItem(item)

        menu = QMenu(self)
        accion_tomar_nombre = menu.addAction("✏ Tomar el nombre")
        accion_eliminar = menu.addAction("🗑 Eliminar")
        accion_elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if accion_elegida == accion_tomar_nombre:
            self._tomar_nombre(item)
        elif accion_elegida == accion_eliminar:
            self._eliminar_candidato(item)

    def _tomar_nombre(self, item):
        """Pedido explícito ("tomará el nombre del JSON que tengo
        registrado en la ventana 3 respetando la extensión -- sin
        pedir confirmación"): renombra el archivo EN DISCO, dejando la
        extensión real del candidato tal cual está (nunca inventada a
        partir del título)."""
        ruta_actual = item.data(0, Qt.ItemDataRole.UserRole)
        extension = os.path.splitext(ruta_actual)[1]
        nombre_nuevo = _sanitizar_nombre_archivo(self._titulo_registro) + extension
        carpeta = os.path.dirname(ruta_actual)
        ruta_nueva = os.path.join(carpeta, nombre_nuevo)

        if ruta_nueva == ruta_actual:
            return
        if os.path.exists(ruta_nueva):
            QMessageBox.warning(
                self, "Tomar el nombre",
                f"Ya existe un archivo con ese nombre en la carpeta:\n{ruta_nueva}",
            )
            return
        try:
            os.rename(ruta_actual, ruta_nueva)
        except OSError as error:
            QMessageBox.warning(self, "Tomar el nombre", f"No se pudo renombrar el archivo:\n{error}")
            return

        item.setData(0, Qt.ItemDataRole.UserRole, ruta_nueva)
        item.setText(COL_ARCHIVO, os.path.basename(ruta_nueva))

    def _eliminar_candidato(self, item):
        """Pedido explícito ("eliminar el tema musical de la
        computadora, con un aviso previo") -- borra el ARCHIVO de la
        PC de forma definitiva. Aclaración de Santiago: esto NUNCA
        toca el registro de la biblioteca (JSON) -- se usa para
        limpiar duplicados o candidatos que no eran los esperados,
        encontrados durante esta búsqueda puntual."""
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        respuesta = QMessageBox.question(
            self, "Eliminar archivo",
            f"Esto borra el archivo de la PC de forma DEFINITIVA (no toca "
            f"ningún registro de la biblioteca):\n{ruta}\n\n¿Confirmás?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        if item is self.tree.currentItem():
            self._detener()
        try:
            os.remove(ruta)
        except OSError as error:
            QMessageBox.warning(self, "Eliminar archivo", f"No se pudo eliminar el archivo:\n{error}")
            return

        indice = self.tree.indexOfTopLevelItem(item)
        if indice >= 0:
            self.tree.takeTopLevelItem(indice)
        self.btn_vincular.setEnabled(self.tree.topLevelItemCount() > 0)
