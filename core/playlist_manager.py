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
  (Ventana 2 - Emisión, y la Ventana Auxiliar). También maneja acá
  el motor "Agregar Pisador": ver más abajo.
- GestorPublicidad: para la Ventana 1 (árbol jerárquico de
  bloques). Además de la reproducción manual, sabe "disparar" un
  bloque completo y avisar cuándo termina (disparar_bloque) — lo
  usa SchedulerAutomatico para el modo AUTOMÁTICO real.
- SchedulerAutomatico: dispara los bloques de Publicidad por
  horario cuando el modo AUTOMÁTICO está activo, pausando/
  reanudando Emisión de forma transparente durante cada bloque, y
  carga sola a medianoche la programación resuelta del día (si hay
  alguna guardada desde el Programador). Ver clase más abajo.

Motor "Agregar Pisador" (Ventana 2 / Auxiliar)
-----------------------------------------------
Un tema musical puede tener anidado, tabulado debajo suyo en el
panel, un archivo de género "Pisador" (ver gui/panel_reproductor.py
- agregar_pisador). Cuando ese tema arranca a sonar:
  1. Se reproduce el Pisador en un segundo MotorAudio en paralelo
     (self.motor_pisador), superpuesto sobre el inicio del tema.
  2. El volumen del tema principal baja `bajada_db_pisador` dB
     (configurable, -4dB por defecto) mientras dura el Pisador.
  3. Al terminar el Pisador, el tema vuelve a su volumen original.
Si se avanza a otro tema (fin normal, Siguiente, error, doble
click) mientras el Pisador todavía está sonando, se corta y el
volumen se restaura antes de arrancar lo nuevo.

