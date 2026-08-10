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
cortes directos.

Bug real corregido — "el Pisador no sonaba si la lista avanzaba
sola, sin apretar Siguiente": el tema ENTRANTE de un crossfade no
disparaba su propio Pisador (única función que lo hacía era
`_reproducir_fila()`, y la transición con crossfade NUNCA pasaba por
ahí) — esto era antes una "limitación conocida" documentada acá.
Primera corrección: disparar el Pisador recién en `_liberar_crossfade()`
(al terminar la rampa de volumen del crossfade, ~duracion_fade_segundos
después) para que no compitiera con esa rampa por el mismo motor —
PERO eso dejaba varios segundos sin NINGÚN sonido de Pisador,
indistinguible en la práctica de "no sonó" (reportado en pruebas
reales). Corrección definitiva: `_disparar_pisador_si_corresponde()`
ahora separa el AUDIO del Pisador (arranca siempre YA, apenas empieza
el crossfade — `motor_pisador.reproducir()` es independiente del
motor principal, nunca compite con nada) del DUCKING (bajar el
volumen del tema mientras suena, parámetro `aplicar_ducking`) — el
ducking sí se sigue difiriendo a `_liberar_crossfade()` para no pelear
con la rampa del crossfade, pero el Pisador YA se escucha desde el
primer instante sin importar eso. Prioridad explícita: que el Pisador
suene SIEMPRE es más importante que el ducking quede perfectamente
sincronizado.
--------------------------------------------------------
"""

import os

from PySide6.QtCore import Qt, QTimer

from core.audio_engine import MotorAudio
from core.analizador_audio import volumen_ajustado_por_ganancia
from core.musicalizador import generar_serie
from core.buscador_duplicados import duracion_a_segundos
from core.hth import resolver_comando_hth
from config.settings import (
    cargar_playlist_emision, guardar_playlist_emision, registrar_error, registrar_evento,
    guardar_ultimo_fmt, obtener_ultimo_fmt,
)

# Techo duro de ítems en un ciclo insertado por tiempo (pedido
# explícito: "agregar X cantidad de tiempo de programación aleatoria
# FMT") -- nunca se cuelga generando de más aunque el formato tenga
# ítems con duración desconocida (0s), que nunca harían avanzar el
# acumulado hacia el objetivo.
LIMITE_ITEMS_CICLO_POR_TIEMPO = 500

DURACION_FADE_PISADOR_SEGUNDOS = 0.8
# Pisador en el Outro (pedido explícito, paridad con Dinesat): cuánto
# antes del final del tema se dispara un Pisador de posición "final".
UMBRAL_DISPARO_PISADOR_OUTRO_MS = 3000
DEBOUNCE_GUARDADO_MS = 500
# Pedido explícito (paridad con Dinesat): el botón verde Play/Siguiente
# hace de "Siguiente con fundido" cuando ya hay algo sonando, y el
# botón Fade-Stop apaga con fundido en vez de corte seco. Duración
# corta a propósito — es una acción manual del operador, no debe
# demorar la transición varios segundos.
DURACION_FUNDIDO_MANUAL_SEGUNDOS = 1.2


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
        duracion_fade_segundos: float = 0.5,
        duracion_fade_in_segundos: float = 0.4,
        persistir: bool = False,
        ventana_explorador=None,
    ):
        self.panel = panel
        self.motor = MotorAudio(id_dispositivo)
        self.motor_pisador = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self.repetir_al_finalizar = repetir_al_finalizar
        self.bajada_db_pisador = bajada_db_pisador
        self.crossfade_activado = crossfade_activado
        # Duración del fade-OUT del saliente (y de cuánto antes del
        # final natural se dispara el crossfade, ver _chequear_crossfade).
        self.duracion_fade_segundos = duracion_fade_segundos
        # Duración del fade-IN del entrante (pedido explícito, ronda
        # posterior: "el inicio con un fundido muy breve de 400ms" —
        # reemplaza la decisión anterior de no hacer fade-in acá).
        self.duracion_fade_in_segundos = duracion_fade_in_segundos
        self.persistir = persistir
        # Musicalizador Avanzado (pedido explícito): necesita el
        # Explorador para resolver categorías/archivos al generar.
        # Sin él (ej. Auxiliar, que no recibe este parámetro), un
        # comando FMT simplemente no puede generar música — se avisa
        # en el log en vez de romper nada.
        self._ventana_explorador = ventana_explorador
        self._formato_musicalizador_activo = None
        self._fallos_consecutivos = 0
        self._volumen_base = 100
        self._pisador_activo = False
        self._generacion_pisador = 0
        # Pisador en el Outro: qué fila ya disparó su Pisador de
        # posición "final" en esta reproducción, para no re-chequear
        # en cada tick de restante_ms_cambio una vez disparado.
        self._fila_pisador_outro_disparado = -1
        self._crossfade_en_curso = False
        self._motor_saliente_crossfade = None
        self._restaurando = False
        # "Stop diferido" (Dinesat): armado, deja terminar el ítem
        # actual y recién ahí detiene TODO — no avanza al siguiente.
        self._stop_diferido_armado = False
        # "Ceder control" (pedido explícito, Ciclo Automático): armado
        # por SchedulerAutomatico (nunca por el operador) cuando llega
        # la hora de un bloque de Publicidad — deja terminar el ítem
        # actual y recién ahí DETIENE de verdad (nunca pausa) antes de
        # avisarle al Scheduler que ya puede arrancar el bloque. Ver
        # ceder_control_al_terminar_item().
        self._ceder_control_armado = False
        self._callback_ceder_control = None

        # Pedido explícito: Auxiliar y Emisión (o cualquier otro par
        # de ventanas que MainWindow decida coordinar) nunca deben
        # sonar a la vez — cada vez que ESTE gestor arranca a sonar
        # desde silencio (Play manual o reanudación automática), este
        # callback (si MainWindow lo conectó) corta a la otra ventana
        # con un fundido corto. Ninguna lógica de "cuál corta a cuál"
        # vive acá — GestorPlaylist no conoce a sus pares, solo avisa.
        self.al_arrancar_reproduccion = None

        # Pedido explícito ("estaría muy bueno que en EMISIÓN me
        # muestre el FMT en uso"): callback opcional, avisado con el
        # nombre del formato activo (o None si se desactivó) cada vez
        # que cambia -- MainWindow lo conecta a
        # VentanaEmision.establecer_sufijo_titulo(). GestorPlaylist no
        # conoce nada de Qt/GUI, solo avisa.
        self.al_cambiar_formato_activo = None

        # HORA/TEMPERATURA manual (pedido explícito, botón azul,
        # exclusivo de Ventana 2): "sin fade ni nada, PISANDO lo que
        # haya sonando" -- se corta el motor principal con detener()
        # de verdad (nunca pausar(), ver la regla ya establecida en
        # este archivo para handoffs que después vuelven "de cero") y
        # los clips se reproducen uno atrás de otro en un motor
        # DEDICADO, para no interferir con el estado de self.motor
        # mientras suenan. Al agotarse la cola, retoma la reproducción
        # normal desde el ítem armado (mismo camino que el botón
        # Play), no reanuda a mitad de canción. Callback opcional
        # (`al_fallar_hth_manual`) para avisar a la GUI si no había
        # nada para reproducir (falta un clip, o no hay datos de
        # clima) -- GestorPlaylist no muestra ningún diálogo por sí
        # solo.
        self.motor_anuncio_manual = MotorAudio(id_dispositivo)
        self.motor_anuncio_manual.finalizo_item.connect(self._on_fin_clip_anuncio_manual)
        self.motor_anuncio_manual.error_reproduccion.connect(
            lambda mensaje: registrar_error(f"[HTH manual] {mensaje}")
        )
        self._cola_anuncio_manual = []
        self._generacion_anuncio_manual = 0
        self._generacion_clip_actual_anuncio_manual = 0
        self.al_fallar_hth_manual = None

        self._conectar_motor(self.motor)

        self.motor_pisador.finalizo_item.connect(self._on_pisador_finalizado)
        self.motor_pisador.error_reproduccion.connect(
            lambda mensaje: registrar_error(f"[Pisador] {mensaje}")
        )

        # Pedido explícito (paridad con Dinesat): el botón verde es
        # Play SI está en silencio, o "Siguiente con fundido" si ya
        # hay algo sonando — las dos funciones en un solo botón.
        self.panel.solicitud_play.connect(self._on_click_play)
        self.panel.solicitud_pausa.connect(self._pausar)
        self.panel.solicitud_stop.connect(self.detener)
        # "Cut" (antes "Siguiente"): corte seco e inmediato al ítem en
        # cola — mismo comportamiento de siempre, solo cambió el
        # nombre/ícono en la UI para igualar Dinesat.
        self.panel.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        if hasattr(self.panel, "solicitud_fade_stop"):
            self.panel.solicitud_fade_stop.connect(self._fade_stop)
        if hasattr(self.panel, "solicitud_stop_diferido"):
            self.panel.solicitud_stop_diferido.connect(self._toggle_stop_diferido)
        self.panel.item_doble_click.connect(self._on_doble_click)
        if hasattr(self.panel, "solicitud_buscar_posicion"):
            self.panel.solicitud_buscar_posicion.connect(self._buscar_posicion)
        if hasattr(self.panel, "solicitud_hth_manual"):
            self.panel.solicitud_hth_manual.connect(self.reproducir_hth_manual)

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
        motor.restante_ms_cambio.connect(self._chequear_pisador_outro)

    def _desconectar_motor(self, motor):
        try:
            motor.posicion_cambiada.disconnect(self.panel.actualizar_contadores)
            motor.posicion_cambiada.disconnect(self._actualizar_indicador)
            motor.finalizo_item.disconnect(self._avanzar_al_siguiente)
            motor.error_reproduccion.disconnect(self._on_error)
            motor.restante_ms_cambio.disconnect(self._chequear_crossfade)
            motor.restante_ms_cambio.disconnect(self._actualizar_progreso)
            motor.restante_ms_cambio.disconnect(self._chequear_pisador_outro)
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

    def _resolver_candidata_verde(self, fila_base: int) -> int:
        """Calcula qué fila debería quedar en VERDE justo después de
        `fila_base` (la que acaba de quedar en rojo/reproduciendo) —
        centralizado para que `_asegurar_rojo_y_verde()`, `_avanzar()`,
        `_iniciar_crossfade()` y `_recalcular_verde_tras_nuevo_rojo()`
        compartan el mismo criterio, mismo espíritu que
        `_marcar_siguiente_con_refill()` (evita el bug ya documentado
        de caminos paralelos que se olvidan de aplicar la misma
        regla).

        Bug real corregido (pedido explícito: "SIEMPRE cuando se
        pinte de rojo el último item... cargue otro ciclo, así puede
        pintar de verde el siguiente"): las 4 llamadoras calculaban
        esto de forma casi idéntica, pero cuando el candidato quedaba
        fuera de rango (`fila_base` es el ÚLTIMO ítem disponible)
        siempre se resolvía primero contra "repetir lista al
        finalizar" (`True` por defecto) — como ese chequeo iba ANTES
        de mirar si había un formato FMT activo, un ciclo de FMT
        agotado nunca generaba nada nuevo: simplemente ENVOLVÍA de
        vuelta al ítem 0, repitiendo la MISMA serie vieja para
        siempre, en vez de generar contenido nuevo — exactamente la
        causa de "no carga otro ciclo". Corregido invirtiendo la
        prioridad: con un formato activo, SIEMPRE se intenta generar
        una serie nueva primero — "repetir al finalizar" solo aplica
        de verdad a una lista ESTÁTICA sin FMT (o como red de
        seguridad si el formato resultó estar roto y no generó
        nada)."""
        total = self.panel.cantidad_items()
        candidata = fila_base + 1
        if candidata >= total:
            generado = False
            if self._formato_musicalizador_activo is not None:
                self._generar_serie_musicalizador()
                total = self.panel.cantidad_items()
                generado = fila_base + 1 < total
            if generado:
                candidata = fila_base + 1
            else:
                candidata = 0 if self.repetir_al_finalizar else -1
        if candidata == fila_base:
            candidata = -1
        return candidata

    def _asegurar_rojo_y_verde(self):
        """Pedido explícito: "siempre tendrá uno cargado en rojo para
        reproducir, y el verde siempre. Si hay 1 solo item, entonces
        será ese en rojo. Sino no [verde]" — nunca deja un hueco donde
        exista un ítem armado (rojo) y un segundo ítem disponible sin
        marcar "en cola" (verde). No pisa un verde ya puesto por el
        operador."""
        total = self.panel.cantidad_items()
        if total == 0:
            return
        fila_roja = self.panel.fila_reproduciendo()
        if fila_roja < 0:
            fila_roja = 0
            self.panel.marcar_reproduciendo(0)
        if 0 <= self.panel.fila_siguiente() < total and self.panel.fila_siguiente() != fila_roja:
            return
        candidata = self._resolver_candidata_verde(fila_roja)
        if candidata >= 0:
            self._marcar_siguiente_con_refill(candidata)

    def reproducir_actual(self):
        # Si el operador aprieta Play mientras el anuncio manual de
        # HORA/TEMPERATURA todavía está sonando, cancela ESE anuncio
        # (motor dedicado + cola) antes de arrancar nada acá -- si no,
        # el ítem armado empezaría a sonar ENCIMA de los clips que
        # todavía están en curso. Si la cola ya estaba vacía (este
        # mismo llamado puede venir del propio anuncio, al terminar),
        # esto es un no-op.
        self._cancelar_anuncio_manual_en_curso()
        # Pedido explícito: arrancar a sonar desde silencio corta a la
        # ventana "hermana" (Auxiliar <-> Emisión) — ANTES de tocar
        # nada acá, para que el corte y el arranque queden lo más
        # superpuestos posible.
        if self.al_arrancar_reproduccion is not None:
            self.al_arrancar_reproduccion()
        self._activar_fmt_recordado_si_corresponde()
        fila = self.panel.fila_reproduciendo()
        if fila < 0 and self.panel.cantidad_items() > 0:
            fila = 0
            self.panel.marcar_reproduciendo(0)
        total = self.panel.cantidad_items()
        if total > 0:
            # Mismo criterio que _avanzar()/_iniciar_crossfade(): si el
            # ítem armado en rojo tiene el archivo faltante, Play no
            # debe intentarlo (ni siquiera de forma reactiva vía el
            # error de VLC) — saltea directo al próximo reproducible.
            fila_valida = self._resolver_siguiente_fila_valida(fila, total)
            if fila_valida < 0:
                self.motor.detener()
                self.panel.resetear_reproduccion()
                return
            if fila_valida != fila:
                fila = fila_valida
                self.panel.marcar_reproduciendo(fila)
        self._asegurar_rojo_y_verde()
        registrar_evento(f"Play (Emisión persistir={self.persistir}) fila={fila}")
        self._reproducir_fila(fila)

    def _activar_fmt_recordado_si_corresponde(self):
        """Pedido explícito: "cuando actives la ventana 2, siempre y
        siempre... vas a reproducir la serie del FMT en memoria" — la
        única excepción es que el operador ya haya agregado contenido
        a mano (arrastrando o agregando, ver
        `MainWindow._on_archivo_soltado_emision`, que llama a
        `detener_musicalizador()` apenas eso pasa). Si Emisión está
        VACÍA y no hay ya un formato activo, carga el último FMT
        recordado (memoria que sobrevive al día, no a la sesión — ver
        config/settings.py:obtener_ultimo_fmt)."""
        if self._formato_musicalizador_activo is not None:
            return
        if self.panel.cantidad_items() > 0:
            return  # ya hay contenido (manual o restaurado) — no lo pisa
        if self._ventana_explorador is None:
            return
        nombre = obtener_ultimo_fmt()
        if not nombre:
            return
        self.iniciar_musicalizador(nombre)

    def _on_click_play(self):
        """Botón verde grande (pedido explícito, paridad con Dinesat):
        "en realidad es Play pero además es siguiente en fundido...
        si no se está reproduciendo, pone en marcha el ítem elegido, y
        si lo vuelvo a apretar en ejecución, pasa al verde" — Play y
        Siguiente-con-fundido conviven en el mismo botón según el
        estado actual del motor."""
        if self.motor.esta_reproduciendo():
            self._avanzar_con_fundido()
        else:
            self.reproducir_actual()

    def _avanzar_con_fundido(self):
        """"Siguiente con fundido": SIEMPRE con fundido superpuesto,
        sin importar si `crossfade_activado` está apagado en
        Configuración — es una acción manual explícita del operador,
        no la transición automática de fin de tema. Reutiliza el
        mismo motor de crossfade ya existente, llamado directo (no vía
        `_chequear_crossfade`, que es quien aplica el gating de
        configuración/umbral)."""
        if self._crossfade_en_curso:
            return  # ya hay una transición en curso, no superponer otra
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()
        registrar_evento(f"Siguiente con fundido (Emisión persistir={self.persistir})")
        # Cancela el Pisador del tema SALIENTE antes de arrancar el
        # fundido — evita que su fade de ducking pelee con la propia
        # rampa del crossfade sobre el mismo motor (mismo criterio que
        # ya se usa en cualquier avance manual).
        self._cancelar_pisador_en_curso()
        self._iniciar_crossfade(duracion_segundos=DURACION_FUNDIDO_MANUAL_SEGUNDOS)

    def _pausar(self):
        self._cancelar_anuncio_manual_en_curso()
        registrar_evento(f"Pausa (Emisión persistir={self.persistir})")
        self.motor.pausar()
        if self._pisador_activo:
            self.motor_pisador.pausar()
        self._actualizar_indicador()

    def detener(self):
        self._cancelar_anuncio_manual_en_curso()
        registrar_evento(f"Stop (Emisión persistir={self.persistir})")
        self.motor.detener()
        if self._motor_saliente_crossfade is not None:
            self._motor_saliente_crossfade.detener()
            self._motor_saliente_crossfade = None
        self._crossfade_en_curso = False
        self._cancelar_pisador_en_curso()
        self._fallos_consecutivos = 0
        self.panel.set_indicador_en_vivo(False)
        # Pedido explícito: la barra de progreso no debe quedar
        # "pegada" en la posición donde se detuvo — Stop la reinicia.
        self.panel.resetear_reproduccion()
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()

    def _fade_stop(self):
        """Botón "Fade" (Dinesat): fundido hasta apagar el ítem en
        reproducción — distinto del Stop (corte seco) y del Stop
        diferido (dejar terminar y recién ahí frenar)."""
        if not self.motor.esta_reproduciendo():
            self.detener()
            return
        registrar_evento(f"Fade-Stop (Emisión persistir={self.persistir})")
        self._cancelar_pisador_en_curso()
        self.motor.fade_volumen_a(0, DURACION_FUNDIDO_MANUAL_SEGUNDOS)
        QTimer.singleShot(int(DURACION_FUNDIDO_MANUAL_SEGUNDOS * 1000) + 150, self.detener)

    def _toggle_stop_diferido(self):
        """Botón "Stop diferido" (Dinesat): deja terminar el ítem en
        reproducción y recién ahí detiene TODO (no avanza al
        siguiente) — un segundo click lo desarma. `panel.
        set_stop_diferido_armado()` refleja el estado en la UI (mismo
        patrón que el resto de los botones con estado)."""
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()
            return
        self._stop_diferido_armado = True
        if hasattr(self.panel, "set_stop_diferido_armado"):
            self.panel.set_stop_diferido_armado(True)
        registrar_evento(f"Stop diferido: armado (Emisión persistir={self.persistir})")

    def _cancelar_stop_diferido(self):
        self._stop_diferido_armado = False
        if hasattr(self.panel, "set_stop_diferido_armado"):
            self.panel.set_stop_diferido_armado(False)
        registrar_evento(f"Stop diferido: desarmado (Emisión persistir={self.persistir})")

    # ------------------------------------------------------------------
    # Botón azul "HORA/TEMP" (pedido explícito, exclusivo de Ventana 2):
    # reproduce el Comando HTH de HORA + el de TEMPERATURA, uno atrás
    # del otro, cortando LIMPIO (sin fundido) lo que estuviera sonando.
    #
    # A diferencia del Comando HTH real de Ventana 1 (que concatena sus
    # clips sobre el MISMO motor que conduce esa lista, ver
    # core/playlist_manager.py:_reproducir_comando_hth), acá el motor
    # principal (self.motor) NO se toca mientras suena el anuncio: se
    # corta con detener() de verdad (nunca pausar() — misma regla ya
    # establecida en este archivo para cualquier handoff que después
    # tiene que "volver limpio") y los clips se reproducen en un motor
    # DEDICADO (self.motor_anuncio_manual). Al agotarse la cola, se
    # retoma la reproducción normal desde el ítem armado (mismo camino
    # que el botón Play) — el ítem interrumpido arranca de nuevo desde
    # el principio, nunca "a mitad de canción" (pedido explícito no
    # cubre qué pasa después; se optó por reusar el camino de Play ya
    # probado en vez de inventar un mecanismo nuevo de pausa/resume,
    # con todo el riesgo de estados intermedios que eso implica).
    # ------------------------------------------------------------------
    def reproducir_hth_manual(self):
        if self._ventana_explorador is None:
            registrar_error("HTH manual: no hay acceso al Explorador, no se puede resolver la hora/temperatura.")
            self._avisar_fallo_hth_manual("No se pudo acceder a la biblioteca del Explorador.")
            return

        clips = []
        for parametro in ("HORA", "TEMPERATURA"):
            resueltos = resolver_comando_hth(self._ventana_explorador, parametro)
            if resueltos:
                clips.extend(resueltos)

        if not clips:
            registrar_error(
                "HTH manual: faltan los clips de voz de HORA/TEMPERATURA, o no hay datos "
                "de clima disponibles -- no se reprodujo nada."
            )
            self._avisar_fallo_hth_manual(
                "Faltan los clips de voz de HORA/TEMPERATURA, o no hay datos de clima "
                "disponibles todavía -- no se reprodujo nada."
            )
            return

        self._generacion_anuncio_manual += 1
        generacion = self._generacion_anuncio_manual
        registrar_evento(
            f"HTH manual: reproduciendo {len(clips)} clip(s), cortando lo que estuviera "
            f"sonando (Emisión persistir={self.persistir})"
        )
        # Corte limpio e INMEDIATO, sin fundido -- pedido explícito
        # ("Debe salir limpia, sin fade ni nada. PISANDO lo que haya
        # sonando").
        self.motor.detener()
        self._cola_anuncio_manual = list(clips)
        self._reproducir_siguiente_clip_anuncio_manual(generacion)

    def _avisar_fallo_hth_manual(self, mensaje: str):
        if self.al_fallar_hth_manual is not None:
            self.al_fallar_hth_manual(mensaje)

    def _cancelar_anuncio_manual_en_curso(self):
        """Aborta la cola/motor del anuncio manual si había uno en
        curso -- llamado desde cualquier otro punto que tome control
        real de la reproducción mientras tanto (Stop, Pausa, Play, Cut,
        crossfade) para que ni el audio del anuncio siga sonando de
        fondo ni su "resume" diferido pise lo que se está por hacer."""
        if self._cola_anuncio_manual:
            self._cola_anuncio_manual = []
            self._generacion_anuncio_manual += 1
            self.motor_anuncio_manual.detener()

    def _reproducir_siguiente_clip_anuncio_manual(self, generacion: int):
        if generacion != self._generacion_anuncio_manual:
            return  # se disparó otro anuncio manual más nuevo, o algo lo canceló
        if not self._cola_anuncio_manual:
            # Terminó el anuncio -- retoma la reproducción normal.
            self.reproducir_actual()
            return
        ruta = self._cola_anuncio_manual.pop(0)
        # Mismo patrón que el Comando HTH real de Ventana 1 (bug real
        # corregido ahí, ronda 44: "no quiero silencios al final...
        # deben ser enganchados") -- se busca el registro completo por
        # ruta para aplicar SU recorte de silencio/nivelado, así los
        # clips de voz concatenados (HORA XX + MINUTOS XX, etc.) no
        # dejan un hueco muerto entre uno y otro. Fail-open si el
        # registro no aparece (nunca romper el anuncio por esto).
        analisis = {}
        registro = self._ventana_explorador.buscar_registro_por_ruta(ruta)
        if registro:
            analisis = registro
        # Bug real evitado (mismo patrón que _generacion_pisador, ver
        # nota al inicio del archivo): `motor_anuncio_manual.finalizo_item`
        # es un slot SIN argumentos, disparado de forma asíncrona por
        # libVLC -- si ahí se releyera `self._generacion_anuncio_manual`
        # (el valor YA actualizado en ese instante) en vez del valor
        # vigente CUANDO SE DESPACHÓ este clip, la comparación de
        # generación de arriba sería un no-op inútil (siempre
        # "coincide consigo misma"), dejando pasar un clip abandonado
        # tras un Stop/Play/Cut de por medio. Se guarda acá, antes de
        # arrancar el clip, y `_on_fin_clip_anuncio_manual()` lee ESTE
        # valor capturado, no el corriente.
        self._generacion_clip_actual_anuncio_manual = generacion
        self.motor_anuncio_manual.reproducir(
            ruta,
            punto_inicio_ms=analisis.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis.get("punto_fin_ms"),
            ganancia_db=analisis.get("ganancia_db") or 0.0,
        )

    def _on_fin_clip_anuncio_manual(self):
        self._reproducir_siguiente_clip_anuncio_manual(self._generacion_clip_actual_anuncio_manual)

    def ceder_control_al_terminar_item(self, callback):
        """Pedido explícito (bug real reportado con audio real):
        "llegado el momento de reproducir el bloque horario de la
        ventana 1, deje terminar el ítem de la ventana 2... una vez
        que vaya a la ventana 1, el archivo y la reproducción de la
        ventana 2 debe liberarse". A diferencia del mecanismo VIEJO
        (fundido + PAUSA, resumible — la causa real del bug: al
        volver resonaba el tema viejo a mitad, y un Comando FMT nuevo
        no limpiaba esa pausa porque `esta_reproduciendo()` da False
        con el motor en pausa), esto NUNCA corta el ítem en curso: lo
        deja terminar solo, y RECIÉN AHÍ hace un `detener()` de
        verdad (nunca pausa) antes de avisar. Arma un "ceder" de una
        sola vez — mismo patrón que "Stop diferido", pero invisible
        al operador (lo arma el Scheduler, nunca el botón). Si no hay
        nada sonando ahora mismo, no hay nada que esperar: cede el
        control ya mismo."""
        if not self.motor.esta_reproduciendo():
            self.detener()
            callback()
            return
        self._ceder_control_armado = True
        self._callback_ceder_control = callback

    def _fila_valida(self, fila: int) -> bool:
        """Pedido explícito ("apliquemos en Ventana 2 el mismo
        criterio que la Ventana 1: si hay un ítem no vinculado, que no
        se detenga y pase al que sigue debajo"): mismo chequeo
        PROACTIVO (`os.path.exists`, antes de intentar reproducir) que
        ya usa `GestorPublicidad._item_valido()` — antes, Emisión solo
        reaccionaba REACTIVAMENTE al error de VLC vía `_on_error()`, y
        si varios ítems rotos caían seguidos, `reintentos_maximos`
        se agotaba y `_on_error()` cortaba TODO el aire. Marca/desmarca
        la X roja de error en el mismo momento en que se evalúa cada
        fila — igual que V1, sincronizado en vivo.

        Ronda posterior (mismo criterio, portado de V1 -- pedido
        explícito ahí: "si elimino ítem de la ventana 3, no debe
        reproducirse igual"): el archivo puede seguir existiendo en
        disco aunque el operador haya sacado su REGISTRO del
        Explorador — `os.path.exists()` solo no alcanza, también hace
        falta que la ruta siga en la biblioteca en vivo (cacheado, ver
        VentanaExplorador.ruta_existe_en_biblioteca())."""
        ruta = self.panel.ruta_en_fila(fila)
        if not ruta or not os.path.exists(ruta):
            self.panel.marcar_item_con_error_en_fila(fila, True)
            return False
        if self._ventana_explorador is not None and not self._ventana_explorador.ruta_existe_en_biblioteca(ruta):
            self.panel.marcar_item_con_error_en_fila(fila, True)
            return False
        self.panel.marcar_item_con_error_en_fila(fila, False)
        return True

    def _resolver_siguiente_fila_valida(self, fila_inicio: int, total: int) -> int:
        """Devuelve la próxima fila REPRODUCIBLE (archivo existente en
        disco) a partir de `fila_inicio`, aplicando la misma lógica de
        fin de lista que ya tenían `_avanzar()`/`_iniciar_crossfade()`
        (refill del Musicalizador si hay un formato activo, si no
        "repetir al finalizar", si no detenerse) — así un archivo sin
        vincular nunca corta el aire, se saltea como ya hace Ventana 1.
        Devuelve -1 si NINGÚN ítem de la lista es reproducible (todo
        roto) — ahí sí no queda nada para reproducir, ni V1 podría."""
        fila = fila_inicio
        # Tope defensivo (mismo espíritu que el resto del proyecto
        # ante libVLC: nunca confiar en una sola vuelta) — con una
        # lista totalmente rota y "repetir al finalizar" activo, sin
        # este tope el fin-de-lista podría rebotar indefinidamente
        # entre "envolver a 0" y "0 también está roto".
        limite = total + 2
        vueltas = 0
        while vueltas <= limite:
            if fila >= total:
                if self._formato_musicalizador_activo is not None:
                    self._generar_serie_musicalizador()
                    total = self.panel.cantidad_items()
                if fila >= total:
                    if self.repetir_al_finalizar:
                        fila = 0
                    else:
                        return -1
            if self._fila_valida(fila):
                return fila
            fila += 1
            vueltas += 1
        return -1

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
        # Bug real corregido ("el ícono de reproducido se marca al
        # seleccionar, no al reproducir"): acá es donde el audio arranca
        # de verdad — ver nota completa en gui/panel_reproductor.py:_pintar_item.
        self.panel.marcar_realmente_reproducido(fila)
        self.panel.set_indicador_en_vivo(True)
        self._fila_pisador_outro_disparado = -1
        # Un Pisador de posición "final" (Outro) NO se dispara acá —
        # se dispara más adelante, cerca del final, en
        # _chequear_pisador_outro().
        if self.panel.posicion_pisador_en_fila(fila) != "final":
            self._disparar_pisador_si_corresponde(fila)

    # ------------------------------------------------------------------
    # Crossfade: se dispara CON ANTICIPACIÓN (faltando duracion_fade_
    # segundos para terminar), no al final — ver nota al inicio del
    # archivo.
    # ------------------------------------------------------------------
    def _chequear_crossfade(self, restante_ms: int):
        if not self.crossfade_activado or self._crossfade_en_curso or self._pisador_activo:
            return
        if self._stop_diferido_armado or self._ceder_control_armado:
            # No arrancar una transición nueva: dejar que el ítem
            # actual llegue a su fin tal cual, _avanzar() frena ahí
            # (o cede el control a Publicidad, si corresponde).
            return
        duracion_ms = int(self.duracion_fade_segundos * 1000)
        if duracion_ms <= 0:
            return
        if 0 < restante_ms <= duracion_ms:
            self._iniciar_crossfade()

    def _iniciar_crossfade(self, duracion_segundos: float = None):
        if self._crossfade_en_curso:
            return  # defensivo: no superponer dos crossfades a la vez
        # Defensivo (en la práctica no debería poder dispararse un
        # crossfade con self.motor detenido durante el anuncio manual
        # de HORA/TEMPERATURA, pero cancelar acá también evita que un
        # "resume" diferido pise una transición que arrancó mientras
        # tanto por otro camino).
        self._cancelar_anuncio_manual_en_curso()
        duracion_segundos = self.duracion_fade_segundos if duracion_segundos is None else duracion_segundos

        total = self.panel.cantidad_items()
        if total == 0:
            return

        fila_actual = self.panel.fila_reproduciendo()
        fila_siguiente = self.panel.fila_siguiente()
        if fila_siguiente < 0 or fila_siguiente == fila_actual:
            fila_siguiente = fila_actual + 1

        # Mismo criterio que _avanzar() (caminos paralelos, ver nota al
        # inicio del archivo — cualquier chequeo sobre "qué ítem sigue"
        # se agrega a los DOS): refill/"repetir al finalizar" + saltear
        # filas con el archivo faltante, para que el crossfade nunca
        # intente cruzar hacia un ítem sin vincular.
        fila_siguiente = self._resolver_siguiente_fila_valida(fila_siguiente, total)
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
            ruta_siguiente, duracion_segundos,
            punto_inicio_ms=analisis_siguiente.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis_siguiente.get("punto_fin_ms"),
            ganancia_db=analisis_siguiente.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
            duracion_fade_in_ms=int(self.duracion_fade_in_segundos * 1000),
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
        self.panel.marcar_realmente_reproducido(fila_siguiente)
        candidata_siguiente = self._resolver_candidata_verde(fila_siguiente)
        if candidata_siguiente >= 0:
            self._marcar_siguiente_con_refill(candidata_siguiente)

        registrar_evento(f"Crossfade: iniciado hacia fila {fila_siguiente} ('{ruta_siguiente}')")

        # Bug real corregido — "el Pisador no sonaba si la lista
        # avanzaba sola": una primera corrección lo disparaba recién
        # en _liberar_crossfade() (al terminar la rampa del crossfade,
        # ~duracion_fade_segundos después) para no competir con esa
        # rampa — pero eso significaba varios segundos SIN NINGÚN
        # sonido de Pisador, indistinguible en la práctica de "no
        # sonó". Pedido explícito: el Pisador debe sonar SIEMPRE. Se
        # dispara el AUDIO ya mismo (aplicar_ducking=False: el
        # ducking, bajar el volumen del tema mientras suena el
        # Pisador, se aplica recién en _liberar_crossfade para no
        # pelear con la rampa de volumen del propio crossfade sobre
        # el mismo motor) — la prioridad es que el audio del Pisador
        # arranque en el momento correcto, aunque el ducking llegue
        # un instante después.
        self._fila_pisador_outro_disparado = -1
        if self.panel.posicion_pisador_en_fila(fila_siguiente) != "final":
            self._disparar_pisador_si_corresponde(fila_siguiente, aplicar_ducking=False)

        QTimer.singleShot(
            int(duracion_segundos * 1000) + 200,
            lambda: self._liberar_crossfade(fila_siguiente),
        )

    def _liberar_crossfade(self, fila_entrante: int):
        self._crossfade_en_curso = False
        self._motor_saliente_crossfade = None

        # El ducking (bajar el volumen del tema mientras suena el
        # Pisador) se aplica recién ACÁ, una vez que la propia rampa
        # de volumen del crossfade ya terminó — así no compiten dos
        # fades por el mismo motor a la vez. Si el Pisador ya terminó
        # solo antes de que esto se ejecute (uno corto, duracion_fade_
        # segundos largo), `_pisador_activo` ya está en False y no hay
        # nada que "duckear" — no hace falta hacer nada. Tampoco si
        # el operador tomó control manual mientras tanto (Siguiente,
        # doble click, Stop) y la fila entrante ya no es la que suena.
        if self._pisador_activo and self.panel.fila_reproduciendo() == fila_entrante:
            volumen_pisado = volumen_ajustado_por_ganancia(self._volumen_base, self.bajada_db_pisador)
            self.motor.fade_volumen_a(volumen_pisado, DURACION_FADE_PISADOR_SEGUNDOS)

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
    def _chequear_pisador_outro(self, restante_ms: int):
        """Pisador en el OUTRO (pedido explícito, paridad con Dinesat):
        mismo motor que el Pisador de inicio (_disparar_pisador_si_
        corresponde), disparado cerca del FINAL del tema en vez de al
        arrancar. Limitación conocida de esta primera versión: si hay
        un crossfade en curso sobre este mismo ítem, el Pisador de
        Outro no se dispara — evita competir con la propia rampa de
        volumen del crossfade sobre el mismo motor (mismo criterio ya
        aplicado, en su momento, al Pisador de inicio + crossfade). Si
        el crossfade termina cortando la reproducción antes de que el
        Pisador llegue a sonar, la próxima ronda lo revisa con audio
        real."""
        if self._pisador_activo or self._crossfade_en_curso:
            return
        fila = self.panel.fila_reproduciendo()
        if fila < 0 or fila == self._fila_pisador_outro_disparado:
            return
        if self.panel.posicion_pisador_en_fila(fila) != "final":
            return
        if restante_ms <= 0 or restante_ms > UMBRAL_DISPARO_PISADOR_OUTRO_MS:
            return
        self._fila_pisador_outro_disparado = fila
        self._disparar_pisador_si_corresponde(fila)

    def _disparar_pisador_si_corresponde(self, fila: int, aplicar_ducking: bool = True):
        ruta_pisador = self.panel.ruta_pisador_en_fila(fila)
        if not ruta_pisador:
            return
        self._generacion_pisador += 1
        self._pisador_activo = True
        volumen_pisado = volumen_ajustado_por_ganancia(self._volumen_base, self.bajada_db_pisador)
        registrar_evento(
            f"Pisador: disparado sobre fila {fila} ('{self.panel.ruta_en_fila(fila)}') -> "
            f"'{ruta_pisador}' (baja de {self._volumen_base} a {volumen_pisado}, "
            f"ducking {'inmediato' if aplicar_ducking else 'diferido (crossfade en curso)'})"
        )
        if aplicar_ducking:
            self.motor.fade_volumen_a(volumen_pisado, DURACION_FADE_PISADOR_SEGUNDOS)
        # El audio del Pisador arranca SIEMPRE ya mismo, sin importar
        # si el ducking del tema principal se aplica ahora o más tarde
        # (pedido explícito: nunca debe quedar en silencio esperando).
        self.motor_pisador.reproducir(ruta_pisador)

    def _on_pisador_finalizado(self):
        registrar_evento("Pisador: terminó solo, el tema principal vuelve a su volumen normal")
        self._pisador_activo = False
        self.motor.fade_volumen_a(self._volumen_base, DURACION_FADE_PISADOR_SEGUNDOS)

    def _cancelar_pisador_en_curso(self):
        if self._pisador_activo:
            registrar_evento("Pisador: cancelado — se avanzó de tema antes de que terminara solo")
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
            # Pedido explícito: "por debajo del ítem que entra en rojo,
            # el de abajo pasa a verde en previo... si está en stop,
            # elijo uno con doble clic para ponerse en rojo, pero el
            # verde quedó en otro ítem diferente" — a diferencia de
            # _asegurar_rojo_y_verde() (que no toca un verde ya
            # válido), acá el verde SIEMPRE se recalcula al de abajo
            # del rojo recién elegido, descartando cualquier verde
            # viejo que hubiera quedado apuntando a otro lado.
            self._recalcular_verde_tras_nuevo_rojo(fila)

    def _recalcular_verde_tras_nuevo_rojo(self, fila_roja: int):
        """SIEMPRE recalcula el verde como el ítem de abajo del rojo
        recién elegido a mano — a diferencia de `_asegurar_rojo_y_verde()`
        (que respeta un verde ya válido, sin importar dónde apunte),
        acá se sobrescribe cualquier verde viejo. `_marcar_siguiente_con_refill`
        se encarga de repintar el verde anterior a su color normal.

        Bug real corregido: cuando `fila_roja` era el ÚLTIMO ítem
        disponible (el caso típico de "elegí a mano el último ítem
        cargado y lo reproduzco"), esta función calculaba el
        candidato a mano en vez de usar `_resolver_candidata_verde()`
        — con un formato FMT activo, eso dejaba el verde vacío para
        siempre sin disparar ningún refill (ver nota completa en
        `_resolver_candidata_verde`)."""
        candidata = self._resolver_candidata_verde(fila_roja)
        if candidata >= 0:
            self._marcar_siguiente_con_refill(candidata)
        else:
            self.panel.marcar_siguiente(-1)

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
        # Cut (o cualquier otro disparador de avance) mientras el
        # anuncio manual de HORA/TEMPERATURA está sonando: cancelarlo
        # antes de tocar nada más, para que no siga sonando de fondo
        # ni su "resume" diferido pise el avance que se está por hacer.
        self._cancelar_anuncio_manual_en_curso()
        if self._ceder_control_armado:
            # Pedido explícito: el ítem que estaba sonando llegó a su
            # fin NATURAL — recién ACÁ se libera Emisión de verdad
            # (detener, nunca pausar) y se avisa al Scheduler que ya
            # puede arrancar el bloque de Publicidad. Aplica sin
            # importar si el disparo fue por fin natural o Cut manual
            # (_chequear_crossfade ya bloqueó una transición nueva).
            self._ceder_control_armado = False
            callback = self._callback_ceder_control
            self._callback_ceder_control = None
            self.detener()
            if callback is not None:
                callback()
            return
        if self._stop_diferido_armado:
            # Pedido explícito (Dinesat, "Stop diferido"): dejar
            # terminar el ítem en reproducción y detener TODO en vez
            # de avanzar al siguiente — aplica sin importar si el
            # disparo fue por fin natural, Cut manual o cascada de
            # error, todos pasan por acá.
            self._cancelar_stop_diferido()
            self.detener()
            return

        total = self.panel.cantidad_items()
        if total == 0:
            return

        fila_actual = self.panel.fila_reproduciendo()
        fila_siguiente = self.panel.fila_siguiente()

        if fila_siguiente < 0 or fila_siguiente == fila_actual:
            fila_siguiente = fila_actual + 1

        # Red de emergencia de fin de lista (serie de 1 solo ítem, o
        # cualquier otro caso sin "ante-último" desde donde marcar
        # verde) + pedido explícito ("si hay un ítem no vinculado, que
        # no se detenga y pase al que sigue debajo"): _resolver_
        # siguiente_fila_valida() resuelve las dos cosas de una —
        # aplica el mismo refill/"repetir al finalizar" de siempre Y
        # saltea cualquier fila con el archivo faltante en el camino.
        fila_siguiente = self._resolver_siguiente_fila_valida(fila_siguiente, total)
        if fila_siguiente < 0:
            # Ningún ítem de la lista es reproducible (todo roto) —
            # ahí sí no queda nada para reproducir.
            self.motor.detener()
            self.panel.resetear_reproduccion()
            return

        self.panel.marcar_reproduciendo(fila_siguiente)

        candidata_siguiente = self._resolver_candidata_verde(fila_siguiente)
        if candidata_siguiente >= 0:
            self._marcar_siguiente_con_refill(candidata_siguiente)

        self._reproducir_fila(fila_siguiente)

    def _marcar_siguiente_con_refill(self, fila: int):
        """Envoltorio ÚNICO sobre `panel.marcar_siguiente()` para
        Emisión — pedido explícito: "cuando el último item cargado en
        la ventana se pinte de verde (sin tomar en cuenta el rojo) vas
        a cargar un nuevo ciclo". El refill del Musicalizador se
        dispara EXACTAMENTE acá, en el mismo instante en que algo se
        pinta de verde por ser el último ítem disponible — sin
        importar qué esté en rojo en ese momento (puede ser el
        ante-último, o cualquier otro, da igual). TODO lugar de este
        archivo que marca "siguiente" en Emisión pasa por acá
        (`_avanzar()`, `_iniciar_crossfade()`, `_asegurar_rojo_y_verde()`)
        — evita el bug ya conocido de que `_avanzar()` e
        `_iniciar_crossfade()` son caminos paralelos que no comparten
        código: centralizando el chequeo en el ÚNICO lugar que de
        verdad pinta de verde, un camino nuevo no puede volver a
        olvidarlo."""
        self.panel.marcar_siguiente(fila)
        if (
            self._formato_musicalizador_activo is not None
            and fila >= 0
            and fila == self.panel.cantidad_items() - 1
        ):
            self._generar_serie_musicalizador()

    # ------------------------------------------------------------------
    # Musicalizador Avanzado + Comandos FMT (pedido explícito,
    # encadenados: al pasar por un ítem-comando FMT de Ventana 1,
    # GestorPublicidad llama acá con el nombre del formato — ver
    # core/playlist_manager.py:_ejecutar_comando y
    # gui/main_window.py, donde se conecta el callback).
    # ------------------------------------------------------------------
    def formato_musicalizador_activo(self) -> str | None:
        return self._formato_musicalizador_activo

    def iniciar_musicalizador(self, nombre_formato: str):
        """Activa la generación continua de música según
        `nombre_formato` (pedido explícito, puntos 6/7/8: "la música
        en la ventana irá reproduciendo de acuerdo al musicalizador
        avanzado de manera continua, siempre repitiendo el esquema").
        Sigue activo hasta que otro comando FMT lo reemplace por otro
        formato, o se llame a detener_musicalizador()."""
        if self._ventana_explorador is None:
            registrar_error("Musicalizador: no hay acceso al Explorador, no se puede generar música.")
            return
        self._formato_musicalizador_activo = nombre_formato
        guardar_ultimo_fmt(nombre_formato)
        registrar_evento(f"Musicalizador: activado formato '{nombre_formato}' (persistir={self.persistir})")
        if self.al_cambiar_formato_activo is not None:
            self.al_cambiar_formato_activo(nombre_formato)
        # Pedido explícito (punto c): un Comando FMT REEMPLAZA el
        # contenido de Emisión, nunca lo acumula arriba de lo que
        # hubiera antes (ítems sueltos del operador, o el lote de un
        # formato anterior). La recarga CONTINUA de este mismo formato
        # mientras suena (ver _avanzar()) es aparte y NUNCA limpia —
        # eso cortaría la música que está sonando.
        self._limpiar_playlist_para_musicalizador()
        self._generar_serie_musicalizador()

    def detener_musicalizador(self):
        if self._formato_musicalizador_activo is not None:
            registrar_evento(
                f"Musicalizador: desactivado (formato '{self._formato_musicalizador_activo}', "
                f"persistir={self.persistir})"
            )
        self._formato_musicalizador_activo = None
        if self.al_cambiar_formato_activo is not None:
            self.al_cambiar_formato_activo(None)

    def _limpiar_playlist_para_musicalizador(self):
        if self.motor.esta_reproduciendo():
            self.motor.detener()
        self.panel.set_indicador_en_vivo(False)
        self.panel.limpiar_items()

    def _generar_serie_musicalizador(self):
        """Genera UNA serie completa (pedido explícito, punto a: "debe
        cargar el número exacto de musicalización... la cantidad que
        haya programado. Solo se extiende si en la serie hay
        sub-formato") — ya NO un tamaño de lote fijo, sino exactamente
        lo que produce una pasada por el formato (ver
        core/musicalizador.py:generar_serie).

        Pedido explícito (ronda posterior): las rutas YA presentes en
        Emisión (la serie anterior, que con el refill disparado al
        "entrar en previo" todavía puede no haber sonado nada) se
        pasan como exclusión extra — el historial persistente por sí
        solo no alcanza para evitar repetir el mismo aleatorio recién
        elegido, porque todavía no se registró como reproducido."""
        if self._formato_musicalizador_activo is None or self._ventana_explorador is None:
            return
        rutas_en_cola = frozenset(
            ruta for i in range(self.panel.cantidad_items())
            if (ruta := self.panel.ruta_en_fila(i))
        )
        items_generados = generar_serie(
            self._ventana_explorador, self._formato_musicalizador_activo, rutas_en_cola,
        )
        if not items_generados:
            registrar_error(
                f"Musicalizador: el formato '{self._formato_musicalizador_activo}' no generó "
                "ningún ítem — revisar sus categorías/archivos en el Musicalizador Avanzado."
            )
            return
        for concreto in items_generados:
            registro = concreto["registro"]
            fila_item = self.panel.agregar_item(
                registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
                registro.get("ruta", ""), registro.get("punto_inicio_ms") or 0,
                registro.get("punto_fin_ms"), registro.get("ganancia_db") or 0.0,
            )
            if concreto.get("pisador") and hasattr(self.panel, "agregar_pisador"):
                fila_idx = self.panel.tree.indexOfTopLevelItem(fila_item)
                pisador_reg = concreto["pisador"]
                self.panel.agregar_pisador(
                    fila_idx, pisador_reg.get("titulo", ""), pisador_reg.get("duracion", ""),
                    pisador_reg.get("codigo", "—"), pisador_reg.get("ruta", ""),
                    concreto.get("pisador_posicion") or "inicio",
                )
        registrar_evento(
            f"Musicalizador: generados {len(items_generados)} ítem(s) del formato "
            f"'{self._formato_musicalizador_activo}'"
        )
        # Si la lista estaba vacía o sin nada armado, el nuevo lote
        # recién generado queda mudo sin un Play manual — igual que el
        # resto de la app, nunca arranca a sonar solo salvo que ya
        # hubiera algo en curso (ver GestorPlaylist con persistir=True).
        self._asegurar_rojo_y_verde()

    def insertar_ciclo_fmt_por_tiempo(self, nombre_formato: str, minutos: float) -> int:
        """Pedido explícito ("agregá un menú contextual en Emisión...
        me pregunta el FMT que deseo y la cantidad de tiempo... el
        sistema calculará esa cantidad de tiempo e insertará ese
        ciclo... como si hubiera pasado por el comando FMT de la
        ventana 1, sin eliminar lo que ya esté cargado"): a diferencia
        de `iniciar_musicalizador()` (que SIEMPRE limpia Emisión antes
        de generar), esto AGREGA al final de lo que ya hay cargado —
        llama a `generar_serie()` en un bucle (misma lógica de
        "repetir el esquema" que ya usa el refill continuo) hasta
        juntar al menos `minutos` de contenido estimado (sumando la
        duración real de cada ítem generado), con un techo duro de
        `LIMITE_ITEMS_CICLO_POR_TIEMPO` para nunca colgarse aunque el
        formato tenga ítems sin duración conocida. "Como si hubiera
        pasado por el Comando FMT" (pedido explícito): deja este
        formato como el ACTIVO para el refill continuo de ahí en más,
        y lo graba como "último FMT" -- la única diferencia real con
        el Comando FMT real es que este NO limpia lo ya cargado.
        Devuelve la cantidad de ítems insertados (0 si el formato no
        generó nada)."""
        if self._ventana_explorador is None:
            registrar_error("Musicalizador: no hay acceso al Explorador, no se puede generar música.")
            return 0

        segundos_objetivo = max(0.0, minutos) * 60
        segundos_acumulados = 0.0
        rutas_en_cola = set(
            ruta for i in range(self.panel.cantidad_items())
            if (ruta := self.panel.ruta_en_fila(i))
        )
        items_generados = []
        intentos_sin_avance = 0
        while (
            segundos_acumulados < segundos_objetivo
            and intentos_sin_avance < 5
            and len(items_generados) < LIMITE_ITEMS_CICLO_POR_TIEMPO
        ):
            concretos = generar_serie(self._ventana_explorador, nombre_formato, frozenset(rutas_en_cola))
            if not concretos:
                intentos_sin_avance += 1
                continue
            intentos_sin_avance = 0
            for concreto in concretos:
                items_generados.append(concreto)
                ruta = concreto["registro"].get("ruta")
                if ruta:
                    rutas_en_cola.add(ruta)
                segundos_acumulados += duracion_a_segundos(concreto["registro"].get("duracion")) or 0
                if (
                    segundos_acumulados >= segundos_objetivo
                    or len(items_generados) >= LIMITE_ITEMS_CICLO_POR_TIEMPO
                ):
                    break

        if not items_generados:
            registrar_error(
                f"Musicalizador: '{nombre_formato}' no generó ningún ítem para el ciclo por tiempo."
            )
            return 0

        for concreto in items_generados:
            registro = concreto["registro"]
            fila_item = self.panel.agregar_item(
                registro.get("titulo", ""), registro.get("duracion", ""), registro.get("codigo", "—"),
                registro.get("ruta", ""), registro.get("punto_inicio_ms") or 0,
                registro.get("punto_fin_ms"), registro.get("ganancia_db") or 0.0,
            )
            if concreto.get("pisador") and hasattr(self.panel, "agregar_pisador"):
                fila_idx = self.panel.tree.indexOfTopLevelItem(fila_item)
                pisador_reg = concreto["pisador"]
                self.panel.agregar_pisador(
                    fila_idx, pisador_reg.get("titulo", ""), pisador_reg.get("duracion", ""),
                    pisador_reg.get("codigo", "—"), pisador_reg.get("ruta", ""),
                    concreto.get("pisador_posicion") or "inicio",
                )

        self._formato_musicalizador_activo = nombre_formato
        guardar_ultimo_fmt(nombre_formato)
        if self.al_cambiar_formato_activo is not None:
            self.al_cambiar_formato_activo(nombre_formato)
        registrar_evento(
            f"Musicalizador: insertado ciclo por tiempo de '{nombre_formato}' -- "
            f"{len(items_generados)} ítem(s), ~{segundos_acumulados / 60:.1f} min, sin borrar lo ya cargado."
        )
        self._asegurar_rojo_y_verde()
        return len(items_generados)

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

    def serializar_items(self) -> list:
        """Vuelca TODO el contenido actual del panel (ítems + Pisador
        anidado + análisis de audio) a una lista de dicts — mismo
        formato que ya usa la persistencia automática de Emisión.
        Reutilizado también por el guardado de listas con nombre del
        Auxiliar (gui/main_window.py), para no duplicar esta lógica."""
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
        return items

    def cargar_items(self, items: list):
        """Reemplaza TODO el contenido actual del panel por `items`
        (mismo formato que serializar_items) — limpia primero, arma
        rojo/verde con el mismo criterio de siempre. Usado por la
        carga de listas con nombre del Auxiliar; nunca reproduce nada
        solo."""
        self._restaurando = True
        try:
            self.panel.limpiar_items()
            for registro in items:
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
            self._asegurar_rojo_y_verde()
        finally:
            self._restaurando = False

    def _guardar_estado_ahora(self):
        guardar_playlist_emision({
            "items": self.serializar_items(),
            "fila_armada": self.panel.fila_reproduciendo(),
            "fila_siguiente": self.panel.fila_siguiente(),
            "formato_musicalizador_activo": self._formato_musicalizador_activo,
        })

    def _restaurar_desde_disco(self):
        self._restaurando = True
        try:
            datos = cargar_playlist_emision()
            # Bug real corregido ("no lee el último FMT... llega al
            # final de la lista y no carga otro ciclo, se detiene"):
            # restaurar el nombre del formato ANTES de marcar rojo/
            # verde, para que el refill (ver _marcar_siguiente_con_refill,
            # más abajo) ya sepa que esta lista sigue viva y hay que
            # seguir generando ciclos nuevos al agotarse.
            self._formato_musicalizador_activo = datos.get("formato_musicalizador_activo")
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
                # _marcar_siguiente_con_refill(), no panel.marcar_siguiente()
                # directo: si el verde restaurado resulta ser el ÚLTIMO
                # ítem de la lista y hay un formato activo, el refill
                # tiene que dispararse YA, acá mismo al reabrir la app
                # — no recién la próxima vez que algo se marque verde.
                self._marcar_siguiente_con_refill(fila_siguiente)
            else:
                # Pedido explícito: si no había un "siguiente" guardado
                # (o quedó inválido), igual debe quedar un verde
                # marcado en cuanto haya un segundo ítem disponible.
                self._asegurar_rojo_y_verde()

            if total > 0:
                registrar_evento(f"Playlist de Emisión restaurada: {total} ítem(s)")
        except Exception as error:
            registrar_error(f"Error restaurando playlist de Emisión: {error}")
        finally:
            self._restaurando = False
