"""
config/settings.py
--------------------------------------------------------
Gestión liviana de configuración persistente en JSON.
Este módulo SÍ está operativo desde esta primera entrega,
ya que la GUI necesita poder guardar/leer rutas, tiempos de
fade y dispositivos de audio sin depender del motor todavía.
--------------------------------------------------------
"""

import copy
import json
import os
from datetime import date

DIRECTORIO_CONFIG = os.path.join(os.path.dirname(__file__), "data")
ARCHIVO_CONFIG_GENERAL = os.path.join(DIRECTORIO_CONFIG, "config_general.json")
ARCHIVO_PROGRAMACION = os.path.join(DIRECTORIO_CONFIG, "programacion.json")
ARCHIVO_BIBLIOTECA = os.path.join(DIRECTORIO_CONFIG, "biblioteca.json")
ARCHIVO_PLAYLIST_EMISION = os.path.join(DIRECTORIO_CONFIG, "playlist_emision.json")
ARCHIVO_PLAYLIST_PUBLICIDAD = os.path.join(DIRECTORIO_CONFIG, "playlist_publicidad.json")
ARCHIVO_MUSICALIZADOR = os.path.join(DIRECTORIO_CONFIG, "musicalizador.json")
ARCHIVO_ULTIMO_FMT = os.path.join(DIRECTORIO_CONFIG, "ultimo_fmt.json")
ARCHIVO_LOG = os.path.join(DIRECTORIO_CONFIG, "log_aplicacion.txt")
ARCHIVO_HISTORIAL_REPRODUCCION = os.path.join(DIRECTORIO_CONFIG, "historial_reproduccion.txt")
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
        # "duracion_fade_segundos" queda solo por compatibilidad con
        # instalaciones viejas (ya no se usa) — reemplazada por el par
        # de abajo, mismo criterio in/out separado que ya tenía
        # Ventana 1 (duracion_fade_out_v1_ms / duracion_fade_in_declick_v1_ms).
        "duracion_fade_segundos": 3.0,
        # Pedido explícito ("perfeccioná el fundido... el inicio sin
        # silencio inicial con un fundido muy breve de 400ms, el final
        # un fundido de 500ms sin silencio"): fundido de Ventana 2
        # (Emisión/crossfade entre ítems), en MILISEGUNDOS.
        "duracion_fade_in_v2_ms": 400,
        "duracion_fade_out_v2_ms": 500,
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
        # "modo_automatico_al_iniciar" se retiró a pedido explícito:
        # el botón AUTOMÁTICO ahora arranca SIEMPRE encendido al abrir
        # (robustez de emisión) — la clave vieja puede seguir presente
        # en config_general.json de instalaciones anteriores y se
        # ignora sin romper nada.
        "tolerancia_silencio_segundos": 2.0,
        "umbral_silencio_dbfs": -40.0,
        "pisador_bajada_db": -4.0,
        # Pedido explícito ("corte de silencio estricto... que sea
        # bien pegados uno a otro"): Publicidad y Separadores (el
        # material de Ventana 1) se analizan con esta tolerancia, MÁS
        # ESTRICTA que la general — 0 por defecto, sin margen extra de
        # silencio, a diferencia de "tolerancia_silencio_segundos" de
        # arriba (que sí deja un colchón a propósito para Música). Ver
        # config/settings.py:tolerancia_silencio_para_genero().
        "tolerancia_silencio_v1_segundos": 0.0,
        # Fade OUT automático y corto entre tandas de Ventana 1
        # (pedido explícito, en MILISEGUNDOS — a diferencia de
        # "duracion_fade_segundos" de Fade/Transiciones, que es en
        # segundos y es para el crossfade/fundido manual de Ventana 2).
        "duracion_fade_out_v1_ms": 500,
        # Pedido explícito, ronda posterior ("perfeccioná el fundido...
        # el inicio sin silencio inicial con un fundido muy breve de
        # 400ms"): esto YA NO es un simple anti-click de milisegundos,
        # es el fade-in real y corto de Ventana 1 — la ronda anterior
        # que lo había sacado ("que los temas suenen más enganchados,
        # sin fade-in") quedó reemplazada por este pedido explícito
        # más reciente. Ver MotorAudio.reproducir(duracion_declick_ms=...).
        "duracion_fade_in_declick_v1_ms": 400,
        # Pedido explícito ("sistema de buffer para evitar tartamudeo...
        # un inicio de milisegundos de retardo no afecta en mucho,
        # configurable"): ver core/audio_engine.py:_argumentos_vlc().
        # Sube el buffer de lectura/decodificación de libVLC — más alto
        # da más margen anti-tartamudeo a costa de un arranque
        # levemente más lento. Requiere reabrir la app para aplicar
        # (es un argumento de instancia de libVLC, fijo al crearla).
        "duracion_buffer_caching_ms": 1000,
        # Retardo (ms) antes de reforzar seek/volumen tras un play() —
        # ver MotorAudio.reproducir()/_tras_arranque. Mismo valor ya
        # probado internamente sin problemas.
        "retardo_arranque_ms": 150,
    },
    "general": {
        "confirmar_antes_de_eliminar": True,
        "mostrar_segundos_en_reloj": True,
        "tema": "oscuro",
        # Pedido explícito: nombre de emisora editable, se muestra a
        # la izquierda del reloj de día/hora en el toolbar — antes era
        # un texto fijo ("RADIO TUYÚ FM 92.5") repetido en cada panel.
        "nombre_emisora": "RADIO TUYÚ FM 92.5",
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
            "HTH": "#00838f",
        },
    },
    # Comando HTH (Hora-Temperatura-Humedad) — coordenadas para la
    # consulta de clima en vivo (ver core/clima_meteo.py). Default:
    # General Juan Madariaga, Buenos Aires, Argentina. Editable en
    # Configuración → General.
    "clima": {
        "latitud": -37.0167,
        "longitud": -57.1167,
    },
}


