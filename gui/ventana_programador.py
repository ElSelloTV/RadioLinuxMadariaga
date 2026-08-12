"""
gui/ventana_programador.py
--------------------------------------------------------
Ventana "Programador": editor de programaciones horarias.

Rediseño (pedido explícito: "es confusa" — mismos comandos de
siempre, layout reorganizado): TRES niveles de acción, cada uno con
su propio `QGroupBox`, para que nunca se mezclen en la cabeza del
operador:

1. LA PROGRAMACIÓN GUARDADA (el archivo entero: nombre + día/fecha +
   todos sus bloques) — las 5 acciones de "archivo" (Nueva / Cargar /
   Eliminar / Eliminar varias / Duplicar para otro día) viven
   agrupadas detrás de UN solo botón desplegable ("📁 Programación",
   mismo patrón ya usado en el toolbar principal — ver
   `gui/main_window.py`, botón "⚙ Configuración") en vez de 6 botones
   sueltos en una fila — deja "▶ Aplicar Ahora en Ventana 1" como la
   ÚNICA acción realmente destacada acá, separada y bien visible (es
   la que corta el aire).
2. LOS BLOQUES HORARIOS (contenedores con hora propia) — Añadir
   Bloque Horario / Reemplazar (editar hora y título) / Quitar. Se
   pueden reordenar arrastrando (`ArbolProgramadorConDrop`, sin
   cambios) tanto dentro de su bloque como hacia otro bloque distinto.
3. LOS ÍTEMS dentro de un bloque (las tandas) — Añadir Ítem (buscador
   de biblioteca a dos columnas) / Reemplazar Item (cambia el archivo
   sin mover la tanda de lugar) / Quitar Item, con una fila propia y
   SEPARADA para "insertar ítem especial" (Comando FMT / Comando HTH /
   Ítem Aleatorio — no son archivos de la biblioteca, se resuelven
   recién al reproducirse). También se puede seguir arrastrando desde
   la Ventana 3 como antes.

"Reemplazar Item" y "Quitar Item" son las MISMAS dos acciones para
bloques e ítems (según qué tipo de nodo esté seleccionado) — a
propósito, para no duplicar botones: `_reemplazar_seleccionado`/
`_quitar_seleccionados` detectan el tipo de nodo y actúan en
consecuencia.

Pre-escucha (pedido explícito, "si es posible, una pre-escucha por la
salida auxiliar"): "▶ Previo"/"⏹ Detener" reproducen el ítem
seleccionado por la salida de "Salida Preescucha" configurada
(Configuración → Audio) — NUNCA por la Master que va al aire, mismo
criterio ya establecido en toda la app (▶ Previo de Ventana 3,
`DialogoVincularArchivo`, etc.).

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

Aplicar automáticamente al guardar "lo de hoy" (pedido explícito): si
la programación que se está guardando corresponde a HOY (fecha
específica == hoy, o el día de semana de hoy está entre los
tildados), `_guardar()` ofrece de una la MISMA acción que
"▶ Aplicar Ahora" — ver `_corresponde_a_hoy()`. Sigue pidiendo
confirmación (puede cortar el aire), nunca se aplica en silencio.
--------------------------------------------------------
"""

import os
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidgetItem,
    QPushButton, QLabel, QCheckBox, QDateEdit, QTimeEdit, QLineEdit,
    QMessageBox, QAbstractItemView, QMenu, QToolButton,
)
from PySide6.QtCore import Qt, QDate, QTime, Signal
from PySide6.QtGui import QBrush, QColor

