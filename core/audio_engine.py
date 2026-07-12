"""
core/audio_engine.py
--------------------------------------------------------
Motor de reproducción real basado en python-vlc (libvlc).

Diseño pensado para la doble salida de audio:
- Cada MotorAudio() envuelve UNA instancia de vlc.Instance()
  con su propio MediaPlayer. Para tener Master + Preescucha
  simultáneos e independientes, se instancian DOS MotorAudio,
  cada uno apuntado a un dispositivo ALSA/Pulse/PipeWire distinto
  vía set_dispositivo_salida(id_dispositivo).
- El crossfade se resuelve con dos MotorAudio en paralelo,
  interpolando volumen (uno baja, el otro sube) durante N
  segundos configurables — sin tocar nada a nivel de C/C++.

Si libvlc NO está instalado en el sistema (sudo apt install vlc
libvlc-dev), el motor NO rompe la aplicación: queda en modo
"no disponible" y emite error_reproduccion con un mensaje claro
en vez de lanzar una excepción no controlada.
--------------------------------------------------------
"""

import vlc
from PySide6.QtCore import QObject, Signal, QTimer

MENSAJE_VLC_NO_DISPONIBLE = (
    "VLC no está instalado o no se encontró libvlc. "
    "Instalalo con: sudo apt install vlc libvlc-dev"
)


