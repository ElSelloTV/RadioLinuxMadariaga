"""
satelite/dialogo_programador_remoto.py
--------------------------------------------------------
Programador remoto — pedido explícito: "que pueda mediante otro
botón, programar, igual que en el programa principal". MVP deliberado
(documentado en CLAUDE.md): cubre el flujo central del Programador
real (cargar un punto de partida, armar bloques/ítems, guardar,
aplicar ahora) reusando las MISMAS funciones de persistencia que ya
usa la app principal (por RPC) — quedan afuera de esta ronda el
drag&drop de reordenar, copiar/pegar entre bloques y "duplicar para
otro día", que sí tiene la versión local (`gui/ventana_programador.py`).

El estado real vive acá, en `self._bloques` (una lista de dicts, el
MISMO formato que ya usa `cargar_bloques()`/`programacion.json`) — el
árbol visual se reconstruye entero desde ahí después de cada cambio
("redraw from model"), más simple y robusto que sincronizar un árbol
Qt a mano contra el modelo.
--------------------------------------------------------
"""
import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QInputDialog,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_bloque_horario import DialogoBloqueHorario
from satelite.dialogo_elegir_registro_biblioteca import DialogoElegirRegistroBiblioteca
from satelite.dialogo_guardar_programacion import DialogoGuardarProgramacion


