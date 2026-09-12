"""
satelite/dialogo_ver_log.py
--------------------------------------------------------
Ver el log de la RADIO (config/data/log_aplicacion.txt) desde la app
satélite -- pedido explícito: "agregá la posibilidad de acceder al
archivo de log desde el satélite para poder también corregir futuros
errores". Solo lectura, nunca escribe nada del lado de la radio.

Muestra las últimas N líneas (ver `ClienteControlRemoto.
obtener_log_aplicacion()`), nunca el archivo entero -- el log real
puede crecer hasta TAMAÑO_MAXIMO_LOG_BYTES (config/settings.py), y un
tail acotado ya alcanza para diagnosticar sin inflar el mensaje del
socket.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor

from satelite.cliente_control_remoto import ErrorControlRemoto

MAXIMO_LINEAS_A_PEDIR = 500


class DialogoVerLog(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self._cliente = cliente
        self.setWindowTitle("Log de la radio")
        self.resize(720, 480)

        layout = QVBoxLayout(self)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setWordWrap(True)
        layout.addWidget(self.lbl_estado)

        self.texto = QPlainTextEdit()
        self.texto.setReadOnly(True)
        self.texto.setFont(QFont("monospace"))
        self.texto.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.texto)

        barra_botones = QHBoxLayout()
        self.btn_refrescar = QPushButton("🔄 Refrescar")
        self.btn_refrescar.clicked.connect(self._refrescar)
        barra_botones.addWidget(self.btn_refrescar)
        barra_botones.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        barra_botones.addWidget(btn_cerrar)
        layout.addLayout(barra_botones)

        self._refrescar()

    def _refrescar(self):
        self.btn_refrescar.setEnabled(False)
        self.lbl_estado.setText("Leyendo el log de la radio...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            datos = self._cliente.obtener_log_aplicacion(MAXIMO_LINEAS_A_PEDIR)
        except ErrorControlRemoto as error:
            self.lbl_estado.setText(f"⚠ {error}")
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_refrescar.setEnabled(True)

        self.texto.setPlainText(datos.get("contenido", ""))
        self.texto.moveCursor(QTextCursor.MoveOperation.End)  # lo más reciente, al final

        totales = datos.get("lineas_totales", 0)
        devueltas = datos.get("lineas_devueltas", 0)
        if devueltas < totales:
            self.lbl_estado.setText(f"Mostrando las últimas {devueltas} de {totales} líneas del log.")
        else:
            self.lbl_estado.setText(f"Log completo ({totales} línea{'s' if totales != 1 else ''}).")