def _asegurar_directorio():
    os.makedirs(DIRECTORIO_CONFIG, exist_ok=True)


def _guardar_json_atomico(ruta: str, datos, compacto: bool = False):
    """Escribe a un archivo temporal y lo renombra ENCIMA del
    definitivo (os.replace es atómico en Linux) — así un corte de luz
    o un apagado forzoso a mitad de la escritura nunca deja el
    archivo corrupto/truncado: o queda la versión anterior completa,
    o la nueva completa, nunca algo a medio escribir. Toda la
    persistencia de la app (config, biblioteca, programaciones) pasa
    por acá.

    `compacto=True` (pedido explícito, biblioteca de ~10-12mil
    archivos: "el JSON parece trabarse... revisá el buffer") — sin
    `indent=2`, `json.dump()` serializa bastante más rápido y el
    archivo resultante pesa una fracción de lo que pesaba con el
    pretty-print (cada nivel de indentación repite espacios en CADA
    una de las miles de líneas) — con una biblioteca grande esto
    reduce tanto el tiempo de escritura como el de `fsync()` (que
    tiene que volcar más bytes a disco cuanto más grande el archivo).
    `guardar_biblioteca()` es la única que lo usa — nadie edita
    biblioteca.json a mano, a diferencia de config_general.json o
    programacion.json, que se quedan legibles con indent=2 por si
    Santiago necesita mirarlos/editarlos directo alguna vez."""
    _asegurar_directorio()
    archivo_temporal = f"{ruta}.tmp"
    with open(archivo_temporal, "w", encoding="utf-8") as f:
        if compacto:
            json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
        else:
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
    """Carga config_general.json o crea uno con valores por defecto.

    Bug real corregido (trampa clásica de Python): `dict(CONFIG_POR_DEFECTO)`
    es una copia SOMERA — las secciones anidadas (`audio`, `fade`,
    etc.) seguían siendo el MISMO objeto que `CONFIG_POR_DEFECTO`. Todo
    código que hace `cfg = cargar_configuracion(); cfg["audio"][clave]
    = valor` (ej. `VentanaConfiguracion._guardar_y_cerrar()`) en una
    instalación TOTALMENTE nueva (sin `config_general.json` todavía)
    terminaba mutando el propio `CONFIG_POR_DEFECTO` global en memoria
    — silencioso, sin romper nada visible de inmediato, pero
    corrompiendo los valores por defecto para el resto del proceso.
    `copy.deepcopy()` evita esto: cada llamada devuelve secciones
    anidadas 100% independientes."""
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_CONFIG_GENERAL):
        guardar_configuracion(CONFIG_POR_DEFECTO)
        return copy.deepcopy(CONFIG_POR_DEFECTO)

    try:
        with open(ARCHIVO_CONFIG_GENERAL, "r", encoding="utf-8") as f:
            return _fusionar_con_defecto(json.load(f))
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo config general: {error}")
        return copy.deepcopy(CONFIG_POR_DEFECTO)


