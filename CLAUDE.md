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
- **Pedido explícito: el repo es público, `README.md` lleva un aviso
  de "PROYECTO EN DESARROLLO" y una línea "Última actualización:
  YYYY-MM-DD".** Actualizar esa fecha (formato ISO, fecha del día en
  que se hace el cambio) en CADA ronda que termine con push a `main`
  — no alcanza con pushear a la rama de trabajo, la fecha debe
  reflejar lo que ve cualquiera que mire el repo público.

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
estructura fija)**: Crear/Modificar/Eliminar Programación (por ahora
simplemente abren el Programador que ya existe —
`VentanaPublicidad.solicitud_abrir_programador` conectada a
`MainWindow.abrir_programador`, hasta que se pida una lógica propia
para cada una), separador, **Cargar Programación** (lógica propia,
ver abajo), separador, **Sacar Item** (funcional, pide confirmación
gateada por `general.confirmar_antes_de_eliminar`, bloqueado para
tandas/bloques marcados), **Agregar Item**/**Reemplazar Item**
(visibles pero DESHABILITADAS a propósito — sin lógica propia
todavía, pedido explícito "andá agregando funciones ya creadas, las
demás las vamos a ir creando"), separador, **Crear Bloque Nuevo**
(funcional, título por defecto `"Bloque: HH:MM:SS"` con la hora
actual, pide confirmación siempre — no gateada por el flag, ya que es
una acción nueva y poco frecuente).

**"Cargar Programación" con lógica real + carga automática diaria
(implementado, pedido explícito)**: `resolver_programacion_del_dia()`
(`config/settings.py`, ya existía) resuelve la programación vigente
para una fecha con la regla **fecha específica > patrón semanal
genérico** — se reutiliza en dos lugares distintos:
1) **Manual** (menú contextual → Cargar Programación,
`VentanaPublicidad.solicitud_cargar_programacion_hoy` →
`MainWindow._cargar_programacion_de_hoy_manual`): resuelve la
programación de HOY y, si encuentra una, PIDE CONFIRMACIÓN antes de
reemplazar los bloques actuales (siempre, no gateado por el flag de
confirmaciones — es una acción explícita del operador); si no hay
nada guardado para hoy, avisa con un mensaje informativo.
2) **Automática** (`SchedulerAutomatico`): ahora corre también en
`__init__` (antes solo se disparaba al detectar cambio de día
calendario mientras la app ya estaba corriendo) — pedido explícito
"a las 00 horas, O CUANDO INICIE EL SISTEMA". Al iniciar, si hay una
programación resuelta para hoy, reemplaza SIN PREGUNTAR lo que
`GestorPublicidad` haya restaurado de la sesión anterior
(`playlist_publicidad.json`); si no hay nada programado para hoy, no
toca lo restaurado — la persistencia de la sesión anterior actúa
como red de seguridad solo cuando no hay una programación real
guardada para el día.

**Ciclo Automático completo (reescrito a pedido explícito — este es
el CORAZÓN de la estación)**: el CONTEXTO que dio Santiago: "la
estación funciona reproduciendo la ventana 2; a la hora del bloque
horario de la ventana 1, corta la 2, reproduce todo el bloque y
vuelve a la 2. Esa es la función del automático. Siempre sin silencio
musical, todo encadenado, con fundido de entrada y salida". Semántica
actual de `SchedulerAutomatico` (`core/playlist_manager.py`, QTimer
de 1s):

- **Los bloques se disparan por horario SIEMPRE**, ya no depende del
  botón AUTOMÁTICO (cambio de semántica explícito: "si no está
  activado, reproducirá el bloque horario y se quedará en silencio").
  El disparo es por TRANSICIÓN de hora (`_ultima_hora_tick <= hora
  <= ahora`): un bloque creado a mitad del día con hora ya pasada
  NUNCA se dispara retroactivamente (antes `Crear Bloque Nuevo`, que
  pone la hora actual por defecto, se habría disparado vacío al
  segundo siguiente). Un bloque VACÍO tampoco dispara nada.
- **El botón AUTOMÁTICO gobierna solo la VUELTA a Emisión**: con el
  modo activo, al terminar la reproducción de Publicidad (fin del
  bloque disparado, freno por hora de un bloque futuro, fin del
  árbol, o cascada de errores agotada) Emisión se reanuda o arranca
  desde el ítem en rojo / el primero
  (`GestorPublicidad.al_finalizar_reproduccion` →
  `SchedulerAutomatico._al_terminar_publicidad`). Con el modo
  apagado, el bloque suena igual a su hora y después silencio.
- **Todas las transiciones Ventana 2 <-> bloque son FUNDIDOS
  superpuestos** (`fade_volumen_a`, duración = la configurada en
  Fade/Transiciones con piso de 0.8s): al disparar un bloque el
  bloque ya arranca mientras Emisión baja en fade (nunca hay bache), y
  una pausa DIFERIDA (`_generacion_pausa_emision`, mismo patrón que
  `_generacion_pisador`) pausa Emisión recién al terminar el fade —
  restaurando el volumen previo con el motor ya pausado, para que un
  Play manual posterior no se encuentre el volumen atrapado en 0. Al
  volver, Emisión arranca inaudible y sube en fade al volumen previo.
  Si el bloque fue más corto que el fade, la pausa vieja se invalida
  por generación y Emisión solo vuelve a subir.
- **Al INICIAR el programa** (pedido a): reproduce el bloque VIGENTE
  — el de hora más tardía que ya pasó y que tenga ítems
  (`_bloque_vigente()`), nunca el primero del árbol
  (`_arrancar_al_iniciar`, diferido 1.2s con singleShot para dejar
  asentar la restauración). Si no hay bloque vigente y el modo
  AUTOMÁTICO está activo (checkbox "modo automático al iniciar" en
  Configuración), arranca directamente Emisión con fundido. OJO: esto
  reemplaza a propósito la regla anterior de "nunca suena nada al
  abrir sin Play" — pedido explícito de esta ronda, la radio debe
  retomar sola tras un corte de luz.
- Al terminar cada bloque queda MARCADO en verde el primer ítem del
  bloque siguiente, sin reproducirlo, en espera de su hora
  (`_marcar_proximo_bloque_en_espera`, punto 4 del pedido; respeta
  un verde que el operador ya haya puesto fuera del bloque terminado).
- Si el operador interviene a mano (doble click, Stop) mientras un
  bloque disparado está en curso, se da por terminado igual (no deja
  Emisión pausada para siempre).

**Ronda de robustez de emisión (pedido explícito, posterior al ciclo
Automático)**:
- **El botón AUTOMÁTICO arranca SIEMPRE encendido al abrir** —
  `MainWindow._inicializar_motores_audio` lo prende incondicional; el
  checkbox "modo automático al iniciar" se RETIRÓ de Configuración →
  Reproducción (contradecía la regla; la clave vieja en
  `config_general.json` se ignora sin romper). El operador puede
  apagarlo a mano después de abrir.
- **Con el Automático activo, los botones STOP de Ventana 1 y
  Ventana 2 quedan DESHABILITADOS** (la estación no se puede
  silenciar a mano mientras el automático conduce el aire): Ventana 1
  en `VentanaPublicidad._toggle_automatico()` (`btn_stop`), Ventana 2
  vía `automatico_cambiado` → `MainWindow._on_automatico_cambiado` →
  `VentanaEmision.set_stop_habilitado()` (delegado a
  `PanelReproductor`). La Auxiliar no se toca. Se rehabilitan al
  apagar el botón.
- **Aviso "No se encontró Bloque Horario en este momento en la
  programación"** (texto textual pedido): si `_arrancar_al_iniciar`
  no encuentra bloque vigente, dispara el callback
  `SchedulerAutomatico.al_no_encontrar_bloque` (lo setea MainWindow —
  el core no crea widgets) → `MainWindow._avisar_sin_bloque_horario`,
  un QMessageBox NO modal (`show()`, no `exec()`) + mensaje en la
  barra de estado — Emisión arranca sola inmediatamente sin esperar
  el OK, desde el ítem en rojo (el primero por defecto).

**Bug real corregido — "la ventana 1 sigue sin reproducir el ítem
siguiente" (pedido b)**: `GestorPublicidad.__init__` NUNCA conectaba
`motor.finalizo_item` (Ventana 2 siempre la tuvo en
`_conectar_motor`) — al terminar una tanda naturalmente nadie llamaba
a `_avanzar()` y la reproducción moría en el primer ítem sin error
visible. Corregido conectándola a `_on_fin_de_item`. Regla: al crear
un gestor nuevo sobre `MotorAudio`, revisar contra `_conectar_motor`
de `core/gestor_emision.py` que estén TODAS las señales conectadas.

**Scheduler de medianoche (implementado)**: el mismo
`SchedulerAutomatico`, al detectar que cambió el día calendario,
llama a `resolver_programacion_del_dia()` (`config/settings.py`) y
si hay algo guardado para hoy (vía el Programador), reemplaza los
bloques de Publicidad con `ventana_publicidad.cargar_bloques(...)`.
Si no hay nada guardado para el día, no toca lo que ya estaba
cargado.

**Play sobre el título del bloque (implementado, pedido explícito)**:
si el ítem con foco (armado, o seleccionado en el árbol) es un nodo
de BLOQUE (no una tanda — `item.parent() is None`), apretar Play ya
no queda sin efecto: `GestorPublicidad._reproducir_seleccion_o_actual`
detecta el caso y llama a `_reproducir_primero_del_bloque()`, que
arranca desde el primer ítem reproducible de ESE bloque (mismo
criterio que usa `disparar_bloque` para el modo automático, pero sin
marcarlo como "bloque automático en curso").

**La reproducción continua nunca adelanta un bloque futuro
(implementado, pedido explícito)**: antes, la restricción de "no
cruzar al bloque siguiente" en `_avanzar()` SOLO aplicaba mientras
`_bloque_automatico_actual` estaba seteado (un bloque disparado por
horario) — el avance manual/natural común (Siguiente, fin de tema)
sí podía saltar de un bloque al próximo sin importar la hora. Ahora
`_avanzar()` chequea SIEMPRE (`_bloque_ya_disponible()`, compara
`ROL_HORA_BLOQUE` contra `QTime.currentTime()`) antes de cruzar a un
bloque DISTINTO del actual: si su hora todavía no llegó, la
reproducción se detiene ahí en vez de arrancarlo antes de tiempo — un
bloque de las 14hs nunca empieza a sonar a las 13:50 solo porque se
terminó el bloque anterior. Esto es una regla nueva, más estricta que
la que ya tenía el modo automático (que sigue además NUNCA cruzando
de bloque bajo ninguna circunstancia mientras dura su disparo).
Ronda posterior: ese freno además AVISA al Scheduler
(`_notificar_fin_reproduccion`) — con Automático activo, el aire
vuelve a Emisión en vez de quedar en silencio (ver "Ciclo Automático
completo" más arriba); el verde queda puesto sobre el bloque futuro
como señal de "en espera de su hora".

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

**Bug real corregido — la leyenda junto al botón AUTOMÁTICO mostraba
el ítem en reproducción (pedido explícito: "ahí no pongas el nombre
del item que se está reproduciendo")**: `marcar_reproduciendo_item()`
pisaba `lbl_estado` con "Reproduciendo: X" (y un fallback de
"Modo automático activo"/"Modo manual" con otro texto), mezclando dos
responsabilidades en la misma etiqueta. Corregido sacando esas líneas
de `marcar_reproduciendo_item()` por completo — `lbl_estado`
(`objectName` `lblEstadoAutomatico`) ahora responde EXCLUSIVAMENTE al
botón AUTOMÁTICO, seteado solo desde `_toggle_automatico()`: texto
"Automático Activo" (rojo, `activo="true"`) o "Modo Manual" (gris,
`activo="false"`) — mismo patrón de propiedad dinámica + QSS
(`gui/styles.py`) que ya usaba `btnAutomatico[activo=...]`.

**Bug real corregido — arrastrar un archivo siempre lo ubicaba en el
primer bloque (pedido explícito: "no me deja ponerlo en donde yo
quiera")**: dos causas combinadas. Primero, `ArbolConDrop.dropEvent()`
(`gui/common_widgets.py`, base compartida — también la usa el árbol de
categorías de Ventana 3 y el del Programador) resolvía `itemAt(punto)`
y, si caía en un hueco vacío (frecuente en un árbol jerárquico disperso
con pocos hijos por bloque), pasaba `item_destino=None` sin más.
Segundo, el fallback en `MainWindow._on_archivo_soltado_publicidad`
(`gui/main_window.py`) usaba ese `None` para ir SIEMPRE al
`topLevelItem(0)` (el primer bloque) — contradiciendo el propio
comentario de `ArbolConDrop` que decía que el fallback debía ser el
ÚLTIMO bloque. Corregido con
`ArbolConDrop._item_de_nivel_superior_mas_cercano()`, que busca el
bloque de nivel superior cuyo centro vertical (`visualItemRect`) está
más cerca del punto soltado — así soltar cerca de cualquier bloque cae
en ESE bloque, no siempre en el primero. El fallback de árbol
REALMENTE vacío en `main_window.py` se corrigió además para usar el
último bloque, no el primero, consistente con la intención original.

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

**Bug real corregido — "mucho silencio y atenuación al encadenar
temas" (pedido explícito: "que suene como debería sonar una FM")**:
`MotorAudio.crossfade_a()` reproducía el tema ENTRANTE sin su recorte
de silencio de entrada ni su nivelado de volumen (`analisis_en_fila`
no se leía ni se pasaba) — cada crossfade arrancaba con el silencio
de cabecera del tema siguiente todavía puesto y a un volumen sin
nivelar, sonando como un "bache" en vez de un encadenado fluido.
Ahora `_iniciar_crossfade` (`core/gestor_emision.py`) lee el análisis
del ítem entrante y se lo pasa a `crossfade_a()`, que a su vez se lo
pasa a `entrante.reproducir()` — mismo patrón que la reproducción
normal. Además, la rampa de volumen del crossfade estaba en una
escala fija 0-100 desconectada del volumen Master configurado: al
arrancar el crossfade, el tema saliente saltaba momentáneamente a
volumen 100 (aunque el Master estuviera en, por ejemplo, 70) antes de
empezar a bajar, y el tema entrante siempre rampeaba hacia 100 planos
sin su propio nivelado — corregido capturando el volumen REAL de
salida (`obtener_volumen()`) como punto de partida del fade-out, y el
volumen YA nivelado del entrante (leído después de su propio
`reproducir()`) como techo del fade-in.

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

**Bug real corregido — "el mismo archivo de Pisador en varios temas,
solo suena la primera vez"**: `MotorAudio.reproducir()` solo llama a
`cargar()` (recarga el media en libVLC) si la ruta nueva es distinta
de `self._ruta_actual` — si se reutiliza el MISMO archivo de Pisador
en dos temas distintos, la segunda vez se saltea `cargar()` porque la
ruta no cambió. El seek explícito a `punto_inicio_ms` que reinicia la
posición, antes, solo se ejecutaba `if punto_inicio_ms and
punto_inicio_ms > 0` — para un Pisador (que siempre arranca en 0) esa
condición era falsa, así que la segunda reproducción quedaba con el
reproductor "trabado" en el final de la reproducción anterior en vez
de arrancar de nuevo, y no sonaba. Corregido haciendo el seek
SIEMPRE (incluso a 0ms) después de cada `play()`, sin importar si
`cargar()` se ejecutó o no — reproducir dos veces seguidas el mismo
archivo ahora reinicia la posición de forma confiable.

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
Play manual). De paso, esto reemplazó los datos de ejemplo que traía
Ventana 2 al arrancar (`VentanaEmision._cargar_datos_demo`,
eliminado) — una instalación nueva arranca con la lista vacía de
verdad.
**Actualización de la ronda del ciclo Automático**: si al restaurar
no había NADA armado, el primer ítem queda en rojo por defecto (sin
sonar) — pedido explícito punto 2 del ciclo: "predeterminadamente el
rojo estará al comienzo, con posibilidad de elegirlo manualmente" —
así la vuelta automática a Emisión siempre tiene desde dónde
arrancar. Y la regla de "nunca suena nada al abrir sin Play" ya NO es
absoluta: el ciclo Automático (ver Ventana 1) reproduce solo el
bloque vigente al iniciar, y arranca Emisión sola si el modo
automático está activo — pedido explícito de esa ronda (la radio debe
retomar sola tras un corte de luz).

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

**Indicador de previo (implementado)**: `IndicadorEnVivo` (el mismo
círculo titilante ya usado en Ventana 1/2) junto al botón "▶ Previo"
(`ventana3.indicador_preview`, `set_indicador_en_vivo()`) — señal
visual clara de "estoy escuchando el previo". `GestorExplorador`
(`core/playlist_manager.py`) lo actualiza desde
`posicion_cambiada`/`finalizo_item`, igual patrón que `GestorPlaylist`
en Ventana 2.

**Bug real corregido — "el previo se dispara sin querer al
arrastrar"**: primero se probó un guard de 400ms
(`ArbolOrigenArrastre.acaba_de_arrastrar`) que ignoraba un doble
click si venía justo después de un arrastre — pero seguía pasando
igual en algunos casos. A pedido explícito, se sacó el trigger del
doble click DE RAÍZ: `tree_archivos.itemDoubleClicked` ya no está
conectado a nada, el único disparador de la preescucha es el botón
"▶ Previo" (`btn_play_preview.clicked`). `acaba_de_arrastrar()` y el
tracking de `_ultimo_arrastre_ms` en `ArbolOrigenArrastre` se
eliminaron por completo (habían quedado sin uso).

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
Editor de programaciones: arrastrás desde el Explorador (o usás el
buscador de biblioteca, ver abajo), armás bloques horarios (hora +
título), y guardás para una fecha específica o para uno o varios días
de la semana (checkboxes L-D).

**Rediseño completo (pedido explícito, "diferenciar bien cargar,
editar, eliminar... la programación, y por otro lado, añadir, borrar,
reemplazar los ítems del bloque, y las mismas opciones para los
bloques horarios")**: la ventana ahora tiene TRES grupos separados a
propósito, cada uno con su propio nivel de acción — Santiago fue
explícito en que mezclarlos en la cabeza del operador era el problema
real, no solo estético:

1. **PROGRAMACIÓN GUARDADA** (nivel "archivo entero": nombre + día/
   fecha + todos sus bloques) — fila simétrica **Nueva / Cargar... /
   Eliminar...** (mismo stretch, mismo tamaño — pedido explícito punto
   a), fila **Duplicar para otro día... / Eliminar varias...**, y el
   botón **▶ Aplicar AHORA en Ventana 1 (al aire)** (`objectName`
   `btnStop`, rojo — es una acción que corta lo que esté sonando).
2. **BLOQUES HORARIOS Y SUS ÍTEMS** (nivel estructura) — el botón que
   antes decía solo "＋ Bloque horario" ahora dice **"＋ Añadir Bloque
   Horario"** (pedido explícito punto b: "no queda intuitivo, para
   diferenciar de Cargar puede ser Añadir"); fila de ítems **➕ Añadir
   Ítem... / 🔁 Reemplazar seleccionado... / ✕ Quitar
   seleccionado(s)**.
3. **GUARDAR PROGRAMACIÓN** (nombre + fecha/día + botón Guardar) —
   sin cambios de fondo, es la identidad de dónde se graba lo que ya
   está en el editor.

**"Reemplazar" es UNA sola acción contextual para bloques E ítems**
(confirmado con Santiago, no dos botones separados):
`_reemplazar_seleccionado()` mira qué hay seleccionado — un BLOQUE
(`item.parent() is None`) abre `DialogoEditarBloque` (hora + título,
conserva sus ítems intactos); un ÍTEM abre el buscador de biblioteca
en modo single y le cambia el archivo (título/duración/código/ruta/
análisis de audio) **sin mover su posición** dentro del bloque. Con
0 o 2+ seleccionados, avisa que hay que elegir uno solo.

**"Quitar seleccionado(s)" ahora admite selección múltiple**
(`self.tree.setSelectionMode(ExtendedSelection)`, pedido explícito
punto h ampliado: "también selección múltiple de bloques/ítems en el
editor") — Ctrl/Shift para elegir varios bloques y/o ítems sueltos a
la vez y sacarlos con un solo clic + una sola confirmación.
`_quitar_seleccionados()` separa los bloques de nivel superior
seleccionados de los ítems sueltos cuyo padre NO esté también
seleccionado (si el padre se va a borrar, no hace falta procesar el
hijo aparte) — evita procesar dos veces o con índices corridos.

**Buscador de biblioteca a dos columnas** (`gui/dialogo_seleccionar_biblioteca.py`,
pedido explícito punto e: "opción clara para añadir ítem... navegar
por categorías y dentro de ellas, el ítem que deseo agregar", "minimalista
del explorador"): izquierda categorías (recursivo, sin límite de
niveles), derecha los archivos de la categoría seleccionada
(Título/Duración/Código). Lee directamente
`ventana_explorador.tree_categorias` (la Ventana 3 tiene que estar
construida, se la pasa `MainWindow.abrir_programador` al crear
`VentanaProgramador`) — copia la ESTRUCTURA a un árbol propio (nunca
reparenta los `QTreeWidgetItem` originales, un ítem solo puede
pertenecer a un `QTreeWidget` a la vez), así siempre refleja lo último
de la biblioteca en memoria sin releer el disco. `permitir_multiple=True`
para "Añadir Ítem" (Ctrl/Shift, agrega varios de una), `False` para
"Reemplazar" (uno solo, doble click confirma directo).

**Recordar la última categoría navegada** (pedido explícito punto f:
"que guarde la última carpeta/categoría... así no tengo que volver a
hacer toda la búsqueda"): `gui/estado_ui.py` ganó un par genérico
`guardar_valor()`/`restaurar_valor()` (sección `estado/` de
`ui_state.ini`, mismo QSettings de siempre) — `VentanaProgramador`
guarda la ruta de nombres (`["Publicidad", "Comerciales"]`) cada vez
que se confirma el buscador, y se la pasa como `categoria_inicial` la
próxima vez que se abre — sobrevive tanto a cerrar y reabrir el
diálogo como a cerrar y reabrir la aplicación entera (persiste en
disco). Ojo con una trampa real de QSettings: una lista guardada de
UN solo elemento vuelve como string suelto al leerla, no como lista
de 1 — `_restaurar_ultima_categoria()` normaliza ese caso.

**Duplicar para otro día — subsisten las dos** (`gui/dialogo_duplicar_programacion.py`,
pedido explícito punto g: "copiar la misma programación para
cambiarla por otro día, generando una nueva... que subsistan las
dos"): pide nombre + fecha específica o días de la semana NUEVOS, y
guarda el contenido ACTUAL del editor (`_serializar_bloques()`) bajo
esa clave nueva con `guardar_programacion()` — como es una clave
distinta (otro día/fecha) en `programacion.json`, la programación de
origen nunca se toca, quedan las dos guardadas.

**Cargar / Eliminar / Eliminar varias unificados en un solo diálogo**
(`gui/dialogo_programaciones_guardadas.py`): reemplaza el viejo
`QInputDialog.getItem` — la MISMA clase sirve para "Cargar" (lista de
selección única) y para "Eliminar varias" (`permitir_multiple=True`,
Ctrl/Shift, una sola confirmación con la lista de nombres a borrar).
`config/settings.py` ganó `eliminar_programacion(tipo, clave)` (borra
esa clave puntual de `dias_semana`/`fechas_especificas` y persiste)
para que Eliminar/Eliminar varias tengan de dónde tirar.

**"Aplicar AHORA en Ventana 1" — al aire, sin pasar por el disco**
(pedido explícito punto d: "no hay una acción que si yo deseo cargar
esa programación en el momento"): `VentanaProgramador` pide
confirmación (texto explícito: "puede cortar lo que esté sonando") y
emite `solicitud_aplicar_ahora(bloques)` con el contenido YA
serializado del editor — no hace falta guardarlo primero.
`MainWindow.abrir_programador()` conecta esa señal a
`_aplicar_programacion_ahora()`, que llama directo a
`self.ventana_publicidad.cargar_bloques(bloques)` (mismo método que ya
usa el arranque automático y "Cargar Programación" de Ventana 1) — la
confirmación de impacto ya la dio el Programador, acá solo se aplica.

**Bug real corregido de paso — el Programador nunca guardaba el
recorte de silencio/nivelado de los ítems**: ni el drag&drop
(`_on_archivo_soltado`) ni `_serializar_bloques()` conocían
`punto_inicio_ms`/`punto_fin_ms`/`ganancia_db` — cualquier tanda
armada en el Programador y guardada llegaba a Ventana 1 sin ese
análisis (mismo tipo de bug ya corregido antes en Ventana 1/2 "al
aire", pero este rincón se había quedado afuera). Corregido: ahora se
guarda con `ROL_ANALISIS_AUDIO` (mismo rol que usa `gui/styles.py` en
el resto de la app) en cada ítem — `_on_archivo_soltado` busca el
registro completo vía `ventana_explorador.buscar_registro_por_ruta()`
(mismo patrón que `MainWindow._on_archivo_soltado_publicidad`), el
buscador de biblioteca siempre trae el registro completo, y
`_serializar_bloques()`/`_cargar_programacion_existente()` leen y
escriben esos tres campos igual que ya hace Ventana 1.

**Regla de negocio importante**: al resolver qué programación aplica
un día dado, una **fecha específica siempre prevalece** sobre el
patrón semanal general de ese día (`config/settings.py:
resolver_programacion_del_dia`). Ya está probado con tests.

**Bug real corregido — el título del bloque se duplicaba en cada
carga de programación (pedido explícito: "el nombre del bloque se
añadió, no se cambió... quedó duplicado varias veces la hora
finalizando en - Bloque")**: `_serializar_bloques()` guardaba
`nodo.text(0)` — el texto VISIBLE ya concatenado "HH:MM:SS - Título" —
como si fuera el título puro. Al recargar esa programación,
`_cargar_programacion_existente()` volvía a concatenar
`f"{hora} - {titulo}"` sobre ese valor ya prefijado, y el ciclo
cargar/editar/guardar repetido iba acumulando cada vez más prefijos de
hora. Corregido con un rol propio `ROL_TITULO_BLOQUE`
(`gui/ventana_programador.py`, mismo patrón que `ROL_HORA_BLOQUE`) que
guarda el título PURO por separado del texto mostrado, usado en
`_agregar_bloque()`, `_cargar_programacion_existente()` y
`_serializar_bloques()`. Además se agregó `titulo_bloque_sin_prefijo_hora()`
(`config/settings.py`), un helper compartido que pela repetidamente el
prefijo "HH:MM:SS - " de un título — usado también en
`VentanaPublicidad.cargar_bloques()` y en
`GestorPublicidad._guardar_estado_ahora()` — así una `programacion.json`
que ya haya quedado corrupta por el bug se AUTOCURA sola la próxima vez
que se carga, sin necesitar reparar los datos a mano.

### Configuración (`gui/ventana_configuracion.py`)
QTabWidget con: Audio (dispositivo master/preescucha, volúmenes),
Fade/Transiciones (crossfade on/off + duración), Rutas (bibliotecas +
logs), Reproducción y Automatización (avanzar en error, reintentos,
repetir lista, tolerancia de silencio — el checkbox "modo automático
al iniciar" se retiró: el Automático arranca siempre ON, ver Ventana 1),
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

**Confirmación al cerrar — SIEMPRE (implementado, pedido explícito
de la ronda de robustez)**: `MainWindow.closeEvent` pide confirmación
Sí/No en TODO cierre (antes solo cuando había audio sonando): si
`_hay_emision_en_curso()` (Emisión/Publicidad/Auxiliar) el texto
advierte que se CORTA la emisión al aire; si no, pregunta genérica
"¿Confirmás que querés cerrar el programa?". Cancela con
`evento.ignore()` si el operador dice que no. Única excepción: el
cierre por actualización (flag `_cerrando_por_actualizacion`), que ya
pidió su propia confirmación.

### Actualizador (`core/actualizador.py`)
`git fetch` + comparar HEAD local contra `origin/main` (o `master`),
`git pull --ff-only` para aplicar, y reinicio del proceso
(`QProcess.startDetached` + `app.closeAllWindows()` + `app.quit()`).
Si la carpeta no es un clon git real, se deshabilita solo con un
mensaje claro en vez de fallar. Botón en Configuración → pestaña
Actualizaciones.

**Reinicio por actualización vs. aviso de cierre (pedido explícito
"salvo actualización")**: el aviso de `MainWindow.closeEvent` por
emisión en curso NO se repite cuando el cierre viene del botón
"Actualizar y reiniciar" (que ya pidió su propia confirmación) —
`VentanaConfiguracion._aplicar_actualizacion` llama a
`MainWindow.preparar_cierre_por_actualizacion()` antes de reiniciar,
y `closeEvent` saltea la pregunta con ese flag. Además
`reiniciar_aplicacion()` ahora hace `closeAllWindows()` ANTES de
`quit()` a propósito: `app.quit()` solo corta el event loop SIN pasar
por `closeEvent`, y ahí se perdía el guardado de layout
(splitters/columnas/geometría) en cada reinicio por actualización.

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

**Segunda vuelta del mismo bug — "la ventana maximizada vuelve a
salirse de pantalla"**: si la sesión anterior se cerró CON la
ventana maximizada, `restoreGeometry()` la restaura ya maximizada, y
en ese estado `frameGeometry()` no es confiable para decidir si
"entra" en la pantalla actual (y mover una ventana maximizada con
`setGeometry()` se comporta distinto según el gestor de ventanas).
Corregido en `_asegurar_dentro_de_pantalla()`: si `isMaximized()` es
True, primero `showNormal()`, se corrige esa geometría normal contra
la pantalla actual, y recién ahí `showMaximized()` — así el gestor de
ventanas maximiza sobre coordenadas válidas de la sesión actual, no
sobre las que se guardaron la vez anterior.

**Ventana 1/2 rediseñadas más compactas (pedido explícito, "otro
skin")**: los relojes bajaron de 26pt a 14pt (`gui/styles.py`), y
`EtiquetaMarquesina` (el sticker del título en Ventana 2) tiene
`minimumSizeHint()` propio de 40px en vez de heredar los 220px de
`sizeHint()` como mínimo real.

**Botones de transporte: de grilla 2x2 a 1 sola fila (pedido
explícito, ronda posterior — "para ahorrar visibilidad de la
lista")**: en una ronda anterior se habían puesto en grilla de 2
columnas (`QGridLayout`) porque una sola fila de 4-5 botones fijaba
un ancho mínimo grande que no dejaba achicar el panel. Con la
tipografía/padding ya reducidos de rondas posteriores, Santiago pidió
volver a 1 SOLA fila para priorizar altura (ver más lista) sobre
ancho — `QHBoxLayout` en `panel_reproductor.py` y
`ventana_publicidad.py`, con los botones marcados
`setProperty("class", "btnTransporte")` y un padding/fuente más
chicos (`gui/styles.py`, selector `QPushButton[class="btnTransporte"]`)
para que las 4-5 entren cómodas en una línea sin repetir el problema
de ancho de la ronda anterior.

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
    (Crear/Modificar/Eliminar Programación abren el Programador por
    ahora; Sacar Item funcional; Agregar/Reemplazar Item visibles
    pero deshabilitadas hasta que se pida esa lógica; Crear Bloque
    Nuevo funcional con confirmación) — implementado (ver Ventana 1
    más arriba). **Bug real corregido de paso, en Ventana 1 Y 2**: el
    recorte de silencio/nivelado calculado en Ventana 3 nunca se
    aplicaba al aire (solo en el Previo) — ahora viaja con el ítem
    (`ROL_ANALISIS_AUDIO`) y se pasa a `MotorAudio.reproducir()`.
    Log temporalmente más detallado (`registrar_evento` en cada
    acción de Publicidad) mientras Santiago prueba esta ronda — pidió
    volver a un nivel normal cuando avise.
14. ~~Correcciones de la ronda de pruebas de Ventana 1~~ — bug real
    del Pisador reutilizado en varios temas (`MotorAudio.reproducir()`
    ahora siempre hace seek, incluso a 0ms); botones de transporte de
    vuelta a 1 sola fila (`btnTransporte`) para priorizar altura sobre
    ancho; el previo de Ventana 3 ya NO se dispara con doble click,
    solo con el botón (se sacó el trigger de raíz en vez de agrandar
    el guard); "Cargar Programación" con lógica real (resuelve HOY con
    prioridad fecha específica > día genérico, pide confirmación si es
    manual, no pregunta si es automática al iniciar/medianoche); y el
    crossfade ahora aplica el recorte de silencio/nivelado del tema
    ENTRANTE (antes solo el saliente lo tenía) además de rampas de
    volumen relativas al volumen real en vez de una escala fija 0-100
    — los tres bugs de audio (Pisador, silencio al aire de la ronda
    anterior, y ahora el crossfade) comparten la misma raíz: partes
    del motor que llamaban a `MotorAudio.reproducir()`/`crossfade_a()`
    sin pasarle el análisis completo del ítem. Falta que Santiago
    confirme con música real que el encadenado ahora suena fluido
    ("como una FM"), que el Pisador repetido funciona en los 4 temas
    de su prueba, y que "Cargar Programación" resuelve bien sus casos
    de fecha específica vs. día genérico guardados.
15. ~~Correcciones gráficas post-prueba (ventana maximizada, leyenda
    Automático, drag&drop al bloque más cercano, título duplicado,
    Play sobre bloque, corte por hora)~~ — segunda vuelta del bug de
    ventana maximizada saliéndose de pantalla (ahora se restaura a
    normal, se corrige la geometría, y recién ahí se vuelve a
    maximizar — antes no se manejaba el caso de sesión cerrada YA
    maximizada); la leyenda junto al botón AUTOMÁTICO en Ventana 1 ya
    no muestra el ítem en reproducción, solo "Automático Activo"
    (rojo) / "Modo Manual" (gris), reflejando exclusivamente el estado
    del botón; arrastrar un archivo a un bloque de Publicidad ya no
    cae siempre en el primero — `ArbolConDrop` (compartido con Ventana
    3 y el Programador) resuelve el bloque de nivel superior más
    cercano al punto soltado; el título de un bloque ya no se duplica
    en cada ciclo de cargar/editar/guardar una programación (rol
    `ROL_TITULO_BLOQUE` separado del texto concatenado, con
    autocuración de programaciones ya corruptas vía
    `titulo_bloque_sin_prefijo_hora()`); seleccionar el TÍTULO de un
    bloque y apretar Play ahora reproduce ese bloque desde su primer
    ítem; y la reproducción continua (no solo el modo automático) ya
    nunca cruza a un bloque cuya hora todavía no llegó, deteniéndose
    ahí en vez de adelantarlo — implementado y probado (17 scripts de
    regresión + smoke test de la app completa, todo sin fallos). Falta
    que Santiago confirme en su notebook real que la ventana ya no se
    sale de pantalla al maximizar (el sandbox no puede probar
    comportamiento real del gestor de ventanas), y que el resto se ve/
    comporta como pidió. Cierre explícito de esta ronda: "Vamos con
    eso. Así pasamos a la programación" — el próximo tema que Santiago
    quiere encarar es el motor de programación/carga automática por
    plantilla, todavía sin especificar en detalle.
16. ~~Ciclo Automático completo (arranque en bloque vigente, avance
    dentro del bloque, vuelta a Emisión con fundidos, cierre por
    actualización)~~ — (a) al abrir el programa se reproduce solo el
    bloque VIGENTE (el de hora más tardía que ya pasó, nunca el
    primero del árbol), y sin bloque vigente con Automático activo
    arranca Emisión directo; (b) bug real corregido: `finalizo_item`
    nunca estuvo conectada en `GestorPublicidad` — por eso Ventana 1
    "no reproducía el ítem siguiente"; (c) semántica nueva del
    Automático: los bloques disparan por horario SIEMPRE (por
    transición de hora, nunca retroactivo, nunca un bloque vacío) y
    el botón gobierna solo la vuelta a Emisión al terminar Publicidad
    (reanudar lo pausado o arrancar desde el rojo/primer ítem, que
    ahora queda en rojo por defecto al restaurar), todo con fundidos
    superpuestos de salida y entrada (sin baches de silencio, pausa
    diferida por generación, volumen nunca atrapado en 0), y al
    terminar cada bloque queda en verde el primer ítem del bloque
    siguiente en espera de su hora; (d) el reinicio por actualización
    ya no repregunta por la emisión en curso y ahora sí guarda el
    layout al reiniciar (`closeAllWindows()` antes de `quit()`) —
    implementado y probado (10 tests nuevos del ciclo + suite de
    regresión completa + smoke test real del arranque con bloque
    vigente restaurado desde disco). Falta que Santiago lo pruebe con
    música real: cómo se escuchan los fundidos Ventana 2 <-> bloque en
    la práctica, y confirmar la duración de fade configurada. Los
    fundidos ENTRE tandas de un mismo bloque de Ventana 1 (crossfade
    interno de Publicidad) quedan como mejora futura si hace falta —
    hoy el encadenado ahí es corte directo con recorte de silencio.
17. ~~Robustez de emisión (Automático ON por defecto, STOPs
    bloqueados, aviso sin bloque, confirmación de cierre siempre)~~ —
    (a) la programación del día se carga sola al abrir sin preguntar
    y se emite automáticamente (ya venía del punto 16, confirmado);
    (b) el botón AUTOMÁTICO arranca SIEMPRE encendido al abrir (se
    retiró el checkbox "modo automático al iniciar" de Configuración,
    que contradecía la regla); (c+d) con el Automático activo los
    botones STOP de Ventana 1 y Ventana 2 quedan deshabilitados y se
    rehabilitan al apagarlo (la Auxiliar no se toca); (e) si al abrir
    no hay bloque horario vigente, aviso no-modal "No se encontró
    Bloque Horario en este momento en la programación" y Emisión
    arranca sola desde el primer ítem sin esperar el OK; (f) cerrar
    el programa pide confirmación SIEMPRE (con advertencia de corte
    si hay audio al aire), salvo el reinicio por actualización —
    implementado y probado (6 tests nuevos + suite de regresión +
    2 smoke tests reales del arranque con y sin playlist de Emisión
    guardada). Falta que Santiago lo pruebe en su notebook con audio
    real, en particular que el STOP bloqueado no le moleste en la
    operación diaria (se desbloquea apagando el Automático).
18. ~~Rediseño completo del Programador de Emisión (3 niveles de
    acción, buscador de biblioteca, duplicar, eliminar varias, aplicar
    ahora)~~ — pedido explícito de diferenciar con claridad
    programación/bloques/ítems: tres grupos separados en la UI
    (Programación Guardada / Bloques y sus Ítems / Guardar); fila
    simétrica Nueva/Cargar/Eliminar; "＋ Bloque horario" renombrado a
    "＋ Añadir Bloque Horario" (verbo explícito); "Reemplazar" como
    ACCIÓN CONTEXTUAL única para bloques (edita hora/título,
    `gui/dialogo_editar_bloque.py`) e ítems (cambia el archivo sin
    mover la posición); "Quitar" con selección múltiple real de
    bloques e ítems mezclados; buscador de biblioteca a dos columnas
    (`gui/dialogo_seleccionar_biblioteca.py`, categorías recursivo +
    archivos de la categoría, copia la estructura del árbol vivo del
    Explorador sin reparentar ítems); última categoría navegada
    persistida en disco (`estado_ui.guardar_valor`/`restaurar_valor`,
    nuevo par genérico); "Duplicar para otro día"
    (`gui/dialogo_duplicar_programacion.py`, guarda bajo una clave
    nueva sin tocar la original — subsisten las dos); Cargar/Eliminar
    varias unificados en `gui/dialogo_programaciones_guardadas.py`
    (`config/settings.eliminar_programacion` nuevo); "Aplicar AHORA en
    Ventana 1" (`solicitud_aplicar_ahora` → `MainWindow.
    _aplicar_programacion_ahora` → `ventana_publicidad.cargar_bloques()`,
    con confirmación de que puede cortar lo que esté sonando). Bug
    real corregido de paso: el Programador nunca guardaba
    `punto_inicio_ms`/`punto_fin_ms`/`ganancia_db` de sus ítems (ni
    por drag&drop ni por el buscador) — cualquier tanda armada ahí
    llegaba a Ventana 1 sin el recorte de silencio/nivelado aplicado;
    corregido con `ROL_ANALISIS_AUDIO` igual que el resto de la app.
    Implementado y probado (13 tests nuevos + integración real de
    punta a punta vía `MainWindow.abrir_programador()` → agregar
    bloque/ítem → Aplicar ahora → verificado en el árbol real de
    Ventana 1 + suite de regresión completa sin fallos nuevos). Falta
    que Santiago lo pruebe con su biblioteca real: navegar categorías
    profundas en el buscador, y confirmar que el layout de 3 grupos se
    entiende de un vistazo sin tener que releer nada.

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
