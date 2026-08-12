"""
satelite/dialogo_configuracion_conexion.py
--------------------------------------------------------
Diálogo de "Host / Puerto / Token" — pedido explícito: "que la
configuración no esté a la vista, sino dentro de un menu interno,
disponible mediante un menu arriba". Antes estos 3 campos vivían
siempre visibles arriba de la ventana; ahora solo se ven al abrir
este diálogo desde el menú "Conexión".
--------------------------------------------------------
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox


class DialogoConfiguracionConexion(QDialog):
    def __init__(self, host: str, puerto: int, token: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar conexión")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_host = QLineEdit(host)
        form.addRow("Host:", self.txt_host)

        self.txt_puerto = QLineEdit(str(puerto))
        form.addRow("Puerto:", self.txt_puerto)

        self.txt_token = QLineEdit(token)
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Token:", self.txt_token)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def resultado(self) -> dict:
        try:
            puerto = int(self.txt_puerto.text().strip())
        except ValueError:
            puerto = 8765
        return {
            "host": self.txt_host.text().strip() or "127.0.0.1",
            "puerto": puerto,
            "token": self.txt_token.text().strip(),
        }
