"""
core/procesador_audio.py
--------------------------------------------------------
Controlador "en frío" de efectos de audio para el aire (pedido
explícito: "el objetivo no es integrar los efectos al programa, sino
que 'cree' un archivo de configuración y lo cargue filter-chain.conf,
algo así como hicimos elegir_config.sh pero con un semi entorno
gráfico integrado"). Mismo criterio de siempre en este proyecto desde
la ronda 55 (EasyEffects por fuera de la app): esta app NUNCA procesa
audio en tiempo real ella misma -- este módulo solo ARMA el texto de
un archivo `pipewire.conf.d/*.conf` con el módulo nativo
`libpipewire-module-filter-chain` (plugins Calf, ya confirmado
funcionando en este proyecto, ronda 52) y, cuando el operador aprieta
"Aplicar", lo escribe y reinicia los 3 servicios de PipeWire para que
lo tome -- exactamente el mismo mecanismo (`~/.config/pipewire/
pipewire.conf.d/`, `systemctl --user restart pipewire pipewire-pulse
wireplumber`) que YA se usó dos veces con éxito en este proyecto real
(ronda 52 y el fix de frecuencia de muestreo de la bitácora de
Sept-2026), nunca un mecanismo nuevo sin probar.

Cambios "en frío": los sliders de la UI (gui/ventana_configuracion.py)
SOLO tocan un preset guardado en `config/data/procesador_audio.json`
(vía config/settings.py:cargar_procesador_audio/guardar_procesador_
audio) -- nada de eso togca PipeWire hasta que se aprieta "✅ Aplicar"
o "🔇 Bypass", los dos únicos puntos de este módulo que tocan el
sistema operativo de verdad.

Catálogo de efectos: los 3 primeros (StereoTools/Compresor/Limiter)
son los YA CONFIRMADOS funcionando en este proyecto (ronda 52, con
audio real: "ahi se escucha!!!") -- sus valores de fábrica acá abajo
son EXACTAMENTE esos, la base de "Configuración 1". El resto
(Exciter/BassEnhancer/Deesser) son "para probar si la PC los soporta"
(pedido explícito) -- quedan DESACTIVADOS por defecto, con los
valores de fábrica del propio plugin (verificados con `lv2info` real
contra `calf-plugins` 0.90.3, el mismo paquete ya usado en la ronda
52 -- nunca un número inventado).

Orden de la cadena (fijo, no editable desde la UI -- criterio
estándar de procesamiento de broadcast: primero imagen estéreo y
"color" del sonido, dinámica al final, LIMITADOR SIEMPRE ÚLTIMO como
red de seguridad contra saturación):
    StereoTools -> Deesser -> BassEnhancer -> Exciter -> Compresor -> Limiter
Un efecto "desactivado" simplemente no entra al grafo -- el resto se
encadena entre sí sin huecos.
--------------------------------------------------------
"""

import os
import shutil
import subprocess
import tempfile

from config.settings import (
    registrar_evento, registrar_error,
    cargar_procesador_audio, guardar_procesador_audio,
)

TIMEOUT_SEGUNDOS = 20.0

RUTA_CONF_DEFECTO = "~/.config/pipewire/pipewire.conf.d/99-radio-fm-processing.conf"
# Confirmado real contra esta misma PC de aire, ver
# extras/procesador_fm_viper4linux/devices.conf.santiago -- el nombre
# exacto del sink de la consola USB Silicon.
SINK_REPRODUCCION_DEFECTO = "alsa_output.usb-MV-SILICON_MVSilicon_USB_Audio_20190808-00.analog-stereo"
# El "sink" virtual donde la app entrega el audio -- Configuración >
# Audio > Salida Master tiene que apuntar a ESTE nombre para que el
# audio de la radio pase por acá antes de llegar al hardware real.
SINK_CAPTURA_DEFECTO = "fm_processing_input"

NOMBRE_PRESET_DEFECTO = "Configuración 1"


def _lineal_desde_db(valor_db: float) -> float:
    return 10 ** (valor_db / 20.0)


