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

import os
import subprocess
import time

import vlc
from PySide6.QtCore import QObject, Signal, QTimer, QProcess

from config.settings import registrar_evento, cargar_configuracion


def _es_nombre_pactl_directo(id_dispositivo) -> bool:
    """True si `id_dispositivo` es un nombre de sink de PipeWire/pactl
    escrito DIRECTO (ej. "alsa_output.pci-0000_00_14.2.analog-stereo",
    tal cual lo devuelve `pactl list sinks short`) — a diferencia del
    formato "modulo||dispositivo" que arma `listar_dispositivos()` a
    partir de los módulos de audio de libVLC.

    Fallback real de producción: en instalaciones donde libVLC no
    tiene compilado un módulo de salida "pulse" (confirmado en una PC
    real — `audio_output_list_get()` solo devolvía módulo "alsa"),
    `audio_output_device_set()` no tiene forma de apuntar a un sink de
    PipeWire específico — con PipeWire manejando la placa de forma
    exclusiva, un dispositivo ALSA "crudo" (`hw:CARD=...`) elegido de
    la lista no hace nada, en silencio. Escribiendo el nombre real del
    sink a mano en el combo de Configuración -> Audio (es editable) —
    o eligiéndolo de la lista simplificada de `listar_dispositivos_pactl()`,
    que SIEMPRE devuelve nombres en este formato — activa
    `_enrutador_pactl().reclamar()` en su lugar, ver
    `MotorAudio.reproducir()`."""
    return bool(id_dispositivo) and id_dispositivo != "default" and "||" not in id_dispositivo


