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
    QToolBar, QStatusBar, QSizePolicy, QToolButton, QMenu,
    QMessageBox, QApplication, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QAction, QKeySequence

from gui.ventana_publicidad import VentanaPublicidad
from gui.ventana_emision import VentanaEmision
from gui.ventana_explorador import VentanaExplorador
from gui.ventana_auxiliar import VentanaAuxiliar
from gui.ventana_programador import VentanaProgramador
from gui.ventana_musicalizador import VentanaMusicalizador
from gui.ventana_configuracion import VentanaConfiguracion
from gui.dialogo_elegir_pisador import DialogoElegirPisador
from gui.dialogo_listas_auxiliar import DialogoListasAuxiliar
from gui.dialogo_seleccionar_biblioteca import DialogoSeleccionarBiblioteca
from gui.dialogo_seleccionar_categoria import DialogoSeleccionarCategoria
from gui.common_widgets import configurar_columnas_ajustables
from gui.styles import qss_para_tema
from gui import estado_ui

from core.playlist_manager import GestorPublicidad, GestorExplorador, SchedulerAutomatico
from core.gestor_emision import GestorPlaylist
from core.audio_engine import obtener_duracion_formateada
from core.clima_meteo import RefrescadorClima, LATITUD_DEFECTO, LONGITUD_DEFECTO
from core import actualizador
from config.settings import (
    cargar_configuracion, registrar_evento,
    guardar_lista_auxiliar, listar_listas_auxiliares,
    obtener_lista_auxiliar, eliminar_lista_auxiliar,
    rutas_recientes_en_historial,
)