Crossfade (Ventana 2 / Auxiliar)
---------------------------------
Con `crossfade_activado` en Configuración → Fade/Transiciones, la
transición NATURAL entre dos temas (el actual llegando a su fin) se
superpone en vez de cortar seco: MotorAudio.crossfade_a() ya sabe
interpolar el volumen entre un motor saliente y uno entrante — acá
se dispara CON ANTICIPACIÓN (cuando falta `duracion_fade_segundos`
para el final, vía la señal restante_ms_cambio de MotorAudio, no
esperando a que termine) y luego self.motor pasa a ser el motor
entrante (se reconectan las señales). Solo aplica a la transición
"de fin de tema" — Siguiente manual, error y cascada siguen siendo
cortes directos. Si el tema entrante tiene su propio Pisador, no se
dispara (evita que dos rampas de volumen distintas peleen por el
mismo motor a la vez) — limitación conocida, documentada acá.
--------------------------------------------------------
"""

from datetime import date

from PySide6.QtCore import Qt, QTimer, QTime, QDate

from core.audio_engine import MotorAudio
from core.analizador_audio import volumen_ajustado_por_ganancia


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
        bajada_db_pisador: float = -4.0,
        crossfade_activado: bool = False,
        duracion_fade_segundos: float = 3.0,
    ):
        self.panel = panel
        self.motor = MotorAudio(id_dispositivo)
        self.motor_pisador = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self.repetir_al_finalizar = repetir_al_finalizar
        self.bajada_db_pisador = bajada_db_pisador
        self.crossfade_activado = crossfade_activado
        self.duracion_fade_segundos = duracion_fade_segundos
        self._fallos_consecutivos = 0
        self._volumen_base = 100
        self._pisador_activo = False
        self._crossfade_en_curso = False
        self._motor_saliente_crossfade = None

        self._conectar_motor(self.motor)

        self.motor_pisador.finalizo_item.connect(self._on_pisador_finalizado)
        self.motor_pisador.error_reproduccion.connect(
            lambda mensaje: print(f"[GestorPlaylist-Pisador] {mensaje}")
        )

        self.panel.solicitud_play.connect(self.reproducir_actual)
        self.panel.solicitud_pausa.connect(self._pausar)
        self.panel.solicitud_stop.connect(self.detener)
        self.panel.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        self.panel.item_doble_click.connect(self._on_doble_click)

    # ------------------------------------------------------------------
    def _conectar_motor(self, motor):
        motor.posicion_cambiada.connect(self.panel.actualizar_contadores)
        motor.finalizo_item.connect(self._avanzar_al_siguiente)
        motor.error_reproduccion.connect(self._on_error)
        motor.restante_ms_cambio.connect(self._chequear_crossfade)

    def _desconectar_motor(self, motor):
        try:
            motor.posicion_cambiada.disconnect(self.panel.actualizar_contadores)
            motor.finalizo_item.disconnect(self._avanzar_al_siguiente)
            motor.error_reproduccion.disconnect(self._on_error)
            motor.restante_ms_cambio.disconnect(self._chequear_crossfade)
        except (TypeError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    def set_volumen_base(self, volumen: int):
        """Volumen 0-100 "normal" del tema principal, al que se vuelve
        apenas termina un Pisador. Reemplaza a llamar motor.set_volumen()
        directo para que el Pisador sepa a qué nivel restaurar."""
        self._volumen_base = volumen
        if not self._pisador_activo:
            self.motor.set_volumen(volumen)

    def reproducir_actual(self):
        fila = self.panel.fila_reproduciendo()
        if fila < 0 and self.panel.cantidad_items() > 0:
            fila = 0
            self.panel.marcar_reproduciendo(0)
        self._reproducir_fila(fila)

    def _pausar(self):
        self.motor.pausar()
        if self._pisador_activo:
            self.motor_pisador.pausar()

    def detener(self):
        self.motor.detener()
        if self._motor_saliente_crossfade is not None:
            self._motor_saliente_crossfade.detener()
            self._motor_saliente_crossfade = None
        self._crossfade_en_curso = False
        self._cancelar_pisador_en_curso()
        self._fallos_consecutivos = 0

    def _reproducir_fila(self, fila: int):
        ruta = self.panel.ruta_en_fila(fila)
        if not ruta:
            return
        self._cancelar_pisador_en_curso()
        self.motor.reproducir(ruta)
        self._disparar_pisador_si_corresponde(fila)

    # ------------------------------------------------------------------
    # Crossfade: se dispara CON ANTICIPACIÓN (faltando duracion_fade_
    # segundos para terminar), no al final — ver nota al inicio del
    # archivo.
    # ------------------------------------------------------------------
    def _chequear_crossfade(self, restante_ms: int):
        if not self.crossfade_activado or self._crossfade_en_curso or self._pisador_activo:
            return
        duracion_ms = int(self.duracion_fade_segundos * 1000)
        if duracion_ms <= 0:
            return
        if 0 < restante_ms <= duracion_ms:
            self._iniciar_crossfade()

    def _iniciar_crossfade(self):
        total = self.panel.cantidad_items()
        if total == 0:
            return

        fila_actual = self.panel.fila_reproduciendo()
        fila_siguiente = self.panel.fila_siguiente()
        if fila_siguiente < 0 or fila_siguiente == fila_actual:
            fila_siguiente = fila_actual + 1
        if fila_siguiente >= total:
            fila_siguiente = 0 if self.repetir_al_finalizar else -1
        if fila_siguiente < 0:
            return

        ruta_siguiente = self.panel.ruta_en_fila(fila_siguiente)
        if not ruta_siguiente:
            return

        motor_saliente = self.motor
        entrante = motor_saliente.crossfade_a(ruta_siguiente, self.duracion_fade_segundos)
        if entrante is None:
            return

        self._crossfade_en_curso = True
        self._motor_saliente_crossfade = motor_saliente

        self._desconectar_motor(motor_saliente)
        self.motor = entrante
        self._conectar_motor(self.motor)

        self._fallos_consecutivos = 0
        self.panel.marcar_reproduciendo(fila_siguiente)
        candidata_siguiente = fila_siguiente + 1
        if candidata_siguiente >= total:
            candidata_siguiente = 0 if self.repetir_al_finalizar else -1
        if candidata_siguiente >= 0:
            self.panel.marcar_siguiente(candidata_siguiente)

        # El tema entrante no dispara su propio Pisador acá — ver
        # limitación documentada al inicio del archivo.

        QTimer.singleShot(int(self.duracion_fade_segundos * 1000) + 200, self._liberar_crossfade)

    def _liberar_crossfade(self):
        self._crossfade_en_curso = False
        self._motor_saliente_crossfade = None

    # ------------------------------------------------------------------
    # Motor "Agregar Pisador"
    # ------------------------------------------------------------------
    def _disparar_pisador_si_corresponde(self, fila: int):
        ruta_pisador = self.panel.ruta_pisador_en_fila(fila) if hasattr(self.panel, "ruta_pisador_en_fila") else ""
        if not ruta_pisador:
            return
        self._pisador_activo = True
        self.motor.set_volumen(volumen_ajustado_por_ganancia(self._volumen_base, self.bajada_db_pisador))
        self.motor_pisador.reproducir(ruta_pisador)

    def _on_pisador_finalizado(self):
        self._pisador_activo = False
        self.motor.set_volumen(self._volumen_base)

    def _cancelar_pisador_en_curso(self):
        if self._pisador_activo:
            self.motor_pisador.detener()
            self.motor.set_volumen(self._volumen_base)
            self._pisador_activo = False

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
    si un ítem falla.

    También sabe "disparar" un bloque COMPLETO y avisar cuándo
    termina (disparar_bloque/al_finalizar) — es lo que usa
    SchedulerAutomatico para el modo AUTOMÁTICO real: mientras hay
    un bloque disparado por horario en curso, el avance normal
    (_avanzar) NO cruza hacia el bloque siguiente del árbol, se
    detiene ahí y avisa. Una interacción manual (doble click, Stop)
    durante un bloque automático lo da por terminado igual, para no
    dejar Emisión pausada para siempre si el operador toma control.
    """

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
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None

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
        if self._bloque_automatico_actual is not None:
            self._finalizar_bloque_automatico()

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
    # Modo AUTOMÁTICO: disparar un bloque completo por horario
    # ------------------------------------------------------------------
    def disparar_bloque(self, item_bloque, al_finalizar=None):
        """Arranca el primer ítem reproducible del bloque. Cuando el
        bloque se termina (último ítem, error irrecuperable, o el
        operador toma control manualmente), se llama a `al_finalizar`
        una única vez — SchedulerAutomatico la usa para reanudar
        Emisión."""
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
        self.motor.detener()
        callback = self._callback_bloque_finalizado
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None
        self.ventana.marcar_reproduciendo_item(None)
        if callback:
            callback()

    # ------------------------------------------------------------------
    def _on_doble_click(self, item):
        if not self._item_valido(item):
            return  # nodo de bloque (sin ruta), no es reproducible
        if self._bloque_automatico_actual is not None:
            # El operador toma control manual: se da por terminado el
            # bloque automático (y se reanuda Emisión) en vez de
            # quedar "colgado" esperando un final que no va a llegar.
            self._finalizar_bloque_automatico()
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
        item_base = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem()
        if item_base is None:
            item_base = self.ventana.primer_item_reproducible()
            self._reproducir_item(item_base)
            return

        siguiente = self.ventana.tree.itemBelow(item_base)
        while siguiente is not None and not self._item_valido(siguiente):
            siguiente = self.ventana.tree.itemBelow(siguiente)

        if self._bloque_automatico_actual is not None:
            # No cruzar hacia el bloque siguiente del árbol: si ya no
            # queda ningún ítem reproducible DENTRO de este bloque, se
            # terminó (avisa a SchedulerAutomatico para que reanude
            # Emisión), no sigue tocando el próximo bloque horario.
            if siguiente is None or siguiente.parent() is not self._bloque_automatico_actual:
                self._finalizar_bloque_automatico()
                return

        if siguiente is None:
            self.motor.detener()
            return

        self._reproducir_item(siguiente)


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