class EnrutadorPactl(QObject):
    """Mueve, vía `pactl move-sink-input`, el stream de audio recién
    arrancado al sink real que corresponde (Master -> consola/USB,
    Preescucha -> parlantes de monitoreo, NUNCA al revés) — necesario
    porque libVLC, sin el módulo "pulse" compilado, no tiene forma de
    apuntar directo a un sink de PipeWire (ver `_es_nombre_pactl_directo`).

    Reemplaza el mecanismo viejo (`mover_stream_nuevo_a_sink()`,
    función suelta con `subprocess.run()`/`time.sleep()` BLOQUEANTES,
    llamada directo desde el hilo principal de Qt en cada
    `reproducir()`) por dos correcciones de fondo, pedidas explícitas
    tras un reporte real de la operadora (cortes de audio "como cuando
    saltaban los CDs", cortinas mudas, y Preescucha filtrándose al
    aire):

    (1) NUNCA bloquea el hilo principal — cada consulta/movimiento a
    `pactl` corre por `QProcess` (asíncrono, con señal `finished`) y
    cada reintento se agenda con `QTimer.singleShot()`, jamás
    `subprocess.run()`/`time.sleep()` síncronos. Antes, CADA
    reproducción (tema, tanda, cortina, Pisador, previo, clip de HTH)
    podía congelar la app entera —botones, timers, avance
    automático, medidor de nivel— durante hasta ~1.2s por reintento,
    en el peor caso varios segundos si `pactl`/PipeWire respondía
    lento, o más todavía si varias reproducciones lo disparaban
    seguidas (los bloqueos se sumaban, uno detrás del otro, todo en
    el mismo hilo).

    (2) NUNCA puede confundir a qué reproducción pertenece un stream
    nuevo — el mecanismo viejo comparaba una foto de
    `pactl list sink-inputs` de ANTES contra la de DESPUÉS y asumía
    que "el que apareció nuevo" era el propio; si DOS reproducciones
    arrancaban casi al mismo tiempo (el crossfade de Ventana 2 usa
    DOS motores en paralelo a propósito, el Pisador es un segundo
    motor, y sobre todo: previsualizar algo en el Explorador mientras
    algo cambia al aire, un flujo de trabajo constante), no había
    forma de saber cuál "nuevo" le pertenecía a cuál — podía terminar
    moviendo el stream de la Preescucha al sink del aire, o viceversa.
    Acá se SERIALIZA: solo hay UN pedido "cazando su propio stream
    nuevo" activo a la vez en TODA la app — la foto de "qué ya
    existía" se toma recién cuando le toca el turno a ESE pedido
    puntual, `MotorAudio.play()` se dispara SOLO después de tener esa
    foto (nunca antes), y solo entonces se busca qué apareció — así
    cualquier stream nuevo que se encuentre durante esa ventana
    SIEMPRE es el correcto, sin importar cuántas otras reproducciones
    estén encoladas esperando su turno. El costo real: si dos
    reproducciones piden ruta casi juntas, la segunda espera a que la
    primera quede confirmada (normalmente milisegundos, como mucho un
    par de segundos si `pactl` responde lento) antes de arrancar de
    verdad — un retraso acotado y siempre mejor que el aire
    silenciado o cruzado.

    (3) Bug real corregido tras un reporte de campo (Santiago: la
    rotativa de Ventana 1 sonaba intermitente y el ítem 1 de Ventana 2
    no salía al aire tras el pase automático, ni reiniciando la app
    entera -- y ni siquiera podía correr `pactl` a mano, "traba la
    barra del explorador de q4os"): ninguna de las dos llamadas a
    `pactl` (`_listar_sink_inputs`/`_mover`) tenía NINGÚN timeout --
    si PipeWire quedaba colgado/degradado (el mismo estado que hace
    que un `pactl` manual tampoco responda, y que puede colgar
    cualquier otro elemento del escritorio que hable con PipeWire,
    como la barra de tareas de TDE), el `QProcess.finished` de ESE
    pedido puntual NUNCA se disparaba -- `self._procesando` quedaba
    en `True` para siempre, y la cola ENTERA de rutas pendientes
    (cualquier reproducción futura, en cualquier ventana) se
    bloqueaba de por vida, sin ningún error visible más que la
    música/publicidad que simplemente no llega a sonar. Como el
    problema vive en PipeWire, no en el proceso de Python, ni
    siquiera reiniciar la app lo resolvía -- el `EnrutadorPactl`
    nuevo volvía a intentar `pactl` contra el mismo PipeWire colgado
    y se trababa de nuevo. Corregido con un timeout duro
    (`TIMEOUT_PROCESO_MS`) sobre CADA invocación de `pactl`: si no
    responde a tiempo, se mata el proceso (`kill()`) y se lo trata
    como una respuesta vacía/fallida -- el job sigue su curso normal
    de reintentos (o se da por vencido tras `MAX_INTENTOS`, dejando
    sonar igual el ítem sin re-rutear, en vez de silenciar la cola
    entera para siempre). Esto NO arregla un PipeWire genuinamente
    colgado a nivel del sistema operativo (eso requiere reiniciar
    PipeWire/la PC), pero evita que un solo `pactl` colgado deje a
    esta app entera muda de por vida hasta el próximo reinicio.

    (4) Bug real corregido tras otro reporte de campo (Santiago: la
    operadora reintentó una cortina que no escuchaba 8 veces seguidas
    en el Auxiliar en ~20 minutos; eso backlogueó la cola compartida
    lo suficiente como para que una cortina REAL del aire tardara 3.8s
    en sonar, y dos pedidos se dieran por vencidos del todo): un
    pedido cuya reproducción de origen ya fue cancelada/superada (Stop,
    o un Play nuevo sobre el mismo motor) antes de que este job
    encontrara su sink-input igual agotaba sus `MAX_INTENTOS`
    completos buscando un stream que NUNCA iba a aparecer -- el propio
    `play()` real nunca se disparó para esa reproducción vieja, así
    que la búsqueda estaba condenada de entrada. Corregido con el
    parámetro `sigue_vigente` de `reclamar()`: se chequea antes de
    arrancar la búsqueda Y en cada reintento -- un pedido que se volvió
    obsoleto se da por terminado DE INMEDIATO, sin agotar el resto de
    sus intentos, dejando pasar al próximo de la cola sin demora.
    Con esto, una racha de clicks repetidos (por más frustrante que
    sea para quien la hace) ya no puede backloguear el aire real
    detrás suyo.

    (5) Camino rápido — enrutado directo VERIFICADO, sin mover nada a
    mano cuando no hace falta (pedido explícito, "más simple y
    rápido... reestructurar", confirmado con una prueba real en la
    PC de aire): `_es_nombre_pactl_directo()` seguía asumiendo que
    libVLC NUNCA puede apuntar directo a un sink escrito a mano (el
    motivo original de esta clase entera) — pero una prueba real,
    hecha DESDE LA SESIÓN FÍSICA (la que usa la radio en producción,
    nunca una sesión remota de Chrome Remote Desktop — ver más abajo
    por qué eso importa), confirmó que `audio_output_device_set(None,
    sink)` SÍ enruta bien, de una, incluso a un sink dinámico creado
    en caliente por otro programa (el caso real: el sink de
    Viper4Linux). Lo que fallaba en instalaciones viejas no era la
    llamada en sí, sino no tener forma de CONFIRMARLA — así que en vez
    de sacar el mecanismo de respaldo (sería apostar la radio en vivo
    a un solo dato), ahora se VERIFICA: apenas aparece el sink-input
    nuevo, si YA está en el sink correcto (porque el enrutado directo
    de libVLC ya lo dejó ahí), se da el pedido por terminado DE UNA —
    sin ningún `pactl move-sink-input` de más. Solo si el sink-input
    nuevo aparece en OTRO sink (el enrutado directo no llegó a tiempo,
    o esta instalación puntual todavía no lo soporta) se cae al
    mecanismo de siempre (`_mover()`, forzar la reubicación a mano) —
    exactamente como antes, sin perder nada de la robustez ya
    probada. Importante: la MISMA prueba, corrida desde la sesión
    VIRTUAL de Chrome Remote Desktop en vez de la física, dio un
    resultado distinto (el stream terminó en el sink de esa sesión
    remota, no en el pedido) — otra razón más para que la radio SIEMPRE
    corra en la sesión física (ya forzado desde otra ronda, ver
    `core/sesion_display.py`)."""

    MAX_INTENTOS = 20
    ESPERA_REINTENTO_MS = 150
    # Tope duro por invocación de `pactl` -- ver punto (3) más arriba.
    # Un `pactl` sano responde en milisegundos; 3s ya es una demora
    # anormal (PipeWire degradado/colgado), y esperar más solo demora
    # la detección sin ganar nada.
    TIMEOUT_PROCESO_MS = 3000

    def __init__(self):
        super().__init__()
        self._cola = []
        self._procesando = False

    def reclamar(self, nombre_sink: str, al_listo_para_reproducir, sigue_vigente=None):
        """Encola un pedido para el sink `nombre_sink`. Cuando le
        toca el turno (nunca antes de que el pedido anterior haya
        terminado), toma la foto de "qué ya existía" y RECIÉN AHÍ
        llama a `al_listo_para_reproducir()` — es responsabilidad de
        quien llama hacer el `self._player.play()` real DENTRO de ese
        callback, nunca antes de encolar.

        `sigue_vigente` (pedido explícito, "arreglá eso del hueco real
        y concreto, para que no vuelva a fallar" — bug real de campo,
        una racha de clicks Play/Stop repetidos en el Auxiliar
        backlogueó la cola entera y demoró una cortina REAL del aire
        3.8s): callable opcional que devuelve `False` el día que ESTE
        pedido puntual ya no tiene sentido perseguir (la reproducción
        que lo generó fue cancelada/superada por otra más nueva en el
        mismo motor — ver `MotorAudio.reproducir()`, que pasa una
        comprobación de generación). Sin esto, un pedido obsoleto
        igual agotaba sus `MAX_INTENTOS` completos buscando un
        sink-input que NUNCA iba a aparecer (porque `al_listo_para_
        reproducir()` nunca llega a llamar `play()` para una
        reproducción ya superada) — hasta varios segundos por pedido
        fantasma, bloqueando a TODA la cola compartida (Master Y
        Preescucha) detrás suyo. Ahora se chequea DOS VECES: antes de
        invocar `al_listo_para_reproducir()` (si ya nació obsoleto
        mientras esperaba su turno, ni se llama) y en cada vuelta de
        `_al_buscar_stream_nuevo()` (si se volvió obsoleto A MITAD de
        la búsqueda) — en cualquiera de los dos casos se da por
        terminado DE INMEDIATO, sin gastar el resto de los intentos.
        `None` (default) equivale a "siempre vigente", para no romper
        ningún llamador que no necesite esto."""
        self._cola.append({
            "sink": nombre_sink, "al_listo": al_listo_para_reproducir,
            "sigue_vigente": sigue_vigente or (lambda: True),
            "intento": 0, "ids_previos": None,
        })
        self._procesar_siguiente_si_libre()

    def _procesar_siguiente_si_libre(self):
        if self._procesando or not self._cola:
            return
        self._procesando = True
        self._listar_sink_inputs(self._al_tener_snapshot_inicial)

    def _ejecutar_pactl_con_timeout(self, argumentos: list, callback_salida):
        """Corre `pactl argumentos` async, con un watchdog de
        `TIMEOUT_PROCESO_MS` -- si no responde a tiempo, lo mata y
        llama `callback_salida(None)` (nunca `""`, que es una salida
        vacía LEGÍTIMA) en vez de dejar la cola trabada para siempre
        (ver punto (3) del docstring de la clase)."""
        proceso = QProcess(self)
        estado = {"resuelto": False}

        def resolver(salida: str):
            if estado["resuelto"]:
                return
            estado["resuelto"] = True
            callback_salida(salida)

        def al_terminar(*_args):
            salida = bytes(proceso.readAllStandardOutput()).decode("utf-8", errors="ignore")
            proceso.deleteLater()
            resolver(salida)

        def al_agotarse_tiempo():
            if estado["resuelto"]:
                return
            registrar_evento(
                f"MotorAudio: EnrutadorPactl -- 'pactl {' '.join(argumentos)}' "
                f"no respondió en {self.TIMEOUT_PROCESO_MS}ms (PipeWire "
                f"colgado/degradado?) -- se mata el proceso y se sigue "
                f"con el próximo reintento"
            )
            try:
                proceso.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            proceso.kill()
            proceso.deleteLater()
            resolver(None)

        proceso.finished.connect(al_terminar)
        QTimer.singleShot(self.TIMEOUT_PROCESO_MS, al_agotarse_tiempo)
        proceso.start("pactl", argumentos)

    def _listar_sink_inputs(self, callback):
        """Devuelve al callback un dict `{id_sink_input: id_sink}` —
        antes solo se guardaba el índice (un `set`), pero desde el
        camino rápido del punto (5) hace falta saber a QUÉ SINK está
        atado cada sink-input, para poder confirmar sin ambigüedad si
        uno nuevo ya aterrizó en el destino correcto."""
        def al_tener_salida(salida):
            sink_inputs = {}
            for linea in (salida or "").splitlines():
                if not linea.strip():
                    continue
                columnas = linea.split("\t")
                if len(columnas) < 2:
                    continue
                sink_inputs[columnas[0].strip()] = columnas[1].strip()
            callback(sink_inputs)

        self._ejecutar_pactl_con_timeout(["list", "sink-inputs", "short"], al_tener_salida)

    def _al_tener_snapshot_inicial(self, sink_inputs_previos: dict):
        job = self._cola[0]

        # Chequeo #1 de "sigue_vigente" -- este pedido pudo haber
        # pasado un buen rato esperando su turno en la cola (detrás de
        # otros), y en ese tiempo la reproducción que lo originó puede
        # haber sido cancelada/superada por otra más nueva en el mismo
        # motor. Si ya nació obsoleto, ni siquiera vale la pena
        # llamar a `al_listo()` (sería un play() que el propio motor
        # va a descartar solo por generación) ni tomar una foto de
        # sink-inputs para nada -- se da por terminado YA, dejando
        # pasar al próximo pedido de la cola de inmediato.
        if not job["sigue_vigente"]():
            self._terminar_job_actual()
            return

        job["sink_inputs_previos"] = sink_inputs_previos
        # Recién ACÁ arranca la reproducción real -- con la foto de
        # "antes" ya en mano, cualquier sink-input nuevo que aparezca
        # de acá en más pertenece SIN AMBIGÜEDAD a este pedido, porque
        # ningún otro pedido de la cola puede estar reproduciendo
        # todavía (están esperando su turno). `al_listo()` es quien
        # llama a `self._player.play()`, y DENTRO de esa misma llamada
        # el motor ya intenta el enrutado DIRECTO
        # (`audio_output_device_set(None, sink)`, ver
        # `_aplicar_dispositivo_salida()`) -- acá solo queda
        # CONFIRMARLO, ver `_al_verificar_enrutado()`.
        job["al_listo"]()
        self._listar_sink_inputs(self._al_verificar_enrutado)

    def _al_verificar_enrutado(self, sink_inputs_actuales: dict):
        job = self._cola[0]

        # Chequeo #2 -- acá el pedido YA arrancó a buscar (ver arriba),
        # pero puede volverse obsoleto A MITAD de la búsqueda (ej. un
        # Stop/Cut, o un Play nuevo sobre el mismo motor, mientras
        # todavía estábamos esperando que aparezca el sink-input). Bug
        # real corregido acá, reporte de campo: una racha de clicks
        # Play/Stop repetidos (el operador reintentando porque no
        # escuchaba nada) hacía que CADA pedido superado agotara sus
        # MAX_INTENTOS completos —hasta varios segundos— buscando un
        # sink-input que nunca iba a aparecer (el play() real nunca
        # llegó a dispararse para esa reproducción vieja), backlogueando
        # la cola COMPARTIDA (Master y Preescucha juntos) detrás suyo —
        # confirmado en un log real: una cortina legítima tardó 3.8s en
        # sonar de verdad por este motivo. Cortar acá, apenas se detecta,
        # es lo que evita que una racha de clicks demore el aire real.
        if not job["sigue_vigente"]():
            self._terminar_job_actual()
            return

        anteriores = job["sink_inputs_previos"]
        nuevos = {sid: sink for sid, sink in sink_inputs_actuales.items() if sid and sid not in anteriores}

        if not nuevos:
            job["intento"] += 1
            if job["intento"] >= self.MAX_INTENTOS:
                registrar_evento(
                    f"MotorAudio: EnrutadorPactl no encontró ningún sink-input "
                    f"nuevo tras {job['intento']} intentos (target: '{job['sink']}')"
                )
                self._terminar_job_actual()
                return
            QTimer.singleShot(self.ESPERA_REINTENTO_MS, lambda: self._listar_sink_inputs(self._al_verificar_enrutado))
            return

        # Camino RÁPIDO (punto (5) del docstring de la clase): si
        # alguno de los sink-inputs nuevos YA está en el sink que
        # pedimos, es que el enrutado DIRECTO de libVLC
        # (`audio_output_device_set(None, ...)`, aplicado dentro de
        # `al_listo()` un poco más arriba) ya lo dejó bien solo -- no
        # hace falta ningún `pactl move-sink-input` de más, se termina
        # el pedido YA.
        id_ya_en_destino = next((sid for sid, sink in nuevos.items() if sink == job["sink"]), None)
        if id_ya_en_destino is not None:
            self._terminar_job_actual()
            return

        # Ninguno de los nuevos está en el sink correcto todavía --
        # Camino de RESPALDO, el de siempre: se toma el primero que
        # apareció (sigue siendo el ÚNICO pedido "cazando su stream
        # nuevo" en toda la app -- serializado, sin ambigüedad de a
        # quién pertenece) y se lo mueve a mano.
        id_cualquiera = next(iter(nuevos))
        self._mover(id_cualquiera, job["sink"])

    def _mover(self, id_stream: str, nombre_sink: str):
        """Camino de RESPALDO (ver punto (5) del docstring de la
        clase) -- solo se llega acá si el enrutado DIRECTO de libVLC
        no dejó el stream en el sink correcto a tiempo. Antes esto era
        el ÚNICO camino posible; ahora es la red de seguridad."""
        def al_terminar(salida):
            # `salida` es `None` únicamente si el watchdog de
            # `_ejecutar_pactl_con_timeout` mató el proceso por
            # colgado -- ahí NO hubo movimiento real, así que no hay
            # que registrarlo como éxito (aunque sea, igual, mejor
            # seguir con la cola que dejarla trabada para siempre).
            if salida is not None:
                registrar_evento(
                    f"MotorAudio: movido sink-input {id_stream} -> '{nombre_sink}' "
                    f"vía pactl (respaldo -- el enrutado directo no llegó a tiempo, "
                    f"serializado)"
                )
            self._terminar_job_actual()

        self._ejecutar_pactl_con_timeout(["move-sink-input", id_stream, nombre_sink], al_terminar)

    def _terminar_job_actual(self):
        if self._cola:
            self._cola.pop(0)
        self._procesando = False
        self._procesar_siguiente_si_libre()


