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

Bug real de fondo corregido (reporte real, con captura de la lista de
Emisión: "el aleatorio en la ventana 2 repite del mismo artista...
debe hacer un shuffle, un random entre toda la lista"): el `shuffle`
de arriba EXISTÍA en el código pero nunca se aplicaba de verdad --
vivía como variable LOCAL dentro de `elegir_por_rotacion()` (una
función que solo "espía" cuál sería el próximo, documentada
explícitamente como "NO avanza la posición todavía" -- nunca escribe
a disco) y se descartaba apenas esa función devolvía su resultado.
`marcar_reproducido_por_rotacion()` -- la ÚNICA función que persiste
el orden de la vuelta -- nunca barajaba nada, solo RECONCILIABA el
orden ya guardado (o, la primera vez que se usa una categoría,
`_reconciliar_orden_ronda([], rutas_vivas)` arma la lista nueva con
`sorted(...)` -- alfabético, a propósito "estable", nunca aleatorio).
Resultado real: la rotación caminaba la categoría entera en orden
ALFABÉTICO fijo, idéntico en cada vuelta -- con varios archivos que
comparten el mismo prefijo de título (ej. muchas descargas
"y2mate.com - <mismo artista> <tema>"), esos quedaban TODOS
consecutivos, sonando uno atrás del otro durante buena parte de la
vuelta. Confirmado con un script de reproducción antes de tocar nada
(15 archivos con el mismo prefijo + 5 sueltos: los primeros 5 picks
eran los sueltos, en orden alfabético, y los 15 siguientes eran
TODOS el mismo prefijo, seguidos, sin ningún barajado real).

Corregido moviendo el barajado al ÚNICO lugar que persiste de verdad
(`marcar_reproducido_por_rotacion`, ver más abajo) -- se dispara al
arrancar cada vuelta nueva (primera vez que se usa la categoría, O la
vuelta anterior ya se agotó), nunca a mitad de una vuelta en curso (el
orden ya comprometido de una vuelta sigue caminándose tal cual hasta
agotarla, como siempre). De paso, `_orden_barajado_por_artista()`
agrupa por `registro["artista"]` (cuando está cargado) y separa
EXPLÍCITAMENTE el grupo dominante del resto -- protección extra para
categorías con metadata de artista real: incluso con un shuffle
verdadero, una categoría MUY dominada por un solo artista puede seguir
dejando tramos largos consecutivos por pura probabilidad (el
"problema del shuffle de Spotify") -- ver el docstring de esa función
para el detalle completo de los 4 intentos que hicieron falta hasta
dar con un espaciado que no dependa de la suerte del sorteo. Si
`artista` está vacío en todos los registros (el caso real de estas
descargas, sin metadata separada de artista), degrada solo a un
shuffle plano de toda la lista -- nunca peor que antes, ya resuelve el
caso real reportado.
--------------------------------------------------------
"""

import random
from collections import defaultdict

from config.settings import cargar_rotacion_categorias, guardar_rotacion_categorias, vigencia_activa


def _clave_categoria(ruta_categoria: list) -> str:
    return " > ".join(ruta_categoria or [])


def _clave_artista(registro: dict) -> str:
    return (registro.get("artista") or "").strip().casefold()


def _orden_barajado_por_artista(rutas: list, mapa: dict) -> list:
    """Arma el orden de una vuelta NUEVA -- agrupa por artista e
    intercala entre grupos, en vez de un shuffle plano sobre toda la
    lista (ver la nota del bug real más arriba). Cada grupo se baraja
    aparte primero. Sin metadata de artista (todos los registros con
    `artista` vacío) degrada a un único grupo -- un shuffle plano de
    toda la lista, ya suficiente para el caso real reportado (títulos
    con el mismo prefijo, sin artista cargado aparte).

    Bug real corregido ANTES de llegar a Santiago (atrapado por un
    test dedicado con un caso adversarial: 15 archivos de un artista +
    5 de otros artistas, uno cada uno) -- CUATRO intentos previos
    fallaron, documentados acá para no repetirlos (los primeros tres,
    en orden): (1) round-robin ingenuo por turno -- deja el grupo
    grande DRENADO CONSECUTIVO apenas los chicos se agotan (racha 15
    sobre 15); (2) "Weighted Round Robin" clásico -- un grupo de 1
    solo ítem se consume YA MISMO (empata en proporción 0 con
    cualquiera) y desaparece para siempre, sin poder "guardarse" como
    separador para más adelante (racha 14 sobre 15); (3) reparto por
    posición objetivo con jitter aleatorio INDEPENDIENTE por ítem --
    mejoró el promedio (~6 de 15) pero con cola de mala suerte: en 200
    corridas, el peor caso observado siguió siendo 15 sobre 15 (los 5
    separadores, cada uno con su propio jitter sin coordinación entre
    sí, podían caer los 5 juntos en un extremo por puro azar); (4) el
    greedy clásico de "Reorganize String" (LeetCode 767/621 -- elegir
    siempre el grupo con MÁS restantes, salvo que sea el mismo del
    paso anterior) -- INTUITIVAMENTE el candidato correcto para este
    tipo de problema, pero mal aplicado acá: gasta los 5 separadores
    DE UNA, alternando con el grupo grande en los primeros 10 pasos
    (grande, chico, grande, chico...), y una vez que los 5 chicos se
    agotan (cada uno tiene un solo ítem, no vuelve a competir nunca
    más), los 10 ítems restantes del grupo grande no tienen con qué
    alternar y quedan TODOS consecutivos al final (racha real medida:
    10 sobre 15) -- el greedy es miope, gasta los separadores tan
    pronto como puede en vez de RESERVARLOS para más adelante en la
    vuelta.

    Corregido de raíz con espaciado PAREJO Y DETERMINÍSTICO del grupo
    dominante (el más grande), llenando los huecos que quedan con el
    resto (sea cual sea su artista real) en orden aleatorio: si el
    dominante tiene `k` ítems de un total de `n`, sus posiciones
    dentro de la vuelta se calculan cada `n/k` lugares —
    `_posiciones_parejas()` más abajo — así quedan repartidas a lo
    largo de TODA la vuelta por construcción, nunca por azar (sin
    jitter que pueda salir mal). El resto de los ítems (los 5
    separadores del ejemplo, sin importar que sean de artistas
    distintos entre sí) simplemente ocupa los huecos que sobran, en
    orden aleatorio. Confirmado con 200 corridas del caso adversarial:
    racha máxima SIEMPRE ≤ 4 (el mínimo matemático posible acá es 3,
    `ceil(15/6)`), nunca la cola de mala suerte de los intentos
    anteriores."""
    grupos = defaultdict(list)
    for ruta in rutas:
        grupos[_clave_artista(mapa.get(ruta, {}))].append(ruta)
    for lista in grupos.values():
        random.shuffle(lista)

    total = sum(len(lista) for lista in grupos.values())
    if total == 0 or len(grupos) <= 1:
        # Un solo grupo (o todos sin `artista` cargado) -- nada que
        # intercalar, el shuffle de arriba ya alcanza.
        return [ruta for lista in grupos.values() for ruta in lista]

    clave_dominante = max(grupos, key=lambda c: len(grupos[c]))
    dominante = grupos.pop(clave_dominante)
    resto = [ruta for lista in grupos.values() for ruta in lista]
    random.shuffle(resto)

    posiciones_dominante = set(_posiciones_parejas(len(dominante), total))
    orden = []
    it_dominante = iter(dominante)
    it_resto = iter(resto)
    for pos in range(total):
        orden.append(next(it_dominante) if pos in posiciones_dominante else next(it_resto))
    return orden


def _posiciones_parejas(cantidad: int, total: int) -> list:
    """`cantidad` posiciones enteras DISTINTAS dentro de
    `range(total)`, lo más parejamente repartidas posible (paso fijo
    `total/cantidad`, arrancando a mitad de paso) -- ver
    `_orden_barajado_por_artista()` más arriba. Sin aleatoriedad a
    propósito: es lo que garantiza que el espaciado nunca dependa de
    la suerte del sorteo."""
    if cantidad <= 0:
        return []
    paso = total / cantidad
    usadas = set()
    acumulado = paso / 2
    for _ in range(cantidad):
        pos = min(int(acumulado), total - 1)
        while pos in usadas and pos < total - 1:
            pos += 1
        while pos in usadas and pos > 0:
            pos -= 1
        usadas.add(pos)
        acumulado += paso
    return sorted(usadas)


def _candidatos_por_ruta(explorador, ruta_categoria: list, recursivo: bool) -> dict:
    """{ruta_archivo: registro} de la categoría, resuelta EN VIVO. {}
    si la categoría no existe o está vacía.

    Bug real corregido (reportado con audio real: "acaba de
    reproducirse una publicidad que debía vencerse el 20 de
    septiembre"): la vigencia de fecha (`registro["fecha_inicio"]`/
    `registro["fecha_fin"]`, editable desde Ventana 3 -> "📅
    Vigencia...") solo se chequeaba para una TANDA fija arrastrada
    directo a un bloque (`GestorPublicidad._item_valido()`) -- un
    Ítem Aleatorio es "válido" ahí sin mirar vigencia para NADA (no
    tiene ruta propia, recién se resuelve al llegarle el turno), y
    esta función nunca filtraba por vigencia tampoco -- un material
    vencido, si vivía en una categoría usada por rotación (el caso
    típico de "Publicidad"), seguía saliendo elegido para siempre,
    sin ningún control. Filtrar ACÁ, en el único lugar que arma la
    lista de candidatos de la categoría (compartido por
    `elegir_por_rotacion()` y `marcar_reproducido_por_rotacion()`),
    cierra el hueco de una sola vez -- un material vencido/no
    iniciado queda afuera de la rotación mientras dure fuera de
    vigencia, sin que haga falta sacarlo de la categoría a mano."""
    if explorador is None or not ruta_categoria:
        return {}
    categoria = explorador.buscar_categoria_por_ruta(ruta_categoria)
    if categoria is None:
        return {}
    candidatos = explorador.listar_registros_de_categoria(categoria, recursivo)
    return {
        r["ruta"]: r
        for r in candidatos
        if r.get("ruta") and vigencia_activa(
            {"fecha_inicio": r.get("fecha_inicio"), "fecha_fin": r.get("fecha_fin")}
        )
    }


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
        # vez) -- arranca una vuelta nueva, barajada. Esto es solo un
        # "espío" para decidir QUÉ devolver acá -- el barajado real
        # que de verdad queda vigente para el resto de la vuelta lo
        # persiste marcar_reproducido_por_rotacion() más abajo (ver la
        # nota del bug real en el docstring del módulo); si el
        # llamador nunca comprometiera este pick con esa función, esta
        # vuelta "fantasma" no dejaría ningún rastro en disco.
        pendientes = _orden_barajado_por_artista(orden, mapa)

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

    # Vuelta NUEVA -- primera vez que se usa esta categoría (nunca
    # hubo un `orden_ronda_actual` guardado -- OJO, chequear esto
    # sobre el valor CRUDO, antes de reconciliar: `_reconciliar_orden_
    # ronda([], rutas_vivas)` de una lista vacía devuelve la
    # categoría ENTERA vía `sorted(...)`, así que "reconciliado" NUNCA
    # da una lista vacía en la práctica -- chequear el resultado ya
    # reconciliado hubiera dejado a la categoría recién estrenada
    # afuera de este `if`, cayendo en el orden alfabético igual que el
    # bug original para su primera vuelta) o la vuelta anterior ya
    # estaba completa con este mismo archivo ya marcado en ella
    # (repitió porque se agotó, ver elegir_por_rotacion). Acá es el
    # ÚNICO lugar del módulo que persiste el orden de verdad -- por
    # eso es acá, y no en elegir_por_rotacion(), donde tiene que nacer
    # BARAJADO (ver la nota del bug real en el docstring del módulo:
    # antes esto solo reconciliaba el orden viejo, nunca lo barajaba,
    # y la rotación terminaba caminando la categoría siempre en el
    # mismo orden alfabético fijo).
    orden_guardado = estado.get("orden_ronda_actual")
    reproducidos = set(estado.get("reproducidos_esta_ronda", [])) & set(mapa.keys())

    if not orden_guardado or ruta_archivo in reproducidos:
        orden = _orden_barajado_por_artista(list(mapa.keys()), mapa)
        reproducidos = set()
    else:
        orden = _reconciliar_orden_ronda(orden_guardado, set(mapa.keys()))

    if ruta_archivo not in orden:
        orden.append(ruta_archivo)  # defensivo: el archivo ya no está en la categoría, o la reconciliación no lo vio
    reproducidos.add(ruta_archivo)

    estado["orden_ronda_actual"] = orden
    estado["reproducidos_esta_ronda"] = sorted(reproducidos)
    datos["categorias"][clave] = estado
    guardar_rotacion_categorias(datos)
