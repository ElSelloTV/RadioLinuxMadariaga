"""
gui/ventana_auxiliar.py
--------------------------------------------------------
Ventana flotante de reproducción secundaria.
Se abre con el botón "🎧 Auxiliar" de la Ventana 2. Por pedido
del usuario, esta ventana comparte la MISMA salida de audio
principal (no es una salida física separada): es simplemente un
segundo reproductor independiente, con idéntica estructura que
la Ventana 2 (contadores, controles, lista, barra de progreso)
reutilizando PanelReproductor.

Pedido explícito (ronda posterior): la gráfica y el funcionamiento
deben ser IGUAL a Ventana 2 — de ahí la barra de progreso, que antes
faltaba acá. Sin la lógica del Musicalizador/Comando FMT ni el pase
de Automático: ninguna de las dos cosas se agregó a propósito
(`GestorPlaylist` de esta ventana no recibe `ventana_explorador` ni
`persistir=True` en MainWindow.abrir_ventana_auxiliar, así que el
Musicalizador queda desactivado solo — ver core/gestor_emision.py —
y el ciclo Automático nunca tocó esta ventana). Auxiliar y Emisión NO
pueden sonar a la vez: al arrancar uno de los dos desde silencio, se
corta el otro con un fundido corto — ver
MainWindow._cortar_reproduccion_de().
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal

from gui.panel_reproductor import PanelReproductor


class VentanaAuxiliar(QDialog):
    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()   # "Cut" en la UI
    solicitud_fade_stop = Signal()
    solicitud_stop_diferido = Signal()
    solicitud_buscar_posicion = Signal(int)     # 0-1000 (por mil)
    archivo_soltado = Signal(str, object)
    item_doble_click = Signal(int)
    solicitud_agregar_pisador = Signal(int)
    solicitud_guardar_lista = Signal()
    solicitud_cargar_lista = Signal()
    solicitud_agregar_item_especifico = Signal()
    solicitud_agregar_item_aleatorio = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reproductor Auxiliar")
        self.setMinimumSize(460, 420)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.panel = PanelReproductor(
            "REPRODUCTOR AUXILIAR", mostrar_barra_progreso=True,
            # Pedido explícito: arrastrar y soltar de Ventana 1 a la
            # Auxiliar (nunca a Ventana 2 — ver
            # ArbolReproductorConDrop.acepta_desde_publicidad).
            acepta_desde_publicidad=True,
            # Pedido explícito ("agregá el menú contextual para agregar
            # ítem, lo mismo que Musicalizador"): solo el Auxiliar lo
            # pide, Ventana 1 (Emisión) se llena sola.
            permitir_agregar_item=True,
        )
        layout.addWidget(self.panel)

        # Pedido explícito: guardar/cargar la lista actual del
        # Auxiliar bajo un nombre — exclusivo de esta ventana, por eso
        # los botones viven acá y no en PanelReproductor (compartido
        # con Ventana 2, que no tiene esta función).
        fila_listas = QHBoxLayout()
        self.btn_guardar_lista = QPushButton("💾 Guardar lista...")
        self.btn_guardar_lista.setToolTip("Guardar el contenido actual del Auxiliar bajo un nombre")
        self.btn_guardar_lista.clicked.connect(self.solicitud_guardar_lista.emit)
        self.btn_cargar_lista = QPushButton("📂 Cargar lista...")
        self.btn_cargar_lista.setToolTip("Cargar una lista guardada (reemplaza lo que esté cargado)")
        self.btn_cargar_lista.clicked.connect(self.solicitud_cargar_lista.emit)
        fila_listas.addWidget(self.btn_guardar_lista)
        fila_listas.addWidget(self.btn_cargar_lista)
        layout.addLayout(fila_listas)

        self.panel.solicitud_play.connect(self.solicitud_play.emit)
        self.panel.solicitud_pausa.connect(self.solicitud_pausa.emit)
        self.panel.solicitud_stop.connect(self.solicitud_stop.emit)
        self.panel.solicitud_siguiente.connect(self.solicitud_siguiente.emit)
        self.panel.solicitud_fade_stop.connect(self.solicitud_fade_stop.emit)
        self.panel.solicitud_stop_diferido.connect(self.solicitud_stop_diferido.emit)
        self.panel.solicitud_buscar_posicion.connect(self.solicitud_buscar_posicion.emit)
        self.panel.archivo_soltado.connect(self.archivo_soltado.emit)
        self.panel.item_doble_click.connect(self.item_doble_click.emit)
        self.panel.solicitud_agregar_pisador.connect(self.solicitud_agregar_pisador.emit)
        self.panel.solicitud_agregar_item_especifico.connect(self.solicitud_agregar_item_especifico.emit)
        self.panel.solicitud_agregar_item_aleatorio.connect(self.solicitud_agregar_item_aleatorio.emit)

    # ------------------------------------------------------------------
    # Delegación: API pública usada por core/playlist_manager.py
    # ------------------------------------------------------------------
    def marcar_reproduciendo(self, fila):
        self.panel.marcar_reproduciendo(fila)

    def marcar_realmente_reproducido(self, fila):
        self.panel.marcar_realmente_reproducido(fila)

    def marcar_siguiente(self, fila):
        self.panel.marcar_siguiente(fila)

    def marcar_item_con_error_en_fila(self, fila, con_error):
        self.panel.marcar_item_con_error_en_fila(fila, con_error)

    def actualizar_contadores(self, transcurrido, restante):
        self.panel.actualizar_contadores(transcurrido, restante)

    def resetear_reproduccion(self):
        self.panel.resetear_reproduccion()

    def actualizar_progreso(self, permille: int):
        self.panel.actualizar_progreso(permille)

    def agregar_item(self, titulo, duracion, codigo, ruta="",
                      punto_inicio_ms=0, punto_fin_ms=None, ganancia_db=0.0):
        return self.panel.agregar_item(titulo, duracion, codigo, ruta,
                                        punto_inicio_ms, punto_fin_ms, ganancia_db)

    def agregar_pisador(self, fila_padre, titulo, duracion, codigo, ruta, posicion="inicio"):
        return self.panel.agregar_pisador(fila_padre, titulo, duracion, codigo, ruta, posicion)

    def ruta_pisador_en_fila(self, fila):
        return self.panel.ruta_pisador_en_fila(fila)

    def posicion_pisador_en_fila(self, fila):
        return self.panel.posicion_pisador_en_fila(fila)

    def cantidad_items(self):
        return self.panel.cantidad_items()

    def limpiar_items(self):
        self.panel.limpiar_items()

    def ruta_en_fila(self, fila):
        return self.panel.ruta_en_fila(fila)

    def analisis_en_fila(self, fila):
        return self.panel.analisis_en_fila(fila)

    def fila_reproduciendo(self):
        return self.panel.fila_reproduciendo()

    def fila_siguiente(self):
        return self.panel.fila_siguiente()

    def set_indicador_en_vivo(self, activo: bool):
        self.panel.set_indicador_en_vivo(activo)

    def set_stop_diferido_armado(self, armado: bool):
        self.panel.set_stop_diferido_armado(armado)

    @property
    def tree(self):
        # Delegación completa por consistencia con VentanaEmision,
        # aunque la Auxiliar no persiste su lista (persistir=False) —
        # ver core/gestor_emision.py.
        return self.panel.tree