_instancia_enrutador_pactl = None


def _enrutador_pactl() -> EnrutadorPactl:
    """Singleton perezoso -- se crea recién al primer uso real, ya con
    QApplication corriendo (nunca antes, un QObject con QTimer/QProcess
    necesita el event loop de Qt ya activo)."""
    global _instancia_enrutador_pactl
    if _instancia_enrutador_pactl is None:
        _instancia_enrutador_pactl = EnrutadorPactl()
    return _instancia_enrutador_pactl

MENSAJE_VLC_NO_DISPONIBLE = (
    "VLC no está instalado o no se encontró libvlc. "
    "Instalalo con: sudo apt install vlc libvlc-dev"
)

# Defaults si config_general.json todavía no tiene estas claves
# (instalación vieja) — ver config/settings.py:CONFIG_POR_DEFECTO["reproduccion"].
BUFFER_CACHING_MS_POR_DEFECTO = 1000
RETARDO_ARRANQUE_MS_POR_DEFECTO = 150

# Piso mínimo (defensivo, segunda capa) para la ventana reproducible
# punto_fin_ms - punto_inicio_ms -- ver el guard en reproducir() y la
# corrección de fondo real en core/analizador_audio.py:
# VENTANA_MINIMA_REPRODUCIBLE_MS (mucho más generoso, 3000ms). Este
# valor acá es a propósito CHICO: solo atrapa casos claramente rotos
# (datos viejos/corruptos), nunca cuestiona un recorte legítimo que ya
# pasó por esa capa.
VENTANA_MINIMA_SEGURA_MS = 500

