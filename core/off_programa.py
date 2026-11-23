"""
core/off_programa.py
--------------------------------------------------------
Motor de "programas OFF" (pedido explícito: "simular un programa en
vivo... grabo con mi celular 3 o 4 bloques solo de voz, los subo a una
carpeta de Drive... armo un FMT que ordene: primero el bloque 1,
música aleatoria por un tiempo, el bloque 2, más música, etc." — sigla
elegida por Santiago, "OFF" por "Offline"; "este motor puede servir
para otros más" -> Configuración → Programas OFF es una lista
GROWABLE, ver config/settings.py:listar_programas_off()).

Diferencia real con ENLATADO (que ya tenía exactamente este mecanismo
de descarga, ver core/sincronizador_drive.py): Enlatado reproduce
TODOS los archivos sincronizados uno atrás del otro, como un Comando
de una sola vez en Ventana 1. Un programa OFF se consume de a UN
bloque por vez, como el tipo de ítem NUEVO "off" del Musicalizador
Avanzado (ver core/musicalizador.py) -- así se puede intercalar con
música/publicidad entre cada bloque. La DESCARGA en sí (gdown, staging
+ swap atómico, orden natural, análisis de silencio/nivelado
cacheado) se REUSA tal cual de core/sincronizador_drive.py -- solo
cambia que la carpeta destino es la que Santiago configuró para ESE
programa, no una fija bajo config/data/enlatados_drive/.

"Si no se descargó HOY, el bloque se saltea en silencio" (decisión
confirmada con Santiago, AskUserQuestion: a diferencia de Enlatado,
que prefiere seguir sonando contenido VIEJO antes que silencio, un
programa OFF es contenido atado a UN día específico -- sonar el
saludo de ayer en un programa en vivo sería peor que no sonar nada).
`resolver_bloque()` chequea la fecha de MODIFICACIÓN de la carpeta
local -- el swap atómico de sincronizar_fuente_drive() la actualiza
sola en cada sincronización exitosa, así que no hace falta ningún
archivo de metadata aparte para saber "¿esto es de hoy?".

Dos usos como PROCESO APARTE vía cron (ver core/actualizador.py:
asegurar_tareas_cron_programas_off(), UNA entrada de descarga + UNA de
limpieza POR programa, con los días/hora que cada uno tenga
configurados — a diferencia de Enlatado, que sincroniza TODOS sus
slots tipo drive juntos a las 00:30, acá cada programa puede tener su
propio horario, "este motor puede servir para otros más" con
necesidades distintas):
    venv/bin/python3 -m core.off_programa --sincronizar --id <id>
    venv/bin/python3 -m core.off_programa --limpiar --id <id>
También lanzado por los botones "🔄 Sincronizar ahora"/"🗑 Limpiar
ahora" de Configuración → Programas OFF vía QProcess (igual mecanismo
ya probado para Enlatado tipo Drive, nunca bloquea la GUI).

**Respaldo de rescate al arrancar la app** (`sincronizar_pendientes_al_iniciar()`,
llamada desde main.py -- pedido explícito tras un caso real: el
horario de descarga de un programa coincidió con el reinicio diario
de la PC, la 5am, y la sincronización de esa madrugada se cortó a
mitad de camino sin que nadie se enterara hasta que ya era tarde en
el día): si al abrir la app algún programa configurado todavía no
quedó sincronizado HOY, dispara una sincronización de rescate ya
mismo, en vez de esperar al próximo horario programado -- ver su
propio docstring para el detalle completo.

**Límite real, honesto, el mismo que ya documenta
core/sincronizador_drive.py**: este entorno de desarrollo no tiene
salida de red hacia drive.google.com, así que la descarga real NUNCA
se pudo probar de punta a punta acá.
--------------------------------------------------------
"""

import os
import re
import sys
from datetime import date

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from core.sincronizador_drive import (
    sincronizar_fuente_drive, EXTENSIONES_AUDIO, NOMBRE_ARCHIVO_ANALISIS,
)


def _numero_de_nombre(nombre_archivo: str) -> int | None:
    """"1.m4a" -> 1, "01.mp3" -> 1, "1 - saludo.wav" -> 1. `None` si el
    nombre no empieza con un número -- ese archivo se ignora (puede
    ser basura/otro formato que se coló en la carpeta de Drive)."""
    base = os.path.splitext(nombre_archivo)[0].strip()
    coincidencia = re.match(r"^0*(\d+)", base)
    return int(coincidencia.group(1)) if coincidencia else None


