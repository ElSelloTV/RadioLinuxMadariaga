"""
core/descargador_youtube_doc.py
--------------------------------------------------------
Importador automático de música desde YouTube, a partir de un
documento de Google Docs con una lista de enlaces — pedido explícito:
"Me gustaría cargar un txt con enlaces de youtube... el archivo en
realidad es un documento de Drive... nunca voy a borrarlo y si lo hago
el programa solo registrará en el LOG que no encontró el archivo."

Formato de CADA línea del documento (campos separados por coma, los
últimos dos opcionales):
    <url de YouTube>, <Categoria>Subcategoria>..., <mm:ss>-<mm:ss>

Ejemplo real (del documento de Santiago):
    https://www.youtube.com/watch?v=Z-cHpUTlTJo&list=RD...&start_radio=1, Musica>Latinos, 00:06-04:38

- La categoría admite cualquier cantidad de niveles con ">" (sin
  límite, igual que el Explorador) — si no existe todavía, se CREA
  sola (confirmado con Santiago, "crearla sola automáticamente").
- Sin el campo de tiempos (o mal formado), se descarga el video
  COMPLETO.
- Con tiempos, el archivo que queda en la biblioteca es ESE TRAMO
  recortado de verdad (confirmado: "recortar físicamente", no solo
  puntos de reproducción) — más liviano, pero no se puede "extender"
  después sin volver a descargar.
- Líneas vacías o que empiezan con "#" se ignoran (comentarios).
- Un link que no sea de YouTube, o una línea sin categoría, se
  saltea sin romper el resto del documento.
- SIEMPRE se baja el video PUNTUAL indicado (`noplaylist`), nunca una
  lista/mezcla asociada (confirmado: los enlaces reales de Santiago
  son del tipo "mezcla radio" de YouTube, `&list=RD...&start_radio=1`
  — esa lista NUNCA debe bajarse entera).

Deduplicación (confirmado con Santiago, "URL + rango de tiempo"): la
MISMA URL se puede pedir dos veces con TRAMOS distintos sin que se
bloqueen entre sí — lo que nunca se vuelve a descargar es la
combinación EXACTA (video + ese mismo tramo, o "completo" si no había
tiempos). Se guarda en `config/data/youtube_doc_descargados.json` (ver
config/settings.py:cargar_descargas_youtube_doc/guardar_...), una base
"ultra liviana" tal cual pidió Santiago.

Descargas SIEMPRE una por una, nunca en paralelo (pedido explícito:
"no todos los enlaces seguidos para no atorar la computadora y la
descarga sea más rápida") — cada línea (red + ffmpeg + análisis de
silencio/nivelado + copia a la biblioteca) termina del todo antes de
arrancar la siguiente. Mismo criterio de "nunca threading" de siempre
en este proyecto.

Corre como PROCESO APARTE vía cron (ver
core/actualizador.py:asegurar_tarea_cron_importar_youtube_doc, a las
3:00am — después de los Enlatados tipo Drive a las 00:30 y antes del
mantenimiento de las 2am... en realidad DESPUÉS de las 2am a
propósito, para no competir con esa tarea por red/CPU al mismo
tiempo) y también a mano, desde Configuración → Importador YouTube →
"Sincronizar ahora" (mismo patrón de QProcess + barra de progreso
gráfica ya usado para Enlatados tipo Drive — nunca bloquea la GUI).

Se puede correr suelto para probar:
    venv/bin/python3 -m core.descargador_youtube_doc

**Límite real, honesto**: este entorno de desarrollo no tiene salida
de red hacia docs.google.com NI youtube.com — el fetch del documento
se probó con datos reales (vía un conector de Drive disponible en la
sesión de diseño, no la ruta real de producción) y la integración con
yt-dlp se probó contra un archivo LOCAL (confirmando la API real:
`info["requested_downloads"][0]["filepath"]` es la ruta final tras la
conversión a mp3, NUNCA `info["filepath"]`, que queda vacío) — pero
nunca se pudo probar de punta a punta contra YouTube real. El recorte
nativo de yt-dlp (`download_ranges`) tiene un fallback real: si falla
por cualquier motivo (confirmado que pasa con formatos/streams que no
soportan descarga parcial), se baja el video COMPLETO y se recorta
después con pydub (la misma librería que ya usa
core/analizador_audio.py en el resto de la app) — nunca se pierde una
línea solo porque el camino más liviano no estuvo disponible para ese
video puntual.
--------------------------------------------------------
"""

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

