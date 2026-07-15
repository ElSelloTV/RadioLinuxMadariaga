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
se dispara el Comando HTH. Si la consulta falla y no hay caché
vigente, devuelve None — core/hth.py lo trata igual que un clip de voz
faltante: saltea el anuncio completo, sin sonar nada.

Usa urllib (librería estándar) en vez de sumar una dependencia nueva
(`requests`) solo para esto — es la primera y única llamada de red de
toda la app.
--------------------------------------------------------
"""

import json
import time
import urllib.error
import urllib.request

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
DURACION_CACHE_SEGUNDOS = 20 * 60
TIMEOUT_SEGUNDOS = 6

LATITUD_DEFECTO = -37.0167
LONGITUD_DEFECTO = -57.1167

_cache = {"datos": None, "momento": 0.0}


def _consultar_open_meteo(latitud: float, longitud: float) -> dict | None:
    url = (
        f"{URL_OPEN_METEO}?latitude={latitud}&longitude={longitud}"
        "&current=temperature_2m,relative_humidity_2m"
    )
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None
    actual = datos.get("current") or {}
    temperatura = actual.get("temperature_2m")
    humedad = actual.get("relative_humidity_2m")
    if temperatura is None or humedad is None:
        return None
    return {"temperatura": round(temperatura), "humedad": round(humedad)}


def obtener_clima(latitud: float = None, longitud: float = None, forzar: bool = False) -> dict | None:
    """{"temperatura": int en °C, "humedad": int en % 0-100}, ambos ya
    redondeados a entero, o None si no se pudo obtener (sin caché
    vigente y la consulta falló). Cachea por DURACION_CACHE_SEGUNDOS —
    no golpea la red en cada disparo del Comando HTH."""
    lat = latitud if latitud is not None else LATITUD_DEFECTO
    lon = longitud if longitud is not None else LONGITUD_DEFECTO

    ahora = time.monotonic()
    if not forzar and _cache["datos"] is not None and (ahora - _cache["momento"]) < DURACION_CACHE_SEGUNDOS:
        return _cache["datos"]

    datos = _consultar_open_meteo(lat, lon)
    if datos is not None:
        _cache["datos"] = datos
        _cache["momento"] = ahora
    return datos