class Parametro:
    """Un control de un plugin LV2 -- rango/valor SIEMPRE en la unidad
    que ve el operador (dB donde tiene sentido, ms, Hz, x:1, etc.);
    `es_db`/`es_bool` le dicen a `_valor_lv2()` cómo convertirlo al
    valor lineal que de verdad espera el puerto LV2 al escribir el
    .conf -- así el preset guardado en JSON siempre queda en unidades
    humanas, nunca en la escala interna del plugin."""

    __slots__ = (
        "simbolo", "etiqueta", "minimo", "maximo", "defecto",
        "decimales", "sufijo", "es_db", "es_bool",
    )

    def __init__(self, simbolo, etiqueta, minimo, maximo, defecto,
                 decimales=1, sufijo="", es_db=False, es_bool=False):
        self.simbolo = simbolo
        self.etiqueta = etiqueta
        self.minimo = minimo
        self.maximo = maximo
        self.defecto = defecto
        self.decimales = decimales
        self.sufijo = sufijo
        self.es_db = es_db
        self.es_bool = es_bool

    def valor_lv2(self, valor_mostrado):
        if self.es_bool:
            return 1 if valor_mostrado else 0
        if self.es_db:
            return round(_lineal_desde_db(valor_mostrado), 6)
        return valor_mostrado


class Efecto:
    __slots__ = ("clave", "nombre", "uri", "parametros", "activado_por_defecto", "descripcion")

    def __init__(self, clave, nombre, uri, parametros, activado_por_defecto, descripcion=""):
        self.clave = clave
        self.nombre = nombre
        self.uri = uri
        self.parametros = parametros
        self.activado_por_defecto = activado_por_defecto
        self.descripcion = descripcion

    def valores_por_defecto(self) -> dict:
        datos = {"activado": self.activado_por_defecto}
        for p in self.parametros:
            datos[p.simbolo] = p.defecto
        return datos


