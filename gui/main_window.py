"""
gui/main_window.py
--------------------------------------------------------
Ventana principal de la aplicación.
Contiene:
- Menú superior (Archivo, Edición, Ver, Reproducción, Acciones...)
- Toolbar superior con reloj en vivo.
- QSplitter horizontal con las 3 ventanas (Publicidad, Emisión,
  Explorador).
- Barra de estado inferior.
- Conexión de las ventanas con el motor de audio real (core/).
- Apertura de la Ventana Auxiliar y del Programador.
--------------------------------------------------------
"""

import os

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QLabel,
    QToolBar, QStatusBar, QMenuBar, QSizePolicy,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QAction, QKeySequence

from gui.ventana_publicidad import VentanaPublicidad
from gui.ventana_emision import VentanaEmision
from gui.ventana_explorador import VentanaExplorador
from gui.ventana_auxiliar import VentanaAuxiliar
from gui.ventana_programador import VentanaProgramador
from gui.ventana_configuracion import VentanaConfiguracion
from gui.dialogo_elegir_pisador import DialogoElegirPisador
from gui.common_widgets import configurar_columnas_ajustables
from gui import estado_ui

from core.playlist_manager import GestorPublicidad, GestorExplorador, SchedulerAutomatico
from core.gestor_emision import GestorPlaylist
from core.audio_engine import obtener_duracion_formateada
from config.settings import cargar_configuracion, registrar_evento


