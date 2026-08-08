"""
gui/ventana_configuracion.py
--------------------------------------------------------
Configuración general de la aplicación, en pestañas: Audio (dispositivos
Master/Preescucha, volúmenes), Fade/Transiciones, Rutas, Reproducción y
Automatización, General, Apariencia, Actualizaciones, Diagnóstico.

La pestaña "Procesador" (compresor/Stereo Enhancer/Volume Normalizer
nativos de VLC, rondas 69-74) se sacó a pedido explícito de Santiago —
armó una app Python aparte, standalone, que controla el filter-chain
nativo de PipeWire para el procesamiento de audio de salida (ver
CLAUDE.md, ronda de esta remoción, para el contexto completo).

Todo se persiste en config/data/config_general.json vía
config/settings.py. No hay nada de satelital/RDS: es justo lo
necesario para emitir publicidad y música de forma automática.
--------------------------------------------------------
"""

import json
import os
import subprocess
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QTabWidget, QWidget,
    QComboBox, QSlider, QCheckBox, QDoubleSpinBox, QSpinBox, QLineEdit,
    QPushButton, QLabel, QDialogButtonBox, QFileDialog, QApplication,
    QMessageBox, QColorDialog, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, QUrl, QProcess
from PySide6.QtGui import QColor, QDesktopServices