CATALOGO = [
    Efecto(
        "stereo_tools", "Stereo Tools (ancho estéreo)",
        "http://calf.sourceforge.net/plugins/StereoTools",
        [
            Parametro("slev", "Ancho estéreo", 0.0, 2.0, 1.15, decimales=2),
            Parametro("stereo_base", "Base estéreo (fase)", -1.0, 1.0, 0.0, decimales=2),
        ],
        activado_por_defecto=True,
        descripcion="Ya habilitado -- confirmado con audio real (ronda 52).",
    ),
    Efecto(
        "deesser", "De-esser (silbidos de voz -- HTH/locución)",
        "http://calf.sourceforge.net/plugins/Deesser",
        [
            Parametro("threshold", "Umbral", -60.0, 0.0, -18.06, sufijo=" dB", es_db=True),
            Parametro("ratio", "Proporción", 1.0, 20.0, 3.0, sufijo=":1"),
            Parametro("f1_freq", "Frecuencia 1", 10.0, 18000.0, 6000.0, decimales=0, sufijo=" Hz"),
            Parametro("f2_freq", "Frecuencia 2", 10.0, 18000.0, 4500.0, decimales=0, sufijo=" Hz"),
            Parametro("makeup", "Ganancia de salida", 0.0, 24.0, 0.0, sufijo=" dB", es_db=True),
        ],
        activado_por_defecto=False,
        descripcion="Para probar -- reduce silbidos de \"s\"/\"ch\" en HTH/locución.",
    ),
    Efecto(
        "bass_enhancer", "Bass Enhancer (realce de graves)",
        "http://calf.sourceforge.net/plugins/BassEnhancer",
        [
            Parametro("amount", "Cantidad", 0.0, 4.0, 1.0, decimales=2),
            Parametro("drive", "Drive", 0.1, 10.0, 8.5, decimales=1),
            Parametro("blend", "Mezcla", -10.0, 10.0, 0.0, decimales=1),
            Parametro("freq", "Frecuencia de corte", 10.0, 250.0, 100.0, decimales=0, sufijo=" Hz"),
        ],
        activado_por_defecto=False,
        descripcion="Para probar -- \"cuerpo\"/graves, sin tocarlo con un EQ.",
    ),
    Efecto(
        "exciter", "Exciter (brillo/presencia)",
        "http://calf.sourceforge.net/plugins/Exciter",
        [
            Parametro("amount", "Cantidad", 0.0, 4.0, 1.0, decimales=2),
            Parametro("drive", "Drive", 0.1, 10.0, 8.5, decimales=1),
            Parametro("blend", "Mezcla", -10.0, 10.0, 0.0, decimales=1),
            Parametro("freq", "Frecuencia de corte", 2000.0, 12000.0, 7500.0, decimales=0, sufijo=" Hz"),
        ],
        activado_por_defecto=False,
        descripcion="Para probar -- \"brillo\"/aire, armónicos de agudos.",
    ),
    Efecto(
        "compresor", "Compresor",
        "http://calf.sourceforge.net/plugins/Compressor",
        [
            Parametro("threshold", "Umbral", -60.0, 0.0, -20.0, sufijo=" dB", es_db=True),
            Parametro("ratio", "Proporción", 1.0, 20.0, 3.5, sufijo=":1"),
            Parametro("attack", "Ataque", 0.1, 200.0, 15.0, decimales=1, sufijo=" ms"),
            Parametro("release", "Release", 10.0, 1000.0, 200.0, decimales=0, sufijo=" ms"),
            Parametro("makeup", "Ganancia de salida", 0.0, 24.0, 6.02, sufijo=" dB", es_db=True),
            Parametro("knee", "Knee (transición suave)", 1.0, 8.0, 2.83, decimales=2),
            Parametro("detection", "Detección RMS (vs. Pico)", 0, 1, 1, es_bool=True),
            Parametro("stereo_link", "Canales enlazados", 0, 1, 1, es_bool=True),
        ],
        activado_por_defecto=True,
        descripcion="Ya habilitado -- confirmado con audio real (ronda 52).",
    ),
    Efecto(
        "limiter", "Limitador (protección final)",
        "http://calf.sourceforge.net/plugins/Limiter",
        [
            Parametro("limit", "Techo", -24.0, 0.0, -0.6, sufijo=" dB", es_db=True),
            Parametro("attack", "Ataque", 0.1, 10.0, 5.0, decimales=1, sufijo=" ms"),
            Parametro("release", "Release", 1.0, 500.0, 50.0, decimales=0, sufijo=" ms"),
            Parametro("oversampling", "Sobremuestreo", 1, 4, 2, decimales=0, sufijo="x"),
            Parametro("asc", "ASC (evita bombeo)", 0, 1, 1, es_bool=True),
            Parametro("auto_level", "Auto-nivelado", 0, 1, 1, es_bool=True),
        ],
        activado_por_defecto=True,
        descripcion="Ya habilitado -- SIEMPRE el último de la cadena, red de seguridad.",
    ),
]

CATALOGO_POR_CLAVE = {efecto.clave: efecto for efecto in CATALOGO}


def preset_de_fabrica() -> dict:
    """Los valores de "Configuración 1" -- StereoTools/Compresor/
    Limiter con los números YA confirmados sonando bien en este
    proyecto (ronda 52); el resto de los efectos entran con los
    valores de fábrica del propio plugin, apagados, listos para
    probar sin tocar nada más."""
    return {efecto.clave: efecto.valores_por_defecto() for efecto in CATALOGO}


# ------------------------------------------------------------------
# Persistencia de presets (config/data/procesador_audio.json)
# ------------------------------------------------------------------

def _datos_por_defecto() -> dict:
    return {
        "ruta_conf_pipewire": RUTA_CONF_DEFECTO,
        "sink_captura": SINK_CAPTURA_DEFECTO,
        "sink_reproduccion": SINK_REPRODUCCION_DEFECTO,
        "preset_predeterminado": NOMBRE_PRESET_DEFECTO,
        "preset_actual": NOMBRE_PRESET_DEFECTO,
        "presets": {NOMBRE_PRESET_DEFECTO: preset_de_fabrica()},
    }


