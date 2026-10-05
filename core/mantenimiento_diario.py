"""
core/mantenimiento_diario.py
--------------------------------------------------------
Mantenimiento diario automático — pedido explícito: "Como la radio se
detiene a las 00 horas todos los dias, programemos que a las 2am todos
los dias haga una 'depuración', limpie archivos residuales, verifique
todo como para dejar 'limpio' par el arranque luego de que se haga
PLAY otra vez a las 6. A las 2am incluso, si se puede, que cargue el
LOG en GitHub para que lo podamos analizar luego. Por ahora el
repositorio es público, pero no interesa."

Corre como PROCESO APARTE vía cron (ver
`core/actualizador.py:asegurar_tarea_cron_mantenimiento()`, que
instala/refresca la entrada de crontab SOLO al arrancar la app — mismo
criterio ya establecido para los lanzadores de escritorio: el botón
"Actualizar" de Configuración solo hace `git pull`, nunca
`instalar.sh`, así que cualquier setup a nivel de sistema operativo
(ahí, un ícono; acá, una entrada de crontab) tiene que hacerse desde
Python en el arranque — documentar "corré esto a mano" no sirve,
porque en la práctica eso nunca se ejecuta).

Se puede correr suelto para probar, igual que `reanalizador_batch`:
    venv/bin/python3 -m core.mantenimiento_diario

Tres tareas, cada una AISLADA con su propio try/except — un fallo en
una nunca frena a las demás (mismo criterio de "nunca romper el lote
por un ítem malo" ya establecido en el resto del proyecto):
  1. Limpieza de archivos residuales — SOLO los patrones que la propia
     app sabe que son temporales y de los que puede estar 100% segura
     sin arriesgar borrar algo real: los ".tmp" de escritura atómica
     (`config/data/.*.tmp`, dejados solo si un proceso murió a mitad
     de escribir — normalmente se autolimpian solos, ver
     `config/settings.py:_guardar_json_atomico`) y los
     "subida_remota_*" de una subida de archivo por control remoto
     que se interrumpió a mitad de camino (carpeta temp del sistema,
     ver `gui/main_window.py:_importar_archivo_remoto`). Umbral de
     antigüedad (1 hora) para nunca tocar un archivo que podría estar
     genuinamente en uso en ESTE MISMO instante — nunca el `.lock` de
     instancia única ni ningún otro archivo, la lista de patrones es
     intencionalmente angosta.
  2. Verificación — motor de audio (reusa
     `core.analizador_audio.verificar_motor_disponible()`, ya
     existente para el botón manual de Configuración → Diagnóstico) +
     espacio libre en disco (chequeo nuevo, liviano: una PC de radio
     corriendo 24/7 e importando música sin parar puede llenar el
     disco sin ningún aviso previo hasta que algo falla al escribir).
  3. Subida del log a GitHub (reusa
     `core.actualizador.subir_log_a_git()`, ya existente para el
     botón manual de Configuración → Diagnóstico — "el repositorio es
     público, pero no interesa", confirmado explícitamente por
     Santiago).

Deliberadamente AFUERA de esta ronda (documentado para no perderlo de
vista si se vuelve a preguntar): la rotación del log YA es automática
por tamaño en cada escritura
(`config/settings.py:_rotar_archivo_si_corresponde`), no hace falta
duplicarla acá; y no se toca nada de PipeWire/pactl — ya hubo varias
rondas de sagas reales ahí, y este script corre sin supervisión, de
noche, sin que Santiago pueda intervenir si algo saliera mal.
--------------------------------------------------------
"""

import glob
import os
import sys
import tempfile
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

ANTIGUEDAD_MINIMA_SEGUNDOS = 3600  # 1 hora -- nunca tocar algo recién creado
UMBRAL_DISCO_LIBRE_GB = 1.0


def _archivos_residuales_candidatos() -> list:
    """Candidatos a borrar — SOLO los dos patrones documentados en el
    docstring del módulo, filtrados por antigüedad. Nunca toca
    `config/data/*.lock` (el lock de instancia única) ni ningún otro
    archivo — la lista blanca es intencionalmente angosta, para nunca
    arriesgar borrar algo real."""
    from config.settings import DIRECTORIO_CONFIG

    ahora = time.time()
    candidatos = []
    patrones = (
        os.path.join(DIRECTORIO_CONFIG, ".*.tmp"),
        os.path.join(tempfile.gettempdir(), "subida_remota_*"),
    )
    for patron in patrones:
        for ruta in glob.glob(patron):
            try:
                if ahora - os.path.getmtime(ruta) >= ANTIGUEDAD_MINIMA_SEGUNDOS:
                    candidatos.append(ruta)
            except OSError:
                continue  # el archivo pudo desaparecer solo entre el glob y el stat
    return candidatos


