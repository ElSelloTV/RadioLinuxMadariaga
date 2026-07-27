"""
core/reanalizador_batch.py
--------------------------------------------------------
Reanálisis de la biblioteca COMPLETA, corrido como PROCESO APARTE —
pedido explícito ("tengo 9800 elementos... se trabó por obvias
razones, necesitamos hacerlo con otro proceso aparte, que me indique
el progreso"). Esta app nunca usó threading (ver CLAUDE.md) — igual
que EasyEffects/git/wmctrl/etc., lo async acá es un `QProcess`
separado, nunca un `QThread`.

Corre de DOS formas, con la MISMA lógica (`ejecutar_reanalisis`):
  1. Como script suelto, útil para el primer pase grande "por fuera"
     que pidió Santiago, con progreso real en la terminal:
         venv/bin/python3 -m core.reanalizador_batch
  2. Lanzado por la propia app (Configuración → "Reanalizar
     biblioteca") vía QProcess — imprime líneas de progreso
     parseables a stdout que gui/ventana_configuracion.py lee para
     actualizar una barra de progreso gráfica en vivo, sin bloquear
     la interfaz ni un instante (a diferencia de la versión anterior,
     que corría en el propio hilo de la GUI y podía "trabar todo el
     programa" varios minutos con una biblioteca de miles de
     archivos).

Bug real corregido de paso, encontrado con el reporte real de
Santiago ("me sale un ícono de aviso ahora en TODOS los archivos
musicales" tras un reanálisis con el motor de audio roto): un fallo
de análisis (`analizado=False`) YA NO pisa las marcas IN/OUT que un
archivo ya tenía calculadas de una vuelta anterior exitosa — un
reanálisis nunca debe ser un RETROCESO. Si el archivo nunca tuvo
marcas buenas, el fallo se guarda igual (para que el ícono de aviso
en Ventana 3 lo señale).

Guardado INCREMENTAL (cada `GUARDAR_CADA` archivos, no solo al
final): con una biblioteca de miles de archivos, un pase completo
puede tardar minutos — guardar cada tanto asegura que interrumpir a
mitad de camino (Ctrl+C, cerrar la terminal, matar el proceso) pierda
como mucho el último tramo sin guardar, nunca todo el trabajo ya
hecho.
--------------------------------------------------------
"""

import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

GUARDAR_CADA = 25


def _contar_elegibles(categorias: list) -> int:
    contador = 0

    def _contar(categoria):
        nonlocal contador
        for registro in categoria.get("archivos", []):
            ruta = registro.get("ruta")
            if ruta and os.path.exists(ruta):
                contador += 1
        for subcategoria in categoria.get("subcategorias", []):
            _contar(subcategoria)

    for categoria in categorias:
        _contar(categoria)
    return contador