class MotorAudio(QObject):
    posicion_cambiada = Signal(str, str)   # (transcurrido "hh:mm:ss", restante "hh:mm:ss")
    restante_ms_cambio = Signal(int)       # restante en ms (considera punto_fin_ms) — lo usa el crossfade
    finalizo_item = Signal()
    error_reproduccion = Signal(str)

    def __init__(self, id_dispositivo: str = None, parent=None):
        super().__init__(parent)
        self._id_dispositivo = id_dispositivo
        self._ruta_actual = ""
        self._disponible = True
        self._instancia = None
        self._player = None
        self._punto_fin_ms = None
        self._timer_fade_volumen = None

        try:
            self._instancia = vlc.Instance()
            self._player = self._instancia.media_player_new()
            if id_dispositivo:
                self._player.audio_output_device_set(None, id_dispositivo)

            eventos = self._player.event_manager()
            eventos.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_fin_reproduccion)
            eventos.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)
        except Exception as error:
            self._disponible = False
            print(f"[MotorAudio] {MENSAJE_VLC_NO_DISPONIBLE} — detalle: {error}")

        self._timer_posicion = QTimer(self)
        self._timer_posicion.setInterval(500)
        self._timer_posicion.timeout.connect(self._emitir_posicion)

    # ------------------------------------------------------------------
    def esta_disponible(self) -> bool:
        return self._disponible

    def cargar(self, ruta: str):
        if not self._disponible:
            return
        media = self._instancia.media_new(ruta)
        self._player.set_media(media)
        self._ruta_actual = ruta

    def reproducir(self, ruta: str = None, punto_inicio_ms: int = 0, punto_fin_ms: int = None,
                    ganancia_db: float = 0.0, volumen_base: int = 100):
        """Reproduce `ruta` (o retoma la actual). Si se pasan
        punto_inicio_ms/punto_fin_ms (calculados por
        core/analizador_audio.py al agregar el tema), arranca desde
        ahí y corta antes de llegar al silencio de salida — sin
        tocar el archivo original. `ganancia_db` nivela el volumen
        de ESTE ítem en particular respecto al resto de la biblioteca.
        """
        if not self._disponible:
            self.error_reproduccion.emit(MENSAJE_VLC_NO_DISPONIBLE)
            return
        if ruta and ruta != self._ruta_actual:
            self.cargar(ruta)

        self._punto_fin_ms = punto_fin_ms

        self._player.play()
        self._timer_posicion.start()

        volumen_final = volumen_base
        if ganancia_db:
            from core.analizador_audio import volumen_ajustado_por_ganancia
            volumen_final = volumen_ajustado_por_ganancia(volumen_base, ganancia_db)
        self.set_volumen(volumen_final)

        if punto_inicio_ms and punto_inicio_ms > 0:
            # El seek necesita que el media ya haya arrancado a
            # reproducirse; libvlc lo tolera con un pequeño retardo.
            QTimer.singleShot(150, lambda: self._player.set_time(punto_inicio_ms) if self._disponible else None)

    def pausar(self):
        if not self._disponible:
            return
        self._player.pause()

    def detener(self):
        if not self._disponible:
            return
        self._player.stop()
        self._timer_posicion.stop()
        self._punto_fin_ms = None
        self.posicion_cambiada.emit("00:00:00", "00:00:00")

    def esta_reproduciendo(self) -> bool:
        if not self._disponible:
            return False
        return self._player.is_playing() == 1

    def set_volumen(self, volumen_0_a_100: int):
        if not self._disponible:
            return
        self._player.audio_set_volume(max(0, min(100, volumen_0_a_100)))

    def obtener_volumen(self) -> int:
        if not self._disponible:
            return 0
        volumen = self._player.audio_get_volume()
        return volumen if volumen >= 0 else 0

    def fade_volumen_a(self, volumen_objetivo: int, duracion_segundos: float = 0.8):
        """Rampa suave de volumen hacia `volumen_objetivo` (0-100) en
        `duracion_segundos`, en vez de un salto brusco — pedido
        explícito: "toda subida y bajada de audio debe ser mediante
        Fade". La usa el ducking del Pisador (bajar/subir el tema
        principal), pero sirve para cualquier cambio de volumen que
        no deba notarse como un corte.
        """
        if not self._disponible:
            self.set_volumen(volumen_objetivo)
            return

        if self._timer_fade_volumen is not None:
            self._timer_fade_volumen.stop()

        volumen_objetivo = max(0, min(100, volumen_objetivo))
        volumen_inicial = self.obtener_volumen()

        if duracion_segundos <= 0 or volumen_inicial == volumen_objetivo:
            self.set_volumen(volumen_objetivo)
            return

        pasos = 20
        intervalo_ms = max(20, int((duracion_segundos * 1000) / pasos))
        contador = {"paso": 0}

        timer = QTimer(self)
        self._timer_fade_volumen = timer
        timer.setInterval(intervalo_ms)

        def _paso():
            contador["paso"] += 1
            fraccion = contador["paso"] / pasos
            volumen_actual = int(volumen_inicial + (volumen_objetivo - volumen_inicial) * fraccion)
            self.set_volumen(volumen_actual)
            if contador["paso"] >= pasos:
                timer.stop()
                self.set_volumen(volumen_objetivo)

        timer.timeout.connect(_paso)
        timer.start()

    # ------------------------------------------------------------------
    # Posición / seek (barra de progreso de Ventana 2)
    # ------------------------------------------------------------------
    def duracion_total_ms(self) -> int:
        if not self._disponible:
            return 0
        return max(0, self._player.get_length())

    def buscar_posicion_ms(self, ms: int):
        if not self._disponible:
            return
        self._player.set_time(max(0, ms))

    def set_dispositivo_salida(self, id_dispositivo: str):
        self._id_dispositivo = id_dispositivo
        if self._disponible:
            self._player.audio_output_device_set(None, id_dispositivo)

    def id_dispositivo(self) -> str:
        return self._id_dispositivo

    def listar_dispositivos(self):
        """[(id, descripcion), ...] de las salidas de audio disponibles."""
        if not self._disponible:
            return []
        dispositivos = []
        lista = self._player.audio_output_device_enum()
        nodo = lista
        while nodo:
            contenido = nodo.contents
            dispositivo_id = contenido.device.decode("utf-8", errors="ignore")
            descripcion = contenido.description.decode("utf-8", errors="ignore")
            dispositivos.append((dispositivo_id, descripcion))
            nodo = contenido.next
        if lista:
            vlc.libvlc_audio_output_device_list_release(lista)
        return dispositivos

    # ------------------------------------------------------------------
    # Crossfade: interpola volumen entre el ítem saliente y el entrante
    # ------------------------------------------------------------------
    def crossfade_a(self, ruta_siguiente: str, duracion_segundos: float = 3.0, motor_entrante=None):
        """
        Ejecuta un crossfade hacia `ruta_siguiente`. Usa un segundo
        MotorAudio (motor_entrante) para el archivo que entra, mientras
        éste (self) hace fade-out del que sale. Si no se pasa
        motor_entrante, se crea uno temporal sobre el mismo dispositivo.
        Devuelve el motor entrante (para que quien llame lo conserve
        como "reproductor activo" luego del fade).
        """
        if not self._disponible:
            self.error_reproduccion.emit(MENSAJE_VLC_NO_DISPONIBLE)
            return None

        entrante = motor_entrante or MotorAudio(self._id_dispositivo)
        entrante.set_volumen(0)
        entrante.reproducir(ruta_siguiente)

        pasos = 30
        intervalo_ms = max(20, int((duracion_segundos * 1000) / pasos))
        contador = {"paso": 0}

        timer = QTimer(self)
        timer.setInterval(intervalo_ms)

        def _paso():
            contador["paso"] += 1
            fraccion = contador["paso"] / pasos
            self.set_volumen(int(100 * (1 - fraccion)))
            entrante.set_volumen(int(100 * fraccion))
            if contador["paso"] >= pasos:
                timer.stop()
                self.detener()

        timer.timeout.connect(_paso)
        timer.start()
        return entrante

    # ------------------------------------------------------------------
    def _emitir_posicion(self):
        if not self._disponible:
            return
        largo_ms = self._player.get_length()
        actual_ms = self._player.get_time()
        if largo_ms <= 0 or actual_ms < 0:
            return

        if self._punto_fin_ms and actual_ms >= self._punto_fin_ms:
            self._timer_posicion.stop()
            self._player.stop()
            self.finalizo_item.emit()
            return

        limite_ms = self._punto_fin_ms if self._punto_fin_ms else largo_ms
        restante_ms = max(0, limite_ms - actual_ms)
        self.posicion_cambiada.emit(self._formatear_ms(actual_ms), self._formatear_ms(restante_ms))
        self.restante_ms_cambio.emit(restante_ms)

    @staticmethod
    def _formatear_ms(ms: int) -> str:
        segundos_totales = ms // 1000
        horas = segundos_totales // 3600
        minutos = (segundos_totales % 3600) // 60
        segundos = segundos_totales % 60
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def _on_fin_reproduccion(self, evento):
        self._timer_posicion.stop()
        self.finalizo_item.emit()

    def _on_error(self, evento):
        self.error_reproduccion.emit(f"Error reproduciendo: {self._ruta_actual}")


def obtener_duracion_formateada(ruta: str) -> str:
    """Duración 'hh:mm:ss' de un archivo de audio usando mutagen.

    Se usa al soltar un archivo desde el Explorador (Ventana 3) en
    cualquiera de las listas, para completar la columna Duración
    sin tener que reproducirlo primero.
    """
    try:
        from mutagen import File as ArchivoMutagen
        audio = ArchivoMutagen(ruta)
        if audio is not None and audio.info is not None:
            return MotorAudio._formatear_ms(int(audio.info.length * 1000))
    except Exception:
        pass
    return "00:00:00"
