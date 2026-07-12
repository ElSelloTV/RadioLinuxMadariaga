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
ARCHIVO_BIBLIOTECA = os.path.join(DIRECTORIO_CONFIG, "biblioteca.json")
ARCHIVO_PLAYLIST_EMISION = os.path.join(DIRECTORIO_CONFIG, "playlist_emision.json")
ARCHIVO_LOG = os.path.join(DIRECTORIO_CONFIG, "log_aplicacion.txt")
TAMAÑO_MAXIMO_LOG_BYTES = 2 * 1024 * 1024  # 2 MB — más allá de esto, rota a .anterior.txt

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
        "umbral_silencio_dbfs": -40.0,
        "pisador_bajada_db": -4.0,
    },
    "general": {
        "confirmar_antes_de_eliminar": True,
        "mostrar_segundos_en_reloj": True,
        "tema": "oscuro",
    },
    "apariencia": {
        # Colores por género (Ventana 3, columna "Categoría", y el
        # Pisador anidado en Ventana 2/Auxiliar). None = sin color.
        # Editable desde Configuración → Apariencia (pedido explícito).
        "colores_genero": {
            "Musica": "#2e7d32",
            "Publicidad": "#f9a825",
            "Separador": "#e65100",
            "Pisador": "#6a1b9a",
            "Artistica": "#1565c0",
        },
    },
}


def _asegurar_directorio():
    os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)


def _guardar_json_atomico(ruta: str, datos):
    """Escribe a un archivo temporal y lo renombra ENCIMA del
    definitivo (os.replace es atómico en Linux) — así un corte de luz
    o un apagado forzoso a mitad de la escritura nunca deja el
    archivo corrupto/truncado: o queda la versión anterior completa,
    o la nueva completa, nunca algo a medio escribir. Toda la
    persistencia de la app (config, biblioteca, programaciones) pasa
    por acá."""
    _asegurar_directorio()
    archivo_temporal = f"{ruta}.tmp"
    with open(archivo_temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(archivo_temporal, ruta)


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
    _guardar_json_atomico(ARCHIVO_CONFIG_GENERAL, config)


def _rotar_log_si_corresponde():
    """Si el log ya pasó TAMAÑO_MAXIMO_LOG_BYTES, lo archiva como
    .anterior.txt (pisando la rotación previa) y arranca uno nuevo —
    para poder dejar el log de "todo tipo de error y funcionamiento"
    activado siempre sin que crezca sin límite en una notebook con
    disco modesto."""
    try:
        if os.path.exists(ARCHIVO_LOG) and os.path.getsize(ARCHIVO_LOG) > TAMAÑO_MAXIMO_LOG_BYTES:
            archivo_anterior = ARCHIVO_LOG.replace(".txt", ".anterior.txt")
            os.replace(ARCHIVO_LOG, archivo_anterior)
    except OSError:
        pass


def _escribir_log(nivel: str, mensaje: str):
    _asegurar_directorio()
    _rotar_log_si_corresponde()
    from datetime import datetime
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{marca_tiempo}] [{nivel}] {mensaje}\n")
    except OSError:
        pass  # si ni el log se puede escribir, no hay nada más que hacer acá


def registrar_error(mensaje: str):
    """Log de errores (config/data/log_aplicacion.txt) — pensado para
    poder depurar sin acceso directo a la PC de Santiago: rotativo,
    con nivel y timestamp. Se puede subir manualmente a GitHub desde
    Configuración → Diagnóstico (core/actualizador.subir_log_a_git)."""
    _escribir_log("ERROR", mensaje)


def registrar_evento(mensaje: str):
    """Log de funcionamiento normal (play/pausa/stop/config aplicada,
    etc.), mismo archivo que registrar_error pero nivel INFO — para
    poder reconstruir la secuencia de acciones previa a un problema
    reportado (ej. "el play no respondía")."""
    _escribir_log("INFO", mensaje)


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
    _guardar_json_atomico(ARCHIVO_PROGRAMACION, datos)


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


# ----------------------------------------------------------------------
# Biblioteca (Ventana 3 - Explorador): categorías + archivos
# ----------------------------------------------------------------------
# Estructura de config/data/biblioteca.json: lista de categorías de
# primer nivel, cada una:
#   {"nombre": str, "archivos": [registro, ...], "subcategorias": [categoría, ...]}
# (recursivo, sin límite de niveles — mismo modelo que el árbol de
# gui/ventana_explorador.py). Se guarda ante CADA alta/baja/cambio,
# no solo al cerrar la app: un corte de luz o apagado forzoso no debe
# perder nada de lo cargado.

def cargar_biblioteca() -> list:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_BIBLIOTECA):
        return []
    try:
        with open(ARCHIVO_BIBLIOTECA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo biblioteca: {error}")
        return []


def guardar_biblioteca(categorias: list):
    _guardar_json_atomico(ARCHIVO_BIBLIOTECA, categorias)


# ----------------------------------------------------------------------
# Playlist de Ventana 2 (Emisión): antes era efímera y se perdía al
# cerrar o ante un corte de luz — pedido explícito de Santiago para
# poder ir probando con música real sin perder el armado cada vez.
# ----------------------------------------------------------------------
# Estructura de config/data/playlist_emision.json:
#   {"items": [{"titulo", "duracion", "codigo", "ruta", "pisador_ruta"}, ...],
#    "fila_armada": int, "fila_siguiente": int}
# Se guarda ante cada alta/baja/reordenada/marcado, igual que la
# biblioteca — no solo al cerrar la app.

PLAYLIST_EMISION_VACIA = {"items": [], "fila_armada": -1, "fila_siguiente": -1}


def cargar_playlist_emision() -> dict:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_PLAYLIST_EMISION):
        return dict(PLAYLIST_EMISION_VACIA)
    try:
        with open(ARCHIVO_PLAYLIST_EMISION, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return {**PLAYLIST_EMISION_VACIA, **datos}
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo playlist de Emisión: {error}")
        return dict(PLAYLIST_EMISION_VACIA)


def guardar_playlist_emision(datos: dict):
    _guardar_json_atomico(ARCHIVO_PLAYLIST_EMISION, datos)
