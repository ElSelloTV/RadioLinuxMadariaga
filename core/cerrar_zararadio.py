"""
core/cerrar_zararadio.py
--------------------------------------------------------
Cierre automático diario de ZaraRadio — pedido explícito: "tengo un
operador que no quiere ni sabe manejar bien las cosas... ¿Es posible
poner un comando que automáticamente cierre ZaraRadio que siempre lo
deja abierto a las 16:10 horas? Todos los días si está abierto?"

ZaraRadio es un programa de automatización radial APARTE de esta app,
corriendo bajo Wine en la misma PC (ya documentado en otras rondas —
ver `core/prioridad_proceso.py` y el incidente de Chrome Remote
Desktop en CLAUDE.md). No tiene ninguna relación con el motor de
audio/playlists de esta app — este módulo NUNCA toca nada de
`core/audio_engine.py` ni de la biblioteca, solo cierra el proceso de
Wine que corre ZaraRadio.exe.

Corre como PROCESO APARTE vía cron (ver
`core/actualizador.py:asegurar_tarea_cron_cerrar_zararadio()`, que
instala/refresca la entrada de crontab SOLO al arrancar la app -- mismo
criterio ya establecido para los lanzadores de escritorio y el resto de
las tareas programadas de este proyecto: el botón "Actualizar" de
Configuración solo hace `git pull`, nunca `instalar.sh`, así que
cualquier setup a nivel de sistema operativo tiene que hacerse desde
Python en el arranque -- documentar "agregá esto al crontab a mano" no
sirve, en la práctica eso nunca se ejecuta, y menos todavía con un
operador que "no quiere ni sabe manejar bien las cosas"). Corre a las
16:10 TODOS los días, independiente de si esta app está abierta o no --
el pedido es "todos los días si está abierto", no "si la radio está
corriendo".

Se puede correr suelto para probar, igual que `mantenimiento_diario`:
    venv/bin/python3 -m core.cerrar_zararadio

Detección vía `pgrep -fi zararadio.exe` (substring "zararadio.exe"
dentro de TODA la línea de comando, sin importar mayúsculas/
minúsculas) -- a propósito NO se asume un nombre de proceso exacto
(bajo Wine, el proceso real puede verse como "wine ZaraRadio.exe",
"ZaraRadio.exe" solo si Wine renombra el proceso, o algo intermedio
según la versión), pero el ".exe" SÍ es a propósito -- no alcanza con
"zararadio" solo. Bug real encontrado y corregido ANTES de llegar a
producción (atrapado por el propio test, con un proceso real, antes de
confiar en esto): el propio nombre de este archivo, "cerrar_zararadio
.py", CONTIENE el substring "zararadio" -- un patrón sin el ".exe" se
auto-matchea contra el PROPIO proceso Python que corre este script
(`pgrep -f` no excluye a sus ancestros, solo a sí mismo), haciendo que
"_esta_corriendo()" devolviera SIEMPRE True aunque ZaraRadio real nunca
estuviera abierto -- y de paso, `pkill` hubiera intentado matar a este
mismo script en cada corrida. Con ".exe" en el patrón, ni el nombre de
este script ni la ruta de instalación de esta app ("RadioLinuxMadariaga")
pueden matchear por accidente -- solo un ejecutable Windows real
corriendo bajo Wine. **Pendiente de confirmar con Santiago** la primera
vez que esto corra: si no llega a cerrarlo, correr
`pgrep -fi zararadio.exe` a mano (con ZaraRadio real abierto) y mandar
la salida para ajustar el patrón si hiciera falta (por ejemplo, si esa
instalación puntual de Wine no conserva el ".exe" en el nombre visible).

Cierre en dos pasos, nunca uno solo -- un Windows binario bajo Wine no
tiene ninguna garantía de manejar una señal de cierre "amable" de forma
útil, y la prioridad real acá es que ZaraRadio quede CERRADO sin falta,
no que se cierre "elegante":
  1. `pkill -fi zararadio` (SIGTERM, el default de pkill) -- le da una
     chance de cerrarse solo primero.
  2. Si sigue vivo un par de segundos después, `pkill -9 -fi zararadio`
     (SIGKILL) -- garantiza que termine, sin excepción.
--------------------------------------------------------
"""

import os
import shutil
import subprocess
import sys
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

PATRON_PROCESO = "zararadio.exe"
SEGUNDOS_ESPERA_CIERRE_AMABLE = 3.0


def _esta_corriendo() -> bool:
    """`pgrep -fi zararadio` -- True si hay al menos un proceso cuya
    línea de comando completa contiene "zararadio" (sin importar
    mayúsculas/minúsculas). Degrada a False (nunca lanza excepción) si
    `pgrep` no está instalado o falla por cualquier motivo."""
    if not shutil.which("pgrep"):
        return False
    try:
        resultado = subprocess.run(
            ["pgrep", "-fi", PATRON_PROCESO], capture_output=True, text=True, timeout=5,
        )
        return resultado.returncode == 0 and bool(resultado.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        return False


def _pkill(senal_dura: bool) -> None:
    if not shutil.which("pkill"):
        return
    argumentos = ["pkill", "-9", "-fi", PATRON_PROCESO] if senal_dura else ["pkill", "-fi", PATRON_PROCESO]
    try:
        subprocess.run(argumentos, capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass


def cerrar_zararadio_si_esta_abierto() -> dict:
    """Si ZaraRadio está corriendo, lo cierra (amable, y si no alcanza,
    forzado). Si no está corriendo, no hace nada. Nunca lanza
    excepción -- degrada limpio ante cualquier fallo de `pgrep`/`pkill`
    (sistema sin esas herramientas, permisos, lo que sea), dejando
    constancia clara en el log de qué pasó."""
    if not _esta_corriendo():
        return {"estaba_abierto": False, "cerrado": None}

    _pkill(senal_dura=False)
    time.sleep(SEGUNDOS_ESPERA_CIERRE_AMABLE)

    if _esta_corriendo():
        _pkill(senal_dura=True)
        time.sleep(1.0)

    return {"estaba_abierto": True, "cerrado": not _esta_corriendo()}


def main():
    from config.settings import registrar_evento, registrar_error

    resultado = cerrar_zararadio_si_esta_abierto()
    if not resultado["estaba_abierto"]:
        registrar_evento("Cierre diario de ZaraRadio (16:10): no estaba abierto, nada que hacer")
    elif resultado["cerrado"]:
        registrar_evento("Cierre diario de ZaraRadio (16:10): estaba abierto, se cerró correctamente")
    else:
        registrar_error(
            "Cierre diario de ZaraRadio (16:10): estaba abierto y NO se pudo cerrar "
            "ni con cierre forzado -- revisar a mano"
        )


if __name__ == "__main__":
    main()
