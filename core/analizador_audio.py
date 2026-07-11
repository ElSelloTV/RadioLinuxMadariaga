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

DBFS_OBJETIVO = -16.0          # nivel de referencia al que se nivela todo
UMBRAL_SILENCIO_DBFS = -40.0   # por debajo de esto se considera "silencio"


def analizar_audio(ruta: str, tolerancia_silencio_segundos: float = 2.0) -> dict:
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
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_leading_silence

        audio = AudioSegment.from_file(ruta)
        duracion_total_ms = len(audio)
        tolerancia_ms = int(tolerancia_silencio_segundos * 1000)

        # Silencio de entrada
        silencio_inicio_ms = detect_leading_silence(audio, silence_threshold=UMBRAL_SILENCIO_DBFS)
        silencio_inicio_ms = max(0, silencio_inicio_ms - tolerancia_ms)  # deja un margen (tolerancia)

        # Silencio de salida: se mide igual pero sobre el audio invertido
        silencio_fin_ms = detect_leading_silence(audio.reverse(), silence_threshold=UMBRAL_SILENCIO_DBFS)
        silencio_fin_ms = max(0, silencio_fin_ms - tolerancia_ms)

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
        print(f"[analizador_audio] {MENSAJE_PYDUB_NO_DISPONIBLE} — detalle: {error}")
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
