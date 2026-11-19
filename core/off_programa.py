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


def resolver_bloque(programa: dict, numero_bloque: int) -> dict | None:
    """El archivo "bloque N" del programa OFF `programa` -- `None` si
    no corresponde reproducir nada (programa sin carpeta configurada,
    no sincronizado HOY, o no existe un archivo "N" en lo
    sincronizado). Devuelve un dict "tipo registro" (ruta/titulo/
    codigo/punto_inicio_ms/punto_fin_ms/ganancia_db), mismo contrato
    que cualquier registro real de la biblioteca -- así
    core/musicalizador.py lo puede tratar exactamente igual que el
    resultado de un ítem Específico/Aleatorio, sin ningún caso
    especial en el resto del motor."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local or not _carpeta_sincronizada_hoy(carpeta_local):
        return None

    analisis_cacheado = {}
    ruta_analisis = os.path.join(carpeta_local, NOMBRE_ARCHIVO_ANALISIS)
    if os.path.isfile(ruta_analisis):
        import json
        try:
            with open(ruta_analisis, "r", encoding="utf-8") as f:
                analisis_cacheado = json.load(f)
        except (OSError, ValueError):
            analisis_cacheado = {}

    try:
        nombres = os.listdir(carpeta_local)
    except OSError:
        return None

    for nombre in nombres:
        if not nombre.lower().endswith(EXTENSIONES_AUDIO):
            continue
        if _numero_de_nombre(nombre) != numero_bloque:
            continue
        datos = analisis_cacheado.get(nombre, {})
        return {
            "ruta": os.path.join(carpeta_local, nombre),
            "titulo": os.path.splitext(nombre)[0],
            "codigo": "",
            "punto_inicio_ms": datos.get("punto_inicio_ms", 0),
            "punto_fin_ms": datos.get("punto_fin_ms"),
            "ganancia_db": datos.get("ganancia_db", 0.0),
        }
    return None  # no hay ningún archivo "N" en lo sincronizado hoy -- se saltea


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


def sincronizar_programa_off(programa: dict, config: dict, callback_progreso=None) -> dict:
    """Descarga los bloques del programa OFF `programa` -- delega
    100% en core.sincronizador_drive.sincronizar_fuente_drive() (el
    MISMO motor ya probado para Enlatado tipo Drive), pasando la
    carpeta local CONFIGURADA de este programa en vez de la fija de
    Enlatado."""
    carpeta_local = (programa.get("carpeta_local") or "").strip()
    if not carpeta_local:
        return {"ok": False, "mensaje": "Sin carpeta local configurada para este programa."}
    return sincronizar_fuente_drive(
        programa.get("id"), programa.get("url_carpeta", ""), config,
        callback_progreso=callback_progreso, carpeta_destino_override=carpeta_local,
    )


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
