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
from core.hth import resolver_comando_hth, TIPO_COMANDO_HTH
from config.settings import (
    cargar_playlist_publicidad, guardar_playlist_publicidad, registrar_error, registrar_evento,
    titulo_bloque_sin_prefijo_hora, vigencia_activa, rutas_recientes_en_historial, registrar_reproduccion,
)

DEBOUNCE_GUARDADO_PUBLICIDAD_MS = 500
# Paridad con Dinesat: el botón verde hace de "Siguiente con fundido"
# con algo sonando, y Fade-Stop apaga con fundido en vez de corte
# seco — duración corta a propósito, es una acción manual.
DURACION_FUNDIDO_MANUAL_SEGUNDOS = 1.2


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
        duracion_fade_out_v1_ms: int = 500,
        duracion_fade_in_declick_ms: int = 60,
        ventana_explorador=None,
    ):
        self.ventana = ventana_publicidad
        self.motor = MotorAudio(id_dispositivo)
        self.avanzar_en_error = avanzar_en_error
        self.reintentos_maximos = max(1, reintentos_maximos)
        self.persistir = persistir
        # Comando HTH (Hora-Temperatura-Humedad, pedido explícito):
        # necesita el Explorador para resolver los clips de voz por
        # género "HTH" (ver core/hth.py). Sin él, el comando se
        # saltea solo, sin sonar nada — mismo criterio que el
        # Musicalizador cuando falta ventana_explorador.
        self._ventana_explorador = ventana_explorador
        # Cola de reproducción INTERNA de un Comando HTH en curso —
        # varios clips concatenados (ej. "HORA 14" + "MINUTOS 30") que
        # suenan uno atrás del otro con el MISMO MotorAudio, sin pasar
        # por _avanzar() hasta que se agota.
        self._reproduciendo_hth = False
        self._cola_hth = []
        # Fade OUT automático y corto entre tandas (pedido explícito,
        # "bien pegados uno a otro, incluso 500 milisegundos de
        # fade... el fade OUT de la ventana 1") — configurable en ms,
        # ver Configuración → Reproducción y Automatización. Se
        # dispara CON ANTICIPACIÓN sobre el ítem SALIENTE (nunca hay
        # fade-in en el entrante — pedido explícito, "el fade es
        # siempre OUT, no usaremos el fade IN").
        self.duracion_fade_out_v1_ms = duracion_fade_out_v1_ms
        # Pedido explícito ("un mínimo tartamudeo, un clip de sonido al
        # inicio de los ítems... un leve fade de inicio"): rampa de
        # milisegundos al ARRANCAR cada ítem (no un fade musical, ver
        # MotorAudio.reproducir) — evita el click de un salto brusco a
        # volumen final, más audible desde que el audio pasa por la
        # cadena de EasyEffects.
        self.duracion_fade_in_declick_ms = duracion_fade_in_declick_ms
        self._fallos_consecutivos = 0
        self._volumen_base = 100
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None
        self._restaurando = False
        self._fundido_en_curso = False
        # Referencia al ítem cuyo fade-out automático ya se disparó —
        # evita redispararlo en cada tick de restante_ms_cambio.
        self._item_fade_out_v1_disparado = None
        # "Stop diferido" (Dinesat): armado, deja terminar el ítem
        # actual y recién ahí detiene TODO — no avanza al siguiente.
        self._stop_diferido_armado = False

        # Callback general de "la reproducción terminó sola" (fin del
        # bloque, freno por hora de un bloque futuro, fin del árbol,
        # o cascada de errores agotada) — SchedulerAutomatico lo usa
        # para el ciclo Automático (volver a Emisión / quedar en
        # silencio según el botón). NO se llama en un Stop manual del
        # operador fuera de un bloque automático: ahí el silencio es
        # intencional.
        self.al_finalizar_reproduccion = None

        # Comando FMT (pedido explícito, encadenado con el
        # Musicalizador Avanzado): callback que MainWindow conecta a
        # GestorPlaylist.iniciar_musicalizador — se llama con el
        # nombre del formato cuando la reproducción "pasa por" un
        # ítem-comando FMT en un bloque (ver _ejecutar_comando).
        self.al_comando_fmt = None

        # Pedido explícito: "cuando pase de la ventana 2 a la 1,
        # haciendo play, cortará en fade la reproducción de la ventana
        # 2, incluso si está en automático" — MainWindow lo conecta a
        # SchedulerAutomatico.cortar_emision_por_play_manual(). A
        # diferencia del botón STOP (bloqueado con el Automático
        # activo), el Play manual de Ventana 1 SIEMPRE corta Emisión.
        self.al_arrancar_manual = None

        self.motor.posicion_cambiada.connect(self.ventana.actualizar_contadores)
        self.motor.posicion_cambiada.connect(self._actualizar_indicador)
        # Bug real corregido — "la ventana 1 no reproduce el ítem
        # siguiente": esta conexión FALTABA (Ventana 2 la tuvo siempre
        # en _conectar_motor). Sin ella, al terminar una tanda
        # naturalmente nadie llamaba a _avanzar() y la reproducción
        # moría en el primer ítem, sin ningún error visible.
        self.motor.finalizo_item.connect(self._on_fin_de_item)
        self.motor.error_reproduccion.connect(self._on_error)
        self.motor.restante_ms_cambio.connect(self._actualizar_progreso)
        self.motor.restante_ms_cambio.connect(self._chequear_fade_out_automatico)

        # Pedido explícito (paridad con Dinesat): el botón verde es
        # Play SI está en silencio, o "Siguiente con fundido" si ya
        # hay algo sonando.
        self.ventana.solicitud_play.connect(self._on_click_play)
        self.ventana.solicitud_pausa.connect(self._pausar)
        self.ventana.solicitud_stop.connect(self._detener)
        # "Cut" (antes "Siguiente"): corte seco e inmediato — mismo
        # comportamiento de siempre, solo cambió el nombre/ícono en la
        # UI para igualar Dinesat.
        self.ventana.solicitud_siguiente.connect(self._avanzar_al_siguiente)
        if hasattr(self.ventana, "solicitud_fade_stop"):
            self.ventana.solicitud_fade_stop.connect(self._fade_stop)
        if hasattr(self.ventana, "solicitud_stop_diferido"):
            self.ventana.solicitud_stop_diferido.connect(self._toggle_stop_diferido)
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

    def _chequear_fade_out_automatico(self, restante_ms: int):
        """Fade OUT automático y corto entre tandas de Publicidad
        (pedido explícito, ver duracion_fade_out_v1_ms) — se dispara
        CON ANTICIPACIÓN sobre el ítem que YA está sonando, cerca de
        su final, para que la transición a la siguiente tanda quede
        "bien pegada" en vez de un corte seco. Nunca compite con un
        fundido manual (_avanzar_con_fundido) ni con el Stop diferido,
        y solo se dispara UNA vez por ítem (guard por referencia,
        evita redispararse en cada tick)."""
        if self._fundido_en_curso or self._stop_diferido_armado:
            return
        if self.duracion_fade_out_v1_ms <= 0:
            return
        item_actual = self.ventana.item_reproduciendo()
        if item_actual is None or item_actual is self._item_fade_out_v1_disparado:
            return
        if 0 < restante_ms <= self.duracion_fade_out_v1_ms:
            self._item_fade_out_v1_disparado = item_actual
            self.motor.fade_volumen_a(0, self.duracion_fade_out_v1_ms / 1000.0)

    def _detener(self):
        registrar_evento("Publicidad: Stop")
        self.motor.detener()
        self._fallos_consecutivos = 0
        # Defensivo (mismo espíritu que el resto del motor de audio de
        # esta app ante libVLC): si el Stop llega a mitad de un
        # Comando HTH, se aborta la cola de clips pendiente — nunca
        # debería sonar un clip más después de un Stop manual.
        self._reproduciendo_hth = False
        self._cola_hth = []
        self.ventana.set_indicador_en_vivo(False)
        # Pedido explícito: la barra de progreso no debe quedar
        # "pegada" en la posición donde se detuvo — Stop la reinicia.
        self.ventana.resetear_reproduccion()
        if self._bloque_automatico_actual is not None:
            self._finalizar_bloque_automatico()
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()

    def _fade_stop(self):
        """Botón "Fade" (Dinesat): fundido hasta apagar el ítem en
        reproducción — distinto del Stop (corte seco) y del Stop
        diferido (dejar terminar y recién ahí frenar)."""
        if not self.motor.esta_reproduciendo():
            self._detener()
            return
        registrar_evento("Publicidad: Fade-Stop")
        self.motor.fade_volumen_a(0, DURACION_FUNDIDO_MANUAL_SEGUNDOS)
        QTimer.singleShot(int(DURACION_FUNDIDO_MANUAL_SEGUNDOS * 1000) + 150, self._detener)

    def _toggle_stop_diferido(self):
        """Botón "Stop diferido" (Dinesat): deja terminar el ítem en
        reproducción y recién ahí detiene TODO (no avanza al
        siguiente) — un segundo click lo desarma."""
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()
            return
        self._stop_diferido_armado = True
        if hasattr(self.ventana, "set_stop_diferido_armado"):
            self.ventana.set_stop_diferido_armado(True)
        registrar_evento("Publicidad: Stop diferido armado")

    def _cancelar_stop_diferido(self):
        self._stop_diferido_armado = False
        if hasattr(self.ventana, "set_stop_diferido_armado"):
            self.ventana.set_stop_diferido_armado(False)
        registrar_evento("Publicidad: Stop diferido desarmado")

    def _item_valido(self, item) -> bool:
        """Pedido explícito (Dinesat): un ítem con vigencia de fecha
        vencida/no iniciada se saltea acá mismo, como si no fuera
        válido — mismo camino que ya usan todos los que llaman a
        _item_valido() para avanzar, sin cortar la emisión ni tocar
        el ítem (sigue en la lista, se saltea cada vez que le toca).
        Un ítem-comando (FMT) SÍ es un candidato válido — no "suena"
        pero se ejecuta al llegarle el turno (ver _reproducir_item). Un
        ítem ALEATORIO también es válido estructuralmente — no tiene
        ruta fija, recién se resuelve (y se puede saltear si la
        categoría está vacía) al llegarle el turno."""
        if item is None:
            return False
        if self.ventana.es_comando(item):
            return True
        if self.ventana.es_aleatorio(item):
            return True
        if not item.data(0, Qt.ItemDataRole.UserRole):
            return False
        return vigencia_activa(self.ventana.vigencia_de_item(item))

    def _bloque_ya_disponible(self, item_bloque) -> bool:
        """True si ya llegó (o pasó) la hora asignada al bloque, o si
        no tiene hora válida (no se restringe)."""
        hora_str = self.ventana.hora_de_bloque(item_bloque)
        if not hora_str:
            return True
        hora_bloque = QTime.fromString(hora_str, "HH:mm:ss")
        if not hora_bloque.isValid():
            return True
        return QTime.currentTime() >= hora_bloque

    def _ejecutar_comando(self, item):
        """Comando FMT (pedido explícito, punto 6): NO ocupa tiempo de
        aire — se ejecuta y la reproducción sigue directo al próximo
        ítem real del bloque (ver _reproducir_item)."""
        tipo_comando = self.ventana.tipo_comando_de_item(item)
        parametro = self.ventana.parametro_comando_de_item(item)
        registrar_evento(f"Publicidad: comando ejecutado -> {tipo_comando} {parametro}")
        if tipo_comando == "FMT" and self.al_comando_fmt is not None:
            try:
                self.al_comando_fmt(parametro)
            except Exception as error:
                registrar_error(f"Publicidad: error ejecutando comando FMT '{parametro}': {error}")

    def _reproducir_item(self, item):
        if not self._item_valido(item):
            return
        # Cualquier arranque "fresco" (ítem normal o un comando nuevo)
        # invalida una secuencia de Comando HTH que hubiera quedado a
        # medias — seguir la cola vieja acá sería un bug (audio de un
        # comando viejo pisando al nuevo). Continuar la MISMA
        # secuencia nunca pasa por acá, ver _reproducir_siguiente_clip_hth().
        self._reproduciendo_hth = False
        self._cola_hth = []
        if self.ventana.es_comando(item):
            tipo_comando = self.ventana.tipo_comando_de_item(item)
            if tipo_comando == TIPO_COMANDO_HTH:
                self._reproducir_comando_hth(item)
                return
            # Bug real corregido: antes esto llamaba a self._avanzar()
            # sin actualizar item_reproduciendo()/item_siguiente() —
            # la próxima vuelta de _avanzar() volvía a resolver este
            # MISMO comando como candidato (item_reproduciendo() seguía
            # apuntando al ítem ANTERIOR, e item_siguiente() todavía
            # apuntaba a este comando), reejecutando el FMT una y otra
            # vez en recursión sin fin hasta el límite de pila de
            # Python — silenciado por el excepthook global, así que
            # visualmente "quedaba en el FMT" sin ningún error. Ahora
            # se marca el comando como reproduciendo (para que
            # item_base avance de verdad) y se recalcula el próximo
            # ítem ANTES de seguir — item_siguiente() nunca vuelve a
            # apuntar a este mismo comando.
            self.ventana.marcar_reproduciendo_item(item)
            self._ejecutar_comando(item)
            siguiente = self.ventana.tree.itemBelow(item)
            while siguiente is not None and not self._item_valido(siguiente):
                siguiente = self.ventana.tree.itemBelow(siguiente)
            self.ventana.marcar_siguiente_item(siguiente)
            self._avanzar()
            return
        if self.ventana.es_aleatorio(item):
            self._reproducir_item_aleatorio(item)
            return
        self.ventana.tree.setCurrentItem(item)
        self.ventana.marcar_reproduciendo_item(item)
        # Nuevo ítem arrancando: habilita de nuevo el fade-out
        # automático para ESTE ítem (el guard de arriba es por
        # referencia, no se "hereda" del ítem anterior).
        self._item_fade_out_v1_disparado = None

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
            duracion_declick_ms=self.duracion_fade_in_declick_ms,
        )
        self.ventana.set_indicador_en_vivo(True)
        registrar_evento(f"Publicidad: reproduciendo '{item.text(0)}'")

    # ------------------------------------------------------------------
    # Ítem ALEATORIO (pedido explícito, Programador: "para darle
    # dinamismo, por ejemplo en separadores... que sea buen aleatorio y
    # variado"): a diferencia de una tanda normal, no tiene una ruta
    # fija — resuelve un archivo al azar de la categoría guardada CADA
    # VEZ que le toca sonar, con el mismo no-repetir vía historial
    # persistente que ya usa el Musicalizador Avanzado
    # (rutas_recientes_en_historial), así nunca repite un archivo hasta
    # agotar los demás de esa categoría.
    # ------------------------------------------------------------------
    def _resolver_item_aleatorio(self, item):
        if self._ventana_explorador is None:
            return None
        ruta_categoria = self.ventana.categoria_aleatorio_de_item(item) or []
        categoria = self._ventana_explorador.buscar_categoria_por_ruta(ruta_categoria)
        if categoria is None:
            return None
        recursivo = self.ventana.recursivo_aleatorio_de_item(item)
        candidatos = self._ventana_explorador.listar_registros_de_categoria(categoria, recursivo)
        if not candidatos:
            return None
        rutas_candidatas = {r.get("ruta") for r in candidatos if r.get("ruta")}
        evitar = rutas_recientes_en_historial(rutas_candidatas, max(0, len(rutas_candidatas) - 1))
        return self._ventana_explorador.elegir_aleatorio_de_categoria(categoria, recursivo, excluir_rutas=evitar)

    def _reproducir_item_aleatorio(self, item):
        registro = self._resolver_item_aleatorio(item)
        if registro is None:
            # Pedido explícito (mismo criterio que el resto de la app):
            # una categoría vacía, borrada, o sin Explorador nunca
            # rompe la emisión — se saltea sin sonar nada y sigue
            # directo con el próximo ítem real.
            registrar_evento(
                f"Publicidad: ítem aleatorio '{item.text(0)}' salteado "
                "(categoría vacía, borrada, o sin Explorador)"
            )
            self.ventana.marcar_reproduciendo_item(item)
            siguiente = self.ventana.tree.itemBelow(item)
            while siguiente is not None and not self._item_valido(siguiente):
                siguiente = self.ventana.tree.itemBelow(siguiente)
            self.ventana.marcar_siguiente_item(siguiente)
            self._avanzar()
            return

        self.ventana.tree.setCurrentItem(item)
        self.ventana.marcar_reproduciendo_item(item)
        self._item_fade_out_v1_disparado = None
        self.motor.reproducir(
            registro.get("ruta", ""),
            punto_inicio_ms=registro.get("punto_inicio_ms") or 0,
            punto_fin_ms=registro.get("punto_fin_ms"),
            ganancia_db=registro.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
            duracion_declick_ms=self.duracion_fade_in_declick_ms,
        )
        self.ventana.set_indicador_en_vivo(True)
        # El historial se registra con el archivo REAL resuelto (no el
        # ítem placeholder, que nunca tiene ruta propia) — es lo que
        # permite que el no-repetir funcione entre una reproducción y
        # la siguiente.
        registrar_reproduccion(
            "Publicidad", registro.get("titulo", ""), registro.get("codigo", ""), registro.get("ruta", ""),
        )
        registrar_evento(f"Publicidad: ítem aleatorio '{item.text(0)}' -> '{registro.get('titulo', '')}'")

    # ------------------------------------------------------------------
    # Comando HTH (Hora-Temperatura-Humedad) — pedido explícito,
    # terminología real de Dinesat (ver core/hth.py y
    # docs/manual_dinesat_visual.md). A diferencia del Comando FMT (no
    # ocupa tiempo de aire, dispara un callback y sigue directo), un
    # Comando HTH SÍ suena: concatena 2-3 clips de voz cortos con el
    # MISMO MotorAudio, uno atrás del otro, y recién cuando termina el
    # último vuelve al flujo normal (_avanzar()).
    # ------------------------------------------------------------------
    def _reproducir_comando_hth(self, item):
        parametro = self.ventana.parametro_comando_de_item(item)
        clips = resolver_comando_hth(self._ventana_explorador, parametro)

        self.ventana.marcar_reproduciendo_item(item)
        self._item_fade_out_v1_disparado = None
        siguiente = self.ventana.tree.itemBelow(item)
        while siguiente is not None and not self._item_valido(siguiente):
            siguiente = self.ventana.tree.itemBelow(siguiente)
        self.ventana.marcar_siguiente_item(siguiente)

        if not clips:
            # Pedido explícito ("Saltea todo el comando, sin sonar
            # nada"): falta un clip de voz, o no se pudo obtener el
            # dato de clima — nunca un anuncio a medias/incoherente.
            registrar_evento(
                f"Publicidad: comando HTH {parametro} salteado "
                "(falta un clip de voz o no se pudo obtener el clima)"
            )
            self._avanzar()
            return

        registrar_evento(f"Publicidad: comando HTH {parametro} -> {len(clips)} clip(s)")
        self._reproduciendo_hth = True
        self._cola_hth = list(clips)
        self._reproducir_siguiente_clip_hth()

    def _reproducir_siguiente_clip_hth(self):
        """Bug real corregido (pedido explícito, "no quiero silencios
        al final... deben ser enganchados"): antes se llamaba acá
        `motor.reproducir(ruta)` a secas, SIN el recorte de silencio
        ni el nivelado ya calculados al importar el clip — mismo tipo
        de bug ya corregido en el resto de la app, pero este rincón
        (Comando HTH) se había quedado afuera. Con clips de voz
        concatenados uno atrás de otro (HORA XX + MINUTOS XX, etc.),
        el silencio de cola SIN recortar de cada clip se sentía como
        un hueco muerto entre palabras. Ahora se busca el registro
        completo por ruta (mismo patrón que `_reproducir_item`) y se
        le pasa el análisis — fail-open si no hay `_ventana_explorador`
        o el registro no aparece (nunca romper el anuncio por esto)."""
        ruta = self._cola_hth.pop(0)
        analisis = {}
        if self._ventana_explorador is not None:
            registro = self._ventana_explorador.buscar_registro_por_ruta(ruta)
            if registro:
                analisis = registro
        self.motor.reproducir(
            ruta,
            punto_inicio_ms=analisis.get("punto_inicio_ms") or 0,
            punto_fin_ms=analisis.get("punto_fin_ms"),
            ganancia_db=analisis.get("ganancia_db") or 0.0,
            volumen_base=self._volumen_base,
        )
        self.ventana.set_indicador_en_vivo(True)

    def _on_click_play(self):
        """Botón verde grande (pedido explícito, paridad con Dinesat):
        "en realidad es Play pero además es siguiente en fundido...
        si no se está reproduciendo, pone en marcha el ítem elegido, y
        si lo vuelvo a apretar en ejecución, pasa al verde"."""
        if self.motor.esta_reproduciendo():
            self._avanzar_con_fundido()
        else:
            self._reproducir_seleccion_o_actual()

    def _avanzar_con_fundido(self):
        """"Siguiente con fundido": fundido de salida en el ítem
        actual, corte, y fundido de entrada en el que sigue —
        reutiliza toda la lógica ya probada de `_avanzar()` (respeta
        el límite de bloque automático y el freno por hora de un
        bloque futuro), solo le agrega el fundido cosmético. A
        diferencia de Ventana 2 (que superpone con un crossfade real
        de dos motores), acá es secuencial: Publicidad solo tiene UN
        MotorAudio, no hay infraestructura de doble motor todavía."""
        if self._fundido_en_curso:
            return
        if self._stop_diferido_armado:
            self._cancelar_stop_diferido()
        if not self.motor.esta_reproduciendo():
            self._avanzar()
            return
        registrar_evento("Publicidad: Siguiente con fundido")
        self._fundido_en_curso = True
        self.motor.fade_volumen_a(0, DURACION_FUNDIDO_MANUAL_SEGUNDOS)
        QTimer.singleShot(
            int(DURACION_FUNDIDO_MANUAL_SEGUNDOS * 1000) + 150,
            self._completar_avance_con_fundido,
        )

    def _completar_avance_con_fundido(self):
        self._fundido_en_curso = False
        self._fallos_consecutivos = 0
        # Pedido explícito ("quitá el fade al inicio, dejá solo el del
        # final... que los temas suenen más enganchados y con mejor
        # entrada"): _avanzar() ya arranca el ítem nuevo a su volumen
        # normal de una — antes acá se lo pisaba a 0 y se lo hacía
        # entrar en fundido; ahora entra directo, solo el ítem SALIENTE
        # (fundido ya disparado en _avanzar_con_fundido) sigue con su
        # fundido de salida.
        self._avanzar()

    def _reproducir_seleccion_o_actual(self):
        # Pedido explícito: el Play manual de Ventana 1 SIEMPRE corta
        # Emisión con fundido, aunque esté sonando y aunque el
        # Automático esté activo — "pasar de la ventana 2 a la 1
        # haciendo play" es una acción explícita del operador, no algo
        # que el botón STOP (bloqueado con Automático) deba impedir.
        if self.al_arrancar_manual is not None:
            self.al_arrancar_manual()

        # Prioridad: si ya hay algo marcado como "en reproducción"
        # (armado en rojo), reanuda/dispara ese; si no, usa la
        # selección del árbol; si tampoco hay selección, arranca por
        # el primer ítem reproducible.
        item = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem() \
            or self.ventana.primer_item_reproducible()

        if item is not None and item.parent() is None:
            # Es el TÍTULO de un bloque (nodo de nivel superior), no
            # una tanda — pedido explícito: seleccionar el bloque y
            # apretar Play debe reproducir ESE bloque horario
            # completo, desde su primer ítem reproducible.
            registrar_evento(f"Publicidad: Play sobre el bloque '{item.text(0)}'")
            self._reproducir_primero_del_bloque(item)
            return

        registrar_evento(f"Publicidad: Play (ítem objetivo: {item.text(0) if item else 'ninguno'})")
        self._reproducir_item(item)
        self._asegurar_rojo_y_verde()

    def _primer_item_valido_de(self, item_bloque):
        for i in range(item_bloque.childCount()):
            candidato = item_bloque.child(i)
            if self._item_valido(candidato):
                return candidato
        return None

    def _reproducir_primer_item_de_bloque(self, item_bloque, primero):
        """Arranca `primero` y deja el verde (item_siguiente) apuntando
        DENTRO de `item_bloque` — nunca a un ítem de otro lado.

        Bug real corregido (pedido explícito: "al abrirse reproduzca
        todo el bloque horario correspondiente" — en la práctica solo
        sonaba el primer ítem y saltaba directo a Emisión): un verde
        restaurado de una sesión anterior (playlist_publicidad.json),
        o dejado por el operador sobre OTRO bloque, podía seguir
        "pareciendo válido" (sigue en el árbol, tiene ruta, sin
        vigencia vencida) — `_asegurar_rojo_y_verde()` por diseño NO
        pisa un verde que ya luce válido (para no interferir con una
        elección manual del operador), así que ese verde stale
        quedaba apuntando afuera del bloque recién disparado. En
        `_avanzar()`, el freno "no cruzar de bloque"
        (`candidato.parent() is not self._bloque_automatico_actual`)
        entonces se disparaba INMEDIATAMENTE después del primer ítem
        — visualmente indistinguible de "solo suena uno y salta a la
        2". Acá, disparar un bloque nuevo (automático o manual) SIEMPRE
        fuerza que el verde apunte al próximo ítem válido DENTRO de
        este mismo bloque (o quede vacío si no hay más), sin importar
        qué hubiera marcado antes."""
        self._reproducir_item(primero)
        verde_actual = self.ventana.item_siguiente()
        if verde_actual is None or verde_actual.parent() is not item_bloque:
            siguiente = self.ventana.tree.itemBelow(primero)
            while siguiente is not None and not self._item_valido(siguiente):
                siguiente = self.ventana.tree.itemBelow(siguiente)
            if siguiente is not None and siguiente.parent() is item_bloque:
                self.ventana.marcar_siguiente_item(siguiente)
            else:
                self.ventana.marcar_siguiente_item(None)
        self._asegurar_rojo_y_verde()

    def _reproducir_primero_del_bloque(self, item_bloque):
        primero = self._primer_item_valido_de(item_bloque)
        if primero is None:
            return
        self._reproducir_primer_item_de_bloque(item_bloque, primero)

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

        primero = self._primer_item_valido_de(item_bloque)
        if primero is None:
            self._finalizar_bloque_automatico()
            return

        self._reproducir_primer_item_de_bloque(item_bloque, primero)

    def _finalizar_bloque_automatico(self):
        registrar_evento("Publicidad: bloque automático finalizado")
        self.motor.detener()
        self.ventana.set_indicador_en_vivo(False)
        # Pedido explícito: al volver a Emisión (cambio de ventana), la
        # barra de progreso de Publicidad no debe quedar congelada.
        self.ventana.resetear_reproduccion()
        bloque_terminado = self._bloque_automatico_actual
        callback = self._callback_bloque_finalizado
        self._bloque_automatico_actual = None
        self._callback_bloque_finalizado = None
        self.ventana.marcar_reproduciendo_item(None)
        # Pedido explícito (ciclo Automático, punto 4): al terminar el
        # bloque queda MARCADO (verde) el primer ítem del bloque que
        # sigue, sin reproducirlo, en espera de que llegue su hora.
        self._marcar_proximo_bloque_en_espera(bloque_terminado)
        if callback:
            callback()

    def _marcar_proximo_bloque_en_espera(self, bloque_terminado):
        """Deja en verde el primer ítem reproducible del bloque
        SIGUIENTE al terminado (si existe). Si el operador ya había
        encolado algo en verde FUERA del bloque que acaba de terminar,
        se respeta esa elección y no se pisa."""
        siguiente_actual = self.ventana.item_siguiente()
        if self._item_valido(siguiente_actual) and siguiente_actual.parent() is not bloque_terminado:
            return
        indice = self.ventana.tree.indexOfTopLevelItem(bloque_terminado) if bloque_terminado is not None else -1
        for i in range(indice + 1, self.ventana.tree.topLevelItemCount()):
            bloque = self.ventana.tree.topLevelItem(i)
            for j in range(bloque.childCount()):
                if self._item_valido(bloque.child(j)):
                    self.ventana.marcar_siguiente_item(bloque.child(j))
                    return
        # No hay más bloques con ítems: limpia un verde que haya
        # quedado apuntando adentro del bloque terminado.
        if siguiente_actual is not None and siguiente_actual.parent() is bloque_terminado:
            self.ventana.marcar_siguiente_item(None)

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
            # Pedido explícito (mismo criterio que Ventana 2): el verde
            # SIEMPRE se recalcula al de abajo del rojo recién elegido
            # a mano, descartando cualquier verde viejo que apuntara a
            # otro ítem distinto.
            self._recalcular_verde_tras_nuevo_rojo(item)

    def _recalcular_verde_tras_nuevo_rojo(self, item_rojo):
        """SIEMPRE recalcula el verde como el ítem de abajo del rojo
        recién elegido a mano — a diferencia de `_asegurar_rojo_y_verde()`
        (que respeta un verde ya válido, sin importar dónde apunte),
        acá se sobrescribe cualquier verde viejo apuntando a otra
        tanda/bloque."""
        candidato = self.ventana.tree.itemBelow(item_rojo)
        while candidato is not None and not self._item_valido(candidato):
            candidato = self.ventana.tree.itemBelow(candidato)
        self.ventana.marcar_siguiente_item(candidato)

    # ------------------------------------------------------------------
    def _avanzar_al_siguiente(self):
        registrar_evento("Publicidad: Siguiente")
        self._fallos_consecutivos = 0
        self._avanzar()

    def _on_fin_de_item(self):
        """Fin NATURAL de una tanda (señal finalizo_item del motor):
        continúa solo con la siguiente hasta agotar el bloque.

        Si en este momento hay un Comando HTH reproduciendo su cola de
        clips concatenados (ver _reproducir_comando_hth), este MISMO
        evento es el que avisa que un clip terminó — se sigue con el
        próximo clip de la cola en vez de tratarlo como el fin de una
        tanda real, y recién cuando la cola se agota se vuelve al
        flujo normal (_avanzar())."""
        self._fallos_consecutivos = 0
        if self._reproduciendo_hth:
            if self._cola_hth:
                self._reproducir_siguiente_clip_hth()
            else:
                self._reproduciendo_hth = False
                self._avanzar()
            return
        self._avanzar()

    def _notificar_fin_reproduccion(self):
        if not self.al_finalizar_reproduccion:
            return
        try:
            self.al_finalizar_reproduccion()
        except Exception as error:
            registrar_error(f"Publicidad: error en el callback de fin de reproducción: {error}")

    def _on_error(self, mensaje: str):
        registrar_error(f"[Publicidad] {mensaje}")
        if self._reproduciendo_hth:
            # Un clip roto/corrupto a mitad de un Comando HTH: no vale
            # la pena reintentar la cascada de errores normal (pensada
            # para tandas reales) — se aborta el resto del anuncio y
            # se sigue directo con el próximo ítem real, ya calculado
            # y marcado en verde por _reproducir_comando_hth().
            registrar_evento("Publicidad: comando HTH interrumpido por error de reproducción, salteando el resto")
            self._reproduciendo_hth = False
            self._cola_hth = []
            self._avanzar()
            return
        if not self.avanzar_en_error:
            if self._bloque_automatico_actual is not None:
                self._finalizar_bloque_automatico()
            else:
                self._notificar_fin_reproduccion()
            return
        self._fallos_consecutivos += 1
        if self._fallos_consecutivos >= self.reintentos_maximos:
            self.motor.detener()
            self._fallos_consecutivos = 0
            if self._bloque_automatico_actual is not None:
                self._finalizar_bloque_automatico()
            else:
                self._notificar_fin_reproduccion()
            return
        self._avanzar()

    def _asegurar_rojo_y_verde(self):
        """Pedido explícito: "siempre tendrá uno cargado en rojo para
        reproducir, y el verde siempre. Si hay 1 solo item, entonces
        será ese en rojo. Sino no [verde]" — nunca deja un hueco donde
        exista un ítem armado (rojo) y un segundo ítem reproducible
        disponible sin marcar "en cola" (verde). No pisa un verde ya
        puesto por el operador."""
        rojo = self.ventana.item_reproduciendo()
        if rojo is None:
            rojo = self.ventana.primer_item_reproducible()
            if rojo is None:
                return
            self.ventana.marcar_reproduciendo_item(rojo)

        verde = self.ventana.item_siguiente()
        if verde is not None and verde is not rojo and self._item_valido(verde):
            return

        candidato = self.ventana.tree.itemBelow(rojo)
        while candidato is not None and not self._item_valido(candidato):
            candidato = self.ventana.tree.itemBelow(candidato)
        self.ventana.marcar_siguiente_item(candidato)

    def _avanzar(self):
        if self._stop_diferido_armado:
            # Pedido explícito (Dinesat, "Stop diferido"): dejar
            # terminar el ítem en reproducción y detener TODO en vez
            # de avanzar — aplica sin importar si el disparo fue por
            # fin natural, Cut manual o cascada de error.
            self._cancelar_stop_diferido()
            self._detener()
            return

        item_base = self.ventana.item_reproduciendo() or self.ventana.tree.currentItem()

        # Prioridad: si hay un ítem marcado "en cola" (verde) válido,
        # es ese — el operador ya eligió qué sigue.
        candidato = self.ventana.item_siguiente()
        if candidato is None or not self._item_valido(candidato):
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
        elif candidato is not None and item_base is not None:
            # Pedido explícito: la reproducción continua "normal" (no
            # disparada por el modo AUTOMÁTICO) NUNCA debe cruzar a un
            # bloque DISTINTO cuya hora todavía no llegó — se detiene
            # ahí en vez de arrancarlo antes de tiempo.
            bloque_actual = item_base if item_base.parent() is None else item_base.parent()
            bloque_candidato = candidato.parent()
            if bloque_candidato is not None and bloque_candidato is not bloque_actual:
                if not self._bloque_ya_disponible(bloque_candidato):
                    registrar_evento(
                        f"Publicidad: reproducción continua detenida — el bloque "
                        f"'{bloque_candidato.text(0)}' todavía no llegó a su hora"
                    )
                    self.motor.detener()
                    self.ventana.marcar_reproduciendo_item(None)
                    self.ventana.set_indicador_en_vivo(False)
                    self.ventana.resetear_reproduccion()
                    # El ítem "en cola" (verde) sobre el bloque futuro
                    # queda puesto a propósito: es la señal de "listo,
                    # esperando su hora" (pedido explícito del ciclo
                    # Automático). Avisar al Scheduler para que, con
                    # Automático activo, vuelva a Emisión sin bache.
                    self._notificar_fin_reproduccion()
                    return

        if candidato is None:
            self.motor.detener()
            self.ventana.marcar_reproduciendo_item(None)
            self.ventana.set_indicador_en_vivo(False)
            self.ventana.resetear_reproduccion()
            self._notificar_fin_reproduccion()
            return

        es_comando = self.ventana.es_comando(candidato)
        self._reproducir_item(candidato)

        # Marca automáticamente el siguiente ítem reproducible como
        # "en cola" (verde) — mismo comportamiento que Ventana 2 al
        # avanzar naturalmente (no en un Play manual sobre el ítem ya
        # armado), da una vista previa continua de qué sigue. Si
        # `candidato` era un Comando, _reproducir_item() YA resolvió y
        # marcó todo esto (y probablemente avanzó más allá, en
        # cascada) al ejecutarlo — recalcularlo acá pisaría ese estado
        # ya correcto con uno viejo (marcaría en verde un ítem que en
        # realidad ya quedó sonando en rojo).
        if es_comando:
            return
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
            titulo = titulo_bloque_sin_prefijo_hora(hora, nodo_bloque.text(0))

            items = []
            for j in range(nodo_bloque.childCount()):
                hijo = nodo_bloque.child(j)
                if self.ventana.es_comando(hijo):
                    items.append({
                        "es_comando": True,
                        "tipo_comando": self.ventana.tipo_comando_de_item(hijo),
                        "parametro_comando": self.ventana.parametro_comando_de_item(hijo),
                    })
                    continue
                if self.ventana.es_aleatorio(hijo):
                    items.append({
                        "es_aleatorio": True,
                        "categoria_aleatorio": self.ventana.categoria_aleatorio_de_item(hijo) or [],
                        "recursivo_aleatorio": self.ventana.recursivo_aleatorio_de_item(hijo),
                    })
                    continue
                analisis = self.ventana.analisis_de_item(hijo)
                vigencia = self.ventana.vigencia_de_item(hijo)
                items.append({
                    "titulo": hijo.text(0), "duracion": hijo.text(1), "codigo": hijo.text(2),
                    "ruta": hijo.data(0, Qt.ItemDataRole.UserRole) or "",
                    "punto_inicio_ms": analisis.get("punto_inicio_ms") or 0,
                    "punto_fin_ms": analisis.get("punto_fin_ms"),
                    "ganancia_db": analisis.get("ganancia_db") or 0.0,
                    "fecha_inicio": vigencia.get("fecha_inicio"),
                    "fecha_fin": vigencia.get("fecha_fin"),
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
            else:
                # Pedido explícito: si no había un "siguiente" guardado
                # (o quedó inválido), igual debe quedar un verde
                # marcado en cuanto haya un segundo ítem reproducible.
                self._asegurar_rojo_y_verde()

            if bloques:
                registrar_evento(f"Playlist de Publicidad restaurada: {len(bloques)} bloque(s)")
        except Exception as error:
            registrar_error(f"Error restaurando playlist de Publicidad: {error}")
        finally:
            self._restaurando = False


class SchedulerAutomatico:
    """Coordinador del ciclo de la estación (pedido explícito, con el
    CONTEXTO de Santiago: "la estación funciona reproduciendo la
    ventana 2; a la hora del bloque horario de la ventana 1, corta la
    2, reproduce todo el bloque y vuelve a la 2"):

    - Los bloques de Publicidad se disparan por horario SIEMPRE (ya no
      depende del botón AUTOMÁTICO — punto 3 del pedido: "si no está
      activado, reproducirá el bloque horario y se quedará en
      silencio"). El disparo es por TRANSICIÓN de hora (la hora del
      bloque cae entre el tick anterior y el actual): un bloque creado
      a mitad del día con una hora ya pasada NO se dispara de golpe.
    - El botón AUTOMÁTICO gobierna la VUELTA a Emisión (Ventana 2): con
      el modo activo, al terminar cada bloque (o al agotarse la
      reproducción de Publicidad porque el próximo bloque es futuro),
      Emisión se reanuda (si estaba pausada por el bloque) o arranca
      desde el ítem en rojo / el primero. Con el modo apagado, el
      bloque suena igual a su hora y después queda en silencio.
    - Todas las transiciones Ventana 2 <-> bloque usan FUNDIDO
      (fade_volumen_a) superpuesto, nunca un corte seco ni un bache de
      silencio — pedido explícito "como debe sonar toda estación de
      radio". Al disparar un bloque, Emisión baja en fade mientras el
      bloque ya está sonando encima; al volver, Emisión sube en fade.
    - Al INICIAR el programa (punto a del pedido): reproduce solo el
      bloque VIGENTE — el de hora más tardía que ya pasó ("el último
      bloque menor más cercano a la actual"), nunca el primero del
      árbol. Si no hay bloque vigente y el modo AUTOMÁTICO está activo,
      arranca directamente Emisión.
    - A medianoche (o al iniciar) carga sola la programación resuelta
      para hoy (fecha específica > patrón semanal — ver
      config/settings.py:resolver_programacion_del_dia), si hay alguna
      guardada desde el Programador.
    """

    INTERVALO_MS = 1000
    RETARDO_INICIO_MS = 1200  # deja asentar la GUI/restauración antes del arranque automático

    def __init__(self, ventana_publicidad, gestor_publicidad, gestor_emision):
        self.ventana = ventana_publicidad
        self.gestor_publicidad = gestor_publicidad
        self.gestor_emision = gestor_emision

        self._dia_actual = QDate.currentDate()
        self._horas_disparadas_hoy = set()
        self._ultima_hora_tick = QTime.currentTime()
        # Pedido explícito (bug real reportado con audio real): un
        # bloque disparado por horario ya NO corta a Emisión a mitad
        # de tema — arma un "ceder" en GestorPlaylist
        # (ceder_control_al_terminar_item) y espera a que el ítem en
        # curso termine SOLO antes de arrancar el bloque. Esta bandera
        # evita que _tick() dispare un SEGUNDO bloque mientras el
        # primero todavía está esperando ese "ceder".
        self._esperando_liberar_emision = False

        # Fin de reproducción de Publicidad fuera de un bloque
        # disparado (freno por hora, fin del árbol, cascada de errores)
        # — mismo destino que el fin de un bloque disparado.
        self.gestor_publicidad.al_finalizar_reproduccion = self._al_terminar_publicidad

        # Aviso al operador cuando el arranque automático no encuentra
        # ningún bloque horario vigente (lo setea MainWindow — la GUI
        # muestra la advertencia, el core no crea widgets).
        self.al_no_encontrar_bloque = None

        self.ventana.automatico_cambiado.connect(self._on_automatico_cambiado)

        self._timer = QTimer()
        self._timer.setInterval(self.INTERVALO_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # Pedido explícito: al iniciar el programa, lo primero que
        # hace es buscar si hay programación guardada para HOY
        # (fecha específica > día genérico) y cargarla sola, sin
        # preguntar — igual que a medianoche. Esto pisa lo que
        # GestorPublicidad haya restaurado de la sesión anterior
        # (playlist_publicidad.json) SOLO si hay algo programado para
        # hoy; si no hay nada guardado, no toca lo restaurado.
        self._cargar_programacion_del_dia()

        # Los bloques cuya hora ya pasó quedan como "ya emitidos hoy"
        # — el arranque automático de abajo reproduce SOLO el vigente.
        self._marcar_bloques_pasados_sin_disparar()
        QTimer.singleShot(self.RETARDO_INICIO_MS, self._arrancar_al_iniciar)

    def detener(self):
        self._timer.stop()

    # ------------------------------------------------------------------
    def _duracion_fade(self) -> float:
        """Duración del fundido Ventana 2 <-> bloque: la misma
        configurada en Fade/Transiciones, con un piso para que nunca
        sea un corte seco."""
        try:
            configurada = float(self.gestor_emision.duracion_fade_segundos or 0)
        except (TypeError, ValueError):
            configurada = 0.0
        return max(0.8, configurada)

    def _bloque_tiene_items(self, bloque) -> bool:
        for j in range(bloque.childCount()):
            if self.gestor_publicidad._item_valido(bloque.child(j)):
                return True
        return False

    # ------------------------------------------------------------------
    def _on_automatico_cambiado(self, activo: bool):
        if not activo:
            return
        self._marcar_bloques_pasados_sin_disparar()
        # Pedido explícito: activar el botón AUTOMÁTICO a mano (no
        # solo al iniciar la app) debe arrancar YA el bloque horario
        # VIGENTE — ej. si son las 21:24, el bloque de las 21hs —
        # mismo criterio que _arrancar_al_iniciar(), reutilizado acá.
        # Guard contra doble disparo: si ya hay un bloque disparándose
        # (esperando que Emisión libere el control) o Publicidad YA
        # está sonando algo (un bloque en curso, o el operador puso a
        # mano un ítem a sonar), no se dispara otro encima — activar
        # el Automático nunca debe REINICIAR desde el principio algo
        # que ya está sonando.
        if self._esperando_liberar_emision or self.gestor_publicidad.motor.esta_reproduciendo():
            return
        bloque = self._bloque_vigente()
        if bloque is None:
            return
        hora_str = self.ventana.hora_de_bloque(bloque)
        if hora_str:
            self._horas_disparadas_hoy.add(hora_str)
        registrar_evento(
            f"Automático activado a mano: reproduciendo el bloque horario vigente '{bloque.text(0)}'"
        )
        self._disparar_bloque(bloque)

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
    # Arranque del programa (punto a): reproducir el bloque VIGENTE
    # ------------------------------------------------------------------
    def _bloque_vigente(self):
        """El bloque con la hora MÁS TARDÍA que ya pasó (<= ahora) y
        que tenga al menos un ítem reproducible. Nunca el primero del
        árbol porque sí."""
        ahora = QTime.currentTime()
        mejor, mejor_hora = None, None
        for bloque in self.ventana.bloques():
            hora_str = self.ventana.hora_de_bloque(bloque)
            hora = QTime.fromString(hora_str, "HH:mm:ss") if hora_str else QTime()
            if not hora.isValid() or hora > ahora:
                continue
            if not self._bloque_tiene_items(bloque):
                continue
            if mejor_hora is None or hora >= mejor_hora:
                mejor, mejor_hora = bloque, hora
        return mejor

    def _arrancar_al_iniciar(self):
        bloque = self._bloque_vigente()
        if bloque is not None:
            # Pedido explícito: un bloque horario SOLO se dispara con
            # el botón AUTOMÁTICO activo — antes se disparaba siempre
            # por horario, sin importar el estado del botón.
            if not self.ventana.esta_en_automatico():
                registrar_evento(
                    f"Inicio: hay un bloque horario vigente ('{bloque.text(0)}') pero "
                    "el Automático está apagado — no se dispara."
                )
                return
            registrar_evento(
                f"Inicio: reproduciendo el bloque horario vigente '{bloque.text(0)}'"
            )
            hora_str = self.ventana.hora_de_bloque(bloque)
            if hora_str:
                self._horas_disparadas_hoy.add(hora_str)
            self._disparar_bloque(bloque)
            return
        # No hay bloque vigente para reproducir: avisar al operador
        # (pedido explícito: "No se encontró Bloque Horario en este
        # momento en la programación") y, con Automático activo (el
        # estado por defecto al abrir), arrancar Emisión sin pedir
        # permiso, desde el ítem en rojo (el primero por defecto).
        if self.al_no_encontrar_bloque:
            try:
                self.al_no_encontrar_bloque()
            except Exception as error:
                registrar_error(f"Inicio: error mostrando el aviso de bloque faltante: {error}")
        if self.ventana.esta_en_automatico():
            registrar_evento("Inicio: sin bloque vigente — arranca Emisión (Automático activo)")
            self._reanudar_o_arrancar_emision()

    # ------------------------------------------------------------------
    def _tick(self):
        hoy = QDate.currentDate()
        if hoy != self._dia_actual:
            self._dia_actual = hoy
            self._horas_disparadas_hoy = set()
            self._ultima_hora_tick = QTime(0, 0, 0)
            self._cargar_programacion_del_dia()

        ahora = QTime.currentTime()
        # Ya hay un bloque esperando que Emisión libere el control
        # (ver _disparar_bloque) — no busca otro hasta que arranque.
        if not self._esperando_liberar_emision:
            for bloque in self.ventana.bloques():
                hora_str = self.ventana.hora_de_bloque(bloque)
                if not hora_str or hora_str in self._horas_disparadas_hoy:
                    continue
                hora_bloque = QTime.fromString(hora_str, "HH:mm:ss")
                if not hora_bloque.isValid():
                    continue
                # Disparo por TRANSICIÓN: la hora del bloque cayó entre
                # el tick anterior y este. Un bloque agregado durante
                # el día con hora ya pasada nunca se dispara
                # retroactivamente.
                if self._ultima_hora_tick <= hora_bloque <= ahora:
                    if not self._bloque_tiene_items(bloque):
                        continue  # un bloque vacío no corta nada
                    self._horas_disparadas_hoy.add(hora_str)
                    # Pedido explícito: "solo se dispara si el botón
                    # Automático está activo, si no, no se debe
                    # disparar" — antes disparaba SIEMPRE por horario,
                    # sin importar el estado del botón.
                    if not self.ventana.esta_en_automatico():
                        registrar_evento(
                            f"Publicidad: bloque de las {hora_str} no se disparó — Automático apagado"
                        )
                        continue
                    self._disparar_bloque(bloque)
                    break  # un bloque por chequeo alcanza y sobra
        self._ultima_hora_tick = ahora

    # ------------------------------------------------------------------
    # Transición Ventana 2 -> bloque de Publicidad
    # ------------------------------------------------------------------
    def _disparar_bloque(self, bloque):
        """Pedido explícito (bug real reportado con audio real): "que
        llegado el momento de reproducir el bloque horario de la
        ventana 1, deje terminar el ítem de la ventana 2... una vez
        que vaya a la ventana 1, el archivo y la reproducción de la
        ventana 2 debe liberarse" — ya NO corta el ítem de Emisión a
        mitad con un fundido: lo deja terminar SOLO y recién ahí
        libera Emisión de verdad (nunca la deja en pausa, resumible a
        medias — esa pausa era la causa real del bug) antes de
        arrancar el bloque."""
        self._esperando_liberar_emision = True
        self.gestor_emision.ceder_control_al_terminar_item(
            lambda: self._arrancar_bloque_ya_liberado(bloque)
        )

    def _arrancar_bloque_ya_liberado(self, bloque):
        self._esperando_liberar_emision = False
        self.gestor_publicidad.disparar_bloque(bloque, al_finalizar=self._al_terminar_publicidad)

    def cortar_emision_por_play_manual(self):
        """Pedido explícito (ronda anterior, sin cambios en esta):
        "cuando pase de la ventana 2 a la 1, haciendo play, cortará en
        fade la reproducción de la ventana 2, incluso si está en
        automático" — a diferencia del bloque automático (que ahora
        espera a que termine el ítem), un Play manual es una decisión
        explícita del operador y corta YA MISMO, con el mismo fundido
        corto de siempre. Lo que sí cambió: ahora libera Emisión de
        verdad (detiene, nunca pausa) — mismo arreglo de fondo que el
        bloque automático, para que al volver arranque siempre fresco
        en vez de resumir un tema viejo a mitad."""
        motor_emision = self.gestor_emision.motor
        if not motor_emision.esta_reproduciendo():
            return
        duracion = self._duracion_fade()
        motor_emision.fade_volumen_a(0, duracion)
        QTimer.singleShot(int(duracion * 1000) + 150, self.gestor_emision.detener)

    def _al_terminar_publicidad(self):
        if not self.ventana.esta_en_automatico():
            # Punto 3 del pedido: sin el botón AUTOMÁTICO, el bloque
            # suena a su hora y después la estación queda en silencio.
            registrar_evento("Publicidad: fin de reproducción — Automático apagado, queda en silencio")
            return
        self._reanudar_o_arrancar_emision()

    def _reanudar_o_arrancar_emision(self):
        """Pedido explícito: Emisión ya NO se pausa en el handoff con
        Publicidad — se detiene de verdad (ver
        GestorPlaylist.ceder_control_al_terminar_item /
        cortar_emision_por_play_manual), así que volver acá SIEMPRE es
        un arranque "de cero": el ítem en punta (rojo), o una serie
        NUEVA del Musicalizador si un Comando FMT disparó una durante
        el bloque — nunca el resume de una posición vieja a mitad de
        tema."""
        motor = self.gestor_emision.motor
        duracion = self._duracion_fade()

        if motor.esta_reproduciendo():
            # Emisión ya está al aire por su cuenta (alguien la
            # arrancó mientras tanto): no hay nada que hacer.
            return

        if self.gestor_emision.panel.cantidad_items() == 0:
            registrar_evento("Automático: Emisión sin ítems — no hay nada para reproducir")
            return
        self.gestor_emision.reproducir_actual()
        objetivo = motor.obtener_volumen() or self.gestor_emision._volumen_base
        motor.set_volumen(0)
        motor.fade_volumen_a(objetivo, duracion)
        registrar_evento("Automático: Emisión arrancada desde el ítem armado, con fundido de entrada")

    # ------------------------------------------------------------------
    def _cargar_programacion_del_dia(self):
        from config.settings import resolver_programacion_del_dia

        contenido = resolver_programacion_del_dia(date.today())
        if not contenido:
            return
        self.ventana.cargar_bloques(contenido.get("bloques", []))
        self.gestor_publicidad._asegurar_rojo_y_verde()
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
