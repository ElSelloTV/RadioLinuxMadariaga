"""
core/analizador_audio.py
--------------------------------------------------------
Motor de agregado de tema musical:
1) Detecta silencio de ENTRADA y de SALIDA (nunca en el medio del
   tema) con una tolerancia configurable (2 segundos por defecto)
   y calcula los puntos de recorte.
2) Reutiliza esos mismos puntos como referencia de "golpe musical"
   para el fade in / fade out (el instante donde arranca y termina
   el contenido audible real).
3) Calcula cuánta ganancia (dB) hay que sumar o restar para que el
   tema quede nivelado a un volumen de referencia común.

IMPORTANTE — enfoque NO DESTRUCTIVO: en vez de recodificar el
archivo original, esto sólo calcula "marcas" (milisegundos de
inicio/fin y una ganancia en dB) que se guardan como metadata del
registro en la biblioteca. El archivo fuente nunca se toca. El
motor de reproducción (MotorAudio) es quien, al reproducir ese
ítem, arranca desde punto_inicio_ms, corta en punto_fin_ms y
aplica la ganancia calculada. Esto es más simple, más rápido, y
evita duplicar archivos de audio en disco.

Por qué esto NUNCA corta un silencio que esté en el MEDIO del
tema (pedido explícito, "cuidado con no cortar un tema musical por
tener un silencio en el medio de la canción"): se usa
`pydub.silence.detect_leading_silence`, que escanea desde un extremo
hacia adentro y se DETIENE apenas encuentra la primera muestra que ya
no es silencio — nunca sigue escaneando más allá de ese punto. Para
el silencio de SALIDA se aplica el mismo escaneo pero sobre el audio
invertido (`audio.reverse()`), así "desde el final hacia adentro" es,
en los hechos, "desde el principio del audio invertido hacia
adentro" — la misma garantía. Una pausa breve a mitad de un tema
jamás se toca, porque el escaneo ya se frenó mucho antes de llegar
ahí (en el primer sonido real después del silencio inicial). Por las
dudas, además, `LIMITE_RECORTE_SILENCIO_SEGUNDOS` pone un techo duro:
aunque se detecte un silencio larguísimo pegado a un extremo (ej. un
intro ambient muy largo que coincide con el umbral), nunca se recorta
más que ese límite de cada lado — para no comerse contenido real por
error de calibración del umbral.

Requiere `pydub` + el binario `ffmpeg` del sistema para decodificar
y analizar samples reales. Si no están disponibles, se degrada de
forma controlada (igual que MotorAudio con libvlc): devuelve
valores neutros y avisa por consola, sin romper el flujo de alta
de un archivo a la biblioteca.
--------------------------------------------------------
"""

MENSAJE_PYDUB_NO_DISPONIBLE = (
    "El análisis de audio (recorte de silencios / nivelado) necesita "
    "pydub + ffmpeg. Instalá con: pip install pydub && sudo apt install ffmpeg"
)

DBFS_OBJETIVO = -16.0                        # nivel de referencia al que se nivela todo
UMBRAL_SILENCIO_DBFS_DEFECTO = -50.0         # por debajo de esto se considera "silencio" (configurable)
LIMITE_RECORTE_SILENCIO_SEGUNDOS = 20.0      # techo duro: nunca recorta más que esto de cada lado

# Tope del margen de seguridad que se deja SIN recortar en la SALIDA
# (bug real corregido, pedido explícito: "finalizó y dejó mucho
# silencio al final. No debería suceder eso"). Antes, el margen de
# salida usaba el mismo `tolerancia_silencio_segundos` que el de
# ENTRADA (2s por defecto) -- para un tema con 3-4s de silencio real
# pegado al final (frecuente en masters/exports con padding), eso
# dejaba hasta 2 segundos de aire casi muerto sonando antes del corte
# real, y de paso retrasaba el disparo del crossfade (que se calcula
# sobre ese mismo punto_fin_ms ya "inflado"). El margen de ENTRADA se
# deja intacto (un pre-roll de 2s antes de que arranque el contenido
# no genera el mismo problema) -- el de SALIDA ahora nunca supera este
# tope, sin importar qué tan grande sea `tolerancia_silencio_segundos`
# configurado (`min(tolerancia_ms, MARGEN_MAXIMO_SALIDA_MS)`): alcanza
# para no cortar en seco una nota/reverberación recién decayendo, sin
# arrastrar segundos de aire muerto. Los géneros de corte estricto
# (Publicidad/Separador/HTH) usan su propia tolerancia chica
# (tolerancia_silencio_v1_segundos, 150ms por defecto desde el fix del
# umbral) -- con un valor tan bajo, este tope casi no entra en juego
# para ellos, importa de verdad solo para Música.
#
# Subido de 300 a 400ms (bug real corregido, pedido explícito: "hay
# canciones que las finaliza antes") -- junto con el fix del umbral
# por defecto (-40 -> -50dBFS, más permisivo), da un colchón extra
# para no cortar la cola de un fundido/decay musical que siga siendo
# audible un poco más allá de donde el detector marca "silencio".
MARGEN_MAXIMO_SALIDA_MS = 400


