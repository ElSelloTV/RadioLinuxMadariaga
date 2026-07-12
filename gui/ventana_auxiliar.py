"""
gui/ventana_auxiliar.py
--------------------------------------------------------
Ventana flotante de reproducción secundaria.
Se abre con el botón "🎧 Auxiliar" de la Ventana 2. Por pedido
del usuario, esta ventana comparte la MISMA salida de audio
principal (no es una salida física separada): es simplemente un
segundo reproductor independiente, con idéntica estructura que
la Ventana 2 (contadores, controles, lista) reutilizando
PanelReproductor.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from gui.panel_reproductor import PanelReproductor


class VentanaAuxiliar(QDialog):
    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    archivo_soltado = Signal(str, object)
    item_doble_click = Signal(int)
    solicitud_agregar_pisador = Signal(int)
    solicitud_eliminar_definitivo = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reproductor Auxiliar")
        self.setMinimumSize(460, 420)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.panel = PanelReproductor("REPRODUCTOR AUXILIAR", mostrar_boton_auxiliar=False)
        layout.addWidget(self.panel)

        self.panel.solicitud_play.connect(self.solicitud_play.emit)
        self.panel.solicitud_pausa.connect(self.solicitud_pausa.emit)
        self.panel.solicitud_stop.connect(self.solicitud_stop.emit)
        self.panel.solicitud_siguiente.connect(self.solicitud_siguiente.emit)
        self.panel.archivo_soltado.connect(self.archivo_soltado.emit)
        self.panel.item_doble_click.connect(self.item_doble_click.emit)
        self.panel.solicitud_agregar_pisador.connect(self.solicitud_agregar_pisador.emit)
        self.panel.solicitud_eliminar_definitivo.connect(self.solicitud_eliminar_definitivo.emit)

    # ------------------------------------------------------------------
    # Delegación: API pública usada por core/playlist_manager.py
    # ------------------------------------------------------------------
    def marcar_reproduciendo(self, fila):
        self.panel.marcar_reproduciendo(fila)

    def marcar_siguiente(self, fila):
        self.panel.marcar_siguiente(fila)

    def actualizar_contadores(self, transcurrido, restante):
        self.panel.actualizar_contadores(transcurrido, restante)

    def agregar_item(self, titulo, duracion, codigo, ruta=""):
        return self.panel.agregar_item(titulo, duracion, codigo, ruta)

    def agregar_pisador(self, fila_padre, titulo, duracion, codigo, ruta):
        return self.panel.agregar_pisador(fila_padre, titulo, duracion, codigo, ruta)

    def ruta_pisador_en_fila(self, fila):
        return self.panel.ruta_pisador_en_fila(fila)

    def cantidad_items(self):
        return self.panel.cantidad_items()

    def ruta_en_fila(self, fila):
        return self.panel.ruta_en_fila(fila)

    def fila_reproduciendo(self):
        return self.panel.fila_reproduciendo()

    def fila_siguiente(self):
        return self.panel.fila_siguiente()

    def set_indicador_en_vivo(self, activo: bool):
        self.panel.set_indicador_en_vivo(activo)

    @property
    def tree(self):
        # Delegación completa por consistencia con VentanaEmision,
        # aunque la Auxiliar no persiste su lista (persistir=False) —
        # ver core/gestor_emision.py.
        return self.panel.tree
