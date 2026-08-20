"""
core/sesion_display.py
--------------------------------------------------------
Evita que la radio arranque en una sesión gráfica REMOTA/virtual en
vez de la sesión física de la PC — bug real reportado por Santiago:
"algunas cosas le gana de mano la sesión del remoto y la principal...
se abre y reproduce en otra sesión y no sale al aire".

Contexto (ver también "Incidente real — PC de la radio se congeló con
Chrome Remote Desktop", más arriba en CLAUDE.md): el modo desatendido
de Chrome Remote Desktop en Linux NO se conecta a la sesión física ya
corriendo (a diferencia de Windows/Mac) — crea una sesión X VIRTUAL
nueva, con su propio $DISPLAY, completamente aparte de la física.
Santiago confirmó su sesión física real: "radio: default (:0, vt7)",
visible en el selector de sesiones de TDE.

Si algo llega a intentar lanzar la radio DENTRO de esa sesión virtual
(un autostart, o un click accidental sobre el mismo ícono de
Escritorio — el Escritorio es la MISMA carpeta para las dos sesiones,
mismo usuario/home), el lock de instancia única
(`core/instancia_unica.py`) NO distingue sesiones — es un simple
archivo compartido — así que CUALQUIERA de las dos que gane la carrera
por tomarlo se queda con el proceso único. Si gana la sesión virtual,
la radio entera (audio incluido) queda atada al PipeWire/PulseAudio de
ESA sesión, que nunca llega a la consola real — "no sale al aire"
mientras la app, desde adentro, funciona perfecto (por eso, de paso,
NINGÚN arreglo de enrutado de audio dentro de una sesión ya wrongly
elegida puede solucionar esto — es un problema de ANTES, de qué sesión
terminó corriendo la app).

Esta protección corta el problema de raíz: la radio se NIEGA a
arrancar si no está corriendo en la sesión física esperada — nunca
entra siquiera a competir por el lock de instancia única, así el
arranque legítimo (sesión física) nunca tiene que "ganarle de mano" a
nada, porque el otro nunca llega a intentarlo.
--------------------------------------------------------
"""
import os

# Sesión física confirmada con Santiago (selector de sesiones de TDE
# en su PC real: "radio: default (:0, vt7)"). Si en otra instalación
# la sesión física real tuviera otro número, es el único valor que
# hay que cambiar acá.
DISPLAY_FISICO_ESPERADO = ":0"


def _display_base() -> str:
    """$DISPLAY sin el sufijo de pantalla (":0.0" -> ":0") — X11 a
    veces reporta el número de pantalla explícito, a veces no; separar
    en el primer "." evita un falso bloqueo por esa sola diferencia de
    formato."""
    return os.environ.get("DISPLAY", "").split(".", 1)[0]


def es_sesion_fisica_esperada() -> bool:
    """True si el proceso actual corre sobre el DISPLAY físico
    esperado. No existe una forma 100% infalible de distinguir "sesión
    física" de "sesión remota" en Linux sin depender de herramientas
    de sistema (`loginctl`, etc.) que pueden no comportarse igual en
    todas las instalaciones — comparar contra el DISPLAY real conocido
    de la PC es la señal más simple y confiable disponible."""
    return _display_base() == DISPLAY_FISICO_ESPERADO


def descripcion_sesion_actual() -> str:
    """Para el log/mensaje de aviso -- qué DISPLAY tiene esta sesión
    en verdad, para poder diagnosticar sin acceso directo a la PC."""
    return os.environ.get("DISPLAY") or "(sin $DISPLAY)"
