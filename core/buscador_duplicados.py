"""
core/buscador_duplicados.py
--------------------------------------------------------
Buscador de duplicados AVANZADO (motor puro, sin Qt) — pedido
explícito: reemplaza/supera al buscador simple por criterios exactos
combinables (gui/dialogo_duplicados.py, ronda anterior) con un motor
de coincidencia APROXIMADA, en 3 niveles de prioridad (el más
estricto primero, un par nunca se evalúa en más de un nivel):

  Nivel 1: nombre 100% + duración 100% + tamaño 100%
  Nivel 2: nombre 80%+ (similitud de texto) + duración 100% (exacta)
  Nivel 3: nombre 50%+ (similitud de texto) + duración 90%+ (similitud)

Pensado para bibliotecas grandes (~10-12 mil registros, ver rondas de
rendimiento anteriores): comparar TODOS los pares posibles (O(n²))
sería demasiado lento en el hardware modesto de Santiago. En cambio,
se ordenan los registros por duración y cada uno se compara solo
contra una VENTANA de vecinos cuya duración esté dentro del 90% de
similitud (el caso más laxo, nivel 3) -- los niveles 1 y 2, que
exigen duración EXACTA, son un subconjunto de esa misma ventana, así
que un solo recorrido ordenado cubre los 3 niveles sin repetir
trabajo. Esto es O(n log n + n·k), con k = candidatos dentro de la
ventana de cada ítem (típicamente chico para una biblioteca real).

Los grupos se arman con Union-Find: dos registros que matchean (en
cualquier nivel) quedan en el MISMO grupo — transitivamente, si A
matchea con B y B con C, los tres terminan juntos aunque A y C no
matcheen directo entre sí. Es el comportamiento esperado de un
buscador de duplicados (varias copias/variantes del mismo tema, no
solo pares sueltos).

Limitación de rendimiento CONOCIDA, documentada a propósito: si una
biblioteca tiene MUCHOS temas agrupados en un rango de duración chico
(ej. cientos de canciones todas de "más o menos 3 minutos", algo
frecuente en una biblioteca real), la ventana de comparación de esa
zona puede volverse grande y el costo de comparar nombres (aunque
`similitud_nombres` ya descarta pares claramente distintos con cotas
baratas antes de pagar el costo completo de SequenceMatcher.ratio())
puede tardar bastante -- una búsqueda de duplicados es una acción
MANUAL y ocasional (con cursor de espera + `callback_progreso` para
que la ventana no se sienta "colgada" mientras corre), no algo que
corre en cada segundo, así que se priorizó CORRECCIÓN sobre velocidad
extrema en el peor caso. Si en el uso real esto resulta molesto con la
biblioteca completa de Santiago, la mejora futura sería indexar por
"bloques" de nombre (ej. primeras letras) además de por duración.
--------------------------------------------------------
"""

from difflib import SequenceMatcher
import re

NIVEL_1_NOMBRE_TAMANO_DURACION = 1
NIVEL_2_NOMBRE_80_DURACION_EXACTA = 2
NIVEL_3_NOMBRE_50_DURACION_90 = 3

UMBRAL_NIVEL_2_NOMBRE = 0.8
UMBRAL_NIVEL_3_NOMBRE = 0.5
UMBRAL_NIVEL_3_DURACION = 0.9

DESCRIPCION_NIVEL = {
    NIVEL_1_NOMBRE_TAMANO_DURACION: "Nivel 1 — nombre, duración y tamaño idénticos",
    NIVEL_2_NOMBRE_80_DURACION_EXACTA: "Nivel 2 — nombre muy similar (80%+) y duración idéntica",
    NIVEL_3_NOMBRE_50_DURACION_90: "Nivel 3 — nombre parecido (50%+) y duración similar (90%+)",
}

_RE_ESPACIOS = re.compile(r"\s+")


def normalizar_titulo(texto: str) -> str:
    """minúsculas, sin espacios repetidos ni en los bordes -- para que
    un espacio de más o una diferencia de mayúsculas/minúsculas no
    cuenten como "nombre distinto"."""
    return _RE_ESPACIOS.sub(" ", (texto or "").strip().lower())


