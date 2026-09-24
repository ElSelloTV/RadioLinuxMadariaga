"""
gui/panel_procesador_audio.py
--------------------------------------------------------
Pestaña "🎚 Procesador FM" de Configuración -- controlador EN FRÍO del
procesador de audio del aire (pedido explícito: "Deslizadores + y -
que aumenten o bajen los parámetros del archivo de configuración...
apretar 'aplicar' para que se cargue"). Mover un deslizador acá NUNCA
toca PipeWire por sí solo -- solo "✅ Aplicar" y "🔇 Bypass" lo hacen
(ver core/procesador_audio.py para el texto/escritura/recarga real).

Presets nombrados (pedido explícito, "algo así como elegir_config.sh
pero con un semi entorno gráfico"): el combo de arriba guarda/carga
juegos completos de valores con nombre -- "Configuración 1" (el
predeterminado de fábrica) es la única "verdad conocida" hasta que
Santiago guarde otras.
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QCheckBox, QSlider, QDoubleSpinBox, QLineEdit,
    QScrollArea, QInputDialog, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, Signal

from core import procesador_audio


class SliderConSpinbox(QWidget):
    """Deslizador + campo numérico sincronizados -- el deslizador da
    el "sentir" de +/- pedido; el spinbox al lado permite tipear un
    valor exacto. `PASOS` es solo la resolución interna del QSlider
    (que solo entiende enteros); el valor real siempre se guarda/lee
    en la unidad humana del propio `Parametro` (dB, ms, Hz, etc.)."""

    valorCambiado = Signal(float)
    PASOS = 1000

    def __init__(self, parametro: "procesador_audio.Parametro", parent=None):
        super().__init__(parent)
        self.parametro = parametro
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.PASOS)
        layout.addWidget(self.slider, 3)

        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(parametro.decimales)
        self.spin.setRange(parametro.minimo, parametro.maximo)
        if parametro.sufijo:
            self.spin.setSuffix(parametro.sufijo)
        rango = parametro.maximo - parametro.minimo
        self.spin.setSingleStep(max(rango / 200.0, 10 ** (-parametro.decimales)))
        layout.addWidget(self.spin, 1)

        self._actualizando = False
        self.slider.valueChanged.connect(self._desde_slider)
        self.spin.valueChanged.connect(self._desde_spin)
        self.establecer_valor(parametro.defecto)

    def _pasos_a_valor(self, pasos: int) -> float:
        rango = self.parametro.maximo - self.parametro.minimo
        valor = self.parametro.minimo + (rango * pasos / self.PASOS) if rango else self.parametro.minimo
        return round(valor, self.parametro.decimales)

    def _valor_a_pasos(self, valor: float) -> int:
        rango = self.parametro.maximo - self.parametro.minimo
        if rango <= 0:
            return 0
        pasos = round((valor - self.parametro.minimo) / rango * self.PASOS)
        return max(0, min(self.PASOS, pasos))

    def _desde_slider(self, pasos: int):
        if self._actualizando:
            return
        self._actualizando = True
        valor = self._pasos_a_valor(pasos)
        self.spin.setValue(valor)
        self._actualizando = False
        self.valorCambiado.emit(valor)

    def _desde_spin(self, valor: float):
        if self._actualizando:
            return
        self._actualizando = True
        self.slider.setValue(self._valor_a_pasos(valor))
        self._actualizando = False
        self.valorCambiado.emit(valor)

    def valor(self) -> float:
        return self.spin.value()

    def establecer_valor(self, valor: float):
        self._actualizando = True
        self.spin.setValue(valor)
        self.slider.setValue(self._valor_a_pasos(valor))
        self._actualizando = False


class GrupoEfecto(QGroupBox):
    """Un plugin del catálogo -- checkbox "Activado" en el título
    (apaga/prende ese nodo de la cadena) + un control por parámetro."""

    def __init__(self, efecto: "procesador_audio.Efecto", parent=None):
        super().__init__(efecto.nombre, parent)
        self.efecto = efecto
        self.setCheckable(True)
        self.setChecked(efecto.activado_por_defecto)

        layout = QVBoxLayout(self)
        if efecto.descripcion:
            lbl = QLabel(efecto.descripcion)
            lbl.setWordWrap(True)
            lbl.setObjectName("lblTituloBloqueActivo")
            layout.addWidget(lbl)

        form = QFormLayout()
        self._controles = {}
        for p in efecto.parametros:
            if p.es_bool:
                control = QCheckBox()
                control.setChecked(bool(p.defecto))
            else:
                control = SliderConSpinbox(p)
            self._controles[p.simbolo] = control
            form.addRow(f"{p.etiqueta}:", control)
        layout.addLayout(form)

        self.toggled.connect(self._alternar_habilitacion)
        self._alternar_habilitacion(self.isChecked())

    def _alternar_habilitacion(self, activado: bool):
        for control in self._controles.values():
            control.setEnabled(activado)

    def valores(self) -> dict:
        datos = {"activado": self.isChecked()}
        for simbolo, control in self._controles.items():
            datos[simbolo] = control.isChecked() if isinstance(control, QCheckBox) else control.valor()
        return datos

    def establecer_valores(self, valores: dict):
        self.setChecked(bool(valores.get("activado", self.efecto.activado_por_defecto)))
        for simbolo, control in self._controles.items():
            if simbolo not in valores:
                continue
            if isinstance(control, QCheckBox):
                control.setChecked(bool(valores[simbolo]))
            else:
                control.establecer_valor(valores[simbolo])


class PanelProcesadorAudio(QWidget):
    # Pedido explícito, reporte real ("aprieto Bypass y deja mudo...
    # tengo que pasar al siguiente ítem, que macana, porque tengo que
    # salir de esa ventana y luego volver"): tanto "Aplicar" como
    # "Bypass" reinician PipeWire/pipewire-pulse/wireplumber para tomar
    # el .conf nuevo (core/procesador_audio.py) -- eso mata TODA
    # conexión de audio abierta, incluida la del ítem que esté sonando
    # en ese instante en Ventana 1/2/Auxiliar. Esta señal avisa a
    # MainWindow (la única con referencias a los gestores/motores
    # reales) para que los reconecte solos -- ver
    # MotorAudio.reconectar_tras_reinicio_audio() y
    # MainWindow._reconectar_audio_tras_reinicio_pipewire().
    reinicio_pipewire_aplicado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._datos = procesador_audio.cargar_datos()
        self._construir_ui()
        self._cargar_preset_en_ui(self._datos["preset_actual"])

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        lbl_intro = QLabel(
            "Controlador \"en frío\" del procesador de audio del aire "
            "(compresor/limitador/etc., vía el módulo filter-chain de "
            "PipeWire) -- esta app NUNCA procesa el audio ella misma, solo "
            "arma y carga el archivo. Movés los deslizadores tranquilo, no "
            "suena nada hasta apretar \"✅ Aplicar\". \"Aplicar\" y "
            "\"Bypass\" reinician PipeWire un instante -- CORTA EL AUDIO DE "
            "TODA LA PC (no solo esta app) por un segundo. Hacé esto en un "
            "hueco tranquilo, nunca con algo importante al aire."
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        fila_preset = QHBoxLayout()
        fila_preset.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        self.combo_preset.currentTextChanged.connect(self._on_cambio_preset)
        fila_preset.addWidget(self.combo_preset, 1)
        btn_guardar_como = QPushButton("💾 Guardar como...")
        btn_guardar_como.setToolTip("Guarda los valores actuales de los deslizadores con un nombre")
        btn_guardar_como.clicked.connect(self._guardar_como)
        btn_renombrar = QPushButton("✏ Renombrar")
        btn_renombrar.clicked.connect(self._renombrar_preset)
        btn_eliminar = QPushButton("✕ Eliminar")
        btn_eliminar.clicked.connect(self._eliminar_preset)
        btn_predeterminar = QPushButton("⭐ Marcar predeterminado")
        btn_predeterminar.setToolTip("El botón \"🔄 Predeterminado\" de abajo va a cargar ESTE preset")
        btn_predeterminar.clicked.connect(self._marcar_como_predeterminado)
        for boton in (btn_guardar_como, btn_renombrar, btn_eliminar, btn_predeterminar):
            fila_preset.addWidget(boton)
        layout.addLayout(fila_preset)

        form_rutas = QFormLayout()
        self.txt_ruta_conf = QLineEdit()
        self.txt_ruta_conf.setToolTip("Archivo .conf que PipeWire carga (pipewire.conf.d/) con el procesador")
        form_rutas.addRow("Archivo filter-chain.conf:", self.txt_ruta_conf)
        self.txt_sink_captura = QLineEdit()
        self.txt_sink_captura.setToolTip(
            "Nombre del sink virtual que arma este archivo -- Configuración > Audio > "
            "Salida Master tiene que apuntar a este MISMO nombre para que el audio de "
            "la radio pase por acá."
        )
        form_rutas.addRow("Sink de captura (= Salida Master):", self.txt_sink_captura)
        self.txt_sink_reproduccion = QLineEdit()
        self.txt_sink_reproduccion.setToolTip(
            "Nombre real del hardware de salida (\"pactl list sinks short\" en la PC de aire)"
        )
        form_rutas.addRow("Sink de salida real (hardware):", self.txt_sink_reproduccion)
        layout.addLayout(form_rutas)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        layout_efectos = QVBoxLayout(contenido)
        self._grupos = {}
        for clave in procesador_audio.ORDEN_CADENA:
            efecto = procesador_audio.CATALOGO_POR_CLAVE[clave]
            grupo = GrupoEfecto(efecto)
            self._grupos[clave] = grupo
            layout_efectos.addWidget(grupo)
        layout_efectos.addStretch()
        scroll.setWidget(contenido)
        layout.addWidget(scroll, 1)

        fila_acciones = QHBoxLayout()
        btn_predeterminado = QPushButton("🔄 Predeterminado")
        btn_predeterminado.setToolTip(
            "Vuelve los deslizadores al preset predeterminado -- todavía en frío, no aplica nada"
        )
        btn_predeterminado.clicked.connect(self._cargar_predeterminado)
        btn_aplicar = QPushButton("✅ Aplicar")
        btn_aplicar.setToolTip("Escribe el .conf con los valores de arriba y reinicia PipeWire para tomarlo")
        btn_aplicar.clicked.connect(self._aplicar)
        self.btn_bypass = QPushButton("🔇 Bypass (sin efectos)")
        self.btn_bypass.setCheckable(True)
        self.btn_bypass.setToolTip("A/B rápido: pasa el aire SIN ningún procesamiento, para comparar")
        self.btn_bypass.clicked.connect(self._alternar_bypass)
        fila_acciones.addWidget(btn_predeterminado)
        fila_acciones.addWidget(btn_aplicar)
        fila_acciones.addWidget(self.btn_bypass)
        layout.addLayout(fila_acciones)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setWordWrap(True)
        layout.addWidget(self.lbl_estado)

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------
    def _refrescar_combo_presets(self, seleccionar: str = None):
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()
        self.combo_preset.addItems(list(self._datos["presets"].keys()))
        if seleccionar and seleccionar in self._datos["presets"]:
            self.combo_preset.setCurrentText(seleccionar)
        self.combo_preset.blockSignals(False)

    def _cargar_preset_en_ui(self, nombre: str):
        preset = procesador_audio.normalizar_preset(self._datos["presets"].get(nombre, {}))
        for clave, grupo in self._grupos.items():
            grupo.establecer_valores(preset[clave])
        self.txt_ruta_conf.setText(self._datos["ruta_conf_pipewire"])
        self.txt_sink_captura.setText(self._datos["sink_captura"])
        self.txt_sink_reproduccion.setText(self._datos["sink_reproduccion"])
        self._datos["preset_actual"] = nombre
        self._refrescar_combo_presets(seleccionar=nombre)

    def _preset_desde_ui(self) -> dict:
        return {clave: grupo.valores() for clave, grupo in self._grupos.items()}

    def _guardar_estado(self):
        self._datos["ruta_conf_pipewire"] = self.txt_ruta_conf.text().strip() or procesador_audio.RUTA_CONF_DEFECTO
        self._datos["sink_captura"] = self.txt_sink_captura.text().strip() or procesador_audio.SINK_CAPTURA_DEFECTO
        self._datos["sink_reproduccion"] = self.txt_sink_reproduccion.text().strip()
        procesador_audio.guardar_datos(self._datos)

    def _on_cambio_preset(self, nombre: str):
        if not nombre or nombre == self._datos.get("preset_actual"):
            return
        self._cargar_preset_en_ui(nombre)

    def _cargar_predeterminado(self):
        nombre = self._datos.get("preset_predeterminado", procesador_audio.NOMBRE_PRESET_DEFECTO)
        self._cargar_preset_en_ui(nombre)
        self.lbl_estado.setText(
            f"Cargado el preset predeterminado (\"{nombre}\") en los deslizadores -- "
            "todavía en frío, apretá \"✅ Aplicar\" para escucharlo."
        )

    def _guardar_como(self):
        nombre_actual = self.combo_preset.currentText() or procesador_audio.NOMBRE_PRESET_DEFECTO
        nombre, ok = QInputDialog.getText(self, "Guardar preset", "Nombre del preset:", text=nombre_actual)
        nombre = (nombre or "").strip()
        if not ok or not nombre:
            return
        if nombre in self._datos["presets"] and nombre != nombre_actual:
            respuesta = QMessageBox.question(
                self, "Guardar preset", f"Ya existe un preset llamado '{nombre}'. ¿Reemplazarlo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        self._datos["presets"][nombre] = self._preset_desde_ui()
        self._guardar_estado()
        self._cargar_preset_en_ui(nombre)
        self.lbl_estado.setText(f"Guardado como '{nombre}' (todavía no aplicado).")

    def _renombrar_preset(self):
        actual = self.combo_preset.currentText()
        if not actual:
            return
        nuevo, ok = QInputDialog.getText(self, "Renombrar preset", "Nuevo nombre:", text=actual)
        nuevo = (nuevo or "").strip()
        if not ok or not nuevo or nuevo == actual:
            return
        if nuevo in self._datos["presets"]:
            QMessageBox.information(self, "Renombrar preset", f"Ya existe un preset llamado '{nuevo}'.")
            return
        self._datos["presets"][nuevo] = self._datos["presets"].pop(actual)
        if self._datos.get("preset_predeterminado") == actual:
            self._datos["preset_predeterminado"] = nuevo
        self._guardar_estado()
        self._cargar_preset_en_ui(nuevo)

    def _eliminar_preset(self):
        actual = self.combo_preset.currentText()
        if not actual:
            return
        if len(self._datos["presets"]) <= 1:
            QMessageBox.information(self, "Eliminar preset", "Tiene que quedar al menos un preset guardado.")
            return
        respuesta = QMessageBox.question(
            self, "Eliminar preset", f"¿Eliminar el preset '{actual}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        del self._datos["presets"][actual]
        if self._datos.get("preset_predeterminado") == actual:
            self._datos["preset_predeterminado"] = next(iter(self._datos["presets"]))
        self._guardar_estado()
        self._cargar_preset_en_ui(self._datos["preset_predeterminado"])

    def _marcar_como_predeterminado(self):
        actual = self.combo_preset.currentText()
        if not actual:
            return
        self._datos["preset_predeterminado"] = actual
        self._guardar_estado()
        self.lbl_estado.setText(f"'{actual}' marcado como predeterminado.")

    # ------------------------------------------------------------------
    # Aplicar / Bypass -- las únicas dos acciones que tocan PipeWire
    # ------------------------------------------------------------------
    def _datos_destino(self):
        ruta = self.txt_ruta_conf.text().strip() or procesador_audio.RUTA_CONF_DEFECTO
        sink_captura = self.txt_sink_captura.text().strip() or procesador_audio.SINK_CAPTURA_DEFECTO
        sink_reproduccion = self.txt_sink_reproduccion.text().strip()
        return ruta, sink_captura, sink_reproduccion

    def _aplicar_texto(self, texto: str, ruta: str) -> tuple[bool, str]:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return procesador_audio.escribir_y_recargar(texto, ruta)
        finally:
            QApplication.restoreOverrideCursor()

    def _aplicar(self):
        self._guardar_estado()
        ruta, sink_captura, sink_reproduccion = self._datos_destino()
        if not sink_reproduccion:
            QMessageBox.warning(
                self, "Aplicar",
                "Falta el 'Sink de salida real (hardware)' -- mirá 'pactl list sinks "
                "short' en la PC de aire para conseguir el nombre exacto.",
            )
            return
        respuesta = QMessageBox.question(
            self, "Aplicar procesador FM",
            "Esto va a REEMPLAZAR el archivo:\n"
            f"{ruta}\n\n"
            "y reiniciar PipeWire para tomarlo -- corta el audio de TODA la PC "
            "un instante (no solo el aire de la radio). Hacé esto en un hueco "
            "tranquilo, nunca con algo importante al aire.\n\n¿Aplicar ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        preset = self._preset_desde_ui()
        texto = procesador_audio.generar_filter_chain_conf(preset, sink_captura, sink_reproduccion)
        exito, mensaje = self._aplicar_texto(texto, ruta)
        self.btn_bypass.setChecked(False)
        self.btn_bypass.setText("🔇 Bypass (sin efectos)")
        if exito:
            self.reinicio_pipewire_aplicado.emit()
        (QMessageBox.information if exito else QMessageBox.warning)(self, "Aplicar procesador FM", mensaje)
        self.lbl_estado.setText(mensaje)

    def _alternar_bypass(self, activado: bool):
        ruta, sink_captura, sink_reproduccion = self._datos_destino()
        if not sink_reproduccion:
            QMessageBox.warning(self, "Bypass", "Falta el 'Sink de salida real (hardware)'.")
            self.btn_bypass.setChecked(not activado)
            return
        self._guardar_estado()
        if activado:
            texto = procesador_audio.generar_bypass_conf(sink_captura, sink_reproduccion)
            aviso = "Va a sonar SIN NINGÚN efecto (bypass)"
        else:
            texto = procesador_audio.generar_filter_chain_conf(
                self._preset_desde_ui(), sink_captura, sink_reproduccion,
            )
            aviso = "Vuelve a aplicar los efectos de arriba"
        respuesta = QMessageBox.question(
            self, "Bypass",
            f"{aviso} -- reinicia PipeWire un instante (corta el audio de toda "
            "la PC). ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            self.btn_bypass.setChecked(not activado)
            return
        exito, mensaje = self._aplicar_texto(texto, ruta)
        if not exito:
            self.btn_bypass.setChecked(not activado)
            QMessageBox.warning(self, "Bypass", mensaje)
        else:
            self.btn_bypass.setText(
                "🔊 Quitar Bypass (volver a los efectos)" if activado else "🔇 Bypass (sin efectos)"
            )
            self.reinicio_pipewire_aplicado.emit()
        self.lbl_estado.setText(mensaje)
