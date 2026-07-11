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

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
    QComboBox, QSlider, QCheckBox, QDoubleSpinBox, QSpinBox, QLineEdit,
    QPushButton, QLabel, QDialogButtonBox, QFileDialog, QApplication,
    QMessageBox
)
from PySide6.QtCore import Qt

from config.settings import cargar_configuracion, guardar_configuracion
from core.audio_engine import MotorAudio
from core import actualizador


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
        self.tabs.addTab(self._crear_tab_actualizaciones(), "Actualizaciones")
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
        self.chk_modo_automatico_inicio = QCheckBox(
            "Iniciar la aplicación con el modo AUTOMÁTICO de Publicidad activado"
        )
        self.spin_tolerancia_silencio = QDoubleSpinBox()
        self.spin_tolerancia_silencio.setRange(0.0, 10.0)
        self.spin_tolerancia_silencio.setSingleStep(0.5)
        self.spin_tolerancia_silencio.setSuffix(" s")

        form.addRow(self.chk_avanzar_en_error)
        form.addRow("Fallos consecutivos antes de detenerse:", self.spin_reintentos)
        form.addRow(self.chk_repetir_lista)
        form.addRow(self.chk_modo_automatico_inicio)
        form.addRow("Tolerancia de silencio al recortar (Ventana 3):", self.spin_tolerancia_silencio)

        return widget

    # ------------------------------------------------------------------
    # Tab: General
    # ------------------------------------------------------------------
    def _crear_tab_general(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.chk_confirmar_eliminar = QCheckBox("Pedir confirmación antes de eliminar un archivo o bloque")
        self.chk_mostrar_segundos = QCheckBox("Mostrar segundos en el reloj de la toolbar")

        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Oscuro", "oscuro")
        self.combo_tema.addItem("Claro (próximamente)", "claro")

        form.addRow(self.chk_confirmar_eliminar)
        form.addRow(self.chk_mostrar_segundos)
        form.addRow("Tema visual:", self.combo_tema)

        return widget

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
        self.chk_modo_automatico_inicio.setChecked(reproduccion["modo_automatico_al_iniciar"])
        self.spin_tolerancia_silencio.setValue(reproduccion["tolerancia_silencio_segundos"])

        general = self._config["general"]
        self.chk_confirmar_eliminar.setChecked(general["confirmar_antes_de_eliminar"])
        self.chk_mostrar_segundos.setChecked(general["mostrar_segundos_en_reloj"])
        indice_tema = self.combo_tema.findData(general["tema"])
        if indice_tema >= 0:
            self.combo_tema.setCurrentIndex(indice_tema)

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
        self._config["reproduccion"]["modo_automatico_al_iniciar"] = self.chk_modo_automatico_inicio.isChecked()
        self._config["reproduccion"]["tolerancia_silencio_segundos"] = self.spin_tolerancia_silencio.value()

        self._config["general"]["confirmar_antes_de_eliminar"] = self.chk_confirmar_eliminar.isChecked()
        self._config["general"]["mostrar_segundos_en_reloj"] = self.chk_mostrar_segundos.isChecked()
        self._config["general"]["tema"] = self.combo_tema.currentData()

        guardar_configuracion(self._config)
        self.accept()
