#!/usr/bin/env python3
"""
main.py
--------------------------------------------------------
Punto de entrada de la aplicación.
Solo se encarga de:
1. Inicializar QApplication.
2. Aplicar la hoja de estilos global (gui/styles.py).
3. Instanciar y mostrar la ventana principal (gui/main_window.py).

Toda la lógica vive en gui/ (interfaz) y core/ (motor), este
archivo debe permanecer siempre mínimo.
--------------------------------------------------------
"""

import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

from gui.main_window import MainWindow
from gui.dialogo_preload_biblioteca import DialogoPreloadBiblioteca
from gui.styles import qss_para_tema
from config.settings import cargar_configuracion, registrar_error, registrar_evento
from core.instancia_unica import adquirir_bloqueo_instancia_unica

RUTA_ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icono.png")


def _manejar_excepcion_no_capturada(tipo, valor, traceback_obj):
    """PySide6, si una excepción ocurre DENTRO de un slot (ej. el
    handler de un botón), por defecto la imprime a stderr y la
    aplicación sigue viva — no crashea, pero esa acción del operador
    silenciosamente no hizo nada. Eso es indistinguible, para el
    operador, de "el botón no respondió" (síntoma real reportado:
    Play de Ventana 2 sin responder sin ningún error visible). Este
    hook captura esa excepción en el log ANTES de dejar que Qt siga
    con su manejo por defecto, para poder reconstruir qué pasó."""
    detalle = "".join(traceback.format_exception(tipo, valor, traceback_obj))
    registrar_error(f"Excepción no capturada:\n{detalle}")
    sys.__excepthook__(tipo, valor, traceback_obj)


def main():
    sys.excepthook = _manejar_excepcion_no_capturada

    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Radio Tuyú")
    app.setApplicationDisplayName("Auto-Radio Tuyú")
    if os.path.exists(RUTA_ICONO):
        app.setWindowIcon(QIcon(RUTA_ICONO))

    # Instancia única (pedido explícito, caso real: un operador clickeó
    # el ícono de escritorio varias veces y terminó con 3 instancias
    # sonando encima una de la otra, sin poder identificar de dónde
    # salía cada audio) — si ya hay otra instancia corriendo, avisa y
    # se cierra ACÁ MISMO, antes de tocar ninguna playlist ni abrir
    # ningún motor de audio nuevo.
    if not adquirir_bloqueo_instancia_unica():
        registrar_evento("Arranque bloqueado: ya había otra instancia de la aplicación abierta")
        QMessageBox.warning(
            None, "Auto-Radio Tuyú ya está abierto",
            "El programa ya está abierto en otra ventana.\n\n"
            "No se puede abrir dos veces a la vez (mezclaría el audio de las\n"
            "dos instancias). Buscá la ventana que ya está abierta —puede\n"
            "estar minimizada— antes de volver a intentar.",
        )
        sys.exit(0)

    # Tema visual (Configuración → General, pedido explícito "Diseñá
    # el tema Claro") — se resuelve ACÁ, antes de armar cualquier
    # ventana, para que arranque directo con el tema correcto (no un
    # parpadeo oscuro->claro). Si config_general.json todavía no
    # existe o está corrupto, cargar_configuracion() ya degrada a los
    # valores de fábrica (tema "oscuro") sin romper el arranque.
    try:
        tema_configurado = cargar_configuracion()["general"]["tema"]
    except Exception:
        tema_configurado = "oscuro"
    app.setStyleSheet(qss_para_tema(tema_configurado))

    # Preload de arranque (pedido explícito): una pantalla breve con
    # el ícono mientras se arma la ventana principal (carga de
    # configuración, biblioteca, playlists persistidas), en vez de que
    # el operador vea la pantalla en blanco unos instantes.
    splash = None
    if os.path.exists(RUTA_ICONO):
        pixmap = QPixmap(RUTA_ICONO).scaled(
            160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        splash = QSplashScreen(pixmap)
        splash.showMessage(
            "Cargando Auto-Radio Tuyú...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        splash.show()
        app.processEvents()

    try:
        cargar_configuracion()
    except Exception as error:
        registrar_error(f"Error al iniciar la aplicación: {error}")

    registrar_evento("Aplicación iniciada")

    ventana = MainWindow()

    # Migración de duración pendiente, con barra de progreso GRÁFICA
    # (pedido explícito: "necesito fluidez... se congela al leer una
    # categoría" + "podés agregar una barra gráfica de preload al
    # inicio"). Antes, la duración faltante de un archivo se calculaba
    # LAZY la primera vez que se veía su categoría — eso era justo la
    # traba real que reportó Santiago. Ahora se migra TODA de una sola
    # vez ACÁ, antes de mostrar la ventana, en lotes chicos (nunca un
    # bucle síncrono gigante) — encaja con que la PC se reinicia sola
    # todos los días a las 00hs: pagar este costo (real, mutagen tiene
    # que abrir cada archivo) una vez por reinicio es mucho mejor que
    # pagarlo a los tropezones durante el uso real del día. Con una
    # biblioteca ya migrada (el caso normal de acá en más) esto no
    # hace nada — ni siquiera llega a mostrar el diálogo.
    dialogo_migracion = {"instancia": None}

    def _migracion_iniciar(total):
        if total > 0:
            dialogo_migracion["instancia"] = DialogoPreloadBiblioteca(total)

    def _migracion_progreso(hechos, total):
        if dialogo_migracion["instancia"] is not None:
            dialogo_migracion["instancia"].actualizar(hechos, total)

    def _migracion_terminada(hechos):
        if dialogo_migracion["instancia"] is not None:
            dialogo_migracion["instancia"].close()
        if hechos:
            registrar_evento(f"Migración de duración al arrancar: {hechos} archivo(s) analizados y guardados")

    ventana.ventana_explorador.iniciar_migracion_duracion_al_arrancar(
        callback_iniciar=_migracion_iniciar,
        callback_progreso=_migracion_progreso,
        callback_terminado=_migracion_terminada,
    )
    if dialogo_migracion["instancia"] is not None:
        dialogo_migracion["instancia"].exec()

    ventana.show()

    if splash is not None:
        # Pedido explícito ("pantalla de inicio breve que oficie de
        # Preload mientras carga todo"): en vez de cerrar el splash
        # apenas la ventana está lista, se lo deja un instante más
        # (BREVE, con tope fijo) — la búsqueda de actualización YA NO
        # corre sola al arrancar (pedido explícito de otra ronda: "se
        # actualizará solo por el menú Configuración"), así que este
        # instante extra es puro margen visual, no cubre ninguna
        # consulta de red. La reproducción — incluido el arranque
        # automático del bloque vigente — NUNCA espera a este cierre:
        # corre por su cuenta en los timers internos de MainWindow,
        # que ya están corriendo aunque el splash siga tapando la
        # pantalla un instante más.
        splash.showMessage(
            "Cargando Auto-Radio Tuyú...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        QTimer.singleShot(1200, lambda: splash.finish(ventana))
    codigo_salida = app.exec()
    registrar_evento(f"Aplicación cerrada (código {codigo_salida})")
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()
