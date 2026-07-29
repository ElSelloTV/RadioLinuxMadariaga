"""
gui/styles.py
--------------------------------------------------------
Hoja de estilos QSS centralizada para toda la aplicación.
Mantener el estilo aislado aquí permite cambiar el theme
completo sin tocar ni una línea de lógica ni de layout.
--------------------------------------------------------
"""

# Paleta base (referencia interna, no se usa directamente en QSS
# pero sirve para mantener consistencia si se generan widgets
# custom por código, ej. QPainter).
COLOR_FONDO_PRINCIPAL = "#2b2b2b"
COLOR_FONDO_PANEL = "#3a3a3a"
COLOR_FONDO_HEADER = "#1f1f1f"
COLOR_BORDE = "#555555"
COLOR_TEXTO = "#e0e0e0"
COLOR_TEXTO_SECUNDARIO = "#9a9a9a"

COLOR_REPRODUCIENDO = "#c0392b"   # Rojo: evento en emisión
COLOR_SIGUIENTE = "#27ae60"       # Verde: próximo evento
COLOR_AUTOMATICO_ON = "#e74c3c"
COLOR_AUTOMATICO_OFF = "#555555"
COLOR_SELECCION = "#5dade2"       # Celeste: cursor de selección (Dinesat), nunca reemplaza rojo/verde
COLOR_ARMADO = "#e67e22"          # Naranja: acción diferida armada (Stop diferido)

