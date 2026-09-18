"""
core/viper4linux_control.py
--------------------------------------------------------
Control MÍNIMO sobre Viper4Linux -- pedido explícito de Santiago tras el
incidente real de producción de hoy con el compresor FET ("un botón
Bypass para que en caliente pueda ver el cambio de efectos, y un botón
que abra el entorno gráfico de Viper4Linux... sin tanto trabajo").

A propósito, ESTO NO es un intento de reconstruir el control de
EasyEffects/filter-chain de PipeWire/compresor nativo de VLC de rondas
anteriores (37-55, 69-78 en CLAUDE.md) -- esas integraciones se
abandonaron varias veces, siempre por decisión explícita de Santiago
("el procesamiento de audio lo manejo por fuera"). El alcance acá es
deliberadamente chico: DOS acciones, ninguna de las dos escribe un solo
valor de DSP desde Python, ninguna maneja el ciclo de vida del proceso
de Viper (eso sigue siendo 100% systemd + el propio `viper`/`viper-gui`,
ver `extras/procesador_fm_viper4linux/`):

1. `abrir_editor_viper()` -- lanza la interfaz gráfica NATIVA
   (`viper-gui`, se instala con `./instalar_procesador_fm.sh --gui`) --
   ahí viven los controles reales (EQ, compresor, limitador, AGC,
   presets), hechos por los propios desarrolladores de Viper para esto.
2. `leer_bypass_activo()` / `establecer_bypass_activo()` -- prenden/
   apagan TODA la cadena de efectos en caliente, sin reiniciar nada ni
   tocar `audio.conf`, vía la interfaz D-Bus REAL que el propio plugin
   expone -- confirmada en el código fuente vendorizado
   (`extras/procesador_fm_viper4linux/vendor/gst-plugin-viperfx/src/
   dbus-interface.c`): bus de SESIÓN, nombre `me.noahbliss.ViperFx`,
   objeto `/me/noahbliss/ViperFx`, propiedad booleana `fx_enable`
   (readwrite). `fx_enable=true` = efectos activos (bypass apagado);
   `fx_enable=false` = bypass real, audio sin procesar.

Mismo criterio de siempre en este proyecto ante una herramienta externa
que puede no estar disponible: degradar limpio, nunca romper nada, y
dejar rastro en el log de la app para poder diagnosticar sin acceso a
la PC real.
--------------------------------------------------------
"""
import shutil
import subprocess

from PySide6.QtCore import QProcess

from config.settings import registrar_evento, registrar_error

TIMEOUT_SEGUNDOS = 3.0

BUS_NOMBRE = "me.noahbliss.ViperFx"
OBJETO_RUTA = "/me/noahbliss/ViperFx"
INTERFAZ = "me.noahbliss.ViperFx"


def esta_gui_instalada() -> bool:
    return shutil.which("viper-gui") is not None


def abrir_editor_viper() -> tuple[bool, str]:
    """Abre la interfaz gráfica nativa de Viper4Linux. Nunca escribe
    ningún valor de configuración desde acá -- eso queda 100% del lado
    de esa interfaz (o de editar audio.conf a mano)."""
    ruta = shutil.which("viper-gui")
    if ruta is None:
        return False, (
            "Viper4Linux-GUI no está instalada en esta PC. Instalala con "
            "'./instalar_procesador_fm.sh --gui' desde "
            "extras/procesador_fm_viper4linux/, y volvé a intentar."
        )
    if not QProcess.startDetached(ruta, []):
        mensaje = "No se pudo lanzar viper-gui."
        registrar_error(f"Viper4Linux: {mensaje}")
        return False, mensaje
    registrar_evento("Viper4Linux: se abrió la interfaz gráfica (viper-gui).")
    return True, "Abriendo Viper4Linux..."


def _gdbus_disponible() -> bool:
    return shutil.which("gdbus") is not None


def leer_bypass_activo() -> tuple[bool | None, str]:
    """Lee el estado REAL de fx_enable en este instante, vía D-Bus --
    nunca confía en un estado guardado en memoria de una llamada
    anterior, porque el operador puede haber tocado esto desde la
    propia interfaz gráfica de Viper mientras tanto. Devuelve
    (activo_o_None_si_no_se_pudo_leer, mensaje_de_error)."""
    if not _gdbus_disponible():
        return None, "'gdbus' no está instalado en esta PC."
    try:
        resultado = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", BUS_NOMBRE, "--object-path", OBJETO_RUTA,
             "--method", "org.freedesktop.DBus.Properties.Get",
             INTERFAZ, "fx_enable"],
            capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        return None, f"No se pudo consultar Viper4Linux: {error}"
    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        return None, f"Viper4Linux no respondió (¿está corriendo?): {detalle}"
    salida = resultado.stdout.strip()
    return ("true" in salida), ""


def establecer_bypass_activo(fx_enable: bool) -> tuple[bool, str]:
    """Prende (fx_enable=True) o apaga (fx_enable=False, bypass real)
    TODA la cadena de efectos de Viper en caliente -- nunca toca
    audio.conf, nunca reinicia el proceso ni el servicio de systemd."""
    if not _gdbus_disponible():
        mensaje = "'gdbus' no está instalado -- no se puede controlar Viper4Linux desde acá."
        registrar_error(f"Viper4Linux: {mensaje}")
        return False, mensaje
    valor = "true" if fx_enable else "false"
    try:
        resultado = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", BUS_NOMBRE, "--object-path", OBJETO_RUTA,
             "--method", "org.freedesktop.DBus.Properties.Set",
             INTERFAZ, "fx_enable", f"<{valor}>"],
            capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        mensaje = f"No se pudo aplicar el cambio: {error}"
        registrar_error(f"Viper4Linux: {mensaje}")
        return False, mensaje
    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        mensaje = f"Viper4Linux rechazó el cambio (¿está corriendo?): {detalle}"
        registrar_error(f"Viper4Linux: {mensaje}")
        return False, mensaje
    estado_texto = "DESACTIVADO (con efectos)" if fx_enable else "ACTIVADO (audio sin procesar)"
    registrar_evento(f"Viper4Linux: bypass {estado_texto}.")
    return True, "Listo."
