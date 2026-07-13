"""
core/playlist_manager.py
--------------------------------------------------------
Motor de Publicidad (Ventana 1), Explorador (Ventana 3) y el
Scheduler automático. El motor de Emisión (Ventana 2 / Auxiliar) vive
aparte, en core/gestor_emision.py (GestorPlaylist) — separación a
propósito para que la futura programación automática de Emisión se
pueda extender sin tocar este archivo.

Reglas de negocio implementadas acá (a pedido explícito):
- Doble click sobre un ítem de Publicidad:
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

- GestorPublicidad: para la Ventana 1 (árbol jerárquico de
  bloques). Además de la reproducción manual, sabe "disparar" un
  bloque completo y avisar cuándo termina (disparar_bloque) — lo
  usa SchedulerAutomatico para el modo AUTOMÁTICO real.
- SchedulerAutomatico: dispara los bloques de Publicidad por
  horario cuando el modo AUTOMÁTICO está activo, pausando/
  reanudando Emisión de forma transparente durante cada bloque, y
  carga sola a medianoche la programación resuelta del día (si hay
  alguna guardada desde el Programador). Ver clase más abajo.
- GestorExplorador: preescucha (Play/Stop) del archivo seleccionado
  en la Ventana 3.
--------------------------------------------------------
"""

from datetime import date

from PySide6.QtCore import Qt, QTimer, QTime, QDate

from core.audio_engine import MotorAudio
from config.settings import (
    cargar_playlist_publicidad, guardar_playlist_publicidad, registrar_error, registrar_evento,
)

DEBOUNCE_GUARDADO_PUBLICIDAD_MS = 500


