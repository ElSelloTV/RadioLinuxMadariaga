"""
satelite/dialogo_programador_remoto.py
--------------------------------------------------------
Programador remoto — pedido explícito: "que pueda mediante otro
botón, programar, igual que en el programa principal" y, ronda
posterior, "dame todo... todo lo que tiene el principal y este no".

Cubre TODO el flujo del Programador local (`gui/ventana_programador.py`):
cargar un punto de partida (guardada / lo actual de Ventana 1 / vacía),
armar bloques e ítems, reordenar (↑ Subir / ↓ Bajar, en vez de
drag&drop — mismo resultado, mecanismo más simple para un panel
remoto), Copiar/Pegar entre bloques, Comando FMT/HTH/ENLATADO, Ítem
Aleatorio, Reemplazar (bloque: hora/título; ítem: cambia el archivo
sin mover su posición), pre-escucha por la salida de Preescucha del
lado servidor, Duplicar para otro día, Guardar y Aplicar Ahora en
Ventana 1.

El estado real vive acá, en `self._bloques` (una lista de dicts, el
MISMO formato que ya usa `cargar_bloques()`/`programacion.json`) — el
árbol visual se reconstruye entero desde ahí después de cada cambio
("redraw from model").
--------------------------------------------------------
"""
import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QMenu,
)
from PySide6.QtCore import Qt

from satelite.cliente_control_remoto import ErrorControlRemoto
from satelite.dialogo_bloque_horario import DialogoBloqueHorario
from satelite.dialogo_elegir_registro_biblioteca import DialogoElegirRegistroBiblioteca
from satelite.dialogo_guardar_programacion import DialogoGuardarProgramacion
from satelite.dialogo_insertar_item_aleatorio_remoto import DialogoInsertarItemAleatorioRemoto

TIPOS_HTH = ["HORA", "TEMPERATURA", "HUMEDAD"]