def guardar_configuracion(config: dict):
    _guardar_json_atomico(ARCHIVO_CONFIG_GENERAL, config)


# Géneros del material típico de Ventana 1 (pedido explícito: "hay
# spot publicitarios y separadores que tienen algunos segundos o
# milisegundos de silencio... sacalos absolutamente"). "HTH" (clips de
# voz del Comando HTH, ver core/hth.py) se agrega acá también — un
# corte de silencio flojo entre "HORA 14" y "MINUTOS 30" sonaría como
# un bache raro en medio del anuncio, así que conviene el mismo
# recorte estricto sin colchón.
GENEROS_CORTE_ESTRICTO = ("Publicidad", "Separador", "HTH")


def tolerancia_silencio_para_genero(config: dict, genero: str) -> float:
    """Publicidad y Separadores usan la tolerancia ESTRICTA
    (`tolerancia_silencio_v1_segundos`, 0 por defecto — sin margen) en
    vez de la general (`tolerancia_silencio_segundos`, que deja a
    propósito un colchón de silencio para Música y el resto). Se
    aplica en el momento de ANALIZAR el archivo (Ventana 3, al
    agregar/reemplazar), no en cada reproducción."""
    reproduccion = config.get("reproduccion", {})
    if genero in GENEROS_CORTE_ESTRICTO:
        return reproduccion.get("tolerancia_silencio_v1_segundos", 0.0)
    return reproduccion.get("tolerancia_silencio_segundos", 2.0)


def _rotar_archivo_si_corresponde(ruta: str):
    """Si `ruta` ya pasó TAMAÑO_MAXIMO_LOG_BYTES, la archiva como
    .anterior.txt (pisando la rotación previa) y arranca una nueva —
    mismo mecanismo para cualquier archivo de log rotativo (aplicación
    e historial de reproducción), para que ninguno crezca sin límite
    en una notebook con disco modesto."""
    try:
        if os.path.exists(ruta) and os.path.getsize(ruta) > TAMAÑO_MAXIMO_LOG_BYTES:
            os.replace(ruta, ruta.replace(".txt", ".anterior.txt"))
    except OSError:
        pass


def _rotar_log_si_corresponde():
    _rotar_archivo_si_corresponde(ARCHIVO_LOG)


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


def registrar_reproduccion(ventana: str, titulo: str, codigo: str = "", ruta: str = ""):
    """Historial de reproducción PERSISTENTE (pedido explícito,
    inspirado en Dinesat) — a diferencia del ícono "ya reproducido"
    (gui/styles.py:ROL_YA_REPRODUCIDO, que solo dura la sesión actual
    y se pierde al reiniciar), esto queda escrito en disco: qué sonó,
    cuándo y en qué ventana, consultable después (Configuración →
    Diagnóstico → "Ver historial de reproducción"). Mismo patrón
    rotativo que log_aplicacion.txt, nunca crece sin límite."""
    _asegurar_directorio()
    _rotar_archivo_si_corresponde(ARCHIVO_HISTORIAL_REPRODUCCION)
    from datetime import datetime
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(ARCHIVO_HISTORIAL_REPRODUCCION, "a", encoding="utf-8") as f:
            f.write(f"[{marca_tiempo}] [{ventana}] {titulo} ({codigo}) - {ruta}\n")
    except OSError:
        pass


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