_CARACTERES_INVALIDOS = '/\\:*?"<>|'
_REGEX_TIEMPO = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")
_REGEX_ID_VIDEO = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{6,})")
_REGEX_ID_DOCUMENTO = re.compile(r"/document/d/([A-Za-z0-9_-]+)")


def _sanitizar_nombre_archivo(nombre: str) -> str:
    """Mismo criterio que gui/dialogo_vincular_archivo.py -- duplicado
    acá a propósito (no importado) para que este script headless
    nunca necesite tocar ningún módulo de gui/."""
    limpio = "".join("_" if c in _CARACTERES_INVALIDOS else c for c in nombre).strip()
    return limpio or "archivo"


def _tamano_bytes(ruta: str):
    try:
        return os.path.getsize(ruta)
    except OSError:
        return None


# ------------------------------------------------------------------
# Lectura del documento de Google Docs
# ------------------------------------------------------------------
def _extraer_id_documento(url_o_id: str) -> str | None:
    """Acepta la URL completa de compartir
    ("https://docs.google.com/document/d/<ID>/edit?usp=sharing") o el
    ID solo, tipeado a mano en Configuración."""
    if not url_o_id:
        return None
    coincidencia = _REGEX_ID_DOCUMENTO.search(url_o_id)
    if coincidencia:
        return coincidencia.group(1)
    if "/" not in url_o_id and " " not in url_o_id:
        return url_o_id.strip()
    return None


def descargar_texto_documento(url_o_id: str, timeout_segundos: int = 30) -> str | None:
    """`None` si el documento no se pudo leer por CUALQUIER motivo
    (borrado, sin conexión, link mal pegado) -- nunca lanza excepción.
    El llamador registra el "no se encontró el archivo" en el log,
    tal cual pidió Santiago."""
    id_doc = _extraer_id_documento(url_o_id)
    if not id_doc:
        return None
    url_export = f"https://docs.google.com/document/d/{id_doc}/export?format=txt"
    import urllib.error
    import urllib.request
    try:
        peticion = urllib.request.Request(url_export, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(peticion, timeout=timeout_segundos) as respuesta:
            return respuesta.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return None


# ------------------------------------------------------------------
# Parseo de líneas
# ------------------------------------------------------------------
def _parsear_segundos(texto: str) -> int | None:
    coincidencia = _REGEX_TIEMPO.match(texto.strip())
    if not coincidencia:
        return None
    horas = int(coincidencia.group(1)) if coincidencia.group(1) else 0
    minutos = int(coincidencia.group(2))
    segundos = int(coincidencia.group(3))
    return horas * 3600 + minutos * 60 + segundos


def parsear_linea(linea: str) -> dict | None:
    """Devuelve {"url", "categoria": [...], "inicio_seg": int|None,
    "fin_seg": int|None}, o None si la línea está vacía, es un
    comentario ("#..."), no es un link de YouTube, o no trae
    categoría -- en cualquiera de esos casos se saltea en silencio,
    sin romper el resto del documento."""
    cruda = linea.strip()
    if not cruda or cruda.startswith("#"):
        return None

    partes = [p.strip() for p in cruda.split(",")]
    if len(partes) < 2:
        return None

    url = partes[0].strip().lstrip("<").rstrip(">")
    if "youtube.com" not in url and "youtu.be" not in url:
        return None

    # "\\>" es un artefacto real visto al leer el documento a través
    # de un renderizador que escapa ">" para markdown -- defensivo,
    # nunca debería hacer falta contra el export de texto plano real,
    # pero no cuesta nada tolerarlo.
    texto_categoria = partes[1].replace("\\>", ">")
    categoria = [n.strip() for n in texto_categoria.split(">") if n.strip()]
    if not categoria:
        return None

    inicio_seg = fin_seg = None
    if len(partes) >= 3 and partes[2].strip() and "-" in partes[2]:
        izquierda, _, derecha = partes[2].strip().partition("-")
        inicio_seg = _parsear_segundos(izquierda)
        fin_seg = _parsear_segundos(derecha)
        if inicio_seg is None or fin_seg is None or fin_seg <= inicio_seg:
            # tiempo mal formado -- se ignora, se baja completo en vez
            # de arriesgar un recorte sin sentido.
            inicio_seg = fin_seg = None

    return {"url": url, "categoria": categoria, "inicio_seg": inicio_seg, "fin_seg": fin_seg}


def _id_video(url: str) -> str | None:
    coincidencia = _REGEX_ID_VIDEO.search(url)
    return coincidencia.group(1) if coincidencia else None


def _clave_dedup(url: str, inicio_seg, fin_seg) -> str:
    identificador = _id_video(url) or url
    if inicio_seg is None or fin_seg is None:
        return f"{identificador}::completo"
    return f"{identificador}::{inicio_seg}-{fin_seg}"


# ------------------------------------------------------------------
# Descarga con yt-dlp (+ recorte, con fallback real)
# ------------------------------------------------------------------
def _opciones_yt_dlp(carpeta_destino: str, inicio_seg=None, fin_seg=None) -> dict:
    import yt_dlp

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(carpeta_destino, "%(title)s.%(ext)s"),
        # SIEMPRE solo el video puntual -- confirmado con Santiago,
        # nunca la lista/mezcla asociada (&list=RD...&start_radio=1).
        "noplaylist": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True, "no_warnings": True, "noprogress": True,
    }
    if inicio_seg is not None and fin_seg is not None:
        opciones["download_ranges"] = yt_dlp.utils.download_range_func(None, [(inicio_seg, fin_seg)])
        opciones["force_keyframes_at_cuts"] = True
    return opciones


