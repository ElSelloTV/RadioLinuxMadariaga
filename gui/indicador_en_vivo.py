"""
gui/indicador_en_vivo.py
--------------------------------------------------------
Luz indicadora de "está sonando": un círculo que titila en rojo
mientras esa ventana tiene audio reproduciéndose de verdad, y queda
apagado (gris) el resto del tiempo. Pedido explícito: saber a simple
vista qué ventana está al aire y que realmente está sonando música
(no solo que hay un ítem marcado en rojo, que puede estar pausado).
--------------------------------------------------------
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QPainter, QColor


class IndicadorEnVivo(QWidget):
    _INTERVALO_PARPADEO_MS = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._activo = False
        self._visible_parpadeo = True
        self.setFixedSize(14, 14)
        self.setToolTip("Sin reproducción")

        self._timer = QTimer(self)
        self._timer.setInterval(self._INTERVALO_PARPADEO_MS)
        self._timer.timeout.connect(self._parpadear)

    def set_activo(self, activo: bool):
        if activo == self._activo:
            return
        self._activo = activo
        self._visible_parpadeo = True
        if activo:
            self._timer.start()
            self.setToolTip("Reproduciendo")
        else:
            self._timer.stop()
            self.setToolTip("Sin reproducción")
        self.update()

    def _parpadear(self):
        self._visible_parpadeo = not self._visible_parpadeo
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(14, 14)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._activo and self._visible_parpadeo:
            color = QColor("#e74c3c")
        elif self._activo:
            color = QColor("#7a231b")
        else:
            color = QColor("#555555")

        pintor.setBrush(color)
        pintor.setPen(QColor("#222222"))
        pintor.drawEllipse(1, 1, 12, 12)
        pintor.end()
