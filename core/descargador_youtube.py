"""
core/descargador_youtube.py
--------------------------------------------------------
Descarga audio de YouTube (un video suelto o una playlist completa)
y lo deja listo como MP3 en disco, ya analizado (recorte de
silencios + nivelado, mismo motor que el resto de la app) para que
Ventana 3 lo suba a la biblioteca. Pedido explícito de Santiago:
armarlo como "módulo" autocontenido -- este archivo no importa nada
de gui/, y gui/ventana_explorador.py es el ÚNICO lugar que lo usa, así
que si algo sale mal acá, no arrastra al resto del programa.

Usa la librería `yt-dlp` (pip, ver requirements.txt) -- no un binario
de sistema aparte. Siempre baja en MP3: el postprocesador
FFmpegExtractAudio de yt-dlp hace la conversión Y borra el archivo
intermedio (el que bajó en el formato original de YouTube) apenas
termina de convertir -- no hace falta ningún manejo manual de
limpieza de archivos, yt-dlp ya lo hace solo (pedido explícito, punto
8: "eliminar el otro archivo, dejando solo el mp3").

Requiere además el binario `ffmpeg` del sistema (dependencia YA
existente de esta app, ver core/analizador_audio.py) para la
conversión a MP3 -- si falta, yt-dlp tira un error claro que se
atrapa acá y se devuelve como mensaje, sin romper la app.

Degrada limpio si `yt-dlp` no está instalado (ImportError atrapada) --
mismo patrón que MotorAudio/analizador_audio ante dependencias
faltantes.
--------------------------------------------------------
"""

import os
import re

from core.analizador_audio import analizar_audio
from core.audio_engine import obtener_duracion_formateada

MENSAJE_YTDLP_NO_DISPONIBLE = (
    "La descarga de YouTube necesita el paquete 'yt-dlp' (dentro del "
    "entorno virtual: pip install -r requirements.txt) y el binario "
    "'ffmpeg' del sistema (sudo apt install ffmpeg) para convertir a MP3."
)

NOMBRE_CARPETA_DESCARGAS = "descargas YT"

# Video, playlist o shorts, con o sin subdominio (www./m./music.).
# Pedido explícito (punto 9): la barra solo acepta enlaces de YouTube.
_PATRON_URL_YOUTUBE = re.compile(
    r"^https?://(www\.|m\.|music\.)?(youtube\.com/(watch\?|playlist\?|shorts/)|youtu\.be/)",
    re.IGNORECASE,
)


def es_url_youtube(url: str) -> bool:
    """Valida que la URL sea de YouTube (video, playlist o shorts)."""
    return bool(_PATRON_URL_YOUTUBE.match((url or "").strip()))


def _sanitizar_nombre_carpeta(nombre: str) -> str:
    """Saca caracteres que rompen nombres de carpeta en Linux -- el
    resto (tildes, signos, espacios) se deja tal cual, el sistema de
    archivos los banca bien."""
    limpio = re.sub(r'[/\\:\*\?"<>\|]', "_", nombre or "").strip()
    return limpio or "Playlist sin título"


def _mp3_en_carpeta(carpeta: str) -> set:
    if not os.path.isdir(carpeta):
        return set()
    return {
        os.path.join(carpeta, nombre)
        for nombre in os.listdir(carpeta)
        if nombre.lower().endswith(".mp3")
    }