class DialogoProgramadorRemoto(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Programador (remoto)")
        self.resize(680, 620)
        self._cliente = cliente
        self._bloques = []
        self._categorias = []
        self._portapapeles = []
        self._construir_ui()
        self._cargar_categorias()

    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QVBoxLayout(self)

        fila_origen = QHBoxLayout()
        btn_cargar_guardada = QPushButton("📂 Cargar guardada...")
        btn_cargar_actual = QPushButton("⬇ Cargar el actual (Ventana 1)")
        btn_nueva = QPushButton("🗎 Nueva (vacía)")
        btn_duplicar = QPushButton("⧉ Duplicar para otro día...")
        btn_duplicar.setToolTip("Guarda una copia de lo cargado acá bajo un nombre y día/fecha nuevos.")
        btn_cargar_guardada.clicked.connect(self._cargar_guardada)
        btn_cargar_actual.clicked.connect(self._cargar_actual)
        btn_nueva.clicked.connect(self._nueva)
        btn_duplicar.clicked.connect(self._duplicar)
        fila_origen.addWidget(btn_cargar_guardada)
        fila_origen.addWidget(btn_cargar_actual)
        fila_origen.addWidget(btn_nueva)
        fila_origen.addWidget(btn_duplicar)
        layout.addLayout(fila_origen)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Bloques e ítems"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tree.itemSelectionChanged.connect(self._detener_previo)
        layout.addWidget(self.tree, 1)

        fila_edicion = QHBoxLayout()
        btn_agregar_bloque = QPushButton("＋ Bloque horario...")
        btn_agregar_item = QPushButton("➕ Agregar ítem...")
        btn_reemplazar = QPushButton("🔁 Reemplazar")
        btn_reemplazar.setToolTip(
            "Bloque seleccionado: edita su hora/título.\nÍtem seleccionado: cambia el archivo sin mover su posición."
        )
        btn_quitar = QPushButton("✕ Quitar seleccionado")
        btn_agregar_bloque.clicked.connect(self._agregar_bloque)
        btn_agregar_item.clicked.connect(self._agregar_item)
        btn_reemplazar.clicked.connect(self._reemplazar_seleccionado)
        btn_quitar.clicked.connect(self._quitar_seleccionado)
        fila_edicion.addWidget(btn_agregar_bloque)
        fila_edicion.addWidget(btn_agregar_item)
        fila_edicion.addWidget(btn_reemplazar)
        fila_edicion.addWidget(btn_quitar)
        layout.addLayout(fila_edicion)

        fila_especiales = QHBoxLayout()
        btn_agregar_fmt = QPushButton("▶ Comando FMT...")
        btn_agregar_fmt.setToolTip(
            "Al pasar la reproducción por este ítem, dispara la generación\n"
            "continua de música en Emisión según un formato del Musicalizador Avanzado."
        )
        btn_agregar_hth = QPushButton("▶ Comando HTH...")
        btn_agregar_hth.setToolTip("Anuncia hora/temperatura/humedad concatenando los clips del género \"HTH\".")
        btn_agregar_enlatado = QPushButton("▶ Comando ENLATADO...")
        btn_agregar_enlatado.setToolTip(
            "Reproduce el ÚLTIMO archivo cargado en la categoría configurada\n"
            "para ese slot (Configuración → Enlatados, lado radio)."
        )
        btn_agregar_aleatorio = QPushButton("🎲 Ítem Aleatorio...")
        btn_agregar_aleatorio.setToolTip("Elige un archivo al azar de una categoría CADA VEZ que le toca sonar.")
        btn_agregar_fmt.clicked.connect(self._insertar_comando_fmt)
        btn_agregar_hth.clicked.connect(self._insertar_comando_hth)
        btn_agregar_enlatado.clicked.connect(self._insertar_comando_enlatado)
        btn_agregar_aleatorio.clicked.connect(self._insertar_item_aleatorio)
        fila_especiales.addWidget(btn_agregar_fmt)
        fila_especiales.addWidget(btn_agregar_hth)
        fila_especiales.addWidget(btn_agregar_enlatado)
        fila_especiales.addWidget(btn_agregar_aleatorio)
        layout.addLayout(fila_especiales)

        fila_orden = QHBoxLayout()
        btn_subir = QPushButton("↑ Subir")
        btn_bajar = QPushButton("↓ Bajar")
        btn_subir.setToolTip("Mueve el ítem seleccionado hacia arriba, dentro de su propio bloque.")
        btn_bajar.setToolTip("Mueve el ítem seleccionado hacia abajo, dentro de su propio bloque.")
        btn_subir.clicked.connect(lambda: self._mover_item(-1))
        btn_bajar.clicked.connect(lambda: self._mover_item(1))
        btn_previo = QPushButton("▶ Previo")
        btn_previo.setToolTip("Pre-escuchar el ítem seleccionado por la salida de Preescucha (nunca la Master al aire).")
        btn_detener_previo = QPushButton("⏹ Detener")
        btn_previo.clicked.connect(self._reproducir_previo)
        btn_detener_previo.clicked.connect(self._detener_previo)
        fila_orden.addWidget(btn_subir)
        fila_orden.addWidget(btn_bajar)
        fila_orden.addWidget(btn_previo)
        fila_orden.addWidget(btn_detener_previo)
        layout.addLayout(fila_orden)

        fila_guardar = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar...")
        btn_aplicar_ahora = QPushButton("▶ Aplicar AHORA en Ventana 1")
        btn_guardar.clicked.connect(self._guardar)
        btn_aplicar_ahora.clicked.connect(self._aplicar_ahora)
        fila_guardar.addWidget(btn_guardar)
        fila_guardar.addWidget(btn_aplicar_ahora)
        layout.addLayout(fila_guardar)

    def _cargar_categorias(self):
        try:
            self._categorias = self._cliente.listar_categorias()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))

    # ------------------------------------------------------------------
    def _refrescar_arbol(self):
        # Recordar qué estaba seleccionado ANTES de reconstruir el
        # árbol entero ("redraw from model") -- sin esto, cada
        # inserción/edición dejaba la selección en blanco, obligando a
        # volver a clickear el bloque antes de la próxima acción
        # (molesto para encadenar varias inserciones seguidas, ej.
        # Comando FMT + Comando HTH + Ítem Aleatorio en el mismo bloque).
        item_previo = self.tree.currentItem()
        seleccion_previa = item_previo.data(0, Qt.ItemDataRole.UserRole) if item_previo is not None else None

        self.tree.clear()
        nodo_a_reseleccionar = None
        for i_bloque, bloque in enumerate(self._bloques):
            nodo = QTreeWidgetItem([f"{bloque.get('hora', '00:00:00')} - {bloque.get('titulo', '')}"])
            nodo.setData(0, Qt.ItemDataRole.UserRole, (i_bloque, None))
            fuente = nodo.font(0)
            fuente.setBold(True)
            nodo.setFont(0, fuente)
            if seleccion_previa == (i_bloque, None):
                nodo_a_reseleccionar = nodo
            for i_item, item in enumerate(bloque.get("items", [])):
                nodo_item = QTreeWidgetItem([self._texto_item(item)])
                nodo_item.setData(0, Qt.ItemDataRole.UserRole, (i_bloque, i_item))
                nodo.addChild(nodo_item)
                if seleccion_previa == (i_bloque, i_item):
                    nodo_a_reseleccionar = nodo_item
            nodo.setExpanded(True)
            self.tree.addTopLevelItem(nodo)

        if nodo_a_reseleccionar is not None:
            self.tree.setCurrentItem(nodo_a_reseleccionar)

    @staticmethod
    def _item_desde_registro(registro: dict) -> dict:
        """Arma un ítem de tanda a partir de un registro de la
        biblioteca remota (`listar_registros_categoria`) -- lleva
        SIEMPRE el recorte de silencio/nivelado YA calculado para ese
        archivo (`punto_inicio_ms`/`punto_fin_ms`/`ganancia_db`), nunca
        valores neutros a ciegas -- mismo criterio que la versión
        local, que arrastra este análisis en cada alta/reemplazo."""
        return {
            "titulo": registro.get("titulo", ""), "duracion": registro.get("duracion", ""),
            "codigo": registro.get("codigo", "—"), "ruta": registro.get("ruta", ""),
            "punto_inicio_ms": registro.get("punto_inicio_ms") or 0,
            "punto_fin_ms": registro.get("punto_fin_ms"),
            "ganancia_db": registro.get("ganancia_db") or 0.0,
            "fecha_inicio": None, "fecha_fin": None,
        }

    @staticmethod
    def _texto_item(item: dict) -> str:
        if item.get("es_comando"):
            return f"▶ {item.get('tipo_comando')}: {item.get('parametro_comando')}"
        if item.get("es_aleatorio"):
            categoria = " / ".join(item.get("categoria_aleatorio") or [])
            return f"🎲 Aleatorio: {categoria}"
        return f"{item.get('titulo', '')} ({item.get('duracion', '')})"

    # ------------------------------------------------------------------
    def _cargar_guardada(self):
        try:
            guardadas = self._cliente.programador_listar_guardadas()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not guardadas:
            QMessageBox.information(self, "Programador", "Todavía no hay ninguna programación guardada.")
            return
        opciones = [f"{g['nombre']} ({g['clave']})" for g in guardadas]
        elegido, ok = QInputDialog.getItem(self, "Cargar programación", "Elegí una:", opciones, editable=False)
        if not ok:
            return
        g = guardadas[opciones.index(elegido)]
        respuesta = self._cliente.programador_cargar_guardada(g["tipo"], g["clave"])
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo cargar."))
            return
        self._bloques = respuesta["datos"]["bloques"]
        self._refrescar_arbol()

    def _cargar_actual(self):
        try:
            self._bloques = self._cliente.programador_bloques_actuales()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        self._refrescar_arbol()

    def _nueva(self):
        if self._bloques:
            respuesta = QMessageBox.question(
                self, "Nueva programación", "Se va a vaciar el editor actual. ¿Confirmás?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        self._bloques = []
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    def _bloque_destino(self):
        item = self.tree.currentItem()
        if item is None:
            return len(self._bloques) - 1 if self._bloques else None
        indices = item.data(0, Qt.ItemDataRole.UserRole)
        return indices[0]

    def _indice_insercion(self, i_bloque):
        """Si hay un ÍTEM (no un bloque) seleccionado DENTRO del bloque
        destino, la próxima inserción va justo DESPUÉS de él -- mismo
        criterio que el Programador local (insertar en el lugar
        seleccionado, no siempre al final)."""
        item = self.tree.currentItem()
        if item is None:
            return None
        i_bloque_sel, i_item_sel = item.data(0, Qt.ItemDataRole.UserRole)
        if i_bloque_sel == i_bloque and i_item_sel is not None:
            return i_item_sel + 1
        return None

    def _indice_insercion_para_hora(self, hora: str, excluir_indice: int = None) -> int:
        """Mismo criterio que la versión local (gui/ventana_programador.py):
        posición donde insertar/reubicar un bloque con esta hora para
        que la lista quede SIEMPRE ordenada cronológicamente — bug
        real corregido (pedido explícito: "agrego un bloque a las
        11:50... y en vez de ubicarlo entre las 11 y las 12, lo manda
        al final"). Comparación lexicográfica sobre "HH:MM:SS"
        (zero-padded) alcanza. `excluir_indice` se saltea para no
        comparar un bloque ya existente contra sí mismo al reubicarlo."""
        for i, bloque in enumerate(self._bloques):
            if i == excluir_indice:
                continue
            if (bloque.get("hora") or "00:00:00") > hora:
                return i
        return len(self._bloques)

    def _agregar_bloque(self):
        dialogo = DialogoBloqueHorario(datetime.datetime.now().strftime("%H:%M:%S"), parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        indice = self._indice_insercion_para_hora(datos["hora"])
        self._bloques.insert(indice, {"hora": datos["hora"], "titulo": datos["titulo"], "items": []})
        self._refrescar_arbol()
        self.tree.setCurrentItem(self.tree.topLevelItem(indice))

    def _quitar_seleccionado(self):
        item = self.tree.currentItem()
        if item is None:
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)
        if i_item is None:
            respuesta = QMessageBox.question(
                self, "Quitar bloque",
                "¿Quitar este bloque horario completo (con todos sus ítems)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
            del self._bloques[i_bloque]
        else:
            del self._bloques[i_bloque]["items"][i_item]
        self._refrescar_arbol()

    def _agregar_item(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Agregar ítem", "Primero creá un bloque horario.")
            return
        if not self._categorias:
            QMessageBox.warning(self, "Agregar ítem", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoElegirRegistroBiblioteca(self._cliente, self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if not registro:
            return
        item = self._item_desde_registro(registro)
        indice = self._indice_insercion(i_bloque)
        if indice is None:
            self._bloques[i_bloque]["items"].append(item)
        else:
            self._bloques[i_bloque]["items"].insert(indice, item)
        self._refrescar_arbol()

    def _insertar_comando_fmt(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Comando FMT", "Primero creá un bloque horario.")
            return
        try:
            formatos = self._cliente.musicalizador_listar_formatos()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not formatos:
            QMessageBox.information(
                self, "Comando FMT", "Todavía no hay ningún formato creado en el Musicalizador Avanzado.",
            )
            return
        elegido, ok = QInputDialog.getItem(self, "Insertar Comando FMT", "Formato:", formatos, editable=False)
        if not ok:
            return
        item = {"es_comando": True, "tipo_comando": "FMT", "parametro_comando": elegido}
        indice = self._indice_insercion(i_bloque)
        if indice is None:
            self._bloques[i_bloque]["items"].append(item)
        else:
            self._bloques[i_bloque]["items"].insert(indice, item)
        self._refrescar_arbol()

    def _insertar_comando_hth(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Comando HTH", "Primero creá un bloque horario.")
            return
        elegido, ok = QInputDialog.getItem(self, "Insertar Comando HTH", "Tipo:", TIPOS_HTH, editable=False)
        if not ok:
            return
        item = {"es_comando": True, "tipo_comando": "HTH", "parametro_comando": elegido}
        indice = self._indice_insercion(i_bloque)
        if indice is None:
            self._bloques[i_bloque]["items"].append(item)
        else:
            self._bloques[i_bloque]["items"].insert(indice, item)
        self._refrescar_arbol()

    def _insertar_comando_enlatado(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Comando ENLATADO", "Primero creá un bloque horario.")
            return
        try:
            enlatados = self._cliente.listar_enlatados()
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        opciones = []
        for numero in ("1", "2", "3", "4", "5"):
            ruta = enlatados.get(numero)
            etiqueta = f"{numero} — " + (" / ".join(ruta) if ruta else "(sin configurar)")
            opciones.append(etiqueta)
        elegido, ok = QInputDialog.getItem(self, "Insertar Comando ENLATADO", "Slot:", opciones, editable=False)
        if not ok:
            return
        numero = elegido.split(" — ", 1)[0]
        item = {"es_comando": True, "tipo_comando": "ENLATADO", "parametro_comando": numero}
        indice = self._indice_insercion(i_bloque)
        if indice is None:
            self._bloques[i_bloque]["items"].append(item)
        else:
            self._bloques[i_bloque]["items"].insert(indice, item)
        self._refrescar_arbol()

    def _insertar_item_aleatorio(self):
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Ítem Aleatorio", "Primero creá un bloque horario.")
            return
        if not self._categorias:
            QMessageBox.warning(self, "Ítem Aleatorio", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoInsertarItemAleatorioRemoto(self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        resultado = dialogo.resultado()
        if not resultado:
            return
        categoria, recursivo, cantidad = resultado
        indice = self._indice_insercion(i_bloque)
        for _ in range(cantidad):
            item = {"es_aleatorio": True, "categoria_aleatorio": categoria, "recursivo_aleatorio": recursivo}
            if indice is None:
                self._bloques[i_bloque]["items"].append(item)
            else:
                self._bloques[i_bloque]["items"].insert(indice, item)
                indice += 1
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    # Reemplazar (pedido explícito, "todo lo que tiene el principal"):
    # bloque -> edita hora/título; ítem -> cambia el archivo sin mover
    # su posición; Comando/Aleatorio -> avisa (se saca y se agrega uno
    # nuevo, mismo criterio que la versión local).
    # ------------------------------------------------------------------
    def _reemplazar_seleccionado(self):
        item = self.tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Reemplazar", "Seleccioná un bloque o un ítem primero.")
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)

        if i_item is None:
            dialogo = DialogoBloqueHorario(
                self._bloques[i_bloque].get("hora", "00:00:00"),
                self._bloques[i_bloque].get("titulo", "TANDA - Rotativa"), parent=self,
            )
            if dialogo.exec() != QDialog.DialogCode.Accepted:
                return
            datos = dialogo.resultado()
            self._bloques[i_bloque]["hora"] = datos["hora"]
            self._bloques[i_bloque]["titulo"] = datos["titulo"]
            # Mismo criterio que al agregar: si cambiar la hora saca al
            # bloque de su posición cronológica, se reubica solo.
            indice_correcto = self._indice_insercion_para_hora(datos["hora"], excluir_indice=i_bloque)
            if indice_correcto != i_bloque and indice_correcto != i_bloque + 1:
                bloque_movido = self._bloques.pop(i_bloque)
                if indice_correcto > i_bloque:
                    indice_correcto -= 1
                self._bloques.insert(indice_correcto, bloque_movido)
                i_bloque = indice_correcto
            self._refrescar_arbol()
            self.tree.setCurrentItem(self.tree.topLevelItem(i_bloque))
            return

        item_actual = self._bloques[i_bloque]["items"][i_item]
        if item_actual.get("es_comando") or item_actual.get("es_aleatorio"):
            QMessageBox.information(
                self, "Reemplazar",
                "Un Comando o un Ítem Aleatorio no se \"reemplaza\" — quitalo\n"
                "(✕ Quitar seleccionado) y agregá uno nuevo si querés cambiarlo.",
            )
            return

        if not self._categorias:
            QMessageBox.warning(self, "Reemplazar", "No hay categorías en la biblioteca remota.")
            return
        dialogo = DialogoElegirRegistroBiblioteca(self._cliente, self._categorias, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        registro = dialogo.resultado()
        if not registro:
            return
        self._bloques[i_bloque]["items"][i_item] = self._item_desde_registro(registro)
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    # Reordenar (pedido explícito -- mismo resultado que el drag&drop
    # local, ↑/↓ dentro del propio bloque).
    # ------------------------------------------------------------------
    def _mover_item(self, delta: int):
        item = self.tree.currentItem()
        if item is None:
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)
        if i_item is None:
            return
        items = self._bloques[i_bloque]["items"]
        nueva_posicion = i_item + delta
        if not (0 <= nueva_posicion < len(items)):
            return
        items[i_item], items[nueva_posicion] = items[nueva_posicion], items[i_item]
        self._refrescar_arbol()
        nodo_bloque = self.tree.topLevelItem(i_bloque)
        if nodo_bloque is not None:
            self.tree.setCurrentItem(nodo_bloque.child(nueva_posicion))

    # ------------------------------------------------------------------
    # Copiar / Pegar entre bloques (pedido explícito, mismo concepto
    # que el menú contextual de la versión local).
    # ------------------------------------------------------------------
    def _mostrar_menu_contextual(self, posicion):
        menu = QMenu(self)
        accion_copiar = menu.addAction("📋 Copiar")
        accion_pegar = menu.addAction("📌 Pegar en este bloque")
        accion_pegar.setEnabled(bool(self._portapapeles))
        elegida = menu.exec(self.tree.viewport().mapToGlobal(posicion))
        if elegida == accion_copiar:
            self._copiar_seleccionado()
        elif elegida == accion_pegar:
            self._pegar_en_bloque_actual()

    def _copiar_seleccionado(self):
        item = self.tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Copiar", "Seleccioná un ítem (no un bloque) para copiar.")
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)
        if i_item is None:
            QMessageBox.information(self, "Copiar", "Seleccioná un ítem (no un bloque entero) para copiar.")
            return
        self._portapapeles = [dict(self._bloques[i_bloque]["items"][i_item])]

    def _pegar_en_bloque_actual(self):
        if not self._portapapeles:
            QMessageBox.information(self, "Pegar", "Todavía no copiaste ningún ítem.")
            return
        i_bloque = self._bloque_destino()
        if i_bloque is None:
            QMessageBox.information(self, "Pegar", "Primero creá un bloque horario.")
            return
        indice = self._indice_insercion(i_bloque)
        for item_data in self._portapapeles:
            copia = dict(item_data)
            if indice is None:
                self._bloques[i_bloque]["items"].append(copia)
            else:
                self._bloques[i_bloque]["items"].insert(indice, copia)
                indice += 1
        self._refrescar_arbol()

    # ------------------------------------------------------------------
    # Pre-escucha (pedido explícito, "una pre-escucha por la salida
    # auxiliar" -- acá SIEMPRE del lado servidor, por la salida de
    # Preescucha configurada, nunca la Master al aire).
    # ------------------------------------------------------------------
    def _reproducir_previo(self):
        item = self.tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Previo", "Seleccioná un ítem para escuchar.")
            return
        i_bloque, i_item = item.data(0, Qt.ItemDataRole.UserRole)
        if i_item is None:
            QMessageBox.information(self, "Previo", "Seleccioná un ítem (no un bloque) para escuchar.")
            return
        item_datos = self._bloques[i_bloque]["items"][i_item]
        if item_datos.get("es_comando") or item_datos.get("es_aleatorio"):
            QMessageBox.information(
                self, "Previo", "Este ítem no tiene un archivo fijo para pre-escuchar (Comando o Aleatorio).",
            )
            return
        ruta = item_datos.get("ruta") or ""
        if not ruta:
            QMessageBox.warning(self, "Previo", "Este ítem no tiene un archivo vinculado.")
            return
        try:
            respuesta = self._cliente.previo_reproducir(
                ruta, item_datos.get("punto_inicio_ms") or 0,
                item_datos.get("punto_fin_ms"), item_datos.get("ganancia_db") or 0.0,
            )
        except ErrorControlRemoto as error:
            QMessageBox.warning(self, "Control remoto", str(error))
            return
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo reproducir el previo."))

    def _detener_previo(self):
        if self._cliente is None:
            return
        try:
            self._cliente.previo_detener()
        except ErrorControlRemoto:
            pass  # cerrar/cambiar de selección nunca debe romper por esto

    def closeEvent(self, evento):
        self._detener_previo()
        super().closeEvent(evento)

    def reject(self):
        self._detener_previo()
        super().reject()

    # ------------------------------------------------------------------
    def _duplicar(self):
        if not self._bloques:
            QMessageBox.warning(self, "Duplicar", "No hay bloques cargados en el editor para duplicar.")
            return
        dialogo = DialogoGuardarProgramacion(parent=self)
        dialogo.setWindowTitle("Duplicar para otro día")
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return
        respuesta = self._cliente.programador_guardar(
            datos["nombre"], self._bloques, datos["dias_semana"], datos["fecha_especifica"],
        )
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo duplicar."))
            return
        QMessageBox.information(
            self, "Duplicar", f"Se guardó \"{datos['nombre']}\" como una programación nueva.\nLa original no se modificó.",
        )

    def _guardar(self):
        if not self._bloques:
            QMessageBox.information(self, "Guardar", "No hay nada para guardar todavía.")
            return
        dialogo = DialogoGuardarProgramacion(parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        datos = dialogo.resultado()
        if not datos:
            return
        respuesta = self._cliente.programador_guardar(
            datos["nombre"], self._bloques, datos["dias_semana"], datos["fecha_especifica"],
        )
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo guardar."))
            return
        QMessageBox.information(self, "Guardar", f"Programación \"{datos['nombre']}\" guardada.")

    def _aplicar_ahora(self):
        if not self._bloques:
            QMessageBox.information(self, "Aplicar ahora", "No hay nada para aplicar todavía.")
            return
        respuesta_confirm = QMessageBox.question(
            self, "Aplicar AHORA en Ventana 1",
            "Esto reemplaza YA lo que Ventana 1 tiene cargado, en vivo -- puede cortar lo\n"
            "que esté sonando. ¿Confirmás?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta_confirm != QMessageBox.StandardButton.Yes:
            return
        respuesta = self._cliente.programador_aplicar_ahora(self._bloques)
        if not respuesta.get("ok"):
            QMessageBox.warning(self, "Control remoto", respuesta.get("error", "No se pudo aplicar."))
            return
        QMessageBox.information(self, "Aplicar ahora", "Aplicado en Ventana 1.")
