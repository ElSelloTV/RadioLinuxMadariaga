"""
gui/styles.py
--------------------------------------------------------
Hoja de estilos QSS centralizada para toda la aplicación.
Mantener el estilo aislado aquí permite cambiar el theme
completo sin tocar ni una línea de lógica ni de layout.

Dos temas disponibles (Configuración → General → "Tema visual"):
"oscuro" (default, sin cambios respecto de siempre) y "claro" (pedido
explícito, "diseñá el tema Claro... exactamente igual [a Dinesat],
sobre todo los colores" — screenshot real de Hardata Dinesat 9 pasado
por Santiago: paneles caqui/tan cálidos, título de cada ventana en
verde oscuro, contadores en un display marrón oscuro con texto crema).

Los colores de ESTADO/SEMÁNTICOS (rojo=reproduciendo, verde=siguiente,
celeste=selección, naranja=armado, etc.) son IGUALES en los dos temas
a propósito — son significado, no superficie (mismo criterio ya
establecido: "los colores que yo elijo... es solo para
identificarlos", y el propio Dinesat real usa el mismo rojo/verde en
su tema claro y en el oscuro). Solo cambian los colores de SUPERFICIE
(fondo/panel/header/borde/texto), agrupados en PALETA_OSCURA/
PALETA_CLARA y aplicados vía _generar_qss(paleta).
--------------------------------------------------------
"""

# Colores de ESTADO/SEMÁNTICOS — iguales en cualquier tema, ver nota
# arriba. Referenciados directo por nombre en _generar_qss() (no van
# en las paletas de superficie) y por el resto de gui/*.py (import
# directo, ej. common_widgets.py/panel_reproductor.py para pintar
# filas rojo/verde).
COLOR_REPRODUCIENDO = "#c0392b"   # Rojo: evento en emisión
COLOR_SIGUIENTE = "#27ae60"       # Verde: próximo evento
# Pedido explícito ("el automático en rojo, como Dinesat real"): una
# ronda anterior lo había pasado a dorado porque, con TEXTO ("AUTO"/
# "MANUAL") al lado del botón Stop (también rojo en ese momento), las
# dos lecturas se confundían fácil. Ahora que TODOS los botones de
# transporte quedaron sin texto ni color propio salvo 3 (Play verde,
# HORA/TEMP celeste, AUTOMÁTICO rojo — pedido explícito), Stop volvió
# al gris genérico de cualquier botón — la confusión de origen ya no
# existe, así que AUTOMÁTICO puede volver a ser rojo como en Dinesat,
# distinguiéndose de Stop por el ÍCONO (glifo), no por el color.
COLOR_AUTOMATICO_ON = COLOR_REPRODUCIENDO
COLOR_AUTOMATICO_ON_BORDE = "#e74c3c"
# Pedido explícito (ronda posterior): "deja rojo cuando está activo y
# un rojo 'desactivado' con borde rojo negro pero un rojo más opaco" —
# ya no gris genérico como el resto de los botones cuando está OFF,
# sino un rojo apagado/opaco (mismo tono en los dos estados, distinta
# intensidad) con un borde rojo-negro bien oscuro.
COLOR_AUTOMATICO_OFF = "#5c2b2b"
COLOR_AUTOMATICO_OFF_BORDE = "#2b0f0f"
COLOR_SELECCION = "#5dade2"       # Celeste: cursor de selección (Dinesat), nunca reemplaza rojo/verde
COLOR_ARMADO = "#e67e22"          # Naranja: acción diferida armada (Stop diferido)

# Fondo de las LISTAS de Ventana 1 y 2 (`tree_publicidad`/`tree_reproductor`
# — este último también lo usa la Auxiliar) — pedido explícito, con
# captura real de Dinesat: "el tema claro de Dinesat... tiene fondo
# negro... copiá exactamente... la diferencia del negro y gris
# oscuro... aplicá esto en tema oscuro COMO claro". A diferencia del
# resto de la superficie (paneles/chrome, que sí cambian entre
# PALETA_OSCURA/PALETA_CLARA), el fondo de ESTAS DOS listas puntuales
# es casi negro en LOS DOS temas de esta app — igual que en Dinesat,
# donde ni su tema "claro" aclara la lista de reproducción (el rojo/
# verde/celeste de estado necesitan un fondo bien oscuro para
# resaltar). No toca Ventana 3 (tree_archivos/tree_categorias), fuera
# del pedido ("el contenido de las ventanas 1 y 2").
COLOR_LISTA_V1V2_FONDO = "#141414"
COLOR_LISTA_V1V2_ALTERNO = "#1e1e1e"
COLOR_LISTA_V1V2_HEADER_FONDO = "#2a2a2a"

# Ventana 3 (Explorador) — pedido explícito, ronda posterior: "aplica
# el mismo color de la ventana negro en el explorador. diferencia
# categoria de la ventana de elementos" — mismo criterio que arriba
# (fondo casi negro FIJO en los dos temas), pero con DOS tonos
# ligeramente distintos para que Categorías (izquierda) y Archivos/
# Elementos (derecha) se distingan entre sí a simple vista, en vez de
# verse como un solo bloque negro sin límites. Archivos reusa EXACTO
# el mismo tono que V1/V2 ("el mismo color de la ventana negro");
# Categorías queda un escalón más claro.
COLOR_LISTA_V3_ARCHIVOS_FONDO = COLOR_LISTA_V1V2_FONDO
COLOR_LISTA_V3_ARCHIVOS_ALTERNO = COLOR_LISTA_V1V2_ALTERNO
COLOR_LISTA_V3_CATEGORIAS_FONDO = "#242424"
COLOR_LISTA_V3_CATEGORIAS_ALTERNO = "#2e2e2e"
COLOR_LISTA_V3_HEADER_FONDO = COLOR_LISTA_V1V2_HEADER_FONDO