# Compartido entre gui/ventana_programador.py y sus diálogos (Duplicar,
# Programaciones guardadas) — vive acá para que ningún diálogo tenga
# que importar de otro (evita import circular entre ellos).
DIAS_SEMANA_ETIQUETAS = [
    ("lunes", "L"), ("martes", "M"), ("miercoles", "X"),
    ("jueves", "J"), ("viernes", "V"), ("sabado", "S"), ("domingo", "D"),
]


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


def eliminar_programacion(tipo: str, clave: str) -> bool:
    """Borra del disco una programación guardada puntual (por día
    genérico o por fecha específica). Devuelve True si había algo que
    borrar. Usado por el Programador (Eliminar / Eliminar varias)."""
    datos = cargar_programaciones()
    diccionario = datos["dias_semana"] if tipo == "dia" else datos["fechas_especificas"] if tipo == "fecha" else None
    if diccionario is None or clave not in diccionario:
        return False
    del diccionario[clave]
    guardar_programaciones(datos)
    return True


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


def titulo_bloque_sin_prefijo_hora(hora: str, texto: str) -> str:
    """Bug real corregido: `VentanaProgramador._serializar_bloques()`
    guardaba `nodo.text(0)` (el texto VISIBLE "HH:MM:SS - Título")
    como si fuera el título puro — al recargar esa programación y
    volver a concatenar `f"{hora} - {titulo}"`, la hora quedaba
    duplicada, y si se repetía el ciclo (cargar/editar/guardar varias
    veces) se iba acumulando cada vez más. Corregido guardando el
    título puro aparte (rol propio), pero esto además "autocura" en
    el momento de leer/mostrar cualquier título que ya haya quedado
    corrupto en una `programacion.json` guardada por una versión
    anterior — pela repetidamente el prefijo "HH:MM:SS - " de
    `texto` si está duplicado."""
    prefijo = f"{hora} - "
    while texto.startswith(prefijo):
        texto = texto[len(prefijo):]
    return texto


def vigencia_activa(vigencia: dict, hoy=None) -> bool:
    """Vigencia de fecha por material (pedido explícito, inspirado en
    Dinesat): `vigencia` es {"fecha_inicio": "YYYY-MM-DD"|None,
    "fecha_fin": "YYYY-MM-DD"|None} guardado junto al ítem. Sin
    `vigencia` (o vacío) el ítem SIEMPRE es válido — no rompe nada de
    lo ya cargado antes de este cambio. Una fecha faltante o mal
    formada de un lado no restringe ESE lado (fail-open, nunca se
    silencia un ítem por un dato corrupto)."""
    if not vigencia:
        return True
    hoy = hoy or date.today()
    inicio = vigencia.get("fecha_inicio")
    fin = vigencia.get("fecha_fin")
    if inicio:
        try:
            if hoy < date.fromisoformat(inicio):
                return False
        except ValueError:
            pass
    if fin:
        try:
            if hoy > date.fromisoformat(fin):
                return False
        except ValueError:
            pass
    return True


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
    _guardar_json_atomico(ARCHIVO_BIBLIOTECA, categorias, compacto=True)


