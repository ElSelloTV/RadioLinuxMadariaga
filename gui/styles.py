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
    margin-top: 18px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 2px 6px;
    background-color: {COLOR_FONDO_HEADER};
    border: 1px solid {COLOR_BORDE};
    border-radius: 3px;
    color: {COLOR_TEXTO};
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
    padding: 4px;
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

/* Ventana 1 (Publicidad) y Ventana 2 (Emisión): el resaltado de
   selección de Qt (azul sólido, regla ::item:selected de más arriba)
   tapaba el rojo/verde de "en punta"/"en cola" — pedido explícito,
   tiene que quedar siempre a la vista. Acá la selección deja de
   pintar un relleno propio (queda transparente) y se marca solo con
   un borde, así el fondo rojo/verde del ítem nunca se cubre, esté
   seleccionado o no. Color CELESTE (pedido explícito, igualando
   Dinesat: "el celeste es solo para una selección... cuando se hace
   clic en un verde o rojo, nunca pierde ese color") — antes era
   amarillo; el celeste es la señal de "acá está el cursor de
   selección", nunca reemplaza al rojo/verde de estado. */
QTreeWidget#tree_reproductor::item:selected, QTreeWidget#tree_publicidad::item:selected {{
    background-color: transparent;
    border: 2px solid {COLOR_SELECCION};
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
    font-size: 11pt;
    font-weight: bold;
    padding: 1px 4px;
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
    font-size: 8pt;
    font-weight: bold;
}}
/* Contorno rojo/verde alrededor de cada fila "Ahora"/"Luego" — mismo
   concepto de color que la fila de la lista, pedido explícito. */
QFrame#frameAhora {{
    border: 2px solid {COLOR_REPRODUCIENDO};
    border-radius: 3px;
    padding: 1px 3px;
}}
QFrame#frameLuego {{
    border: 2px solid {COLOR_SIGUIENTE};
    border-radius: 3px;
    padding: 1px 3px;
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

# Colores por género, usados en la Ventana 3 (Explorador) para pintar
# el fondo de cada fila según el tipo de material (pedido explícito).
GENERO_COLORES = {
    "Musica": "#2e7d32",       # verde
    "Publicidad": "#f9a825",   # amarillo
    "Separador": "#e65100",    # naranja
    "Pisador": "#6a1b9a",      # violeta
    "Artistica": "#1565c0",    # azul
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
}

LISTA_GENEROS = ["Musica", "Publicidad", "Separador", "Pisador", "Artistica"]


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
