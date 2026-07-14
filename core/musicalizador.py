"""
core/musicalizador.py
--------------------------------------------------------
Motor del Musicalizador Avanzado + Comandos FMT (pedido explícito,
"los últimos 2 [temas] que más uso", inspirado en Hardata Dinesat 9).

Un "formato" (config/settings.py:obtener_formato) es una lista
ORDENADA de ítems de 3 tipos, tal cual describe Santiago (y Dinesat):
- "especifico": un archivo FIJO, nunca aleatorio. Puede llevar Pisador.
- "aleatorio": SIEMPRE elige UN tema al azar de una categoría (y, si
  se pide, sus subcategorías) — pedido explícito: "el aleatorio
  (siempre será 1 tema elegido al azar)". Puede llevar Pisador. "No
  repetir hasta agotar la categoría" se resuelve consultando el
  historial de reproducción PERSISTENTE (config/settings.py:
  rutas_recientes_en_historial) — sobrevive un reinicio del programa.
- "subformato": referencia a OTRO formato ya creado, expandido hasta
  cubrir una duración en segundos — permite anidar formatos dentro de
  formatos, igual que Dinesat.

Este módulo NO depende de Qt directamente: recibe un `explorador` con
"pato-tipado" (duck typing) — cualquier objeto con los métodos
`buscar_registro_por_ruta`, `buscar_categoria_por_ruta`,
`listar_registros_de_categoria`, `elegir_aleatorio_de_categoria`
sirve (en producción es VentanaExplorador; en los tests, un fake
liviano) — así la lógica de generación se puede probar sin levantar
QApplication/QTreeWidget.

Regla de robustez pedida explícitamente por Santiago ("que luego se
borre un ítem... no debe impedir que cargue los demás ítem del
musicalizador"): un ítem roto (categoría/archivo/subformato que ya
no existe) se SALTEA en silencio durante la generación — nunca frena
ni rompe la generación de los demás ítems del formato.
--------------------------------------------------------
"""

from config.settings import obtener_formato, rutas_recientes_en_historial

DURACION_SEGUNDOS_POR_DEFECTO = 180  # 3 min — fallback si la duración del registro es ilegible
TOPE_VUELTAS_POR_DURACION = 500  # freno defensivo, nunca debería hacer falta en la práctica


def _duracion_a_segundos(texto_duracion: str) -> int:
    """"HH:MM:SS" -> segundos. Tolerante a formatos raros o vacíos
    (fail-open: nunca rompe la generación por un dato de duración
    corrupto, solo usa una estimación razonable)."""
    try:
        partes = [int(p) for p in str(texto_duracion).split(":")]
        while len(partes) < 3:
            partes.insert(0, 0)
        h, m, s = partes[-3:]
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError, TypeError):
        return DURACION_SEGUNDOS_POR_DEFECTO


def _resolver_pisador(explorador, item_config: dict):
    """Si el ítem del formato pide Pisador, lo resuelve de una de DOS
    formas (pedido explícito, punto a: "debo tener las dos opciones,
    elegir un aleatorio de la categoría PISADORES, o bien elegir un
    archivo específico de pisador") — `pisador_tipo` decide cuál:
    - "especifico" (nuevo): SIEMPRE el mismo archivo (`pisador_ruta`).
    - "categoria" (default, compatible con formatos ya guardados antes
      de este cambio): uno al azar de esa categoría, SIN garantía de
      no-repetición (eso es solo para la canción principal).
    Devuelve (registro_pisador, posicion) o (None, None) si no
    corresponde o la referencia ya no existe."""
    tipo_pisador = item_config.get("pisador_tipo", "categoria")
    posicion = item_config.get("pisador_posicion") or "inicio"

    if tipo_pisador == "especifico":
        ruta = item_config.get("pisador_ruta")
        if not ruta:
            return None, None
        registro = explorador.buscar_registro_por_ruta(ruta)
        if not registro:
            return None, None
        return registro, posicion

    ruta_categoria = item_config.get("pisador_categoria")
    if not ruta_categoria:
        return None, None
    categoria = explorador.buscar_categoria_por_ruta(ruta_categoria)
    if categoria is None:
        return None, None
    registro = explorador.elegir_aleatorio_de_categoria(categoria, recursivo=True)
    if registro is None:
        return None, None
    return registro, posicion


