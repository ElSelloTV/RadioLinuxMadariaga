"""
core/playlist_manager.py
--------------------------------------------------------
Conecta las señales de una ventana de la GUI (Play/Pausa/Stop/
Siguiente/doble-click) con un MotorAudio real, y traduce los
eventos del motor (posición, fin de reproducción, error) de
vuelta a la GUI.

Reglas de negocio implementadas acá (a pedido explícito):
- Doble click sobre un ítem:
    - Si el reproductor está DETENIDO -> ese ítem pasa a ser el
      que suena (rojo) y arranca a reproducirse inmediatamente.
    - Si el reproductor está REPRODUCIENDO algo -> ese ítem
      queda marcado como "siguiente" (verde), sin interrumpir lo
      que está sonando.
- Si un ítem falla al reproducirse (archivo corrupto, ruta
  inválida, etc.) el motor avanza automáticamente al siguiente,
  y así en cascada, hasta un máximo de `reintentos_maximos`
  fallos consecutivos (para no quedar en loop infinito si toda
  la lista está rota).
- El fin de lista respeta la configuración "repetir_lista_al_finalizar":
  si está activada, vuelve al ítem 0; si no, se detiene.

- GestorPlaylist: para paneles con cola propia indexada por fila
  (Ventana 2 - Emisión, y la Ventana Auxiliar).
- GestorPublicidad: para la Ventana 1 (árbol jerárquico de
  bloques). La cola automática disparada por horario (modo
  AUTOMÁTICO real) queda para una próxima iteración.
--------------------------------------------------------
"""

from PySide6.QtCore import Qt

from core.audio_engine import MotorAudio


class GestorPlaylist:
    """Bridge entre un panel tipo PanelReproductor (o VentanaEmision /
    VentanaAuxiliar, que delegan en él) y un MotorAudio real."""

    def __init__(
        self,
        panel,
        id_dispositivo: str = None,
        avanzar_en_error: bool = True,
        reintentos_maximos: int = 3,
        repetir_al_finalizar: bool = True,
    ):
        self.panel = panel
        self.motor = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self.repetir_al_finalizar = repetir_al_finalizar
        self._fallos_consecutivos = 0

        self.motor.posicion_cambiada.connect(self.panel.actualizar_contadores)
        self.motor.finalizo_item.connect(self._avanzar_al_siguiente)
        self.motor.error_reproduccion.connect(self._on_error)

        self.panel.solicitud_play.connect(self.reproducir_actual)
        self.panel.solicitud_pausa.connect(self.motor.pausar)
        self.panel.solicitud_stop.connect(self.detener)
        self.panel.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        self.panel.item_doble_click.connect(self._on_doble_click)

    # ------------------------------------------------------------------
    def reproducir_actual(self):
        fila = self.panel.fila_reproduciendo()
        if fila < 0 and self.panel.cantidad_items() > 0:
            fila = 0
            self.panel.marcar_reproduciendo(0)
        self._reproducir_fila(fila)

    def detener(self):
        self.motor.detener()
        self._fallos_consecutivos = 0

    def _reproducir_fila(self, fila: int):
        ruta = self.panel.ruta_en_fila(fila)
        if not ruta:
            return
        self.motor.reproducir(ruta)

    # ------------------------------------------------------------------
    # Selección manual por doble click (arranca detenido / encola en reproducción)
    # ------------------------------------------------------------------
    def _on_doble_click(self, fila: int):
        if self.motor.esta_reproduciendo():
            # Ya está sonando algo: el doble click solo elige qué
            # sigue después, sin interrumpir lo que está en el aire.
            self.panel.marcar_siguiente(fila)
        else:
            # Reproductor apagado: el usuario elige DESDE dónde arrancar.
            self._fallos_consecutivos = 0
            self.panel.marcar_reproduciendo(fila)
            self._reproducir_fila(fila)

    # ------------------------------------------------------------------
    # Avance normal (fin de tema / botón Siguiente) y avance forzado por error
    # ------------------------------------------------------------------
    def _avanzar_al_siguiente(self):
        self._fallos_consecutivos = 0
        self._avanzar(es_reintento=False)

    def _on_error(self, mensaje: str):
        print(f"[GestorPlaylist] {mensaje}")
        if not self.avanzar_en_error:
            return
        self._fallos_consecutivos += 1
        if self._fallos_consecutivos >= self.reintentos_maximos:
            self.motor.detener()
            self._fallos_consecutivos = 0
            return
        self._avanzar(es_reintento=True)

    def _avanzar(self, es_reintento: bool):
        total = self.panel.cantidad_items()
        if total == 0:
            return

        fila_actual = self.panel.fila_reproduciendo()
        fila_siguiente = self.panel.fila_siguiente()

        if fila_siguiente < 0 or fila_siguiente == fila_actual:
            fila_siguiente = fila_actual + 1

        if fila_siguiente >= total:
            if self.repetir_al_finalizar:
                fila_siguiente = 0
            else:
                self.motor.detener()
                return

        self.panel.marcar_reproduciendo(fila_siguiente)

        candidata_siguiente = fila_siguiente + 1
        if candidata_siguiente >= total:
            candidata_siguiente = 0 if self.repetir_al_finalizar else -1
        if candidata_siguiente >= 0:
            self.panel.marcar_siguiente(candidata_siguiente)

        self._reproducir_fila(fila_siguiente)


