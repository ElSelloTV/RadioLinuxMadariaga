"""
gui/ventana_emision.py
--------------------------------------------------------
Ventana 2 (Centro): Emisión Musical Actual.
Envoltorio delgado sobre PanelReproductor (gui/panel_reproductor.py):
ahí vive toda la lógica de contadores/controles/lista. Acá solo
se agregan los datos de demostración y se reexportan las señales
para que main_window/core no necesiten saber que hay una
composición interna.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from gui.panel_reproductor import PanelReproductor


class VentanaEmision(QWidget):
    solicitud_play = Signal()
    solicitud_pausa = Signal()
    solicitud_stop = Signal()
    solicitud_siguiente = Signal()
    item_marcado_como_siguiente = Signal(int)
    archivo_soltado = Signal(str, object)
    solicitud_abrir_auxiliar = Signal()
    item_doble_click = Signal(int)
    solicitud_agregar_pisador = Signal(int)
    solicitud_eliminar_definitivo = Signal(str)
    solicitud_buscar_posicion = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.panel = PanelReproductor(
            "EMISIÓN MUSICAL ACTUAL", mostrar_boton_auxiliar=True, mostrar_barra_progreso=True
        )
        layout.addWidget(self.panel)

        self.panel.solicitud_play.connect(self.solicitud_play.emit)
        self.panel.solicitud_pausa.connect(self.solicitud_pausa.emit)
        self.panel.solicitud_stop.connect(self.solicitud_stop.emit)
        self.panel.solicitud_siguiente.connect(self.solicitud_siguiente.emit)
        self.panel.item_marcado_como_siguiente.connect(self.item_marcado_como_siguiente.emit)
        self.panel.archivo_soltado.connect(self.archivo_soltado.emit)
        self.panel.solicitud_abrir_auxiliar.connect(self.solicitud_abrir_auxiliar.emit)
        self.panel.item_doble_click.connect(self.item_doble_click.emit)
        self.panel.solicitud_agregar_pisador.connect(self.solicitud_agregar_pisador.emit)
        self.panel.solicitud_eliminar_definitivo.connect(self.solicitud_eliminar_definitivo.emit)
        self.panel.solicitud_buscar_posicion.connect(self.solicitud_buscar_posicion.emit)

        self._cargar_datos_demo()

    def _cargar_datos_demo(self):
        items_demo = [
            ("Soy aquel", "00:04:04", "VIE0109"),
            ("VUELA", "00:00:00", "—"),
            ("Amarte (Feat Bethliza...)", "00:04:09", "VIE0282"),
            ("RADIO CONTACTO F...", "00:00:11", "JIN0033"),
            ("Perdóname", "00:04:11", "VIE0166"),
        ]
        for titulo, duracion, codigo in items_demo:
            self.panel.agregar_item(titulo, duracion, codigo)

        if self.panel.cantidad_items() > 0:
            self.panel.marcar_reproduciendo(0)
        if self.panel.cantidad_items() > 1:
            self.panel.marcar_siguiente(1)

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

    def actualizar_progreso(self, permille: int):
        self.panel.actualizar_progreso(permille)
