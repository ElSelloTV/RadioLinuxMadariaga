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

from config.settings import registrar_evento, cargar_configuracion

MENSAJE_VLC_NO_DISPONIBLE = (
    "VLC no está instalado o no se encontró libvlc. "
    "Instalalo con: sudo apt install vlc libvlc-dev"
)

# Defaults si config_general.json todavía no tiene estas claves
# (instalación vieja) — ver config/settings.py:CONFIG_POR_DEFECTO["reproduccion"].
BUFFER_CACHING_MS_POR_DEFECTO = 1000
RETARDO_ARRANQUE_MS_POR_DEFECTO = 150


def _argumentos_vlc(duracion_buffer_caching_ms: int, audio_cfg: dict = None) -> list:
    """Argumentos de la instancia de libVLC (pedido explícito, "para
    robustecer el sistema"):
    - "--no-video": esta app es 100% de audio — si un archivo cargado
      por error tiene pista de video (ej. un .mp4 importado a la
      biblioteca), libVLC NUNCA decodifica ni intenta abrir una ventana
      de video para él, solo extrae el audio. Sin esto, decodificar
      video de más gasta CPU/memoria en vano en hardware modesto (la
      notebook de Santiago, Celeron N2820) y puede ser una causa real de
      "tartamudeo".
    - "--file-caching=N": sube el buffer de lectura/decodificación de
      archivo de libVLC de ~300ms (default de libVLC) a N ms — pedido
      explícito ("un sistema de buffer... que otorgue fluidez
      auditiva"): con más margen de buffer, una ráfaga de CPU ocupada
      por otra tarea de la app (un import pesado, redibujar la UI,
      etc.) tiene mucho más espacio antes de que la reproducción
      llegue a notarse entrecortada. Configurable desde Configuración
      → Reproducción y Automatización (pedido explícito, ronda
      posterior) — OJO: es un argumento de instancia de libVLC, un
      cambio solo aplica a los MotorAudio creados DESPUÉS de guardar
      (en la práctica, tras reabrir la app), no a los ya en curso.

    El compresor/Stereo Enhancer/Volume Normalizer nativos de libVLC
    que vivieron acá (Configuración → Procesador, rondas 69-74) se
    sacaron a pedido explícito de Santiago: construyó una app Python
    aparte, standalone, que controla el filter-chain NATIVO de
    PipeWire (plugins Calf en C, cero procesamiento en Python) — el
    mismo enfoque que ya se había probado y sonaba bien en la ronda
    52, ahora con una interfaz de control propia. El diagnóstico de
    esa ronda había confirmado además que el compresor headless de
    esta app probablemente nunca aplicaba de verdad sobre el audio
    real (libVLC sin interfaz gráfica adjunta no arma el filtro de
    forma confiable) — otra razón de peso para no mantenerlo acá.
    `audio_cfg` queda como parámetro por compatibilidad de firma, sin
    uso real por ahora."""
    return ["--no-video", f"--file-caching={max(0, int(duracion_buffer_caching_ms))}"]