def _cargar_audio(ruta: str):
    """`AudioSegment.from_file(ruta)` con un fallback real para WAV
    comprimidos en IMA-ADPCM (bug real encontrado con el log de
    Santiago -- 61 archivos de su biblioteca, todos ADPCM, fallaban
    SIEMPRE con "Decoding failed. ffmpeg returned error code: 8" /
    "Unknown encoder 'pcm_s4le'").

    Causa de fondo (confirmada leyendo el propio `pydub/audio_segment.py`
    instalado, no adivinada): al convertir un archivo, pydub le pide a
    `ffprobe` el `bits_per_sample` del stream de audio y arma el
    encoder de SALIDA como `"pcm_s%dle" % bits_per_sample` -- para
    IMA-ADPCM, ffprobe reporta 4 bits/muestra (el tamaño de la unidad
    COMPRIMIDA, no el ancho real del PCM decodificado), así que pydub
    termina pidiéndole a ffmpeg el encoder `pcm_s4le`, que no existe
    (ffmpeg no tiene PCM de 4 bits) -- la conversión revienta siempre,
    para cualquier archivo con este códec, sin importar el contenido.

    El fallback: si la carga directa falla, se decodifica el archivo a
    PCM de 16 bits con ffmpeg DIRECTO (subprocess propio, sin pasar
    por el auto-detect roto de pydub) a un WAV temporal, y recién ahí
    se lo entrega a pydub -- el archivo original nunca se toca (mismo
    enfoque no destructivo de siempre). Si ffmpeg no está en el PATH,
    o la conversión manual también falla, se relanza el error
    ORIGINAL (nunca uno nuevo, más confuso, del segundo intento)."""
    from pydub import AudioSegment
    try:
        return AudioSegment.from_file(ruta)
    except Exception as error_original:
        import os
        import shutil
        import subprocess
        import tempfile

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise error_original

        descriptor, ruta_temp = tempfile.mkstemp(suffix=".wav")
        os.close(descriptor)
        try:
            resultado = subprocess.run(
                [ffmpeg, "-y", "-i", ruta, "-acodec", "pcm_s16le", "-f", "wav", ruta_temp],
                capture_output=True, timeout=120,
            )
            if resultado.returncode != 0 or not os.path.exists(ruta_temp) or os.path.getsize(ruta_temp) == 0:
                raise error_original
            return AudioSegment.from_file(ruta_temp)
        except Exception:
            raise error_original
        finally:
            try:
                os.unlink(ruta_temp)
            except OSError:
                pass