class DialogoProgramadorRemoto(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Programador (remoto)")
        self.resize(640, 560)
        self._cliente = cliente
        self._bloques = []
        self._categorias = []
        self._construir_ui()
        self._cargar_categorias()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        fila_origen = QHBoxLayout()
        btn_cargar_guardada = QPushButton("📂 Cargar guardada...")
        btn_cargar_actual = QPushButton("⬇ Cargar el actual (Ventana 1)")
        btn_nueva = QPushButton("🗎 Nueva (vacía)")
        btn_cargar_guardada.clicked.connect(self._cargar_guardada)
        btn_cargar_actual.clicked.connect(self._cargar_actual)
        btn_nueva.clicked.connect(self._nueva)
        fila_origen.addWidget(btn_cargar_guardada)
        fila_origen.addWidget(btn_cargar_actual)
        fila_origen.addWidget(btn_nueva)
        layout.addLayout(fila_origen)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Bloques e ítems"])
        layout.addWidget(self.tree, 1)

        fila_edicion = QHBoxLayout()
        btn_agregar_bloque = QPushButton("＋ Bloque horario...")
        btn_agregar_item = QPushButton("➕ Agregar ítem...")
        btn_quitar = QPushButton("✕ Quitar seleccionado")
        btn_agregar_bloque.clicked.connect(self._agregar_bloque)
        btn_agregar_item.clicked.connect(self._agregar_item)
        btn_quitar.clicked.connect(self._quitar_seleccionado)
        fila_edicion.addWidget(btn_agregar_bloque)
        fila_edicion.addWidget(btn_agregar_item)
        fila_edicion.addWidget(btn_quitar)
        layout.addLayout(fila_edicion)

        fila_guardar = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar...")
        btn_aplicar_ahora = QPushButton("▶ Aplicar AHORA en Ventana 1")
        btn_guardar.clicked.connect(self._guardar)
        btn_aplicar_ahora.clicked.connect(self._aplicar_ahora)
        fila_guardar.addWidget(btn_guardar)
        fila_guardar.addWidget(btn_aplicar_ahora)
        layout.addLayout(fila_guardar)

    def _cargar_categorias(self):
        try:
            self._categorias = self._cliente.listar_categorias()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))

    # ------------------------------------------------------------------
    def _refrescar_arbol(self):
        self.tree.clear()
        for i_bloque, bloque in enumerate(self._bloques):
            nodo = QTreeWidgetItem([f"{bloque.get('hora', '00:00:00')} - {bloque.get('titulo', '')}"])
            nodo.setData(0, Qt.ItemDataRole.UserRole, (i_bloque, None))
            fuente = nodo.font(0)
            fuente.setBold(True)
            nodo.setFont(0, fuente)
            for i_item, item in enumerate(bloque.get("items", [])):
                nodo_item = QTreeWidgetItem([self._texto_item(item)])
                nodo_item.setData(0, Qt.ItemDataRole.UserRole, (i_bloque, i_item))
                nodo.addChild(nodo_item)
            nodo.setExpanded(True)
            self.tree.addTopLevelItem(nodo)

    @staticmethod
    def _texto_item(item: dict) -> str:
        if item.get("es_comando"):
            return f"▶ {item.get('tipo_comando')}: {item.get('parametro_comando')}"
        if item.get("es_aleatorio"):
            categoria = " / ".join(item.get("categoria_aleatorio") or [])
            return f"🎲 Aleatorio: {categoria}"
        return f"{item.get('titulo', '')} ({item.get('duracion', '')})"

    # ------------------------------------------------------------------
    def _cargar_guardada(self):
        try:
            guardadas = self._cliente.programador_listar_guardadas()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not guardadas:
            QMessageBox.information(self, "Programador", "Todavía no hay ninguna programación guardada.")
            return
        opciones = [f"{g['nombre']} ({g['clave']})" for g in guardadas]
        elegido, ok = QInputDialog.getItem(self, "Cargar programación", "Elegí una:", opciones, editable=False)
        if not ok:
            return
        g = guardadas[opciones.index(elegido)]
        respuesta = self._cliente.programador_cargar_guardada(g["tipo"], g["clave"])
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo cargar."))
            return
        self._bloques = respuesta["datos"]["bloques"]
        self._refrescar_arbol()

    def _cargar_actual(self):
        try:
            self._bloques = self._cliente.programador_bloques_actuales()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        self._refrescar_arbol()

    def _nueva(self):
        if self._bloques:
            respuesta = QMessageBox.question(
                self, "Nueva programación", "Se va a vaciar el editor actual. ¿Confirmás?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        self._bloques = []
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    def _bloque_destino(self):
        item = self.tree.currentItem()
        if item is None:
            return len(self._bloques) - 1 if self._bloques else None
        indices = item.data(0, Qt.ItemDataRole.UserRole)
        return indices[0]

    def _agregar_bloque(self):
        dialogo = DialogoBloqueHorario(datetime.datetime.now().strftime("%H:%M:%S"), parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        self._bloques.append({"hora": datos["hora"], "titulo": datos["titulo"], "items": []})
        self._refrescar_arbol()

    def _quitar_seleccionado(self):
        item = self.tree.currentItem()
        if item is None:
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)
        if i_item is None:
            respuesta = QMessageBox.question(
                self, "Quitar bloque",
                "¿Quitar este bloque horario completo (con todos sus ítems)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
            del self._bloques[i_bloque]
        else:
            del self._bloques[i_bloque]["items"][i_item]
        self._refrescar_arbol()

    def _agregar_item(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Agregar ítem", "Primero creá un bloque horario.")
            return
        if not self._categorias:
            QMessageBox.warning(self, "Agregar ítem", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoElegirRegistroBiblioteca(self._cliente, self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if not registro:
            return
        item = {
            "titulo": registro["titulo"], "duracion": registro["duracion"], "codigo": registro["codigo"],
            "ruta": registro["ruta"], "punto_inicio_ms": 0, "punto_fin_ms": None, "ganancia_db": 0.0,
            "fecha_inicio": None, "fecha_fin": None,
        }
        self._bloques[i_bloque]["items"].append(item)
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    def _guardar(self):
        if not self._bloques:
            QMessageBox.information(self, "Guardar", "No hay nada para guardar todavía.")
            return
        dialogo = DialogoGuardarProgramacion(parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return
        respuesta = self._cliente.programador_guardar(
            datos["nombre"], self._bloques, datos["dias_semana"], datos["fecha_especifica"],
        )
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo guardar."))
            return
        QMessageBox.information(self, "Guardar", f"Programación \"{datos['nombre']}\" guardada.")

    def _aplicar_ahora(self):
        if not self._bloques:
            QMessageBox.information(self, "Aplicar ahora", "No hay nada para aplicar todavía.")
            return
        respuesta_confirm = QMessageBox.question(
            self, "Aplicar AHORA en Ventana 1",
            "Esto reemplaza YA lo que Ventana 1 tiene cargado, en vivo -- puede cortar lo\n"
            "que esté sonando. ¿Confirmás?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta_confirm != QMessageBox.StandardButton.Yes:
            return
        respuesta = self._cliente.programador_aplicar_ahora(self._bloques)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo aplicar."))
            return
        QMessageBox.information(self, "Aplicar ahora", "Aplicado en Ventana 1.")
