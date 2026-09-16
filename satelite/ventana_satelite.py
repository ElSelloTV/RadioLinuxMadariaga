"""
satelite/ventana_satelite.py
--------------------------------------------------------
Ventana principal de la app satélite (pedido explícito: "una app
aparte satélite... pueda controlar el programa en ejecución por el
usuario Radio... incluso subir algún archivo de audio al explorador").

Pedido explícito de reorganización (ronda posterior, "ordenemos"):
- La configuración de conexión (host/puerto/token) ya NO está a la
  vista -- vive en un diálogo aparte, disponible desde el menú
  "Conexión" de arriba (`DialogoConfiguracionConexion`).
- La carga de archivos es lo PRIMERO que se ve, arriba de todo.
- "Poner y/o sacar el automático" vive en el menú "Opciones".
- Dos botones nuevos, "📅 Programador" y "🎵 Musicalizador", abren
  versiones remotas de esas ventanas (alcance MVP deliberado, ver los
  docstrings de `dialogo_programador_remoto.py`/
  `dialogo_musicalizador_remoto.py` y la nota en CLAUDE.md).
- Pedido explícito (ronda posterior): el Programador remoto puede
  insertar un Comando FMT en un bloque, y Ventana 2 (Emisión) tiene un
  botón "🎵 FMT..." para agregar X minutos de un formato del
  Musicalizador sin borrar lo ya cargado — mismos dos mecanismos que
  ya tenía la app principal, ahora también remotos.

Sin salida de audio — es lo único que queda afuera a propósito (pedido
explícito: "sería un programa aparte satélite sin salida de audio").
Todo lo demás pasa por `core/servidor_control_remoto.py`, que resuelve
cada pedido reusando los MISMOS métodos que ya usa la GUI principal —
esta ventana nunca toca ningún JSON de la radio directo.
--------------------------------------------------------
"""
import base64
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QMessageBox, QDialog,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction

from satelite.cliente_control_remoto import ClienteControlRemoto, ErrorControlRemoto
from satelite.config_satelite import cargar_config_satelite, guardar_config_satelite
from satelite.dialogo_actualizaciones import DialogoActualizaciones
from satelite.dialogo_ciclo_fmt_remoto import DialogoCicloFMTRemoto
from satelite.dialogo_configuracion_conexion import DialogoConfiguracionConexion
from satelite.dialogo_musicalizador_remoto import DialogoMusicalizadorRemoto
from satelite.dialogo_programador_remoto import DialogoProgramadorRemoto
from satelite.dialogo_subir_archivo import DialogoSubirArchivo
from satelite.dialogo_ver_log import DialogoVerLog

INTERVALO_POLLING_MS = 3000