# Diagnóstico de silencios reales al aire (pedido explícito, tras un
# reporte real: "encuentro un silencio largo cuando terminó el bloque
# del automático de las 19"). Ninguna señal existente medía esto de
# forma directa -- ver reproducir()/_arrancar_reproduccion_real() más
# abajo: cuando la Salida configurada es un nombre de sink de pactl
# (el caso real de Santiago, sin el módulo "pulse" en su libVLC), el
# play() de verdad queda diferido a que EnrutadorPactl le dé su turno
# en la cola serializada -- si esa cola está congestionada (varias
# reproducciones casi simultáneas en CUALQUIER ventana, ya que el
# enrutador es un singleton compartido por toda la app) o `pactl`
# responde lento, el audio puede tardar bastante más que lo esperado
# en arrancar de verdad, sin que ningún otro mecanismo lo deje
# registrado. Un umbral de 1.5s ya es un corte perceptible al aire —
# por debajo de eso ni vale la pena loguear (ruido).
UMBRAL_DEMORA_REPRODUCCION_SOSPECHOSA_SEGUNDOS = 1.5


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
        # Ganancia (dB) del ítem que está sonando AHORA MISMO -- la que
        # ya se calculó UNA vez al importar/analizar ese archivo
        # (nivelado por loudness, ronda 94). Bug real corregido
        # ("guardar Configuración pisa la ganancia del ítem en curso"):
        # antes, quien quería actualizar el Volumen Master en caliente
        # (ej. al guardar Configuración) llamaba set_volumen(volumen_base)
        # directo, con el volumen CRUDO -- perdía el ajuste propio del
        # ítem que estaba sonando en ESE momento. Ahora se recuerda acá
        # (ver reproducir()) para que actualizar_volumen_base() pueda
        # recalcular el volumen final SIN perder ese ajuste.
        self._ganancia_db_actual = 0.0
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

        # Red de seguridad — segunda capa, nunca confiar en una sola
        # (mismo criterio de siempre en este archivo): si
        # punto_inicio_ms/punto_fin_ms llegan con una ventana
        # reproducible sospechosamente chica (bug real: "los
        # separadores y artísticas hay veces que no las reproduce...
        # el siguiente tampoco" — ver VENTANA_MINIMA_REPRODUCIBLE_MS en
        # core/analizador_audio.py, la corrección de fondo), sin
        # importar de dónde vinieron esos valores (análisis roto, o un
        # dato VIEJO en biblioteca.json calculado antes de ese fix —
        # esto no es retroactivo hasta que se reanalice), se ignoran y
        # se reproduce el archivo completo en vez de arriesgar una
        # reproducción casi instantánea que se lea como "no reprodujo
        # nada". Un umbral chico a propósito (VENTANA_MINIMA_SEGURA_MS,
        # muy por debajo del piso real de analizador_audio.py): acá
        # solo se atrapan casos claramente rotos, nunca se segunda-
        # adivina un recorte legítimo ya validado por esa capa.
        if punto_fin_ms is not None and (punto_fin_ms - punto_inicio_ms) < VENTANA_MINIMA_SEGURA_MS:
            punto_inicio_ms = 0
            punto_fin_ms = None

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

        # Bug real corregido — "se corta la música como cuando saltaban
        # los CDs... una cortina se reproduce pero sin audio... lo que
        # tiro en previo vuelve a salir al aire" (reporte real de la
        # operadora): el mecanismo viejo tomaba la foto de "qué ya
        # existía" y llamaba a play() TODO en el mismo instante
        # síncrono, así que el pedido a `EnrutadorPactl` (que corre
        # play() recién cuando tiene su propia foto confirmada, sin
        # pisarse con otra reproducción que arranque casi al mismo
        # tiempo) es quien decide CUÁNDO dispara el player.play() real
        # — ver `_arrancar_reproduccion_real()` más abajo. Con un
        # dispositivo normal (id de módulo de libVLC, o "default") el
        # comportamiento es IDÉNTICO a como era antes: arranca ya
        # mismo, sin ninguna cola de por medio.
        momento_pedido_reproducir = time.monotonic()

        def _arrancar_reproduccion_real():
            if self._generacion_reproduccion != generacion_de_esta_reproduccion:
                return  # una reproducción MÁS NUEVA ya canceló esta (ver más abajo)
            # Diagnóstico de silencios reales al aire (ver constante
            # UMBRAL_DEMORA_REPRODUCCION_SOSPECHOSA_SEGUNDOS más arriba)
            # -- mide cuánto tardó ESTE play() en dispararse de verdad
            # desde que se pidió reproducir(), sin importar si quedó
            # diferido por EnrutadorPactl (cola congestionada, pactl
            # lento) o arrancó ya mismo (dispositivo normal, cola
            # libre). Nunca se dispara para una demora chica/normal.
            demora_segundos = time.monotonic() - momento_pedido_reproducir
            if demora_segundos > UMBRAL_DEMORA_REPRODUCCION_SOSPECHOSA_SEGUNDOS:
                registrar_evento(
                    f"MotorAudio: '{self._ruta_actual}' tardó {demora_segundos:.1f}s en "
                    f"arrancar a sonar de verdad desde que se pidió reproducir() -- "
                    f"posible corte de audio real al aire (ver EnrutadorPactl, cola de enrutado)"
                )
            self._player.play()
            self._timer_posicion.start()

            # Re-aplica el dispositivo de salida elegido — ver
            # _aplicar_dispositivo_salida(): el stop() de arriba desarma
            # la salida de audio, así que la selección hecha en
            # Configuración se pierde si no se refuerza acá en cada
            # arranque.
            self._aplicar_dispositivo_salida()

            self._ganancia_db_actual = ganancia_db
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

        # Ver _es_nombre_pactl_directo()/EnrutadorPactl más arriba —
        # NUNCA bloquea el hilo principal, y serializa para que dos
        # reproducciones que arrancan casi juntas nunca se confundan
        # sobre cuál sink-input le pertenece a cuál.
        if _es_nombre_pactl_directo(self._id_dispositivo):
            _enrutador_pactl().reclamar(
                self._id_dispositivo, _arrancar_reproduccion_real,
                sigue_vigente=lambda: self._generacion_reproduccion == generacion_de_esta_reproduccion,
            )
        else:
            _arrancar_reproduccion_real()

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
        # Invalida cualquier play() que hubiera quedado ENCOLADO
        # esperando su turno en EnrutadorPactl (dispositivo de salida
        # por pactl directo) sin haber arrancado a sonar todavía —
        # sin este bump, un Stop/Cut mientras ese pedido sigue en
        # cola no lo cancelaba de verdad: el play() diferido terminaba
        # arrancando igual un rato después, resucitando una
        # reproducción que el operador ya había cortado a mano. Mismo
        # mecanismo ya usado para invalidar el diferido de
        # `_tras_arranque()` -- acá se extiende a `reproducir()`
        # entero, no solo a su remate.
        self._generacion_reproduccion += 1

    def liberar(self):
        """Libera de forma DETERMINÍSTICA los recursos de libVLC de
        este motor -- nunca depender de que el ciclo de referencias
        Python (self -> self._player -> event_manager -> callback ->
        self, creado por `event_attach()` en `__init__`) se recolecte
        solo vía el recolector cíclico de Python, que puede tardar
        mucho bajo carga liviana de asignación de memoria (un
        QObject/vlc.Instance pesa poco en el heap de Python, aunque
        mantenga abierta una conexión de cliente PipeWire/ALSA real).

        Bug real de producción, encontrado con el log real de una
        jornada COMPLETA de Santiago: cada crossfade NATURAL de
        Ventana 2 (`core/gestor_emision.py:_iniciar_crossfade()`) crea
        un `MotorAudio` NUEVO (`vlc.Instance()` propio) para el ítem
        entrante y abandona el saliente con solo `self.
        _motor_saliente_crossfade = None` -- sin liberar nada. A lo
        largo de un día real de emisión (un crossfade cada pocos
        minutos, muchas horas seguidas), decenas/cientos de esas
        instancias quedaban "vivas" en memoria (con su conexión de
        audio subyacente todavía abierta) esperando una pasada del GC
        cíclico que podía demorar arbitrariamente. Encaja exacto con
        el patrón real observado: `EnrutadorPactl` (ver más arriba)
        empezó a fallar cada vez más seguido a medida que avanzaba el
        día ("no encontró ningún sink-input nuevo tras 20 intentos"),
        hasta fallar CASI SIEMPRE ya entrada la noche -- y volvió a la
        normalidad de inmediato tras reiniciar el proceso completo
        (que fuerza al sistema operativo a cerrar TODAS las conexiones
        de audio de ese proceso de una sola vez, sin depender de
        ningún GC de Python). Esta función cierra esa ventana: se
        llama sobre el motor SALIENTE de un crossfade justo cuando ya
        terminó de fundirse y no hace falta para nada más (`core/
        gestor_emision.py`: `_liberar_crossfade()` y `detener()`).

        Segura de llamar más de una vez, o sobre un motor que nunca
        llegó a inicializar libVLC (degradado desde el arranque).

        Bug real de fondo, encontrado releyendo este mismo método con
        Santiago tras confirmar con un log real que la fuga SEGUÍA
        pasando pese a este fix: acá abajo nunca se llamaba
        `event_manager().event_detach(...)` de los dos eventos
        adjuntados en `__init__` -- `player.release()` baja el
        contador de libVLC, pero el `EventManager` de python-vlc
        guarda el callback (`self._on_fin_reproduccion`/`_on_error`,
        métodos LIGADOS a esta misma instancia) en su propio dict
        interno (`self._callbacks`), colgado del player -- el ciclo
        real es `self -> self._player -> event_manager -> _callbacks[k]
        -> método ligado -> self`. Un ciclo así NUNCA se rompe por
        conteo de referencias simple, sin importar cuántos `release()`
        se llamen -- hace falta el recolector CÍCLICO de Python, que
        no tiene un momento fijo (corre según umbrales de asignación
        de memoria) y en una app de radio de bajo churn puede tardar
        mucho más de lo que tarda en acumularse una fuga real.
        `event_detach()` (confirmado en el propio código de python-vlc)
        hace `del self._callbacks[k]` -- corta el ciclo A MANO, en el
        instante exacto, sin depender de ningún GC."""
        if self._timer_posicion is not None:
            self._timer_posicion.stop()
        if self._timer_fade_volumen is not None:
            self._timer_fade_volumen.stop()
            self._timer_fade_volumen = None
        if self._player is not None:
            try:
                eventos = self._player.event_manager()
                eventos.event_detach(vlc.EventType.MediaPlayerEndReached)
                eventos.event_detach(vlc.EventType.MediaPlayerEncounteredError)
            except Exception:
                pass
            try:
                self._player.stop()
            except Exception:
                pass
            try:
                self._player.release()
            except Exception:
                pass
            self._player = None
        if self._instancia is not None:
            try:
                self._instancia.release()
            except Exception:
                pass
            self._instancia = None
        self._disponible = False

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

    def ganancia_db_actual(self) -> float:
        """La ganancia (dB) del ítem que está sonando ahora mismo —
        calculada UNA sola vez al importar/analizar ese archivo
        (nivelado por loudness). Ver actualizar_volumen_base()."""
        return self._ganancia_db_actual

    def actualizar_volumen_base(self, volumen_base: int):
        """Pedido explícito ("corregí el bug puntual que guardar
        configuración no pise la ganancia"): a diferencia de
        set_volumen() (fija un volumen 0-100 CRUDO, sin nivelar), este
        método recalcula el volumen FINAL del ítem que está sonando
        ahora mismo usando SU ganancia ya calculada
        (ganancia_db_actual()) sobre el volumen base NUEVO — así
        cambiar el Volumen Master desde Configuración (por cualquier
        motivo, aunque no tenga nada que ver con audio — ej. cambiar
        el tamaño de letra) nunca vuelve a pisar/perder el nivelado
        del ítem en curso. Quien necesite fijar un volumen crudo sin
        nivelar (ej. el ducking del Pisador, que ya calcula su propio
        volumen final) sigue usando set_volumen() directo."""
        from core.analizador_audio import volumen_ajustado_por_ganancia
        self.set_volumen(volumen_ajustado_por_ganancia(volumen_base, self._ganancia_db_actual))

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


