"""
core/gestor_emision.py
--------------------------------------------------------
TODO el motor de la Ventana 2 (Emisión) y de la Ventana Auxiliar vive
acá, en un único archivo — separado a propósito de
core/playlist_manager.py (que tiene Publicidad/Explorador/Scheduler).
Pedido explícito: cuando más adelante se implemente programación
automática (cargar ítems solos conforme una plantilla), esa función
nueva se agrega ACÁ, sin tener que tocar el resto del motor de la app.

Conecta las señales de un panel tipo PanelReproductor (o
VentanaEmision/VentanaAuxiliar, que delegan en él) con un MotorAudio
real, y traduce los eventos del motor (posición, fin de reproducción,
error) de vuelta a la GUI.

Reglas de negocio implementadas acá (a pedido explícito):
- Doble click (o Enter) sobre un ítem:
    - Si el reproductor está EN SILENCIO -> ese ítem se marca "en
      punta" (rojo), LISTO para arrancar, pero no arranca solo — recién
      suena cuando el operador aprieta Play (reproducir_actual usa el
      ítem ya marcado).
    - Si el reproductor está REPRODUCIENDO algo -> ese ítem
      queda marcado como "siguiente" (verde), sin interrumpir lo
      que está sonando.
- Los ítems marcados en rojo o verde no se pueden quitar de la lista
  (bloqueo en PanelReproductor.quitar_item) — se liberan solos al
  elegir otro ítem o al terminar su reproducción. El ítem rojo,
  además, no se puede mover por arrastre ni editar (Pisador) mientras
  está en esa posición (ver gui/common_widgets.py y
  gui/panel_reproductor.py).
- Si un ítem falla al reproducirse (archivo corrupto, ruta
  inválida, etc.) el motor avanza automáticamente al siguiente,
  y así en cascada, hasta un máximo de `reintentos_maximos`
  fallos consecutivos (para no quedar en loop infinito si toda
  la lista está rota).
- El fin de lista respeta la configuración "repetir_lista_al_finalizar":
  si está activada, vuelve al ítem 0; si no, se detiene.

Persistencia (pedido explícito: "se borra toda la música cuando se
cierra, corte de luz, etc.")
-----------------------------------------------------------------
La playlist de Ventana 2 (Emisión) ya NO es efímera: cada alta, baja,
reordenada o marcado se guarda en config/data/playlist_emision.json
(escritura atómica, mismo patrón que la biblioteca de Ventana 3) con
un debounce corto para no escribir en ráfaga durante un drag&drop. Al
reabrir la app, la lista se restaura tal cual quedó, incluido qué
ítem estaba armado/en cola — pero SIN arrancar a sonar solo: el
ítem "en punta" queda marcado en rojo esperando un Play manual, igual
que si el operador lo acabara de marcar a mano (nunca hay audio
saliendo al aire sin que alguien apriete Play). Solo aplica a Ventana
2 (persistir=True); la Auxiliar sigue siendo una lista de trabajo
efímera, a propósito.

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

from PySide6.QtCore import Qt, QTimer

from core.audio_engine import MotorAudio
from core.analizador_audio import volumen_ajustado_por_ganancia
from config.settings import cargar_playlist_emision, guardar_playlist_emision, registrar_error, registrar_evento

DURACION_FADE_PISADOR_SEGUNDOS = 0.8
DEBOUNCE_GUARDADO_MS = 500


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
        persistir: bool = False,
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
        self.persistir = persistir
        self._fallos_consecutivos = 0
        self._volumen_base = 100
        self._pisador_activo = False
        self._generacion_pisador = 0
        self._crossfade_en_curso = False
        self._motor_saliente_crossfade = None
        self._restaurando = False

        self._conectar_motor(self.motor)

        self.motor_pisador.finalizo_item.connect(self._on_pisador_finalizado)
        self.motor_pisador.error_reproduccion.connect(
            lambda mensaje: registrar_error(f"[Pisador] {mensaje}")
        )

        self.panel.solicitud_play.connect(self.reproducir_actual)
        self.panel.solicitud_pausa.connect(self._pausar)
        self.panel.solicitud_stop.connect(self.detener)
        self.panel.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        self.panel.item_doble_click.connect(self._on_doble_click)
        if hasattr(self.panel, "solicitud_buscar_posicion"):
            self.panel.solicitud_buscar_posicion.connect(self._buscar_posicion)

        if self.persistir:
            self._timer_guardado = QTimer()
            self._timer_guardado.setSingleShot(True)
            self._timer_guardado.timeout.connect(self._guardar_estado_ahora)
            self._conectar_persistencia()
            self._restaurar_desde_disco()

    # ------------------------------------------------------------------
    def _conectar_motor(self, motor):
        motor.posicion_cambiada.connect(self.panel.actualizar_contadores)
        motor.posicion_cambiada.connect(self._actualizar_indicador)
        motor.finalizo_item.connect(self._avanzar_al_siguiente)
        motor.error_reproduccion.connect(self._on_error)
        motor.restante_ms_cambio.connect(self._chequear_crossfade)
        motor.restante_ms_cambio.connect(self._actualizar_progreso)

    def _desconectar_motor(self, motor):
        try:
            motor.posicion_cambiada.disconnect(self.panel.actualizar_contadores)
            motor.posicion_cambiada.disconnect(self._actualizar_indicador)
            motor.finalizo_item.disconnect(self._avanzar_al_siguiente)
            motor.error_reproduccion.disconnect(self._on_error)
            motor.restante_ms_cambio.disconnect(self._chequear_crossfade)
            motor.restante_ms_cambio.disconnect(self._actualizar_progreso)
        except (TypeError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    # Indicador "en vivo" y barra de progreso (Ventana 2 solamente,
    # vía hasattr — Auxiliar no tiene solicitud_buscar_posicion).
    # ------------------------------------------------------------------
    def _actualizar_indicador(self, *_args):
        self.panel.set_indicador_en_vivo(self.motor.esta_reproduciendo())

    def _actualizar_progreso(self, restante_ms: int):
        if not hasattr(self.panel, "actualizar_progreso"):
            return
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        transcurrido_ms = max(0, total_ms - restante_ms)
        permille = int(1000 * transcurrido_ms / total_ms)
        self.panel.actualizar_progreso(max(0, min(1000, permille)))

    def _buscar_posicion(self, permille: int):
        total_ms = self.motor.duracion_total_ms()
        if total_ms <= 0:
            return
        self.motor.buscar_posicion_ms(int(total_ms * permille / 1000))

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
        registrar_evento(f"Play (Emisión persistir={self.persistir}) fila={fila}")
        self._reproducir_fila(fila)

    def _pausar(self):
        registrar_evento(f"Pausa (Emisión persistir={self.persistir})")
        self.motor.pausar()
        if self._pisador_activo:
            self.motor_pisador.pausar()
        self._actualizar_indicador()

    def detener(self):
        registrar_evento(f"Stop (Emisión persistir={self.persistir})")
        self.motor.detener()
        if self._motor_saliente_crossfade is not None:
            self._motor_saliente_crossfade.detener()
            self._motor_saliente_crossfade = None
        self._crossfade_en_curso = False
        self._cancelar_pisador_en_curso()
        self._fallos_consecutivos = 0
        self.panel.set_indicador_en_vivo(False)

    def _reproducir_fila(self, fila: int):
        ruta = self.panel.ruta_en_fila(fila)
        if not ruta:
            return
        self._cancelar_pisador_en_curso()
        # Bug real corregido: antes se llamaba motor.reproducir(ruta)
        # sin el recorte de silencio ni el nivelado ya calculados por
        # core/analizador_audio.py — solo el "Previo" de Ventana 3 los
        # aplicaba. Ahora se leen del propio ítem (ROL_ANALISIS_AUDIO,
        # ver gui/panel_reproductor.py) y se pasan igual que ya hacía
        # GestorExplorador.
        analisis = self.panel.analisis_en_fila(fila)
        self.motor.reproducir(
            ruta,
            punto_inicio_ms=analisis.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis.get("punto_fin_ms"),
            ganancia_db=analisis.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
        )
        self.panel.set_indicador_en_vivo(True)
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

        # Bug real corregido: el tema entrante del crossfade se
        # reproducía sin su recorte de silencio ni nivelado de
        # volumen — ver nota completa en MotorAudio.crossfade_a().
        analisis_siguiente = self.panel.analisis_en_fila(fila_siguiente)
        motor_saliente = self.motor
        entrante = motor_saliente.crossfade_a(
            ruta_siguiente, self.duracion_fade_segundos,
            punto_inicio_ms=analisis_siguiente.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis_siguiente.get("punto_fin_ms"),
            ganancia_db=analisis_siguiente.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
        )
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
    # Motor "Agregar Pisador": toda subida/bajada de volumen es un
    # fade suave (DURACION_FADE_PISADOR_SEGUNDOS), nunca un salto
    # brusco — pedido explícito.
    #
    # Bug real corregido — "a veces no se dispara": pasar de tema en
    # tema rápido (Siguiente varias veces seguidas, o una cascada de
    # errores) podía cancelar un Pisador, programar su detención
    # DIFERIDA (QTimer.singleShot, para dejarlo terminar el fade-out),
    # y ANTES de que ese timer disparara ya se había arrancado un
    # Pisador NUEVO en el mismo motor_pisador para el tema siguiente
    # — cuando el timer viejo finalmente se ejecutaba, cortaba el
    # Pisador nuevo (recién arrancado o ni siquiera arrancado del
    # todo), sin ningún error visible. `_generacion_pisador` es un
    # contador que se incrementa en cada cancelación/disparo nuevo; el
    # `detener()` diferido solo se ejecuta si la generación no cambió
    # mientras tanto (si cambió, significa que ya hay un Pisador más
    # nuevo en curso y no hay que tocarlo).
    # ------------------------------------------------------------------
    def _disparar_pisador_si_corresponde(self, fila: int):
        ruta_pisador = self.panel.ruta_pisador_en_fila(fila)
        if not ruta_pisador:
            return
        self._generacion_pisador += 1
        self._pisador_activo = True
        volumen_pisado = volumen_ajustado_por_ganancia(self._volumen_base, self.bajada_db_pisador)
        self.motor.fade_volumen_a(volumen_pisado, DURACION_FADE_PISADOR_SEGUNDOS)
        self.motor_pisador.reproducir(ruta_pisador)

    def _on_pisador_finalizado(self):
        self._pisador_activo = False
        self.motor.fade_volumen_a(self._volumen_base, DURACION_FADE_PISADOR_SEGUNDOS)

    def _cancelar_pisador_en_curso(self):
        if self._pisador_activo:
            self._generacion_pisador += 1
            generacion_al_cancelar = self._generacion_pisador
            self.motor_pisador.fade_volumen_a(0, DURACION_FADE_PISADOR_SEGUNDOS)
            QTimer.singleShot(
                int(DURACION_FADE_PISADOR_SEGUNDOS * 1000) + 100,
                lambda: self._detener_pisador_si_generacion_vigente(generacion_al_cancelar),
            )
            self.motor.fade_volumen_a(self._volumen_base, DURACION_FADE_PISADOR_SEGUNDOS)
            self._pisador_activo = False

    def _detener_pisador_si_generacion_vigente(self, generacion: int):
        if generacion == self._generacion_pisador:
            self.motor_pisador.detener()

    # ------------------------------------------------------------------
    # Selección manual por doble click / Enter (arma en punta / encola)
    # ------------------------------------------------------------------
    def _on_doble_click(self, fila: int):
        if self.motor.esta_reproduciendo():
            # Ya está sonando algo: el doble click solo elige qué
            # sigue después, sin interrumpir lo que está en el aire.
            self.panel.marcar_siguiente(fila)
        else:
            # Reproductor en silencio: el doble click (o Enter) solo
            # ARMA el ítem "en punta" (rojo) — pedido explícito, ya NO
            # arranca solo. Recién suena cuando el operador aprieta
            # Play (reproducir_actual usa el ítem ya marcado).
            self._fallos_consecutivos = 0
            self.panel.marcar_reproduciendo(fila)

    # ------------------------------------------------------------------
    # Avance normal (fin de tema / botón Siguiente) y avance forzado por error
    # ------------------------------------------------------------------
    def _avanzar_al_siguiente(self):
        self._fallos_consecutivos = 0
        self._avanzar(es_reintento=False)

    def _on_error(self, mensaje: str):
        registrar_error(f"[Emisión persistir={self.persistir}] {mensaje}")
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

    # ------------------------------------------------------------------
    # Persistencia (solo si persistir=True — Ventana 2, no Auxiliar).
    # Escucha el modelo interno del árbol para detectar CUALQUIER
    # mutación (alta, baja, reordenada por arrastre, marcado) desde un
    # único lugar, en vez de tener que llamar guardar() a mano desde
    # cada sitio de main_window.py que agrega/quita/reordena ítems.
    # ------------------------------------------------------------------
    def _conectar_persistencia(self):
        modelo = self.panel.tree.model()
        modelo.rowsInserted.connect(self._guardar_estado_diferido)
        modelo.rowsRemoved.connect(self._guardar_estado_diferido)
        modelo.rowsMoved.connect(self._guardar_estado_diferido)
        modelo.dataChanged.connect(self._guardar_estado_diferido)

    def _guardar_estado_diferido(self, *_args):
        if self._restaurando:
            return
        self._timer_guardado.start(DEBOUNCE_GUARDADO_MS)

    def _guardar_estado_ahora(self):
        items = []
        tree = self.panel.tree
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            analisis = self.panel.analisis_en_fila(i)
            registro = {
                "titulo": item.text(0),
                "duracion": item.text(1),
                "codigo": item.text(2),
                "ruta": item.data(0, Qt.ItemDataRole.UserRole) or "",
                "punto_inicio_ms": analisis.get("punto_inicio_ms") or 0,
                "punto_fin_ms": analisis.get("punto_fin_ms"),
                "ganancia_db": analisis.get("ganancia_db") or 0.0,
            }
            if item.childCount() > 0:
                hijo = item.child(0)
                registro["pisador"] = {
                    "titulo": hijo.text(0).removeprefix("↳ "),
                    "duracion": hijo.text(1),
                    "codigo": hijo.text(2),
                    "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
                }
            items.append(registro)

        guardar_playlist_emision({
            "items": items,
            "fila_armada": self.panel.fila_reproduciendo(),
            "fila_siguiente": self.panel.fila_siguiente(),
        })

    def _restaurar_desde_disco(self):
        self._restaurando = True
        try:
            datos = cargar_playlist_emision()
            for registro in datos.get("items", []):
                fila = self.panel.cantidad_items()
                self.panel.agregar_item(
                    registro.get("titulo", ""), registro.get("duracion", ""),
                    registro.get("codigo", ""), registro.get("ruta", ""),
                    registro.get("punto_inicio_ms") or 0, registro.get("punto_fin_ms"),
                    registro.get("ganancia_db") or 0.0,
                )
                pisador = registro.get("pisador")
                if pisador:
                    self.panel.agregar_pisador(
                        fila, pisador.get("titulo", ""), pisador.get("duracion", ""),
                        pisador.get("codigo", ""), pisador.get("ruta", ""),
                    )

            total = self.panel.cantidad_items()
            fila_armada = datos.get("fila_armada", -1)
            if 0 <= fila_armada < total:
                # Restaura el marcado "en punta" (rojo) SIN reproducir
                # nada solo — el audio nunca arranca sin que alguien
                # apriete Play, ni siquiera al reabrir la app.
                self.panel.marcar_reproduciendo(fila_armada)
            elif total > 0:
                # Pedido explícito (ciclo Automático, punto 2):
                # "predeterminadamente el rojo estará al comienzo, con
                # posibilidad de elegirlo manualmente" — si no había
                # nada armado, el primer ítem queda en punta por
                # defecto (sin sonar) para que la vuelta automática a
                # Emisión siempre tenga desde dónde arrancar.
                self.panel.marcar_reproduciendo(0)
            fila_siguiente = datos.get("fila_siguiente", -1)
            if 0 <= fila_siguiente < total and fila_siguiente != fila_armada:
                self.panel.marcar_siguiente(fila_siguiente)

            if total > 0:
                registrar_evento(f"Playlist de Emisión restaurada: {total} ítem(s)")
        except Exception as error:
            registrar_error(f"Error restaurando playlist de Emisión: {error}")
        finally:
            self._restaurando = False