def ejecutar_reanalisis(config: dict, callback_progreso=None) -> dict:
    """`callback_progreso(hechos, total)`, opcional, se llama después
    de procesar CADA archivo elegible -- el total ya se conoce de
    antemano (pre-conteo barato, solo `os.path.exists`, antes de pagar
    el costo real de pydub/ffmpeg). Devuelve el mismo desglose que
    `config.settings.reanalizar_biblioteca()`
    (total/analizados/fallidos/musica_total/musica_analizados), más
    `preservados` (archivos cuyo análisis falló esta vez pero que ya
    tenían marcas buenas de antes -- NUNCA se destruyen)."""
    from config.settings import (
        cargar_biblioteca, guardar_biblioteca, registrar_error, tolerancia_silencio_para_genero,
    )
    from core.analizador_audio import analizar_audio

    def _guardar_sin_frenar_el_lote(categorias):
        # Defensivo (mismo criterio ya establecido en el proyecto:
        # "nunca confiar en una sola capa de protección"): un guardado
        # periódico que falla (ej. una carrera puntual con otro
        # escritor, ya blindada en _guardar_json_atomico, o cualquier
        # otro problema transitorio de disco) NO debe tirar abajo todo
        # el reanálisis -- perdería en memoria el trabajo de miles de
        # archivos ya procesados. Se registra el error y se sigue; el
        # PRÓXIMO checkpoint (GUARDAR_CADA archivos después, o el
        # guardado final) vuelve a intentarlo.
        try:
            guardar_biblioteca(categorias)
        except Exception as error:
            registrar_error(f"reanalizador_batch: guardado periódico falló, se sigue igual: {error}")

    categorias = cargar_biblioteca()
    total = _contar_elegibles(categorias)
    stats = {
        "total": 0, "analizados": 0, "fallidos": 0, "preservados": 0,
        "musica_total": 0, "musica_analizados": 0,
    }
    contador_sin_guardar = 0

    def _procesar_categoria(categoria: dict):
        nonlocal contador_sin_guardar
        for registro in categoria.get("archivos", []):
            ruta = registro.get("ruta")
            if not ruta or not os.path.exists(ruta):
                continue

            tenia_marcas_buenas = registro.get("analizado") is True
            tolerancia = tolerancia_silencio_para_genero(config, registro.get("genero"))
            umbral = config.get("reproduccion", {}).get("umbral_silencio_dbfs", -40.0)
            analisis = analizar_audio(ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral)

            stats["total"] += 1
            es_musica = registro.get("genero") == "Musica"
            if es_musica:
                stats["musica_total"] += 1

            if analisis["analizado"]:
                registro["punto_inicio_ms"] = analisis["punto_inicio_ms"]
                registro["punto_fin_ms"] = analisis["punto_fin_ms"] or None
                registro["ganancia_db"] = analisis["ganancia_db"]
                registro["analizado"] = True
                stats["analizados"] += 1
                if es_musica:
                    stats["musica_analizados"] += 1
            elif tenia_marcas_buenas:
                # Fallo esta vuelta, pero YA tenía marcas reales de
                # antes -- se preservan intactas, nunca se pisan con
                # el fallback neutro.
                stats["preservados"] += 1
            else:
                registro["punto_inicio_ms"] = 0
                registro["punto_fin_ms"] = None
                registro["ganancia_db"] = 0.0
                registro["analizado"] = False
                stats["fallidos"] += 1

            contador_sin_guardar += 1
            if contador_sin_guardar >= GUARDAR_CADA:
                _guardar_sin_frenar_el_lote(categorias)
                contador_sin_guardar = 0
            if callback_progreso is not None:
                callback_progreso(stats["total"], total)
        for subcategoria in categoria.get("subcategorias", []):
            _procesar_categoria(subcategoria)

    for categoria in categorias:
        _procesar_categoria(categoria)

    _guardar_sin_frenar_el_lote(categorias)
    return stats


def main():
    from config.settings import cargar_configuracion

    parser = argparse.ArgumentParser(
        description="Reanaliza toda la biblioteca (recorte de silencio / nivelado) como proceso aparte.",
    )
    parser.add_argument("--tolerancia-general", type=float, default=None,
                         help="Tolerancia de silencio en segundos (Música/Artística/Pisador)")
    parser.add_argument("--tolerancia-v1", type=float, default=None,
                         help="Tolerancia de silencio en segundos (Publicidad/Separador/HTH)")
    parser.add_argument("--umbral", type=float, default=None, help="Umbral de silencio en dBFS")
    args = parser.parse_args()

    config = cargar_configuracion()
    if args.tolerancia_general is not None:
        config["reproduccion"]["tolerancia_silencio_segundos"] = args.tolerancia_general
    if args.tolerancia_v1 is not None:
        config["reproduccion"]["tolerancia_silencio_v1_segundos"] = args.tolerancia_v1
    if args.umbral is not None:
        config["reproduccion"]["umbral_silencio_dbfs"] = args.umbral

    def _progreso(hechos, total):
        # Línea parseable por la GUI (QProcess.readyReadStandardOutput)
        # -- también legible corriendo esto suelto en una terminal.
        print(f"PROGRESO {hechos} {total}", flush=True)

    stats = ejecutar_reanalisis(config, callback_progreso=_progreso)
    print(f"RESULTADO {json.dumps(stats)}", flush=True)


if __name__ == "__main__":
    main()
