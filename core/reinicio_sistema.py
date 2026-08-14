"""
core/reinicio_sistema.py
--------------------------------------------------------
Reinicio forzado de la PC (pedido explícito, Configuración: "agregame
la posibilidad de reiniciar la PC... sin importar los procesos o
programas abiertos. un reinicio forzado sería") — un botón de última
instancia para cuando la radio quedó "colgada" y no hay forma de
acceder a una terminal (mismo escenario ya documentado en CLAUDE.md,
el incidente de Chrome Remote Desktop con la PC de la radio).

`systemctl reboot -i` es el mecanismo elegido:
- No necesita ningún permiso especial nuevo en la mayoría de los
  escritorios Linux (Q4OS/TDE incluido) — logind/polkit ya autorizan
  a la sesión gráfica ACTIVA a reiniciar sin sudo (política
  "org.freedesktop.login1.reboot"), a diferencia de `reboot`/
  `shutdown -r now`, que sí piden privilegios de root.
- `-i, --ignore-inhibitors` es el "forzado" real del pedido — ignora
  cualquier inhibitor lock que otro programa haya puesto (ej. "hay
  cambios sin guardar") y reinicia igual, sin esperar a nadie.

Si `systemctl` no está disponible o el comando falla (otro init
system, falta de permisos, lo que sea), degrada limpio: nunca rompe
nada, deja un aviso claro en el log y devuelve el error real para
mostrarlo en la UI — mismo criterio de siempre en este proyecto ante
comandos del sistema operativo que pueden no estar disponibles.
--------------------------------------------------------
"""
import shutil
import subprocess

from config.settings import registrar_evento, registrar_error

TIMEOUT_SEGUNDOS = 5.0


def reiniciar_pc_forzado() -> tuple[bool, str]:
    """Dispara un reinicio INMEDIATO y FORZADO de toda la PC — no del
    programa, de la máquina entera. Devuelve (éxito, mensaje). El
    éxito acá solo confirma que el COMANDO se aceptó -- si tiene
    éxito, la PC se reinicia sola en los próximos segundos, sin
    esperar ninguna otra confirmación."""
    if shutil.which("systemctl") is None:
        mensaje = (
            "No se encontró 'systemctl' en esta instalación -- no se puede "
            "reiniciar la PC desde acá. Hace falta reiniciarla a mano."
        )
        registrar_error(f"Reinicio forzado de la PC: {mensaje}")
        return False, mensaje

    try:
        resultado = subprocess.run(
            ["systemctl", "reboot", "-i"],
            capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        mensaje = f"No se pudo ejecutar el reinicio: {error}"
        registrar_error(f"Reinicio forzado de la PC: {mensaje}")
        return False, mensaje

    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        mensaje = (
            f"El sistema rechazó el reinicio (código {resultado.returncode})"
            + (f": {detalle}" if detalle else "")
        )
        registrar_error(f"Reinicio forzado de la PC: {mensaje}")
        return False, mensaje

    registrar_evento("Reinicio forzado de la PC solicitado desde Configuración -- reiniciando ahora.")
    return True, "Reinicio aceptado -- la PC se está reiniciando ahora."
