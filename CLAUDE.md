# CLAUDE.md — Contexto del proyecto para Claude Code

Este archivo se lee automáticamente cada vez que Claude Code arranca en
esta carpeta. Es el resumen de todo lo construido hasta ahora en
conversación con Santiago vía claude.ai, para que Code retome sin
tener que redescubrir nada.

## Qué es esto

**Auto-Radio Tuyú** (nombre de la app; el repo sigue llamándose
`RadioLinuxMadariaga`, no se renombró la carpeta/repo, solo lo que ve
el usuario): automatización radial para Linux, clon funcional de
Dinesat 9. Python + PySide6 (GUI) + python-vlc (audio) + pydub/ffmpeg
(análisis de audio) + JSON/QSettings (persistencia).
Repo: https://github.com/ElSelloTV/RadioLinuxMadariaga

Título de ventana / nombre de aplicación: "Automatizador Radio Linux -
by Santiago M. Escobar - Radio Tuyú Gral. Madariaga" (`gui/main_window.py`
`setWindowTitle`, `main.py` `setApplicationName`/`setApplicationDisplayName`).
Ícono (`assets/icono.png`) regenerado con Pillow — antes era un
placeholder que se veía como una cruz; ahora es una torre de
transmisión con ondas de radio sobre medallón oscuro con anillo rojo.
`assets/radiolinuxmadariaga.desktop` actualizado a juego (`Name=`/
`Comment=`). El nombre del repo/carpeta/instalador (`RadioLinuxMadariaga`)
NO cambió — Santiago no lo pidió, solo el nombre visible de la app.

Usuario: Santiago Martín Escobar — abogado, músico, operador de medios
(ElSelloTV/LU28 Radio Tuyú). Notebook con **Q4OS Linux**, hardware
modesto (Celeron N2820, 4GB RAM). Este programa es para su propia
radio, uso diario en producción.

## Cómo prefiere trabajar Santiago (aplica también en Code)

- Directo, sin vueltas. Código **completo**, listo para copiar/pegar,
  nunca resumido ni truncado.
- Si hay varios archivos, preferible dejarlos armados en disco (acá ya
  estamos en el repo, así que directamente escribir/editar los
  archivos reales).
- Antes de escribir código nuevo: **correr y probar** (smoke test con
  `QT_QPA_PLATFORM=offscreen`, ver sección de testing más abajo).
  Santiago valora mucho que las cosas se prueben antes de entregarlas,
  no solo que compilen.
- Explicaciones breves de qué se hizo, sin relleno.
- **Pedido explícito: hacer `git push` ante todo cambio.** No dejar
  trabajo terminado sin subir a `claude/radio-app-design-yu3mcp` (y
  avisar si hace falta fusionarlo a `main` para que el botón
  Actualizar de Configuración lo traiga — main no se actualiza sola).

## Arquitectura (estricta separación GUI / core / config)

```
main.py                    # punto de entrada, mínimo
gui/                        # SOLO interfaz — nunca lógica de audio acá
  main_window.py             # ventana raíz, arma splitter de las 3 ventanas
  ventana_publicidad.py       # Ventana 1 (izquierda)
  ventana_emision.py          # Ventana 2 (centro) — envoltorio de panel_reproductor.py
  ventana_explorador.py       # Ventana 3 (derecha) — categorías + archivos
  ventana_auxiliar.py         # ventana flotante secundaria — también envoltorio
  ventana_programador.py      # editor de programaciones horarias
  ventana_configuracion.py    # QTabWidget con toda la config
  panel_reproductor.py        # UI reutilizable: contadores+controles+lista
  common_widgets.py           # ArbolConDrop / ArbolOrigenArrastre / configurar_columnas_ajustables
  dialogo_agregar_archivo.py  # modal al agregar un tema a la biblioteca
  estado_ui.py                # persistencia de splitters/columnas (QSettings INI)
  styles.py                   # TODO el QSS y las paletas de color viven acá

core/                        # lógica y motor de audio — nunca widgets acá
  audio_engine.py             # MotorAudio (python-vlc), degrada si no hay libvlc
  gestor_emision.py           # TODO el motor de Ventana 2/Auxiliar (GestorPlaylist) + su persistencia
  playlist_manager.py         # GestorPublicidad / GestorExplorador / SchedulerAutomatico
  analizador_audio.py         # recorte de silencios + nivelado (pydub/ffmpeg)
  actualizador.py             # git fetch/pull + reinicio de la app + subir_log_a_git

config/
  settings.py                 # config general (JSON) + programaciones (JSON) + log de errores/eventos
  data/                        # generado en runtime, NO se versiona (.gitignore salvo subida manual del log)

assets/
  radiolinuxmadariaga.desktop # lanzador de escritorio
  icono.png                    # ícono (torre de transmisión + ondas de radio)

iniciar.sh                   # lanzador robusto usado por el ícono de escritorio
instalar.sh                  # clona/actualiza + venv + deps + lanzador
requirements.txt
```

**Regla de oro repetida varias veces en el desarrollo**: los manejadores
de Drag&Drop (`dragEnterEvent`, `dropEvent`, `startDrag`) son métodos
virtuales de C++. Asignarlos como atributo de instancia
(`widget.dropEvent = mi_funcion`) **no funciona** — hay que
subclasear de verdad. Por eso existen `ArbolConDrop` y
`ArbolOrigenArrastre` en `common_widgets.py`; todo el Drag&Drop de la
app pasa por ahí. Si Code necesita un nuevo widget con drag/drop,
seguir ese mismo patrón.

## Estado de cada ventana

### Ventana 1 — Publicidad
Árbol de bloques horarios (bloque -> tandas), reescrita a pedido
explícito para traer la misma robustez que ya tenía Ventana 2, con
algunos cambios: **sin Pisador ni reproductor Auxiliar** (exclusivos
de Ventana 2), y con un menú contextual propio orientado a
Programación + bloques (ver más abajo). Botón AUTOMÁTICO (rojo=ON,
contorno rojo permanente para ubicarlo mejor — ver abajo). Contadores
de tiempo arriba, frames "Ahora"/"Luego" con contorno rojo/verde,
controles Play/Pausa/Stop/Siguiente, barra de progreso/seek, lista al
final. `GestorPublicidad` en `core/playlist_manager.py` maneja todo
esto y el salto en cascada si un ítem falla.

**Máquina de estados en punta (rojo)/en cola (verde) — igual que
Ventana 2 (implementado, pedido explícito)**: doble click (o Enter,
`ArbolPublicidadConDrop.keyPressEvent` en `common_widgets.py`) sobre
una tanda, con el reproductor EN SILENCIO, la ARMA en rojo sin
arrancar sola — recién suena al apretar Play
(`GestorPublicidad._reproducir_seleccion_o_actual` usa
`ventana.item_reproduciendo()`, que apunta a la tanda ya armada). Con
el reproductor sonando, doble click/Enter encola en verde sin
interrumplir (antes, a propósito, Ventana 1 no tenía cola — este es
el cambio de comportamiento explícito de esta ronda). Al avanzar
naturalmente (fin de tanda / botón Siguiente / cascada de error) se
prioriza la tanda ya encolada en verde si hay una, y se marca
automáticamente la tanda siguiente como nueva candidata verde. Las
tandas rojo/verde (o un BLOQUE que contenga alguna) no se pueden
"Sacar" hasta liberarse (`VentanaPublicidad._bloqueado_por_reproduccion`,
recorre también los hijos — sacar un bloque que contiene la tanda al
aire está bloqueado igual que sacar la tanda sola).

**"Ahora"/"Luego" con contorno + barra de progreso (implementado,
pedido explícito, mismo patrón que Ventana 2)**: `lbl_titulo_actual`/
`lbl_titulo_siguiente` (`EtiquetaMarquesina`) dentro de `QFrame`
con `objectName` `frameAhora`/`frameLuego` — contorno rojo/verde
(`gui/styles.py`) alrededor de toda la fila, no solo el texto. Mismo
concepto aplicado también a Ventana 2 (`panel_reproductor.py`) en esta
misma ronda. `slider_progreso` es un `SliderBusqueda` (ver Ventana 2
más abajo — clic directo, no solo arrastre).

