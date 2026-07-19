"""
gui/medidor_nivel.py
--------------------------------------------------------
Medidor de nivel vertical DECORATIVO (pedido explícito, estilo
Dinesat): mismo lugar y aspecto que un VU-meter real, pero SIN medir
audio de verdad — python-vlc no expone el nivel de señal en vivo de
forma simple, y fabricar un número inventado sería peor que no tener
nada (el operador podría confiar en una lectura falsa). Se limita a
reflejar si HAY audio sonando o no: segmentos verde/amarillo/rojo
"encendidos" mientras suena, apagados en silencio.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor

# De abajo hacia arriba: verde, verde, amarillo, amarillo, rojo — como
# cualquier VU-meter de consola de radio.
COLORES_SEGMENTOS = ["#27ae60", "#2ecc71", "#f1c40f", "#f39c12", "#e74c3c"]


class MedidorNivelDecorativo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._activo = False
        # Pedido explícito ("rediseño compacto"): mínimo más bajo —
        # antes 40px de alto fijaba un piso más alto del necesario
        # para toda la fila de relojes/Ahora-Luego, aunque el resto
        # de esos widgets ya se hubiera achicado.
        self.setMinimumSize(8, 26)
        self.setMaximumWidth(14)
        self.setToolTip("Medidor de nivel (decorativo)")

    def sizeHint(self):
        return QSize(10, 30)

    def set_activo(self, activo: bool):
        if activo != self._activo:
            self._activo = activo
            self.update()

    def paintEvent(self, _evento):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        ancho = self.width()
        alto = self.height()
        cantidad = len(COLORES_SEGMENTOS)
        espacio = 2
        alto_segmento = max(2, (alto - espacio * (cantidad - 1)) // cantidad)

        # Con audio sonando, quedan "encendidos" la mayoría de los
        # segmentos (look de estación en vivo); en silencio, apagados
        # del todo — nunca pretende ser una medición real.
        encendidos = cantidad - 1 if self._activo else 0

        for i in range(cantidad):
            indice_desde_abajo = cantidad - 1 - i
            y = i * (alto_segmento + espacio)
            color = QColor(COLORES_SEGMENTOS[indice_desde_abajo])
            if indice_desde_abajo >= encendidos:
                color = color.darker(320)
            painter.fillRect(0, y, ancho, alto_segmento, color)

        painter.end()
