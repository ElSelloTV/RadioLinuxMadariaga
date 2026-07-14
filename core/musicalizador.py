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
    """Si el ítem del formato pide Pisador (tiene una categoría de
    Pisador configurada), elige UNO al azar de esa categoría — SIN
    garantía de no-repetición (eso es solo para la canción principal,
    pedido explícito). Devuelve (registro_pisador, posicion) o
    (None, None) si no corresponde o la categoría ya no existe."""
    ruta_categoria = item_config.get("pisador_categoria")
    if not ruta_categoria:
        return None, None
    categoria = explorador.buscar_categoria_por_ruta(ruta_categoria)
    if categoria is None:
        return None, None
    registro = explorador.elegir_aleatorio_de_categoria(categoria, recursivo=True)
    if registro is None:
        return None, None
    return registro, item_config.get("pisador_posicion") or "inicio"


def _resolver_aleatorio(explorador, item_config: dict) -> dict | None:
    categoria = explorador.buscar_categoria_por_ruta(item_config.get("categoria") or [])
    if categoria is None:
        return None
    recursivo = item_config.get("recursivo", True)
    candidatos = explorador.listar_registros_de_categoria(categoria, recursivo)
    if not candidatos:
        return None
    rutas_candidatas = {r.get("ruta") for r in candidatos if r.get("ruta")}
    # No repetir hasta agotar la categoría (pedido explícito): excluye
    # las (N-1) rutas de ESTA categoría más recientes en el historial.
    excluidas = rutas_recientes_en_historial(rutas_candidatas, len(rutas_candidatas) - 1)
    return explorador.elegir_aleatorio_de_categoria(categoria, recursivo, excluir_rutas=excluidas)


def _resolver_item(explorador, item_config: dict, visitados: frozenset) -> list:
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
        registro = _resolver_aleatorio(explorador, item_config)
        if not registro:
            return []
        pisador, posicion = _resolver_pisador(explorador, item_config)
        return [{"registro": registro, "pisador": pisador, "pisador_posicion": posicion}]

    if tipo == "subformato":
        nombre_sub = item_config.get("nombre")
        duracion_objetivo = item_config.get("duracion_segundos") or 0
        return _generar_por_duracion(explorador, nombre_sub, duracion_objetivo, visitados)

    return []  # tipo desconocido / ítem corrupto: se saltea solo


def _generar_por_duracion(explorador, nombre_formato: str, duracion_objetivo_segundos: int,
                           visitados: frozenset) -> list:
    """Expande un formato (usado como subformato) hasta cubrir
    `duracion_objetivo_segundos`, repitiendo su esquema tantas veces
    como haga falta. `visitados` corta cualquier ciclo de subformatos
    en tiempo de ejecución — red de seguridad además de la validación
    al guardar (ver validar_formato)."""
    if nombre_formato in visitados or duracion_objetivo_segundos <= 0:
        return []
    formato = obtener_formato(nombre_formato)
    if not formato or not formato.get("items"):
        return []
    visitados_ahora = visitados | {nombre_formato}

    resultado = []
    acumulado_segundos = 0
    vueltas = 0
    while acumulado_segundos < duracion_objetivo_segundos and vueltas < TOPE_VUELTAS_POR_DURACION:
        agregados_esta_vuelta = 0
        for item_config in formato["items"]:
            if acumulado_segundos >= duracion_objetivo_segundos:
                break
            for concreto in _resolver_item(explorador, item_config, visitados_ahora):
                resultado.append(concreto)
                acumulado_segundos += _duracion_a_segundos(concreto["registro"].get("duracion", ""))
                agregados_esta_vuelta += 1
        vueltas += 1
        if agregados_esta_vuelta == 0:
            break  # el formato entero está roto/vacío — no insistir en un loop infinito
    return resultado


def generar_items(explorador, nombre_formato: str, cantidad: int) -> list:
    """Punto de entrada del motor: genera hasta `cantidad` "ítems
    concretos" ({"registro", "pisador", "pisador_posicion"})
    recorriendo `nombre_formato` en orden y REPITIENDO el esquema
    completo cuantas veces haga falta (pedido explícito: "siempre
    repitiendo el esquema del musicalizador... de manera continua").
    Lo usa GestorPlaylist (core/gestor_emision.py) para la generación
    inicial al disparar un comando FMT y para el relleno continuo."""
    if cantidad <= 0:
        return []
    formato = obtener_formato(nombre_formato)
    if not formato or not formato.get("items"):
        return []
    visitados = frozenset({nombre_formato})

    resultado = []
    while len(resultado) < cantidad:
        agregados_esta_vuelta = 0
        for item_config in formato["items"]:
            if len(resultado) >= cantidad:
                break
            for concreto in _resolver_item(explorador, item_config, visitados):
                if len(resultado) >= cantidad:
                    break
                resultado.append(concreto)
                agregados_esta_vuelta += 1
        if agregados_esta_vuelta == 0:
            break  # el formato entero está roto/vacío — no insistir en un loop infinito
    return resultado[:cantidad]


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
        ruta_pisador = item_config.get("pisador_categoria")
        if ruta_pisador and explorador.buscar_categoria_por_ruta(ruta_pisador) is None:
            problemas.append({"item": i, "bloquea": False,
                               "mensaje": f"Ítem {i}: la categoría del Pisador ya no existe."})
    return problemas