def _carpeta_sincronizada_hoy(carpeta_local: str) -> bool:
    """`True` si `carpeta_local` existe Y su fecha de modificación es
    HOY -- el swap atómico de sincronizar_fuente_drive() la actualiza
    sola en cada sincronización exitosa (nunca la toca si la corrida
    falló, ver docstring del módulo), así que esto es, sin necesitar
    ningún archivo de metadata aparte, "¿el contenido de acá es el que
    se bajó esta madrugada, o es de un día anterior?"."""
    if not os.path.isdir(carpeta_local):
        return False
    try:
        fecha_modificacion = date.fromtimestamp(os.path.getmtime(carpeta_local))
    except OSError:
        return False
    return fecha_modificacion == date.today()


def _archivos_por_numero(carpeta_local: str) -> dict[int, list[str]]:
    """{número_bloque: [nombre_archivo, ...]} de TODO lo sincronizado
    en `carpeta_local` -- usado por `resolver_bloque()` (elegir cuál
    reproducir) y por `bloques_duplicados_hoy()` (detectar y avisar si
    hay más de un archivo para el mismo número). No chequea "¿es de
    hoy?" -- eso lo decide el llamador."""
    try:
        nombres = os.listdir(carpeta_local)
    except OSError:
        return {}
    por_numero: dict[int, list[str]] = {}
    for nombre in nombres:
        if not nombre.lower().endswith(EXTENSIONES_AUDIO):
            continue
        numero = _numero_de_nombre(nombre)
        if numero is None:
            continue
        por_numero.setdefault(numero, []).append(nombre)
    return por_numero


def resolver_bloque(programa: dict, numero_bloque: int) -> dict | None:
    """El archivo "bloque N" del programa OFF `programa` -- `None` si
    no corresponde reproducir nada (programa sin carpeta configurada,
    no sincronizado HOY, o no existe un archivo "N" en lo
    sincronizado). Devuelve un dict "tipo registro" (ruta/titulo/
    codigo/punto_inicio_ms/punto_fin_ms/ganancia_db), mismo contrato
    que cualquier registro real de la biblioteca -- así
    core/musicalizador.py lo puede tratar exactamente igual que el
    resultado de un ítem Específico/Aleatorio, sin ningún caso
    especial en el resto del motor.

    Bug real evitado ANTES de llegar a Santiago (pregunta directa:
    "¿debo reemplazarlos para que no haya dos archivos por nombre 1,
    2, etc.?"): si Drive llega a tener, por un olvido, dos archivos
    distintos que matchean el mismo número (ej. "1 - lunes.mp3" y
    "1 - martes.mp3"), elegir el PRIMERO que devuelva `os.listdir()`
    (orden del sistema de archivos, nunca garantizado) sería
    impredecible -- podría sonar un día uno, al día siguiente el otro,
    sin ningún patrón visible. Ahora, si hay más de uno, se elige
    SIEMPRE el mismo (orden alfabético) -- determinístico, aunque la
    causa real (el duplicado en Drive) solo se resuelve borrándolo ahí
    -- ver bloques_duplicados_hoy(), que avisa de esto en el resultado
    de cada sincronización."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local or not _carpeta_sincronizada_hoy(carpeta_local):
        return None

    candidatos = sorted(_archivos_por_numero(carpeta_local).get(numero_bloque, []))
    if not candidatos:
        return None  # no hay ningún archivo "N" en lo sincronizado hoy -- se saltea
    nombre = candidatos[0]

    analisis_cacheado = {}
    ruta_analisis = os.path.join(carpeta_local, NOMBRE_ARCHIVO_ANALISIS)
    if os.path.isfile(ruta_analisis):
        import json
        try:
            with open(ruta_analisis, "r", encoding="utf-8") as f:
                analisis_cacheado = json.load(f)
        except (OSError, ValueError):
            analisis_cacheado = {}

    datos = analisis_cacheado.get(nombre, {})
    return {
        "ruta": os.path.join(carpeta_local, nombre),
        "titulo": os.path.splitext(nombre)[0],
        "codigo": "",
        "punto_inicio_ms": datos.get("punto_inicio_ms", 0),
        "punto_fin_ms": datos.get("punto_fin_ms"),
        "ganancia_db": datos.get("ganancia_db", 0.0),
    }


def bloques_duplicados_hoy(programa: dict) -> dict[int, list[str]]:
    """{número_bloque: [nombre_archivo, ...]} SOLO para los números
    con MÁS DE UN archivo en lo recién sincronizado -- usado por
    sincronizar_programa_off() para avisar en el resultado de la
    sincronización ("hay 2 archivos para el bloque 1") en vez de
    dejar que Santiago lo descubra días después como un misterioso
    "cambió de archivo sin que yo tocara nada"."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local or not _carpeta_sincronizada_hoy(carpeta_local):
        return {}
    return {
        numero: nombres
        for numero, nombres in _archivos_por_numero(carpeta_local).items()
        if len(nombres) > 1
    }