def listar_dispositivos_pactl():
    """[(nombre_sink, descripcion), ...] leído directo de `pactl list
    sinks` — reemplaza la enumeración vía libVLC
    (`audio_output_list_get()`), que en instalaciones sin módulo
    "pulse" compilado (confirmado en una PC real) devuelve una lista
    interminable de variantes ALSA (hw/plughw/dmix/dsnoop/surround
    2.1-7.1, una por cada tarjeta) que además NO enrutan de verdad —
    pedido explícito: "no quiero la lista interminable de salidas...
    modificá para que tome las mismas salidas que veo en KMix".

    `pactl` es la MISMA fuente de verdad que ya usa KMix (y
    Viper4Linux) — el nombre de sink que devuelve acá NUNCA tiene el
    separador "||" que usaba el formato viejo, así que activa SIEMPRE
    el fallback de `EnrutadorPactl` al reproducir (ver
    `_es_nombre_pactl_directo`) — cualquier opción de esta lista nueva
    enruta de forma confiable, no solo la escrita a mano."""
    try:
        salida = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=3,
        )
        if salida.returncode != 0:
            return []
    except Exception:
        return []

    dispositivos = []
    nombre_actual = None
    for linea in salida.stdout.splitlines():
        linea_limpia = linea.strip()
        if linea_limpia.startswith("Name:"):
            nombre_actual = linea_limpia.split(":", 1)[1].strip()
        elif linea_limpia.startswith("Description:") and nombre_actual:
            descripcion = linea_limpia.split(":", 1)[1].strip()
            dispositivos.append((nombre_actual, descripcion))
            nombre_actual = None
    return dispositivos


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
    _dispositivos = listar_dispositivos_pactl()
    print(_json.dumps(_dispositivos))


