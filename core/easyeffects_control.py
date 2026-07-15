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
TIMEOUT_ARRANQUE_SEGUNDOS = 3.0
INTERVALO_SONDEO_SEGUNDOS = 0.2


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


def asegurar_en_ejecucion() -> tuple[bool, str]:
    """Arranca EasyEffects OCULTO si todavía no está corriendo, o lo
    oculta si ya estaba con la ventana abierta (el operador la abrió
    a mano) — el mismo flag `--hide-window` sirve para las dos cosas.
    No bloquea el arranque en sí (proceso desacoplado); sondea con
    `pgrep` hasta que la instancia queda realmente arriba, porque los
    comandos posteriores (cambiar de preset, etc.) necesitan que ya
    esté registrada."""
    if not esta_instalado():
        return False, (
            "EasyEffects no está instalado en este sistema. "
            "Instalalo con: sudo apt install easyeffects"
        )

    if _esta_corriendo():
        _ejecutar_comando(FLAG_OCULTAR_VENTANA)
        return True, "EasyEffects ya estaba en ejecución."

    if not QProcess.startDetached(NOMBRE_BINARIO, [FLAG_OCULTAR_VENTANA]):
        return False, "No se pudo lanzar EasyEffects."

    inicio = time.monotonic()
    while time.monotonic() - inicio < TIMEOUT_ARRANQUE_SEGUNDOS:
        if _esta_corriendo():
            return True, "EasyEffects arrancó oculto correctamente."
        time.sleep(INTERVALO_SONDEO_SEGUNDOS)
    return False, "EasyEffects no respondió a tiempo al arrancar."


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
    if resultado is None:
        return False, "EasyEffects no respondió al cambiar de preset."
    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
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
