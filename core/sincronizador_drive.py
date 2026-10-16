"""
core/sincronizador_drive.py
--------------------------------------------------------
Sincroniza carpetas PÚBLICAS de Google Drive a una carpeta local, para
los slots ENLATADO de tipo "drive" (Configuración → Enlatados, ver
config/settings.py:listar_enlatados()). Corre como PROCESO APARTE
(mismo criterio de siempre en este proyecto — nunca threading), de
DOS formas:
  1. Suelto, sin argumentos, o vía cron a las 00:30 (ver
     core/actualizador.py: asegurar_tarea_cron_sincronizar_drive —
     ANTES de la de las 2am a propósito, "entre las 00 y 5am... a las
     00:30 preparar los enlatados"): sincroniza TODOS los slots tipo
     "drive" configurados, leyéndolos de disco.
         venv/bin/python3 -m core.sincronizador_drive
  2. Con `--slot-id`/`--url`, lanzado por el botón "🔄 Sincronizar
     ahora" de Configuración → Enlatados vía QProcess: sincroniza UN
     solo slot, imprimiendo líneas "PROGRESO hechos total"/
     "RESULTADO {json}" que gui/ventana_configuracion.py lee para una
     barra de progreso gráfica en vivo.

     Bug real corregido (reportado por Santiago probándolo: "al
     intentar descargar el drive se quedó 'trabado' el programa"):
     antes, ese botón llamaba a `sincronizar_fuente_drive()` DIRECTO
     en el hilo de la GUI — con una descarga real (red + análisis de
     audio por archivo), podía tardar lo suficiente como para
     sentirse colgado, mismo síntoma ya corregido antes para el
     reanálisis de biblioteca completa (ver core/reanalizador_batch.py,
     mismo mecanismo de QProcess, copiado acá). `--url` se pasa
     EXPLÍCITO (nunca releído de disco por `--slot-id`) para que
     "Sincronizar ahora" use el link recién tipeado en la UI, incluso
     antes de apretar "Guardar" — mismo criterio que ya usa el
     reanalizador con la tolerancia/umbral tipeados en pantalla.

Pedido explícito, con la estructura REAL confirmada por Santiago
(carpeta pública compartida con subcarpetas fijas, ej. "SA 4 BLOQUES",
con archivos tipo "BLOQUE 1.mp3".."BLOQUE 4.mp3" + una subcarpeta
"OTROS" de programas viejos que NUNCA hay que tocar ni reproducir):
por cada fuente, baja SOLO los archivos que están DIRECTO en la
carpeta configurada — nunca recursivo a ninguna subcarpeta, es lo que
excluye "OTROS" automáticamente, sin necesitar ninguna lista de
exclusión a mano — los ordena alfabético/natural (para que "BLOQUE 10"
no quede antes que "BLOQUE 2" el día que haya 10+), los analiza con el
mismo motor de silencio/nivelado de siempre, y los deja listos en
config/data/enlatados_drive/<id_slot>/.

"Si falla, sigue sonando lo de la semana pasada" (pedido explícito,
decisión de Santiago, "nunca reproducir en caliente, deben estar
preparados para su momento"): la carpeta final de un slot SOLO se
reemplaza si la sincronización de ESTA corrida terminó 100% completa,
con al menos 1 archivo de audio real — se arma todo en una carpeta
STAGING aparte (en el MISMO filesystem que el destino final, para que
el swap sea un rename atómico de verdad, nunca un cross-device copy a
medio camino) y recién al final se reemplaza la carpeta vieja. Un
fallo a mitad de camino (sin internet, Drive caído, carpeta vacía o
reestructurada) deja la carpeta de la semana anterior completamente
intacta.

**Límite real, honesto**: la biblioteca `gdown` (nueva dependencia
OPCIONAL, agregada a requirements.txt — degrada limpio si falta, igual
que pydub/ffmpeg/pyloudnorm en el resto de la app) solo funciona
contra Google Drive real — este entorno de desarrollo no tiene salida
de red hacia drive.google.com, así que la descarga real NUNCA se pudo
probar de punta a punta acá. El diseño (`gdown.download_folder(...,
skip_download=True)` para listar sin bajar nada, filtrando por `"/"
not in entrada.path` para quedarse solo con lo que está DIRECTO en la
carpeta pedida, `gdown.download(id=..., output=...)` por archivo) se
armó leyendo el código fuente real de gdown
(GoogleDriveFileToDownload con .id/.path/.local_path), no a ciegas —
pero falta la confirmación de Santiago corriendo esto contra su
carpeta real de Drive.
--------------------------------------------------------
"""

import json
import os
import re
import shutil
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

CARPETA_ENLATADOS_DRIVE = os.path.join(_RAIZ, "config", "data", "enlatados_drive")
EXTENSIONES_AUDIO = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
NOMBRE_ARCHIVO_ANALISIS = ".analisis.json"


def _clave_orden_natural(texto: str):
    """Orden alfabético pero NUMÉRICO para los dígitos (así "BLOQUE
    10" no queda antes que "BLOQUE 2" el día que haya 10+ bloques) —
    mismo criterio de robustez barata ya aplicado en otros rincones de
    este proyecto (ver core/buscador_duplicados.py)."""
    return [int(parte) if parte.isdigit() else parte.lower() for parte in re.split(r"(\d+)", texto)]


