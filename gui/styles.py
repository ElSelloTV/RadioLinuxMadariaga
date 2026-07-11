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

QPushButton#btnAutomatico[activo="true"] {{
    background-color: {COLOR_AUTOMATICO_ON};
    border: 1px solid #ff6b5b;
    font-weight: bold;
    color: white;
}}
QPushButton#btnAutomatico[activo="false"] {{
    background-color: {COLOR_AUTOMATICO_OFF};
    font-weight: bold;
    color: #cccccc;
}}

/* ---------- Contadores de tiempo (estilo display grande) ---------- */
QLabel#lblTiempoTranscurrido, QLabel#lblTiempoRestante {{
    background-color: #101010;
    color: #f5f5f5;
    border: 1px solid {COLOR_BORDE};
    border-radius: 4px;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 26pt;
    font-weight: bold;
    padding: 2px 8px;
}}
QLabel#lblTituloBloqueActivo {{
    color: {COLOR_TEXTO_SECUNDARIO};
    font-style: italic;
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
