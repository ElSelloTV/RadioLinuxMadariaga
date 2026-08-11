"""
core/servidor_control_remoto.py
--------------------------------------------------------
Servidor de control remoto para la app satélite (pedido explícito:
"una app aparte satélite... pueda controlar el programa en ejecución
por el usuario Radio... incluso subir algún archivo de audio al
explorador"). Caso de uso real: Santiago y sus operadores usan
Escritorio Remoto de Chrome para conectarse a la PC de la radio, pero
eso los deja en la sesión de OTRO usuario del sistema (Chrome Remote
Desktop en Linux arma su propia sesión virtual, no se engancha a la
sesión física donde corre esta app como usuario "Radio") — ven un
escritorio limpio, sin la radio. Este servidor corre EMBEBIDO en el
proceso principal, escuchando en 127.0.0.1 — como las dos sesiones
están en la MISMA PC física, loopback alcanza, nunca hace falta
exponer nada a la red real.

Regla de diseño de fondo, la que evita corromper datos: este servidor
NUNCA escribe los JSON de la biblioteca/playlists por su cuenta — cada
acción remota se resuelve llamando a los MISMOS métodos que ya usa la
GUI principal cuando el operador hace click en persona (el
"manejador" que instala `MainWindow`, ver `_manejar_comando_remoto`).
Así hay un solo escritor real de cada JSON (el proceso principal, con
su copia en memoria siempre al día) — nunca dos procesos peleando por
el mismo archivo ni un cambio remoto que el proceso principal
sobrescriba sin saberlo en su próximo guardado.

Protocolo: JSON delimitado por salto de línea sobre TCP. Un pedido =
una respuesta = una conexión (simple y robusto para conexiones
locales de corta vida — no hace falta manejar múltiples pedidos por
socket). Cada pedido debe incluir "token"; si no coincide con el
configurado, se corta la conexión sin responder nada (ni un error
explícito, para no dar pistas a quien no lo tenga).
--------------------------------------------------------
"""
import json

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QHostAddress, QTcpServer

# Margen de sobra para subir un archivo de audio entero en base64
# (un tema de varios MB todavía entra cómodo acá).
TAMANO_MAXIMO_MENSAJE = 150 * 1024 * 1024


class ServidorControlRemoto(QObject):
    """`self.manejador` es un callable `(accion: str, params: dict) ->
    dict` que resuelve cada comando — lo setea `MainWindow` después de
    construir el servidor; este módulo no conoce nada de la GUI real
    (mismo patrón de callback ya usado en el proyecto entre core/ y
    gui/, ej. `GestorPlaylist.al_cambiar_formato_activo`)."""

    def __init__(self, puerto: int, token: str, parent=None):
        super().__init__(parent)
        self.manejador = None
        self._puerto = puerto
        self._token = token
        self._servidor = QTcpServer(self)
        self._servidor.newConnection.connect(self._on_nueva_conexion)
        self._buffers = {}

    def iniciar(self):
        """Devuelve (True, "") si arrancó bien, (False, mensaje) si no
        — nunca tira una excepción (ej. puerto ya en uso)."""
        if self._servidor.isListening():
            return True, ""
        ok = self._servidor.listen(QHostAddress.LocalHost, self._puerto)
        if not ok:
            return False, self._servidor.errorString()
        return True, ""

    def detener(self):
        self._servidor.close()
        self._buffers.clear()

    def esta_activo(self) -> bool:
        return self._servidor.isListening()

    def puerto(self) -> int:
        return self._servidor.serverPort()

    # ------------------------------------------------------------------
    def _on_nueva_conexion(self):
        while self._servidor.hasPendingConnections():
            socket = self._servidor.nextPendingConnection()
            self._buffers[socket] = bytearray()
            socket.readyRead.connect(lambda s=socket: self._on_datos(s))
            socket.disconnected.connect(lambda s=socket: self._buffers.pop(s, None))

    def _on_datos(self, socket):
        buffer = self._buffers.get(socket)
        if buffer is None:
            return
        buffer.extend(bytes(socket.readAll()))
        if len(buffer) > TAMANO_MAXIMO_MENSAJE:
            self._buffers.pop(socket, None)
            socket.disconnectFromHost()
            return
        indice = buffer.find(b"\n")
        if indice == -1:
            return
        linea = bytes(buffer[:indice])
        self._buffers.pop(socket, None)  # un pedido por conexión, no hace falta más
        self._procesar(socket, linea)

    def _procesar(self, socket, linea: bytes):
        try:
            pedido = json.loads(linea.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            socket.disconnectFromHost()
            return
        if not isinstance(pedido, dict) or pedido.get("token") != self._token:
            socket.disconnectFromHost()
            return
        accion = pedido.get("accion", "")
        params = pedido.get("params") or {}
        if self.manejador is None:
            respuesta = {"ok": False, "error": "El servidor no tiene un manejador configurado."}
        else:
            try:
                respuesta = self.manejador(accion, params)
            except Exception as error:  # nunca tirar abajo la app por un pedido remoto malformado
                respuesta = {"ok": False, "error": str(error)}
        try:
            socket.write((json.dumps(respuesta) + "\n").encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(2000)
        finally:
            socket.disconnectFromHost()