# Paleta de SUPERFICIE del tema OSCURO (default, sin cambios respecto
# de siempre — mismos valores que antes vivían como constantes
# sueltas COLOR_FONDO_PRINCIPAL/COLOR_FONDO_PANEL/etc.). `chrome_fondo`/
# `header_columnas_fondo` son claves NUEVAS (ronda de ajuste del tema
# Claro) que antes compartían el valor de `fondo_header` — acá quedan
# iguales a `fondo_header` a propósito, para que el tema oscuro no
# cambie ni un píxel.
PALETA_OSCURA = {
    "fondo_principal": "#2b2b2b",
    "fondo_panel": "#3a3a3a",
    "fondo_header": "#1f1f1f",
    "chrome_fondo": "#1f1f1f",
    "header_columnas_fondo": "#1f1f1f",
    "borde": "#555555",
    "texto": "#e0e0e0",
    "texto_secundario": "#9a9a9a",
    "tree_fondo": "#262626",
    "tree_alterno": "#2d2d2d",
    "tree_seleccion": "#45688e",
    "menubar_hover": "#444444",
    "menu_item_hover": "#505050",
    "toolbar_boton": "#333333",
    "toolbar_boton_hover": "#444444",
    "toolbar_boton_pressed": "#222222",
    "boton_fondo": "#3d3d3d",
    "boton_hover": "#4a4a4a",
    "boton_pressed": "#2a2a2a",
    "contador_fondo": "#101010",
    "contador_texto": "#f5f5f5",
    "scrollbar_handle": "#5a5a5a",
}

# Paleta de SUPERFICIE del tema CLARO — pedido explícito, imitando la
# imagen real de Hardata Dinesat 9 que pasó Santiago, con 3 ajustes
# pedidos en la ronda siguiente ("la letra sigue blanca", "sacá el
# verde de los botones de arriba", "no tan caqui, más plata"):
# - `fondo_header` (verde oscuro) quedó RESERVADO solo para el título
#   de cada panel (QGroupBox::title, "PROGRAMACIÓN"/"EMISIÓN"/etc — el
#   equivalente a la barra de título de cada ventana de Dinesat). La
#   toolbar/menú/barra de estado, que en la captura real de Dinesat
#   son gris CLARO (no verde), pasan a usar `chrome_fondo` — un gris
#   plata neutro, distinto del verde de los paneles.
# - Fondo general aclarado y desaturado ("no tan caqui, más plata")
#   respecto de la primera versión (`#c7bb98`/`#d6cba8`, bastante más
#   saturado) a un beige-plata mucho más neutro.
# - `header_columnas_fondo` (encabezado de columnas de las listas,
#   "Título/Duración/Código") queda un tostado medio, con contraste
#   suficiente para texto blanco sin necesitar ser tan oscuro como el
#   título de panel.
PALETA_CLARA = {
    "fondo_principal": "#d6d2c4",
    "fondo_panel": "#e2ded0",
    "fondo_header": "#2e4a2e",
    "chrome_fondo": "#c9c4b0",
    "header_columnas_fondo": "#8f7f52",
    "borde": "#ada088",
    "texto": "#241c10",
    "texto_secundario": "#6b5d3f",
    "tree_fondo": "#f0ecdf",
    "tree_alterno": "#e6e0cd",
    "tree_seleccion": "#4a7ab5",
    "menubar_hover": "#b8ac86",
    "menu_item_hover": "#c9bd97",
    "toolbar_boton": "#ded7bf",
    "toolbar_boton_hover": "#e9e2c9",
    "toolbar_boton_pressed": "#c0b48a",
    "boton_fondo": "#ded7bf",
    "boton_hover": "#e9e2c9",
    "boton_pressed": "#c0b48a",
    "contador_fondo": "#3c2a25",
    "contador_texto": "#f2e6c9",
    "scrollbar_handle": "#a8996f",
}