class MotorAudio(QObject):
    posicion_cambiada = Signal(str, str)   # (transcurrido "hh:mm:ss", restante "hh:mm:ss")
    restante_ms_cambio = Signal(int)       # restante en ms (considera punto_fin_ms) — lo usa el crossfade
    finalizo_item = Signal()
    error_reproduccion = Signal(str)

    def __init__(self, id_dispositivo: str = None, parent=None, aplicar_procesador: bool = True):
        super().__init__(parent)
        self._id_dispositivo = id_dispositivo
        # `aplicar_procesador` queda como parámetro por compatibilidad
        # con los llamadores existentes (GestorExplorador lo pasa en
        # `False` para el Previo de Ventana 3) — desde que se sacó el
        # compresor/Stereo Enhancer/Volume Normalizer nativos de libVLC
        # (ver `_argumentos_vlc()`), ya no cambia nada en la práctica.
        self._aplicar_procesador = aplicar_procesador
        self._ruta_actual = ""
        self._disponible = True
        self._instancia = None
        self._player = None
        self._punto_fin_ms = None
        self._timer_fade_volumen = None
        # Bug real corregido — "es la hora veintitres, en punto en
        # punto" (HTH) y en general cualquier ítem repetido/salteado de
        # más al terminar: `finalizo_item` podía emitirse DOS VECES
        # para el mismo fin de reproducción — una desde el tick de
        # `_emitir_posicion()` (corte por `punto_fin_ms`, conexión
        # DIRECTA en el hilo principal) y otra desde el evento nativo
        # `MediaPlayerEndReached` de libVLC (`_on_fin_reproduccion`,
        # disparado desde un hilo interno de libVLC — la entrega al
        # slot en el hilo principal queda ENCOLADA por Qt, así que
        # puede procesarse recién después de que la primera ya haya
        # arrancado el clip/ítem SIGUIENTE). Para un clip corto con
        # margen de silencio casi nulo (los HTH, género de "corte
        # estricto") ambas detecciones de "se terminó" caen casi
        # siempre dentro de la misma ventana de tiempo. Con la cola de
        # clips del Comando HTH ya en su último elemento, esa segunda
        # emisión tardía volvía a evaluar "cola vacía" y disparaba
        # OTRA vuelta de avance — sonando como si el último clip
        # ("en punto") se repitiera. Corregido con un guard de una
        # sola vez por reproducción: cada `reproducir()` nuevo abre una
        # ventana fresca (`_fin_ya_emitido = False`); la PRIMERA
        # detección de fin (sea cual sea el origen) emite la señal y
        # cierra la ventana — cualquier detección posterior para ESA
        # MISMA reproducción se ignora en silencio.
        self._fin_ya_emitido = False
        # Contador de generación de reproducción — ver el guard dentro
        # de reproducir()/_tras_arranque() más abajo (bug real: "repite
        # muy breve el inicio").
        self._generacion_reproduccion = 0
        # Volumen que ESTE motor debería tener ahora mismo — la fuente
        # de verdad del volumen ya no es el reproductor de libVLC sino
        # este atributo (ver set_volumen / _emitir_posicion). Bug real
        # corregido: audio_set_volume() llamado justo después de
        # play() puede ser DESCARTADO en silencio por libVLC (la
        # salida de audio del reproductor todavía no terminó de
        # crearse, sobre todo después de un stop()) — el resultado era
        # un ítem o un Pisador reproduciéndose entero PERO MUDO, sin
        # ningún error. Ahora el volumen deseado se recuerda acá y se
        # re-aplica solo (en el arranque diferido y en cada tick de
        # posición) hasta que el reproductor lo tome de verdad.
        self._volumen_deseado = 100
        # Diagnóstico (pedido explícito, "sigue sin reproducir por
        # donde lo selecciono"): recuerda el último device por el que
        # se logueó, para no spamear log_aplicacion.txt en cada
        # reproducir() -- pero SÍ dejar un rastro claro de qué string
        # exacto se le manda a libVLC, comparable a mano contra
        # `pactl list sinks short` en la PC real.
        self._ultimo_dispositivo_logueado = "___sin_loguear_todavia___"

        config_actual = cargar_configuracion()
        reproduccion = config_actual.get("reproduccion", {})
        self._retardo_arranque_ms = reproduccion.get(
            "retardo_arranque_ms", RETARDO_ARRANQUE_MS_POR_DEFECTO
        )
        duracion_buffer_caching_ms = reproduccion.get(
            "duracion_buffer_caching_ms", BUFFER_CACHING_MS_POR_DEFECTO
        )

        try:
            argumentos_finales = _argumentos_vlc(duracion_buffer_caching_ms)
            self._instancia = vlc.Instance(argumentos_finales)
            if self._instancia is None:
                raise RuntimeError("vlc.Instance() devolvió None")
            self._player = self._instancia.media_player_new()
            if id_dispositivo:
                self._aplicar_dispositivo_salida()

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
                    ganancia_db: float = 0.0, volumen_base: int = 100, duracion_declick_ms: int = 0):
        """Reproduce `ruta` (o retoma la actual). Si se pasan
        punto_inicio_ms/punto_fin_ms (calculados por
        core/analizador_audio.py al agregar el tema), arranca desde
        ahí y corta antes de llegar al silencio de salida — sin
        tocar el archivo original. `ganancia_db` nivela el volumen
        de ESTE ítem en particular respecto al resto de la biblioteca.

        `duracion_declick_ms` (pedido explícito, Ventana 1: "un mínimo
        tartamudeo, incluso un clip de sonido al inicio... un leve
        fade de inicio"): en vez de saltar de golpe a `volumen_final`
        justo al arrancar, sube en una rampa de unos pocos MILISEGUNDOS
        — evita el click/discontinuidad de un escalón de volumen
        instantáneo (más audible desde que el audio pasa por una
        cadena de efectos como EasyEffects, donde un compresor/
        limiter/autogain puede reaccionar de forma audible a ese
        escalón). 0 (default) = comportamiento de siempre, salto
        directo. Esto es DISTINTO del fade-in MUSICAL que se sacó a
        propósito en una ronda anterior ("que los temas suenen más
        enganchados, sin fade-in") — acá la duración es de
        milisegundos, muy por debajo de lo perceptible como "fundido",
        solo alcanza para evitar el artefacto digital.
        """
        if not self._disponible:
            self.error_reproduccion.emit(MENSAJE_VLC_NO_DISPONIBLE)
            return
        if ruta and ruta != self._ruta_actual:
            self.cargar(ruta)

        self._punto_fin_ms = punto_fin_ms
        # Nueva ventana de "fin todavía no emitido" para ESTA
        # reproducción -- ver el guard `_fin_ya_emitido` en __init__.
        self._fin_ya_emitido = False
        # Generación de ESTA reproducción -- ver `_tras_arranque()` más
        # abajo, mismo espíritu que `_fin_ya_emitido`: protege contra un
        # `_tras_arranque()` diferido de una llamada VIEJA que llegue a
        # disparar después de que ya arrancó una reproducción NUEVA en
        # este mismo motor (reproducir() llamado de nuevo rápido, ej. un
        # Pisador cancelado/reemplazado dentro de la ventana de 150ms
        # del diferido) -- sin esto, el seek/volumen viejo corrompería
        # la reproducción nueva.
        self._generacion_reproduccion += 1
        generacion_de_esta_reproduccion = self._generacion_reproduccion

        # Bug real corregido — "el mismo archivo de Pisador reusado en
        # varios temas, deja de sonar después de la primera vez, ni
        # siquiera con el seek a 0ms de más abajo": cuando libVLC llega
        # al FIN NATURAL de un media (evento MediaPlayerEndReached, sin
        # que nadie llame a stop() explícitamente), el reproductor
        # queda en estado "Ended" — en ese estado, un simple play() NO
        # reinicia la reproducción de forma confiable en varias
        # versiones de libVLC (queda "vivo" pero mudo). Un stop()
        # explícito ANTES de play() fuerza a libVLC a resetear ese
        # estado, sin importar si cargar() se ejecutó arriba o no —
        # así reproducir dos, tres o más veces el MISMO archivo
        # siempre vuelve a sonar, no solo la primera.
        self._player.stop()

        # Cualquier fade de volumen que haya quedado corriendo de una
        # reproducción anterior en ESTE MISMO motor (ej. el fundido a
        # 0 de "cancelar un Pisador en curso") se cancela acá — si no,
        # ese timer viejo puede seguir pisando el volumen de la
        # reproducción recién arrancada varios pasos más, dejándola
        # sonando pero en silencio.
        if self._timer_fade_volumen is not None:
            self._timer_fade_volumen.stop()

        self._player.play()
        self._timer_posicion.start()

        # Re-aplica el dispositivo de salida elegido — ver
        # _aplicar_dispositivo_salida(): el stop() de arriba desarma la
        # salida de audio, así que la selección hecha en Configuración
        # se pierde si no se refuerza acá en cada arranque.
        self._aplicar_dispositivo_salida()

        volumen_final = volumen_base
        if ganancia_db:
            from core.analizador_audio import volumen_ajustado_por_ganancia
            volumen_final = volumen_ajustado_por_ganancia(volumen_base, ganancia_db)
        if duracion_declick_ms > 0:
            self.set_volumen(0)
            self.fade_volumen_a(volumen_final, duracion_declick_ms / 1000.0)
        else:
            self.set_volumen(volumen_final)

        # El seek necesita que el media ya haya arrancado a
        # reproducirse; libvlc lo tolera con un pequeño retardo.
        # En el mismo diferido se RE-APLICA el volumen deseado: el
        # set_volumen() de arriba corre justo después de play(), y en
        # ese instante libVLC puede descartarlo en silencio porque la
        # salida de audio del reproductor todavía no existe (sobre
        # todo tras el stop() de arriba, que la desarma) — el síntoma
        # real era un Pisador o un tema reproduciéndose entero pero
        # MUDO. La red de seguridad final es _emitir_posicion(), que
        # re-aplica el volumen deseado en cada tick de posición.
        #
        # Bug real corregido — "repite muy breve el inicio" (Pisadores
        # en Ventana 2/Auxiliar, y algunos ítems de Ventana 1): el seek
        # de acá SIEMPRE se hacía, incluso a 0ms — pero el stop() de
        # arriba YA garantiza que un play() nuevo arranca desde la
        # posición 0 (es justo el fix del bug de "el Pisador reusado
        # deja de sonar", documentado arriba). Con punto_inicio_ms en 0
        # (frecuente en Pisadores/stings cortos sin silencio de cabeza,
        # y en cualquier ítem donde el análisis de silencio no encontró
        # nada para recortar), el archivo YA estaba sonando de forma
        # correcta desde el instante 0 durante los `retardo_arranque_ms`
        # (150ms por defecto) que tarda en dispararse este diferido —
        # el `set_time(0)` de acá, en vez de ser un no-op, REBOBINABA
        # ese contenido YA reproducido de vuelta al principio, sonando
        # como si el inicio se repitiera. Corregido: el seek SOLO se
        # hace si `punto_inicio_ms` es un offset real (> 0) — no hay
        # nada que "reiniciar" si ya está sonando desde el principio.
        def _tras_arranque():
            if not self._disponible:
                return
            if self._generacion_reproduccion != generacion_de_esta_reproduccion:
                return  # una reproducción MÁS NUEVA ya arrancó en este motor
            if punto_inicio_ms > 0:
                self._player.set_time(punto_inicio_ms)
            self._player.audio_set_volume(self._volumen_deseado)
            self._aplicar_dispositivo_salida()
        QTimer.singleShot(self._retardo_arranque_ms, _tras_arranque)

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
        # El volumen deseado se recuerda SIEMPRE (aunque libVLC no
        # esté disponible o descarte la llamada) — es la fuente de
        # verdad que _emitir_posicion() re-aplica en cada tick.
        self._volumen_deseado = max(0, min(100, volumen_0_a_100))
        if not self._disponible:
            return
        self._player.audio_set_volume(self._volumen_deseado)

    def volumen_deseado(self) -> int:
        """El volumen que este motor DEBERÍA tener ahora (el último
        pedido vía set_volumen) — a diferencia de obtener_volumen(),
        nunca depende del estado interno de libVLC, así que es seguro
        leerlo inmediatamente después de reproducir() (cuando el
        reproductor real todavía puede devolver 0/-1)."""
        return self._volumen_deseado

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
        # El punto de partida de la rampa es el volumen DESEADO, no el
        # que reporta libVLC — leído justo después de un play() el
        # reproductor puede devolver 0/-1 espurio y la rampa saldría
        # de un valor falso.
        volumen_inicial = self._volumen_deseado

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
        self._aplicar_dispositivo_salida()

    def id_dispositivo(self) -> str:
        return self._id_dispositivo

    @staticmethod
    def _modulo_y_dispositivo(id_dispositivo: str):
        """Separa el id compuesto que arma `listar_dispositivos()`
        (`"{modulo}||{device}"`) en (modulo, device) —
        `audio_output_device_set()` necesita el módulo (ej. "pulse",
        "alsa") para aplicar la selección de verdad, no alcanza con el
        id del dispositivo solo (ver nota en `listar_dispositivos()`).
        Si no tiene el separador (un id "viejo" guardado por una
        versión anterior de la app, o algo tipeado a mano en el combo
        editable de Configuración), se interpreta como dispositivo
        solo, sin módulo — mismo comportamiento de siempre, sigue
        funcionando para no romper una config ya guardada."""
        if id_dispositivo and "||" in id_dispositivo:
            modulo, _, device = id_dispositivo.partition("||")
            return modulo, device
        return None, id_dispositivo

    def _aplicar_dispositivo_salida(self):
        """Bug real corregido ("sin importar lo que yo elija, siempre
        sale por la salida principal"): dos causas, una encima de la
        otra.

        (1) `reproducir()` hace un `stop()` antes de cada `play()`
        (necesario para el bug de libVLC de Pisadores reusados, ver
        más arriba) — y cada `stop()` DESARMA la salida de audio
        (aout) del reproductor, que se vuelve a crear de cero en el
        próximo `play()`. La selección de dispositivo, aplicada UNA
        sola vez al elegirla en Configuración, se perdía en el primer
        stop()/play() siguiente (que pasa todo el tiempo en el uso
        normal de la radio) — mismo patrón de bug ya resuelto para el
        volumen (`_volumen_deseado`, re-aplicado en cada arranque).
        Esta función es el punto único de aplicación, llamada tanto al
        elegir el dispositivo como en cada `reproducir()` (inmediato y
        en el diferido de 150ms) — nunca confiar en que UNA sola
        llamada alcance.

        (2) Segunda causa, más de fondo, encontrada tras el primer
        fix: `MediaPlayer.audio_output_device_set(module, device_id)`
        documenta textualmente (docstring real de python-vlc) que
        pasar un MÓDULO explícito (ej. "pulse") "no tiene efecto en
        algunos módulos de audio, notablemente MMDevice y
        **PulseAudio**" — y que "si el parámetro module es None, la
        salida de audio se mueve al dispositivo indicado
        INMEDIATAMENTE. Este es el uso recomendado." Como la inmensa
        mayoría de instalaciones Linux de escritorio (la de Santiago
        incluida) corren sobre PulseAudio o el compat layer de
        PipeWire, pasar el módulo explícito (necesario para
        `listar_dispositivos()`, que si necesita recorrer módulo por
        módulo para poder listar SIN haber reproducido nada — ver esa
        función, NO tocar esa parte) hacía que la selección se
        aplicara en silencio a nada — libVLC ni siquiera tira error
        ("Errors are ignored (this is a design bug)", literal del
        propio docstring). Corregido pasando SIEMPRE `module=None` acá
        (el uso recomendado por la propia librería) — el módulo
        codificado en el id compuesto (`"{modulo}||{device}"`) se
        sigue usando para LISTAR (evita duplicados/ambigüedad entre
        módulos) pero se descarta al momento de aplicar.

        Log de diagnóstico (pedido explícito, "sigue sin reproducir
        por donde lo selecciono... no toma control sobre la placa"):
        deja un rastro en `log_aplicacion.txt` con el string EXACTO
        que se le pasa a libVLC, para comparar a mano contra `pactl
        list sinks short` en la PC real — dedupeado (una vez por
        device distinto, no en cada reproducir()) para no saturar el
        log."""
        if not self._disponible or not self._id_dispositivo:
            return
        _, device = self._modulo_y_dispositivo(self._id_dispositivo)
        if device != self._ultimo_dispositivo_logueado:
            registrar_evento(
                f"MotorAudio: aplicando audio_output_device_set(None, '{device}') "
                f"(id guardado en config: '{self._id_dispositivo}')"
            )
            self._ultimo_dispositivo_logueado = device
        self._player.audio_output_device_set(None, device)

    def listar_dispositivos(self):
        """[(id, descripcion), ...] de las salidas de audio reales del
        sistema (ej. parlantes analógicos Y salida HDMI de un monitor,
        como dos entradas separadas).

        Bug real corregido ("no tengo forma gráfica de elegir la
        salida" — el combo de Configuración no mostraba las salidas
        reales, ej. una HDMI): antes usaba
        `MediaPlayer.audio_output_device_enum()`, que por diseño de
        libVLC solo enumera los dispositivos del output QUE YA ESTÁ EN
        USO — con un reproductor que TODAVÍA NO reprodujo nada (el
        caso real acá: Configuración arma un `MotorAudio()` de mentira
        solo para listar, sin reproducir nada), esa llamada devuelve
        una lista vacía o incompleta, sin las salidas reales del
        hardware. Reemplazado por la API a nivel de `Instance`
        (`audio_output_list_get()` + `audio_output_device_list_get()`
        por cada módulo de audio del sistema — pulse, alsa, etc.),
        disponible desde libVLC 2.1.0, que NO depende de que haya una
        salida activa: recorre TODOS los módulos y sus dispositivos
        reales sin necesitar reproducir nada primero.

        El id devuelto codifica el módulo junto con el dispositivo —
        ver `_modulo_y_dispositivo()`, que lo separa de nuevo al
        aplicar la selección."""
        if not self._disponible:
            return []
        dispositivos = []
        modulos = self._instancia.audio_output_list_get()
        nodo_modulo = modulos
        while nodo_modulo:
            contenido_modulo = nodo_modulo.contents
            nombre_modulo = contenido_modulo.name.decode("utf-8", errors="ignore")

            lista_dispositivos = self._instancia.audio_output_device_list_get(nombre_modulo)
            nodo = lista_dispositivos
            while nodo:
                contenido = nodo.contents
                device_id = contenido.device.decode("utf-8", errors="ignore")
                descripcion = contenido.description.decode("utf-8", errors="ignore")
                dispositivos.append((f"{nombre_modulo}||{device_id}", descripcion))
                nodo = contenido.next
            if lista_dispositivos:
                vlc.libvlc_audio_output_device_list_release(lista_dispositivos)

            nodo_modulo = contenido_modulo.next
        if modulos:
            vlc.libvlc_audio_output_list_release(modulos)
        return dispositivos

    # ------------------------------------------------------------------
    # Crossfade: interpola volumen entre el ítem saliente y el entrante
    # ------------------------------------------------------------------
    def crossfade_a(self, ruta_siguiente: str, duracion_segundos: float = 3.0, motor_entrante=None,
                     punto_inicio_ms: int = 0, punto_fin_ms: int = None, ganancia_db: float = 0.0,
                     volumen_base: int = 100, duracion_fade_in_ms: int = 0):
        """
        Ejecuta un crossfade hacia `ruta_siguiente`. Usa un segundo
        MotorAudio (motor_entrante) para el archivo que entra, mientras
        éste (self) hace fade-out del que sale. Si no se pasa
        motor_entrante, se crea uno temporal sobre el mismo dispositivo.
        Devuelve el motor entrante (para que quien llame lo conserve
        como "reproductor activo" luego del fade).

        Bug real corregido — "mucho silencio y atenuación al
        encadenar temas": antes el tema ENTRANTE se reproducía sin su
        recorte de silencio de entrada ni su nivelado de volumen (se
        llamaba reproducir() sin esos parámetros), así que cada
        crossfade arrancaba con el silencio de entrada del tema
        siguiente todavía puesto, y a un volumen sin nivelar —
        sonaba como un "bache" en vez de un encadenado fluido. Ahora
        recibe los mismos punto_inicio_ms/punto_fin_ms/ganancia_db que
        ya usa la reproducción normal. Además, el volumen de la rampa
        ahora es relativo al volumen REAL de cada motor (el actual del
        saliente, el correcto ya nivelado del entrante) en vez de una
        escala fija 0-100 — antes eso producía un salto audible de
        volumen justo al arrancar el crossfade si el volumen Master
        configurado no era 100.

        `duracion_fade_in_ms` (pedido explícito, ronda posterior:
        "perfeccioná el fundido... el inicio con un fundido muy breve
        de 400ms"): reemplaza la decisión de una ronda anterior de NO
        hacer fade-in en el entrante — ahora el entrante SÍ arranca con
        una rampa corta (vía `MotorAudio.reproducir(duracion_declick_ms=...)`),
        en paralelo al fade-out del saliente. 0 = sin fade-in (arranca
        directo a volumen final, comportamiento de la ronda anterior).
        """
        if not self._disponible:
            self.error_reproduccion.emit(MENSAJE_VLC_NO_DISPONIBLE)
            return None

        # Punto de partida del fade-out: el volumen real del saliente,
        # con el deseado como respaldo si libVLC devuelve 0/-1 espurio.
        volumen_inicial_saliente = self.obtener_volumen() or self._volumen_deseado

        entrante = motor_entrante or MotorAudio(self._id_dispositivo, aplicar_procesador=self._aplicar_procesador)
        entrante.reproducir(
            ruta_siguiente, punto_inicio_ms=punto_inicio_ms, punto_fin_ms=punto_fin_ms,
            ganancia_db=ganancia_db, volumen_base=volumen_base,
            duracion_declick_ms=duracion_fade_in_ms,
        )
        if duracion_fade_in_ms <= 0:
            # Sin fade-in configurado: arranca directo a volumen final
            # (nivelado por `reproducir()`/`volumen_deseado()` — nunca
            # una lectura espuria de libVLC recién arrancado).
            entrante.set_volumen(entrante.volumen_deseado())

        pasos = 30
        intervalo_ms = max(20, int((duracion_segundos * 1000) / pasos))
        contador = {"paso": 0}

        timer = QTimer(self)
        timer.setInterval(intervalo_ms)

        def _paso():
            contador["paso"] += 1
            fraccion = contador["paso"] / pasos
            self.set_volumen(int(volumen_inicial_saliente * (1 - fraccion)))
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

        # Red de seguridad del volumen (bug real: "el ítem se
        # reproduce pero está MUDO"): si el volumen real del
        # reproductor no coincide con el deseado — porque libVLC
        # descartó un audio_set_volume() hecho antes de que su salida
        # de audio existiera — se re-aplica acá, en cada tick (500ms),
        # hasta que quede efectivo. Los fades no se rompen: cada paso
        # de rampa pasa por set_volumen(), que actualiza el deseado.
        volumen_real = self._player.audio_get_volume()
        if volumen_real != self._volumen_deseado:
            self._player.audio_set_volume(self._volumen_deseado)

        largo_ms = self._player.get_length()
        actual_ms = self._player.get_time()
        if largo_ms <= 0 or actual_ms < 0:
            return

        if self._punto_fin_ms and actual_ms >= self._punto_fin_ms:
            self._timer_posicion.stop()
            self._player.stop()
            self._emitir_fin_una_vez()
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
        self._emitir_fin_una_vez()

    def _emitir_fin_una_vez(self):
        """Emite `finalizo_item` UNA sola vez por reproducción -- ver
        el guard `_fin_ya_emitido` (comentario completo en __init__).
        Cualquier detección de "fin" posterior a la primera, para esta
        MISMA reproducción, se ignora en silencio."""
        if self._fin_ya_emitido:
            return
        self._fin_ya_emitido = True
        self.finalizo_item.emit()

    def _on_error(self, evento):
        self.error_reproduccion.emit(f"Error reproduciendo: {self._ruta_actual}")


