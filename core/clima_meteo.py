"""
core/clima_meteo.py
--------------------------------------------------------
Consulta de clima en vivo para el Comando HTH (TEMPERATURA/HUMEDAD) —
confirmado con Santiago (AskUserQuestion) que la fuente es Open-Meteo
(open-meteo.com): gratis, sin API key, esquema JSON estable. Se
descartó tiempoyradar.com.ar (sitio comercial renderizado con
JavaScript, sin API pública documentada).

Coordenadas por defecto: General Juan Madariaga, Buenos Aires,
Argentina — configurables en Configuración
(config_general.json -> clima.latitud/longitud) por si hace falta
apuntar a otra ciudad.

Caché de ~20 minutos (pedido explícito, "cachear ~15-30 minutos"): el
clima real no cambia tan rápido, y evita golpear la API cada vez que
se dispara el Comando HTH.

Refresco en SEGUNDO PLANO (pedido explícito, ronda posterior: "que lo
lea en off y lo tenga guardado de antemano... que no interrumpa la
emisión ni demore la carga, que trabaje de manera silenciosa"): la
consulta original usaba `urllib.request.urlopen` SINCRÓNICO — si el
Comando HTH se disparaba con la caché vencida (o todavía vacía, recién
abierta la app), esa consulta bloqueaba el hilo principal (y con él,
la radio entera) hasta 6 segundos — el "breve silencio" que reportó
Santiago. Ahora `RefrescadorClima` mantiene la caché TIBIA en segundo
plano con pedidos HTTP ASÍNCRONOS (`QNetworkAccessManager` — Qt-nativo,
sin subprocess ni QThread, mismo espíritu "sin threading" del resto de
la app), disparados solo cada `INTERVALO_REFRESCO_MINUTOS` (bien por
debajo de los 20 minutos de vigencia) — así en uso normal la caché
nunca llega a vencerse antes del próximo refresco. `obtener_clima()`,
el único punto que usa `core/hth.py` en el camino de reproducción, ya
NUNCA sale a la red: si no hay caché vigente, devuelve `None` de
inmediato — core/hth.py lo trata igual que un clip de voz faltante
(saltea el anuncio completo, nunca bloquea esperando).
--------------------------------------------------------
"""

import json
import time
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
DURACION_CACHE_SEGUNDOS = 20 * 60
TIMEOUT_SEGUNDOS = 6
# Bien por debajo de DURACION_CACHE_SEGUNDOS (20 min): en uso normal,
# el refresco de fondo renueva la caché mucho antes de que llegue a
# vencerse, así el Comando HTH siempre la encuentra tibia.
INTERVALO_REFRESCO_MINUTOS = 15

LATITUD_DEFECTO = -37.0167
LONGITUD_DEFECTO = -57.1167

_cache = {"datos": None, "momento": 0.0}


def _armar_url(latitud: float, longitud: float) -> str:
    return (
        f"{URL_OPEN_METEO}?latitude={latitud}&longitude={longitud}"
        "&current=temperature_2m,relative_humidity_2m"
    )


def _parsear_respuesta(bruto: bytes) -> dict | None:
    try:
        datos = json.loads(bruto.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    actual = datos.get("current") or {}
    temperatura = actual.get("temperature_2m")
    humedad = actual.get("relative_humidity_2m")
    if temperatura is None or humedad is None:
        return None
    return {"temperatura": round(temperatura), "humedad": round(humedad)}


def obtener_clima(latitud: float = None, longitud: float = None) -> dict | None:
    """{"temperatura": int en °C, "humedad": int en % 0-100}, o None si
    todavía no hay una lectura vigente en caché. Pedido explícito: esta
    función NUNCA sale a la red — es una simple lectura de memoria, así
    que llamarla desde el camino de reproducción (Comando HTH) es
    instantáneo, nunca bloquea la emisión. La caché la mantiene tibia
    RefrescadorClima en segundo plano; `latitud`/`longitud` quedan
    como parámetros por compatibilidad de interfaz con core/hth.py,
    pero no afectan esta lectura (las usa el refrescador para pedir
    los datos)."""
    if _cache["datos"] is None:
        return None
    if (time.monotonic() - _cache["momento"]) >= DURACION_CACHE_SEGUNDOS:
        return None
    return _cache["datos"]


def _consultar_open_meteo_sincronico(latitud: float, longitud: float) -> dict | None:
    """Consulta BLOQUEANTE de respaldo — a propósito NUNCA se llama
    desde el camino de reproducción (ver obtener_clima), solo queda
    disponible por si algún día hace falta un botón "probar ahora" en
    Configuración, donde una espera breve sí es aceptable (acción
    manual explícita del operador, no algo en segundo plano)."""
    try:
        with urllib.request.urlopen(_armar_url(latitud, longitud), timeout=TIMEOUT_SEGUNDOS) as respuesta:
            return _parsear_respuesta(respuesta.read())
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


class RefrescadorClima(QObject):
    """Mantiene la caché de clima TIBIA en segundo plano, con pedidos
    HTTP ASÍNCRONOS (QNetworkAccessManager) — nunca bloquea el hilo
    principal, a diferencia de un urllib.request.urlopen sincrónico.
    `obtener_coordenadas` es un callable sin argumentos que devuelve
    (latitud, longitud) actuales — se vuelve a llamar en cada refresco,
    así un cambio de coordenadas en Configuración se aplica solo, sin
    tener que reiniciar la app."""

    def __init__(self, obtener_coordenadas, parent=None):
        super().__init__(parent)
        self._obtener_coordenadas = obtener_coordenadas
        self._gestor_red = QNetworkAccessManager(self)
        self._respuesta_en_curso = None
        self._timer = QTimer(self)
        self._timer.setInterval(INTERVALO_REFRESCO_MINUTOS * 60 * 1000)
        self._timer.timeout.connect(self.refrescar_ahora)

    def iniciar(self, demora_inicial_ms: int = 3000):
        """`demora_inicial_ms` (pedido explícito, "que no... demore la
        carga"): el primer refresco se dispara diferido, para no
        competir con el arranque de la radio — mismo criterio ya usado
        para EasyEffects y la búsqueda de actualización."""
        self._timer.start()
        QTimer.singleShot(demora_inicial_ms, self.refrescar_ahora)

    def refrescar_ahora(self):
        if self._respuesta_en_curso is not None:
            return  # ya hay un pedido en vuelo, no superponer otro
        try:
            latitud, longitud = self._obtener_coordenadas()
        except Exception:
            return
        pedido = QNetworkRequest(QUrl(_armar_url(latitud, longitud)))
        self._respuesta_en_curso = self._gestor_red.get(pedido)
        self._respuesta_en_curso.finished.connect(self._on_respuesta)

    def _on_respuesta(self):
        from config.settings import registrar_evento

        respuesta = self._respuesta_en_curso
        self._respuesta_en_curso = None
        if respuesta is None:
            return
        try:
            if respuesta.error() != QNetworkReply.NetworkError.NoError:
                registrar_evento(f"Clima: error consultando Open-Meteo en segundo plano: {respuesta.errorString()}")
                return
            datos = _parsear_respuesta(bytes(respuesta.readAll()))
            if datos is None:
                registrar_evento("Clima: respuesta de Open-Meteo sin datos utilizables")
                return
            _cache["datos"] = datos
            _cache["momento"] = time.monotonic()
            registrar_evento(f"Clima: caché actualizada en segundo plano ({datos})")
        finally:
            respuesta.deleteLater()
