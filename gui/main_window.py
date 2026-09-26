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
from core.audio_engine import obtener_duracion_formateada, MotorAudio, contar_descriptores_y_pulseaudio
from core.clima_meteo import RefrescadorClima, LATITUD_DEFECTO, LONGITUD_DEFECTO
from core.servidor_control_remoto import ServidorControlRemoto
from core.musicalizador import validar_formato
from core.rotacion_categoria import elegir_por_rotacion, marcar_reproducido_por_rotacion
from core import actualizador
from core import reinicio_sistema
import core.prioridad_proceso as prioridad_proceso
from config.settings import (
    cargar_configuracion, registrar_evento, registrar_error, guardar_configuracion,
    guardar_lista_auxiliar, listar_listas_auxiliares,
    obtener_lista_auxiliar, eliminar_lista_auxiliar,
    listar_programaciones, obtener_programacion, guardar_programacion,
    cargar_musicalizador, listar_formatos, obtener_formato,
    guardar_formato, eliminar_formato, renombrar_formato,
    categoria_de_enlatado,
    ARCHIVO_LOG,
)

# Pedido explícito: "cambiá el botón BAYS por uno que diga AUDIO
# CANAL, donde detenga todas las reproducciones y emita SOLO el audio
# del siguiente streaming" -- ver VentanaExplorador.solicitud_audio_canal
# y MainWindow._on_solicitud_audio_canal() más abajo.
# Se probó reemplazar este HLS por un RTSP local
# (rtsp://192.168.1.150/12, buscando menor delay) -- Santiago probó en
# producción y NO se escuchaba nada, revertido a pedido explícito.
# Causa no diagnosticada todavía (posible: el codificador de esa IP no
# responde en ese puerto/canal, credenciales, o el transport RTSP que
# usa libVLC por default no es el que espera ese equipo) -- si se
# retoma en el futuro, conviene primero confirmar con un
# `vlc rtsp://192.168.1.150/12` suelto en esa PC que conecta y trae
# audio, antes de volver a cambiar esta constante.
URL_AUDIO_CANAL = "https://elsellotvmax.com.ar:9443/elsellotv.m3u8"


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
        self._servidor_control_remoto = None
        # Pre-escucha remota (Programador satélite, "▶ Previo"): motor
        # dedicado, creado recién en el primer pedido -- mismo criterio
        # que la Preescucha local (`VentanaProgramador._motor_previo`),
        # SIEMPRE por la salida de Preescucha configurada, nunca la
        # Master que va al aire.
        self._motor_previo_remoto = None
        # "AUDIO CANAL" (pedido explícito, reemplaza al botón "Bays"
        # de Ventana 3): motor DEDICADO al streaming externo, creado
        # recién al primer uso y reutilizado de ahí en más (nunca se
        # recrea en cada toggle -- mismo criterio que _motor_previo_remoto,
        # y a propósito el patrón OPUESTO al que causó la fuga real de
        # una ronda anterior, "crear un MotorAudio nuevo repetidas
        # veces sin liberarlo").
        self._motor_audio_canal = None
        self._audio_canal_activo = False

        self._config = cargar_configuracion()

        self._construir_menu()
        self._construir_toolbar()
        self._construir_paneles_centrales()
        self._aplicar_tamano_fuente_ventanas()
        self._construir_status_bar()
        self._conectar_señales()
        self._inicializar_motores_audio()
        self._inicializar_control_remoto()

        # Bug real de fondo, encontrado auditando el código tras un
        # reporte de Santiago ("se traba la barra de tareas SOLO
        # cuando cierro este programa, con otros programas no me
        # pasa"): hasta esta ronda, cerrar la app NUNCA liberaba
        # ordenadamente ninguno de los ~8-10 MotorAudio() que puede
        # llegar a tener abiertos a la vez (V1 + su HORA/TEMP manual,
        # V2 + Pisador + su HORA/TEMP manual, el Auxiliar con el mismo
        # trío si está abierto, el Previo de Ventana 3, y AUDIO
        # CANAL/Previo remoto si se llegaron a usar) — el proceso de
        # Python los mataba a todos DE GOLPE al salir, sin llamar
        # nunca a `MotorAudio.liberar()` (el mismo método que ya
        # existe desde el fix real de la fuga de audio del crossfade
        # -- ver `core/gestor_emision.py` -- pensado justo para esto:
        # cerrar la conexión de audio con PipeWire de forma prolija en
        # vez de dejar que el sistema operativo la corte de un tirón).
        # Ningún otro programa de la PC abre tantos clientes de audio
        # simultáneos como este -- coherente con que el síntoma sea
        # específico de cerrar ESTE programa. `aboutToQuit` (no
        # `closeEvent`) porque se dispara siempre que el cierre ya
        # está confirmado y va a pasar de verdad, sin importar por
        # qué camino se llegó ahí.
        QApplication.instance().aboutToQuit.connect(self._liberar_todos_los_motores_al_salir)

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

        # Pedido explícito ("sacar la búsqueda de actualizaciones al
        # abrir el programa — se actualizará solo por el menú
        # Configuración, como está"): la búsqueda automática al
        # arrancar (agregada en una ronda anterior) se sacó por
        # completo — Configuración → Actualizaciones sigue teniendo su
        # propio botón manual, independiente de esto, sin cambios.

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
        # pestaña de Audio) — ahora un desplegable con accesos
        # directos a las pestañas más usadas, reemplazando al viejo
        # menú "Herramientas". Bug real ya documentado (ver CLAUDE.md,
        # "El botón 'Actualizar'..." y el episodio de este mismo
        # desplegable con "Procesador" en el medio): estos índices son
        # ÍNDICES DE PESTAÑA — si el orden de `_construir_ui()` (más
        # arriba, en ventana_configuracion.py) cambia, HAY QUE
        # actualizar esta lista en el mismo cambio, nunca por separado.
        boton_config = QToolButton()
        boton_config.setText("⚙ Configuración")
        boton_config.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_config = QMenu(boton_config)
        for texto, indice_tab in (
            ("Configuración de audio...", 0),
            ("Tiempos de Fade...", 1),
            ("🎚 Procesador FM...", 2),
            ("Reproducción y Automatización...", 3),
            ("Rutas de archivos...", 5),
            ("Preferencias generales...", 6),
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
        if self._motor_audio_canal is not None:
            motores.append(self._motor_audio_canal)
        return any(motor.esta_reproduciendo() for motor in motores)

    def _liberar_todos_los_motores_al_salir(self):
        """Conectado a `QApplication.aboutToQuit` -- ver el comentario
        en `__init__`. Recorre TODOS los MotorAudio que esta ventana
        puede llegar a tener vivos (los principales de las 3 ventanas
        + los secundarios de cada una -- Pisador, HORA/TEMP manual,
        el motor "entrante" de un crossfade si justo quedó uno a
        mitad, más los creados bajo demanda que puede que nunca se
        hayan usado, de ahí el chequeo `is not None` en cada uno) y
        llama `.liberar()` en cada uno -- nunca falla si alguno ya
        está liberado o nunca se inicializó (ver el propio docstring
        de `MotorAudio.liberar()`)."""
        motores = [
            self.gestor_publicidad.motor,
            self.gestor_publicidad.motor_anuncio_manual,
            self.gestor_emision.motor,
            self.gestor_emision.motor_pisador,
            self.gestor_emision.motor_anuncio_manual,
            self.gestor_explorador.motor,
        ]
        if self.gestor_emision._motor_saliente_crossfade is not None:
            motores.append(self.gestor_emision._motor_saliente_crossfade)
        if self._gestor_auxiliar is not None:
            motores.extend([
                self._gestor_auxiliar.motor,
                self._gestor_auxiliar.motor_pisador,
                self._gestor_auxiliar.motor_anuncio_manual,
            ])
            if self._gestor_auxiliar._motor_saliente_crossfade is not None:
                motores.append(self._gestor_auxiliar._motor_saliente_crossfade)
        if self._motor_audio_canal is not None:
            motores.append(self._motor_audio_canal)
        if self._motor_previo_remoto is not None:
            motores.append(self._motor_previo_remoto)
        for motor in motores:
            try:
                motor.liberar()
            except Exception:
                # Nunca dejar que un motor puntual roto trabe la
                # liberación del resto ni el cierre del programa.
                pass

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

        if self._servidor_control_remoto is not None:
            self._servidor_control_remoto.detener()

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
        self.ventana_explorador.solicitud_audio_canal.connect(self._on_solicitud_audio_canal)

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

        # Bug real corregido (pedido explícito, verificado): agregar un
        # ítem a mano SOLÍA cortar el ciclo continuo del Musicalizador
        # por completo (`detener_musicalizador()`), pensado en su
        # momento para que un refill no "compitiera" con lo recién
        # puesto — pero el refill de `_generar_serie_musicalizador()`
        # SOLO agrega al final, nunca borra ni pisa nada ya cargado, así
        # que ese temor nunca aplicaba de verdad. En la práctica, cortar
        # el Musicalizador acá hacía que la carga automática del FMT
        # dejara de reponerse para siempre después de UN solo arrastre
        # manual, hasta que algo disparara un Comando FMT de nuevo — ya
        # NO se corta: el ítem soltado se inserta donde corresponda y
        # el ciclo del formato activo sigue reponiéndose solo.
        titulo = os.path.splitext(os.path.basename(ruta))[0]
        duracion = obtener_duracion_formateada(ruta)
        self.ventana_emision.agregar_item(
            titulo, duracion, "—", ruta,
            (registro or {}).get("punto_inicio_ms") or 0,
            (registro or {}).get("punto_fin_ms"),
            (registro or {}).get("ganancia_db") or 0.0,
            item_destino,
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
        # No repetir hasta agotar la categoría (pedido explícito,
        # "necesito absoluta variedad... el máximo tiempo para que no
        # se repita"): usa la misma rotación secuencial persistida por
        # categoría que ya usa el Ítem Aleatorio de Ventana 1
        # (core/rotacion_categoria.py) en vez del historial de
        # reproducción — garantiza matemáticamente el espaciado máximo
        # posible, sin depender de cuánto haya quedado escrito en el
        # log antes de su última rotación por tamaño. El "commit"
        # (avanzar la rotación) pasa acá mismo, al agregarlo a la
        # lista — a diferencia de Ventana 1, este ítem queda FIJO en
        # el Auxiliar desde el momento de agregarlo, no hay ningún
        # "arranca a sonar de verdad" posterior donde volver a
        # resolverlo.
        dialogo = DialogoSeleccionarCategoria(self.ventana_explorador.tree_categorias, parent=self)
        if dialogo.exec() != DialogoSeleccionarCategoria.DialogCode.Accepted:
            return
        ruta_categoria = dialogo.ruta_elegida()
        if not ruta_categoria:
            return
        registro = elegir_por_rotacion(self.ventana_explorador, ruta_categoria, recursivo=True)
        if registro is None:
            QMessageBox.information(self, "Agregar ítem aleatorio", "Esa categoría no tiene archivos.")
            return
        self._ventana_auxiliar.panel.agregar_item(
            registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
            registro.get("ruta", ""), registro.get("punto_inicio_ms") or 0,
            registro.get("punto_fin_ms"), registro.get("ganancia_db") or 0.0,
        )
        marcar_reproducido_por_rotacion(self.ventana_explorador, ruta_categoria, registro.get("ruta", ""), True)
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
            item_destino,
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
    # "AUDIO CANAL" (Ventana 3, pedido explícito -- reemplaza al botón
    # "Bays": "detenga todas las reproducciones y emita SOLO el audio
    # del siguiente streaming"). Toggle: un segundo click desactiva el
    # streaming y deja la radio en silencio, lista para retomar a mano
    # -- mismo criterio de "nunca auto-resume tras un corte
    # deliberado" ya establecido en toda la app (Auxiliar<->Emisión,
    # bloque automático<->Emisión, etc.).
    #
    # Límite conocido, a propósito no resuelto acá (fuera del pedido
    # literal): esto NO queda enganchado a la exclusión mutua
    # Auxiliar<->Emisión (`al_arrancar_reproduccion`) ni al corte de
    # Play manual de V1 (`al_arrancar_manual`) -- si el operador
    # apreta Play a mano en V1/V2/Auxiliar mientras el streaming está
    # sonando, las dos cosas suenan superpuestas hasta que se vuelva a
    # apretar "AUDIO CANAL" para cortarlo. Extenderlo a esos 3
    # callbacks (hoy de un solo destinatario cada uno, no una lista)
    # es un cambio de arquitectura más grande, no pedido explícito.
    # ------------------------------------------------------------------
    def _on_solicitud_audio_canal(self):
        if self._audio_canal_activo:
            self._desactivar_audio_canal()
            return
        respuesta = QMessageBox.question(
            self, "Audio Canal",
            "Esto va a DETENER toda la reproducción de Publicidad, Emisión "
            "y Auxiliar, y va a poner al aire SOLO el audio de un "
            "streaming externo.\n\nLa radio va a quedar en modo \"Audio "
            "Canal\" hasta que vuelvas a apretar este mismo botón para "
            "desactivarlo.\n\n¿Confirmás que querés activarlo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self._activar_audio_canal()

    def _activar_audio_canal(self):
        # Corta las 3 ventanas de reproducción reusando los botones
        # Stop REALES (mismo patrón ya usado por el control remoto,
        # `accion_transporte`: `getattr(objetivo, boton).click()`) --
        # así se hereda gratis cualquier guard que ya tengan (ej. Stop
        # de V1 apaga el Automático solo, ronda 108) sin duplicar esa
        # lógica acá. V1 primero: apaga el Automático como efecto
        # colateral, así el Stop de V2 (bloqueado mientras el
        # Automático esté activo) ya no queda bloqueado al llegarle el
        # turno.
        self.ventana_publicidad.btn_stop.click()
        self.ventana_emision.panel.btn_stop.click()
        if self._ventana_auxiliar is not None:
            self._ventana_auxiliar.panel.btn_stop.click()

        motor = self._motor_audio_canal_o_crear()
        motor.reproducir(URL_AUDIO_CANAL)
        self._audio_canal_activo = True
        self.ventana_explorador.set_audio_canal_activo(True)
        self.statusBar().showMessage("📡 Audio Canal activo — streaming externo al aire.", 8000)
        registrar_evento(f"Audio Canal: activado, streaming '{URL_AUDIO_CANAL}'")

    def _detener_v2_y_auxiliar_por_comando_stop(self):
        """Comando STOP de Ventana 1 (pedido explícito): la parte de
        Publicidad (motor propio + Automático) ya la maneja
        GestorPublicidad solo -- acá solo falta Emisión y el Auxiliar,
        mismo patrón (botones Stop REALES, no duplicar la lógica de
        cada uno) ya usado en _activar_audio_canal más arriba. El
        Automático ya está apagado para cuando esto se llama (lo apaga
        GestorPublicidad ANTES de disparar este callback), así el Stop
        de V2 no llega bloqueado."""
        self.ventana_emision.panel.btn_stop.click()
        if self._ventana_auxiliar is not None:
            self._ventana_auxiliar.panel.btn_stop.click()

    def _desactivar_audio_canal(self):
        if self._motor_audio_canal is not None:
            self._motor_audio_canal.detener()
        self._audio_canal_activo = False
        self.ventana_explorador.set_audio_canal_activo(False)
        self.statusBar().showMessage("Audio Canal detenido.", 6000)
        registrar_evento("Audio Canal: desactivado")

    def _motor_audio_canal_o_crear(self) -> MotorAudio:
        if self._motor_audio_canal is None:
            audio_cfg = self._config.get("audio", {})
            dispositivo_master = audio_cfg.get("dispositivo_master", "default")
            id_dispositivo_master = dispositivo_master if dispositivo_master != "default" else None
            self._motor_audio_canal = MotorAudio(id_dispositivo_master)
            # Sin esto, un error real (streaming caído, URL
            # inalcanzable, credenciales vencidas) quedaría totalmente
            # invisible -- este motor no pasa por ningún GestorPlaylist/
            # GestorPublicidad que ya conecte error_reproduccion por su
            # cuenta (mismo criterio ya usado para motor_pisador/
            # motor_anuncio_manual).
            self._motor_audio_canal.error_reproduccion.connect(
                lambda mensaje: registrar_error(f"[Audio Canal] {mensaje}")
            )
        return self._motor_audio_canal

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
        # Pedido explícito (botón azul "HORA/TEMP"): si el operador lo
        # aprieta y no hay nada para reproducir (falta un clip, o no
        # hay datos de clima todavía), avisa en la barra de estado en
        # vez de quedar en silencio sin ninguna señal.
        self.gestor_emision.al_fallar_hth_manual = lambda mensaje: self.statusBar().showMessage(mensaje, 6000)

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
        # Comandos STOP/PLAY (pedido explícito, "para poner en la
        # programación de Ventana 1 cuando yo quiera"): GestorPublicidad
        # ya se apaga/prende y toca el Automático por su cuenta -- estos
        # dos callbacks cubren solo lo que ese gestor no puede tocar
        # directo: Emisión (V2) y el Auxiliar.
        self.gestor_publicidad.al_comando_stop = self._detener_v2_y_auxiliar_por_comando_stop
        self.gestor_publicidad.al_comando_play = self.gestor_emision.reproducir_actual
        # Pedido explícito (botón azul "HORA/TEMP", ahora también en
        # Ventana 1): mismo aviso por la barra de estado que ya tiene
        # Ventana 2 si no hay nada para reproducir.
        self.gestor_publicidad.al_fallar_hth_manual = lambda mensaje: self.statusBar().showMessage(mensaje, 6000)

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

        # Pedido explícito ("prioridad de reproducción, solo cuando
        # está play en cualquier ventana activo... si no hay
        # reproductor musical devolver la prioridad a otro, ej.
        # ZaraRadio"): chequeo liviano cada 2s de los 3 motores
        # PRINCIPALES (Publicidad/Emisión/Auxiliar -- no los
        # secundarios como Pisador/previo/HORA-TEMP, que son ráfagas
        # cortas, no "reproducción" en el sentido que pidió Santiago).
        # Ver core/prioridad_proceso.py para el detalle completo
        # (requiere permiso del sistema operativo, degrada limpio si
        # no lo tiene).
        self._timer_prioridad_proceso = QTimer(self)
        self._timer_prioridad_proceso.setInterval(2000)
        self._timer_prioridad_proceso.timeout.connect(self._actualizar_prioridad_proceso)
        self._timer_prioridad_proceso.start()

        # Pedido explícito, de la misma investigación de la fuga de
        # audio real ("que el log también registre todos esos
        # números, así me ahorra correr el comando"): antes había que
        # pedirle a Santiago que corriera a mano `ls /proc/<pid>/fd |
        # wc -l` por Chrome Remote Desktop cada vez que algo se sentía
        # raro. Ahora el propio proceso se audita solo cada 15 minutos
        # -- pura lectura de /proc/self/fd (ver
        # contar_descriptores_y_pulseaudio en core/audio_engine.py),
        # nunca subprocess/pactl, así que nunca puede colgarse ni
        # competir con EnrutadorPactl. El intervalo (15 min) da buena
        # resolución contra el ritmo de fuga real observado (~1 cada
        # 13-14 min) sin saturar el log de líneas repetidas.
        self._timer_diagnostico_recursos = QTimer(self)
        self._timer_diagnostico_recursos.setInterval(15 * 60 * 1000)
        self._timer_diagnostico_recursos.timeout.connect(self._registrar_diagnostico_recursos)
        self._timer_diagnostico_recursos.start()
        self._registrar_diagnostico_recursos()  # una primera foto ya al arrancar, no recién a los 15 min

    def _actualizar_prioridad_proceso(self):
        motores = [self.gestor_publicidad.motor, self.gestor_emision.motor]
        if self._gestor_auxiliar is not None:
            motores.append(self._gestor_auxiliar.motor)
        if self._motor_audio_canal is not None:
            motores.append(self._motor_audio_canal)
        hay_algo_sonando = any(motor.esta_reproduciendo() for motor in motores)
        prioridad_proceso.actualizar_segun_reproduccion(hay_algo_sonando)

    def _registrar_diagnostico_recursos(self):
        total, pulseaudio = contar_descriptores_y_pulseaudio()
        if total < 0:
            return  # /proc no disponible -- no debería pasar en Linux, pero nunca romper por esto
        registrar_evento(
            f"Diagnóstico de recursos: {total} descriptores de archivo abiertos "
            f"({pulseaudio} conexiones PulseAudio vía memfd)"
        )

    # ------------------------------------------------------------------
    # Control remoto (app satélite) — pedido explícito: "una app aparte
    # satélite... pueda controlar el programa en ejecución por el
    # usuario Radio... incluso subir algún archivo de audio al
    # explorador". Ver core/servidor_control_remoto.py para el
    # servidor en sí y la regla de fondo (un solo escritor real de los
    # JSON: este proceso, nunca la satélite directo).
    # ------------------------------------------------------------------
    def _inicializar_control_remoto(self):
        cr = self._config.get("control_remoto", {})
        if not cr.get("activado"):
            return
        token = cr.get("token") or ""
        if not token:
            import secrets
            token = secrets.token_hex(16)
            self._config["control_remoto"]["token"] = token
            guardar_configuracion(self._config)
        self._servidor_control_remoto = ServidorControlRemoto(cr.get("puerto", 8765), token, parent=self)
        self._servidor_control_remoto.manejador = self._manejar_comando_remoto
        ok, error = self._servidor_control_remoto.iniciar()
        if ok:
            registrar_evento(f"Control remoto: servidor escuchando en 127.0.0.1:{self._servidor_control_remoto.puerto()}")
        else:
            registrar_error(f"Control remoto: no se pudo iniciar el servidor — {error}")
            self.statusBar().showMessage(f"Control remoto: no se pudo iniciar ({error})", 8000)

    def _manejar_comando_remoto(self, accion: str, params: dict) -> dict:
        """Resuelve un pedido de la app satélite. Reusa SIEMPRE los
        mismos métodos que ya usa la GUI principal (nunca escribe JSON
        por su cuenta) — ver la nota de diseño en
        core/servidor_control_remoto.py."""
        if accion == "ping":
            return {"ok": True, "datos": {"app": "Auto-Radio Tuyú"}}
        if accion == "listar_categorias":
            return {"ok": True, "datos": {"categorias": self.ventana_explorador.listar_categorias_planas()}}
        if accion == "listar_generos":
            from gui.styles import LISTA_GENEROS
            return {"ok": True, "datos": {"generos": LISTA_GENEROS}}
        if accion == "estado_transporte":
            return {"ok": True, "datos": self._estado_transporte_remoto()}
        if accion == "accion_transporte":
            return self._accion_transporte_remota(params.get("ventana", ""), params.get("accion", ""))
        if accion == "importar_archivo":
            return self._importar_archivo_remoto(params)
        if accion == "alternar_automatico":
            return self._alternar_automatico_remoto(bool(params.get("activar")))
        if accion == "listar_registros_categoria":
            return self._listar_registros_categoria_remoto(params)
        if accion == "listar_registros_por_genero":
            return self._listar_registros_por_genero_remoto(params)
        if accion == "resolver_registro_por_ruta":
            return self._resolver_registro_por_ruta_remoto(params)
        if accion == "programador_previo_reproducir":
            return self._programador_previo_reproducir_remoto(params)
        if accion == "programador_previo_detener":
            return self._programador_previo_detener_remoto()
        if accion == "programador_listar_guardadas":
            return self._programador_listar_guardadas_remoto()
        if accion == "programador_cargar_guardada":
            return self._programador_cargar_guardada_remoto(params)
        if accion == "programador_bloques_actuales":
            return {"ok": True, "datos": {"bloques": self.ventana_publicidad.serializar_bloques_actuales()}}
        if accion == "programador_guardar":
            return self._programador_guardar_remoto(params)
        if accion == "programador_aplicar_ahora":
            return self._programador_aplicar_ahora_remoto(params)
        if accion == "musicalizador_listar_formatos":
            return {"ok": True, "datos": {"formatos": listar_formatos()}}
        if accion == "musicalizador_obtener_formato":
            return self._musicalizador_obtener_formato_remoto(params)
        if accion == "musicalizador_guardar_formato":
            return self._musicalizador_guardar_formato_remoto(params)
        if accion == "musicalizador_nuevo_formato":
            return self._musicalizador_nuevo_formato_remoto(params)
        if accion == "musicalizador_eliminar_formato":
            return self._musicalizador_eliminar_formato_remoto(params)
        if accion == "musicalizador_renombrar_formato":
            return self._musicalizador_renombrar_formato_remoto(params)
        if accion == "emision_agregar_ciclo_fmt":
            return self._emision_agregar_ciclo_fmt_remoto(params)
        if accion == "listar_enlatados":
            return {"ok": True, "datos": {"enlatados": self._listar_enlatados_remoto()}}
        if accion == "actualizar_reiniciar_principal":
            return self._actualizar_reiniciar_principal_remoto()
        if accion == "obtener_log_aplicacion":
            return self._obtener_log_aplicacion_remoto(params)
        if accion == "reiniciar_pc_forzado":
            return self._reiniciar_pc_forzado_remoto()
        return {"ok": False, "error": f"Acción desconocida: {accion}"}

    def _listar_enlatados_remoto(self) -> dict:
        """Camino de categoría configurado para cada slot ENLATADO
        1-5 (Configuración → Enlatados), para que el Programador
        remoto pueda mostrar de un vistazo qué categoría le
        corresponde a cada número — mismo criterio que ya usa
        `gui/dialogo_insertar_comando_enlatado.py` del lado local."""
        config = cargar_configuracion()
        return {numero: categoria_de_enlatado(config, numero) for numero in ("1", "2", "3", "4", "5")}

    def _alternar_automatico_remoto(self, activar: bool) -> dict:
        """Prende/apaga el Automático de Ventana 1 -- mismo mecanismo
        que YA usa el arranque de la app y el botón Stop de V1 (ronda
        108) para cambiar el modo SIN pasar por el diálogo de
        confirmación Sí/No de `_on_click_automatico()` (ese diálogo,
        si se disparara acá, sería un QMessageBox MODAL congelando el
        proceso principal esperando un click que nadie puede dar del
        otro lado del socket). La confirmación, si hace falta, la pide
        la propia app satélite ANTES de mandar este pedido."""
        v1 = self.ventana_publicidad
        if v1.esta_en_automatico() == activar:
            return {"ok": True, "datos": {"automatico_activo": activar}}
        v1.btn_automatico.setChecked(activar)
        v1._toggle_automatico()
        registrar_evento(f"Control remoto: Automático de V1 {'activado' if activar else 'desactivado'} de forma remota")
        return {"ok": True, "datos": {"automatico_activo": v1.esta_en_automatico()}}

    def _listar_registros_categoria_remoto(self, params: dict) -> dict:
        categoria_ruta = params.get("categoria_ruta") or []
        recursivo = bool(params.get("recursivo", False))
        item_categoria = self.ventana_explorador.buscar_categoria_por_ruta(categoria_ruta)
        if item_categoria is None:
            return {"ok": False, "error": f"No se encontró la categoría {categoria_ruta!r}."}
        registros = self.ventana_explorador.listar_registros_de_categoria(item_categoria, recursivo)
        datos = [
            {
                "codigo": r.get("codigo", ""), "titulo": r.get("titulo", ""),
                "duracion": r.get("duracion", ""), "ruta": r.get("ruta", ""),
                "genero": r.get("genero", ""),
                # Bug real corregido de paso, mismo patrón ya documentado
                # varias veces en este proyecto ("el recorte de silencio
                # nunca se aplicaba al aire"): sin estos 3 campos, un
                # ítem agregado/reemplazado desde el Programador remoto
                # sonaba SIN el recorte de silencio ni el nivelado ya
                # calculados para ese archivo -- quedaban en 0/None/0.0
                # a ciegas del lado del diálogo remoto.
                "punto_inicio_ms": r.get("punto_inicio_ms") or 0,
                "punto_fin_ms": r.get("punto_fin_ms"),
                "ganancia_db": r.get("ganancia_db") or 0.0,
            }
            for r in registros
        ]
        return {"ok": True, "datos": {"registros": datos}}

    def _listar_registros_por_genero_remoto(self, params: dict) -> dict:
        """Usado por el Musicalizador remoto para elegir un Pisador
        ESPECÍFICO -- mismo filtro que ya usa "Agregar Pisador" en
        Ventana 2/Auxiliar y el Pisador del Musicalizador local."""
        genero = params.get("genero") or ""
        registros = self.ventana_explorador.listar_registros_por_genero(genero)
        datos = [
            {
                "codigo": r.get("codigo", ""), "titulo": r.get("titulo", ""),
                "duracion": r.get("duracion", ""), "ruta": r.get("ruta", ""),
            }
            for r in registros
        ]
        return {"ok": True, "datos": {"registros": datos}}

    def _resolver_registro_por_ruta_remoto(self, params: dict) -> dict:
        """Usado por el Musicalizador remoto para mostrar el TÍTULO
        real de un ítem Específico (columna "Título", mismo criterio
        que `_texto_titulo()` de la versión local) y por el
        Programador remoto para la pre-escucha (análisis de audio del
        ítem seleccionado)."""
        ruta = params.get("ruta") or ""
        registro = self.ventana_explorador.buscar_registro_por_ruta(ruta)
        if registro is None:
            return {"ok": True, "datos": {"registro": None}}
        datos = {
            "codigo": registro.get("codigo", ""), "titulo": registro.get("titulo", ""),
            "duracion": registro.get("duracion", ""), "ruta": registro.get("ruta", ""),
            "genero": registro.get("genero", ""),
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
        }
        return {"ok": True, "datos": {"registro": datos}}

    # ------------------------------------------------------------------
    # Pre-escucha remota del Programador (pedido explícito: "todo lo
    # que tiene el principal y este no" -- el Programador local tiene
    # "▶ Previo"/"⏹ Detener" desde la ronda 121). Motor DEDICADO,
    # creado recién al primer pedido, SIEMPRE por la salida de
    # Preescucha configurada (aplicar_procesador=False, nunca la
    # Master que va al aire) -- mismo criterio que el ▶ Previo local.
    # ------------------------------------------------------------------
    def _motor_previo_remoto_o_crear(self) -> MotorAudio:
        if self._motor_previo_remoto is None:
            audio_cfg = self._config.get("audio", {})
            id_dispositivo = audio_cfg.get("dispositivo_preescucha")
            if id_dispositivo in (None, "default"):
                id_dispositivo = None
            self._motor_previo_remoto = MotorAudio(id_dispositivo, aplicar_procesador=False)
        return self._motor_previo_remoto

    def _programador_previo_reproducir_remoto(self, params: dict) -> dict:
        ruta = params.get("ruta") or ""
        if not ruta:
            return {"ok": False, "error": "Falta la ruta del archivo a pre-escuchar."}
        motor = self._motor_previo_remoto_o_crear()
        motor.reproducir(
            ruta,
            punto_inicio_ms=int(params.get("punto_inicio_ms") or 0),
            punto_fin_ms=params.get("punto_fin_ms"),
            ganancia_db=float(params.get("ganancia_db") or 0.0),
        )
        return {"ok": True}

    def _programador_previo_detener_remoto(self) -> dict:
        if self._motor_previo_remoto is not None:
            self._motor_previo_remoto.detener()
        return {"ok": True}

    # ------------------------------------------------------------------
    # Programador remoto (pedido explícito: "que pueda mediante otro
    # botón, programar, igual que en el programa principal" -- y,
    # ronda posterior, "dame todo y las mismas opciones... Todo lo que
    # tiene el principal y este no"): cubre el flujo central
    # (cargar/armar/guardar/aplicar), reordenar, copiar/pegar,
    # duplicar para otro día, Comando FMT/HTH, Ítem Aleatorio,
    # Reemplazar y pre-escucha -- reusando SIEMPRE los MISMOS métodos
    # que ya usa VentanaProgramador/config.settings.
    # ------------------------------------------------------------------
    def _programador_listar_guardadas_remoto(self) -> dict:
        datos = [
            {"tipo": tipo, "clave": clave, "nombre": nombre}
            for tipo, clave, nombre in listar_programaciones()
        ]
        return {"ok": True, "datos": {"programaciones": datos}}

    def _programador_cargar_guardada_remoto(self, params: dict) -> dict:
        tipo = params.get("tipo", "")
        clave = params.get("clave", "")
        contenido = obtener_programacion(tipo, clave)
        if contenido is None:
            return {"ok": False, "error": "No se encontró esa programación guardada."}
        return {"ok": True, "datos": {"nombre": contenido.get("nombre", ""), "bloques": contenido.get("bloques", [])}}

    def _programador_guardar_remoto(self, params: dict) -> dict:
        nombre = (params.get("nombre") or "").strip()
        bloques = params.get("bloques") or []
        dias_semana = params.get("dias_semana") or []
        fecha_especifica = params.get("fecha_especifica") or None
        if not nombre:
            return {"ok": False, "error": "Falta el nombre de la programación."}
        if not dias_semana and not fecha_especifica:
            return {"ok": False, "error": "Elegí al menos un día de la semana o una fecha específica."}
        guardar_programacion(nombre, bloques, dias_semana=dias_semana, fecha_especifica=fecha_especifica)
        registrar_evento(f"Control remoto: programación \"{nombre}\" guardada de forma remota")
        return {"ok": True}

    def _programador_aplicar_ahora_remoto(self, params: dict) -> dict:
        bloques = params.get("bloques") or []
        self._aplicar_programacion_ahora(bloques)
        return {"ok": True}

    # ------------------------------------------------------------------
    # Musicalizador remoto (pedido explícito: "que pueda mediante otro
    # botón, musicalizar, igual que en el programa principal") -- MVP
    # deliberado, mismo criterio que el Programador remoto de arriba:
    # cubre crear/editar/guardar formatos con ítems Específico/
    # Aleatorio/Subformato, sin Pisador (queda para una ronda futura
    # si hace falta).
    # ------------------------------------------------------------------
    def _musicalizador_obtener_formato_remoto(self, params: dict) -> dict:
        nombre = params.get("nombre") or ""
        formato = obtener_formato(nombre)
        if formato is None:
            return {"ok": False, "error": f"No se encontró el formato '{nombre}'."}
        return {"ok": True, "datos": {"items": formato.get("items", [])}}

    def _musicalizador_guardar_formato_remoto(self, params: dict) -> dict:
        nombre = (params.get("nombre") or "").strip()
        items = params.get("items") or []
        forzar = bool(params.get("forzar"))
        if not nombre:
            return {"ok": False, "error": "Falta el nombre del formato."}
        todos_los_formatos = cargar_musicalizador()["formatos"]
        problemas = validar_formato(self.ventana_explorador, nombre, items, todos_los_formatos)
        bloqueantes = [p for p in problemas if p["bloquea"]]
        if bloqueantes:
            return {"ok": False, "error": "No se puede guardar: " + " / ".join(p["mensaje"] for p in bloqueantes)}
        avisos = [p for p in problemas if not p["bloquea"]]
        if avisos and not forzar:
            return {
                "ok": False, "requiere_confirmacion": True,
                "avisos": [p["mensaje"] for p in avisos],
            }
        guardar_formato(nombre, items)
        registrar_evento(f"Control remoto: formato del Musicalizador \"{nombre}\" guardado de forma remota")
        return {"ok": True}

    def _musicalizador_nuevo_formato_remoto(self, params: dict) -> dict:
        nombre = (params.get("nombre") or "").strip()
        if not nombre:
            return {"ok": False, "error": "Falta el nombre del formato."}
        if obtener_formato(nombre) is not None:
            return {"ok": False, "error": f"Ya existe un formato llamado '{nombre}'."}
        guardar_formato(nombre, [])
        return {"ok": True}

    def _musicalizador_eliminar_formato_remoto(self, params: dict) -> dict:
        nombre = params.get("nombre") or ""
        eliminar_formato(nombre)
        registrar_evento(f"Control remoto: formato del Musicalizador \"{nombre}\" eliminado de forma remota")
        return {"ok": True}

    def _musicalizador_renombrar_formato_remoto(self, params: dict) -> dict:
        nombre_viejo = params.get("nombre_viejo") or ""
        nombre_nuevo = (params.get("nombre_nuevo") or "").strip()
        if not nombre_nuevo:
            return {"ok": False, "error": "Falta el nombre nuevo."}
        if not renombrar_formato(nombre_viejo, nombre_nuevo):
            return {"ok": False, "error": f"Ya existe un formato llamado '{nombre_nuevo}'."}
        return {"ok": True}

    def _emision_agregar_ciclo_fmt_remoto(self, params: dict) -> dict:
        """Pedido explícito ("en la ventana 2 pueda también cargar x
        cantidad de tiempo de FMT") — mismo motor que ya usa el botón
        local `_agregar_ciclo_fmt_emision()`
        (`GestorPlaylist.insertar_ciclo_fmt_por_tiempo`, AGREGA al
        final de lo que ya hay cargado, nunca limpia Emisión). El
        cliente decide qué mostrarle al operador según `cantidad`
        (0 = el formato no generó nada) — acá solo se ejecuta y se
        informa el resultado crudo."""
        nombre_formato = (params.get("nombre_formato") or "").strip()
        if not nombre_formato:
            return {"ok": False, "error": "Falta el nombre del formato."}
        try:
            minutos = float(params.get("minutos"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "Cantidad de minutos inválida."}
        cantidad = self.gestor_emision.insertar_ciclo_fmt_por_tiempo(nombre_formato, minutos)
        registrar_evento(
            f"Control remoto: agregó ciclo FMT '{nombre_formato}' (~{minutos} min) a "
            f"Emisión de forma remota — {cantidad} ítem(s)"
        )
        return {"ok": True, "datos": {"cantidad": cantidad, "nombre_formato": nombre_formato, "minutos": minutos}}

    def _estado_transporte_remoto(self) -> dict:
        v1 = self.ventana_publicidad
        v2 = self.ventana_emision.panel
        return {
            "v1": {
                "ahora": v1.lbl_titulo_actual.text(),
                "luego": v1.lbl_titulo_siguiente.text(),
                "automatico_activo": v1.esta_en_automatico(),
            },
            "v2": {
                "ahora": v2.lbl_titulo_actual.text(),
                "luego": v2.lbl_titulo_siguiente.text(),
                "stop_bloqueado": v2._stop_bloqueado_por_automatico,
            },
        }

    def _accion_transporte_remota(self, ventana: str, accion: str) -> dict:
        """Dispara el MISMO botón que apretaría el operador en persona
        (`boton.click()`, no un atajo por señal aparte) — así respeta
        cualquier guard/confirmación que ya tenga ese botón, sin
        duplicar esa lógica acá. Único caso especial: el Stop de
        Ventana 2 puede quedar bloqueado por el Automático de Ventana 1
        y mostrar un QMessageBox MODAL — clickearlo a ciegas congelaría
        el proceso principal esperando un click que nadie puede dar
        del otro lado del socket, así que ACÁ se chequea el mismo flag
        que usa ese botón y se devuelve un error en vez de clickear."""
        if ventana == "v1":
            objetivo = self.ventana_publicidad
        elif ventana == "v2":
            objetivo = self.ventana_emision.panel
        else:
            return {"ok": False, "error": f"Ventana desconocida: {ventana!r} (usar 'v1' o 'v2')"}

        if ventana == "v2" and accion == "stop" and objetivo._stop_bloqueado_por_automatico:
            return {"ok": False, "error": "Stop bloqueado: el modo AUTOMÁTICO de Ventana 1 está activo."}

        boton = {"play": "btn_play", "stop": "btn_stop", "cut": "btn_cut"}.get(accion)
        if boton is None or not hasattr(objetivo, boton):
            return {"ok": False, "error": f"Acción desconocida: {accion!r} (usar 'play', 'stop' o 'cut')"}
        getattr(objetivo, boton).click()
        return {"ok": True}

    def _importar_archivo_remoto(self, params: dict) -> dict:
        import base64
        import os
        import tempfile

        nombre_archivo = (params.get("nombre_archivo") or "").strip()
        contenido_base64 = params.get("contenido_base64") or ""
        categoria_ruta = params.get("categoria_ruta") or []
        titulo = (params.get("titulo") or "").strip()
        artista = (params.get("artista") or "").strip()
        genero = params.get("genero") or ""

        if not nombre_archivo or not contenido_base64:
            return {"ok": False, "error": "Falta el archivo (nombre_archivo/contenido_base64)."}
        if not titulo:
            return {"ok": False, "error": "Falta el título."}

        from gui.styles import LISTA_GENEROS
        if genero not in LISTA_GENEROS:
            return {"ok": False, "error": f"Género inválido: {genero!r} (opciones: {', '.join(LISTA_GENEROS)})"}

        item_categoria = self.ventana_explorador.buscar_categoria_por_ruta(categoria_ruta)
        if item_categoria is None:
            return {"ok": False, "error": f"No se encontró la categoría {categoria_ruta!r}."}

        try:
            contenido = base64.b64decode(contenido_base64)
        except (ValueError, TypeError) as error:
            return {"ok": False, "error": f"El archivo llegó corrupto (base64 inválido): {error}"}

        _, extension = os.path.splitext(nombre_archivo)
        descriptor, ruta_temporal = tempfile.mkstemp(suffix=extension or ".mp3", prefix="subida_remota_")
        try:
            with os.fdopen(descriptor, "wb") as f:
                f.write(contenido)
            registro = self.ventana_explorador._completar_alta_archivo(
                ruta_temporal, item_categoria, titulo, artista, genero,
            )
        finally:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)

        registrar_evento(f"Control remoto: archivo subido e importado — \"{titulo}\" ({registro['codigo']})")
        return {"ok": True, "datos": {"codigo": registro["codigo"], "ruta": registro["ruta"]}}

    def _actualizar_reiniciar_principal_remoto(self) -> dict:
        """Actualizar y reiniciar la RADIO (esta app) desde la
        satélite -- pedido explícito: "actualiza pero reinicia el
        satélite, no el principal... ¿se puede arreglar? o si o si
        debo ir hasta la pc?". Mismo mecanismo que ya usa el botón
        local (Configuración → Actualizaciones →
        `VentanaConfiguracion._aplicar_actualizacion`), disparado acá
        por el socket en vez de un click. La confirmación ("esto corta
        el aire un momento") la pide la propia satélite ANTES de
        mandar este pedido -- mismo criterio ya establecido para el
        resto de las acciones remotas sensibles (Automático, Aplicar
        Ahora): un QMessageBox acá sería MODAL y congelaría este
        proceso esperando un click que nadie puede dar del otro lado.

        El `git pull` (`aplicar_actualizacion()`) corre SÍNCRONO acá,
        hasta 120s -- igual que el botón local, no es un riesgo nuevo.
        Lo que SÍ hay que diferir es el reinicio en sí: `reiniciar_
        aplicacion()` termina en `app.quit()`, y si se llamara directo
        el proceso se cerraría ANTES de que `core/servidor_control_
        remoto.py:_procesar()` llegue a escribir esta respuesta en el
        socket -- la satélite vería la conexión cortada sin saber si
        funcionó. `QTimer.singleShot` da el tiempo justo para que la
        respuesta salga primero."""
        exito, mensaje = actualizador.aplicar_actualizacion()
        if not exito:
            registrar_error(f"Control remoto: actualización de la radio falló — {mensaje}")
            return {"ok": False, "error": mensaje}

        registrar_evento("Control remoto: actualización aplicada, reiniciando la radio a pedido de la satélite")
        self.preparar_cierre_por_actualizacion()
        QTimer.singleShot(500, lambda: actualizador.reiniciar_aplicacion(QApplication.instance()))
        return {"ok": True, "datos": {"mensaje": mensaje}}

    def _obtener_log_aplicacion_remoto(self, params: dict) -> dict:
        """Pedido explícito: "agregá la posibilidad de acceder al
        archivo de log desde el satélite, para poder también corregir
        futuros errores" -- devuelve las últimas N líneas de `config/
        data/log_aplicacion.txt` (nunca el archivo entero: puede crecer
        hasta TAMAÑO_MAXIMO_LOG_BYTES, un tail acotado ya alcanza para
        diagnosticar sin inflar el mensaje del socket)."""
        maximo_lineas = params.get("lineas") or 500
        try:
            maximo_lineas = int(maximo_lineas)
        except (TypeError, ValueError):
            maximo_lineas = 500
        maximo_lineas = max(50, min(maximo_lineas, 5000))

        if not os.path.isfile(ARCHIVO_LOG):
            return {"ok": True, "datos": {"contenido": "", "lineas_totales": 0, "lineas_devueltas": 0}}
        try:
            with open(ARCHIVO_LOG, "r", encoding="utf-8", errors="replace") as f:
                lineas = f.readlines()
        except OSError as error:
            return {"ok": False, "error": f"No se pudo leer el log: {error}"}

        recortadas = lineas[-maximo_lineas:]
        return {
            "ok": True,
            "datos": {
                "contenido": "".join(recortadas),
                "lineas_totales": len(lineas),
                "lineas_devueltas": len(recortadas),
            },
        }

    def _reiniciar_pc_forzado_remoto(self) -> dict:
        """Reiniciar la PC ENTERA desde la satélite -- caso real:
        "estoy en la sesión de satélite y tengo que reiniciar TODA la
        PC" — `systemctl reboot -i` corrido A MANO desde la sesión
        virtual de Chrome Remote Desktop falla siempre ("Access
        denied"), porque logind/polkit solo autoriza el reinicio sin
        contraseña a la sesión gráfica ACTIVA (seat0, la física) — y
        esa sesión virtual nunca es la activa.

        Este proceso (la radio) SÍ corre siempre en la sesión física
        (`:0`, forzado por `core/sesion_display.py` desde la ronda del
        bug de "otra sesión le gana de mano al arranque") — así que el
        MISMO `core.reinicio_sistema.reiniciar_pc_forzado()` que ya usa
        el botón local de Configuración, corrido desde ACÁ (disparado
        por el socket en vez de un click), tiene el permiso que a la
        sesión de CRD le falta. La confirmación ("esto reinicia TODA
        la PC, corta el aire") la pide la propia satélite ANTES de
        mandar este pedido -- mismo criterio que el resto de las
        acciones remotas sensibles, un QMessageBox acá sería MODAL y
        congelaría este proceso.

        Sin QTimer diferido: a diferencia de actualizar+reiniciar LA
        APP, acá no hay ningún `app.quit()` de este proceso -- el
        comando solo le pide a systemd que reinicie la MÁQUINA, algo
        que sucede unos segundos después, afuera de este proceso. La
        respuesta al socket sale normal, sin ninguna carrera."""
        exito, mensaje = reinicio_sistema.reiniciar_pc_forzado()
        if not exito:
            registrar_error(f"Control remoto: reinicio forzado de la PC falló — {mensaje}")
            return {"ok": False, "error": mensaje}
        registrar_evento("Control remoto: reinicio forzado de la PC solicitado desde la satélite")
        return {"ok": True, "datos": {"mensaje": mensaje}}

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
            for motor in (gestor.motor, gestor.motor_pisador, gestor.motor_anuncio_manual):
                if motor.id_dispositivo() != id_dispositivo_master:
                    motor.set_dispositivo_salida(id_dispositivo_master)

        self.gestor_emision.set_volumen_base(audio["volumen_master"])
        if self._gestor_auxiliar is not None:
            self._gestor_auxiliar.set_volumen_base(audio["volumen_master"])

        self.gestor_publicidad.avanzar_en_error = reproduccion["avanzar_automaticamente_en_error"]
        self.gestor_publicidad.reintentos_maximos = max(1, reproduccion["reintentos_antes_de_detener"])
        self.gestor_publicidad.duracion_fade_out_v1_ms = reproduccion["duracion_fade_out_v1_ms"]
        self.gestor_publicidad.duracion_fade_in_declick_ms = reproduccion["duracion_fade_in_declick_v1_ms"]
        for motor in (self.gestor_publicidad.motor, self.gestor_publicidad.motor_anuncio_manual):
            if motor.id_dispositivo() != id_dispositivo_master:
                motor.set_dispositivo_salida(id_dispositivo_master)
        self.gestor_publicidad.set_volumen_base(audio["volumen_master"])

        if self.gestor_explorador.motor.id_dispositivo() != id_dispositivo_preescucha:
            self.gestor_explorador.motor.set_dispositivo_salida(id_dispositivo_preescucha)

        self.ventana_explorador.repintar_colores_genero()
        self.ventana_explorador.repintar_estilo_categorias()
        self._aplicar_tamano_fuente_ventanas()

    def _aplicar_tamano_fuente_ventanas(self):
        """Pedido explícito ("el monitor suele estar lejos y cuesta
        leer con el tamaño actual... configurable por las 3 ventanas
        separadas"): tamaño de letra independiente para Publicidad
        (V1), Emisión (V2 -- el Auxiliar comparte el mismo valor, ya
        que reutiliza el mismo widget de lista, PanelReproductor) y el
        Explorador (V3, archivos + categorías). `setStyleSheet()` a
        nivel de INSTANCIA (no de la hoja global de la app) siempre
        gana sobre la QSS general para ese widget puntual -- mismo
        criterio que ya usa el resto de la app para pintar colores en
        caliente sin reiniciar."""
        tamanos = self._config["apariencia"]["tamano_fuente_ventanas"]
        self.ventana_publicidad.tree.setStyleSheet(f"font-size: {tamanos['publicidad']}pt;")
        self.ventana_emision.tree.setStyleSheet(f"font-size: {tamanos['emision']}pt;")
        if self._ventana_auxiliar is not None:
            self._ventana_auxiliar.tree.setStyleSheet(f"font-size: {tamanos['emision']}pt;")
        self.ventana_explorador.tree_archivos.setStyleSheet(f"font-size: {tamanos['explorador']}pt;")
        # Bug real corregido (pedido explícito: "se aplica solo hasta
        # 3 niveles, no a todos"): tree_categorias NO alcanza con un
        # setStyleSheet() -- toda su jerarquía se arma EAGER, antes de
        # que este método corra por primera vez (VentanaExplorador
        # carga la biblioteca completa en su propio __init__, que pasa
        # DENTRO de _construir_paneles_centrales, siempre antes de
        # llegar acá) -- cada nodo ya queda con una fuente EXPLÍCITA
        # (tamaño ya resuelto) desde su creación, y un QFont explícito
        # ya no vuelve a heredar del stylesheet del widget por más que
        # este cambie después. establecer_tamano_fuente_categorias()
        # recorre TODO el árbol y fuerza el tamaño correcto en los 5
        # niveles, sin importar cuándo se creó cada nodo.
        self.ventana_explorador.establecer_tamano_fuente_categorias(tamanos["explorador"])

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
            self._aplicar_tamano_fuente_ventanas()

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
        dialogo.aplicado_procesador_fm.connect(self._reconectar_audio_tras_reinicio_pipewire)
        if dialogo.exec() == VentanaConfiguracion.DialogCode.Accepted:
            self._aplicar_configuracion_en_vivo()
            self.statusBar().showMessage("Configuración guardada y aplicada (sin cortar la reproducción).", 4000)

    def _reconectar_audio_tras_reinicio_pipewire(self):
        """Conectado a VentanaConfiguracion.aplicado_procesador_fm
        (ver gui/panel_procesador_audio.py) -- pedido explícito, reporte
        real de Santiago: "aprieto Bypass y deja mudo, y debo pasar al
        siguiente ítem, que macana, porque tengo que salir de esa
        ventana y luego volver". "Aplicar"/"Bypass" del Procesador FM
        reinician PipeWire/pipewire-pulse/wireplumber a propósito para
        tomar el .conf nuevo -- eso mata cualquier conexión de audio ya
        abierta, dejando MUDO (pero "vivo") cualquier ítem que estuviera
        sonando en ese instante en Ventana 1/2/Auxiliar/Preescucha.

        En vez de obligar al operador a saltar a mano al próximo ítem
        para recuperar sonido, se reconecta SOLO lo que de verdad siga
        "sonando" (esta_reproduciendo() en cada motor -- ver
        MotorAudio.reconectar_tras_reinicio_audio(), preserva posición
        y volumen, no reinicia nada desde el principio). Diferido un
        instante (systemctl --user restart ya espera a que los 3
        servicios terminen de levantar antes de devolver el control,
        pero wireplumber puede tardar un pelo más en terminar de
        reconocer los dispositivos -- mismo margen de seguridad que ya
        usa el resto de la app para "dale un instante al sistema")."""
        def _reconectar():
            motores = [
                self.gestor_publicidad.motor,
                self.gestor_publicidad.motor_anuncio_manual,
                self.gestor_emision.motor,
                self.gestor_emision.motor_pisador,
                self.gestor_emision.motor_anuncio_manual,
                self.gestor_explorador.motor,
            ]
            if self._gestor_auxiliar is not None:
                motores.extend([
                    self._gestor_auxiliar.motor,
                    self._gestor_auxiliar.motor_pisador,
                    self._gestor_auxiliar.motor_anuncio_manual,
                ])
            for motor in motores:
                motor.reconectar_tras_reinicio_audio()

        QTimer.singleShot(600, _reconectar)
