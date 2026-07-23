"""
gui/medidor_nivel.py
--------------------------------------------------------
Medidor de nivel vertical DECORATIVO (pedido explícito, estilo
Dinesat): mismo lugar y aspecto que un VU-meter real, pero SIN medir
audio de verdad — python-vlc no expone el nivel de señal en vivo de
forma simple, y fabricar un número inventado sería peor que no tener
nada (el operador podría confiar en una lectura falsa).

Animación (pedido explícito, ronda posterior — "animá FICTICIAMENTE,
no real... que se mueva lo más real posible, mientras se reproduce"):
Santiago pidió explícitamente esto sabiendo que es ficticio, así que
no contradice la nota de arriba (el riesgo era una lectura que
APARENTE ser real sin decirlo — acá el propio pedido ya asume que no
lo es). Mientras `_activo`, un QTimer randomiza la cantidad de
segmentos encendidos cada pocos ms, simulando el rebote de una aguja
real; en silencio queda apagado del todo, nunca pretende medir nada.
--------------------------------------------------------
"""

import random

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPainter, QColor

# De abajo hacia arriba: verde, verde, amarillo, amarillo, rojo — como
# cualquier VU-meter de consola de radio.
COLORES_SEGMENTOS = ["#27ae60", "#2ecc71", "#f1c40f", "#f39c12", "#e74c3c"]

INTERVALO_ANIMACION_MS = 120


class MedidorNivelDecorativo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._activo = False
        self._encendidos = 0
        # Pedido explícito ("rediseño compacto"): mínimo más bajo —
        # antes 40px de alto fijaba un piso más alto del necesario
        # para toda la fila de relojes/Ahora-Luego, aunque el resto
        # de esos widgets ya se hubiera achicado.
        self.setMinimumSize(8, 26)
        self.setMaximumWidth(14)
        self.setToolTip("Medidor de nivel (decorativo)")

        self._timer_animacion = QTimer(self)
        self._timer_animacion.setInterval(INTERVALO_ANIMACION_MS)
        self._timer_animacion.timeout.connect(self._rebote_aleatorio)

    def sizeHint(self):
        return QSize(10, 30)

    def set_activo(self, activo: bool):
        if activo == self._activo:
            return
        self._activo = activo
        if activo:
            self._rebote_aleatorio()
            self._timer_animacion.start()
        else:
            self._timer_animacion.stop()
            self._encendidos = 0
            self.update()

    def _rebote_aleatorio(self):
        cantidad = len(COLORES_SEGMENTOS)
        # Rango amplio (como voz/música real: picos y valles), con
        # sesgo hacia "casi lleno" (más parecido a un tema ya
        # nivelado) — nunca 0 mientras suena, para que no parezca
        # apagado por error.
        self._encendidos = random.randint(max(1, cantidad - 3), cantidad)
        self.update()

    def paintEvent(self, _evento):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        ancho = self.width()
        alto = self.height()
        cantidad = len(COLORES_SEGMENTOS)
        espacio = 2
        alto_segmento = max(2, (alto - espacio * (cantidad - 1)) // cantidad)

        encendidos = self._encendidos if self._activo else 0

        for i in range(cantidad):
            indice_desde_abajo = cantidad - 1 - i
            y = i * (alto_segmento + espacio)
            color = QColor(COLORES_SEGMENTOS[indice_desde_abajo])
            if indice_desde_abajo >= encendidos:
                color = color.darker(320)
            painter.fillRect(0, y, ancho, alto_segmento, color)

        painter.end()
