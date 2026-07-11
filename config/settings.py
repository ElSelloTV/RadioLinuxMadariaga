"""
config/settings.py
--------------------------------------------------------
Gestión liviana de configuración persistente en JSON.
Este módulo SÍ está operativo desde esta primera entrega,
ya que la GUI necesita poder guardar/leer rutas, tiempos de
fade y dispositivos de audio sin depender del motor todavía.
--------------------------------------------------------
"""

import json
import os

DIRECTORIO_CONFIG = os.path.join(os.path.dirname(__file__), "data")
ARCHIVO_CONFIG_GENERAL = os.path.join(DIRECTORIO_CONFIG, "config_general.json")
ARCHIVO_PROGRAMACION = os.path.join(DIRECTORIO_CONFIG, "programacion.json")
ARCHIVO_LOG = os.path.join(DIRECTORIO_CONFIG, "log_emision.txt")

CONFIG_POR_DEFECTO = {
    "audio": {
        "dispositivo_master": "default",
        "dispositivo_preescucha": "default",
        "volumen_master": 100,
        "volumen_preescucha": 100,
    },
    "fade": {
        "crossfade_activado": True,
        "duracion_fade_segundos": 3.0,
    },
    "rutas": {
        "biblioteca_musical": os.path.expanduser("~/Musica"),
        "biblioteca_publicidad": os.path.expanduser("~/Publicidad"),
        "carpeta_logs": DIRECTORIO_CONFIG,
    },
    "reproduccion": {
        "avanzar_automaticamente_en_error": True,
        "reintentos_antes_de_detener": 3,
        "repetir_lista_al_finalizar": True,
        "modo_automatico_al_iniciar": False,
        "tolerancia_silencio_segundos": 2.0,
    },
    "general": {
        "confirmar_antes_de_eliminar": True,
        "mostrar_segundos_en_reloj": True,
        "tema": "oscuro",
    },
}


def _asegurar_directorio():
    os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)


def _fusionar_con_defecto(config_guardada: dict) -> dict:
    """Completa con los valores por defecto cualquier clave/sección nueva
    que no exista todavía en un config_general.json guardado con una
    versión anterior de la app (evita KeyError al agregar settings)."""
    resultado = {}
    for seccion, valores_defecto in CONFIG_POR_DEFECTO.items():
        valores_guardados = config_guardada.get(seccion, {})
        resultado[seccion] = {**valores_defecto, **valores_guardados}
    return resultado


def cargar_configuracion() -> dict:
    """Carga config_general.json o crea uno con valores por defecto."""
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_CONFIG_GENERAL):
        guardar_configuracion(CONFIG_POR_DEFECTO)
        return dict(CONFIG_POR_DEFECTO)

    try:
        with open(ARCHIVO_CONFIG_GENERAL, "r", encoding="utf-8") as f:
            return _fusionar_con_defecto(json.load(f))
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo config general: {error}")
        return dict(CONFIG_POR_DEFECTO)


def guardar_configuracion(config: dict):
    _asegurar_directorio()
    with open(ARCHIVO_CONFIG_GENERAL, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def registrar_error(mensaje: str):
    """Log simple de errores a texto plano (config/data/log_emision.txt)."""
    _asegurar_directorio()
    from datetime import datetime
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{marca_tiempo}] {mensaje}\n")


# ----------------------------------------------------------------------
# Programaciones (Programador de emisión)
# ----------------------------------------------------------------------
# Estructura de config/data/programacion.json:
# {
#   "dias_semana": {
#       "lunes": {"nombre": "...", "bloques": [...]},
#       ...
#   },
#   "fechas_especificas": {
#       "2026-07-15": {"nombre": "...", "bloques": [...]}
#   }
# }
#
# Regla de superposición: una fecha específica SIEMPRE prevalece
# sobre el patrón semanal general para ese mismo día calendario.
# Ej: si hay una programación general para "lunes" y además se
# graba una programación específica para el lunes 2026-07-13,
# ese día puntual se emite la específica, no la general.

NOMBRES_DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def cargar_programaciones() -> dict:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_PROGRAMACION):
        estructura_vacia = {"dias_semana": {}, "fechas_especificas": {}}
        guardar_programaciones(estructura_vacia)
        return estructura_vacia

    try:
        with open(ARCHIVO_PROGRAMACION, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo programaciones: {error}")
        datos = {}

    datos.setdefault("dias_semana", {})
    datos.setdefault("fechas_especificas", {})
    return datos


def guardar_programaciones(datos: dict):
    _asegurar_directorio()
    with open(ARCHIVO_PROGRAMACION, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def guardar_programacion(nombre: str, bloques: list, dias_semana: list = None, fecha_especifica: str = None):
    """Guarda una programación (lista de bloques horarios) para:
    - una fecha puntual (fecha_especifica='YYYY-MM-DD'), y/o
    - uno o varios días de la semana (dias_semana=['lunes', 'martes', ...]).
    """
    datos = cargar_programaciones()
    contenido = {"nombre": nombre, "bloques": bloques}

    if fecha_especifica:
        datos["fechas_especificas"][fecha_especifica] = contenido

    for dia in (dias_semana or []):
        if dia in NOMBRES_DIAS_SEMANA:
            datos["dias_semana"][dia] = contenido

    guardar_programaciones(datos)


def listar_programaciones() -> list:
    """Devuelve todas las programaciones guardadas, para poblar el
    selector del botón "Cargar" del Programador.

    Cada entrada: (tipo, clave, nombre)
      tipo  -> "dia" | "fecha"
      clave -> "lunes".."domingo"  |  "YYYY-MM-DD"
      nombre -> nombre visible que le puso el usuario al guardar
    """
    datos = cargar_programaciones()
    resultado = []
    for dia in NOMBRES_DIAS_SEMANA:
        contenido = datos["dias_semana"].get(dia)
        if contenido:
            resultado.append(("dia", dia, contenido.get("nombre", dia)))
    for fecha_clave, contenido in sorted(datos["fechas_especificas"].items()):
        resultado.append(("fecha", fecha_clave, contenido.get("nombre", fecha_clave)))
    return resultado


def obtener_programacion(tipo: str, clave: str) -> dict | None:
    """Recupera el contenido completo (nombre + bloques) de una
    programación puntual, dado lo devuelto por listar_programaciones()."""
    datos = cargar_programaciones()
    if tipo == "dia":
        return datos["dias_semana"].get(clave)
    if tipo == "fecha":
        return datos["fechas_especificas"].get(clave)
    return None


def resolver_programacion_del_dia(fecha) -> dict | None:
    """Devuelve la programación vigente para `fecha` (objeto date),
    aplicando la regla: fecha específica > patrón semanal general.
    Devuelve None si no hay ninguna programación cargada para ese día.
    """
    datos = cargar_programaciones()
    clave_fecha = fecha.isoformat()

    if clave_fecha in datos["fechas_especificas"]:
        return datos["fechas_especificas"][clave_fecha]

    nombre_dia = NOMBRES_DIAS_SEMANA[fecha.weekday()]
    return datos["dias_semana"].get(nombre_dia)