def limpiar_archivos_residuales() -> dict:
    """Borra los candidatos encontrados. Nunca lanza excepción -- un
    archivo que no se pueda borrar (permisos, ya se borró por otra
    razón mientras tanto) se cuenta como fallido y se sigue con el
    resto, nunca aborta la limpieza entera."""
    candidatos = _archivos_residuales_candidatos()
    borrados, fallidos = [], []
    for ruta in candidatos:
        try:
            os.remove(ruta)
            borrados.append(ruta)
        except OSError:
            fallidos.append(ruta)
    return {"candidatos": len(candidatos), "borrados": borrados, "fallidos": fallidos}


def verificar_espacio_disco() -> dict:
    """Chequeo liviano de espacio libre en el disco de la app -- nunca
    bloquea nada, solo informa (el llamador decide si avisar según
    UMBRAL_DISCO_LIBRE_GB)."""
    import shutil
    uso = shutil.disk_usage(_RAIZ)
    return {
        "libre_gb": round(uso.free / (1024 ** 3), 2),
        "total_gb": round(uso.total / (1024 ** 3), 2),
    }


def ejecutar_mantenimiento_diario() -> dict:
    """Corre las 3 tareas en orden, cada una aislada con su propio
    try/except, y deja constancia DETALLADA en log_aplicacion.txt (vía
    registrar_evento/registrar_error) -- así el propio log que se sube
    a GitHub ya documenta qué pasó en el mantenimiento de esa noche,
    sin necesitar ningún archivo de reporte aparte."""
    from config.settings import registrar_evento, registrar_error, ARCHIVO_LOG
    from core.analizador_audio import verificar_motor_disponible
    from core.actualizador import subir_log_a_git

    resultado = {"limpieza": None, "disco": None, "motor": None, "log_subido": None}
    registrar_evento("Mantenimiento diario (2am): iniciado")

    try:
        resultado["limpieza"] = limpiar_archivos_residuales()
        registrar_evento(
            f"Mantenimiento diario: limpieza -- {len(resultado['limpieza']['borrados'])} "
            f"archivo(s) residual(es) borrados, {len(resultado['limpieza']['fallidos'])} "
            f"fallido(s) (de {resultado['limpieza']['candidatos']} candidato(s) encontrados)"
        )
    except Exception as error:
        registrar_error(f"Mantenimiento diario: la limpieza de residuales falló -- {error}")

    try:
        resultado["disco"] = verificar_espacio_disco()
        libre = resultado["disco"]["libre_gb"]
        if libre < UMBRAL_DISCO_LIBRE_GB:
            registrar_error(
                f"Mantenimiento diario: espacio libre en disco BAJO -- {libre}GB "
                f"(de {resultado['disco']['total_gb']}GB totales, umbral {UMBRAL_DISCO_LIBRE_GB}GB)"
            )
        else:
            registrar_evento(f"Mantenimiento diario: espacio libre en disco OK -- {libre}GB")
    except Exception as error:
        registrar_error(f"Mantenimiento diario: la verificación de espacio en disco falló -- {error}")

    try:
        diagnostico = verificar_motor_disponible()
        resultado["motor"] = diagnostico
        if diagnostico.get("prueba_ok"):
            registrar_evento("Mantenimiento diario: motor de audio (recorte de silencio) OK")
        else:
            registrar_error(
                "Mantenimiento diario: motor de audio con problemas -- "
                f"{diagnostico.get('mensaje') or '(sin detalle)'}"
            )
    except Exception as error:
        registrar_error(f"Mantenimiento diario: la verificación del motor de audio falló -- {error}")

    try:
        exito, mensaje = subir_log_a_git(ARCHIVO_LOG)
        resultado["log_subido"] = {"exito": exito, "mensaje": mensaje}
        registrar_evento(
            f"Mantenimiento diario: subida del log a GitHub -- {'OK' if exito else 'FALLÓ'}: {mensaje}"
        )
    except Exception as error:
        registrar_error(f"Mantenimiento diario: la subida del log a GitHub falló -- {error}")

    registrar_evento("Mantenimiento diario (2am): terminado")
    return resultado


def main():
    ejecutar_mantenimiento_diario()


if __name__ == "__main__":
    main()