def cantidad_bloques_disponibles_hoy(programa: dict) -> int:
    """Cuántos bloques numerados hay sincronizados HOY para
    `programa` -- usado por la UI del Musicalizador para mostrar algo
    útil ("hoy hay 4 bloques descargados") sin tener que adivinar."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local or not _carpeta_sincronizada_hoy(carpeta_local):
        return 0
    try:
        nombres = os.listdir(carpeta_local)
    except OSError:
        return 0
    numeros = {_numero_de_nombre(n) for n in nombres if n.lower().endswith(EXTENSIONES_AUDIO)}
    numeros.discard(None)
    return len(numeros)


def sincronizar_pendientes_al_iniciar() -> None:
    """Respaldo de rescate, pedido explícito tras un caso real: Santiago
    grabó 4 bloques nuevos y los subió a Drive un domingo a las 18hs --
    el único horario de descarga configurado para ESE programa era
    5:00am, la MISMA hora en la que la PC de la radio se reinicia sola
    todos los días (rutina ya documentada, ver CLAUDE.md) -- la
    sincronización de la madrugada se cortó a mitad de camino (la red
    se va durante el reinicio), la carpeta local nunca quedó marcada
    como "de hoy", y como el próximo intento programado era recién al
    día siguiente a la misma hora, el programa se quedó sin contenido
    TODO el día sin que nadie se entere hasta que ya era tarde.

    Llamada al ARRANCAR la app (main.py, mismo criterio que el resto
    de las tareas de cron de ahí -- nunca debe poder frenar nada si
    algo falla): por cada programa OFF bien configurado (con
    `carpeta_local` y `url_carpeta`) que TODAVÍA no quedó sincronizado
    hoy -- sin importar si hoy es uno de los `dias_descarga` elegidos,
    el objetivo es "nunca te quedes todo un día sin contenido fresco
    por una sincronización fallida", no repetir la lógica de
    agendamiento del cron -- dispara una sincronización de RESCATE en
    segundo plano, sin esperar el horario programado.

    Idempotente de forma natural: en cuanto una sincronización (la de
    rescate, o la programada de siempre) tiene éxito,
    `_carpeta_sincronizada_hoy()` pasa a `True` y un reinicio posterior
    de la app el MISMO día ya no vuelve a disparar nada para ese
    programa -- no hace falta ningún estado propio para "ya lo
    intenté hoy".

    Fire-and-forget (`QProcess.startDetached()`, mismo mecanismo ya
    usado por `core.actualizador.reiniciar_aplicacion()` -- no
    necesita el event loop de Qt corriendo todavía, ya que esto se
    llama ANTES de `app.exec()`): nunca bloquea el arranque de la
    radio, y el resultado de cada intento (éxito o error, con el
    detalle real) queda igual en el log de siempre
    (`registrar_evento()`/`registrar_error()`, el mismo que ya usa
    `main()` más abajo cuando lo dispara el cron) -- no hace falta
    ningún seguimiento extra acá, el proceso hijo ya deja constancia
    por su cuenta."""
    from PySide6.QtCore import QProcess
    from config.settings import cargar_configuracion, listar_programas_off

    config = cargar_configuracion()
    script = os.path.join(_RAIZ, "core", "off_programa.py")
    for programa in listar_programas_off(config):
        id_programa = str(programa.get("id") or "").strip()
        carpeta_local = (programa.get("carpeta_local") or "").strip()
        url = (programa.get("url_carpeta") or "").strip()
        if not id_programa or not carpeta_local or not url:
            continue
        if _carpeta_sincronizada_hoy(carpeta_local):
            continue  # ya está al día -- nada que rescatar
        QProcess.startDetached(sys.executable, [script, "--sincronizar", "--id", id_programa])


def sincronizar_programa_off(programa: dict, config: dict, callback_progreso=None) -> dict:
    """Descarga los bloques del programa OFF `programa` -- delega
    100% en core.sincronizador_drive.sincronizar_fuente_drive() (el
    MISMO motor ya probado para Enlatado tipo Drive), pasando la
    carpeta local CONFIGURADA de este programa en vez de la fija de
    Enlatado."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local:
        return {"ok": False, "mensaje": "Sin carpeta local configurada para este programa."}
    resultado = sincronizar_fuente_drive(
        programa.get("id"), programa.get("url_carpeta", ""), config,
        callback_progreso=callback_progreso, carpeta_destino_override=carpeta_local,
    )
    # Pregunta directa de Santiago ("¿debo reemplazarlos para que no
    # haya dos archivos por nombre 1, 2, etc.?") -- si quedó más de un
    # archivo para el mismo número (se subió el nuevo a Drive sin
    # borrar el viejo), avisa EN EL RESULTADO de esta misma
    # sincronización -- el único punto donde Santiago realmente lo va
    # a ver, en vez de descubrirlo días después como un bloque que
    # "cambió sin que él tocara nada".
    if resultado.get("ok"):
        duplicados = bloques_duplicados_hoy(programa)
        if duplicados:
            detalle = "; ".join(
                f"bloque {numero}: {', '.join(nombres)}"
                for numero, nombres in sorted(duplicados.items())
            )
            resultado["mensaje"] += (
                f" ⚠ ATENCIÓN: hay más de un archivo para el mismo número ({detalle}) -- "
                "se va a reproducir siempre el mismo (orden alfabético), pero conviene borrar "
                "el que no corresponda en Drive antes de la próxima sincronización."
            )
    return resultado