if __name__ == "__main__":
    # Invocado como PROCESO APARTE por
    # VentanaConfiguracion._listar_dispositivos_disponibles() (gui/
    # ventana_configuracion.py) -- nunca a mano. Bug real de
    # producción: listar dispositivos armaba un MotorAudio() temporal
    # DENTRO del mismo proceso que ya tiene otras instancias de libVLC
    # reproduciendo -- si esa consulta se cuelga (le pasa al módulo
    # "pulse" bajo ciertas condiciones), un primer fix (hilo con
    # timeout de 3s) evitaba el freeze de la ventana, pero la conexión
    # de PulseAudio del hilo abandonado NUNCA se cerraba -- tras varias
    # horas de abrir Configuración, `pipewire-pulse` terminó
    # rechazando TODAS las conexiones nuevas ("too many client
    # application connections"), cortando hasta `pactl`. Un hilo de
    # Python no puede abortar una llamada C bloqueante de forma
    # segura ni liberar su socket; un PROCESO aparte sí -- si no
    # responde a tiempo, se lo mata con SIGKILL desde afuera, y el
    # sistema operativo cierra su conexión de PulseAudio solo, sin
    # dejar nada pendiente.
    import json as _json
    _motor = MotorAudio()
    _dispositivos = _motor.listar_dispositivos() if _motor.esta_disponible() else []
    print(_json.dumps(_dispositivos))


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