class GestorPublicidad:
    """Reproductor para la Ventana 1: soporta elegir manualmente el
    ítem de arranque (doble click) y avanza en cascada por el árbol
    si un ítem falla."""

    def __init__(
        self,
        ventana_publicidad,
        id_dispositivo: str = None,
        avanzar_en_error: bool = True,
        reintentos_maximos: int = 3,
    ):
        self.ventana = ventana_publicidad
        self.motor = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self._fallos_consecutivos = 0

        self.motor.posicion_cambiada.connect(self.ventana.actualizar_contadores)
        self.motor.error_reproduccion.connect(self._on_error)

        self.ventana.solicitud_play.connect(self._reproducir_seleccion_o_actual)
        self.ventana.solicitud_pausa.connect(self.motor.pausar)
        self.ventana.solicitud_stop.connect(self._detener)
        self.ventana.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        self.ventana.item_doble_click.connect(self._on_doble_click)

    # ------------------------------------------------------------------
    def _detener(self):
        self.motor.detener()
        self._fallos_consecutivos = 0

    def _item_valido(self, item) -> bool:
        return item is not None and bool(item.data(0, Qt.ItemDataRole.UserRole))

    def _reproducir_item(self, item):
        if not self._item_valido(item):
            return
        self.ventana.tree.setCurrentItem(item)
        self.ventana.marcar_reproduciendo_item(item)
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        self.motor.reproducir(ruta)

    def _reproducir_seleccion_o_actual(self):
        # Prioridad: si ya hay algo marcado como "en reproducción",
        # reanuda ese; si no, usa la selección del árbol; si tampoco
        # hay selección, arranca por el primer ítem reproducible.
        item = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem() \
            or self.ventana.primer_item_reproducible()
        self._reproducir_item(item)

    # ------------------------------------------------------------------
    def _on_doble_click(self, item):
        if not self._item_valido(item):
            return  # nodo de bloque (sin ruta), no es reproducible
        # En Publicidad, a diferencia de la Ventana 2, no hay cola con
        # "próximo" separado: doble click siempre define desde dónde
        # arranca (según pedido explícito, poder elegir el punto de inicio).
        self._fallos_consecutivos = 0
        self._reproducir_item(item)

    # ------------------------------------------------------------------
    def _avanzar_al_siguiente(self):
        self._fallos_consecutivos = 0
        self._avanzar()

    def _on_error(self, mensaje: str):
        print(f"[GestorPublicidad] {mensaje}")
        if not self.avanzar_en_error:
            return
        self._fallos_consecutivos += 1
        if self._fallos_consecutivos >= self.reintentos_maximos:
            self.motor.detener()
            self._fallos_consecutivos = 0
            return
        self._avanzar()

    def _avanzar(self):
        item_base = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem()
        if item_base is None:
            item_base = self.ventana.primer_item_reproducible()
            self._reproducir_item(item_base)
            return

        siguiente = self.ventana.tree.itemBelow(item_base)
        while siguiente is not None and not self._item_valido(siguiente):
            siguiente = self.ventana.tree.itemBelow(siguiente)

        if siguiente is None:
            self.motor.detener()
            return

        self._reproducir_item(siguiente)


class GestorExplorador:
    """Preescucha (Play/Stop) del archivo seleccionado en la Ventana 3.
    Usa los puntos de recorte de silencio y la ganancia calculados
    por core/analizador_audio.py si el registro ya fue analizado."""

    def __init__(self, ventana_explorador, id_dispositivo: str = None):
        self.ventana = ventana_explorador
        self.motor = MotorAudio(id_dispositivo)
        self.motor.error_reproduccion.connect(self._on_error)

        self.ventana.solicitud_play_preview.connect(self._reproducir_seleccion)
        self.ventana.solicitud_stop_preview.connect(self.motor.detener)

    def _reproducir_seleccion(self):
        registro = self.ventana.registro_seleccionado()
        if not registro or not registro.get("ruta"):
            return
        self.motor.reproducir(
            registro["ruta"],
            punto_inicio_ms=registro.get("punto_inicio_ms") or 0,
            punto_fin_ms=registro.get("punto_fin_ms"),
            ganancia_db=registro.get("ganancia_db") or 0.0,
        )

    def _on_error(self, mensaje: str):
        print(f"[GestorExplorador] {mensaje}")
