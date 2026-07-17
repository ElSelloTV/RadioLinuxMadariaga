"""
core/easyeffects_control.py
--------------------------------------------------------
Integración con EasyEffects (host de plugins LV2/PipeWire con
compresor, ecualizador, limitador, etc. — Santiago ya lo usa a mano
para procesar el aire de la FM). Pedido explícito: un botón "FM" en
el toolbar para cambiar de preset sin tener que abrir la ventana de
EasyEffects — la afinación fina de cada plugin sigue haciéndose ahí,
con su propia interfaz; esta app solo dispara comandos de línea de
comandos sobre la instancia YA CORRIENDO, en modo oculto
(`--hide-window`, confirmado en la versión 7.2.3 de Santiago — no
existe flag `--gapplication-service` documentado en esta versión,
pero `--hide-window` cumple la misma función: arranca/activa la
instancia única de EasyEffects sin mostrar su ventana).

Comandos usados (confirmados con `easyeffects --help` en la
instalación real de Santiago, EasyEffects 7.2.3):
    -w, --hide-window       Ocultar la ventana
    -l, --load-preset NAME  Cargar un perfil
    -p, --presets           Mostrar los perfiles disponibles
    -b, --bypass N          1=habilitar, 2=deshabilitar, 3=estado
    -s, --active-preset CAT Categoría "input"/"output" (el ejemplo
                             de la ayuda usa el valor en inglés,
                             aunque la descripción esté traducida)
    -q, --quit               Cerrar

Pedido explícito ("debe ser tolerante a actualizaciones, sino con la
primera actualización perdería el acceso"): los flags viven como
constantes acá arriba, para que un cambio de EasyEffects en el futuro
sea un edit de una línea; y CADA llamada está envuelta en try/except,
nunca deja pasar una excepción sin atrapar — si el binario no existe,
si EasyEffects tarda en responder, o si algún flag cambiara de nombre
en una versión futura, esto degrada limpio (mensaje claro para
mostrar en la UI) en vez de romper la aplicación. Mismo patrón que
core/actualizador.py (subprocess.run con timeout, try/except
(TimeoutExpired, OSError), devuelve (éxito: bool, mensaje: str)).

GApplication (single-instance) — por qué el arranque necesita ser
DETACHED y no bloqueante: si EasyEffects todavía no está corriendo,
la PRIMERA invocación de `easyeffects` se convierte en la instancia
"primaria" y se queda corriendo indefinidamente (no vuelve la
terminal) — bloquearía subprocess.run() para siempre. Por eso
asegurar_en_ejecucion() lanza el proceso DESACOPLADO
(QProcess.startDetached) y sondea con `pgrep` (no depende de ningún
flag propio de EasyEffects, así que es más tolerante a cambios de
versión) hasta confirmar que ya quedó arriba, antes de dejar que
cualquier otro comando (que sí espera una respuesta rápida) se envíe.
--------------------------------------------------------
"""

import os
import shutil
import subprocess
import time

from config.settings import registrar_error, registrar_evento, DIRECTORIO_CONFIG

NOMBRE_BINARIO = "easyeffects"

# Bug real reportado ("se abre EasyEffects pero se cierra... no me
# deja activar el preset"): el sondeo de 2 fases (ver más abajo) ya
# detecta CUÁNDO falla, pero hasta ahora no había forma de ver POR QUÉ
# — el lanzamiento usaba QProcess.startDetached(), que no permite
# redirigir stdout/stderr del proceso hijo, así que si EasyEffects
# crasheaba al arrancar, ese mensaje de error se perdía por completo
# (ni Santiago ni Claude Code podían verlo sin acceso a una terminal
# en el momento exacto del fallo). Ahora el lanzamiento usa
# subprocess.Popen redirigiendo stdout/stderr a este archivo
# (sobrescrito en CADA intento, para que siempre refleje el último
# lanzamiento) — start_new_session=True mantiene el mismo
# comportamiento "independiente de la app" que ya tenía
# QProcess.startDetached() (el proceso sigue vivo aunque se cierre la
# radio). Si el sondeo de 2 fases termina fallando, la cola de este
# archivo se agrega al mensaje de error mostrado en el menú FM y al
# log de la app — el error REAL del sistema queda a la vista sin
# necesitar terminal.
RUTA_LOG_PROCESO = os.path.join(DIRECTORIO_CONFIG, "easyeffects_stdout.txt")