def limpiar_programa_off(programa: dict) -> dict:
    """Borra todos los archivos de voz YA descargados de `programa`
    (pedido explícito: "los archivos de voz deberán eliminarse del
    sistema todos los domingos por la noche, para liberar espacio y
    comenzar una semana nueva desde 0"). Borra el CONTENIDO de
    `carpeta_local`, nunca la carpeta en sí (así una próxima
    sincronización, al recrearla con el swap atómico, no tiene que
    lidiar con una carpeta "a medio borrar" de permisos raros) --
    aislado con su propio try/except por archivo, mismo criterio de
    "nunca romper el lote por un ítem malo" de siempre en este
    proyecto."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local or not os.path.isdir(carpeta_local):
        return {"ok": True, "mensaje": "Nada para limpiar (sin carpeta local, o todavía no existía).", "borrados": 0}

    borrados, fallidos = 0, 0
    for nombre in os.listdir(carpeta_local):
        ruta = os.path.join(carpeta_local, nombre)
        try:
            os.remove(ruta)
            borrados += 1
        except OSError:
            fallidos += 1
    mensaje = f"{borrados} archivo(s) borrado(s)" + (f", {fallidos} fallido(s)" if fallidos else "") + "."
    return {"ok": fallidos == 0, "mensaje": mensaje, "borrados": borrados}


def main():
    import argparse
    import json as json_mod

    parser = argparse.ArgumentParser(
        description="Sincroniza o limpia UN programa OFF, como proceso aparte.",
    )
    parser.add_argument("--id", required=True, help="Id del programa OFF (Configuración → Programas OFF).")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--sincronizar", action="store_true", help="Descarga los bloques del programa.")
    grupo.add_argument("--limpiar", action="store_true", help="Borra los bloques ya descargados.")
    # --url/--carpeta-local se pasan EXPLÍCITO (nunca releídos de disco
    # si están presentes) -- mismo criterio ya usado por
    # sincronizador_drive.py --slot-id/--url: "Sincronizar ahora" en la
    # UI usa lo recién tipeado, incluso antes de apretar "Guardar".
    parser.add_argument("--url", default=None)
    parser.add_argument("--carpeta-local", default=None)
    args = parser.parse_args()

    from config.settings import cargar_configuracion, obtener_programa_off, registrar_evento, registrar_error

    config = cargar_configuracion()
    programa = obtener_programa_off(config, args.id) or {"id": args.id, "nombre": args.id}
    if args.url is not None:
        programa = dict(programa, url_carpeta=args.url)
    if args.carpeta_local is not None:
        programa = dict(programa, carpeta_local=args.carpeta_local)
    nombre = programa.get("nombre") or args.id

    if args.sincronizar:
        def _progreso(hechos, total):
            print(f"PROGRESO {hechos} {total}", flush=True)

        resultado = sincronizar_programa_off(programa, config, callback_progreso=_progreso)
        print(f"RESULTADO {json_mod.dumps(resultado)}", flush=True)
        if resultado["ok"]:
            registrar_evento(f"Programa OFF '{nombre}': sincronización -- {resultado['mensaje']}")
        else:
            registrar_error(f"Programa OFF '{nombre}': sincronización falló -- {resultado['mensaje']}")
    else:
        resultado = limpiar_programa_off(programa)
        print(f"RESULTADO {json_mod.dumps(resultado)}", flush=True)
        registrar_evento(f"Programa OFF '{nombre}': limpieza semanal -- {resultado['mensaje']}")


if __name__ == "__main__":
    main()