def cargar_datos() -> dict:
    guardado = cargar_procesador_audio()
    datos = _datos_por_defecto()
    if not guardado:
        return datos
    datos["ruta_conf_pipewire"] = guardado.get("ruta_conf_pipewire") or datos["ruta_conf_pipewire"]
    datos["sink_captura"] = guardado.get("sink_captura") or datos["sink_captura"]
    datos["sink_reproduccion"] = guardado.get("sink_reproduccion") or datos["sink_reproduccion"]
    presets = guardado.get("presets") or {}
    if presets:
        datos["presets"] = presets
    nombres = list(datos["presets"].keys())
    predeterminado = guardado.get("preset_predeterminado")
    datos["preset_predeterminado"] = predeterminado if predeterminado in datos["presets"] else nombres[0]
    actual = guardado.get("preset_actual")
    datos["preset_actual"] = actual if actual in datos["presets"] else datos["preset_predeterminado"]
    return datos


def guardar_datos(datos: dict):
    guardar_procesador_audio(datos)


def normalizar_preset(preset: dict) -> dict:
    """Completa cualquier efecto/parámetro faltante con su valor de
    fábrica -- un preset guardado con una versión anterior de esta
    app (menos efectos en el catálogo) nunca rompe al cargarlo."""
    completo = preset_de_fabrica()
    for clave, valores in (preset or {}).items():
        if clave in completo:
            completo[clave].update(valores)
    return completo


# ------------------------------------------------------------------
# Generación del texto del .conf
# ------------------------------------------------------------------

ORDEN_CADENA = ["stereo_tools", "deesser", "bass_enhancer", "exciter", "compresor", "limiter"]


def _bloque_control(efecto: Efecto, valores: dict) -> str:
    lineas = []
    for p in efecto.parametros:
        valor_mostrado = valores.get(p.simbolo, p.defecto)
        valor = p.valor_lv2(valor_mostrado)
        lineas.append(f"                    {p.simbolo} = {valor}")
    return "\n".join(lineas)


def generar_filter_chain_conf(preset: dict, sink_captura: str, sink_reproduccion: str) -> str:
    """Arma el texto completo del .conf con el módulo nativo
    `libpipewire-module-filter-chain` (mismo formato ya confirmado
    funcionando en la ronda 52) -- SOLO con los efectos que están
    `activado` en `preset`, encadenados en el orden fijo de
    ORDEN_CADENA. Si no queda ningún efecto activado, cae solo al
    passthrough (ver `generar_bypass_conf`)."""
    preset = normalizar_preset(preset)
    activos = [clave for clave in ORDEN_CADENA if preset.get(clave, {}).get("activado")]
    if not activos:
        return generar_bypass_conf(sink_captura, sink_reproduccion)

    nodos = []
    for clave in activos:
        efecto = CATALOGO_POR_CLAVE[clave]
        control = _bloque_control(efecto, preset[clave])
        nodos.append(
            "                {\n"
            "                    type = lv2\n"
            f"                    name = {clave}\n"
            f"                    plugin = \"{efecto.uri}\"\n"
            "                    control = {\n"
            f"{control}\n"
            "                    }\n"
            "                }"
        )
    texto_nodos = "\n".join(nodos)

    enlaces = []
    for anterior, siguiente in zip(activos, activos[1:]):
        enlaces.append(
            f"                {{ output = \"{anterior}:out_l\" input = \"{siguiente}:in_l\" }}\n"
            f"                {{ output = \"{anterior}:out_r\" input = \"{siguiente}:in_r\" }}"
        )
    texto_enlaces = "\n".join(enlaces)

    primero, ultimo = activos[0], activos[-1]

    return f"""\
context.modules = [
    {{   name = libpipewire-module-filter-chain
        args = {{
            node.description = "Radio Tuyú -- Procesador FM"
            media.name       = "Radio Tuyú -- Procesador FM"
            filter.graph = {{
                nodes = [
{texto_nodos}
                ]
                links = [
{texto_enlaces}
                ]
                inputs = [ "{primero}:in_l" "{primero}:in_r" ]
                outputs = [ "{ultimo}:out_l" "{ultimo}:out_r" ]
            }}
            capture.props = {{
                node.name = "{sink_captura}"
                media.class = Audio/Sink
                audio.position = [ FL FR ]
            }}
            playback.props = {{
                node.name = "{sink_captura}_salida"
                media.class = Stream/Output/Audio
                target.object = "{sink_reproduccion}"
                audio.position = [ FL FR ]
            }}
        }}
        flags = [ ifexists nofail ]
    }}
]
"""