from gui.common_widgets import ArbolProgramadorConDrop
from gui.styles import (
    ROL_ANALISIS_AUDIO, ROL_VIGENCIA, ROL_ES_COMANDO, ROL_TIPO_COMANDO, ROL_PARAMETRO_COMANDO, COLOR_COMANDO,
    ROL_ES_ALEATORIO, ROL_CATEGORIA_ALEATORIO, ROL_RECURSIVO_ALEATORIO, COLOR_ALEATORIO,
)
from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
from gui.dialogo_editar_bloque import DialogoEditarBloque
from gui.dialogo_programaciones_guardadas import DialogoProgramacionesGuardadas
from gui.dialogo_duplicar_programacion import DialogoDuplicarProgramacion
from gui.dialogo_insertar_comando_fmt import DialogoInsertarComandoFMT
from gui.dialogo_insertar_comando_hth import DialogoInsertarComandoHTH
from gui.dialogo_insertar_item_aleatorio import DialogoInsertarItemAleatorio
from gui import estado_ui
from core.audio_engine import obtener_duracion_formateada, MotorAudio
from config.settings import (
    guardar_programacion, listar_programaciones, obtener_programacion, eliminar_programacion,
    titulo_bloque_sin_prefijo_hora, DIAS_SEMANA_ETIQUETAS, NOMBRES_DIAS_SEMANA, cargar_configuracion,
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
        self.setMinimumSize(780, 620)
        self.setWindowModality(Qt.WindowModality.NonModal)
        # Bug real corregido — "no maximiza ni minimiza": un QDialog NO
        # pide esos botones de la barra de título por defecto (a
        # diferencia de QMainWindow), quedaba solo el de cerrar.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self._ventana_explorador = ventana_explorador
        # Copiar/Pegar (pedido explícito, menú contextual): lista de
        # dicts serializados con el mismo formato que _serializar_item()
        # / los ítems de una programación guardada — así "Pegar" puede
        # reusar _agregar_registro_a_bloque()/_agregar_comando_a_bloque()
        # tal cual, sin un tipo de dato paralelo.
        self._portapapeles = []

        # Pre-escucha (pedido explícito, "una pre-escucha por la
        # salida auxiliar"): motor DEDICADO, SIEMPRE por la salida de
        # "Salida Preescucha" configurada (aplicar_procesador=False,
        # nunca la Master que va al aire) — mismo criterio que el
        # ▶ Previo de Ventana 3 / DialogoVincularArchivo.
        audio_cfg = cargar_configuracion().get("audio", {})
        id_dispositivo_preescucha = (
            audio_cfg.get("dispositivo_preescucha")
            if audio_cfg.get("dispositivo_preescucha") not in (None, "default")
            else None
        )
        self._motor_previo = MotorAudio(id_dispositivo_preescucha, aplicar_procesador=False)
        self._motor_previo.finalizo_item.connect(self._detener_previo)

        self._construir_ui()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        # ============================================================
        # Grupo 1: LA PROGRAMACIÓN GUARDADA (nivel "archivo completo")
        # Rediseño: las 5 acciones de "archivo" quedan agrupadas
        # detrás de un solo botón desplegable — "▶ Aplicar Ahora"
        # queda como la única acción realmente destacada del grupo.
        # ============================================================
        grupo_prog = QGroupBox("PROGRAMACIÓN GUARDADA")
        fila_prog = QHBoxLayout(grupo_prog)

        self.boton_archivo = QToolButton()
        self.boton_archivo.setText("📁 Programación")
        self.boton_archivo.setToolTip("Nueva / Cargar / Eliminar / Eliminar varias / Duplicar para otro día")
        self.boton_archivo.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_archivo = QMenu(self.boton_archivo)
        self.accion_nueva = self.menu_archivo.addAction("🗎 Nueva")
        self.accion_nueva.setToolTip("Vacía el editor y arranca con una plantilla de 24 bloques (00 a 23hs).")
        self.accion_nueva.triggered.connect(lambda: self._nueva_programacion(confirmar=True, con_plantilla=True))
        self.menu_archivo.addSeparator()
        self.accion_cargar = self.menu_archivo.addAction("📂 Cargar...")
        self.accion_cargar.triggered.connect(self._cargar_programacion_existente)
        self.menu_archivo.addSeparator()
        self.accion_eliminar = self.menu_archivo.addAction("🗑 Eliminar...")
        self.accion_eliminar.triggered.connect(self._eliminar_programacion_guardada)
        self.accion_eliminar_varias = self.menu_archivo.addAction("🗑📑 Eliminar varias...")
        self.accion_eliminar_varias.triggered.connect(self._eliminar_varias_programaciones)
        self.menu_archivo.addSeparator()
        self.accion_duplicar = self.menu_archivo.addAction("⧉ Duplicar para otro día...")
        self.accion_duplicar.setToolTip("Guarda una copia de lo cargado acá bajo un nombre y día/fecha nuevos.")
        self.accion_duplicar.triggered.connect(self._duplicar_programacion)
        self.boton_archivo.setMenu(self.menu_archivo)
        fila_prog.addWidget(self.boton_archivo)

        fila_prog.addStretch()

        self.btn_aplicar_ahora = QPushButton("▶ Aplicar Ahora en Ventana 1")
        self.btn_aplicar_ahora.setObjectName("btnStop")
        self.btn_aplicar_ahora.setToolTip(
            "Aplicar AHORA en Ventana 1 (al aire): reemplaza YA MISMO los bloques\n"
            "de la Ventana 1 en vivo por lo que está cargado acá en el editor.\n"
            "Puede cortar lo que esté sonando."
        )
        self.btn_aplicar_ahora.clicked.connect(self._aplicar_ahora)
        fila_prog.addWidget(self.btn_aplicar_ahora)

        layout.addWidget(grupo_prog)

        # ============================================================
        # Grupo 2: BLOQUES HORARIOS Y SUS ÍTEMS (nivel estructura)
        # Rediseño: cada fila de botones lleva su propio subtítulo
        # (estilo atenuado, mismo que la nota de abajo) para separar
        # visualmente "esto arma un bloque" / "esto actúa sobre lo
        # seleccionado" / "esto inserta algo especial (no un archivo)".
        # ============================================================
        grupo = QGroupBox("BLOQUES HORARIOS Y SUS ÍTEMS")
        layout_grupo = QVBoxLayout(grupo)

        layout_grupo.addWidget(self._crear_subtitulo("Nuevo bloque horario:"))
        barra_bloque = QHBoxLayout()
        self.time_nuevo_bloque = QTimeEdit(QTime.currentTime())
        self.txt_titulo_bloque = QLineEdit()
        self.txt_titulo_bloque.setPlaceholderText("Título del bloque (ej. Bloque Mediodía)")
        self.btn_agregar_bloque = QPushButton("＋ Añadir Bloque Horario")
        self.btn_agregar_bloque.clicked.connect(self._agregar_bloque)
        barra_bloque.addWidget(self.time_nuevo_bloque)
        barra_bloque.addWidget(self.txt_titulo_bloque, 1)
        barra_bloque.addWidget(self.btn_agregar_bloque)
        layout_grupo.addLayout(barra_bloque)

        self.tree = ArbolProgramadorConDrop()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Título", "Duración", "Código"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.archivo_soltado.connect(self._on_archivo_soltado)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        # Cambiar de selección corta cualquier pre-escucha en curso —
        # mismo criterio que el ▶ Previo de Ventana 3.
        self.tree.itemSelectionChanged.connect(self._detener_previo)
        layout_grupo.addWidget(self.tree, 1)

        layout_grupo.addWidget(self._crear_subtitulo(
            "Ítem seleccionado en el árbol (bloque -> edita hora/título; ítem -> cambia el archivo):"
        ))
        fila_items = QHBoxLayout()
        self.btn_agregar_item = QPushButton("➕ Añadir Ítem...")
        self.btn_agregar_item.setToolTip("Buscador de biblioteca a dos columnas (categorías / archivos).")
        self.btn_agregar_item.clicked.connect(self._abrir_picker_agregar_item)
        self.btn_reemplazar = QPushButton("🔁 Reemplazar Item")
        self.btn_reemplazar.setToolTip(
            "Bloque seleccionado: edita su hora/título.\n"
            "Ítem seleccionado: cambia el archivo sin mover su posición."
        )
        self.btn_reemplazar.clicked.connect(self._reemplazar_seleccionado)
        self.btn_quitar = QPushButton("✕ Quitar Item")
        self.btn_quitar.setToolTip("Quita del editor lo seleccionado (bloques y/o ítems) — no borra nada de la biblioteca.")
        self.btn_quitar.clicked.connect(self._quitar_seleccionados)
        for boton in (self.btn_agregar_item, self.btn_reemplazar, self.btn_quitar):
            fila_items.addWidget(boton, 1)

        fila_items.addSpacing(12)
        self.btn_previo = QPushButton("▶ Previo")
        self.btn_previo.setToolTip("Pre-escuchar el ítem seleccionado por la salida de Preescucha (nunca la Master al aire).")
        self.btn_previo.clicked.connect(self._reproducir_previo)
        self.btn_detener_previo = QPushButton("⏹ Detener")
        self.btn_detener_previo.clicked.connect(self._detener_previo)
        fila_items.addWidget(self.btn_previo)
        fila_items.addWidget(self.btn_detener_previo)
        layout_grupo.addLayout(fila_items)

        layout_grupo.addWidget(self._crear_subtitulo(
            "Insertar ítem especial en el bloque (no es un archivo de la biblioteca):"
        ))
        fila_especiales = QHBoxLayout()
        self.btn_insertar_fmt = QPushButton("▶ Comando FMT...")
        self.btn_insertar_fmt.setToolTip(
            "Al pasar la reproducción por este ítem, dispara la generación\n"
            "continua de música en Emisión según un formato del Musicalizador Avanzado."
        )
        self.btn_insertar_fmt.clicked.connect(self._insertar_comando_fmt)
        self.btn_insertar_hth = QPushButton("▶ Comando HTH...")
        self.btn_insertar_hth.setToolTip(
            "Al pasar la reproducción por este ítem, anuncia hora/temperatura/\n"
            "humedad concatenando los clips de voz del género \"HTH\"."
        )
        self.btn_insertar_hth.clicked.connect(self._insertar_comando_hth)
        self.btn_insertar_aleatorio = QPushButton("🎲 Ítem Aleatorio...")
        self.btn_insertar_aleatorio.setToolTip(
            "Elige un archivo al azar de una categoría/subcategoría CADA VEZ que\n"
            "le toca sonar (nunca el mismo fijo) — para darle dinamismo, ej. separadores."
        )
        self.btn_insertar_aleatorio.clicked.connect(self._insertar_item_aleatorio)
        for boton in (self.btn_insertar_fmt, self.btn_insertar_hth, self.btn_insertar_aleatorio):
            fila_especiales.addWidget(boton, 1)
        layout_grupo.addLayout(fila_especiales)

        layout.addWidget(grupo, 1)

        # ============================================================
        # Grupo 3: GUARDAR (nombre + fecha/día de la programación actual)
        # ============================================================
        grupo_guardar = QGroupBox("GUARDAR PROGRAMACIÓN")
        layout_guardar = QVBoxLayout(grupo_guardar)

        fila_nombre = QHBoxLayout()
        self.txt_nombre_programacion = QLineEdit()
        self.txt_nombre_programacion.setPlaceholderText("Nombre de la programación")
        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setObjectName("btnPlay")
        self.btn_guardar.clicked.connect(self._guardar)
        fila_nombre.addWidget(self.txt_nombre_programacion, 1)
        fila_nombre.addWidget(self.btn_guardar)
        layout_guardar.addLayout(fila_nombre)

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
            "Nota: una fecha específica prevalece sobre el patrón semanal de ese día. "
            "Si lo que guardás corresponde a HOY, se ofrece aplicarlo ya en Ventana 1."
        )
        lbl_nota.setObjectName("lblTituloBloqueActivo")
        lbl_nota.setWordWrap(True)
        layout_guardar.addWidget(lbl_nota)

        layout.addWidget(grupo_guardar)

    @staticmethod
    def _crear_subtitulo(texto: str) -> QLabel:
        """Etiqueta chica y atenuada usada como separador visual entre
        las distintas filas de botones del Grupo 2 — mismo estilo ya
        establecido en la app (`lblTituloBloqueActivo`, itálica y en
        el color de texto secundario) para no sumar peso visual extra."""
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("lblTituloBloqueActivo")
        return etiqueta

    # ------------------------------------------------------------------
    def _reproducir_previo(self):
        """Pre-escucha (pedido explícito, "por la salida auxiliar"):
        SIEMPRE por la salida de Preescucha configurada, nunca la
        Master que va al aire — solo tiene sentido sobre un ÍTEM real
        (tanda con archivo), nunca sobre un bloque, un Comando o un
        Ítem Aleatorio (no tienen un archivo fijo)."""
        item = self.tree.currentItem()
        if item is None or item.parent() is None:
            QMessageBox.information(self, "Previo", "Seleccioná un ítem (no un bloque) para escuchar.")
            return
        if item.data(0, ROL_ES_COMANDO) or item.data(0, ROL_ES_ALEATORIO):
            QMessageBox.information(
                self, "Previo", "Este ítem no tiene un archivo fijo para pre-escuchar (Comando o Aleatorio).",
            )
            return
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        if not ruta or not os.path.exists(ruta):
            QMessageBox.warning(self, "Previo", "El archivo de este ítem no existe (o no está vinculado).")
            return
        analisis = item.data(0, ROL_ANALISIS_AUDIO) or {}
        self._motor_previo.reproducir(
            ruta,
            punto_inicio_ms=analisis.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis.get("punto_fin_ms"),
            ganancia_db=analisis.get("ganancia_db") or 0.0,
        )

    def _detener_previo(self):
        self._motor_previo.detener()

    def closeEvent(self, evento):
        self._detener_previo()
        super().closeEvent(evento)

    def reject(self):
        self._detener_previo()
        super().reject()

    # ------------------------------------------------------------------
    def _on_toggle_fecha_especifica(self, activo: bool):
        self.date_especifica.setEnabled(activo)
        for chk in self.checks_dias.values():
            chk.setEnabled(not activo)

    # ==================================================================
    # Nivel 2a: BLOQUES horarios — Añadir / Reemplazar (editar) / Quitar
    # ==================================================================
    def _agregar_bloque(self):
        # Pedido explícito: si el operador no tipea un título, el
        # default ya no dice "Bloque" — dice "TANDA - Rotativa".
        titulo = self.txt_titulo_bloque.text().strip() or "TANDA - Rotativa"
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

    def _indice_insercion_actual(self, bloque):
        """Si hay un ÍTEM (no un bloque) seleccionado DENTRO de
        `bloque`, la próxima inserción va justo DESPUÉS de él —
        pedido explícito: "que lo haga en el lugar donde haya
        seleccionado y no necesariamente al final". Sin una selección
        útil, sigue agregando al final (`None`, comportamiento de
        siempre)."""
        item = self.tree.currentItem()
        if item is not None and item.parent() is bloque:
            return bloque.indexOfChild(item) + 1
        return None

    def _agregar_registro_a_bloque(self, bloque, registro: dict, indice: int = None):
        hijo = QTreeWidgetItem([
            registro.get("titulo") or "Sin título", registro.get("duracion", ""), registro.get("codigo", "—"),
        ])
        hijo.setData(0, Qt.ItemDataRole.UserRole, registro.get("ruta", ""))
        hijo.setData(0, ROL_ANALISIS_AUDIO, {
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
        })
        hijo.setData(0, ROL_VIGENCIA, {
            "fecha_inicio": registro.get("fecha_inicio"), "fecha_fin": registro.get("fecha_fin"),
        })
        if indice is None:
            bloque.addChild(hijo)
        else:
            bloque.insertChild(indice, hijo)
        bloque.setExpanded(True)
        return hijo

    def _agregar_comando_a_bloque(self, bloque, tipo_comando: str, parametro: str, indice: int = None):
        """Comando FMT (pedido explícito, encadenado con el
        Musicalizador Avanzado) — mismo concepto que
        VentanaPublicidad.agregar_comando(), acá en el editor del
        Programador."""
        hijo = QTreeWidgetItem([f"▶ {tipo_comando}: {parametro}", "—", "—"])
        hijo.setData(0, Qt.ItemDataRole.UserRole, "")
        hijo.setData(0, ROL_ES_COMANDO, True)
        hijo.setData(0, ROL_TIPO_COMANDO, tipo_comando)
        hijo.setData(0, ROL_PARAMETRO_COMANDO, parametro)
        fondo = QBrush(QColor(COLOR_COMANDO))
        for columna in range(3):
            hijo.setBackground(columna, fondo)
            hijo.setForeground(columna, QBrush(QColor("white")))
        if indice is None:
            bloque.addChild(hijo)
        else:
            bloque.insertChild(indice, hijo)
        bloque.setExpanded(True)
        return hijo

    def _agregar_item_aleatorio_a_bloque(self, bloque, categoria: list, recursivo: bool, indice: int = None):
        """Ítem ALEATORIO (pedido explícito: "agregar un ítem aleatorio
        de alguna categoría o sub-categoría, para darle dinamismo") —
        mismo concepto que VentanaPublicidad.agregar_item_aleatorio(),
        acá en el editor del Programador."""
        titulo_categoria = " / ".join(categoria) if categoria else "(categoría no encontrada)"
        hijo = QTreeWidgetItem([f"🎲 Aleatorio: {titulo_categoria}", "—", "—"])
        hijo.setData(0, Qt.ItemDataRole.UserRole, "")
        hijo.setData(0, ROL_ES_ALEATORIO, True)
        hijo.setData(0, ROL_CATEGORIA_ALEATORIO, categoria)
        hijo.setData(0, ROL_RECURSIVO_ALEATORIO, recursivo)
        fondo = QBrush(QColor(COLOR_ALEATORIO))
        for columna in range(3):
            hijo.setBackground(columna, fondo)
            hijo.setForeground(columna, QBrush(QColor("white")))
        if indice is None:
            bloque.addChild(hijo)
        else:
            bloque.insertChild(indice, hijo)
        bloque.setExpanded(True)
        return hijo

    def _insertar_item_aleatorio(self):
        bloque = self._bloque_destino_actual()
        if bloque is None:
            QMessageBox.information(self, "Ítem Aleatorio", "Primero creá un bloque horario.")
            return
        if self._ventana_explorador is None:
            QMessageBox.information(self, "Ítem Aleatorio", "No hay Explorador disponible.")
            return
        dialogo = DialogoInsertarItemAleatorio(self._ventana_explorador.tree_categorias, parent=self)
        if dialogo.exec() != DialogoInsertarItemAleatorio.DialogCode.Accepted:
            return
        categoria, recursivo, cantidad = dialogo.resultado()
        if not categoria:
            return
        # Pedido explícito: insertar varios ítems aleatorios de una
        # (2, 3, 4, 5...) — cada inserción sucesiva se coloca DESPUÉS
        # de la anterior, en el mismo orden en que se van agregando
        # (recalculando el índice de inserción cada vez, para que
        # queden uno después del otro y no todos apilados al revés).
        indice = self._indice_insercion_actual(bloque)
        for _ in range(cantidad):
            self._agregar_item_aleatorio_a_bloque(bloque, categoria, recursivo, indice)
            if indice is not None:
                indice += 1

    def _insertar_comando_fmt(self):
        bloque = self._bloque_destino_actual()
        if bloque is None:
            QMessageBox.information(self, "Insertar Comando FMT", "Primero creá un bloque horario.")
            return
        dialogo = DialogoInsertarComandoFMT(parent=self)
        if dialogo.exec() != DialogoInsertarComandoFMT.DialogCode.Accepted:
            return
        formato = dialogo.formato_elegido()
        if formato:
            self._agregar_comando_a_bloque(bloque, "FMT", formato, self._indice_insercion_actual(bloque))

    def _insertar_comando_hth(self):
        bloque = self._bloque_destino_actual()
        if bloque is None:
            QMessageBox.information(self, "Insertar Comando HTH", "Primero creá un bloque horario.")
            return
        dialogo = DialogoInsertarComandoHTH(parent=self)
        if dialogo.exec() != DialogoInsertarComandoHTH.DialogCode.Accepted:
            return
        parametro = dialogo.parametro_elegido()
        if parametro:
            self._agregar_comando_a_bloque(bloque, "HTH", parametro, self._indice_insercion_actual(bloque))

    # ==================================================================
    # Copiar / Pegar (pedido explícito, menú contextual): en la
    # selección múltiple ya existente, copiar uno o más ítems y
    # pegarlos en OTRO bloque horario — más rápido que rearmar la
    # misma tanda a mano en cada bloque.
    # ==================================================================
    def _mostrar_menu_contextual(self, posicion):
        menu = QMenu(self)
        accion_copiar = menu.addAction("📋 Copiar")
        accion_pegar = menu.addAction("📌 Pegar en este bloque")
        accion_pegar.setEnabled(bool(self._portapapeles))
        elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if elegida == accion_copiar:
            self._copiar_seleccionados()
        elif elegida == accion_pegar:
            self._pegar_en_bloque_actual()

    def _serializar_item(self, hijo) -> dict:
        """Serializa UN ítem (tanda o comando) al mismo formato que ya
        usa `_serializar_bloques()` para guardar en disco — reusado
        también por "Copiar", así el portapapeles nunca tiene un
        formato de datos paralelo."""
        if hijo.data(0, ROL_ES_COMANDO):
            return {
                "es_comando": True,
                "tipo_comando": hijo.data(0, ROL_TIPO_COMANDO),
                "parametro_comando": hijo.data(0, ROL_PARAMETRO_COMANDO),
            }
        if hijo.data(0, ROL_ES_ALEATORIO):
            return {
                "es_aleatorio": True,
                "categoria_aleatorio": hijo.data(0, ROL_CATEGORIA_ALEATORIO) or [],
                "recursivo_aleatorio": True if hijo.data(0, ROL_RECURSIVO_ALEATORIO) is None
                    else bool(hijo.data(0, ROL_RECURSIVO_ALEATORIO)),
            }
        analisis = hijo.data(0, ROL_ANALISIS_AUDIO) or {}
        vigencia = hijo.data(0, ROL_VIGENCIA) or {}
        return {
            "titulo": hijo.text(0), "duracion": hijo.text(1), "codigo": hijo.text(2),
            "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
            "punto_inicio_ms": analisis.get("punto_inicio_ms") or 0,
            "punto_fin_ms": analisis.get("punto_fin_ms"),
            "ganancia_db": analisis.get("ganancia_db") or 0.0,
            "fecha_inicio": vigencia.get("fecha_inicio"),
            "fecha_fin": vigencia.get("fecha_fin"),
        }

    def _copiar_seleccionados(self):
        seleccionados = self.tree.selectedItems()
        items_a_copiar = [it for it in seleccionados if it.parent() is not None]
        if not items_a_copiar:
            QMessageBox.information(
                self, "Copiar", "Seleccioná uno o más ítems (no bloques enteros) para copiar.",
            )
            return
        self._portapapeles = [self._serializar_item(it) for it in items_a_copiar]

    def _pegar_en_bloque_actual(self):
        if not self._portapapeles:
            QMessageBox.information(self, "Pegar", "Todavía no copiaste ningún ítem.")
            return
        bloque = self._bloque_destino_actual()
        if bloque is None:
            QMessageBox.information(self, "Pegar", "Primero creá un bloque horario.")
            return
        # Pedido explícito: pegar debe insertar en el LUGAR seleccionado,
        # no siempre al final — cada ítem pegado avanza el índice para
        # que la serie completa quede en orden, justo después del
        # ítem que estaba seleccionado.
        indice = self._indice_insercion_actual(bloque)
        for item_data in self._portapapeles:
            if item_data.get("es_comando"):
                self._agregar_comando_a_bloque(
                    bloque, item_data.get("tipo_comando", "FMT"), item_data.get("parametro_comando", ""), indice,
                )
            elif item_data.get("es_aleatorio"):
                self._agregar_item_aleatorio_a_bloque(
                    bloque, item_data.get("categoria_aleatorio") or [],
                    item_data.get("recursivo_aleatorio", True), indice,
                )
            else:
                self._agregar_registro_a_bloque(bloque, item_data, indice)
            if indice is not None:
                indice += 1
        bloque.setExpanded(True)

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

        indice = self._indice_insercion_actual(bloque)
        for registro in dialogo.registros_elegidos():
            self._agregar_registro_a_bloque(bloque, registro, indice)
            if indice is not None:
                indice += 1
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

        if item.data(0, ROL_ES_COMANDO):
            QMessageBox.information(
                self, "Reemplazar",
                "Un Comando (FMT/HTH) no se \"reemplaza\" — quitalo (botón ✕ Quitar)\n"
                "y agregá uno nuevo con \"▶ Comando FMT...\" o \"▶ Comando HTH...\"\n"
                "si querés cambiar el comando.",
            )
            return

        if item.data(0, ROL_ES_ALEATORIO):
            QMessageBox.information(
                self, "Reemplazar",
                "Un Ítem Aleatorio no se \"reemplaza\" — quitalo (botón ✕ Quitar)\n"
                "y agregá uno nuevo con \"🎲 Ítem Aleatorio...\" si querés cambiar\n"
                "la categoría.",
            )
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
        item.setData(0, ROL_VIGENCIA, {
            "fecha_inicio": registro.get("fecha_inicio"), "fecha_fin": registro.get("fecha_fin"),
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
                if item.get("es_comando"):
                    self._agregar_comando_a_bloque(nodo, item.get("tipo_comando", "FMT"), item.get("parametro_comando", ""))
                    continue
                if item.get("es_aleatorio"):
                    self._agregar_item_aleatorio_a_bloque(
                        nodo, item.get("categoria_aleatorio") or [], item.get("recursivo_aleatorio", True),
                    )
                    continue
                hijo = QTreeWidgetItem([item.get("titulo", ""), item.get("duracion", ""), item.get("codigo", "—")])
                hijo.setData(0, Qt.ItemDataRole.UserRole, item.get("ruta", ""))
                hijo.setData(0, ROL_ANALISIS_AUDIO, {
                    "punto_inicio_ms": item.get("punto_inicio_ms") or 0,
                    "punto_fin_ms": item.get("punto_fin_ms"),
                    "ganancia_db": item.get("ganancia_db") or 0.0,
                })
                hijo.setData(0, ROL_VIGENCIA, {
                    "fecha_inicio": item.get("fecha_inicio"), "fecha_fin": item.get("fecha_fin"),
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

    def _nueva_programacion(self, confirmar: bool = True, con_plantilla: bool = False):
        """`con_plantilla=True` SOLO cuando el operador aprieta el
        botón "Nueva" de verdad (pedido explícito, punto f: arrancar
        con un esqueleto de 24 bloques ya listos). Los usos INTERNOS
        de este método (vaciar el editor antes de volcar una
        programación cargada) nunca deben traer la plantilla — si la
        trajeran, quedaría mezclada con los bloques recién cargados."""
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

        if con_plantilla:
            self._cargar_plantilla_basica()

    def _cargar_plantilla_basica(self):
        """Pedido explícito (punto f): "Nueva" arranca con una
        plantilla básica de bloques de 00 a 23hs, uno por cada hora
        del día, vacíos — el operador solo tiene que completarlos con
        ítems en vez de crear los 24 bloques a mano."""
        for hora_num in range(24):
            hora = f"{hora_num:02d}:00:00"
            # Pedido explícito: ya no dice "Bloque" — dice "TANDA -
            # Rotativa" (la hora ya queda como prefijo del texto).
            titulo = "TANDA - Rotativa"
            nodo = QTreeWidgetItem([f"{hora} - {titulo}", "", ""])
            fuente = nodo.font(0)
            fuente.setBold(True)
            nodo.setFont(0, fuente)
            nodo.setData(0, ROL_HORA_BLOQUE, hora)
            nodo.setData(0, ROL_TITULO_BLOQUE, titulo)
            self.tree.addTopLevelItem(nodo)

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

        # Pedido explícito: si lo que se acaba de guardar corresponde a
        # HOY (fecha específica == hoy, o el día de semana de hoy está
        # entre los tildados), se ofrece de una la MISMA acción que
        # "▶ Aplicar Ahora" — nunca en silencio, sigue pidiendo
        # confirmación (puede cortar el aire), solo que ya no hace
        # falta ir a buscar el botón aparte.
        if self._corresponde_a_hoy(fecha_especifica, dias_seleccionados):
            respuesta = QMessageBox.question(
                self, "Guardar",
                "Programación guardada correctamente.\n\n"
                "Esta programación corresponde a HOY — ¿aplicarla YA en\n"
                "Ventana 1 (al aire)? Puede cortar lo que esté sonando.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                self.solicitud_aplicar_ahora.emit(bloques)
        else:
            QMessageBox.information(self, "Guardar", "Programación guardada correctamente.")

    @staticmethod
    def _corresponde_a_hoy(fecha_especifica, dias_seleccionados) -> bool:
        """True si la programación que se está guardando aplica HOY:
        la fecha específica es la de hoy, o el día de semana de hoy
        está entre los días tildados."""
        hoy = date.today()
        if fecha_especifica and fecha_especifica == hoy.isoformat():
            return True
        dia_hoy = NOMBRES_DIAS_SEMANA[hoy.weekday()]
        return dia_hoy in dias_seleccionados

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
            items = [self._serializar_item(nodo.child(j)) for j in range(nodo.childCount())]
            bloques.append({"hora": hora, "titulo": titulo, "items": items})
        return bloques
