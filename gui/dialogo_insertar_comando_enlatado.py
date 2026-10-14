"""
gui/dialogo_insertar_comando_enlatado.py
--------------------------------------------------------
Insertar un Comando ENLATADO en un bloque de Publicidad (o del
Programador) — pedido explícito: "programas 'enlatados' que se cargan
semanalmente... el comando ENLATADO pondrá solamente en reproducción
el último archivo cargado en la categoría ya configurada" (tipo
"categoria") o, más adelante, "una carpeta de Google Drive... reproduce
todos los bloques en orden" (tipo "drive", unificado al mismo
mecanismo — ver core/playlist_manager.py). A diferencia del Comando
FMT (lista formatos ya creados en el Musicalizador) o HTH (3 tipos
fijos), acá los slots son una lista CRECEDORA con NOMBRE propio, cada
uno configurado aparte en Configuración → Enlatados. Este diálogo solo
elige CUÁL insertar, mostrando de un vistazo qué tiene configurado
cada uno (o el aviso de que todavía no se configuró nada).
--------------------------------------------------------
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLabel, QDialogButtonBox

from config.settings import cargar_configuracion, listar_enlatados


class DialogoInsertarComandoEnlatado(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Comando ENLATADO")
        self.setMinimumWidth(420)
        self._parametro_elegido = None
        self._entradas = listar_enlatados(cargar_configuracion())

        layout = QVBoxLayout(self)
        if not self._entradas:
            layout.addWidget(QLabel(
                "Todavía no hay ningún Enlatado creado. Creá uno primero en\n"
                "Configuración → 📦 Enlatados (categoría local o carpeta de\n"
                "Google Drive)."
            ))
        else:
            layout.addWidget(QLabel(
                "Al llegar la reproducción a este comando, reproduce el\n"
                "contenido del slot elegido -- el ÚLTIMO archivo cargado (si es\n"
                "una categoría local) o todos los archivos sincronizados en\n"
                "orden (si es una carpeta de Drive). Terminado, sigue directo\n"
                "con lo que haya después en el bloque. Si el slot está vacío o\n"
                "mal configurado, se saltea sin sonar nada."
            ))
            self.combo_slot = QComboBox()
            for entrada in self._entradas:
                self.combo_slot.addItem(entrada.get("nombre") or "(sin nombre)", entrada.get("id"))
            self.combo_slot.currentIndexChanged.connect(self._actualizar_descripcion)
            layout.addWidget(self.combo_slot)

            self.lbl_detalle = QLabel()
            self.lbl_detalle.setWordWrap(True)
            layout.addWidget(self.lbl_detalle)
            self._actualizar_descripcion()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._confirmar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        if not self._entradas:
            botones.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _entrada_actual(self) -> dict | None:
        id_slot = self.combo_slot.currentData()
        for entrada in self._entradas:
            if entrada.get("id") == id_slot:
                return entrada
        return None

    def _actualizar_descripcion(self, *_args):
        entrada = self._entrada_actual()
        if entrada is None:
            self.lbl_detalle.setText("")
            return
        if entrada.get("tipo") == "drive":
            url = entrada.get("url_carpeta")
            self.lbl_detalle.setText(
                f"Carpeta de Drive: {url}" if url else
                "⚠ Sin enlace de Drive configurado todavía -- andá a Configuración "
                "→ Enlatados y pegalo."
            )
        else:
            ruta = entrada.get("categoria_ruta")
            self.lbl_detalle.setText(
                "Categoría configurada: " + " / ".join(ruta) if ruta else
                "⚠ Todavía sin categoría configurada -- andá a Configuración → "
                "Enlatados y elegí una antes de usar este comando."
            )

    def _confirmar(self):
        self._parametro_elegido = self.combo_slot.currentData()
        self.accept()

    def parametro_elegido(self) -> str | None:
        return self._parametro_elegido
