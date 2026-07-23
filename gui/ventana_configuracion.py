"""
gui/ventana_configuracion.py
--------------------------------------------------------
Configuración general de la aplicación, en pestañas:
  1. Audio            -> dispositivos Master / Preescucha, volúmenes.
  2. Fade/Transiciones -> crossfade on/off y duración.
  3. Rutas            -> bibliotecas de música/publicidad y logs.
  4. Reproducción      -> automatización: avanzar en error,
                          reintentos, repetir lista, modo automático
                          al iniciar.
  5. General           -> confirmaciones, reloj, tema.

Todo se persiste en config/data/config_general.json vía
config/settings.py. No hay nada de satelital/RDS: es justo lo
necesario para emitir publicidad y música de forma automática.
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
    QComboBox, QSlider, QCheckBox, QDoubleSpinBox, QSpinBox, QLineEdit,
    QPushButton, QLabel, QDialogButtonBox, QFileDialog, QApplication,
    QMessageBox, QColorDialog
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices

from config.settings import (
    cargar_configuracion, guardar_configuracion, reanalizar_biblioteca,
    ARCHIVO_LOG, ARCHIVO_HISTORIAL_REPRODUCCION,
)
from core.audio_engine import MotorAudio
from core import actualizador
from gui.styles import LISTA_GENEROS


class VentanaConfiguracion(QDialog):
    def __init__(self, parent=None, pestaña_inicial: int = 0, ventana_explorador=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumSize(560, 520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Pedido explícito: "Reanalizar biblioteca" (tab Diagnóstico)
        # necesita refrescar el árbol EN VIVO del Explorador después
        # de recalcular el recorte de silencio de todo lo ya importado.
        self._ventana_explorador = ventana_explorador

        self._config = cargar_configuracion()
        self._construir_ui()
        self._cargar_valores_en_ui()

        if 0 <= pestaña_inicial < self.tabs.count():
            self.tabs.setCurrentIndex(pestaña_inicial)

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._crear_tab_audio(), "Audio")
        self.tabs.addTab(self._crear_tab_fade(), "Fade / Transiciones")
        self.tabs.addTab(self._crear_tab_rutas(), "Rutas")
        self.tabs.addTab(self._crear_tab_reproduccion(), "Reproducción y Automatización")
        self.tabs.addTab(self._crear_tab_general(), "General")
        self.tabs.addTab(self._crear_tab_apariencia(), "Apariencia")
        self.tabs.addTab(self._crear_tab_actualizaciones(), "Actualizaciones")
        self.tabs.addTab(self._crear_tab_diagnostico(), "Diagnóstico")
        layout.addWidget(self.tabs)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._guardar_y_cerrar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    # ------------------------------------------------------------------
    # Tab: Audio
    # ------------------------------------------------------------------
    def _crear_tab_audio(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.combo_dispositivo_master = QComboBox()
        self.combo_dispositivo_master.setEditable(True)
        self.combo_dispositivo_preescucha = QComboBox()
        self.combo_dispositivo_preescucha.setEditable(True)

        dispositivos = self._listar_dispositivos_disponibles()
        for combo in (self.combo_dispositivo_master, self.combo_dispositivo_preescucha):
            combo.addItem("default (salida del sistema)", "default")
            for id_dispositivo, descripcion in dispositivos:
                combo.addItem(f"{descripcion} ({id_dispositivo})", id_dispositivo)

        self.slider_volumen_master = self._crear_slider_volumen()
        self.slider_volumen_preescucha = self._crear_slider_volumen()

        form.addRow("Salida Master (Emisión / Publicidad):", self.combo_dispositivo_master)
        form.addRow("Volumen Master:", self.slider_volumen_master)
        form.addRow(QLabel(""))
        form.addRow("Salida Preescucha (▶ Previo de Ventana 3):", self.combo_dispositivo_preescucha)
        form.addRow("Volumen Preescucha:", self.slider_volumen_preescucha)

        nota = QLabel(
            "Nota: por ahora el Auxiliar comparte la salida Master.\n"
            "La salida de Preescucha es la que usa el botón ▶ Previo\n"
            "del Explorador (Ventana 3) — pensada para ir a los parlantes\n"
            "de monitoreo de la PC, separada de la salida Master que va\n"
            "al aire (ej. un procesador/codificador conectado aparte)."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        form.addRow(nota)

        return widget

    def _crear_slider_volumen(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(100)
        return slider

    def _listar_dispositivos_disponibles(self):
        try:
            motor_temporal = MotorAudio()
            if motor_temporal.esta_disponible():
                return motor_temporal.listar_dispositivos()
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Tab: Fade / Transiciones
    # ------------------------------------------------------------------
    def _crear_tab_fade(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.chk_crossfade = QCheckBox("Activar crossfade entre temas de la Ventana 2")
        self.spin_fade_in_v2 = QSpinBox()
        self.spin_fade_in_v2.setRange(0, 3000)
        self.spin_fade_in_v2.setSingleStep(50)
        self.spin_fade_in_v2.setSuffix(" ms")
        self.spin_fade_out_v2 = QSpinBox()
        self.spin_fade_out_v2.setRange(0, 3000)
        self.spin_fade_out_v2.setSingleStep(50)
        self.spin_fade_out_v2.setSuffix(" ms")

        form.addRow(self.chk_crossfade)
        form.addRow("Fade IN al entrar un tema (Ventana 2):", self.spin_fade_in_v2)
        form.addRow("Fade OUT al terminar un tema (Ventana 2):", self.spin_fade_out_v2)

        nota = QLabel(
            "El fade se aplica únicamente a las transiciones de música\n"
            "(Ventana 2). Los cortes hacia Publicidad en modo AUTOMÁTICO\n"
            "son directos, sin crossfade, para no solapar audio comercial."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        form.addRow(nota)

        return widget

    # ------------------------------------------------------------------
    # Tab: Rutas
    # ------------------------------------------------------------------
    def _crear_tab_rutas(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.txt_ruta_musica = QLineEdit()
        self.txt_ruta_publicidad = QLineEdit()
        self.txt_ruta_logs = QLineEdit()

        form.addRow("Biblioteca musical:", self._fila_con_examinar(self.txt_ruta_musica))
        form.addRow("Biblioteca de publicidad:", self._fila_con_examinar(self.txt_ruta_publicidad))
        form.addRow("Carpeta de logs:", self._fila_con_examinar(self.txt_ruta_logs))

        return widget

    def _fila_con_examinar(self, campo_texto: QLineEdit) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(campo_texto)
        boton = QPushButton("Examinar...")
        boton.clicked.connect(lambda: self._elegir_carpeta(campo_texto))
        layout.addWidget(boton)
        return contenedor

    def _elegir_carpeta(self, campo_texto: QLineEdit):
        carpeta = QFileDialog.getExistingDirectory(self, "Elegir carpeta", campo_texto.text())
        if carpeta:
            campo_texto.setText(carpeta)

    # ------------------------------------------------------------------
    # Tab: Reproducción y Automatización
    # ------------------------------------------------------------------
    def _crear_tab_reproduccion(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.chk_avanzar_en_error = QCheckBox(
            "Si un ítem falla al reproducirse, saltar automáticamente al siguiente"
        )
        self.spin_reintentos = QSpinBox()
        self.spin_reintentos.setRange(1, 20)

        self.chk_repetir_lista = QCheckBox("Repetir la lista de Emisión al llegar al final")
        # El checkbox "modo automático al iniciar" se retiró a pedido
        # explícito: el botón AUTOMÁTICO ahora arranca SIEMPRE
        # encendido al abrir el programa (robustez de emisión).
        self.spin_tolerancia_silencio = QDoubleSpinBox()
        self.spin_tolerancia_silencio.setRange(0.0, 10.0)
        self.spin_tolerancia_silencio.setSingleStep(0.5)
        self.spin_tolerancia_silencio.setSuffix(" s")
        self.spin_tolerancia_silencio.setToolTip(
            "Margen de silencio que se DEJA a propósito al recortar Música/\n"
            "Artística/Pisador/HTH al importarlos (no es exclusivo de la\n"
            "vista previa de Ventana 3: este recorte queda grabado en cada\n"
            "material y se aplica después en la reproducción real de\n"
            "Ventana 1 y 2). Un valor más alto deja MÁS silencio al final.\n"
            "OJO: cambiar este valor NO es retroactivo — los archivos ya\n"
            "importados conservan el recorte calculado en su momento; usá\n"
            "\"Reanalizar biblioteca\" (pestaña Diagnóstico) para aplicar el\n"
            "valor nuevo a lo que ya estaba cargado."
        )

        self.spin_tolerancia_silencio_v1 = QDoubleSpinBox()
        self.spin_tolerancia_silencio_v1.setRange(0.0, 5.0)
        self.spin_tolerancia_silencio_v1.setSingleStep(0.1)
        self.spin_tolerancia_silencio_v1.setSuffix(" s")
        self.spin_tolerancia_silencio_v1.setToolTip(
            "Mismo concepto, pero para Publicidad/Separadores/HTH — sin\n"
            "margen por defecto (recorte más agresivo, pensado para que\n"
            "las tandas queden bien pegadas). También aplica en Ventana 1/2\n"
            "y tampoco es retroactivo — ver \"Reanalizar biblioteca\"."
        )

        self.spin_umbral_silencio = QDoubleSpinBox()
        self.spin_umbral_silencio.setRange(-60.0, -10.0)
        self.spin_umbral_silencio.setSingleStep(1.0)
        self.spin_umbral_silencio.setSuffix(" dBFS")

        self.spin_bajada_pisador = QDoubleSpinBox()
        self.spin_bajada_pisador.setRange(-24.0, 0.0)
        self.spin_bajada_pisador.setSingleStep(0.5)
        self.spin_bajada_pisador.setSuffix(" dB")

        self.spin_fade_out_v1 = QSpinBox()
        self.spin_fade_out_v1.setRange(0, 5000)
        self.spin_fade_out_v1.setSingleStep(50)
        self.spin_fade_out_v1.setSuffix(" ms")

        self.spin_fade_in_declick_v1 = QSpinBox()
        self.spin_fade_in_declick_v1.setRange(0, 3000)
        self.spin_fade_in_declick_v1.setSingleStep(10)
        self.spin_fade_in_declick_v1.setSuffix(" ms")
        self.spin_fade_in_declick_v1.setToolTip(
            "Fade-in corto al ARRANCAR cada ítem de Ventana 1 — sin\n"
            "silencio inicial, rampa breve (400ms recomendado) en vez de\n"
            "un salto brusco a volumen final. 0 = desactivado, salto directo."
        )

        self.spin_buffer_caching = QSpinBox()
        self.spin_buffer_caching.setRange(0, 5000)
        self.spin_buffer_caching.setSingleStep(100)
        self.spin_buffer_caching.setSuffix(" ms")
        self.spin_buffer_caching.setToolTip(
            "Buffer de lectura/decodificación de audio (libVLC) — más alto\n"
            "da más margen contra tartamudeos si la PC se ocupa con otra\n"
            "tarea, a costa de un arranque levemente más lento. Requiere\n"
            "reabrir la app para aplicar."
        )

        self.spin_retardo_arranque = QSpinBox()
        self.spin_retardo_arranque.setRange(0, 1000)
        self.spin_retardo_arranque.setSingleStep(10)
        self.spin_retardo_arranque.setSuffix(" ms")
        self.spin_retardo_arranque.setToolTip(
            "Pequeño retardo interno tras arrancar cada ítem, antes de\n"
            "reforzar posición/volumen — no afecta perceptiblemente el\n"
            "arranque. Requiere reabrir la app para aplicar."
        )

        form.addRow(self.chk_avanzar_en_error)
        form.addRow("Fallos consecutivos antes de detenerse:", self.spin_reintentos)
        form.addRow(self.chk_repetir_lista)
        form.addRow("Tolerancia de silencio al recortar (Música/Artística/Pisador):", self.spin_tolerancia_silencio)
        form.addRow("Tolerancia de silencio estricta (Publicidad/Separadores/HTH):", self.spin_tolerancia_silencio_v1)
        form.addRow("Umbral de silencio (más negativo = más permisivo):", self.spin_umbral_silencio)
        form.addRow("Bajada de volumen al sonar un Pisador:", self.spin_bajada_pisador)
        form.addRow("Fade OUT entre tandas de Ventana 1:", self.spin_fade_out_v1)
        form.addRow("Fade IN al arrancar ítems de Ventana 1:", self.spin_fade_in_declick_v1)
        form.addRow("Buffer de audio (anti-tartamudeo):", self.spin_buffer_caching)
        form.addRow("Retardo de arranque interno:", self.spin_retardo_arranque)

        nota_silencio = QLabel(
            "El recorte de silencio SOLO mira el principio y el final de\n"
            "cada tema, nunca el medio — una pausa breve a mitad de una\n"
            "canción nunca se corta, sin importar el umbral elegido.\n"
            "Publicidad y Separadores usan una tolerancia más estricta (por\n"
            "defecto 0, sin margen) para que las tandas queden bien pegadas."
        )
        nota_silencio.setObjectName("lblTituloBloqueActivo")
        form.addRow(nota_silencio)

        nota_pisador = QLabel(
            "Mientras suena el Pisador superpuesto al inicio de un tema\n"
            "(Ventana 2 / Auxiliar), el tema baja este nivel de volumen y\n"
            "vuelve al original apenas termina el Pisador."
        )
        nota_pisador.setObjectName("lblTituloBloqueActivo")
        form.addRow(nota_pisador)

        return widget

    # ------------------------------------------------------------------
    # Tab: General
    # ------------------------------------------------------------------
    def _crear_tab_general(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        # Pedido explícito: nombre de emisora editable, se muestra a
        # la izquierda del reloj de día/hora en el toolbar (antes era
        # un texto fijo repetido en cada panel — ver MainWindow).
        self.txt_nombre_emisora = QLineEdit()
        self.txt_nombre_emisora.setPlaceholderText("RADIO TUYÚ FM 92.5")
        form.addRow("Nombre de emisora:", self.txt_nombre_emisora)

        self.chk_confirmar_eliminar = QCheckBox(
            "Pedir confirmación antes de eliminar, reemplazar o cambiar de\n"
            "categoría un archivo (o eliminar un bloque)"
        )
        self.chk_mostrar_segundos = QCheckBox("Mostrar segundos en el reloj de la toolbar")

        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Oscuro", "oscuro")
        self.combo_tema.addItem("Claro (próximamente)", "claro")

        form.addRow(self.chk_confirmar_eliminar)
        form.addRow(self.chk_mostrar_segundos)
        form.addRow("Tema visual:", self.combo_tema)

        # Comando HTH — Clima (pedido explícito): coordenadas para
        # consultar la temperatura/humedad en vivo (ver
        # core/clima_meteo.py). Default: General Juan Madariaga.
        self.spin_latitud = QDoubleSpinBox()
        self.spin_latitud.setRange(-90.0, 90.0)
        self.spin_latitud.setDecimals(4)
        self.spin_longitud = QDoubleSpinBox()
        self.spin_longitud.setRange(-180.0, 180.0)
        self.spin_longitud.setDecimals(4)
        form.addRow("Clima — Latitud:", self.spin_latitud)
        form.addRow("Clima — Longitud:", self.spin_longitud)

        return widget

    # ------------------------------------------------------------------
    # Tab: Apariencia — color por género (Ventana 3 + Pisador anidado
    # en Ventana 2/Auxiliar), incluyendo "sin color" (pedido explícito).
    # ------------------------------------------------------------------
    def _crear_tab_apariencia(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        nota = QLabel(
            "Color de fondo por género en la columna \"Categoría\" de la\n"
            "Ventana 3 (y del Pisador anidado en Ventana 2/Auxiliar)."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        form.addRow(nota)

        self._botones_color_genero = {}
        self._chk_sin_color_genero = {}
        for genero in LISTA_GENEROS:
            fila = QHBoxLayout()
            boton = QPushButton("")
            boton.setFixedSize(48, 22)
            boton.clicked.connect(lambda _checked=False, g=genero: self._elegir_color_genero(g))
            chk_sin_color = QCheckBox("Sin color")
            chk_sin_color.toggled.connect(lambda activo, g=genero: self._on_sin_color_toggled(g, activo))
            fila.addWidget(boton)
            fila.addWidget(chk_sin_color)
            fila.addStretch()
            self._botones_color_genero[genero] = boton
            self._chk_sin_color_genero[genero] = chk_sin_color
            form.addRow(f"{genero}:", self._envolver_layout(fila))

        return widget

    def _envolver_layout(self, layout) -> QWidget:
        contenedor = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        contenedor.setLayout(layout)
        return contenedor

    def _elegir_color_genero(self, genero: str):
        boton = self._botones_color_genero[genero]
        color_actual = boton.property("color_hex") or "#808080"
        color = QColorDialog.getColor(QColor(color_actual), self, f"Color para {genero}")
        if color.isValid():
            self._chk_sin_color_genero[genero].setChecked(False)
            self._pintar_boton_color(genero, color.name())

    def _on_sin_color_toggled(self, genero: str, sin_color: bool):
        self._botones_color_genero[genero].setEnabled(not sin_color)

    def _pintar_boton_color(self, genero: str, color_hex: str):
        boton = self._botones_color_genero[genero]
        boton.setProperty("color_hex", color_hex)
        boton.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #555;")

    # ------------------------------------------------------------------
    # Tab: Diagnóstico — log de errores/funcionamiento (pedido
    # explícito: sin acceso directo a la PC, subir el log a GitHub
    # a mano para poder depurar).
    # ------------------------------------------------------------------
    def _crear_tab_diagnostico(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        nota = QLabel(
            "El programa registra en este archivo todo tipo de error y de\n"
            "funcionamiento (play/pausa/stop, errores de reproducción, etc.)\n"
            "para poder depurar problemas después de que ocurran, incluso\n"
            "sin acceso directo a esta PC."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        nota.setWordWrap(True)
        layout.addWidget(nota)

        self.lbl_ruta_log = QLabel(f"Archivo: {ARCHIVO_LOG}")
        self.lbl_ruta_log.setWordWrap(True)
        layout.addWidget(self.lbl_ruta_log)

        self.lbl_tamaño_log = QLabel()
        layout.addWidget(self.lbl_tamaño_log)
        self._actualizar_info_log()

        barra_botones = QHBoxLayout()
        btn_ver_log = QPushButton("📄 Ver log")
        btn_ver_log.clicked.connect(self._ver_log)
        self.btn_subir_log = QPushButton("⬆ Subir log a GitHub")
        self.btn_subir_log.clicked.connect(self._subir_log)
        barra_botones.addWidget(btn_ver_log)
        barra_botones.addWidget(self.btn_subir_log)
        layout.addLayout(barra_botones)

        nota_historial = QLabel(
            "Historial de reproducción: registro persistente (sobrevive un\n"
            "reinicio) de qué sonó, cuándo y en qué ventana — a diferencia\n"
            "del ícono de \"ya reproducido\", que solo dura la sesión actual."
        )
        nota_historial.setObjectName("lblTituloBloqueActivo")
        nota_historial.setWordWrap(True)
        layout.addWidget(nota_historial)
        btn_ver_historial = QPushButton("📊 Ver historial de reproducción")
        btn_ver_historial.clicked.connect(self._ver_historial_reproduccion)
        layout.addWidget(btn_ver_historial)

        self.lbl_estado_log = QLabel("")
        self.lbl_estado_log.setWordWrap(True)
        layout.addWidget(self.lbl_estado_log)

        nota_subida = QLabel(
            "\"Subir log a GitHub\" hace un commit + push manual de este\n"
            "archivo a la rama actual del repositorio — NO se sube solo en\n"
            "cada cierre. Usalo cuando quieras que se pueda revisar un\n"
            "problema que reportaste."
        )
        nota_subida.setObjectName("lblTituloBloqueActivo")
        nota_subida.setWordWrap(True)
        layout.addWidget(nota_subida)

        # Pedido explícito ("los temas siguen teniendo silencio al
        # final"): el recorte de silencio se calcula UNA vez al
        # importar/reemplazar un archivo — cambiar la tolerancia en
        # esta misma pestaña de Configuración NO afecta solo con
        # guardar a lo que ya estaba cargado. Este botón fuerza un
        # reanálisis de TODA la biblioteca con los valores actuales.
        nota_reanalizar = QLabel(
            "Reanalizar biblioteca: vuelve a calcular el recorte de\n"
            "silencio y el nivelado de TODO lo ya importado, con la\n"
            "tolerancia/umbral actuales de esta pestaña — necesario porque\n"
            "cambiar esos valores no es retroactivo por sí solo. Puede\n"
            "tardar según el tamaño de la biblioteca; el programa queda sin\n"
            "responder mientras tanto."
        )
        nota_reanalizar.setObjectName("lblTituloBloqueActivo")
        nota_reanalizar.setWordWrap(True)
        layout.addWidget(nota_reanalizar)
        self.btn_reanalizar_biblioteca = QPushButton("🔄 Reanalizar biblioteca (recorte de silencio)")
        self.btn_reanalizar_biblioteca.clicked.connect(self._reanalizar_biblioteca)
        layout.addWidget(self.btn_reanalizar_biblioteca)
        if self._ventana_explorador is None:
            self.btn_reanalizar_biblioteca.setEnabled(False)

        layout.addStretch()

        if not actualizador.es_instalacion_git():
            self.btn_subir_log.setEnabled(False)
            self.lbl_estado_log.setText(
                "Esta copia no es una instalación por git, así que no se puede subir el log."
            )

        return widget

    def _actualizar_info_log(self):
        if os.path.exists(ARCHIVO_LOG):
            tamaño_kb = os.path.getsize(ARCHIVO_LOG) / 1024
            self.lbl_tamaño_log.setText(f"Tamaño actual: {tamaño_kb:.1f} KB")
        else:
            self.lbl_tamaño_log.setText("Todavía no se generó ningún log en esta instalación.")

    def _ver_log(self):
        if not os.path.exists(ARCHIVO_LOG):
            QMessageBox.information(self, "Ver log", "Todavía no se generó ningún log en esta instalación.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(ARCHIVO_LOG)):
            QMessageBox.information(
                self, "Ver log",
                f"No se pudo abrir un visor de texto automáticamente.\nRuta del log:\n{ARCHIVO_LOG}",
            )

    def _ver_historial_reproduccion(self):
        if not os.path.exists(ARCHIVO_HISTORIAL_REPRODUCCION):
            QMessageBox.information(
                self, "Ver historial", "Todavía no se registró ninguna reproducción en esta instalación.",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(ARCHIVO_HISTORIAL_REPRODUCCION)):
            QMessageBox.information(
                self, "Ver historial",
                f"No se pudo abrir un visor de texto automáticamente.\nRuta:\n{ARCHIVO_HISTORIAL_REPRODUCCION}",
            )

    def _subir_log(self):
        self.lbl_estado_log.setText("Subiendo log a GitHub...")
        QApplication.processEvents()
        exito, mensaje = actualizador.subir_log_a_git(ARCHIVO_LOG)
        self.lbl_estado_log.setText(mensaje)
        if not exito:
            QMessageBox.warning(self, "Subir log", mensaje)

    def _reanalizar_biblioteca(self):
        if self._ventana_explorador is None:
            return
        respuesta = QMessageBox.question(
            self, "Reanalizar biblioteca",
            "Esto vuelve a calcular el recorte de silencio y el nivelado de\n"
            "TODOS los archivos ya importados, con los valores de tolerancia/\n"
            "umbral que están puestos AHORA MISMO en la pestaña Reproducción\n"
            "y Automatización (aunque todavía no hayas apretado Guardar).\n"
            "Puede tardar varios minutos con una biblioteca grande, y el\n"
            "programa queda sin responder mientras tanto.\n\n"
            "¿Confirmás que querés continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        # Usa los valores YA TIPEADOS en esta ventana, no self._config
        # (que todavía tiene los viejos hasta que se guarde) — así el
        # operador puede ajustar la tolerancia y reanalizar de una,
        # sin tener que guardar-cerrar-reabrir primero.
        config_temporal = {
            "reproduccion": {
                "tolerancia_silencio_segundos": self.spin_tolerancia_silencio.value(),
                "tolerancia_silencio_v1_segundos": self.spin_tolerancia_silencio_v1.value(),
                "umbral_silencio_dbfs": self.spin_umbral_silencio.value(),
            },
        }
        texto_original = self.btn_reanalizar_biblioteca.text()
        self.btn_reanalizar_biblioteca.setEnabled(False)
        self.btn_reanalizar_biblioteca.setText("Reanalizando... (puede tardar)")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            cantidad = reanalizar_biblioteca(config_temporal)
            self._ventana_explorador.recargar_biblioteca_desde_disco()
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_reanalizar_biblioteca.setEnabled(True)
            self.btn_reanalizar_biblioteca.setText(texto_original)
        QMessageBox.information(
            self, "Reanalizar biblioteca",
            f"Listo: {cantidad} archivo(s) reanalizado(s) con los valores nuevos.",
        )

    # ------------------------------------------------------------------
    # Tab: Actualizaciones
    # ------------------------------------------------------------------
    def _crear_tab_actualizaciones(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl_repo = QLabel(f"Repositorio: {actualizador.REPO_URL}")
        lbl_repo.setObjectName("lblTituloBloqueActivo")
        lbl_repo.setWordWrap(True)
        layout.addWidget(lbl_repo)

        self.lbl_version_actual = QLabel(f"Versión instalada (commit): {actualizador.commit_actual()}")
        layout.addWidget(self.lbl_version_actual)

        self.lbl_estado_actualizacion = QLabel("Todavía no se buscaron actualizaciones en esta sesión.")
        self.lbl_estado_actualizacion.setWordWrap(True)
        layout.addWidget(self.lbl_estado_actualizacion)

        barra_botones = QHBoxLayout()
        self.btn_buscar_actualizacion = QPushButton("🔎 Buscar actualización")
        self.btn_buscar_actualizacion.clicked.connect(self._buscar_actualizacion)
        self.btn_aplicar_actualizacion = QPushButton("⬇ Actualizar y reiniciar")
        self.btn_aplicar_actualizacion.setObjectName("btnPlay")
        self.btn_aplicar_actualizacion.setEnabled(False)
        self.btn_aplicar_actualizacion.clicked.connect(self._aplicar_actualizacion)
        barra_botones.addWidget(self.btn_buscar_actualizacion)
        barra_botones.addWidget(self.btn_aplicar_actualizacion)
        layout.addLayout(barra_botones)

        nota = QLabel(
            "Al actualizar, el programa descarga los cambios desde GitHub\n"
            "(git pull) y se reinicia solo — se cierra y vuelve a abrir con\n"
            "la versión nueva ya aplicada."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        layout.addWidget(nota)
        layout.addStretch()

        if not actualizador.es_instalacion_git():
            self.lbl_estado_actualizacion.setText(
                "Esta copia no es una instalación por git — la actualización automática\n"
                "no está disponible. Instalá con instalar.sh o cloná el repositorio\n"
                "para poder actualizar desde acá."
            )
            self.btn_buscar_actualizacion.setEnabled(False)

        return widget

    def _buscar_actualizacion(self):
        self.lbl_estado_actualizacion.setText("Buscando actualizaciones en GitHub...")
        QApplication.processEvents()

        hay_actualizacion, mensaje = actualizador.hay_actualizacion_disponible()
        self.lbl_estado_actualizacion.setText(mensaje)
        self.btn_aplicar_actualizacion.setEnabled(hay_actualizacion)

    def _aplicar_actualizacion(self):
        respuesta = QMessageBox.question(
            self, "Actualizar",
            "Se va a descargar la actualización y la aplicación se va a reiniciar.\n"
            "¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.lbl_estado_actualizacion.setText("Descargando actualización...")
        QApplication.processEvents()

        exito, mensaje = actualizador.aplicar_actualizacion()
        self.lbl_estado_actualizacion.setText(mensaje)

        if not exito:
            QMessageBox.warning(self, "Actualizar", mensaje)
            return

        QMessageBox.information(self, "Actualizar", "Actualización aplicada. La aplicación se va a reiniciar.")
        # El reinicio ya fue confirmado acá — avisar a la ventana
        # principal para que closeEvent no vuelva a preguntar por la
        # emisión en curso (pedido explícito: "salvo actualización").
        principal = self.parent()
        if principal is not None and hasattr(principal, "preparar_cierre_por_actualizacion"):
            principal.preparar_cierre_por_actualizacion()
        actualizador.reiniciar_aplicacion(QApplication.instance())
    # ------------------------------------------------------------------
    def _cargar_valores_en_ui(self):
        audio = self._config["audio"]
        self._seleccionar_en_combo(self.combo_dispositivo_master, audio["dispositivo_master"])
        self._seleccionar_en_combo(self.combo_dispositivo_preescucha, audio["dispositivo_preescucha"])
        self.slider_volumen_master.setValue(audio["volumen_master"])
        self.slider_volumen_preescucha.setValue(audio["volumen_preescucha"])

        fade = self._config["fade"]
        self.chk_crossfade.setChecked(fade["crossfade_activado"])
        self.spin_fade_in_v2.setValue(fade["duracion_fade_in_v2_ms"])
        self.spin_fade_out_v2.setValue(fade["duracion_fade_out_v2_ms"])

        rutas = self._config["rutas"]
        self.txt_ruta_musica.setText(rutas["biblioteca_musical"])
        self.txt_ruta_publicidad.setText(rutas["biblioteca_publicidad"])
        self.txt_ruta_logs.setText(rutas["carpeta_logs"])

        reproduccion = self._config["reproduccion"]
        self.chk_avanzar_en_error.setChecked(reproduccion["avanzar_automaticamente_en_error"])
        self.spin_reintentos.setValue(reproduccion["reintentos_antes_de_detener"])
        self.chk_repetir_lista.setChecked(reproduccion["repetir_lista_al_finalizar"])
        self.spin_tolerancia_silencio.setValue(reproduccion["tolerancia_silencio_segundos"])
        self.spin_tolerancia_silencio_v1.setValue(reproduccion["tolerancia_silencio_v1_segundos"])
        self.spin_umbral_silencio.setValue(reproduccion["umbral_silencio_dbfs"])
        self.spin_bajada_pisador.setValue(reproduccion["pisador_bajada_db"])
        self.spin_fade_out_v1.setValue(reproduccion["duracion_fade_out_v1_ms"])
        self.spin_fade_in_declick_v1.setValue(reproduccion["duracion_fade_in_declick_v1_ms"])
        self.spin_buffer_caching.setValue(reproduccion["duracion_buffer_caching_ms"])
        self.spin_retardo_arranque.setValue(reproduccion["retardo_arranque_ms"])

        general = self._config["general"]
        self.txt_nombre_emisora.setText(general.get("nombre_emisora", ""))
        self.chk_confirmar_eliminar.setChecked(general["confirmar_antes_de_eliminar"])
        self.chk_mostrar_segundos.setChecked(general["mostrar_segundos_en_reloj"])
        indice_tema = self.combo_tema.findData(general["tema"])
        if indice_tema >= 0:
            self.combo_tema.setCurrentIndex(indice_tema)

        clima = self._config["clima"]
        self.spin_latitud.setValue(clima["latitud"])
        self.spin_longitud.setValue(clima["longitud"])

        colores_genero = self._config["apariencia"]["colores_genero"]
        for genero in LISTA_GENEROS:
            color_hex = colores_genero.get(genero)
            if color_hex:
                self._pintar_boton_color(genero, color_hex)
                self._chk_sin_color_genero[genero].setChecked(False)
            else:
                self._pintar_boton_color(genero, "#808080")
                self._chk_sin_color_genero[genero].setChecked(True)

    def _seleccionar_en_combo(self, combo: QComboBox, valor: str):
        indice = combo.findData(valor)
        if indice >= 0:
            combo.setCurrentIndex(indice)
        else:
            combo.setEditText(valor)

    def _guardar_y_cerrar(self):
        self._config["audio"]["dispositivo_master"] = self.combo_dispositivo_master.currentData() \
            or self.combo_dispositivo_master.currentText()
        self._config["audio"]["dispositivo_preescucha"] = self.combo_dispositivo_preescucha.currentData() \
            or self.combo_dispositivo_preescucha.currentText()
        self._config["audio"]["volumen_master"] = self.slider_volumen_master.value()
        self._config["audio"]["volumen_preescucha"] = self.slider_volumen_preescucha.value()

        self._config["fade"]["crossfade_activado"] = self.chk_crossfade.isChecked()
        self._config["fade"]["duracion_fade_in_v2_ms"] = self.spin_fade_in_v2.value()
        self._config["fade"]["duracion_fade_out_v2_ms"] = self.spin_fade_out_v2.value()

        self._config["rutas"]["biblioteca_musical"] = self.txt_ruta_musica.text()
        self._config["rutas"]["biblioteca_publicidad"] = self.txt_ruta_publicidad.text()
        self._config["rutas"]["carpeta_logs"] = self.txt_ruta_logs.text()

        self._config["reproduccion"]["avanzar_automaticamente_en_error"] = self.chk_avanzar_en_error.isChecked()
        self._config["reproduccion"]["reintentos_antes_de_detener"] = self.spin_reintentos.value()
        self._config["reproduccion"]["repetir_lista_al_finalizar"] = self.chk_repetir_lista.isChecked()
        self._config["reproduccion"]["tolerancia_silencio_segundos"] = self.spin_tolerancia_silencio.value()
        self._config["reproduccion"]["tolerancia_silencio_v1_segundos"] = self.spin_tolerancia_silencio_v1.value()
        self._config["reproduccion"]["umbral_silencio_dbfs"] = self.spin_umbral_silencio.value()
        self._config["reproduccion"]["pisador_bajada_db"] = self.spin_bajada_pisador.value()
        self._config["reproduccion"]["duracion_fade_out_v1_ms"] = self.spin_fade_out_v1.value()
        self._config["reproduccion"]["duracion_fade_in_declick_v1_ms"] = self.spin_fade_in_declick_v1.value()
        self._config["reproduccion"]["duracion_buffer_caching_ms"] = self.spin_buffer_caching.value()
        self._config["reproduccion"]["retardo_arranque_ms"] = self.spin_retardo_arranque.value()

        self._config["clima"]["latitud"] = self.spin_latitud.value()
        self._config["clima"]["longitud"] = self.spin_longitud.value()

        self._config["general"]["nombre_emisora"] = self.txt_nombre_emisora.text().strip()
        self._config["general"]["confirmar_antes_de_eliminar"] = self.chk_confirmar_eliminar.isChecked()
        self._config["general"]["mostrar_segundos_en_reloj"] = self.chk_mostrar_segundos.isChecked()
        self._config["general"]["tema"] = self.combo_tema.currentData()

        colores_genero = {}
        for genero in LISTA_GENEROS:
            if self._chk_sin_color_genero[genero].isChecked():
                colores_genero[genero] = None
            else:
                colores_genero[genero] = self._botones_color_genero[genero].property("color_hex")
        self._config["apariencia"]["colores_genero"] = colores_genero

        guardar_configuracion(self._config)
        self.accept()