class MainWindow(QMainWindow):
    """Ventana raíz: agrupa las 3 ventanas principales del automatizador."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Automatizador Radio Linux - by Santiago M. Escobar - Radio Tuyú Gral. Madariaga"
        )
        self.resize(1400, 800)

        self._ventana_auxiliar = None
        self._gestor_auxiliar = None
        self._ventana_programador = None
        self._ventana_configuracion = None
        self._explorador_expandido = False
        self._tamaños_splitter_previos = None

        self._config = cargar_configuracion()

        self._construir_menu()
        self._construir_toolbar()
        self._construir_paneles_centrales()
        self._construir_status_bar()
        self._conectar_señales()
        self._inicializar_motores_audio()

        self._timer_reloj = QTimer(self)
        self._timer_reloj.timeout.connect(self._actualizar_reloj)
        self._timer_reloj.start(1000)
        self._actualizar_reloj()

    # ------------------------------------------------------------------
    # Menú superior
    # ------------------------------------------------------------------
    def _construir_menu(self):
        barra_menu: QMenuBar = self.menuBar()

        menu_archivo = barra_menu.addMenu("&Archivo")
        menu_archivo.addAction(self._crear_accion("Nueva programación", "Ctrl+N"))
        menu_archivo.addAction(self._crear_accion("Abrir programación...", "Ctrl+O"))
        menu_archivo.addAction(self._crear_accion("Guardar", "Ctrl+S"))
        menu_archivo.addSeparator()
        accion_salir = self._crear_accion("Salir", "Ctrl+Q")
        accion_salir.triggered.connect(self.close)
        menu_archivo.addAction(accion_salir)

        menu_edicion = barra_menu.addMenu("&Edición")
        menu_edicion.addAction(self._crear_accion("Deshacer", "Ctrl+Z"))
        menu_edicion.addAction(self._crear_accion("Rehacer", "Ctrl+Y"))

        menu_ver = barra_menu.addMenu("&Ver")
        menu_ver.addAction(self._crear_accion("Pantalla completa", "F11"))

        menu_reproduccion = barra_menu.addMenu("&Reproducción")
        menu_reproduccion.addAction(self._crear_accion("Play", "F5"))
        menu_reproduccion.addAction(self._crear_accion("Stop", "F6"))
        menu_reproduccion.addSeparator()
        accion_aux = self._crear_accion("Abrir ventana auxiliar (preescucha)", "Ctrl+Shift+A")
        accion_aux.triggered.connect(self.abrir_ventana_auxiliar)
        menu_reproduccion.addAction(accion_aux)

        menu_acciones = barra_menu.addMenu("&Acciones")
        accion_programador = self._crear_accion("Programador...", "Ctrl+P")
        accion_programador.triggered.connect(self.abrir_programador)
        menu_acciones.addAction(accion_programador)
        menu_acciones.addAction(self._crear_accion("Importar FMT..."))

        menu_herramientas = barra_menu.addMenu("&Herramientas")

        accion_audio = self._crear_accion("Configuración de audio...")
        accion_audio.triggered.connect(lambda: self.abrir_configuracion(0))
        menu_herramientas.addAction(accion_audio)

        accion_fade = self._crear_accion("Tiempos de Fade...")
        accion_fade.triggered.connect(lambda: self.abrir_configuracion(1))
        menu_herramientas.addAction(accion_fade)

        accion_rutas = self._crear_accion("Rutas de archivos...")
        accion_rutas.triggered.connect(lambda: self.abrir_configuracion(2))
        menu_herramientas.addAction(accion_rutas)

        accion_reproduccion = self._crear_accion("Reproducción y Automatización...")
        accion_reproduccion.triggered.connect(lambda: self.abrir_configuracion(3))
        menu_herramientas.addAction(accion_reproduccion)

        accion_general = self._crear_accion("Preferencias generales...")
        accion_general.triggered.connect(lambda: self.abrir_configuracion(4))
        menu_herramientas.addAction(accion_general)

    def _crear_accion(self, texto: str, atajo: str | None = None) -> QAction:
        accion = QAction(texto, self)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ------------------------------------------------------------------
    # Toolbar superior (con reloj)
    # ------------------------------------------------------------------
    def _construir_toolbar(self):
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self._crear_accion("Abrir"))
        toolbar.addAction(self._crear_accion("Buscar"))
        toolbar.addAction(self._crear_accion("▶ Play"))
        toolbar.addAction(self._crear_accion("● Grabar"))
        toolbar.addAction(self._crear_accion("Lista"))
        toolbar.addAction(self._crear_accion("＋ Agregar"))
        toolbar.addSeparator()

        accion_programador = self._crear_accion("📅 Programador")
        accion_programador.triggered.connect(self.abrir_programador)
        toolbar.addAction(accion_programador)

        toolbar.addSeparator()
        accion_config_toolbar = self._crear_accion("⚙ Configuración")
        accion_config_toolbar.triggered.connect(lambda: self.abrir_configuracion(0))
        toolbar.addAction(accion_config_toolbar)
        toolbar.addSeparator()

        espaciador = QWidget()
        espaciador.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(espaciador)

        self.lbl_reloj = QLabel("--/--/---- --:--:--")
        self.lbl_reloj.setStyleSheet("font-weight: bold; padding-right: 10px;")
        toolbar.addWidget(self.lbl_reloj)

    def _actualizar_reloj(self):
        ahora = QDateTime.currentDateTime()
        self.lbl_reloj.setText(ahora.toString("ddd dd/MM/yyyy hh:mm:ss"))

    # ------------------------------------------------------------------
    # Paneles centrales (las 3 ventanas)
    # ------------------------------------------------------------------
    def _construir_paneles_centrales(self):
        self.ventana_publicidad = VentanaPublicidad()
        self.ventana_emision = VentanaEmision()
        self.ventana_explorador = VentanaExplorador()

        self.splitter_principal = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_principal.setChildrenCollapsible(False)
        self.splitter_principal.addWidget(self.ventana_publicidad)
        self.splitter_principal.addWidget(self.ventana_emision)
        self.splitter_principal.addWidget(self.ventana_explorador)
        self.splitter_principal.setStretchFactor(0, 3)
        self.splitter_principal.setStretchFactor(1, 4)
        self.splitter_principal.setStretchFactor(2, 3)
        self.splitter_principal.setSizes([420, 480, 420])

        self.setCentralWidget(self.splitter_principal)

        # Modo compacto (pedido explícito): anchos por defecto más
        # angostos y un mínimo de columna bajo — antes el mínimo de
        # 45px no dejaba achicar más la columna de Publicidad.
        # Ventana 2 (Emisión) arma sus propias columnas de ajuste
        # LIBRE en panel_reproductor.py — no se toca acá.
        configurar_columnas_ajustables(self.ventana_publicidad.tree, [150, 70])
        self.ventana_publicidad.tree.header().setMinimumSectionSize(24)

        self.ventana_explorador.solicitud_alternar_expansion.connect(self._alternar_expansion_explorador)
        self.ventana_explorador.busqueda_realizada.connect(self._on_busqueda_realizada)

        self._restaurar_disposicion_guardada()

    # ------------------------------------------------------------------
    # Ventana 3 "desmontable": expandir dentro de la ventana principal
    # (colapsa Publicidad y Emisión a un costado) y volver a su lugar.
    # ------------------------------------------------------------------
    def _alternar_expansion_explorador(self):
        if not self._explorador_expandido:
            self._tamaños_splitter_previos = self.splitter_principal.sizes()
            total = sum(self._tamaños_splitter_previos) or 1200
            self.splitter_principal.setSizes([1, 1, total])
        elif self._tamaños_splitter_previos:
            self.splitter_principal.setSizes(self._tamaños_splitter_previos)

        self._explorador_expandido = not self._explorador_expandido
        self.ventana_explorador.set_expandido(self._explorador_expandido)

    def _on_busqueda_realizada(self, cantidad: int):
        if cantidad == 0:
            self.statusBar().showMessage("Sin resultados para esa búsqueda.", 4000)
        else:
            self.statusBar().showMessage(f"{cantidad} resultado(s) encontrado(s).", 4000)

    def _restaurar_disposicion_guardada(self):
        estado_ui.restaurar_geometria_ventana(self)
        estado_ui.restaurar_splitter("principal", self.splitter_principal)
        estado_ui.restaurar_splitter("explorador", self.ventana_explorador.splitter)
        estado_ui.restaurar_columnas("publicidad", self.ventana_publicidad.tree)
        estado_ui.restaurar_columnas("emision", self.ventana_emision.panel.tree)
        self.ventana_explorador.restaurar_disposicion()

    def _guardar_disposicion_actual(self):
        estado_ui.guardar_geometria_ventana(self)
        estado_ui.guardar_splitter("principal", self.splitter_principal)
        estado_ui.guardar_splitter("explorador", self.ventana_explorador.splitter)
        estado_ui.guardar_columnas("publicidad", self.ventana_publicidad.tree)
        estado_ui.guardar_columnas("emision", self.ventana_emision.panel.tree)
        self.ventana_explorador.guardar_disposicion()

    def _hay_emision_en_curso(self) -> bool:
        motores = [self.gestor_emision.motor, self.gestor_publicidad.motor]
        if self._gestor_auxiliar is not None:
            motores.append(self._gestor_auxiliar.motor)
        return any(motor.esta_reproduciendo() for motor in motores)

    def closeEvent(self, evento):
        # Pedido explícito: la música no se corta sola por nada salvo
        # Stop o cerrar el programa — y cerrar el programa avisa antes,
        # porque eso SÍ va a interrumpir la emisión al aire.
        if self._hay_emision_en_curso():
            respuesta = QMessageBox.question(
                self, "Hay una emisión en curso",
                "Se está reproduciendo audio ahora mismo (Publicidad, Emisión y/o "
                "Auxiliar).\n\nCerrar el programa va a interrumpir la emisión al aire.\n"
                "¿Confirmás que querés cerrar de todos modos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                registrar_evento("Cierre cancelado por el operador: había emisión en curso")
                evento.ignore()
                return

        self._guardar_disposicion_actual()
        if self._ventana_auxiliar is not None:
            estado_ui.guardar_columnas("auxiliar", self._ventana_auxiliar.panel.tree)
            estado_ui.guardar_geometria_ventana(self._ventana_auxiliar, "auxiliar")
        if self._ventana_programador is not None:
            estado_ui.guardar_columnas("programador", self._ventana_programador.tree)
            estado_ui.guardar_geometria_ventana(self._ventana_programador, "programador")
        super().closeEvent(evento)

    # ------------------------------------------------------------------
    # Barra de estado
    # ------------------------------------------------------------------
    def _construir_status_bar(self):
        status: QStatusBar = self.statusBar()
        self.lbl_status_modo = QLabel("Modo: MANUAL")
        self.lbl_status_materiales = QLabel("0 materiales")
        status.addWidget(self.lbl_status_modo)
        status.addPermanentWidget(self.lbl_status_materiales)

    # ------------------------------------------------------------------
    # Señales entre ventanas
    # ------------------------------------------------------------------
    def _conectar_señales(self):
        self.ventana_publicidad.automatico_cambiado.connect(self._on_automatico_cambiado)
        self.ventana_publicidad.archivo_soltado.connect(self._on_archivo_soltado_publicidad)
        self.ventana_publicidad.solicitud_abrir_programador.connect(self.abrir_programador)

        self.ventana_emision.archivo_soltado.connect(self._on_archivo_soltado_emision)
        self.ventana_emision.solicitud_abrir_auxiliar.connect(self.abrir_ventana_auxiliar)
        self.ventana_emision.solicitud_agregar_pisador.connect(
            lambda fila: self._abrir_dialogo_pisador(self.ventana_emision, fila)
        )
        self.ventana_emision.solicitud_eliminar_definitivo.connect(self._eliminar_definitivo_de_biblioteca)

        self.ventana_explorador.archivo_agregado.connect(self._on_archivo_agregado)
        self.ventana_explorador.archivo_movido.connect(self._on_archivo_movido)

    def _on_automatico_cambiado(self, activo: bool):
        self.lbl_status_modo.setText(f"Modo: {'AUTOMÁTICO' if activo else 'MANUAL'}")

    def _on_archivo_agregado(self, ruta: str):
        self.statusBar().showMessage(f"Agregado: {ruta}", 4000)

    def _on_archivo_movido(self, titulo: str, categoria_destino: str):
        self.statusBar().showMessage(f"'{titulo}' movido a: {categoria_destino}", 4000)

    # ------------------------------------------------------------------
    # Drag & Drop entrante: agrega el archivo soltado a la lista correspondiente
    # ------------------------------------------------------------------
    def _on_archivo_soltado_emision(self, ruta: str, item_destino):
        # Si es un archivo de género Pisador soltado sobre un tema
        # musical (no sobre otro Pisador), se anida como el Pisador
        # de ese tema en vez de agregarse como un tema nuevo.
        registro = self.ventana_explorador.buscar_registro_por_ruta(ruta)
        genero = (registro or {}).get("genero")
        if genero == "Pisador" and item_destino is not None and item_destino.parent() is None:
            fila = self.ventana_emision.panel.tree.indexOfTopLevelItem(item_destino)
            duracion = obtener_duracion_formateada(ruta)
            self.ventana_emision.agregar_pisador(
                fila, registro.get("titulo", os.path.basename(ruta)),
                duracion, registro.get("codigo", "—"), ruta,
            )
            self.statusBar().showMessage(f"Pisador agregado a: {item_destino.text(0)}", 3000)
            return

        titulo = os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        self.ventana_emision.agregar_item(
            titulo, duracion, "—", ruta,
            (registro or {}).get("punto_inicio_ms") or 0,
            (registro or {}).get("punto_fin_ms"),
            (registro or {}).get("ganancia_db") or 0.0,
        )
        self.statusBar().showMessage(f"Agregado a Emisión: {titulo}", 3000)

    # ------------------------------------------------------------------
    # Motor "Agregar Pisador": pide el archivo Pisador a usar (filtrado
    # por género desde la biblioteca del Explorador) y lo anida en el
    # tema elegido de la ventana que lo pidió (Emisión o Auxiliar).
    # ------------------------------------------------------------------
    def _abrir_dialogo_pisador(self, ventana, fila: int):
        registros_pisador = self.ventana_explorador.listar_registros_por_genero("Pisador")
        if not registros_pisador:
            QMessageBox.information(
                self, "Agregar Pisador",
                "No hay archivos de género 'Pisador' cargados en el Explorador todavía.\n"
                "Agregá alguno ahí (Ventana 3) con ese género antes de asignarlo.",
            )
            return

        dialogo = DialogoElegirPisador(registros_pisador, parent=self)
        if dialogo.exec() != DialogoElegirPisador.DialogCode.Accepted:
            return

        registro = dialogo.registro_elegido()
        if not registro:
            return

        duracion = obtener_duracion_formateada(registro["ruta"])
        ventana.agregar_pisador(fila, registro.get("titulo", ""), duracion, registro.get("codigo", "—"), registro["ruta"])
        self.statusBar().showMessage(f"Pisador '{registro.get('titulo', '')}' asignado.", 3000)

    # ------------------------------------------------------------------
    # "Eliminar de la biblioteca" del menú contextual de Ventana 2 /
    # Auxiliar: borra el registro completo del Explorador, no solo el
    # ítem de esa lista puntual (esa parte ya la maneja el panel).
    # ------------------------------------------------------------------
    def _eliminar_definitivo_de_biblioteca(self, ruta: str):
        eliminado = self.ventana_explorador.eliminar_registro_por_ruta(ruta)
        if eliminado:
            self.statusBar().showMessage(f"Eliminado de la biblioteca: {os.path.basename(ruta)}", 4000)
        else:
            self.statusBar().showMessage("Ese archivo no estaba registrado en la biblioteca del Explorador.", 4000)

    def _on_archivo_soltado_publicidad(self, ruta: str, item_destino):
        registro = self.ventana_explorador.buscar_registro_por_ruta(ruta)
        titulo = (registro or {}).get("titulo") or os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        codigo = (registro or {}).get("codigo", "—")

        bloque = item_destino
        while bloque is not None and bloque.parent() is not None:
            bloque = bloque.parent()
        if bloque is None:
            if self.ventana_publicidad.tree.topLevelItemCount() == 0:
                self.statusBar().showMessage("Creá primero un bloque horario en Publicidad.", 4000)
                return
            bloque = self.ventana_publicidad.tree.topLevelItem(0)

        self.ventana_publicidad.agregar_tanda(
            bloque, titulo, duracion, codigo, ruta,
            (registro or {}).get("punto_inicio_ms") or 0,
            (registro or {}).get("punto_fin_ms"),
            (registro or {}).get("ganancia_db") or 0.0,
        )
        bloque.setExpanded(True)
        self.statusBar().showMessage(f"Agregado a Publicidad: {titulo}", 3000)

    def _on_archivo_soltado_auxiliar(self, ruta: str, item_destino):
        registro = self.ventana_explorador.buscar_registro_por_ruta(ruta)
        genero = (registro or {}).get("genero")
        if genero == "Pisador" and item_destino is not None and item_destino.parent() is None:
            fila = self._ventana_auxiliar.panel.tree.indexOfTopLevelItem(item_destino)
            duracion = obtener_duracion_formateada(ruta)
            self._ventana_auxiliar.agregar_pisador(
                fila, registro.get("titulo", os.path.basename(ruta)),
                duracion, registro.get("codigo", "—"), ruta,
            )
            return

        titulo = os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        self._ventana_auxiliar.agregar_item(
            titulo, duracion, "—", ruta,
            (registro or {}).get("punto_inicio_ms") or 0,
            (registro or {}).get("punto_fin_ms"),
            (registro or {}).get("ganancia_db") or 0.0,
        )

    # ------------------------------------------------------------------
    # Motor de audio real (core/)
    # ------------------------------------------------------------------
    def _inicializar_motores_audio(self):
        audio = self._config["audio"]
        reproduccion = self._config["reproduccion"]
        fade = self._config["fade"]

        id_dispositivo_master = audio["dispositivo_master"] if audio["dispositivo_master"] != "default" else None

        self.gestor_emision = GestorPlaylist(
            self.ventana_emision,
            id_dispositivo=id_dispositivo_master,
            avanzar_en_error=reproduccion["avanzar_automaticamente_en_error"],
            reintentos_maximos=reproduccion["reintentos_antes_de_detener"],
            repetir_al_finalizar=reproduccion["repetir_lista_al_finalizar"],
            bajada_db_pisador=reproduccion["pisador_bajada_db"],
            crossfade_activado=fade["crossfade_activado"],
            duracion_fade_segundos=fade["duracion_fade_segundos"],
            persistir=True,
        )
        self.gestor_publicidad = GestorPublicidad(
            self.ventana_publicidad,
            id_dispositivo=id_dispositivo_master,
            avanzar_en_error=reproduccion["avanzar_automaticamente_en_error"],
            reintentos_maximos=reproduccion["reintentos_antes_de_detener"],
            persistir=True,
        )

        self.gestor_emision.set_volumen_base(audio["volumen_master"])
        self.gestor_publicidad.set_volumen_base(audio["volumen_master"])

        self.gestor_explorador = GestorExplorador(self.ventana_explorador, id_dispositivo=id_dispositivo_master)

        if reproduccion["modo_automatico_al_iniciar"]:
            self.ventana_publicidad.btn_automatico.setChecked(True)
            self.ventana_publicidad._toggle_automatico()

        if getattr(self, "scheduler_automatico", None) is not None:
            self.scheduler_automatico.detener()
        self.scheduler_automatico = SchedulerAutomatico(
            self.ventana_publicidad, self.gestor_publicidad, self.gestor_emision
        )

        if not self.gestor_emision.motor.esta_disponible():
            self.statusBar().showMessage(
                "VLC no está instalado — la reproducción está deshabilitada "
                "(sudo apt install vlc libvlc-dev). La interfaz funciona igual.",
                8000,
            )

    def _aplicar_configuracion_en_vivo(self):
        """Aplica la configuración recién guardada SIN recrear ni
        detener nada — pedido explícito: la música no se interrumpe
        por guardar Configuración, solo por Stop o cerrar el programa.

        Antes esto llamaba _inicializar_motores_audio() de nuevo, que
        creaba objetos MotorAudio NUEVOS (silenciosos) y de paso
        llamaba .detener() a los que estaban sonando — cortaba
        cualquier reproducción en curso. Ahora se actualizan los
        atributos de los gestores YA EXISTENTES en caliente, y el
        dispositivo de salida se cambia con
        MotorAudio.set_dispositivo_salida() sobre el motor que ya
        está reproduciendo (sin recrearlo) — libVLC tolera cambiar de
        dispositivo sin cortar la reproducción."""
        self._config = cargar_configuracion()
        audio = self._config["audio"]
        reproduccion = self._config["reproduccion"]
        fade = self._config["fade"]
        id_dispositivo_master = audio["dispositivo_master"] if audio["dispositivo_master"] != "default" else None

        for gestor in (self.gestor_emision, self._gestor_auxiliar):
            if gestor is None:
                continue
            gestor.avanzar_en_error = reproduccion["avanzar_automaticamente_en_error"]
            gestor.reintentos_maximos = max(1, reproduccion["reintentos_antes_de_detener"])
            gestor.repetir_al_finalizar = reproduccion["repetir_lista_al_finalizar"]
            gestor.bajada_db_pisador = reproduccion["pisador_bajada_db"]
            gestor.crossfade_activado = fade["crossfade_activado"]
            gestor.duracion_fade_segundos = fade["duracion_fade_segundos"]
            for motor in (gestor.motor, gestor.motor_pisador):
                if motor.id_dispositivo() != id_dispositivo_master:
                    motor.set_dispositivo_salida(id_dispositivo_master)

        self.gestor_emision.set_volumen_base(audio["volumen_master"])
        if self._gestor_auxiliar is not None:
            self._gestor_auxiliar.set_volumen_base(audio["volumen_master"])

        self.gestor_publicidad.avanzar_en_error = reproduccion["avanzar_automaticamente_en_error"]
        self.gestor_publicidad.reintentos_maximos = max(1, reproduccion["reintentos_antes_de_detener"])
        if self.gestor_publicidad.motor.id_dispositivo() != id_dispositivo_master:
            self.gestor_publicidad.motor.set_dispositivo_salida(id_dispositivo_master)
        self.gestor_publicidad.set_volumen_base(audio["volumen_master"])

        if self.gestor_explorador.motor.id_dispositivo() != id_dispositivo_master:
            self.gestor_explorador.motor.set_dispositivo_salida(id_dispositivo_master)

        self.ventana_explorador.repintar_colores_genero()

    # ------------------------------------------------------------------
    # Ventana auxiliar flotante (preescucha / reproducción secundaria)
    # ------------------------------------------------------------------
    def abrir_ventana_auxiliar(self):
        if self._ventana_auxiliar is None:
            audio = self._config["audio"]
            reproduccion = self._config["reproduccion"]
            fade = self._config["fade"]
            id_dispositivo_master = audio["dispositivo_master"] if audio["dispositivo_master"] != "default" else None

            self._ventana_auxiliar = VentanaAuxiliar(self)
            # Ventana Auxiliar arma sus propias columnas de ajuste LIBRE
            # en panel_reproductor.py — solo se restaura lo guardado.
            estado_ui.restaurar_columnas("auxiliar", self._ventana_auxiliar.panel.tree)
            estado_ui.restaurar_geometria_ventana(self._ventana_auxiliar, "auxiliar")

            self._gestor_auxiliar = GestorPlaylist(
                self._ventana_auxiliar,
                id_dispositivo=id_dispositivo_master,
                avanzar_en_error=reproduccion["avanzar_automaticamente_en_error"],
                reintentos_maximos=reproduccion["reintentos_antes_de_detener"],
                repetir_al_finalizar=reproduccion["repetir_lista_al_finalizar"],
                bajada_db_pisador=reproduccion["pisador_bajada_db"],
                crossfade_activado=fade["crossfade_activado"],
                duracion_fade_segundos=fade["duracion_fade_segundos"],
            )
            self._gestor_auxiliar.set_volumen_base(audio["volumen_master"])
            self._ventana_auxiliar.archivo_soltado.connect(self._on_archivo_soltado_auxiliar)
            self._ventana_auxiliar.solicitud_agregar_pisador.connect(
                lambda fila: self._abrir_dialogo_pisador(self._ventana_auxiliar, fila)
            )
            self._ventana_auxiliar.solicitud_eliminar_definitivo.connect(self._eliminar_definitivo_de_biblioteca)

        self._ventana_auxiliar.show()
        self._ventana_auxiliar.raise_()
        self._ventana_auxiliar.activateWindow()

    # ------------------------------------------------------------------
    # Programador de emisión
    # ------------------------------------------------------------------
    def abrir_programador(self):
        if self._ventana_programador is None:
            self._ventana_programador = VentanaProgramador(self)
            configurar_columnas_ajustables(self._ventana_programador.tree, [200, 90])
            self._ventana_programador.tree.header().setMinimumSectionSize(45)
            estado_ui.restaurar_columnas("programador", self._ventana_programador.tree)
            estado_ui.restaurar_geometria_ventana(self._ventana_programador, "programador")

        self._ventana_programador.show()
        self._ventana_programador.raise_()
        self._ventana_programador.activateWindow()

    # ------------------------------------------------------------------
    # Configuración general
    # ------------------------------------------------------------------
    def abrir_configuracion(self, pestaña: int = 0):
        dialogo = VentanaConfiguracion(self, pestaña_inicial=pestaña)
        if dialogo.exec() == VentanaConfiguracion.DialogCode.Accepted:
            self._aplicar_configuracion_en_vivo()
            self.statusBar().showMessage("Configuración guardada y aplicada (sin cortar la reproducción).", 4000)