def _resolver_aleatorio(explorador, item_config: dict, rutas_a_evitar: frozenset = frozenset()) -> dict | None:
    categoria = explorador.buscar_categoria_por_ruta(item_config.get("categoria") or [])
    if categoria is None:
        return None
    recursivo = item_config.get("recursivo", True)
    candidatos = explorador.listar_registros_de_categoria(categoria, recursivo)
    if not candidatos:
        return None
    rutas_candidatas = {r.get("ruta") for r in candidatos if r.get("ruta")}
    # No repetir hasta agotar la categoría (pedido explícito): excluye
    # las (N-1) rutas de ESTA categoría más recientes en el historial
    # PERSISTENTE (lo que YA sonó), MÁS `rutas_a_evitar` (lo que ya se
    # generó en esta misma serie o en una serie anterior todavía en
    # cola sin sonar — pedido explícito, ronda posterior: "cuando
    # volvió a cargar la serie, cargó el mismo archivo aleatorio que
    # en la primera". El historial por sí solo no alcanza: solo
    # registra lo que YA se REPRODUJO, y con el refill ahora disparado
    # apenas algo "entra en previo" (verde), la serie nueva se genera
    # ANTES de que la anterior termine de sonar — el historial todavía
    # no reflejaría esas rutas). Mismo criterio de "nunca dejar hueco"
    # (ver `elegir_aleatorio_de_categoria`): si excluir todo vacía la
    # lista de candidatos, la exclusión se ignora antes que repetir un
    # tema a dejar silencio.
    excluidas_historial = rutas_recientes_en_historial(rutas_candidatas, len(rutas_candidatas) - 1)
    excluidas = excluidas_historial | (rutas_a_evitar & rutas_candidatas)
    return explorador.elegir_aleatorio_de_categoria(categoria, recursivo, excluir_rutas=excluidas)


def _resolver_item(explorador, item_config: dict, visitados: frozenset,
                    rutas_a_evitar: frozenset = frozenset()) -> list:
    """Devuelve una lista de "items concretos" — normalmente 0 o 1
    ({"registro", "pisador", "pisador_posicion"}), salvo un
    subformato, que puede devolver varios de una vez."""
    tipo = item_config.get("tipo")
    if tipo == "especifico":
        registro = explorador.buscar_registro_por_ruta(item_config.get("ruta", ""))
        if not registro:
            return []
        pisador, posicion = _resolver_pisador(explorador, item_config)
        return [{"registro": registro, "pisador": pisador, "pisador_posicion": posicion}]

    if tipo == "aleatorio":
        registro = _resolver_aleatorio(explorador, item_config, rutas_a_evitar)
        if not registro:
            return []
        pisador, posicion = _resolver_pisador(explorador, item_config)
        return [{"registro": registro, "pisador": pisador, "pisador_posicion": posicion}]

    if tipo == "subformato":
        nombre_sub = item_config.get("nombre")
        duracion_objetivo = item_config.get("duracion_segundos") or 0
        return _generar_por_duracion(explorador, nombre_sub, duracion_objetivo, visitados, rutas_a_evitar)

    return []  # tipo desconocido / ítem corrupto: se saltea solo


def _generar_por_duracion(explorador, nombre_formato: str, duracion_objetivo_segundos: int,
                           visitados: frozenset, rutas_a_evitar: frozenset = frozenset()) -> list:
    """Expande un formato (usado como subformato) hasta cubrir
    `duracion_objetivo_segundos`, repitiendo su esquema tantas veces
    como haga falta. `visitados` corta cualquier ciclo de subformatos
    en tiempo de ejecución — red de seguridad además de la validación
    al guardar (ver validar_formato). `rutas_a_evitar` se acumula a
    medida que se van resolviendo ítems (dentro de esta expansión y
    heredado de fuera) para que el propio subformato tampoco se repita
    a sí mismo en una misma vuelta."""
    if nombre_formato in visitados or duracion_objetivo_segundos <= 0:
        return []
    formato = obtener_formato(nombre_formato)
    if not formato or not formato.get("items"):
        return []
    visitados_ahora = visitados | {nombre_formato}

    resultado = []
    rutas_usadas = set(rutas_a_evitar)
    acumulado_segundos = 0
    vueltas = 0
    while acumulado_segundos < duracion_objetivo_segundos and vueltas < TOPE_VUELTAS_POR_DURACION:
        agregados_esta_vuelta = 0
        for item_config in formato["items"]:
            if acumulado_segundos >= duracion_objetivo_segundos:
                break
            for concreto in _resolver_item(explorador, item_config, visitados_ahora, frozenset(rutas_usadas)):
                resultado.append(concreto)
                ruta = concreto["registro"].get("ruta")
                if ruta:
                    rutas_usadas.add(ruta)
                acumulado_segundos += _duracion_a_segundos(concreto["registro"].get("duracion", ""))
                agregados_esta_vuelta += 1
        vueltas += 1
        if agregados_esta_vuelta == 0:
            break  # el formato entero está roto/vacío — no insistir en un loop infinito
    return resultado