class GestorPublicidad:
    """Reproductor para la Ventana 1: máquina de estados "en punta"
    (rojo)/"en cola" (verde) igual que Ventana 2 — doble click/Enter
    en silencio ARMA sin arrancar solo (Play dispara), con algo
    sonando encola sin interrumpir. Avanza en cascada por el árbol si
    un ítem falla, y aplica el recorte de silencio/nivelado ya
    calculado por core/analizador_audio.py (bug real corregido: antes
    solo se aplicaba en el "Previo" de Ventana 3).

    También sabe "disparar" un bloque COMPLETO y avisar cuándo
    termina (disparar_bloque/al_finalizar) — es lo que usa
    SchedulerAutomatico para el modo AUTOMÁTICO real: mientras hay
    un bloque disparado por horario en curso, el avance normal
    (_avanzar) NO cruza hacia el bloque siguiente del árbol, se
    detiene ahí y avisa. Una interacción manual (doble click, Stop)
    durante un bloque automático lo da por terminado igual, para no
    dejar Emisión pausada para siempre si el operador toma control.

    Persistencia (persistir=True): la lista de bloques sobrevive a un
    cierre/corte de luz, mismo tratamiento que Ventana 2
    (config/data/playlist_publicidad.json, escritura atómica,
    debounce). Al restaurar, el ítem armado/en cola vuelve a marcarse
    pero SIN sonar solo.
    """

    def __init__(
        self,
        ventana_publicidad,
        id_dispositivo: str = None,
        avanzar_en_error: bool = True,
        reintentos_maximos: int = 3,
        persistir: bool = False,
    ):
        self.ventana = ventana_publicidad
        self.motor = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self.persistir = persistir
        self._fallos_consecutivos = 0
        self._volumen_base = 100
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None
        self._restaurando = False

        self.motor.posicion_cambiada.connect(self.ventana.actualizar_contadores)
        self.motor.posicion_cambiada.connect(self._actualizar_indicador)
        self.motor.error_reproduccion.connect(self._on_error)
        self.motor.restante_ms_cambio.connect(self._actualizar_progreso)

        self.ventana.solicitud_play.connect(self._reproducir_seleccion_o_actual)
        self.ventana.solicitud_pausa.connect(self._pausar)
        self.ventana.solicitud_stop.connect(self._detener)
        self.ventana.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        self.ventana.item_doble_click.connect(self._on_doble_click)
        self.ventana.solicitud_buscar_posicion.connect(self._buscar_posicion)

        if self.persistir:
            self._timer_guardado = QTimer()
            self._timer_guardado.setSingleShot(True)
            self._timer_guardado.timeout.connect(self._guardar_estado_ahora)
            self._conectar_persistencia()
            self._restaurar_desde_disco()

    # ------------------------------------------------------------------
    def set_volumen_base(self, volumen: int):
        self._volumen_base = volumen
        self.motor.set_volumen(volumen)

    def _pausar(self):
        registrar_evento("Publicidad: Pausa")
        self.motor.pausar()
        self._actualizar_indicador()

    def _actualizar_indicador(self, *_args):
        self.ventana.set_indicador_en_vivo(self.motor.esta_reproduciendo())

    def _actualizar_progreso(self, restante_ms: int):
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        transcurrido_ms = max(0, total_ms - restante_ms)
        permille = int(1000 * transcurrido_ms / total_ms)
        self.ventana.actualizar_progreso(max(0, min(1000, permille)))

    def _buscar_posicion(self, permille: int):
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        self.motor.buscar_posicion_ms(int(total_ms * permille / 1000))

    def _detener(self):
        registrar_evento("Publicidad: Stop")
        self.motor.detener()
        self._fallos_consecutivos = 0
        self.ventana.set_indicador_en_vivo(False)
        if self._bloque_automatico_actual is not None:
            self._finalizar_bloque_automatico()

    def _item_valido(self, item) -> bool:
        return item is not None and bool(item.data(0, Qt.ItemDataRole.UserRole))

    def _reproducir_item(self, item):
        if not self._item_valido(item):
            return
        self.ventana.tree.setCurrentItem(item)
        self.ventana.marcar_reproduciendo_item(item)

        # Bug real corregido: antes se llamaba motor.reproducir(ruta)
        # sin el recorte de silencio ni el nivelado ya calculados —
        # ahora se leen del propio ítem (ROL_ANALISIS_AUDIO) y se
        # pasan igual que ya hacía GestorExplorador/GestorPlaylist.
        analisis = self.ventana.analisis_de_item(item)
        ruta = item.data(0, Qt.ItemDataRole.UserRole)
        self.motor.reproducir(
            ruta,
            punto_inicio_ms=analisis.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis.get("punto_fin_ms"),
            ganancia_db=analisis.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
        )
        self.ventana.set_indicador_en_vivo(True)
        registrar_evento(f"Publicidad: reproduciendo '{item.text(0)}'")

    def _reproducir_seleccion_o_actual(self):
        # Prioridad: si ya hay algo marcado como "en reproducción"
        # (armado en rojo), reanuda/dispara ese; si no, usa la
        # selección del árbol; si tampoco hay selección, arranca por
        # el primer ítem reproducible.
        item = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem() \
            or self.ventana.primer_item_reproducible()
        registrar_evento(f"Publicidad: Play (ítem objetivo: {item.text(0) if item else 'ninguno'})")
        self._reproducir_item(item)

    # ------------------------------------------------------------------
    # Modo AUTOMÁTICO: disparar un bloque completo por horario
    # ------------------------------------------------------------------
    def disparar_bloque(self, item_bloque, al_finalizar=None):
        """Arranca el primer ítem reproducible del bloque. Cuando el
        bloque se termina (último ítem, error irrecuperable, o el
        operador toma control manualmente), se llama a `al_finalizar`
        una única vez — SchedulerAutomatico la usa para reanudar
        Emisión."""
        registrar_evento(f"Publicidad: disparando bloque automático '{item_bloque.text(0)}'")
        self._fallos_consecutivos = 0
        self._bloque_automatico_actual = item_bloque
        self._callback_bloque_finalizado = al_finalizar

        primero = None
        for i in range(item_bloque.childCount()):
            candidato = item_bloque.child(i)
            if self._item_valido(candidato):
                primero = candidato
                break

        if primero is None:
            self._finalizar_bloque_automatico()
            return

        self._reproducir_item(primero)

    def _finalizar_bloque_automatico(self):
        registrar_evento("Publicidad: bloque automático finalizado")
        self.motor.detener()
        self.ventana.set_indicador_en_vivo(False)
        callback = self._callback_bloque_finalizado
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None
        self.ventana.marcar_reproduciendo_item(None)
        if callback:
            callback()

    # ------------------------------------------------------------------
    # Selección manual por doble click / Enter (arma en punta / encola)
    # — mismo comportamiento que GestorPlaylist en core/gestor_emision.py.
    # ------------------------------------------------------------------
    def _on_doble_click(self, item):
        if not self._item_valido(item):
            return  # nodo de bloque (sin ruta), no es reproducible
        if self._bloque_automatico_actual is not None:
            # El operador toma control manual: se da por terminado el
            # bloque automático (y se reanuda Emisión) en vez de
            # quedar "colgado" esperando un final que no va a llegar.
            self._finalizar_bloque_automatico()

        if self.motor.esta_reproduciendo():
            self.ventana.marcar_siguiente_item(item)
            registrar_evento(f"Publicidad: '{item.text(0)}' marcado en cola (verde)")
        else:
            self._fallos_consecutivos = 0
            self.ventana.marcar_reproduciendo_item(item)
            registrar_evento(f"Publicidad: '{item.text(0)}' armado en punta (rojo)")

    # ------------------------------------------------------------------
    def _avanzar_al_siguiente(self):
        registrar_evento("Publicidad: Siguiente")
        self._fallos_consecutivos = 0
        self._avanzar()

    def _on_error(self, mensaje: str):
        registrar_error(f"[Publicidad] {mensaje}")
        if not self.avanzar_en_error:
            if self._bloque_automatico_actual is not None:
                self._finalizar_bloque_automatico()
            return
        self._fallos_consecutivos += 1
        if self._fallos_consecutivos >= self.reintentos_maximos:
            self.motor.detener()
            self._fallos_consecutivos = 0
            if self._bloque_automatico_actual is not None:
                self._finalizar_bloque_automatico()
            return
        self._avanzar()

    def _avanzar(self):
        # Prioridad: si hay un ítem marcado "en cola" (verde) válido,
        # es ese — el operador ya eligió qué sigue.
        candidato = self.ventana.item_siguiente()
        if candidato is None or not self._item_valido(candidato):
            item_base = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem()
            if item_base is None:
                item_base = self.ventana.primer_item_reproducible()
                self._reproducir_item(item_base)
                return

            candidato = self.ventana.tree.itemBelow(item_base)
            while candidato is not None and not self._item_valido(candidato):
                candidato = self.ventana.tree.itemBelow(candidato)

        if self._bloque_automatico_actual is not None:
            # No cruzar hacia el bloque siguiente del árbol: si ya no
            # queda ningún ítem reproducible DENTRO de este bloque, se
            # terminó (avisa a SchedulerAutomatico para que reanude
            # Emisión), no sigue tocando el próximo bloque horario.
            if candidato is None or candidato.parent() is not self._bloque_automatico_actual:
                self._finalizar_bloque_automatico()
                return

        if candidato is None:
            self.motor.detener()
            return

        self._reproducir_item(candidato)

        # Marca automáticamente el siguiente ítem reproducible como
        # "en cola" (verde) — mismo comportamiento que Ventana 2 al
        # avanzar naturalmente (no en un Play manual sobre el ítem ya
        # armado), da una vista previa continua de qué sigue.
        siguiente_candidato = self.ventana.tree.itemBelow(candidato)
        while siguiente_candidato is not None and not self._item_valido(siguiente_candidato):
            siguiente_candidato = self.ventana.tree.itemBelow(siguiente_candidato)
        self.ventana.marcar_siguiente_item(siguiente_candidato)

    # ------------------------------------------------------------------
    # Persistencia (solo si persistir=True). Escucha el modelo interno
    # del árbol para detectar CUALQUIER mutación (alta, baja, marcado)
    # desde un único lugar — mismo patrón que core/gestor_emision.py.
    # ------------------------------------------------------------------
    def _conectar_persistencia(self):
        modelo = self.ventana.tree.model()
        modelo.rowsInserted.connect(self._guardar_estado_diferido)
        modelo.rowsRemoved.connect(self._guardar_estado_diferido)
        modelo.rowsMoved.connect(self._guardar_estado_diferido)
        modelo.dataChanged.connect(self._guardar_estado_diferido)

    def _guardar_estado_diferido(self, *_args):
        if self._restaurando:
            return
        self._timer_guardado.start(DEBOUNCE_GUARDADO_PUBLICIDAD_MS)

    def _indice_de_item(self, item):
        if item is None or item.parent() is None:
            return None
        bloque = item.parent()
        indice_bloque = self.ventana.tree.indexOfTopLevelItem(bloque)
        indice_tanda = bloque.indexOfChild(item)
        if indice_bloque < 0 or indice_tanda < 0:
            return None
        return [indice_bloque, indice_tanda]

    def _item_en_indice(self, indice):
        if not indice or len(indice) != 2:
            return None
        indice_bloque, indice_tanda = indice
        bloque = self.ventana.tree.topLevelItem(indice_bloque)
        if bloque is None:
            return None
        return bloque.child(indice_tanda)

    def _guardar_estado_ahora(self):
        bloques = []
        for i in range(self.ventana.tree.topLevelItemCount()):
            nodo_bloque = self.ventana.tree.topLevelItem(i)
            hora = self.ventana.hora_de_bloque(nodo_bloque)
            texto_completo = nodo_bloque.text(0)
            prefijo = f"{hora} - "
            titulo = texto_completo[len(prefijo):] if texto_completo.startswith(prefijo) else texto_completo

            items = []
            for j in range(nodo_bloque.childCount()):
                hijo = nodo_bloque.child(j)
                analisis = self.ventana.analisis_de_item(hijo)
                items.append({
                    "titulo": hijo.text(0), "duracion": hijo.text(1), "codigo": hijo.text(2),
                    "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
                    "punto_inicio_ms": analisis.get("punto_inicio_ms") or 0,
                    "punto_fin_ms": analisis.get("punto_fin_ms"),
                    "ganancia_db": analisis.get("ganancia_db") or 0.0,
                })
            bloques.append({"hora": hora, "titulo": titulo, "items": items})

        guardar_playlist_publicidad({
            "bloques": bloques,
            "indice_armado": self._indice_de_item(self.ventana.item_reproduciendo()),
            "indice_siguiente": self._indice_de_item(self.ventana.item_siguiente()),
        })

    def _restaurar_desde_disco(self):
        self._restaurando = True
        try:
            datos = cargar_playlist_publicidad()
            bloques = datos.get("bloques", [])
            if bloques:
                self.ventana.cargar_bloques(bloques)

            indice_armado = datos.get("indice_armado")
            item_armado = self._item_en_indice(indice_armado)
            if item_armado is not None:
                # Restaura el marcado "en punta" (rojo) SIN reproducir
                # nada solo — igual que Ventana 2.
                self.ventana.marcar_reproduciendo_item(item_armado)

            indice_siguiente = datos.get("indice_siguiente")
            item_siguiente = self._item_en_indice(indice_siguiente)
            if item_siguiente is not None and item_siguiente is not item_armado:
                self.ventana.marcar_siguiente_item(item_siguiente)

            if bloques:
                registrar_evento(f"Playlist de Publicidad restaurada: {len(bloques)} bloque(s)")
        except Exception as error:
            registrar_error(f"Error restaurando playlist de Publicidad: {error}")
        finally:
            self._restaurando = False