**Bug real corregido — el recorte de silencio nunca se aplicaba al
aire**: al arrastrar un tema desde el Explorador a Publicidad o
Emisión, antes solo viajaba la RUTA del archivo — el
`punto_inicio_ms`/`punto_fin_ms`/`ganancia_db` ya calculados por
`core/analizador_audio.py` se perdían en el camino, y solo se
aplicaban en el "Previo" de Ventana 3 (`GestorExplorador`). Corregido
guardando ese análisis junto al ítem (`ROL_ANALISIS_AUDIO` en
`gui/styles.py`, poblado por `VentanaPublicidad.agregar_tanda()` /
`PanelReproductor.agregar_item()`) y pasándolo a
`MotorAudio.reproducir()` en `GestorPublicidad._reproducir_item` /
`GestorPlaylist._reproducir_fila` — mismo patrón que ya usaba
`GestorExplorador`. Corregido en Ventana 1 Y Ventana 2 a la vez (raíz
común). `MainWindow._on_archivo_soltado_publicidad`/`_emision`/
`_auxiliar` ahora buscan el registro completo (no solo la ruta) para
threadear ese análisis al soltar el archivo.

**Persistencia de la playlist de Publicidad (implementado, pedido
explícito: "mismo tratamiento que Emisión")**: `GestorPublicidad(
persistir=True)` guarda en `config/data/playlist_publicidad.json`
(escritura atómica, debounce, mismo patrón que Emisión) — bloques +
tandas + análisis de audio + qué tanda estaba armada/en cola (por
índice `[indice_bloque, indice_tanda]`, ya que acá el árbol es
jerárquico, no una lista plana como en Ventana 2). Al restaurar, la
tanda armada NO arranca a sonar sola. Esto reemplazó los bloques de
ejemplo que traía la ventana al arrancar — una instalación nueva
arranca sin bloques, igual que ya se hizo con Ventana 2 y Ventana 3.