def _carpeta_destino(id_slot: str) -> str:
    return os.path.join(CARPETA_ENLATADOS_DRIVE, str(id_slot))


def listar_archivos_sincronizados(id_slot: str) -> list:
    """Archivos YA sincronizados (de una corrida anterior, nunca
    toca la red) para el slot `id_slot`, en orden de reproducción —
    esto es lo que usa GestorPublicidad en vivo. Cada entrada es un
    dict "tipo registro" (ruta/titulo/codigo/punto_inicio_ms/
    punto_fin_ms/ganancia_db) para poder reproducirse por el mismo
    camino que cualquier archivo de la biblioteca."""
    carpeta = _carpeta_destino(id_slot)
    if not os.path.isdir(carpeta):
        return []

    analisis_cacheado = {}
    ruta_analisis = os.path.join(carpeta, NOMBRE_ARCHIVO_ANALISIS)
    if os.path.isfile(ruta_analisis):
        try:
            with open(ruta_analisis, "r", encoding="utf-8") as f:
                analisis_cacheado = json.load(f)
        except (OSError, ValueError):
            analisis_cacheado = {}

    try:
        nombres = sorted(
            (n for n in os.listdir(carpeta) if n.lower().endswith(EXTENSIONES_AUDIO)),
            key=_clave_orden_natural,
        )
    except OSError:
        return []

    resultado = []
    for nombre in nombres:
        datos = analisis_cacheado.get(nombre, {})
        resultado.append({
            "ruta": os.path.join(carpeta, nombre),
            "titulo": os.path.splitext(nombre)[0],
            "codigo": "",
            "punto_inicio_ms": datos.get("punto_inicio_ms", 0),
            "punto_fin_ms": datos.get("punto_fin_ms"),
            "ganancia_db": datos.get("ganancia_db", 0.0),
        })
    return resultado


def sincronizar_fuente_drive(id_slot: str, url_carpeta: str, config: dict, callback_progreso=None) -> dict:
    """Baja los archivos DIRECTOS (nunca subcarpetas) de `url_carpeta`
    (una carpeta PÚBLICA de Google Drive) y los deja listos para
    `id_slot`. Nunca lanza excepción -- degrada con
    {"ok": False, "mensaje": ...} si algo sale mal, dejando la carpeta
    ya sincronizada de una corrida anterior COMPLETAMENTE INTACTA (ver
    docstring del módulo).

    `callback_progreso(hechos, total)`, opcional, se llama después de
    descargar+analizar CADA archivo -- mismo contrato que
    core.reanalizador_batch.ejecutar_reanalisis, para que la GUI pueda
    mostrar una barra de progreso real sin bloquearse."""
    if not url_carpeta:
        return {"ok": False, "mensaje": "Sin URL de carpeta configurada."}

    try:
        import gdown
    except ImportError:
        return {"ok": False, "mensaje": "Falta instalar gdown (con el venv activado: pip install gdown)."}

    from config.settings import parametros_nivelado
    from core.analizador_audio import analizar_audio

    carpeta_staging = None
    try:
        entradas = gdown.download_folder(url=url_carpeta, skip_download=True, quiet=True)
        if not entradas:
            return {"ok": False, "mensaje": "La carpeta de Drive está vacía, o no se pudo leer (¿el link sigue siendo público?)."}

        # SOLO archivos DIRECTO en la carpeta pedida -- nunca dentro de
        # una subcarpeta (ahí es donde vive "OTROS") -- `path` viene
        # relativo a la raíz pedida; un separador en el medio significa
        # que está anidado más adentro.
        candidatos = [
            entrada for entrada in entradas
            if "/" not in entrada.path.replace(os.sep, "/")
            and entrada.path.lower().endswith(EXTENSIONES_AUDIO)
        ]
        if not candidatos:
            return {
                "ok": False,
                "mensaje": "No se encontró ningún archivo de audio DIRECTO en esa carpeta "
                           "(¿están todos dentro de una subcarpeta?).",
            }

        candidatos.sort(key=lambda entrada: _clave_orden_natural(entrada.path))

        os.makedirs(CARPETA_ENLATADOS_DRIVE, exist_ok=True)
        # Staging en el MISMO directorio que el destino final -> mismo
        # filesystem -> el swap de más abajo es un rename atómico de
        # verdad, nunca un copy cross-device a medio camino.
        carpeta_staging = tempfile.mkdtemp(prefix=f".{id_slot}_staging_", dir=CARPETA_ENLATADOS_DRIVE)

        nivelado_activado, objetivo_lufs, techo_pico_dbfs = parametros_nivelado(config)
        reproduccion = config.get("reproduccion", {})
        total = len(candidatos)
        if callback_progreso is not None:
            callback_progreso(0, total)  # el total ya se conoce -- la barra arranca en 0/N, no "indeterminada"
        analisis = {}
        for indice, entrada in enumerate(candidatos):
            nombre = os.path.basename(entrada.path)
            destino = os.path.join(carpeta_staging, nombre)
            gdown.download(id=entrada.id, output=destino, quiet=True)
            if not os.path.isfile(destino) or os.path.getsize(destino) == 0:
                raise RuntimeError(f"no se pudo descargar '{nombre}' (archivo vacío o ausente tras la descarga)")

            resultado_analisis = analizar_audio(
                destino,
                tolerancia_silencio_segundos=reproduccion.get("tolerancia_silencio_segundos", 2.0),
                umbral_silencio_dbfs=reproduccion.get("umbral_silencio_dbfs", -50.0),
                objetivo_lufs=objetivo_lufs, techo_pico_dbfs=techo_pico_dbfs,
                nivelado_activado=nivelado_activado,
            )
            analisis[nombre] = {
                "punto_inicio_ms": resultado_analisis.get("punto_inicio_ms", 0),
                "punto_fin_ms": resultado_analisis.get("punto_fin_ms"),
                "ganancia_db": resultado_analisis.get("ganancia_db", 0.0),
            }
            if callback_progreso is not None:
                callback_progreso(indice + 1, total)

        with open(os.path.join(carpeta_staging, NOMBRE_ARCHIVO_ANALISIS), "w", encoding="utf-8") as f:
            json.dump(analisis, f, ensure_ascii=False)

        destino_final = _carpeta_destino(id_slot)
        if os.path.isdir(destino_final):
            shutil.rmtree(destino_final)
        os.replace(carpeta_staging, destino_final)
        carpeta_staging = None  # ya se movió -- el finally no debe limpiarlo

        return {
            "ok": True,
            "mensaje": f"{len(candidatos)} archivo(s) sincronizado(s).",
            "cantidad": len(candidatos),
        }

    except Exception as error:
        return {"ok": False, "mensaje": f"Error sincronizando: {error}"}
    finally:
        if carpeta_staging and os.path.isdir(carpeta_staging):
            shutil.rmtree(carpeta_staging, ignore_errors=True)