def generar_bypass_conf(sink_captura: str, sink_reproduccion: str) -> str:
    """Passthrough puro (pedido explícito, botón Bypass "para testear
    los efectos") -- usa `libpipewire-module-loopback` en vez de un
    filter-chain con nodos, mucho más simple/confiable que intentar
    "apagar" cada plugin uno por uno: conecta captura -> reproducción
    directo, sin ningún procesamiento. El nombre del sink de captura
    queda IDÉNTICO al del modo con efectos -- la Salida Master de la
    app (Configuración > Audio) nunca necesita cambiar al alternar
    Bypass, solo cambia qué hay "detrás" de ese sink."""
    return f"""\
context.modules = [
    {{   name = libpipewire-module-loopback
        args = {{
            node.description = "Radio Tuyú -- Procesador FM (bypass)"
            capture.props = {{
                node.name = "{sink_captura}"
                media.class = Audio/Sink
                audio.position = [ FL FR ]
            }}
            playback.props = {{
                node.name = "{sink_captura}_salida"
                media.class = Stream/Output/Audio
                target.object = "{sink_reproduccion}"
                audio.position = [ FL FR ]
            }}
        }}
        flags = [ ifexists nofail ]
    }}
]
"""


# ------------------------------------------------------------------
# Escritura + recarga de PipeWire (la ÚNICA parte de este módulo que
# toca el sistema operativo de verdad -- todo lo de arriba es texto
# puro, sin efecto hasta acá)
# ------------------------------------------------------------------

def escribir_y_recargar(texto_conf: str, ruta_archivo: str) -> tuple[bool, str]:
    """Escribe `texto_conf` en `ruta_archivo` (expandiendo `~`, creando
    la carpeta si hace falta) y reinicia los 3 servicios de PipeWire
    para que lo tome -- mismo mecanismo ya usado con éxito en este
    proyecto (ronda 52, fix de frecuencia de la bitácora). Escritura
    ATÓMICA (tempfile único + os.replace, mismo criterio que
    config/settings.py:_guardar_json_atomico -- nunca un .tmp fijo
    compartido). Devuelve (éxito, mensaje)."""
    ruta_real = os.path.expanduser(ruta_archivo)
    carpeta = os.path.dirname(ruta_real)
    try:
        os.makedirs(carpeta, exist_ok=True)
        fd, temporal = tempfile.mkstemp(dir=carpeta, prefix=".procesador_fm_", suffix=".conf.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(texto_conf)
            os.replace(temporal, ruta_real)
        except Exception:
            try:
                os.remove(temporal)
            except OSError:
                pass
            raise
    except OSError as error:
        mensaje = f"No se pudo escribir '{ruta_real}': {error}"
        registrar_error(f"Procesador FM: {mensaje}")
        return False, mensaje

    if shutil.which("systemctl") is None:
        mensaje = (
            f"Archivo escrito en '{ruta_real}', pero no se encontró 'systemctl' para "
            "recargar PipeWire -- hace falta reiniciarlo a mano."
        )
        registrar_error(f"Procesador FM: {mensaje}")
        return False, mensaje

    try:
        resultado = subprocess.run(
            ["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"],
            capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        mensaje = f"Archivo escrito en '{ruta_real}', pero no se pudo reiniciar PipeWire: {error}"
        registrar_error(f"Procesador FM: {mensaje}")
        return False, mensaje

    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        mensaje = (
            f"Archivo escrito en '{ruta_real}', pero PipeWire no se pudo reiniciar "
            f"(código {resultado.returncode})" + (f": {detalle}" if detalle else "")
        )
        registrar_error(f"Procesador FM: {mensaje}")
        return False, mensaje

    registrar_evento(f"Procesador FM: '{ruta_real}' aplicado, PipeWire reiniciado.")
    return True, "Aplicado -- PipeWire se reinició con la configuración nueva."