def similitud_nombres(a: str, b: str) -> float:
    """0.0 a 1.0 -- proporción de similitud de texto (difflib), sobre
    los títulos ya normalizados.

    Optimización de rendimiento importante para bibliotecas grandes
    con muchos archivos de la MISMA duración exacta (ej. decenas de
    separadores/station-IDs de 5 segundos, que caen todos en la misma
    "ventana" del buscador -- ver buscar_grupos_duplicados): antes de
    pagar el costo real de `.ratio()` (cuadrático en el peor caso), se
    prueban DOS cotas superiores baratas, de la más barata a la menos:
    (1) por longitud -- `ratio()` nunca puede superar
    `2·min(len_a,len_b)/(len_a+len_b)`, sin importar el contenido, O(1)
    sin construir nada; (2) `real_quick_ratio()` de SequenceMatcher --
    O(n), cuenta caracteres en común sin importar el orden. Contra el
    umbral MÁS BAJO que usa este motor (nivel 3, 0.5): si ninguna de
    las dos cotas llega a 0.5, la similitud real tampoco puede llegar
    (son cotas superiores garantizadas), así que se devuelve 0.0 sin
    calcular el ratio exacto -- válido acá porque el único uso real de
    este valor, en todo el módulo, es compararlo contra un umbral fijo
    (nunca se necesita el número exacto por debajo de 0.5)."""
    na, nb = normalizar_titulo(a), normalizar_titulo(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    len_a, len_b = len(na), len(nb)
    cota_longitud = 2 * min(len_a, len_b) / (len_a + len_b)
    if cota_longitud < UMBRAL_NIVEL_3_NOMBRE:
        return 0.0
    matcher = SequenceMatcher(None, na, nb)
    if matcher.real_quick_ratio() < UMBRAL_NIVEL_3_NOMBRE:
        return 0.0
    return matcher.ratio()


def duracion_a_segundos(texto):
    """"HH:MM:SS" (o "MM:SS") -> segundos totales. None si no se puede
    parsear, o si da 0 -- un registro sin duración real (nunca
    analizado, o con vínculo roto) no participa de ningún nivel."""
    if not texto:
        return None
    try:
        partes = [int(p) for p in str(texto).split(":")]
    except ValueError:
        return None
    if not partes:
        return None
    segundos = 0
    for p in partes:
        segundos = segundos * 60 + p
    return segundos if segundos > 0 else None


def similitud_duracion(seg_a: int, seg_b: int) -> float:
    """0.0 a 1.0 -- proporción menor/mayor entre las dos duraciones."""
    if not seg_a or not seg_b or seg_a <= 0 or seg_b <= 0:
        return 0.0
    menor, mayor = (seg_a, seg_b) if seg_a <= seg_b else (seg_b, seg_a)
    return menor / mayor


def nivel_de_coincidencia(entrada_a: dict, entrada_b: dict):
    """`entrada_*` = {"titulo", "duracion_seg", "tamano_bytes"} (ya
    resueltos por el llamador -- duracion_seg > 0 siempre). Devuelve
    el nivel (1/2/3) MÁS ESTRICTO que cumplen, o None si no coinciden
    en ninguno."""
    ratio_duracion = similitud_duracion(entrada_a["duracion_seg"], entrada_b["duracion_seg"])
    if ratio_duracion < UMBRAL_NIVEL_3_DURACION:
        return None

    sim_nombre = similitud_nombres(entrada_a["titulo"], entrada_b["titulo"])
    duracion_exacta = entrada_a["duracion_seg"] == entrada_b["duracion_seg"]

    if duracion_exacta:
        tamano_a, tamano_b = entrada_a.get("tamano_bytes"), entrada_b.get("tamano_bytes")
        nombre_exacto = normalizar_titulo(entrada_a["titulo"]) == normalizar_titulo(entrada_b["titulo"])
        if nombre_exacto and tamano_a is not None and tamano_b is not None and tamano_a == tamano_b:
            return NIVEL_1_NOMBRE_TAMANO_DURACION
        if sim_nombre >= UMBRAL_NIVEL_2_NOMBRE:
            return NIVEL_2_NOMBRE_80_DURACION_EXACTA

    if sim_nombre >= UMBRAL_NIVEL_3_NOMBRE:
        return NIVEL_3_NOMBRE_50_DURACION_90

    return None


class _UnionFind:
    def __init__(self, n):
        self._padre = list(range(n))

    def find(self, x):
        while self._padre[x] != x:
            self._padre[x] = self._padre[self._padre[x]]
            x = self._padre[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._padre[ra] = rb


def buscar_grupos_duplicados(entradas: list, callback_progreso=None) -> list:
    """`entradas`: lista de dicts con al menos "titulo"/"duracion" (en
    formato "HH:MM:SS") y, opcionalmente, "tamano_bytes" -- cualquier
    otra clave del dict del llamador se ignora acá, viaja aparte (el
    llamador mapea de vuelta por índice). Devuelve una lista de
    grupos, cada uno `{"indices": [...], "nivel": 1|2|3}` (índices =
    posiciones dentro de `entradas`), ordenados por nivel (los más
    estrictos primero) y, dentro de un mismo nivel, por tamaño de
    grupo descendente -- solo grupos de 2+ (duplicados reales).

    `callback_progreso(hechos, total)`, opcional: se llama cada tanto
    durante el recorrido -- pensado para que el llamador (GUI) pueda
    procesar eventos (`QApplication.processEvents()`) en una búsqueda
    grande y que la ventana no se sienta "colgada" mientras corre,
    mismo patrón ya usado en el resto de la app (import masivo,
    migración de biblioteca) -- este módulo en sí no importa Qt."""
    n = len(entradas)
    preparadas = []
    for i, e in enumerate(entradas):
        seg = duracion_a_segundos(e.get("duracion"))
        if seg is None:
            continue
        preparadas.append((seg, i, {
            "titulo": e.get("titulo", ""),
            "duracion_seg": seg,
            "tamano_bytes": e.get("tamano_bytes"),
        }))
    preparadas.sort(key=lambda t: t[0])

    uf = _UnionFind(n)
    aristas = []  # (i, j, nivel) -- solo pares que matchearon

    total = len(preparadas)
    for idx in range(total):
        if callback_progreso is not None and idx % 20 == 0:
            callback_progreso(idx, total)
        seg_i, i, entrada_i = preparadas[idx]
        limite = seg_i / UMBRAL_NIVEL_3_DURACION
        j_idx = idx + 1
        while j_idx < total and preparadas[j_idx][0] <= limite:
            seg_j, j, entrada_j = preparadas[j_idx]
            nivel = nivel_de_coincidencia(entrada_i, entrada_j)
            if nivel is not None:
                uf.union(i, j)
                aristas.append((i, j, nivel))
            j_idx += 1

    grupos_por_raiz = {}
    for _, i, _ in preparadas:
        raiz = uf.find(i)
        grupos_por_raiz.setdefault(raiz, []).append(i)

    mejor_nivel_por_raiz = {}
    for i, j, nivel in aristas:
        raiz = uf.find(i)
        actual = mejor_nivel_por_raiz.get(raiz)
        if actual is None or nivel < actual:
            mejor_nivel_por_raiz[raiz] = nivel

    resultado = []
    for raiz, indices in grupos_por_raiz.items():
        if len(indices) < 2:
            continue
        resultado.append({
            "indices": sorted(indices),
            "nivel": mejor_nivel_por_raiz.get(raiz, NIVEL_3_NOMBRE_50_DURACION_90),
        })

    resultado.sort(key=lambda g: (g["nivel"], -len(g["indices"])))
    return resultado


def sugerir_indice_a_mantener(entradas_grupo: list) -> int:
    """Heurística del "plan automático" (modo en masa): sugiere cuál
    de los miembros del grupo conviene MANTENER (posición dentro de
    `entradas_grupo`, no el índice global) -- el resto queda sugerido
    para eliminar. Preferencia, en orden: (1) tiene ruta vinculada de
    verdad (un duplicado sin vincular es el candidato más débil), (2)
    tiene más metadata completa (artista no vacío, tamaño cacheado),
    (3) el primero de la lista, como desempate estable."""
    def puntaje(entrada):
        tiene_ruta = 1 if entrada.get("ruta") else 0
        tiene_artista = 1 if (entrada.get("artista") or "").strip() else 0
        tiene_tamano = 1 if entrada.get("tamano_bytes") is not None else 0
        return (tiene_ruta, tiene_artista, tiene_tamano)

    mejor_indice = 0
    mejor_puntaje = puntaje(entradas_grupo[0])
    for i in range(1, len(entradas_grupo)):
        p = puntaje(entradas_grupo[i])
        if p > mejor_puntaje:
            mejor_puntaje = p
            mejor_indice = i
    return mejor_indice