def analizar_audio(
    ruta: str,
    tolerancia_silencio_segundos: float = 2.0,
    umbral_silencio_dbfs: float = UMBRAL_SILENCIO_DBFS_DEFECTO,
) -> dict:
    """Analiza `ruta` y devuelve:
        {
            "punto_inicio_ms": int,   # arranca después de cortar silencio de entrada
            "punto_fin_ms": int,      # corta antes del silencio de salida
            "punto_golpe_in_ms": int, # referencia de fade in (= punto_inicio_ms)
            "punto_golpe_out_ms": int,# referencia de fade out (= punto_fin_ms)
            "ganancia_db": float,     # ajuste para nivelar el volumen
            "duracion_total_ms": int,
            "analizado": bool,        # False si no se pudo analizar (fallback neutro)
        }
    Nunca lanza excepción: si el análisis falla, devuelve valores
    neutros (sin recorte, sin ganancia) para que el archivo se pueda
    agregar igual a la biblioteca.

    `umbral_silencio_dbfs` (configurable desde Configuración →
    Reproducción y Automatización): más cerca de 0 = más estricto
    (considera silencio a cosas más audibles, corta más); más
    negativo = más permisivo (solo corta silencio casi total). Ver
    nota al inicio del archivo sobre por qué esto es seguro incluso
    con un umbral agresivo — solo mira los extremos, nunca el medio.
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_leading_silence

        audio = _cargar_audio(ruta)
        duracion_total_ms = len(audio)
        tolerancia_ms = int(tolerancia_silencio_segundos * 1000)
        limite_ms = int(LIMITE_RECORTE_SILENCIO_SEGUNDOS * 1000)

        # Silencio de entrada: escanea desde el principio hacia
        # adentro y se detiene en la primera muestra no silenciosa —
        # jamás llega a mirar el medio del tema.
        silencio_inicio_ms = detect_leading_silence(audio, silence_threshold=umbral_silencio_dbfs)
        silencio_inicio_ms = min(silencio_inicio_ms, limite_ms)
        silencio_inicio_ms = max(0, silencio_inicio_ms - tolerancia_ms)  # deja un margen (tolerancia)

        # Silencio de salida: mismo escaneo "desde afuera hacia
        # adentro", pero sobre el audio invertido — misma garantía.
        # El margen que se deja SIN recortar acá está topeado por
        # MARGEN_MAXIMO_SALIDA_MS (ver nota arriba) — nunca el
        # tolerancia_ms completo, para no dejar segundos de aire
        # muerto sonando antes del corte real.
        silencio_fin_ms = detect_leading_silence(audio.reverse(), silence_threshold=umbral_silencio_dbfs)
        silencio_fin_ms = min(silencio_fin_ms, limite_ms)
        margen_salida_ms = min(tolerancia_ms, MARGEN_MAXIMO_SALIDA_MS)
        silencio_fin_ms = max(0, silencio_fin_ms - margen_salida_ms)

        punto_inicio_ms = min(silencio_inicio_ms, max(0, duracion_total_ms - 1))
        punto_fin_ms = max(punto_inicio_ms + 1, duracion_total_ms - silencio_fin_ms)

        # Nivelado: diferencia entre el volumen actual (dBFS) y el objetivo
        ganancia_db = 0.0
        if audio.dBFS != float("-inf"):
            ganancia_db = round(DBFS_OBJETIVO - audio.dBFS, 2)

        return {
            "punto_inicio_ms": punto_inicio_ms,
            "punto_fin_ms": punto_fin_ms,
            "punto_golpe_in_ms": punto_inicio_ms,
            "punto_golpe_out_ms": punto_fin_ms,
            "ganancia_db": ganancia_db,
            "duracion_total_ms": duracion_total_ms,
            "analizado": True,
        }

    except Exception as error:
        mensaje = f"{MENSAJE_PYDUB_NO_DISPONIBLE} — archivo: {ruta} — detalle: {error}"
        print(f"[analizador_audio] {mensaje}")
        # Bug real corregido, causa más probable de "el recorte de
        # silencio nunca funciona": antes esto SOLO se imprimía a una
        # consola que nadie ve (la app se lanza desde el ícono de
        # escritorio, sin terminal visible) -- quedaba un fallo
        # COMPLETAMENTE invisible, indistinguible de "funcionó pero no
        # había silencio que cortar". Ahora también queda en
        # log_aplicacion.txt (Configuración -> Diagnóstico -> Ver log),
        # diagnosticable sin tener que reproducir el problema en vivo.
        # Import diferido (config/settings.py ya importa
        # analizador_audio.py de forma diferida en reanalizar_biblioteca
        # -- evita un ciclo de imports a nivel de módulo).
        try:
            from config.settings import registrar_error
            registrar_error(mensaje)
        except Exception:
            pass
        return {
            "punto_inicio_ms": 0,
            "punto_fin_ms": 0,
            "punto_golpe_in_ms": 0,
            "punto_golpe_out_ms": 0,
            "ganancia_db": 0.0,
            "duracion_total_ms": 0,
            "analizado": False,
        }


def volumen_ajustado_por_ganancia(volumen_base_0_a_100: int, ganancia_db: float) -> int:
    """Convierte una ganancia en dB a un volumen 0-100 relativo al
    volumen base, para que MotorAudio.set_volumen() lo aplique al
    arrancar la reproducción de un ítem nivelado."""
    factor = 10 ** (ganancia_db / 20.0)
    volumen = int(round(volumen_base_0_a_100 * factor))
    return max(0, min(100, volumen))


def verificar_motor_disponible() -> dict:
    """Diagnóstico manual (pedido explícito: "veo que nunca funciona
    el recorte de silencio") -- confirma, de punta a punta, si el
    motor de marcas IN/OUT (recorte de silencio + nivelado) puede
    correr de verdad en esta instalación, en vez de descubrirlo recién
    cuando un archivo real falla en silencio. Comprueba, en orden:
    (1) que `pydub` esté instalado, (2) que el binario `ffmpeg` del
    sistema exista en el PATH (pydub lo necesita para decodificar
    cualquier formato que no sea WAV crudo), y (3) una prueba REAL de
    punta a punta con audio sintético generado en memoria (silencio +
    tono, sin necesitar ningún archivo de la biblioteca) para confirmar
    que `analizar_audio()` efectivamente devuelve `analizado=True`.
    Nunca lanza excepción -- degrada a un mensaje claro de qué falta."""
    resultado = {"pydub_ok": False, "ffmpeg_ok": False, "prueba_ok": False, "mensaje": ""}

    # Bug real corregido, encontrado con el log real de Santiago: acá
    # SOLO se atrapaba `ImportError` y se asumía "pydub no está
    # instalado" -- pero en Python 3.13+ el módulo `audioop` de la
    # librería estándar fue ELIMINADO (PEP 594), y pydub (sin
    # actualizarse desde 2021) todavía depende de él en su propio
    # `pydub/utils.py`. Con pydub YA instalado pero `audioop`
    # faltante, `import pydub` igual revienta con un
    # `ModuleNotFoundError` (subclase de `ImportError`) -- el mensaje
    # decía "Falta instalar pydub. pip install pydub", mandando a
    # reinstalar algo que ya estaba instalado y ocultando la causa
    # real. Corregido distinguiendo los dos casos con
    # `importlib.util.find_spec()` (confirma si el PAQUETE existe en
    # disco sin ejecutar su código, así nunca dispara el mismo error
    # que se está diagnosticando) antes de intentar el `import` real.
    import importlib.util
    pydub_instalado_en_disco = importlib.util.find_spec("pydub") is not None
    try:
        import pydub  # noqa: F401
        resultado["pydub_ok"] = True
    except Exception as error:
        if pydub_instalado_en_disco:
            resultado["mensaje"] = (
                f"pydub está instalado, pero falló al importarlo: {error}\n\n"
                "Causa más probable en Python 3.13 o más nuevo: el módulo "
                "\"audioop\" de la librería estándar fue ELIMINADO de Python "
                "(PEP 594) y pydub todavía depende de él. Instalá el "
                "reemplazo (con el entorno virtual activado):\n"
                "pip install audioop-lts"
            )
        else:
            resultado["mensaje"] = (
                "Falta instalar pydub. Con el entorno virtual activado:\n"
                "pip install pydub"
            )
        return resultado

    import shutil
    ffmpeg_encontrado = shutil.which("ffmpeg")
    resultado["ffmpeg_ok"] = bool(ffmpeg_encontrado)
    if not ffmpeg_encontrado:
        resultado["mensaje"] = (
            "pydub está instalado, pero no se encontró el binario \"ffmpeg\" "
            "del sistema (pydub lo necesita para decodificar MP3/M4A/etc.).\n"
            "Instalalo con: sudo apt install ffmpeg"
        )
        return resultado

    try:
        import tempfile
        from pydub import AudioSegment
        from pydub.generators import Sine

        # 300ms de silencio real + 1s de tono a 440Hz + 300ms de
        # silencio -- un caso mínimo con silencio de sobra en los dos
        # extremos para el detector, sin depender de ningún archivo
        # real de la biblioteca (útil incluso en una instalación sin
        # ningún tema cargado todavía).
        segmento = (
            AudioSegment.silent(duration=300)
            + Sine(440).to_audio_segment(duration=1000).apply_gain(-3)
            + AudioSegment.silent(duration=300)
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as archivo_temp:
            ruta_temp = archivo_temp.name
        try:
            segmento.export(ruta_temp, format="wav")
            analisis = analizar_audio(ruta_temp, tolerancia_silencio_segundos=0.1)
        finally:
            import os
            try:
                os.unlink(ruta_temp)
            except OSError:
                pass

        resultado["prueba_ok"] = bool(analisis.get("analizado"))
        if resultado["prueba_ok"]:
            resultado["mensaje"] = (
                "Todo en orden: pydub y ffmpeg están disponibles, y una prueba "
                "real de análisis (silencio + tono generados en memoria) "
                "confirma que el motor calcula marcas IN/OUT correctamente."
            )
        else:
            resultado["mensaje"] = (
                "pydub y ffmpeg están instalados, pero la prueba real de "
                "análisis no devolvió un resultado válido -- revisá el log "
                "de la aplicación para el detalle exacto del error."
            )
    except Exception as error:
        resultado["mensaje"] = f"La prueba real de análisis falló con un error: {error}"

    return resultado