def _generar_qss(p: dict) -> str:
    """Arma el QSS completo de la app a partir de una paleta de
    superficie (`PALETA_OSCURA`/`PALETA_CLARA`) — mismos selectores
    para los dos temas, solo cambian los colores; así un tema nuevo
    nunca puede "olvidarse" de un selector que el otro sí tiene."""
    return f"""
QMainWindow {{
    background-color: {p['fondo_principal']};
}}

QWidget {{
    background-color: {p['fondo_principal']};
    color: {p['texto']};
    font-family: "DejaVu Sans", "Noto Sans", sans-serif;
    font-size: 10pt;
}}

/* ---------- Menú superior ---------- */
/* Pedido explícito ("en los botones de arriba se ve un fondo verde,
   sacarlo"): la toolbar/menú son CHROME general de la app, no la
   "barra de título" de un panel puntual — usan `chrome_fondo` (gris
   plata en el tema claro), nunca `fondo_header` (verde oscuro,
   reservado solo para QGroupBox::title más abajo, el equivalente a
   la barra de título de CADA ventana en Dinesat). `color: {{p['texto']}}`
   en vez de blanco fijo -- se ajusta solo a cualquier tono de
   chrome_fondo, oscuro o claro. */
QMenuBar {{
    background-color: {p['chrome_fondo']};
    color: {p['texto']};
    border-bottom: 1px solid {p['borde']};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
}}
QMenuBar::item:selected {{
    background-color: {p['menubar_hover']};
    border-radius: 3px;
}}
QMenu {{
    background-color: {p['fondo_panel']};
    border: 1px solid {p['borde']};
}}
QMenu::item:selected {{
    background-color: {p['menu_item_hover']};
}}

/* ---------- Toolbar superior ---------- */
QToolBar {{
    background-color: {p['chrome_fondo']};
    border-bottom: 1px solid {p['borde']};
    spacing: 4px;
    padding: 3px;
}}
QToolButton {{
    background-color: {p['toolbar_boton']};
    border: 1px solid {p['borde']};
    border-radius: 4px;
    padding: 4px;
}}
QToolButton:hover {{
    background-color: {p['toolbar_boton_hover']};
}}
QToolButton:pressed {{
    background-color: {p['toolbar_boton_pressed']};
}}

/* ---------- Paneles / GroupBox de cada ventana ---------- */
QGroupBox {{
    background-color: {p['fondo_panel']};
    border: 1px solid {p['borde']};
    border-radius: 4px;
    margin-top: 16px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 1px 5px;
    background-color: {p['fondo_header']};
    border: 1px solid {p['borde']};
    border-radius: 3px;
    color: white;
    font-size: 11pt;
}}

/* Toolbar principal única (pedido explícito, "rediseño compacto":
   el QMenuBar clásico se sacó del todo — ver main_window.py — así
   que esta es la ÚNICA fila de navegación de arriba). Padding/fuente
   más chicos que el QToolButton por defecto de Qt para no repetir el
   mismo problema de "doble fila" con una sola fila más alta de lo
   necesario. */
QToolBar#toolbarPrincipal {{
    padding: 1px;
    spacing: 3px;
}}
QToolBar#toolbarPrincipal QToolButton {{
    padding: 3px 7px;
    font-size: 9pt;
}}

/* ---------- TreeView / TreeWidget (Publicidad y Explorador) ---------- */
QTreeWidget {{
    background-color: {p['tree_fondo']};
    alternate-background-color: {p['tree_alterno']};
    border: 1px solid {p['borde']};
    show-decoration-selected: 1;
}}
QTreeWidget::item {{
    padding: 3px;
}}
QTreeWidget::item:selected {{
    background-color: {p['tree_seleccion']};
    color: white;
}}
QHeaderView::section {{
    background-color: {p['header_columnas_fondo']};
    color: white;
    padding: 2px;
    border: 1px solid {p['borde']};
}}

/* ---------- Ventana 3 (Explorador): tipografía más chica en los
   ítems (pedido explícito) para tener más visibilidad de los datos
   sin agrandar la ventana. Fondo casi negro FIJO en los dos temas
   (pedido explícito, ronda posterior: "aplica el mismo color de la
   ventana negro en el explorador") — Categorías y Archivos con dos
   tonos distintos ("diferencia categoria de la ventana de
   elementos"), y texto claro FIJO (nunca {{p['texto']}}, que en el
   tema Claro es oscuro y quedaría ilegible sobre negro — mismo
   criterio que ya se usó para V1/V2). Un ítem con color de género
   propio (`_pintar_por_genero`) sigue pisando esto con su propio
   fondo/texto, sin cambios ahí — esta regla solo cubre filas SIN
   color asignado. ---------- */
QTreeWidget#tree_archivos, QTreeWidget#tree_categorias {{
    font-size: 8pt;
}}
QTreeWidget#tree_archivos::item, QTreeWidget#tree_categorias::item {{
    padding: 1px;
    color: #e0e0e0;
}}
QTreeWidget#tree_archivos {{
    background-color: {COLOR_LISTA_V3_ARCHIVOS_FONDO};
    alternate-background-color: {COLOR_LISTA_V3_ARCHIVOS_ALTERNO};
}}
QTreeWidget#tree_categorias {{
    background-color: {COLOR_LISTA_V3_CATEGORIAS_FONDO};
    alternate-background-color: {COLOR_LISTA_V3_CATEGORIAS_ALTERNO};
}}
QTreeWidget#tree_archivos QHeaderView::section,
QTreeWidget#tree_categorias QHeaderView::section {{
    background-color: {COLOR_LISTA_V3_HEADER_FONDO};
    color: #e0e0e0;
}}

/* Barra de búsqueda de Ventana 3 (pedido explícito, ronda posterior:
   "agregá fondo negro sobre la barra de búsqueda") — mismo criterio
   que las listas de arriba: fondo casi negro FIJO en los dos temas
   (reusa el mismo tono que tree_archivos), texto claro. Sin esto
   quedaba con el fondo blanco por defecto del estilo Fusion, fuera de
   lugar al lado de un Explorador ya oscurecido. */
QLineEdit#txtBusqueda {{
    background-color: {COLOR_LISTA_V3_ARCHIVOS_FONDO};
    color: #e0e0e0;
    border: 1px solid {p['borde']};
    border-radius: 3px;
    padding: 3px 6px;
}}

/* Ventana 3, árbol de categorías: NADA de QSS custom sobre ::branch a
   propósito (bug real de la ronda anterior, corregido acá) — las
   líneas de conexión que se habían agregado ahí ("hasta 5 niveles...
   colores, negrita, líneas") tienen un efecto secundario real de Qt:
   en cuanto un stylesheet toca CUALQUIER pseudo-estado de ::branch,
   Qt deja de dibujar el triángulo NATIVO de expandir/colapsar para
   los estados que ese QSS no cubre explícitamente (acá nunca se
   cubrieron :closed/:open) — el triángulo quedaba invisible en la
   práctica, justo la señal que hace falta para saber que una
   categoría tiene más niveles debajo. Corregido sacando el override
   por completo: `tree_categorias` vuelve a usar el triángulo nativo
   del estilo activo (Fusion), que SIEMPRE se dibuja solo en cualquier
   ítem con hijos, sin depender de assets propios. La jerarquía visual
   sigue viva vía negrita/cursiva/color por nivel
   (_aplicar_estilo_por_nivel, gui/ventana_explorador.py) y
   setRootIsDecorated(True) (mismo archivo) asegura que el triángulo
   se vea también en las categorías de nivel 1. */

/* ---------- Modo compacto: Ventana 1 (Publicidad) y Ventana 2 /
   Auxiliar (Emisión) — fuente y relleno más chicos para poder
   achicar columnas de verdad (antes un mínimo de sección lo
   impedía). ---------- */
QTreeWidget#tree_publicidad, QTreeWidget#tree_reproductor, QTreeWidget#tree_programador {{
    font-size: 8pt;
    background-color: {COLOR_LISTA_V1V2_FONDO};
    alternate-background-color: {COLOR_LISTA_V1V2_ALTERNO};
}}
/* Texto claro FIJO (no {{p['texto']}}) — con el fondo casi negro de
   arriba, el texto oscuro del tema Claro (pensado para fondos
   caqui/plata del resto de la app) quedaría ilegible acá. Un ítem
   rojo/verde ya trae su propio blanco explícito por Python
   (_color_para_estado), esto solo cubre el estado NORMAL. El árbol
   del Programador (`tree_programador`, pedido explícito "utilizá
   también una paleta con negros y grises") reusa el MISMO tono que
   V1/V2 en vez de uno propio — es conceptualmente el mismo tipo de
   lista (bloques + ítems), aunque viva en un QDialog aparte. */
QTreeWidget#tree_publicidad::item, QTreeWidget#tree_reproductor::item, QTreeWidget#tree_programador::item {{
    padding: 1px;
    color: #e0e0e0;
}}
QTreeWidget#tree_publicidad QHeaderView::section,
QTreeWidget#tree_reproductor QHeaderView::section,
QTreeWidget#tree_programador QHeaderView::section {{
    background-color: {COLOR_LISTA_V1V2_HEADER_FONDO};
    color: #e0e0e0;
}}

/* Ventana 1 (Publicidad) y Ventana 2 (Emisión): selección con
   relleno CELESTE sólido + letra negra, SIN borde (pedido explícito,
   ronda posterior: "sacá el celeste del contorno... sin borde dejá
   una selección con relleno celeste y letra negras"). Esto aplica
   SOLO a ítems SIN estado (ni rojo ni verde) — un ítem en rojo/verde
   NUNCA debe perder su color al seleccionarlo (regla permanente,
   "esto es siempre"): con QSS puro esa excepción no se puede
   expresar (la regla ::item:selected no puede "preguntar" si el
   ítem tiene un color propio), así que el delegado
   DelegadoConservaColorEstado (gui/common_widgets.py) intercepta el
   pintado ANTES de que esta regla se aplique — para un ítem
   rojo/verde seleccionado, pinta directamente su propio color sin
   pasar por acá, sin fill celeste y sin ningún borde. */
QTreeWidget#tree_reproductor::item:selected, QTreeWidget#tree_publicidad::item:selected {{
    background-color: {COLOR_SELECCION};
    color: black;
    border: none;
}}

/* ---------- Botones de transporte ---------- */
QPushButton {{
    background-color: {p['boton_fondo']};
    border: 1px solid {p['borde']};
    border-radius: 4px;
    padding: 6px 10px;
}}
QPushButton:hover {{
    background-color: {p['boton_hover']};
}}
QPushButton:pressed {{
    background-color: {p['boton_pressed']};
}}

/* Botones con relleno de "identidad" saturado (Play/Play principal,
   más abajo) llevan `color: white` EXPLÍCITO — sin esto heredarían el
   `color` genérico de QWidget (que en el tema claro es un marrón
   oscuro, ilegible sobre estos rellenos también oscuros/saturados). */
QPushButton#btnPlay {{
    background-color: #1e8449;
    color: white;
    font-weight: bold;
}}
QPushButton#btnPlay:hover {{ background-color: #229954; }}

/* Grilla de transporte estilo Dinesat SIN TEXTO (pedido explícito:
   "se podrá poner sin texto y recrear el mismo diseño de botones...
   el resto grises como la imagen en tema claro y oscuro"): Stop/Fade/
   Pausa/Cut/Stop-diferido (en reposo) ya NO tienen un color de
   "identidad" propio — vuelven al gris genérico de cualquier botón
   de la app (`p['boton_fondo']`, mismo en los dos temas por diseño),
   la diferencia entre ellos es solo el ÍCONO/glifo, como en Dinesat
   real. Solo 3 botones conservan color propio, IGUAL en los dos
   temas por ser significado y no superficie (mismo criterio que
   rojo/verde/celeste de las listas): Play (verde), HORA/TEMP
   (celeste) y AUTOMÁTICO (rojo cuando está activo).
   Pedido explícito, tras ver la app real en pantalla ("no te parecen
   un poco grandes?"): bajado de 16pt/34x30 a 11pt/24x22 — el glifo
   sigue siendo el único contenido del botón, pero sin ocupar tanto
   espacio de la grilla como cuando compartía tamaño con el texto que
   tenía antes. */
QPushButton[class="btnTransporte"] {{
    padding: 2px 5px;
    font-size: 11pt;
    min-width: 24px;
    min-height: 22px;
}}

/* Botones de acción de la Ventana 3 (Explorador) — pedido explícito
   ("se va de ancho, imposible trabajar así" en una pantalla de
   1360px): mismo criterio que btnTransporte, padding/fuente más
   chicos para que las filas de botones (Agregar/Info/Reemplazar/
   Eliminar, Categoría/Sub/Eliminar categoría) pidan menos ancho
   mínimo. */
QPushButton[class="btnCompacto"] {{
    padding: 3px 5px;
    font-size: 8pt;
}}

/* ---------- Grilla de transporte estilo Dinesat (pedido explícito,
   "igualá lo más que pueda... la distribución de las ventanas 1 y 2";
   ronda posterior, sin texto: "recrear el mismo diseño de botones...
   botón play verde, el de la hora celeste, el automático en rojo, el
   resto grises") ----------
   Botón grande verde: Play SI está en silencio, "Siguiente con
   fundido" si ya hay algo sonando — las dos funciones en un botón,
   ahora solo el glifo "▶", sin texto. Pedido explícito, ronda
   posterior ("el botón play es rectangular, hacelo cuadrado tal cual
   Dinesat"): `padding: 0` acá (en vez de heredar el `6px 10px`
   asimétrico del QPushButton genérico) para que el glifo quede
   centrado en un cuadrado de verdad — el tamaño FIJO real
   (`setFixedSize`, igual en las dos ventanas) lo pone
   panel_reproductor.py/ventana_publicidad.py en Python. */
QPushButton#btnPlayPrincipal {{
    background-color: #1e8449;
    border: 2px solid #2ecc71;
    color: white;
    font-weight: bold;
    font-size: 20pt;
    padding: 0;
}}
QPushButton#btnPlayPrincipal:hover {{ background-color: #229954; }}
QPushButton#btnPlayPrincipal:pressed {{ background-color: #145a32; }}

/* Fade-Stop y Cut ya NO tienen relleno de "identidad" propio (pedido
   explícito "el resto grises") -- heredan el gris genérico de
   QPushButton de arriba, la diferencia con Stop/Pausa/Stop-diferido
   es solo el glifo/ícono, igual que en Dinesat real. */

/* Botón "HORA/TEMP" manual (pedido explícito: "un botón color azul...
   reproducirse la hora y la temperatura de manera manual"; ronda
   posterior: "el de la hora celeste"): mismo celeste que ya usa
   COLOR_SELECCION para el cursor de selección de las listas
   (#5dade2) -- hardcodeado acá (no como referencia a la constante)
   porque este bloque QSS se genera ANTES de que COLOR_SELECCION se
   defina más abajo en el archivo. Texto NEGRO (no blanco): el celeste
   es un color claro, el contraste con blanco queda pobre. */
QPushButton#btnHthManual {{
    background-color: #5dade2;
    color: black;
    font-weight: bold;
}}
QPushButton#btnHthManual:hover {{ background-color: #7fc1ea; }}

/* Stop diferido: deja terminar el ítem actual y recién ahí frena
   todo — queda "armado" (naranja) hasta que se ejecute o se
   desarme con un segundo click, mismo patrón visual que el botón
   AUTOMÁTICO (propiedad dinámica + QSS). */
QPushButton#btnStopDiferido[armado="true"] {{
    background-color: {COLOR_ARMADO};
    border: 2px solid #f39c12;
    font-weight: bold;
    color: white;
}}
QPushButton#btnStopDiferido[armado="false"] {{
    background-color: {p['boton_fondo']};
}}

/* Nombre de la estación (pedido explícito, imitando el nameplate de
   Dinesat) — puramente decorativo, texto fijo. Se apoya sobre
   fondo_header (siempre oscuro en los dos temas, ver paletas de
   arriba), así el mismo naranja se lee bien en cualquiera de los
   dos. */
QLabel#lblNombreEstacion {{
    color: #e67e22;
    font-weight: bold;
    font-size: 8pt;
    letter-spacing: 1px;
}}

/* AUTOMÁTICO (pedido explícito, "el automático en rojo, como
   Dinesat real"): ON = rojo sólido (mismo color que "reproduciendo"
   en las listas, reutilizado a propósito — es un color semántico, no
   de superficie, igual en los dos temas). OFF = rojo "desactivado"
   (pedido explícito, ronda posterior: "un rojo desactivado con borde
   rojo negro pero un rojo más opaco") — mismo tono de familia, más
   apagado/opaco que el ON, con un borde rojo-negro bien oscuro; ya no
   comparte el gris genérico de Stop/Fade/Pausa/Cut, este botón
   siempre se lee como AUTOMÁTICO de un vistazo, prendido o apagado.
   Sin texto (antes "AUTO"/"MANUAL") — el glifo (🔁) es el mismo en
   los dos estados, distinto en FORMA de Stop (■), la diferencia de
   color hace el resto. */
QPushButton#btnAutomatico[activo="true"] {{
    background-color: {COLOR_AUTOMATICO_ON};
    border: 2px solid {COLOR_AUTOMATICO_ON_BORDE};
    font-weight: bold;
    color: white;
}}
QPushButton#btnAutomatico[activo="false"] {{
    background-color: {COLOR_AUTOMATICO_OFF};
    border: 2px solid {COLOR_AUTOMATICO_OFF_BORDE};
    color: #d8b8b8;
}}

/* ---------- Contadores de tiempo (estilo display) ----------
   Antes 26pt (impedía achicar columnas), después 14pt lado a lado.
   Pedido explícito de esta ronda: los relojes pasan a apilarse a la
   IZQUIERDA (uno arriba, otro abajo) en vez de ir lado a lado —
   bajado a 11pt + ancho máximo fijo para que la columna quede
   angosta de verdad y sobre espacio para "Ahora"/"Luego" a la
   derecha en la misma fila. En el tema claro, este display imita el
   reloj marrón oscuro con texto crema del "00:00:00" de Dinesat. */
QLabel#lblTiempoTranscurrido, QLabel#lblTiempoRestante {{
    background-color: {p['contador_fondo']};
    color: {p['contador_texto']};
    border: 1px solid {p['borde']};
    border-radius: 4px;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 9pt;
    font-weight: bold;
    padding: 0px 3px;
}}
QLabel#lblTituloBloqueActivo {{
    color: {p['texto_secundario']};
    font-style: italic;
}}
/* Leyenda junto al botón AUTOMÁTICO (Ventana 1) — responde SOLO al
   estado de ese botón (Activo/Manual), pedido explícito: nunca debe
   mostrar el ítem en reproducción ahí. */
QLabel#lblEstadoAutomatico[activo="true"] {{
    color: {COLOR_REPRODUCIENDO};
    font-weight: bold;
}}
QLabel#lblEstadoAutomatico[activo="false"] {{
    color: {p['texto_secundario']};
}}
/* "Ahora:"/"Luego:" junto al título en Ventana 1/2/Auxiliar — pedido
   explícito, más robusto que depender solo del color de fila. */
QLabel#lblEtiquetaAhoraLuego {{
    color: {p['texto_secundario']};
    font-size: 7pt;
    font-weight: bold;
}}
/* Contorno rojo/verde alrededor de cada fila "Ahora"/"Luego" — mismo
   concepto de color que la fila de la lista, pedido explícito.
   Padding reducido (pedido explícito, "rediseño compacto": el
   cartel Ahora/Luego era muy grande) — el contorno de color sigue
   siendo la misma señal visual de siempre, solo ocupa menos alto. */
QFrame#frameAhora {{
    border: 2px solid {COLOR_REPRODUCIENDO};
    border-radius: 3px;
    padding: 0px 2px;
}}
QFrame#frameLuego {{
    border: 2px solid {COLOR_SIGUIENTE};
    border-radius: 3px;
    padding: 0px 2px;
}}

/* ---------- Barra de estado ---------- */
QStatusBar {{
    background-color: {p['chrome_fondo']};
    border-top: 1px solid {p['borde']};
    color: {p['texto_secundario']};
}}

/* ---------- Splitter entre las 3 ventanas ---------- */
QSplitter::handle {{
    background-color: {p['borde']};
    width: 3px;
}}

/* ---------- ScrollBars discretas ---------- */
QScrollBar:vertical {{
    background: {p['fondo_panel']};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {p['scrollbar_handle']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


# Los dos temas generados de una sola vez a partir de la misma
# plantilla — ver _generar_qss(). QSS_APLICACION es el default de
# siempre (tema oscuro), usado por cualquier código que todavía lo
# importe directo (compatibilidad); qss_para_tema() es el punto de
# entrada nuevo, usado por main.py y por
# MainWindow._aplicar_configuracion_en_vivo() para poder cambiar de
# tema sin reiniciar la app.
QSS_APLICACION = _generar_qss(PALETA_OSCURA)
QSS_APLICACION_CLARO = _generar_qss(PALETA_CLARA)


def qss_para_tema(tema: str) -> str:
    """`tema` es el valor guardado en config_general.json →
    general.tema ("oscuro"/"claro") — cualquier valor desconocido o
    ausente cae al oscuro, nunca a una pantalla sin estilo."""
    return QSS_APLICACION_CLARO if tema == "claro" else QSS_APLICACION

# Nombres de "roles" usados en TreeWidget para pintar filas mediante
# datos de usuario en lugar de índices mágicos. Evita errores al
# reordenar columnas en el futuro.
ROL_ESTADO_ITEM = 1000  # Qt.UserRole + N

ESTADO_NORMAL = 0
ESTADO_REPRODUCIENDO = 1
ESTADO_SIGUIENTE = 2

# Bug real corregido: al arrastrar un tema desde el Explorador a
# Ventana 1/2/Auxiliar, antes solo viajaba la RUTA del archivo — el
# recorte de silencio y el nivelado de volumen ya calculados por
# core/analizador_audio.py se perdían (solo se aplicaban en el
# "Previo" de Ventana 3, nunca al aire). Este rol guarda ese análisis
# {"punto_inicio_ms", "punto_fin_ms", "ganancia_db"} junto al ítem,
# para que GestorPlaylist/GestorPublicidad lo pasen a
# MotorAudio.reproducir() igual que ya hacía GestorExplorador.
ROL_ANALISIS_AUDIO = 1002

# Marca "ya se reprodujo en esta sesión" (pedido explícito: un ícono a
# la izquierda, sin texto, para saber de un vistazo qué ítems ya
# sonaron) — se pone al arrancar a sonar (ESTADO_REPRODUCIENDO) y ya
# NUNCA se saca, ni cuando el ítem deja de estar en rojo/verde.
ROL_YA_REPRODUCIDO = 1003

# Vigencia de fecha (pedido explícito, inspirado en Dinesat): un ítem
# de Publicidad puede tener {"fecha_inicio": "YYYY-MM-DD"|None,
# "fecha_fin": "YYYY-MM-DD"|None} — fuera de ese rango se saltea en la
# reproducción sin cortar el aire (ver config.settings.vigencia_activa).
ROL_VIGENCIA = 1004

# Posición del Pisador anidado (pedido explícito, paridad con
# Dinesat): "inicio" (default, comportamiento de siempre — se dispara
# al arrancar el tema) o "final" (se dispara cerca del final, sobre el
# outro). Guardado en el ítem HIJO del Pisador (gui/panel_reproductor.
# py:agregar_pisador), no en el tema principal.
ROL_POSICION_PISADOR = 1005

# Comando FMT (pedido explícito, "encadenado con Musicalizador
# Avanzado" — inspirado en Dinesat): un ítem de Ventana 1 puede ser un
# COMANDO en vez de audio real — no tiene ruta, no "suena", al
# llegarle el turno ejecuta una acción (hoy solo "FMT", dispara la
# generación continua de música en Ventana 2) y la reproducción sigue
# directo al próximo ítem real, sin ocupar tiempo de aire.
ROL_ES_COMANDO = 1006
ROL_TIPO_COMANDO = 1007       # ej. "FMT"
ROL_PARAMETRO_COMANDO = 1008  # ej. nombre del formato del Musicalizador
COLOR_COMANDO = "#2980b9"     # azul, distinto del rojo/verde de estado y del violeta del Pisador

# Ítem ALEATORIO (pedido explícito, Programador de Ventana 1: "agregar
# un ítem aleatorio de alguna categoría o sub-categoría, para darle
# dinamismo... que sea buen aleatorio y variado"): igual que un
# Comando, no tiene una ruta FIJA — a diferencia de arrastrar un
# archivo puntual, este ítem guarda el CAMINO de una categoría y
# recién resuelve un archivo al azar de ahí CADA VEZ que le toca sonar
# (no una sola vez al agregarlo) — mismo mecanismo de no-repetir vía
# historial ya usado por el Musicalizador Avanzado
# (config.settings.rutas_recientes_en_historial), así nunca repite un
# archivo hasta agotar los demás de esa categoría.
ROL_ES_ALEATORIO = 1009
ROL_CATEGORIA_ALEATORIO = 1010    # list[str]: camino de nombres (ver VentanaExplorador.ruta_de_categoria)
ROL_RECURSIVO_ALEATORIO = 1011    # bool: suma también las subcategorías
COLOR_ALEATORIO = "#16a085"       # verde azulado, distinto de COLOR_COMANDO y del rojo/verde de estado

# Marca "archivo no encontrado" (pedido explícito, Ventana 1: "que no
# se detenga, sino que avance al item siguiente, marque con una X roja
# como error... no elimine el item de la biblioteca"). Se recalcula en
# vivo cada vez que GestorPublicidad._item_valido() evalúa el ítem — no
# se persiste a disco a propósito, es un reflejo del estado REAL del
# archivo en disco en este instante, se saca solo si el archivo
# reaparece (ej. el operador reconecta la unidad/corrige la ruta).
ROL_ITEM_CON_ERROR = 1012

# Colores por género, usados en la Ventana 3 (Explorador) para pintar
# el fondo de cada fila según el tipo de material (pedido explícito).
GENERO_COLORES = {
    "Musica": "#2e7d32",       # verde
    "Publicidad": "#f9a825",   # amarillo
    "Separador": "#e65100",    # naranja
    "Pisador": "#6a1b9a",      # violeta
    "Artistica": "#1565c0",    # azul
    "HTH": "#00838f",          # cian oscuro — clips de voz de Hora/Clima
}

# Con fondo amarillo el texto blanco no contrasta: estos géneros
# usan texto oscuro en vez de blanco sobre su color de fondo.
GENEROS_CON_TEXTO_OSCURO = {"Publicidad"}

GENERO_PREFIJOS_CODIGO = {
    "Musica": "MUS",
    "Publicidad": "PUB",
    "Separador": "SEP",
    "Pisador": "PIS",
    "Artistica": "ART",
    "HTH": "HTH",
}

# Pedido explícito ("Comando HTH", ver docs/manual_dinesat_visual.md
# 5.3.5.1): un género MÁS, no una categoría — así los clips de voz
# (HORA 00, MINUTOS 00, TEMPERATURA GRADOS 20, HUMEDAD 045, etc.) se
# importan con el mismo flujo de siempre ("＋ Agregar" del Explorador,
# eligiendo género HTH y escribiendo la nomenclatura exacta como
# título) y quedan buscables globalmente con
# VentanaExplorador.listar_registros_por_genero("HTH") — mismo patrón
# ya usado por "Pisador", sin inventar un tipo de categoría nuevo.
LISTA_GENEROS = ["Musica", "Publicidad", "Separador", "Pisador", "Artistica", "HTH"]


def color_texto_legible(color_hex: str) -> str:
    """Negro o blanco según la luminancia del color de fondo. Antes
    GENEROS_CON_TEXTO_OSCURO era una lista fija (solo Publicidad); con
    los colores por género ahora editables desde Configuración, el
    usuario puede asignarle amarillo a cualquier género, así que el
    contraste se calcula en vez de asumirlo."""
    color_hex = (color_hex or "").lstrip("#")
    if len(color_hex) != 6:
        return "white"
    try:
        r, g, b = (int(color_hex[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "white"
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    return "black" if luminancia > 150 else "white"


_ICONO_YA_REPRODUCIDO = None


def icono_reproducido():
    """Tilde verde "ya reproducido" (pedido explícito: "una marca a la
    izquierda, con algún ícono de OK... no escrito, solo ícono"). Se
    arma a mano con QPainter (no hay assets reales de Dinesat) y se
    cachea en un módulo-global — un QPixmap no se puede construir
    antes de que exista QApplication, así que la primera llamada real
    ocurre en tiempo de ejecución, nunca al importar este módulo."""
    global _ICONO_YA_REPRODUCIDO
    if _ICONO_YA_REPRODUCIDO is None:
        from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QPolygon, QColor as _QColor
        from PySide6.QtCore import Qt as _Qt, QPoint

        pixmap = QPixmap(14, 14)
        pixmap.fill(_Qt.GlobalColor.transparent)
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        lapiz = QPen(_QColor("#2ecc71"))
        lapiz.setWidth(2)
        lapiz.setCapStyle(_Qt.PenCapStyle.RoundCap)
        lapiz.setJoinStyle(_Qt.PenJoinStyle.RoundJoin)
        pintor.setPen(lapiz)
        pintor.drawPolyline(QPolygon([QPoint(2, 7), QPoint(6, 11), QPoint(12, 3)]))
        pintor.end()
        _ICONO_YA_REPRODUCIDO = QIcon(pixmap)
    return _ICONO_YA_REPRODUCIDO


_ICONO_ITEM_CON_ERROR = None


def icono_error():
    """X roja "archivo no encontrado" (pedido explícito, Ventana 1) —
    mismo patrón de icono armado a mano con QPainter que
    icono_reproducido(), cacheado en un módulo-global por la misma
    razón (un QPixmap no se puede construir antes de que exista
    QApplication)."""
    global _ICONO_ITEM_CON_ERROR
    if _ICONO_ITEM_CON_ERROR is None:
        from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor as _QColor
        from PySide6.QtCore import Qt as _Qt

        pixmap = QPixmap(14, 14)
        pixmap.fill(_Qt.GlobalColor.transparent)
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        lapiz = QPen(_QColor("#e74c3c"))
        lapiz.setWidth(2)
        lapiz.setCapStyle(_Qt.PenCapStyle.RoundCap)
        pintor.setPen(lapiz)
        pintor.drawLine(2, 2, 12, 12)
        pintor.drawLine(12, 2, 2, 12)
        pintor.end()
        _ICONO_ITEM_CON_ERROR = QIcon(pixmap)
    return _ICONO_ITEM_CON_ERROR


_ICONO_SIN_MARCAS_IN_OUT = None


def icono_sin_marcas_in_out():
    """Triángulo de aviso ámbar "sin marcas IN/OUT" (pedido explícito,
    "veo que nunca funciona el recorte de silencio" -- Ventana 3
    ahora marca a simple vista qué archivos de MÚSICA se importaron
    SIN que el análisis de silencio/nivelado pudiera calcular sus
    marcas, en vez de descubrirlo recién al aire). Mismo patrón de
    QPainter cacheado que icono_reproducido()/icono_error() -- color
    ámbar (`#f39c12`) para no confundirlo con la X roja de "archivo no
    encontrado" (icono_error) ni con el tilde verde de "ya
    reproducido"."""
    global _ICONO_SIN_MARCAS_IN_OUT
    if _ICONO_SIN_MARCAS_IN_OUT is None:
        from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QPolygon, QColor as _QColor
        from PySide6.QtCore import Qt as _Qt, QPoint

        pixmap = QPixmap(14, 14)
        pixmap.fill(_Qt.GlobalColor.transparent)
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = _QColor("#f39c12")
        pintor.setPen(QPen(color, 1))
        pintor.setBrush(QBrush(color))
        pintor.drawPolygon(QPolygon([QPoint(7, 1), QPoint(13, 12), QPoint(1, 12)]))
        pintor.setPen(QPen(_QColor("#2c2c2c"), 2))
        pintor.drawLine(7, 5, 7, 9)
        pintor.drawPoint(7, 11)
        pintor.end()
        _ICONO_SIN_MARCAS_IN_OUT = QIcon(pixmap)
    return _ICONO_SIN_MARCAS_IN_OUT
