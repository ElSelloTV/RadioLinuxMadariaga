"""
gui/etiqueta_marquesina.py
--------------------------------------------------------
Etiqueta "sticker" de tamaño fijo para mostrar el título del tema
en reproducción (Ventana 2 / Auxiliar), estilo Winamp: el ancho del
widget NUNCA cambia con el largo del texto (así no empuja ni
redimensiona el panel ni la columna cada vez que cambia el tema), y
si el título no entra, se desplaza en marquesina en vez de
cortarse en silencio.
--------------------------------------------------------
"""

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QFontMetrics


class EtiquetaMarquesina(QWidget):
    _INTERVALO_MS = 40
    _PASO_PX = 2
    _SEPARACION_PX = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lblTituloSticker")
        self._texto = "Sin reproducción"
        self._offset = 0
        self._ancho_texto = 0
        self._necesita_scroll = False
        # Pedido explícito ("las ventanas de antes y luego deberían
        # ser mucho más angosta"): Preferred en vez de Expanding — el
        # frame que la contiene ahora se agrega con AlignLeft (ver
        # panel_reproductor.py / ventana_publicidad.py), así el
        # sticker ya no reclama todo el ancho disponible del panel.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        # Pedido explícito ("rediseño compacto"): 18px en vez de 22 —
        # el cartel "Ahora"/"Luego" (frameAhora/frameLuego) era
        # demasiado grande para pantallas chicas.
        self.setMinimumHeight(18)

        self._timer = QTimer(self)
        self._timer.setInterval(self._INTERVALO_MS)
        self._timer.timeout.connect(self._avanzar)

        self._recalcular_scroll()

    # ------------------------------------------------------------------
    def setText(self, texto: str):
        self._texto = texto or ""
        self._offset = 0
        self._recalcular_scroll()
        self.update()

    def text(self) -> str:
        return self._texto

    def sizeHint(self) -> QSize:
        # Antes 220px: pedido explícito de achicarlo bastante para que
        # el cartel "Ahora"/"Luego" no quede tan grande — con
        # marquesina, un título largo se sigue viendo completo
        # desplazándose, no hace falta ancho fijo grande. Alto bajado
        # de 22 a 18 en la ronda de rediseño compacto.
        return QSize(120, 18)

    def minimumSizeHint(self) -> QSize:
        return QSize(40, 18)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._recalcular_scroll()

    def _recalcular_scroll(self):
        metricas = QFontMetrics(self.font())
        self._ancho_texto = metricas.horizontalAdvance(self._texto)
        self._necesita_scroll = self._ancho_texto > (self.width() - 16)
        if self._necesita_scroll:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._offset = 0

    def _avanzar(self):
        self._offset += self._PASO_PX
        if self._offset >= self._ancho_texto + self._SEPARACION_PX:
            self._offset = 0
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        pintor.fillRect(rect, QColor("#101010"))
        pintor.setPen(QColor("#555555"))
        pintor.drawRect(rect.adjusted(0, 0, -1, -1))

        pintor.setClipRect(rect.adjusted(2, 2, -2, -2))
        pintor.setPen(QColor("#f5f5f5"))
        metricas = pintor.fontMetrics()
        y_texto = (rect.height() + metricas.ascent() - metricas.descent()) // 2

        if not self._necesita_scroll:
            x_texto = (rect.width() - self._ancho_texto) // 2
            pintor.drawText(max(4, x_texto), y_texto, self._texto)
        else:
            x = -self._offset
            while x < rect.width():
                pintor.drawText(x, y_texto, self._texto)
                x += self._ancho_texto + self._SEPARACION_PX

        pintor.end()
