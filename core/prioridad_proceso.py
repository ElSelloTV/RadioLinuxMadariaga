"""
core/prioridad_proceso.py
--------------------------------------------------------
Prioridad de proceso dinámica (pedido explícito: "agrega prioridad de
reproducción, solo cuando está play en cualquier ventana activo, si
no hay reproductor musical devolver la prioridad a otro, por ejemplo
ZaraRadio").

Mientras hay audio sonando en CUALQUIERA de las 3 ventanas de
reproducción (Publicidad, Emisión, Auxiliar), este proceso le pide al
sistema operativo una prioridad de scheduling MÁS ALTA (nice más
bajo) que la normal — en un hardware modesto compartiendo CPU con
otros programas (ej. ZaraRadio bajo Wine), esto le da al sistema
operativo una señal explícita de "priorizame a mí" mientras el audio
está al aire. En cuanto no queda nada sonando, vuelve a la prioridad
NORMAL (nice 0) — deja el mismo terreno parejo para cualquier otro
programa (ZaraRadio incluido) el resto del tiempo.

Límite real, importante: este programa NO tiene ninguna forma
legítima de tocar la prioridad de OTRO proceso ajeno (ZaraRadio corre
como un programa completamente aparte, sin relación con este) — lo
único que puede hacer es subir/bajar SU PROPIA prioridad. "Devolverle
la prioridad a ZaraRadio" en la práctica significa: no quedarse con
una ventaja permanente, solo tomarla mientras hace falta.

Requiere permiso del sistema operativo para bajar el nice (subir
prioridad) — un usuario sin privilegios normalmente NO puede hacerlo
por defecto en Linux (hace falta ser root, o tener una regla en
/etc/security/limits.d/ que lo habilite, o la capability
CAP_SYS_NICE). Si el sistema no lo permite, esto degrada limpio: se
queda en la prioridad normal de siempre, sin romper nada, y deja UN
aviso en el log (nunca en loop) explicando qué falta para habilitarlo.
"""
import os

from config.settings import registrar_evento

NICE_NORMAL = 0
NICE_REPRODUCIENDO = -5  # moderado a propósito -- no hace falta ir a los extremos (-20)

_aviso_sin_permiso_ya_mostrado = False
_prioridad_actual = None  # None = todavía no se tocó desde que arrancó el proceso


def _establecer_nice(nivel: int) -> bool:
    global _aviso_sin_permiso_ya_mostrado
    try:
        os.setpriority(os.PRIO_PROCESS, 0, nivel)
        return True
    except (PermissionError, OSError) as error:
        if not _aviso_sin_permiso_ya_mostrado:
            _aviso_sin_permiso_ya_mostrado = True
            registrar_evento(
                f"Prioridad de proceso: el sistema operativo no permite elevar la "
                f"prioridad (nice {nivel}) sin privilegios -- se sigue en la "
                f"prioridad normal de siempre, sin que esto rompa nada. "
                f"Para habilitarlo hace falta una regla en /etc/security/limits.d/ "
                f"(o correr el programa con permisos que lo permitan). Detalle: {error}"
            )
        return False


def actualizar_segun_reproduccion(hay_algo_sonando: bool):
    """Llamar cada vez que se quiera sincronizar la prioridad del
    proceso con el estado agregado de reproducción de la app (algo
    sonando en cualquiera de las 3 ventanas, o nada). Idempotente — no
    repite la llamada al sistema operativo si el nivel deseado no
    cambió desde la última vez."""
    global _prioridad_actual
    nivel_deseado = NICE_REPRODUCIENDO if hay_algo_sonando else NICE_NORMAL
    if nivel_deseado == _prioridad_actual:
        return
    exito = _establecer_nice(nivel_deseado)
    _prioridad_actual = nivel_deseado
    if exito:
        registrar_evento(
            "Prioridad de proceso: elevada (hay reproducción activa)"
            if hay_algo_sonando else
            "Prioridad de proceso: devuelta a la normal (sin reproducción activa)"
        )