def _extraer_resultado_descarga(info: dict) -> tuple:
    """(ruta_final, titulo) -- confirmado contra la API real de
    yt-dlp (con un archivo local de prueba): el filepath final
    DESPUÉS de la conversión a mp3 vive en
    info["requested_downloads"][0]["filepath"], NUNCA en
    info["filepath"] (ese queda vacío/sin tocar para una descarga de
    audio con postprocesador)."""
    titulo = info.get("title") or "Sin título"
    descargas = info.get("requested_downloads") or []
    ruta = descargas[0].get("filepath") if descargas else None
    return ruta, titulo


def _cortar_con_pydub(ruta_entrada: str, inicio_seg: int, fin_seg: int) -> dict:
    """Recorte de RESPALDO (ver docstring del módulo) -- se usa SOLO
    si el recorte nativo de yt-dlp (download_ranges) falló para ese
    video puntual. Sobrescribe `ruta_entrada` en el lugar -- siempre
    un archivo temporal propio de esta descarga, nunca algo del
    operador."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(ruta_entrada)
        recorte = audio[inicio_seg * 1000: fin_seg * 1000]
        recorte.export(ruta_entrada, format="mp3")
        return {"ok": True}
    except Exception as error:
        return {"ok": False, "mensaje": f"No se pudo recortar el video completo con pydub: {error}"}


def descargar_audio(url: str, carpeta_destino: str, inicio_seg=None, fin_seg=None) -> dict:
    """Descarga el audio de `url` a `carpeta_destino`. Si se dan
    inicio_seg/fin_seg, el resultado queda recortado a ESE tramo --
    primero intenta el camino liviano (yt-dlp baja/corta solo esa
    sección), y si eso falla (confirmado que puede pasar según el
    formato/stream del video), cae al respaldo: bajar completo y
    recortar con pydub. Nunca lanza excepción -- degrada a
    {"ok": False, "mensaje": ...}."""
    try:
        import yt_dlp
    except ImportError:
        return {"ok": False, "mensaje": "Falta instalar yt-dlp (con el venv activado: pip install yt-dlp)."}

    if inicio_seg is not None and fin_seg is not None:
        try:
            with yt_dlp.YoutubeDL(_opciones_yt_dlp(carpeta_destino, inicio_seg, fin_seg)) as ydl:
                info = ydl.extract_info(url, download=True)
            ruta, titulo = _extraer_resultado_descarga(info)
            if ruta and os.path.isfile(ruta):
                return {"ok": True, "ruta": ruta, "titulo": titulo}
        except Exception as error:
            from config.settings import registrar_evento
            registrar_evento(
                f"Importador YouTube: el recorte nativo de yt-dlp falló para '{url}' "
                f"({error}) -- bajando completo y recortando con pydub aparte"
            )

    try:
        with yt_dlp.YoutubeDL(_opciones_yt_dlp(carpeta_destino)) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as error:
        return {"ok": False, "mensaje": f"No se pudo descargar '{url}': {error}"}

    ruta, titulo = _extraer_resultado_descarga(info)
    if not ruta or not os.path.isfile(ruta):
        return {"ok": False, "mensaje": "yt-dlp no generó ningún archivo de audio reconocible."}

    if inicio_seg is not None and fin_seg is not None:
        resultado_corte = _cortar_con_pydub(ruta, inicio_seg, fin_seg)
        if not resultado_corte["ok"]:
            return resultado_corte

    return {"ok": True, "ruta": ruta, "titulo": titulo}


# ------------------------------------------------------------------
# Alta en la biblioteca (headless -- sin QApplication, mismo criterio
# que core/reanalizador_batch.py: opera directo sobre la lista de
# dicts de cargar_biblioteca(), nunca importa nada de gui/).
# ------------------------------------------------------------------
def _importar_a_biblioteca(ruta_descargada: str, titulo: str, categoria_nombres: list, config: dict) -> dict:
    from config.settings import (
        buscar_o_crear_categoria_por_ruta, cargar_biblioteca, guardar_biblioteca,
        parametros_nivelado, tolerancia_silencio_para_genero,
    )
    from core.analizador_audio import analizar_audio
    from core.audio_engine import obtener_duracion_formateada

    categorias = cargar_biblioteca()
    categoria = buscar_o_crear_categoria_por_ruta(categorias, categoria_nombres)
    registros = categoria.setdefault("archivos", [])
    # Mismo prefijo que GENERO_PREFIJOS_CODIGO["Musica"] en
    # gui/styles.py -- duplicado como literal a propósito (nunca "MUS"
    # va a cambiar) para que este script no importe nada de gui/.
    codigo = f"MUS{len(registros) + 1:05d}"

    raiz = config["rutas"]["biblioteca_musical"]
    carpeta_destino = raiz
    for nombre in categoria_nombres:
        carpeta_destino = os.path.join(carpeta_destino, _sanitizar_nombre_archivo(nombre))
    os.makedirs(carpeta_destino, exist_ok=True)

    nombre_archivo = _sanitizar_nombre_archivo(os.path.basename(ruta_descargada))
    base, extension = os.path.splitext(nombre_archivo)
    destino = os.path.join(carpeta_destino, nombre_archivo)
    contador = 2
    while os.path.exists(destino):
        destino = os.path.join(carpeta_destino, f"{base} ({contador}){extension}")
        contador += 1
    shutil.move(ruta_descargada, destino)

    tolerancia = tolerancia_silencio_para_genero(config, "Musica")
    umbral = config.get("reproduccion", {}).get("umbral_silencio_dbfs", -50.0)
    nivelado_activado, objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)
    analisis = analizar_audio(
        destino, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral,
        objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs, nivelado_activado=nivelado_activado,
    )

    registro = {
        "titulo": titulo, "artista": "", "genero": "Musica", "codigo": codigo, "ruta": destino,
        "duracion": obtener_duracion_formateada(destino),
        "tamaño_bytes": _tamano_bytes(destino),
        "punto_inicio_ms": analisis["punto_inicio_ms"],
        "punto_fin_ms": analisis["punto_fin_ms"] or None,
        "ganancia_db": analisis["ganancia_db"],
        "analizado": analisis["analizado"],
        "fecha_inicio": None, "fecha_fin": None,
    }
    registros.append(registro)
    guardar_biblioteca(categorias)
    return registro


def _procesar_una_entrada(entrada: dict, config: dict) -> dict:
    carpeta_temporal = tempfile.mkdtemp(prefix="youtube_doc_")
    try:
        resultado_descarga = descargar_audio(
            entrada["url"], carpeta_temporal, entrada["inicio_seg"], entrada["fin_seg"],
        )
        if not resultado_descarga["ok"]:
            return resultado_descarga
        registro = _importar_a_biblioteca(
            resultado_descarga["ruta"], resultado_descarga["titulo"], entrada["categoria"], config,
        )
        return {"ok": True, "titulo": registro["titulo"]}
    finally:
        shutil.rmtree(carpeta_temporal, ignore_errors=True)


# ------------------------------------------------------------------
# Orquestación
# ------------------------------------------------------------------
def ejecutar_importacion(config: dict = None, callback_progreso=None, url_doc_override: str = None) -> dict:
    """`callback_progreso(hechos, total)`, opcional, se llama después
    de procesar CADA línea pendiente -- mismo contrato que
    core.reanalizador_batch/core.sincronizador_drive.

    `url_doc_override` (mismo criterio que `--url` en
    core/sincronizador_drive.py): usa ESE link en vez de leerlo de
    `config` -- lo que usa el botón manual "Sincronizar ahora" para
    tomar el link recién tipeado en pantalla, incluso antes de
    apretar "Guardar"."""
    from config.settings import (
        cargar_configuracion, cargar_descargas_youtube_doc, guardar_descargas_youtube_doc,
        registrar_error, registrar_evento,
    )

    if config is None:
        config = cargar_configuracion()

    url_doc = (url_doc_override or "").strip() or \
        (config.get("importador_youtube_doc", {}) or {}).get("url_documento", "").strip()
    if not url_doc:
        return {"ok": False, "mensaje": "No hay ningún documento de YouTube configurado todavía."}

    texto = descargar_texto_documento(url_doc)
    if texto is None:
        return {
            "ok": False,
            "mensaje": "No se encontró el documento de YouTube (¿se borró, se dejó de compartir, "
                       "o cambió el link en Configuración?).",
        }

    lineas_parseadas = [p for p in (parsear_linea(l) for l in texto.splitlines()) if p is not None]

    descargados = cargar_descargas_youtube_doc()
    claves_vistas_en_este_doc = set()
    pendientes = []
    for entrada in lineas_parseadas:
        clave = _clave_dedup(entrada["url"], entrada["inicio_seg"], entrada["fin_seg"])
        if clave in claves_vistas_en_este_doc or clave in descargados:
            continue
        claves_vistas_en_este_doc.add(clave)
        pendientes.append((clave, entrada))

    total = len(pendientes)
    if callback_progreso is not None:
        callback_progreso(0, total)

    nuevos = fallidos = 0
    for indice, (clave, entrada) in enumerate(pendientes):
        # Uno a la vez, SIEMPRE -- pedido explícito de Santiago ("no
        # todos los enlaces seguidos para no atorar la computadora").
        try:
            resultado_item = _procesar_una_entrada(entrada, config)
        except Exception as error:
            resultado_item = {"ok": False, "mensaje": f"Excepción inesperada: {error}"}

        if resultado_item["ok"]:
            descargados[clave] = {
                "titulo": resultado_item.get("titulo"),
                "categoria": entrada["categoria"],
                "fecha": datetime.now().strftime("%Y-%m-%d"),
            }
            # Guardado INCREMENTAL, no al final -- mismo criterio que
            # reanalizador_batch: si se interrumpe a mitad de camino,
            # lo ya descargado nunca se re-descarga de nuevo mañana.
            guardar_descargas_youtube_doc(descargados)
            nuevos += 1
            registrar_evento(
                f"Importador YouTube: descargado '{resultado_item.get('titulo')}' -> "
                f"{' > '.join(entrada['categoria'])}"
            )
        else:
            fallidos += 1
            registrar_error(f"Importador YouTube: falló '{entrada['url']}' -- {resultado_item.get('mensaje')}")

        if callback_progreso is not None:
            callback_progreso(indice + 1, total)

    mensaje = f"{nuevos} nuevo(s) descargado(s), {fallidos} fallido(s) (de {total} pendiente(s) en el documento)."
    return {"ok": True, "mensaje": mensaje, "nuevos": nuevos, "fallidos": fallidos, "total_pendientes": total}


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Importa música desde el documento de YouTube como proceso aparte.",
    )
    parser.add_argument(
        "--url", default=None,
        help="Link del documento de Google Docs a usar -- se usa EXPLÍCITO, nunca releído "
             "de disco, para que \"Sincronizar ahora\" tome el link recién tipeado en "
             "Configuración aunque todavía no se haya apretado Guardar. Si se omite, se "
             "sincroniza con el link ya guardado en Configuración -- uso normal de la "
             "tarea nocturna de las 3am.",
    )
    args = parser.parse_args()

    from config.settings import cargar_configuracion, registrar_error, registrar_evento

    def _progreso(hechos, total):
        # Línea parseable por la GUI (QProcess.readyReadStandardOutput)
        # -- también legible corriendo esto suelto en una terminal.
        print(f"PROGRESO {hechos} {total}", flush=True)

    config = cargar_configuracion()
    etiqueta = "manual" if args.url else "3am"
    registrar_evento(f"Importador YouTube ({etiqueta}): iniciado")
    resultado = ejecutar_importacion(config, callback_progreso=_progreso, url_doc_override=args.url)
    print(f"RESULTADO {json.dumps(resultado)}", flush=True)
    if resultado["ok"]:
        registrar_evento(f"Importador YouTube ({etiqueta}): {resultado['mensaje']}")
    else:
        registrar_error(f"Importador YouTube ({etiqueta}) falló: {resultado['mensaje']}")


if __name__ == "__main__":
    main()