def contar_descriptores_y_pulseaudio() -> tuple:
    """Diagnóstico de la fuga real de audio investigada con Santiago
    (log de producción real, ronda de "EnrutadorPactl no encontró
    ningún sink-input nuevo"): antes había que pedirle que corriera a
    mano `ls /proc/<pid>/fd | wc -l` (y mirar cuántos son
    `memfd:pulseaudio (deleted)`) por Chrome Remote Desktop cada vez
    que algo se sentía raro. Pedido explícito: "que el log también
    registre todos esos números, así me ahorra correr el comando".

    Devuelve (total_descriptores, conexiones_pulseaudio) leyendo
    `/proc/self/fd` DIRECTO desde este mismo proceso -- sin
    `subprocess`, sin `pactl`, sin nada que pueda colgarse (mismo
    criterio de la ronda anterior: nunca competir con o repetir el
    riesgo que `EnrutadorPactl` ya tuvo que blindar con un timeout).
    Devuelve (-1, -1) si `/proc` no está disponible (no debería pasar
    en Linux, pero nunca hay que asumirlo)."""
    try:
        entradas = os.listdir("/proc/self/fd")
    except OSError:
        return -1, -1
    total = len(entradas)
    conexiones_pulseaudio = 0
    for entrada in entradas:
        try:
            destino = os.readlink(f"/proc/self/fd/{entrada}")
        except OSError:
            continue
        if "pulseaudio" in destino:
            conexiones_pulseaudio += 1
    return total, conexiones_pulseaudio


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
