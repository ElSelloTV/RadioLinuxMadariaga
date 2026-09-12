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
    cambió desde la última vez.

    Bug real corregido (encontrado leyendo un log de producción real,
    "por qué el log solo muestra 'devuelta a la normal' pero nunca
    'elevada'"): `_prioridad_actual` se actualizaba al valor DESEADO
    sin importar si `_establecer_nice()` realmente tuvo éxito — en una
    instalación SIN el permiso de sistema operativo necesario para
    elevar prioridad (nice negativo, ver el docstring del módulo), el
    intento de "elevar" fallaba en silencio (solo un aviso genérico UNA
    vez en toda la sesión) pero quedaba MARCADO como si hubiera subido
    -- así, la próxima vez que dejaba de sonar algo, el intento de
    "bajar a 0" SÍ tenía éxito (nunca hace falta permiso para eso) y
    quedaba logueado como si reflejara un cambio real de estado, aunque
    la prioridad real del proceso NUNCA se hubiera movido de 0 en
    absoluto. Esto hacía que la línea "devuelta a la normal" apareciera
    en el log ante CUALQUIER transición a "nada sonando" que el poll de
    2s llegara a atrapar -- sin ser, por sí sola, prueba de que hubo un
    corte LARGO, solo de que en ESE instante puntual no había nada
    reproduciéndose. Corregido: `_prioridad_actual` solo se actualiza
    si `_establecer_nice()` realmente tuvo éxito -- sin el permiso
    habilitado, esta función ahora simplemente no cambia nada (ni
    interno ni real) en cada llamada, consistente con la realidad."""
    global _prioridad_actual
    nivel_deseado = NICE_REPRODUCIENDO if hay_algo_sonando else NICE_NORMAL
    if nivel_deseado == _prioridad_actual:
        return
    exito = _establecer_nice(nivel_deseado)
    if not exito:
        return
    _prioridad_actual = nivel_deseado
    registrar_evento(
        "Prioridad de proceso: elevada (hay reproducción activa)"
        if hay_algo_sonando else
        "Prioridad de proceso: devuelta a la normal (sin reproducción activa)"
    )