from config.settings import (
    cargar_configuracion, guardar_configuracion, registrar_error,
    ARCHIVO_LOG, ARCHIVO_HISTORIAL_REPRODUCCION,
)
from core.audio_engine import MotorAudio
from core import actualizador
from gui.styles import LISTA_GENEROS
from gui.dialogo_preload_biblioteca import DialogoPreloadBiblioteca


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
            combo.addItem("PipeWire (por defecto del sistema)", "default")
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
        """Lista los dispositivos de audio reales corriendo
        `core/audio_engine.py` como PROCESO APARTE (`python3 -m
        core.audio_engine`), nunca dentro de este proceso.

        Segunda vuelta de un bug real de producción: la primera
        corrección (un MotorAudio() temporal armado en un HILO con
        timeout de 3s, para no colgar la ventana si
        `audio_output_device_list_get()` del módulo "pulse" de libVLC
        se cuelga con otras instancias ya reproduciendo en el mismo
        proceso) evitaba el freeze, pero un hilo abandonado no puede
        cerrar su conexión de PulseAudio -- tras varias horas de abrir
        Configuración repetidas veces en producción, cada cuelgue dejó
        una conexión viva para siempre, hasta que `pipewire-pulse`
        empezó a rechazar TODO ("too many client application
        connections"), tirando abajo hasta `pactl`.

        Corregido de raíz: un PROCESO aparte, si no responde a tiempo,
        se mata con SIGKILL desde afuera -- el sistema operativo cierra
        su conexión de PulseAudio solo al matarlo, sin dejar nada
        pendiente nunca, a diferencia de un hilo que comparte el mismo
        proceso. Un timeout/error acá siempre degrada a mostrar solo
        "default", nunca vuelve a poder colgar ni ensuciar la app."""
        try:
            raiz_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resultado = subprocess.run(
                [sys.executable, "-m", "core.audio_engine"],
                capture_output=True, text=True, timeout=5, cwd=raiz_proyecto,
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                # Tomamos SOLO la última línea de stdout como el JSON --
                # `core/audio_engine.py` puede imprimir avisos sueltos
                # antes (ej. "VLC no está instalado"), y el JSON en sí
                # siempre es lo último que imprime el script.
                ultima_linea = resultado.stdout.strip().splitlines()[-1]
                return [tuple(d) for d in json.loads(ultima_linea)]
        except subprocess.TimeoutExpired:
            registrar_error(
                "VentanaConfiguracion: listar_dispositivos() (proceso aparte) "
                "no respondió en 5s -- matado sin dejar ninguna conexión de "
                "PulseAudio abierta. Se muestra solo 'default'."
            )
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Tab: Fade / Transiciones
    # ------------------------------------------------------------------
    def _crear_tab_fade(self) -> QWidget:
        """Pedido explícito ("perfeccioná el fundido... configuración
        por ventana separada en el menú configuraciones"): los 4 spin
        boxes de fundido (IN/OUT x Ventana 1/Ventana 2) viven TODOS
        acá, agrupados por ventana — antes los de Ventana 1 estaban
        sueltos en la pestaña "Reproducción y Automatización", mezclados
        con tolerancia de silencio/buffer/reintentos, lejos de los de
        Ventana 2. Los nombres de atributo (`spin_fade_out_v1`,
        `spin_fade_in_declick_v1`, `spin_fade_in_v2`, `spin_fade_out_v2`)
        no cambiaron — solo se movió DÓNDE se construyen y se muestran,
        así `_cargar_valores()`/`_guardar_y_cerrar()` siguen intactos."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        grupo_v1 = QGroupBox("Ventana 1 — Publicidad / Tanda")
        form_v1 = QFormLayout(grupo_v1)

        self.spin_fade_in_declick_v1 = QSpinBox()
        self.spin_fade_in_declick_v1.setRange(0, 3000)
        self.spin_fade_in_declick_v1.setSingleStep(10)
        self.spin_fade_in_declick_v1.setSuffix(" ms")
        self.spin_fade_in_declick_v1.setToolTip(
            "Fade-in corto al ARRANCAR cada ítem de Ventana 1 — sin\n"
            "silencio inicial, rampa breve (400ms recomendado) en vez de\n"
            "un salto brusco a volumen final. 0 = desactivado, salto directo."
        )
        self.spin_fade_out_v1 = QSpinBox()
        self.spin_fade_out_v1.setRange(0, 5000)
        self.spin_fade_out_v1.setSingleStep(50)
        self.spin_fade_out_v1.setSuffix(" ms")
        self.spin_fade_out_v1.setToolTip(
            "Fade-out corto al terminar naturalmente una tanda y encadenar\n"
            "con la siguiente dentro del mismo bloque de Ventana 1."
        )

        form_v1.addRow("Fade IN al arrancar un ítem:", self.spin_fade_in_declick_v1)
        form_v1.addRow("Fade OUT al terminar un ítem:", self.spin_fade_out_v1)
        layout.addWidget(grupo_v1)

        grupo_v2 = QGroupBox("Ventana 2 — Emisión")
        form_v2 = QFormLayout(grupo_v2)

        self.chk_crossfade = QCheckBox("Activar crossfade entre temas de la Ventana 2")
        self.spin_fade_in_v2 = QSpinBox()
        self.spin_fade_in_v2.setRange(0, 3000)
        self.spin_fade_in_v2.setSingleStep(50)
        self.spin_fade_in_v2.setSuffix(" ms")
        self.spin_fade_out_v2 = QSpinBox()
        self.spin_fade_out_v2.setRange(0, 3000)
        self.spin_fade_out_v2.setSingleStep(50)
        self.spin_fade_out_v2.setSuffix(" ms")

        form_v2.addRow(self.chk_crossfade)
        form_v2.addRow("Fade IN al entrar un tema:", self.spin_fade_in_v2)
        form_v2.addRow("Fade OUT al terminar un tema:", self.spin_fade_out_v2)
        layout.addWidget(grupo_v2)

        nota = QLabel(
            "En Ventana 1, el fade OUT encadena tandas dentro del mismo\n"
            "bloque; en Ventana 2, el fade se aplica a las transiciones\n"
            "entre temas de música (crossfade). Los cortes hacia\n"
            "Publicidad en modo AUTOMÁTICO son siempre directos, sin\n"
            "crossfade, para no solapar audio comercial."
        )
        nota.setObjectName("lblTituloBloqueActivo")
        layout.addWidget(nota)
        layout.addStretch()

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

        # Nivelado de volumen por loudness (pedido explícito: "en
        # mhWaveEdit normalizo audio a mano, ¿se puede automático al
        # importar/analizar?" -- ver core/analizador_audio.py:
        # _calcular_ganancia_db()). NO destructivo: solo cambia el
        # ajuste de volumen calculado, nunca el archivo.
        self.spin_objetivo_lufs = QDoubleSpinBox()
        self.spin_objetivo_lufs.setRange(-30.0, -6.0)
        self.spin_objetivo_lufs.setSingleStep(0.5)
        self.spin_objetivo_lufs.setSuffix(" LUFS")
        self.spin_objetivo_lufs.setToolTip(
            "Sonoridad objetivo a la que se nivela cada archivo al importar/\n"
            "reanalizar (loudness real, EBU R128, no un simple promedio de\n"
            "amplitud). Más cerca de 0 = más fuerte; más negativo = más flojo.\n"
            "-16 LUFS es un punto de partida típico para radio/streaming.\n"
            "OJO: no es retroactivo — usá \"Reanalizar biblioteca\" o \"Aplicar\n"
            "análisis de silencio\" (Ventana 3) para aplicarlo a lo ya cargado."
        )

        self.spin_techo_pico = QDoubleSpinBox()
        self.spin_techo_pico.setRange(-6.0, 0.0)
        self.spin_techo_pico.setSingleStep(0.5)
        self.spin_techo_pico.setSuffix(" dBFS")
        self.spin_techo_pico.setToolTip(
            "Techo de seguridad: el nivelado NUNCA empuja el pico de un\n"
            "archivo por encima de este valor, aunque eso signifique aplicar\n"
            "menos ganancia de la calculada — protege contra saturación en\n"
            "temas con promedio bajo pero algún pico alto."
        )

        # Pedido explícito ("configuración por ventana separada"): los
        # fade IN/OUT de Ventana 1 (spin_fade_in_declick_v1/
        # spin_fade_out_v1) se movieron a la pestaña "Fade /
        # Transiciones", agrupados junto a los de Ventana 2 — ya no se
        # construyen acá, ver _crear_tab_fade().

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
        form.addRow("Nivelado de volumen — objetivo de sonoridad:", self.spin_objetivo_lufs)
        form.addRow("Nivelado de volumen — techo de seguridad de pico:", self.spin_techo_pico)
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

        nota_nivelado = QLabel(
            "El nivelado de volumen NUNCA reescribe el archivo original —\n"
            "solo calcula un ajuste de volumen que se aplica al reproducir.\n"
            "Usa sonoridad real (LUFS) si pyloudnorm está instalado (ver\n"
            "Diagnóstico → \"Verificar motor de análisis de audio\"); si no,\n"
            "cae a un promedio de amplitud más simple, sin romper nada."
        )
        nota_nivelado.setObjectName("lblTituloBloqueActivo")
        nota_nivelado.setWordWrap(True)
        form.addRow(nota_nivelado)

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
        self.combo_tema.addItem("Claro (estilo Dinesat)", "claro")

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
        """Pedido explícito ("organizá mejor la pestaña Diagnóstico...
        los botones muchas veces quedan largos y se tapan las
        letras... que entre todo fácil"): esta pestaña había ido
        creciendo, ronda tras ronda, hasta acumular 8 botones y 8
        explicaciones en párrafo completo, todo apilado en una sola
        columna angosta — cada texto largo (algunos con emoji, que en
        Linux puede estimar mal su propio ancho) competía por el mismo
        espacio reducido. Reorganizado en 3 grupos temáticos (Log de
        la app / Historial y análisis de audio / Mantenimiento de
        biblioteca) con botones más CORTOS en grilla de 2 columnas —
        la explicación larga de cada uno pasó a vivir en su `toolTip()`
        (aparece al pasar el mouse) en vez de un párrafo siempre
        visible, y todo el contenido quedó envuelto en un
        `QScrollArea` (mismo patrón ya usado en otras pestañas de este
        diálogo) para que, aunque en el futuro se sume otro botón más,
        nunca vuelva a apretarse el layout — scrollea en vez de
        romperse."""
        contenedor_scroll = QScrollArea()
        contenedor_scroll.setWidgetResizable(True)
        contenedor_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # ---------- Grupo 1: Log de la aplicación ----------
        grupo_log = QGroupBox("📋 Log de la aplicación")
        layout_log = QVBoxLayout(grupo_log)

        self.lbl_ruta_log = QLabel(f"Archivo: {ARCHIVO_LOG}")
        self.lbl_ruta_log.setWordWrap(True)
        self.lbl_ruta_log.setToolTip(
            "El programa registra acá todo tipo de error y de funcionamiento\n"
            "(play/pausa/stop, errores de reproducción, etc.) para poder\n"
            "depurar problemas después de que ocurran, incluso sin acceso\n"
            "directo a esta PC."
        )
        layout_log.addWidget(self.lbl_ruta_log)

        self.lbl_tamaño_log = QLabel()
        layout_log.addWidget(self.lbl_tamaño_log)
        self._actualizar_info_log()

        barra_botones = QHBoxLayout()
        btn_ver_log = QPushButton("📄 Ver log")
        btn_ver_log.clicked.connect(self._ver_log)
        self.btn_subir_log = QPushButton("⬆ Subir a GitHub")
        self.btn_subir_log.setToolTip(
            "Hace un commit + push MANUAL de este archivo a la rama actual\n"
            "del repositorio — NO se sube solo en cada cierre. Usalo cuando\n"
            "quieras que se pueda revisar un problema que reportaste."
        )
        self.btn_subir_log.clicked.connect(self._subir_log)
        barra_botones.addWidget(btn_ver_log)
        barra_botones.addWidget(self.btn_subir_log)
        layout_log.addLayout(barra_botones)

        self.lbl_estado_log = QLabel("")
        self.lbl_estado_log.setWordWrap(True)
        layout_log.addWidget(self.lbl_estado_log)

        layout.addWidget(grupo_log)

        # ---------- Grupo 2: Historial y análisis de audio ----------
        grupo_audio = QGroupBox("🎧 Historial y análisis de audio")
        grid_audio = QGridLayout(grupo_audio)

        btn_ver_historial = QPushButton("📊 Ver historial")
        btn_ver_historial.setToolTip(
            "Historial de reproducción: registro persistente (sobrevive un\n"
            "reinicio) de qué sonó, cuándo y en qué ventana — a diferencia\n"
            "del ícono de \"ya reproducido\", que solo dura la sesión actual."
        )
        btn_ver_historial.clicked.connect(self._ver_historial_reproduccion)
        grid_audio.addWidget(btn_ver_historial, 0, 0)

        self.btn_verificar_motor_audio = QPushButton("🩺 Verificar motor de audio")
        self.btn_verificar_motor_audio.setToolTip(
            "Confirma si pydub + ffmpeg están disponibles (necesarios para\n"
            "calcular las marcas IN/OUT de silencio y el nivelado) con una\n"
            "prueba real, sin tocar ningún archivo de la biblioteca."
        )
        self.btn_verificar_motor_audio.clicked.connect(self._verificar_motor_audio)
        grid_audio.addWidget(self.btn_verificar_motor_audio, 0, 1)

        # Pedido explícito ("los temas siguen teniendo silencio al
        # final"): el recorte de silencio se calcula UNA vez al
        # importar/reemplazar un archivo — cambiar la tolerancia en
        # esta misma pestaña de Configuración NO afecta solo con
        # guardar a lo que ya estaba cargado. Este botón fuerza un
        # reanálisis de TODA la biblioteca con los valores actuales.
        self.btn_reanalizar_biblioteca = QPushButton("🔄 Reanalizar biblioteca (Música)")
        self.btn_reanalizar_biblioteca.setToolTip(
            "Vuelve a calcular el recorte de silencio y el nivelado de TODO\n"
            "lo ya importado (solo género Música), con la tolerancia/umbral\n"
            "actuales de la pestaña Reproducción — necesario porque cambiar\n"
            "esos valores no es retroactivo por sí solo. Corre en un proceso\n"
            "aparte, con barra de progreso, sin trabar el programa."
        )
        self.btn_reanalizar_biblioteca.clicked.connect(self._reanalizar_biblioteca)
        grid_audio.addWidget(self.btn_reanalizar_biblioteca, 1, 0, 1, 2)
        if self._ventana_explorador is None:
            self.btn_reanalizar_biblioteca.setEnabled(False)

        layout.addWidget(grupo_audio)

        # ---------- Grupo 3: Mantenimiento de biblioteca ----------
        grupo_biblioteca = QGroupBox("🗂 Mantenimiento de biblioteca")
        grid_biblioteca = QGridLayout(grupo_biblioteca)

        # Pedido explícito ("¿esta verificación se puede hacer también
        # manual desde Configuraciones?"): la migración de duración
        # faltante ya corre sola al arrancar la app — este botón es el
        # mismo mecanismo, disparable a mano en cualquier momento.
        self.btn_verificar_biblioteca = QPushButton("🔎 Duración faltante")
        self.btn_verificar_biblioteca.setToolTip(
            "Busca archivos sin la duración calculada todavía (típico de\n"
            "una biblioteca migrada por fuera de las altas normales) y la\n"
            "completa — mismo chequeo que ya corre solo al abrir el\n"
            "programa, para correrlo a mano sin tener que reiniciar."
        )
        self.btn_verificar_biblioteca.clicked.connect(self._verificar_biblioteca)
        grid_biblioteca.addWidget(self.btn_verificar_biblioteca, 0, 0)
        if self._ventana_explorador is None:
            self.btn_verificar_biblioteca.setEnabled(False)

        # Pedido explícito ("hacer esta ubicación de archivos perdidos
        # de manera masiva en todo el explorador"): recorre TODA la
        # biblioteca buscando archivos con el vínculo roto (movidos/
        # borrados/renombrados por fuera de esta app) y los ofrece
        # resolver uno por uno — mismo diálogo de "Ubicar" del menú
        # contextual de Ventana 3.
        self.btn_verificar_perdidos = QPushButton("🔗 Archivos perdidos")
        self.btn_verificar_perdidos.setToolTip(
            "Recorre TODA la biblioteca buscando materiales cuyo archivo de\n"
            "audio ya no está donde el registro dice, y los revisa uno por\n"
            "uno con el mismo buscador de \"Ubicar\" (Previo, Saltar,\n"
            "Vincular)."
        )
        self.btn_verificar_perdidos.clicked.connect(self._verificar_archivos_perdidos)
        grid_biblioteca.addWidget(self.btn_verificar_perdidos, 0, 1)
        if self._ventana_explorador is None:
            self.btn_verificar_perdidos.setEnabled(False)

        # Pedido explícito: "búsqueda de duplicados... por nombre,
        # duración y tamaño con opción de elegir alguno de esos
        # filtros incluso los 3 juntos".
        self.btn_buscar_duplicados = QPushButton("🧩 Duplicados")
        self.btn_buscar_duplicados.setToolTip(
            "Agrupa materiales de toda la biblioteca que coincidan por\n"
            "nombre, duración y/o tamaño (combinables) — permite moverlos a\n"
            "otra categoría o eliminar el registro sobrante, mostrando la\n"
            "ruta de categoría de cada uno."
        )
        self.btn_buscar_duplicados.clicked.connect(self._buscar_duplicados)
        grid_biblioteca.addWidget(self.btn_buscar_duplicados, 1, 0)
        if self._ventana_explorador is None:
            self.btn_buscar_duplicados.setEnabled(False)

        layout.addWidget(grupo_biblioteca)
        layout.addStretch()

        if not actualizador.es_instalacion_git():
            self.btn_subir_log.setEnabled(False)
            self.lbl_estado_log.setText(
                "Esta copia no es una instalación por git, así que no se puede subir el log."
            )

        contenedor_scroll.setWidget(widget)
        return contenedor_scroll

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
        """Pedido explícito ("tengo 9800 elementos... se trabó por
        obvias razones, necesitamos hacerlo con otro proceso aparte,
        que me indique el progreso"): corre `core/reanalizador_batch.py`
        como PROCESO APARTE vía QProcess (mismo mecanismo ya usado para
        EasyEffects/git/actualizaciones en este proyecto — nunca
        threading) — el programa entero queda RESPONSIVE mientras
        procesa una biblioteca grande, con una barra de progreso real
        (X / Y archivos) en vez de "quedarse sin responder" varios
        minutos sin ninguna señal de vida."""
        if self._ventana_explorador is None:
            return
        respuesta = QMessageBox.question(
            self, "Reanalizar biblioteca",
            "Esto vuelve a calcular el recorte de silencio y el nivelado de\n"
            "TODOS los archivos de género MÚSICA ya importados (Publicidad/\n"
            "Separador/Pisador/Artística/HTH quedan afuera -- para esos usá\n"
            "\"Aplicar/Revertir análisis de silencio\" en el menú contextual\n"
            "de Ventana 3, archivo por archivo o en lote), con los valores de\n"
            "tolerancia/umbral que están puestos AHORA MISMO en la pestaña\n"
            "Reproducción y Automatización (aunque todavía no hayas apretado\n"
            "Guardar). Corre en SEGUNDO PLANO (proceso aparte, con barra de\n"
            "progreso) — el programa sigue respondiendo mientras tanto.\n\n"
            "¿Confirmás que querés continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "reanalizador_batch.py")
        # Usa los valores YA TIPEADOS en esta ventana, no self._config
        # (que todavía tiene los viejos hasta que se guarde) — así el
        # operador puede ajustar la tolerancia y reanalizar de una,
        # sin tener que guardar-cerrar-reabrir primero.
        argumentos = [
            script,
            "--tolerancia-general", str(self.spin_tolerancia_silencio.value()),
            "--tolerancia-v1", str(self.spin_tolerancia_silencio_v1.value()),
            "--umbral", str(self.spin_umbral_silencio.value()),
        ]

        self._dialogo_reanalisis = DialogoPreloadBiblioteca(
            1, parent=self, titulo="Reanalizando biblioteca",
            texto="Reanalizando biblioteca -- solo Música (recorte de silencio / nivelado)...",
            nota="Corre en un proceso aparte -- el programa sigue respondiendo mientras tanto.",
        )
        self._dialogo_reanalisis.show()

        self._buffer_stdout_reanalisis = ""
        self._resultado_reanalisis = None
        self._proceso_reanalisis = QProcess(self)
        self._proceso_reanalisis.setProgram(sys.executable)
        self._proceso_reanalisis.setArguments(argumentos)
        self._proceso_reanalisis.readyReadStandardOutput.connect(self._leer_progreso_reanalisis)
        self._proceso_reanalisis.finished.connect(self._al_terminar_reanalisis)
        self.btn_reanalizar_biblioteca.setEnabled(False)
        self._proceso_reanalisis.start()

    def _leer_progreso_reanalisis(self):
        """Parsea las líneas "PROGRESO hechos total" / "RESULTADO
        {json}" que imprime core/reanalizador_batch.py -- bufferea
        hasta tener una línea completa, ya que readyReadStandardOutput
        puede entregar los datos en pedazos arbitrarios."""
        self._buffer_stdout_reanalisis += bytes(
            self._proceso_reanalisis.readAllStandardOutput()
        ).decode("utf-8", errors="replace")
        while "\n" in self._buffer_stdout_reanalisis:
            linea, self._buffer_stdout_reanalisis = self._buffer_stdout_reanalisis.split("\n", 1)
            linea = linea.strip()
            if linea.startswith("PROGRESO "):
                partes = linea.split()
                if len(partes) == 3:
                    try:
                        hechos, total = int(partes[1]), int(partes[2])
                    except ValueError:
                        continue
                    if self._dialogo_reanalisis is not None:
                        self._dialogo_reanalisis.actualizar(hechos, total)
            elif linea.startswith("RESULTADO "):
                try:
                    self._resultado_reanalisis = json.loads(linea[len("RESULTADO "):])
                except ValueError:
                    pass

    def _al_terminar_reanalisis(self, codigo_salida, _estado_salida):
        if self._dialogo_reanalisis is not None:
            self._dialogo_reanalisis.close()
            self._dialogo_reanalisis = None
        self.btn_reanalizar_biblioteca.setEnabled(True)

        if self._ventana_explorador is not None:
            self._ventana_explorador.recargar_biblioteca_desde_disco()

        stats = self._resultado_reanalisis
        if stats is None:
            error = bytes(self._proceso_reanalisis.readAllStandardError()).decode("utf-8", errors="replace").strip()
            QMessageBox.warning(
                self, "Reanalizar biblioteca",
                f"El proceso de reanálisis terminó sin devolver un resultado válido "
                f"(código {codigo_salida}).\n\n{error}",
            )
            return

        # Bug real corregido ("nunca funciona el recorte de silencio"):
        # antes este mensaje solo decía "N reanalizados", contando
        # como éxito CUALQUIER intento aunque pydub/ffmpeg hubieran
        # fallado y el archivo quedara con marcas IN/OUT vacías. Ahora
        # desglosa cuántos quedaron con marcas REALES, cuántos
        # fallaron, y cuántos se PRESERVARON intactos (ya tenían
        # marcas buenas de antes, un fallo nuevo nunca las destruye) —
        # destacando además el género Música.
        if stats["fallidos"] > 0:
            QMessageBox.warning(
                self, "Reanalizar biblioteca",
                f"Terminado, pero con fallas: {stats['analizados']} de {stats['total']} "
                f"archivo(s) quedaron con marcas IN/OUT reales; "
                f"{stats['fallidos']} FALLARON de verdad (nunca tuvieron marcas, "
                f"quedan sin recorte de silencio ni nivelado); "
                f"{stats.get('preservados', 0)} ya tenían marcas buenas de antes y "
                f"se preservaron SIN TOCAR pese a fallar esta vuelta.\n\n"
                f"De género Música: {stats['musica_analizados']} de {stats['musica_total']} "
                f"con marcas reales.\n\n"
                "Los fallos suelen ser por falta de pydub/ffmpeg -- corré "
                "\"🩺 Verificar motor de análisis de audio\" (más abajo) para "
                "confirmar qué falta, y el detalle de cada archivo queda en el log.",
            )
        else:
            QMessageBox.information(
                self, "Reanalizar biblioteca",
                f"Listo: {stats['analizados']} de {stats['total']} archivo(s) quedaron "
                f"con marcas IN/OUT reales (de género Música: "
                f"{stats['musica_analizados']} de {stats['musica_total']}).",
            )

    def _verificar_motor_audio(self):
        """Pedido explícito ("veo que nunca funciona el recorte de
        silencio"): confirma de antemano, con una prueba real (audio
        sintético generado en memoria, sin tocar ningún archivo de la
        biblioteca), si el motor de marcas IN/OUT puede correr en esta
        instalación -- y con qué falta exactamente si no, en vez de
        descubrirlo recién cuando un archivo real falla en silencio."""
        from core.analizador_audio import verificar_motor_disponible

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            resultado = verificar_motor_disponible()
        finally:
            QApplication.restoreOverrideCursor()

        if resultado["prueba_ok"]:
            QMessageBox.information(self, "Verificar motor de análisis de audio", resultado["mensaje"])
        else:
            QMessageBox.warning(self, "Verificar motor de análisis de audio", resultado["mensaje"])

    def _verificar_biblioteca(self):
        """Corre a mano el mismo chequeo de duración faltante que ya
        corre solo al abrir el programa — reusa `iniciar_migracion_
        duracion_al_arrancar()` (lotes chicos vía QTimer, nunca un
        bucle síncrono gigante) y la MISMA barra de progreso gráfica,
        así se comporta igual sea que se dispare al arrancar o a mano
        desde acá."""
        if self._ventana_explorador is None:
            return

        estado = {"dialogo": None, "hechos": 0}

        def _iniciar(total):
            if total > 0:
                estado["dialogo"] = DialogoPreloadBiblioteca(total, parent=self)
                estado["dialogo"].show()

        def _progreso(hechos, total):
            if estado["dialogo"] is not None:
                estado["dialogo"].actualizar(hechos, total)

        def _terminado(hechos):
            estado["hechos"] = hechos
            if estado["dialogo"] is not None:
                estado["dialogo"].close()

        self._ventana_explorador.iniciar_migracion_duracion_al_arrancar(
            callback_iniciar=_iniciar, callback_progreso=_progreso, callback_terminado=_terminado,
        )
        if estado["dialogo"] is not None:
            estado["dialogo"].exec()
            QMessageBox.information(
                self, "Verificar biblioteca",
                f"Listo: {estado['hechos']} archivo(s) con duración calculada y guardada.",
            )
        else:
            QMessageBox.information(
                self, "Verificar biblioteca",
                "No había nada pendiente — todos los archivos ya tenían la duración calculada.",
            )

    def _verificar_archivos_perdidos(self):
        """Delega TODA la lógica en VentanaExplorador — este botón
        solo la dispara desde Configuración (ver ronda de "Ubicar")."""
        if self._ventana_explorador is None:
            return
        self._ventana_explorador.verificar_archivos_perdidos_biblioteca()

    def _buscar_duplicados(self):
        """Abre el diálogo de duplicados (gui/dialogo_duplicados.py) —
        toda la lógica de búsqueda/mover/eliminar vive ahí y en
        VentanaExplorador; este botón solo lo dispara desde
        Configuración."""
        if self._ventana_explorador is None:
            return
        from gui.dialogo_duplicados import DialogoDuplicados
        dialogo = DialogoDuplicados(self._ventana_explorador, parent=self)
        dialogo.exec()

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
        self.spin_objetivo_lufs.setValue(reproduccion["nivelado_loudness_lufs_objetivo"])
        self.spin_techo_pico.setValue(reproduccion["nivelado_techo_pico_dbfs"])
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

    def _valor_dispositivo_combo(self, combo: QComboBox) -> str:
        """Devuelve el dispositivo elegido en un combo Master/
        Preescucha (editable). Bug real de producción: `currentData()`
        de un QComboBox editable sigue devolviendo el dato del ÍTIMO
        ÍTEM seleccionado por índice, INCLUSO DESPUÉS de escribir texto
        libre a mano — tipear (o `setEditText()`) no cambia
        `currentIndex()` — así que `currentData() or currentText()`
        (como estaba antes) casi siempre terminaba guardando el
        dispositivo VIEJO, ignorando por completo lo recién tipeado
        (confirmado en producción: el operador escribía un nombre de
        sink de pactl a mano y, al guardar, quedaba otra cosa
        completamente distinta). Corregido comparando el texto actual
        contra el texto que debería tener el ítem realmente
        seleccionado: si coinciden, no se tocó nada — se usa el id
        "limpio" de `currentData()`; si no coinciden, se escribió algo
        a mano — se usa ese texto tal cual."""
        texto_actual = combo.currentText().strip()
        indice = combo.currentIndex()
        if indice >= 0 and combo.itemText(indice) == texto_actual:
            return combo.currentData() or texto_actual
        return texto_actual

    def _guardar_y_cerrar(self):
        self._config["audio"]["dispositivo_master"] = self._valor_dispositivo_combo(self.combo_dispositivo_master)
        self._config["audio"]["dispositivo_preescucha"] = self._valor_dispositivo_combo(self.combo_dispositivo_preescucha)
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
        self._config["reproduccion"]["nivelado_loudness_lufs_objetivo"] = self.spin_objetivo_lufs.value()
        self._config["reproduccion"]["nivelado_techo_pico_dbfs"] = self.spin_techo_pico.value()
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