QSS_APLICACION = f"""
QMainWindow {{
    background-color: {COLOR_FONDO_PRINCIPAL};
}}

QWidget {{
    background-color: {COLOR_FONDO_PRINCIPAL};
    color: {COLOR_TEXTO};
    font-family: "DejaVu Sans", "Noto Sans", sans-serif;
    font-size: 10pt;
}}

/* ---------- Menú superior ---------- */
QMenuBar {{
    background-color: {COLOR_FONDO_HEADER};
    color: {COLOR_TEXTO};
    border-bottom: 1px solid {COLOR_BORDE};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
}}
QMenuBar::item:selected {{
    background-color: #444444;
    border-radius: 3px;
}}
QMenu {{
    background-color: {COLOR_FONDO_PANEL};
    border: 1px solid {COLOR_BORDE};
}}
QMenu::item:selected {{
    background-color: #505050;
}}

/* ---------- Toolbar superior ---------- */
QToolBar {{
    background-color: {COLOR_FONDO_HEADER};
    border-bottom: 1px solid {COLOR_BORDE};
    spacing: 4px;
    padding: 3px;
}}
QToolButton {{
    background-color: #333333;
    border: 1px solid {COLOR_BORDE};
    border-radius: 4px;
    padding: 4px;
}}
QToolButton:hover {{
    background-color: #444444;
}}
QToolButton:pressed {{
    background-color: #222222;
}}

/* ---------- Paneles / GroupBox de cada ventana ---------- */
QGroupBox {{
    background-color: {COLOR_FONDO_PANEL};
    border: 1px solid {COLOR_BORDE};
    border-radius: 4px;
    margin-top: 16px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 1px 5px;
    background-color: {COLOR_FONDO_HEADER};
    border: 1px solid {COLOR_BORDE};
    border-radius: 3px;
    color: {COLOR_TEXTO};
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
    background-color: #262626;
    alternate-background-color: #2d2d2d;
    border: 1px solid {COLOR_BORDE};
    show-decoration-selected: 1;
}}
QTreeWidget::item {{
    padding: 3px;
}}
QTreeWidget::item:selected {{
    background-color: #45688e;
    color: white;
}}
QHeaderView::section {{
    background-color: {COLOR_FONDO_HEADER};
    color: {COLOR_TEXTO};
    padding: 2px;
    border: 1px solid {COLOR_BORDE};
}}

/* ---------- Ventana 3 (Explorador): tipografía más chica en los
   ítems (pedido explícito) para tener más visibilidad de los datos
   sin agrandar la ventana. ---------- */
QTreeWidget#tree_archivos, QTreeWidget#tree_categorias {{
    font-size: 8pt;
}}
QTreeWidget#tree_archivos::item, QTreeWidget#tree_categorias::item {{
    padding: 1px;
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
QTreeWidget#tree_publicidad, QTreeWidget#tree_reproductor {{
    font-size: 8pt;
}}
QTreeWidget#tree_publicidad::item, QTreeWidget#tree_reproductor::item {{
    padding: 1px;
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
    background-color: #3d3d3d;
    border: 1px solid {COLOR_BORDE};
    border-radius: 4px;
    padding: 6px 10px;
}}
QPushButton:hover {{
    background-color: #4a4a4a;
}}
QPushButton:pressed {{
    background-color: #2a2a2a;
}}

QPushButton#btnPlay {{
    background-color: #1e8449;
    font-weight: bold;
}}
QPushButton#btnPlay:hover {{ background-color: #229954; }}

QPushButton#btnStop {{
    background-color: #922b21;
    font-weight: bold;
}}
QPushButton#btnStop:hover {{ background-color: #c0392b; }}

/* Play/Pausa/Stop/Siguiente en 1 SOLA fila (Ventana 1 y 2/Auxiliar,
   antes en grilla de 2 filas) — pedido explícito, para ahorrar
   visibilidad de la lista. Padding/fuente más chicos para que las
   4-5 entren cómodas en una línea sin volver a fijar un ancho
   mínimo grande (el motivo por el que antes se habían puesto en
   grilla de 2x2). */
QPushButton[class="btnTransporte"] {{
    padding: 4px 6px;
    font-size: 8pt;
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
   "igualá lo más que pueda... la distribución de las ventanas 1 y 2")
   ----------
   Botón grande verde: Play SI está en silencio, "Siguiente con
   fundido" si ya hay algo sonando — las dos funciones en un botón. */
QPushButton#btnPlayPrincipal {{
    background-color: #1e8449;
    border: 2px solid #2ecc71;
    font-weight: bold;
    font-size: 9pt;
}}
QPushButton#btnPlayPrincipal:hover {{ background-color: #229954; }}
QPushButton#btnPlayPrincipal:pressed {{ background-color: #145a32; }}

/* Fade-Stop: fundido hasta apagar — distinto color de Stop (corte
   seco) para no confundirlos de un vistazo. */
QPushButton#btnFadeStop {{
    background-color: #6c3483;
    font-weight: bold;
}}
QPushButton#btnFadeStop:hover {{ background-color: #8e44ad; }}

/* Cut (antes "Siguiente"): corte seco e inmediato al ítem en cola. */
QPushButton#btnCut {{
    background-color: #34495e;
    font-weight: bold;
}}
QPushButton#btnCut:hover {{ background-color: #46617a; }}

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
    background-color: #3d3d3d;
}}

/* Nombre de la estación (pedido explícito, imitando el nameplate de
   Dinesat) — puramente decorativo, texto fijo. */
QLabel#lblNombreEstacion {{
    color: #e67e22;
    font-weight: bold;
    font-size: 8pt;
    letter-spacing: 1px;
}}

/* Contorno rojo PERMANENTE (esté ON u OFF) para ubicarlo mejor de un
   vistazo — pedido explícito. El relleno rojo + cambio de texto al
   activarlo NO cambia, sigue siendo la única señal de estado real. */
QPushButton#btnAutomatico[activo="true"] {{
    background-color: {COLOR_AUTOMATICO_ON};
    border: 2px solid #ff6b5b;
    font-weight: bold;
    color: white;
}}
QPushButton#btnAutomatico[activo="false"] {{
    background-color: {COLOR_AUTOMATICO_OFF};
    border: 2px solid {COLOR_REPRODUCIENDO};
    font-weight: bold;
    color: #cccccc;
}}

/* ---------- Contadores de tiempo (estilo display) ----------
   Antes 26pt (impedía achicar columnas), después 14pt lado a lado.
   Pedido explícito de esta ronda: los relojes pasan a apilarse a la
   IZQUIERDA (uno arriba, otro abajo) en vez de ir lado a lado —
   bajado a 11pt + ancho máximo fijo para que la columna quede
   angosta de verdad y sobre espacio para "Ahora"/"Luego" a la
   derecha en la misma fila. */
QLabel#lblTiempoTranscurrido, QLabel#lblTiempoRestante {{
    background-color: #101010;
    color: #f5f5f5;
    border: 1px solid {COLOR_BORDE};
    border-radius: 4px;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 9pt;
    font-weight: bold;
    padding: 0px 3px;
}}
QLabel#lblTituloBloqueActivo {{
    color: {COLOR_TEXTO_SECUNDARIO};
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
    color: {COLOR_TEXTO_SECUNDARIO};
}}
/* "Ahora:"/"Luego:" junto al título en Ventana 1/2/Auxiliar — pedido
   explícito, más robusto que depender solo del color de fila. */
QLabel#lblEtiquetaAhoraLuego {{
    color: {COLOR_TEXTO_SECUNDARIO};
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
    background-color: {COLOR_FONDO_HEADER};
    border-top: 1px solid {COLOR_BORDE};
    color: {COLOR_TEXTO_SECUNDARIO};
}}

/* ---------- Splitter entre las 3 ventanas ---------- */
QSplitter::handle {{
    background-color: {COLOR_BORDE};
    width: 3px;
}}

/* ---------- ScrollBars discretas ---------- */
QScrollBar:vertical {{
    background: {COLOR_FONDO_PANEL};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: #5a5a5a;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

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
