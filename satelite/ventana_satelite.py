"""
satelite/ventana_satelite.py
--------------------------------------------------------
Ventana principal de la app satélite (pedido explícito: "una app
aparte satélite... pueda controlar el programa en ejecución por el
usuario Radio... incluso subir algún archivo de audio al explorador").

Alcance de esta primera ronda (confirmado con Santiago): control
básico de transporte (Play/Stop/Cut de Ventana 1 y 2, con su estado
Ahora/Luego) + subir un archivo de audio al Explorador con el mismo
tipo de diálogo de categoría/género que ya usa la app real. Abrir el
Programador/Musicalizador remoto queda para una ronda futura.

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
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import QTimer, Qt

from satelite.cliente_control_remoto import ClienteControlRemoto, ErrorControlRemoto
from satelite.config_satelite import cargar_config_satelite, guardar_config_satelite
from satelite.dialogo_subir_archivo import DialogoSubirArchivo

INTERVALO_POLLING_MS = 3000


class VentanaSatelite(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Radio Tuyú — Satélite (control remoto)")
        self.setMinimumWidth(480)
        self._cliente = None
        self._construir_ui()
        self._cargar_configuracion_en_ui()

        self._timer_estado = QTimer(self)
        self._timer_estado.setInterval(INTERVALO_POLLING_MS)
        self._timer_estado.timeout.connect(self._actualizar_estado_transporte)

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        grupo_conexion = QGroupBox("Conexión")
        form_conexion = QFormLayout(grupo_conexion)
        self.txt_host = QLineEdit()
        self.spin_puerto = QLineEdit()
        self.txt_token = QLineEdit()
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        form_conexion.addRow("Host:", self.txt_host)
        form_conexion.addRow("Puerto:", self.spin_puerto)
        form_conexion.addRow("Token:", self.txt_token)
        self.btn_conectar = QPushButton("🔌 Conectar")
        self.btn_conectar.clicked.connect(self._conectar)
        form_conexion.addRow(self.btn_conectar)
        self.lbl_estado_conexion = QLabel("Sin conectar.")
        self.lbl_estado_conexion.setWordWrap(True)
        form_conexion.addRow(self.lbl_estado_conexion)
        layout.addWidget(grupo_conexion)

        self.grupo_transporte = QGroupBox("Transporte")
        layout_transporte = QVBoxLayout(self.grupo_transporte)
        self._widgets_v1 = self._fila_transporte(layout_transporte, "Ventana 1 (Publicidad)", "v1")
        self._widgets_v2 = self._fila_transporte(layout_transporte, "Ventana 2 (Emisión)", "v2")
        self.grupo_transporte.setEnabled(False)
        layout.addWidget(self.grupo_transporte)

        self.grupo_subir = QGroupBox("Subir archivo al Explorador")
        layout_subir = QVBoxLayout(self.grupo_subir)
        self.btn_elegir_archivo = QPushButton("📂 Elegir archivo y subir...")
        self.btn_elegir_archivo.clicked.connect(self._elegir_y_subir_archivo)
        layout_subir.addWidget(self.btn_elegir_archivo)
        self.lbl_estado_subida = QLabel("")
        self.lbl_estado_subida.setWordWrap(True)
        layout_subir.addWidget(self.lbl_estado_subida)
        self.grupo_subir.setEnabled(False)
        layout.addWidget(self.grupo_subir)

        layout.addStretch()

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
        btn_stop = QPushButton("■ Stop")
        btn_cut = QPushButton("✂ Cut")
        btn_play.clicked.connect(lambda: self._accion_transporte(ventana, "play"))
        btn_stop.clicked.connect(lambda: self._accion_transporte(ventana, "stop"))
        btn_cut.clicked.connect(lambda: self._accion_transporte(ventana, "cut"))
        fila_botones.addWidget(btn_play)
        fila_botones.addWidget(btn_stop)
        fila_botones.addWidget(btn_cut)
        layout.addLayout(fila_botones)

        layout_padre.addWidget(grupo)
        return {"lbl_ahora": lbl_ahora, "lbl_luego": lbl_luego}

    # ------------------------------------------------------------------
    def _cargar_configuracion_en_ui(self):
        config = cargar_config_satelite()
        self.txt_host.setText(config["host"])
        self.spin_puerto.setText(str(config["puerto"]))
        self.txt_token.setText(config["token"])

    def _guardar_configuracion_de_ui(self):
        try:
            puerto = int(self.spin_puerto.text().strip())
        except ValueError:
            puerto = 8765
        guardar_config_satelite({
            "host": self.txt_host.text().strip() or "127.0.0.1",
            "puerto": puerto,
            "token": self.txt_token.text().strip(),
        })

    # ------------------------------------------------------------------
    def _conectar(self):
        self._guardar_configuracion_de_ui()
        config = cargar_config_satelite()
        self._cliente = ClienteControlRemoto(config["host"], config["puerto"], config["token"])
        try:
            respuesta = self._cliente.ping()
        except ErrorControlRemoto as error:
            self._cliente = None
            self.lbl_estado_conexion.setText(f"⚠ {error}")
            self.grupo_transporte.setEnabled(False)
            self.grupo_subir.setEnabled(False)
            self._timer_estado.stop()
            return

        if not respuesta.get("ok"):
            self._cliente = None
            self.lbl_estado_conexion.setText(
                "⚠ El servidor respondió pero rechazó el pedido -- revisá el token."
            )
            self.grupo_transporte.setEnabled(False)
            self.grupo_subir.setEnabled(False)
            self._timer_estado.stop()
            return

        self.lbl_estado_conexion.setText("✅ Conectado.")
        self.grupo_transporte.setEnabled(True)
        self.grupo_subir.setEnabled(True)
        self._actualizar_estado_transporte()
        self._timer_estado.start()

    # ------------------------------------------------------------------
    def _actualizar_estado_transporte(self):
        if self._cliente is None:
            return
        try:
            estado = self._cliente.estado_transporte()
        except ErrorControlRemoto as error:
            self.lbl_estado_conexion.setText(f"⚠ Se perdió la conexión: {error}")
            self._timer_estado.stop()
            self.grupo_transporte.setEnabled(False)
            self.grupo_subir.setEnabled(False)
            return

        v1 = estado.get("v1", {})
        self._widgets_v1["lbl_ahora"].setText(f"Ahora: {v1.get('ahora') or '—'}")
        etiqueta_luego_v1 = f"Luego: {v1.get('luego') or '—'}"
        if v1.get("automatico_activo"):
            etiqueta_luego_v1 += "   (AUTOMÁTICO activo)"
        self._widgets_v1["lbl_luego"].setText(etiqueta_luego_v1)

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

        self.lbl_estado_subida.setText("Subiendo...")
        try:
            respuesta = self._cliente.importar_archivo(
                os.path.basename(ruta_local), contenido_base64, datos["categoria_ruta"],
                datos["titulo"], datos["artista"], datos["genero"],
            )
        except ErrorControlRemoto as error:
            self.lbl_estado_subida.setText(f"⚠ {error}")
            return

        if not respuesta.get("ok"):
            self.lbl_estado_subida.setText(f"⚠ {respuesta.get('error', 'Falló la subida.')}")
            return

        codigo = respuesta.get("datos", {}).get("codigo", "")
        self.lbl_estado_subida.setText(f"✅ Subido e importado como \"{datos['titulo']}\" ({codigo}).")