def generar_serie(explorador, nombre_formato: str, rutas_a_evitar: frozenset = frozenset()) -> list:
    """Punto de entrada del motor: genera UNA serie completa — la
    cantidad EXACTA de "ítems concretos" que produce UNA sola pasada
    por `nombre_formato`, en el orden programado (pedido explícito:
    "debe cargar el número exacto de musicalización... la cantidad que
    haya programado. Solo se extiende si en la serie hay sub-formato,
    ya que en este caso carga la cantidad de ESE sub-formato" — la
    expansión por duración de un subformato no cambia, ver
    `_generar_por_duracion`; lo único que cambió es que el formato
    "padre" ya NO repite su propio esquema para completar un tamaño de
    lote artificial). Cada llamada resuelve los ítems "aleatorio" de
    nuevo (nuevas elecciones al azar) y mantiene los "específico"
    siempre iguales — así una serie nueva usa "otros archivos de los
    aleatorios, el mismo específico" (pedido explícito). Lo usa
    GestorPlaylist (core/gestor_emision.py) para la carga inicial al
    disparar un Comando FMT y para cargar la próxima serie cuando la
    anterior está por terminarse (relleno continuo).

    `rutas_a_evitar` (pedido explícito, ronda posterior — "optimizá
    mejor la lógica de aleatorio... cargó el mismo archivo aleatorio
    que en la primera"): rutas que el LLAMADOR ya sabe que están en
    cola sin sonar todavía (ej. lo que ya hay cargado en Emisión) —
    se suman a la exclusión de cada ítem "aleatorio" ADEMÁS del
    historial persistente, y también se van acumulando ítem a ítem
    DENTRO de esta misma pasada (así dos ítems aleatorios del mismo
    formato tampoco eligen el mismo archivo entre sí)."""
    formato = obtener_formato(nombre_formato)
    if not formato or not formato.get("items"):
        return []
    visitados = frozenset({nombre_formato})
    resultado = []
    rutas_usadas = set(rutas_a_evitar)
    for item_config in formato["items"]:
        concretos = _resolver_item(explorador, item_config, visitados, frozenset(rutas_usadas))
        resultado.extend(concretos)
        for concreto in concretos:
            ruta = concreto["registro"].get("ruta")
            if ruta:
                rutas_usadas.add(ruta)
    return resultado


# ------------------------------------------------------------------
# Validación al guardar un formato (pedido explícito, punto 5): NO
# modifica nada, solo devuelve la lista de problemas encontrados. El
# llamador (gui/ventana_musicalizador.py) decide qué hacer con cada
# uno — bucles de subformato BLOQUEAN el guardado (podrían colgar el
# motor generando infinito); referencias rotas y categorías vacías
# solo AVISAN, nunca bloquean (pedido explícito: "no debe impedir que
# cargue los demás ítem").
# ------------------------------------------------------------------
def _hay_ciclo(nombre_origen: str, nombre_a_visitar: str, todos_los_formatos: dict, visitados: set) -> bool:
    if nombre_a_visitar == nombre_origen:
        return True
    if nombre_a_visitar in visitados:
        return False
    visitados = visitados | {nombre_a_visitar}
    formato = todos_los_formatos.get(nombre_a_visitar)
    if not formato:
        return False
    for item_config in formato.get("items", []):
        if item_config.get("tipo") == "subformato":
            if _hay_ciclo(nombre_origen, item_config.get("nombre"), todos_los_formatos, visitados):
                return True
    return False


def validar_formato(explorador, nombre_formato_actual: str, items: list, todos_los_formatos: dict) -> list:
    """Devuelve una lista de dicts {"item": int (1-based), "mensaje": str,
    "bloquea": bool} — "bloquea"=True son bucles de subformato, el
    resto son avisos (referencia rota / categoría vacía)."""
    problemas = []
    for i, item_config in enumerate(items, start=1):
        tipo = item_config.get("tipo")
        if tipo == "especifico":
            if not explorador.buscar_registro_por_ruta(item_config.get("ruta", "")):
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: el archivo específico ya no existe en la biblioteca."})
        elif tipo == "aleatorio":
            categoria = explorador.buscar_categoria_por_ruta(item_config.get("categoria") or [])
            if categoria is None:
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: la categoría ya no existe en la biblioteca."})
            elif not explorador.listar_registros_de_categoria(categoria, item_config.get("recursivo", True)):
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: la categoría está vacía (se puede guardar igual)."})
        elif tipo == "subformato":
            nombre_sub = item_config.get("nombre")
            if nombre_sub not in todos_los_formatos:
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: el subformato '{nombre_sub}' ya no existe."})
            elif _hay_ciclo(nombre_formato_actual, nombre_sub, todos_los_formatos, set()):
                problemas.append({"item": i, "bloquea": True,
                                   "mensaje": f"Ítem {i}: el subformato '{nombre_sub}' genera un bucle "
                                              f"infinito con este formato — no se puede guardar así."})
        if item_config.get("pisador_tipo") == "especifico":
            ruta_pisador_especifico = item_config.get("pisador_ruta")
            if ruta_pisador_especifico and not explorador.buscar_registro_por_ruta(ruta_pisador_especifico):
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: el archivo específico del Pisador ya no existe."})
        else:
            ruta_pisador = item_config.get("pisador_categoria")
            if ruta_pisador and explorador.buscar_categoria_por_ruta(ruta_pisador) is None:
                problemas.append({"item": i, "bloquea": False,
                                   "mensaje": f"Ítem {i}: la categoría del Pisador ya no existe."})
    return problemas
