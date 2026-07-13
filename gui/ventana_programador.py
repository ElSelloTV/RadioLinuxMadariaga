"""
gui/ventana_programador.py
--------------------------------------------------------
Ventana "Programador": editor de programaciones horarias.
Misma estructura visual que la Ventana 1 (árbol de bloques),
pero editable: el usuario arrastra archivos desde el Explorador
(Ventana 3), arma bloques horarios con su propio horario, y
guarda el resultado para:
  - una fecha específica (ej. 2026-07-15), o
  - uno o varios días de la semana (patrón general que se repite).

Regla de superposición (pedida explícitamente): al resolver la
programación de un día, una fecha específica SIEMPRE prevalece
sobre el patrón general de ese día de la semana. Ver
config/settings.py:resolver_programacion_del_dia().
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidgetItem,
    QPushButton, QLabel, QCheckBox, QDateEdit, QTimeEdit, QLineEdit,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, QDate, QTime

from gui.common_widgets import ArbolConDrop
from core.audio_engine import obtener_duracion_formateada
from config.settings import (
    guardar_programacion, listar_programaciones, obtener_programacion, titulo_bloque_sin_prefijo_hora,
)

DIAS_SEMANA = [
    ("lunes", "L"), ("martes", "M"), ("miercoles", "X"),
    ("jueves", "J"), ("viernes", "V"), ("sabado", "S"), ("domingo", "D"),
]

ROL_HORA_BLOQUE = Qt.ItemDataRole.UserRole + 1
# Bug real corregido: antes se guardaba nodo.text(0) (el texto VISIBLE
# "hora - título") como si fuera el título puro — al recargar y volver
# a concatenar la hora, quedaba duplicada (y se acumulaba en cada
# ciclo de cargar/editar/guardar). Ahora el título puro se guarda acá
# aparte, separado del texto mostrado.
ROL_TITULO_BLOQUE = Qt.ItemDataRole.UserRole + 2


class VentanaProgramador(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Programador de emisión")
        self.setMinimumSize(560, 660)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._construir_ui()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        # --- Bloques horarios ---
        grupo = QGroupBox("BLOQUES HORARIOS DE LA PROGRAMACIÓN")
        layout_grupo = QVBoxLayout(grupo)

        barra_carga = QHBoxLayout()
        self.btn_cargar = QPushButton("📂 Cargar programación existente...")
        self.btn_cargar.clicked.connect(self._cargar_programacion_existente)
        self.btn_nueva = QPushButton("🗎 Nueva (vaciar)")
        self.btn_nueva.clicked.connect(self._nueva_programacion)
        barra_carga.addWidget(self.btn_cargar)
        barra_carga.addWidget(self.btn_nueva)
        layout_grupo.addLayout(barra_carga)

        barra_bloque = QHBoxLayout()
        self.time_nuevo_bloque = QTimeEdit(QTime.currentTime())
        self.txt_titulo_bloque = QLineEdit()
        self.txt_titulo_bloque.setPlaceholderText("Título del bloque (ej. Bloque Mediodía)")
        self.btn_agregar_bloque = QPushButton("＋ Bloque horario")
        self.btn_agregar_bloque.clicked.connect(self._agregar_bloque)
        barra_bloque.addWidget(self.time_nuevo_bloque)
        barra_bloque.addWidget(self.txt_titulo_bloque)
        barra_bloque.addWidget(self.btn_agregar_bloque)
        layout_grupo.addLayout(barra_bloque)

        self.tree = ArbolConDrop()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.archivo_soltado.connect(self._on_archivo_soltado)
        layout_grupo.addWidget(self.tree)

        self.btn_eliminar_item = QPushButton("✕ Eliminar seleccionado")
        self.btn_eliminar_item.clicked.connect(self._eliminar_seleccionado)
        layout_grupo.addWidget(self.btn_eliminar_item)

        layout.addWidget(grupo)

        # --- Guardado ---
        grupo_guardar = QGroupBox("GUARDAR PROGRAMACIÓN")
        layout_guardar = QVBoxLayout(grupo_guardar)

        self.txt_nombre_programacion = QLineEdit()
        self.txt_nombre_programacion.setPlaceholderText("Nombre de la programación")
        layout_guardar.addWidget(self.txt_nombre_programacion)

        fila_fecha = QHBoxLayout()
        self.chk_fecha_especifica = QCheckBox("Fecha específica:")
        self.date_especifica = QDateEdit(QDate.currentDate())
        self.date_especifica.setCalendarPopup(True)
        self.date_especifica.setEnabled(False)
        self.chk_fecha_especifica.toggled.connect(self._on_toggle_fecha_especifica)
        fila_fecha.addWidget(self.chk_fecha_especifica)
        fila_fecha.addWidget(self.date_especifica)
        layout_guardar.addLayout(fila_fecha)

        layout_guardar.addWidget(QLabel("...o días de la semana (patrón general, se repite cada semana):"))
        fila_dias = QHBoxLayout()
        self.checks_dias = {}
        for clave, etiqueta in DIAS_SEMANA:
            chk = QCheckBox(etiqueta)
            self.checks_dias[clave] = chk
            fila_dias.addWidget(chk)
        layout_guardar.addLayout(fila_dias)

        lbl_nota = QLabel(
            "Nota: si guardás para una fecha específica, esa programación\n"
            "reemplaza al patrón semanal general SOLO para ese día puntual."
        )
        lbl_nota.setObjectName("lblTituloBloqueActivo")
        layout_guardar.addWidget(lbl_nota)

        self.btn_guardar = QPushButton("💾 Guardar programación")
        self.btn_guardar.setObjectName("btnPlay")
        self.btn_guardar.clicked.connect(self._guardar)
        layout_guardar.addWidget(self.btn_guardar)

        layout.addWidget(grupo_guardar)

    # ------------------------------------------------------------------
    def _on_toggle_fecha_especifica(self, activo: bool):
        self.date_especifica.setEnabled(activo)
        for chk in self.checks_dias.values():
            chk.setEnabled(not activo)

    def _agregar_bloque(self):
        titulo = self.txt_titulo_bloque.text().strip() or "Bloque sin título"
        hora = self.time_nuevo_bloque.time().toString("HH:mm:ss")
        nodo = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
        fuente = nodo.font(0)
        fuente.setBold(True)
        nodo.setFont(0, fuente)
        nodo.setData(0, ROL_HORA_BLOQUE, hora)
        nodo.setData(0, ROL_TITULO_BLOQUE, titulo)
        self.tree.addTopLevelItem(nodo)
        nodo.setExpanded(True)
        self.txt_titulo_bloque.clear()

    def _on_archivo_soltado(self, ruta, item_destino):
        bloque = item_destino
        while bloque is not None and bloque.parent() is not None:
            bloque = bloque.parent()
        if bloque is None:
            if self.tree.topLevelItemCount() == 0:
                QMessageBox.information(self, "Programador", "Primero creá un bloque horario.")
                return
            bloque = self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)

        titulo = os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        hijo = QTreeWidgetItem([titulo, duracion, "—"])
        hijo.setData(0, Qt.ItemDataRole.UserRole, ruta)
        bloque.addChild(hijo)
        bloque.setExpanded(True)

    def _eliminar_seleccionado(self):
        item = self.tree.currentItem()
        if item is None:
            return
        padre = item.parent()
        if padre:
            padre.removeChild(item)
        else:
            indice = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(indice)

    # ------------------------------------------------------------------
    # Cargar una programación existente para editarla
    # ------------------------------------------------------------------
    def _cargar_programacion_existente(self):
        disponibles = listar_programaciones()
        if not disponibles:
            QMessageBox.information(self, "Cargar", "Todavía no hay ninguna programación guardada.")
            return

        etiquetas = []
        for tipo, clave, nombre in disponibles:
            prefijo = f"Día: {clave}" if tipo == "dia" else f"Fecha: {clave}"
            etiquetas.append(f"{prefijo} — {nombre}")

        etiqueta_elegida, ok = QInputDialog.getItem(
            self, "Cargar programación", "Elegí una programación para editar:",
            etiquetas, 0, False,
        )
        if not ok:
            return

        indice = etiquetas.index(etiqueta_elegida)
        tipo, clave, _nombre = disponibles[indice]
        contenido = obtener_programacion(tipo, clave)
        if not contenido:
            QMessageBox.warning(self, "Cargar", "No se pudo leer esa programación.")
            return

        self._nueva_programacion(confirmar=False)
        self.txt_nombre_programacion.setText(contenido.get("nombre", ""))

        for bloque in contenido.get("bloques", []):
            hora = bloque.get("hora", "00:00:00")
            # titulo_bloque_sin_prefijo_hora "autocura" cualquier
            # título que ya haya quedado duplicado por el bug de
            # rondas anteriores (ver nota en config/settings.py).
            titulo = titulo_bloque_sin_prefijo_hora(hora, bloque.get("titulo", ""))
            nodo = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
            fuente = nodo.font(0)
            fuente.setBold(True)
            nodo.setFont(0, fuente)
            nodo.setData(0, ROL_HORA_BLOQUE, hora)
            nodo.setData(0, ROL_TITULO_BLOQUE, titulo)
            self.tree.addTopLevelItem(nodo)
            for item in bloque.get("items", []):
                hijo = QTreeWidgetItem([item.get("titulo", ""), item.get("duracion", ""), item.get("codigo", "—")])
                hijo.setData(0, Qt.ItemDataRole.UserRole, item.get("ruta", ""))
                nodo.addChild(hijo)
            nodo.setExpanded(True)

        if tipo == "fecha":
            self.chk_fecha_especifica.setChecked(True)
            self.date_especifica.setDate(QDate.fromString(clave, "yyyy-MM-dd"))
        else:
            self.chk_fecha_especifica.setChecked(False)
            for dia_clave, chk in self.checks_dias.items():
                chk.setChecked(dia_clave == clave)

    def _nueva_programacion(self, confirmar: bool = True):
        if confirmar and self.tree.topLevelItemCount() > 0:
            respuesta = QMessageBox.question(
                self, "Nueva programación",
                "¿Vaciar el editor? Se perderán los cambios no guardados.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        self.tree.clear()
        self.txt_nombre_programacion.clear()
        self.chk_fecha_especifica.setChecked(False)
        for chk in self.checks_dias.values():
            chk.setChecked(False)

    # ------------------------------------------------------------------
    def _guardar(self):
        nombre = self.txt_nombre_programacion.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Guardar", "Ingresá un nombre para la programación.")
            return

        fecha_especifica = None
        dias_seleccionados = []
        if self.chk_fecha_especifica.isChecked():
            fecha_especifica = self.date_especifica.date().toString("yyyy-MM-dd")
        else:
            dias_seleccionados = [clave for clave, chk in self.checks_dias.items() if chk.isChecked()]

        if not fecha_especifica and not dias_seleccionados:
            QMessageBox.warning(self, "Guardar", "Elegí una fecha específica o al menos un día de la semana.")
            return

        bloques = self._serializar_bloques()
        if not bloques:
            QMessageBox.warning(self, "Guardar", "No hay bloques horarios para guardar.")
            return

        guardar_programacion(nombre, bloques, dias_semana=dias_seleccionados, fecha_especifica=fecha_especifica)
        QMessageBox.information(self, "Guardar", "Programación guardada correctamente.")

    def _serializar_bloques(self):
        bloques = []
        for i in range(self.tree.topLevelItemCount()):
            nodo = self.tree.topLevelItem(i)
            hora = nodo.data(0, ROL_HORA_BLOQUE) or "00:00:00"
            # Título PURO desde su rol propio (nunca nodo.text(0),
            # que incluye la hora concatenada — bug real corregido,
            # ver nota en config/settings.py). Si por algún motivo
            # faltara el rol (dato viejo), se autocura peor.
            titulo = nodo.data(0, ROL_TITULO_BLOQUE)
            if not titulo:
                titulo = titulo_bloque_sin_prefijo_hora(hora, nodo.text(0))
            items = []
            for j in range(nodo.childCount()):
                hijo = nodo.child(j)
                items.append({
                    "titulo": hijo.text(0),
                    "duracion": hijo.text(1),
                    "codigo": hijo.text(2),
                    "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
                })
            bloques.append({"hora": hora, "titulo": titulo, "items": items})
        return bloques
