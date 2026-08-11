"""
core/instancia_unica.py
--------------------------------------------------------
Evita que la app se abra más de una vez al mismo tiempo — pedido
explícito, caso real: un operador no entendía y apretó el ícono de
escritorio varias veces seguidas, terminó con 3 instancias del
programa abiertas a la vez, cada una con su propio motor de audio
sonando por su cuenta, sin poder identificar de dónde salía cada cosa
("imaginate el problema... tenía 3 veces el programa abierto").

Usa un lock de ARCHIVO (`fcntl.flock`, exclusivo y no bloqueante), no
un archivo de PID a mano — la ventaja real: el lock lo libera el
sistema operativo SOLO, apenas el proceso termina, sin importar CÓMO
termine (cierre normal, `kill -9`, corte de luz) — un archivo de PID
comparado a mano puede quedar "stale" (apuntando a un proceso que ya
no existe) y necesitaría lógica extra para detectarlo y limpiarlo. Con
flock, si el lock se puede tomar, es porque la instancia anterior YA
NO existe de verdad — nunca hay un falso "ocupado" que bloquee un
arranque legítimo tras un cierre anormal.
--------------------------------------------------------
"""
import fcntl
import os

from config.settings import DIRECTORIO_CONFIG

RUTA_LOCK_INSTANCIA = os.path.join(DIRECTORIO_CONFIG, "instancia.lock")

# Referencia global al file descriptor del lock -- tiene que
# sobrevivir mientras dure el proceso: si Python lo recolecta (o se
# reasigna sin querer), el lock se libera solo antes de tiempo. Nunca
# se cierra a propósito salvo con liberar_bloqueo_instancia_unica().
_archivo_lock = None


def adquirir_bloqueo_instancia_unica() -> bool:
    """Intenta tomar el lock exclusivo de instancia única. Devuelve
    True si esta es la ÚNICA instancia corriendo (lock adquirido) o
    False si ya hay otra instancia con el lock tomado — en ese caso,
    el llamador debe avisar y cerrarse, sin construir ninguna ventana
    ni tocar ninguna playlist."""
    global _archivo_lock
    os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)
    candidato = open(RUTA_LOCK_INSTANCIA, "w")
    try:
        fcntl.flock(candidato.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        candidato.close()
        return False
    # Recién ahora, con el lock YA tomado de verdad, se reemplaza la
    # referencia global -- nunca pisarla antes de confirmar el éxito,
    # para no soltar por accidente un lock previo válido.
    _archivo_lock = candidato
    try:
        _archivo_lock.write(str(os.getpid()))
        _archivo_lock.flush()
    except OSError:
        pass  # el PID adentro es solo para diagnóstico manual, nunca crítico
    return True


def liberar_bloqueo_instancia_unica():
    """Suelta el lock a mano. En producción nunca hace falta llamarla
    (el lock se libera solo al terminar el proceso, sin importar
    cómo) -- existe sobre todo para poder testear adquirir/soltar
    dentro del mismo proceso."""
    global _archivo_lock
    if _archivo_lock is not None:
        try:
            fcntl.flock(_archivo_lock.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        _archivo_lock.close()
        _archivo_lock = None