class MainWindow(QMainWindow):
    """Ventana raíz: agrupa las 3 ventanas principales del automatizador."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Automatizador Radio Linux - by Santiago M. Escobar - Radio Tuyú Gral. Madariaga"
        )
        # Pedido explícito ("el programa detecte el tamaño de
        # resolución del display y se ajuste a ello, sí o sí"): el
        # tamaño de arranque (usado la primera vez, sin geometría
        # guardada todavía) se calcula CONTRA la pantalla real en vez
        # de un 1400x800 fijo — en una notebook con display más chico
        # que eso (ej. 1366x768, hardware modesto tipo el de Santiago),
        # el tamaño fijo ya arrancaba más grande que la pantalla. Un
        # piso bajo (900x550) evita que la ventana quede reducida a
        # una tira inutilizable en un display muy chico.
        self.setMinimumSize(900, 550)
        pantalla = QApplication.primaryScreen()
        disponible = pantalla.availableGeometry() if pantalla else None
        if disponible is not None:
            self.resize(min(1400, disponible.width()), min(800, disponible.height()))
        else:
            self.resize(1400, 800)

        self._ventana_auxiliar = None
        self._gestor_auxiliar = None
        self._ventana_programador = None
        self._ventana_musicalizador = None
        self._ventana_configuracion = None
        self._explorador_expandido = False
        self._tamaños_splitter_previos = None
        self._cerrando_por_actualizacion = False
        self._preload_activo = False
        self._proceso_buscar_actualizacion = None

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

        self._mostrar_preload("Cargando Auto-Radio Tuyú...")

        # Pedido explícito ("que lo lea en off y lo tenga guardado de
        # antemano... que no interrumpa la emisión ni demore la
        # carga"): el clima del Comando HTH se refresca solo, en
        # segundo plano y de forma asíncrona (QNetworkAccessManager,
        # nunca bloquea), mucho antes de que la rotativa lo necesite —
        # ver core/clima_meteo.py.
        self._refrescador_clima = RefrescadorClima(self._coordenadas_clima_actuales)
        self._refrescador_clima.iniciar()

        # Pedido explícito: buscar actualización SOLA al abrir el
        # programa (antes solo se buscaba a mano, en Configuración →
        # Actualizaciones). Ahora corre en un QProcess asíncrono (ver
        # core/actualizador.buscar_actualizacion_async) — como ya NO
        # puede congelar nada, el defer de 2.5s (mismo de siempre) es
        # solo para no competir con el arranque de la radio, no por
        # miedo a que bloquee. Se mantiene deliberadamente largo (no
        # se achicó): varios scripts de test bombean el event loop por
        # un par de segundos para procesar timers diferidos (fades,
        # etc.) sin esperar disparar esto — un defer corto dispara un
        # `git fetch` REAL contra el repo en medio de esos tests.
        QTimer.singleShot(2500, self._buscar_actualizacion_automatica)

        # Pedido explícito ("veo que nunca funciona el recorte de
        # silencio") -- bug real de fondo: un fallo del motor de
        # marcas IN/OUT (pydub/ffmpeg) se descubría recién cuando
        # Santiago notaba que un tema sonaba sin recortar, sin ningún
        # aviso -- el análisis fallido solo imprimía a una consola que
        # nadie ve al lanzar desde el ícono de escritorio. Esta
        # verificación corre SOLA al abrir (diferida 3s, mismo defer
        # largo que la búsqueda de actualización, por el mismo motivo:
        # varios tests bombean el event loop un par de segundos sin
        # querer disparar esto) y avisa, NO MODAL, solo si algo falla
        # -- si todo está en orden, no interrumpe nada.
        QTimer.singleShot(3000, self._verificar_motor_analisis_al_iniciar)

    # ------------------------------------------------------------------
    # Menú superior
    # ------------------------------------------------------------------
    def _construir_menu(self):
        # Pedido explícito ("los menú de arriba son también dobles" —
        # el QMenuBar clásico ocupaba una fila entera aparte de la
        # toolbar, achicando el espacio real para las listas). Auditado
        # antes de sacarlo: casi todos sus ítems (Nueva programación/
        # Abrir/Guardar/Deshacer/Rehacer/Pantalla completa/Play/Stop del
        # menú) nunca tuvieron un handler conectado — no hacían nada al
        # clickear. "Salir" se preserva como atajo de teclado sin fila
        # de menú visible (`self.addAction`, funciona igual con
        # `QMainWindow` sin pasar por `menuBar()`); "Auxiliar" pasó a
        # ser un botón visible en la toolbar (pedido explícito, ver
        # `_construir_toolbar` — antes vivía DENTRO de Ventana 2, "no
        # hace falta que esté ahí... dará mayor posibilidad de ampliar
        # la ventana 3 a gusto"), pero la acción se arma acá para que
        # el atajo Ctrl+Shift+A siga andando en los dos lugares con el
        # mismo objeto. El resto de la navegación real (Programador/
        # Musicalizador/Configuración) vive en esa misma toolbar de una
        # sola fila. Nunca se llama a `self.menuBar()`, así Qt no
        # reserva esa fila en absoluto.
        accion_salir = self._crear_accion("Salir", "Ctrl+Q")
        accion_salir.triggered.connect(self.close)
        self.addAction(accion_salir)

        self._accion_auxiliar = self._crear_accion("🎧 Auxiliar", "Ctrl+Shift+A")
        self._accion_auxiliar.triggered.connect(self.abrir_ventana_auxiliar)

    def _crear_accion(self, texto: str, atajo: str | None = None) -> QAction:
        accion = QAction(texto, self)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ------------------------------------------------------------------
    # Toolbar superior (con reloj)
    # ------------------------------------------------------------------
    def _construir_toolbar(self):
        # Pedido explícito ("rediseño compacto, juntar lo que puede
        # estar junto"): esta es ahora la ÚNICA fila de navegación de
        # arriba (ver _construir_menu, que ya no muestra ningún
        # QMenuBar). Se sacaron los botones "Abrir/Buscar/▶ Play/
        # ● Grabar/Lista/＋ Agregar" — auditados, ninguno tenía handler
        # conectado, eran puro relleno decorativo sin función real.
        toolbar = QToolBar("Principal")
        toolbar.setObjectName("toolbarPrincipal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        accion_programador = self._crear_accion("📅 Programador")
        accion_programador.triggered.connect(self.abrir_programador)
        toolbar.addAction(accion_programador)

        accion_musicalizador_toolbar = self._crear_accion("🎵 Musicalizador")
        accion_musicalizador_toolbar.triggered.connect(self.abrir_musicalizador)
        toolbar.addAction(accion_musicalizador_toolbar)

        toolbar.addSeparator()

        # Auxiliar (pedido explícito: "podría estar arriba al lado de
        # Configuración... no hace falta que esté ahí [Ventana 2],
        # eso dará mayor posibilidad de ampliar la ventana 3 a
        # gusto") — antes era un botón DENTRO del panel de Ventana 2
        # (`panel_reproductor.py`), ocupando ancho ahí; movido acá no
        # le pide ancho mínimo a Ventana 2, dejando más margen para
        # angostarla y agrandar el Explorador.
        toolbar.addAction(self._accion_auxiliar)
        toolbar.addSeparator()

        # Configuración: antes un botón simple (siempre abría la
        # pestaña de Audio) — ahora un desplegable con las 5 pestañas,
        # reemplazando al viejo menú "Herramientas" que tenía los
        # mismos 5 accesos (mismo contenido, una fila menos).
        boton_config = QToolButton()
        boton_config.setText("⚙ Configuración")
        boton_config.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_config = QMenu(boton_config)
        for texto, indice_tab in (
            ("Configuración de audio...", 0),
            ("Tiempos de Fade...", 1),
            ("Rutas de archivos...", 2),
            ("Reproducción y Automatización...", 3),
            ("Preferencias generales...", 4),
        ):
            accion_tab = self._crear_accion(texto)
            accion_tab.triggered.connect(lambda checked=False, i=indice_tab: self.abrir_configuracion(i))
            menu_config.addAction(accion_tab)
        boton_config.setMenu(menu_config)
        toolbar.addWidget(boton_config)
        toolbar.addSeparator()

        espaciador = QWidget()
        espaciador.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(espaciador)

        # Nombre de emisora (pedido explícito, editable en Configuración
        # → General) a la izquierda del reloj — reemplaza el cartel fijo
        # "RADIO TUYÚ FM 92.5" que antes se repetía en cada panel,
        # liberando esa fila para ver más ítems de la lista.
        self.lbl_nombre_emisora = QLabel("")
        self.lbl_nombre_emisora.setObjectName("lblNombreEstacion")
        self.lbl_nombre_emisora.setStyleSheet("padding-right: 10px;")
        toolbar.addWidget(self.lbl_nombre_emisora)
        self._actualizar_nombre_emisora()

        self.lbl_reloj = QLabel("--/--/---- --:--:--")
        self.lbl_reloj.setStyleSheet("font-weight: bold; padding-right: 10px;")
        toolbar.addWidget(self.lbl_reloj)

    def _actualizar_nombre_emisora(self):
        self.lbl_nombre_emisora.setText(self._config.get("general", {}).get("nombre_emisora", "") or "")

    def _actualizar_reloj(self):
        ahora = QDateTime.currentDateTime()
        self.lbl_reloj.setText(ahora.toString("ddd dd/MM/yyyy hh:mm:ss"))

    # ------------------------------------------------------------------
    # Clima del Comando HTH (pedido explícito, ver core/clima_meteo.py):
    # coordenadas ACTUALES para el refresco en segundo plano — se
    # vuelve a leer la config en cada refresco (no una copia fija al
    # arrancar), así un cambio en Configuración → General se aplica
    # solo, sin reiniciar la app.
    # ------------------------------------------------------------------
    def _coordenadas_clima_actuales(self):
        seccion_clima = cargar_configuracion().get("clima", {})
        latitud = seccion_clima.get("latitud")
        longitud = seccion_clima.get("longitud")
        return (
            latitud if latitud is not None else LATITUD_DEFECTO,
            longitud if longitud is not None else LONGITUD_DEFECTO,
        )

    # ------------------------------------------------------------------
    # Paneles centrales (las 3 ventanas)
    # ------------------------------------------------------------------
    def _construir_paneles_centrales(self):
        self.ventana_publicidad = VentanaPublicidad()
        self.ventana_emision = VentanaEmision()
        self.ventana_explorador = VentanaExplorador()
        # Pedido explícito: Agregar/Reemplazar Item en el menú
        # contextual de Ventana 1 necesita el Explorador para el
        # buscador de biblioteca — se setea acá porque se construye
        # DESPUÉS de Ventana 1.
        self.ventana_publicidad.set_ventana_explorador(self.ventana_explorador)

        self.splitter_principal = QSplitter(Qt.Orientation.Horizontal)
        # Bug real corregido (pedido explícito, "el maximizado se va de
        # pantalla, no toma el ancho del display" en 3 computadoras
        # distintas): mismo motivo que el splitter interno de Ventana 3
        # (ver ventana_explorador.py) — con `childrenCollapsible=False`
        # este splitter (Publicidad/Emisión/Explorador) nunca deja que
        # sus 3 paneles bajen de su ancho mínimo natural, y eso fija un
        # piso de ancho para TODA la ventana principal — en una pantalla
        # más chica que ese piso, ni maximizar ni ningún resize() podían
        # angostarla lo suficiente (Qt ignora un tamaño pedido por
        # debajo del mínimo impuesto). `True` deja que el splitter
        # comprima sus paneles más allá de su tamaño "cómodo" en vez de
        # bloquear el resize entero.
        self.splitter_principal.setChildrenCollapsible(True)
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
        # Pedido explícito ("una barra de preload, que sepa que la PC
        # está trabajando"): ver Ventana 3 -> solicitud_preload, emitida
        # al armar de golpe una vista grande de tree_archivos (miles de
        # ítems con una biblioteca de ~10-12mil archivos) — reusa el
        # mismo mecanismo de preload de siempre, sin agregar uno nuevo.
        self.ventana_explorador.solicitud_preload.connect(self._mostrar_preload)

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
        estado_ui.restaurar_geometria_ventana(self, maximizar_si_es_nueva=True)
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

    def preparar_cierre_por_actualizacion(self):
        """El reinicio por actualización YA pide su propia confirmación
        en Configuración → Actualizaciones — pedido explícito: en ese
        caso no hay que preguntar OTRA VEZ por la emisión en curso al
        cerrar (el layout y demás guardados del cierre se hacen igual)."""
        self._cerrando_por_actualizacion = True

    def closeEvent(self, evento):
        # Pedido explícito (robustez de emisión): cerrar el programa
        # SIEMPRE pide confirmación — esto es una radio al aire y un
        # cierre accidental corta la emisión. Si además hay audio
        # sonando ahora mismo, el texto lo advierte explícitamente.
        # Única excepción: el reinicio por actualización, que ya pidió
        # su propia confirmación en Configuración → Actualizaciones.
        if not self._cerrando_por_actualizacion:
            if self._hay_emision_en_curso():
                titulo = "Hay una emisión en curso"
                texto = (
                    "Se está reproduciendo audio ahora mismo (Publicidad, Emisión y/o "
                    "Auxiliar).\n\nCerrar el programa va a CORTAR la emisión al aire.\n"
                    "¿Confirmás que querés cerrar de todos modos?"
                )
            else:
                titulo = "Cerrar el programa"
                texto = (
                    "Vas a cerrar el automatizador de la radio.\n"
                    "¿Confirmás que querés cerrar el programa?"
                )
            respuesta = QMessageBox.question(
                self, titulo, texto,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                registrar_evento("Cierre cancelado por el operador")
                evento.ignore()
                return

        # Pedido explícito ("el JSON parece trabarse... con 10-12mil
        # archivos"): la mayoría de las mutaciones de la biblioteca
        # (Ventana 3) ahora se guardan DEBOUNCED (ver
        # `VentanaExplorador._guardar_biblioteca_debounced`) para no
        # reescribir el archivo entero ante cada click — acá se fuerza
        # el guardado YA MISMO si había uno pendiente, para no perder
        # la última ráfaga de cambios al cerrar el programa antes de
        # que el timer del debounce llegara a disparar solo.
        self.ventana_explorador.flush_biblioteca_pendiente()

        self._guardar_disposicion_actual()
        if self._ventana_auxiliar is not None:
            estado_ui.guardar_columnas("auxiliar", self._ventana_auxiliar.panel.tree)
            estado_ui.guardar_geometria_ventana(self._ventana_auxiliar, "auxiliar")
        if self._ventana_programador is not None:
            estado_ui.guardar_columnas("programador", self._ventana_programador.tree)
            estado_ui.guardar_geometria_ventana(self._ventana_programador, "programador")
        if self._ventana_musicalizador is not None:
            estado_ui.guardar_geometria_ventana(self._ventana_musicalizador, "musicalizador")
        super().closeEvent(evento)

    # ------------------------------------------------------------------
    # Barra de estado
    # ------------------------------------------------------------------
    def _construir_status_bar(self):
        status: QStatusBar = self.statusBar()
        # Pedido explícito (ronda posterior): la leyenda "Modo Manual"/
        # "Automático Activo" (roja cuando está activo) de Ventana 1
        # se movió ACÁ, reemplazando la vieja leyenda duplicada "Modo:
        # AUTOMÁTICO"/"Modo: MANUAL" — reusa el mismo objectName/QSS
        # que ya tenía `VentanaPublicidad.lbl_estado`
        # (`lblEstadoAutomatico[activo="true"/"false"]`), así el color
        # rojo sale gratis sin QSS nuevo.
        self.lbl_status_modo = QLabel("Modo Manual")
        self.lbl_status_modo.setObjectName("lblEstadoAutomatico")
        self.lbl_status_modo.setProperty("activo", "false")
        self.lbl_status_materiales = QLabel("0 materiales")
        status.addWidget(self.lbl_status_modo)
        status.addPermanentWidget(self.lbl_status_materiales)

    # ------------------------------------------------------------------
    # "Preload" (pedido explícito): indicador visual breve de carga —
    # cursor de espera + mensaje en la barra de estado, se retira solo.
    # Se dispara al iniciar el programa, al cargar música (Ventana 3)
    # y al cargar una programación (Ventana 1, cualquier vía: manual,
    # scheduler de medianoche/arranque, o "Aplicar ahora").
    # ------------------------------------------------------------------
    def _mostrar_preload(self, texto: str, duracion_ms: int = 900):
        if not self._preload_activo:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self._preload_activo = True
        # Con timeout propio (en vez de showMessage sin límite + un
        # clearMessage() diferido): así, si justo después se muestra
        # OTRO mensaje de estado (ej. "Agregado: ..."), este preload
        # nunca se lo borra antes de tiempo.
        self.statusBar().showMessage(texto, duracion_ms)
        QTimer.singleShot(duracion_ms, self._ocultar_preload)

    def _ocultar_preload(self):
        if self._preload_activo:
            QApplication.restoreOverrideCursor()
            self._preload_activo = False

    # ------------------------------------------------------------------
    # Buscar actualización SOLA al abrir el programa (pedido explícito)
    # ------------------------------------------------------------------
    def _buscar_actualizacion_automatica(self):
        """Antes solo se buscaba a mano en Configuración →
        Actualizaciones — ahora también se chequea sola al abrir. Corre
        con `actualizador.buscar_actualizacion_async()` — pedido
        explícito ("no debe impedir la reproducción inmediata y con
        automático activado"): el único paso lento de esto es de red
        (git fetch), y antes corría SINCRÓNICO en el mismo hilo que la
        radio — con una conexión lenta, eso podía congelar la app
        entera (incluida música ya sonando) hasta 30s. Ahora es un
        QProcess asíncrono: nunca bloquea nada, la radio sigue su
        curso normal mientras se resuelve en segundo plano. Se guarda
        la referencia en self._proceso_buscar_actualizacion para que
        Python no lo recolecte a mitad de camino."""
        self._mostrar_preload("Buscando actualización...", duracion_ms=500)
        self._proceso_buscar_actualizacion = actualizador.buscar_actualizacion_async(
            self._on_resultado_busqueda_actualizacion
        )

    def _on_resultado_busqueda_actualizacion(self, hay_actualizacion: bool, mensaje: str):
        self._proceso_buscar_actualizacion = None
        if not hay_actualizacion:
            registrar_evento(f"Buscar actualización automática: {mensaje}")
            return

        registrar_evento("Buscar actualización automática: hay una disponible.")
        if not self._preguntar_actualizar_ahora():
            return

        self._mostrar_preload("Descargando actualización...", duracion_ms=500)
        exito, mensaje_aplicar = actualizador.aplicar_actualizacion()
        if not exito:
            QMessageBox.warning(self, "Actualizar", mensaje_aplicar)
            return

        QMessageBox.information(self, "Actualizar", "Actualización aplicada. La aplicación se va a reiniciar.")
        # Mismo flag que ya usa el botón manual de Configuración: evita
        # que closeEvent vuelva a preguntar por la emisión en curso.
        self.preparar_cierre_por_actualizacion()
        actualizador.reiniciar_aplicacion(QApplication.instance())

    def _preguntar_actualizar_ahora(self) -> bool:
        """Extraído aparte (en vez de en línea dentro de
        _buscar_actualizacion_automatica) para poder testear la
        decisión sin simular un click real sobre un QMessageBox real
        — offscreen no puede. Botones con texto propio en vez de Sí/No
        genérico, pedido explícito: "preguntar si desea actualizar
        ahora o luego"."""
        caja = QMessageBox(self)
        caja.setWindowTitle("Actualización disponible")
        caja.setText(
            "Hay una actualización disponible para Auto-Radio Tuyú.\n"
            "¿Querés actualizarla ahora? La aplicación se va a reiniciar sola."
        )
        boton_ahora = caja.addButton("Actualizar ahora", QMessageBox.ButtonRole.AcceptRole)
        boton_luego = caja.addButton("Más tarde", QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(boton_luego)
        caja.exec()
        return caja.clickedButton() is boton_ahora

    # ------------------------------------------------------------------
    # Señales entre ventanas
    # ------------------------------------------------------------------
    def _conectar_señales(self):
        self.ventana_publicidad.automatico_cambiado.connect(self._on_automatico_cambiado)
        self.ventana_publicidad.archivo_soltado.connect(self._on_archivo_soltado_publicidad)
        self.ventana_publicidad.solicitud_abrir_programador.connect(self.abrir_programador)
        self.ventana_publicidad.solicitud_cargar_programacion_hoy.connect(self._cargar_programacion_de_hoy_manual)
        self.ventana_publicidad.programacion_cargada.connect(
            lambda: self._mostrar_preload("Cargando programación...")
        )

        self.ventana_emision.archivo_soltado.connect(self._on_archivo_soltado_emision)
        self.ventana_emision.solicitud_agregar_pisador.connect(
            lambda fila: self._abrir_dialogo_pisador(self.ventana_emision, fila)
        )
        self.ventana_emision.solicitud_agregar_ciclo_fmt.connect(self._agregar_ciclo_fmt_emision)

        self.ventana_explorador.archivo_agregado.connect(self._on_archivo_agregado)
        self.ventana_explorador.archivo_movido.connect(self._on_archivo_movido)
        self.ventana_explorador.archivo_copiado.connect(self._on_archivo_copiado)
        self.ventana_explorador.categoria_renombrada.connect(self._on_categoria_renombrada)

    def _on_automatico_cambiado(self, activo: bool):
        self.lbl_status_modo.setText("Automático Activo" if activo else "Modo Manual")
        self.lbl_status_modo.setProperty("activo", "true" if activo else "false")
        self.lbl_status_modo.style().unpolish(self.lbl_status_modo)
        self.lbl_status_modo.style().polish(self.lbl_status_modo)
        # Pedido explícito (robustez de emisión): mientras el
        # Automático está activo, el STOP de Emisión (Ventana 2)
        # queda deshabilitado — igual que el de Publicidad, que se
        # deshabilita en VentanaPublicidad._toggle_automatico(). La
        # Auxiliar no se toca (es preescucha, no el aire).
        self.ventana_emision.set_stop_habilitado(not activo)

    def _avisar_sin_bloque_horario(self):
        """Aviso del arranque automático (pedido explícito, texto
        textual de Santiago): no hay bloque horario vigente en la
        programación al abrir. NO es modal-bloqueante (show(), no
        exec()): Emisión arranca sola inmediatamente después de este
        aviso y no debe quedar esperando un click en OK."""
        registrar_evento("Inicio: no se encontró bloque horario vigente en la programación")
        self.statusBar().showMessage(
            "No se encontró Bloque Horario en este momento en la programación.", 10000
        )
        self._aviso_sin_bloque = QMessageBox(self)
        self._aviso_sin_bloque.setIcon(QMessageBox.Icon.Warning)
        self._aviso_sin_bloque.setWindowTitle("Programación")
        self._aviso_sin_bloque.setText(
            "No se encontró Bloque Horario en este momento en la programación"
        )
        self._aviso_sin_bloque.setStandardButtons(QMessageBox.StandardButton.Ok)
        self._aviso_sin_bloque.show()

    def _verificar_motor_analisis_al_iniciar(self):
        """Ver comentario en __init__. Corre la prueba real (audio
        sintético en memoria, sin tocar la biblioteca) y avisa NO
        MODAL solo si falla -- con todo en orden no hace nada, no
        interrumpe el arranque."""
        from core.analizador_audio import verificar_motor_disponible

        resultado = verificar_motor_disponible()
        if resultado["prueba_ok"]:
            return

        registrar_evento(f"Verificación de motor de análisis de audio al iniciar: {resultado['mensaje']}")
        self.statusBar().showMessage(
            "El motor de marcas IN/OUT (recorte de silencio) no está funcionando -- ver Configuración → Diagnóstico.",
            10000,
        )
        self._aviso_motor_analisis = QMessageBox(self)
        self._aviso_motor_analisis.setIcon(QMessageBox.Icon.Warning)
        self._aviso_motor_analisis.setWindowTitle("Motor de análisis de audio")
        self._aviso_motor_analisis.setText(
            "El motor de marcas IN/OUT (recorte de silencio y nivelado) no está "
            "funcionando en esta instalación:\n\n"
            f"{resultado['mensaje']}\n\n"
            "Mientras tanto, la música se reproduce SIN recorte de silencio ni "
            "nivelado. Podés volver a verificarlo en cualquier momento desde "
            "Configuración → Diagnóstico → \"Verificar motor de análisis de audio\"."
        )
        self._aviso_motor_analisis.setStandardButtons(QMessageBox.StandardButton.Ok)
        self._aviso_motor_analisis.show()

    def _on_archivo_agregado(self, ruta: str):
        self._mostrar_preload("Cargando música...")
        self.statusBar().showMessage(f"Agregado: {ruta}", 4000)

    def _on_archivo_movido(self, titulo: str, categoria_destino: str):
        self.statusBar().showMessage(f"'{titulo}' movido a: {categoria_destino}", 4000)

    def _on_archivo_copiado(self, titulo: str, categoria_destino: str):
        self.statusBar().showMessage(f"'{titulo}' copiado a: {categoria_destino}", 4000)

    def _on_categoria_renombrada(self, ruta_vieja: list, ruta_nueva: list):
        # config.settings.corregir_referencias_categoria_renombrada()
        # ya corrigió lo persistido en disco (playlist_publicidad.json/
        # programacion.json/musicalizador.json, ver
        # VentanaExplorador._renombrar_categoria) -- esto corrige
        # además el árbol de bloques que Ventana 1 tiene YA CARGADO en
        # memoria, el que de verdad conduce la emisión en este
        # instante, sin esperar a un reinicio.
        tocados = self.ventana_publicidad.corregir_categoria_aleatorio_en_vivo(ruta_vieja, ruta_nueva)
        if tocados:
            self.statusBar().showMessage(
                f"Categoría renombrada: {tocados} ítem(s) Aleatorio de Ventana 1 actualizados en vivo.", 5000,
            )

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

        # Pedido explícito: agregar un ítem a mano (arrastrando) es la
        # ÚNICA excepción a "Ventana 2 siempre reproduce el FMT en
        # memoria" — corta el modo Musicalizador para que no compita
        # con lo que el operador acaba de poner.
        self.gestor_emision.detener_musicalizador()

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
        ventana.agregar_pisador(
            fila, registro.get("titulo", ""), duracion, registro.get("codigo", "—"), registro["ruta"],
            dialogo.posicion_elegida(),
        )
        self.statusBar().showMessage(f"Pisador '{registro.get('titulo', '')}' asignado.", 3000)

    # ------------------------------------------------------------------
    # Menú contextual "Agregar ítem" del Auxiliar (pedido explícito,
    # "lo mismo que Musicalizador: específico o aleatorio"). A
    # diferencia del "aleatorio" de Ventana 1 (Publicidad), que queda
    # como un PLACEHOLDER que se re-resuelve cada vez que suena, acá se
    # resuelve UNA VEZ, ahora mismo, y se agrega como un ítem concreto
    # — el Auxiliar no tiene el mecanismo de re-resolución al vuelo
    # (eso es específico de GestorPublicidad).
    # ------------------------------------------------------------------
    def _agregar_item_especifico_auxiliar(self):
        dialogo = DialogoSeleccionarBiblioteca(
            self.ventana_explorador.tree_categorias, permitir_multiple=True,
            titulo="Agregar ítem al Auxiliar", parent=self,
        )
        if dialogo.exec() != DialogoSeleccionarBiblioteca.DialogCode.Accepted:
            return
        registros = dialogo.registros_elegidos()
        for registro in registros:
            self._ventana_auxiliar.panel.agregar_item(
                registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
                registro.get("ruta", ""), registro.get("punto_inicio_ms") or 0,
                registro.get("punto_fin_ms"), registro.get("ganancia_db") or 0.0,
            )
        if registros:
            self.statusBar().showMessage(f"{len(registros)} ítem(s) agregado(s) al Auxiliar.", 3000)

    def _agregar_item_aleatorio_auxiliar(self):
        dialogo = DialogoSeleccionarCategoria(self.ventana_explorador.tree_categorias, parent=self)
        if dialogo.exec() != DialogoSeleccionarCategoria.DialogCode.Accepted:
            return
        ruta_categoria = dialogo.ruta_elegida()
        if not ruta_categoria:
            return
        categoria = self.ventana_explorador.buscar_categoria_por_ruta(ruta_categoria)
        if categoria is None:
            return
        candidatos = self.ventana_explorador.listar_registros_de_categoria(categoria, recursivo=True)
        if not candidatos:
            QMessageBox.information(self, "Agregar ítem aleatorio", "Esa categoría no tiene archivos.")
            return
        rutas_candidatas = {r.get("ruta") for r in candidatos if r.get("ruta")}
        evitar = rutas_recientes_en_historial(rutas_candidatas, max(0, len(rutas_candidatas) - 1))
        registro = self.ventana_explorador.elegir_aleatorio_de_categoria(categoria, recursivo=True, excluir_rutas=evitar)
        if registro is None:
            return
        self._ventana_auxiliar.panel.agregar_item(
            registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
            registro.get("ruta", ""), registro.get("punto_inicio_ms") or 0,
            registro.get("punto_fin_ms"), registro.get("ganancia_db") or 0.0,
        )
        self.statusBar().showMessage(f"Agregado al azar: {registro.get('titulo', '')}", 3000)

    def _agregar_ciclo_fmt_emision(self):
        """Pedido explícito ("agregá un menú contextual en Emisión...
        me pregunta el FMT que deseo y la cantidad de tiempo... el
        sistema calculará esa cantidad de tiempo e insertará ese ciclo
        sin eliminar lo que ya esté cargado"): abre
        DialogoCicloFMTPorTiempo (formato + minutos) y delega la
        generación real en GestorPlaylist.insertar_ciclo_fmt_por_tiempo()
        -- mismo motor que ya usa el Comando FMT real, pero SIN limpiar
        lo ya cargado."""
        from gui.dialogo_ciclo_fmt_por_tiempo import DialogoCicloFMTPorTiempo
        dialogo = DialogoCicloFMTPorTiempo(parent=self)
        if dialogo.exec() != DialogoCicloFMTPorTiempo.DialogCode.Accepted:
            return
        resultado = dialogo.resultado()
        if resultado is None:
            return
        nombre_formato, minutos = resultado
        self._mostrar_preload(f"Generando ciclo de '{nombre_formato}'...")
        cantidad = self.gestor_emision.insertar_ciclo_fmt_por_tiempo(nombre_formato, minutos)
        if cantidad:
            self.statusBar().showMessage(
                f"Agregados {cantidad} ítem(s) de '{nombre_formato}' (~{minutos} min) a Emisión.", 5000,
            )
        else:
            QMessageBox.warning(
                self, "Agregar ciclo FMT",
                f"El formato '{nombre_formato}' no generó ningún ítem -- revisá sus "
                "categorías/archivos en el Musicalizador Avanzado.",
            )

    def _on_archivo_soltado_publicidad(self, ruta: str, item_destino):
        registro = self.ventana_explorador.buscar_registro_por_ruta(ruta)
        titulo = (registro or {}).get("titulo") or os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        codigo = (registro or {}).get("codigo", "—")

        bloque = item_destino
        while bloque is not None and bloque.parent() is not None:
            bloque = bloque.parent()
        if bloque is None:
            # ArbolConDrop.dropEvent ya resuelve el bloque más cercano
            # al punto soltado cuando cae en un hueco vacío — esto
            # solo se ejecuta si el árbol está realmente vacío.
            if self.ventana_publicidad.tree.topLevelItemCount() == 0:
                self.statusBar().showMessage("Creá primero un bloque horario en Publicidad.", 4000)
                return
            bloque = self.ventana_publicidad.tree.topLevelItem(self.ventana_publicidad.tree.topLevelItemCount() - 1)

        self.ventana_publicidad.agregar_tanda(
            bloque, titulo, duracion, codigo, ruta,
            (registro or {}).get("punto_inicio_ms") or 0,
            (registro or {}).get("punto_fin_ms"),
            (registro or {}).get("ganancia_db") or 0.0,
            (registro or {}).get("fecha_inicio"),
            (registro or {}).get("fecha_fin"),
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
    # Exclusión mutua Auxiliar <-> Emisión (pedido explícito: "ninguna
    # ventana debe reproducirse al mismo tiempo junto con otra")
    # ------------------------------------------------------------------
    def _cortar_reproduccion_de(self, gestor):
        """Fundido corto + detener() REAL (nunca pausa — misma regla
        de fondo que SchedulerAutomatico.cortar_emision_por_play_manual/
        _reanudar_o_arrancar_emision, ver CLAUDE.md "Cosas ya
        resueltas") sobre `gestor`, si tenía algo sonando. Helper
        genérico: no sabe si `gestor` es Emisión o Auxiliar, solo
        corta lo que le pasen — así cualquier par de ventanas que
        MainWindow decida coordinar más adelante reusa lo mismo."""
        if gestor is None:
            return
        motor = gestor.motor
        if not motor.esta_reproduciendo():
            return
        try:
            duracion = float(gestor.duracion_fade_segundos or 0)
        except (TypeError, ValueError):
            duracion = 0.0
        duracion = max(0.8, duracion)
        motor.fade_volumen_a(0, duracion)
        QTimer.singleShot(int(duracion * 1000) + 150, gestor.detener)

    def _cortar_auxiliar_por_emision(self):
        self._cortar_reproduccion_de(self._gestor_auxiliar)

    def _cortar_emision_por_auxiliar(self):
        self._cortar_reproduccion_de(self.gestor_emision)

    # ------------------------------------------------------------------
    # Motor de audio real (core/)
    # ------------------------------------------------------------------
    def _inicializar_motores_audio(self):
        audio = self._config["audio"]
        reproduccion = self._config["reproduccion"]
        fade = self._config["fade"]

        id_dispositivo_master = audio["dispositivo_master"] if audio["dispositivo_master"] != "default" else None
        id_dispositivo_preescucha = audio["dispositivo_preescucha"] if audio["dispositivo_preescucha"] != "default" else None

        self.gestor_emision = GestorPlaylist(
            self.ventana_emision,
            id_dispositivo=id_dispositivo_master,
            avanzar_en_error=reproduccion["avanzar_automaticamente_en_error"],
            reintentos_maximos=reproduccion["reintentos_antes_de_detener"],
            repetir_al_finalizar=reproduccion["repetir_lista_al_finalizar"],
            bajada_db_pisador=reproduccion["pisador_bajada_db"],
            crossfade_activado=fade["crossfade_activado"],
            duracion_fade_segundos=fade["duracion_fade_out_v2_ms"] / 1000.0,
            duracion_fade_in_segundos=fade["duracion_fade_in_v2_ms"] / 1000.0,
            persistir=True,
            ventana_explorador=self.ventana_explorador,
        )
        # Pedido explícito ("estaría muy bueno que en EMISIÓN me
        # muestre el FMT en uso... EMISIÓN - LATINO, no hace falta que
        # salga FMT escrito"): sincroniza el título YA (por si la
        # sesión anterior restauró un FMT activo desde disco, ver
        # _restaurar_desde_disco -- corre ANTES de que este callback
        # exista) y lo mantiene actualizado de ahí en más.
        self.gestor_emision.al_cambiar_formato_activo = self.ventana_emision.establecer_sufijo_titulo
        self.ventana_emision.establecer_sufijo_titulo(self.gestor_emision.formato_musicalizador_activo())

        self.gestor_publicidad = GestorPublicidad(
            self.ventana_publicidad,
            id_dispositivo=id_dispositivo_master,
            avanzar_en_error=reproduccion["avanzar_automaticamente_en_error"],
            reintentos_maximos=reproduccion["reintentos_antes_de_detener"],
            persistir=True,
            duracion_fade_out_v1_ms=reproduccion["duracion_fade_out_v1_ms"],
            duracion_fade_in_declick_ms=reproduccion["duracion_fade_in_declick_v1_ms"],
            ventana_explorador=self.ventana_explorador,
        )
        # Comando FMT (pedido explícito, encadenado con el
        # Musicalizador Avanzado): al pasar por un ítem-comando FMT en
        # un bloque de Publicidad, dispara la generación continua de
        # música en Emisión.
        self.gestor_publicidad.al_comando_fmt = self.gestor_emision.iniciar_musicalizador

        self.gestor_emision.set_volumen_base(audio["volumen_master"])
        self.gestor_publicidad.set_volumen_base(audio["volumen_master"])

        # Pedido explícito: la preescucha de Ventana 3 (▶ Previo) va a
        # una salida SEPARADA de la Master — la Master alimenta la
        # cadena de procesamiento (compresor/limitador/EQ) hacia el
        # equipo que sale al aire, mientras que la Preescucha va a los
        # parlantes de monitoreo de la PC (más potencia, para
        # escuchar cómodo mientras se prepara el material).
        self.gestor_explorador = GestorExplorador(self.ventana_explorador, id_dispositivo=id_dispositivo_preescucha)

        # Pedido explícito (robustez de emisión): el botón AUTOMÁTICO
        # arranca SIEMPRE encendido al abrir el programa — la estación
        # debe retomar el aire sola sin intervención del operador
        # (reemplaza al viejo checkbox "modo automático al iniciar" de
        # Configuración, que quedaba en OFF y contradecía esta regla).
        # El operador puede apagarlo a mano después de abrir.
        self.ventana_publicidad.btn_automatico.setChecked(True)
        self.ventana_publicidad._toggle_automatico()

        if getattr(self, "scheduler_automatico", None) is not None:
            self.scheduler_automatico.detener()
        self.scheduler_automatico = SchedulerAutomatico(
            self.ventana_publicidad, self.gestor_publicidad, self.gestor_emision
        )
        self.scheduler_automatico.al_no_encontrar_bloque = self._avisar_sin_bloque_horario
        # Pedido explícito: Play manual en Ventana 1 corta Emisión con
        # fundido SIEMPRE (incluso con el Automático activo).
        self.gestor_publicidad.al_arrancar_manual = self.scheduler_automatico.cortar_emision_por_play_manual

        # Pedido explícito: "en rigor de verdad, ninguna ventana debe
        # reproducirse al mismo tiempo junto con otra" — Emisión y
        # Auxiliar nunca suenan a la vez. Arrancar Emisión desde
        # silencio corta al Auxiliar si estaba sonando (ver también
        # abrir_ventana_auxiliar(), que conecta la wiring inversa
        # recién cuando el Auxiliar se crea).
        self.gestor_emision.al_arrancar_reproduccion = self._cortar_auxiliar_por_emision

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
        self._actualizar_nombre_emisora()
        # Tema visual (pedido explícito, "Diseñá el tema Claro"):
        # cambiar el combo en Configuración → General se aplica ACÁ,
        # en caliente, sin reiniciar la app -- mismo criterio ya
        # establecido para el resto de "aplicar configuración en
        # vivo" (nombre de emisora, volumen, dispositivo de salida).
        app_actual = QApplication.instance()
        if app_actual is not None:
            app_actual.setStyleSheet(qss_para_tema(self._config["general"]["tema"]))
        audio = self._config["audio"]
        reproduccion = self._config["reproduccion"]
        fade = self._config["fade"]
        id_dispositivo_master = audio["dispositivo_master"] if audio["dispositivo_master"] != "default" else None
        id_dispositivo_preescucha = audio["dispositivo_preescucha"] if audio["dispositivo_preescucha"] != "default" else None

        for gestor in (self.gestor_emision, self._gestor_auxiliar):
            if gestor is None:
                continue
            gestor.avanzar_en_error = reproduccion["avanzar_automaticamente_en_error"]
            gestor.reintentos_maximos = max(1, reproduccion["reintentos_antes_de_detener"])
            gestor.repetir_al_finalizar = reproduccion["repetir_lista_al_finalizar"]
            gestor.bajada_db_pisador = reproduccion["pisador_bajada_db"]
            gestor.crossfade_activado = fade["crossfade_activado"]
            gestor.duracion_fade_segundos = fade["duracion_fade_out_v2_ms"] / 1000.0
            gestor.duracion_fade_in_segundos = fade["duracion_fade_in_v2_ms"] / 1000.0
            for motor in (gestor.motor, gestor.motor_pisador):
                if motor.id_dispositivo() != id_dispositivo_master:
                    motor.set_dispositivo_salida(id_dispositivo_master)

        self.gestor_emision.set_volumen_base(audio["volumen_master"])
        if self._gestor_auxiliar is not None:
            self._gestor_auxiliar.set_volumen_base(audio["volumen_master"])

        self.gestor_publicidad.avanzar_en_error = reproduccion["avanzar_automaticamente_en_error"]
        self.gestor_publicidad.reintentos_maximos = max(1, reproduccion["reintentos_antes_de_detener"])
        self.gestor_publicidad.duracion_fade_out_v1_ms = reproduccion["duracion_fade_out_v1_ms"]
        self.gestor_publicidad.duracion_fade_in_declick_ms = reproduccion["duracion_fade_in_declick_v1_ms"]
        if self.gestor_publicidad.motor.id_dispositivo() != id_dispositivo_master:
            self.gestor_publicidad.motor.set_dispositivo_salida(id_dispositivo_master)
        self.gestor_publicidad.set_volumen_base(audio["volumen_master"])

        if self.gestor_explorador.motor.id_dispositivo() != id_dispositivo_preescucha:
            self.gestor_explorador.motor.set_dispositivo_salida(id_dispositivo_preescucha)

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
                duracion_fade_segundos=fade["duracion_fade_out_v2_ms"] / 1000.0,
                duracion_fade_in_segundos=fade["duracion_fade_in_v2_ms"] / 1000.0,
            )
            self._gestor_auxiliar.set_volumen_base(audio["volumen_master"])
            # Pedido explícito: mismo criterio que arriba, en el
            # sentido inverso — arrancar el Auxiliar desde silencio
            # corta a Emisión.
            self._gestor_auxiliar.al_arrancar_reproduccion = self._cortar_emision_por_auxiliar
            self._ventana_auxiliar.archivo_soltado.connect(self._on_archivo_soltado_auxiliar)
            self._ventana_auxiliar.solicitud_agregar_pisador.connect(
                lambda fila: self._abrir_dialogo_pisador(self._ventana_auxiliar, fila)
            )
            self._ventana_auxiliar.solicitud_agregar_item_especifico.connect(self._agregar_item_especifico_auxiliar)
            self._ventana_auxiliar.solicitud_agregar_item_aleatorio.connect(self._agregar_item_aleatorio_auxiliar)
            self._ventana_auxiliar.solicitud_guardar_lista.connect(self._guardar_lista_auxiliar)
            self._ventana_auxiliar.solicitud_cargar_lista.connect(self._cargar_lista_auxiliar)

        self._ventana_auxiliar.show()
        self._ventana_auxiliar.raise_()
        self._ventana_auxiliar.activateWindow()

    # ------------------------------------------------------------------
    # Listas guardadas del Auxiliar (pedido explícito: guardar el
    # contenido actual bajo un nombre, cargarlo después reemplazando lo
    # que hubiera, o borrarlo — todo con confirmación siempre).
    # ------------------------------------------------------------------
    def _guardar_lista_auxiliar(self):
        if self._gestor_auxiliar is None or self._ventana_auxiliar.cantidad_items() == 0:
            QMessageBox.information(
                self, "Guardar lista", "El Auxiliar está vacío — no hay nada para guardar."
            )
            return

        nombre, ok = QInputDialog.getText(
            self, "Guardar lista del Auxiliar", "Nombre de la lista:"
        )
        nombre = nombre.strip()
        if not ok or not nombre:
            return

        ya_existe = nombre in listar_listas_auxiliares()
        texto_confirmacion = (
            f"¿Confirmás que querés SOBRESCRIBIR la lista guardada '{nombre}'\n"
            "con el contenido actual del Auxiliar?"
            if ya_existe else
            f"¿Confirmás que querés guardar la lista actual del Auxiliar como '{nombre}'?"
        )
        respuesta = QMessageBox.question(
            self, "Guardar lista", texto_confirmacion,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        items = self._gestor_auxiliar.serializar_items()
        guardar_lista_auxiliar(nombre, items)
        registrar_evento(f"Auxiliar: lista '{nombre}' guardada ({len(items)} ítem(s))")
        self.statusBar().showMessage(f"Lista '{nombre}' guardada.", 4000)

    def _cargar_lista_auxiliar(self):
        if self._gestor_auxiliar is None:
            return
        nombres = listar_listas_auxiliares()
        if not nombres:
            QMessageBox.information(
                self, "Cargar lista", "Todavía no hay ninguna lista guardada en el Auxiliar."
            )
            return

        dialogo = DialogoListasAuxiliar(nombres, self)
        resultado = dialogo.exec()

        nombre_borrar = dialogo.nombre_a_borrar()
        if nombre_borrar is not None:
            respuesta = QMessageBox.question(
                self, "Borrar lista",
                f"¿Confirmás que querés borrar la lista guardada '{nombre_borrar}'?\n"
                "Esta acción no se puede deshacer.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                if eliminar_lista_auxiliar(nombre_borrar):
                    registrar_evento(f"Auxiliar: lista '{nombre_borrar}' borrada")
                    self.statusBar().showMessage(f"Lista '{nombre_borrar}' borrada.", 4000)
            return

        if resultado != 1:  # QDialog.DialogCode.Accepted
            return
        nombre = dialogo.nombre_a_cargar()
        if not nombre:
            return

        items = obtener_lista_auxiliar(nombre)
        if items is None:
            QMessageBox.warning(self, "Cargar lista", f"La lista '{nombre}' ya no existe.")
            return

        if self._ventana_auxiliar.cantidad_items() > 0:
            respuesta = QMessageBox.question(
                self, "Cargar lista",
                f"Cargar '{nombre}' va a REEMPLAZAR el contenido actual del Auxiliar.\n"
                "¿Confirmás?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        else:
            respuesta = QMessageBox.question(
                self, "Cargar lista", f"¿Confirmás que querés cargar la lista '{nombre}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        self._gestor_auxiliar.cargar_items(items)
        registrar_evento(f"Auxiliar: lista '{nombre}' cargada ({len(items)} ítem(s))")
        self.statusBar().showMessage(f"Lista '{nombre}' cargada.", 4000)

    # ------------------------------------------------------------------
    # Programador de emisión
    # ------------------------------------------------------------------
    def abrir_programador(self):
        if self._ventana_programador is None:
            self._ventana_programador = VentanaProgramador(self, ventana_explorador=self.ventana_explorador)
            configurar_columnas_ajustables(self._ventana_programador.tree, [200, 90])
            self._ventana_programador.tree.header().setMinimumSectionSize(45)
            estado_ui.restaurar_columnas("programador", self._ventana_programador.tree)
            estado_ui.restaurar_geometria_ventana(self._ventana_programador, "programador")
            self._ventana_programador.solicitud_aplicar_ahora.connect(self._aplicar_programacion_ahora)

        self._ventana_programador.show()
        self._ventana_programador.raise_()
        self._ventana_programador.activateWindow()

    # ------------------------------------------------------------------
    # Musicalizador Avanzado (pedido explícito, encadenado con
    # Comandos FMT)
    # ------------------------------------------------------------------
    def abrir_musicalizador(self):
        if self._ventana_musicalizador is None:
            self._ventana_musicalizador = VentanaMusicalizador(ventana_explorador=self.ventana_explorador, parent=self)
            estado_ui.restaurar_geometria_ventana(self._ventana_musicalizador, "musicalizador")

        self._ventana_musicalizador.show()
        self._ventana_musicalizador.raise_()
        self._ventana_musicalizador.activateWindow()

    def _aplicar_programacion_ahora(self, bloques: list):
        """Pedido explícito del Programador (punto d): "cargar esa
        programación en el momento" — la confirmación de que puede
        cortar lo que está sonando ya la pidió VentanaProgramador antes
        de emitir esta señal; acá solo se aplica en vivo."""
        self.ventana_publicidad.cargar_bloques(bloques)
        self.gestor_publicidad._asegurar_rojo_y_verde()
        registrar_evento("Publicidad: bloques aplicados en vivo desde el Programador")
        self.statusBar().showMessage("Programación aplicada ahora mismo en Ventana 1.", 4000)

    def _cargar_programacion_de_hoy_manual(self):
        """"Cargar Programación" del menú contextual de Ventana 1 —
        pedido explícito: resuelve la programación de HOY (fecha
        específica tiene prioridad sobre el patrón semanal genérico,
        resolver_programacion_del_dia ya implementa esa regla) y pide
        confirmación antes de reemplazar los bloques actuales, ya que
        es una acción manual explícita (a diferencia de la carga
        automática de medianoche/inicio, que no pregunta)."""
        from datetime import date
        from config.settings import resolver_programacion_del_dia

        contenido = resolver_programacion_del_dia(date.today())
        if not contenido:
            QMessageBox.information(
                self, "Cargar Programación",
                "No hay ninguna programación guardada para hoy (ni por fecha\n"
                "específica ni por día de la semana).",
            )
            return

        respuesta = QMessageBox.question(
            self, "Cargar Programación",
            f"Se encontró la programación de hoy: \"{contenido.get('nombre', '')}\".\n\n"
            "Esto va a reemplazar los bloques actuales de Publicidad.\n"
            "¿Confirmás que querés cargarla?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.ventana_publicidad.cargar_bloques(contenido.get("bloques", []))
        self.gestor_publicidad._asegurar_rojo_y_verde()
        self.statusBar().showMessage(f"Programación de hoy cargada: {contenido.get('nombre', '')}", 4000)

    # ------------------------------------------------------------------
    # Configuración general
    # ------------------------------------------------------------------
    def abrir_configuracion(self, pestaña: int = 0):
        dialogo = VentanaConfiguracion(self, pestaña_inicial=pestaña, ventana_explorador=self.ventana_explorador)
        if dialogo.exec() == VentanaConfiguracion.DialogCode.Accepted:
            self._aplicar_configuracion_en_vivo()
            self.statusBar().showMessage("Configuración guardada y aplicada (sin cortar la reproducción).", 4000)