# Flags de la CLI — un solo lugar para actualizar si una versión
# futura de EasyEffects les cambia el nombre (ver nota arriba).
FLAG_OCULTAR_VENTANA = "--hide-window"
FLAG_CARGAR_PRESET = "--load-preset"
FLAG_LISTAR_PRESETS = "--presets"
FLAG_BYPASS = "--bypass"
FLAG_PRESET_ACTIVO = "--active-preset"
FLAG_SALIR = "--quit"
CATEGORIA_SALIDA = "output"   # el ejemplo de `--help` usa el valor en inglés
CATEGORIA_ENTRADA = "input"

TIMEOUT_COMANDO_SEGUNDOS = 5
# Bug real reportado: "se abre EasyEffects pero se cierra... 'no
# respondió al cambiar de preset'" — pgrep detectaba el PROCESO vivo,
# pero eso no garantiza que el servicio D-Bus/GApplication ya esté
# registrado y listo para aceptar comandos remotos (--load-preset,
# etc.). En hardware modesto (Celeron N2820) ese registro puede tardar
# bastante más que los 3s que había antes. Se sube el techo de sondeo
# de proceso Y se agrega una segunda fase que confirma con un comando
# REAL (--presets, de solo lectura) antes de declarar éxito — ver
# asegurar_en_ejecucion().
TIMEOUT_ARRANQUE_SEGUNDOS = 8.0
TIMEOUT_PROBE_CLI_SEGUNDOS = 6.0
INTERVALO_SONDEO_SEGUNDOS = 0.3


def esta_instalado() -> bool:
    return shutil.which(NOMBRE_BINARIO) is not None


