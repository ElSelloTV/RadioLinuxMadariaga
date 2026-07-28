"""
core/rotacion_categoria.py
--------------------------------------------------------
Motor puro (sin Qt — mismo espíritu que core/musicalizador.py, recibe
un `explorador` duck-typed con `buscar_categoria_por_ruta`/
`listar_registros_de_categoria`) de rotación SECUENCIAL por categoría.

Pedido explícito de Santiago, ejemplo real: "estoy escuchando las
mismas 2 publicidades en todos los bloques... ¿será porque armé el
bloque de las 00 horas y copié y pegué?" — el ítem Aleatorio de
Ventana 1 (core/playlist_manager.py) usaba no-repetir por HISTORIAL
(rutas_recientes_en_historial, config/settings.py), una ventana de
RECENCIA derivada del log de reproducción — funciona bien para
Ventana 2 con ~9000 archivos de música (a propósito, NO SE TOCA acá),
pero con categorías chicas de Publicidad/Separadores usadas en TODOS
los bloques horarios del día no garantizaba variedad real entre un
bloque y el siguiente.

Diseño pedido explícitamente por Santiago, punto por punto ("mi idea
es la siguiente, si no está aplicada"):
a) Los candidatos de la categoría se re-evalúan SIEMPRE en vivo (más
   estricto todavía que "cada hora": nunca una foto vieja).
b) Una posición separada POR CATEGORÍA (nunca mezclada entre
   categorías distintas, ni con Música).
c) Recorre los archivos de la categoría en orden hasta agotarlos,
   vuelve a empezar recién ahí.
d) La posición avanza SOLO cuando el archivo elegido arranca a sonar
   de verdad (nunca al quedar solo armado/en cola) -- y sobrevive
   reinicios de la app y cambios de día calendario (nunca se resetea
   sola, solo al agotar la vuelta).

Decisión de diseño propia, no preguntada explícitamente (documentada
acá): el "orden" de cada vuelta se BARAJA una vez al empezar la
vuelta (no un orden fijo alfabético/por código, repetido
idénticamente para siempre) -- concilia la letra del pedido ("del
ítem 1 al final, vuelve a empezar al agotarlos" -- SÍ hay un orden
fijo que se recorre completo antes de repetir) con que la función
siga sintiéndose "aleatoria" (el propio nombre de la función en toda
la app) en vez de sonar SIEMPRE en el mismo orden día tras día.
--------------------------------------------------------
"""

import random

from config.settings import cargar_rotacion_categorias, guardar_rotacion_categorias


def _clave_categoria(ruta_categoria: list) -> str:
    return " > ".join(ruta_categoria or [])


def _candidatos_por_ruta(explorador, ruta_categoria: list, recursivo: bool) -> dict:
    """{ruta_archivo: registro} de la categoría, resuelta EN VIVO. {}
    si la categoría no existe o está vacía."""
    if explorador is None or not ruta_categoria:
        return {}
    categoria = explorador.buscar_categoria_por_ruta(ruta_categoria)
    if categoria is None:
        return {}
    candidatos = explorador.listar_registros_de_categoria(categoria, recursivo)
    return {r["ruta"]: r for r in candidatos if r.get("ruta")}


def _reconciliar_orden_ronda(orden_previo: list, rutas_vivas: set) -> list:
    """Saca del orden lo que ya no está en la categoría (borrado/
    movido) y agrega al final lo que sea nuevo (archivo recién
    importado a la categoría) -- nunca se pierde un archivo nuevo
    esperando una vuelta completa nueva."""
    orden = [r for r in orden_previo if r in rutas_vivas]
    ya_presentes = set(orden)
    nuevos = sorted(rutas_vivas - ya_presentes)  # orden estable para lo nuevo
    orden.extend(nuevos)
    return orden


def elegir_por_rotacion(explorador, ruta_categoria: list, recursivo: bool = True, excluir_rutas: set = frozenset()):
    """Elige el PRÓXIMO archivo de la categoría según la rotación
    persistida -- NO avanza la posición todavía (ver
    `marcar_reproducido_por_rotacion`, se llama recién cuando el
    archivo arranca a sonar de verdad). `excluir_rutas` es una capa
    EXTRA opcional (ej. "ya sonó en este mismo bloque horario") --
    nunca reemplaza la rotación persistida, solo se suma; si excluir
    todo dejara la categoría sin candidatos, se ignora antes que dejar
    un hueco de silencio (mismo criterio de siempre en este proyecto).
    Devuelve `None` si la categoría no existe o está vacía."""
    mapa = _candidatos_por_ruta(explorador, ruta_categoria, recursivo)
    if not mapa:
        return None

    datos = cargar_rotacion_categorias()
    estado = datos["categorias"].get(_clave_categoria(ruta_categoria), {})
    orden = _reconciliar_orden_ronda(estado.get("orden_ronda_actual", []), set(mapa.keys()))
    reproducidos = set(estado.get("reproducidos_esta_ronda", [])) & set(orden)

    pendientes = [r for r in orden if r not in reproducidos]
    if not pendientes:
        # Vuelta agotada (o la reconciliación vació todo, ej. primera
        # vez) -- arranca una vuelta nueva, barajada.
        pendientes = list(orden)
        random.shuffle(pendientes)

    pendientes_sin_exclusion_extra = [r for r in pendientes if r not in excluir_rutas]
    elegidos = pendientes_sin_exclusion_extra or pendientes
    if not elegidos:
        return None
    return mapa[elegidos[0]]


def marcar_reproducido_por_rotacion(explorador, ruta_categoria: list, ruta_archivo: str, recursivo: bool = True):
    """Avanza la rotación DE VERDAD -- llamar únicamente en el momento
    en que `ruta_archivo` arranca a sonar de verdad. Persiste en disco
    (sobrevive reinicios y cambios de día)."""
    if not ruta_categoria or not ruta_archivo:
        return
    mapa = _candidatos_por_ruta(explorador, ruta_categoria, recursivo)

    datos = cargar_rotacion_categorias()
    clave = _clave_categoria(ruta_categoria)
    estado = datos["categorias"].setdefault(clave, {})
    estado["ruta"] = list(ruta_categoria)

    orden = _reconciliar_orden_ronda(estado.get("orden_ronda_actual", []), set(mapa.keys()))
    if ruta_archivo not in orden:
        orden.append(ruta_archivo)  # defensivo: el archivo ya no está en la categoría, o la reconciliación no lo vio

    reproducidos = set(estado.get("reproducidos_esta_ronda", [])) & set(orden)
    if ruta_archivo in reproducidos:
        # Vuelta completa CON este archivo ya marcado antes (repitió
        # porque la categoría se agotó, ver elegir_por_rotacion) --
        # arranca la vuelta siguiente de una, con este como único ya
        # reproducido en ella.
        reproducidos = set()
    reproducidos.add(ruta_archivo)

    estado["orden_ronda_actual"] = orden
    estado["reproducidos_esta_ronda"] = sorted(reproducidos)
    datos["categorias"][clave] = estado
    guardar_rotacion_categorias(datos)
