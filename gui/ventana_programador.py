"""
gui/ventana_programador.py
--------------------------------------------------------
Ventana "Programador": editor de programaciones horarias.

Pedido explícito: diferenciar con claridad TRES niveles de acción,
cada uno con su propio grupo de botones en la UI, para que nunca se
mezclen en la cabeza del operador:

1. LA PROGRAMACIÓN GUARDADA (el archivo entero: nombre + día/fecha +
   todos sus bloques) — Nueva / Cargar / Eliminar / Eliminar varias /
   Duplicar para otro día / Aplicar ahora en Ventana 1 (en vivo).
2. LOS BLOQUES HORARIOS (contenedores con hora propia) — Añadir
   Bloque Horario / Reemplazar (editar hora y título) / Quitar.
3. LOS ÍTEMS dentro de un bloque (las tandas) — Añadir Ítem (buscador
   de biblioteca a dos columnas) / Reemplazar (cambia el archivo sin
   mover la tanda de lugar) / Quitar. También se puede seguir
   arrastrando desde la Ventana 3 como antes.

"Reemplazar" y "Quitar" son las MISMAS dos acciones para bloques e
ítems (según qué tipo de nodo esté seleccionado) — a propósito, para
no duplicar botones: `_reemplazar_seleccionado`/`_quitar_seleccionados`
detectan el tipo de nodo y actúan en consecuencia.

El usuario arrastra archivos desde el Explorador (Ventana 3), o los
busca con el buscador de biblioteca (gui/dialogo_seleccionar_biblioteca.py
— mismo concepto a dos columnas que la Ventana 3, pero minimalista),
arma bloques horarios con su propio horario, y guarda el resultado
para:
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
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate, QTime, Signal

from gui.common_widgets import ArbolConDrop
from gui.styles import ROL_ANALISIS_AUDIO
from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
from gui.dialogo_editar_bloque import DialogoEditarBloque
from gui.dialogo_programaciones_guardadas import DialogoProgramacionesGuardadas
from gui.dialogo_duplicar_programacion import DialogoDuplicarProgramacion
from gui import estado_ui
from core.audio_engine import obtener_duracion_formateada
from config.settings import (
    guardar_programacion, listar_programaciones, obtener_programacion, eliminar_programacion,
    titulo_bloque_sin_prefijo_hora, DIAS_SEMANA_ETIQUETAS,
)

DIAS_SEMANA = DIAS_SEMANA_ETIQUETAS

ROL_HORA_BLOQUE = Qt.ItemDataRole.UserRole + 1
# Bug real corregido: antes se guardaba nodo.text(0) (el texto VISIBLE
# "hora - título") como si fuera el título puro — al recargar y volver
# a concatenar la hora, quedaba duplicada (y se acumulaba en cada
# ciclo de cargar/editar/guardar). Ahora el título puro se guarda acá
# aparte, separado del texto mostrado.
ROL_TITULO_BLOQUE = Qt.ItemDataRole.UserRole + 2

CLAVE_ULTIMA_CATEGORIA_PICKER = "programador_ultima_categoria"


class VentanaProgramador(QDialog):
    # Pedido explícito (punto d): "cargar esa programación en el
    # momento" — aplicar YA lo que está cargado en el editor a la
    # Ventana 1 en vivo. MainWindow conecta esta señal.
    solicitud_aplicar_ahora = Signal(list)

    def __init__(self, parent=None, ventana_explorador=None):
        super().__init__(parent)
        self.setWindowTitle("Programador de emisión")
        self.setMinimumSize(640, 780)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._ventana_explorador = ventana_explorador
        self._construir_ui()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        # ============================================================
        # Grupo 1: LA PROGRAMACIÓN GUARDADA (nivel "archivo completo")
        # ============================================================
        grupo_prog = QGroupBox("PROGRAMACIÓN GUARDADA")
        layout_prog = QVBoxLayout(grupo_prog)

        fila1 = QHBoxLayout()
        self.btn_nueva = QPushButton("🗎 Nueva")
        self.btn_nueva.clicked.connect(self._nueva_programacion)
        self.btn_cargar = QPushButton("📂 Cargar...")
        self.btn_cargar.clicked.connect(self._cargar_programacion_existente)
        self.btn_eliminar = QPushButton("🗑 Eliminar...")
        self.btn_eliminar.clicked.connect(self._eliminar_programacion_guardada)
        for boton in (self.btn_nueva, self.btn_cargar, self.btn_eliminar):
            fila1.addWidget(boton, 1)
        layout_prog.addLayout(fila1)

        fila2 = QHBoxLayout()
        self.btn_duplicar = QPushButton("⧉ Duplicar para otro día...")
        self.btn_duplicar.clicked.connect(self._duplicar_programacion)
        self.btn_eliminar_varias = QPushButton("🗑📑 Eliminar varias...")
        self.btn_eliminar_varias.clicked.connect(self._eliminar_varias_programaciones)
        for boton in (self.btn_duplicar, self.btn_eliminar_varias):
            fila2.addWidget(boton, 1)
        layout_prog.addLayout(fila2)

        self.btn_aplicar_ahora = QPushButton("▶ Aplicar AHORA en Ventana 1 (al aire)")
        self.btn_aplicar_ahora.setObjectName("btnStop")
        self.btn_aplicar_ahora.setToolTip(
            "Reemplaza YA MISMO los bloques de la Ventana 1 en vivo por lo que\n"
            "está cargado acá en el editor. Puede cortar lo que esté sonando."
        )
        self.btn_aplicar_ahora.clicked.connect(self._aplicar_ahora)
        layout_prog.addWidget(self.btn_aplicar_ahora)

        layout.addWidget(grupo_prog)

        # ============================================================
        # Grupo 2: BLOQUES HORARIOS Y SUS ÍTEMS (nivel estructura)
        # ============================================================
        grupo = QGroupBox("BLOQUES HORARIOS Y SUS ÍTEMS")
        layout_grupo = QVBoxLayout(grupo)

        barra_bloque = QHBoxLayout()
        self.time_nuevo_bloque = QTimeEdit(QTime.currentTime())
        self.txt_titulo_bloque = QLineEdit()
        self.txt_titulo_bloque.setPlaceholderText("Título del bloque (ej. Bloque Mediodía)")
        self.btn_agregar_bloque = QPushButton("＋ Añadir Bloque Horario")
        self.btn_agregar_bloque.clicked.connect(self._agregar_bloque)
        barra_bloque.addWidget(self.time_nuevo_bloque)
        barra_bloque.addWidget(self.txt_titulo_bloque)
        barra_bloque.addWidget(self.btn_agregar_bloque)
        layout_grupo.addLayout(barra_bloque)

        self.tree = ArbolConDrop()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.archivo_soltado.connect(self._on_archivo_soltado)
        layout_grupo.addWidget(self.tree)

        fila_items = QHBoxLayout()
        self.btn_agregar_item = QPushButton("➕ Añadir Ítem...")
        self.btn_agregar_item.setToolTip("Buscador de biblioteca a dos columnas (categorías / archivos).")
        self.btn_agregar_item.clicked.connect(self._abrir_picker_agregar_item)
        self.btn_reemplazar = QPushButton("🔁 Reemplazar seleccionado...")
        self.btn_reemplazar.setToolTip(
            "Bloque seleccionado: edita su hora/título.\n"
            "Ítem seleccionado: cambia el archivo sin mover su posición."
        )
        self.btn_reemplazar.clicked.connect(self._reemplazar_seleccionado)
        self.btn_quitar = QPushButton("✕ Quitar seleccionado(s)")
        self.btn_quitar.clicked.connect(self._quitar_seleccionados)
        for boton in (self.btn_agregar_item, self.btn_reemplazar, self.btn_quitar):
            fila_items.addWidget(boton, 1)
        layout_grupo.addLayout(fila_items)

        layout.addWidget(grupo)

        # ============================================================
        # Grupo 3: GUARDAR (nombre + fecha/día de la programación actual)
        # ============================================================
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

    # ==================================================================
    # Nivel 2a: BLOQUES horarios — Añadir / Reemplazar (editar) / Quitar
    # ==================================================================
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
        self.tree.setCurrentItem(nodo)
        self.txt_titulo_bloque.clear()

    def _editar_bloque(self, bloque):
        hora_actual = bloque.data(0, ROL_HORA_BLOQUE) or "00:00:00"
        titulo_actual = bloque.data(0, ROL_TITULO_BLOQUE) or titulo_bloque_sin_prefijo_hora(hora_actual, bloque.text(0))
        dialogo = DialogoEditarBloque(hora_actual, titulo_actual, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        hora_nueva = dialogo.hora()
        titulo_nuevo = dialogo.titulo()
        bloque.setData(0, ROL_HORA_BLOQUE, hora_nueva)
        bloque.setData(0, ROL_TITULO_BLOQUE, titulo_nuevo)
        bloque.setText(0, f"{hora_nueva} - {titulo_nuevo}")

    # ==================================================================
    # Nivel 2b: ÍTEMS (tandas) — Añadir / Reemplazar / Quitar
    # ==================================================================
    def _bloque_destino_actual(self):
        """Resuelve a qué bloque va un ítem nuevo: el bloque del nodo
        seleccionado (si es una tanda, su bloque padre; si es un
        bloque, él mismo), o el ÚLTIMO bloque del árbol si no hay nada
        útil seleccionado — mismo criterio de fallback que ya usa
        ArbolConDrop para el drag&drop."""
        item = self.tree.currentItem()
        if item is not None:
            return item if item.parent() is None else item.parent()
        if self.tree.topLevelItemCount() == 0:
            return None
        return self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)

    def _agregar_registro_a_bloque(self, bloque, registro: dict):
        hijo = QTreeWidgetItem([
            registro.get("titulo") or "Sin título", registro.get("duracion", ""), registro.get("codigo", "—"),
        ])
        hijo.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))
        hijo.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
        })
        bloque.addChild(hijo)
        bloque.setExpanded(True)
        return hijo

    def _on_archivo_soltado(self, ruta, item_destino):
        bloque = item_destino
        while bloque is not None and bloque.parent() is not None:
            bloque = bloque.parent()
        if bloque is None:
            if self.tree.topLevelItemCount() == 0:
                QMessageBox.information(self, "Programador", "Primero creá un bloque horario.")
                return
            bloque = self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)

        # Bug real corregido de paso: antes solo viajaba la ruta (sin
        # recorte de silencio ni nivelado) — mismo patrón que ya se
        # corrigió en Ventana 1/2 (ver CLAUDE.md). Si el Explorador no
        # está disponible o el archivo no está registrado, degrada a
        # los valores neutros de siempre.
        registro = None
        if self._ventana_explorador is not None:
            registro = self._ventana_explorador.buscar_registro_por_ruta(ruta)
        if not registro:
            registro = {
                "titulo": os.path.splitext(os.path.basename(ruta))[0],
                "duracion": obtener_duracion_formateada(ruta),
                "codigo": "—",
                "ruta": ruta,
            }
        self._agregar_registro_a_bloque(bloque, registro)

    def _abrir_picker_agregar_item(self):
        bloque = self._bloque_destino_actual()
        if bloque is None:
            QMessageBox.information(self, "Añadir Ítem", "Primero creá un bloque horario.")
            return
        if self._ventana_explorador is None:
            QMessageBox.warning(self, "Añadir Ítem", "No hay acceso al Explorador (Ventana 3) en esta sesión.")
            return

        dialogo = DialogoSeleccionarBiblioteca(
            self._ventana_explorador.tree_categorias, permitir_multiple=True,
            categoria_inicial=self._restaurar_ultima_categoria(),
            titulo="Añadir Ítem al bloque", parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        for registro in dialogo.registros_elegidos():
            self._agregar_registro_a_bloque(bloque, registro)
        self._guardar_ultima_categoria(dialogo.ruta_categoria_seleccionada())

    def _reemplazar_seleccionado(self):
        seleccionados = self.tree.selectedItems()
        if len(seleccionados) != 1:
            QMessageBox.information(
                self, "Reemplazar",
                "Seleccioná un solo bloque horario (para editar hora/título) o\n"
                "un solo ítem (para cambiar su archivo) — no varios a la vez.",
            )
            return

        item = seleccionados[0]
        if item.parent() is None:
            self._editar_bloque(item)
            return

        if self._ventana_explorador is None:
            QMessageBox.warning(self, "Reemplazar", "No hay acceso al Explorador (Ventana 3) en esta sesión.")
            return

        dialogo = DialogoSeleccionarBiblioteca(
            self._ventana_explorador.tree_categorias, permitir_multiple=False,
            categoria_inicial=self._restaurar_ultima_categoria(),
            titulo="Reemplazar ítem", parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.registro_elegido()
        if not registro:
            return

        item.setText(0, registro.get("titulo") or "Sin título")
        item.setText(1, registro.get("duracion", ""))
        item.setText(2, registro.get("codigo", "—"))
        item.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))
        item.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
        })
        self._guardar_ultima_categoria(dialogo.ruta_categoria_seleccionada())

    def _quitar_seleccionados(self):
        seleccionados = self.tree.selectedItems()
        if not seleccionados:
            return

        bloques_a_quitar = [it for it in seleccionados if it.parent() is None]
        items_a_quitar = [
            it for it in seleccionados if it.parent() is not None and it.parent() not in bloques_a_quitar
        ]
        cantidad = len(bloques_a_quitar) + len(items_a_quitar)
        if cantidad == 0:
            return

        respuesta = QMessageBox.question(
            self, "Quitar",
            f"¿Quitar {cantidad} elemento(s) seleccionado(s) del editor?\n"
            "(esto no borra nada de la biblioteca, solo del editor)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        for item in items_a_quitar:
            padre = item.parent()
            if padre is not None:
                padre.removeChild(item)
        for bloque in bloques_a_quitar:
            indice = self.tree.indexOfTopLevelItem(bloque)
            if indice >= 0:
                self.tree.takeTopLevelItem(indice)

    # ------------------------------------------------------------------
    # Recordar la última categoría navegada (pedido explícito, punto f)
    # ------------------------------------------------------------------
    def _guardar_ultima_categoria(self, ruta: list):
        if ruta:
            estado_ui.guardar_valor(CLAVE_ULTIMA_CATEGORIA_PICKER, ruta)

    def _restaurar_ultima_categoria(self) -> list:
        valor = estado_ui.restaurar_valor(CLAVE_ULTIMA_CATEGORIA_PICKER, [])
        if isinstance(valor, str):
            # QSettings devuelve un string suelto (no una lista de 1
            # elemento) cuando la ruta guardada tenía un solo nombre —
            # se normaliza acá para que el resto del código no tenga
            # que lidiar con ese caso especial.
            return [valor] if valor else []
        return list(valor) if valor else []

    # ==================================================================
    # Nivel 1: LA PROGRAMACIÓN GUARDADA — Nueva / Cargar / Eliminar /
    # Eliminar varias / Duplicar / Aplicar ahora
    # ==================================================================
    def _cargar_programacion_existente(self):
        disponibles = listar_programaciones()
        if not disponibles:
            QMessageBox.information(self, "Cargar", "Todavía no hay ninguna programación guardada.")
            return

        dialogo = DialogoProgramacionesGuardadas(
            disponibles, permitir_multiple=False, titulo="Cargar programación",
            texto_ayuda="Elegí una programación para editar:", parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        elegidos = dialogo.seleccionados()
        if not elegidos:
            return
        tipo, clave, _nombre = elegidos[0]

        contenido = obtener_programacion(tipo, clave)
        if not contenido:
            QMessageBox.warning(self, "Cargar", "No se pudo leer esa programación.")
            return

        self._nueva_programacion(confirmar=False)
        self.txt_nombre_programacion.setText(contenido.get("nombre", ""))

        for bloque in contenido.get("bloques", []):
            hora = bloque.get("hora", "00:00:00")
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
                hijo.setData(0, ROL_ANALISIS_AUDIO, {
                    "punto_inicio_ms": item.get("punto_inicio_ms") or 0,
                    "punto_fin_ms": item.get("punto_fin_ms"),
                    "ganancia_db": item.get("ganancia_db") or 0.0,
                })
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

    def _eliminar_programacion_guardada(self):
        disponibles = listar_programaciones()
        if not disponibles:
            QMessageBox.information(self, "Eliminar", "Todavía no hay ninguna programación guardada.")
            return

        dialogo = DialogoProgramacionesGuardadas(
            disponibles, permitir_multiple=False, titulo="Eliminar programación",
            texto_ayuda="Elegí la programación a eliminar:", parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        elegidos = dialogo.seleccionados()
        if not elegidos:
            return
        tipo, clave, nombre = elegidos[0]

        respuesta = QMessageBox.question(
            self, "Eliminar programación",
            f"¿Eliminar definitivamente \"{nombre}\"?\n\nEsto NO afecta lo que tengas cargado ahora en el editor.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        eliminar_programacion(tipo, clave)
        QMessageBox.information(self, "Eliminar", "Programación eliminada.")

    def _eliminar_varias_programaciones(self):
        disponibles = listar_programaciones()
        if not disponibles:
            QMessageBox.information(self, "Eliminar varias", "Todavía no hay ninguna programación guardada.")
            return

        dialogo = DialogoProgramacionesGuardadas(
            disponibles, permitir_multiple=True, titulo="Eliminar varias programaciones",
            texto_ayuda="Seleccioná (Ctrl/Shift) las programaciones viejas que querés borrar:", parent=self,
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        elegidos = dialogo.seleccionados()
        if not elegidos:
            return

        nombres = "\n".join(f"— {nombre}" for _tipo, _clave, nombre in elegidos)
        respuesta = QMessageBox.question(
            self, "Eliminar varias programaciones",
            f"¿Eliminar definitivamente estas {len(elegidos)} programación(es)?\n\n{nombres}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        for tipo, clave, _nombre in elegidos:
            eliminar_programacion(tipo, clave)
        QMessageBox.information(self, "Eliminar varias", f"{len(elegidos)} programación(es) eliminada(s).")

    def _duplicar_programacion(self):
        bloques = self._serializar_bloques()
        if not bloques:
            QMessageBox.warning(self, "Duplicar", "No hay bloques cargados en el editor para duplicar.")
            return

        nombre_actual = self.txt_nombre_programacion.text().strip()
        sugerido = f"{nombre_actual} (copia)" if nombre_actual else ""
        dialogo = DialogoDuplicarProgramacion(nombre_sugerido=sugerido, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        resultado = dialogo.resultado()
        if resultado is None:
            return

        nombre_nuevo, fecha_nueva, dias_nuevos = resultado
        guardar_programacion(nombre_nuevo, bloques, dias_semana=dias_nuevos, fecha_especifica=fecha_nueva)
        QMessageBox.information(
            self, "Duplicar",
            f"Se guardó \"{nombre_nuevo}\" como una programación nueva.\nLa original no se modificó.",
        )

    def _aplicar_ahora(self):
        bloques = self._serializar_bloques()
        if not bloques:
            QMessageBox.warning(self, "Aplicar ahora", "No hay bloques cargados en el editor para aplicar.")
            return

        respuesta = QMessageBox.question(
            self, "Aplicar AHORA en Ventana 1",
            "Esto reemplaza YA MISMO los bloques horarios de la Ventana 1 EN VIVO\n"
            "por lo que está cargado acá en el editor — puede cortar lo que esté\n"
            "sonando ahora mismo en Publicidad.\n\n¿Confirmás que querés aplicarlo ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.solicitud_aplicar_ahora.emit(bloques)

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
                analisis = hijo.data(0, ROL_ANALISIS_AUDIO) or {}
                items.append({
                    "titulo": hijo.text(0),
                    "duracion": hijo.text(1),
                    "codigo": hijo.text(2),
                    "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
                    "punto_inicio_ms": analisis.get("punto_inicio_ms") or 0,
                    "punto_fin_ms": analisis.get("punto_fin_ms"),
                    "ganancia_db": analisis.get("ganancia_db") or 0.0,
                })
            bloques.append({"hora": hora, "titulo": titulo, "items": items})
        return bloques