def reanalizar_biblioteca(config: dict) -> int:
    """Pedido explícito ("los temas siguen teniendo silencio al
    final"): cambiar la tolerancia de silencio en Configuración NO es
    retroactivo por sí solo — el recorte se calcula UNA sola vez, al
    importar/reemplazar un archivo en Ventana 3 (ver
    gui/ventana_explorador.py). Esta función vuelve a analizar TODOS
    los materiales YA importados con la tolerancia/umbral ACTUALES —
    es la forma de aplicar un valor nuevo a lo que ya estaba cargado,
    sin tener que reemplazar archivo por archivo a mano. Devuelve la
    cantidad de archivos reanalizados. Un archivo cuya ruta ya no
    existe en disco se saltea sin romper el resto (ni el propio
    recorrido, ni la reanudación de la app)."""
    from core.analizador_audio import analizar_audio

    categorias = cargar_biblioteca()
    contador = 0

    def _procesar_categoria(categoria: dict):
        nonlocal contador
        for registro in categoria.get("archivos", []):
            ruta = registro.get("ruta")
            if not ruta or not os.path.exists(ruta):
                continue
            tolerancia = tolerancia_silencio_para_genero(config, registro.get("genero"))
            umbral = config.get("reproduccion", {}).get("umbral_silencio_dbfs", -40.0)
            analisis = analizar_audio(ruta, tolerancia_silencio_segundos=tolerancia, umbral_silencio_dbfs=umbral)
            registro["punto_inicio_ms"] = analisis["punto_inicio_ms"]
            registro["punto_fin_ms"] = analisis["punto_fin_ms"] or None
            registro["ganancia_db"] = analisis["ganancia_db"]
            registro["analizado"] = analisis["analizado"]
            contador += 1
        for subcategoria in categoria.get("subcategorias", []):
            _procesar_categoria(subcategoria)

    for categoria in categorias:
        _procesar_categoria(categoria)

    guardar_biblioteca(categorias)
    return contador


# ----------------------------------------------------------------------
# Playlist de Ventana 2 (Emisión): antes era efímera y se perdía al
# cerrar o ante un corte de luz — pedido explícito de Santiago para
# poder ir probando con música real sin perder el armado cada vez.
# ----------------------------------------------------------------------
# Estructura de config/data/playlist_emision.json:
#   {"items": [{"titulo", "duracion", "codigo", "ruta", "pisador_ruta"}, ...],
#    "fila_armada": int, "fila_siguiente": int,
#    "formato_musicalizador_activo": str|None}
# Se guarda ante cada alta/baja/reordenada/marcado, igual que la
# biblioteca — no solo al cerrar la app.
#
# "formato_musicalizador_activo" (pedido explícito, bug real
# corregido: "no lee el ultimo FMT... llega al final de la lista y no
# carga otro ciclo, se detiene"): antes de esto, reabrir la app
# restauraba los ÍTEMS de una serie generada por el Musicalizador,
# pero NO el hecho de que esa lista estaba siendo alimentada por un
# formato activo — GestorPlaylist._formato_musicalizador_activo volvía
# a None, así que el refill (ver core/gestor_emision.py:
# _marcar_siguiente_con_refill) nunca se disparaba una vez que la
# lista restaurada se agotaba. Ahora el nombre del formato activo se
# persiste junto con los ítems y se restaura de punta a punta.

PLAYLIST_EMISION_VACIA = {
    "items": [], "fila_armada": -1, "fila_siguiente": -1,
    "formato_musicalizador_activo": None,
}


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


# ----------------------------------------------------------------------
# Playlist de Ventana 1 (Publicidad): mismo tratamiento que Emisión —
# pedido explícito, sobrevive a un cierre/corte de luz.
# ----------------------------------------------------------------------
# Estructura de config/data/playlist_publicidad.json:
#   {"bloques": [{"hora","titulo","items":[{...}]}, ...],
#    "indice_armado": [indice_bloque, indice_tanda] | None,
#    "indice_siguiente": [indice_bloque, indice_tanda] | None}

PLAYLIST_PUBLICIDAD_VACIA = {"bloques": [], "indice_armado": None, "indice_siguiente": None}