def sincronizar_todas_las_fuentes_drive() -> dict:
    """Sincroniza TODOS los slots ENLATADO de tipo "drive" configurados
    -- lo que corre la tarea de las 00:30 (ver core/actualizador.py:
    asegurar_tarea_cron_sincronizar_drive), pero también se puede
    correr suelta. Cada fuente se sincroniza de forma AISLADA -- un
    fallo en una nunca frena a las demás, mismo criterio de "nunca
    romper el lote por un ítem malo" ya establecido en el resto de
    este proyecto (ver core/musicalizador.py, core/reanalizador_batch.py)."""
    from config.settings import cargar_configuracion, listar_enlatados, registrar_evento, registrar_error

    config = cargar_configuracion()
    resultados = {}
    for slot in listar_enlatados(config):
        if slot.get("tipo") != "drive":
            continue
        id_slot = slot.get("id")
        nombre = slot.get("nombre") or id_slot
        try:
            resultado = sincronizar_fuente_drive(id_slot, slot.get("url_carpeta", ""), config)
        except Exception as error:
            resultado = {"ok": False, "mensaje": f"Excepción inesperada: {error}"}
        resultados[id_slot] = resultado
        if resultado["ok"]:
            registrar_evento(f"Sincronización Drive '{nombre}': {resultado['mensaje']}")
        else:
            registrar_error(f"Sincronización Drive '{nombre}' falló (se mantiene lo ya sincronizado antes, si había): {resultado['mensaje']}")
    return resultados


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Sincroniza los slots ENLATADO de tipo \"drive\" como proceso aparte.",
    )
    parser.add_argument(
        "--slot-id", default=None,
        help="Id de UN solo slot a sincronizar (junto con --url). Si se omite, sincroniza "
             "TODOS los slots tipo \"drive\" guardados en Configuración -- uso normal de la "
             "tarea nocturna de las 00:30.",
    )
    parser.add_argument(
        "--url", default=None,
        help="Link de la carpeta de Drive para --slot-id -- se usa EXPLÍCITO, nunca releído "
             "de disco, para que \"Sincronizar ahora\" tome el link recién tipeado aunque "
             "todavía no se haya apretado Guardar.",
    )
    args = parser.parse_args()

    if not args.slot_id:
        sincronizar_todas_las_fuentes_drive()
        return

    from config.settings import cargar_configuracion, registrar_evento, registrar_error

    def _progreso(hechos, total):
        # Línea parseable por la GUI (QProcess.readyReadStandardOutput)
        # -- también legible corriendo esto suelto en una terminal.
        print(f"PROGRESO {hechos} {total}", flush=True)

    config = cargar_configuracion()
    resultado = sincronizar_fuente_drive(args.slot_id, args.url or "", config, callback_progreso=_progreso)
    print(f"RESULTADO {json.dumps(resultado)}", flush=True)
    if resultado["ok"]:
        registrar_evento(f"Sincronización Drive (manual, slot {args.slot_id}): {resultado['mensaje']}")
    else:
        registrar_error(f"Sincronización Drive (manual, slot {args.slot_id}) falló: {resultado['mensaje']}")


if __name__ == "__main__":
    main()
