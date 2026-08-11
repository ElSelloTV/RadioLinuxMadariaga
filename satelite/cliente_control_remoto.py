"""
satelite/cliente_control_remoto.py
--------------------------------------------------------
Cliente del protocolo de `core/servidor_control_remoto.py` (JSON
delimitado por salto de línea sobre TCP, un pedido = una respuesta =
una conexión). Sin Qt a propósito — es lógica de red pura, testeable
sin necesitar una QApplication ni un display.

Cada método bloquea hasta tener respuesta o timeout — la app satélite
lo llama siempre desde el hilo principal de la GUI, en acciones
puntuales (conectar, subir un archivo, apretar Play/Stop/Cut) o desde
un QTimer de polling corto (estado del transporte) — nunca hay una
operación tan larga como para justificar hilos aparte, mismo criterio
de "sin threading" que ya rige el resto de este proyecto.
--------------------------------------------------------
"""
import json
import socket

TIMEOUT_SEGUNDOS = 6.0


class ErrorControlRemoto(Exception):
    """Fallo de red/protocolo (no llegó a haber respuesta del
    servidor) — distinto de un `{"ok": False, "error": "..."}` bien
    formado, que es una respuesta válida rechazando el pedido."""


class ClienteControlRemoto:
    def __init__(self, host: str, puerto: int, token: str):
        self.host = host
        self.puerto = puerto
        self.token = token

    def _pedir(self, accion: str, params: dict = None) -> dict:
        pedido = {"token": self.token, "accion": accion, "params": params or {}}
        linea = (json.dumps(pedido) + "\n").encode("utf-8")
        try:
            with socket.create_connection((self.host, self.puerto), timeout=TIMEOUT_SEGUNDOS) as conexion:
                conexion.settimeout(TIMEOUT_SEGUNDOS)
                conexion.sendall(linea)
                conexion.shutdown(socket.SHUT_WR)
                trozos = []
                while True:
                    trozo = conexion.recv(65536)
                    if not trozo:
                        break
                    trozos.append(trozo)
        except (OSError, socket.timeout) as error:
            raise ErrorControlRemoto(f"No se pudo conectar a {self.host}:{self.puerto} — {error}") from error

        crudo = b"".join(trozos).strip()
        if not crudo:
            raise ErrorControlRemoto(
                "El servidor no respondió nada -- revisá que el token sea el correcto "
                "(un token equivocado hace que el servidor corte la conexión en silencio)."
            )
        try:
            return json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ErrorControlRemoto(f"Respuesta del servidor ilegible: {error}") from error

    # ------------------------------------------------------------------
    def ping(self) -> dict:
        return self._pedir("ping")

    def listar_categorias(self) -> list:
        respuesta = self._pedir("listar_categorias")
        if not respuesta.get("ok"):
            raise ErrorControlRemoto(respuesta.get("error", "listar_categorias falló"))
        return respuesta["datos"]["categorias"]

    def listar_generos(self) -> list:
        respuesta = self._pedir("listar_generos")
        if not respuesta.get("ok"):
            raise ErrorControlRemoto(respuesta.get("error", "listar_generos falló"))
        return respuesta["datos"]["generos"]

    def estado_transporte(self) -> dict:
        respuesta = self._pedir("estado_transporte")
        if not respuesta.get("ok"):
            raise ErrorControlRemoto(respuesta.get("error", "estado_transporte falló"))
        return respuesta["datos"]

    def accion_transporte(self, ventana: str, accion: str) -> dict:
        return self._pedir("accion_transporte", {"ventana": ventana, "accion": accion})

    def importar_archivo(self, nombre_archivo: str, contenido_base64: str, categoria_ruta: list,
                          titulo: str, artista: str, genero: str) -> dict:
        return self._pedir("importar_archivo", {
            "nombre_archivo": nombre_archivo,
            "contenido_base64": contenido_base64,
            "categoria_ruta": categoria_ruta,
            "titulo": titulo,
            "artista": artista,
            "genero": genero,
        })
