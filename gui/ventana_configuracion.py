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

from config.settings import cargar_configuracion, guardar_configuracion, ARCHIVO_LOG
from core.audio_engine import MotorAudio
from core import actualizador
from gui.styles import LISTA_GENEROS


class VentanaConfiguracion(QDialog):
    def __init__(self, parent=None, pestaña_inicial: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumSize(560, 520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

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
        form.addRow("Salida Preescucha (reservado a futuro):", self.combo_dispositivo_preescucha)
        form.addRow("Volumen Preescucha:", self.slider_volumen_preescucha)

        nota = QLabel(
            "Nota: por ahora el Auxiliar comparte la salida Master.\n"
            "La salida de Preescucha queda lista en el motor para\n"
            "cuando se habilite una previsualización independiente."
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
        self.spin_duracion_fade = QDoubleSpinBox()
        self.spin_duracion_fade.setRange(0.0, 15.0)
        self.spin_duracion_fade.setSingleStep(0.5)
        self.spin_duracion_fade.setSuffix(" s")

        form.addRow(self.chk_crossfade)
        form.addRow("Duración del fade:", self.spin_duracion_fade)

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

        self.spin_umbral_silencio = QDoubleSpinBox()
        self.spin_umbral_silencio.setRange(-60.0, -10.0)
        self.spin_umbral_silencio.setSingleStep(1.0)
        self.spin_umbral_silencio.setSuffix(" dBFS")

        self.spin_bajada_pisador = QDoubleSpinBox()
        self.spin_bajada_pisador.setRange(-24.0, 0.0)
        self.spin_bajada_pisador.setSingleStep(0.5)
        self.spin_bajada_pisador.setSuffix(" dB")

        form.addRow(self.chk_avanzar_en_error)
        form.addRow("Fallos consecutivos antes de detenerse:", self.spin_reintentos)
        form.addRow(self.chk_repetir_lista)
        form.addRow("Tolerancia de silencio al recortar (Ventana 3):", self.spin_tolerancia_silencio)
        form.addRow("Umbral de silencio (más negativo = más permisivo):", self.spin_umbral_silencio)
        form.addRow("Bajada de volumen al sonar un Pisador:", self.spin_bajada_pisador)

        nota_silencio = QLabel(
            "El recorte de silencio SOLO mira el principio y el final de\n"
            "cada tema, nunca el medio — una pausa breve a mitad de una\n"
            "canción nunca se corta, sin importar el umbral elegido."
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

    def _subir_log(self):
        self.lbl_estado_log.setText("Subiendo log a GitHub...")
        QApplication.processEvents()
        exito, mensaje = actualizador.subir_log_a_git(ARCHIVO_LOG)
        self.lbl_estado_log.setText(mensaje)
        if not exito:
            QMessageBox.warning(self, "Subir log", mensaje)

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
        self.spin_duracion_fade.setValue(fade["duracion_fade_segundos"])

        rutas = self._config["rutas"]
        self.txt_ruta_musica.setText(rutas["biblioteca_musical"])
        self.txt_ruta_publicidad.setText(rutas["biblioteca_publicidad"])
        self.txt_ruta_logs.setText(rutas["carpeta_logs"])

        reproduccion = self._config["reproduccion"]
        self.chk_avanzar_en_error.setChecked(reproduccion["avanzar_automaticamente_en_error"])
        self.spin_reintentos.setValue(reproduccion["reintentos_antes_de_detener"])
        self.chk_repetir_lista.setChecked(reproduccion["repetir_lista_al_finalizar"])
        self.spin_tolerancia_silencio.setValue(reproduccion["tolerancia_silencio_segundos"])
        self.spin_umbral_silencio.setValue(reproduccion["umbral_silencio_dbfs"])
        self.spin_bajada_pisador.setValue(reproduccion["pisador_bajada_db"])

        general = self._config["general"]
        self.chk_confirmar_eliminar.setChecked(general["confirmar_antes_de_eliminar"])
        self.chk_mostrar_segundos.setChecked(general["mostrar_segundos_en_reloj"])
        indice_tema = self.combo_tema.findData(general["tema"])
        if indice_tema >= 0:
            self.combo_tema.setCurrentIndex(indice_tema)

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
        self._config["fade"]["duracion_fade_segundos"] = self.spin_duracion_fade.value()

        self._config["rutas"]["biblioteca_musical"] = self.txt_ruta_musica.text()
        self._config["rutas"]["biblioteca_publicidad"] = self.txt_ruta_publicidad.text()
        self._config["rutas"]["carpeta_logs"] = self.txt_ruta_logs.text()

        self._config["reproduccion"]["avanzar_automaticamente_en_error"] = self.chk_avanzar_en_error.isChecked()
        self._config["reproduccion"]["reintentos_antes_de_detener"] = self.spin_reintentos.value()
        self._config["reproduccion"]["repetir_lista_al_finalizar"] = self.chk_repetir_lista.isChecked()
        self._config["reproduccion"]["tolerancia_silencio_segundos"] = self.spin_tolerancia_silencio.value()
        self._config["reproduccion"]["umbral_silencio_dbfs"] = self.spin_umbral_silencio.value()
        self._config["reproduccion"]["pisador_bajada_db"] = self.spin_bajada_pisador.value()

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