def _lanzar_proceso_con_captura(args: list) -> bool:
    """Lanza `easyeffects` DESACOPLADO de esta app (sigue vivo aunque
    se cierre la radio, mismo comportamiento que ya tenía
    QProcess.startDetached), pero redirigiendo su stdout/stderr a
    RUTA_LOG_PROCESO — sobrescrito en cada intento — para poder
    diagnosticar un crash real (ver nota arriba). Devuelve False solo
    si el lanzamiento en sí no pudo iniciarse (binario inexistente,
    permisos, etc.) — nunca lanza excepción."""
    try:
        os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)
        with open(RUTA_LOG_PROCESO, "w", encoding="utf-8", errors="replace") as archivo_log:
            subprocess.Popen(
                [NOMBRE_BINARIO, *args],
                stdout=archivo_log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return True
    except OSError as error:
        registrar_error(f"EasyEffects: no se pudo lanzar el proceso ({args}): {error}")
        return False


def _cola_log_proceso(max_lineas: int = 20) -> str:
    """Últimas líneas de RUTA_LOG_PROCESO — el error REAL del sistema
    (crash, falta de PipeWire, D-Bus, etc.) si el proceso falló al
    arrancar o quedó sin responder. Cadena vacía si no hay nada
    capturado (nunca rompe el flujo por esto)."""
    try:
        with open(RUTA_LOG_PROCESO, "r", encoding="utf-8", errors="replace") as archivo_log:
            lineas = archivo_log.readlines()
        return "".join(lineas[-max_lineas:]).strip()
    except OSError:
        return ""


def _esta_corriendo() -> bool:
    """Vía `pgrep`, no vía ningún flag propio de EasyEffects — más
    tolerante a que un flag cambie de nombre en una actualización."""
    try:
        resultado = subprocess.run(
            ["pgrep", "-x", NOMBRE_BINARIO], capture_output=True, text=True, timeout=3,
        )
        return resultado.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _ejecutar_comando(*args, timeout: float = TIMEOUT_COMANDO_SEGUNDOS):
    """Envía `args` a la instancia YA CORRIENDO de EasyEffects (round
    trip corto vía D-Bus/GApplication). Nunca se debe llamar antes de
    confirmar que hay una instancia arriba (ver asegurar_en_ejecucion) —
    si no, esta invocación se convertiría en la instancia primaria y
    subprocess.run() colgaría hasta el timeout."""
    try:
        return subprocess.run(
            [NOMBRE_BINARIO, *args], capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def _cli_responde() -> bool:
    """Round-trip REAL contra la instancia (no solo "el proceso
    existe" como pgrep) — usa --presets, de solo lectura, como sondeo
    inofensivo. Si esto tiene éxito, cualquier comando posterior
    (cambiar de preset, bypass, etc.) debería funcionar igual."""
    resultado = _ejecutar_comando(FLAG_LISTAR_PRESETS)
    return resultado is not None and resultado.returncode == 0


def _esperar_cli_responda(timeout_segundos: float) -> bool:
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout_segundos:
        if _cli_responde():
            return True
        time.sleep(INTERVALO_SONDEO_SEGUNDOS)
    return False


def asegurar_en_ejecucion() -> tuple[bool, str]:
    """Arranca EasyEffects OCULTO si todavía no está corriendo, o lo
    oculta si ya estaba con la ventana abierta (el operador la abrió
    a mano) — el mismo flag `--hide-window` sirve para las dos cosas.
    No bloquea el arranque en sí (proceso desacoplado); sondea en DOS
    fases antes de declarar éxito:
    1) `pgrep` hasta que el PROCESO esté vivo (arranque en sí).
    2) Un comando REAL de solo lectura (--presets) hasta que la
       instancia responda de verdad — bug real reportado ("se abre
       EasyEffects pero se cierra... no respondió al cambiar de
       preset"): el proceso puede existir un rato antes de que su
       servicio D-Bus/GApplication esté listo para comandos remotos,
       y los comandos posteriores (cambiar de preset, etc.) fallaban
       en esa ventana. Ambas fases quedan en el log de la app para
       poder diagnosticar sin acceso directo a la PC si vuelve a
       fallar."""
    if not esta_instalado():
        return False, (
            "EasyEffects no está instalado en este sistema. "
            "Instalalo con: sudo apt install easyeffects"
        )

    if _esta_corriendo():
        # Ya estaba corriendo — pero "el proceso existe" no es lo
        # mismo que "responde": si estaba a mitad de arrancar o de
        # cerrarse, --hide-window puede fallar en silencio. Se
        # confirma con el mismo sondeo de CLI antes de dar por buena
        # la instancia existente.
        if _cli_responde():
            _ejecutar_comando(FLAG_OCULTAR_VENTANA)
            return True, "EasyEffects ya estaba en ejecución."
        registrar_evento(
            "EasyEffects: proceso detectado (pgrep) pero no respondió al sondeo — esperando..."
        )
        if _esperar_cli_responda(TIMEOUT_PROBE_CLI_SEGUNDOS):
            _ejecutar_comando(FLAG_OCULTAR_VENTANA)
            registrar_evento("EasyEffects: respondió tras esperar.")
            return True, "EasyEffects ya estaba en ejecución."
        registrar_error("EasyEffects: el proceso existe pero nunca respondió a los comandos.")
        return False, "EasyEffects está abierto pero no responde. Probá cerrarlo y volver a intentar."

    if not _lanzar_proceso_con_captura([FLAG_OCULTAR_VENTANA]):
        return False, "No se pudo lanzar EasyEffects."

    if not _esperar_proceso_vivo(TIMEOUT_ARRANQUE_SEGUNDOS):
        cola = _cola_log_proceso()
        registrar_error(
            f"EasyEffects: el proceso no apareció (pgrep) en {TIMEOUT_ARRANQUE_SEGUNDOS}s tras el arranque."
            + (f" Salida capturada:\n{cola}" if cola else "")
        )
        mensaje = "EasyEffects no respondió a tiempo al arrancar."
        return False, mensaje + (f" Detalle: {cola[:300]}" if cola else "")

    if not _esperar_cli_responda(TIMEOUT_PROBE_CLI_SEGUNDOS):
        # El proceso llegó a existir (posiblemente se vio brevemente
        # la ventana, "se abre y se cierra") pero nunca quedó listo
        # para recibir comandos — puede haberse caído solo apenas
        # arrancado. Se adjunta la cola de RUTA_LOG_PROCESO (stdout/
        # stderr real del proceso) — antes esto era invisible porque
        # QProcess.startDetached() no permite capturar la salida del
        # hijo, así que un crash quedaba sin ningún rastro.
        cola = _cola_log_proceso()
        registrar_error(
            "EasyEffects: el proceso arrancó pero nunca respondió a los comandos "
            f"dentro de {TIMEOUT_PROBE_CLI_SEGUNDOS}s (¿se cerró solo justo después de abrir?)."
            + (f" Salida capturada:\n{cola}" if cola else " Sin salida capturada.")
        )
        mensaje = "EasyEffects arrancó pero no llegó a responder."
        return False, mensaje + (f" Detalle: {cola[:300]}" if cola else " Reintentá desde el ícono FM.")

    registrar_evento("EasyEffects: arrancó oculto y respondió correctamente.")
    return True, "EasyEffects arrancó oculto correctamente."


def _esperar_proceso_vivo(timeout_segundos: float) -> bool:
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout_segundos:
        if _esta_corriendo():
            return True
        time.sleep(INTERVALO_SONDEO_SEGUNDOS)
    return False


def listar_presets() -> list[str]:
    """Presets guardados en EasyEffects (salida de `--presets`).
    Lista vacía si EasyEffects no responde o no hay ninguno — nunca
    rompe la UI que la use.

    Bug real reportado por Santiago ("no me deja activar el preset")
    — el log real mostró que se le mandaba a `--load-preset` el
    nombre literal 'Perfiles de salida: Radio Tuyu,' en vez de 'Radio
    Tuyu': en su instalación (EasyEffects 7.2.3, sistema en español),
    `--presets` NO imprime un nombre de preset por línea (la
    suposición original) — imprime UNA LÍNEA POR CATEGORÍA, con los
    nombres separados por coma:
        Perfiles de salida: Radio Tuyu,
        Perfiles de entrada:
    (el encabezado de categoría sale traducido según el idioma del
    sistema — "Output presets:"/"Input presets:" en inglés, etc.).
    Ahora se parsea de forma tolerante al formato: si la línea tiene
    ":", se toma solo lo de DESPUÉS de los dos puntos (sin importar el
    texto de la categoría) y se separa por comas; si no tiene ":", se
    toma la línea entera como un solo nombre (compatibilidad con una
    versión que sí liste un nombre por línea, sin categorías)."""
    resultado = _ejecutar_comando(FLAG_LISTAR_PRESETS)
    if resultado is None or resultado.returncode != 0:
        return []
    presets = []
    for linea in resultado.stdout.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        _, separador, resto = linea.partition(":")
        if separador:
            for nombre in resto.split(","):
                nombre = nombre.strip()
                if nombre:
                    presets.append(nombre)
        else:
            presets.append(linea)
    return presets


def cargar_preset(nombre: str) -> tuple[bool, str]:
    resultado = _ejecutar_comando(FLAG_CARGAR_PRESET, nombre)
    if resultado is None or resultado.returncode != 0:
        # Defensivo (mismo criterio ya usado para libVLC en este
        # proyecto: "nunca confiar en una sola capa de protección"):
        # un solo intento fallido — sea porque no respondió (None) o
        # porque respondió con error (returncode != 0) — puede ser una
        # race transitoria justo después del arranque; un reintento
        # corto suele alcanzar.
        registrar_evento(f"EasyEffects: '{FLAG_CARGAR_PRESET} {nombre}' falló, reintentando una vez...")
        time.sleep(0.5)
        resultado = _ejecutar_comando(FLAG_CARGAR_PRESET, nombre)
    if resultado is None:
        registrar_error(f"EasyEffects: '{FLAG_CARGAR_PRESET} {nombre}' no respondió tras reintentar.")
        return False, "EasyEffects no respondió al cambiar de preset."
    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        registrar_error(f"EasyEffects: no se pudo cargar el preset '{nombre}' tras reintentar: {detalle}")
        return False, f"No se pudo cargar el preset '{nombre}'" + (f": {detalle}" if detalle else ".")
    return True, f"Preset '{nombre}' aplicado."


def preset_activo(categoria: str = CATEGORIA_SALIDA) -> str | None:
    resultado = _ejecutar_comando(FLAG_PRESET_ACTIVO, categoria)
    if resultado is None or resultado.returncode != 0:
        return None
    salida = resultado.stdout.strip()
    return salida or None


def set_bypass(activar: bool) -> tuple[bool, str]:
    resultado = _ejecutar_comando(FLAG_BYPASS, "1" if activar else "2")
    if resultado is None or resultado.returncode != 0:
        return False, "No se pudo cambiar el bypass de EasyEffects."
    return True, ("Bypass activado (efectos apagados)." if activar else "Bypass desactivado (efectos activos).")


def esta_en_bypass() -> bool | None:
    """None si no se pudo determinar (nunca falsea un estado)."""
    resultado = _ejecutar_comando(FLAG_BYPASS, "3")
    if resultado is None or resultado.returncode != 0:
        return None
    salida = resultado.stdout.strip().lower()
    if "true" in salida or salida == "1":
        return True
    if "false" in salida or salida == "0":
        return False
    return None


def abrir_ventana() -> tuple[bool, str]:
    """Muestra la ventana real de EasyEffects para afinar los plugins
    a fondo.

    Bug real reportado ("tampoco abre desde FM EasyEffects (Opciones
    Avanzadas)"): la suposición original — invocar el binario SIN
    --hide-window sobre una instancia YA corriendo oculta activaría
    esa instancia y GApplication presentaría su ventana sola, sin
    hacer falta ningún otro paso — no se cumplió en la práctica (ya
    quedaba documentado como incierto desde que se escribió, nunca
    confirmado). No hay un flag "--show-window" documentado en el
    --help real de Santiago para forzarlo directamente. La única
    forma CONFIABLE de garantizar que la ventana aparezca, sin
    depender de un comportamiento de reactivación no confirmado, es
    cerrar la instancia oculta actual (`--quit`, sí confirmado en su
    --help) y esperar a que termine de verdad, y recién ahí lanzar
    una instancia NUEVA sin --hide-window — un arranque fresco sin
    ese flag muestra su ventana por comportamiento normal de
    cualquier app GTK, sin depender de si la activación remota la
    "destapa" o no."""
    if not esta_instalado():
        return False, (
            "EasyEffects no está instalado en este sistema. "
            "Instalalo con: sudo apt install easyeffects"
        )

    if _esta_corriendo():
        _ejecutar_comando(FLAG_SALIR)
        inicio = time.monotonic()
        while time.monotonic() - inicio < TIMEOUT_ARRANQUE_SEGUNDOS:
            if not _esta_corriendo():
                break
            time.sleep(INTERVALO_SONDEO_SEGUNDOS)
        else:
            registrar_error(
                "EasyEffects: no terminó de cerrarse tras --quit — no se pudo "
                "relanzar con la ventana visible."
            )
            return False, (
                "EasyEffects no respondió al intentar cerrarlo para volver a "
                "abrirlo con la ventana visible."
            )

    if not _lanzar_proceso_con_captura([]):
        return False, "No se pudo abrir la ventana de EasyEffects."

    if not _esperar_proceso_vivo(TIMEOUT_ARRANQUE_SEGUNDOS):
        cola = _cola_log_proceso()
        registrar_error(
            "EasyEffects: no volvió a aparecer tras relanzarlo (sin --hide-window) para mostrar la ventana."
            + (f" Salida capturada:\n{cola}" if cola else "")
        )
        mensaje = "EasyEffects no volvió a abrir tras relanzarlo."
        return False, mensaje + (f" Detalle: {cola[:300]}" if cola else "")

    registrar_evento("EasyEffects: relanzado sin --hide-window para mostrar la ventana.")
    return True, "Ventana de EasyEffects abierta."