**Menú contextual completo (implementado, pedido explícito con
estructura fija)**: Crear/Modificar/Eliminar/Cargar Programación
(las cuatro, por ahora, simplemente abren el Programador que ya
existe — `VentanaPublicidad.solicitud_abrir_programador` conectada a
`MainWindow.abrir_programador`, hasta que se pida una lógica propia
para cada una), separador, **Sacar Item** (funcional, pide
confirmación gateada por `general.confirmar_antes_de_eliminar`,
bloqueado para tandas/bloques marcados), **Agregar Item**/
**Reemplazar Item** (visibles pero DESHABILITADAS a propósito — sin
lógica propia todavía, pedido explícito "andá agregando funciones ya
creadas, las demás las vamos a ir creando"), separador, **Crear
Bloque Nuevo** (funcional, título por defecto `"Bloque: HH:MM:SS"`
con la hora actual, pide confirmación siempre — no gateada por el
flag, ya que es una acción nueva y poco frecuente).

**Modo AUTOMÁTICO real (implementado)**: cada bloque guarda su hora
real como dato (`ROL_HORA_BLOQUE` en `ventana_publicidad.py`, no solo
como texto en el título). `SchedulerAutomatico`
(`core/playlist_manager.py`) es un QTimer de 1s que, con el modo
AUTOMÁTICO activo, dispara el bloque cuya hora ya llegó: pausa
Emisión (Ventana 2) si estaba sonando, reproduce el bloque completo
(`GestorPublicidad.disparar_bloque`, que NO cruza hacia el bloque
siguiente del árbol — se detiene al agotar los ítems de ESE bloque),
y reanuda Emisión sola al terminar (`pausar()` de `MotorAudio` es un
TOGGLE de libVLC, se usa la misma llamada para pausar y para
reanudar). Si el operador interviene a mano (doble click, Stop)
mientras un bloque automático está en curso, se da por terminado
igual (no deja Emisión pausada para siempre). Activar el modo a
mitad de la tarde NO dispara de golpe los bloques que ya pasaron hoy
(se marcan como "ya emitidos" sin sonar, ver
`_marcar_bloques_pasados_sin_disparar`).

**Scheduler de medianoche (implementado)**: el mismo
`SchedulerAutomatico`, al detectar que cambió el día calendario,
llama a `resolver_programacion_del_dia()` (`config/settings.py`) y
si hay algo guardado para hoy (vía el Programador), reemplaza los
bloques de Publicidad con `ventana_publicidad.cargar_bloques(...)`.
Si no hay nada guardado para el día, no toca lo que ya estaba
cargado.

**Selección múltiple + indicador "en vivo" (implementado)**: el
árbol admite Ctrl/Shift+click (`ExtendedSelection`); menú contextual
"Quitar de la lista" opera sobre todos los seleccionados a la vez.
`IndicadorEnVivo` (`gui/indicador_en_vivo.py`) — círculo que titila
en rojo mientras hay audio sonando de verdad (no solo un ítem
marcado) — junto al estado; `GestorPublicidad` lo actualiza en cada
play/pausa/stop y también cada 500ms (self-corrige solo).

**Modo compacto (implementado)**: fuente 8pt + padding chico en el
árbol (`gui/styles.py`, selector `#tree_publicidad`) y el mínimo de
columna bajó de 45px a 24px — antes ese 45px no dejaba achicar más
las columnas, era el motivo real del reclamo "no me deja achicar".

**Contorno rojo permanente en el botón AUTOMÁTICO (implementado,
pedido explícito "para ubicarlo mejor")**: `gui/styles.py`,
`QPushButton#btnAutomatico[activo="true"/"false"]` — ahora ambos
estados tienen `border: 2px solid` en rojo (más claro cuando está ON,
el rojo de emisión cuando está OFF). El relleno rojo + cambio de
texto (`AUTOMÁTICO: ON`/`OFF`) al activarlo NO cambió, sigue siendo
la única señal de estado real — el contorno es solo para ubicar el
botón de un vistazo, no reemplaza esa señal.

### Ventana 2 — Emisión + Ventana Auxiliar
Ambas son un envoltorio delgado sobre `PanelReproductor`
(`gui/panel_reproductor.py`) — la misma clase de UI, reutilizada por
composición. Rojo = armado/sonando, verde = en cola. Doble click: en
silencio ARMA (rojo) sin arrancar solo, hace falta Play; sonando =
marca como "en cola" sin interrumpir (ver "Máquina de estados de
selección" más abajo para el detalle completo — cambió respecto de
como arrancó este panel). `GestorPlaylist` maneja avance normal,
avance manual, y cascada de errores (reintentos configurables antes
de rendirse), respetando "repetir lista al finalizar" de Configuración.

Botón "🎧 Auxiliar" en Emisión abre la ventana flotante — por decisión
explícita de Santiago, el Auxiliar **comparte la salida de audio
Master**, no es una salida física separada (aunque `MotorAudio` ya
soporta múltiples dispositivos si en algún momento se quiere separar).

**Título en reproducción**: `gui/etiqueta_marquesina.py` —
`EtiquetaMarquesina`, sticker de ancho fijo estilo Winamp
(`sizeHint()` constante pase lo que pase el texto, así nunca empuja
el panel/columna). Si el título no entra, se desplaza en marquesina
con un QTimer; si entra, queda centrado y quieto.

**Lista de reproducción**: `ArbolReproductorConDrop`
(`gui/common_widgets.py`) combina DOS drag&drop a la vez — acepta
soltar archivos desde el Explorador (como `ArbolConDrop`) Y permite
reordenar sus propios ítems arrastrándolos arriba/abajo
(`event.source() is self` distingue un caso del otro en
`dropEvent`). Columnas en ajuste LIBRE (`Interactive` en las tres,
sin Stretch forzado — pedido explícito, a diferencia del Explorador).

La fila "reproduciendo"/"siguiente" en `PanelReproductor` se
rastrea por **referencia al QTreeWidgetItem**, no por índice entero
(`self._item_reproduciendo` / `self._item_siguiente`; `fila_x()`
hace `indexOfTopLevelItem()` al vuelo). Es lo que hace que sobreviva
sin romperse a una reordenada por arrastre — el índice numérico de
un ítem cambia en cualquier momento, el objeto no.

**Reordenar por arrastre NUNCA anida** (`ArbolReproductorConDrop._reordenar_manual`
en `gui/common_widgets.py`): el `dropEvent` nativo de QTreeWidget, si
soltás justo "sobre" otra fila (indicador `OnItem`), por defecto la
anida como HIJA — eso creaba un sub-árbol no deseado. Corregido no
delegando en `super().dropEvent()` para el caso interno: se calcula
la posición a mano (usando `dropIndicatorPosition()` solo para
decidir antes/después) y siempre se reinserta como HERMANO de nivel
superior con `takeTopLevelItem`/`insertTopLevelItem`. Anidar (el
"↳" tabulado) es EXCLUSIVO del motor de Pisador, nunca un efecto
secundario de reordenar. Si el tema arrastrado tenía su propio
Pisador, viaja con él (`takeTopLevelItem` preserva el subárbol).

Menú contextual (clic derecho) en la lista: **Quitar de la lista**
(solo saca el ítem de ahí, no toca la biblioteca), **Información**
(propiedades + ubicación, con bitrate/frecuencia si mutagen puede
leerlo), **Agregar/Quitar Pisador**, **Eliminar de la biblioteca**
(definitivo, con advertencia — ver motor de Pisador abajo).

**Motor "Agregar Pisador"** (`core/playlist_manager.py` —
`GestorPlaylist`): un tema musical puede tener anidado, tabulado
debajo en el árbol, un archivo de género **Pisador** (como mucho
uno por tema; agregar otro reemplaza al anterior). Al arrancar ese
tema: se reproduce el Pisador en un segundo `MotorAudio` en paralelo
(`self.motor_pisador`) superpuesto sobre el inicio, el tema principal
baja `pisador_bajada_db` dB (configurable en Configuración →
Reproducción y Automatización, -4dB por defecto) y vuelve a su
volumen original apenas termina el Pisador
(`motor_pisador.finalizo_item` → `_on_pisador_finalizado`). Si se
avanza a otro tema mientras el Pisador sigue sonando, se corta y el
volumen se restaura antes de arrancar lo nuevo
(`_cancelar_pisador_en_curso`). Solo se puede asignar un archivo de
género "Pisador" (tanto por el diálogo — `gui/dialogo_elegir_pisador.py`,
que filtra `listar_registros_por_genero("Pisador")` — como al
soltarlo por drag&drop directo sobre un tema, chequeado por género
en `MainWindow._on_archivo_soltado_emision`/`_auxiliar`).
Aplica igual en Ventana 2 y en la Auxiliar (misma clase compartida).

**Crossfade (implementado)**: con `crossfade_activado` en
Configuración → Fade/Transiciones, la transición NATURAL entre dos
temas (llegando al final, no Siguiente manual ni error/cascada) se
superpone en vez de cortar seco. Se dispara CON ANTICIPACIÓN —
`MotorAudio.restante_ms_cambio` (nueva señal, considera
`punto_fin_ms` si el tema fue analizado) avisa a `GestorPlaylist`
cuando falta `duracion_fade_segundos` para el final, y ahí se llama
`MotorAudio.crossfade_a()`. Como el motor "entrante" que arma
`crossfade_a()` es una instancia NUEVA, `GestorPlaylist.motor` se
reemplaza por ese entrante a mitad de la rampa (`_desconectar_motor`/
`_conectar_motor` reenganchan `posicion_cambiada`/`finalizo_item`/
`error_reproduccion`/`restante_ms_cambio` al motor correcto) — el
motor saliente sigue fundiéndose solo en paralelo hasta apagarse.
**Limitación conocida**: si el tema ENTRANTE por crossfade tiene su
propio Pisador, no se dispara (dos rampas de volumen peleando por el
mismo motor a la vez) — pendiente de resolver si hace falta.

**Bug real corregido — el Pisador no sonaba**: `GestorPlaylist.panel`
es la ventana WRAPPER (`VentanaEmision`/`VentanaAuxiliar`), no
`PanelReproductor` directo. `ruta_pisador_en_fila` existía en
`PanelReproductor` pero nunca se delegó en los wrappers — el código
tenía un `hasattr()` defensivo que absorbía el `AttributeError` en
silencio y el motor de Pisador jamás se disparaba, sin ningún error
visible. Corregido agregando la delegación en ambos wrappers Y
sacando el `hasattr` (ya no hace falta, y **taparía el mismo bug de
nuevo si volviera a faltar** — regla: cuando un wrapper delega en
`PanelReproductor`, delegar TODOS los métodos que el core necesita,
nunca confiar en que un `hasattr` lo salve).

**Fade en el Pisador (implementado)**: `MotorAudio.fade_volumen_a()`
(rampa por pasos con QTimer, mismo patrón que `crossfade_a`) — el
ducking del tema principal (bajar al arrancar el Pisador, subir al
terminar) y el corte del Pisador si se interrumpe ya NO son saltos
de volumen bruscos, son fades de `DURACION_FADE_PISADOR_SEGUNDOS`
(0.8s, constante en `core/gestor_emision.py`).

**Bug real corregido — "a veces el Pisador no se dispara"**: pasar
de tema en tema rápido (Siguiente varias veces seguidas, o una
cascada de errores) cancelaba un Pisador en curso y programaba su
detención DIFERIDA (`QTimer.singleShot`, para dejarlo terminar el
fade-out) — pero si un Pisador NUEVO arrancaba en el mismo
`motor_pisador` antes de que ese timer disparara, el timer viejo
terminaba cortando al Pisador nuevo (recién arrancado o ni
arrancado del todo) sin ningún error visible. Corregido con
`_generacion_pisador`, un contador que se incrementa en cada
cancelación/disparo nuevo: la detención diferida
(`_detener_pisador_si_generacion_vigente`) solo se ejecuta si la
generación no cambió mientras tanto — si cambió, ya hay un Pisador
más nuevo en curso y no hay que tocarlo. Probado simulando avance
rápido por 3 temas con Pisador cada uno: el último en sonar siempre
es el correcto, nunca uno de los intermedios cortado por un timer
viejo.

**Selección múltiple + arrastre múltiple (implementado)**: lista con
`ExtendedSelection`; Quitar/Eliminar en el menú contextual operan
sobre toda la selección. El reordenar por arrastre se DESHABILITA a
propósito con 2+ seleccionados (evita mover "un poco cada uno" de
forma confusa) — la selección múltiple ahí sirve para arrastrar
varios temas juntos hacia otra ventana o para acciones en lote, no
para reordenar.

**Barra de progreso / seek (implementado, SOLO Ventana 2, no
Auxiliar)**: `PanelReproductor(mostrar_barra_progreso=True)` agrega
un `SliderBusqueda` 0-1000‰ (ver más abajo). `GestorPlaylist` lo
alimenta desde `restante_ms_cambio` + `MotorAudio.duracion_total_ms()`,
y al soltar el slider llama `MotorAudio.buscar_posicion_ms()`. La
gating de "solo Ventana 2" es por
`hasattr(self.panel, "solicitud_buscar_posicion")` — `VentanaAuxiliar`
a propósito NO expone esa señal/método.

**Click directo en la barra de progreso (implementado, pedido
explícito "si hay clic más adelante, la barra avance a ese
momento")**: antes solo arrastrar el mango adelantaba — un click en
cualquier otro punto del surco solo movía un "page step" (comportamiento
por defecto de `QSlider`), no saltaba al punto exacto. `SliderBusqueda`
(`gui/common_widgets.py`) sobrescribe `mousePressEvent`: si el click
no fue directo sobre el mango, calcula la posición con
`QStyle.sliderValueFromPosition` y hace `setValue()` ahí mismo antes
de dejar que Qt siga con su manejo normal (así arrastrar desde ese
punto nuevo sigue funcionando igual que siempre). La reutilizan tanto
la barra de Ventana 2 (`slider_progreso`) como la del previo de
Ventana 3 (`slider_preview`) — mismo widget, un solo lugar con la
lógica.

**Etiquetas "Ahora"/"Luego" (implementado, pedido explícito "le
falta robustez a la selección de los ítems")**: además del color de
fila (rojo/verde), `PanelReproductor` ahora muestra el título en
texto plano — `lbl_titulo_actual` ("Ahora:", ya existía) y
`lbl_titulo_siguiente` ("Luego:", nuevo), actualizados desde
`marcar_reproduciendo()`/`marcar_siguiente()` y limpiados a texto
vacío si no hay ítem marcado. Da una segunda confirmación textual de
qué está sonando y qué viene después, sin depender solo de ubicar la
fila coloreada en la lista. **Contorno rojo/verde (ronda siguiente,
pedido explícito)**: cada fila vive en un `QFrame` (`frameAhora`/
`frameLuego`, `gui/styles.py`) con un borde del mismo color que la
fila en la lista — mismo concepto aplicado también a Ventana 1.

**Motor de Ventana 2 en archivo aparte (implementado, pedido
explícito de cara a la futura programación automática)**: `GestorPlaylist`
se mudó de `core/playlist_manager.py` a `core/gestor_emision.py` —
archivo dedicado, separado de Publicidad/Explorador/Scheduler. Cuando
se implemente la carga automática de ítems por plantilla, esa lógica
nueva va ACÁ, sin tocar el resto del motor.

**Máquina de estados de selección — "en punta" (rojo) / "en cola"
(verde) (implementado, pedido explícito)**: cambio de comportamiento
respecto de antes — doble click (o **tecla Enter**, nueva,
`ArbolReproductorConDrop.keyPressEvent` en `common_widgets.py`) sobre
un ítem, estando el reproductor EN SILENCIO, ya NO arranca a sonar
solo: solo lo marca "en punta" (rojo), listo para arrancar recién
cuando el operador aprieta Play (`GestorPlaylist.reproducir_actual`
usa `panel.fila_reproduciendo()`, que ahora apunta al ítem ya
armado). Con el reproductor sonando, doble click/Enter sigue
marcando "en cola" (verde) sin interrumpir — sin cambios ahí.
Bloqueos agregados: **`PanelReproductor.quitar_item` devuelve `False`
sin hacer nada** si el ítem está en rojo o verde (no se puede quitar
de la lista ni por el menú contextual ni por "Eliminar de la
biblioteca" hasta liberarse solo — se elige otro ítem, o termina su
reproducción); el ítem ROJO específicamente tampoco se puede
**mover por arrastre** (bloqueado en
`ArbolReproductorConDrop.startDrag`) ni **editar el Pisador** (opción
oculta del menú contextual mientras esté en rojo). Fix visual: el
resaltado de selección nativo de Qt (azul sólido) tapaba el
rojo/verde cuando esa fila también estaba seleccionada — corregido en
`gui/styles.py` (`#tree_reproductor::item:selected`) haciendo la
selección transparente con solo un borde, así el color de estado
siempre queda a la vista.

**Bug real corregido — "los ítems desaparecen" al reordenar por
arrastre**: `ArbolReproductorConDrop` necesita `dragDropMode =
DragDrop` (no `InternalMove`) porque también acepta arrastres
EXTERNOS desde el Explorador — pero la implementación base de
`QAbstractItemView.startDrag()`, al terminar un arrastre aceptado con
`MoveAction`, borra las filas ORIGINALES del modelo salvo que el modo
sea `InternalMove`. Como `_reordenar_manual` ya reinsertaba el ítem a
mano (`takeTopLevelItem`/`insertTopLevelItem`), ese borrado automático
posterior de Qt se disparaba IGUAL después, borrando el ítem recién
reordenado — el síntoma reportado era que el ítem "desaparecía" al
soltar (y confundía más si el mouse salía de la ventana durante el
arrastre). Corregido con `ArbolReproductorConDrop.startDrag()` propio
que arma y ejecuta el `QDrag` a mano, sin llamar a
`super().startDrag()` — así ese borrado automático de Qt nunca se
dispara, y `_reordenar_manual` sigue siendo la única lógica que mueve
ítems de lugar.

**Persistencia de la playlist de Emisión (implementado, pedido
explícito: "se borra toda la música cuando se cierra, corte de
luz")**: antes la lista de Ventana 2 era efímera (nunca se guardaba
en disco). Ahora `GestorPlaylist(persistir=True)` (SOLO Ventana 2, la
Auxiliar sigue efímera a propósito) escucha el modelo interno del
árbol (`rowsInserted`/`rowsRemoved`/`rowsMoved`/`dataChanged`) con un
debounce de 500ms y guarda en `config/data/playlist_emision.json`
(escritura atómica, mismo patrón que `biblioteca.json`) — ítems,
Pisador anidado si tenía, y qué fila estaba armada/en cola. Al
reabrir la app se restaura todo tal cual quedó, PERO el ítem "en
punta" no arranca a sonar solo (queda armado en rojo esperando un
Play manual) — ni siquiera al reiniciar el programa hay audio que
salga al aire sin que el operador apriete Play. De paso, esto
reemplazó los datos de ejemplo que traía Ventana 2 al arrancar
(`VentanaEmision._cargar_datos_demo`, eliminado) — una instalación
nueva arranca con la lista vacía de verdad.

### Ventana 3 — Explorador (la más elaborada, "terminada" según Santiago)

**Persistencia (implementado, pedido explícito de Santiago)**: toda
la biblioteca (categorías + archivos, recursivo) se guarda en
`config/data/biblioteca.json` vía `config/settings.py:
cargar_biblioteca()`/`guardar_biblioteca()`. Se guarda ante CADA
alta, baja, reemplazo o movimiento — no solo al cerrar la app
(`VentanaExplorador._guardar_biblioteca()`, llamado al final de
`_dar_de_alta_archivo`, `_reemplazar_archivo`, `_eliminar_archivo`,
`_on_archivo_soltado_en_categoria`, `eliminar_registro_por_ruta`,
`_nueva_categoria`/`_nueva_subcategoria`/`_eliminar_categoria`). El
único borrado real es manual. Al arrancar, si `biblioteca.json` no
existe todavía, arranca VACÍO (`_cargar_biblioteca_inicial`) — antes
se cargaban categorías demo (Música/Publicidad/Separadores/etc.) y se
persistían como base inicial; a pedido explícito ("ya es momento de
sacar los ítems de ejemplo, necesito probar con música real") esas
categorías de ejemplo ya no se crean solas. Un `biblioteca.json` YA
EXISTENTE de una instalación anterior nunca se toca por esto — solo
afecta instalaciones nuevas.

**Escritura atómica ante corte de luz**: `config/settings.py:
_guardar_json_atomico()` escribe a un `.tmp` y lo renombra encima
del archivo definitivo con `os.replace()` (atómico en Linux) — así
un corte de luz o apagado forzoso a mitad de la escritura nunca deja
un JSON corrupto/truncado: o queda la versión anterior completa, o
la nueva completa. La usan `guardar_configuracion()`,
`guardar_programaciones()` Y `guardar_biblioteca()` — probado
matando el archivo `.tmp` a mitad de escribir y confirmando que el
definitivo no se toca hasta que el `.tmp` está completo.

- Categorías a la izquierda (`tree_categorias`, ahora `ArbolConDrop`),
  **sin límite de niveles** de subcategoría. Cada categoría guarda su
  lista de archivos directamente en el propio `QTreeWidgetItem`
  (rol `ROL_ARCHIVOS`), no en un diccionario plano — así no hay
  límite de profundidad ni colisión de nombres.
- Archivos a la derecha (`tree_archivos`, `ArbolOrigenArrastre`),
  columnas **Duración/Título/Artista/Categoría/Código** (orden
  pedido explícito; "Categoría" es el género de siempre, solo
  renombrado en el header), **movibles** (`header.setSectionsMovable`)
  y fuente 8pt (`gui/styles.py`, selector `#tree_archivos`), coloreadas
  por género: Música=verde, Publicidad=amarillo, Separador=naranja,
  Pisador=violeta, Artística=azul (`gui/styles.py:GENERO_COLORES`).
  `registro["duracion"]` se calcula una vez (mutagen) y queda
  cacheado en el registro; los registros viejos sin ese campo se
  migran solos la primera vez que se muestran.
- **Selección múltiple** (`ExtendedSelection`) en `tree_archivos`:
  arrastrar varios a la vez exporta varias URLs de una
  (`ArbolOrigenArrastre.startDrag`), y Eliminar borra todos los
  seleccionados con una sola confirmación.
- **Drag&Drop interno/externo unificado y en LOTE**:
  `_on_archivos_soltados_en_categoria` recibe la lista completa de
  rutas soltadas de una vez (`ArbolConDrop.archivos_soltados`, señal
  nueva además de la de a uno). Si la ruta YA es un registro
  conocido de la biblioteca (`buscar_registro_por_ruta`), es un
  MOVIMIENTO entre categorías; si NO lo es (viene de afuera, ej. el
  explorador de archivos del sistema), es una IMPORTACIÓN — con 1
  archivo va al diálogo de siempre, con 2+ va a
  `DialogoAgregarArchivosMasivo` (un solo diálogo de categoría+género
  para todo el lote, título derivado del nombre de archivo).
- Al agregar UN archivo se abre `DialogoAgregarArchivo`: elegir
  categoría (combo jerárquico con sangría), nombre editorial (puede
  diferir del archivo fuente), artista, género. El código correlativo
  se calcula solo: prefijo por género (`GENERO_PREFIJOS_CODIGO`) +
  número correlativo **dentro de esa categoría específica**. El botón
  "＋ Agregar" también acepta selección múltiple en el diálogo de
  archivos del sistema — con 2+ elegidos salta directo al flujo
  masivo de arriba.
- **Búsqueda** (`gui/ventana_explorador.py:_buscar`/`_limpiar_busqueda`):
  barra debajo del título con lupa (clic) y Enter, filtra TODA la
  biblioteca por título/artista sin importar la categoría y muestra
  los resultados en el mismo `tree_archivos`; mientras tanto
  `tree_categorias` se deshabilita para no mezclar estados. Limpiar
  la búsqueda vuelve a la categoría que estaba seleccionada.
- **Expandir/Restaurar** (`gui/ventana_explorador.py` botón +
  `MainWindow._alternar_expansion_explorador`): la Ventana 3 puede
  ocupar casi toda la pantalla principal (colapsa Publicidad/Emisión
  a un costado con `splitter.setSizes([1, 1, total])`, guardando los
  tamaños previos) y volver con el mismo botón. Dueña del splitter es
  `MainWindow`, no la ventana — por eso es un signal/callback, no un
  método local.
- Botón de preescucha se llama **"▶ Previo"**, no "Play" (a propósito,
  para no confundirlo con la reproducción real al aire de Ventana 1/2).
- Menú contextual (botón derecho): Importar, Exportar, Reemplazar,
  Eliminar (en lote si hay selección múltiple), Editar (abre el
  editor de audio predeterminado del
  sistema vía `QDesktopServices`; si no hay ninguno asociado, ofrece
  elegir un ejecutable a mano).
- Botones Previo/Stop de preescucha (`GestorExplorador`).
- Columnas: última columna (Código) en modo `Stretch` +
  `setMinimumSectionSize` para que nunca quede tapada al
  redimensionar (ver `configurar_columnas_ajustables` en
  `common_widgets.py`) — esto fue un bug reportado explícitamente por
  Santiago y ya está resuelto.

**Indicador de previo + guard contra reproducción accidental por
arrastre (implementado)**: Santiago reportó que el previo "se dispara
sin querer" al arrastrar un archivo hacia otra ventana. Causa: el
`itemDoubleClicked` del árbol de archivos se disparaba también al
soltar un arrastre en ciertos casos. Solución de dos partes —
1) `ArbolOrigenArrastre.acaba_de_arrastrar(margen_ms=400)`
(`gui/common_widgets.py`) guarda `self._ultimo_arrastre_ms` al
iniciar cada `startDrag` y expone si pasó menos de 400ms desde el
último arrastre; `VentanaExplorador._on_doble_click_preview`
(reemplaza el lambda directo a `solicitud_play_preview.emit()`)
ignora el doble click si `acaba_de_arrastrar()` da True.
2) `IndicadorEnVivo` (el mismo círculo titilante ya usado en
Ventana 1/2) agregado junto al botón "▶ Previo"
(`ventana3.indicador_preview`, `set_indicador_en_vivo()`), así
además de evitar el disparo accidental, ahora hay señal visual clara
de "estoy escuchando el previo". `GestorExplorador`
(`core/playlist_manager.py`) quedó reescrito para actualizarlo desde
`posicion_cambiada`/`finalizo_item`, igual patrón que
`GestorPlaylist` en Ventana 2.

**Barra de progreso/seek del previo (implementado, pedido explícito
"la misma barra de reproducción en la ventana 3")**: `slider_preview`
(QSlider 0-1000‰) debajo de los botones Previo/Stop.
`GestorExplorador._actualizar_progreso` lo alimenta desde
`restante_ms_cambio` + `duracion_total_ms()`, y al soltar llama
`MotorAudio.buscar_posicion_ms()` vía la señal nueva
`solicitud_buscar_posicion_preview`. Mismo patrón de
"no pisar mientras el operador arrastra" que ya existía en Ventana 2
(`self._arrastrando_slider_preview`).

**Confirmación antes de reemplazar/eliminar/mover de categoría
(implementado, pedido explícito)**: Santiago pidió que "básicamente
casi todas las funciones (excepto reproducir y parar la emisión del
previo)" avisen antes de actuar, incluyendo mover un archivo de
categoría por drag&drop. Ya existía confirmación para Eliminar;
se agregó también en `_reemplazar_archivo()` (antes de pisar el
archivo de audio y volver a analizarlo) y en
`_on_archivos_soltados_en_categoria()` (antes de mover uno o varios
archivos ya conocidos de la biblioteca a otra categoría por
arrastre — la importación de archivos NUEVOS desde afuera sigue su
propio diálogo, no este). Todo gateado por el mismo flag existente
`config_general.json → general.confirmar_antes_de_eliminar`
(checkbox en Configuración, texto ampliado para reflejar que ahora
cubre más que "eliminar"). A propósito, reproducir/detener el previo
NUNCA piden confirmación (son acciones reversibles e inmediatas).

### Motor de agregado de tema musical (`core/analizador_audio.py`)
No destructivo: nunca reescribe el archivo original. Analiza con
pydub y guarda como metadata del registro:
`punto_inicio_ms` / `punto_fin_ms` (recorte de silencio de
entrada/salida, tolerancia configurable, 2s por defecto),
`punto_golpe_in_ms` / `punto_golpe_out_ms` (mismos puntos, reusados
como referencia de fade), `ganancia_db` (nivelado de volumen contra
un objetivo de -16 dBFS). `MotorAudio.reproducir()` acepta estos
parámetros y los aplica al reproducir (seek + volumen ajustado). Si
no hay pydub/ffmpeg instalados, degrada limpio (valores neutros, no
rompe el alta del archivo) — mismo patrón que MotorAudio con libvlc.

**Umbral de silencio configurable (implementado, pedido explícito
"que no haya baches, poner el valor en dB del silencio")**:
`config_general.json → reproduccion.umbral_silencio_dbfs` (-40 dBFS
por defecto), editable en Configuración → Reproducción y
Automatización junto a la tolerancia ya existente. **Por qué esto
nunca corta un silencio del MEDIO de la canción** (preocupación
explícita de Santiago): se usa `pydub.silence.detect_leading_silence`,
que escanea desde un extremo hacia adentro y se DETIENE en la primera
muestra no silenciosa — nunca llega a mirar la mitad del tema, sin
importar qué tan agresivo sea el umbral. El silencio de salida usa el
mismo escaneo sobre el audio invertido (`audio.reverse()`), misma
garantía. Además, `LIMITE_RECORTE_SILENCIO_SEGUNDOS` (20s, constante
en `analizador_audio.py`) pone un techo duro de cada lado, por si el
umbral queda mal calibrado contra un intro/outro largo y ambient que
no es realmente silencio. Probado con audio sintético (pydub +
`Sine`, sin necesitar ffmpeg): silencio inicial/final se recortan
bien, un "bache" de 300ms a mitad del tema queda intacto, y un
silencio de 30s pegado a un extremo se limita a los 20s del techo.

### Ventana Programador
Editor de programaciones: arrastrás desde el Explorador, armás
bloques horarios (hora + título), y guardás para una fecha específica
o para uno o varios días de la semana (checkboxes L-D). Botón
"📂 Cargar programación existente..." lista todo lo guardado y lo
vuelca en el editor.

**Regla de negocio importante**: al resolver qué programación aplica
un día dado, una **fecha específica siempre prevalece** sobre el
patrón semanal general de ese día (`config/settings.py:
resolver_programacion_del_dia`). Ya está probado con tests.

### Configuración (`gui/ventana_configuracion.py`)
QTabWidget con: Audio (dispositivo master/preescucha, volúmenes),
Fade/Transiciones (crossfade on/off + duración), Rutas (bibliotecas +
logs), Reproducción y Automatización (avanzar en error, reintentos,
repetir lista, modo automático al iniciar, tolerancia de silencio),
General (confirmaciones, reloj, tema), **Apariencia** (colores por
género, ver abajo), **Actualizaciones** (ver abajo), **Diagnóstico**
(log de errores, ver abajo). Todo persiste en
`config/data/config_general.json`. Deliberadamente **sin nada de
satelital/RDS** — Santiago fue explícito en que no lo necesita.

**Colores por género configurables (implementado, pedido explícito
"que en configuraciones pueda elegir los colores para las categorías,
incluso no poner color")**: alcance = los 5 géneros fijos (Música/
Publicidad/Separador/Pisador/Artística), no las categorías reales del
árbol (que son arbitrarias/ilimitadas). `config_general.json →
apariencia.colores_genero` (dict género→hex o `null` = sin color).
Tab Apariencia: un botón-swatch (`QColorDialog`) + checkbox "Sin
color" por género. `gui/styles.GENERO_COLORES` sigue existiendo como
default de fábrica (semilla del config la primera vez); en
runtime, Ventana 3 (`_pintar_por_genero`) y el Pisador anidado de
Ventana 2 (`PanelReproductor.agregar_pisador`) leen SIEMPRE la config
en vivo, nunca la constante. `VentanaExplorador.repintar_colores_genero()`
refresca la paleta y repinta las filas visibles, llamado desde
`MainWindow._aplicar_configuracion_en_vivo()` al guardar Configuración
— no hace falta reiniciar para ver el cambio. Como el color ahora lo
elige el operador (ya no es fijo por género), el contraste de texto
(blanco/negro) se calcula por luminancia (`gui/styles.color_texto_legible`)
en vez de una lista fija de géneros con texto oscuro.

**Bug real corregido — guardar Configuración cortaba la
reproducción**: `MainWindow._reinicializar_motores_audio()` (ya no
existe) recreaba los `GestorPlaylist`/`GestorPublicidad` con
`MotorAudio` NUEVOS y de paso llamaba `.detener()` a los que estaban
sonando — cualquier música al aire se cortaba solo con tocar
Configuración. Reemplazado por
`MainWindow._aplicar_configuracion_en_vivo()`: actualiza los
atributos (reintentos, crossfade, dB del Pisador, volumen) de los
gestores YA EXISTENTES en caliente, sin recrear nada; el dispositivo
de salida se cambia con `MotorAudio.set_dispositivo_salida()` sobre
el motor que ya está reproduciendo (solo si de verdad cambió,
comparando con el nuevo `MotorAudio.id_dispositivo()`). **Regla**:
la reproducción NUNCA se debe interrumpir salvo Stop manual o cerrar
el programa — cualquier acción futura sobre "aplicar configuración"
tiene que seguir este mismo patrón (mutar objetos vivos, jamás
recrear el `MotorAudio` que está sonando).

**Aviso al cerrar con audio al aire (implementado)**:
`MainWindow.closeEvent` chequea `motor.esta_reproduciendo()` en
Emisión/Publicidad/Auxiliar antes de cerrar; si hay algo sonando,
pregunta con Sí/No y cancela el cierre (`evento.ignore()`) si el
operador dice que no.

### Actualizador (`core/actualizador.py`)
`git fetch` + comparar HEAD local contra `origin/main` (o `master`),
`git pull --ff-only` para aplicar, y reinicio del proceso
(`QProcess.startDetached` + `app.quit()`). Si la carpeta no es un
clon git real, se deshabilita solo con un mensaje claro en vez de
fallar. Botón en Configuración → pestaña Actualizaciones.

### Sistema de log (`config/settings.py` + Configuración → Diagnóstico)
Pedido explícito tras un caso real: el Play de Ventana 2 dejó de
responder sin ningún error visible (cerrar y reabrir "solucionó" solo
en apariencia — inaceptable en una radio en vivo). `registrar_error()`
existía pero casi no se usaba; ahora es un log rotativo (`config/data/
log_aplicacion.txt`, rota a `.anterior.txt` pasados 2MB) con DOS
niveles: `registrar_error()` (errores) y `registrar_evento()` (Play/
Pausa/Stop, restauración de playlist, cierre cancelado, etc. — para
poder reconstruir la secuencia previa a un problema reportado).
Wireado en: `main.py` (inicio/cierre de la app + `sys.excepthook`
global — PySide6, si una excepción ocurre DENTRO de un slot como el
handler de un botón, por defecto la imprime a stderr y la app sigue
viva SIN avisar; eso es indistinguible para el operador de "el botón
no respondió", que es exactamente el síntoma reportado), `core/
gestor_emision.py` (Play/Pausa/Stop/errores de reproducción/
restauración de playlist), `MainWindow.closeEvent` (cierre cancelado
por emisión en curso). Configuración → pestaña **Diagnóstico**: ver
ruta/tamaño del log, botón "Ver log" (`QDesktopServices.openUrl`) y
botón **"Subir log a GitHub"** (`actualizador.subir_log_a_git`) — a
pedido explícito, esto es SOLO MANUAL, nunca automático en cada
cierre (decisión tomada con Santiago: menos riesgo de tocar git solo
en su PC sin que él lo sepa). `config/data/*.txt` está en
`.gitignore` a propósito (datos de cada instalación, no se versionan
solos); `subir_log_a_git` usa `git add -f` puntualmente SOLO cuando
el operador aprieta ese botón, para saltear ese ignore de forma
explícita. Si no hay red/credenciales, el commit local igual queda
hecho y el mensaje de error es claro sobre qué falló.

### Lanzador de escritorio (`iniciar.sh` + `assets/radiolinuxmadariaga.desktop`)
El ícono de escritorio no llama a `main.py` directamente: llama a
`iniciar.sh`, que redirige toda la salida a
`config/data/log_lanzador.txt` y muestra un aviso (`zenity`/`kdialog`/
`notify-send`, lo que haya disponible) si el proceso termina con
error. Esto es clave porque al lanzar desde un ícono no hay terminal
visible — sin esto, cualquier falla (venv roto, falta una dependencia)
es un doble click que "no hace nada" y no hay forma de diagnosticarlo.
`instalar.sh` detecta la carpeta de escritorio real vía
`xdg-user-dir DESKTOP` (con fallback a `~/Escritorio` o `~/Desktop`,
porque Q4OS en español usa "Escritorio") y marca el `.desktop` como
confiable (`gio set ... metadata::trusted true`) si el entorno lo
requiere.

## Persistencia de layout (`gui/estado_ui.py`)
Anchos de columna y posiciones de splitter (principal + interno del
Explorador) se guardan en `config/data/ui_state.ini` (QSettings
formato INI) al cerrar (`MainWindow.closeEvent`) y se restauran al
abrir. Ya probado entre "sesiones" (cerrar y reabrir el proceso).

**Bug real corregido — la ventana se iba de pantalla al maximizar**:
`restaurar_geometria_ventana()` hacía `widget.restoreGeometry(valor)`
a ciegas, sin validar contra la pantalla ACTUAL. Si la geometría
guardada venía de otro monitor/resolución, la ventana podía arrancar
parcialmente fuera de pantalla — y ahí el gestor de ventanas
maximizaba en base a esa posición inválida, perdiendo de vista los
controles de la derecha. Corregido con `_asegurar_dentro_de_pantalla()`,
que se llama siempre después de restaurar (o de la geometría inicial
por defecto) y reacomoda el rectángulo para que entre completo en
`screen().availableGeometry()`. **Ojo con el off-by-one**: el límite
derecho/inferior válido es `disponible.left() + disponible.width() -
ancho`, NO `disponible.right() - ancho` (`QRect.right()` devuelve
`x + width - 1`, no `x + width` — usar `right()` ahí corta la ventana
un píxel de más).

**Ventana 1/2 rediseñadas más compactas (pedido explícito, "otro
skin")**: los botones de transporte (Play/Pausa/Stop/Siguiente[/
Auxiliar]) pasaron de una fila horizontal larga a una **grilla de 2
columnas** (`QGridLayout` en `panel_reproductor.py` y
`ventana_publicidad.py`) — una fila de 4-5 botones en línea fijaba
un ancho mínimo grande que no dejaba achicar el panel NI notar el
botón "Expandir" de Ventana 3 (Publicidad/Emisión se negaban a
bajar de ~350-450px). Los relojes bajaron de 26pt a 14pt
(`gui/styles.py`), y `EtiquetaMarquesina` (el sticker del título en
Ventana 2) ahora tiene `minimumSizeHint()` propio de 40px en vez de
heredar los 220px de `sizeHint()` como mínimo real. Resultado medido:
`PanelReproductor.minimumSizeHint()` bajó a ~213px de ancho,
`VentanaPublicidad` a ~269px (antes ninguna bajaba de ~350-450px).

## Testing — cómo probar cambios sin display real

El entorno de desarrollo (sandbox de claude.ai) no tiene VLC ni
display gráfico, así que todo se probó así — recomendado seguir
haciéndolo en Code también antes de dar algo por terminado:

```bash
# sintaxis
python3 -m py_compile main.py gui/*.py core/*.py config/*.py

# arranque sin crashear (VLC puede no estar instalado, debe degradar
# limpio, no debe haber traceback)
QT_QPA_PLATFORM=offscreen timeout 6 python3 main.py

# para probar interacciones específicas (doble click, drag&drop
# simulado, guardado de config, etc.) armar un script suelto que
# importe MainWindow, parchee QMessageBox para que no bloquee, y
# llame los métodos internos directamente con QTimer.singleShot.
# Ver el historial de conversación para varios ejemplos de este
# patrón de test si hace falta reconstruir uno.
```

`MotorAudio` y `analizar_audio()` están diseñados para degradar sin
romper nada si falta `libvlc` o `pydub`/`ffmpeg` — cualquier código
nuevo que dependa de dependencias del sistema debería seguir el mismo
patrón (try/except amplio, mensaje claro, valores neutros de
fallback).

## Dependencias del sistema (no van en requirements.txt)

```bash
sudo apt install vlc libvlc-dev ffmpeg
```

`requirements.txt` (Python): PySide6, python-vlc, mutagen, pydub.

## Convención de entorno

Se usa **venv**, no `pip install` directo (el sistema es
externally-managed / PEP 668):

```bash
cd ~/RadioLinuxMadariaga
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Dirección futura (mencionado por Santiago, todavía no arrancado)

Antes de encarar los "motores principales" (programación/carga
automática de ítems por plantilla), Santiago adelantó que más
adelante quiere poder agregar **Módulos o Plugins** (siempre
aditivos, nunca reemplazando lo existente) para incorporar
funcionalidad nueva sin tocar el core. Todavía no se diseñó nada
concreto — el primer paso ya dado en esa dirección es la separación
`core/gestor_emision.py` (motor de Ventana 2) vs
`core/playlist_manager.py` (Publicidad/Explorador/Scheduler): cuando
se diseñe el sistema de plugins, mantener ese mismo espíritu de
"cada motor en su archivo, con una interfaz clara hacia GUI/config"
para que sea fácil enchufar algo nuevo sin tener que entender/tocar
todo el resto.

## Pendiente (roadmap acordado con Santiago, en orden de prioridad)

1. ~~Modo AUTOMÁTICO real~~ — implementado (`SchedulerAutomatico`,
   ver Ventana 1 más arriba). Falta probarlo con horarios reales en
   la notebook de Santiago (acá se probó simulando el reloj).
2. ~~Scheduler de medianoche~~ — implementado junto con el punto 1.
3. ~~Crossfade real~~ — implementado (ver Ventana 2 más arriba).
   Falta probarlo con audio real: acá se probó con motores
   simulados (sin VLC), verificar que se escuche bien en la práctica.
4. Sistema FMT (archivos de programación especial que cargan una
   playlist musical pregrabada) — mencionado en el pedido original,
   todavía no empezado.
5. UI de selección de dispositivo de audio ya tiene la API en
   `MotorAudio` (`listar_dispositivos`, `set_dispositivo_salida`) y
   el combo en Configuración, pero no se probó contra hardware real
   (el sandbox no tiene tarjeta de sonido).
6. Integrar crossfade + Pisador para cuando el tema ENTRANTE de un
   crossfade tiene su propio Pisador (limitación conocida, ver nota
   en Ventana 2).
7. ~~El Pisador no sonaba~~ — era un bug real de delegación faltante
   (ver Ventana 2 más arriba), corregido, y de paso se le agregó fade
   en vez de saltos de volumen. Falta confirmar con audio real que
   suene bien (acá se probó con motor simulado).
8. Ítems básicos de UI (selección múltiple, Ventana 3 expandible,
   import masivo, búsqueda, indicador en vivo, barra de progreso,
   modo compacto) — implementados, ver cada ventana más arriba.
9. ~~4 bugs urgentes de UX~~ — botón Expandir sin efecto visible,
   ventana maximizada se iba de pantalla, guardar Configuración
   cortaba la reproducción, columnas de Ventana 1/2 que no achicaban
   — los cuatro corregidos (ver notas en Ventana 1/2/Explorador y en
   `gui/estado_ui.py` más arriba).
10. ~~Ajustes de Ventana 3 + rebranding~~ — indicador de previo +
    guard contra reproducción accidental por arrastre, confirmación
    antes de reemplazar/eliminar/mover de categoría, barra de
    progreso/seek del previo, nombre de la app a "Auto-Radio Tuyú" /
    "Automatizador Radio Linux - by Santiago M. Escobar - Radio Tuyú
    Gral. Madariaga", ícono nuevo — implementado (ver Ventana 3 y
    encabezado más arriba). Falta que Santiago confirme en su
    notebook real cómo se ve/siente el ícono nuevo, si el margen de
    400ms del guard anti-arrastre es suficiente, y probar la barra
    de seek del previo con audio real (acá VLC no está disponible en
    el sandbox).
11. ~~Colores configurables + motores de Ventana 2~~ — colores por
    género editables en Configuración (con "sin color"), quitar los
    ítems de ejemplo de Ventana 2 (Auxiliar nunca tuvo), persistencia
    real de la playlist de Emisión (sobrevive cierre/corte de luz sin
    arrancar sola a sonar), arreglo del bug real de "los ítems
    desaparecen" al reordenar por arrastre, máquina de estados en
    punta (rojo)/en cola (verde) con Play manual obligatorio y
    bloqueos de eliminar/mover/editar, fix visual de la selección
    tapando el color de estado, motor de Ventana 2 movido a
    `core/gestor_emision.py`, y sistema de log rotativo con subida
    manual a GitHub — implementado (ver Ventana 2 y Configuración más
    arriba). Falta que Santiago lo pruebe con música real: el drag de
    reordenar con archivos de verdad, si el corte visual
    rojo/verde/seleccionado se ve bien en su pantalla, y confirmar que
    el próximo "no respondía" (si vuelve a pasar) ahora quede
    registrado en el log para poder diagnosticarlo sin acceso a su PC.
12. ~~Pisador intermitente + robustez de selección + seek por click +
    umbral de silencio configurable~~ — bug real de condición de
    carrera corregido (`_generacion_pisador`, ver Ventana 2 más
    arriba) para cuando se avanza de tema en tema rápido; etiquetas
    "Ahora"/"Luego" con el título en texto plano además del color de
    fila; `SliderBusqueda` con click directo (no solo arrastre) en
    ambas barras de progreso (Ventana 2 y previo de Ventana 3); umbral
    de silencio en dBFS configurable en Reproducción y Automatización,
    con techo de seguridad de 20s y garantía de que nunca recorta un
    silencio breve a mitad de la canción (solo mira los extremos) —
    implementado y probado con audio sintético real (pydub + tonos
    generados, sin necesitar ffmpeg). Falta que Santiago confirme con
    música real de su biblioteca: si el Pisador ahora dispara siempre
    al pasar de tema rápido, y si el umbral por defecto (-40 dBFS)
    necesita ajuste para sus archivos.
13. ~~Ventana 1 con la misma robustez de Ventana 2~~ — máquina de
    estados en punta (rojo)/en cola (verde) con Play manual
    obligatorio (cambio de comportamiento explícito respecto de como
    arrancó Publicidad), bloqueo de "Sacar" para tandas/bloques
    marcados, frames "Ahora"/"Luego" con contorno rojo/verde (también
    agregado a Ventana 2), barra de progreso/seek con clic directo,
    persistencia de la playlist de Publicidad (mismo tratamiento que
    Emisión, sin bloques de ejemplo en instalación nueva), botón
    AUTOMÁTICO con contorno rojo permanente, menú contextual completo
    (Crear/Modificar/Eliminar/Cargar Programación abren el Programador
    por ahora; Sacar Item funcional; Agregar/Reemplazar Item visibles
    pero deshabilitadas hasta que se pida esa lógica; Crear Bloque
    Nuevo funcional con confirmación) — implementado (ver Ventana 1
    más arriba). **Bug real corregido de paso, en Ventana 1 Y 2**: el
    recorte de silencio/nivelado calculado en Ventana 3 nunca se
    aplicaba al aire (solo en el Previo) — ahora viaja con el ítem
    (`ROL_ANALISIS_AUDIO`) y se pasa a `MotorAudio.reproducir()`.
    Log temporalmente más detallado (`registrar_evento` en cada
    acción de Publicidad) mientras Santiago prueba esta ronda — pidió
    volver a un nivel normal cuando avise. Falta que lo prueba con
    música real: Crear Bloque Nuevo + arrastre de tandas, el flujo
    completo armar/encolar/Play en Publicidad, y confirmar que ahora
    sí se note el recorte de silencio al aire en ambas ventanas.

## Cosas ya resueltas que NO hay que "redescubrir"

- El bug de Drag&Drop que no funcionaba (ver regla de oro arriba).
- **El Pisador no sonaba porque faltaba una delegación** (ver nota
  completa en Ventana 2): cuando un wrapper (`VentanaEmision`/
  `VentanaAuxiliar`) delega métodos en `PanelReproductor`, hay que
  delegar TODOS los que el core (`GestorPlaylist`) necesita — un
  `hasattr()` defensivo puede tapar el faltante en silencio sin
  ningún error visible. Si algo "no pasa nada" sin traceback, primero
  sospechar de una delegación incompleta entre wrapper y panel.
- La columna que se tapaba al redimensionar (Stretch +
  minimumSectionSize).
- `externally-managed-environment` de pip → usar venv siempre.
- `QProcess` está en `QtCore`, no en `QtWidgets` (error real que
  apareció durante el desarrollo).
- Confirmado con Santiago: sin satelital, sin RDS — el foco es
  publicidad + música automatizada, nada más.
- El ícono de escritorio no aparecía en Q4OS porque `instalar.sh`
  buscaba `~/Desktop` a mano y el sistema en español usa
  `~/Escritorio` — resuelto con `xdg-user-dir DESKTOP`.
- **Trampa real de PySide6 (¡importante, puede volver a morder!)**:
  `QTreeWidgetItem.setData(rol, objeto_python)` /`.data(rol)` para
  roles custom (por encima de `Qt.UserRole`) devuelve una **COPIA**
  del objeto Python guardado (probado empíricamente: dos llamadas a
  `.data()` seguidas dan listas Y dicts con identidad distinta).
  Cualquier código que compare `algo is registro` / `algo is not
  registro` contra un dict sacado de `.data()` en otra llamada NUNCA
  va a matchear — se rompe en silencio (el ítem "parece" borrado en
  la vista pero sigue en los datos persistidos, reaparece al
  refrescar la categoría). Esto ya rompía `_eliminar_archivo`,
  `_sincronizar_registro_en_categoria` (usado por Reemplazar) y
  `_on_archivo_soltado_en_categoria` en `ventana_explorador.py` —
  corregido comparando por `ruta` (clave estable), no por identidad
  de objeto. **Regla**: nunca comparar por identidad (`is`) un dict
  que salió de `item.data()`; comparar siempre por una clave de
  contenido estable (acá, `ruta`).
- **Otra trampa real de PySide6 — "los ítems desaparecen" al
  reordenar por arrastre**: si un `QTreeWidget` tiene
  `dragDropMode = DragDrop` (necesario para aceptar arrastres
  EXTERNOS además de reordenar los propios) y vos manejás la
  reordenada a mano en `dropEvent` (`takeTopLevelItem`/
  `insertTopLevelItem`), la implementación BASE de
  `QAbstractItemView.startDrag()` IGUAL borra las filas originales del
  modelo al terminar el arrastre con `MoveAction` — ese borrado
  automático solo se salta con `dragDropMode = InternalMove`, que acá
  no se puede usar (bloquearía los arrastres externos). Resultado: el
  ítem recién reordenado a mano se borra solo después, sin ningún
  error. **Regla**: si un árbol maneja su propia reordenada interna Y
  además acepta arrastres externos, hay que sobrescribir `startDrag()`
  también (armar y ejecutar el `QDrag` a mano, sin llamar a
  `super().startDrag()`) para que Qt no haga esa limpieza automática
  por su cuenta. Ver `ArbolReproductorConDrop.startDrag` en
  `gui/common_widgets.py`.