def cargar_playlist_publicidad() -> dict:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_PLAYLIST_PUBLICIDAD):
        return dict(PLAYLIST_PUBLICIDAD_VACIA)
    try:
        with open(ARCHIVO_PLAYLIST_PUBLICIDAD, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return {**PLAYLIST_PUBLICIDAD_VACIA, **datos}
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo playlist de Publicidad: {error}")
        return dict(PLAYLIST_PUBLICIDAD_VACIA)


def guardar_playlist_publicidad(datos: dict):
    _guardar_json_atomico(ARCHIVO_PLAYLIST_PUBLICIDAD, datos)


# ----------------------------------------------------------------------
# Listas guardadas del Auxiliar (pedido explícito): el operador puede
# guardar el contenido actual del Auxiliar bajo un NOMBRE elegido a
# mano, y más tarde cargarlo de nuevo (reemplazando lo que hubiera) o
# borrarlo — todo con confirmación en la UI, acá solo la persistencia.
# Mismo formato de ítem que ya usa playlist_emision.json (incluido el
# Pisador anidado), para poder reusar exactamente el mismo camino de
# guardado/restauración ya probado.
# ----------------------------------------------------------------------
# Estructura de config/data/listas_auxiliar.json:
#   {"Nombre de la lista": {"items": [{...}, ...]}, ...}

ARCHIVO_LISTAS_AUXILIAR = os.path.join(DIRECTORIO_CONFIG, "listas_auxiliar.json")


def cargar_listas_auxiliares() -> dict:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_LISTAS_AUXILIAR):
        return {}
    try:
        with open(ARCHIVO_LISTAS_AUXILIAR, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo listas guardadas del Auxiliar: {error}")
        return {}


def guardar_lista_auxiliar(nombre: str, items: list):
    """Guarda (o sobrescribe, si ya existía ese nombre) una lista con
    el contenido actual del Auxiliar."""
    datos = cargar_listas_auxiliares()
    datos[nombre] = {"items": items}
    _guardar_json_atomico(ARCHIVO_LISTAS_AUXILIAR, datos)


def listar_listas_auxiliares() -> list:
    """Nombres de las listas guardadas, orden alfabético."""
    return sorted(cargar_listas_auxiliares().keys())


def obtener_lista_auxiliar(nombre: str) -> list | None:
    datos = cargar_listas_auxiliares()
    entrada = datos.get(nombre)
    if entrada is None:
        return None
    return entrada.get("items", [])


def eliminar_lista_auxiliar(nombre: str) -> bool:
    datos = cargar_listas_auxiliares()
    if nombre not in datos:
        return False
    del datos[nombre]
    _guardar_json_atomico(ARCHIVO_LISTAS_AUXILIAR, datos)
    return True


# ----------------------------------------------------------------------
# Musicalizador Avanzado + Comandos FMT (pedido explícito, inspirado en
# Hardata Dinesat 9 — "los últimos 2 [temas] que más usa"). Ver
# core/musicalizador.py para el motor de generación.
# ----------------------------------------------------------------------
# Estructura de config/data/musicalizador.json:
#   {"formatos": {
#       "Folclore": {"items": [
#           {"tipo": "especifico", "ruta": "...", "pisador_categoria": [...]|None, "pisador_posicion": "inicio"|"final"},
#           {"tipo": "aleatorio", "categoria": ["Música","Folclore"], "recursivo": True, "pisador_categoria": [...]|None, "pisador_posicion": "inicio"|"final"},
#           {"tipo": "subformato", "nombre": "OtroFormato", "duracion_segundos": 600},
#       ]},
#       ...
#   }}
# "categoria"/"pisador_categoria" guardan el CAMINO de nombres desde la
# raíz (ver VentanaExplorador.ruta_de_categoria/buscar_categoria_por_ruta),
# nunca una referencia viva al QTreeWidgetItem.

def cargar_musicalizador() -> dict:
    _asegurar_directorio()
    if not os.path.exists(ARCHIVO_MUSICALIZADOR):
        return {"formatos": {}}
    try:
        with open(ARCHIVO_MUSICALIZADOR, "r", encoding="utf-8") as f:
            datos = json.load(f)
        datos.setdefault("formatos", {})
        return datos
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo musicalizador: {error}")
        return {"formatos": {}}


def guardar_musicalizador(datos: dict):
    _guardar_json_atomico(ARCHIVO_MUSICALIZADOR, datos)


def listar_formatos() -> list:
    return sorted(cargar_musicalizador()["formatos"].keys())


def obtener_formato(nombre: str) -> dict | None:
    return cargar_musicalizador()["formatos"].get(nombre)


def guardar_formato(nombre: str, items: list):
    datos = cargar_musicalizador()
    datos["formatos"][nombre] = {"items": items}
    guardar_musicalizador(datos)


def eliminar_formato(nombre: str):
    datos = cargar_musicalizador()
    if nombre in datos["formatos"]:
        del datos["formatos"][nombre]
        guardar_musicalizador(datos)


def renombrar_formato(nombre_viejo: str, nombre_nuevo: str) -> bool:
    """True si se pudo renombrar (el nombre viejo existía y el nuevo
    no estaba ya usado por OTRO formato)."""
    datos = cargar_musicalizador()
    if nombre_viejo not in datos["formatos"] or nombre_viejo == nombre_nuevo:
        return nombre_viejo == nombre_nuevo
    if nombre_nuevo in datos["formatos"]:
        return False
    datos["formatos"][nombre_nuevo] = datos["formatos"].pop(nombre_viejo)
    guardar_musicalizador(datos)
    return True


# ----------------------------------------------------------------------
# "Último FMT cargado" (pedido explícito: "lo guardarás en memoria
# temporal, sobrevive al día no a la sesión") — a diferencia de
# _formato_musicalizador_activo (puramente en memoria de
# GestorPlaylist), esto persiste en disco para sobrevivir un reinicio
# de la app DENTRO del mismo día, pero se ignora solo (no se borra el
# archivo, simplemente deja de aplicar) apenas cambia el día — así una
# instalación que se reinicia de madrugada no arrastra el FMT de ayer.
# ----------------------------------------------------------------------
def guardar_ultimo_fmt(nombre_formato: str):
    _guardar_json_atomico(ARCHIVO_ULTIMO_FMT, {"nombre": nombre_formato, "fecha": date.today().isoformat()})


def obtener_ultimo_fmt() -> str | None:
    if not os.path.exists(ARCHIVO_ULTIMO_FMT):
        return None
    try:
        with open(ARCHIVO_ULTIMO_FMT, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (json.JSONDecodeError, OSError) as error:
        registrar_error(f"Error leyendo último FMT: {error}")
        return None
    if datos.get("fecha") != date.today().isoformat():
        return None  # de otro día — "sobrevive al día, no más que eso"
    return datos.get("nombre") or None


def rutas_recientes_en_historial(rutas_candidatas: set, cantidad_a_excluir: int) -> set:
    """Pedido explícito ("no repetir una canción hasta tanto no se
    haya reproducido toda la lista... búsqueda lógica... en el log de
    reproducción"): lee `historial_reproduccion.txt` de atrás para
    adelante y devuelve hasta `cantidad_a_excluir` rutas DISTINTAS (de
    las que están en `rutas_candidatas`) que sonaron más
    recientemente. Al elegir un aleatorio, el llamador excluye este
    conjunto — así una categoría de N temas no repite ninguno hasta
    que los otros N-1 ya sonaron, y esto sobrevive un reinicio porque
    lee el archivo en disco, no un contador en memoria. No lee
    `.anterior.txt` (una rotación del log es un corte de ciclo
    aceptable, no un bug)."""
    if cantidad_a_excluir <= 0 or not rutas_candidatas:
        return set()
    if not os.path.exists(ARCHIVO_HISTORIAL_REPRODUCCION):
        return set()
    try:
        with open(ARCHIVO_HISTORIAL_REPRODUCCION, "r", encoding="utf-8") as f:
            lineas = f.readlines()
    except OSError:
        return set()

    excluidas = set()
    for linea in reversed(lineas):
        if len(excluidas) >= cantidad_a_excluir:
            break
        # Formato de cada línea: "[timestamp] [Ventana] Título (Código) - ruta"
        # rsplit (no split): el título puede contener " - " también, la
        # ruta es siempre el último tramo.
        partes = linea.rstrip("\n").rsplit(" - ", 1)
        if len(partes) != 2:
            continue
        ruta = partes[1]
        if ruta in rutas_candidatas:
            excluidas.add(ruta)
    return excluidas
