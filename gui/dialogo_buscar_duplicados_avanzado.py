"""
gui/dialogo_buscar_duplicados_avanzado.py
--------------------------------------------------------
Buscador de duplicados AVANZADO -- pedido explícito, sustituye/amplía
el buscador simple de criterios exactos combinables
(gui/dialogo_duplicados.py) con coincidencia APROXIMADA en 3 niveles
de prioridad, evaluados del más estricto al más laxo (ver
core/buscador_duplicados.py):

  Nivel 1: nombre 100% + duración 100% + tamaño 100%
  Nivel 2: nombre 80%+ (similitud) + duración 100% (exacta)
  Nivel 3: nombre 50%+ (similitud) + duración 90%+ (similar)

Sobre cada grupo encontrado (2 o más archivos -- "pueden existir más
de 2 archivos duplicados, la lista debe ser completa"), el operador
puede:
  - Escuchar el ▶ Previo de cualquier miembro (SIEMPRE la salida de
    Preescucha, nunca la Master que va al aire -- mismo criterio que
    el resto de los previos de la app).
  - Marcar cuáles ELIMINAR (checkbox por fila) -- lo que queda sin
    tildar se mantiene. Nada obliga a elegir; si no se tilda nada, ese
    grupo se deja intacto.
  - Aplicar los cambios de ESE grupo y pasar al siguiente, ⏭ Omitir el
    grupo entero sin tocar nada, o Cancelar (corta toda la revisión).

Dos flujos, elegidos por VentanaExplorador ANTES de abrir este
archivo:
  - Revisión UNO POR UNO (DialogoRevisarGrupoDuplicado, un diálogo por
    grupo, secuencial) -- disponible siempre.
  - MODO AUTOMÁTICO EN MASA (DialogoPlanMasivoDuplicados) -- pedido
    explícito como bonus SOLO cuando se buscó dentro de una categoría
    específica (no toda la biblioteca): arma un PLAN completo de una
    (una sugerencia de qué mantener por grupo, heurística en
    core.buscador_duplicados.sugerir_indice_a_mantener) y lo muestra
    TODO junto en un árbol con checkboxes -- el operador puede
    aprobarlo de una ("✅ Aprobar plan completo") o entrar a editar
    cualquier ítem puntual (tildar/destildar) antes de aprobar.

En los dos flujos, "Eliminar" borra el REGISTRO de la biblioteca JSON
-- nunca el archivo físico (mismo criterio ya establecido para
gui/dialogo_duplicados.py, para no confundir con el "Eliminar" de
gui/dialogo_vincular_archivo.py, que sí borra el archivo real de la
PC y nunca toca el JSON).
--------------------------------------------------------
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QDialogButtonBox, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt

from core.audio_engine import MotorAudio
from core.buscador_duplicados import DESCRIPCION_NIVEL, sugerir_indice_a_mantener

COL_TITULO, COL_CATEGORIA, COL_DURACION, COL_TAMANO, COL_RUTA = range(5)


def _formatear_tamano(tamano_bytes) -> str:
    if not tamano_bytes:
        return "(desconocido)"
    valor = float(tamano_bytes)
    for unidad in ("B", "KB", "MB", "GB"):
        if valor < 1024:
            return f"{valor:.0f} {unidad}" if unidad == "B" else f"{valor:.1f} {unidad}"
        valor /= 1024
    return f"{valor:.1f} TB"


class _DialogoConPrevio(QDialog):
    """Base compartida por los dos flujos: motor de Previo (Preescucha,
    nunca la Master), sin duplicar ese manejo en las dos subclases."""

    def __init__(self, id_dispositivo_preescucha, parent=None):
        super().__init__(parent)
        self._motor = MotorAudio(id_dispositivo_preescucha, aplicar_procesador=False)
        self._motor.finalizo_item.connect(self._detener_previo)

    def _reproducir_previo(self, ruta: str):
        if not ruta:
            return
        self._motor.reproducir(ruta)

    def _detener_previo(self):
        self._motor.detener()

    def reject(self):
        self._detener_previo()
        super().reject()

    def closeEvent(self, evento):
        self._detener_previo()
        super().closeEvent(evento)


class DialogoRevisarGrupoDuplicado(_DialogoConPrevio):
    """Revisión de UN grupo de duplicados -- flujo secuencial "uno por
    uno"."""

    # Código de resultado propio para "⏭ Omitir" (distinto de
    # QDialog.Accepted=1/Rejected=0), mismo patrón que
    # DialogoVincularArchivo.SALTAR.
    SALTAR = 2

    def __init__(self, nivel: int, miembros: list, resolver_ruta_categoria,
                 id_dispositivo_preescucha, indice_grupo: int, total_grupos: int, parent=None):
        super().__init__(id_dispositivo_preescucha, parent)
        self.setWindowTitle(f"Duplicado {indice_grupo} de {total_grupos}")
        self.setMinimumSize(720, 380)

        layout = QVBoxLayout(self)
        descripcion = DESCRIPCION_NIVEL.get(nivel, f"Nivel {nivel}")
        layout.addWidget(QLabel(
            f"Grupo {indice_grupo} de {total_grupos} -- {len(miembros)} archivo(s) parecidos.\n"
            f"{descripcion}."
        ))
        layout.addWidget(QLabel(
            "Tildá los que querés ELIMINAR de la biblioteca (lo que dejes sin\n"
            "tildar se mantiene). Podés escuchar el previo antes de decidir:"
        ))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Título", "Categoría", "Duración", "Tamaño", "Ruta"])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.tree)

        sugerido_mantener = sugerir_indice_a_mantener([r for r, _c in miembros])
        for i, (registro, categoria) in enumerate(miembros):
            ruta = registro.get("ruta", "") or ""
            ruta_categoria = " > ".join(resolver_ruta_categoria(categoria)) or "(raíz)"
            item = QTreeWidgetItem([
                registro.get("titulo", ""),
                ruta_categoria,
                registro.get("duracion", ""),
                _formatear_tamano(registro.get("tamaño_bytes")),
                ruta or "(sin vincular)",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, ruta)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                COL_TITULO,
                Qt.CheckState.Unchecked if i == sugerido_mantener else Qt.CheckState.Checked,
            )
            self.tree.addTopLevelItem(item)
        for columna in range(5):
            self.tree.resizeColumnToContents(columna)
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(sugerido_mantener))
        self.tree.itemSelectionChanged.connect(self._detener_previo)

        fila_previo = QHBoxLayout()
        btn_previo = QPushButton("▶ Previo")
        btn_previo.clicked.connect(self._reproducir_seleccion)
        btn_detener = QPushButton("■ Detener")
        btn_detener.clicked.connect(self._detener_previo)
        fila_previo.addWidget(btn_previo)
        fila_previo.addWidget(btn_detener)
        fila_previo.addStretch()
        layout.addLayout(fila_previo)

        fila_botones = QHBoxLayout()
        btn_omitir = QPushButton("⏭ Omitir este grupo")
        btn_omitir.clicked.connect(self._omitir)
        fila_botones.addWidget(btn_omitir)
        fila_botones.addStretch()
        botones = QDialogButtonBox()
        botones.addButton("✅ Aplicar y seguir", QDialogButtonBox.ButtonRole.AcceptRole)
        botones.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        botones.accepted.connect(self._aplicar)
        botones.rejected.connect(self.reject)
        fila_botones.addWidget(botones)
        layout.addLayout(fila_botones)

    def _reproducir_seleccion(self):
        item = self.tree.currentItem()
        if item is None:
            return
        self._reproducir_previo(item.data(0, Qt.ItemDataRole.UserRole))

    def _omitir(self):
        self._detener_previo()
        self.done(self.SALTAR)

    def _indices_marcados(self) -> list:
        return [
            i for i in range(self.tree.topLevelItemCount())
            if self.tree.topLevelItem(i).checkState(COL_TITULO) == Qt.CheckState.Checked
        ]

    def _aplicar(self):
        indices = self._indices_marcados()
        if indices and len(indices) == self.tree.topLevelItemCount():
            respuesta = QMessageBox.question(
                self, "Eliminar todo el grupo",
                "Tildaste TODOS los archivos de este grupo -- no quedaría ninguno.\n"
                "¿Confirmás eliminarlos todos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        self._detener_previo()
        self.accept()

    def indices_a_eliminar(self) -> list:
        return self._indices_marcados()


class DialogoPlanMasivoDuplicados(_DialogoConPrevio):
    """Modo AUTOMÁTICO EN MASA (bonus, solo ofrecido tras elegir una
    categoría específica): arma un plan completo -- todos los grupos
    juntos, con una sugerencia de qué mantener por grupo -- y lo deja
    aprobar de una, o editar (tildar/destildar) antes de aprobar."""

    def __init__(self, grupos: list, resolver_ruta_categoria, id_dispositivo_preescucha, parent=None):
        super().__init__(id_dispositivo_preescucha, parent)
        self.setWindowTitle("Plan de duplicados -- modo automático en masa")
        self.setMinimumSize(780, 480)
        self._plan_aprobado = []

        layout = QVBoxLayout(self)
        total_archivos = sum(len(g["miembros"]) for g in grupos)
        layout.addWidget(QLabel(
            f"{len(grupos)} grupo(s) de duplicados -- {total_archivos} archivo(s) en total.\n"
            "Ya viene tildado (para eliminar) lo que el sistema sugiere -- revisá y\n"
            "ajustá lo que haga falta antes de aprobar el plan completo:"
        ))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Título", "Categoría", "Duración", "Tamaño", "Ruta"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.tree)

        self._items_hijos = []  # list[(QTreeWidgetItem, registro, categoria)]
        for indice_grupo, grupo in enumerate(grupos, start=1):
            miembros = grupo["miembros"]
            descripcion = DESCRIPCION_NIVEL.get(grupo["nivel"], f"Nivel {grupo['nivel']}")
            nodo_grupo = QTreeWidgetItem([
                f"Grupo {indice_grupo} -- {len(miembros)} archivo(s) -- {descripcion}", "", "", "", "",
            ])
            nodo_grupo.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(nodo_grupo)

            sugerido_mantener = sugerir_indice_a_mantener([r for r, _c in miembros])
            for i, (registro, categoria) in enumerate(miembros):
                ruta = registro.get("ruta", "") or ""
                ruta_categoria = " > ".join(resolver_ruta_categoria(categoria)) or "(raíz)"
                hijo = QTreeWidgetItem([
                    registro.get("titulo", ""),
                    ruta_categoria,
                    registro.get("duracion", ""),
                    _formatear_tamano(registro.get("tamaño_bytes")),
                    ruta or "(sin vincular)",
                ])
                hijo.setData(0, Qt.ItemDataRole.UserRole, ruta)
                hijo.setFlags(hijo.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                hijo.setCheckState(
                    COL_TITULO,
                    Qt.CheckState.Unchecked if i == sugerido_mantener else Qt.CheckState.Checked,
                )
                nodo_grupo.addChild(hijo)
                self._items_hijos.append((hijo, registro, categoria))
            nodo_grupo.setExpanded(True)

        for columna in range(5):
            self.tree.resizeColumnToContents(columna)
        self.tree.itemSelectionChanged.connect(self._detener_previo)

        fila_previo = QHBoxLayout()
        btn_previo = QPushButton("▶ Previo")
        btn_previo.clicked.connect(self._reproducir_seleccion)
        btn_detener = QPushButton("■ Detener")
        btn_detener.clicked.connect(self._detener_previo)
        fila_previo.addWidget(btn_previo)
        fila_previo.addWidget(btn_detener)
        fila_previo.addStretch()
        layout.addLayout(fila_previo)

        botones = QDialogButtonBox()
        botones.addButton("✅ Aprobar plan completo", QDialogButtonBox.ButtonRole.AcceptRole)
        botones.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        botones.accepted.connect(self._aprobar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _reproducir_seleccion(self):
        item = self.tree.currentItem()
        if item is None or item.parent() is None:
            return
        self._reproducir_previo(item.data(0, Qt.ItemDataRole.UserRole))

    def _grupos_que_quedarian_vacios(self) -> list:
        vaciados = []
        indice_hijo = 0
        for nodo_i in range(self.tree.topLevelItemCount()):
            nodo = self.tree.topLevelItem(nodo_i)
            hijos_de_este_grupo = self._items_hijos[indice_hijo:indice_hijo + nodo.childCount()]
            indice_hijo += nodo.childCount()
            if hijos_de_este_grupo and all(
                hijo.checkState(COL_TITULO) == Qt.CheckState.Checked for hijo, _r, _c in hijos_de_este_grupo
            ):
                vaciados.append(nodo.text(0))
        return vaciados

    def _aprobar(self):
        grupos_vaciados = self._grupos_que_quedarian_vacios()
        if grupos_vaciados:
            respuesta = QMessageBox.question(
                self, "Grupos completos marcados",
                "Estos grupos quedarían con TODOS sus archivos eliminados "
                "(ninguno se mantiene):\n\n" + "\n".join(f"- {g}" for g in grupos_vaciados) +
                "\n\n¿Confirmás aplicar el plan igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        self._plan_aprobado = [
            (registro, categoria) for hijo, registro, categoria in self._items_hijos
            if hijo.checkState(COL_TITULO) == Qt.CheckState.Checked
        ]
        self._detener_previo()
        self.accept()

    def plan_aprobado(self) -> list:
        return self._plan_aprobado
