"""
gui/dialogo_duplicados.py
--------------------------------------------------------
Buscador de duplicados en la biblioteca (Ventana 3) — pedido
explícito: "búsqueda de duplicados en el explorador (ventana 3) por
nombre, duración y tamaño con opción de elegir alguno de esos filtros
incluso los 3 juntos. Menú contextual de mover o eliminar. Debo ver
las rutas de categorías cuando aparezcan duplicados."

Los 3 criterios (Nombre/Duración/Tamaño) son checkboxes combinables —
buscar_duplicados_biblioteca() (gui/ventana_explorador.py) agrupa por
la INTERSECCIÓN de los criterios activos, nunca por unión: con los 3
tildados, dos registros solo cuentan como duplicados si coinciden en
los 3 a la vez.

Nota importante, para no confundir con gui/dialogo_vincular_archivo.py:
acá "Eliminar" borra el REGISTRO de la biblioteca JSON (la entrada,
nunca el archivo físico) — el concepto opuesto al "Eliminar" del
diálogo de Vincular archivos perdidos, que borra el archivo real de la
PC y nunca toca el JSON. Los dos conviven a propósito, cada uno con su
alcance bien distinto.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt

from gui.dialogo_seleccionar_categoria import DialogoSeleccionarCategoria

ROL_REGISTRO = Qt.ItemDataRole.UserRole + 1
ROL_CATEGORIA = Qt.ItemDataRole.UserRole + 2

COL_TITULO, COL_CATEGORIA, COL_DURACION, COL_TAMANO, COL_RUTA = range(5)


class DialogoDuplicados(QDialog):
    def __init__(self, ventana_explorador, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar duplicados en la biblioteca")
        self.setMinimumSize(760, 480)
        self._ventana_explorador = ventana_explorador

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Elegí uno o varios criterios — un grupo solo se considera\n"
            "duplicado si coincide en TODOS los criterios tildados:"
        ))

        fila_criterios = QHBoxLayout()
        self.chk_nombre = QCheckBox("Nombre")
        self.chk_nombre.setChecked(True)
        self.chk_duracion = QCheckBox("Duración")
        self.chk_tamano = QCheckBox("Tamaño")
        fila_criterios.addWidget(self.chk_nombre)
        fila_criterios.addWidget(self.chk_duracion)
        fila_criterios.addWidget(self.chk_tamano)
        fila_criterios.addStretch()
        self.btn_buscar = QPushButton("🔎 Buscar duplicados")
        self.btn_buscar.clicked.connect(self._buscar)
        fila_criterios.addWidget(self.btn_buscar)
        layout.addLayout(fila_criterios)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Título", "Categoría", "Duración", "Tamaño", "Ruta"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        layout.addWidget(self.tree)

        self.lbl_estado = QLabel("")
        layout.addWidget(self.lbl_estado)

        fila_botones = QHBoxLayout()
        fila_botones.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        fila_botones.addWidget(btn_cerrar)
        layout.addLayout(fila_botones)

    # ------------------------------------------------------------------
    def _buscar(self):
        self.tree.clear()
        grupos = self._ventana_explorador.buscar_duplicados_biblioteca(
            por_nombre=self.chk_nombre.isChecked(),
            por_duracion=self.chk_duracion.isChecked(),
            por_tamano=self.chk_tamano.isChecked(),
        )
        if not (self.chk_nombre.isChecked() or self.chk_duracion.isChecked() or self.chk_tamano.isChecked()):
            self.lbl_estado.setText("⚠ Elegí al menos un criterio de búsqueda.")
            return

        for indice, grupo in enumerate(grupos, start=1):
            titulo = grupo[0][0].get("titulo", "")
            nodo_grupo = QTreeWidgetItem([f"Grupo {indice} — {len(grupo)} coincidencias de '{titulo}'", "", "", "", ""])
            nodo_grupo.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(nodo_grupo)
            for registro, categoria in grupo:
                ruta_categoria = " > ".join(self._ventana_explorador.ruta_de_categoria(categoria)) or "(raíz)"
                hijo = QTreeWidgetItem([
                    registro.get("titulo", ""),
                    ruta_categoria,
                    registro.get("duracion", ""),
                    self._formatear_tamano(registro.get("tamaño_bytes")),
                    registro.get("ruta", "") or "(sin vincular)",
                ])
                hijo.setData(0, ROL_REGISTRO, registro)
                hijo.setData(0, ROL_CATEGORIA, categoria)
                nodo_grupo.addChild(hijo)
            nodo_grupo.setExpanded(True)

        if not grupos:
            self.lbl_estado.setText("No se encontraron duplicados con los criterios elegidos.")
        else:
            total = sum(len(g) for g in grupos)
            self.lbl_estado.setText(f"{len(grupos)} grupo(s) de duplicados — {total} archivos en total.")

    @staticmethod
    def _formatear_tamano(tamano_bytes):
        if not tamano_bytes:
            return "(desconocido)"
        for unidad in ("B", "KB", "MB", "GB"):
            if tamano_bytes < 1024:
                return f"{tamano_bytes:.0f} {unidad}" if unidad == "B" else f"{tamano_bytes:.1f} {unidad}"
            tamano_bytes /= 1024
        return f"{tamano_bytes:.1f} TB"

    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, punto):
        item = self.tree.itemAt(punto)
        if item is None or item.parent() is None:
            return
        registro = item.data(0, ROL_REGISTRO)
        if registro is None:
            return

        menu = QMenu(self)
        accion_mover = menu.addAction("📂 Mover a categoría...")
        accion_eliminar = menu.addAction("🗑 Eliminar registro de la biblioteca")
        elegida = menu.exec(self.tree.viewport().mapToGlobal(punto))
        if elegida == accion_mover:
            self._mover_item(item)
        elif elegida == accion_eliminar:
            self._eliminar_item(item)

    def _mover_item(self, item):
        registro = item.data(0, ROL_REGISTRO)
        categoria_origen = item.data(0, ROL_CATEGORIA)
        dialogo = DialogoSeleccionarCategoria(
            self._ventana_explorador.tree_categorias,
            titulo="Mover a categoría",
            parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        ruta_elegida = dialogo.ruta_elegida()
        if not ruta_elegida:
            return
        categoria_destino = self._ventana_explorador.buscar_categoria_por_ruta(ruta_elegida)
        if categoria_destino is None:
            return
        if self._ventana_explorador.mover_registro_a_otra_categoria(registro, categoria_origen, categoria_destino):
            item.parent().removeChild(item)

    def _eliminar_item(self, item):
        respuesta = QMessageBox.question(
            self, "Eliminar registro",
            f"¿Eliminar '{item.text(COL_TITULO)}' de la biblioteca?\n\n"
            "Esto borra el REGISTRO (la entrada de la biblioteca), no el\n"
            "archivo físico en la computadora.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        registro = item.data(0, ROL_REGISTRO)
        categoria = item.data(0, ROL_CATEGORIA)
        if self._ventana_explorador.eliminar_registro_de_categoria(registro, categoria):
            item.parent().removeChild(item)