class SchedulerAutomatico:
    """Dispara los bloques de Publicidad por horario cuando el modo
    AUTOMÁTICO (Ventana 1) está activo, pausando/reanudando Emisión
    (Ventana 2) de forma transparente durante cada bloque. También
    carga sola, al cambiar el día (medianoche), la programación
    resuelta para hoy (fecha específica > patrón semanal — ver
    config/settings.py:resolver_programacion_del_dia), si hay alguna
    guardada desde el Programador.

    Un QTimer chequea cada segundo. Al activar el modo AUTOMÁTICO (o
    si ya arranca activado), los bloques cuya hora ya pasó se marcan
    como "ya emitidos hoy" SIN dispararlos — activar el modo a mitad
    de la tarde no debe hacer sonar de golpe todo lo que ya pasó.
    """

    INTERVALO_MS = 1000

    def __init__(self, ventana_publicidad, gestor_publicidad, gestor_emision):
        self.ventana = ventana_publicidad
        self.gestor_publicidad = gestor_publicidad
        self.gestor_emision = gestor_emision

        self._dia_actual = QDate.currentDate()
        self._horas_disparadas_hoy = set()
        self._emision_estaba_sonando = False

        self.ventana.automatico_cambiado.connect(self._on_automatico_cambiado)

        self._timer = QTimer()
        self._timer.setInterval(self.INTERVALO_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        if self.ventana.esta_en_automatico():
            self._marcar_bloques_pasados_sin_disparar()

        # Pedido explícito: al iniciar el programa, lo primero que
        # hace es buscar si hay programación guardada para HOY
        # (fecha específica > día genérico) y cargarla sola, sin
        # preguntar — igual que ya hacía a medianoche. Esto pisa lo
        # que GestorPublicidad haya restaurado de la sesión anterior
        # (playlist_publicidad.json) SOLO si hay algo programado para
        # hoy; si no hay nada guardado, no toca lo restaurado.
        self._cargar_programacion_del_dia()

    def detener(self):
        self._timer.stop()

    # ------------------------------------------------------------------
    def _on_automatico_cambiado(self, activo: bool):
        if activo:
            self._marcar_bloques_pasados_sin_disparar()

    def _marcar_bloques_pasados_sin_disparar(self):
        ahora = QTime.currentTime()
        marcadas = set()
        for bloque in self.ventana.bloques():
            hora_str = self.ventana.hora_de_bloque(bloque)
            hora_bloque = QTime.fromString(hora_str, "HH:mm:ss") if hora_str else QTime()
            if hora_bloque.isValid() and hora_bloque <= ahora:
                marcadas.add(hora_str)
        self._horas_disparadas_hoy = marcadas

    # ------------------------------------------------------------------
    def _tick(self):
        hoy = QDate.currentDate()
        if hoy != self._dia_actual:
            self._dia_actual = hoy
            self._horas_disparadas_hoy = set()
            self._cargar_programacion_del_dia()

        if not self.ventana.esta_en_automatico():
            return

        ahora = QTime.currentTime()
        for bloque in self.ventana.bloques():
            hora_str = self.ventana.hora_de_bloque(bloque)
            if not hora_str or hora_str in self._horas_disparadas_hoy:
                continue
            hora_bloque = QTime.fromString(hora_str, "HH:mm:ss")
            if hora_bloque.isValid() and ahora >= hora_bloque:
                self._horas_disparadas_hoy.add(hora_str)
                self._disparar_bloque(bloque)
                break  # un bloque por chequeo alcanza y sobra

    # ------------------------------------------------------------------
    def _disparar_bloque(self, bloque):
        self._emision_estaba_sonando = self.gestor_emision.motor.esta_reproduciendo()
        if self._emision_estaba_sonando:
            self.gestor_emision.motor.pausar()
        self.gestor_publicidad.disparar_bloque(bloque, al_finalizar=self._reanudar_emision)

    def _reanudar_emision(self):
        if self._emision_estaba_sonando and not self.gestor_emision.motor.esta_reproduciendo():
            self.gestor_emision.motor.pausar()  # pausar() alterna: reanuda lo que estaba pausado

    # ------------------------------------------------------------------
    def _cargar_programacion_del_dia(self):
        from config.settings import resolver_programacion_del_dia

        contenido = resolver_programacion_del_dia(date.today())
        if not contenido:
            return
        self.ventana.cargar_bloques(contenido.get("bloques", []))
        registrar_evento(f"Publicidad: programación de hoy cargada automáticamente ('{contenido.get('nombre', '')}')")


class GestorExplorador:
    """Preescucha (Play/Stop) del archivo seleccionado en la Ventana 3.
    Usa los puntos de recorte de silencio y la ganancia calculados
    por core/analizador_audio.py si el registro ya fue analizado.

    Indicador "en vivo" + barra de progreso: mismo patrón que
    GestorPlaylist (Ventana 2) — pedido explícito, para que se note a
    simple vista cuándo está sonando el previo (antes podía disparar
    sin querer arrastrando y no había forma de notarlo) y para poder
    adelantar/retroceder igual que en Emisión."""

    def __init__(self, ventana_explorador, id_dispositivo: str = None):
        self.ventana = ventana_explorador
        self.motor = MotorAudio(id_dispositivo)
        self.motor.error_reproduccion.connect(self._on_error)
        self.motor.posicion_cambiada.connect(self._actualizar_indicador)
        self.motor.restante_ms_cambio.connect(self._actualizar_progreso)
        self.motor.finalizo_item.connect(self._on_fin_preview)

        self.ventana.solicitud_play_preview.connect(self._reproducir_seleccion)
        self.ventana.solicitud_stop_preview.connect(self._detener)
        if hasattr(self.ventana, "solicitud_buscar_posicion_preview"):
            self.ventana.solicitud_buscar_posicion_preview.connect(self._buscar_posicion)

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
        self.ventana.set_indicador_en_vivo(True)

    def _detener(self):
        self.motor.detener()
        self.ventana.set_indicador_en_vivo(False)
        self.ventana.actualizar_progreso_preview(0)

    def _on_fin_preview(self):
        self.ventana.set_indicador_en_vivo(False)
        self.ventana.actualizar_progreso_preview(0)

    def _actualizar_indicador(self, *_args):
        self.ventana.set_indicador_en_vivo(self.motor.esta_reproduciendo())

    def _actualizar_progreso(self, restante_ms: int):
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        transcurrido_ms = max(0, total_ms - restante_ms)
        permille = int(1000 * transcurrido_ms / total_ms)
        self.ventana.actualizar_progreso_preview(max(0, min(1000, permille)))

    def _buscar_posicion(self, permille: int):
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        self.motor.buscar_posicion_ms(int(total_ms * permille / 1000))

    def _on_error(self, mensaje: str):
        print(f"[GestorExplorador] {mensaje}")
