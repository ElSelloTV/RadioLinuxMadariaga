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
from satelite.dialogo_configuracion_conexion import DialogoConfiguracionConexion
from satelite.dialogo_musicalizador_remoto import DialogoMusicalizadorRemoto
from satelite.dialogo_programador_remoto import DialogoProgramadorRemoto
from satelite.dialogo_subir_archivo import DialogoSubirArchivo

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
        self._widgets_v2 = self._fila_transporte(layout_transporte, "Ventana 2 (Emisión)", "v2")
        layout.addWidget(self.grupo_transporte)

        layout.addStretch()
        self.setCentralWidget(central)
        self._set_widgets_habilitados(False)

    def _set_widgets_habilitados(self, activo: bool):
        self.grupo_subir.setEnabled(activo)
        self.grupo_transporte.setEnabled(activo)
        self.btn_programador.setEnabled(activo)
        self.btn_musicalizador.setEnabled(activo)

    def _fila_transporte(self, layout_padre, titulo: str, ventana: str) -> dict:
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