class VentanaSatelite(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remoto Radio — control remoto de Auto-Radio Tuyú")
        self.setMinimumWidth(480)
        self._cliente = None
        self._construir_menu()
        self._construir_ui()

        self._timer_estado = QTimer(self)
        self._timer_estado.setInterval(INTERVALO_POLLING_MS)
        self._timer_estado.timeout.connect(self._actualizar_estado_transporte)

        # Auto-conectar al abrir SI ya hay una conexión guardada de
        # antes -- evita tener que ir al menú Conexión cada vez que se
        # abre la app. Diferido para no demorar el primer render.
        if cargar_config_satelite().get("token"):
            QTimer.singleShot(0, self._conectar)

    # ------------------------------------------------------------------
    def _construir_menu(self):
        menu_conexion = self.menuBar().addMenu("Conexión")
        accion_configurar = menu_conexion.addAction("⚙ Configurar conexión...")
        accion_configurar.triggered.connect(self._abrir_configuracion_conexion)
        accion_reconectar = menu_conexion.addAction("🔄 Reconectar")
        accion_reconectar.triggered.connect(self._conectar)

        menu_opciones = self.menuBar().addMenu("Opciones")
        self._accion_automatico = QAction("🔁 Automático activo (Ventana 1)", self)
        self._accion_automatico.setCheckable(True)
        self._accion_automatico.triggered.connect(self._on_toggle_automatico_menu)
        menu_opciones.addAction(self._accion_automatico)

        # Pedido explícito: "agregale también en Configuraciones, la
        # opción de actualizar el programa por GitHub, aunque reinice
        # la APP, no importa" — independiente de la conexión con la
        # radio (es git local, no pasa por el socket de control
        # remoto), así que queda disponible siempre, conectado o no.
        menu_config = self.menuBar().addMenu("Configuración")
        accion_actualizaciones = menu_config.addAction("⬇ Actualizaciones...")
        accion_actualizaciones.triggered.connect(self._abrir_actualizaciones)

        # Pedido explícito: "actualiza pero reinicia el satélite, no el
        # principal que está corriendo en la otra sesión... ¿se puede
        # arreglar?" -- esto SÍ pasa por el socket de control remoto
        # (a diferencia de "⬇ Actualizaciones..." de arriba, que es git
        # local de la propia satélite), así que requiere estar
        # conectado a la radio.
        menu_config.addSeparator()
        accion_actualizar_radio = menu_config.addAction("🔁 Actualizar y reiniciar la RADIO (principal)...")
        accion_actualizar_radio.triggered.connect(self._actualizar_reiniciar_radio)
        accion_ver_log = menu_config.addAction("📋 Ver log de la radio...")
        accion_ver_log.triggered.connect(self._ver_log_radio)

        # Pedido explícito, caso real: "estoy en la sesión de satélite
        # y tengo que reiniciar TODA la PC. Como hago?" -- un
        # `systemctl reboot` corrido a mano desde la sesión virtual de
        # Chrome Remote Desktop falla siempre ("Access denied", esa
        # sesión no cuenta como la activa para polkit) -- disparado
        # desde ACÁ, viaja por el socket hasta el proceso de la radio,
        # que SÍ corre en la sesión física y tiene el permiso.
        menu_config.addSeparator()
        accion_reiniciar_pc = menu_config.addAction("💻 Reiniciar la PC (forzado)...")
        accion_reiniciar_pc.triggered.connect(self._reiniciar_pc_forzado)

    def _construir_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        self.lbl_estado_conexion = QLabel("Sin conectar -- configurala desde el menú \"Conexión\".")
        self.lbl_estado_conexion.setWordWrap(True)
        layout.addWidget(self.lbl_estado_conexion)

        # Pedido explícito: "que la carga de archivos sea lo primero
        # arriba" -- es el grupo más usado en el flujo real (recibir
        # un archivo por correo y subirlo), así que va primero.
        self.grupo_subir = QGroupBox("Subir archivo al Explorador")
        layout_subir = QVBoxLayout(self.grupo_subir)
        self.btn_elegir_archivo = QPushButton("📂 Elegir archivo y subir...")
        self.btn_elegir_archivo.clicked.connect(self._elegir_y_subir_archivo)
        layout_subir.addWidget(self.btn_elegir_archivo)
        self.lbl_estado_subida = QLabel("")
        self.lbl_estado_subida.setWordWrap(True)
        layout_subir.addWidget(self.lbl_estado_subida)
        layout.addWidget(self.grupo_subir)

        fila_remotas = QHBoxLayout()
        self.btn_programador = QPushButton("📅 Programador")
        self.btn_musicalizador = QPushButton("🎵 Musicalizador")
        self.btn_programador.clicked.connect(self._abrir_programador_remoto)
        self.btn_musicalizador.clicked.connect(self._abrir_musicalizador_remoto)
        fila_remotas.addWidget(self.btn_programador)
        fila_remotas.addWidget(self.btn_musicalizador)
        layout.addLayout(fila_remotas)

        self.grupo_transporte = QGroupBox("Transporte")
        layout_transporte = QVBoxLayout(self.grupo_transporte)
        self._widgets_v1 = self._fila_transporte(layout_transporte, "Ventana 1 (Publicidad)", "v1")
        # Pedido explícito: "en la ventana 2 pueda también cargar x
        # cantidad de tiempo de FMT" -- exclusivo de V2, mismo criterio
        # que `permitir_ciclo_fmt` en gui/panel_reproductor.py (nunca
        # V1, que ya tiene su propio Comando FMT dentro de un bloque).
        self._widgets_v2 = self._fila_transporte(
            layout_transporte, "Ventana 2 (Emisión)", "v2", permitir_ciclo_fmt=True,
        )
        layout.addWidget(self.grupo_transporte)

        layout.addStretch()
        self.setCentralWidget(central)
        self._set_widgets_habilitados(False)

    def _set_widgets_habilitados(self, activo: bool):
        self.grupo_subir.setEnabled(activo)
        self.grupo_transporte.setEnabled(activo)
        self.btn_programador.setEnabled(activo)
        self.btn_musicalizador.setEnabled(activo)

    def _fila_transporte(self, layout_padre, titulo: str, ventana: str, permitir_ciclo_fmt: bool = False) -> dict:
        grupo = QGroupBox(titulo)
        layout = QVBoxLayout(grupo)
        lbl_ahora = QLabel("Ahora: —")
        lbl_luego = QLabel("Luego: —")
        lbl_ahora.setWordWrap(True)
        lbl_luego.setWordWrap(True)
        layout.addWidget(lbl_ahora)
        layout.addWidget(lbl_luego)

        fila_botones = QHBoxLayout()
        btn_play = QPushButton("▶ Play")
        btn_play.clicked.connect(lambda: self._accion_transporte(ventana, "play"))
        fila_botones.addWidget(btn_play)

        # Pedido explícito: "los demás botones (salvo el Play) se
        # estiran, dejalos cuadrados, del mismo ancho" -- sin
        # setFixedSize, un QPushButton dentro de un QHBoxLayout crece
        # para llenar el espacio sobrante (política Minimum por
        # defecto), dando anchos disparejos según cuánto lugar quede.
        # Stop/Cut pasan a íconos SOLOS (sin texto, con tooltip) en un
        # cuadrado fijo -- mismo criterio ya usado en los botones de
        # transporte del programa principal (glifo + tooltip, sin
        # etiqueta) -- así "cuadrado" es literal, no aproximado. Play
        # queda afuera a propósito, con su texto y su tamaño natural.
        lado_boton_cuadrado = 40
        btn_stop = QPushButton("■")
        btn_stop.setToolTip("Detener")
        btn_cut = QPushButton("✂")
        btn_cut.setToolTip("Cut (corte al siguiente)")
        for boton in (btn_stop, btn_cut):
            boton.setFixedSize(lado_boton_cuadrado, lado_boton_cuadrado)
        btn_stop.clicked.connect(lambda: self._accion_transporte(ventana, "stop"))
        btn_cut.clicked.connect(lambda: self._accion_transporte(ventana, "cut"))
        fila_botones.addWidget(btn_stop)
        fila_botones.addWidget(btn_cut)
        if permitir_ciclo_fmt:
            btn_fmt = QPushButton("🎵 FMT...")
            btn_fmt.setToolTip(
                "Agregar un ciclo de un formato del Musicalizador por X minutos,\n"
                "al final de lo que ya esté cargado (nunca lo borra)."
            )
            btn_fmt.clicked.connect(self._agregar_ciclo_fmt_emision)
            fila_botones.addWidget(btn_fmt)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        layout_padre.addWidget(grupo)
        return {"lbl_ahora": lbl_ahora, "lbl_luego": lbl_luego}

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    def _abrir_configuracion_conexion(self):
        config = cargar_config_satelite()
        dialogo = DialogoConfiguracionConexion(config["host"], config["puerto"], config["token"], parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        guardar_config_satelite(dialogo.resultado())
        self._conectar()

    # ------------------------------------------------------------------
    # Configuración -> Actualizaciones
    # ------------------------------------------------------------------
    def _abrir_actualizaciones(self):
        DialogoActualizaciones(parent=self).exec()

    def _actualizar_reiniciar_radio(self):
        """Pedido explícito: "actualiza pero reinicia el satélite, no
        el principal que está corriendo en la otra sesión... ¿se puede
        arreglar? o si o si debo ir hasta la pc y del principal
        reiniciar?" -- corta el aire un momento (git pull + reinicio
        del proceso principal), así que pide confirmación con un texto
        explícito, mismo criterio que el resto de las acciones que
        interrumpen la emisión desde acá (ver `_on_toggle_automatico_menu`)."""
        if self._cliente is None:
            QMessageBox.warning(self, "Control remoto", "Conectate primero (menú \"Conexión\").")
            return
        respuesta = QMessageBox.question(
            self, "Actualizar la radio",
            "Esto va a actualizar y REINICIAR el programa principal de la radio "
            "(el que está sonando al aire) -- corta la emisión un momento mientras "
            "se reinicia.\n\n¿Confirmás que querés continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            r = self._cliente.actualizar_reiniciar_principal()
        except ErrorControlRemoto as error:
            # Un error de conexión ACÁ es esperable si el pull sí se
            # aplicó y la radio ya se está reiniciando -- el proceso
            # viejo corta el socket antes de que este pedido reciba
            # respuesta. No lo tratamos como una falla dura.
            QMessageBox.information(
                self, "Actualizar la radio",
                f"Se perdió la conexión mientras esperaba la respuesta -- probable que "
                f"la radio ya se esté reiniciando con la actualización aplicada.\n\n"
                f"Detalle: {error}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
        if not r.get("ok"):
            QMessageBox.warning(self, "Actualizar la radio", r.get("error", "No se pudo actualizar."))
            return
        QMessageBox.information(
            self, "Actualizar la radio",
            "Actualización aplicada -- la radio se está reiniciando. Puede tardar unos "
            "segundos en volver a estar disponible.",
        )
        self._timer_estado.stop()

    def _ver_log_radio(self):
        """Pedido explícito: "agregá la posibilidad de acceder al
        archivo de log desde el satélite para poder también corregir
        futuros errores"."""
        if self._cliente is None:
            QMessageBox.warning(self, "Control remoto", "Conectate primero (menú \"Conexión\").")
            return
        DialogoVerLog(self._cliente, parent=self).exec()

    def _reiniciar_pc_forzado(self):
        """Pedido explícito, caso real: "estoy en la sesión de
        satélite y tengo que reiniciar TODA la PC. Como hago?" --
        reinicia la MÁQUINA ENTERA (no solo la radio) desde la sesión
        física, algo que la propia sesión de CRD no puede hacerse a sí
        misma por permisos. Texto de confirmación bien explícito: esto
        también corta la conexión de ESTA app satélite (vive en la
        misma PC física que se está reiniciando)."""
        if self._cliente is None:
            QMessageBox.warning(self, "Control remoto", "Conectate primero (menú \"Conexión\").")
            return
        respuesta = QMessageBox.question(
            self, "Reiniciar la PC",
            "Esto reinicia TODA la PC de la radio -- no solo el programa, la "
            "máquina entera. Corta el aire, y esta misma conexión remota también "
            "se va a cortar (la PC física se apaga y vuelve a prender sola).\n\n"
            "¿Confirmás que querés reiniciar la PC ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            r = self._cliente.reiniciar_pc_forzado()
        except ErrorControlRemoto as error:
            # Igual que con actualizar+reiniciar la radio: perder la
            # conexión justo acá es esperable si el reinicio YA se
            # disparó -- la PC entera se está apagando.
            QMessageBox.information(
                self, "Reiniciar la PC",
                f"Se perdió la conexión mientras esperaba la respuesta -- probable "
                f"que el reinicio ya se haya disparado y la PC se esté apagando.\n\n"
                f"Detalle: {error}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
        if not r.get("ok"):
            QMessageBox.warning(self, "Reiniciar la PC", r.get("error", "No se pudo reiniciar la PC."))
            return
        QMessageBox.information(
            self, "Reiniciar la PC",
            "Reinicio aceptado -- la PC se está reiniciando ahora. Esta conexión "
            "se va a cortar en cualquier momento.",
        )
        self._timer_estado.stop()

    def _conectar(self):
        config = cargar_config_satelite()
        if not config.get("token"):
            self.lbl_estado_conexion.setText("⚠ Configurá la conexión primero (menú \"Conexión\").")
            return
        self._cliente = ClienteControlRemoto(config["host"], config["puerto"], config["token"])
        try:
            respuesta = self._cliente.ping()
        except ErrorControlRemoto as error:
            self._cliente = None
            self.lbl_estado_conexion.setText(f"⚠ {error}")
            self._set_widgets_habilitados(False)
            self._timer_estado.stop()
            return

        if not respuesta.get("ok"):
            self._cliente = None
            self.lbl_estado_conexion.setText(
                "⚠ El servidor respondió pero rechazó el pedido -- revisá el token."
            )
            self._set_widgets_habilitados(False)
            self._timer_estado.stop()
            return

        self.lbl_estado_conexion.setText(f"✅ Conectado a {config['host']}:{config['puerto']}.")
        self._set_widgets_habilitados(True)
        self._actualizar_estado_transporte()
        self._timer_estado.start()

    # ------------------------------------------------------------------
    # Transporte + Automático
    # ------------------------------------------------------------------
    def _actualizar_estado_transporte(self):
        if self._cliente is None:
            return
        try:
            estado = self._cliente.estado_transporte()
        except ErrorControlRemoto as error:
            self.lbl_estado_conexion.setText(f"⚠ Se perdió la conexión: {error}")
            self._timer_estado.stop()
            self._set_widgets_habilitados(False)
            return

        v1 = estado.get("v1", {})
        self._widgets_v1["lbl_ahora"].setText(f"Ahora: {v1.get('ahora') or '—'}")
        etiqueta_luego_v1 = f"Luego: {v1.get('luego') or '—'}"
        if v1.get("automatico_activo"):
            etiqueta_luego_v1 += "   (AUTOMÁTICO activo)"
        self._widgets_v1["lbl_luego"].setText(etiqueta_luego_v1)
        # setChecked() no emite `triggered` -- sincronizar acá nunca
        # dispara el pedido de confirmación por su cuenta.
        self._accion_automatico.setChecked(bool(v1.get("automatico_activo")))

        v2 = estado.get("v2", {})
        self._widgets_v2["lbl_ahora"].setText(f"Ahora: {v2.get('ahora') or '—'}")
        etiqueta_luego_v2 = f"Luego: {v2.get('luego') or '—'}"
        if v2.get("stop_bloqueado"):
            etiqueta_luego_v2 += "   (Stop bloqueado por AUTOMÁTICO de V1)"
        self._widgets_v2["lbl_luego"].setText(etiqueta_luego_v2)

    def _accion_transporte(self, ventana: str, accion: str):
        if self._cliente is None:
            return
        try:
            respuesta = self._cliente.accion_transporte(ventana, accion)
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "Acción rechazada."))
            return
        self._actualizar_estado_transporte()

    def _on_toggle_automatico_menu(self, activar: bool):
        """Pedido explícito: "poner y/o sacar el automático" desde las
        opciones. Mismo criterio de confirmación que la app principal
        (ronda 54) -- PERO la confirmación se pide ACÁ, del lado
        satélite, nunca del lado servidor (un QMessageBox ahí sería
        MODAL y congelaría el proceso principal esperando un click que
        nadie puede dar remoto)."""
        if self._cliente is None:
            self._accion_automatico.setChecked(not activar)
            return
        texto = "ACTIVAR" if activar else "DESACTIVAR"
        respuesta = QMessageBox.question(
            self, "Automático",
            f"¿Confirmás que querés {texto} el modo AUTOMÁTICO de Ventana 1?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            self._accion_automatico.setChecked(not activar)
            return
        try:
            r = self._cliente.alternar_automatico(activar)
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            self._accion_automatico.setChecked(not activar)
            return
        if not r.get("ok"):
            QMessageBox.warning(self, "Control remoto", r.get("error", "No se pudo cambiar."))
            self._accion_automatico.setChecked(not activar)
            return
        self._actualizar_estado_transporte()

    # ------------------------------------------------------------------
    # Programador / Musicalizador remotos
    # ------------------------------------------------------------------
    def _abrir_programador_remoto(self):
        if self._cliente is None:
            return
        DialogoProgramadorRemoto(self._cliente, parent=self).exec()

    def _abrir_musicalizador_remoto(self):
        if self._cliente is None:
            return
        DialogoMusicalizadorRemoto(self._cliente, parent=self).exec()

    def _agregar_ciclo_fmt_emision(self):
        """Pedido explícito: "en la ventana 2 pueda también cargar x
        cantidad de tiempo de FMT" — mismo flujo que el botón local
        equivalente (elegir formato + minutos, AGREGA al final de lo
        ya cargado en Emisión, nunca lo limpia)."""
        if self._cliente is None:
            return
        try:
            formatos = self._cliente.musicalizador_listar_formatos()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return

        dialogo = DialogoCicloFMTRemoto(formatos, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        resultado = dialogo.resultado()
        if resultado is None:
            return
        nombre_formato, minutos = resultado

        try:
            respuesta = self._cliente.emision_agregar_ciclo_fmt(nombre_formato, minutos)
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo agregar el ciclo FMT."))
            return

        cantidad = respuesta.get("datos", {}).get("cantidad", 0)
        if cantidad:
            QMessageBox.information(
                self, "Ciclo FMT",
                f"Agregados {cantidad} ítem(s) de \"{nombre_formato}\" (~{minutos} min) a Emisión.",
            )
        else:
            QMessageBox.warning(
                self, "Ciclo FMT",
                f"El formato \"{nombre_formato}\" no generó ningún ítem — revisá sus\n"
                "categorías/archivos en el Musicalizador Avanzado.",
            )
        self._actualizar_estado_transporte()

    # ------------------------------------------------------------------
    # Subir archivo
    # ------------------------------------------------------------------
    def _elegir_y_subir_archivo(self):
        if self._cliente is None:
            return
        ruta_local, _ = QFileDialog.getOpenFileName(
            self, "Elegir archivo de audio", os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.mp4 *.m4a)",
        )
        if not ruta_local:
            return

        try:
            categorias = self._cliente.listar_categorias()
            generos = self._cliente.listar_generos()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", f"No se pudo leer la biblioteca remota: {error}")
            return

        if not categorias:
            QMessageBox.warning(
                self, "Control remoto",
                "La radio todavía no tiene ninguna categoría creada -- "
                "creá al menos una desde el Explorador antes de subir un archivo.",
            )
            return

        dialogo = DialogoSubirArchivo(ruta_local, categorias, generos, parent=self)
        if dialogo.exec() != DialogoSubirArchivo.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return

        try:
            with open(ruta_local, "rb") as f:
                contenido_base64 = base64.b64encode(f.read()).decode("ascii")
        except OSError as error:
            QMessageBox.warning(self, "Control remoto", f"No se pudo leer el archivo local: {error}")
            return

        # La radio analiza el archivo completo (recorte de silencio +
        # nivelado) ANTES de responder -- para un tema real de varios
        # minutos esto puede tardar bien más que un pedido normal
        # (ver TIMEOUT_IMPORTAR_ARCHIVO_SEGUNDOS), así que se avisa
        # explícitamente en vez de dejar la ventana "quieta" sin
        # ninguna señal de que sigue trabajando.
        self.lbl_estado_subida.setText("Subiendo y analizando en la radio (puede tardar unos segundos)...")
        self.btn_elegir_archivo.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            respuesta = self._cliente.importar_archivo(
                os.path.basename(ruta_local), contenido_base64, datos["categoria_ruta"],
                datos["titulo"], datos["artista"], datos["genero"],
            )
        except ErrorControlRemoto as error:
            self.lbl_estado_subida.setText(f"⚠ {error}")
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_elegir_archivo.setEnabled(True)

        if not respuesta.get("ok"):
            self.lbl_estado_subida.setText(f"⚠ {respuesta.get('error', 'Falló la subida.')}")
            return

        codigo = respuesta.get("datos", {}).get("codigo", "")
        self.lbl_estado_subida.setText(f"✅ Subido e importado como \"{datos['titulo']}\" ({codigo}).")
