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

import shutil
import subprocess
import time

from PySide6.QtCore import QProcess

from config.settings import registrar_error, registrar_evento

NOMBRE_BINARIO = "easyeffects"

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

    if not QProcess.startDetached(NOMBRE_BINARIO, [FLAG_OCULTAR_VENTANA]):
        registrar_error("EasyEffects: QProcess.startDetached() no pudo lanzar el proceso.")
        return False, "No se pudo lanzar EasyEffects."

    if not _esperar_proceso_vivo(TIMEOUT_ARRANQUE_SEGUNDOS):
        registrar_error(
            f"EasyEffects: el proceso no apareció (pgrep) en {TIMEOUT_ARRANQUE_SEGUNDOS}s tras el arranque."
        )
        return False, "EasyEffects no respondió a tiempo al arrancar."

    if not _esperar_cli_responda(TIMEOUT_PROBE_CLI_SEGUNDOS):
        # El proceso llegó a existir (posiblemente se vio brevemente
        # la ventana, "se abre y se cierra") pero nunca quedó listo
        # para recibir comandos — puede haberse caído solo apenas
        # arrancado. Reportarlo así, en vez del genérico "no
        # respondió", para que quede claro en el log qué fase falló.
        registrar_error(
            "EasyEffects: el proceso arrancó pero nunca respondió a los comandos "
            f"dentro de {TIMEOUT_PROBE_CLI_SEGUNDOS}s (¿se cerró solo justo después de abrir?)."
        )
        return False, "EasyEffects arrancó pero no llegó a responder. Reintentá desde el ícono FM."

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
    rompe la UI que la use."""
    resultado = _ejecutar_comando(FLAG_LISTAR_PRESETS)
    if resultado is None or resultado.returncode != 0:
        return []
    return [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]


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
    a fondo. No hay un flag "mostrar ventana" documentado en esta
    versión (solo --hide-window para ocultarla) — invocar el binario
    SIN ese flag activa la instancia existente, y GApplication
    presenta su ventana por defecto al recibir esa activación."""
    ok, mensaje = asegurar_en_ejecucion()
    if not ok:
        return False, mensaje
    if not QProcess.startDetached(NOMBRE_BINARIO, []):
        return False, "No se pudo abrir la ventana de EasyEffects."
    return True, "Ventana de EasyEffects abierta."
