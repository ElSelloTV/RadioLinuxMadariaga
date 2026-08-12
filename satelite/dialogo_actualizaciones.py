"""
satelite/dialogo_actualizaciones.py
--------------------------------------------------------
Actualizar la app satélite por GitHub (pedido explícito: "agregale
también en Configuraciones, la opción de actualizar el programa por
GitHub, aunque reinice la APP, no importa") — mismo mecanismo y misma
UX que Configuración → Actualizaciones de la app principal
(gui/ventana_configuracion.py), reusando core/actualizador.py tal
cual (git fetch/pull + reinicio del proceso, ambas apps comparten el
MISMO checkout git — no hay dos repos separados). La ÚNICA diferencia
real es a qué script relanza el reinicio: `reiniciar_aplicacion(app,
script="satelite_main.py")` — nunca `main.py`, la satélite tiene que
reabrirse a SÍ MISMA, no la radio.
--------------------------------------------------------
"""
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
)

import core.actualizador as actualizador


class DialogoActualizaciones(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Actualizaciones")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        lbl_repo = QLabel(f"Repositorio: {actualizador.REPO_URL}")
        lbl_repo.setWordWrap(True)
        layout.addWidget(lbl_repo)

        self.lbl_version_actual = QLabel(f"Versión instalada (commit): {actualizador.commit_actual()}")
        layout.addWidget(self.lbl_version_actual)

        self.lbl_estado = QLabel("Todavía no se buscaron actualizaciones en esta sesión.")
        self.lbl_estado.setWordWrap(True)
        layout.addWidget(self.lbl_estado)

        barra_botones = QHBoxLayout()
        self.btn_buscar = QPushButton("🔎 Buscar actualización")
        self.btn_buscar.clicked.connect(self._buscar)
        self.btn_actualizar = QPushButton("⬇ Actualizar y reiniciar")
        self.btn_actualizar.setObjectName("btnPlay")
        self.btn_actualizar.setEnabled(False)
        self.btn_actualizar.clicked.connect(self._actualizar)
        barra_botones.addWidget(self.btn_buscar)
        barra_botones.addWidget(self.btn_actualizar)
        layout.addLayout(barra_botones)

        nota = QLabel(
            "Al actualizar, la app satélite descarga los cambios desde GitHub\n"
            "(git pull) y se reinicia sola — se cierra y vuelve a abrir con la\n"
            "versión nueva ya aplicada. La radio (programa principal) NO se toca\n"
            "ni se reinicia desde acá."
        )
        nota.setWordWrap(True)
        layout.addWidget(nota)

        if not actualizador.es_instalacion_git():
            self.lbl_estado.setText(
                "Esta copia no es una instalación por git — la actualización\n"
                "automática no está disponible acá."
            )
            self.btn_buscar.setEnabled(False)

    def _buscar(self):
        self.lbl_estado.setText("Buscando actualizaciones en GitHub...")
        QApplication.processEvents()

        hay_actualizacion, mensaje = actualizador.hay_actualizacion_disponible()
        self.lbl_estado.setText(mensaje)
        self.btn_actualizar.setEnabled(hay_actualizacion)

    def _actualizar(self):
        respuesta = QMessageBox.question(
            self, "Actualizar",
            "Se va a descargar la actualización y la app satélite se va a\n"
            "reiniciar. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.lbl_estado.setText("Descargando actualización...")
        QApplication.processEvents()

        exito, mensaje = actualizador.aplicar_actualizacion()
        self.lbl_estado.setText(mensaje)

        if not exito:
            QMessageBox.warning(self, "Actualizar", mensaje)
            return

        QMessageBox.information(self, "Actualizar", "Actualización aplicada. La app satélite se va a reiniciar.")
        actualizador.reiniciar_aplicacion(QApplication.instance(), script="satelite_main.py")