def descargar(
    url: str,
    carpeta_base: str,
    tolerancia_silencio_segundos: float = 2.0,
    umbral_silencio_dbfs: float = -40.0,
    callback_progreso=None,
) -> tuple:
    """Descarga `url` (video suelto o playlist) como MP3 dentro de
    `carpeta_base/descargas YT/` (video suelto) o
    `carpeta_base/descargas YT/<título de la playlist>/` (playlist).

    `callback_progreso`, si se pasa, se llama con un string de estado
    (ej. "Descargando: Tema (43%)") -- pensado para que el llamador
    (gui/ventana_explorador.py) actualice una etiqueta y llame a
    QApplication.processEvents(), sin que este módulo dependa de Qt.

    Devuelve (éxito: bool, mensaje: str, resultado: dict | None).
    `resultado`, si hubo éxito:
        {
            "es_playlist": bool,
            "titulo_playlist": str | None,
            "carpeta": str,        # carpeta final de los mp3
            "archivos": [
                {"ruta": str, "titulo": str, "duracion": str,
                 "punto_inicio_ms": int, "punto_fin_ms": int | None,
                 "ganancia_db": float, "analizado": bool},
                ...
            ],
        }
    Nunca lanza excepción -- cualquier fallo (red, video privado/
    borrado, yt-dlp faltante, ffmpeg faltante) vuelve como
    (False, mensaje, None).
    """
    try:
        import yt_dlp
    except ImportError:
        return False, MENSAJE_YTDLP_NO_DISPONIBLE, None

    if not es_url_youtube(url):
        return False, "La URL no parece ser de YouTube.", None

    carpeta_descargas = os.path.join(carpeta_base, NOMBRE_CARPETA_DESCARGAS)

    # Sondeo SIN descargar: hace falta saber si es un video suelto o
    # una playlist para resolver la subcarpeta destino ANTES de bajar
    # nada -- evita bajar todo a medias para recién ahí descubrir
    # dónde tendría que haber quedado.
    opciones_sondeo = {
        "quiet": True, "no_warnings": True,
        "extract_flat": "in_playlist", "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(opciones_sondeo) as ydl:
            info_previa = ydl.extract_info(url, download=False)
    except Exception as exc:
        return False, f"No se pudo leer la URL de YouTube: {exc}", None

    if info_previa is None:
        return False, "No se pudo leer la URL de YouTube.", None

    es_playlist = info_previa.get("_type") == "playlist"
    titulo_playlist = None
    if es_playlist:
        titulo_playlist = _sanitizar_nombre_carpeta(info_previa.get("title") or "Playlist sin título")
        carpeta_destino = os.path.join(carpeta_descargas, titulo_playlist)
    else:
        carpeta_destino = carpeta_descargas

    os.makedirs(carpeta_destino, exist_ok=True)
    mp3_antes = _mp3_en_carpeta(carpeta_destino)

    # Capa 1 de detección de archivos bajados: los hooks de yt-dlp
    # (más precisos, dan el título real de cada uno). Ver la capa 2
    # (diff de carpeta) más abajo -- nunca confiar en una sola forma
    # de detectar el resultado, mismo criterio que ya rige el resto
    # del proyecto ante libVLC/EasyEffects.
    rutas_por_hook = []

    def _hook_postproceso(estado):
        if estado.get("status") != "finished":
            return
        info = estado.get("info_dict") or {}
        ruta_final = info.get("filepath") or info.get("_filename")
        if ruta_final and ruta_final.lower().endswith(".mp3") and ruta_final not in rutas_por_hook:
            rutas_por_hook.append(ruta_final)

    def _hook_progreso(estado):
        if callback_progreso is None:
            return
        if estado.get("status") == "downloading":
            info = estado.get("info_dict") or {}
            titulo = info.get("title", "")
            porcentaje = (estado.get("_percent_str") or "").strip()
            callback_progreso(f"Descargando: {titulo} ({porcentaje})")
        elif estado.get("status") == "finished":
            callback_progreso("Convirtiendo a MP3...")

    opciones_descarga = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(carpeta_destino, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": not es_playlist,
        "ignoreerrors": True,   # un video roto de la playlist no frena a los demás
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_hook_progreso],
        "postprocessor_hooks": [_hook_postproceso],
    }

    try:
        with yt_dlp.YoutubeDL(opciones_descarga) as ydl:
            ydl.download([url])
    except Exception as exc:
        return False, f"Error al descargar: {exc}", None

    # Capa 2: además de lo que reportaron los hooks, se compara qué
    # archivos .mp3 nuevos aparecieron en la carpeta destino -- cubre
    # tanto el caso "los hooks no dieron nada" (cambio de formato
    # interno de yt-dlp entre versiones) como una playlist donde el
    # hook falló para ALGUNOS ítems pero no para otros.
    mp3_despues = _mp3_en_carpeta(carpeta_destino)
    extras_por_diff = sorted((mp3_despues - mp3_antes) - set(rutas_por_hook))
    rutas_finales = rutas_por_hook + extras_por_diff

    if not rutas_finales:
        return False, "No se pudo descargar ningún archivo de esa URL.", None

    if callback_progreso is not None:
        callback_progreso("Analizando silencios...")

    archivos = []
    for ruta in rutas_finales:
        if not os.path.isfile(ruta):
            continue
        analisis = analizar_audio(
            ruta,
            tolerancia_silencio_segundos=tolerancia_silencio_segundos,
            umbral_silencio_dbfs=umbral_silencio_dbfs,
        )
        archivos.append({
            "ruta": ruta,
            "titulo": os.path.splitext(os.path.basename(ruta))[0],
            "duracion": obtener_duracion_formateada(ruta),
            "punto_inicio_ms": analisis["punto_inicio_ms"],
            "punto_fin_ms": analisis["punto_fin_ms"] or None,
            "ganancia_db": analisis["ganancia_db"],
            "analizado": analisis["analizado"],
        })

    if not archivos:
        return False, "No se pudo descargar ningún archivo de esa URL.", None

    resultado = {
        "es_playlist": es_playlist,
        "titulo_playlist": titulo_playlist,
        "carpeta": carpeta_destino,
        "archivos": archivos,
    }
    return True, f"Se descargaron {len(archivos)} archivo(s).", resultado
