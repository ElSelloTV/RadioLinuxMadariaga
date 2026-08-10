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

## Manual de Dinesat Visual (referencia de diseño completa)

Santiago pasó el manual de usuario completo de Dinesat Visual (Hardata,
v4.0.4.17) — es la referencia de diseño de toda esta app, guardado a
pedido explícito ("Guardalo en la memoria de este proyecto") en
[`docs/manual_dinesat_visual.md`](docs/manual_dinesat_visual.md). Ese
archivo tiene el manual completo en Markdown más anotaciones de Claude
Code marcando qué partes ya se implementaron, cuáles quedaron
explícitamente descartadas (video/NDI, satélite/RS232, RDS, SIP,
VNC, multi-emisora, sistema de usuarios — ver "Estudio del manual de
Hardata" más abajo) y qué ambigüedades quedan pendientes de preguntar.
Consultarlo ahí antes de tocar cualquier función que diga inspirarse
en Dinesat, en vez de redescubrir la tabla de comandos o la
nomenclatura de materiales de memoria.

**Nota de nomenclatura importante** (puede generar confusión si no se
tiene en cuenta): en Dinesat real, el prefijo de comando **`FMT`** es
EXCLUSIVO de la selección de formato musical del Musicalizador
Avanzado (`FMT ROCK`, `FMT SALSA`, etc. — ya implementado en esta app,
ver roadmap ronda 28). Los anuncios de hora/temperatura/humedad que
Santiago pidió (llamándolos informalmente "FMT HORA"/"FMT CLIMA") son
en realidad los comandos **`HTH`** de Dinesat (Hora-Temperatura-
Humedad — comandos `HORA`, `TEMPERATURA`, `HUMEDAD`, `TERMICA`,
sección 5.2.7.3/5.3.5/5.3.5.2 del manual) — un tipo de comando
SEPARADO del FMT. Pendiente confirmar con Santiago cómo prefiere que
se llame la función nueva en esta app.

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
  Ventana 2 quedan BLOQUEADOS** (la estación no se puede silenciar a
  mano mientras el automático conduce el aire): Ventana 1 vía
  `VentanaPublicidad._modo_automatico`, Ventana 2 vía
  `automatico_cambiado` → `MainWindow._on_automatico_cambiado` →
  `VentanaEmision.set_stop_habilitado()` (delegado a
  `PanelReproductor._stop_bloqueado_por_automatico`). La Auxiliar no
  se toca. Se desbloquean al apagar el botón. **Bug real corregido,
  ronda posterior**: originalmente esto deshabilitaba el botón
  (`setEnabled(False)`) — un botón deshabilitado no emite `clicked`,
  así que el operador apretaba STOP y "no pasaba nada", sin ningún
  aviso (pedido explícito: "avisar con un mensaje... indicando que
  para detener, primero debo sacar el automático"). Ahora el botón
  queda SIEMPRE clickeable (`ventana_publicidad._on_click_stop` /
  `PanelReproductor._on_click_stop`) y, si el Automático está activo,
  muestra un `QMessageBox.information` explícito en vez de detener.
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
**Paridad con Ventana 2 + exclusión mutua (implementado, ver roadmap
ronda 38)**: la Auxiliar ahora tiene la misma barra de progreso/seek
que Ventana 2 (antes le faltaba); el Musicalizador/FMT y el pase de
Automático quedan naturalmente inertes ahí (su `GestorPlaylist` no
recibe `ventana_explorador` ni `persistir=True` en
`MainWindow.abrir_ventana_auxiliar()`). Auxiliar y Emisión NUNCA
suenan a la vez: arrancar cualquiera de las dos desde silencio corta a
la otra con un fundido corto (`GestorPlaylist.al_arrancar_reproduccion`
→ `MainWindow._cortar_reproduccion_de()`) — el lado cortado queda en
silencio de verdad, sin auto-resume.

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

**Colores: solo rojo/verde/normal + celeste de selección, nunca color
de género (pedido explícito, ronda posterior)**: el Pisador anidado
tenía un color VIOLETA FIJO puesto una sola vez al agregarlo
(`agregar_pisador()`, leído de `colores_genero["Pisador"]` en
Configuración → Apariencia) — el mismo color que Ventana 3 usa para
identificar género en el Explorador, pero acá no tenía sentido: "los
colores que yo elijo en la ventana 3 es solo para identificarlos en
el explorador". Un ítem PRINCIPAL de Ventana 2 nunca tuvo color de
género (siempre fue solo rojo/verde/normal), así que el único cambio
real fue el Pisador. Corregido: `agregar_pisador()` ya no lee
`colores_genero` — el hijo nace con el MISMO estado (color) que su
padre en ese momento (`PanelReproductor._color_para_estado()`, helper
nuevo compartido), y **"el pisador toma el color de arriba, del ítem
principal, rojo o verde"** (pedido explícito) se mantiene sincronizado
de ahí en más: `_pintar_item()` ahora, después de pintar el ítem
principal, recorre `item.childCount()` y pinta cada hijo con el MISMO
`(fondo, texto)` — así marcar/desmarcar rojo o verde en el padre
(`marcar_reproduciendo`/`marcar_siguiente`) automáticamente actualiza
el Pisador sin tocar nada en esos dos métodos.

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

**Sin fade-in al arrancar un tema — solo fade-out (pedido explícito,
ronda posterior, Ventana 1 y 2: "quitá el fade al inicio, dejá solo
el del final... que los temas suenen más enganchados y con mejor
entrada")**: hasta acá, toda transición con fundido (crossfade
natural de Ventana 2, y el botón verde "Play/Siguiente con fundido"
de Ventana 1 y 2) hacía un fundido SIMÉTRICO — el tema saliente baja
a 0 Y el entrante sube desde 0 — lo que en la práctica se sentía como
que cada tema arrancaba "flojo" en vez de entrar con fuerza.
Corregido en los DOS lugares donde existía una rampa de entrada:
- `MotorAudio.crossfade_a()` (`core/audio_engine.py`): el motor
  ENTRANTE ya no arranca en volumen 0 para subir en cada paso de la
  rampa — arranca DIRECTO a `entrante.volumen_deseado()` (su volumen
  final ya nivelado) apenas se llama `entrante.reproducir()`, y se
  queda ahí fijo durante todo el crossfade. El motor SALIENTE sigue
  bajando en rampa hasta 0 exactamente igual que antes — la
  transición sigue sin ser un corte seco, solo que ahora es
  asimétrica: el que se va se apaga de a poco, el que entra pega
  fuerte de una. Afecta por igual al crossfade NATURAL (fin de tema)
  y al botón verde "Play/Siguiente con fundido" de Ventana 2 (ambos
  pasan por `_iniciar_crossfade()`/`crossfade_a()`).
- `GestorPublicidad._completar_avance_con_fundido()` (Ventana 1,
  `core/playlist_manager.py`): antes, después de que `_avanzar()`
  arrancaba el ítem nuevo (ya a su volumen normal, de una), el código
  lo pisaba a `set_volumen(0)` y lo hacía subir con
  `fade_volumen_a(volumen_base, ...)` — ahora esa parte se eliminó
  directamente: el ítem nuevo se deja sonar tal cual lo dejó
  `_avanzar()`/`motor.reproducir()`, sin ningún fundido de entrada. El
  fundido de SALIDA del ítem anterior (`_avanzar_con_fundido()`,
  `motor.fade_volumen_a(0, DURACION_FUNDIDO_MANUAL_SEGUNDOS)`, antes
  de cortar) no se tocó — sigue exactamente igual.
No se tocó el fundido de las transiciones Ventana 2 <-> bloque de
Publicidad del Ciclo Automático (Emisión pausándose/reanudándose
alrededor de un bloque disparado por horario) — es una función
distinta, ya pedida explícitamente en una ronda anterior ("sin
silencio musical, todo encadenado, con fundido de entrada y salida"),
y acá el pedido fue específicamente sobre "los temas", no sobre esa
transición de bloque.

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

**Segunda vuelta del mismo bug — el seek NO alcanzaba cuando el
archivo llegó a su fin NATURAL**: Santiago probó con audio real
(mismo Pisador reutilizado en 3 temas de una lista con crossfade) y
reportó que solo sonó la PRIMERA vez — la segunda y la tercera,
silencio total. Causa real: cuando libVLC llega al fin natural de un
media (evento `MediaPlayerEndReached`, sin que nadie llame a `stop()`
a mano — es justo lo que le pasa a un Pisador corto, siempre termina
solo), el reproductor queda en estado interno "Ended"; en ese estado,
un simple `play()` NO reinicia la reproducción de forma confiable en
varias versiones de libVLC (el seek a `punto_inicio_ms` de la
corrección anterior no alcanzaba, porque el problema no era la
posición sino que el `play()` mismo no "revivía" al reproductor).
Corregido con un `self._player.stop()` explícito ANTES de cada
`play()`, sin importar si `cargar()` se ejecutó arriba o no — fuerza
a libVLC a resetear ese estado. De paso se corrigió un segundo bug
relacionado, encontrado en el mismo log real: al cancelar un Pisador
en curso (`_cancelar_pisador_en_curso`) queda un fundido a volumen 0
corriendo en `motor_pisador` durante 0.8s; si un Pisador NUEVO se
dispara en ese mismo motor antes de que ese fundido termine (pasa de
tema rápido con Pisador en cada uno), el fundido viejo seguía
pisándole el volumen al nuevo — sonaba pero en silencio. Corregido
cancelando cualquier `_timer_fade_volumen` en curso al inicio de
`reproducir()`, para cualquier motor, no solo el del Pisador.
**Advertencia**: este bug de estado de libVLC no se puede reproducir
en el sandbox (no hay VLC instalado acá) — el fix se basa en un
comportamiento documentado de libVLC y en el log real que mandó
Santiago, pero falta que él lo confirme con audio real de nuevo.

**Tercera vuelta — LA CAUSA DE FONDO del "se reproduce pero está
MUDO" (ítems Y Pisadores)**: Santiago probó la ronda anterior y fue
PEOR: el Pisador sonó solo la primera vez, y además un tema musical
entero quedó mudo (el reloj avanzaba, cero sonido; Stop+Play manual
lo "arregló"). Su log mostró que el Pisador de las 17:24:32 se
reprodujo ENTERO (7s, "terminó solo") pero inaudible — reproducción
corriendo + cero sonido = el volumen nunca se aplicó. Causa real:
**libVLC DESCARTA en silencio un `audio_set_volume()` llamado antes
de que la salida de audio del reproductor exista** — y esa salida se
crea de forma asíncrona después de `play()` (y se DESARMA con cada
`stop()`, así que el fix anterior de stop()-antes-de-play() agrandó
la ventana del problema: por eso fue peor). Dos síntomas del mismo
bug: (1) el Pisador reusado quedaba mudo (su `set_volumen(100)` tras
`play()` se descartaba); (2) el tema ENTRANTE de un crossfade quedaba
mudo porque el techo del fade-in se leía con
`entrante.obtener_volumen()` recién arrancado → 0/-1 → la rampa subía
"hacia 0". Corrección de fondo en `MotorAudio`:
- `_volumen_deseado`: el volumen que el motor DEBERÍA tener es un
  atributo propio, la fuente de verdad ya no es libVLC.
  `set_volumen()` lo actualiza siempre; `volumen_deseado()` lo expone.
- `_emitir_posicion()` (tick de 500ms) **re-aplica el volumen deseado
  si el real no coincide** — cualquier volumen descartado se
  autocorrige en <=500ms, para ítems y Pisadores por igual. Los fades
  no se rompen: cada paso de rampa pasa por `set_volumen()`.
- `reproducir()` re-aplica el volumen en el mismo diferido de 150ms
  del seek (achica la ventana muda inicial).
- `crossfade_a()` usa `entrante.volumen_deseado()` (calculado) como
  techo del fade-in, nunca una lectura del reproductor recién
  arrancado; el piso del fade-out usa `obtener_volumen()` con el
  deseado como respaldo.
- `fade_volumen_a()` parte del deseado, no de una lectura espuria.
**Regla para el futuro**: nunca confiar en UNA llamada de volumen a
libVLC ni en leer el volumen de un reproductor recién arrancado — el
volumen se declara (deseado) y el tick lo garantiza.

**Bug real corregido — "el Pisador funciona si aprieto Siguiente,
pero no cuando la lista avanza sola" (pedido explícito, prioridad
alta)**: la única función que disparaba el Pisador era
`_reproducir_fila()` (la usan Play manual, Siguiente, y el avance
natural SIN crossfade) — pero con `crossfade_activado` en
Configuración → Fade/Transiciones (que es como Santiago usa la radio
en producción), la transición NATURAL entre dos temas pasa por
`_iniciar_crossfade()`, que nunca llamaba a `_reproducir_fila()` ni
disparaba el Pisador del tema ENTRANTE — antes documentado como
"limitación conocida" (dos rampas de volumen peleando por el mismo
motor a la vez). Esto explicaba también el síntoma "a veces sí, a
veces no": dependía de si esa transición puntual terminó pasando por
crossfade o no.

Primera corrección (insuficiente, corregida en la ronda siguiente):
disparar el Pisador recién en `_liberar_crossfade()`, al terminar la
rampa de volumen del crossfade — pero eso dejaba varios segundos SIN
NINGÚN sonido de Pisador, indistinguible en la práctica de "no sonó"
(así lo reportó Santiago probándolo con audio real: "seleccioné otro
ítem con el mismo pisador... terminó el rojo y al iniciarse no se
escuchó el pisador").

**Corrección definitiva**: `_disparar_pisador_si_corresponde()` ganó
un parámetro `aplicar_ducking: bool` que separa DOS cosas que antes
viajaban juntas: el AUDIO del Pisador (`motor_pisador.reproducir()`,
un motor totalmente independiente del principal — nunca compite con
nada) y el DUCKING (bajar el volumen del tema principal mientras
suena, que si se aplica INMEDIATO sobre el motor entrante SÍ compite
con la propia rampa de volumen del crossfade). `_iniciar_crossfade()`
ahora llama a `_disparar_pisador_si_corresponde(fila_siguiente,
aplicar_ducking=False)` YA MISMO, apenas arranca el crossfade — el
Pisador se escucha desde el primer instante, siempre. El ducking se
sigue difiriendo a `_liberar_crossfade(fila_entrante)`, una vez que la
rampa del crossfade ya terminó, con dos guards: solo se aplica si el
Pisador sigue activo (`_pisador_activo` — si ya terminó solo, por ser
corto, no hay nada que "duckear") y si `panel.fila_reproduciendo() ==
fila_entrante` (nadie tomó control manual mientras tanto). Regla de
diseño explícita para el futuro: si hay que elegir entre que el
Pisador suene siempre (aunque el ducking llegue un instante después) o
que el ducking esté perfectamente sincronizado (arriesgando que el
Pisador no se escuche), gana SIEMPRE lo primero.

**Log del Pisador (pedido explícito, para diagnosticar "por qué unas
veces suena y otras no")**: antes el ciclo de vida completo del
Pisador (disparo, cancelación, fin natural) no dejaba NINGÚN rastro en
`config/data/log_aplicacion.txt` — solo se veía qué tema principal
sonaba. Ahora `_disparar_pisador_si_corresponde()` /
`_on_pisador_finalizado()` / `_cancelar_pisador_en_curso()` (y el
arranque de cada crossfade) llaman a `registrar_evento()` con la fila,
la ruta del Pisador y el volumen de bajada — sirve para reconstruir en
el log exactamente cuándo se disparó, cuándo se canceló y cuándo
terminó solo, sin tener que reproducir el problema en vivo con
Santiago para verlo.

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

**Ventana compacta + maximizable (pedido explícito: "queda muy larga,
se me va de pantalla la última parte" / "no maximiza ni minimiza")**:
dos causas combinadas. (1) Las 6 acciones del grupo "PROGRAMACIÓN
GUARDADA" (Nueva/Cargar/Eliminar/Eliminar varias/Duplicar/Aplicar
ahora) ocupaban 3 filas — ahora entran en UNA sola fila con etiquetas
cortas (el detalle de cada botón vive en su tooltip); el campo nombre
y el botón "💾 Guardar" del grupo GUARDAR también se unificaron en una
fila en vez de dos, y la nota debajo se acortó a una sola línea. Entre
los dos cambios el alto mínimo bajó de 780 a 560px. (2) `QDialog` NO
pide los botones minimizar/maximizar de la barra de título por
defecto (a diferencia de `QMainWindow`) — quedaba solo el de cerrar,
por eso "no maximiza ni minimiza" no era un bug de layout sino que
esos botones nunca se pidieron. Corregido con
`self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint
| Qt.WindowType.WindowMaximizeButtonHint)` en el `__init__`.

**"Nueva" carga una plantilla básica de 24 bloques (pedido explícito,
punto f)**: apretar el botón "🗎 Nueva" de verdad (no los usos
INTERNOS de `_nueva_programacion()`, como vaciar el editor antes de
volcar una programación recién cargada) arma solo un esqueleto de 24
bloques vacíos, uno por cada hora del día ("00:00:00 - Bloque 00hs" ...
"23:00:00 - Bloque 23hs", `_cargar_plantilla_basica()`) — el operador
completa cada uno con sus ítems en vez de tener que crear los 24 a
mano. Parámetro nuevo `con_plantilla: bool` en `_nueva_programacion()`,
default `False` — SOLO el botón real lo pasa en `True`; si el uso
interno (antes de `_cargar_programacion_existente()`) también lo
trajera, la plantilla de 24 bloques vacíos quedaría mezclada con los
bloques recién cargados.

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

**Copiar/Pegar entre bloques (implementado, pedido explícito: "un menu
contextual donde en la selección múltiple... pueda copiar y pegar los
elementos... en otro bloque horario, así me es más fácil
programar")**: primer menú contextual real del árbol del Programador
(antes todas las acciones eran solo botones) — `self.tree.
customContextMenuRequested` conectado a `_mostrar_menu_contextual()`,
con dos entradas: "📋 Copiar" y "📌 Pegar en este bloque" (deshabilitada
si el portapapeles está vacío). `_copiar_seleccionados()` toma TODOS
los ítems seleccionados (ignora bloques enteros si están mezclados en
la selección — "copiar" es a nivel ítem, no bloque) y los serializa con
`_serializar_item()` — un helper NUEVO extraído de `_serializar_bloques()`
(que ahora lo reusa, en vez de tener la lógica de armar el dict
duplicada) — así el portapapeles (`self._portapapeles`, lista de
dicts en memoria, se pierde al cerrar la ventana, no se persiste a
disco) usa el MISMO formato de datos que ya usa el guardado a JSON,
sin un tipo de dato paralelo. "Pegar" resuelve el bloque destino con
el mismo criterio ya existente (`_bloque_destino_actual()` — el bloque
del nodo con foco, o el último bloque como fallback) y reconstruye
cada ítem copiado con `_agregar_registro_a_bloque()`/
`_agregar_comando_a_bloque()` según corresponda — soporta copiar y
pegar Comandos FMT igual que tandas de audio normales. Copiar es una
COPIA, no un mover — los ítems originales quedan intactos en su
bloque de origen, se puede pegar el mismo portapapeles en varios
bloques distintos sin volver a copiar.

### Paridad de diseño con Hardata Dinesat 9 (Ventana 1 y Ventana 2)
Pedido explícito de Santiago, con 4 fotos de referencia de Dinesat 9
("el mejor a mi gusto"): igualar lo más posible el display y la
distribución de controles de arriba, el comportamiento de los colores
rojo/verde en las listas, y fusionar Play+Siguiente en un solo botón
como hace Dinesat. Antes de implementar se confirmaron 4 decisiones
con Santiago (todas la opción recomendada): el medidor de nivel es
**solo decorativo** (python-vlc no expone nivel de audio real en vivo,
y un número inventado sería peor que no tener nada); el botón
"Siguiente" de toda la vida **se convierte en "Cut"** (mismo
comportamiento de corte seco, solo renombrado/reubicado); el nuevo
botón "Stop diferido" se bloquea con el Automático activo **igual que
el Stop actual** (mismo aviso); los íconos nuevos son **símbolos/
emoji + tooltip** (no hay assets reales de Dinesat, solo fotos
borrosas de referencia).

**Display superior (`gui/panel_reproductor.py` Ventana 2/Auxiliar,
`gui/ventana_publicidad.py` Ventana 1)**: cartel de nombre de emisora
(`lbl_nombre_estacion`, objectName `lblNombreEstacion`, texto "RADIO
TUYÚ FM 92.5") arriba de los contadores, y `MedidorNivelDecorativo`
(`gui/medidor_nivel.py`, NUEVO) — barra vertical de 5 segmentos verde/
amarillo/rojo estilo VU-meter, pegada a los contadores. Es puramente
visual: `set_activo(bool)` prende/apaga los segmentos según
`motor.esta_reproduciendo()` (mismo lugar donde ya se actualiza
`IndicadorEnVivo`, `set_indicador_en_vivo()` ahora llama a los dos).
No mide señal real — si en algún momento se consigue una forma
confiable de leer nivel de audio real de python-vlc, este widget es
el punto de enganche, pero hoy es decorativo a propósito.

**Selección celeste, rojo/verde nunca se pisan (pedido explícito, "en
ningún momento pierden su color, el celeste es solo para una
selección")**: `gui/styles.py` — `COLOR_SELECCION = "#5dade2"` (antes
la selección usaba el mismo amarillo que ya usaba otra cosa, quedaba
ambiguo). `QTreeWidget#tree_reproductor::item:selected` y
`#tree_publicidad::item:selected` ahora tienen fondo transparente +
borde celeste de 2px — como el color rojo/verde de estado ya se pinta
aparte (fondo de fila) y la selección solo agrega el borde, un ítem
puede estar SELECCIONADO (celeste) Y en punta/en cola (rojo/verde) al
mismo tiempo sin que ninguno tape al otro; seleccionar OTRO ítem solo
mueve el borde celeste, nunca toca el rojo/verde de fondo.

**Botón verde grande = Play + Siguiente-con-fundido, fusionados
(pedido explícito, punto c)**: un solo botón (`btnPlayPrincipal`,
`"▶ PLAY /\nSIG."`, grande, a la izquierda de la grilla de transporte)
reemplaza la vieja dualidad de apretar Play y aparte Siguiente para
avanzar. `_on_click_play()` (en `GestorPlaylist` y `GestorPublicidad`)
decide según el estado real del motor:
- **En silencio**: comportamiento de Play de siempre — arranca el
  ítem armado/seleccionado (`reproducir_actual()` /
  `_reproducir_seleccion_o_actual()`), sin cambios.
- **Sonando algo**: actúa como "Siguiente" pero SIEMPRE con fundido
  (nunca corte seco) — avanza al ítem en cola (verde) si hay uno, si
  no al próximo válido, respetando todas las reglas ya existentes de
  `_avanzar()` (freno de hora de bloque, límites del árbol, etc.).
  Usa una duración de fundido FIJA y corta,
  `DURACION_FUNDIDO_MANUAL_SEGUNDOS = 1.2` (separada a propósito de
  `duracion_fade_segundos` de Configuración — este botón siempre
  funde, sin importar si el operador tiene el crossfade automático
  apagado en Configuración → Fade/Transiciones).
- **Diferencia de arquitectura V1 vs. V2, documentada y deliberada**:
  Ventana 2 (`GestorPlaylist._avanzar_con_fundido`) reutiliza el
  motor DUAL de crossfade que ya existía (`_iniciar_crossfade`, ahora
  con un parámetro `duracion_segundos` opcional en vez de siempre leer
  la config) — es un fundido SUPERPUESTO real, igual que el crossfade
  automático de fin de tema. Ventana 1 (`GestorPublicidad`) NO tiene
  motor dual (siempre tuvo un solo `MotorAudio`) — implementar un
  crossfade real ahí era alcance grande con riesgo de regresión sobre
  `_avanzar()` (método históricamente delicado, con las reglas de
  freno por hora de bloque). Se optó por un fundido SECUENCIAL con el
  mismo botón (`_avanzar_con_fundido`/`_completar_avance_con_fundido`
  en `core/playlist_manager.py`): baja el volumen del ítem actual a 0
  en 1.2s, y RECIÉN AHÍ llama a `_avanzar()` sin modificarlo (para
  heredar todas sus reglas tal cual están), y sube el volumen del
  ítem nuevo desde 0. No se superpone (no suena simultáneo un
  instante como en V2), pero tampoco es un corte seco — sigue siendo
  un fundido, solo que uno atrás del otro. Mejora futura si Santiago
  pide overlap real en Ventana 1: armar el mismo motor dual que ya
  tiene `GestorPlaylist`.
- Un fundido manual en curso no se puede superponer con otro
  (`_crossfade_en_curso` en V2, `_fundido_en_curso` en V1) — apretar
  el botón verde de nuevo mientras el fundido está corriendo no hace
  nada.

**Botón "Fade" / Fade-Stop (nuevo, 2do botón de la fila de arriba,
`btnFadeStop`)**: fundido de volumen hasta apagar el ítem en
reproducción y detenerlo — distinto de Stop (corte seco inmediato) y
de Stop diferido (dejar terminar solo). `_fade_stop()` en ambos
gestores: `motor.fade_volumen_a(0, DURACION_FUNDIDO_MANUAL_SEGUNDOS)`
+ `QTimer.singleShot` que llama a Stop real una vez terminada la
rampa (con margen de 150ms). Si no hay nada sonando, actúa como Stop
directo (nada que fundir).

**Botón "Cut" (antes "Siguiente", renombrado — pedido explícito,
comportamiento SIN CAMBIOS)**: corte seco e inmediato al siguiente
ítem, tal cual funcionaba el viejo botón Siguiente — a propósito el
nombre interno de la señal (`solicitud_siguiente`) y del slot
(`_avanzar_al_siguiente`) no cambiaron, solo el texto/objectName/
tooltip visibles (`btnCut`), para minimizar puntos de contacto y
riesgo de regresión sobre un botón que ya funcionaba bien.

**Botón "Stop diferido" (nuevo, `btnStopDiferido`, con contorno
naranja permanente + relleno cuando está armado — mismo patrón visual
que `btnAutomatico`)**: es un TOGGLE, no una acción inmediata — un
primer click lo ARMA (deja terminar el ítem actual solo, y ahí
detiene TODA la emisión en vez de avanzar al siguiente); un segundo
click lo DESARMA sin tocar nada más. `_toggle_stop_diferido()` /
`_cancelar_stop_diferido()` en ambos gestores, con
`panel.set_stop_diferido_armado(bool)` reflejando el estado en la UI
(`COLOR_ARMADO = "#e67e22"` en `gui/styles.py`). El guard vive en UN
solo lugar por gestor — el TOPE de `_avanzar()` (V1) / `_avanzar()`
(V2) — así cubre TODOS los disparadores por igual (fin natural de
ítem, Cut manual, cascada de reintentos por error): si está armado,
se desarma y se llama a Stop en vez de continuar. En V2 además se
frena `_chequear_crossfade()`/`_iniciar_crossfade()` mientras está
armado, para que no arranque una transición automática que
`_avanzar()` tendría que cortar de nuevo.

**Automático como 4to botón de la fila de abajo (solo Ventana 1,
pedido explícito "la ventana 1 tiene un 4to botón abajo")**: el botón
ya existente se movió de la barra superior (`barra_superior`, donde
convivía con `lbl_estado`) a la grilla de transporte, como último
botón de `fila_inferior` junto a Pausa/Cut/Stop-diferido. Texto
acortado de "AUTOMÁTICO: ON/OFF" a "AUTO"/"MAN" para entrar en el
espacio compacto de la grilla — el estado completo sigue disponible
en `lbl_estado` ("Automático Activo"/"Modo Manual", sin cambios) y en
el tooltip del botón. Su lógica (`_toggle_automatico`, contorno rojo
permanente, bloqueo de Stop) no cambió, solo la ubicación visual.

**Bloqueo por Automático extendido a Fade-Stop y Stop diferido
(pedido explícito, mismo criterio ya usado para Stop)**: con el
Automático activo, los tres botones (Stop, Fade-Stop, Stop diferido)
de Ventana 1 y Ventana 2 muestran el mismo aviso ("primero desactivá
el Automático") en vez de actuar — mismo helper
`_avisar_bloqueado_por_automatico()` reutilizado por los tres
handlers en cada ventana. La Auxiliar no se toca (nunca recibe
`set_stop_habilitado()`), así que sus tres botones nunca quedan
bloqueados — consistente con la regla ya establecida.

**Fila de transporte reorganizada (2 filas + botón grande)**: en vez
de una sola fila de 4-5 botones, ahora es `btn_play` grande a la
izquierda + una grilla de 2x2 a la derecha (`fila_superior`: Stop,
Fade-Stop / `fila_inferior`: Pausa, Cut, Stop-diferido [, Automático
en V1]) — necesario para sumar los 2 botones nuevos sin volver a la
fila ancha de una sola línea que ya se había descartado en una ronda
anterior por ocupar demasiado ancho.

Probado con 15 tests nuevos dedicados (botón verde Play-vs-fundido en
ambos estados y en ambas ventanas, no superposición de fundidos, Cut
sin cambios, Fade-Stop con y sin audio sonando, Stop diferido armado/
desarmado/disparado por fin natural, bloqueo por Automático de los
tres botones, color celeste de selección en la QSS, existencia de los
6 botones + Automático) + suite de regresión completa (26 scripts)
sin fallos nuevos — los 2 fallos preexistentes (`test_confirmaciones.py`,
`test_log_git.py`, de rondas anteriores, entorno) y 2 fallos de
horario dependientes de la hora real del sistema
(`test_ciclo_automatico.py`, `test_play_bloque_y_hora.py`, ya fallaban
igual en el commit anterior a esta ronda, confirmado con `git stash`)
siguen igual, sin relación con este cambio. Falta que Santiago lo
compare con Dinesat en su pantalla real y confirme: si el layout de
2 filas + botón grande se parece lo suficiente a las fotos que mandó,
si el medidor de nivel decorativo cumple su función visual aunque no
mida audio real, y si el fundido secuencial de Ventana 1 (a diferencia
del solapado de Ventana 2) se nota o le alcanza así.

### Ronda de ajustes post-Dinesat (Ahora/Luego angostos, selección
que nunca pisa rojo/verde, preload, swap Automático/Fade, ícono "ya
reproducido")
Pedido explícito tras la primera comparación con Dinesat, 5 puntos:

**a) "Ahora"/"Luego" mucho más angostos**: `EtiquetaMarquesina`
(`gui/etiqueta_marquesina.py`) usaba `sizeHint() = 220x30` con
política `Expanding` — dentro de un `QHBoxLayout` era el único widget
que podía crecer, así que se comía TODO el ancho sobrante del panel,
inflando el frame entero a un cartel enorme de punta a punta. Bajado
a `sizeHint() = 130x22` y política `Preferred`; y, más importante,
`frame_ahora`/`frame_luego` ahora se agregan a `layout_grupo` con
`Qt.AlignmentFlag.AlignLeft` (`panel_reproductor.py` y
`ventana_publicidad.py`) — sin eso, un `QVBoxLayout` estira igual
CUALQUIER hijo a todo su ancho sin importar la política del hijo; con
`AlignLeft` el frame se dimensiona por el `sizeHint()` real de su
contenido (indicador + etiqueta + sticker angosto) en vez de ocupar
todo el panel.

**b) Rojo/verde NUNCA cambian al seleccionar (bug real corregido)**:
Santiago reportó que, a pesar del cambio de la ronda anterior, un
ítem en rojo/verde SEGUÍA perdiendo su color al seleccionarlo. Causa
de fondo: la técnica QSS usada (`background-color: transparent;
border: 2px solid celeste` en `::item:selected`) tiene una limitación
real de Qt — en cuanto el stylesheet define CUALQUIER propiedad para
un estado (`:selected`), Qt deja de pintar el brush propio del ítem
(`Qt::BackgroundRole`, seteado por `item.setBackground()`) para ESE
estado y pinta directamente lo que dice el QSS; como acá decía
"transparent", el rojo/verde se perdía por completo al seleccionar
(quedaba solo el borde celeste sobre el fondo oscuro del árbol) — el
QSS no tiene forma de "preguntar" si el ítem tiene un color propio
antes de decidir qué pintar. Corregido con un delegado propio,
`DelegadoConservaColorEstado` (`gui/common_widgets.py`, subclase de
`QStyledItemDelegate`): si el ítem está en rojo/verde
(`ROL_ESTADO_ITEM`, leído siempre de la columna 0 vía
`index.sibling(index.row(), 0)` porque el rol solo se guarda ahí, aunque
el color se pinte en las 3 columnas) Y está seleccionado, se le saca el
flag `State_Selected` a una copia de la opción antes de pintar (así
`super().paint()` usa el color propio del ítem, nunca el highlight) y
se dibuja a mano un borde celeste fino encima — mismo aspecto que
antes, pero sin perder el fondo. Cualquier ítem SIN estado sigue el
camino de siempre (QSS puro, ya confirmado correcto por Santiago: "el
color es celeste, correcto" para ítems normales). El delegado se
instala en `ArbolReproductorConDrop.__init__` y
`ArbolPublicidadConDrop.__init__` (nuevo), cubriendo Ventana 1, 2 y
Auxiliar (que reutiliza `ArbolReproductorConDrop`) de una sola vez.

**c) Preload al iniciar / cargar música / cargar programación**:
`main.py` muestra un `QSplashScreen` (ícono + "Cargando Auto-Radio
Tuyú...") entre crear la `QApplication` y terminar de construir
`MainWindow`, cerrado con `splash.finish(ventana)` recién cuando la
ventana ya está lista. Dentro de la app, `MainWindow._mostrar_preload(
texto, duracion_ms=900)` (cursor de espera + mensaje en la barra de
estado, con timeout propio en `showMessage()` para no pisar un
mensaje posterior — antes un `clearMessage()` diferido a mano hubiera
podido borrar prematuramente un mensaje DISTINTO mostrado después,
como "Agregado: X") se dispara en tres puntos: al terminar
`MainWindow.__init__` (arranque), en `VentanaPublicidad.
cargar_bloques()` — nueva señal `programacion_cargada`, cubre los 4
lugares que llaman a `cargar_bloques()` (manual, scheduler de
medianoche/arranque, "Aplicar ahora") con un solo punto de enganche —
y en `MainWindow._on_archivo_agregado()` (ya conectado a
`VentanaExplorador.archivo_agregado`, que ya disparaba tanto para alta
individual como en lote — no hizo falta tocar `ventana_explorador.py`).
`_preload_activo` evita apilar `setOverrideCursor()` si se dispara de
nuevo antes de que termine el anterior.

**d) AUTOMÁTICO y FADE intercambiados (Ventana 1, pedido explícito
"más intuitivo y a la vista")**: en `ventana_publicidad.py`,
`fila_superior` pasó de [Stop, Fade-Stop] a [Stop, AUTOMÁTICO] y
`fila_inferior` de [Pausa, Cut, Stop diferido, AUTOMÁTICO] a [Pausa,
Cut, Stop diferido, Fade-Stop] — mismos botones, mismas conexiones,
solo se reordenaron las líneas `addWidget()`. Exclusivo de Ventana 1
(Ventana 2/Auxiliar no tienen botón AUTOMÁTICO).

**e) Ícono "ya reproducido" (pedido explícito: "una marca a la
izquierda, con ícono de OK... no escrito, solo ícono")**: nuevo rol
`ROL_YA_REPRODUCIDO` (`gui/styles.py`) y `icono_reproducido()` —
tilde verde armada a mano con `QPainter` sobre un `QPixmap` de 14x14
(no hay assets reales), cacheada en un global del módulo porque un
`QPixmap` no se puede construir antes de que exista `QApplication`
(la primera construcción real ocurre recién en tiempo de ejecución).
`_pintar_item()` (en `panel_reproductor.py` Y `ventana_publicidad.py`,
mismo patrón en las dos) llama `item.setIcon(0, icono_reproducido())`
únicamente en la rama `ESTADO_REPRODUCIENDO` — se pone al arrancar a
sonar y **ya nunca se saca**, ni cuando el ítem deja el rojo (la rama
que limpia el color a `ESTADO_NORMAL` no toca el ícono). Como
`setIcon()` es un ícono real de Qt (no texto concatenado al título),
aparece a la izquierda del texto de la columna 0 sin tocar el título
en sí. Cubre Ventana 1, 2 y Auxiliar (misma `PanelReproductor`). La
marca es solo de la sesión actual (no se persiste a disco) —
consistente con que los bloques/playlists ya se recargan solos cada
día/reinicio.

Probado con 10 tests nuevos dedicados (ancho de `EtiquetaMarquesina`,
frames "Ahora" bastante más angostos que el panel en Ventana 1 y 2,
delegado instalado en ambos árboles, color de fondo intacto tras
seleccionar un ítem rojo, preload manual se muestra/retira solo,
`cargar_bloques()` dispara el preload, agregar música dispara el
preload, posición intercambiada de Automático/Fade por coordenada Y
real tras `show()`, ícono aparece al sonar y persiste en Ventana 1 y
2) + suite de regresión completa sin fallos nuevos — los mismos 4
fallos preexistentes de siempre (`test_confirmaciones.py`,
`test_log_git.py`, y los 2 dependientes de la hora real del sistema)
confirmados sin relación con este cambio (`git stash`). Falta que
Santiago confirme en su notebook real que los carteles ahora se ven
angostos como pidió, que el rojo/verde ya no se pierde nunca al
seleccionar con un click real, y que el preload (cursor de espera +
mensaje) se nota lo suficiente sin resultar molesto en el uso diario.

### Ronda de aprovechamiento de espacio (relojes apilados, renombre de
ventanas, nombre de emisora configurable)
Pedido explícito, 3 puntos:

**a) Relojes apilados a la izquierda + Ahora/Luego a la derecha (ahorra
otra fila)**: antes la fila de contadores (reloj transcurrido + reloj
restante lado a lado + medidor) y las filas "Ahora"/"Luego" eran 3
filas separadas. Ahora es UNA sola fila combinada
(`fila_info = QHBoxLayout()`, en `panel_reproductor.py` y
`ventana_publicidad.py`): a la izquierda una columna angosta
(`columna_relojes = QVBoxLayout()`) con el reloj transcurrido arriba y
el restante abajo (`setMaximumWidth(90)` en los dos, y la fuente de
`QLabel#lblTiempoTranscurrido`/`#lblTiempoRestante` bajó de 14pt a
11pt en `gui/styles.py` — apilados verticalmente ya no necesitan tanto
ancho), el medidor de nivel decorativo al costado, y a la derecha
`columna_ahora_luego` con los mismos frames "Ahora"/"Luego" de
siempre, uno arriba del otro. `fila_info.addStretch()` al final
mantiene las dos columnas compactas a la izquierda (mismo criterio que
el `AlignLeft` de la ronda anterior, pero acá hace falta un stretch
porque ahora son sub-layouts anidados dentro de un `QHBoxLayout`, no
widgets sueltos en el `QVBoxLayout` del panel).

**b) Ventanas renombradas (pedido explícito)**: el título del
`QGroupBox` de Ventana 1 pasó de "PUBLICIDAD" a "PROGRAMACIÓN /
ROTATIVA" (`ventana_publicidad.py`), y el de Ventana 2 de "EMISIÓN
MUSICAL ACTUAL" a solo "EMISIÓN" (`ventana_emision.py`, se lo pasa a
`PanelReproductor`). Es solo el título VISIBLE — los nombres de clase
(`VentanaPublicidad`, `GestorPublicidad`, etc.), archivos, variables y
comentarios internos NO se tocaron (cambiarlos hubiera sido un
refactor grande sin pedido explícito para eso).

**c) Nombre de emisora configurable, junto al reloj del toolbar
(reemplaza el cartel fijo de cada panel)**: nueva clave
`general.nombre_emisora` en `config_general.json` (default
`"RADIO TUYÚ FM 92.5"`, así una instalación existente no "pierde" el
texto que ya tenía fijo) — campo de texto en Configuración → General
(`gui/ventana_configuracion.py`, `txt_nombre_emisora`). El cartel
"RADIO TUYÚ FM 92.5" que antes vivía DUPLICADO en cada panel
(`lbl_nombre_estacion` en `panel_reproductor.py` Y en
`ventana_publicidad.py`) se sacó de los dos por completo — ese
espacio ahora es una fila menos de alto en Ventana 1 y 2 (para el
punto (a) de arriba), y el nombre se muestra UNA sola vez, en el
toolbar de `MainWindow` (`lbl_nombre_emisora`, objectName
`lblNombreEstacion` — reutiliza el mismo selector QSS que ya existía,
mismo aspecto naranja/decorativo), a la izquierda del reloj de
día/hora. `MainWindow._actualizar_nombre_emisora()` lo refresca en
`_construir_toolbar()` (arranque) y en `_aplicar_configuracion_en_vivo()`
(al guardar Configuración) — cambiar el nombre no requiere reiniciar
la app, mismo patrón ya establecido para el resto de "aplicar
configuración en vivo".

Probado con 7 tests nuevos dedicados (títulos de Ventana 1/2 por
`QGroupBox.title()`, relojes apilados verificados por geometría real
tras `show()` — misma X, Y creciente, Ahora/Luego a la derecha en la
misma fila combinada—, ausencia del atributo `lbl_nombre_estacion` en
ambos paneles, nombre de emisora por defecto visible en el toolbar,
actualización en vivo del toolbar al guardar Configuración, y
carga/guardado correcto del campo nuevo en `VentanaConfiguracion`) +
suite de regresión completa sin fallos nuevos (mismos 4 fallos
preexistentes de siempre, ninguno relacionado con este cambio). Falta
que Santiago confirme en su notebook real cuánto espacio vertical
ganó de verdad, y que el nombre de emisora se vea bien ubicado junto
al reloj del toolbar.

### Estudio del manual de Hardata Dinesat 9/Visual y mejoras "bajo a
medio" inspiradas ahí
Santiago pasó el manual completo de Dinesat Visual (la referencia de
diseño de toda esta app) y pidió comparar función por función qué
tenemos y qué se podría sumar, ANTES de encarar los dos ítems que más
usa: **Musicalizador Avanzado** (encadenado con **Comandos FMT**) —
ambos quedan pendientes para una ronda dedicada, ver roadmap. Quedó
EXPLÍCITAMENTE afuera de cualquier propuesta todo lo que depende de
una cadena de emisoras (Satélite+Tonos/RS232/Reemplazo de Música,
comandos PLAY LOCAL/STOP LOCAL/SYNC/REC/PGM1/PGM2, Server de Backup)
— Santiago fue explícito: "Satélite, Remoto, no me gusta", esta app es
para UNA sola emisora standalone. También quedaron afuera: video/NDI/
switcher (la app es de audio), RDS (declinado en una ronda anterior),
acceso web multiusuario (arquitectura cliente-servidor grande, no
aplica a una app de escritorio de un operador), extractor de CD
(hardware legacy), Contestador Telefónico SIP (necesita línea/SIP),
Grabador Continuo (**declinado por Santiago en esta ronda**: "los
micrófonos no están enchufados a la PC, la grabación del master seria
siempre de la música... no tiene sentido" — a reconsiderar el día que
conecte la consola por USB a la PC), Asistente en vivo/soundboard y
"Anuncio" (concepto de Dinesat distinto del Pisador, atado a un tema
específico por código — Santiago pidió encararlo junto con el
Musicalizador Avanzado, ya que en Dinesat se configura desde ahí).

De los candidatos "bajo a medio" que SÍ se pidieron para esta ronda,
uno quedó fuera del pedido en vivo (implementado):

**a) Vigencia de fecha por material (pedido explícito, alcance
acotado a Ventana 1/Publicidad — es el caso de uso real, "campaña que
vence")**: nuevo rol `ROL_VIGENCIA` (`gui/styles.py`) con
`{"fecha_inicio", "fecha_fin"}` (ambos opcionales, `None` = sin
restricción) y `config/settings.vigencia_activa(vigencia, hoy=None)`
— función PURA (sin Qt), fail-open ante una fecha faltante o corrupta
(nunca silencia un ítem por un dato mal formado). Se puede fijar al
IMPORTAR un archivo (`DialogoAgregarArchivo`, checkbox + `QDateEdit`
por cada fecha) o editar DESPUÉS sobre un material ya cargado con el
nuevo ítem de menú contextual "📅 Vigencia..." de Ventana 3
(`gui/dialogo_vigencia.py`, dialogo chico reutilizable, mismo patrón
de checkbox+`QDateEdit` que ya usaba `dialogo_duplicar_programacion.py`).
La vigencia VIAJA con el ítem igual que `ROL_ANALISIS_AUDIO` (mismo
patrón ya establecido) — se propaga en `VentanaPublicidad.
agregar_tanda()`/`cargar_bloques()`, en el drag&drop
(`MainWindow._on_archivo_soltado_publicidad`) y en las 4 rutas del
Programador que tocan un ítem (`_agregar_registro_a_bloque`,
`_reemplazar_seleccionado`, `_cargar_programacion_existente`,
`_serializar_bloques`) — así sobrevive guardar/cargar una programación
completa. El gating real vive en
`GestorPublicidad._item_valido()` (`core/playlist_manager.py`): un
ítem fuera de vigencia se trata como inválido y se SALTEA al buscar
el próximo candidato, exactamente igual que Dinesat describe ("En las
ventanas de Emisión simplemente salteará el material, continuando con
la reproducción normalmente, sin detener la emisión") — nunca se
borra solo, sigue en la lista, se saltea cada vez que le toca. A
propósito NO se extendió a Ventana 2/Auxiliar en esta ronda (vigencia
de fecha es un concepto de campaña publicitaria, no de música) — si
Santiago lo pide para música más adelante, es la misma extensión.

**b) Historial de reproducción PERSISTENTE (pedido explícito,
distinto del ícono "ya reproducido" que solo dura la sesión)**:
`config/settings.registrar_reproduccion(ventana, titulo, codigo, ruta)`
escribe una línea con timestamp en `config/data/
historial_reproduccion.txt`, mismo mecanismo de rotación que
`log_aplicacion.txt` (rota a `.anterior.txt` pasados 2MB —
`_rotar_archivo_si_corresponde()` se generalizó a partir de
`_rotar_log_si_corresponde()` para poder reusarla en los dos
archivos). Se dispara desde el mismo punto donde ya se pone el ícono
de "ya reproducido" — `_pintar_item()` en `panel_reproductor.py`
(Ventana 2/Auxiliar, usa `self._titulo_panel` como identificador de
ventana) y en `ventana_publicidad.py` (Ventana 1, hardcodeado
"Publicidad"). "Consultable después" (pedido explícito): botón nuevo
"📊 Ver historial de reproducción" en Configuración → Diagnóstico,
mismo patrón que el botón "Ver log" ya existente (abre el archivo de
texto con el visor por defecto del sistema vía `QDesktopServices`).

**c) Pisador también en el Outro (pedido explícito, extiende el motor
de Pisador ya maduro de Ventana 2/Auxiliar — Ventana 1 no tiene
Pisador, no aplica ahí)**: en vez de dos pisadores simultáneos por
tema, se agregó una POSICIÓN al Pisador único ya existente —
`ROL_POSICION_PISADOR` (`gui/styles.py`), `"inicio"` (default, mismo
comportamiento de siempre) o `"final"`. Elegible en
`DialogoElegirPisador` (dos radio buttons "Al empezar el tema (Intro)"
/ "Al terminar el tema (Outro)") — el drag&drop directo de un Pisador
sobre un tema sigue asignando "inicio" sin cambios (solo el flujo del
diálogo ofrece elegir). Visualmente el ítem anidado muestra "(Outro)"
al final del título si corresponde. En el motor
(`core/gestor_emision.py`): los dos puntos que ya disparaban el
Pisador al ARRANCAR el tema (`_reproducir_fila`, `_iniciar_crossfade`)
ahora se saltean si la posición es "final"; un nuevo
`_chequear_pisador_outro()`, colgado de la MISMA señal
`restante_ms_cambio` que ya usa el crossfade
(`UMBRAL_DISPARO_PISADOR_OUTRO_MS = 3000`), dispara
`_disparar_pisador_si_corresponde()` — la MISMA función que ya usaba
el Pisador de inicio, sin duplicar nada de la lógica de ducking/
generación/fade — cuando falta poco para el final. Guard
`_fila_pisador_outro_disparado` evita re-disparar en cada tick una vez
que ya sonó para esa fila (se resetea a -1 cada vez que arranca un
tema nuevo). **Limitación conocida y documentada a propósito** (mismo
criterio que ya se usó en su momento para el Pisador de inicio +
crossfade, antes de resolverse en una ronda posterior): si hay un
crossfade EN CURSO sobre ese mismo ítem, el Pisador de Outro NO se
dispara — evita competir con la propia rampa de volumen del crossfade
sobre el mismo motor; si el crossfade corta la reproducción antes de
que le toque sonar, se revisa con audio real en una ronda futura si
hace falta, igual que se hizo antes con el Pisador de inicio. **Bug
real corregido de paso**: `VentanaEmision`/`VentanaAuxiliar`
(`gui/ventana_emision.py`/`gui/ventana_auxiliar.py`) NO delegaban
`posicion_pisador_en_fila()` al panel — mismo tipo de bug ya
documentado antes ("cuando un wrapper delega en PanelReproductor, hay
que delegar TODOS los métodos que el core necesita"), atrapado por los
tests nuevos de esta ronda antes de llegar a Santiago.

**d) Función de selección aleatoria reutilizable sobre categoría/
subcategoría (pedido explícito, preparación para el Musicalizador
Avanzado — "es importante ir teniendo escrito la función aleatoria...
para que siempre suene temas musicales diferentes todos los días")**:
`VentanaExplorador.listar_registros_de_categoria(item_categoria,
recursivo=True)` (reutiliza el helper recursivo `_para_cada_categoria`
ya existente, pasándole la categoría como punto de partida en vez de
recorrer toda la biblioteca) y `elegir_aleatorio_de_categoria(
item_categoria, recursivo=True, excluir_rutas=None)` — esta última
usa `random.choice()` sobre los candidatos, y si `excluir_rutas` (para
más adelante: "no repetir los últimos N temas") vacía la lista de
candidatos, IGNORA la exclusión antes que devolver `None` (mejor
repetir un tema a dejar un hueco de silencio). Por ahora son funciones
de librería sin ningún botón que las use todavía — el enganche real
llega con el Musicalizador Avanzado.

Probado con 22 tests nuevos dedicados (vigencia: item inválido antes/
después/dentro del rango, `_item_valido`/`_avanzar` la respetan,
persistencia ida y vuelta en `playlist_publicidad.json`, diálogo de
alta y de edición; historial: se escribe al marcar reproduciendo en
V1 y V2; Pisador de Outro: no dispara al arrancar, dispara cerca del
final, no se re-dispara, se bloquea con un crossfade en curso, el de
Inicio sigue sin cambios, el diálogo expone la posición elegida;
aleatorio: recursivo suma subcategorías, no-recursivo no, siempre
elige dentro del alcance dado, exclusión no vacía la selección,
categoría vacía da `None`) + suite de regresión completa sin fallos
nuevos (mismos 4 fallos preexistentes de siempre). Falta que Santiago
pruebe con datos reales: vigencia con una tanda real vencida, el
Pisador de Outro con audio real (esta ronda, como toda vez que se
toca este motor, no se puede probar con VLC real en el sandbox), y
que confirme el criterio de "excluir_rutas nunca deja hueco" antes de
que el Musicalizador Avanzado lo use de verdad.

### Musicalizador Avanzado + Comandos FMT (implementado, pedido
explícito — "uno de los últimos 2 [temas] que más uso, encadenado")

Santiago mandó 11 puntos describiendo cómo funciona en Dinesat 9 y
pidió que se le pregunte todo antes de encarar el diseño. Se hicieron
4 preguntas críticas por `AskUserQuestion`, y las 4 respuestas son
decisiones de arquitectura que quedaron FIJAS:

1. **La música generada por un comando FMT carga en Ventana 2
   (Emisión), NO en Ventana 1** — aunque el pedido original de
   Santiago decía literalmente "ventana 1" en los puntos 6-8, eso
   contradice tanto el propio Dinesat (el FMT alimenta la emisión
   continua, no la tanda publicitaria) como el punto 4 (Pisador en el
   aleatorio — el motor de Pisador solo existe en Ventana 2/Auxiliar).
   Se lo señalé explícitamente a Santiago y confirmó Ventana 2. El
   *comando* en sí (el ítem "▶ FMT: Folclore") sigue viviendo dentro
   de un bloque de Ventana 1 — es RECIÉN AHÍ, al pasarle el turno de
   reproducción, que dispara la generación en Ventana 2.
2. **El comando se crea eligiendo de una LISTA de formatos ya creados**
   en el Musicalizador — no escribiendo texto libre ("FMT Folclore")
   como en Dinesat. Más seguro: nunca queda un comando "huérfano"
   apuntando a un nombre mal tipeado.
3. **El no-repetir del aleatorio sobrevive reinicios**, consultando el
   historial de reproducción PERSISTENTE (`historial_reproduccion.txt`,
   de la ronda anterior) en vez de un contador solo en memoria.
4. **Validación**: referencias rotas y categorías vacías son solo
   AVISOS (no bloquean guardar); un bucle de subformatos (A→B→A) SÍ
   bloquea. Pedido explícito adicional de Santiago sobre este punto:
   *"que luego se borre un item [de la biblioteca]. No debe impedir
   que cargue los demás item del musicalizador"* — el motor en tiempo
   de ejecución nunca debe frenarse por un ítem roto, solo saltearlo.

**Decisión propia, explicada a Santiago antes de empezar (reducción de
alcance deliberada)**: en vez de construir un tipo de "material" FMT
nuevo en el Explorador/biblioteca (como hace Dinesat, con géneros y
drag&drop propios — alcance grande, similar al que llevó la vigencia
de fecha), el comando FMT se inserta DIRECTO como un ítem especial de
un bloque de Ventana 1 (o del Programador), vía un diálogo dedicado
que lista los formatos existentes. Nunca pasa por la biblioteca.

**Datos** (`config/data/musicalizador.json`, vía
`config/settings.py`: `cargar_musicalizador`/`guardar_musicalizador`/
`listar_formatos`/`obtener_formato`/`guardar_formato`/
`eliminar_formato`/`renombrar_formato`, escritura atómica igual que el
resto de la app):
```json
{"formatos": {
    "Folclore": {"items": [
        {"tipo": "especifico", "ruta": "...", "pisador_categoria": [...]|null, "pisador_posicion": "inicio"|"final"},
        {"tipo": "aleatorio", "categoria": ["Música","Folclore"], "recursivo": true, "pisador_categoria": [...]|null, "pisador_posicion": "..."},
        {"tipo": "subformato", "nombre": "OtroFormato", "duracion_segundos": 600}
    ]}
}}
```
Tres tipos de ítem, calcados del manual de Dinesat (punto 1): **Específico**
(un archivo fijo, nunca aleatorio — punto 11), **Aleatorio** (siempre
elige EXACTAMENTE un tema al azar de una categoría+subcategorías, con
Pisador opcional Intro/Outro — punto 4), **Subformato** (otro formato
ya creado, expandido hasta cubrir X minutos — permite anidar
musicalizadores, ej. "1 hora de separadores variados" del punto 9).

**Motor puro** (`core/musicalizador.py`, deliberadamente SIN Qt —
recibe un objeto "explorador" duck-typed con 4 métodos:
`buscar_registro_por_ruta`, `buscar_categoria_por_ruta`,
`listar_registros_de_categoria`, `elegir_aleatorio_de_categoria`; en
producción es la `VentanaExplorador` real, en tests es un
`ExploradorFalso` sin QApplication):
- `generar_items(explorador, nombre_formato, cantidad)`: función
  pública principal. Repite la secuencia de ítems del formato tantas
  veces como haga falta hasta juntar `cantidad` ítems concretos
  (punto 8: "siempre repitiendo el esquema"); si una vuelta completa
  no agrega ningún ítem (formato totalmente roto), corta en vez de
  colgarse.
- No-repetir (punto 10): `config/settings.rutas_recientes_en_historial()`
  lee `historial_reproduccion.txt` de ATRÁS para adelante y junta
  hasta `len(candidatos)-1` rutas distintas de esa categoría como
  exclusión — garantiza que el tema N-ésimo de una categoría de N
  siempre pueda sonar (nunca se vacía la lista de candidatos), y se
  autorregenera solo a medida que pasa el tiempo. Parsea cada línea
  con `rsplit(" - ", 1)` (no `split`) para no romperse con un título
  que contenga " - " en el medio.
- Cada resolución (`_resolver_especifico`/`_resolver_aleatorio`/
  subformato) devuelve vacío en vez de tirar excepción ante una
  referencia rota — así un ítem roto se saltea solo sin frenar a los
  demás (el pedido explícito de Santiago del punto 4). Probado con un
  formato donde 2 de 3 ítems están rotos: los otros 2 siguen
  generando con normalidad.
- Protección de ciclos en runtime (además de la validación de guardado
  más abajo): un parámetro `visitados: frozenset` viaja por toda la
  cadena de expansión de subformatos — nunca confiar en una sola capa
  de protección (mismo espíritu que ya rige el resto del proyecto
  tras los bugs de libVLC). Probado con `signal.alarm(5)` para
  confirmar que un ciclo A→B→A no cuelga el motor.
- `validar_formato(explorador, nombre_actual, items, todos_los_formatos)`:
  se llama SOLO al guardar (`VentanaMusicalizador._guardar_formato_actual`).
  Devuelve una lista de problemas con `bloquea: bool` — referencia
  rota / categoría vacía → aviso (no bloquea, con confirmación
  "¿Guardar igual?"); ciclo de subformatos → bloquea el guardado por
  completo (`QMessageBox.warning`, sin persistir).

**Comando FMT en Ventana 1** (`gui/styles.py`: `ROL_ES_COMANDO`,
`ROL_TIPO_COMANDO`, `ROL_PARAMETRO_COMANDO`, `COLOR_COMANDO` = azul
`#2980b9`, para distinguirlo a simple vista del rojo/verde de estado y
del violeta del Pisador): `VentanaPublicidad.agregar_comando()`/
`es_comando()`/`tipo_comando_de_item()`/`parametro_comando_de_item()`
— un ítem SIN ruta, muestra "▶ FMT: Folclore" en vez de título/
duración/código reales. Se inserta con el diálogo nuevo
`gui/dialogo_insertar_comando_fmt.py` (lista los formatos vía
`listar_formatos()`; si no hay ninguno, avisa y no deja seguir), desde
el menú contextual de Ventana 1 ("▶ Insertar Comando FMT...") y desde
un botón nuevo del Programador ("▶ Comando FMT..." en la fila de
ítems). El comando viaja con el bloque en TODOS los caminos ya
existentes de persistencia/carga — `cargar_bloques()` (Ventana 1),
`_guardar_estado_ahora()`/`_restaurar_desde_disco()`
(`core/playlist_manager.py`), y `_serializar_bloques()`/
`_cargar_programacion_existente()` (Programador) — todos ramifican por
`item.get("es_comando")`/`hijo.data(0, ROL_ES_COMANDO)` antes de tratar
el ítem como audio. "Reemplazar" del Programador avisa en vez de
corromper un comando si se lo selecciona por error (los comandos no se
"reemplazan": se quita y se agrega uno nuevo).

**Disparo y generación continua** (`core/playlist_manager.py`
`GestorPublicidad`): `_item_valido()` ahora acepta un comando como
válido aunque no tenga ruta; `_reproducir_item()` detecta
`ventana.es_comando(item)` y, en vez de reproducir audio, llama a
`_ejecutar_comando()` (registra el evento en el log, y si el tipo es
"FMT" invoca el callback `self.al_comando_fmt(parametro)`) y sigue
DIRECTO al próximo ítem con `_avanzar()` — cero tiempo de aire, tal
cual describe Dinesat. `MainWindow._inicializar_motores_audio()`
conecta `gestor_publicidad.al_comando_fmt = gestor_emision.iniciar_musicalizador`.

`core/gestor_emision.py` (`GestorPlaylist`) ganó `ventana_explorador`
en el constructor (para poder resolver categorías) y:
- `iniciar_musicalizador(nombre_formato)`: activa el modo, genera un
  primer lote de `TAMAÑO_LOTE_MUSICALIZADOR = 8` ítems.
- `_generar_lote_musicalizador()`: llama a `generar_items()`, agrega
  cada ítem concreto al panel (`panel.agregar_item()`), y si el ítem
  tenía Pisador asignado lo agrega también (`panel.agregar_pisador()`,
  mismo mecanismo intro/outro de siempre). Si la lista estaba vacía y
  no había nada armado, deja el primer ítem nuevo en rojo/el segundo
  en verde (arranca sola, igual que la restauración de sesión).
- **Recarga continua (puntos 7-8)**: en `_avanzar()`, cada vez que la
  candidata "siguiente" (verde) resulta ser el ÚLTIMO ítem del panel
  Y hay un formato musicalizador activo, se dispara
  `_generar_lote_musicalizador()` de inmediato — la lista nunca llega
  a vaciarse del todo, siempre hay más generado antes de necesitarlo.
- `detener_musicalizador()`: apaga el modo (no borra lo ya generado).

**Interfaz** (`gui/ventana_musicalizador.py`, abierta con
Ctrl+M o el botón "🎵 Musicalizador" del toolbar/menú Programación —
mismo patrón de ventana que el Programador, geometría persistida en
`ui_state.ini`): columna izquierda con los FORMATOS (Nuevo/Renombrar/
Eliminar); columna derecha con los ÍTEMS del formato seleccionado
(Añadir/Editar/Quitar/Subir/Bajar — puntos 2 y 3 del pedido) y el
botón "💾 Guardar formato" que corre `validar_formato()` antes de
persistir. `gui/dialogo_item_musicalizador.py` arma/edita UN ítem:
combo de tipo + `QStackedWidget` con la página correspondiente
(Específico usa el buscador de biblioteca ya existente; Aleatorio y el
Pisador usan el selector de categoría nuevo,
`gui/dialogo_seleccionar_categoria.py` — mismo patrón de copiar la
estructura del árbol vivo del Explorador que ya usaba el buscador de
biblioteca, pero sin elegir archivo, solo categoría; Subformato es un
combo de los demás formatos, excluyendo el actual, + duración en
minutos). El grupo Pisador (checkbox + categoría + radio Intro/Outro)
se oculta para Subformato (no aplica a un contenedor).
`VentanaExplorador` ganó dos helpers chicos para esto:
`ruta_de_categoria(item)` (camino de nombres desde la raíz) y
`buscar_categoria_por_ruta(ruta)` (el inverso — resuelve un `list[str]`
guardado en disco contra el árbol vivo actual, `None` si algún tramo
ya no existe).

Probado con 14 tests del motor puro (`test_musicalizador_motor.py`,
sin Qt: CRUD de formatos, tipo específico sin aleatoriedad, tipo
aleatorio recursivo, no-repetir vía historial incluyendo un título con
" - " en el medio, Pisador en el aleatorio, expansión de subformato
por duración, ítems rotos no frenan la generación de los demás, un
formato totalmente roto no cuelga, ciclo de subformatos no cuelga en
runtime con guard de `signal.alarm`, y los 3 casos de
`validar_formato`) + 18 checks de integración con la `MainWindow` real
(`test_musicalizador_gui.py`: crear un formato, insertar un Comando
FMT real en un bloque de Ventana 1, disparar el comando y verificar
que Ventana 2 se llena con `TAMAÑO_LOTE_MUSICALIZADOR` ítems, que el
wiring `al_comando_fmt` → `iniciar_musicalizador` está conectado, que
`_item_valido` acepta el comando, persistencia ida y vuelta del
comando en `playlist_publicidad.json`, y el mismo roundtrip completo
en el Programador incluyendo que "Reemplazar" no corrompe un comando
seleccionado por error) + suite de regresión completa sin fallos
nuevos (mismos 4 fallos preexistentes de siempre: `test_confirmaciones.py`,
`test_log_git.py`, `test_ventana3.py`, y a veces los 2 dependientes de
la hora real del sistema). **Nunca probado con audio real** (como todo
lo que toca el motor de reproducción — el sandbox no tiene VLC): falta
que Santiago arme un formato real, lo encadene con un Comando FMT en
un bloque de Ventana 1, y confirme en su notebook que (a) Ventana 2 se
llena sola y nunca se queda en silencio, (b) el no-repetir se siente
bien con su biblioteca real, y (c) el Pisador de los ítems aleatorios
suena — mismo motor ya validado con audio real en rondas anteriores,
pero nunca disparado desde este camino nuevo.

**Ronda de corrección tras la primera prueba real de Santiago (4 bugs
reales, todos en el motor, no en el diseño)**: Santiago probó el
Musicalizador/FMT apenas terminado y reportó 4 fallas concretas —
"me parece bien el diseño y la gráfica, pero falla el motor":

**a) "Quedó trabado en el FMT" — recursión infinita silenciosa (bug
real, causa raíz de (a) y (b))**: `GestorPublicidad._reproducir_item()`,
al detectar un Comando, ejecutaba `_ejecutar_comando()` y llamaba a
`self._avanzar()` de nuevo — pero SIN actualizar antes
`item_reproduciendo()`/`item_siguiente()`. La siguiente vuelta de
`_avanzar()` volvía a resolver el candidato como el MISMO comando
(`item_reproduciendo()` seguía apuntando al ítem ANTERIOR al comando,
e `item_siguiente()` todavía apuntaba al propio comando, marcado verde
antes de llegarle el turno) — recursión infinita en Python hasta el
límite de pila, silenciada por el `sys.excepthook` global (mismo
mecanismo ya documentado: una excepción dentro de un slot no avisa,
la app "sigue viva" con el estado congelado justo ahí). Visualmente
esto era EXACTAMENTE "queda en el FMT". Corregido: al ejecutar un
Comando, `_reproducir_item()` ahora marca el comando como reproduciendo
(para que `item_base` avance de verdad) y RECALCULA el próximo ítem
real ANTES de volver a llamar a `_avanzar()` — `item_siguiente()` ya
nunca vuelve a apuntar al comando que se acaba de ejecutar, así que no
hay forma de que la recursión se repita sobre el mismo ítem. De paso,
el código que marca automáticamente el "siguiente" (verde) al final de
`_avanzar()` ahora se saltea cuando el candidato recién reproducido
era un Comando (ese caso ya deja todo resuelto por dentro de
`_reproducir_item()` — dejarlo correr de nuevo ahí afuera pisaba el
ítem que acababa de quedar en rojo, marcándolo también en verde).

**b) "Cargó infinitas veces el mismo archivo" — consecuencia directa
de (a)**: cada vuelta de la recursión infinita volvía a llamar
`iniciar_musicalizador()` completo, que generaba OTRO lote de 8 ítems
y los apilaba arriba de los anteriores — con una sola vuelta ya eran
8 ítems duplicados, y con la recursión sin freno, docenas/cientos
antes de que Python cortara por límite de pila. Con (a) corregido, el
comando se ejecuta UNA sola vez por disparo — confirmado con un test
que cuenta las llamadas reales a `generar_items()` y falla si se
disparan más de 3 veces. Si a Santiago le sigue pareciendo "el mismo
archivo repetido" con una categoría real, es esperable si esa
categoría tiene MUY pocos archivos (un lote de 8 ítems repite el
esquema del formato tantas veces como haga falta para completarlo —
con 1 solo archivo en la categoría, los 8 van a ser el mismo; con más
archivos, el no-repetir por historial entra a jugar).

**c) "Antes de cargar la musicalización del FMT, debe limpiar la
ventana 2" — no implementado, corregido**: `GestorPlaylist.
iniciar_musicalizador()` ahora limpia TODO lo que hubiera en Emisión
(ítems sueltos del operador, o el lote de un formato anterior) ANTES
de generar el lote nuevo — un Comando FMT REEMPLAZA el contenido, no
lo acumula. Nuevo método `PanelReproductor.limpiar_items()` (detiene
el motor si algo estaba sonando, limpia las referencias
`_item_reproduciendo`/`_item_siguiente` ANTES de vaciar el árbol para
nunca tocar un `QTreeWidgetItem` ya eliminado, y recién ahí
`tree.clear()`). **Bug real de delegación atrapado por los tests antes
de llegar a Santiago** (mismo patrón ya documentado varias veces en
este archivo): `GestorPlaylist.panel` es el wrapper
(`VentanaEmision`/`VentanaAuxiliar`), no `PanelReproductor` directo —
`limpiar_items()` no estaba delegado en ninguno de los dos wrappers, así
que la primera versión de este fix tiraba `AttributeError` en
silencio (atrapado por el mismo `try/except` amplio de
`_ejecutar_comando`, que hacía que el Comando pareciera "no hacer
nada" sin ningún error visible). Corregido agregando la delegación en
ambos wrappers. **Regla reafirmada**: cuando un wrapper delega
métodos en `PanelReproductor`, hay que delegar TODOS los que el core
necesita — cada vez que se agrega un método nuevo al core que usa
`self.panel.algo()`, hay que sumarlo a los dos wrappers de una.
Importante: la recarga CONTINUA de este MISMO formato mientras ya está
sonando (`_generar_lote_musicalizador()`, disparada por `_avanzar()`
cuando el último ítem generado queda en cola) NUNCA limpia — eso
cortaría la música que está sonando; la limpieza es EXCLUSIVA del
momento en que un Comando FMT se dispara de nuevo.

**d) "Si es el último ítem de la ventana 1, debe ir en automático a la
ventana 2" — resuelto como consecuencia directa de (a)**: con la
recursión infinita corregida, el mecanismo de fin de bloque/fin de
reproducción YA EXISTENTE (Ciclo Automático, ver más arriba) vuelve a
dispararse con normalidad cuando un Comando FMT resulta ser el último
ítem reproducible: al recalcular correctamente `item_siguiente()`
DESPUÉS del comando, si no hay nada más, `_avanzar()` cae en el mismo
camino de siempre (`_finalizar_bloque_automatico()` con un bloque
disparado por horario, o `_notificar_fin_reproduccion()` en
reproducción continua normal) — no hizo falta ninguna lógica nueva,
solo que (a) dejara de "atascar" la máquina de estados antes de
llegar ahí.

Probado con 5 tests nuevos dedicados (`test_musicalizador_fixes.py`,
sobre el flujo REAL de avance natural — fin de ítem disparando
`_avanzar()`, no un llamado directo a `_ejecutar_comando()` como
hacían los tests de la ronda anterior, que por eso no habían atrapado
estos 4 bugs): el Comando dispara la generación exactamente una vez
(contador sobre `generar_items()` con freno a las 3 llamadas), la
reproducción de Ventana 1 sigue con el ítem DESPUÉS del comando (no
queda trabada), Emisión limpia su lote anterior al re-disparar un
Comando FMT, y un Comando FMT como último ítem de un bloque disparado
por el modo Automático finaliza el bloque (vuelta a Emisión) igual
que cualquier otro fin de bloque — más la suite de regresión completa
sin fallos nuevos (mismos 3 fallos preexistentes de siempre:
`test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
**Sigue sin poder probarse con audio/VLC real** (limitación de
siempre del sandbox): falta que Santiago repita su prueba original
(bloque con un Comando FMT en Ventana 1, categoría con más de un
archivo esta vez) y confirme que ahora sí avanza solo, genera un lote
razonable, limpia lo anterior, y vuelve sola a Emisión al terminar.

**Ronda de refinamiento tras el uso real (Pisador específico, columnas
CLASE/TIPO/DETALLE, series de cantidad EXACTA, refill robusto incluso
con 1 solo ítem)**: Santiago probó el Musicalizador ya andando y pidió
4 cambios, dos de diseño y dos de motor — los de motor resultaron ser
un cambio de fondo en cómo se genera la música, no un ajuste chico:

**a) Pisador del ítem: Categoría O Archivo específico (pedido
explícito: "debo tener las dos opciones")**: antes el Pisador de un
ítem Específico/Aleatorio SOLO podía apuntar a una categoría (elegido
al azar en cada generación). Ahora `DialogoItemMusicalizador` tiene un
selector de tipo propio para el Pisador (radio "Categoría (aleatorio)"
/ "Archivo específico", con su propio `QStackedWidget`) — igual
concepto que el tipo del ítem principal, acotado a estas dos
variantes. El archivo específico se elige con
`gui/dialogo_elegir_pisador.py` (el MISMO diálogo que ya usa "Agregar
Pisador" en Ventana 2/Auxiliar, filtrado a género "Pisador" vía
`listar_registros_por_genero`) — su propio selector de posición
Intro/Outro se IGNORA a propósito (el formulario del Musicalizador ya
tiene el suyo, compartido entre ambos tipos, para no preguntar dos
veces). Datos: `pisador_tipo: "categoria"|"especifico"` (default
`"categoria"` — formatos guardados ANTES de este cambio siguen
funcionando sin migración) + `pisador_ruta` (nuevo) o
`pisador_categoria` (ya existía) según corresponda.
`core/musicalizador.py:_resolver_pisador()` bifurca por `pisador_tipo`
— un archivo específico SIEMPRE resuelve el mismo registro (nunca al
azar), consistente con el resto del motor. `validar_formato()` ganó el
aviso simétrico ("el archivo específico del Pisador ya no existe") sin
bloquear el guardado, mismo criterio que las demás referencias.

**b) Columnas CLASE / TIPO / DETALLE / PISADOR (pedido explícito: "que
yo sepa que voy musicalizando")**: `self.lista_items`
(`gui/ventana_musicalizador.py`) pasó de un `QListWidget` con un texto
resumen único a un `QTreeWidget` de 4 columnas. `_texto_tipo()`
(Específico/Aleatorio/"—" para Subformato), `_texto_detalle()` (ruta
del archivo / camino de categoría / "nombre — N min" del subformato),
y `_texto_pisador()` (posición + ruta o categoría del Pisador, vacío
si no tiene) son puramente derivados del `item_config`, sin Qt.
`_texto_clase()` sí necesita el `ventana_explorador` — decisión propia
(no preguntada, documentada acá por si Santiago la quiere ajustar):
para un ítem **Subformato** la CLASE es literal `"Subformato"` (es un
contenedor, no tiene género); para un ítem **Específico**, la CLASE es
el género REAL del archivo (`registro["genero"]`, ya cargado en la
biblioteca); para un ítem **Aleatorio**, como apunta a una CATEGORÍA
completa (no un archivo puntual), la CLASE se DERIVA mirando el género
de los archivos que hay ahí: si todos comparten género, se muestra ese
género; si están mezclados, `"(variado)"`; si la categoría está vacía
o rota, un texto que lo indica. Se recalcula en vivo cada vez que se
refresca la lista — nunca queda desactualizada si la biblioteca
cambia.

**c) y d) Series de cantidad EXACTA + refill que nunca corta la
música (pedido explícito, el cambio de fondo de esta ronda)**: Santiago
fue explícito en que el motor debía cargar "el número exacto de
musicalización... la cantidad que haya programado. Solo se extiende si
en la serie hay sub-formato" — esto contradecía el diseño anterior
(`generar_items(explorador, nombre, cantidad)`, que repetía el esquema
completo del formato las veces que hicieran falta para juntar un
**lote fijo de 8 ítems**, `TAMAÑO_LOTE_MUSICALIZADOR`). Reemplazado por
`generar_serie(explorador, nombre_formato)` (`core/musicalizador.py`,
sin parámetro `cantidad`): UNA sola pasada por los ítems programados
del formato, en orden — ni más ni menos. Un ítem Subformato SÍ sigue
expandiéndose según SU PROPIA duración configurada (`_generar_por_duracion`,
sin cambios ahí) — es la única forma en que una serie "se extiende",
tal cual pidió Santiago. Cada llamada nueva resuelve los ítems
Aleatorio de nuevo (nuevas elecciones al azar, con el mismo no-repetir
de siempre) y mantiene los Específicos siempre iguales — así "otra
serie diferente" (punto b de su pedido) usa "otros archivos de los
aleatorios, el mismo específico", tal cual lo describió.
`GestorPlaylist._generar_serie_musicalizador()` (renombrado desde
`_generar_lote_musicalizador`) llama a `generar_serie()` sin cantidad;
el disparo de refill sigue en el mismo lugar de siempre (`_avanzar()`,
al marcar en verde el ÚLTIMO ítem de la lista actual, se precarga otra
serie completa ANTES de que la reproducción llegue a quedarse sin
nada).

**Bug real encontrado y corregido de paso, mientras se revisaba este
mecanismo**: con el lote fijo de 8 de antes, una serie chica nunca se
notaba este problema, pero con series de cantidad EXACTA (que ahora
pueden ser de 1 solo ítem) apareció un caso real donde el refill NUNCA
se disparaba: el "marcar en verde el último y precargar" solo puede
pasar si hay un "ante-último" desde donde hacerlo — con una serie de
UN solo ítem no existe tal cosa (el ítem es a la vez el primero Y el
último), así que nunca llegaba a marcarse nada en verde, y al terminar
ese único ítem `_avanzar()` simplemente se rendía (`motor.detener()`)
en vez de seguir. Corregido en `core/gestor_emision.py:_avanzar()`:
cuando se detecta que YA NO HAY más ítems a continuación
(`fila_siguiente >= total`) y el Musicalizador está activo, se genera
una serie nueva AHÍ MISMO (como red de seguridad) antes de rendirse, y
recién si TODAVÍA no alcanza (formato roto que no genera nada) se
detiene — cubre tanto series de 1 solo ítem como cualquier otro caso
donde el refill preventivo no llegó a tiempo. Probado con un test
dedicado (`test_musicalizador_serie_refill.py`) que confirma el
comportamiento general (serie de 3 ítems, precarga al marcar verde el
último) Y el caso límite de 1 solo ítem (refill de emergencia al
terminar, sin cortar la música).

Probado con 2 tests nuevos del motor puro (Pisador específico siempre
resuelve el mismo archivo, aviso de validación si ese archivo se
borra) + reescritura de los tests existentes del motor para reflejar
la nueva semántica de "una serie = cantidad exacta, sin repetir el
esquema" (antes asumían el lote fijo de 8) + tests nuevos de
integración GUI (columnas CLASE/TIPO/DETALLE/PISADOR, cantidad exacta
contra el Explorador real, refill de una serie de 1 solo ítem sin
cortar la música) + `test_musicalizador_serie_refill.py` dedicado +
suite de regresión completa sin fallos nuevos (mismos 3 fallos
preexistentes de siempre). **Sigue sin poder probarse con audio/VLC
real**: falta que Santiago confirme que una serie real (por ejemplo
sus 7 ítems del ejemplo que mandó) carga la cantidad exacta, que el
Pisador específico se escucha, que las columnas nuevas se leen bien de
un vistazo, y que el refill nunca corta la música al llegar al final
de una serie — sea de 1 ítem o de 20.

**Ronda de afinado del refill + no-repeat entre series (pedido
explícito)**: dos ajustes más de fondo sobre el mismo mecanismo de
series/refill de la ronda anterior:

**c) El refill se dispara al "entrar en previo" (verde), nunca al
terminar de sonar (pedido explícito: "que la nueva serie se cargue no
cuando termina de reproducirse el último item, sino cuando entra en
previo (verde), directamente ahí que cargue la nueva serie")**: la
ronda anterior tenía DOS mecanismos de refill separados — uno
"preventivo" (al marcar en verde el último ítem, mientras sonaba el
ante-último) y uno de "emergencia" (recién al toparse con el final,
agregado específicamente para series de 1 solo ítem, que no tienen
ante-último). Unificados en UNO SOLO, más simple y consistente:
`GestorPlaylist._avanzar()` ahora chequea, ANTES de marcar/reproducir
el próximo ítem, si `fila_siguiente >= total - 1` (es decir, si el
ítem que está por arrancar ES el último disponible) — si el
Musicalizador está activo, genera la serie siguiente AHÍ MISMO,
extendiendo `total` ANTES de que el código de más abajo marque el
próximo "en cola" (verde). Resultado: el ítem recién generado por la
serie nueva queda marcado en verde en el MISMO instante en que el
último de la serie vieja arranca a sonar — nunca hay que esperar a
que termine nada, y series largas y cortas (incluida la de 1 solo
ítem) comparten exactamente la misma lógica sin casos especiales.

**d) El aleatorio ya no repite el mismo archivo entre series
consecutivas (pedido explícito: "cuando volvió a cargar la serie,
cargó el mismo archivo aleatorio que en la primera")**: causa real —
el no-repetir de `_resolver_aleatorio()` solo consultaba el historial
de reproducción PERSISTENTE (lo que YA sonó), pero con el refill
disparándose apenas algo "entra en previo" (punto c, arriba), la
serie nueva se genera ANTES de que la serie vieja termine de sonar —
el historial todavía no tiene registrado nada de esa serie vieja
(recién se escribe cuando un ítem arranca a sonar de verdad), así que
no había NINGUNA señal de "esto ya se acaba de elegir". Corregido con
un parámetro nuevo `rutas_a_evitar` que viaja por
`generar_serie()`/`_resolver_item()`/`_resolver_aleatorio()`/
`_generar_por_duracion()` (`core/musicalizador.py`) — además de la
exclusión por historial de siempre, se excluyen las rutas que el
LLAMADOR ya sabe que están en cola sin sonar todavía.
`GestorPlaylist._generar_serie_musicalizador()`
(`core/gestor_emision.py`) arma ese conjunto leyendo
`panel.ruta_en_fila(i)` de TODO lo que ya hay cargado en Emisión en
ese momento, y se lo pasa a `generar_serie()`. De paso, DENTRO de una
misma llamada a `generar_serie()`/`_generar_por_duracion()`, las
rutas ya elegidas por un ítem "aleatorio" anterior en la MISMA pasada
también se van acumulando y excluyendo — así dos ítems aleatorios del
mismo formato tampoco eligen el mismo archivo entre sí. Mismo
criterio de "nunca dejar hueco" de siempre: si excluir todo vacía la
lista de candidatos (categoría muy chica), la exclusión se ignora
antes que repetir un tema a dejar silencio.

Probado con `test_ronda_afinado_musicalizador.py` (nuevo, cubre los 5
pedidos de esta ronda de una — ver también más abajo, colores y
fundido): refill exactamente al llegar al último ítem disponible (no
antes, no después) tanto en series largas como en la de 1 solo ítem,
y una serie regenerada con varios candidatos disponibles elige un
archivo DISTINTO al de la serie anterior — + suite de regresión
completa sin fallos nuevos (mismos 3 fallos preexistentes de
siempre). **Sigue sin poder probarse con audio/VLC real**: falta que
Santiago confirme que el encadenado se siente sin baches al recargar,
y que con su biblioteca real (categorías bastante más grandes que las
de los tests) el aleatorio varía notoriamente entre una serie y la
siguiente.

**Ronda "siempre rojo+verde" + Play manual de Ventana 1 corta Emisión
(pedido explícito, 3 puntos)**: Santiago probó la app y pidió tres
ajustes más de robustez, encontrados mientras usaba el ciclo real de
la estación:

**a) "El previo en color verde aparece siempre en el ítem... si hay 1
solo ítem, entonces será ese en rojo. Sino no [verde]"**: auditado
todo punto de entrada de Ventana 1 y Ventana 2 que arma/carga una
lista y encontrados varios huecos reales donde quedaba un ítem en
rojo sin un segundo ítem marcado en verde, a pesar de haber uno
disponible — el patrón correcto ("marcar el primero en rojo y el
segundo en verde si existe") ya vivía en UN solo lugar
(`_generar_lote_musicalizador`, ronda del Musicalizador) pero no se
aplicaba en el resto de la app. Corregido con un helper nuevo,
`_asegurar_rojo_y_verde()`, en cada gestor:
- `GestorPublicidad._asegurar_rojo_y_verde()` (`core/playlist_manager.py`):
  si no hay nada armado, arma el primer ítem reproducible; si el
  verde no apunta a un ítem distinto y válido, lo recalcula con
  `tree.itemBelow()` (mismo criterio que ya usa `_avanzar()` al
  avanzar naturalmente — puede cruzar a otro bloque, igual que
  `_marcar_proximo_bloque_en_espera` ya hacía). Llamado desde
  `_reproducir_seleccion_o_actual()`/`_reproducir_primero_del_bloque()`
  (Play manual — antes NO dejaba nada en verde), `disparar_bloque()`
  (bloque automático — antes el verde recién aparecía al FINALIZAR el
  bloque, nunca al empezarlo), `_restaurar_desde_disco()` (como
  respaldo si no había un `indice_siguiente` guardado o quedó
  inválido) y `SchedulerAutomatico._cargar_programacion_del_dia()`
  (carga de medianoche/inicio, antes no marcaba nada en absoluto).
- `GestorPlaylist._asegurar_rojo_y_verde()` (`core/gestor_emision.py`):
  mismo criterio por índice de fila. Llamado desde `reproducir_actual()`
  (Play manual en silencio — antes solo armaba el rojo) y como
  respaldo en `_restaurar_desde_disco()` (el rojo YA tenía un
  fallback documentado de una ronda anterior — "si no había nada
  armado, el primer ítem queda en rojo por defecto" — pero el verde
  no tenía ninguno, asimetría real). `_generar_lote_musicalizador()`
  ahora también llama a este helper compartido en vez de tener su
  propia lógica duplicada.
- `MainWindow._aplicar_programacion_ahora()` y
  `_cargar_programacion_de_hoy_manual()` (las otras dos rutas que
  cargan bloques nuevos en Ventana 1) también llaman al helper
  después de `cargar_bloques()`.
El helper nunca pisa un rojo o un verde ya puesto por el operador —
solo completa lo que falte.

**b) "Cuando en la ventana 2 se cargue el último ítem como previo,
cargará otro ciclo de FMT que se esté reproduciendo"**: esto ya
estaba implementado en la ronda anterior (el refill se dispara
exactamente al entrar en verde el último ítem disponible) — se
reconfirmó con un test dedicado que sigue funcionando igual después
del refactor del punto (a) (`_generar_lote_musicalizador()` ahora
delega en `_asegurar_rojo_y_verde()` para el caso de arranque inicial,
sin afectar el mecanismo de refill de `_avanzar()`, que es aparte).

**c) "Cuando pase de la ventana 2 a la 1, haciendo play, cortará en
fade la reproducción de la ventana 2, incluso si está en automático"**:
bug real de diseño — `GestorPublicidad` no tenía NINGUNA referencia a
Emisión ni forma de tocarla; solo `SchedulerAutomatico` (el disparo
POR HORARIO de un bloque) pausaba Emisión con fundido. Si el operador
apretaba Play a mano en Ventana 1 mientras Emisión sonaba, las dos
sonaban superpuestas sin que nada las coordinara. Corregido:
`SchedulerAutomatico._disparar_bloque()` se dividió en dos — la
lógica de "bajar Emisión en fundido superpuesto y pausarla al
terminar el fade" se extrajo a `_fade_pausar_emision()` (mismo
mecanismo de siempre, con su generación anti-carrera si Emisión
vuelve antes de que el fade termine), y se agregó un método público
nuevo, `cortar_emision_por_play_manual()`, que llama a lo mismo.
`GestorPublicidad` ganó un callback `self.al_arrancar_manual`
(`core/playlist_manager.py`), llamado al INICIO de
`_reproducir_seleccion_o_actual()` — el único punto de entrada real
de "Ventana 1 arranca a sonar por una acción manual del operador"
(doble click en silencio solo ARMA, nunca suena solo; ver máquina de
estados ya documentada). `MainWindow._inicializar_motores_audio()`
conecta `gestor_publicidad.al_arrancar_manual = scheduler_automatico.
cortar_emision_por_play_manual`. A propósito, esto es una asimetría
deliberada con el botón STOP (que SÍ queda bloqueado con el Automático
activo): arrancar Ventana 1 a mano SIEMPRE tiene prioridad y corta
Emisión, silenciar la estación a mano NO la tiene.

Probado con `test_ronda_rojo_verde_y_corte_v1.py` (nuevo, 15
verificaciones: Play sobre un bloque de 2+ tandas deja rojo+verde,
un bloque de 1 sola tanda deja solo rojo, `disparar_bloque` automático
también arma el verde de una, `_asegurar_rojo_y_verde` completa un
verde faltante sin pisar el rojo, mismo comportamiento en V2 vía
`reproducir_actual()`, el refill del FMT sigue funcionando tras el
refactor, y Play manual en V1 dispara el fundido de Emisión con el
Automático activo) + suite de regresión completa sin fallos nuevos
(mismos 3 fallos preexistentes de siempre — confirmado con `git
stash` que `test_play_bloque_y_hora.py` fallaba igual ANTES de esta
ronda, por la hora real del sistema cerca de medianoche al correr los
tests, no por este cambio). **Sigue sin poder probarse con audio/VLC
real**: falta que Santiago confirme en su notebook que el verde
siempre aparece cuando corresponde, y que el corte de Emisión al
pasar a Ventana 1 con Play se escucha como un fundido, no como un
corte seco ni como una superposición de las dos.

**Bug real corregido — el refill del FMT seguía cargando recién al
terminar el último ítem, pese al pedido explícito de la ronda
anterior**: Santiago reportó que "el nuevo ciclo lo carga cuando
termina de reproducirse el ultimo item cargado" — a pesar de que la
ronda anterior había agregado el chequeo de refill "al entrar en
previo" a `GestorPlaylist._avanzar()`. Causa real: ese chequeo se
agregó SOLO a `_avanzar()`, pero `_avanzar()` únicamente se dispara
por el fin NATURAL de un ítem sin crossfade (`motor.finalizo_item` →
`_avanzar_al_siguiente`). Con `crossfade_activado=True` — que es
cómo Santiago usa la radio en producción — la transición NATURAL
entre temas pasa por un camino de código COMPLETAMENTE DISTINTO:
`_chequear_crossfade()` → `_iniciar_crossfade()`, que tiene su PROPIA
copia de la lógica "calcular fila_siguiente, marcar rojo/verde" y
nunca tuvo el chequeo de refill. En la práctica, el refill solo
terminaba disparando en el caso residual de que el crossfade no
llegara a iniciarse (ej. sin ítem siguiente todavía) y el tema
llegara a su fin real — exactamente "cuando termina de reproducirse
el último ítem", tal como describió Santiago. Corregido agregando el
MISMO chequeo (`if self._formato_musicalizador_activo is not None
and fila_siguiente >= total - 1: self._generar_serie_musicalizador()`)
también en `_iniciar_crossfade()`, en el mismo punto donde ya
calculaba `fila_siguiente` — así el refill se dispara ahí apenas se
resuelve que el próximo ítem a cruzar (por crossfade) es el último
disponible, sin esperar a que nada termine de sonar. Probado con
`test_musicalizador_refill_crossfade.py` (nuevo, simula el motor
"entrante" que arma `crossfade_a()` con una instancia real de
`MotorAudio` sin VLC — mismo patrón que el resto de los tests de
crossfade — y confirma que el refill se dispara EXACTAMENTE al cruzar
al último ítem vía crossfade, no antes ni al terminar) + suite de
regresión completa sin fallos nuevos. **Regla para el futuro**:
`_avanzar()` y `_iniciar_crossfade()` mantienen lógicas de avance
PARALELAS y NO comparten código — cualquier chequeo nuevo que dependa
de "qué ítem viene después" (como este refill, o el freno por hora de
bloque) tiene que agregarse a AMBOS lugares, nunca solo a uno.

### Configuración (`gui/ventana_configuracion.py`)
QTabWidget con: Audio (dispositivo master/preescucha, volúmenes),
Fade/Transiciones (crossfade on/off + duración), Rutas (bibliotecas +
logs), Reproducción y Automatización (avanzar en error, reintentos,
repetir lista, tolerancia de silencio — el checkbox "modo automático
al iniciar" se retiró: el Automático arranca siempre ON, ver Ventana 1),
General (nombre de emisora, confirmaciones, reloj, tema), **Apariencia** (colores por
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

Procesamiento de audio de la FM (Compresor/Limitador/Estéreo): fuera
del alcance de esta app, a pedido explícito de Santiago (ver roadmap
ronda 55 — "para mayor compatibilidad... lo manejaré por fuera").
Historial completo de los dos intentos previos (EasyEffects
controlado desde acá, rondas 37-51; luego el módulo nativo
`filter-chain` de PipeWire con plugins Calf, ronda 52) queda
documentado más abajo por si en algún momento se retoma, pero AMBOS
se descartaron — Santiago instala y configura EasyEffects a mano,
totalmente independiente de esta app, sin ningún control ni
integración desde el programa. Lo único de nivelado de volumen que SÍ
sigue viviendo en esta app es el nivelado POR TEMA de
`core/analizador_audio.py` (nunca dependió de EasyEffects ni de
PipeWire — ver esa sección más abajo).

`requirements.txt` (Python): PySide6, python-vlc, mutagen, pydub,
yt-dlp (descargador de YouTube de Ventana 3, ver roadmap ronda 53 —
conviene actualizarlo de vez en cuando con `pip install --upgrade
yt-dlp` dentro del venv, ya que YouTube cambia su formato de página
seguido y yt-dlp saca versiones nuevas para seguirle el paso).

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
6. ~~Integrar crossfade + Pisador para cuando el tema ENTRANTE de un
   crossfade tiene su propio Pisador~~ — era la causa real de "el
   Pisador funciona si aprieto Siguiente, pero no cuando la lista
   avanza sola": con crossfade activado, la transición natural nunca
   pasaba por la única función que disparaba el Pisador. Corregido
   disparándolo en `_liberar_crossfade()` una vez que la rampa del
   crossfade ya terminó (ver Ventana 2 más abajo).
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
19. ~~Pisador+crossfade, log del Pisador, aviso de STOP con Automático,
    Programador compacto/maximizable, plantilla en "Nueva"~~ — (a)
    bug real corregido, prioridad alta: con crossfade activado (cómo
    usa la radio Santiago en producción), la transición NATURAL entre
    temas nunca disparaba el Pisador del tema entrante — solo pasaba
    si el operador apretaba Siguiente a mano; corregido disparándolo
    en `_liberar_crossfade()` una vez que la propia rampa del
    crossfade ya terminó, sin competir por el mismo motor; (b) el log
    ahora registra todo el ciclo de vida del Pisador (disparo con fila/
    ruta/volumen, cancelación, fin natural) y el inicio de cada
    crossfade, antes invisible; (c) el STOP de Ventana 1/2 ya NO se
    deshabilita con el Automático activo (un botón deshabilitado no
    avisaba nada) — queda siempre clickeable y muestra un mensaje
    explícito ("primero desactivá el Automático") en vez de quedar
    mudo; (d+e) el Programador bajó su alto mínimo de 780 a 560px
    (las 6 acciones de "Programación guardada" pasaron de 3 filas a
    1, nombre+Guardar se unificaron en una fila) y ahora pide los
    botones minimizar/maximizar de la barra de título (un `QDialog`
    no los pide por defecto, por eso no aparecían); (f) "Nueva" arma
    solo una plantilla de 24 bloques vacíos (00 a 23hs) para completar,
    en vez de tener que crear cada uno a mano — implementado y probado
    (13 tests nuevos + suite de regresión completa, incluida la
    actualización de los tests de la ronda anterior que asumían el
    STOP deshabilitado).
20. ~~Corrección definitiva del Pisador+crossfade (la de la ronda 19 no
    alcanzaba)~~ — Santiago probó la ronda 19 con audio real y reportó
    que el Pisador SEGUÍA sin sonar en una transición con crossfade
    (adelantó la barra cerca del final, encoló otro ítem con el mismo
    Pisador en verde, terminó el rojo y "no se escuchó el pisador").
    Causa: la corrección anterior disparaba el Pisador recién en
    `_liberar_crossfade()`, ~`duracion_fade_segundos` (3s por defecto)
    DESPUÉS de arrancar el tema entrante — un silencio de varios
    segundos indistinguible de "no sonó". Corregido separando el AUDIO
    del Pisador (arranca YA, siempre, apenas empieza el crossfade —
    `motor_pisador.reproducir()` es un motor aparte, nunca compite con
    nada) del DUCKING (bajar el volumen del tema principal, que sí
    puede pelear con la rampa del crossfade — ese sí se sigue
    difiriendo a `_liberar_crossfade()`, con guards para no aplicarlo
    tarde si el Pisador ya terminó solo o si el operador tomó control
    manual mientras tanto). Regla de diseño para el futuro: ante la
    duda, que el Pisador SIEMPRE se escuche gana por sobre que el
    ducking quede perfectamente sincronizado — probado con 4 tests
    nuevos (audio inmediato al iniciar el crossfade, ducking diferido
    al liberarlo, sin ducking tardío si el Pisador ya terminó solo, sin
    ducking sobre una fila vieja si el operador intervino) + suite de
    regresión completa sin fallos nuevos. Falta que Santiago repita la
    prueba exacta que hizo (adelantar la barra, encolar en verde un
    ítem con Pisador, dejar que termine solo) y confirme que ahora sí
    se escucha siempre.
21. ~~Bug real de libVLC: el Pisador reutilizado dejaba de sonar a
    partir de la segunda vez~~ — Santiago mandó el log real de una
    prueba (24hs de programación real, Pisador "PISADOR RADIO HITS
    91" reutilizado en 3 temas distintos): sonó la primera vez, las
    otras dos NO — a pesar del fix de la ronda 20. El log reveló que
    en realidad estaba corriendo la versión INTERMEDIA (la de la
    ronda 19, sin el sufijo de log "ducking inmediato/diferido" de la
    ronda 20) — pero investigando igual apareció un bug real
    independiente y más profundo: cuando libVLC llega al fin NATURAL
    de un archivo (`MediaPlayerEndReached`, que es exactamente cómo
    termina un Pisador corto todas las veces), el reproductor queda
    en estado "Ended" — un simple `play()` sobre ese estado no
    reinicia la reproducción de forma confiable en varias versiones
    de libVLC, sin importar el seek a `punto_inicio_ms` que ya se
    hacía (ronda de "reuso de Pisador" anterior). Corregido con un
    `self._player.stop()` explícito ANTES de cada `play()` en
    `MotorAudio.reproducir()`, siempre, para forzar el reset de
    estado. De paso, un segundo bug relacionado encontrado en el
    mismo log: al cancelar un Pisador en curso queda un fundido a
    volumen 0 corriendo 0.8s en `motor_pisador` — si un Pisador nuevo
    se dispara en ese mismo motor antes de que termine ese fundido
    (pasar de tema rápido, cada uno con Pisador), el fundido viejo le
    seguía pisando el volumen al nuevo, sonando pero en silencio;
    corregido cancelando cualquier fade en curso al inicio de
    `reproducir()`. **Este bug es imposible de reproducir en el
    sandbox** (no hay libVLC instalado acá) — el fix se basa en el
    log real de Santiago y en un comportamiento documentado de
    libVLC, probado acá solo estructuralmente (orden de llamadas
    `stop()`→`play()`, cancelación del fade viejo, mockeando el
    reproductor). Falta que Santiago lo confirme con audio real —
    repetir la prueba de reutilizar el mismo Pisador en varios temas
    seguidos de una lista real.
22. ~~LA CAUSA DE FONDO del audio mudo: libVLC descarta el volumen si
    la salida de audio no existe todavía~~ — la ronda 21 fue PEOR en
    la prueba real de Santiago: el Pisador solo sonó la primera vez Y
    un tema musical entero quedó MUDO (reloj avanzando, cero sonido;
    Stop+Play manual lo "arregló" — inaceptable para una radio). El
    log demostró que el Pisador "mudo" se reprodujo completo (7s,
    "terminó solo"): el problema no era la reproducción sino el
    VOLUMEN. Causa de fondo: libVLC descarta en silencio
    `audio_set_volume()` llamado antes de que la salida de audio del
    reproductor exista (se crea asíncrona tras `play()`, y cada
    `stop()` la desarma — el stop()-antes-de-play() de la ronda 21
    agrandó la ventana del bug, por eso empeoró). El tema mudo del
    crossfade era lo mismo del otro lado: el techo del fade-in se
    leía del reproductor recién arrancado (0/-1) y la rampa subía
    "hacia 0". Corrección de fondo en `MotorAudio` (ver nota completa
    en Ventana 2): `_volumen_deseado` como fuente de verdad propia,
    re-aplicación en el diferido de 150ms del arranque, red de
    seguridad en `_emitir_posicion()` (re-aplica el deseado en cada
    tick de 500ms si el real no coincide — un ítem mudo se
    autocorrige solo), techo del fade-in del crossfade CALCULADO
    (`volumen_deseado()`) en vez de leído, y rampas que parten del
    deseado. Probado con 5 tests nuevos usando un player falso que
    replica el comportamiento real de libVLC (descarta sets hasta que
    la salida "existe") + suite completa sin fallos nuevos. Como
    siempre con libVLC: el sandbox no tiene VLC, falta la
    confirmación de Santiago con audio real — misma prueba (un solo
    Pisador reutilizado en varios ítems, lista con crossfade).
23. ~~Paridad de diseño con Hardata Dinesat 9~~ — pedido explícito con
    4 fotos de referencia: cartel de nombre de emisora + medidor de
    nivel decorativo arriba de los contadores (Ventana 1 y 2); color
    celeste exclusivo de selección, ya no pisa el rojo/verde de
    estado; botón verde grande que fusiona Play y "Siguiente con
    fundido" (crossfade solapado real en Ventana 2, fundido
    secuencial en Ventana 1 por no tener motor dual — diferencia
    documentada y deliberada); botón nuevo Fade-Stop (fundido hasta
    apagar); botón nuevo Stop diferido (toggle: deja terminar el
    ítem actual y recién ahí frena todo, sin avanzar — guard único en
    el tope de `_avanzar()` de cada gestor, cubre fin natural/Cut/
    cascada de error por igual); "Siguiente" renombrado a "Cut" sin
    tocar su lógica; Automático reubicado como 4to botón de la grilla
    de transporte de Ventana 1; bloqueo por Automático extendido a
    Fade-Stop y Stop diferido (mismo aviso que ya tenía Stop) —
    implementado y probado (15 tests nuevos dedicados + suite de
    regresión completa de 26 scripts sin fallos nuevos; confirmado
    con `git stash` que los 2 fallos de horario preexistentes ya
    fallaban igual antes de esta ronda). Falta que Santiago compare
    el resultado con las fotos reales de Dinesat en su pantalla y
    confirme si el layout se parece lo suficiente, si el medidor
    decorativo cumple su función aunque no mida audio real, y si el
    fundido secuencial de Ventana 1 le alcanza o prefiere pedir el
    crossfade solapado real ahí también más adelante.
24. ~~Ronda de ajustes post-Dinesat~~ — 5 pedidos puntuales tras la
    primera comparación con las fotos: (a) "Ahora"/"Luego" mucho más
    angostos (`EtiquetaMarquesina` de 220 a 130px + `AlignLeft` al
    agregar el frame, antes `QVBoxLayout` lo estiraba a todo el ancho
    del panel sin importar el tamaño del contenido); (b) bug real
    corregido — el rojo/verde SEGUÍA perdiéndose al seleccionar pese
    al cambio de la ronda anterior: la técnica QSS
    (`background-color: transparent` en `:selected`) no puede
    "preguntar" si el ítem tiene color propio, así que lo perdía
    igual; corregido con `DelegadoConservaColorEstado`
    (`gui/common_widgets.py`), que pinta sin el flag de selección
    cuando el ítem está en rojo/verde (conserva su color) y agrega el
    borde celeste a mano; (c) preload (cursor de espera + mensaje) al
    iniciar (`QSplashScreen` en `main.py` + `MainWindow.
    _mostrar_preload()`), al cargar música (`archivo_agregado`) y al
    cargar una programación (nueva señal `programacion_cargada` en
    `VentanaPublicidad.cargar_bloques()`, cubre sus 4 puntos de
    llamada de una sola vez); (d) AUTOMÁTICO y Fade-Stop
    intercambiados de fila en Ventana 1 (Automático ahora arriba,
    junto a Stop); (e) ícono "ya reproducido" (tilde verde armada con
    QPainter, `gui/styles.py:icono_reproducido()`) a la izquierda del
    título, puesto al arrancar a sonar y que YA NUNCA se saca —
    implementado y probado (10 tests nuevos + suite de regresión
    completa sin fallos nuevos, mismos 4 preexistentes de siempre).
    Falta que Santiago confirme en su notebook real el ancho de los
    carteles, que el rojo/verde ya no se pierda con un click real, y
    si el preload se nota lo justo sin molestar en el uso diario.
25. ~~Aprovechamiento de espacio (relojes apilados, renombre de
    ventanas, nombre de emisora configurable)~~ — (a) relojes
    transcurrido/restante apilados a la izquierda (angostos, 11pt,
    max-width 90px) con "Ahora"/"Luego" a la derecha en la MISMA fila
    combinada, en vez de 3 filas separadas — ahorra otra fila de alto
    de panel en Ventana 1 y 2; (b) título de Ventana 1 "PUBLICIDAD" →
    "PROGRAMACIÓN / ROTATIVA", título de Ventana 2 "EMISIÓN MUSICAL
    ACTUAL" → "EMISIÓN" (solo el texto visible, sin tocar nombres de
    clase/archivo); (c) nombre de emisora ahora es un campo editable
    en Configuración → General (`nombre_emisora`, default "RADIO TUYÚ
    FM 92.5") que se muestra UNA sola vez, a la izquierda del reloj de
    día/hora del toolbar — se sacó el cartel fijo que antes vivía
    duplicado en cada panel, liberando otra fila más y permitiendo ver
    más ítems de la lista; se actualiza en vivo al guardar
    Configuración, sin reiniciar — implementado y probado (7 tests
    nuevos + suite de regresión completa sin fallos nuevos, mismos 4
    preexistentes de siempre). Falta que Santiago confirme cuánto
    espacio ganó de verdad en su pantalla y que el nombre de emisora
    se vea bien ubicado junto al reloj del toolbar.
26. ~~Estudio del manual de Dinesat + mejoras "bajo a medio"~~ —
    Santiago pasó el manual completo de Dinesat Visual; se comparó
    función por función contra lo ya implementado y se propuso (vía
    `AskUserQuestion`) una lista de candidatos, descartando a propósito
    todo lo de cadena de emisoras (Satélite/Remoto — "no me gusta"),
    video/NDI, RDS (ya declinado antes), acceso web multiusuario,
    SIP/telefonía y extractor de CD. De lo elegido: Asistente en vivo
    (soundboard) y Grabador Continuo quedaron explícitamente pausados
    (el segundo porque "los micrófonos no están enchufados a la PC,
    la grabación del master sería siempre de la música... no tiene
    sentido" hasta que Santiago conecte la consola por USB — cambio
    físico pendiente de su lado). Implementado en esta ronda: (a)
    vigencia de fecha por material (Ventana 1/Publicidad, un ítem
    fuera de rango se saltea sin cortar el aire); (b) historial de
    reproducción PERSISTENTE (además del ícono de sesión ya existente,
    consultable en Configuración → Diagnóstico); (c) Pisador también
    en el Outro (extiende el motor de Pisador ya maduro con una
    posición inicio/final, elegible desde el diálogo — bug real de
    delegación faltante en `VentanaEmision`/`VentanaAuxiliar` atrapado
    por los tests antes de llegar a Santiago); (d) función de
    selección aleatoria reutilizable sobre categoría/subcategoría —
    preparación explícita para el Musicalizador Avanzado, sin ningún
    botón que la use todavía. Implementado y probado (22 tests nuevos
    + suite de regresión completa sin fallos nuevos, mismos 4
    preexistentes de siempre). **Próximo paso acordado con Santiago**:
    Musicalizador Avanzado encadenado con Comandos FMT — los dos temas
    que más usa, quedan para una ronda dedicada. Clima también
    pendiente: Santiago va a pasar la fuente de datos meteorológicos
    (página web) antes de encararlo; mientras tanto, pensar dónde
    encaja en la UI (candidato natural: una ventana nueva tipo
    "Ventana Clima" en el menú Emisión, más una categoría de tipo HTH
    en el Explorador y un tab en Configuración para ciudad/unidades —
    mismo espíritu que Dinesat, sin comprometerse a nada hasta tener
    la fuente de datos real).
27. ~~Ajuste estético: título de ventana (QGroupBox) a 14pt~~ — pedido
    explícito, cambio chico: `QGroupBox::title` (gui/styles.py) pasó a
    `font-size: 14pt` (antes heredaba el 10pt general); `margin-top`
    del propio `QGroupBox` subió de 18px a 24px de paso, para que el
    título más grande no quede recortado contra el borde superior del
    panel. Aplica a los 3 títulos principales (PROGRAMACIÓN/ROTATIVA,
    EMISIÓN, EXPLORADOR) y a cualquier otro `QGroupBox` de la app
    (es una regla QSS global, no por ventana puntual).
28. ~~Musicalizador Avanzado + Comandos FMT~~ — el tema pendiente más
    grande del roadmap, con 11 puntos de pedido y 4 decisiones de
    arquitectura confirmadas por `AskUserQuestion` (ver sección
    dedicada más arriba, entre Ventana Programador y Configuración):
    la música generada carga en Ventana 2 (no en Ventana 1, pese a la
    redacción original del pedido — confirmado explícitamente con
    Santiago), el comando FMT se crea eligiendo de una lista (no texto
    libre), el no-repetir usa el historial persistente, y la
    validación bloquea solo en ciclos de subformatos. Tres tipos de
    ítem (Específico/Aleatorio/Subformato), Pisador Intro/Outro en los
    ítems Específico/Aleatorio, motor puro sin Qt
    (`core/musicalizador.py`) con degradación total ante ítems rotos
    (nunca frena la generación de los demás — pedido explícito de
    Santiago), ventana dedicada (Ctrl+M), y recarga continua en
    Ventana 2 cuando el último ítem generado queda marcado en cola —
    implementado y probado (14 tests del motor puro + 18 checks de
    integración con la app real + suite de regresión completa sin
    fallos nuevos). Falta que Santiago lo pruebe con audio real y su
    biblioteca real: armar un formato, encadenarlo con un Comando FMT,
    y confirmar que Emisión se llena sola de forma continua.
29. ~~Corrección del motor del Musicalizador/FMT tras la primera
    prueba real de Santiago~~ — 4 bugs reales reportados de una
    ("me parece bien el diseño y la gráfica, pero falla el motor"),
    los 4 con la MISMA causa raíz: `GestorPublicidad._reproducir_item()`
    ejecutaba un Comando FMT y recursaba sobre `_avanzar()` sin
    actualizar antes `item_reproduciendo()`/`item_siguiente()` — la
    vuelta siguiente volvía a resolver el MISMO comando como
    candidato, disparando una recursión infinita silenciada por el
    `sys.excepthook` global (por eso "quedaba trabado en el FMT" sin
    ningún error visible, y cada vuelta de la recursión volvía a
    generar y apilar otro lote de 8 ítems — "cargó infinitas veces el
    mismo archivo"). Corregido marcando el comando como reproduciendo
    y recalculando el próximo ítem ANTES de recursar. De paso: un
    Comando FMT ahora LIMPIA Emisión antes de cargar el lote nuevo
    (`PanelReproductor.limpiar_items()`, nuevo — atrapado en el camino
    un bug real de delegación faltante en `VentanaEmision`/
    `VentanaAuxiliar`, mismo patrón ya documentado varias veces en
    este archivo), y la vuelta automática a Ventana 2 cuando el
    Comando FMT es el último ítem de un bloque quedó resuelta sola, sin
    tocar nada más, en cuanto la recursión infinita dejó de "atascar"
    la máquina de estados antes de llegar ahí. Probado con 5 tests
    nuevos sobre el flujo REAL de avance natural (fin de ítem, no un
    llamado directo a la ejecución del comando como hacían los tests
    de la ronda anterior — por eso no habían atrapado esto) + suite de
    regresión completa sin fallos nuevos. Falta que Santiago repita su
    prueba original con una categoría con más de un archivo y confirme
    los 4 puntos.
30. ~~Copiar/Pegar en el Programador + refinamiento del Musicalizador
    (Pisador específico, columnas CLASE/TIPO/DETALLE, series de
    cantidad exacta, refill robusto)~~ — dos pedidos en paralelo: (1)
    menú contextual NUEVO en el árbol del Programador (antes todo era
    por botones) con Copiar/Pegar sobre la selección múltiple ya
    existente, para reprogramar el mismo ítem en otro bloque horario
    sin rearmarlo a mano — reusa el mismo formato de serialización que
    ya usa el guardado a JSON, portapapeles solo en memoria; (2) en el
    Musicalizador: Pisador con selector propio Categoría/Archivo
    específico (antes solo categoría), columnas CLASE/TIPO/DETALLE/
    PISADOR en la lista de ítems (antes un texto resumen único) para
    "saber qué se está musicalizando" de un vistazo, y el cambio de
    fondo — el motor ahora genera series de cantidad EXACTA (los
    ítems que el operador programó, ni más ni menos; un Subformato
    sigue expandiéndose por su propia duración) en vez de un lote fijo
    de 8 ítems repitiendo el esquema. Bug real encontrado y corregido
    en el camino: con series muy cortas (el caso límite de 1 solo
    ítem) el refill continuo NUNCA se disparaba — el mecanismo
    dependía de poder marcar en verde un "ante-último" que, con 1 solo
    ítem, no existe; corregido con un refill de emergencia en
    `_avanzar()` cuando se detecta que no queda nada más y el
    Musicalizador sigue activo. Implementado y probado (motor puro +
    integración GUI + test dedicado de series/refill + suite de
    regresión completa sin fallos nuevos). Falta que Santiago pruebe
    con su biblioteca real: el Copiar/Pegar del Programador en su flujo
    de armar bloques, el Pisador específico con audio real, que las
    columnas nuevas se lean claro, y que una serie real (sus 7 ítems
    del ejemplo, o los que programe) cargue la cantidad exacta y
    nunca corte la música al recargar.
31. ~~Ronda de afinado: colores solo rojo/verde en Ventana 2, Pisador
    hereda color del padre, refill al entrar en verde (no al
    terminar), no-repetir entre series, sin fade-in (solo fade-out)~~
    — 5 pedidos puntuales tras seguir probando el Musicalizador: (a+b)
    el Pisador anidado de Ventana 2 tenía un color violeta FIJO de
    género (pensado para identificar categorías en el Explorador, sin
    sentido acá) — ahora nace y se mantiene sincronizado con el color
    rojo/verde/normal de su tema principal (`PanelReproductor.
    _pintar_item()` ahora cascada el color a los hijos); (c) el
    refill de una serie del Musicalizador se unificó en un solo
    mecanismo que dispara apenas el próximo ítem a reproducir ES el
    último disponible — ya no dos mecanismos separados (uno
    "preventivo" al marcar verde, uno de "emergencia" al terminar),
    que en la práctica para series cortas solo disparaba el de
    emergencia (justo lo que Santiago no quería: esperar al final);
    (d) bug real corregido — el no-repetir del aleatorio solo miraba
    el historial de lo YA reproducido, pero con el refill disparando
    antes de que la serie vieja termine de sonar, el historial todavía
    no reflejaba nada de ella — agregado `rutas_a_evitar` (lo que ya
    está en cola en Emisión) como exclusión extra en
    `core/musicalizador.py`; (e) sin fade-in al arrancar un tema en
    Ventana 1 y 2 — solo el fade-out se mantiene (crossfade de Ventana
    2 y el fundido secuencial de Ventana 1), "para que los temas
    suenen más enganchados". Implementado y probado (test dedicado +
    actualización de 2 tests preexistentes que asumían el fade-in
    viejo + suite de regresión completa sin fallos nuevos). Falta que
    Santiago confirme con audio real que el encadenado se siente sin
    baches, que el aleatorio varía notoriamente entre series con su
    biblioteca real, y que los temas "pegan" mejor a la entrada sin el
    fade-in.
32. ~~Ronda "siempre rojo+verde" + Play manual de Ventana 1 corta
    Emisión~~ — (a) auditados todos los puntos de entrada de Ventana 1
    y 2 que arman/cargan una lista; corregidos varios huecos reales
    donde quedaba un ítem en rojo sin un segundo marcado en verde
    aunque hubiera uno disponible (Play manual, bloque disparado por
    horario, restaurar desde disco sin `indice_siguiente` guardado,
    cargar programación por medianoche/"Aplicar ahora"/"Cargar
    Programación") — unificado en un helper `_asegurar_rojo_y_verde()`
    por gestor, que nunca pisa una marca ya puesta por el operador;
    (b) reconfirmado que el refill del FMT al entrar en verde el
    último ítem sigue funcionando tras ese refactor; (c) bug real de
    diseño corregido — `GestorPublicidad` no tenía forma de tocar
    Emisión, así que un Play manual en Ventana 1 dejaba sonar las dos
    ventanas superpuestas; ahora un Play manual SIEMPRE corta Emisión
    con el mismo fundido superpuesto que ya usaba el disparo
    automático por horario, incluso con el Automático activo (a
    propósito, asimetría deliberada con el botón STOP, que sí sigue
    bloqueado). Implementado y probado (15 verificaciones nuevas +
    suite de regresión completa sin fallos nuevos — confirmado con
    `git stash` que el único fallo adicional visto durante esta ronda,
    `test_play_bloque_y_hora.py`, ya fallaba igual ANTES del cambio
    por la hora real del sistema cerca de medianoche, no por esto).
    Falta que Santiago confirme en su notebook que el verde siempre
    aparece cuando corresponde y que el corte de Emisión al pasar a
    Ventana 1 con Play se escucha como un fundido, nunca como una
    superposición.
33. ~~Bug real: el refill del FMT no disparaba con crossfade
    activado~~ — Santiago reportó que, pese al pedido explícito de la
    ronda anterior, el nuevo ciclo del Musicalizador seguía cargando
    recién cuando el último ítem terminaba de sonar, no al entrar en
    verde. Causa real: el chequeo de refill se había agregado SOLO a
    `GestorPlaylist._avanzar()`, pero con `crossfade_activado=True`
    (cómo Santiago usa la radio en producción) la transición NATURAL
    entre temas pasa por `_iniciar_crossfade()` — un camino de código
    totalmente separado, con su propia copia de la lógica de avance,
    que nunca tuvo el chequeo. Corregido agregando el mismo chequeo
    también ahí. **Regla para el futuro**: `_avanzar()` e
    `_iniciar_crossfade()` no comparten código — cualquier lógica
    nueva sobre "qué ítem viene después" tiene que agregarse a AMBOS
    lugares. Probado con un test dedicado que simula el crossfade real
    (motor entrante real sin VLC) + suite de regresión completa sin
    fallos nuevos.
34. ~~Memoria de "último FMT" (sobrevive al día) + Ventana 2 siempre
    activa el FMT recordado + refill centralizado, disparado
    ESTRICTAMENTE por el verde~~ — pedido explícito, 3 partes en un
    solo mensaje: "El último FMT cargado lo guardarás en memoria
    temporal (sobrevive al día no a la sesión). Cuando actives la
    ventana 2, siempre y siempre (solo admitiendo la excepción de que
    yo agregue manualmente item arrastrando o agregando) vas a
    reproducir la serie del FMT en memoria. Cuando el último item
    cargado en la ventana se pinte de verde (sin tomar en cuenta el
    rojo) vas a cargar un nuevo ciclo."
    - **(a) Memoria del último FMT, con vencimiento diario**:
      `config/settings.py` — `guardar_ultimo_fmt(nombre)` /
      `obtener_ultimo_fmt()`, nuevo archivo
      `config/data/ultimo_fmt.json` (`{"nombre": ..., "fecha":
      "YYYY-MM-DD"}`, escritura atómica de siempre). `obtener_ultimo_fmt()`
      compara la fecha guardada contra `date.today()`: si no coincide,
      devuelve `None` como si no hubiera nada — el archivo NO se
      borra, simplemente deja de aplicar solo en cuanto cambia el día
      (fail-open también ante JSON corrupto o archivo ausente). Se
      graba cada vez que se activa un formato,
      `GestorPlaylist.iniciar_musicalizador()`, sin importar si el
      disparo fue un Comando FMT real de Ventana 1 o el auto-arranque
      nuevo del punto (b) — así la memoria siempre refleja el ÚLTIMO
      FMT usado en el día, venga de donde venga.
    - **(b) Ventana 2 arranca sola el FMT recordado al "activarse"**:
      nuevo método `GestorPlaylist._activar_fmt_recordado_si_corresponde()`,
      llamado como primera línea de `reproducir_actual()` (el Play
      manual desde silencio, y también el punto de entrada común que
      ya usan tanto el arranque de la app como la vuelta automática de
      `SchedulerAutomatico` tras un bloque — cubre los tres casos con
      un solo gancho). Si Emisión está VACÍA y no hay ya un
      Musicalizador activo, busca el FMT recordado de HOY y lo carga
      con `iniciar_musicalizador()`; si ya hay contenido (restaurado
      de sesión anterior, o agregado a mano) NO lo pisa. La ÚNICA
      excepción real al "siempre" es agregar un ítem a mano
      arrastrando desde el Explorador — `MainWindow.
      _on_archivo_soltado_emision()` ahora llama a
      `gestor_emision.detener_musicalizador()` apenas el operador
      suelta un archivo (antes de agregarlo), así el auto-arranque no
      compite con lo que el operador acaba de elegir; si más tarde
      vacía la lista de nuevo, el SIGUIENTE Play retoma el FMT
      recordado con normalidad (no hace falta un flag de "suprimido
      permanentemente" — la propia condición de "lista vacía" alcanza).
      **Dos decisiones de diseño tomadas sin poder consultarlas con
      Santiago** (una falla de herramienta impidió preguntarle antes
      de programar, documentado para que las corrija si no es lo que
      tenía en mente): qué cuenta como "activar la ventana 2" (acá:
      cualquier Play que encuentra la lista vacía — cubre manual,
      automático y arranque) y cuánto dura la excepción del agregado
      manual (acá: hasta que la lista vuelva a quedar vacía, no una
      sesión entera ni un flag separado).
    - **(c) Refill centralizado, disparado por el VERDE, no por el
      rojo**: cambio de fondo pedido explícitamente ("no toma en
      cuenta el color rojo, sino el verde") — antes (ronda 33) el
      refill se chequeaba en `_avanzar()` e `_iniciar_crossfade()` por
      separado, mirando si el PRÓXIMO ROJO iba a ser el último. Ahora
      un solo método nuevo, `GestorPlaylist._marcar_siguiente_con_refill()`,
      envuelve TODA marca de verde de Emisión — `panel.marcar_siguiente()`
      ya no se llama nunca directo, siempre a través de este
      envoltorio, desde `_avanzar()`, `_iniciar_crossfade()` Y
      `_asegurar_rojo_y_verde()` (los tres lugares del archivo que
      pueden pintar algo de verde). El refill se dispara ADENTRO de
      este método, en el mismo instante en que la fila que se acaba
      de marcar verde resulta ser la última disponible —
      completamente desacoplado de qué esté en rojo en ese momento.
      Consecuencia real y esperada (no un bug): con series MUY cortas
      (2 ítems), el segundo y último ítem queda en verde ya en la
      CARGA INICIAL (es el único candidato posible), así que la
      cascada a una 2da serie arranca de inmediato, antes de que
      suene una sola nota — coherente con la letra del pedido de
      Santiago, que no distingue "carga inicial" de "avance normal".
      Centralizar en un único método, en vez de agregar el chequeo
      suelto en cada lugar (como se hizo, y se rompió, en la ronda
      33), cierra la clase entera de bug de "caminos paralelos que se
      olvidan de compartir una regla" para cualquier código futuro que
      marque verde en Emisión.
      El caso límite de una serie de 1 solo ítem (nunca hay
      "ante-último" desde donde marcar un verde distinto) sigue
      cubierto por la red de emergencia ya existente dentro de
      `_avanzar()`, en la rama `fila_siguiente >= total` — restaurada
      en esta ronda tras haber sido reemplazada por el chequeo suelto
      de la ronda 33.
    Probado con un test nuevo dedicado
    (`test_fmt_memoria_y_refill_verde.py`: round-trip y vencimiento
    diario de la memoria del FMT, Play con Emisión vacía auto-carga el
    FMT recordado sin pisar contenido existente, sin `ventana_explorador`
    no hace nada, agregar a mano corta el Musicalizador y vaciar la
    lista lo retoma, refill exacto al marcar verde el último ítem vía
    `_avanzar()` Y vía `_iniciar_crossfade()`, caso límite de 1 solo
    ítem) + actualización de 3 tests preexistentes que asumían el
    punto de disparo VIEJO del refill (`test_musicalizador_refill_crossfade.py`,
    `test_ronda_afinado_musicalizador.py`,
    `test_ronda_rojo_verde_y_corte_v1.py` — sus fallos NO eran
    regresiones, sino aserciones que codificaban el timing anterior)
    + suite de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder probarse
    con audio/VLC real**: falta que Santiago confirme (1) si "activar
    la ventana 2" y la duración de la excepción manual son lo que
    tenía en mente (ver los dos judgment calls documentados arriba en
    (b) — puede pedir que se ajusten), (2) que el FMT recordado
    efectivamente arranque solo al otro día si vuelve a abrir la app
    sin haber cargado nada nuevo (y que YA NO arranque si pasó a otro
    día), y (3) que el refill se sienta "más adelantado" (antes,
    incluso, de que termine de sonar nada) tal como pidió.
35. ~~Ronda de 7 pedidos: barra de progreso, rojo/verde tras doble
    click, silencio estricto + fade-out en V1, auditoría de fade-OUT,
    reordenar en el Programador, Agregar/Reemplazar en V1, leyenda de
    Automático abajo~~ — siete pedidos independientes en un solo
    mensaje:
    - **(1) La barra de progreso quedaba "pegada" en Stop/Fade/cambio
      de ventana**: nuevo `resetear_reproduccion()` en
      `PanelReproductor`/`VentanaPublicidad` (reinicia el slider Y los
      contadores a 00:00:00) — llamado desde `detener()` (V1 y V2),
      los finales de `_avanzar()` sin más ítems, `_finalizar_bloque_automatico()`,
      y `SchedulerAutomatico._pausar_emision_tras_fade()` (el caso
      "cambio de ventana": Emisión pausada porque un bloque de
      Publicidad tomó el aire). La Pausa NORMAL nunca lo toca — sigue
      conservando la posición para reanudar, a propósito. **Bug real
      de delegación atrapado por el test antes de llegar a Santiago**
      (mismo patrón ya documentado varias veces): `GestorPlaylist.panel`
      es el wrapper (`VentanaEmision`/`VentanaAuxiliar`), no
      `PanelReproductor` directo — hubo que agregar la delegación de
      `resetear_reproduccion()` en los dos wrappers.
    - **(2) Rojo/verde: doble click en silencio no recalculaba el
      verde**: "por debajo del ítem que entra en rojo, el de abajo
      pasa a verde... si está en stop, elijo uno con doble clic para
      ponerse en rojo, pero el verde quedó en otro ítem diferente".
      `_asegurar_rojo_y_verde()` no alcanzaba porque respeta un verde
      YA VÁLIDO sin importar dónde apunte — nuevo
      `_recalcular_verde_tras_nuevo_rojo()` (en los dos gestores) que
      SIEMPRE sobrescribe el verde al de abajo del rojo recién armado
      a mano, llamado desde la rama "en silencio" de `_on_doble_click`
      en Ventana 1 y 2 (la rama "encolar mientras suena" no se tocó —
      esa sigue permitiendo elegir un verde arbitrario a propósito).
    - **(3) V1: corte de silencio estricto para Publicidad/Separadores
      + fade-out automático configurable en milisegundos**: nueva
      config `reproduccion.tolerancia_silencio_v1_segundos` (0.0 por
      defecto, sin margen — a diferencia de `tolerancia_silencio_segundos`
      general, que sigue dejando un colchón para Música) aplicada
      automáticamente por género al analizar un archivo
      (`config/settings.py:tolerancia_silencio_para_genero()`, gatea
      por `GENEROS_CORTE_ESTRICTO = ("Publicidad", "Separador")`) en
      los 3 puntos de `ventana_explorador.py` que llaman a
      `analizar_audio()`. Además, nueva config
      `reproduccion.duracion_fade_out_v1_ms` (500 por defecto, EN
      MILISEGUNDOS — a diferencia de `duracion_fade_segundos` de
      Fade/Transiciones, que es en segundos y es para Ventana 2) que
      dispara un fade-out corto y automático sobre CUALQUIER
      transición natural entre tandas de Publicidad
      (`GestorPublicidad._chequear_fade_out_automatico()`, colgado de
      `restante_ms_cambio` igual que el resto de los disparos "con
      anticipación" del proyecto) — antes el encadenado entre tandas
      de un mismo bloque era un corte directo (pendiente documentado
      desde el roadmap 16). Ambos campos nuevos, editables en
      Configuración → Reproducción y Automatización.
    - **(4) Auditoría "el fade es siempre OUT, nunca IN"**: revisados
      todos los `fade_volumen_a()` del proyecto — el fade-out nuevo
      del punto (3) solo baja el ítem SALIENTE a 0, el ENTRANTE arranca
      directo a su volumen final (sin rampa), igual que el resto del
      motor desde la ronda que sacó el fade-in de los temas. **Dos
      excepciones preexistentes, deliberadamente NO tocadas** porque
      pertenecen a un pedido explícito distinto de una ronda anterior:
      el fundido de ENTRADA de Emisión al volver de un bloque
      automático (`SchedulerAutomatico._reanudar_o_arrancar_emision`
      — "fundido de entrada y salida" en el handoff V1↔V2, pedido a
      propósito así) y la restauración de volumen del Pisador al
      terminar (`_on_pisador_finalizado`/`_cancelar_pisador_en_curso`
      — es un "des-ducking", no la entrada de un tema nuevo). Si
      Santiago quiere que estas dos también se acoten a config, avisar
      para una ronda dedicada.
    - **(5) Programador: reordenar por arrastre + Agregar Ítem/Pegar
      en la posición seleccionada**: nueva `ArbolProgramadorConDrop`
      (`gui/common_widgets.py`), subclase de `ArbolConDrop` con
      reordenado jerárquico (mismo patrón de `startDrag()` propio sin
      `super().startDrag()` que ya usa `ArbolReproductorConDrop`, para
      no pisar el bug real ya documentado de "los ítems desaparecen")
      — un ítem se puede mover DENTRO de su bloque o a OTRO bloque
      distinto, nunca los bloques en sí. `_agregar_registro_a_bloque`/
      `_agregar_comando_a_bloque` ganaron un parámetro `indice`
      opcional; nuevo `_indice_insercion_actual()` calcula "justo
      después del ítem seleccionado" (si hay uno dentro del bloque
      destino) en vez de siempre `None` (al final) — usado por "Añadir
      Ítem..." y "Pegar en este bloque" por igual.
    - **(6) V1: Agregar/Reemplazar Item habilitadas en el menú
      contextual**: las dos acciones que quedaban visibles pero
      deshabilitadas desde la ronda 13 ("andá agregando funciones ya
      creadas, las demás las vamos a ir creando") ahora usan el MISMO
      buscador de biblioteca del Programador
      (`gui/dialogo_seleccionar_biblioteca.py`) directo sobre Ventana
      1, sin abrir el Programador — `VentanaPublicidad` ganó
      `set_ventana_explorador()` (seteado por `MainWindow` justo
      después de construir el Explorador, que se crea DESPUÉS de
      Ventana 1) y los handlers `_agregar_item_v1()`/`_reemplazar_item_v1()`.
      Reemplazar respeta el mismo bloqueo de rojo/verde que ya tenía
      "Sacar Item" (`_bloqueado_por_reproduccion`) y rechaza tocar un
      Comando FMT (se saca y se agrega uno nuevo, igual que en el
      Programador).
    - **(7) Leyenda de Automático simplificada, movida abajo**: la
      barra de estado inferior de `MainWindow` mostraba una leyenda
      DUPLICADA y con otra redacción ("Modo: AUTOMÁTICO"/"Modo:
      MANUAL", `lbl_status_modo`) además de la que ya tenía Ventana 1
      arriba de sus contadores ("Modo Manual"/"Automático Activo" en
      rojo, `lbl_estado`). Unificado: `lbl_status_modo` ahora reusa el
      mismo objectName/QSS que `lbl_estado`
      (`lblEstadoAutomatico[activo="true"/"false"]`, rojo cuando está
      activo — gratis, sin QSS nuevo) y el texto simple "Automático
      Activo"/"Modo Manual"; la fila de arriba en Ventana 1
      (`barra_superior`) se sacó de la UI visible por completo —
      `lbl_estado` sigue existiendo como atributo interno (se sigue
      actualizando en `_toggle_automatico()`) para no romper código
      que lo consulte, pero ya no se agrega a ningún layout visible.
    Probado con un test nuevo dedicado (`test_ronda_7pedidos.py`, 39
    verificaciones cubriendo los 7 puntos) + actualización de un test
    preexistente que codificaba el estado VIEJO de Agregar/Reemplazar
    deshabilitadas (`test_silencio_v2_y_menu.py`) + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`). **Sigue sin poder probarse con audio/VLC
    real**: falta que Santiago confirme (1) que la barra de progreso
    ya no queda "pegada", (2) que el verde siempre se recalcula bien
    al elegir un rojo nuevo con doble click, (3) que el corte de
    silencio estricto + el fade-out de 500ms dejan las tandas de
    Publicidad "bien pegadas" como pidió — y si el valor por defecto
    le sirve o prefiere ajustarlo, (4) que el reordenar por arrastre
    en el Programador se sienta natural, y (5) que Agregar/Reemplazar
    Item en Ventana 1 cumple lo que esperaba sin tener que abrir el
    Programador.
36. ~~Bug real con audio real: el bloque automático cortaba el ítem de
    Emisión a mitad (pausa resumible) en vez de dejarlo terminar y
    liberar de verdad~~ — Santiago reportó, ya reproduciendo en
    producción con el Musicalizador/FMT: "está reproduciendo la
    ventana 2... llega la tanda y no deja terminar el tema en
    reproducción, lo deja en pausa, termina la publicidad y vuelve
    luego de la pausa... si en la ventana 1 hay otro FMT, reproduce
    desde la pausa el ítem que quedó cargado (no quiero eso). Y si hay
    otro FMT aunque sea el mismo, debe comenzar un ciclo nuevo desde
    0". Causa de fondo: el mecanismo viejo (`_fade_pausar_emision()`)
    cortaba Emisión con un fundido apenas llegaba la hora del bloque y
    la dejaba en PAUSA (resumible) mientras sonaba Publicidad — y
    `MotorAudio.esta_reproduciendo()` da `False` con el motor en
    pausa, así que si el bloque disparaba OTRO Comando FMT,
    `_limpiar_playlist_para_musicalizador()`'s guard
    (`if self.motor.esta_reproduciendo(): self.motor.detener()`) se
    saltaba el `detener()` — el motor viejo quedaba pausado en el
    tema de antes, sin que nadie lo tocara, y al volver de Publicidad
    el mecanismo de "reanudar" (`motor.pausar()`, que alterna) revivía
    ESE tema viejo en vez de la serie nueva recién generada en el
    panel.

    Rediseño de fondo (confirmado con Santiago vía `AskUserQuestion`
    que el Play MANUAL en Ventana 1 sigue cortando Emisión de
    inmediato, sin esperar — solo el disparo AUTOMÁTICO por horario
    cambia):
    - **`GestorPlaylist.ceder_control_al_terminar_item(callback)`**
      (`core/gestor_emision.py`), nuevo: si Emisión está sonando, NO
      corta nada — arma un flag de una sola vez
      (`_ceder_control_armado`, mismo patrón que "Stop diferido" pero
      invisible al operador, lo arma el Scheduler) que bloquea
      `_chequear_crossfade()` (no arranca una transición nueva) y se
      resuelve en el próximo fin NATURAL del ítem, dentro de
      `_avanzar()`: recién ahí hace un `detener()` DE VERDAD (nunca
      pausa) y llama a `callback()`. Si no hay nada sonando, cede el
      control ya mismo (nada que esperar).
    - **`SchedulerAutomatico._disparar_bloque()`** ya no llama a
      `_fade_pausar_emision()` — arma `ceder_control_al_terminar_item()`
      con un callback que recién ahí dispara
      `GestorPublicidad.disparar_bloque()`. Nueva bandera
      `_esperando_liberar_emision` evita que `_tick()` intente
      disparar un SEGUNDO bloque mientras el primero sigue esperando
      que Emisión libere el control (puede tardar varios minutos si el
      tema en curso recién empezó — a propósito, prioriza nunca cortar
      sobre ser puntual al segundo).
    - **`cortar_emision_por_play_manual()`** (Play manual en Ventana
      1, pedido de una ronda anterior, sin cambios en el TIMING —
      sigue cortando YA, con el mismo fundido corto de siempre) se
      simplificó para usar `motor.fade_volumen_a(0, duracion)` +
      `QTimer.singleShot(..., self.gestor_emision.detener)` — MISMO
      arreglo de fondo que el automático: detiene de verdad, nunca
      pausa, para no dejar la misma clase de bug latente en este
      camino manual.
    - **`_reanudar_o_arrancar_emision()`** se simplificó radicalmente:
      al no existir más una "pausa" que resumir, perdió el parámetro
      `estaba_sonando` y las dos ramas de resume — ahora SIEMPRE es un
      arranque de cero: si Emisión no está sonando por su cuenta y hay
      ítems en el panel, llama a `reproducir_actual()` (Play normal:
      el ítem en punta, o una serie NUEVA del Musicalizador si un
      Comando FMT disparó una durante el bloque) con el mismo fundido
      de entrada de siempre.
    - Eliminados por completo: `_fade_pausar_emision()`,
      `_pausar_emision_tras_fade()`, `_volumen_objetivo_emision()`, y
      los atributos `_emision_estaba_sonando`/`_volumen_emision_previo`/
      `_generacion_pausa_emision` — toda la infraestructura de
      pausa/resume/generación quedó obsoleta de raíz, no solo
      parcheada.

    Con esto, el escenario reportado por Santiago queda resuelto en la
    raíz: como Emisión nunca vuelve a quedar "pausada" en un tema
    viejo, un Comando FMT (mismo formato o distinto) que dispare
    durante el bloque SIEMPRE genera su serie sobre un panel/motor ya
    liberado — no hay nada que revivir por accidente, nunca.

    Probado con `test_ciclo_deja_terminar_item.py` (nuevo, 31
    verificaciones: `ceder_control_al_terminar_item` no corta un ítem
    sonando y lo deja terminar solo antes de detener de verdad;
    control cedido de inmediato si no hay nada sonando; bloquea el
    crossfade mientras espera; `_disparar_bloque` espera si Emisión
    suena y dispara ya si no; `_tick()` no dispara un segundo bloque
    mientras el primero espera; un Comando FMT "aunque sea el mismo"
    genera una serie nueva de punta a punta tras el ciclo completo;
    `_al_terminar_publicidad` siempre hace un Play normal, nunca un
    resume; Play manual sigue cortando de inmediato sin esperar, pero
    ahora libera en vez de pausar) + reescritura completa de la
    sección de disparo por horario de `test_ciclo_automatico.py` (el
    test viejo codificaba literalmente el mecanismo de pausa que se
    eliminó — sus fallos no eran una regresión, sino aserciones que
    verificaban el comportamiento que Santiago pidió cambiar) + suite
    de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder probarse
    con audio/VLC real** (como todo lo que toca este motor): falta que
    Santiago confirme con su radio real que ahora el tema de Emisión
    siempre termina entero antes de que entre el bloque, que Emisión
    arranca fresca al volver (nunca el tema viejo a mitad), y que un
    Comando FMT del mismo formato genera contenido realmente nuevo
    cada vez.
37. ~~Integración con EasyEffects (procesamiento de audio de la FM:
    compresor, ecualizador, limitador — Santiago ya lo usa a mano)~~ —
    pedido explícito, en dos partes: primero una consulta exploratoria
    ("¿hay manera de integrarlo al programa?"), después el pedido
    concreto ("dejar EasyEffects andando en ícono junto al reloj y no
    como pestaña abajo minimizado... que se ejecute oculto, y que
    solo lo controle cuando aprieto ese botón"). Decisión de diseño
    explicada y acordada con Santiago ANTES de programar: EasyEffects
    es un host de plugins LV2 sobre PipeWire que intercepta el audio
    de la app a nivel del SISTEMA (no es un plugin embebible) —
    reimplementar sus controles adentro de esta app significaría
    construir un host LV2 propio en Python, un proyecto en sí mismo.
    En cambio: Santiago arma y afina las cadenas de efectos con la
    propia interfaz de EasyEffects (agregando los plugins que quiera)
    y las guarda como PRESETS; esta app solo cambia de preset desde
    afuera, por línea de comandos, sobre una instancia de EasyEffects
    corriendo OCULTA en segundo plano.

    **Comandos confirmados por Santiago en su instalación real**
    (EasyEffects 7.2.3, vía `easyeffects --help`) — no existe
    `--gapplication-service` en esta versión, pero `-w/--hide-window`
    cumple la misma función (arranca/activa la instancia única sin
    mostrar su ventana): `-w/--hide-window`, `-l/--load-preset NAME`,
    `-p/--presets`, `-b/--bypass N` (1/2/3 = habilitar/deshabilitar/
    estado), `-s/--active-preset CAT` (el ejemplo de la ayuda usa el
    valor en inglés "input"/"output", aunque la descripción esté
    traducida — se usa "output" tal cual el ejemplo, sin traducir).

    **`core/easyeffects_control.py`** (nuevo, deliberadamente sin Qt
    salvo `QProcess.startDetached` — mismo patrón que
    `core/actualizador.py`: `subprocess.run` con timeout,
    try/except `(TimeoutExpired, OSError)`, devuelve `(éxito: bool,
    mensaje: str)`): los flags de la CLI viven como CONSTANTES al
    principio del archivo — pedido explícito de Santiago ("debe ser
    tolerante a actualizaciones, sino con la primera actualización
    perdería el acceso"): si una versión futura de EasyEffects
    renombra un flag, arreglarlo es un edit de una línea, y mientras
    tanto cualquier comando que falle degrada limpio (mensaje claro
    en la UI) en vez de romper la app — mismo espíritu que
    `MotorAudio`/`analizar_audio()` ante dependencias faltantes.
    - **Por qué el arranque tiene que ser DESACOPLADO y sondeado, no
      un `subprocess.run` directo**: EasyEffects es una GApplication
      de instancia única — si TODAVÍA no está corriendo, la primera
      invocación de `easyeffects` se convierte en la instancia
      "primaria" y se queda corriendo indefinidamente (nunca vuelve
      la terminal); un `subprocess.run()` directo ahí colgaría para
      siempre. `asegurar_en_ejecucion()` lanza el proceso con
      `QProcess.startDetached()` (no bloquea) y sondea con `pgrep`
      (no depende de ningún flag propio de EasyEffects — más
      tolerante a cambios de versión que parsear su salida) hasta
      confirmar que la instancia ya quedó arriba, recién ahí permite
      que otros comandos (que sí esperan una respuesta rápida de la
      instancia ya activa) se envíen con `subprocess.run` normal.
    - Funciones expuestas: `esta_instalado()`, `asegurar_en_ejecucion()`,
      `listar_presets()`, `cargar_preset(nombre)`, `preset_activo()`,
      `set_bypass(activar)`, `esta_en_bypass()`, `abrir_ventana()`
      (para la afinación fina de los plugins — sin un flag "mostrar
      ventana" documentado en esta versión, invocar el binario SIN
      `--hide-window` activa la instancia existente y GApplication
      presenta su ventana por defecto al recibir esa activación; a
      confirmar con Santiago si de verdad la destapa).

    **GUI (`gui/main_window.py`)**: botón "🎚 FM" (`QToolButton`,
    `ToolButtonPopupMode.InstantPopup` — un solo click despliega el
    menú, sin flecha aparte) junto al reloj del toolbar. El menú se
    puebla de nuevo cada vez que se abre (`aboutToShow`), mostrando
    cursor de espera (`_mostrar_preload`, mismo patrón que el resto de
    la app) mientras confirma que la instancia está arriba — así el
    primer uso de la sesión (o si el operador cerró EasyEffects a
    mano) puede tardar un instante, pero los usos siguientes son
    instantáneos. Contenido del menú: la lista de presets (marcado el
    activo, `QActionGroup` exclusivo), separador, "Bypass (sin
    efectos)" (checkeable), separador, "Abrir EasyEffects (edición
    avanzada)...". Si EasyEffects no está instalado, un único ítem
    deshabilitado avisa con claridad en vez de un menú vacío o roto.
    `MainWindow.__init__` llama a `_iniciar_easyeffects_en_segundo_plano()`
    apenas arranca — pedido explícito ("que se ejecute oculto") — pero
    a propósito es puro *fire-and-forget* (`QProcess.startDetached`
    directo, SIN el sondeo de `asegurar_en_ejecucion()`) para no
    demorar el arranque de la radio ni un segundo; para cuando el
    operador realmente abre el menú, ya tuvo tiempo de terminar de
    levantar solo.

    Probado con `test_easyeffects_control.py` (nuevo, 27
    verificaciones): sin EasyEffects instalado (el caso real del
    sandbox) TODAS las funciones degradan limpio sin excepción; con un
    binario FALSO que simula EasyEffects instalado y corriendo (un
    script Python ejecutable en el PATH, más un `pgrep` falso que
    "ve" el proceso recién después de recibir `--hide-window`) se
    prueban los flujos reales de arranque/sondeo, listar presets,
    cambiar de preset (éxito y error con un nombre inexistente),
    consultar/cambiar bypass y abrir ventana — confirmando que se usan
    EXACTAMENTE los flags que Santiago pegó de su `--help` real, no
    otros inventados; y la parte GUI confirma que el botón existe, que
    el menú se puebla con los 3 presets del binario falso (el activo
    marcado) más Bypass/Abrir, y que sin el binario en el PATH el menú
    cae al aviso de "no instalado" deshabilitado — + suite de
    regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Nunca se probó contra el
    EasyEffects REAL** (el sandbox no lo tiene instalado, todo lo de
    arriba se probó contra un binario falso que imita su CLI): falta
    que Santiago confirme en su notebook real (1) que el ícono "🎚 FM"
    aparece y el menú lista sus presets reales de verdad, (2) que
    cambiar de preset desde el menú se escucha en el aire, (3) que
    EasyEffects arranca oculto de verdad al abrir la radio (nunca ve
    su ventana ni la ve minimizada en la barra de tareas), y (4) que
    "Abrir EasyEffects" efectivamente destapa la ventana para la
    afinación fina — es el punto más incierto de esta ronda, al no
    haber un flag "mostrar ventana" documentado explícitamente.
38. ~~Reproductor Auxiliar a la par de Ventana 2 + exclusión mutua
    entre TODAS las ventanas de reproducción~~ — pedido explícito, dos
    partes en el mismo mensaje: "la gráfica y funcionamiento debe ser
    igual a la ventana de Emisión (ventana 2), sin la lógica de FMT ni
    pase de Automático" y "no pueden funcionar a mismo tiempo, el
    Auxiliar y la ventana de Emisión... en rigor de verdad, ninguna
    ventana debe reproducirse al mismo tiempo junto con otra".
    - **(a) Paridad con Ventana 2**: a la Auxiliar le faltaba la barra
      de progreso/seek — `gui/ventana_auxiliar.py` ahora construye su
      `PanelReproductor` con `mostrar_barra_progreso=True` (antes
      `False` implícito), agrega la señal `solicitud_buscar_posicion`
      (antes inexistente ahí) conectada igual que en `VentanaEmision`,
      y delega `actualizar_progreso()` al panel — mismo patrón de
      delegación completa ya documentado varias veces en este archivo.
      El resto de la paridad (contadores, Play/Pausa/Cut/Fade-Stop/
      Stop diferido, rojo/verde, Pisador Intro/Outro, ícono "ya
      reproducido") YA era compartido de fábrica por reutilizar
      `PanelReproductor` — no hacía falta tocar nada ahí. **FMT/
      Musicalizador y el pase de Automático ya estaban naturalmente
      excluidos de la Auxiliar sin necesitar ningún código nuevo**:
      `MainWindow.abrir_ventana_auxiliar()` construye su
      `GestorPlaylist` sin pasarle `ventana_explorador=` ni
      `persistir=True` — sin `ventana_explorador`, un Comando FMT no
      tiene de dónde resolver categorías/archivos (ver roadmap 28), y
      el ciclo Automático (`SchedulerAutomatico`) nunca tuvo ninguna
      referencia a la Auxiliar. Confirmado con un test que audita
      ambos atributos directamente en vez de asumirlo.
    - **(b) Exclusión mutua, diseño genérico**: nuevo campo
      `GestorPlaylist.al_arrancar_reproduccion` (`core/gestor_emision.py`,
      `None` por defecto), invocado como la PRIMERA línea de
      `reproducir_actual()` — el único punto de entrada real de
      "arrancar a sonar desde silencio" (cubre tanto el Play manual
      del operador como la reanudación automática de
      `SchedulerAutomatico._reanudar_o_arrancar_emision()`, que
      también pasa por acá). A propósito, `GestorPlaylist` NO SABE
      quién es su par — el campo es un callback genérico que
      `MainWindow` conecta desde afuera, así el mismo mecanismo sirve
      para cualquier otro par de ventanas de reproducción que se
      decida coordinar en el futuro, no solo Auxiliar↔Emisión.
      `MainWindow` (`gui/main_window.py`) agrega el helper genérico
      `_cortar_reproduccion_de(gestor)` — mismo patrón EXACTO que
      `SchedulerAutomatico.cortar_emision_por_play_manual()` (fundido
      corto con piso de 0.8s + `QTimer.singleShot` que llama a
      `gestor.detener()`, NUNCA `pausar()` — ver la regla de fondo ya
      documentada en "Cosas ya resueltas" sobre pausa vs. stop para
      handoffs) — y dos wrappers finitos,
      `_cortar_auxiliar_por_emision()`/`_cortar_emision_por_auxiliar()`,
      conectados en `_inicializar_motores_audio()` (Emisión existe
      desde el arranque) y en `abrir_ventana_auxiliar()` (la Auxiliar
      se crea recién la primera vez que el operador la abre — por eso
      la wiring de ESE lado se conecta ahí, no antes). El lado
      cortado queda en silencio de verdad, sin ningún auto-resume — el
      operador tiene que volver a apretar Play a mano en esa ventana
      cuando quiera retomarla.
    Probado con `test_auxiliar_paridad_y_exclusion.py` (nuevo, 15
    verificaciones: paridad estructural de la Auxiliar —
    `solicitud_buscar_posicion`, `slider_progreso` real,
    `actualizar_progreso()` delegado —, FMT/persistencia inertes por
    construcción, arrancar el Auxiliar dispara YA un fundido a 0 sobre
    Emisión y termina cortándola de verdad, arrancar Emisión hace lo
    mismo sobre el Auxiliar, el lado cortado no vuelve a sonar solo, y
    `_cortar_reproduccion_de()` tolera `None` y un gestor sin nada
    sonando sin romperse) + suite de regresión completa sin fallos
    nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
    **Sigue sin poder probarse con audio/VLC real**: falta que
    Santiago confirme en su notebook que la Auxiliar se ve/comporta
    igual que Ventana 2 (barra de progreso incluida), y que abrir
    cualquiera de las dos ventanas mientras la otra está sonando corta
    con un fundido corto en vez de superponerse o quedar en pausa.
39. ~~Comando HTH (Hora-Temperatura-Humedad) — el segundo tema grande
    pendiente, junto con FMT/Musicalizador~~ — Santiago pasó el manual
    completo de Dinesat Visual (guardado en
    [`docs/manual_dinesat_visual.md`](docs/manual_dinesat_visual.md),
    ver también la sección "Manual de Dinesat Visual" al principio de
    este archivo) y pidió los comandos que él llamaba informalmente
    "FMT HORA"/"FMT CLIMA" — el manual reveló que en Dinesat real son
    los comandos **HTH** (sección 5.2.7.3/5.3.5/5.3.5.1/5.3.5.2), un
    tipo separado del FMT del Musicalizador. Se confirmaron 8
    decisiones de arquitectura por `AskUserQuestion` antes de programar
    (pedido explícito de Santiago, "Preguntame todo"):
    1. Terminología: **"Comando HTH"** (nombre real de Dinesat), no
       "FMT HORA/CLIMA".
    2. **3 comandos independientes** — HORA, TEMPERATURA, HUMEDAD —
       cada uno se inserta por separado en un bloque, igual que
       Dinesat real (no un comando "CLIMA" combinado).
    3. Los clips de voz viven en una **categoría dedicada del
       Explorador** — resuelto como un género MÁS (`"HTH"`), no un
       tipo de categoría nuevo (ver abajo).
    4. Si falta un clip o falla la consulta de clima: **saltea TODO el
       comando, sin sonar nada** (nunca un anuncio a medias).
    5. Clip de intro de la hora (el manual no lo documenta): un clip
       fijo nuevo, **"INTRO HORA"**.
    6. Temperatura: **redondeada a grados enteros**, sin décimas (no
       hace falta grabar `TEMPERATURA DECIMA XX`).
    7. Bajo cero: **prefijo fijo "TEMPERATURA BAJO CERO" + reutiliza**
       el clip de `TEMPERATURA GRADOS XX` del valor absoluto (no hay
       que grabar un clip por cada valor negativo).
    8. Clima: **caché de ~20 minutos** contra Open-Meteo (confirmado en
       una ronda anterior como fuente, ver roadmap de esa ronda) —
       no golpea la API en cada disparo del comando.

    **Género "HTH", no una categoría de tipo especial (decisión de
    diseño, máxima reutilización de lo que ya existe)**: en vez de
    inventar un concepto nuevo de "tipo de categoría" (que esta app
    nunca tuvo — las categorías del Explorador son contenedores
    género-agnósticos), los clips de voz se agregan como un género MÁS
    (`gui/styles.py`: `LISTA_GENEROS`/`GENERO_COLORES`/
    `GENERO_PREFIJOS_CODIGO` ganaron `"HTH"`, color cian oscuro
    `#00838f`) — Santiago los importa con el flujo de siempre ("＋
    Agregar" del Explorador, género "HTH", el "nombre editorial" es la
    nomenclatura exacta como título: `HORA 14`, `MINUTOS 30`,
    `TEMPERATURA GRADOS 20`, `TEMPERATURA BAJO CERO`, `HUMEDAD 045`,
    `INTRO HORA`) y quedan buscables GLOBALMENTE (sin importar en qué
    categoría/subcategoría estén archivados) con
    `VentanaExplorador.listar_registros_por_genero("HTH")` — el MISMO
    mecanismo que ya usa "Pisador". También se agregó `"HTH"` a
    `GENEROS_CORTE_ESTRICTO` (`config/settings.py`) — un corte de
    silencio flojo entre "HORA 14" y "MINUTOS 30" sonaría como un
    bache raro a mitad del anuncio, igual razón que ya aplicaba a
    Publicidad/Separador.

    **Motor puro (`core/hth.py`, sin Qt — mismo espíritu que
    `core/musicalizador.py`)**: `resolver_clips_hora/temperatura/
    humedad()` arman la lista ORDENADA de rutas a concatenar buscando
    por título EXACTO (normalizado a mayúsculas/espacios) entre TODOS
    los registros de género HTH; si falta cualquiera, devuelven `None`
    — todo o nada. `resolver_comando_hth(explorador, parametro, ahora=,
    clima=)` es el punto de entrada único que usa `GestorPublicidad` —
    `ahora`/`clima` son inyectables (para tests deterministas sin
    tocar la hora real ni la red), en producción se resuelven solos
    (`datetime.now()` / `core.clima_meteo.obtener_clima()` con las
    coordenadas de Configuración).

    **`core/clima_meteo.py` (primera y única llamada de red de toda la
    app)**: `obtener_clima(latitud, longitud)` consulta Open-Meteo
    (`api.open-meteo.com/v1/forecast`, `current=temperature_2m,
    relative_humidity_2m`) con `urllib` de la librería estándar (no
    hizo falta sumar la dependencia `requests` solo para esto) y
    cachea el resultado en memoria por `DURACION_CACHE_SEGUNDOS` (20
    min). Si la consulta falla y no hay caché vigente, devuelve `None`
    — `core/hth.py` lo trata exactamente igual que un clip de voz
    faltante (salteo silencioso del comando completo, decisión 4 de
    arriba). Coordenadas configurables en Configuración → General
    (`clima.latitud`/`clima.longitud`, default General Juan Madariaga,
    Buenos Aires).

    **Motor de reproducción en `GestorPublicidad`
    (`core/playlist_manager.py`)**: a diferencia del Comando FMT (no
    ocupa tiempo de aire — dispara un callback y sigue directo), un
    Comando HTH SÍ suena: concatena 2-3 clips cortos con el MISMO
    `MotorAudio`, uno atrás del otro, y recién cuando termina el
    último vuelve al flujo normal. Nueva cola interna
    (`self._reproduciendo_hth`/`self._cola_hth`), poblada por
    `_reproducir_comando_hth()` (marca el comando como reproduciendo,
    calcula y marca el ítem real SIGUIENTE — mismo patrón anti-
    recursión que ya usa el Comando FMT desde la ronda 29 — y arranca
    el primer clip) y avanzada por `_reproducir_siguiente_clip_hth()`.
    `_on_fin_de_item()` (la señal `finalizo_item` del motor) ahora
    bifurca: si hay una secuencia HTH en curso, sigue con el próximo
    clip de la cola o, si ya se agotó, sale del modo HTH y recién ahí
    llama a `_avanzar()` para continuar con el ítem real. Un error de
    reproducción (`_on_error`) a mitad de la secuencia aborta el resto
    del anuncio en vez de disparar la cascada de reintentos normal
    (pensada para tandas reales, no para clips de voz cortos) — sigue
    directo con el ítem real ya calculado. `_detener()` (Stop) también
    aborta la cola por las dudas (defensivo, mismo espíritu de
    "nunca confiar en una sola capa de protección" ya establecido para
    libVLC en este proyecto). `GestorPublicidad` ganó un parámetro
    `ventana_explorador=None` en el constructor (wireado en
    `MainWindow._inicializar_motores_audio()`), necesario para que
    `core/hth.py` pueda resolver los clips por género.

    **UI**: `gui/dialogo_insertar_comando_hth.py` (nuevo, lista fija
    HORA/TEMPERATURA/HUMEDAD — a diferencia del diálogo de FMT, acá no
    hace falta "crear" nada antes, los 3 tipos siempre existen).
    Insertable desde el menú contextual de Ventana 1 ("▶ Insertar
    Comando HTH...", junto al de FMT) y desde un botón nuevo del
    Programador ("▶ Comando HTH...", junto al de FMT). El comando se
    guarda con `agregar_comando(bloque, "HTH", parametro)` — MISMA
    función genérica que ya usaba FMT (`tipo_comando="HTH"`,
    `parametro_comando="HORA"/"TEMPERATURA"/"HUMEDAD"`), así que TODA
    la persistencia/carga/serialización (`cargar_bloques()`,
    `_guardar_estado_ahora()`/`_restaurar_desde_disco()`,
    `_serializar_bloques()`/`_cargar_programacion_existente()` del
    Programador) ya lo soportaba sin cambios — confirmado con un test
    de round-trip. Se muestra como "▶ HTH: HORA" en el árbol (mismo
    azul `COLOR_COMANDO` que FMT). El mensaje de "Reemplazar" de
    Ventana 1 y del Programador se generalizó para mencionar "Comando
    (FMT/HTH)" en vez de sólo FMT.

    Probado con `test_hth_motor.py` (nuevo, 15 verificaciones del
    motor puro: orden intro→hora→minutos, falta un clip → `None`,
    normalización de título, positiva vs. negativa con reuso del clip
    de grados, formato de 3 dígitos de humedad con clamp 0-100,
    despacho de `resolver_comando_hth` con `ahora`/`clima` inyectados,
    parámetro desconocido) + `test_hth_gui.py` (nuevo, 32
    verificaciones de integración con la `MainWindow` real: género HTH
    disponible, comando insertado y mostrado correctamente, secuencia
    de 3 clips reproducidos EN ORDEN con un solo llamado a
    `resolver_comando_hth` — sin recursión ni duplicados — terminando
    en el ítem real de después, comando sin clips completos salteado
    sin sonar nada, error a mitad de secuencia aborta sin disparar la
    cascada normal, Stop aborta la cola, el MISMO flujo pero
    DESCUBIERTO por `_avanzar()` de forma natural — fin de ítem, no un
    llamado directo, mismo motivo que llevó a reescribir
    `test_musicalizador_fixes.py` en su momento —, diálogo expone los
    3 tipos fijos, y persistencia round-trip) + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`). **Nunca probado con audio/VLC real ni contra
    la API real de Open-Meteo** (el sandbox no tiene libVLC y el
    fetch de clima se probó solo con datos inyectados, sin red real):
    falta que Santiago (1) grabe los clips de voz reales con la
    nomenclatura exacta documentada en `core/hth.py` y los importe con
    género "HTH", (2) confirme que un `curl` manual a
    `api.open-meteo.com` desde su notebook funciona (para descartar
    cualquier bloqueo de red específico de su entorno), (3) inserte un
    Comando HTH real en un bloque de Ventana 1 y confirme que se
    escucha el anuncio completo sin baches ni recortes raros entre
    clips, y (4) confirme las coordenadas de Configuración → General
    (default General Juan Madariaga) o las ajuste si hace falta.
40. ~~4 pedidos tras la primera prueba real del Comando HTH y de
    EasyEffects: robustez de EasyEffects, drag&drop V1→Auxiliar,
    reanalizar biblioteca, instrucciones de importación HTH~~ —
    Santiago probó ambas funciones nuevas con hardware/EasyEffects
    reales y reportó 3 pedidos de código más una pregunta operativa:

    **a) Bug real: "se abre EasyEffects pero se cierra... no respondió
    al cambiar de preset"** — causa de fondo en `asegurar_en_ejecucion()`
    (`core/easyeffects_control.py`): el sondeo previo solo confirmaba
    que el PROCESO existía (`pgrep`), no que la instancia ya estuviera
    lista para aceptar comandos remotos — el servicio D-Bus/GApplication
    puede tardar bastante más en registrarse, sobre todo en hardware
    modesto (Celeron N2820). `_poblar_menu_easyeffects()` llamaba
    `listar_presets()`/`preset_activo()` inmediatamente después,
    y el operador podía elegir un preset antes de que la instancia
    respondiera de verdad — de ahí "se abre pero se cierra" (posible
    caída temprana del proceso) seguido del error al cambiar de
    preset. Corregido con un sondeo en DOS FASES: (1) `pgrep` hasta
    que el proceso existe (`TIMEOUT_ARRANQUE_SEGUNDOS`, subido de 3 a
    8s), (2) un comando REAL de solo lectura (`--presets`) reintentado
    hasta que la instancia responda de verdad
    (`TIMEOUT_PROBE_CLI_SEGUNDOS`, 6s) — recién ahí se declara éxito.
    La rama "ya estaba corriendo" de `asegurar_en_ejecucion()` (la que
    se ejecuta CADA VEZ que se abre el menú "FM") también se corrigió
    para no confiar ciegamente en que el proceso exista — repite el
    mismo sondeo de responsividad antes de dar por buena la instancia.
    Además, `cargar_preset()` ahora reintenta UNA vez (con una pausa
    corta) si el primer intento falla, sea por timeout/excepción o por
    un returncode de error — mismo criterio de "nunca confiar en una
    sola capa de protección" ya establecido para libVLC en este
    proyecto. Todo el módulo ahora deja rastro en el log
    (`registrar_evento`/`registrar_error`) de cada fase — antes no
    dejaba ninguno, dificultando diagnosticar sin acceso a la PC.
    **Nunca probado contra el EasyEffects real de Santiago** (el
    sandbox no lo tiene instalado): falta que confirme que el ícono FM
    ya no falla al elegir un preset la primera vez que se usa en la
    sesión.

    **b) Drag&drop de Ventana 1 al Auxiliar, NUNCA a Ventana 2**
    (pedido explícito, con esa restricción textual) — `ArbolPublicidadConDrop`
    (`gui/common_widgets.py`) pasó de `DropOnly` (solo podía RECIBIR
    arrastres) a `DragDrop`, con un `startDrag()` nuevo que exporta la
    ruta del ítem seleccionado (una tanda con archivo real — los
    nodos de bloque y los Comandos, sin ruta, no se arrastran) con el
    mismo protocolo `QUrl`/texto que ya usa `ArbolOrigenArrastre` del
    Explorador — así el lado receptor no necesita código nuevo, procesa
    el drop exactamente como si viniera de Ventana 3. El desafío real
    fue el "nunca a Ventana 2": `ArbolReproductorConDrop` es la MISMA
    clase que usan tanto Ventana 2 como la Auxiliar (ver roadmap ronda
    38), así que la distinción no se puede hacer por tipo — se agregó
    un parámetro de instancia, `acepta_desde_publicidad: bool = False`
    (default `False`, así Ventana 2 queda excluida sin tocarla), que
    gatea `dragEnterEvent`/`dragMoveEvent`/`dropEvent` chequeando
    `isinstance(event.source(), ArbolPublicidadConDrop)` — si el
    arrastre viene de Ventana 1 y esta instancia puntual no lo acepta,
    se ignora. `PanelReproductor` (constructor y `_construir_ui`)
    ganó el mismo parámetro para poder pasarlo hacia abajo, y
    `gui/ventana_auxiliar.py` es el ÚNICO lugar que lo pasa en `True`.
    El resto del flujo de recepción (`MainWindow._on_archivo_soltado_auxiliar`)
    no necesitó ningún cambio — ya resolvía el registro completo por
    ruta si el archivo estaba en la biblioteca, y degradaba a
    metadata mínima si no.

    **c) "Los temas siguen teniendo silencio al final" — reanalizar
    biblioteca (no era un bug de que la config no se aplicara, sino
    de retroactividad)**: investigado a fondo, el recorte de silencio
    SÍ se aplica en la reproducción real de Ventana 1/2 (queda grabado
    en `punto_inicio_ms`/`punto_fin_ms` de cada material al
    importarlo, y `MotorAudio._emitir_posicion()` corta ahí de
    verdad, ver `core/audio_engine.py`) — la etiqueta "(Ventana 3)"
    del campo en Configuración era simplemente confusa (daba a
    entender que el valor solo afectaba la vista previa), corregida a
    "(Música/Artística/Pisador)" con un tooltip nuevo que aclara que
    SÍ gobierna la reproducción real. El problema real de fondo:
    **cambiar la tolerancia en Configuración nunca fue retroactivo**
    — el análisis se calcula UNA sola vez, al importar/reemplazar un
    archivo; un tema ya cargado con la tolerancia vieja se queda con
    ese recorte para siempre hasta que se lo reemplace a mano. Nueva
    función `config/settings.reanalizar_biblioteca(config)`: recorre
    TODA la biblioteca (recursivo, con subcategorías) directamente
    sobre `biblioteca.json` — sin necesitar la ventana Explorador
    abierta ni su árbol en memoria —, vuelve a correr `analizar_audio()`
    con la tolerancia/umbral ACTUALES (respetando la misma regla de
    género estricto/general que ya usa el alta normal,
    `tolerancia_silencio_para_genero()`), actualiza cada registro en
    el lugar y persiste. Los archivos cuya ruta ya no existe en disco
    se saltean sin romper el resto. Nuevo método público
    `VentanaExplorador.recargar_biblioteca_desde_disco()` para
    refrescar el árbol EN VIVO después (sin él, habría que cerrar y
    reabrir la app para ver el resultado). Botón nuevo "🔄 Reanalizar
    biblioteca (recorte de silencio)" en Configuración → Diagnóstico
    — usa los valores de tolerancia/umbral YA TIPEADOS en esa misma
    ventana (aunque no se haya guardado todavía), pide confirmación
    (puede tardar y congela la UI mientras corre, avisado en el
    diálogo), y muestra cuántos archivos se reanalizaron al terminar.
    `VentanaConfiguracion` ganó un parámetro `ventana_explorador=None`
    en el constructor para poder llamar al refresco — `MainWindow.
    abrir_configuracion()` lo pasa siempre.

    **d) Instrucciones de importación de HTH** — Santiago está
    importando los HTH reales de Dinesat a esta app; se le contestó en
    el chat con la receta exacta (género "HTH" + nomenclatura EXACTA
    de `core/hth.py` como título) — no ameritó cambio de código,
    la nomenclatura ya estaba completamente definida en la ronda 39.

    Probado con `test_ronda_dnd_reanalisis_ee.py` (nuevo, 20
    verificaciones): Ventana 1 exporta ítems por drag (bloques/
    Comandos sin ruta no arrastran), Ventana 2 rechaza un drag
    proveniente de Ventana 1 mientras la Auxiliar lo acepta (con un
    `event.source()` simulado), un drag desde otro origen (Explorador)
    sigue funcionando en ambas; `reanalizar_biblioteca()` recorre
    categorías anidadas, aplica la tolerancia correcta por género,
    persiste los cambios y saltea rutas inexistentes sin romper nada;
    EasyEffects con un binario falso que simula "proceso vivo pero
    `--presets` falla las primeras veces" confirma que
    `asegurar_en_ejecucion()` espera la respuesta real antes de
    declarar éxito, y que `cargar_preset()` reintenta exactamente una
    vez — + suite de regresión completa sin fallos nuevos (mismos 3
    fallos preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder probarse
    con audio/VLC/EasyEffects reales**: falta que Santiago confirme
    que el ícono FM ya no falla al primer uso, que arrastrar una tanda
    de Ventana 1 a la Auxiliar funciona y que intentarlo sobre Ventana
    2 no hace nada, y que "Reanalizar biblioteca" deja los temas
    musicales sin silencio al final con una tolerancia más baja.
41. ~~4 pedidos tras importar los HTH reales: sacar INTRO HORA,
    buscar actualización sola al abrir, preload en operaciones lentas,
    "Editar información" en el Explorador~~ — Santiago terminó de
    importar sus HTH reales y reportó 4 pedidos más:

    **a) Bug real: el Comando HTH nunca sonaba — "es la hora..." ya
    viene grabado DENTRO de cada clip de hora**: el diseño original
    (ronda 39) inventó un clip de intro fijo, "INTRO HORA", que el
    manual de Dinesat no documenta — pero los archivos reales de
    Santiago no lo necesitan: cada clip `HORA XX` ya dice la frase
    completa ("es la hora cero", "es la hora una"). Como ese material
    "INTRO HORA" no existe (nunca se iba a grabar), el comando HORA se
    saltaba SIEMPRE sin sonar nada — el mismo criterio "todo o nada"
    de `core/hth.py` que evita un anuncio a medias también terminaba
    bloqueando el caso normal. Corregido sacando "INTRO HORA" por
    completo de `resolver_clips_hora()` — ahora concatena únicamente
    `HORA XX` + `MINUTOS XX`. **Regla para el futuro**: un clip
    "genérico" inventado por esta app (no documentado en el manual de
    Dinesat) es un candidato a redundar con lo que el operador ya
    tiene grabado — conviene confirmar contra el material real antes
    de exigirlo como obligatorio.

    **b) Buscar actualización sola al abrir, preguntando ahora/luego**
    (antes solo se buscaba a mano en Configuración → Actualizaciones):
    `MainWindow.__init__` dispara `_buscar_actualizacion_automatica()`
    diferido 2.5s (`QTimer.singleShot`, misma prioridad ya usada para
    EasyEffects — no competir con el arranque de la radio). Es una
    consulta de red (`git fetch`, ver `core/actualizador.py`), así que
    corre con el mismo cursor de espera que el resto de la app en vez
    de trabar el arranque en silencio. Si hay una actualización,
    pregunta con botones de texto propio ("Actualizar ahora"/"Más
    tarde", no un Sí/No genérico) — NUNCA la aplica sola sin
    confirmación. La decisión del diálogo se extrajo a
    `_preguntar_actualizar_ahora()`, un método aparte devolviendo
    `bool`, específicamente para poder testearla sin tener que simular
    un click real sobre un `QMessageBox` (imposible en offscreen). Si
    el operador elige "ahora", reusa el mismo camino que ya tenía el
    botón manual de Configuración (`aplicar_actualizacion()` +
    `preparar_cierre_por_actualizacion()` + `reiniciar_aplicacion()`).

    **c) Preload en operaciones lentas (pedido explícito, "que se
    congele es normal, pero deberíamos poner un preload")**: esta app
    nunca usó threading (confirmado, cero `QThread` en todo el
    código) — la solución adoptada, consistente con ese estilo
    deliberadamente simple, es cursor de espera (`WaitCursor`) +
    `QApplication.processEvents()` periódico (cada 15 archivos)
    DURANTE el bucle lento, no reemplazar el bloqueo por threading
    real. Aplicado al caso que Santiago reportó en carne propia
    (importar 700 archivos de una — `VentanaExplorador.
    _importar_archivos_masivo()`, el único bucle que corre
    `analizar_audio()` — pydub/ffmpeg, lento de verdad — por cada
    archivo del lote). Los altas/reemplazos de UN solo archivo y
    "Reanalizar biblioteca" (ronda 40) ya tenían o no necesitan este
    tratamiento (un solo archivo es rápido; reanalizar ya usaba
    `WaitCursor` desde que se creó).

    **d) "Editar información" (menú contextual + botón, Explorador)**:
    pedido explícito para poder "cambiar nombre, etc." de un material
    YA importado sin tocar el audio ni re-analizarlo — distinto de
    "🎚 Editar audio" (ya existía, abre el editor de audio del
    sistema, renombrado en el menú para no confundirlo) y de "⟲
    Reemplazar" (cambia el archivo de audio en sí). Nuevo diálogo
    `gui/dialogo_editar_informacion.py` (mismo patrón de combo de
    categoría con sangría que `DialogoAgregarArchivo`) edita título/
    artista/género, y opcionalmente MUEVE el material a otra
    categoría — en ese caso, mismo criterio que un move por
    drag&drop (`_mover_archivos_a_categoria`): el registro conserva su
    código y el resto de su metadata, solo cambia de lista; gateado
    por el mismo flag `confirmar_antes_de_eliminar` que ya usa el
    resto de operaciones "riesgosas" del Explorador. Botón "✏ Info"
    nuevo junto a Agregar/Reemplazar/Eliminar, y entrada "✏ Editar
    información..." en el menú contextual.

    Probado con `test_ronda_hth_update_preload_editar.py` (nuevo, 18
    verificaciones): `resolver_clips_hora()` ya no pide "INTRO HORA";
    `_buscar_actualizacion_automatica()` con
    `hay_actualizacion_disponible`/`aplicar_actualizacion` mockeados
    cubre los 4 casos (sin actualización no pregunta nada, "Más
    tarde" no aplica nada, "Actualizar ahora" aplica+reinicia, y un
    fallo de `aplicar_actualizacion()` no dispara el reinicio);
    importación masiva con `analizar_audio` mockeado confirma que el
    cursor de espera se restaura al terminar (comparando profundidad
    de pila, no un `None` absoluto, porque el preload de arranque de
    `MainWindow.__init__` puede dejar su propio cursor apilado sin
    que corra su QTimer de auto-retiro en un script sin event loop
    real) y que los 5 archivos de prueba quedan importados;
    "Editar información" con el diálogo mockeado confirma edición
    sin mover categoría (código y ruta intactos) y edición CON
    cambio de categoría (el registro aparece en la categoría destino,
    desaparece de la origen, código igual) — + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`). **Sigue sin poder probarse con audio/VLC/git
    reales**: falta que Santiago confirme que el Comando HTH de HORA
    ahora sí suena con sus clips reales, que la búsqueda de
    actualización automática no demora el arranque de forma molesta,
    que el preload se nota en una importación grande de verdad, y que
    "Editar información" cambia lo esperado sin romper nada de lo ya
    cargado.
42. ~~5 pedidos: ordenar columnas del Explorador, bloque de V1 gateado
    por Automático, drag&drop multi-selección V1->Auxiliar, listas
    guardadas del Auxiliar, renombrar "Bloque" a "TANDA - Rotativa"~~
    — cinco pedidos independientes en un solo mensaje:

    **a) Ordenar la lista de archivos del Explorador por columna
    (pedido explícito, "A-Z y si aprieto otra vez Z-A")**: click en
    cualquier encabezado de `tree_archivos` (Duración/Título/Artista/
    Categoría/Código) ordena ascendente; un segundo click en la MISMA
    columna invierte a descendente (`VentanaExplorador.
    _ordenar_por_columna()`, colgado de `header().sectionClicked`).
    Orden MANUAL, no `QTreeWidget.setSortingEnabled()` — se ordena por
    el campo REAL del registro (`_CAMPO_POR_COLUMNA`, ej. "Categoría"
    ordena por `genero`, no por el texto de la celda), releyendo
    `ROL_REGISTRO` de cada fila y re-renderizando con el mismo
    `_agregar_fila_archivo()` que ya usan la selección de categoría y
    la búsqueda — sin lógica de pintado duplicada. La Duración ya
    viene formateada "HH:MM:SS" con ceros a la izquierda, así que el
    orden lexicográfico de esa cadena coincide con el cronológico real
    sin necesitar parsear a segundos.

    **b) Bug real de diseño revertido: el bloque de Ventana 1 se
    disparaba por horario SIN importar el botón AUTOMÁTICO (pedido
    explícito: "solo se dispara si el botón Automático está activo")**
    — una ronda anterior había fijado a propósito la regla opuesta
    ("los bloques se disparan por horario SIEMPRE, no depende del
    botón"); Santiago pidió ahora invertirla. Corregido en los DOS
    puntos de disparo de `SchedulerAutomatico`
    (`core/playlist_manager.py`) — `_arrancar_al_iniciar()` (bloque
    vigente al abrir la app) y `_tick()` (disparo por transición de
    hora, cada segundo): ambos chequean
    `self.ventana.esta_en_automatico()` ANTES de llamar a
    `_disparar_bloque()`, y si está apagado, no disparan nada (con un
    evento en el log para poder diagnosticarlo sin audio real). La
    vuelta a Emisión al terminar Publicidad ya estaba gateada por el
    mismo botón desde antes — no hizo falta tocar nada ahí, la
    asimetría (disparo SÍ gateado ahora, vuelta YA gateada) queda
    resuelta con un único botón gobernando el ciclo completo, tal como
    pidió Santiago. Regresión confirmada contra la suite existente del
    ciclo automático (`test_ciclo_automatico.py`): los 10 tests ya
    existentes siguen pasando sin cambios porque todos arrancan con el
    Automático prendido (default de fábrica) o lo prenden a mano antes
    de disparar — la rama nueva ("apagado no dispara") es
    estrictamente aditiva.

    **c) Drag&drop de Ventana 1 al Auxiliar con selección múltiple
    (pedido explícito, extiende la ronda 40)**: `ArbolPublicidadConDrop.
    startDrag()` (`gui/common_widgets.py`) pasó de exportar solo
    `self.currentItem()` a exportar TODAS las tandas seleccionadas
    (`self.selectedItems()`, mismo patrón Ctrl/Shift ya soportado por
    el árbol) como una lista de `QUrl` — los nodos de bloque y los
    Comandos (sin ruta real) se descartan de la selección en silencio
    en vez de cancelar todo el arrastre, así seleccionar varias tandas
    Y de paso un bloque/comando no rompe nada. El lado RECEPTOR
    (`ArbolReproductorConDrop.dropEvent()`, compartido por Ventana 2 y
    la Auxiliar) ya iteraba `event.mimeData().urls()` en un loop desde
    antes — no hizo falta tocar nada ahí, confirmado con un test
    dedicado que arrastra 3 tandas de una y verifica que la Auxiliar
    recibe las 3, mientras Ventana 2 (`acepta_desde_publicidad=False`)
    sigue rechazando el arrastre completo igual que antes.

    **d) Listas guardadas del Auxiliar — guardar con nombre, cargar
    (reemplaza lo que haya) o borrar, todo con confirmación siempre
    (pedido explícito)**: nuevo archivo `config/data/listas_auxiliar.json`
    (`{"Nombre": {"items": [...]}, ...}`, escritura atómica de
    siempre) con las funciones nuevas en `config/settings.py`
    (`guardar_lista_auxiliar`/`listar_listas_auxiliares`/
    `obtener_lista_auxiliar`/`eliminar_lista_auxiliar`). Refactor
    aprovechado de paso en `core/gestor_emision.py`: la lógica de
    volcar el panel a una lista de dicts (ítems + Pisador anidado +
    análisis de audio) y de restaurarla, que antes vivía SOLO adentro
    de `_guardar_estado_ahora()`/`_restaurar_desde_disco()` (la
    persistencia automática de Ventana 2), se extrajo a dos métodos
    públicos reutilizables — `GestorPlaylist.serializar_items()` /
    `cargar_items()` — así el guardado/carga de listas con nombre del
    Auxiliar usa EXACTAMENTE el mismo camino ya probado, sin duplicar
    la lógica de armar/leer el dict de cada ítem. Dos botones nuevos,
    exclusivos de la Auxiliar (`gui/ventana_auxiliar.py`, no
    compartidos con Ventana 2 vía `PanelReproductor` porque esta
    función no aplica ahí): "💾 Guardar lista..." (pide nombre con
    `QInputDialog`, confirma sobreescritura si el nombre ya existía,
    confirma el guardado en cualquier caso) y "📂 Cargar lista..."
    (abre `gui/dialogo_listas_auxiliar.py`, diálogo NUEVO que lista
    las guardadas y tiene un botón "🗑 Borrar" en el MISMO diálogo —
    pedido explícito de Santiago de no separar cargar y borrar en
    lugares distintos — con su propia confirmación antes de borrar de
    verdad; cargar confirma siempre, con un texto más fuerte si ya
    había algo cargado que se va a REEMPLAZAR). `MainWindow` conecta
    las nuevas señales `solicitud_guardar_lista`/`solicitud_cargar_lista`
    recién cuando la Auxiliar se crea (mismo punto donde ya se conecta
    el resto de su wiring). Probado con un test dedicado: round-trip
    completo de guardar/listar/obtener/sobrescribir/eliminar contra el
    archivo JSON aislado, más integración contra un panel REAL de la
    Auxiliar (`serializar_items()` vuelca ítems+Pisador reales,
    `cargar_items()` reemplaza el contenido de un panel con "basura"
    previa cargada y arma rojo/verde por defecto sin reproducir nada
    solo).

    **e) "Bloque" reemplazado por "TANDA - Rotativa" en Ventana 1 y el
    Programador (pedido explícito, solo texto visible — mismo criterio
    ya usado para el retitulado de Ventana 1/2 de una ronda anterior,
    sin tocar `ROL_HORA_BLOQUE`/`bloques()`/`crear_bloque_nuevo()` ni
    ningún otro identificador interno)**: el TÍTULO por defecto de una
    tanda horaria nueva —lo que el operador realmente lee como "el
    nombre de esto" en el árbol— ya no dice "Bloque" en ningún lado:
    `VentanaPublicidad.crear_bloque_nuevo()` (antes `"Bloque: {hora}"`,
    ahora `"TANDA - Rotativa"` — la hora ya queda como prefijo del
    texto mostrado, así no se duplica), su diálogo de confirmación
    (`_confirmar_y_crear_bloque()`, refleja el nuevo título en el
    mensaje), `VentanaProgramador._agregar_bloque()` (default cuando
    el campo de título queda vacío, antes `"Bloque sin título"`),
    `VentanaProgramador._cargar_plantilla_basica()` (los 24 bloques de
    la plantilla "Nueva", antes `"Bloque {:02d}hs"`) y
    `DialogoEditarBloque.titulo()` (mismo default vacío que el
    Programador). Los mensajes/tooltips que usan "bloque horario" como
    término GENÉRICO del concepto (ej. "＋ Añadir Bloque Horario",
    "Primero creá un bloque horario", el aviso fijo "No se encontró
    Bloque Horario..." pedido textualmente en una ronda anterior) NO
    se tocaron a propósito — la distinción es la misma que ya rige
    todo el proyecto: renombrar el NOMBRE VISIBLE de la entidad, nunca
    barrer cada ocurrencia genérica de la palabra. Probado con un test
    dedicado (`crear_bloque_nuevo()`, `_agregar_bloque()` sin título,
    los 24 de la plantilla básica, y `DialogoEditarBloque.titulo()`
    vacío — ninguno contiene ya la palabra "Bloque").

    Probado con 4 tests nuevos dedicados (ordenar columnas, drag&drop
    multi-selección V1→Auxiliar con verificación de que Ventana 2
    sigue rechazando, listas guardadas del Auxiliar con integración de
    panel real, renombre TANDA - Rotativa) + actualización de 2
    aserciones preexistentes que codificaban el título viejo
    ("Bloque 00hs"/"Bloque 23hs" en la plantilla de 24, dentro de
    `test_pisador_crossfade_stop_programador.py`) + regresión de
    `_ciclo_automatico.py` (10/10 sin cambios) + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py` — confirmado corriendo la MISMA batería contra
    el código sin modificar vía `git stash`, que dos fallas
    adicionales vistas en una corrida de la batería completa
    —`test_ventana1.py`/`test_ventana1_persistencia.py`— ya aparecían
    igual en el código original: son contaminación de estado entre
    scripts que comparten `config/data/` al correr 50+ tests seguidos
    sin limpiar entre uno y otro, no una regresión de esta ronda).
    **Sigue sin poder probarse con audio/VLC real**: falta que
    Santiago confirme que ordenar por columna en el Explorador se
    siente natural con su biblioteca real, que un bloque de Ventana 1
    ya NO se dispara solo con el Automático apagado, que arrastrar
    varias tandas seleccionadas de Ventana 1 al Auxiliar las trae
    todas de una, que guardar/cargar/borrar listas del Auxiliar
    funciona como espera en el uso diario, y que "TANDA - Rotativa" es
    el texto que quería ver en vez de "Bloque".
43. ~~5 pedidos: Automático dispara el bloque vigente al activarse,
    drag&drop de reordenar en V1 (tandas y FMT/HTH), selección celeste
    con relleno sin borde, reordenar categorías del Explorador,
    búsqueda de actualización asíncrona (nunca bloqueante)~~ — cinco
    pedidos independientes en un solo mensaje, "quedan detalles":

    **a) Activar el botón AUTOMÁTICO a mano debe arrancar YA el
    bloque horario vigente (pedido explícito: "si son las 21.24 debe
    comenzar con el bloque de las 21 horas")**: `SchedulerAutomatico.
    _on_automatico_cambiado()` (`core/playlist_manager.py`) ya existía
    pero solo hacía "limpieza" (`_marcar_bloques_pasados_sin_disparar`)
    sin arrancar nada — ahora, al activarse, también llama a
    `_bloque_vigente()` (mismo criterio que usa `_arrancar_al_iniciar`
    al abrir la app: el de hora más tardía que ya pasó, con ítems) y
    lo dispara con `_disparar_bloque()`. Dos guards: no dispara si ya
    hay un bloque disparándose (`_esperando_liberar_emision`), y —
    **bug real encontrado en esta misma ronda, atrapado por el propio
    test de regresión antes de llegar a Santiago**— tampoco dispara si
    Publicidad YA está sonando algo (`gestor_publicidad.motor.
    esta_reproduciendo()`): sin este segundo guard, activar el
    Automático mientras un bloque ya estaba en curso lo REINICIABA
    desde el primer ítem en vez de dejarlo seguir — activar el botón
    nunca debe interrumpir/reiniciar algo que ya está sonando, solo
    debe tomar el control de la vuelta a Emisión al terminar.

    **b) Drag&drop para reordenar en Ventana 1 — tandas Y Comandos
    FMT/HTH (pedido explícito: "no lo puedo hacer, y los FMT tampoco
    me permite arrastrarlo")**: el diseño original de
    `ArbolPublicidadConDrop` (`gui/common_widgets.py`) decía
    literalmente "Nunca hubo reordenado interno pedido para Ventana
    1" e ignoraba cualquier auto-drop; además su `startDrag()` excluía
    de la selección cualquier ítem SIN ruta real (los Comandos). Ahora
    implementa el mismo algoritmo jerárquico (bloque -> tandas/
    comandos) que ya usa `ArbolProgramadorConDrop._reordenar_manual`
    — un ítem se reordena DENTRO de su bloque o se mueve a OTRO
    bloque, nunca los bloques enteros — y los Comandos se reordenan
    igual que una tanda (simplemente no viajan como `QUrl` si el
    destino es la Auxiliar, ya que ahí no tienen sentido). El ítem "en
    punta" (rojo) sigue sin poder moverse mientras suena, mismo
    criterio que Ventana 2. El `startDrag()` unificado ahora sirve DOS
    destinos con el mismo gesto: reordenar dentro de sí mismo, y
    exportar a la Auxiliar (selección múltiple, pedido de la ronda
    anterior) — se distinguen en `dropEvent()` por `event.source()`,
    mismo patrón que el resto de árboles con Drag&Drop de la app.

    **c) Selección celeste con relleno sólido + texto negro, sin
    borde — pero sin tapar nunca rojo/verde (pedido explícito, "regla
    permanente")**: `gui/styles.py`, la regla
    `#tree_reproductor::item:selected`/`#tree_publicidad::item:selected`
    pasó de `background-color: transparent; border: 2px solid celeste`
    a `background-color: celeste; color: black; border: none`. Esto
    SOLO afecta a ítems SIN estado — `DelegadoConservaColorEstado`
    (`gui/common_widgets.py`) sigue interceptando el pintado ANTES de
    que esta regla se aplique cuando el ítem está en rojo/verde,
    pintándolo SIN el flag de selección (conserva su color propio
    intacto); como ahora ya no hace falta señalizar la selección con
    un borde alternativo en ESE caso (pedido explícito "sin borde,
    siempre"), se sacó también el borde manual que el delegado
    dibujaba antes para rojo/verde+seleccionado — un ítem rojo/verde
    seleccionado ahora no tiene NINGUNA decoración extra, solo su
    color de estado de siempre.

    **d) Reordenar las categorías del Explorador por arrastre (pedido
    explícito: "permití también que pueda ordenar las carpetas de las
    categorías")**: nueva `ArbolCategoriasConDrop`
    (`gui/common_widgets.py`), reemplaza el `ArbolConDrop` genérico
    que usaba `tree_categorias`. Alcance acotado A PROPÓSITO: solo
    reordena una categoría ENTRE SUS HERMANAS (mismo padre, nivel
    superior o una subcategoría anidada) — mover una categoría a OTRO
    padre (re-anidarla) es una operación mucho más grande y riesgosa
    (arrastraría todos sus archivos y subcategorías) que no fue
    pedida, sigue haciéndose a mano. El drop de archivos EXTERNOS
    sobre una categoría (ya existente, heredado de `ArbolConDrop`)
    sigue funcionando igual — se distingue por `event.source()`. Señal
    nueva `orden_cambiado`, conectada a `VentanaExplorador.
    _guardar_biblioteca()` — el nuevo orden se persiste solo, sin
    código nuevo de serialización (`_serializar_biblioteca()` ya
    recorre el árbol en orden visual).

    **e) Búsqueda de actualización ASÍNCRONA — bug real de fondo
    corregido de paso (pedido explícito: "no debe impedir la
    reproducción inmediata y con automático activado")**: la
    verificación automática al abrir (ronda 41) llamaba a
    `hay_actualizacion_disponible()`, que hace `git fetch` +
    `rev-parse` con `subprocess.run()` SINCRÓNICO, en el mismo hilo
    que corre TODA la app (este proyecto nunca usó threading — ver
    "Testing" más abajo). Con una conexión lenta, eso podía congelar
    la app ENTERA (incluida música ya sonando: crossfade, posición,
    cualquier click) hasta el timeout de 30s. Nueva función
    `core/actualizador.buscar_actualizacion_async(callback)`: el único
    paso realmente lento (`git fetch`, va por red) corre en un
    `QProcess` asíncrono — mismo estilo ya usado en este proyecto para
    EasyEffects/`reiniciar_aplicacion()`, sin necesitar un `QThread`
    — y el resto (comparar `rev-parse` local vs. remoto) son lecturas
    de disco casi instantáneas que sí se resuelven sincrónico dentro
    del callback. `MainWindow._buscar_actualizacion_automatica()`
    ahora llama a esta versión, guardando la referencia del
    `QProcess` en curso (`self._proceso_buscar_actualizacion`, para
    que Python no lo recolecte a mitad de camino) — el
    `hay_actualizacion_disponible()` sincrónico ORIGINAL se dejó
    intacto y sigue siendo el que usa el botón MANUAL de Configuración
    → Actualizaciones (una espera breve ahí es aceptable, es una
    acción explícita del operador, no algo que corre solo en segundo
    plano). El defer de 2.5s antes de disparar la búsqueda se
    MANTUVO igual (ya no es por miedo a que bloquee, es solo para no
    competir con el primer render de la ventana) — **bug real
    encontrado por el propio test de regresión de esta ronda**: un
    defer más corto (300ms) hacía que varios scripts de test que
    bombean el event loop un par de segundos para procesar timers
    diferidos (fades, etc.) dispararan sin querer un `git fetch` REAL
    contra el repo en medio del test, colgando el proceso hasta que
    `git` fallara por timeout de red — confirma que 2.5s es la
    duración correcta, no solo un número arbitrario. Además,
    `main.py` ahora deja la pantalla de preload (`QSplashScreen`, ya
    existente desde una ronda anterior) un instante más —
    tope FIJO de 1.2s, nunca depende de que la verificación termine—
    mostrando "Verificando actualizaciones..." para cubrir
    visualmente también esa fase, sin que la reproducción (incluido
    el arranque automático del bloque vigente, que corre por su
    cuenta en los timers internos de `MainWindow`) espere a que el
    splash se cierre.

    Probado con 5 tests nuevos dedicados (Automático dispara el
    bloque vigente correcto —no uno futuro— al activarse, no dispara
    nada sin bloque vigente, NO reinicia un bloque ya en curso al
    activarse; reordenar tandas dentro de un bloque y entre bloques en
    Ventana 1, reordenar un Comando FMT/HTH, bloqueo del ítem rojo
    tanto en `_reordenar_manual` como en `startDrag`; QSS de selección
    con relleno celeste + texto negro + sin borde, delegado confirma
    que un ítem rojo pierde el flag de selección — nunca se tapa, sin
    decoración extra; reordenar categorías de nivel superior y
    subcategorías, rechazo de mover entre padres distintos,
    persistencia reflejada en `_serializar_biblioteca()`; búsqueda de
    actualización asíncrona con git REAL contra un remoto bare local
    de prueba —sin mockear nada— confirmando que el callback se
    dispara exactamente una vez con el resultado correcto tanto sin
    cambios como con un commit nuevo en el remoto) + actualización de
    un test preexistente que mockeaba la API sincrónica vieja
    (`test_ronda_hth_update_preload_editar.py`) + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`). **Sigue sin poder probarse con audio/VLC/git
    reales de producción**: falta que Santiago confirme que activar el
    Automático arranca el bloque de la hora correspondiente sin
    interrumpir nada que ya estuviera sonando, que ahora puede
    reordenar tandas y Comandos en Ventana 1 arrastrando con
    naturalidad, que la selección celeste se ve como esperaba sin
    tapar nunca el rojo/verde, que reordenar categorías en el
    Explorador funciona con su biblioteca real, y que el arranque se
    siente igual de inmediato que antes (la búsqueda de actualización
    nunca debería notarse).
44. ~~Robustez de audio: buffer anti-tartamudeo, motor 100% audio
    (ignora video), re-verificación de silencios V1/V2~~ — pedido
    explícito, "para robustecer el sistema":

    **a) Buffer para evitar "tartamudeo" ("fluidez auditiva, evitar
    ruidos o algo que interfiera en la reproducción limpia y
    persistente")**: `core/audio_engine.py` ganó
    `ARGUMENTOS_VLC = ["--no-video", "--file-caching=1000"]`, pasado a
    CADA `vlc.Instance()` que crea un `MotorAudio` (Emisión,
    Publicidad, Auxiliar, Pisador, previo del Explorador — todos
    comparten la misma clase). `--file-caching=1000` sube el buffer de
    lectura/decodificación de archivo de libVLC de ~300ms (default) a
    1000ms — con más margen de buffer, una ráfaga de CPU ocupada por
    otra tarea de la app (un import pesado, redibujar la UI, etc., algo
    más notorio en el hardware modesto de Santiago — Celeron N2820)
    tiene mucho más espacio antes de que la reproducción llegue a
    notarse entrecortada.

    **b) Motor 100% audio, ignora video (pedido explícito: "Hay
    archivos que son videos, hacé que el motor VLC reproduzca SOLO
    audio")**: el mismo `--no-video` del punto (a) resuelve esto de
    raíz — con ese flag, libVLC NUNCA decodifica ni intenta abrir una
    ventana de video para un archivo que la tenga (ej. un .mp4
    importado por error a la biblioteca), solo extrae y reproduce su
    pista de audio. De paso, esto también ayuda al punto (a): decodificar
    video de más es trabajo de CPU completamente inútil para esta app
    (100% de audio) y una causa real de tartamudeo en hardware modesto.

    **c) Re-verificación de silencios en Ventana 1 y 2 (pedido
    explícito: "NO quiero silencios al final de la reproducción...
    deben ser enganchados los temas, un fade veloz") — bug real
    encontrado y corregido**: se auditaron TODOS los puntos donde el
    código llama `motor.reproducir()`/`crossfade_a()` en
    `core/gestor_emision.py` y `core/playlist_manager.py` para
    confirmar que siempre pasan `punto_inicio_ms`/`punto_fin_ms`/
    `ganancia_db` (el recorte de silencio y nivelado ya calculados al
    importar el archivo). La reproducción normal de Ventana 1 y 2, el
    crossfade de Ventana 2, y el previo del Explorador ya estaban
    todos correctos — pero
    `GestorPublicidad._reproducir_siguiente_clip_hth()` (el motor del
    Comando HTH — concatena 2-3 clips de voz cortos, ej. "HORA 14" +
    "MINUTOS 30", uno atrás del otro) se había quedado afuera de esa
    disciplina: llamaba `motor.reproducir(ruta)` a secas, sin ningún
    análisis — mismo tipo de bug ya corregido varias veces antes en
    otros rincones de la app, pero este nunca se había tocado desde
    que se implementó el Comando HTH (ronda 39). El resultado real:
    el silencio de cola SIN recortar de cada clip se sentía como un
    hueco muerto entre "HORA 14" y "MINUTOS 30" — exactamente el tipo
    de "silencio al final" que Santiago pidió eliminar, aunque acá no
    se trate de "temas" sino de clips de voz cortos concatenados.
    Corregido buscando el registro completo por ruta
    (`ventana_explorador.buscar_registro_por_ruta()`, mismo patrón que
    ya usa `_reproducir_item()` para las tandas normales) antes de
    reproducir cada clip de la cola — fail-open (sin análisis si no
    hay `_ventana_explorador` o el registro no aparece, nunca romper
    el anuncio por esto). El resto del mecanismo de "enganchado con
    fade veloz" ya estaba andando correctamente y se confirma sin
    cambios: el fade-out automático de Ventana 1 entre tandas
    (`duracion_fade_out_v1_ms`, 500ms por defecto) y el crossfade de
    Ventana 2 (cuando `crossfade_activado`) ya arrancan el tema
    ENTRANTE inmediato a su volumen final (sin fade-in, pedido de una
    ronda anterior) mientras el SALIENTE se apaga con un fundido
    corto — sin gap, sin corte seco.

    Probado con `test_audio_only_y_buffer.py` (nuevo: confirma que
    `ARGUMENTOS_VLC` incluye `--no-video` y un `--file-caching` mayor
    al default, que `vlc.Instance()` se invoca efectivamente con esos
    argumentos —interceptando la llamada real—, y que `MotorAudio()`
    sigue degradando limpio sin romper nada si no hay libVLC instalado,
    con o sin los argumentos nuevos) + `test_hth_silencio_analisis.py`
    (nuevo: arma 2 clips HTH reales con análisis distinto cada uno en
    la biblioteca, dispara un Comando HTH real a través de
    `GestorPublicidad._reproducir_item()`, y confirma que CADA clip de
    la cola llega a `motor.reproducir()` con su propio
    `punto_inicio_ms`/`punto_fin_ms`/`ganancia_db` — no solo el
    primero) + regresión de `test_hth_gui.py` (18/18 sin cambios, el
    fix no rompió la máquina de estados de la cola de clips) + suite
    de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder probarse
    con audio/VLC real** (como siempre que se toca `core/audio_engine.py`
    — el sandbox no tiene libVLC instalado): falta que Santiago
    confirme con su radio real que (1) el tartamudeo que reportó ya no
    aparece, sobre todo mientras hace algo pesado en paralelo (importar
    archivos, reanalizar biblioteca), (2) que un archivo de video
    importado por error ahora suena bien sin abrir ninguna ventana ni
    gastar CPU de más, y (3) que el Comando HTH ahora suena con los
    clips bien pegados, sin el hueco de silencio que tenía antes entre
    "HORA" y "MINUTOS".
45. ~~Bug real: al abrir solo sonaba el primer ítem de Ventana 1 y
    saltaba a Emisión + ítem Aleatorio de categoría/subcategoría en el
    Programador~~ — dos pedidos:

    **a) Bug real corregido — "cuando abro, se reproduce solo el
    primer item de la ventana 1, y luego pasa a la 2"**: investigado a
    fondo con un test que simula el arranque real (`_arrancar_al_iniciar`
    + varios `finalizo_item` consecutivos sobre un bloque de 3 tandas)
    — la lógica de avance DENTRO de un bloque (`_avanzar()` +
    `_bloque_automatico_actual`) resultó estar bien en el caso general,
    pero se encontró la causa real con un segundo test que reproduce
    el escenario de un verde (`item_siguiente`) restaurado de una
    sesión anterior (`playlist_publicidad.json`) apuntando a OTRO
    bloque: `disparar_bloque()`/`_reproducir_primero_del_bloque()`
    llamaban a `_asegurar_rojo_y_verde()` después de arrancar el
    primer ítem, pero ese helper por diseño NUNCA pisa un verde que
    "todavía parece válido" (sigue en el árbol, tiene ruta, sin
    vigencia vencida) — para no interferir con una elección manual del
    operador. El problema: un verde STALE de una sesión anterior (o
    dejado en otro bloque) sigue pareciendo válido aunque apunte a un
    bloque totalmente distinto del que se acaba de disparar. Con ese
    verde stale todavía puesto, `_avanzar()` — al terminar el PRIMER
    ítem del bloque recién disparado — evalúa el candidato (ese verde
    viejo), ve que `candidato.parent() is not self._bloque_automatico_actual`,
    y llama a `_finalizar_bloque_automatico()` de inmediato: exactamente
    "suena uno y salta a la 2". Corregido con un helper nuevo
    compartido, `_reproducir_primer_item_de_bloque()` (usado por
    `disparar_bloque()` Y `_reproducir_primero_del_bloque()`): después
    de arrancar el primer ítem, si el verde actual NO apunta dentro del
    bloque recién disparado, se recalcula a mano al próximo ítem válido
    DENTRO de ese bloque (o se limpia a `None` si no hay más) — antes
    de llamar a `_asegurar_rojo_y_verde()`. Confirmado con un test que
    primero reprodujo el bug tal cual en el código original (`git
    stash` sobre el fix, la aserción del verde stale falla exactamente
    como describe Santiago) y luego con el fix aplicado, el bloque
    completo (las 3 tandas) suena entero antes de pasar a Emisión.

    **b) Ítem Aleatorio en el Programador de Ventana 1 (pedido
    explícito: "agregar un ítem aleatorio de alguna categoría o
    sub-categoría, para darle dinamismo, por ejemplo en separadores...
    que sea buen aleatorio y variado")**: a diferencia de arrastrar un
    archivo puntual, este ítem nuevo (`ROL_ES_ALEATORIO`,
    `ROL_CATEGORIA_ALEATORIO`, `ROL_RECURSIVO_ALEATORIO` en
    `gui/styles.py`, color verde azulado `#16a085` para distinguirlo
    del azul de los Comandos) NO tiene una ruta fija — guarda el
    CAMINO de una categoría/subcategoría y recién resuelve un archivo
    al azar de ahí CADA VEZ que le toca sonar
    (`GestorPublicidad._resolver_item_aleatorio()`), nunca el mismo
    archivo elegido una sola vez para siempre. Reutiliza al 100% la
    infraestructura YA PREPARADA para esto en una ronda anterior
    ("preparación explícita para el Musicalizador Avanzado"):
    `VentanaExplorador.elegir_aleatorio_de_categoria()`/
    `listar_registros_de_categoria()`/`buscar_categoria_por_ruta()`, y
    el mismo mecanismo de no-repetir del Musicalizador
    (`config.settings.rutas_recientes_en_historial()`, lee el
    historial de reproducción PERSISTENTE) — "buen aleatorio y
    variado" se traduce en: nunca repite un archivo hasta agotar los
    demás de esa categoría, y esto sobrevive un reinicio porque lee el
    historial en disco, no un contador en memoria.
    - **Motor** (`core/playlist_manager.py`): `_item_valido()` acepta
      un ítem aleatorio como válido estructuralmente (igual que un
      Comando — no "suena" hasta que se resuelve). `_reproducir_item()`
      detecta `es_aleatorio(item)` y llama a
      `_reproducir_item_aleatorio()`: resuelve un registro real,
      arranca `motor.reproducir()` con SU análisis completo (recorte
      de silencio + nivelado, mismo patrón que toda la app) y llama a
      `registrar_reproduccion()` con la ruta REAL resuelta (no la del
      placeholder, que nunca tiene ruta propia — es lo que hace
      funcionar el no-repetir de una reproducción a la siguiente). Si
      la categoría está vacía, borrada, o no hay `_ventana_explorador`
      disponible, se saltea sin sonar nada y sigue con el próximo
      ítem real — mismo criterio "nunca romper la emisión" que ya
      rige toda la app.
    - **UI** (`gui/dialogo_insertar_item_aleatorio.py`, nuevo): elige
      categoría con el selector ya existente
      (`gui/dialogo_seleccionar_categoria.py`, mismo que usa el
      Musicalizador) + checkbox "Incluir subcategorías" (default
      activado). Botón nuevo "🎲 Ítem Aleatorio..." en el Programador,
      junto a los de Comando FMT/HTH. "Reemplazar" avisa que un ítem
      aleatorio no se reemplaza (quitar + agregar uno nuevo), mismo
      criterio ya usado para los Comandos.
    - **Persistencia end-to-end**: viaja por TODOS los caminos ya
      existentes sin duplicar lógica — `VentanaPublicidad.cargar_bloques()`
      (Ventana 1), `GestorPublicidad._guardar_estado_ahora()`/
      `_restaurar_desde_disco()` (playlist_publicidad.json),
      `VentanaProgramador._serializar_item()`/`_serializar_bloques()`/
      `_cargar_programacion_existente()` (programacion.json), y
      Copiar/Pegar del Programador (reusa `_serializar_item()`, mismo
      formato de datos que el resto).

    Probado con `test_verde_stale_al_disparar_bloque.py` (nuevo: 3
    tandas en el bloque vigente, un verde stale apuntando a OTRO
    bloque de una "sesión restaurada", confirma que el fix lo
    recalcula a T2 dentro del bloque disparado y que las 3 tandas
    suenan enteras antes de pasar a Emisión — y confirmado que este
    mismo test FALLA tal cual sobre el código sin el fix, vía `git
    stash`) + `test_arranque_bloque_completo.py` (nuevo, regresión del
    caso general sin verde stale) + `test_item_aleatorio_v1.py` (nuevo,
    12 verificaciones: creación del ítem, `_item_valido()`, resolución
    real con análisis completo, variedad entre 3 archivos en 6 vueltas
    sin repetir de entrada, categoría vacía se saltea sin sonar nada,
    persistencia ida y vuelta en playlist_publicidad.json, diálogo
    expone categoría+recursivo) + `test_item_aleatorio_programador.py`
    (nuevo, round-trip completo: insertar → guardar programación →
    vaciar el editor → cargar de nuevo → copiar/pegar → "Aplicar
    Ahora" en Ventana 1) + suite de regresión completa sin fallos
    nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
    **Sigue sin poder probarse con audio/VLC real**: falta que
    Santiago confirme con su radio real que al abrir la app ahora suena
    el bloque horario COMPLETO antes de pasar a Emisión (el caso real
    que reportó, con playlists restauradas de una sesión anterior), y
    que el ítem Aleatorio en un bloque de separadores realmente varía
    de archivo cada vez que le toca sonar.
46. ~~Refresco de clima en segundo plano (sin bloquear la emisión)~~ —
    Santiago confirmó que el Comando HTH ya lee bien el clima, pero
    notó "un breve silencio porque está leyendo los datos mediante la
    web del servidor del clima" y pidió que se lea "en off... guardado
    de antemano... que no interrumpa la emisión ni demore la carga,
    que trabaje de alguna manera silenciosa". Causa real: `core/
    clima_meteo.py:obtener_clima()` (única llamada de red de toda la
    app) usaba `urllib.request.urlopen()` SINCRÓNICO, disparado
    LAZY — recién en el momento exacto en que el Comando HTH necesita
    el dato — dentro de `core/hth.py:resolver_comando_hth()`, que a su
    vez se llama desde `GestorPublicidad._reproducir_comando_hth()` en
    el hilo principal (esta app nunca usó threading). Si la caché de
    20 minutos ya estaba vencida (o todavía vacía, poco después de
    abrir la app), esa consulta bloqueaba TODO el hilo principal —
    incluida la música ya sonando — hasta 6 segundos: el "breve
    silencio" que reportó Santiago.

    Corrección de fondo, no un ajuste de timeout: `core/clima_meteo.py`
    ganó `RefrescadorClima` (`QObject` con `QNetworkAccessManager` —
    HTTP asíncrono NATIVO de Qt, sin subprocess ni `QThread`, mismo
    espíritu "sin threading" del resto de la app) que se dispara SOLO,
    en segundo plano, cada `INTERVALO_REFRESCO_MINUTOS = 15` (bien por
    debajo de los 20 minutos de vigencia de la caché — en uso normal,
    el refresco de fondo renueva la caché mucho antes de que llegue a
    vencerse) más una vez al arrancar la app (diferido 3s, mismo
    criterio que EasyEffects/la búsqueda de actualización: no competir
    con el primer render). `obtener_clima()` — el ÚNICO punto que usa
    `core/hth.py` en el camino de reproducción — cambió de raíz: ya
    NUNCA sale a la red, es una simple lectura de la caché en memoria
    (instantánea); si no hay caché vigente (recién abierta la app,
    antes del primer refresco de fondo, o si el refresco dejó de
    andar por algún motivo), devuelve `None` de inmediato — `core/
    hth.py` ya trataba eso exactamente igual que un clip de voz
    faltante ("saltea todo el comando, sin sonar nada"), así que el
    comportamiento de "nunca deja el aire en un estado raro" se
    mantiene sin cambios, solo que ahora el camino de reproducción
    JAMÁS puede bloquearse esperando una respuesta de red. Un
    `_consultar_open_meteo_sincronico()` bloqueante queda disponible
    como respaldo (sin usarse por ahora) por si algún día hace falta
    un botón "probar ahora" en Configuración, donde una espera breve
    sí es aceptable (acción manual explícita del operador). Wireado
    en `MainWindow.__init__` (nuevo `_coordenadas_clima_actuales()`,
    vuelve a leer `config_general.json → clima` en cada refresco —
    un cambio de coordenadas en Configuración se aplica solo, sin
    reiniciar la app).

    Probado con `test_clima_refresco_async.py` (nuevo, 7
    verificaciones): `obtener_clima()` con caché vacía devuelve `None`
    de inmediato SIN tocar la red (confirmado interceptando
    `urllib.request.urlopen` para asegurar que jamás se llama), con
    caché vigente devuelve el valor cacheado, con caché vencida
    devuelve `None` (no sirve datos arbitrariamente viejos si el
    refresco de fondo dejó de andar); `RefrescadorClima.refrescar_ahora()`
    dispara el pedido asíncrono sin bloquear ni tocar la caché hasta
    que llega la respuesta (simulada con un reply falso, sin red real
    — la caché se actualiza recién al emitir `finished`), no superpone
    un segundo pedido mientras uno ya está en vuelo, un error de red
    no rompe nada (la caché anterior queda intacta), y `iniciar()`
    arranca el timer periódico con el intervalo correcto — + regresión
    de `test_hth_motor.py`/`test_hth_gui.py` (sin cambios, ambos
    inyectan `clima=`/`ahora=` directo, sin depender de la red) + suite
    de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py` — un cuarto fallo visto en
    una corrida puntual, `test_dinesat_play_fundido_stops.py`, resultó
    ser flaky/no reproducible: confirmado corriendo la MISMA suite dos
    veces más, pasó limpio las dos, sin relación con este cambio).
    **Sigue sin poder probarse contra la red real de Open-Meteo ni con
    audio real**: falta que Santiago confirme que el Comando HTH de
    TEMPERATURA/HUMEDAD ya no tiene ningún hueco de silencio al
    dispararse (el dato debería estar siempre "tibio" de antemano), y
    que cambiar la ciudad en Configuración → General sigue actualizando
    el clima sin reiniciar la app.
47. ~~Captura del error real de EasyEffects ("se abre pero se cierra")~~
    — Santiago probó la ronda de robustez de EasyEffects (sondeo en 2
    fases + reintento de preset, ver más arriba) y el problema
    persistió: "sigue fallando EasyEffects... se abre pero se cierra,
    no me deja activar el preset por medio del programa" — y pidió
    explícitamente si había forma de ver el error real que tira.

    **Causa de fondo, encontrada al auditar el lanzamiento**: hasta
    esta ronda, `core/easyeffects_control.py` lanzaba el proceso con
    `QProcess.startDetached()` — el mecanismo elegido a propósito en
    su momento porque deja a EasyEffects corriendo INDEPENDIENTE de
    esta app (sigue vivo aunque se cierre la radio). El problema real:
    `QProcess.startDetached()` **no tiene ninguna forma de capturar
    stdout/stderr del proceso hijo** — si EasyEffects crasheaba al
    arrancar (exactamente "se abre pero se cierra"), cualquier mensaje
    de error real del sistema (GTK, PipeWire, D-Bus, lo que sea) se
    perdía por completo, sin dejar NINGÚN rastro ni en pantalla ni en
    ningún archivo — invisible tanto para Santiago como para Claude
    Code, sin acceso a una terminal en el momento exacto del fallo.

    **Corrección**: reemplazado por `subprocess.Popen(...,
    start_new_session=True)` — mismo comportamiento "desacoplado,
    sobrevive al cierre de la radio" que ya tenía `startDetached()`
    (`start_new_session=True` es el equivalente de `setsid`), pero
    esta vez redirigiendo `stdout`/`stderr` a un archivo nuevo,
    `config/data/easyeffects_stdout.txt` (`RUTA_LOG_PROCESO`,
    `core/easyeffects_control.py`) — **sobrescrito en CADA intento de
    lanzamiento** (`open(..., "w")`, no append), así el contenido
    siempre refleja el ÚLTIMO intento, nunca datos viejos de una
    sesión anterior. Se redirige a un ARCHIVO, no a un `subprocess.PIPE`
    — a propósito, para evitar un riesgo real: el stdout/stderr de un
    proceso desacoplado de larga vida, si nadie lo lee, puede llenar el
    buffer de un pipe del sistema operativo y eventualmente bloquear al
    proceso hijo cuando escriba lo suficiente; un archivo en disco no
    tiene ese límite. El extra `.txt` de la extensión se eligió a
    propósito para que el patrón YA EXISTENTE en `.gitignore`
    (`config/data/*.txt`) lo cubra solo, sin tocar el archivo de
    ignorados.

    Dos funciones nuevas (`_lanzar_proceso_con_captura()`,
    `_cola_log_proceso()`) reemplazan el único lugar que llamaba
    `QProcess.startDetached()` directo — tanto en
    `asegurar_en_ejecucion()` (el camino con el sondeo de 2 fases:
    primero espera que el PROCESO exista vía `pgrep`, después que la
    CLI responda de verdad a un comando real, `--presets`) como en
    `abrir_ventana()`. Los DOS puntos de fallo del sondeo existente
    ahora adjuntan la cola del archivo capturado (últimas 20 líneas)
    tanto al `registrar_error()` del log de la app como al MENSAJE
    devuelto — que en la práctica termina mostrándose directo en el
    ítem deshabilitado del menú "🎚 FM" cuando algo sale mal, sin que
    Santiago necesite abrir ningún archivo a mano. El lanzamiento
    fire-and-forget al ARRANCAR la app
    (`MainWindow._iniciar_easyeffects_en_segundo_plano()`, que a
    propósito NO usa el sondeo completo para no demorar el arranque de
    la radio) también se cambió a `_lanzar_proceso_con_captura()` — así
    un crash silencioso ahí (antes de que el operador toque el menú
    "FM" siquiera) también queda capturado desde el primer instante.

    Probado con `test_easyeffects_captura_error.py` (nuevo, dedicado):
    un binario `easyeffects` FALSO que simula un crash realista al
    arrancar (escribe mensajes de estilo GTK/PipeWire a stderr y sale
    con código de error, sin llegar a quedar corriendo — `pgrep` falso
    siempre "no lo ve") confirma que (1) el stderr REAL del proceso
    queda capturado tal cual en `RUTA_LOG_PROCESO`, (2)
    `asegurar_en_ejecucion()` adjunta ese detalle al mensaje que
    devuelve, y (3) el mismo detalle queda también en
    `log_aplicacion.txt` — + regresión de los dos tests preexistentes
    de EasyEffects (`test_easyeffects_control.py`,
    `test_ronda_dnd_reanalisis_ee.py`, ambos sin cambios, confirmando
    que el reemplazo del mecanismo de lanzamiento no rompió ningún
    flujo ya probado: arranque oculto, listar/cargar presets, bypass,
    abrir ventana, ni el sondeo de 2 fases con reintentos) + suite de
    regresión completa sin fallos nuevos (mismos 3 fallos preexistentes
    de siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`). **Sigue sin poder probarse contra el
    EasyEffects real de Santiago** (el sandbox no lo tiene instalado,
    todo esto se probó contra un binario falso que imita un crash):
    falta que Santiago repita la prueba que le sigue fallando y, si
    vuelve a fallar, esta vez comparta el mensaje de error nuevo que
    debería aparecer en el menú "🎚 FM" (o el contenido de
    `config/data/easyeffects_stdout.txt` / `config/data/log_aplicacion.txt`)
    — recién con ese detalle real se va a poder saber SI el problema es
    PipeWire, D-Bus, GTK, permisos, u otra cosa, y encarar el arreglo
    de fondo específico para su instalación.
48. ~~Bug real encontrado con el log real de Santiago: `--presets` en
    su instalación no lista un preset por línea, así que `--load-preset`
    recibía basura~~ — pedido explícito: "ahí volvió a fallar, revisá
    el archivo de log y decime cuál es el problema". Santiago pegó el
    contenido de `easyeffects_stdout.txt` (solo un warning inofensivo
    de PipeWire, ningún crash) y de `log_aplicacion.txt`, que reveló la
    causa real de una:

    ```
    EasyEffects: arrancó oculto y respondió correctamente.
    EasyEffects: '--load-preset Perfiles de salida: Radio Tuyu,' falló,
    reintentando una vez...
    EasyEffects: '--load-preset Perfiles de salida: Radio Tuyu,' no
    respondió tras reintentar.
    ```

    EasyEffects arrancaba y respondía bien (la captura de la ronda
    anterior confirmó que NO era un crash) — el problema era que
    `listar_presets()` le estaba mandando a `--load-preset` el string
    **`"Perfiles de salida: Radio Tuyu,"`** en vez de simplemente
    **`"Radio Tuyu"`**. Causa de fondo: `listar_presets()` asumía que
    `--presets` imprime UN NOMBRE DE PRESET POR LÍNEA (suposición
    basada en la ayuda de la CLI, nunca confirmada contra la salida
    real) — pero en la instalación real de Santiago (EasyEffects 7.2.3,
    sistema en español) imprime UNA LÍNEA POR CATEGORÍA, con los
    nombres separados por coma:
    ```
    Perfiles de salida: Radio Tuyu,
    Perfiles de entrada:
    ```
    `listar_presets()` tomaba la línea ENTERA como si fuera el nombre
    de un preset — de ahí el string con el prefijo de categoría y la
    coma pegados, que obviamente no coincide con ningún preset real
    guardado, así que `--load-preset` fallaba siempre (ni un timeout ni
    un crash — un simple "no existe un preset con ese nombre").

    Corregido en `listar_presets()` (`core/easyeffects_control.py`)
    con un parseo tolerante al formato: por cada línea no vacía, si
    tiene `":"`, se toma solo lo de DESPUÉS de los dos puntos (sin
    importar el texto ni el idioma de la categoría — "Perfiles de
    salida"/"Output presets"/lo que sea) y se separa por comas,
    filtrando vacíos; si la línea NO tiene `":"`, se toma entera como
    un solo nombre (compatibilidad hacia atrás, por si alguna versión
    sí lista un nombre por línea sin categorías — es el formato que ya
    usaban los tests/binarios falsos preexistentes, así que sigue
    funcionando sin tocarlos). `preset_activo()` no se tocó — usa
    `--active-preset <categoría>`, una consulta de UNA sola categoría
    a la vez, sin ambigüedad que resolver con un prefijo, y el log no
    mostró ningún síntoma de que tuviera el mismo problema.

    Probado con `test_easyeffects_parseo_presets.py` (nuevo, 6
    verificaciones): el formato REAL exacto que mandó Santiago (un
    preset de salida, ninguno de entrada) parsea a `["Radio Tuyu"]`;
    varios presets en la misma categoría separados por coma; el mismo
    parseo funciona igual con el encabezado en inglés ("Output
    presets:"); el formato viejo sin categorías (un nombre por línea,
    sin `":"`) sigue funcionando igual que antes; sin presets
    guardados en ninguna categoría da lista vacía (no basura tipo
    `["", ""]`); y de punta a punta, `cargar_preset("Radio Tuyu")` con
    el nombre ya limpio le manda a la CLI exactamente
    `('--load-preset', 'Radio Tuyu')`, confirmado interceptando el
    comando real — + regresión de `test_easyeffects_control.py`,
    `test_ronda_dnd_reanalisis_ee.py` y
    `test_easyeffects_captura_error.py` (los tres sin cambios, sin
    fallos nuevos) + suite de regresión completa sin fallos nuevos
    (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
    **Sigue sin poder confirmarse contra el EasyEffects real de
    Santiago** (el sandbox no lo tiene instalado, el formato real se
    reconstruyó a partir del log que él pegó, no de una instalación
    real corriendo acá): falta que Santiago vuelva a intentar cambiar
    de preset desde el menú "🎚 FM" y confirme que ahora sí se aplica
    en el aire — si el menú le muestra "Radio Tuyu" (sin el prefijo de
    categoría) como opción, es la señal de que el parseo ya está
    limpio.
49. ~~"Abrir EasyEffects (Opciones Avanzadas)" tampoco abría la
    ventana~~ — Santiago probó el fix del parseo de presets (ronda
    48, ya sin error) y reportó dos cosas más de una: "no se escucha
    que se aplique el preset" (lo probó comparando contra abrir
    EasyEffects a mano desde el menú de su PC) y "tampoco abre desde
    FM EasyEffects (Opciones Avanzadas)".

    **b) Botón "Abrir EasyEffects" corregido**: la suposición original
    (documentada como incierta desde que se escribió, nunca
    confirmada) era que invocar el binario SIN `--hide-window` sobre
    una instancia YA corriendo oculta la "destaparía" sola, por
    comportamiento de reactivación de GApplication. Santiago confirmó
    que eso no pasa en la práctica. Como no hay un flag `--show-window`
    documentado en su `--help` real, `abrir_ventana()`
    (`core/easyeffects_control.py`) se reescribió para no depender de
    ese comportamiento no confirmado: si EasyEffects está corriendo,
    se le manda `--quit` (SÍ confirmado en el `--help` de Santiago) y
    se espera a que el proceso termine de verdad (sondeado por
    `pgrep`, mismo mecanismo de siempre); recién ahí se relanza una
    instancia FRESCA sin `--hide-window` — un arranque nuevo sin ese
    flag muestra su ventana por comportamiento normal de cualquier app
    GTK, sin depender de si la reactivación remota la destapa. Si no
    estaba corriendo, no hace falta el paso de `--quit`, va directo al
    relanzamiento. Mismo mecanismo de captura de stderr/stdout de la
    ronda 47 (`_lanzar_proceso_con_captura()`) sigue aplicando acá, así
    que si el relanzamiento fallara también quedaría diagnosticable.

    **a) "No se escucha que se aplique el preset" — NO es un bug de
    esta app, es (casi con certeza) ruteo de audio en PipeWire, sin
    poder confirmarlo sin datos de la instalación real de Santiago**:
    el comando `--load-preset` ahora tiene éxito sin error (confirmado
    por el propio Santiago: "ahora no arroja error"), lo cual descarta
    que sea el mismo bug de parseo de la ronda 48 — EasyEffects SÍ
    recibe y acepta el cambio de preset. Que el cambio no se escuche
    aunque el comando funcione es el síntoma típico de que el audio de
    esta app (via libVLC) no está pasando físicamente por el nodo de
    procesamiento de EasyEffects en PipeWire — EasyEffects solo aplica
    efectos al audio que está efectivamente ruteado a través de su
    sink/nodo virtual, no a todo el audio del sistema por arte de
    magia. No se tocó código por esto — no hay forma de diagnosticar
    ruteo de PipeWire sin ver la instalación real, y modificar a
    ciegas el módulo de salida de audio del motor (`core/audio_engine.py`,
    que hoy deja que libVLC autodetecte el módulo de audio) sin saber
    la causa real sería puro tanteo. Pendiente que Santiago confirme
    dos datos concretos para poder seguir: (1) qué dispositivo de
    salida tiene elegido en Configuración → Audio → Master — si es
    "default"/el que trae por defecto, o si eligió un dispositivo
    específico por nombre; (2) con la radio reproduciendo, abrir
    EasyEffects a mano (como ya lo hace) y mirar la pestaña que lista
    las apps/streams conectados (en inglés suele llamarse "Pipe
    Manager" o similar) — si ahí NO aparece esta app/su proceso
    conectado al pipeline de Salida, confirma que el audio nunca pasa
    por EasyEffects sin importar qué preset esté cargado, y el ajuste
    necesario sería de ruteo de PipeWire (o de qué dispositivo elige
    esta app), no de la lógica de `--load-preset`.

    Probado con `test_easyeffects_abrir_ventana.py` (nuevo, dedicado):
    contra un binario falso que simula el ciclo completo (corriendo
    oculto -> `--quit` -> deja de estar "corriendo" -> relanzado sin
    flags -> vuelve a aparecer, esta vez "con ventana"), confirma que
    la PRIMERA llamada es `--quit`, que hay una invocación sin flags
    DESPUÉS de esa (nunca antes), que `abrir_ventana()` devuelve éxito
    al final, y que si NO había nada corriendo previamente no se manda
    ningún `--quit` de más (va directo al relanzamiento) — + ajuste al
    binario falso de `test_easyeffects_control.py` (agregado el manejo
    de `--quit` y de la invocación sin flags, que antes no existían en
    ese fake) para que su assertion preexistente de `abrir_ventana()`
    siga reflejando el comportamiento real + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py` — un cuarto fallo visto en esta corrida puntual,
    `test_dinesat_play_fundido_stops.py`, ya está documentado desde la
    ronda 46 como flaky/no reproducible por timing de garbage
    collection de Qt; confirmado de nuevo corriéndolo 3 veces más
    aislado, pasó limpio en 2 de esas 3, sin relación con este cambio).
    **Sigue sin poder probarse contra el EasyEffects real de Santiago**:
    falta que confirme que "Abrir EasyEffects" ahora sí muestra la
    ventana, y que comparta los dos datos pedidos arriba (dispositivo
    de audio configurado + si esta app aparece conectada en el Pipe
    Manager de EasyEffects) para poder avanzar con el problema del
    preset que no se escucha.
50. ~~LA CAUSA DE FONDO del preset que no se escuchaba: `--hide-window`
    nunca arma el pipeline de audio en la instalación real de
    Santiago~~ — investigación conjunta con Santiago en vivo, sesión
    larga de diagnóstico con datos reales de su sistema (nunca
    reproducible en el sandbox, que no tiene PipeWire/EasyEffects):

    **El camino hasta la causa real**: descartado el dispositivo de
    salida (probó "default" y el explícito, sin cambio) y descartado
    un problema de timing (Stop+Play tras el arranque tampoco cambió
    nada, ni el Bypass del menú FM) — se le pidió el ruteo REAL de
    PipeWire con `pactl`/`pw-link -l` en vez de confiar en lo que
    mostraba la interfaz. `pactl list sink-inputs` reveló que el
    stream de VLC estaba conectado DIRECTO al sink físico
    (`alsa_output.pci-...`), sin ningún nodo de EasyEffects en el
    medio — a pesar de que EasyEffects mostraba el reproductor como
    "Activar" tildado. La prueba decisiva fue comparar `pw-link -l`
    CON y SIN la ventana de EasyEffects abierta: **sin ventana
    (incluso lanzada con `--hide-window`), NUNCA existe el nodo
    `easyeffects_sink` ni la cadena de plugins — con la ventana
    genuinamente abierta, aparece la cadena completa y funciona
    perfecto** (`VLC → easyeffects_sink → autogain → loudness →
    crystalizer → compressor → limiter → stereo_tools → spectrum →
    output_level → hardware`). Santiago confirmó además que
    MINIMIZAR (no cerrar) la ventana ya abierta mantiene la cadena
    intacta — solo cerrarla con la X la destruye. Conclusión: en su
    instalación, `--hide-window` JAMÁS llega a construir el pipeline
    de PipeWire (documentado como asumido, nunca antes verificado, en
    las rondas 37/40/43) — el pipeline se arma SOLO cuando la ventana
    existe de verdad (mapeada por el gestor de ventanas), aunque sea
    un instante, y sobrevive minimizada.

    **Rediseño de fondo en `core/easyeffects_control.py`**: reemplazado
    `--hide-window` por completo (la constante `FLAG_OCULTAR_VENTANA`
    queda definida por si una versión futura lo arregla, pero ya no se
    usa) por control de ventana con **`wmctrl`** (herramienta estándar
    de X11/EWMH, ajena a EasyEffects — Santiago confirmó tenerla
    instalada) — arranca con la ventana REAL y la oculta por software
    apenas aparece: `wmctrl -b add,hidden,skip_taskbar` la minimiza Y
    le pide al escritorio que no le muestre ícono en la barra de
    tareas (pedido explícito de Santiago, "que pueda verlo y no
    verlo... no quiero que se vea minimizado en la barra de tareas");
    `wmctrl -b remove,hidden,remove,skip_taskbar` + `-a` la restaura y
    le da foco. Dos versiones del ocultamiento, mismo criterio ya
    usado en el resto del proyecto para separar caminos bloqueantes de
    no bloqueantes:
    - `ocultar_ventana_bloqueante()` — poll con `time.sleep()`, para
      usar SOLO desde un camino ya bloqueante/interactivo
      (`asegurar_en_ejecucion()`, disparado por el operador desde el
      menú FM, que ya muestra un cursor de espera).
    - `ocultar_ventana_diferido()` — la MISMA lógica pero encadenada
      vía `QTimer.singleShot` en vez de `time.sleep()`, exclusiva del
      arranque fire-and-forget de `MainWindow` — la radio nunca debe
      demorarse ni un instante esperando que la ventana de EasyEffects
      llegue a existir.
    Sin `wmctrl` instalado, degrada limpio (deja la ventana visible,
    avisa una vez en el log con la instrucción de instalación) — mismo
    criterio de tolerancia a dependencias faltantes de siempre.

    **`asegurar_en_ejecucion()`** ya no manda `--hide-window` en
    ningún caso — si hay que lanzar de cero, arranca sin flags y
    oculta la ventana recién construido el pipeline (`ocultar_ventana_bloqueante()`
    al final, no antes — antes de eso la ventana todavía no existe).
    Si YA estaba corriendo (la lanzó esta misma app antes, o el
    operador la abrió a mano), esta función **ya no le toca la
    visibilidad** — decisión de diseño explícita: mostrar/ocultar a
    partir de ahí es una acción DELIBERADA del operador, nunca un
    efecto secundario silencioso de simplemente cambiar un preset
    desde el menú FM.

    **`abrir_ventana()` simplificado** (ya no necesita el ciclo
    `--quit` + relanzar de la ronda 49 como camino principal): si
    EasyEffects ya está corriendo, alcanza con RESTAURAR la ventana
    existente (`wmctrl -b remove,hidden...` + `-a`) — mucho más
    liviano que reiniciar el proceso entero. El ciclo `--quit` +
    relanzar de la ronda anterior queda como RESPALDO, para cuando
    `wmctrl` no está disponible o por algún motivo no se encuentra la
    ventana.

    **Nuevo, pedido explícito ("que pueda verlo y no verlo desde el
    programa nuestro")**: función pública `ocultar_ventana()` +
    ítem de menú nuevo **"Ocultar ventana de EasyEffects"** (junto a
    "Abrir EasyEffects (edición avanzada)...", `gui/main_window.py`) —
    el operador ahora puede mostrar Y volver a ocultar la ventana real
    desde el propio programa, sin cerrar el proceso (el pipeline de
    audio sigue andando durante todo el ciclo mostrar/ocultar, solo
    cambia si la ventana se ve o no).

    Probado con `test_easyeffects_ocultar_mostrar_wmctrl.py` (nuevo,
    dedicado — con binarios falsos de `easyeffects`, `pgrep` Y
    `wmctrl` simulando el ciclo completo, algo que ningún test anterior
    había cubierto): `asegurar_en_ejecucion()` de punta a punta arranca
    con ventana real y queda oculta sola al final (nunca manda
    `--hide-window`); `abrir_ventana()` restaura la ventana existente
    SIN pasar por el ciclo quit+relanzar; `ocultar_ventana()` nuevo
    vuelve a ocultarla; `ocultar_ventana_diferido()` oculta de
    inmediato si la ventana ya existe, NO bloquea en el primer llamado
    si todavía no existe, y el reintento vía `QTimer` la encuentra y
    oculta apenas aparece (simulado haciendo "aparecer" la ventana con
    un `QTimer.singleShot` propio del test, bombeando el event loop
    real con `app.processEvents()` — no un mock); degradación limpia
    confirmada sin `wmctrl` en el PATH (mensaje explícito, sin
    excepción) — + actualización de 2 tests preexistentes
    (`test_easyeffects_control.py`, que verificaba literalmente el uso
    de `--hide-window`, ahora verifica lo opuesto; `test_ronda_dnd_reanalisis_ee.py`,
    cuyo fake de `easyeffects` no manejaba una invocación sin flags) +
    regresión de `test_easyeffects_captura_error.py`,
    `test_easyeffects_abrir_ventana.py` y
    `test_easyeffects_parseo_presets.py` sin cambios necesarios + suite
    de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder
    confirmarse contra el EasyEffects/wmctrl/PipeWire reales de
    Santiago** (el sandbox no tiene ninguno de los tres): falta que
    confirme (1) que al abrir la radio, EasyEffects arranca con
    efectos realmente activos desde el primer instante (`pw-link -l`
    debería mostrar la cadena completa poco después del arranque) y
    sin dejar ningún ícono en la barra de tareas, (2) que "Abrir
    EasyEffects"/"Ocultar ventana de EasyEffects" alternan mostrar/
    ocultar la ventana real sin reiniciar el proceso ni perder los
    efectos, y (3) que con esto YA resuelto (el pipeline realmente
    armado), el cambio de preset desde el menú FM finalmente SÍ se
    escucha en el aire — que era el problema original de esta
    investigación.
51. ~~Fade-in "declick" configurable en Ventana 1 (evitar el click al
    arrancar cada ítem)~~ — pedido explícito: "hay un titubeo, un
    mínimo tartamudeo al inicio de los ítems en la ventana 1, incluso
    un clip de sonido al inicio, ¿lo puedo silenciar con un leve fade
    de inicio en configuraciones?". Este pedido llegó justo después de
    la ronda anterior (armar el pipeline real de EasyEffects) —
    consistente con la causa más probable: un salto INSTANTÁNEO a
    volumen final justo al arrancar cada ítem (comportamiento de
    siempre de `MotorAudio.reproducir()`, nunca antes había una rampa
    de entrada) es mucho más audible ahora que el audio pasa por una
    cadena de dinámica real (autogain/compressor/limiter de
    EasyEffects) — un escalón de volumen instantáneo es un disparador
    clásico de "pumping"/click en ese tipo de plugins.

    **Aclaración importante, para no confundir con una ronda
    anterior**: esto NO es volver a poner el fade-in MUSICAL que se
    sacó a propósito ("que los temas suenen más enganchados, sin
    fade-in", varias rondas atrás) — esa decisión sigue vigente sin
    cambios (crossfade de Ventana 2, botón verde con fundido). Acá la
    rampa es de unos pocos MILISEGUNDOS (60ms por defecto) — muy por
    debajo del umbral en el que un oído humano percibe algo como "un
    fundido" (~100-150ms) — solo alcanza para evitar la discontinuidad
    digital, no para que se note como una entrada gradual.

    **Implementación**: `MotorAudio.reproducir()`
    (`core/audio_engine.py`) ganó un parámetro nuevo,
    `duracion_declick_ms: int = 0` — en vez del salto directo de
    siempre (`set_volumen(volumen_final)`), si es mayor a 0 arranca en
    `set_volumen(0)` y sube con el mismo mecanismo de rampa ya
    existente (`fade_volumen_a(volumen_final, duracion_declick_ms /
    1000.0)`) — reusa toda la infraestructura de volumen "deseado"
    de rondas anteriores (la re-aplicación diferida a los 150ms sigue
    funcionando sin cambios, solo reafirma el valor interpolado que la
    rampa ya está sosteniendo en ese instante). Con `duracion_declick_ms=0`
    (el valor por defecto de `MotorAudio.reproducir()` en sí, para no
    afectar ningún llamador que no lo pase explícitamente) el
    comportamiento es IDÉNTICO a como era antes de esta ronda.

    `GestorPublicidad` (`core/playlist_manager.py`) ganó
    `duracion_fade_in_declick_ms: int = 60` en el constructor, guardado
    como atributo, y pasado como `duracion_declick_ms=` en los DOS
    lugares donde arranca un ítem real de Ventana 1: `_reproducir_item()`
    (tanda normal) y `_reproducir_item_aleatorio()` (ítem Aleatorio,
    ronda 39) — a propósito, scope acotado a Ventana 1 por ahora
    (mismo criterio ya usado para `duracion_fade_out_v1_ms`, que
    tampoco toca Ventana 2); si Santiago confirma que el mismo
    artefacto se nota en Ventana 2/Auxiliar, es la misma técnica,
    fácil de extender a `GestorPlaylist` en una ronda futura. Nueva
    clave de configuración `reproduccion.duracion_fade_in_declick_v1_ms`
    (default 60, en `config/settings.py` — `0` = desactivado, salto
    directo como toda la vida), con spin box nuevo en Configuración →
    Reproducción y Automatización ("Fade IN (anti-click) al arrancar
    ítems de Ventana 1"), rango 0-500ms, junto al ya existente "Fade
    OUT entre tandas de Ventana 1". Wireado en `MainWindow` tanto en la
    construcción de `GestorPublicidad` como en
    `_aplicar_configuracion_en_vivo()` (mismo patrón exacto que
    `duracion_fade_out_v1_ms` — cambiar el valor en Configuración se
    aplica sin reiniciar la app).

    Probado con `test_fade_in_declick_v1.py` (nuevo, dedicado, 15
    verificaciones): con un player VLC falso (mismo patrón ya usado en
    `test_volumen_robusto.py`), `duracion_declick_ms=0` confirma el
    comportamiento IDÉNTICO de siempre (salto directo, sin ningún timer
    de fade); `duracion_declick_ms=200` confirma que arranca en
    silencio absoluto (volumen deseado 0) justo después de
    `reproducir()` y que, bombeando el event loop real, la rampa
    termina exactamente en el volumen final — incluido el caso con
    `ganancia_db` (el techo de la rampa es el volumen YA nivelado, no
    el volumen_base crudo); el valor por defecto en
    `CONFIG_POR_DEFECTO` es 60ms y un `config_general.json` VIEJO (sin
    la clave nueva, de una instalación anterior a esta ronda) se
    autocompleta solo al fusionar, sin `KeyError`; `GestorPublicidad`
    se construye con el valor de config y lo pasa correctamente tanto
    para un ítem normal como para uno Aleatorio (confirmado
    interceptando `motor.reproducir` y mirando los kwargs reales);
    cambiar el valor en Configuración se aplica en vivo sin reiniciar;
    el spin box nuevo carga y guarda el valor correctamente — + suite
    de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder
    confirmarse con audio/EasyEffects reales** (como todo lo que toca
    `core/audio_engine.py` — el sandbox no tiene libVLC): falta que
    Santiago confirme que el titubeo/click al inicio de los ítems de
    Ventana 1 desaparece con el valor por defecto (60ms), y que ese
    valor le alcanza o prefiere ajustarlo desde Configuración (0 lo
    desactiva por completo, volviendo al comportamiento de siempre).
52. ~~Reemplazo de EasyEffects por el módulo nativo `filter-chain` de
    PipeWire (en curso — primera mitad: remoción de EasyEffects)~~ —
    pedido explícito de Santiago tras la ronda anterior: "EasyEffects
    tampoco es que se solucionó, la ventana sigue apareciendo de
    fondo. Vayamos con la opción [PipeWire nativo], que además es
    liviana para el sistema... Desinstalemos EasyEffects." Cinco
    rondas (37, 40, 43-51) de trabajo sobre la integración con
    EasyEffects (arranque oculto, sondeo de 2 fases, captura de
    stderr/stdout, parseo de presets, ciclo quit+relanzar, control de
    ventana con wmctrl) terminaron en la misma conclusión: EasyEffects
    necesita una ventana real y VISIBLE (aunque sea un instante) para
    armar su pipeline de audio, y eso siempre iba a dejar algún rastro
    (aparecer un instante, quedar en la barra de tareas según el
    gestor de ventanas) que Santiago no terminaba de aceptar — la
    alternativa que eligió, el módulo `libpipewire-module-filter-chain`
    de PipeWire, corre DENTRO del propio servidor de audio, sin ningún
    proceso ni ventana por separado, así que el problema de fondo
    (¿cómo ocultar una ventana ajena?) directamente deja de existir.

    **Primera mitad de esta ronda — remoción completa de EasyEffects**
    (la segunda mitad, escribir y afinar el `filter-chain` con
    plugins Calf para un preset de FM, queda pendiente: necesita los
    nombres REALES de los puertos LV2 de la instalación de Santiago
    —`lv2ls`/`lv2info`— antes de escribir la configuración, para no
    adivinar un nombre de control y que un parámetro quede sin
    aplicarse en silencio; se le pidieron esos comandos y se sigue en
    la próxima ronda con su resultado):
    - `core/easyeffects_control.py` eliminado por completo (todo el
      módulo — lanzamiento, sondeo de 2 fases, parseo de presets,
      wmctrl, captura de stderr/stdout).
    - `gui/main_window.py`: sacado el botón "🎚 FM" del toolbar, el
      menú completo (presets/bypass/abrir/ocultar ventana), los 6
      métodos manejadores (`_iniciar_easyeffects_en_segundo_plano`,
      `_poblar_menu_easyeffects`, `_cambiar_preset_easyeffects`,
      `_alternar_bypass_easyeffects`, `_abrir_ventana_easyeffects`,
      `_ocultar_ventana_easyeffects`), el `import easyeffects_control`
      y el llamado de arranque en `__init__` — de paso, `QToolButton`/
      `QMenu`/`QActionGroup` quedaron sin ningún otro uso en el
      archivo y se sacaron también de los imports (ya no hacía falta
      un `# noqa` ni dejarlos "por las dudas": nada más en el archivo
      los necesitaba).
    - 5 archivos de test dedicados a EasyEffects eliminados
      (`test_easyeffects_control.py`, `test_easyeffects_captura_error.py`,
      `test_easyeffects_abrir_ventana.py`, `test_easyeffects_parseo_presets.py`,
      `test_easyeffects_ocultar_mostrar_wmctrl.py`) — probaban un
      módulo que ya no existe. `test_ronda_dnd_reanalisis_ee.py`
      (compartía archivo con drag&drop V1→Auxiliar y "Reanalizar
      biblioteca", features que SÍ siguen vigentes) se editó para
      sacar solo su sección 3 (el bloque de EasyEffects), sin tocar
      las otras dos.
    - `duracion_fade_in_declick_v1_ms` (ronda anterior) se queda TAL
      CUAL — el motivo original (evitar que un salto instantáneo de
      volumen "pumpee" un compresor/limiter aguas abajo) sigue
      aplicando igual, o más, con el filter-chain de PipeWire que lo
      reemplace.

    Probado: suite de regresión completa sin fallos nuevos (mismos 3
    fallos preexistentes de siempre — `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py` — más 2 fallos dependientes
    de la hora real del sistema, `test_automatico_dispara_al_activar.py`
    y `test_play_bloque_y_hora.py`, que la corrida cayó cerca de
    medianoche; confirmado con `git stash` que fallan IDÉNTICO contra
    el código sin este cambio, ya documentados como flaky desde rondas
    anteriores) + smoke test de arranque limpio. **Pendiente antes de
    seguir con la segunda mitad**: que Santiago corra en su máquina
    real (esta app NO puede desinstalar/instalar paquetes ni ejecutar
    nada en su PC — todo lo que sigue son comandos para que él corra):
    ```bash
    sudo apt remove --purge easyeffects
    sudo apt install calf-plugins
    lv2ls | grep -i calf
    lv2info http://calf.sourceforge.net/plugins/Compressor
    lv2info http://calf.sourceforge.net/plugins/Limiter
    lv2info http://calf.sourceforge.net/plugins/StereoTools
    ```
    y pegue el resultado — con eso se escribe el `filter-chain.conf`
    con los nombres de control CONFIRMADOS (no adivinados) para un
    preset de FM: separación estéreo, compresión que nivele temas
    silenciosos contra temas con picos altos al mismo rango, limitador
    contra saturación, y sonoridad/escala sin distorsión — pedido
    textual de Santiago para la segunda mitad de esta ronda.

    **Segunda mitad — el archivo de configuración
    (`assets/pipewire-fm-processing.conf`, nuevo)**: Santiago
    desinstaló EasyEffects e instaló `calf-plugins` (`lv2ls`/`lv2info`
    no venían con ese paquete — hubo que pedirle además `lilv-utils`,
    que trae esas herramientas de introspección). Con la salida REAL
    de `lv2info` (nombres de puerto y rangos confirmados, filtrada a
    `Symbol/Minimum/Maximum/Default/Type` para que no fuera tan larga
    de pegar) se armó la cadena `libpipewire-module-filter-chain` con
    tres plugins de Calf en serie:
    - **StereoTools** (ancho estéreo): `slev = 1.15` (15% más ancho
      que el original) — a propósito MODERADO, un ancho mayor arriesga
      cancelación de fase y problemas de compatibilidad mono, algo
      sensible en una transmisión FM real. `stereo_base` y el resto de
      los controles de fase/balance quedan neutros (0), sin activar
      ningún modo de ensanchado más agresivo.
    - **Compressor** (nivelado — pedido textual: "que el tema más
      silencioso... y otro con picos altos, se escuche parejo... al
      mismo rango"): `threshold = 0.1` (~-20dB, en escala LINEAL —
      importante: los controles de ganancia de Calf son lineales, no
      dB, aunque su interfaz gráfica los muestre en dB) para que
      agarre la MAYORÍA del contenido, no solo picos ocasionales —
      `ratio = 3.5`, `attack = 15ms`, `release = 200ms` (lo
      suficientemente lento para no sonar "bombeado"), `detection = 1`
      (RMS, más musical que peak), `stereo_link = 1` (los dos canales
      se reducen IGUAL, para que la imagen estéreo no se corra al
      comprimir — explícito porque el default de Calf es 0/desvinculado),
      `makeup = 2.0` (~+6dB lineal, moderado a propósito para no
      forzar de más al limitador de después).
    - **Limiter** (seguridad — pedido textual: "por si hay algún
      sobre salto de saturación"): `limit = 0.933` (~-0.6dB lineal,
      techo con margen contra picos entre muestras/inter-sample
      peaks — nunca deja pasar saturación real), `asc = 1` (Automatic
      Sustain Control, reduce el bombeo audible en pasajes fuertes
      sostenidos), `oversampling = 2` (mejor calidad que el default
      sin llegar al máximo — equilibrio pensado para el hardware
      modesto de Santiago, Celeron N2820), `auto_level = 1` (auto-
      compensación de nivel, ya viene así por defecto en Calf).
    `capture.props` arma un sink virtual nuevo, `fm_processing_input`
    — ESE es el que hay que elegir como salida en Configuración →
    Audio → Salida Master del programa una vez confirmado que anda.
    `playback.props` conecta la salida ya procesada a
    `@DEFAULT_SINK@` (el hardware real).

    **Limitación reconocida de esta ronda, explicada a Santiago**: no
    se pudo verificar la sintaxis exacta del archivo (la estructura
    general de `context.modules`/`filter.graph`/`capture.props`)
    contra la documentación oficial en vivo — el acceso saliente de
    este entorno a `docs.pipewire.org`/`wiki.archlinux.org` está
    bloqueado por política (403 del proxy de la organización, no un
    error de la app). Los nombres de PLUGINS y de CONTROLES sí están
    100% confirmados contra la instalación real de Santiago
    (`lv2info`), pero la sintaxis general del archivo es la mejor
    reconstrucción posible a partir de fragmentos de documentación
    indirectos (resultados de búsqueda) — no una copia verificada de
    un ejemplo oficial. Por eso el pedido explícito a Santiago es
    probarlo primero como proceso SUELTO en primer plano
    (`pipewire -c assets/pipewire-fm-processing.conf`, matable con
    Ctrl+C sin tocar su audio real en curso) antes de ponerlo en
    autoarranque — si hay un error de sintaxis, PipeWire lo va a
    imprimir ahí mismo en texto plano, sin romper nada de lo que ya
    está sonando, y se corrige con ese detalle real (mismo patrón
    colaborativo "ground truth de tu máquina real" que ya funcionó
    bien durante toda la investigación de EasyEffects).

    No probado — no hay forma de hacerlo en el sandbox (no tiene
    PipeWire real, ni Calf, ni una tarjeta de sonido): falta que
    Santiago corra el comando de prueba en primer plano, confirme que
    no tira error de sintaxis, verifique con `pactl list sinks short |
    grep fm_processing` que aparecen los nodos nuevos, elija
    "fm_processing_input" como salida en Configuración → Audio del
    programa, y confirme cómo suena — recién ahí, si todo anda, mover
    el archivo a `~/.config/pipewire/pipewire.conf.d/` para que
    arranque solo con el sistema (sin pasar por esta app en absoluto,
    a diferencia de EasyEffects — el filter-chain de PipeWire es
    completamente independiente del programa de la radio).

    **Actualización en vivo, probando con Santiago en su PC secundaria
    (no la de aire)**: `pipewire -c archivo.conf` (arrancar un
    servidor nuevo desde cero) dio error — es la herramienta
    equivocada, no un problema del archivo; un supuesto binario
    standalone `pipewire-filter-chain` tampoco existe en su Debian.
    El camino real que SÍ funcionó: copiar el archivo a
    `~/.config/pipewire/pipewire.conf.d/` y
    `systemctl --user restart pipewire pipewire-pulse wireplumber` —
    el sink `fm_processing_input` apareció sin errores
    (`pactl list sinks short`).

    **Primer diagnóstico, descartado — fue un artefacto de `grep`, no
    un bug real**: al no escucharse nada, un primer `pw-link -l |
    grep -iE "fm_proc|alsa_output"` pareció mostrar la salida
    conectada a SÍ MISMA (`fm_processing_input:playback_FL |->
    fm_processing_input:playback_FL`) — pero ese filtro corta la línea
    de ORIGEN de cada conexión si no contiene el patrón buscado,
    mostrando solo el DESTINO y dando la falsa impresión de un bucle.
    Repitiendo con contexto (`grep -B1`) se vio la imagen real: el
    audio de VLC SÍ entraba bien a `fm_processing_input` — el problema
    real estaba del otro lado, en que la salida ya procesada nunca
    aparecía conectada a NADA (ni a `alsa_output`, ni a ningún otro
    lado), ni siquiera con `target.object` ya apuntando al dispositivo
    real. **Regla para el futuro**: un `grep` que filtra `pw-link -l`
    por un patrón puede cortar la línea de contexto que prueba o
    descarta un diagnóstico — repetir siempre con `-B1` (o sin filtro)
    antes de confiar en una lectura así.

    **Causa real, confirmada contra la documentación oficial (`Stream/
    Output/Audio is a playback stream`, vía búsqueda — esta vez sí se
    pudo verificar)**: `playback.props` tenía `media.class =
    "Audio/Source"` — la clase EQUIVOCADA. "Audio/Source" es para algo
    de lo que OTROS clientes capturan (como un micrófono virtual);
    nunca se conecta solo a ningún lado, sin importar qué diga
    `target.object`. La clase correcta para un stream que debe
    empujar su audio HACIA un dispositivo de salida, igual que
    cualquier reproductor común, es `Stream/Output/Audio`. Corregido
    en `assets/pipewire-fm-processing.conf` — con la clase correcta,
    `target.object` (ya apuntando al nombre real del hardware, no a
    `@DEFAULT_SINK@`, sigue siendo la elección correcta para no
    depender de cuál sea "el default" del sistema en cualquier
    momento) debería conectarse solo, igual que lo haría VLC.

    **CONFIRMADO CON AUDIO REAL — el fix de `media.class` fue la causa
    de fondo**: Santiago recargó el archivo corregido y confirmó "ahi
    se escucha!!!" — la cadena StereoTools→Compressor→Limiter ya está
    procesando de verdad el audio de la radio en su PC de prueba
    (destinada a terminar siendo la de aire, ver el pedido original de
    esta ronda). Pendiente de una prueba más específica: confirmar que
    los plugins realmente están APLICANDO efecto (no un passthrough
    silencioso) — se le indicó un test de oído con un parámetro
    extremo (bajar `limit` del Limiter a `0.05` momentáneamente, volver
    a `0.933` después) más verificación visual opcional con `qpwgraph`
    (`sudo apt install qpwgraph`) y `pw-top`. Falta la confirmación de
    ese test puntual, y repetir el despliegue completo (desinstalar
    EasyEffects + instalar calf-plugins + copiar el `.conf` a
    `~/.config/pipewire/pipewire.conf.d/`) en la PC real de aire si es
    distinta de la que se usó para probar.

53. ~~Descargador de YouTube integrado en Ventana 3 (video suelto o
    playlist completa, MP3 sin silencios, categoría de aterrizaje
    "Descargas YT")~~ — pedido explícito, 9 puntos, con el criterio
    de diseño de Santiago repetido dos veces ("esto sí tipo 'módulo'
    así no rompemos mucho el programa original") — llega justo cuando
    la app queda lista para la importación real y definitiva de
    música y programación ("tenemos casi casi todo listo").

    **`core/descargador_youtube.py` (nuevo, sin Qt — mismo espíritu
    que `core/actualizador.py`/`core/clima_meteo.py`)**: usa la
    librería `yt-dlp` (pip, agregada a `requirements.txt`) en vez de
    un binario de sistema aparte — se eligió la librería Python
    directa (no CLI + parseo de su salida) porque da acceso
    estructurado a metadata (título, si es playlist, título de la
    playlist) sin tener que interpretar texto. Degrada limpio si
    `yt-dlp` no está instalado (mismo patrón que MotorAudio/
    analizador_audio ante dependencias faltantes) y requiere `ffmpeg`
    del sistema (dependencia YA existente de esta app) para la
    conversión — si falta, yt-dlp tira un error claro que se atrapa y
    se devuelve como mensaje.
    - `es_url_youtube(url)`: regex que acepta youtube.com/watch,
      /playlist, /shorts/ y youtu.be, con o sin subdominio www./m./
      music. — pedido explícito (punto 9), rechaza cualquier otro
      dominio.
    - `descargar(url, carpeta_base, ...)`: primero hace un SONDEO sin
      descargar (`extract_flat`, `skip_download`) para saber si es un
      video suelto o una playlist y resolver la carpeta destino ANTES
      de bajar nada — evita bajar todo a medias para recién ahí
      descubrir dónde tendría que haber quedado. Video suelto →
      `<biblioteca_musical>/descargas YT/`; playlist →
      `<biblioteca_musical>/descargas YT/<título de la playlist>/`
      (pedido explícito, puntos 5 y 7) — `<biblioteca_musical>` es la
      MISMA ruta que ya existía en Configuración → Rutas → "Biblioteca
      musical" (punto 4: "el mismo lugar que elijo en
      configuraciones", sin necesidad de agregar un campo de
      configuración nuevo).
    - **Siempre MP3, limpieza automática (punto 8) SIN código propio**:
      el postprocesador `FFmpegExtractAudio` de yt-dlp (`preferredcodec:
      "mp3"`) ya borra el archivo intermedio (el que bajó en el
      formato original de YouTube) apenas termina de convertir — no
      hizo falta ningún manejo manual de limpieza de archivos, es
      comportamiento nativo de yt-dlp.
    - **Detección de qué se descargó, en DOS capas** (nunca confiar en
      una sola forma de leer el resultado, mismo criterio que ya rige
      el resto del proyecto ante libVLC/EasyEffects): capa 1, los
      `postprocessor_hooks` de yt-dlp (dan el título real de cada
      archivo); capa 2, comparar qué `.mp3` nuevos aparecieron en la
      carpeta destino (diff de carpeta antes/después) — las dos capas
      se COMBINAN, no una reemplaza a la otra, para cubrir tanto una
      playlist donde el hook falla para algunos ítems como un cambio
      de formato interno de yt-dlp entre versiones donde fallara para
      todos. Un bug real de esta clase apareció en el primer test
      (capa 2 nunca se activaba si la capa 1 devolvía AUNQUE SEA un
      resultado parcial) y quedó cubierto por un test dedicado que
      simula justo ese caso (un archivo detectado por hook, el otro
      solo por diff).
    - **Recorte de silencios (punto 3) reusando el motor YA
      existente**: cada archivo descargado pasa por
      `core/analizador_audio.analizar_audio()` (mismo motor no
      destructivo del resto de la app — nunca reescribe el mp3, solo
      calcula `punto_inicio_ms`/`punto_fin_ms`/`ganancia_db` como
      metadata) ANTES de devolver el resultado a la GUI — así el
      recorte de silencio de una descarga de YouTube es un campo más
      del registro, igual que cualquier archivo importado a mano,
      sin lógica paralela.
    - `ignoreerrors=True` en las opciones de yt-dlp: un video roto o
      privado dentro de una playlist no frena la descarga de los
      demás — mismo criterio de "nunca romper el lote por un ítem
      malo" ya usado en el Musicalizador/reanalizar biblioteca.
    - `callback_progreso` (opcional): un callable que recibe texto de
      estado ("Descargando: Tema (43%)", "Convirtiendo a MP3...",
      "Analizando silencios...") — el módulo lo llama desde los hooks
      de yt-dlp sin importar Qt para nada; es la GUI la que decide
      qué hacer con ese texto.

    **GUI (`gui/ventana_explorador.py`)**: un `QGroupBox` nuevo
    "⬇ Descargar de YouTube" al FINAL de `layout_archivos` (debajo de
    la lista de archivos, los botones Agregar/Info/Reemplazar/
    Eliminar, Previo/Stop y la barra de progreso del previo) — la
    interpretación de "tercio inferior derecho de la ventana 3" que
    mejor calza con el layout real: el panel de archivos ya ocupa el
    lado derecho de la ventana (splitter categorías 40% / archivos
    60%), y esto queda en su tercio inferior. Un `QLineEdit` con
    placeholder ("Pegá acá el enlace de YouTube...") + botón
    "⬇ Descargar" (Enter en el campo hace lo mismo que clickear el
    botón) + una etiqueta de estado chica debajo (gris para progreso,
    roja para el aviso de URL inválida).
    - **Validación de URL en la barra, sin diálogo emergente (pedido
      explícito, punto 9: "avisar como mensaje en la barra de URL")**:
      si `es_url_youtube()` da `False`, la etiqueta de estado se pone
      roja con "⚠ Solo se aceptan enlaces de YouTube..." y no se
      intenta descargar nada — ni siquiera se importa `yt_dlp` para
      este caso.
    - **Progreso sin threading (mismo patrón ya establecido, ronda de
      preload — "esta app nunca usó threading")**: `WaitCursor` +
      `callback_progreso` que actualiza la etiqueta y llama
      `QApplication.processEvents()` en cada aviso de yt-dlp — bloquea
      la UI igual que cualquier descarga real (no hay forma de evitarlo
      sin `QThread`, decisión de arquitectura ya tomada para toda la
      app), pero al menos no se ve "colgada": el texto cambia con cada
      video de una playlist y con el progreso de conversión.
    - **`_dar_de_alta_descarga_youtube(resultado)`**: arma un
      `registro` por archivo (mismo formato que cualquier alta manual
      — título/artista/género/código/ruta/duración/análisis de
      silencio) con género fijo `"Musica"` y código correlativo con
      el prefijo `MUS` de siempre, y lo agrega a la categoría "Descargas
      YT" (o su subcategoría con el título de la playlist) vía el
      helper nuevo `_obtener_o_crear_categoria_por_ruta()` — como
      `buscar_categoria_por_ruta()` (ya existía, usado por el
      Musicalizador) pero CREA los tramos que falten en vez de
      devolver `None`, así "Descargas YT" se crea sola la primera vez
      y se reutiliza (nunca se duplica) en cada descarga siguiente.
      Persiste con `_guardar_biblioteca()` de siempre.
    - **Aviso post-descarga (pedido explícito, punto 6)**: un
      `QMessageBox.information` indica a qué categoría exacta
      aterrizó ("Descargas YT" o "Descargas YT > <playlist>") y que
      hay que arrastrarlo a la categoría que corresponda — a
      propósito la app NUNCA intenta adivinar la categoría real
      (Música/Separadores/etc.), eso queda 100% a criterio del
      operador.
    - **Decisión de diseño no preguntada explícitamente, documentada
      acá por si Santiago la quiere ajustar**: la subcategoría de una
      playlist queda SIEMPRE anidada bajo "Descargas YT" (nunca como
      categoría de primer nivel separada) — mismo criterio de "zona de
      aterrizaje única antes de triage manual" que ya establecían los
      puntos 5-6 para un video suelto.

    Probado con `test_descargador_youtube.py` (nuevo, sin red real —
    se mockea `yt_dlp.YoutubeDL` por completo, simulando lo que
    devolvería yt-dlp de verdad, incluido el caso de detección mixta
    capa 1/capa 2 mencionado arriba): validación de URL (YouTube en
    sus variantes vs. Vimeo/texto random/vacío/`None`), degradación
    limpia sin `yt-dlp` instalado, rechazo de URL no-YouTube sin tocar
    yt-dlp, descarga de un video suelto de punta a punta (carpeta
    correcta, título, análisis de silencio adjunto, callback de
    progreso llamado), descarga de una playlist de 2 temas (carpeta
    con el título de la playlist, ambos títulos detectados pese a que
    solo uno pasa por el hook), sanitización de nombre de carpeta,
    `_obtener_o_crear_categoria_por_ruta()` (crea de cero, reutiliza en
    vez de duplicar, anida correctamente la subcategoría de playlist),
    alta completa de un video suelto y de una playlist en la GUI real
    (géneros/códigos/persistencia en `biblioteca.json` verificados) y
    el aviso de URL inválida en la barra — + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`, más 2 dependientes de la hora real del
    sistema y 2 de contaminación de estado entre scripts corridos en
    lote — todos ya documentados en rondas anteriores, confirmados sin
    relación con este cambio corriéndolos en aislado).

    **CONFIRMADO CON USO REAL**: la primera prueba de Santiago dio el
    mensaje de "necesito instalar yt-dlp en el entorno virtual" — no
    era un bug, `requirements.txt` se actualizó pero eso no reinstala
    solo en un venv ya creado; con `pip install -r requirements.txt`
    (venv activado) se resolvió. Confirmado después: **"anda todo muy
    bien"** — descarga real de YouTube funcionando de punta a punta.

54. ~~Confirmación al activar/desactivar el botón AUTOMÁTICO a
    mano~~ — pedido explícito, el último de una larga tanda de rondas
    ("lo último por largos días por el momento"): un diálogo Sí/No
    antes de aplicar el cambio, en los dos sentidos (activar y
    desactivar) — con una condición clave, textual: "lógicamente
    cuando inicia no, solo cuando una vez que lo abro al programa".

    **Por qué no alcanzaba con poner la confirmación dentro de
    `_toggle_automatico()`**: ese método es el que de verdad cambia el
    estado (texto del botón, color, `lbl_estado`, emite
    `automatico_cambiado`) — pero es el MISMO método que
    `MainWindow._inicializar_motores_audio()` llama directo al abrir
    la app para prender el Automático solo (`btn_automatico.setChecked(True)`
    + `_toggle_automatico()`, sin pasar por ningún click). Poner la
    pregunta ahí adentro hubiera interrumpido CADA arranque de la
    radio con un diálogo — exactamente lo que Santiago pidió evitar.

    **Solución**: `VentanaPublicidad._on_click_automatico()` (nuevo),
    conectado a `btn_automatico.clicked` en lugar de
    `_toggle_automatico()` directo. Como el botón es checkable, Qt ya
    invirtió su estado ANTES de emitir `clicked` — el método lee ese
    estado ya invertido para armar el texto de la pregunta ("¿Activar
    el modo AUTOMÁTICO?..." o "¿Desactivar el modo AUTOMÁTICO?...",
    cada uno con su propia explicación de qué implica) y pide
    confirmación con `QMessageBox.question`. Si el operador cancela
    (No), el botón se REVIERTE a mano (`setChecked(not activar)`) SIN
    llamar a `_toggle_automatico()` — así no se emite ningún cambio
    real, ni se toca `lbl_estado` ni la señal `automatico_cambiado`.
    Si confirma (Yes), recién ahí se llama a `_toggle_automatico()`
    (el método de siempre, sin cambios). El arranque de la app sigue
    llamando a `_toggle_automatico()` directo, como siempre — nunca
    pasa por `_on_click_automatico()`, así que nunca pregunta nada al
    abrir el programa.

    Probado con `test_confirmacion_automatico.py` (nuevo, dedicado): el
    arranque real de `MainWindow` NO dispara ningún `QMessageBox.question`
    y el botón queda encendido solo; un click manual SÍ pregunta, con
    el texto correcto según el sentido (activar/desactivar); cancelar
    (No) revierte el botón sin cambiar `esta_en_automatico()` ni emitir
    la señal; confirmar (Yes) aplica el cambio real y emite
    `automatico_cambiado` con el valor correcto — + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre: `test_confirmaciones.py`, `test_log_git.py`,
    `test_ventana3.py`, confirmados en aislado sin relación con este
    cambio). Falta que Santiago confirme en su notebook real que la
    pregunta aparece al tocar el botón a mano (en los dos sentidos) y
    que el arranque de la app sigue sin interrumpirse con ningún
    diálogo.
55. ~~Sacar el procesador de audio nativo de PipeWire (ronda 52) —
    Santiago vuelve a EasyEffects, manejado por FUERA de la app~~ —
    pedido explícito: "para mayor compatibilidad, el procesador de
    audio y demás lo manejaré por fuera, así que instalaré EasyEffects
    que tenía mayor control por fuera. Saquemos todo procesador de
    audio, eso que hicimos." Reversión de la ronda 52 (que a su vez
    había reemplazado la integración de EasyEffects de las rondas
    37-51) — a esta altura, la app pasó por DOS intentos de resolver
    el procesamiento de FM (compresor/limitador/estéreo) y en ambos
    casos Santiago terminó prefiriendo manejarlo él mismo, fuera del
    programa: primero controlando EasyEffects desde acá (5 rondas de
    ida y vuelta con la ventana/el pipeline), después con un
    filter-chain nativo de PipeWire (que sí llegó a sonar, ronda 52) —
    y ahora decide que ninguno de los dos vale la complejidad, prefiere
    instalar y configurar EasyEffects él mismo desde su propia
    interfaz, sin que este programa lo toque para nada.

    Eliminado: `assets/pipewire-fm-processing.conf` (el único archivo
    que existía de la integración — nunca estuvo wireado en Python, así
    que sacarlo no toca ni una línea de `core/`/`gui/`, coherente con
    que desde el principio se armó como una pieza aparte). No había
    nada más que sacar — `core/easyeffects_control.py` y el botón
    "🎚 FM" ya se habían eliminado por completo en la propia ronda 52,
    antes de construir el filter-chain nativo.

    **"Mantené si es posible, la autoganancia de salida para que no
    haya diferencia de volumen entre canción y canción" — YA estaba,
    sin relación con nada de esto**: el nivelado de volumen POR TEMA
    (`core/analizador_audio.py`, sección "Motor de agregado de tema
    musical" más arriba) es una función mucho más vieja que toda la
    saga de EasyEffects/PipeWire — calcula, al importar cada archivo,
    cuánta ganancia en dB hay que sumar o restar para dejarlo nivelado
    contra un objetivo común (`DBFS_OBJETIVO = -16.0`), y
    `MotorAudio.reproducir()` aplica esa ganancia (`ganancia_db`) al
    arrancar cada ítem — así un tema grabado bajito y otro grabado
    fuerte suenan parejos al aire. Esto NUNCA dependió de EasyEffects
    ni del filter-chain de PipeWire (son mecanismos completamente
    independientes) — sacar el procesador de audio de esta ronda no le
    cambia nada: sigue funcionando exactamente igual, para Música,
    Publicidad, Separadores, Pisador, Artística y HTH por igual, en
    Ventana 1, Ventana 2 y la Auxiliar. Es lo más parecido a una
    "autoganancia de salida" que esta app puede ofrecer sin volver a
    depender de un procesador de audio externo — no es una función
    NUEVA de esta ronda, es la confirmación de que ya cumple el pedido.

    No hizo falta ningún test nuevo (la única pieza que se tocó fue un
    archivo `.conf` sin ningún código que lo importe o lo referencie) —
    sí se corrió la suite de regresión completa para confirmar que
    nada más se rompió (mismos fallos preexistentes de siempre, sin
    relación). Pendiente: que Santiago instale EasyEffects y arme su
    propia cadena a su gusto, completamente por fuera de esta app —
    si en algún momento más adelante quiere retomar algún tipo de
    integración, este archivo (roadmap rondas 37-52 y esta) tiene el
    historial completo de qué se probó y por qué no prosperó, para no
    tener que redescubrirlo.

56. ~~Bug real, crítico — el maximizado se iba de pantalla en 3
    computadoras distintas, "no toma el ancho de los display"~~ —
    pedido explícito, textual: "eso es inaceptable, debemos tener
    compatibilidad para todo tipo de resolución en monitores... No
    podemos avanzar si eso sucede... Debemos encontrar la forma de
    que el programa detecte el tamaño de resolución del display y se
    ajuste a ello. Sí o sí." Segunda vuelta del bug de la ronda 15
    (que solo corregía la POSICIÓN de una geometría restaurada de
    otro monitor) — esta vez la causa era otra, y mucho más grave:
    afectaba a instalaciones NUEVAS, sin ninguna geometría guardada
    todavía.

    **Causa real, cuantificada**: `MainWindow` nunca seteaba un
    `minimumSize()` explícito — `mw.minimumWidth()` daba **0**. Sin
    ese piso explícito, Qt usa `minimumSizeHint()` (calculado en
    cascada por todo el árbol de layouts) como el mínimo real que un
    gestor de ventanas respeta al maximizar/redimensionar — medido
    con esta misma UI, ese mínimo daba **1517px de ancho**. Cualquier
    monitor más angosto que eso (1366px es probablemente EL tamaño
    más común en notebooks, incluida la propia notebook de hardware
    modesto de Santiago) hacía que maximizar fuera físicamente
    imposible de encajar: el gestor de ventanas pedía el ancho de la
    pantalla, Qt se negaba a bajar de 1517px, y la ventana quedaba
    más ancha que el display. El origen de ese 1517px:
    `QSplitter.setChildrenCollapsible(False)` en DOS lugares —
    `splitter_principal` (`main_window.py`, las 3 ventanas
    Publicidad/Emisión/Explorador) y el splitter interno de Ventana 3
    (`ventana_explorador.py`, categorías/archivos) — ambos, puestos a
    propósito en una ronda muy anterior para evitar que un splitter
    se colapsara sin querer, tienen como efecto secundario que
    NINGUNO de sus paneles puede bajar de su tamaño "cómodo" natural,
    y eso se propaga hacia arriba hasta convertirse en el piso de
    ancho de TODA la ventana principal.

    **Corregido en 3 frentes**:
    - `splitter_principal.setChildrenCollapsible(True)` y
      `ventana_explorador.splitter.setChildrenCollapsible(True)` —
      ahora los paneles SÍ pueden comprimirse más allá de su tamaño
      cómodo (con scrollbars/controles más apretados) en vez de
      bloquear el resize entero.
    - `MainWindow.__init__` ahora llama `self.setMinimumSize(900,
      550)` explícito — este es el fix de fondo: al haber un mínimo
      EXPLÍCITO seteado, Qt ya no cae al `minimumSizeHint()` grande
      del árbol de layouts como piso real para el resize/maximizado
      manejado por el gestor de ventanas. 900px entra cómodo en
      prácticamente cualquier notebook real, incluidas las viejas de
      1024px.
    - El tamaño INICIAL (`self.resize(...)`, usado la primera vez que
      no hay geometría guardada) dejó de ser un `1400x800` fijo — 
      ahora se calcula contra `QApplication.primaryScreen().
      availableGeometry()`, nunca pidiendo más de lo que la pantalla
      real tiene disponible, con el mismo `1400x800` como techo si la
      pantalla es más grande.
    - `gui/estado_ui.py:_asegurar_dentro_de_pantalla()` (el mecanismo
      de la ronda 15, que corrige una geometría restaurada de otro
      monitor) queda sin tocar en su lógica — pero ahora sí puede
      cumplir lo que ya intentaba hacer, porque el piso que antes se
      lo impedía en silencio ya no existe.

    Probado con `test_ventana_ajusta_a_pantalla.py` (nuevo, dedicado):
    ambos splitters confirmados `childrenCollapsible=True`;
    `mw.resize(1024, 600)` (tamaño tipo notebook chica) ahora sí
    produce esa medida EXACTA; `minimumWidth()` pasó de 0 (sin
    protección) a 900 (piso explícito, confirmado con `git stash`
    contra el código viejo: daba 0 de `minimumWidth()` y 1517x390 de
    `minimumSizeHint()`); `_asegurar_dentro_de_pantalla()` con una
    pantalla simulada de 1024x600 encaja correctamente una geometría
    guardada de un monitor de 1920px, tanto en el caso normal como en
    el caso "estaba maximizada"; el tamaño inicial de una ventana
    nueva nunca excede la pantalla disponible — + suite de regresión
    completa sin fallos nuevos (mismos fallos preexistentes de
    siempre). **Limitación reconocida de esta prueba**: el backend
    `offscreen` del sandbox no tiene un gestor de ventanas real, así
    que un `resize()` llamado directo en Python no reproduce el
    síntoma EXACTO que describió Santiago (que ocurre específicamente
    cuando el gestor de ventanas real negocia el tamaño al maximizar)
    — por eso el test se apoya en la métrica más robusta y
    verificable en el sandbox (`minimumWidth()` explícito vs. 0), que
    es la causa raíz confirmada, no un síntoma indirecto. Falta que
    Santiago confirme en sus 3 computadoras reales que el maximizado
    ahora sí encaja siempre en el display, sin importar la resolución.

57. ~~Reconciliación de dos ramas divergentes — la PC de escritorio
    (la definitiva de aire) había quedado en otra rama, con trabajo
    real de audio que había que evaluar antes de descartar~~ —
    episodio importante para no repetir: Santiago probó el fix de la
    ronda 56 en la PC de escritorio (**la que va a ser la de aire
    definitiva**, según ya había aclarado en la ronda del filter-chain
    de PipeWire) y seguía viendo el bug en 1360x768. La causa NO era
    el código: esa PC tenía checkouteada `claude/screen-eq-adjustments-
    nc529p`, una rama de una sesión de Claude Code DISTINTA de esta
    conversación (Santiago había ido a esa PC específicamente "porque
    necesitaba acomodar la salida de audio y sonido", antes de dejarla
    como la definitiva) — arrancó del mismo punto que esta rama (el
    commit de "Confirmar antes de activar/desactivar AUTOMÁTICO",
    ayer) pero se fue para otro lado: en vez de sacar el procesador de
    PipeWire (lo que se decidió ACÁ, ronda 55), esa sesión lo siguió
    construyendo (ecualizador de 8 bandas, apuntado al codificador USB
    real) — y de paso intentó, dos veces, arreglar el mismo bug de
    pantalla con un enfoque distinto.

    **Por qué el botón "Actualizar" de Configuración decía "ya estás
    al día" estando desactualizado**: no era un bug nuevo, era un
    efecto secundario correcto de un fix real hecho en ESA otra rama
    (`_evaluar_version()`, ver más abajo) — compara HEAD contra el
    upstream REALMENTE configurado en el checkout local, no siempre
    contra `main`. Como el checkout de esa PC apuntaba a
    `claude/screen-eq-adjustments-nc529p`, el botón nunca iba a mirar
    `main` (donde vivían los fixes de esta conversación) por más que
    se lo apretara mil veces — no hay forma de que un `git pull`
    normal cruce a una rama distinta de la que está checkouteada.

    **Reconciliación, comando por comando** (se revisó el diff
    COMPLETO de las 6 commits de esa rama contra el ancestro común
    antes de decidir nada — nunca se descartó a ciegas): 2 de las 6
    tocaban EXCLUSIVAMENTE `assets/pipewire-fm-processing.conf` (el
    ecualizador de 8 bandas y el apuntado al codificador USB) —
    descartadas sin más trámite, ese archivo ya no existe en esta rama
    desde la ronda 55, coherente con la decisión de Santiago. Las
    otras 4 SÍ eran válidas e independientes del procesador de audio,
    y se sumaron acá con `git cherry-pick` (las 4 aplicaron limpio,
    sin conflictos):
    - **"Arrancar maximizada en una PC/perfil nuevo"**: en una
      instalación sin `ui_state.ini` todavía (máquina nueva),
      `restaurar_geometria_ventana()` ahora arranca directamente
      `showMaximized()` en vez de confiar en un tamaño calculado —
      complementa (no reemplaza) el fix de la ronda 56, que sigue
      siendo el que garantiza que ESE maximizado realmente entre en
      la pantalla.
    - **"Separar la salida de Preescucha de la Master"**: bug real
      independiente, sin relación con PipeWire — el campo "Salida
      Preescucha" de Configuración → Audio existía desde hacía mucho
      pero estaba documentado como "reservado a futuro" y nunca se
      aplicaba de verdad (`GestorExplorador` siempre usaba el
      dispositivo Master). Ahora sí usa `dispositivo_preescucha` —
      pensado para que el ▶ Previo de Ventana 3 salga por los
      parlantes de monitoreo de la PC, separado de la salida Master
      que va al equipo que sale al aire.
    - **"Corregir bucle infinito de 'hay actualización disponible'"**
      (`core/actualizador.py`): el bug real explicado arriba —
      `_rama_remota_disponible()` pasó de asumir siempre `main`/
      `master` a usar el upstream configurado de verdad (`git
      rev-parse @{u}`), y `_evaluar_version()` (nueva, compartida
      entre la versión síncrona y la asíncrona) solo reporta
      actualización real si el remoto es descendiente directo de HEAD
      (`git merge-base --is-ancestor`) — un local adelantado o
      DIVERGIDO ya no dispara ni un falso positivo (el bug original:
      bucle actualizar→reiniciar→"hay actualización" de nuevo) ni,
      como efecto colateral en el caso de Santiago, deja de avisar
      cuando corresponde SI el checkout apunta a la rama correcta.
    - **"Achicar el ancho mínimo de Ventana 3"**: fix COMPLEMENTARIO al
      de la ronda 56, no redundante — mientras el `setMinimumSize()`
      de esa ronda le permite a la ventana bajar de su mínimo natural
      a la fuerza (paneles se comprimen), esta reduce el mínimo
      NATURAL en sí: las filas de botones de Ventana 3 (Categoría/Sub/
      Eliminar, Agregar/Info/Reemplazar/Eliminar) pasan de 1 fila a 2
      (clase QSS nueva `btnCompacto`, mismo criterio que `btnTransporte`
      de Ventana 1/2) — cambia ancho por alto, que sobra en pantallas
      anchas pero bajas como 1360x768. Medido: `minimumSizeHint()` de
      `MainWindow` bajó de 1517px (ronda 56) a **1260px** con este fix
      sumado — casi 100px de margen real contra los 1360px de
      Santiago, en vez de estar clavado casi al límite.

    Probado: suite de regresión completa tras las 4 cherry-picks sin
    fallos nuevos (mismos fallos preexistentes de siempre — confirmado
    que 2 fallos vistos en esta corrida puntual, `test_ciclo_automatico.py`
    y `test_play_bloque_y_hora.py`, son los ya documentados
    dependientes de la hora real del sistema, no relacionados: la
    corrida cayó a las 00:26 UTC, la franja horaria que ya rompía estos
    dos tests en rondas anteriores) + re-medido `minimumSizeHint()`
    combinado (1260x396) y `resize(1360, 768)` aplicado exacto, sin
    clamping. **Regla para el futuro, importante**: si Santiago dice
    que algo "no se actualiza" o el comportamiento no coincide con lo
    último de esta conversación, preguntar primero en qué máquina/rama
    está parado (`git log -1`, `git status`) antes de asumir que el
    código de acá está mal — puede haber otra sesión de Claude Code
    trabajando en paralelo sobre la misma PC. Pendiente: que Santiago,
    una vez mergeado esto a `main`, cambie el checkout de la PC de
    escritorio a `main` (comandos exactos en el chat) y confirme que
    el maximizado ya entra en su pantalla de 1360x768, y que el botón
    Actualizar vuelve a funcionar de ahí en más.

58. ~~Rediseño compacto para pantallas chicas (1360x768): sacar la
    doble fila de menú+toolbar, achicar relojes/Ahora-Luego/título de
    panel~~ — pedido explícito con captura de pantalla real adjunta:
    "está muy compacto, debemos rediseñar. Juntar lo que puede estar
    junto. Lo importante son las listas de ítem." — con libertad
    explícita para rediseñar el skin siempre que entre en pantalla y
    se puedan seguir achicando las 3 columnas a gusto.

    **Auditoría antes de tocar nada**: se revisó código por código qué
    hacía cada botón del `QMenuBar` clásico (Archivo/Edición/Ver/
    Reproducción/Herramientas) y de la toolbar de abajo — resultado:
    CASI TODO era decorativo. "Nueva programación"/"Abrir programación"/
    "Guardar"/"Deshacer"/"Rehacer"/"Pantalla completa"/"Play"/"Stop" del
    menú, y "Abrir"/"Buscar"/"▶ Play"/"● Grabar"/"Lista"/"＋ Agregar" de
    la toolbar NUNCA tuvieron un `.triggered.connect(...)` — clickearlos
    no hacía absolutamente nada, eran relleno visual de rondas muy
    tempranas del proyecto que nunca se limpió. Los únicos ítems reales
    del menú eran Salir, Auxiliar, y las 5 pestañas de "Herramientas"
    (que abren Configuración).

    **Consolidado en UNA sola fila** (`gui/main_window.py`):
    - `_construir_menu()` ya NO llama a `self.menuBar()` en absoluto —
      Qt no reserva esa fila si nunca se pide. Los dos ítems reales
      (Salir/Ctrl+Q, Auxiliar/Ctrl+Shift+A) sobreviven como atajos de
      teclado invisibles (`self.addAction(...)`, funciona sin pasar
      por ningún menú visible).
    - `_construir_toolbar()` se achicó a solo 3 elementos reales:
      Programador, Musicalizador, y un botón "⚙ Configuración" nuevo
      —ahora un `QToolButton` con `ToolButtonPopupMode.InstantPopup` y
      un `QMenu` desplegable con las 5 pestañas (mismo contenido que
      tenía el viejo menú "Herramientas", un solo click en vez de
      abrir un menú aparte). Nombre de emisora + reloj siguen a la
      derecha, sin cambios.
    - QSS nuevo (`gui/styles.py`, `QToolBar#toolbarPrincipal`/
      `QToolButton` dentro de ella): padding y fuente reducidos —
      antes del cambio la toolbar sola sería la única fila de
      navegación y no debía volver a quedar más alta de lo necesario.

    **Achicado el contenido de cada panel** (relojes, "Ahora"/"Luego",
    título del `QGroupBox`, medidor de nivel decorativo) — mismos
    cambios espejados en `panel_reproductor.py` (Ventana 2/Auxiliar) Y
    `ventana_publicidad.py` (Ventana 1, implementación paralela
    propia, ver "Cosas ya resueltas" sobre por qué no comparten
    código):
    - Relojes (`QLabel#lblTiempoTranscurrido`/`Restante`): 11pt→9pt,
      padding `1px 4px`→`0px 3px`, ancho máximo 90→76px.
    - `QFrame#frameAhora`/`frameLuego`: padding `1px 3px`→`0px 2px`,
      `contentsMargins` del layout interno 2→1px,
      `QLabel#lblEtiquetaAhoraLuego` ("Ahora:"/"Luego:") 8pt→7pt.
    - `EtiquetaMarquesina` (el sticker del título): alto mínimo/
      `sizeHint` 22px→18px.
    - `MedidorNivelDecorativo`: alto mínimo 40px→26px — este era en
      la práctica el piso real de toda la fila `fila_info` (clocks +
      Ahora/Luego), por encima incluso de lo que pedían los relojes
      ya achicados; sin bajarlo, el resto de las reducciones de esta
      fila no se notaban.
    - Título de `QGroupBox` (afecta los 3 paneles + cualquier otro
      grupo de la app, ej. el panel de descarga de YouTube):
      `margin-top` 24px→16px, fuente 14pt→11pt.
    - Botón grande "▶ PLAY/SIG.": alto mínimo 52px→42px, ancho mínimo
      56px→50px.
    - `QHeaderView::section` (encabezado de columnas de cualquier
      árbol): padding 4px→2px.

    Medido: `MainWindow.minimumSizeHint()` bajó de altura (396px →
    375px) sin perder ningún ancho de margen ya ganado en la ronda
    anterior (`resize(1360, 768)` sigue aplicando exacto). Se generó
    una captura real de la app a 1360x768 (`QWidget.render()` sobre un
    widget con `WA_DontShowOnScreen`, para que el backend `offscreen`
    del sandbox no la recorte a su pantalla virtual chica) y se le
    mandó a Santiago para que la compare contra su pantalla real antes
    de que actualice — confirma visualmente una sola fila de
    navegación arriba, relojes/Ahora-Luego mucho más chicos, y bastante
    más alto libre para las listas antes de llegar al borde inferior.

    El splitter de las 3 ventanas (`splitter_principal`, ya
    `childrenCollapsible=True` desde la ronda 56) sigue sin cambios —
    el pedido de "poder achicar las columnas de las 3 ventanas a mi
    gusto" ya estaba resuelto ahí, arrastrando los separadores.

    Probado con `test_rediseño_compacto.py` (nuevo, dedicado): sin
    `QMenuBar` visible pero con los 2 atajos reales preservados,
    toolbar con solo los 3 botones reales (los 6 decorativos
    confirmados ausentes uno por uno), el desplegable de Configuración
    con las 5 pestañas en el orden correcto, `minimumSizeHint()` más
    bajo que antes de esta ronda, `resize(1360, 768)` exacto, y los
    tamaños nuevos de reloj/`EtiquetaMarquesina`/medidor de nivel
    confirmados por valor — + suite de regresión completa sin fallos
    nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
    **Sigue sin poder confirmarse "a ojo" en una pantalla real** (el
    sandbox no tiene un monitor de verdad ni el font-rendering exacto
    del sistema de Santiago): falta que confirme si el resultado
    visual (captura enviada) le alcanza, o si quiere ajustar algo más
    puntual (algún botón, algún texto) una vez que lo vea en su propia
    pantalla.

59. ~~Mover el botón "🎧 Auxiliar" de adentro de Ventana 2 a la
    toolbar, junto a Configuración~~ — pedido explícito, continuación
    directa del rediseño compacto de la ronda anterior: "el botón
    'auxiliar' en la ventana 2 podría estar arriba al lado de
    'Configuraciones', no hace falta que esté ahí. Eso dará mayor
    posibilidad de ampliar la ventana 3 a gusto." El botón vivía
    DENTRO de `panel_reproductor.py` (parámetro
    `mostrar_boton_auxiliar=True`, exclusivo de Ventana 2 — la
    Auxiliar y Ventana 1 nunca lo tuvieron), sumando su ancho mínimo a
    la fila de transporte de Ventana 2 — sacarlo de ahí le resta ese
    ancho mínimo a Ventana 2 y deja más margen para angostarla y
    agrandar el Explorador arrastrando el splitter.

    **Limpieza de código, no solo mover un widget**: se sacó
    `mostrar_boton_auxiliar` del todo (parámetro de
    `PanelReproductor.__init__`/`_construir_ui`, ya no tiene sentido
    con un solo llamador real) y la señal `solicitud_abrir_auxiliar`
    completa (existía en `PanelReproductor` Y en `VentanaEmision`,
    reenviándose una a la otra hasta `MainWindow`) — la cadena entera
    quedaba sin razón de ser una vez que el botón que la disparaba ya
    no vive ahí. La acción real (`self._accion_auxiliar`, construida
    en `_construir_menu()` junto con "Salir" — mismo lugar de siempre
    para las 2 acciones invisibles/reales del viejo menú) se agrega
    directo a la toolbar en `_construir_toolbar()`, entre Musicalizador
    y Configuración — el atajo Ctrl+Shift+A sigue funcionando igual
    (una `QAction` mantiene su shortcut activo con solo estar en el
    árbol de widgets de la ventana, no hace falta agregarla dos veces).

    Medido: `MainWindow.minimumSizeHint()` bajó de ancho otros 84px
    (1248px → 1164px) solo por sacar este botón de Ventana 2 — sumado
    a las rondas 56 y 58, el margen contra los 1360px de la pantalla
    de Santiago sigue creciendo. Se generó una captura nueva a
    1360x768 confirmando visualmente el botón en su nueva posición
    (toolbar: Programador / Musicalizador / Auxiliar / Configuración)
    y su ausencia en la fila de transporte de Ventana 2 (quedó Stop/
    Fade arriba, Pausa/Cut/Stop diferido abajo, sin el botón extra).

    Probado (ampliando `test_rediseño_compacto.py`): Ventana 2 ya no
    tiene `btn_auxiliar` como atributo, `VentanaEmision` ya no tiene
    la señal `solicitud_abrir_auxiliar`, la Auxiliar no se crea sola
    al arrancar, el atajo Ctrl+Shift+A sigue en la acción de la
    toolbar, y clickear (`.trigger()`) el botón "🎧 Auxiliar" de la
    toolbar abre la ventana Auxiliar de verdad (`mw._ventana_auxiliar`
    deja de ser `None`) — + suite de regresión completa sin fallos
    nuevos (mismos 3 fallos preexistentes de siempre). Falta que
    Santiago confirme en su pantalla real que el botón se ve bien
    ubicado ahí arriba y que ahora puede ampliar el Explorador más de
    lo que podía antes.

60. ~~Dos bugs reales de fondo en la selección de dispositivo de audio
    (Configuración → Audio)~~ — pedido explícito, con diagnóstico
    propio de Santiago: "sin importar lo que yo elija, siempre sale
    por la principal de parlantes... tengo una salida analógica y otra
    por el monitor Arzopa por HDMI, no tengo forma gráfica de elegir
    la salida." Preguntó si había que cambiar KMix por otro mezclador
    — aclarado en el chat: KMix es solo la applet de volumen de Plasma
    (frontend de PulseAudio/ALSA), no decide el ruteo — el bug real
    estaba en cómo esta app habla con libVLC, nada que ver con KMix.

    **Bug A — el combo de Configuración no listaba las salidas reales
    (ej. la HDMI nunca aparecía)**: `listar_dispositivos()` usaba
    `MediaPlayer.audio_output_device_enum()`, que por diseño de libVLC
    solo enumera los dispositivos del output QUE YA ESTÁ EN USO por
    ESE reproductor puntual — pero `VentanaConfiguracion.
    _listar_dispositivos_disponibles()` arma un `MotorAudio()` de
    mentira SOLO para listar, sin reproducir nada nunca — con un
    reproductor que nunca arrancó, esa llamada devuelve una lista
    vacía o incompleta, sin las salidas reales del hardware.
    Reemplazado por la API a nivel de `Instance`
    (`audio_output_list_get()` — lista los MÓDULOS de audio del
    sistema, pulse/alsa/etc. — + `audio_output_device_list_get()` por
    cada uno), disponible desde libVLC 2.1.0, que NO depende de que
    haya una salida activa: recorre todos los módulos y sus
    dispositivos reales sin necesitar reproducir nada primero.

    **Bug B — la selección elegida nunca se mantenía ("siempre sale
    por la principal")**: `reproducir()` hace un `self._player.stop()`
    justo antes de cada `play()` (fix de una ronda mucho anterior, para
    que un Pisador reusado no quede mudo tras el fin natural de un
    media) — pero cada `stop()` DESARMA la salida de audio (aout) del
    reproductor, que se reconstruye de cero en el siguiente `play()`.
    La selección de dispositivo, aplicada UNA sola vez al elegirla en
    Configuración, se perdía en el primer stop()/play() que pasara
    después (que es CONSTANTEMENTE, con cada tema nuevo) — libVLC
    volvía a la salida por defecto del sistema cada vez. Es el MISMO
    patrón de bug ya resuelto hace rondas para el volumen
    (`_volumen_deseado`, re-aplicado en cada arranque) — nunca se le
    había aplicado el mismo criterio al dispositivo de salida.
    Corregido con `_aplicar_dispositivo_salida()` (nuevo, punto único
    de aplicación), llamado en el constructor, en
    `set_dispositivo_salida()`, e INMEDIATO + en el diferido de 150ms
    de cada `reproducir()` — mismas dos capas de seguridad que ya usa
    el volumen.

    **Detalle técnico que conecta ambos bugs**: `audio_output_device_set()`
    necesita DOS datos para aplicar la selección de verdad — el MÓDULO
    de audio (ej. `"pulse"`) y el ID del dispositivo dentro de ese
    módulo — pero el código viejo siempre pasaba `module=None`, que
    solo funciona de casualidad si el id resulta ser único entre
    módulos. Como el fix de listado (Bug A) ahora SÍ conoce el módulo
    de cada dispositivo real, el id que se guarda en
    `config_general.json` pasó a ser compuesto
    (`"{modulo}||{device}"`) — `MotorAudio._modulo_y_dispositivo()`
    lo separa de nuevo al aplicar. Compatible con instalaciones viejas:
    un id SIN el separador `||` (guardado por una versión anterior, o
    el sentinel `"default"`) se interpreta como dispositivo solo, sin
    módulo — mismo comportamiento de siempre, no rompe una config ya
    guardada.

    Probado con `test_dispositivo_salida.py` (nuevo, dedicado — usa
    estructuras `ctypes` REALES de `vlc.py`, no mocks livianos, para
    reproducir con fidelidad cómo libVLC arma sus listas enlazadas):
    `listar_dispositivos()` recorre 2 módulos con 3 dispositivos
    reales sin haber reproducido nada; `_modulo_y_dispositivo()` separa
    bien el id compuesto y degrada limpio ante un id viejo sin
    separador; `set_dispositivo_salida()` aplica módulo+dispositivo
    por separado; `reproducir()` re-aplica el dispositivo tanto
    inmediato como en el diferido de 150ms, Y en un SEGUNDO
    `reproducir()` consecutivo (simulando pasar de tema en tema, el
    caso real que rompía la selección) — + suite de regresión completa
    sin fallos nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`).
    **Sigue sin poder confirmarse con audio/hardware real** (el sandbox
    no tiene libVLC ni tarjeta de sonido): falta que Santiago confirme
    que ahora el combo de Configuración → Audio SÍ muestra la salida
    HDMI del Arzopa como opción separada de los parlantes analógicos,
    y que elegirla de verdad saca el audio por ahí de forma persistente
    (no solo la primera vez).
61. ~~Selección de dispositivo de audio: LA CAUSA DE FONDO real, tras
    confirmar que el listado (ronda 60) ya andaba perfecto~~ — Santiago
    probó la ronda 60 y confirmó el listado ("Aparecen TODOS los
    dispositivos, por ese lado correcto... no lo cambies") pero
    reportó que la selección seguía sin aplicarse: "al pasar el master
    a ARZOPA no se cambia, sigue saliendo por los parlantes... no veo
    ningun cambio, falta algo más?"

    **Causa real, encontrada leyendo el propio docstring de
    `python-vlc`** (no adivinada — `inspect.getsource(vlc.MediaPlayer.
    audio_output_device_set)` en el venv real de este proyecto):
    ```
    If the module parameter is not None, the device parameter of the
    corresponding audio output, if it exists, will be set to the
    specified string. Note that some audio output modules do not have
    such a parameter (notably MMDevice and PulseAudio).
    ...
    If the module paramater is None, audio output will be moved to
    the device specified by the device identifier string immediately.
    This is the recommended usage.
    ```
    El propio fix de la ronda 60 (Bug B) pasaba SIEMPRE un módulo
    explícito (`"pulse"`, `"alsa"`, etc., extraído del id compuesto)
    porque hacía falta para poder LISTAR sin haber reproducido nada
    (Bug A) — pero para APLICAR la selección, ese mismo módulo
    explícito es EXACTAMENTE el caso que la librería documenta como
    "sin efecto" en PulseAudio — el motor de audio casi universal en
    escritorios Linux modernos (Debian/Q4OS de Santiago incluido,
    vía PulseAudio o el compat layer de PipeWire). Como el propio
    docstring aclara, "Errors are ignored (this is a design bug)" — la
    llamada no fallaba ni avisaba nada, simplemente no hacía nada, así
    que el fix de la ronda 60 quedó funcionalmente inerte en la
    práctica para el caso real de Santiago, a pesar de estar bien
    armado en todo lo demás (listado, re-aplicación en cada
    `reproducir()`, etc.).

    **Corrección**: `MotorAudio._aplicar_dispositivo_salida()`
    (`core/audio_engine.py`) ahora llama SIEMPRE
    `self._player.audio_output_device_set(None, device)` — `module`
    fijo en `None` (el "uso recomendado" documentado por la propia
    librería para mover la salida de inmediato), descartando el
    módulo del id compuesto en este punto puntual. El módulo sigue
    viajando en el id guardado (`"{modulo}||{device}"`) y se sigue
    usando exactamente igual que antes en `listar_dispositivos()` —
    **sin tocar el listado**, tal cual pidió Santiago explícitamente
    ("no lo cambies") — el módulo ahí evita duplicados/ambigüedad
    entre módulos al armar el combo, simplemente ya no se le pasa a
    libVLC al momento de aplicar la selección.

    Probado extendiendo `test_dispositivo_salida.py`: todas las
    aserciones de aplicación (`set_dispositivo_salida()` directo,
    `reproducir()` inmediato, el diferido de 150ms, y un segundo
    `reproducir()` simulando cambio de tema) confirman que la llamada
    real a `audio_output_device_set()` ahora siempre lleva
    `module=None` con el `device` correcto — más un caso nuevo
    dedicado a un id VIEJO sin separador `||` (de una instalación
    anterior a la ronda 60), que también aplica con `module=None` sin
    romperse — + regresión de las aserciones de LISTADO (Bug A, sin
    tocar) sin cambios + suite de regresión completa sin fallos nuevos
    (mismos 3 fallos preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`). **Sigue sin poder
    confirmarse con audio/hardware real** (el sandbox no tiene libVLC
    ni PulseAudio/PipeWire real — este fix se basa en la documentación
    oficial de la librería, no en una prueba contra el propio motor de
    audio): falta que Santiago confirme que ahora sí, al elegir la
    salida HDMI del Arzopa (o cualquier otra) en Configuración → Audio
    y guardar, el audio efectivamente sale por ahí — tanto al empezar
    un tema nuevo como (si prueba) mientras algo ya está sonando.
    **Nota para el futuro sobre el caso "ya está sonando"**:
    `MainWindow._aplicar_configuracion_en_vivo()` llama a
    `motor.set_dispositivo_salida()` directo sobre un motor que puede
    estar reproduciendo en ese mismo instante, asumiendo (según su
    propio comentario) que "libVLC tolera cambiar de dispositivo sin
    cortar la reproducción" — con `module=None` esto debería funcionar
    de verdad ahora (es justamente el caso que la documentación llama
    "immediately"), pero si Santiago reporta que el cambio en vivo
    sigue sin notarse mientras algo suena (y solo se nota recién en el
    próximo tema), la costura a revisar es esa: forzar un
    stop()/replay() ahí en vez de confiar en el hot-swap in-place.
62. ~~Selección de dispositivo: log de diagnóstico agregado — el fix de
    la ronda 61 (`module=None`) SIGUE sin funcionar en la PC real de
    Santiago~~ — reportó, tras probar la ronda 61: "sigue sin
    reproducir por donde lo selecciono... no toma control sobre la
    placa y no hace caso a lo que selecciono... no importa que
    seleccione, siempre sale por la analógica de parlantes."

    Este es ya el SEGUNDO fix basado 100% en documentación de
    `python-vlc` que no resuelve el problema en su hardware real — el
    patrón (dos rondas seguidas de fixes "correctos según el manual"
    que no cambian nada en la práctica) es la señal de que hace falta
    DATOS REALES de su sistema antes de seguir adivinando, mismo
    criterio que ya destrabó la investigación de EasyEffects/PipeWire
    en su momento (ahí también costó varias rondas a ciegas hasta que
    un `pw-link -l` real reveló la causa exacta). No se hizo un tercer
    cambio de código a ciegas.

    **Agregado en esta ronda, mientras se espera el diagnóstico**: log
    de diagnóstico en `MotorAudio._aplicar_dispositivo_salida()`
    (`core/audio_engine.py`, vía `config.settings.registrar_evento()`)
    — cada vez que se aplica un dispositivo DISTINTO al último
    logueado, deja una línea en `config/data/log_aplicacion.txt` con
    el string EXACTO que la app le manda a libVLC (`audio_output_
    device_set(None, '<device>')`) junto con el id completo guardado
    en la config — dedupeado para no saturar el log en cada
    `reproducir()`. Esto permite comparar a mano, sin adivinar, si el
    string que la app cree que está mandando coincide EXACTO (mayúsculas,
    guiones, todo) con el nombre real del sink que devuelve `pactl`.

    **Pedido a Santiago para la próxima ronda** (mismo espíritu que la
    investigación de PipeWire/EasyEffects — "ground truth de tu
    máquina real" antes de seguir tocando código a ciegas), con la
    radio reproduciendo algo:
    ```bash
    pactl info | grep "Server Name"
    pactl list sinks short
    pactl list sink-inputs
    ```
    y en Configuración → Diagnóstico → "Ver log", copiar la línea más
    reciente que empiece con "MotorAudio: aplicando audio_output_
    device_set". Con esos tres datos se puede comparar el nombre del
    sink que la app cree que eligió contra el nombre real que
    PulseAudio/PipeWire conoce, y ver a qué sink está conectado el
    stream de la app AHORA MISMO (buscar la entrada de `sink-inputs`
    con `application.name` tipo "vlc"/vlc process, o el PID de la
    app).

    **La prueba más importante, el litmus test real**: de la salida de
    `pactl list sink-inputs`, anotar el número de índice del stream de
    la app (línea `Sink Input #<N>`) y probar moverlo A MANO:
    ```bash
    pactl move-sink-input <N> <nombre_del_sink_deseado_de_arriba>
    ```
    Esto separa las dos causas posibles de una vez: **si ese comando
    manual TAMBIÉN falla en mover el audio**, el problema es 100%
    externo a esta app — una política de ruteo de WirePlumber/PipeWire
    en su sistema que fuerza todo de vuelta al sink por defecto, algo
    que este programa no puede arreglar desde Python (haría falta
    tocar la configuración de WirePlumber en su PC, fuera del alcance
    de este repo). **Si el `pactl move-sink-input` manual SÍ mueve el
    audio correctamente**, entonces el problema es específicamente que
    la llamada de libVLC (`audio_output_device_set`) no está
    ejecutando ese mismo movimiento pese a la documentación — y la
    solución pasaría por que esta app haga el `pactl move-sink-input`
    ella misma (shell-out directo, mismo patrón ya usado en el
    proyecto para `wmctrl`/`git`/`yt-dlp`), identificando su propio
    stream por PID (`os.getpid()`, ya que python-vlc corre in-process,
    no como proceso aparte) en vez de confiar en el mecanismo interno
    de libVLC.

    No se tocó nada más de la lógica de aplicación en esta ronda —
    solo se agregó el log, sin cambiar el comportamiento real (mismo
    `module=None` de la ronda 61) hasta tener el diagnóstico real.
    Probado: suite de regresión completa sin fallos nuevos (mismos 3
    preexistentes de siempre) + confirmado que el log nuevo se escribe
    correctamente con el formato esperado.
63. ~~PR #2 traído de otra sesión — fundidos estandarizados, buffer
    configurable, y varias mejoras de UX~~ — pedido explícito: "Hay una
    rama ya pusheada a GitHub con cambios que hicimos en otra sesión...
    Traela, revisá el diff contra main, abrí el Pull Request, y si está
    todo bien mergealo." Rama `claude/fundidos-y-mejoras-explorador-022105`,
    11 archivos: (a) fade-in/out de Ventana 1 y 2 (crossfade)
    estandarizado a 400ms/500ms, configurable por separado
    (`duracion_fade_in_v2_ms`/`duracion_fade_out_v2_ms` en
    Configuración → Fade/Transiciones — reemplaza la vieja
    `duracion_fade_segundos` única, que queda solo por compatibilidad
    hacia atrás sin usarse más); (b) buffer de audio (`--file-caching`
    de libVLC) y retardo de arranque interno, antes fijos en el
    código, ahora configurables desde Configuración → Reproducción
    (`duracion_buffer_caching_ms`/`retardo_arranque_ms` — requieren
    reabrir la app, son argumentos de instancia de libVLC fijados al
    crearla); (c) bug real corregido — el ícono "ya reproducido" (y el
    historial persistente) se marcaba al ARMAR un ítem en rojo
    (`_asegurar_rojo_y_verde`, con el reproductor en silencio), no al
    reproducirlo de verdad — separado en pintar rojo (puramente
    visual, `_pintar_item`) vs. `marcar_realmente_reproducido()`
    (ícono + historial), llamado por el motor SOLO en el punto exacto
    donde el audio arranca de verdad (`_reproducir_fila`/
    `_iniciar_crossfade` en Ventana 2, `_reproducir_item`/
    `_reproducir_item_aleatorio` en Ventana 1 — esta última usa
    `marcar_icono_reproducido_item()`, sin historial, porque ya lo
    registra aparte con la ruta REAL resuelta); (d) Explorador:
    categoría raíz en negrita+MAYÚSCULAS, subcategoría directa en
    negrita, nivel 3+ sin cambios — solo estilo de pintado
    (`QFont.Capitalization`), nunca toca el texto real guardado en
    `biblioteca.json`; (e) "🎚 Editar audio" ahora prueba primero
    `mhwaveedit` (editor ultra liviano, corte/volumen/fade) de forma
    explícita antes de caer a la asociación de archivos del sistema
    (que solía abrir un REPRODUCTOR, no un editor); (f) Reproductor
    Auxiliar: nuevo menú contextual "➕ Agregar ítem específico..." /
    "🎲 Agregar ítem aleatorio..." (mismo criterio de aleatorio que ya
    usa el Musicalizador — resuelve un archivo random de una
    categoría, con el mismo no-repetir vía historial), exclusivo del
    Auxiliar (`PanelReproductor` ganó `permitir_agregar_item: bool`,
    off por defecto — Ventana 2/Emisión se llena sola vía
    Musicalizador/arrastre); (g) Ventana 1: los bloques quedan SIEMPRE
    expandidos (`tree.setItemsExpandable(False)`, se sacó la
    interacción de colapsarlos), y doble click en el TÍTULO de un
    bloque ahora arma el primer ítem hijo en vez de no hacer nada;
    (h) `MedidorNivelDecorativo` ahora anima con un rebote aleatorio
    (`QTimer` cada 120ms, sesgado hacia "casi lleno") mientras suena,
    en vez de quedar fijo en un valor — sigue siendo 100% decorativo
    (nunca mide audio real), pedido explícito de Santiago sabiendo que
    es ficticio.

    **Bug real encontrado y corregido durante la revisión, antes de
    mergear**: `PanelReproductor` ganó `marcar_realmente_reproducido()`
    en esta misma rama, pero los DOS wrappers que lo envuelven
    (`VentanaEmision`/`VentanaAuxiliar`) nunca lo delegaron — el MISMO
    patrón de bug ya documentado varias veces en este archivo ("cuando
    un wrapper delega en `PanelReproductor`, hay que delegar TODOS los
    métodos que el core necesita"). Sin este fix, Emisión rompía con
    un `AttributeError` silenciado dentro de un slot de Qt (indistinguible
    de "el play no respondió") cada vez que resumía después de un
    bloque automático de Publicidad, o en CUALQUIER transición con
    crossfade — es decir, prácticamente todo el uso real de Ventana 2
    en producción. Encontrado corriendo la suite de regresión completa
    ANTES de mergear (12 tests rompían exactamente ahí:
    `test_ciclo_automatico.py`, `test_musicalizador_gui.py`,
    `test_silencio_v2_y_menu.py`, `test_ventana2_estados.py`,
    `test_robustez_emision.py`, `test_pisador_race.py`,
    `test_dinesat_play_fundido_stops.py`,
    `test_auxiliar_paridad_y_exclusion.py`,
    `test_fmt_memoria_y_refill_verde.py`,
    `test_musicalizador_refill_crossfade.py`,
    `test_pisador_crossfade_stop_programador.py`,
    `test_ronda_7pedidos.py`, `test_ronda_rojo_verde_y_corte_v1.py`,
    `test_ciclo_deja_terminar_item.py` — confirmado que NINGUNO de
    estos fallaba contra `main` sin la rama nueva, así que no eran
    tests desactualizados sino una regresión real de la rama).
    Corregido agregando `marcar_realmente_reproducido(fila)` a ambos
    wrappers (delega a `self.panel.marcar_realmente_reproducido(fila)`,
    mismo patrón que ya usan `marcar_reproduciendo`/`marcar_siguiente`)
    — los 12 tests volvieron a pasar. Otros 4 tests locales que
    también fallaban (`test_audio_only_y_buffer.py`,
    `test_fade_in_declick_v1.py`, `test_ronda_ajustes_dinesat2.py`,
    `test_ronda_dinesat3.py`) resultaron ser tests VIEJOS de esta
    sesión que hardcodeaban comportamiento que esta rama cambió a
    propósito (la constante `ARGUMENTOS_VLC` pasó a ser una función
    parametrizable, el default de `duracion_fade_in_declick_v1_ms`
    subió de 60 a 400, y el timing del ícono "ya reproducido" es
    justamente el punto (c) de arriba) — no regresiones, confirmado
    revisando cada traceback a mano antes de descartarlos.

    PR #2 abierto y mergeado a `main` después del fix (suite de
    regresión completa corrida DOS VECES — antes y después del fix de
    delegación — sin fallos nuevos tras el fix; mismos 3 fallos
    preexistentes de siempre: `test_confirmaciones.py`,
    `test_log_git.py`, `test_ventana3.py`) + smoke test de arranque
    limpio. **Sigue sin poder confirmarse con audio/hardware real**
    (como siempre que se toca `core/audio_engine.py`): falta que
    Santiago confirme que los fundidos de 400ms/500ms se sienten bien,
    que el buffer configurable ayuda con el tartamudeo que reportó, y
    que el resto de los cambios de UX (categorías en mayúsculas,
    mhwaveedit, menú del Auxiliar, bloques siempre expandidos, medidor
    animado) se ven/comportan como esperaba.
64. ~~3 pedidos chicos: búsqueda del Explorador bloqueaba el árbol de
    categorías, "Eliminar de la biblioteca" sacada de Ventana 2/
    Auxiliar (riesgosa), y renovación del ícono de la app~~ — tres
    pedidos independientes:

    **a) Bug real corregido — buscar en el Explorador bloqueaba elegir
    categoría/moverse en el árbol**: `_buscar()` deshabilitaba por
    completo `tree_categorias` (`setEnabled(False)`) mientras había
    resultados de búsqueda mostrados en `tree_archivos` — un widget
    deshabilitado en Qt no recibe clicks, así que no había forma de
    elegir OTRA categoría (ni de usar los 3 botones de abajo con
    normalidad) hasta limpiar la búsqueda a mano con el botón "✕".
    Corregido sacando el `setEnabled(False)/(True)` por completo — el
    árbol queda SIEMPRE clickeable — y agregando
    `_salir_de_busqueda_si_corresponde()` (nuevo, `gui/ventana_explorador.py`):
    limpia `_en_busqueda`/el texto de la barra SIN refrescar
    `tree_archivos` (eso lo hace el llamador a continuación). Se llama
    desde `_on_categoria_seleccionada()` (antes esa función, mientras
    se buscaba, simplemente IGNORABA el cambio de categoría con un
    `return` — ahora sale de la búsqueda sola y muestra la categoría
    recién elegida con normalidad) y desde el arranque de
    `_nueva_categoria()`/`_nueva_subcategoria()`/`_eliminar_categoria()`
    (los "3 botones de abajo" del pedido) — así tocar cualquiera de
    los cuatro puntos de entrada (clickear una categoría, o cualquiera
    de esos 3 botones) limpia la búsqueda de forma consistente en vez
    de dejarla bloqueada o en un estado ambiguo.

    **b) "Eliminar de la biblioteca" sacada del menú contextual de
    Ventana 2 y el Auxiliar (pedido explícito, "riesgoso")**: Santiago
    fue explícito en que el menú de la lista de reproducción solo
    debe poder "Quitar de la lista" — nunca borrar el archivo de TODA
    la biblioteca desde ahí, ni por accidente. Confirmado con
    `AskUserQuestion` que el alcance es sacarla de LAS DOS ventanas
    (Ventana 2 Y Auxiliar comparten `PanelReproductor`, mismo riesgo
    en cualquiera de las dos). Eliminado de punta a punta: la acción
    "🗑 Eliminar de la biblioteca..." del menú contextual, el método
    `PanelReproductor._solicitar_eliminacion_definitiva()`, la señal
    `solicitud_eliminar_definitivo` (en `PanelReproductor`,
    `VentanaEmision` y `VentanaAuxiliar`), y el handler
    `MainWindow._eliminar_definitivo_de_biblioteca()` (ya sin ningún
    llamador). El menú de Ventana 2/Auxiliar queda con exactamente
    "✕ Quitar de la lista" / "ℹ Información..." / "🎚 Agregar/Quitar
    Pisador..." — la eliminación REAL de un archivo de la biblioteca
    sigue existiendo tal cual, pero solo desde Ventana 3 (Explorador),
    donde el operador tiene el contexto completo de qué está
    borrando (categoría, otros usos del mismo archivo, etc.).

    **c) Ícono de la aplicación renovado**: Santiago pasó una imagen
    de referencia (insignia cuadrada de esquinas redondeadas, degradé
    naranja, texto "D9" en negro) y pidió incorporarla "como ícono del
    programa para todo". Como la imagen llegó pegada en el chat (sin
    quedar accesible como archivo en el filesystem de este entorno),
    se reconstruyó con Pillow — mismo criterio ya usado en una ronda
    muy anterior para el ícono anterior ("regenerado con Pillow" — ver
    encabezado de este archivo) — en vez de aproximarla a mano con
    herramientas de dibujo: cuadrado redondeado con degradé radial
    naranja claro→oscuro, borde sutil más claro, brillo glossy
    translúcido en la mitad superior (estilo ícono de app/botón), y
    "D9" en negro bold (DejaVu Sans Bold), generado a 512x512 con
    supersampling 2x para antialiasing prolijo y reducido al tamaño
    final. Pillow se instaló en el venv SOLO para esta generación
    puntual y se desinstaló después — nunca fue ni es una dependencia
    de la app en tiempo de ejecución, no se tocó `requirements.txt`.
    No hizo falta tocar ningún código: tanto `main.py`
    (`app.setWindowIcon()` + el pixmap del `QSplashScreen` de
    arranque) como `assets/radiolinuxmadariaga.desktop` (el lanzador
    de escritorio) ya apuntaban al mismo archivo único,
    `assets/icono.png` — sobrescribirlo alcanza para que el ícono
    nuevo aplique en todos los puntos de la app de una sola vez (barra
    de tareas, ventana, splash de arranque, ícono del escritorio).

    Probado: `test_busqueda_y_eliminar_v2.py` (nuevo, dedicado — la
    búsqueda queda activa y el árbol de categorías nunca se
    deshabilita tras `_buscar()`; elegir otra categoría durante la
    búsqueda la limpia sola; tocar "＋ Categoría" durante la búsqueda
    también la limpia, incluso cancelando el diálogo; `PanelReproductor`
    ya no tiene la señal ni el método de eliminación definitiva;
    `MainWindow`/`VentanaEmision` ya no los reexponen; el menú
    contextual de Ventana 2, armado sin llegar a bloquear en
    `QMenu.exec()` — interceptando `QMenu.addAction()`, técnica más
    confiable en offscreen que parchear `QMenu.exec()` directamente —
    queda con exactamente Quitar/Información/Pisador, sin ningún
    rastro de "biblioteca") + suite de regresión completa sin fallos
    nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`,
    más los 4 tests locales ya diagnosticados en la ronda 63 como
    desactualizados, sin relación con este cambio) + smoke test de
    arranque limpio con el ícono nuevo cargando sin errores. Falta que
    Santiago confirme visualmente que el ícono se ve bien en su
    barra de tareas/escritorio real (la reconstrucción con Pillow es
    una aproximación fiel a la imagen de referencia, no un archivo
    idéntico pixel a pixel), y que buscar+navegar categorías y el
    menú de Ventana 2 se sienten como esperaba en el uso diario.
65. ~~Configuración: los fundidos de Ventana 1 y Ventana 2 agrupados
    juntos en la pestaña Fade/Transiciones~~ — episodio de
    diagnóstico + reorganización de UI, en dos partes:

    **Diagnóstico ("me dice que tengo la última versión")**: mismo
    bug ya documentado en la ronda 57 — la app compara la versión
    contra el UPSTREAM que la rama efectivamente checkouteada tiene
    configurado (`git rev-parse @{u}`), no siempre contra `main`. La
    PC de Santiago había quedado con el checkout en
    `claude/fundidos-y-mejoras-explorador-022105` (la rama de la
    ronda 63, ya mergeada a `main` en su momento) — esa rama estaba al
    día CONSIGO MISMA, pero 5 commits atrás de `main`, así que el
    chequeo de actualización comparaba contra la rama equivocada y
    decía "ya estás al día" con total literalidad, aunque `main` ya
    tuviera todo lo nuevo. Confirmado con `git status`/`git branch -vv`
    reales antes de tocar nada (mismo criterio de "ground truth de tu
    máquina real" ya establecido) — sin cambios locales sin guardar,
    solo hacía falta `git checkout main && git pull origin main`.
    **Regla reafirmada para el futuro**: cada vez que se prueba algo
    puntual en una rama de feature directo en la PC real, hay que
    volver a `git checkout main` al terminar — quedarse en la rama de
    feature hace que el chequeo de actualización compare contra ESA
    rama de ahí en más, no contra `main`, aunque `main` en GitHub siga
    avanzando.

    **"Me retrocedió una actualización que hice por la otra rama"**:
    tras el `git checkout main`, Santiago sintió que se había perdido
    un pedido anterior (fundidos 400ms/500ms configurables por
    ventana). Investigado: `origin/claude/fundidos-y-mejoras-explorador-022105`
    no tenía NINGÚN commit por encima de lo ya mergeado a `main` (`git
    log origin/main..origin/rama` vacío) — nada se perdió a nivel de
    git, los valores 400ms/500ms YA estaban en `main` desde la ronda
    63. Lo que SÍ era cierto, revisando el pedido original de Santiago
    palabra por palabra ("Configuración por ventana separada en el
    menú configuraciones"): los 4 controles de fundido vivían
    DISPERSOS en dos pestañas distintas — los de Ventana 2
    (`duracion_fade_in_v2_ms`/`duracion_fade_out_v2_ms`) en "Fade /
    Transiciones", los de Ventana 1
    (`duracion_fade_in_declick_v1_ms`/`duracion_fade_out_v1_ms`)
    perdidos en medio de "Reproducción y Automatización" junto a
    tolerancia de silencio/buffer/reintentos — nunca agrupados "por
    ventana" como pedía el texto original. Corregido en
    `gui/ventana_configuracion.py`: `_crear_tab_fade()` ahora arma DOS
    `QGroupBox` dentro de la misma pestaña "Fade / Transiciones" —
    "Ventana 1 — Publicidad / Tanda" (Fade IN/OUT) y "Ventana 2 —
    Emisión" (checkbox de crossfade + Fade IN/OUT) — y los dos spin
    box de Ventana 1 se sacaron por completo de
    `_crear_tab_reproduccion()` (que conserva el resto: avanzar en
    error, reintentos, tolerancia de silencio x2, umbral, bajada de
    Pisador, buffer, retardo de arranque — nada de eso es "fundido").
    Los NOMBRES de atributo (`spin_fade_in_declick_v1`,
    `spin_fade_out_v1`, `spin_fade_in_v2`, `spin_fade_out_v2`) y las
    claves de `config_general.json` que leen/escriben NO cambiaron —
    solo se movió DÓNDE se construyen los widgets, así
    `_cargar_valores_en_ui()`/`_guardar_y_cerrar()` siguieron intactos
    sin tocar una línea.

    Probado con `test_fade_config_reagrupado.py` (nuevo, dedicado): la
    pestaña "Fade / Transiciones" tiene los dos `QGroupBox` con los
    títulos correctos, los 4 spin box viven físicamente dentro de esa
    pestaña (no de "Reproducción"), los defaults siguen siendo
    400ms/500ms en las cuatro, y guardar desde la UI reorganizada
    sigue escribiendo exactamente las mismas claves de siempre en
    `config_general.json` (round-trip completo) — + suite de
    regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre + los 4 tests locales ya diagnosticados
    en la ronda 63 como desactualizados, sin relación con este
    cambio) + smoke test de arranque limpio. Falta que Santiago
    confirme que la pestaña Fade/Transiciones reorganizada, con
    "Ventana 1"/"Ventana 2" agrupados por separado, es lo que tenía en
    mente al pedir "configuración por ventana separada".
66. ~~Ventana 1: archivo faltante ya no corta el aire hacia Emisión +
    Ventana 2: el último FMT ahora sobrevive a un reinicio de la
    app~~ — dos bugs reales de fondo, uno por ventana, pedidos en el
    mismo mensaje:

    **VENTANA 1 — "cuando encuentra un item que no está en el
    explorador, se detiene y pasa a la ventana 2"**: la causa real era
    que un archivo faltante SOLO se detectaba REACTIVAMENTE — recién
    cuando `MotorAudio` ya había intentado reproducirlo de verdad y
    fallaba (`error_reproduccion` → `GestorPublicidad._on_error()`).
    Si eso pasaba varias veces seguidas (varios archivos faltantes en
    fila, ej. toda una carpeta movida/renombrada), la cascada de
    `reintentos_maximos` (config "Fallos consecutivos antes de
    detenerse") se agotaba y terminaba cortando el aire hacia Emisión
    — exactamente el síntoma reportado. Corregido moviendo la
    detección a `GestorPublicidad._item_valido()` (`core/playlist_manager.py`)
    — el ÚNICO lugar por el que pasan TODOS los skip-loops de avance
    del archivo (`_avanzar()`, `_asegurar_rojo_y_verde()`,
    `_primer_item_valido_de()`, `disparar_bloque()`, etc., más de 8
    puntos de llamada) — agregando `os.path.exists(ruta)` ANTES de
    intentar reproducir nada: un archivo faltante ahora se saltea
    SIEMPRE de inmediato, exactamente igual que un ítem con vigencia
    vencida (nunca cuenta como "fallo de reproducción", nunca consume
    presupuesto de `reintentos_maximos`, nunca puede agotar la
    cascada). Nuevo ícono "X roja" (pedido explícito, `ROL_ITEM_CON_ERROR`
    + `icono_error()` en `gui/styles.py`, mismo patrón de `QPainter`
    cacheado que ya usa `icono_reproducido()`) puesto/sacado por
    `VentanaPublicidad.marcar_item_con_error()` — se sincroniza EN
    VIVO con el estado real del archivo en disco cada vez que
    `_item_valido()` evalúa el ítem: aparece la primera vez que se
    detecta faltante, y se saca solo si el operador corrige la ruta o
    reconecta el archivo (sin pisar el tilde verde de "ya reproducido"
    si el ítem ya lo tenía de antes — restaura ESE ícono en vez de
    dejarlo en blanco). El ítem NUNCA se toca ni se elimina de la
    biblioteca ni del árbol — pedido explícito, sigue ahí para que
    Santiago lo corrija cuando pueda. Alcance a propósito: la X roja
    cubre específicamente "archivo faltante en disco" (lo que pidió
    Santiago, "no está en el explorador") — un archivo que SÍ existe
    pero está corrupto/con codec no soportado sigue yendo por el
    camino reactivo de siempre (`_on_error`/cascada de reintentos), sin
    cambios ahí.

    **VENTANA 2 — "no lee el último FMT... llega al final de la lista
    y no carga otro ciclo, se detiene"**: confirmado con Santiago que
    la memoria del último FMT (`config/settings.obtener_ultimo_fmt()`,
    ronda 34) SÍ debía aplicar al reabrir. La causa real: al restaurar
    la playlist de Emisión desde disco
    (`GestorPlaylist._restaurar_desde_disco()`), se restauraban los
    ÍTEMS de una serie ya generada por el Musicalizador, pero NUNCA el
    hecho de que `self._formato_musicalizador_activo` seguía
    "activo" — ese atributo volvía a `None` en cada reinicio de la
    app, así que el mecanismo de refill
    (`_marcar_siguiente_con_refill()`, que solo dispara si
    `_formato_musicalizador_activo is not None`) quedaba inerte para
    siempre sobre una lista restaurada, aunque esa lista viniera 100%
    de un FMT. Corregido persistiendo el nombre del formato activo
    junto con los ítems en `config/data/playlist_emision.json`
    (`config/settings.py`: nueva clave `formato_musicalizador_activo`
    en `PLAYLIST_EMISION_VACIA`/`cargar_playlist_emision()` — merge
    con default `None`, no rompe una instalación vieja sin esa clave)
    y restaurándolo en el mismo punto donde se restauran los ítems,
    ANTES de marcar rojo/verde. Segundo detalle real encontrado en el
    camino: `_restaurar_desde_disco()` marcaba el verde restaurado con
    `panel.marcar_siguiente()` DIRECTO, no con el envoltorio
    `_marcar_siguiente_con_refill()` que ya centraliza el chequeo de
    refill en TODO el resto del archivo (regla ya establecida, ronda
    34, justo para evitar este tipo de bug) — si el verde restaurado
    resultaba ser el ÚLTIMO ítem disponible (caso típico: se cerró la
    app justo con la serie casi terminada), el refill nunca se
    disparaba ni siquiera cuando `_formato_musicalizador_activo` ya
    estuviera bien restaurado. Corregido usando
    `_marcar_siguiente_con_refill()` también ahí — el refill ahora
    puede dispararse en el mismo instante de la restauración si
    corresponde, sin esperar a que algo más vuelva a marcar verde.

    Probado con `test_v1_archivo_faltante_y_v2_fmt_restart.py` (nuevo,
    dedicado): Ventana 1 — `_item_valido()` rechaza un archivo
    faltante y marca la X sin tocar el resto; un bloque con T1 roto
    (ruta inexistente) + T2/T3 reales (archivos temporales de verdad)
    arranca DIRECTO en T2 sin sonar T1, sin consumir la cascada de
    reintentos, sin que Emisión arranque nunca por su culpa, con T1
    intacto en el árbol; corregir la ruta de T1 a un archivo real hace
    que vuelva a ser válido y saca la X sola. Ventana 2 — el formato
    activo se persiste en `playlist_emision.json`; una `VentanaEmision`
    + `GestorPlaylist` TOTALMENTE nuevos (simulando un reinicio real de
    la app, no reutilizar el panel ya poblado) restauran el formato y
    los 2 ítems guardados sin duplicar, y el refill se dispara YA
    durante la propia restauración porque el verde restaurado
    resultaba ser el último ítem disponible. **Bug de infraestructura
    de testing encontrado y corregido en el camino (no de la app)**:
    el nuevo chequeo de `os.path.exists()` rompió 17 scripts de
    regresión preexistentes de rondas anteriores que usaban rutas
    ficticias sin crear nunca (`"/tmp/t1.mp3"`, `"/tmp/musica_a.mp3"`,
    etc.) como stand-in de un archivo real — confirmado comparando
    cada fallo contra el mismo síntoma exacto (la ruta ficticia nunca
    existió en disco) antes de tocar nada; se crearon esas 81 rutas
    ficticias como archivos vacíos reales en `/tmp` para esta corrida
    de regresión (no se tocó la lógica de ningún test), y con eso los
    17 volvieron a pasar sin cambios — confirma que el fix es un
    agregado quirúrgico sin ningún otro efecto colateral sobre
    comportamiento ya probado. + suite de regresión completa sin
    fallos nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`, +
    los 4 tests locales ya diagnosticados en la ronda 63/65 como
    desactualizados por cambios de comportamiento intencionales,
    sin relación con este cambio) + smoke test de arranque limpio.
    **Sigue sin poder probarse con audio/VLC real** (como siempre que
    se toca este motor): falta que Santiago confirme con su biblioteca
    real que un archivo movido/borrado ya no corta el bloque de
    Publicidad (queda marcado con la X roja, se saltea solo, sigue en
    el árbol para corregirlo cuando pueda), y que el último FMT
    efectivamente retoma un ciclo nuevo al reabrir la app en vez de
    quedarse en silencio al agotar la lista restaurada.
67. ~~Bug real, encontrado en la práctica apenas 5 minutos después de
    la ronda anterior: doble click en el título de un bloque dejó de
    arrancar cuando el primer ítem está roto~~ — reporte textual de
    Santiago: "cuando selecciono el bloque de la ventana 1, ya no
    marca en rojo el primer item y reproduce automaticamente... hay
    item marcados como error con la cruz, deberia dejar al menos
    poder seleccionarlo, saltear ellos, e ir reproduciendo uno a uno
    todo los item (que se puedan) del bloque horario".

    **Causa real**: `VentanaPublicidad._on_doble_click_item()` (doble
    click en el TÍTULO de un bloque, agregado en la ronda 63)
    resolvía `item.child(0)` a ciegas — el hijo LITERAL en la
    posición 0 del bloque, sin pasar por ninguna validación — y
    emitía ESE ítem puntual. `GestorPublicidad._on_doble_click()`
    hacía `if not self._item_valido(item): return` sin ningún intento
    de saltear al siguiente — si ese primer hijo resultaba ser el que
    la ronda anterior (66) recién empezó a poder marcar como "archivo
    faltante" (X roja), doble click en el título del bloque no hacía
    absolutamente NADA, ni sonaba, ni saltaba, ni avisaba. Antes de la
    ronda 66 esto pasaba desapercibido porque casi cualquier ruta no
    vacía se consideraba "válida" (no había chequeo de existencia en
    disco) — la ronda 66 no introdujo el bug, lo hizo VISIBLE por
    primera vez, exactamente el patrón "esto ya estaba mal, recién
    ahora se nota" que motivó revisar a fondo en vez de asumir una
    regresión aislada.

    **Corregido centralizando en el lugar que YA sabía saltear ítems
    inválidos dentro de un bloque** (`_primer_item_valido_de()` /
    `_reproducir_primero_del_bloque()`, usado desde antes por el botón
    Play sobre un bloque seleccionado) en vez de mantener una segunda
    implementación paralela sin ese salteo — mismo espíritu que la
    regla ya documentada en este archivo sobre `_avanzar()`/
    `_iniciar_crossfade()` de Ventana 2 ("caminos paralelos que no
    comparten código" es una clase de bug recurrente en este
    proyecto). `_on_doble_click_item()` (GUI) ya NO resuelve nada —
    emite el nodo de bloque tal cual; `GestorPublicidad._on_doble_click()`
    (core) detecta `item.parent() is None` (nodo de bloque) y delega
    en `_reproducir_primero_del_bloque(item)`.

    **Mismo defecto de fondo encontrado y corregido en dos lugares más
    que comparten la causa raíz** (`primer_item_reproducible()`,
    `gui/ventana_publicidad.py` — devuelve el hijo LITERAL en la
    posición 0 del primer bloque con hijos, sin validar nada, usado
    como fallback en dos puntos de `core/playlist_manager.py`):
    - `_asegurar_rojo_y_verde()`: si el primer ítem "reproducible" que
      encuentra está roto, ahora avanza con `tree.itemBelow()` hasta
      el próximo VÁLIDO antes de armarlo en rojo (en vez de armar
      directamente un ítem que nunca va a sonar).
    - `_reproducir_seleccion_o_actual()` (botón Play): mismo salteo,
      pero ACOTADO a propósito al caso "no hay nada armado NI
      seleccionado" (el fallback genuino de arrancar desde cero) — si
      el operador armó o seleccionó a mano un ítem roto en particular,
      Play sigue sin hacer nada sobre ESE ítem puntual, mismo criterio
      ya establecido en `_on_doble_click` (una elección explícita del
      operador sobre un ítem inválido no debe "adivinar" otra cosa
      distinta a lo que pidió).

    Probado con `test_bloque_saltea_primero_roto.py` (nuevo, dedicado,
    reproduce el reporte EXACTO de Santiago con un bloque de 3 tandas
    donde la primera tiene ruta inexistente): doble click en el título
    del bloque saltea la tanda rota y arranca en la segunda (con T1
    intacto en el árbol, nunca tocado); el botón Play sin nada armado
    ni seleccionado hace lo mismo; `_asegurar_rojo_y_verde()` arma el
    primer ítem VÁLIDO (no el literal primero) y deja el verde en el
    siguiente después de ese — + suite de regresión completa sin
    fallos nuevos (mismos 3 fallos preexistentes de siempre + los 4
    tests locales ya diagnosticados como desactualizados en rondas
    anteriores, sin relación con este cambio) + smoke test de arranque
    limpio. **Sigue sin poder probarse con audio/VLC real**: falta que
    Santiago confirme que ahora, con su biblioteca real (que puede
    tener archivos faltantes en cualquier posición de un bloque,
    incluida la primera), seleccionar/doble-clickear un bloque siempre
    encuentra y arranca desde el primer ítem realmente reproducible,
    saltando cualquier ítem marcado con la X en el camino, sin importar
    en qué posición esté.
68. ~~Corrección de la ronda anterior: doble click en un bloque de V1
    NO debe reproducir (solo Play/horario) + el refill del FMT no
    disparaba cuando el rojo era el último ítem~~ — Santiago probó la
    ronda 67 (que arreglaba el salteo de ítems rotos al doble-clickear
    un bloque) y reportó "hay un error que no puede suceder": el fix
    de esa ronda hacía que doble click en el TÍTULO de un bloque
    arrancara audio de una — violando la regla explícita "La ventana 1
    solo ingresa a reproducir cuando: a) es su momento horario del
    bloque, b) cuando manualmente le doy play" — y de paso, como ese
    camino nunca pasaba por `al_arrancar_manual` (el único mecanismo
    que corta Emisión antes de que Ventana 1 empiece a sonar), el
    audio de V1 sonaba ENCIMA del de Ventana 2 — violando también la
    regla de exclusión mutua ya establecida ("NUNCA una ventana pisará
    en audio a la otra"). Aparte, reportó el problema más grande de
    esta ronda: el Musicalizador/FMT de Ventana 2 seguía sin cargar un
    ciclo nuevo al llegar al final de la lista, ni siquiera al abrir
    la app y reproducir a mano el último ítem restaurado.

    **a) V1: doble click en un bloque vuelve a ser "solo ARMA, nunca
    reproduce" (pedido explícito, mismo criterio que cualquier tanda
    suelta)**: `GestorPublicidad._on_doble_click()`
    (`core/playlist_manager.py`) ya no llama a
    `_reproducir_primero_del_bloque()` (que arranca audio) en la rama
    de nodo de bloque — ahora solo resuelve `primero =
    self._primer_item_valido_de(item)` (el mismo salteo de ítems rotos
    de la ronda anterior, intacto) y deja que `item = primero` caiga
    en la MISMA lógica de siempre (armar en rojo si está en silencio,
    encolar en verde si está sonando) — sin duplicar código, un solo
    camino para tanda suelta y título de bloque. Como nunca se llama a
    `_reproducir_item()`, no hay audio que overlappee con Emisión — el
    bug de "pisar" a Ventana 2 queda resuelto como consecuencia directa,
    sin tocar nada de la coordinación de `al_arrancar_manual`. Los
    ÚNICOS dos caminos que siguen arrancando audio de verdad en V1 son
    `_reproducir_seleccion_o_actual()` (botón Play, ya llama a
    `al_arrancar_manual` para cortar Emisión) y `disparar_bloque()`
    (el Scheduler, por horario) — ninguno de los dos se tocó.

    **b) V2: LA CAUSA DE FONDO real del refill que "no carga otro
    ciclo" — un bug de PRECEDENCIA, no de que el mecanismo faltara**:
    investigando el reporte de Santiago ("SIEMPRE cuando se pinte de
    rojo el último item... cargue otro ciclo") se encontraron DOS
    problemas superpuestos en `core/gestor_emision.py`:
    1. **Cuatro lugares distintos** (`_asegurar_rojo_y_verde()`,
       `_avanzar()`, `_iniciar_crossfade()`,
       `_recalcular_verde_tras_nuevo_rojo()`) calculaban "qué fila
       debería quedar en verde" con la MISMA lógica casi-duplicada —
       y los CUATRO tenían el mismo agujero: cuando el candidato a
       verde quedaba fuera de rango (la fila roja/actual es el ÚLTIMO
       ítem disponible), directamente se rendían a `-1` SIN pasar
       nunca por `_marcar_siguiente_con_refill()` — el ÚNICO punto que
       dispara el refill del Musicalizador (centralizado ahí desde la
       ronda 34c, a propósito, para evitar justo este tipo de bug). Es
       decir: el refill NUNCA se disparaba en ningún escenario donde
       el rojo llegara a ser el último ítem por un camino que NO fuera
       el caso límite de "serie de 1 solo ítem" (que sí tenía su
       propia red de emergencia dedicada, agregada en la ronda 30).
       Corregido centralizando el cálculo en un helper NUEVO,
       `_resolver_candidata_verde(fila_base)` — usado por los 4
       lugares — que, si el candidato queda fuera de rango y hay un
       formato FMT activo, genera una serie nueva ANTES de rendirse.
    2. **El bug MÁS de fondo, encontrado recién al escribir el test**:
       incluso con el helper centralizado, `repetir_lista_al_finalizar`
       (`True` por defecto en `config_general.json`) se chequeaba
       ANTES que el formato FMT activo en los 3 lugares que decidían
       "qué pasa cuando no hay más ítems" (el candidato a verde en el
       helper nuevo, y los dos chequeos de límite de la fila ROJA en
       `_avanzar()` y `_iniciar_crossfade()`) — con la config por
       defecto, esto significaba que un ciclo de FMT agotado
       simplemente ENVOLVÍA de vuelta al ítem 0 y REPETÍA la misma
       serie vieja para siempre, en vez de generar contenido nuevo —
       la causa real y exacta de "no carga otro ciclo", reproducible
       con la config de fábrica de cualquier instalación nueva.
       Corregido invirtiendo la prioridad en los 3 lugares: con un
       formato activo, SIEMPRE se intenta generar una serie nueva
       PRIMERO; "repetir al finalizar" queda como red de seguridad
       solo si el formato resultó estar roto (no generó nada) o si no
       hay ningún FMT activo (lista estática armada a mano).
    **Efecto colateral esperado, no un bug**: con este fix, una serie
    de pocos ítems (1 o 2) ahora encadena el refill siguiente de forma
    MÁS PROACTIVA que antes — incluso en la propia carga inicial
    (`iniciar_musicalizador()`), si el primer/único ítem generado
    resulta ser también el último, el refill se dispara ya mismo, en
    vez de esperar reactivamente a que `_avanzar()` se topara con el
    límite más tarde. Varios tests preexistentes de rondas anteriores
    (`test_fmt_memoria_y_refill_verde.py`, `test_musicalizador_fixes.py`,
    `test_musicalizador_gui.py`, `test_ronda_afinado_musicalizador.py`)
    tenían aserciones que codificaban literalmente el conteo EXACTO
    del comportamiento viejo (ej. "una serie de 1 solo ítem carga
    exactamente 1, sin verde") — actualizadas para reflejar el nuevo
    comportamiento proactivo, confirmado que no eran regresiones sino
    aserciones desactualizadas por un cambio de comportamiento
    deliberado (mismo criterio ya aplicado varias veces en este
    archivo).

    Probado con `test_v1_no_autoplay_v2_refill_siempre.py` (nuevo,
    dedicado, 12 verificaciones): doble click en el título de un
    bloque NUNCA dispara `motor.reproducir()` ni con V1 en silencio ni
    con V2 sonando (y V2 nunca se corta, porque nada la interrumpe);
    Play (botón) SÍ reproduce y SÍ corta Emisión; `disparar_bloque()`
    (horario) sigue reproduciendo con normalidad, sin cambios;
    `_asegurar_rojo_y_verde()` con el rojo en el último ítem de una
    serie FMT genera una serie nueva en vez de dejar el verde vacío;
    el escenario EXACTO reportado por Santiago (abrir la app, elegir a
    mano con doble click el último ítem cargado y "reproducirlo")
    dispara un ciclo nuevo — + actualización de las 4 suites
    preexistentes mencionadas arriba + suite de regresión completa sin
    fallos nuevos (mismos 3 fallos preexistentes de siempre:
    `test_confirmaciones.py`, `test_log_git.py`, `test_ventana3.py`, +
    4 tests locales ya diagnosticados como desactualizados desde la
    ronda 63, confirmados sin relación con este cambio corriendo la
    misma batería contra el código sin modificar vía `git stash`) +
    smoke test de arranque limpio. **Sigue sin poder probarse con
    audio/VLC real**: falta que Santiago confirme que doble click en
    un bloque de Ventana 1 ya nunca arranca a sonar solo (solo Play o
    el horario), que ya no hay superposición de audio entre V1 y V2
    bajo ninguna circunstancia, y que el Musicalizador/FMT de Ventana 2
    ahora sí encadena ciclos nuevos sin fin — tanto en uso continuo
    normal como en el escenario puntual de abrir la app y retomar a
    mano el último ítem de una lista restaurada.
69. ~~Autoscroll de Ventana 2 al llenarse + compresor de salida
    configurable~~ — dos pedidos independientes:

    **a) Autoscroll de Emisión con "aire" (pedido explícito: "una vez
    que se va llenando la ventana 2... me gustaría ir viendo siempre
    hacia abajo de manera automática... dejando un aire de espacio")**:
    `PanelReproductor.agregar_item()` (`gui/panel_reproductor.py`)
    ahora llama a `_scroll_al_final_con_aire()` (nuevo) después de cada
    alta — mueve la barra vertical al máximo y le resta el alto de UNA
    fila (`tree.sizeHintForRow(0)`), así el último ítem agregado queda
    a la vista sin quedar pegado al borde inferior. Como `agregar_item()`
    es el ÚNICO punto de alta compartido por el drag&drop manual y por
    `_generar_serie_musicalizador()` (el refill del FMT), cubre "se van
    cargando los ciclos de FMT" de una sola vez, sin tocar nada del
    motor. Aplica igual a Ventana 2 y a la Auxiliar (mismo
    `PanelReproductor` compartido) — nunca borra ítems anteriores,
    solo mueve el scroll.

    **b) Compresor de salida configurable (pedido explícito: "incluí
    un compresor... Entrada de Audio, Ratio, Ataque, Release, Salida
    (Ganancia de Compensación)")**: a diferencia de los DOS intentos
    previos de procesar el audio de salida (control remoto de
    EasyEffects, rondas 37-51; filter-chain nativo de PipeWire, ronda
    52) — ambos DESCARTADOS a pedido explícito de Santiago en la ronda
    55 porque prefería manejar el procesamiento por FUERA de esta
    app — este compresor vive DENTRO de cada `MotorAudio`, usando el
    filtro de audio NATIVO que ya trae libVLC de fábrica (módulo
    `"compressor"`), sin depender de ningún proceso externo ni tocar
    la configuración del sistema — no contradice la decisión de la
    ronda 55 porque no es un procesador de sistema, es parte del motor
    de audio que esta app ya usa. `core/audio_engine.py` ganó
    `_argumentos_compresor(audio_cfg)`, que arma
    `--audio-filter=compressor` + los 5 flags reales del módulo
    (`--compressor-threshold`, `--compressor-ratio`,
    `--compressor-attack`, `--compressor-release`,
    `--compressor-makeup-gain`) SOLO si `compresor_activado` está en
    `True` — mapeo 1 a 1 con lo pedido: "Entrada de Audio" = umbral
    (threshold, dB), Ratio, Ataque (ms), Release (ms), "Salida
    (Ganancia de Compensación)" = makeup-gain (dB). `_argumentos_vlc()`
    los concatena con los argumentos ya existentes de buffer/`--no-video`.
    Mismo criterio ya establecido para `duracion_buffer_caching_ms`
    (ronda de la PR #2): es un argumento de INSTANCIA de libVLC, fijo
    al crear cada `MotorAudio` — cambiar un valor en Configuración
    requiere reabrir la app para aplicar, avisado explícitamente en la
    UI. Nueva sección `compresor_*` en `config_general.json → audio`
    (desactivado por defecto — una instalación existente nunca empieza
    a comprimir sola) y un `QGroupBox` nuevo en Configuración → Audio
    con el checkbox + los 5 campos, rangos acotados a los límites
    reales del módulo de libVLC (threshold -30/0 dB, ratio 1-20,
    ataque 1.5-400ms, release 2-800ms, makeup-gain 0-24dB).

    **Bug real encontrado y corregido en el camino, mientras se
    probaba el compresor**: `cargar_configuracion()` (`config/settings.py`)
    devolvía `dict(CONFIG_POR_DEFECTO)` en una instalación TOTALMENTE
    nueva (sin `config_general.json` todavía) — una copia SOMERA, no
    profunda. Como las secciones anidadas (`audio`, `fade`, etc.) son
    diccionarios, `dict(CONFIG_POR_DEFECTO)` copia el diccionario de
    NIVEL SUPERIOR pero cada sección sigue siendo el MISMO objeto que
    `CONFIG_POR_DEFECTO["audio"]` — cualquier código que haga `cfg =
    cargar_configuracion(); cfg["audio"][clave] = valor` (exactamente
    lo que hace `VentanaConfiguracion._guardar_y_cerrar()`) en el
    primerísimo arranque de una instalación nueva terminaba mutando el
    propio `CONFIG_POR_DEFECTO` global EN MEMORIA, silenciosamente,
    para el resto del proceso — sin romper nada visible de inmediato
    (el archivo en disco quedaba bien escrito igual), pero corrompiendo
    los valores "de fábrica" en memoria. Corregido con
    `copy.deepcopy(CONFIG_POR_DEFECTO)` en los dos lugares que
    devuelven los valores por defecto tal cual (instalación nueva, y
    el fallback ante un JSON corrupto).

    Probado con `test_autoscroll_y_compresor.py` (nuevo, dedicado):
    `_scroll_al_final_con_aire()` deja el scroll exactamente a un
    "aire" de una fila del fondo (nunca pegado), con clamp a 0 en el
    caso límite de un rango más chico que una fila, y `agregar_item()`
    la dispara siempre; `_argumentos_compresor()`/`_argumentos_vlc()`
    arman los flags correctos con el compresor activado y desactivado,
    con defaults de libVLC ante una clave faltante, y sin romper el
    caso ya existente sin compresor; `MotorAudio()` sigue degradando
    limpio con el compresor activado en config (sin libVLC en el
    sandbox); una instalación nueva tiene el compresor desactivado por
    defecto (confirma el fix de `cargar_configuracion()`); los 5
    campos + el checkbox existen en la UI y el round-trip de
    guardar/recargar refleja los valores editados — + suite de
    regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre + 4 tests locales ya diagnosticados como
    desactualizados desde la ronda 63, sin relación con este cambio) +
    smoke test de arranque limpio. **Sigue sin poder probarse con
    audio/VLC real** (el sandbox no tiene libVLC instalado, y menos
    aún el módulo de filtro "compressor" compilado): falta que
    Santiago confirme (1) que el autoscroll de Ventana 2 se siente
    natural al ir llenándose con ciclos del Musicalizador, sin resultar
    molesto, y (2) que al activar el compresor y reabrir la app,
    escucha el efecto esperado en el aire — si algún valor de los 5
    campos no tiene efecto audible, la primera sospecha debería ser el
    nombre exacto del flag de libVLC (`--compressor-*`), verificable
    con `cvlc --longhelp --advanced | grep -A2 compressor` en su
    notebook real.
70. ~~Compresor: confirmar que se aplica sobre la salida Master +
    pestaña "Procesador" nueva (en curso, esperando el preset de
    EasyEffects)~~ — Santiago probó la ronda anterior ("No noto ningún
    cambio") y pidió dos cosas: (a) verificar que el compresor se
    aplique sobre la salida Master configurada, y (b) incorporar los 2
    efectos reales de su preset de EasyEffects "Radio Tuyú" a una
    pestaña nueva "Procesador" (o la misma Audio, con scroll).

    **a) Bug real de alcance encontrado y corregido**: el compresor
    (argumento de INSTANCIA de libVLC, ver ronda anterior) se aplicaba
    de forma IDÉNTICA a TODOS los `MotorAudio` del programa —
    Publicidad, Emisión, Auxiliar, Pisador, **Y TAMBIÉN el Previo de
    Ventana 3** (`GestorExplorador`, que usa la salida de Preescucha,
    pensada para los parlantes de monitoreo de la PC, no la que va al
    aire) — nunca estuvo realmente acotado a "la salida Master", pese
    a que el pedido original ya decía "compresor de salida de audio".
    Corregido con un parámetro nuevo, `aplicar_compresor: bool = True`
    en `MotorAudio.__init__` (`core/audio_engine.py`) — `True` por
    defecto, así que Publicidad/Emisión/Auxiliar/Pisador y el motor
    "entrante" de un crossfade (que hereda el criterio del motor que
    lo originó, vía `self._aplicar_compresor`) siguen recibiéndolo sin
    tocar nada; `GestorExplorador.__init__` (`core/playlist_manager.py`)
    es el ÚNICO llamador que ahora pasa `aplicar_compresor=False`
    explícito. **Diagnóstico agregado** (mismo criterio ya usado para
    la selección de dispositivo de audio en rondas anteriores): con el
    compresor activado, cada `MotorAudio` nuevo deja una línea en
    `log_aplicacion.txt` con el string EXACTO que se le manda a
    libVLC (`MotorAudio: compresor activado, argumentos de instancia
    libVLC: [...]`) — comparable a mano contra un `cvlc
    --audio-filter=compressor --compressor-threshold=... archivo.mp3`
    corrido suelto en la terminal, para aislar si el problema es esta
    app o el propio filtro de libVLC en su instalación. **Este
    diagnóstico es la pieza clave pendiente**: como el sandbox no
    tiene libVLC instalado, no hay forma de confirmar acá si el filtro
    realmente produce un efecto audible — la sospecha más probable
    de "no noto ningún cambio" sigue siendo que haga falta REABRIR la
    app después de activar el compresor en Configuración (es un
    argumento de instancia, fijo al crear cada motor, no se aplica en
    caliente) — pendiente que Santiago confirme si ya lo había hecho.

    **b) Pestaña "Procesador" nueva, compresor mudado ahí**: se creó
    `_crear_tab_procesador()` (`gui/ventana_configuracion.py`), una
    pestaña nueva entre Audio y Fade/Transiciones, con el grupo del
    Compresor MUDADO desde Audio (mismos widgets/nombres de atributo,
    solo cambió qué pestaña los contiene) — pensada como el lugar
    único para todo el procesamiento de audio de esta app, incluidos
    los 2 efectos del preset de EasyEffects que Santiago pidió sumar.
    Envuelta en `QScrollArea` (`setWidgetResizable(True)`, pedido
    explícito: "agregá las barras para hacer scroll hacia abajo y
    arriba") — deja margen para sumar más efectos más adelante sin
    tener que agrandar el diálogo. **Pendiente, bloqueado por falta de
    datos reales**: Santiago pidió leer su archivo de preset de
    EasyEffects llamado "Radio Tuyú" (2 efectos) e incorporarlos con
    sus valores reales — ese archivo vive en SU máquina (típicamente
    `~/.config/easyeffects/output/Radio Tuyú.json`), no accesible
    desde este sandbox ni pegado en el chat todavía. Se le pidió
    explícitamente el contenido del archivo (pegado como texto, o los
    valores desde la propia interfaz de EasyEffects) para poder leer
    QUÉ 2 efectos son y con qué valores reales, en vez de adivinar —
    ninguna función nueva de UI se agregó a ciegas para esto, a
    propósito (mismo criterio de "nunca inventar parámetros/nombres
    de control sin confirmarlos contra la fuente real" ya aplicado en
    la investigación de Calf/PipeWire de la ronda del filter-chain).

    Probado con `test_compresor_scope_master.py` (nuevo, dedicado):
    `MotorAudio()` por defecto aplica el compresor,
    `GestorExplorador` (Previo) NO lo aplica, el motor "entrante" de
    un crossfade hereda el criterio de su origen, el log se escribe
    con los argumentos EXACTOS solo cuando el compresor está activado
    (nunca de más) — + regresión de `test_autoscroll_y_compresor.py`
    (los `hasattr()` sobre los widgets del compresor siguen pasando
    igual, sin importar en qué pestaña viven ahora) + actualización de
    `test_fade_config_reagrupado.py` (ronda 65), que asumía índices de
    pestaña FIJOS (`tabs.widget(1)`/`tabs.widget(3)`) — robustecido a
    una búsqueda por TEXTO de pestaña en vez de índice, para que
    agregar una pestaña nueva en el futuro no vuelva a romperlo — +
    suite de regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre + 4 tests locales ya diagnosticados como
    desactualizados desde la ronda 63, sin relación con este cambio) +
    smoke test de arranque limpio. **Sigue sin poder confirmarse con
    audio/VLC real**: falta (1) que Santiago pegue el contenido del
    preset "Radio Tuyú" de EasyEffects (los 2 efectos + sus valores)
    para poder incorporarlos de verdad a la pestaña Procesador, y (2)
    que, tras reabrir la app con el compresor activado, confirme si
    ahora sí escucha el efecto — con el diagnóstico del log ya puesto,
    la próxima vuelta debería poder aislar mucho más rápido si el
    problema está en esta app o en la instalación de libVLC.
71. ~~Preset real de EasyEffects leído — descubierto un mismatch de
    tecnología real entre el compresor de esta app (filtro nativo de
    libVLC) y lo que EasyEffects usa de verdad (plugins LSP)~~ —
    Santiago pasó el contenido completo de su preset "Radio Tuyú"
    (`~/.configtde/easyeffects/output/Radio Tuyu.json` — nota: su
    sistema usa `~/.configtde` en vez de `~/.config`, probablemente
    por el entorno de escritorio). Confirmó 2 efectos, tal como había
    dicho: `compressor#0` y `stereo_tools#0`.

    **Compresor — mapeado con la mejor aproximación posible, pero NO
    es un port exacto (diferencia real de tecnología, documentada acá
    para no perderla de vista)**: el preset real usa un compresor LSP
    (vía LV2, el motor de EasyEffects) con `mode: "Upward"` — un modo
    que LEVANTA lo que está por DEBAJO del umbral (para subir pasajes
    flojos), completamente distinto al compresor "downward" clásico
    (bajar los picos que superan el umbral) que es el ÚNICO modo que
    soporta el filtro nativo `compressor` de libVLC usado en esta app.
    El preset también usa `dry`/`wet` (mezcla de señal procesada vs.
    original), `boost-amount`/`boost-threshold`, y un sidechain con
    HPF/LPF propios — ninguno de estos conceptos existe en el filtro
    simple de libVLC. Mapeados los 5 parámetros que SÍ tienen
    equivalente directo — `threshold: -12.0` → `compresor_umbral_db`,
    `ratio: 3.0` → `compresor_ratio`, `attack: 20.0` →
    `compresor_ataque_ms`, `release: 100.0` → `compresor_release_ms`,
    y `makeup (0.0) + output-gain (2.0) ≈ 2.0` →
    `compresor_ganancia_salida_db` (los dos controles de ganancia
    final del preset se combinaron en el único que tiene el filtro de
    libVLC) — actualizados como nuevo DEFAULT en `CONFIG_POR_DEFECTO`
    (`config/settings.py`), así una instalación nueva (o resetear los
    valores en Configuración → Procesador) ya arranca con estos
    números en vez de los defaults genéricos de libVLC. **Importante,
    explicado a Santiago**: el resultado audible NO va a sonar igual
    al de EasyEffects — el filtro de esta app puede acercarse en
    carácter (compresión moderada, ratio 3:1) pero nunca replica el
    levantado de señal floja del modo Upward ni el resto de las
    diferencias de arriba.

    **Stereo Tools — SIN equivalente en libVLC, y en este preset en
    particular no hace nada audible igual**: revisando los valores
    reales de `stereo_tools#0` (LSP Stereo Tools, un procesador
    Mid/Side con balance, mute/inversión de fase por canal, ancho
    estéreo, etc.) — TODOS sus parámetros están en su posición
    NEUTRA/default: `middle-level`/`side-level` en 0dB, `stereo-base:
    0.0` (sin ensanchado), `mode: "LR > LR (Stereo Default)"`, sin
    mute ni inversión de fase en ningún canal, ganancias en 0dB. En la
    práctica, este efecto puntual del preset de Santiago NO está
    haciendo ningún procesamiento audible tal como está configurado
    hoy — no hay ganancia real perdida por no poder replicarlo. libVLC
    tampoco tiene NINGÚN filtro nativo con este mismo concepto (Mid/
    Side con estos controles) — lo más cercano que existe,
    `stereo_widen` ("Stereo Enhancer" de VLC, basado en delay/
    feedback/crossfeed), es un algoritmo TOTALMENTE distinto, no una
    traducción de estos mismos parámetros.

    **Pendiente, genuina decisión de Santiago (no adivinada, quedó
    preguntado en el chat en vez de programado a ciegas)**: cómo
    seguir con Stereo Tools — (a) dejarlo afuera, ya que en su preset
    actual no hace nada audible igual; (b) agregar el "Stereo
    Enhancer" REAL de VLC (`stereo_widen`, con sus propios 4
    parámetros — delay/feedback/crossfeed/dry-mix — SIN pretender que
    sea "lo mismo" que Stereo Tools, simplemente una función de
    ensanchado estéreo distinta, honestamente etiquetada); o (c)
    reconsiderar el enfoque completo del procesamiento (mismo dilema
    ya recorrido en las rondas 37-55: control remoto de EasyEffects, o
    un filter-chain de PipeWire con los MISMOS plugins LSP/Calf — ambos
    ya descartados en su momento a favor de "manejarlo por fuera", pero
    ahora que se sabe que el compresor de libVLC no puede replicar el
    modo Upward, vale la pena que Santiago decida con los ojos
    abiertos si el compresor nativo le alcanza o prefiere volver a uno
    de esos caminos).

    No hizo falta ningún código nuevo más allá de actualizar los 5
    valores default del compresor (ver arriba) — se corrió la suite de
    regresión completa (actualizando una sola aserción en
    `test_autoscroll_y_compresor.py` que verificaba el default VIEJO
    de `-11.0`, ahora `-12.0`) sin fallos nuevos (mismos 3
    preexistentes de siempre + 4 tests locales ya diagnosticados como
    desactualizados desde la ronda 63) + smoke test de arranque
    limpio. Pendiente: la respuesta de Santiago sobre Stereo Tools, y
    que confirme (con el compresor ya en valores más cercanos a su
    preset real) si ahora sí nota el efecto al reabrir la app.
72. ~~Stereo Enhancer nativo de VLC (segundo efecto) + pregunta de
    Santiago sobre un filtro "Upward" en VLC~~ — Santiago eligió, vía
    `AskUserQuestion` con 3 opciones concretas, "Agregar el Stereo
    Enhancer real de VLC" para el efecto sin equivalente ("Stereo
    Tools") — implementado con el mismo criterio ya establecido para
    el compresor: filtro NATIVO de libVLC (módulo `stereo_widen`, un
    ensanchador estéreo por delay/feedback/crossfeed — algoritmo
    TOTALMENTE distinto de un procesador Mid/Side como Stereo Tools,
    nunca presentado como un port), configurable en Configuración →
    Procesador con sus 4 parámetros reales (Delay ms, Feedback %,
    Crossfeed %, Dry Mix %), desactivado por defecto con los valores
    de fábrica de libVLC (20/30/30/70 — acá no hay nada que "portear"
    de un preset real, a diferencia del compresor).

    **Refactor necesario para combinar DOS filtros de audio en libVLC
    correctamente**: `_argumentos_compresor()` y la nueva
    `_argumentos_estereo_ancho()` (`core/audio_engine.py`) ya NO arman
    su propio `--audio-filter=...` — devuelven solo sus flags
    `--compressor-*`/`--stereo-widen-*` — porque libVLC NO acumula
    varios `--audio-filter=` sueltos (el último pisa a los anteriores,
    no se combinan solos). `_argumentos_vlc()` es ahora el ÚNICO lugar
    que decide el nombre del filtro, combinando los activos en una
    sola cadena (`--audio-filter=compressor:stereo_widen` si los dos
    están prendidos, o solo uno de los dos nombres si es el único
    activo). El parámetro `aplicar_compresor` de `MotorAudio.__init__`
    se renombró a `aplicar_procesador` (y `self._aplicar_compresor` a
    `self._aplicar_procesador`) porque ahora gatea AMBOS efectos, no
    solo uno — mismo alcance de siempre (`True` por defecto en
    Publicidad/Emisión/Auxiliar/Pisador/crossfade-entrante, `False`
    únicamente en `GestorExplorador`, el Previo de Preescucha). El
    mensaje de diagnóstico en el log pasó de "compresor activado" a
    "procesador de audio activado", disparándose si CUALQUIERA de los
    dos filtros está activo. De paso se corrigió una nota de UI que
    había quedado desactualizada desde la ronda del alcance-Master
    ("afecta... el Previo por igual" — ya no es cierto desde esa
    ronda).

    **Pregunta directa de Santiago, respondida en el chat**: "¿Qué
    filtro podemos aplicar para tener el efecto 'levanta lo que está
    bajo el umbral' en VLC?" — respuesta honesta: **libVLC no tiene
    ningún filtro de compresión Upward verdadero** (threshold+ratio
    aplicado a lo que está POR DEBAJO de un umbral, como el
    `compressor#0` real de su preset). Lo más parecido que existe de
    verdad en libVLC es el filtro **`normvol`** (Volume Normalizer) —
    pero es un algoritmo distinto: calcula un promedio de nivel en una
    ventana móvil y aplica una ganancia continua para acercar la señal
    a un nivel objetivo (más parecido a un AGC/auto-nivelador que a un
    compresor paramétrico con threshold/ratio/attack/release). Sus
    únicos 2 parámetros reales son `norm-buff-size` (tamaño de la
    ventana de promediado) y `norm-max-level` (techo de amplificación).
    **No se implementó todavía** — quedó como respuesta informativa a
    la pregunta puntual de Santiago, pendiente de que él confirme si
    quiere sumarlo como una TERCERA función honesta (mismo criterio
    que el Stereo Enhancer: distinta técnica, jamás un "port" de
    Upward compression).

    Probado con `test_stereo_enhancer.py` (nuevo, dedicado — mismo
    patrón que `test_compresor_scope_master.py`: defaults de fábrica
    en instalación nueva, `MotorAudio()` lo aplica por defecto,
    `GestorExplorador` NO lo aplica, diagnóstico en el log con el
    valor exacto configurado) + actualización de
    `test_autoscroll_y_compresor.py` (los `_argumentos_compresor()`/
    `_argumentos_estereo_ancho()` ya no incluyen su propio
    `--audio-filter=`, más 4 checks nuevos de combinación: solo
    compresor, solo Stereo Enhancer, ambos combinados en una cadena,
    nunca dos flags `--audio-filter=` sueltos) + actualización de
    `test_compresor_scope_master.py` (rename `_aplicar_compresor` →
    `_aplicar_procesador`, mensaje de log actualizado) + suite de
    regresión completa sin fallos nuevos (mismos 3 fallos
    preexistentes de siempre + 4 tests locales ya diagnosticados como
    desactualizados desde la ronda 63) + smoke test de arranque
    limpio. **Sigue sin poder probarse con audio/VLC real**: falta que
    Santiago confirme que el Stereo Enhancer se escucha al activarlo
    (mismo requisito de reabrir la app que el compresor), y que decida
    si quiere sumar el Volume Normalizer como tercera función.
73. ~~LA CAUSA DE FONDO del "no se escucha nada": el compresor roto se
    llevaba puesto TODO el motor de audio + Volume Normalizer (tercer
    efecto)~~ — Santiago confirmó que quería el Volume Normalizer, y
    de paso reportó un bug real crítico: tras activar el compresor,
    "ahora solo tengo la opción de salida por 'predeterminada del
    sistema' y no puedo elegir las salidas como antes, con el
    listado, ni Pipe, ni Alsa, ni nada" — y sin sonido.

    **Causa de fondo encontrada**: `MotorAudio.__init__()` construye
    `vlc.Instance(argumentos_finales)` UNA sola vez, con los flags del
    compresor/Stereo Enhancer ya incluidos si estaban activados — si
    ESA llamada fallaba en la instalación real de Santiago (versión de
    libVLC sin el módulo compilado, sintaxis no soportada, lo que sea
    — no reproducible en el sandbox, que no tiene libVLC), el bloque
    `except` general de todo el constructor se disparaba y ponía
    `self._disponible = False` — dejando el motor ENTERO inutilizable,
    no solo el filtro que falló. Como
    `VentanaConfiguracion._listar_dispositivos_disponibles()` arma un
    `MotorAudio()` temporal solo para listar dispositivos y devuelve
    `[]` si `esta_disponible()` es `False`, el combo de Configuración
    → Audio se quedaba con un solo ítem hardcodeado ("default") — el
    síntoma exacto que reportó Santiago. Mismo motivo explica "no se
    escucha": CUALQUIER motor nuevo (Publicidad, Emisión, Auxiliar,
    Pisador) fallaba igual con el compresor activado.

    **Corregido con un reintento, no con más cautela previa (no hay
    forma de validar de antemano si libVLC va a aceptar un flag)**:
    `MotorAudio.__init__()` ahora intenta `vlc.Instance()` CON los
    filtros de audio primero — si eso falla (excepción o `None`), se
    registra el error en el log con el motivo exacto y se reintenta
    SIN ningún filtro, dejando el motor disponible igual (audio sin
    procesar, en vez de sin audio) — mismo criterio de "nunca confiar
    en una sola llamada, degradar limpio" ya aplicado repetidas veces
    en este archivo para bugs de libVLC. El diagnóstico ya agregado en
    la ronda del compresor (log con los argumentos exactos) se
    mantiene sin cambios — ahora se complementa con el motivo del
    fallo si el reintento llegó a dispararse.

    **Volume Normalizer (tercer efecto, "normvol")**: respuesta a la
    pregunta directa de Santiago sobre un filtro Upward — libVLC no
    tiene ninguno real, este es lo más parecido (un AGC/auto-nivelador
    que promedia el nivel de señal en una ventana móvil y ajusta
    ganancia hacia un objetivo, sin threshold/ratio/attack/release).
    Mismos 2 parámetros reales del módulo (`--norm-buff-size`,
    `--norm-max-level`), mismo criterio de alcance que los otros dos
    (desactivado por defecto, salida Master únicamente vía
    `aplicar_procesador`, requiere reabrir la app). `_argumentos_vlc()`
    ahora combina hasta 3 filtros en una sola cadena
    (`compressor:stereo_widen:normvol`).

    Probado con `test_fallback_filtro_roto_y_normalizador.py` (nuevo,
    dedicado — REPRODUCE el bug real con un `vlc.Instance()` mockeado
    que falla específicamente cuando ve `--audio-filter=` en los
    argumentos, igual que se sospecha que pasa en la instalación de
    Santiago): confirma que el primer intento incluye el filtro, el
    segundo (reintento) NO incluye ninguno, el motor queda disponible
    tras el reintento (antes se perdía por completo), y el log deja
    constancia del motivo — más el camino feliz (sin excepción) sigue
    llamando a `vlc.Instance()` una sola vez, sin reintentos de más —
    + defaults/argumentos/combinación de 3 filtros/escaneo Master-
    Preescucha/UI del Volume Normalizer + suite de regresión completa
    sin fallos nuevos (mismos 3 fallos preexistentes de siempre + 4
    tests locales ya diagnosticados como desactualizados desde la
    ronda 63) + smoke test de arranque limpio. **Sigue sin poder
    confirmarse con audio/libVLC real** (la causa exacta del fallo en
    la instalación de Santiago sigue sin conocerse — el mock reproduce
    el SÍNTOMA, "vlc.Instance() falla con esos flags", no
    necesariamente la causa raíz específica de su sistema): falta que
    Santiago confirme que, tras esta ronda, (1) el combo de
    Configuración → Audio vuelve a listar todas sus salidas reales
    (Pipe/Alsa/etc.), (2) el audio vuelve a sonar con el compresor
    activado — aunque sea SIN el efecto de compresión aplicado, si
    resulta que su libVLC de verdad no admite ese filtro, el log de
    Configuración → Diagnóstico → Ver log ahora debería decir
    exactamente por qué — y (3) que confirme si el Volume Normalizer
    se escucha al activarlo.
74. ~~Diagnóstico real con Santiago: la GUI de VLC aplica el compresor,
    `cvlc`/el motor headless de esta app NO — decisión explícita de
    Santiago de NO perseguir esa causa por ahora, sino corregir/ampliar
    los controles del compresor a los 7 reales de VLC~~ — sesión larga
    de diagnóstico guiado paso a paso con comandos reales en la máquina
    de Santiago (mismo criterio "ground truth de tu máquina real" ya
    usado para EasyEffects/PipeWire en su momento):
    - `cvlc --list | grep -i compressor` confirmó que el módulo SÍ está
      instalado. Un `cvlc --audio-filter=compressor --compressor-threshold=-60
      --compressor-ratio=20 --compressor-makeup-gain=0 archivo.mp3` con
      valores extremos (debería saturar/deformar sin duda) **no produjo
      ningún cambio audible** contra la reproducción sin el filtro.
    - Probado el mismo archivo con la GUI completa de VLC (`vlc`, con
      interfaz gráfica): activando el compresor a mano desde
      Herramientas → Efectos y Filtros → Compresor, **sí se percibió**
      el efecto — confirmado por Santiago explícitamente ("Si, se
      percibe el compresor... se percibe").
    - Con eso ya aislado (el módulo funciona, el problema es el modo
      HEADLESS), se probó pasarle los mismos flags `--audio-filter=
      compressor --compressor-*` a la GUI de `vlc` por línea de
      comandos (en vez de activarlo a mano) — Santiago confirmó "Entre
      uno y otro, no hay nada de diferencia, en absoluto", es decir,
      los flags de línea de comandos SÍ activan el filtro cuando el
      proceso tiene una interfaz gráfica real.
    - **Conclusión, no 100% definitiva pero fuertemente respaldada por
      estas pruebas**: `cvlc` (interfaz "dummy") y el embedding
      `python-vlc` que usa esta app (sin ningún módulo de interfaz
      adjunto, igual de "headless" que `cvlc`) muy probablemente NO
      aplican `--audio-filter=` de forma confiable a la salida de audio
      real — sería una limitación real de cómo libVLC arma la cadena de
      filtros sin una interfaz activa, no un error de sintaxis ni de
      esta app. Esto significaría que el compresor/Stereo Enhancer/
      Volume Normalizer, aunque configurados y aplicados sin tirar
      ningún error, podrían no estar teniendo NINGÚN efecto real sobre
      el audio que sale al aire.
    - Frente a esto, se preparó una pregunta formal de 3 caminos
      (investigar mecanismos alternativos de libVLC / dejarlo como está
      sin garantía de efecto / reconsiderar volver a EasyEffects-
      PipeWire) — **el intento de hacer esa pregunta fue rechazado
      explícitamente** (bloqueo del propio sistema: "The user doesn't
      want to proceed with this tool use... STOP"). Santiago dio en
      cambio su propia instrucción directa, por texto: **"Te corrijo.
      dejalo como está pero cambiemos los controles y valores del
      compresor."** — mantener la arquitectura actual TAL CUAL está
      (sin perseguir la causa de fondo del modo headless por ahora),
      pero corregir/ampliar los controles expuestos.

    **Controles del compresor ampliados de 5 a los 7 reales del
    módulo** (`core/audio_engine.py`, `config/settings.py`,
    `gui/ventana_configuracion.py`) — Santiago pasó el listado EXACTO
    con los rangos reales de su VLC 3.0.23 (Herramientas → Efectos y
    Filtros → Compresor), agregando los 2 que faltaban desde el
    principio (RMS/Pico y Radio Knee) y corrigiendo los rangos de los 5
    que ya existían para que coincidan EXACTO con los de su interfaz:
    - RMS/Pico (`--compressor-rms-peak`, 0.0 a 1.0) — **nuevo**.
    - Ataque (`--compressor-attack`, 1.5 a 400.0 ms) — rango corregido
      (antes sin tope explícito acorde a esto).
    - Release (`--compressor-release`, 2.0 a 800.0 ms) — rango
      corregido.
    - Umbral / "Entrada de Audio" (`--compressor-threshold`, -30.0 a
      0.0 dB) — sin cambios de rango, solo reetiquetado.
    - Ratio / "Proporción" (`--compressor-ratio`, 1.0 a 20.0) — sin
      cambios de rango, reetiquetado.
    - Radio Knee (`--compressor-knee`, 1.0 a 10.0 dB) — **nuevo**.
    - Salida / "Ganancia de Maquillaje" (`--compressor-makeup-gain`, 0
      a 24 dB) — sin cambios de rango, reetiquetado ("de Compensación"
      → "de Maquillaje", nombre real del control en VLC).
    `_argumentos_compresor()` ahora arma los 7 flags en el mismo orden
    que la interfaz real de VLC. Nuevas claves de config
    `compresor_rms_pico` (default 0.0) y `compresor_knee_db` (default
    2.5, el "factory default" de libVLC — Santiago no pasó un valor
    real de su preset para este control porque EasyEffects no tiene un
    concepto de "knee" equivalente en su `compressor#0`). El `QGroupBox`
    del Compresor en Configuración → Procesador ganó los 2 spin box
    nuevos y los 5 existentes se relabelearon/re-rangearon para que el
    formulario sea un espejo fiel de lo que Santiago ve en su propio
    VLC — pensado para que, si prueba manualmente en la GUI de VLC un
    valor que sí percibe, pueda replicar el mismo número acá con
    confianza de que es el control correcto.

    **Nota de honestidad, importante para no perder de vista**: esta
    ronda NO resuelve la limitación de fondo encontrada en el
    diagnóstico (headless vs. GUI) — fue una decisión EXPLÍCITA de
    Santiago de no perseguirla por ahora, priorizando corregir los
    controles primero. La hipótesis propia de Santiago ("Creo que la
    configuración fuera de esos rangos puede ser la falla") es
    plausible pero no es la explicación más respaldada por las pruebas
    ya hechas — los valores que se usaron en el litmus test de `cvlc`
    (threshold -60, ratio 20, makeup-gain 0) estaban DENTRO de rangos
    razonables y aun así no tuvieron ningún efecto audible, mientras
    que la MISMA sintaxis de línea de comandos SÍ funcionó apenas se
    la pasó a la GUI de `vlc` en vez de a `cvlc` — el patrón apunta más
    a headless-vs-GUI que a rangos fuera de límite. Si tras esta ronda
    Santiago sigue sin percibir el efecto incluso con los controles ya
    corregidos, la pista más prometedora para una futura ronda sigue
    siendo esa: investigar si existe alguna forma de forzar a libVLC a
    activar sus filtros de audio sin una interfaz gráfica real adjunta
    (o, si no la hay, aceptar la limitación y reconsiderar el enfoque).

    Probado extendiendo `test_autoscroll_y_compresor.py` (los 7 flags
    en el orden correcto, con y sin valores parciales — usa los
    defaults de fábrica si falta una clave — y el conteo exacto de 7,
    ni uno más ni uno menos) + regresión de
    `test_compresor_scope_master.py` y `test_fallback_filtro_roto_y_
    normalizador.py` (ambos pasan sin cambios, ninguno depende del
    conteo/orden exacto de flags del compresor) + suite de regresión
    completa sin fallos nuevos (mismos 3 fallos preexistentes de
    siempre + 4 tests locales ya diagnosticados como desactualizados
    desde la ronda 63, sin relación con este cambio) + smoke test de
    arranque limpio. **Sigue sin poder confirmarse con audio/VLC
    real**: falta que Santiago cargue los 7 controles con los valores
    que sabe que SÍ percibe en la GUI de su VLC y confirme si, con esos
    mismos números, el compresor headless de esta app finalmente
    produce algún efecto audible — si sigue sin notarse nada, es la
    señal más fuerte de que el problema es la limitación headless
    encontrada en el diagnóstico, no los rangos de los controles.
75. ~~Compresor/Stereo Enhancer/Volume Normalizer SACADOS de esta app
    (confirmado: era la limitación headless) + bug real: silencio
    excesivo al final de una canción~~ — dos pedidos en el mismo
    mensaje, tras confirmar Santiago que el diagnóstico de la ronda
    anterior daba en el clavo ("Si, es la limitación headless"):

    **a) Remoción completa del procesador de audio nativo de VLC**:
    Santiago armó, en otra sesión de Claude Code, una app Python
    standalone que controla el filter-chain NATIVO de PipeWire
    (plugins Calf en C — el mismo enfoque que ya había sonado bien en
    la ronda 52) con una interfaz de bandeja del sistema propia — así
    que el compresor/Stereo Enhancer/Volume Normalizer de las rondas
    69-74 quedaron redundantes (y, peor, probablemente inertes de
    fondo por la limitación headless recién confirmada). Se sacó todo
    de punta a punta:
    - `core/audio_engine.py`: eliminadas `_argumentos_compresor()`,
      `_argumentos_estereo_ancho()`, `_argumentos_normalizador()`, sus
      constantes de default, y la combinación de filtros en
      `_argumentos_vlc()` (que ahora vuelve a devolver solo
      `--no-video`/`--file-caching=N`, como antes de la ronda 69). El
      reintento "con filtros / sin filtros" de `MotorAudio.__init__()`
      (ronda 73) ya no hace falta — `vlc.Instance()` se llama una sola
      vez, sin ninguna rama de fallback. `aplicar_procesador` queda
      como parámetro de compatibilidad (`GestorExplorador` lo sigue
      pasando en `False`) pero ya no cambia nada en la práctica.
    - `config/settings.py`: sacadas las 13 claves
      `compresor_*`/`estereo_ancho_*`/`normalizador_*` de
      `CONFIG_POR_DEFECTO["audio"]`.
    - `gui/ventana_configuracion.py`: eliminada la pestaña completa
      "Procesador" (`_crear_tab_procesador()` y su wiring en
      `_cargar_valores_en_ui()`/`_guardar_y_cerrar()`).
    - **Bug real de UI encontrado y corregido como efecto colateral**:
      el menú desplegable "⚙ Configuración" del toolbar
      (`gui/main_window.py`, de la ronda del rediseño compacto)
      mapeaba "Tiempos de Fade..." al índice de pestaña 1 — correcto
      ANTES de que la ronda 70 insertara "Procesador" ahí mismo, pero
      nunca actualizado después: desde la ronda 70, ese ítem de menú
      en realidad abría la pestaña Procesador, no Fade. Sacar
      "Procesador" (que volvía a dejar Fade en el índice 1) corrigió
      este desalineamiento sin tocar una línea de `main_window.py` —
      probado explícitamente con un test que confirma el orden real
      de pestañas.
    - 3 archivos de test dedicados a estos 3 efectos se eliminaron
      (`test_compresor_scope_master.py`, `test_stereo_enhancer.py`,
      `test_fallback_filtro_roto_y_normalizador.py`); el archivo que
      compartía sección con el compresor
      (`test_autoscroll_y_compresor.py`, autoscroll de Ventana 2)
      se recortó a solo esa parte + un chequeo nuevo que confirma la
      remoción completa (config, argumentos de libVLC, y UI).
    3 rondas de trabajo (69-74) sobre un enfoque que terminó
    descartado — el historial completo (por qué se intentó, qué se
    aprendió del diagnóstico headless-vs-GUI, y por qué Santiago
    prefirió una app aparte) queda documentado arriba, sin borrarlo,
    para no tener que repetir la misma investigación si en algún
    momento se reconsidera.

    **b) Bug real de audio: "un tema finalizó y dejó mucho silencio al
    final"**: investigado en `core/analizador_audio.py`. El margen de
    seguridad que se deja SIN recortar en la SALIDA usaba el MISMO
    `tolerancia_silencio_segundos` que el margen de la ENTRADA (2.0s
    por defecto para Música) — para un tema con 3-4 segundos de
    silencio real pegado al final (común en masters/exports con
    padding), eso dejaba sonando hasta 2 segundos ENTEROS de aire casi
    muerto antes de llegar al corte real (`punto_fin_ms`). Peor
    todavía: el crossfade de Ventana 2 se calcula sobre ESE MISMO
    `punto_fin_ms` (vía `restante_ms_cambio` en `core/audio_engine.py`
    y `_chequear_crossfade()` en `core/gestor_emision.py`) — con el
    punto de corte "inflado" por ese margen de 2s, el crossfade
    también arrancaba más tarde de lo que debería, agravando el mismo
    síntoma. Corregido con un tope duro nuevo,
    `MARGEN_MAXIMO_SALIDA_MS = 300` — el margen de salida ahora es
    `min(tolerancia_ms, 300)`, nunca la tolerancia completa: alcanza
    para no cortar en seco una nota/reverberación recién decayendo,
    sin arrastrar segundos de aire muerto. El margen de ENTRADA (el
    pre-roll de silencio antes de que arranque el contenido real)
    queda INTACTO — no era la queja de Santiago, y cortar ahí de más
    podría sonar más abrupto al empezar un tema. Los géneros de corte
    estricto (Publicidad/Separador/HTH, `tolerancia_silencio_v1_segundos=0`)
    no se ven afectados — `min(0, 300)` sigue dando `0`, mismo
    comportamiento "sin margen" de siempre.

    **Importante — este fix NO es retroactivo**: como con cualquier
    cambio a `analizador_audio.py`, un archivo YA IMPORTADO conserva
    el `punto_fin_ms` calculado con el margen VIEJO hasta que se
    reanalice — el botón "🔄 Reanalizar biblioteca" (Configuración →
    Diagnóstico, ronda 40) recalcula todo con la fórmula nueva. Un
    archivo importado/reemplazado DE ACÁ EN MÁS ya usa el margen
    corregido automáticamente, sin acción manual.

    Probado con `test_fix_silencio_final_cancion.py` (nuevo, dedicado,
    con audio SINTÉTICO real vía `pydub.generators.Sine` + WAV, sin
    necesitar ffmpeg — mismo patrón ya usado para el umbral de
    silencio configurable de una ronda muy anterior): un tema con 4s
    de silencio de salida real queda con el margen SONANDO topeado en
    ~300ms (antes hubiera dejado ~2000ms, confirmado comparando contra
    el punto de corte que habría dado el margen viejo); los géneros de
    corte estricto siguen en margen ~0; un tema casi sin silencio de
    salida no pierde contenido real — + `test_autoscroll_y_compresor.py`
    actualizado + suite de regresión completa. La corrida cayó
    exactamente sobre la medianoche del sistema (00:0x UTC) y sumó 6
    fallos de horario más a los 7 preexistentes de siempre —
    confirmado con `git stash` que los MISMOS 6 fallan igual contra el
    código sin este cambio, en el mismo instante (el conocido patrón
    de tests que resuelven "bloque vigente" contra la hora real,
    documentado desde hace muchas rondas) — ninguno relacionado con
    este cambio. + smoke test de arranque limpio. **Sigue sin poder
    confirmarse con audio real**: falta que Santiago reanalice su
    biblioteca (o importe algo nuevo) y confirme que los temas ya no
    dejan un hueco de silencio audible al terminar, y que active su
    app externa de PipeWire para el procesamiento de audio que antes
    vivía acá.
76. ~~Rendimiento del Explorador con una biblioteca de ~10-12mil
    archivos (pedido explícito, tras un pase real de casi 10mil
    ítems) + barra de preload~~ — "el JSON parece trabarse un poco
    para la lectura de exploración, por ejemplo al ver los ítems en
    la categoría... revisá el buffer". Investigado a fondo en
    `gui/ventana_explorador.py`, tres causas reales combinadas — la
    tercera resultó ser, con datos realistas, la MÁS importante:

    **a) Render de `tree_archivos` sin batchear**: `_on_categoria_
    seleccionada`/`_buscar`/`_ordenar_por_columna` armaban cada
    `QTreeWidgetItem` con `addTopLevelItem()` UNO POR UNO — con una
    categoría de varios miles de ítems (frecuente: una importación
    masiva suele caer entera en UNA sola categoría), cada inserción
    dispara su propio recálculo interno de Qt. Corregido con
    `_llenar_tree_archivos()` (nuevo, usado por los 3 lugares): arma
    TODOS los ítems sueltos, los inserta de una con
    `addTopLevelItems()`, y envuelve todo en
    `setUpdatesEnabled(False)/(True)` — esto nunca toca disco (la
    biblioteca ya está 100% en memoria desde el arranque, ver más
    abajo), es puramente el costo de poblar el widget.

    **b) Guardado de biblioteca.json SINCRÓNICO en cada mutación**:
    `_guardar_biblioteca()` serializa TODA la biblioteca (recursivo)
    y reescribe el archivo entero con `fsync()` — se disparaba en
    CADA alta/baja/movimiento individual, bloqueando la UI un
    instante cada vez, incluso en ráfagas (ej. arrastrar 20 archivos
    uno por uno). Corregido con `_guardar_biblioteca_debounced()`
    (timer de 600ms, mismo patrón de debounce ya usado en este
    proyecto para la persistencia de Emisión/Publicidad) — usado en
    11 de los 12 puntos que antes guardaban directo; se dejan
    INMEDIATOS a propósito la importación masiva (que ya hace un solo
    guardado deliberado al final del lote) y `flush_biblioteca_
    pendiente()` (nuevo, llamado desde `MainWindow.closeEvent()` para
    no perder la última ráfaga de cambios al cerrar el programa antes
    de que el timer dispare solo). De paso, `guardar_biblioteca()`
    ahora escribe COMPACTO (`config/settings.py:_guardar_json_atomico
    (compacto=True)`, sin `indent=2`) — nadie edita biblioteca.json a
    mano, a diferencia de config_general.json/programacion.json, que
    se quedan legibles.

    **c) EL BUG DE FONDO REAL, encontrado midiendo con datos
    realistas de 10mil ítems (no una corazonada — medido: sin este
    fix, la migración de duración era 3 VECES más lenta Y NUNCA
    quedaba cacheada de verdad)**: registros guardados sin la columna
    Duración (típico de una biblioteca migrada por fuera de las
    altas normales de la app — "＋ Agregar"/"Importar masivo" SÍ la
    calculan al alta) disparan una "migración silenciosa" en
    `_agregar_fila_archivo()` que calcula la duración con mutagen y
    la guarda en el dict del registro — pero **`QTreeWidgetItem.data()`
    para roles custom (por encima de `Qt.UserRole`, como
    `ROL_ARCHIVOS`) devuelve una COPIA del objeto Python guardado**
    (trampa real de PySide6 ya documentada varias veces en este
    proyecto, para otros roles) — mutar los dicts de esa copia NUNCA
    se reflejaba en la data real del ítem de categoría, así que la
    migración se perdía y se recalculaba desde cero CADA VEZ que se
    volvía a leer esa categoría (cada click, no solo cada reinicio de
    la app como decía el comentario original) — esto por sí solo
    explica por completo el "se traba al ver los ítems de la
    categoría" para cualquier biblioteca con ítems sin duración
    cacheada. Corregido con `_registros_de_categoria()` (nuevo, único
    punto de lectura de `ROL_ARCHIVOS` para MOSTRAR una categoría,
    usado por `_on_categoria_seleccionada` y por `_buscar` — esta
    última migra de paso TODA categoría que toca en el camino, no
    solo lo que matchea el texto, "autocurando" el resto de la
    biblioteca gratis): si migra algo, escribe la lista de vuelta con
    `item_categoria.setData(...)` (ahora sí en la data real del
    ítem) y dispara un guardado debounced — la duración migrada queda
    persistida en biblioteca.json y nunca más hace falta recalcularla
    para ese archivo.

    **d) Preload (pedido explícito, "que sepa que la PC está
    trabajando")**: nueva señal `solicitud_preload` (Ventana 3),
    conectada en `MainWindow` al mismo `_mostrar_preload()` de
    siempre (cursor de espera + mensaje en la barra de estado) —
    emitida por `_llenar_tree_archivos()` solo si la lista supera
    `_UMBRAL_ITEMS_PRELOAD = 300` (por debajo, mostrarlo sería puro
    ruido visual, la operación ya es casi instantánea). Con listas
    grandes también corre `QApplication.processEvents()` cada 500
    ítems durante el armado — mismo patrón ya usado para la
    importación masiva — para que la ventana no se vea "colgada" en
    hardware modesto. El arranque de la app (carga inicial de TODA la
    biblioteca) ya estaba cubierto por el `QSplashScreen` de siempre
    en `main.py` — no hizo falta tocar nada ahí.

    Probado con `test_biblioteca_grande_rendimiento.py` (nuevo,
    dedicado, con datos sintéticos de hasta 10mil ítems): JSON
    compacto vs. indentado (tamaño y validez), debounce coalescia 5
    mutaciones en ráfaga en 1 solo guardado real, `flush_biblioteca_
    pendiente()` fuerza el guardado pendiente sin duplicar si no hay
    nada pendiente, `_llenar_tree_archivos()` arma correctamente
    listas chicas (sin preload) y grandes (con preload, cantidad
    correcta en el aviso), **reproduce el bug real de la copia de
    PySide6 y confirma el fix**: migrar duración queda cacheada en
    memoria Y persistida en disco, y una `VentanaExplorador` "nueva"
    (simulando un reinicio real leyendo de disco) ya no recalcula
    nada ni dispara guardados de más — + selección de categoría/
    búsqueda/orden por columna siguen funcionando igual con el camino
    nuevo + actualización de 2 tests preexistentes que asumían el
    guardado SINCRÓNICO viejo (`test_reordenar_categorias.py`,
    `test_descargador_youtube.py` — ahora usan `flush_biblioteca_
    pendiente()` antes de mirar el disco, no es una regresión, es el
    debounce funcionando como se diseñó) + suite de regresión completa
    sin fallos nuevos (mismos 7 fallos preexistentes de siempre) +
    smoke test de arranque limpio. **Sigue sin poder confirmarse en
    hardware real**: falta que Santiago confirme en su notebook
    (Celeron N2820) que ver una categoría grande ya no se siente
    trabada — la primera vista de una categoría con ítems sin
    duración cacheada TODAVÍA va a tardar un poco (mutagen tiene que
    leer cada archivo una vez, inevitable), pero de ahí en más debería
    ser instantánea, incluso después de cerrar y reabrir la app.
77. ~~La ronda anterior no alcanzaba: migración de duración movida de
    LAZY (por categoría, la primera vez que se ve) a UN SOLO PASO al
    ARRANCAR, con barra de progreso GRÁFICA real~~ — Santiago probó la
    ronda 76 y la gráfica SEGUÍA congelándose al leer una categoría
    (visible incluso en el medidor de nivel decorativo, que dejaba de
    animarse) — el fix de persistencia de la ronda anterior era
    correcto (ya no se repetía la migración en cada sesión), pero la
    PRIMERA vez que se ve cada categoría con ítems sin duración
    cacheada TODAVÍA paga el costo real de mutagen de punta a punta,
    de forma síncrona, en el hilo único de la GUI — con una categoría
    de miles de archivos migrados por fuera de la app, eso es
    perceptible como una traba real, no cosmética. Dato clave que dio
    Santiago para la solución: la PC se reinicia sola todos los días a
    las 00hs — "a cada reinicio del programa podemos agregar alguna
    instancia... que (aunque tarde) me ofrezca fluidez".

    **Rediseño**: la migración ya NO espera a que el operador abra
    cada categoría — se hace TODA de una sola vez, ANTES de mostrar la
    ventana principal, con una barra de progreso GRÁFICA real (pedido
    explícito: "una barra gráfica de preload al inicio", a diferencia
    del cursor de espera + texto que ya usa el resto de la app).
    - `gui/dialogo_preload_biblioteca.py` (nuevo): `QDialog` chico con
      `QLabel` + `QProgressBar` determinado (`%v / %m archivos`).
    - `VentanaExplorador.iniciar_migracion_duracion_al_arrancar()`
      (nuevo): en vez de un bucle síncrono gigante, recorre TODAS las
      categorías en LOTES de `_TAMANO_LOTE_MIGRACION = 25` archivos,
      encadenados vía `QTimer.singleShot(0, ...)` — cada lote cede el
      control a Qt antes del siguiente, así cualquier animación
      (el medidor de nivel, la propia barra de progreso) sigue
      respirando entre lotes en vez de congelarse de punta a punta.
      Por categoría, la copia de `ROL_ARCHIVOS` se lee UNA sola vez
      (guardada en un `estado` que sobrevive entre lotes mientras esa
      categoría no termine) y se escribe de vuelta UNA sola vez al
      terminarla — ni recopia la lista completa en cada tick de más,
      ni cae de nuevo en la trampa de la copia descartable de PySide6
      (misma clase de bug que la ronda anterior, evitada desde el
      diseño esta vez). Contrato de 3 callbacks: `callback_iniciar(total)`
      (una vez, ANTES de migrar nada — si `total == 0`, que es el caso
      normal después de la primera vez que corre esto, no se llama a
      ningún otro callback ni se hace nada más), `callback_progreso(
      hechos, total)` (por lote), `callback_terminado(hechos)` (al
      final, con el guardado YA hecho en disco, inmediato — no
      debounced, para tener la garantía de que quedó escrito antes de
      seguir con el arranque).
    - `main.py`: entre construir `MainWindow()` y `ventana.show()`, se
      llama a `iniciar_migracion_duracion_al_arrancar()`; si hay algo
      pendiente, se arma el diálogo y se lo bloquea con `.exec()`
      (nested event loop de Qt — los `QTimer.singleShot(0, ...)`
      encadenados de la migración SÍ se procesan durante ese loop
      anidado, igual que cualquier otro timer de la app, confirmado
      con un smoke test real). Con la biblioteca ya migrada (el caso
      normal de acá en más, incluidos TODOS los reinicios diarios
      siguientes) el diálogo ni siquiera llega a construirse.
    - `_registros_de_categoria()` (ronda anterior) queda como red de
      seguridad, no como mecanismo principal — solo entraría en juego
      si algo agrega un ítem sin duración a mitad de una sesión (fuera
      del flujo normal de alta, que siempre la calcula al importar).
    - **Aclaración importante, respondiendo la otra parte del pedido
      ("optimizar la entrega veloz del JSON y su lectura")**: medido
      con datos realistas (12.000 registros con todos los campos que
      usa la app) — serializar + escribir biblioteca.json compacto
      tarda ~50ms, leer + parsearlo tarda ~35ms. El JSON en sí NUNCA
      fue el cuello de botella — el costo real, de punta a punta,
      siempre fue mutagen abriendo cada archivo de audio para leer su
      duración. No hay nada más para optimizar del lado del JSON.

    Probado con `test_migracion_duracion_arranque.py` (nuevo,
    dedicado): sin nada pendiente no dispara ningún callback de más
    (ni arma el diálogo); con archivos repartidos en categorías chicas
    y una categoría más grande que un solo lote, migra TODO, el
    progreso avanza monótono y termina en 100%, cada categoría queda
    con la duración cacheada de verdad (vía `.data()` fresco, no la
    copia vieja) y persistida en disco; una `VentanaExplorador` nueva
    simulando un reinicio ya no tiene nada pendiente; el diálogo se
    arma y actualiza sin romperse — + smoke test de punta a punta real
    corriendo `main.py` completo con una biblioteca de 120 ítems sin
    duración (offscreen, sin ventana real pero con el mismo
    `QDialog.exec()`/`QTimer` real): la app arranca sin excepción y
    los 120 registros terminan con duración persistida en
    `biblioteca.json` al final — + suite de regresión completa sin
    fallos nuevos (mismos 7 fallos preexistentes de siempre) + smoke
    test de arranque limpio sin biblioteca pendiente. **Sigue sin
    poder confirmarse en hardware real**: falta que Santiago reinicie
    su PC (o simplemente reabra la app una vez, ya que el escaneo
    corre igual al abrir) con su biblioteca real de ~10-12mil
    archivos y confirme (1) que ve la barra de progreso gráfica
    avanzar en vez de una pantalla congelada, (2) que aunque tarde un
    rato la primera vez, el arranque en sí no se siente "tildado" (los
    lotes de a 25 deberían mantener la interfaz respirando), y (3) que
    DESPUÉS de esa migración inicial, explorar cualquier categoría —
    incluso las que nunca había abierto — ya es instantáneo, sin
    ningún tranco.
78. ~~Botón manual "Verificar biblioteca" en Configuración + confirmado
    que no queda ningún procesador de audio en la app~~ — dos
    consultas de Santiago tras probar la ronda anterior:

    **a) "¿Esta verificación se puede hacer también manual desde
    Configuraciones?"**: sí — nuevo botón "🔎 Verificar biblioteca
    (duración faltante)" en Configuración → Diagnóstico, junto a
    "🔄 Reanalizar biblioteca" (que es una función DISTINTA — recalcula
    el recorte de silencio/nivelado con la tolerancia actual, nunca
    toca la duración). El botón nuevo reusa EXACTAMENTE el mismo
    mecanismo que ya corre solo al arrancar
    (`VentanaExplorador.iniciar_migracion_duracion_al_arrancar()` +
    `DialogoPreloadBiblioteca`, ronda anterior) — mismos lotes chicos
    vía `QTimer`, misma barra de progreso gráfica — así se comporta
    igual sea que se dispare al abrir el programa o a mano desde acá,
    sin tener que reiniciar. Si no hay nada pendiente, avisa que no
    hacía falta nada en vez de mostrar una barra vacía.
    **Sobre la otra mitad de la pregunta ("cuando se agregan archivos
    nuevos")**: no hizo falta agregar ningún gancho nuevo — los 3
    caminos de alta de la app ("＋ Agregar", "Importar masivo",
    descarga de YouTube) YA calculan la duración en el momento mismo
    de importar (`obtener_duracion_formateada(ruta)`, confirmado
    revisando los 3 puntos de alta en `gui/ventana_explorador.py`) —
    nunca queda un hueco para un archivo agregado por la vía normal de
    la app. El botón nuevo (más el chequeo lazy de
    `_registros_de_categoria()`, ronda anterior, que sigue como red de
    seguridad) cubre el único caso real donde SÍ podría faltar: un
    archivo que entra a la biblioteca por fuera de esos 3 caminos (ej.
    editando `biblioteca.json` a mano o por script).

    **b) "¿Quedó algún proceso de algún procesador de audio, autoganancia
    o algo por el estilo?"**: NO — confirmado con una búsqueda
    puntual en todo `core/` y `config/settings.py`: del compresor/
    Stereo Enhancer/Volume Normalizer nativos de libVLC (sacados en la
    ronda 75, cuando Santiago armó su propia app de PipeWire) no queda
    ningún código funcional — solo comentarios explicando la remoción
    y el parámetro `aplicar_procesador` de `MotorAudio`, que sigue
    existiendo por compatibilidad de firma pero ya no cambia nada en
    la práctica. **Lo único relacionado con volumen que SÍ sigue
    activo, y es importante no confundirlo con un "procesador"**: el
    nivelado POR TEMA de `core/analizador_audio.py`
    (`ganancia_db = DBFS_OBJETIVO - audio.dBFS`, calculado UNA vez al
    importar cada archivo, aplicado como un simple ajuste de volumen
    estático al reproducir) — esto NUNCA formó parte de la saga
    EasyEffects/PipeWire/compresor de VLC, existe desde mucho antes, y
    es justamente lo que ya se le había confirmado a Santiago en la
    ronda 55 como "lo más parecido a una autoganancia de salida que
    esta app puede ofrecer sin volver a depender de un procesador de
    audio externo" — sigue funcionando igual, sin cambios.

    Probado con `test_verificar_biblioteca_manual.py` (nuevo,
    dedicado): el botón queda deshabilitado sin `ventana_explorador`
    (mismo criterio que "Reanalizar biblioteca"), con archivos
    pendientes dispara la migración y deja todo persistido con el
    mensaje de resumen correcto, y sin nada pendiente avisa que no
    hacía falta nada sin mostrar ningún diálogo de progreso — + suite
    de regresión completa sin fallos nuevos (mismos 7 fallos
    preexistentes de siempre) + smoke test de arranque limpio. Falta
    que Santiago confirme que el botón nuevo aparece en Configuración
    → Diagnóstico y funciona como espera.
79. ~~"Ubicar" archivo en el explorador de la PC + recuperar vínculos
    rotos (buscar por duración/tamaño y "Vincular")~~ — pedido
    explícito, 9 puntos (a-i) sobre Ventana 3/Explorador:

    **a) "Ubicar" nuevo en el menú contextual**: localiza el archivo
    de un registro EN EL EXPLORADOR DE ARCHIVOS DEL SISTEMA, sin
    ninguna acción sobre él — ni reproduce, ni edita. No existe un
    mecanismo universal en Linux para "abrir seleccionando un archivo"
    (a diferencia de macOS `open -R` / Windows `explorer /select,`) —
    `_localizar_en_explorador_de_archivos()` (`gui/ventana_explorador.py`)
    prueba, en orden, los gestores de archivos más comunes que sí
    soportan selección directa por línea de comandos (`dolphin
    --select`, `nautilus --select`, `nemo`, `pcmanfm-qt`, `pcmanfm`)
    vía `shutil.which()` + `QProcess.startDetached()` — mismo patrón
    ya usado para `mhwaveedit` en "🎚 Editar audio". Si ninguno está
    instalado, cae a abrir la CARPETA contenedora con el programa
    default del sistema (`QDesktopServices.openUrl`, sin selección
    puntual pero siempre funciona); si ni eso funciona, avisa con la
    ruta de la carpeta a mano. Como no se sabe de antemano qué gestor
    de archivos tiene instalado Santiago (Q4OS suele traer TDE/Trinity
    o Plasma), esta cadena de fallback queda documentada como
    incierta hasta que él confirme cuál efectivamente selecciona el
    archivo.

    **b) Archivo faltante -> pregunta Buscar/Eliminar/Cancelar**: si
    `os.path.exists(ruta)` da `False` (o nunca tuvo ruta),
    `_preguntar_que_hacer_con_archivo_perdido()` arma un
    `QMessageBox` con 3 botones de texto propio ("Buscarlo...",
    "Eliminar registro", "Cancelar") — mismo patrón ya establecido por
    `MainWindow._preguntar_actualizar_ahora()` (extraído en su propio
    método para poder testear la decisión sin simular un click real,
    algo que offscreen no puede). "Eliminar registro" usa
    `_eliminar_registro_sin_confirmar()`, una versión liviana de
    `_eliminar_archivo()` que NO vuelve a pedir confirmación (la
    propia pregunta "¿Buscarlo o eliminar?" YA es la confirmación —
    reusar `_eliminar_archivo()` tal cual hubiera disparado una
    segunda, redundante, gateada por
    `confirmar_antes_de_eliminar`).

    **c+d) "Buscar" escanea Publicidad primero, Musical segundo, por
    duración de identidad**: `_buscar_archivo_perdido()` recorre
    (`os.walk`, recursivo) las DOS carpetas base de Configuración →
    Rutas, en ese orden — Biblioteca de Publicidad primero, Biblioteca
    musical segunda (pedido explícito, punto d) — filtrando por
    `EXTENSIONES_SOPORTADAS` antes de calcular la duración de cada
    candidato (`obtener_duracion_formateada`, mutagen — liviano,
    nunca pydub/ffmpeg para esto). La duración es la identidad REAL
    del match (el nombre del archivo pudo cambiar): se compara la
    cadena "HH:MM:SS" exacta contra la guardada en el registro — ya
    viene truncada al segundo por el propio formateador, así que la
    comparación es naturalmente tolerante sin necesitar un margen
    aparte. El tamaño en bytes (`tamaño_bytes`, campo NUEVO agregado
    en esta ronda a los 3 puntos de alta existentes — "＋ Agregar",
    Importar masivo, descarga de YouTube — y al nuevo "🔗 Vincular")
    viaja como dato INFORMATIVO por candidato (columna "¿Tamaño
    coincide?"), nunca como filtro duro — decisión propia, explicada
    acá: muchos registros viejos no tienen tamaño guardado todavía, y
    un archivo re-codificado puede compartir duración con un tamaño
    distinto — filtrar por los dos a la vez rompería en silencio
    justo el caso que se quiere resolver. Con listas grandes, un
    `QApplication.processEvents()` cada 25 archivos evita que el
    escaneo se sienta "colgado" (mismo patrón ya usado en import
    masivo/migración de biblioteca), con `solicitud_preload` emitido
    para el mensaje de estado.

    **e+f+g) Diálogo de candidatos con Previo (por Preescucha) y
    Vincular**: `gui/dialogo_vincular_archivo.py` (nuevo,
    `DialogoVincularArchivo`) — un `QTreeWidget` con TODOS los
    candidatos encontrados (columnas Carpeta/Archivo/Duración/Tamaño/
    ¿Tamaño coincide?, pedido explícito punto e: "pueden haber 1, 2 o
    más archivos... me dará TODOS"), botones "▶ Previo"/"■ Detener"
    (punto f) que arrancan/detienen un `MotorAudio` PROPIO del
    diálogo, y "🔗 Vincular" (punto g) que confirma la elección
    (`.resultado()` devuelve la ruta elegida o `None`). El motor se
    detiene siempre al cerrar/cancelar (`reject()`/`closeEvent()`
    sobrescritos) — nunca queda sonando de fondo con el diálogo ya
    cerrado.

    **h) El archivo vinculado queda listo para reproducir**: nuevo
    `VentanaExplorador._aplicar_nuevo_archivo(item, categoria,
    registro, ruta_nueva)` — extraído de `_reemplazar_archivo()`
    (mismo re-análisis de silencio/nivelado, misma actualización de
    `ruta`/`duracion`/`tamaño_bytes`, mismo `setData()`+
    `_sincronizar_registro_en_categoria()`+guardado debounced) para
    que "⟲ Reemplazar" (el operador elige el archivo a mano) y
    "🔗 Vincular" (el operador elige un candidato de la búsqueda)
    compartan un solo camino, sin lógica duplicada — el registro queda
    con el archivo nuevo ya analizado y persistido, tal como si se
    hubiera reemplazado a mano.

    **i) Previo por Salida Preescucha, nunca Master**: el
    `MotorAudio` interno del diálogo se construye con
    `aplicar_procesador=False` e `id_dispositivo=` el
    `dispositivo_preescucha` configurado (resuelto en
    `_buscar_archivo_perdido()` con el mismo criterio ya usado por
    `GestorExplorador`, el ▶ Previo normal de Ventana 3: `"default"` →
    `None`) — exactamente lo que Santiago pidió explícito, este previo
    NUNCA sale por la salida que va al aire.

    **Detalle real de testing, no de la app**: al escribir el test
    del menú contextual apareció un problema real de offscreen no
    documentado hasta ahora en este proyecto — parchear `QMenu.exec`
    a nivel de CLASE (`patch.object(QMenu, "exec", ...)` o asignación
    directa), la técnica que varios tests anteriores creían que
    funcionaba, en realidad NO intercepta la llamada real para
    `QMenu.exec(QPoint)` — el `exec()` nativo se ejecuta igual y
    cuelga para siempre esperando un click que nunca llega (confirmado
    con un repro mínimo aislado, `menu.exec(QPoint(0,0))` con la clase
    parcheada sigue bloqueando). Lo que sí funciona de forma
    confiable: parchear la INSTANCIA (`menu.exec = lambda ...`, no la
    clase) — pero como `QMenu(self)` se crea DENTRO del método bajo
    prueba, no hay forma de agarrar esa instancia de antemano.
    Solución que sí probó andar: interceptar `QMenu.addAction`
    (siempre patcheable, se ejecuta ANTES de `exec()`) y, la primera
    vez que se llama sobre una instancia de menú nueva, agendar
    `QTimer.singleShot(0, self.close)` sobre ESA instancia real — así
    el `exec()` real, bloqueante, entra a su loop de eventos, procesa
    el timer ya encolado, y se cierra solo casi de inmediato. **Regla
    para el futuro**: cualquier test nuevo que necesite simular un
    menú contextual sin bloquear debe usar este patrón (cerrar la
    instancia real vía timer agendado desde `addAction`), no confiar
    en parchear `QMenu.exec` a nivel de clase — varios tests
    anteriores de este proyecto puede que hayan estado "pasando" sin
    haber ejercitado de verdad la rama de `exec()` (por ejemplo, si el
    menú resultaba estar vacío o el método retornaba antes de llegar
    ahí) sin que nadie lo notara.

    Probado con `test_ubicar_vincular_archivo.py` (nuevo, dedicado):
    archivo existente dispara el localizador con la ruta correcta sin
    preguntar nada; archivo faltante + "cancelar" no hace nada;
    "eliminar" quita el registro de la lista Y de la categoría
    persistida SIN una segunda confirmación (`QMessageBox.question`
    nunca se llama); "buscar" encuentra candidatos en Publicidad
    (raíz y subcarpeta, recursivo) Y en Musical (combina ambas
    carpetas, nunca se detiene en la primera con resultados), ignora
    archivos no-audio, le pasa el dispositivo de Preescucha correcto
    al diálogo, marca `tamaño_coincide` como informativo sin filtrar
    ningún candidato por eso; Vincular aplica el archivo elegido
    (ruta/duración/tamaño actualizados) y lo persiste en disco; sin
    candidatos avisa sin abrir el diálogo; el ítem "Ubicar" está en el
    menú contextual — + `test_dialogo_vincular_archivo.py` (nuevo,
    dedicado: lista candidatos, preselección, Previo/Detener degradan
    limpio sin libVLC real, Vincular devuelve la ruta elegida, sin
    candidatos el botón Vincular queda deshabilitado, cancelar no deja
    ninguna ruta elegida) + suite de regresión completa sin fallos
    nuevos (mismos 7 fallos preexistentes de siempre:
    `test_audio_only_y_buffer.py`, `test_confirmaciones.py`,
    `test_fade_in_declick_v1.py`, `test_log_git.py`,
    `test_ronda_ajustes_dinesat2.py`, `test_ronda_dinesat3.py`,
    `test_ventana3.py`) + smoke test de arranque limpio. **Sigue sin
    poder confirmarse con hardware/gestor de archivos real** (el
    sandbox no tiene ningún gestor de archivos gráfico instalado, y el
    Previo usa libVLC que tampoco está disponible acá): falta que
    Santiago confirme (1) que "Ubicar" abre su gestor de archivos real
    (Dolphin, Nautilus, u otro — avisar cuál si ninguno de los
    probados selecciona el archivo, para sumarlo a la lista), (2) que
    la búsqueda por duración encuentra los candidatos esperados con su
    biblioteca real (archivos movidos/renombrados de verdad), (3) que
    el Previo del diálogo de candidatos suena por sus parlantes de
    Preescucha, no por la salida al aire, y (4) que vincular un
    candidato deja el material listo para reproducir con normalidad en
    Ventana 1/2/Auxiliar.

    **Ajuste inmediato, pedido explícito tras probarlo en la práctica
    ("no me encuentra nada y sé que debe encontrar")**: dos cambios de
    fondo sobre el mecanismo de "Buscar" de arriba, ambos con la causa
    real explicada:
    - **a) Tamaño PRIMERO, duración segundo (se invirtió la
      prioridad)**: el diseño original de esta misma ronda usaba la
      duración como filtro DURO y el tamaño como dato informativo — la
      sospecha real de por qué "no encontraba nada": la duración que
      calcula `mutagen` puede variar un segundo entre lecturas/
      formatos/encoders para el MISMO archivo, mientras que el tamaño
      en bytes de una copia/movida real es siempre idéntico byte a
      byte. Invertido: si el registro tiene `tamaño_bytes` guardado,
      ESE es ahora el filtro duro (comparación barata,
      `os.path.getsize()`, calculada para TODOS los candidatos antes
      de pagar el costo de abrir el archivo con mutagen — mejora de
      paso en rendimiento, ya que la duración solo se calcula para los
      que YA pasaron el filtro de tamaño); si el registro es viejo y
      no tiene tamaño guardado, se cae a duración como único criterio
      posible (mismo comportamiento de siempre para ESE caso). Ambos
      campos (`tamaño_coincide`/`duracion_coincide`) se siguen
      mostrando en el diálogo como columnas informativas.
    - **b) Ignora las rutas de Configuración, busca la carpeta Música
      REAL del sistema**: nuevo `_resolver_carpeta_musica_real()`
      (`gui/ventana_explorador.py`) — mismo mecanismo ya usado en
      `instalar.sh` para el Escritorio (`xdg-user-dir DESKTOP`, porque
      Q4OS en español usa "Escritorio", no "Desktop"): acá se usa
      `xdg-user-dir MUSIC` primero, y si no responde, se prueba
      `~/Música`/`~/Musica`/`~/Music` en ese orden. La sospecha real:
      las rutas configuradas en Configuración → Rutas (Biblioteca de
      Publicidad/musical) pueden no reflejar dónde vive realmente la
      biblioteca completa de Santiago, o directamente no coincidir con
      el nombre real de la carpeta del sistema (mismo tipo de bug ya
      encontrado antes con "Escritorio"/"Desktop") — la búsqueda ahora
      escanea SIEMPRE la carpeta Música real completa, sin depender de
      que esos dos campos de Configuración estén bien seteados. Si no
      se encuentra ninguna carpeta de Música válida, avisa en vez de
      romper (mismo criterio fail-open de siempre).

    Probado extendiendo `test_ubicar_vincular_archivo.py` (mockeando
    `_resolver_carpeta_musica_real` a una carpeta de prueba única):
    dos candidatos del mismo tamaño se encuentran —uno en la raíz, uno
    en subcarpeta, recursivo—, un candidato de OTRO tamaño ahora queda
    AFUERA (antes aparecía igual, solo sin la marca de coincidencia);
    un registro sin tamaño guardado cae a duración como único
    criterio; `_resolver_carpeta_musica_real()` probado con
    `subprocess.run`/`os.path.isdir`/`os.path.expanduser` mockeados
    para los 3 casos (xdg-user-dir responde, cae a `~/Musica`, no
    encuentra nada -> `None`) — + `test_dialogo_vincular_archivo.py`
    actualizado a las 6 columnas nuevas (se agregó "¿Duración
    coincide?") + suite de regresión completa sin fallos nuevos
    (mismos 7 fallos preexistentes de siempre) + smoke test de
    arranque limpio. **Sigue sin poder confirmarse con la biblioteca
    real de Santiago**: falta que confirme que ahora SÍ encuentra los
    archivos perdidos (con la causa de fondo corregida, el tamaño
    exacto en bytes debería ser mucho más confiable que la duración
    estimada), y que escanear toda la carpeta Música real —en vez de
    las rutas configuradas— no tarda demasiado con su biblioteca de
    varios miles de archivos.
80. ~~Tres mejoras sobre "Ubicar"/"Vincular": Tomar el nombre/Eliminar
    sobre los candidatos, botón "⏭ Saltar", verificación masiva desde
    Configuración~~ — pedido explícito, 3 puntos (a-c), sobre el
    diálogo de candidatos de la ronda anterior:

    **a) Menú contextual sobre cada candidato — "✏ Tomar el nombre" /
    "🗑 Eliminar"**: nuevo en `gui/dialogo_vincular_archivo.py`
    (`QMenu` sobre `self.tree`, mismo patrón de `customContextMenuRequested`
    ya usado en el resto de la app). "Tomar el nombre" renombra el
    archivo candidato EN DISCO al título del registro roto (pedido
    explícito: "respetando la extensión — sin pedir confirmación") —
    `_sanitizar_nombre_archivo()` reemplaza los caracteres inválidos
    de filesystem (`/ \ : * ? " < > |`) por `_`, y la extensión es la
    REAL del archivo candidato (nunca inventada a partir del título).
    Si ya existe un archivo con ese nombre en la carpeta, avisa y NO
    pisa nada (nunca sobreescribe en silencio). "Eliminar" borra el
    archivo candidato de la PC de forma definitiva, con
    `QMessageBox.question` de confirmación SIEMPRE (pedido explícito
    "con un aviso previo") — **aclaración importante de Santiago,
    respetada al pie de la letra**: "eliminar el archivo de la
    computadora no elimina el registro de la base JSON, lo utilizaré
    por si hay 2 archivos iguales o las coincidencias no son las que
    yo esperaba y sobra el archivo" — esta acción es pura limpieza de
    disco sobre candidatos encontrados, NUNCA toca `biblioteca.json`
    ni el registro roto que se está buscando (a propósito, un
    concepto totalmente distinto de "Eliminar registro" del diálogo
    inicial de "Ubicar", que sí borra la entrada JSON pero nunca toca
    ningún archivo real).

    **b) Botón "⏭ Saltar"**: pasa al PRÓXIMO archivo sin vincular sin
    elegir ningún candidato de este — pedido explícito, "para que pase
    al siguiente archivo no localizado de la Categoría". Implementado
    con un código de resultado propio en `DialogoVincularArchivo`
    (`SALTAR = 2`, vía `self.done(self.SALTAR)` — distinto de
    `Accepted=1`/`Rejected=0`, así el llamador puede distinguir los 3
    desenlaces). Del lado de `VentanaExplorador`
    (`gui/ventana_explorador.py`), esto obligó un rediseño de fondo del
    flujo de "Buscar" — antes una función aislada por ítem, ahora un
    procesador de COLA compartido:
    - `_buscar_archivo_perdido(item, registro, categoria, carpeta_musica)`
      cambió de firma (`categoria`/`carpeta_musica` ahora los resuelve
      el LLAMADOR, no la función — necesario para no repetir el
      resolver de carpeta en cada ítem de una cola larga) y de
      contrato: devuelve `True` ("seguir con el próximo de la cola" —
      Vincular exitoso, Saltar, o sin candidatos) o `False` ("Cancelar"
      del operador, corta TODA la cola).
    - `_procesar_lista_de_perdidos(entradas: list[(categoria, registro,
      item)]) -> bool` (nuevo): el driver único que recorre la cola,
      resuelve la carpeta Música UNA sola vez al principio (no una vez
      por ítem), y llama a `_buscar_archivo_perdido` por cada entrada
      hasta que devuelva `False` o se acabe la lista. `item` puede ser
      `None` (registro no visible en `tree_archivos` en ese momento —
      típico de una cola que abarca otras categorías) — 
      `_aplicar_nuevo_archivo()` se extendió para tolerar `item=None`
      (solo actualiza la biblioteca persistida, sin tocar ninguna fila
      visual en ese caso).
    - `_ubicar_archivo()` (el "Ubicar" individual del menú contextual)
      ahora arma la cola completa ANTES de arrancar: el ítem
      clickeado (con su `item` real) + todo el resto de registros SIN
      vincular de la MISMA categoría, en orden, buscados a partir de
      su posición (con `item=None`, ya que no están necesariamente
      visibles) — así "Saltar" siempre tiene a dónde seguir dentro de
      esa categoría, tal cual pidió Santiago.

    **c) Verificación masiva desde Configuración**: nuevo botón
    "🔗 Verificar archivos perdidos (todos)" en Configuración →
    Diagnóstico (mismo patrón de habilitación condicional que
    "🔎 Verificar biblioteca"/"🔄 Reanalizar biblioteca" — deshabilitado
    sin `ventana_explorador`). Nuevo método público
    `VentanaExplorador.verificar_archivos_perdidos_biblioteca()`:
    recorre TODA la biblioteca (`_para_cada_categoria`), arma la cola
    de TODOS los registros con vínculo roto (sin ruta, o
    `os.path.exists()` falso) en orden de categoría, pide confirmación
    una sola vez ("¿Revisarlos ahora, uno por uno?"), y reusa el MISMO
    `_procesar_lista_de_perdidos()` que ya usa "Saltar" — cero lógica
    duplicada entre el caso "una categoría" y el caso "toda la
    biblioteca", ambos son simplemente listas de entrada distintas
    para el mismo procesador de cola. Al terminar la cola completa,
    avisa "Verificación completa"; si el operador cierra algún
    diálogo de candidatos con Cancelar a mitad de camino, la cola se
    corta ahí (`_procesar_lista_de_perdidos` devuelve `False`) y ese
    aviso final NO aparece — evita el mensaje engañoso de "completo"
    sobre una revisión que en realidad se abandonó a mitad de camino.

    Probado extendiendo `test_ubicar_vincular_archivo.py` (Saltar dos
    veces avanza por los 3 pendientes de una categoría en orden, sin
    vincular los saltados, vinculando solo el último con "Vincular";
    verificación masiva: sin nada pendiente avisa sin preguntar, con
    "No" no abre ningún diálogo, con "Sí" procesa la cola completa
    entre categorías sin tocar el registro que ya estaba bien, cancelar
    a mitad de camino corta la cola sin el mensaje de "completa" y sin
    llegar a procesar el resto; botón de Configuración existe,
    se deshabilita sin `ventana_explorador`, y delega correctamente) +
    `test_dialogo_vincular_archivo.py` extendido (Saltar deja el código
    propio sin ruta elegida; menú contextual con exactamente las 2
    acciones nuevas; "Tomar el nombre" renombra de verdad en disco con
    sanitización y extensión real, actualiza la fila, y avisa sin pisar
    si el destino ya existe; "Eliminar" pide confirmación siempre,
    borra el archivo real y la fila, deshabilita Vincular al vaciar la
    lista, y con "No" no borra nada) — + suite de regresión completa
    sin fallos nuevos (mismos 7 fallos preexistentes de siempre) +
    smoke test de arranque limpio. **Sigue sin poder confirmarse con
    hardware/biblioteca real**: falta que Santiago confirme (1) que
    "Tomar el nombre" deja archivos con nombres reconocibles sin pisar
    nada por accidente, (2) que "Eliminar" sobre un candidato de sobra
    no le genera dudas sobre si toca o no su JSON (aclarado en el
    código y en este archivo, pero vale la pena que lo confirme en la
    práctica), (3) que "Saltar" se siente natural para revisar una
    categoría entera de un tirón, y (4) que la verificación masiva de
    Configuración es cómoda para una limpieza grande de toda la
    biblioteca de una sola vez.
81. ~~Mostrar la categoría/subcategoría del registro roto en el diálogo
    de candidatos~~ — pedido explícito, retoque chico sobre la ronda
    anterior: "algunos archivos son Cierre.mp3 y no sé a qué programa
    o categoría corresponde... necesito esa información para vincular
    correctamente". `VentanaExplorador._buscar_archivo_perdido()`
    calcula `" > ".join(self.ruta_de_categoria(categoria))` (helper YA
    existente, de la ronda del Musicalizador Avanzado — camino de
    nombres desde la raíz hasta la categoría, ej. `"Programas >
    Cierres"`) y se lo pasa como parámetro nuevo (`ruta_categoria`) a
    `DialogoVincularArchivo`, que lo muestra en negrita, en su propia
    línea, separado del resto del texto (`self.lbl_categoria`, pedido
    explícito "bien visible") — así un título genérico como "Cierre"
    ya no deja al operador adivinando de qué programa/categoría se
    trata. Categoría vacía (una de nivel raíz, sin padre) muestra
    "(raíz, sin subcategoría)" en vez de quedar en blanco. De paso, el
    mensaje de "no se encontró ningún candidato" también incluye la
    categoría, mismo criterio.

    Probado extendiendo `test_ubicar_vincular_archivo.py` (se le pasa
    al diálogo la categoría correcta de nivel raíz, y el camino
    completo "Padre > Hijo" con una subcategoría real) +
    `test_dialogo_vincular_archivo.py` (la etiqueta muestra la
    categoría pasada, y aclara "(raíz...)" cuando no hay ninguna) +
    suite de regresión completa sin fallos nuevos (mismos 7 fallos
    preexistentes de siempre) + smoke test de arranque limpio.
82. ~~Subrayado visual de los ítems sin vinculación en Ventana 3~~ —
    pedido explícito: "agreguemos un subrayado de los ítem que no
    tengan vinculación... así también me doy cuenta visualmente". Antes
    de esta ronda, la única forma de notar un vínculo roto era abrir el
    menú contextual "📍 Ubicar" ítem por ítem — ahora se ve de un
    vistazo recorriendo la lista. Nuevo `VentanaExplorador.
    _actualizar_vinculo_item(item, registro)`: si `registro["ruta"]`
    está vacía o `os.path.exists()` da `False`, subraya la fuente de
    las 5 columnas de esa fila (mismo criterio de "aplicar a todas las
    columnas" que ya usa `_pintar_por_genero` para el color, pero
    INDEPENDIENTE del color — un ítem sin vínculo puede ser de
    cualquier género). Llamado desde `_agregar_fila_archivo()` (cubre
    los 3 caminos que arman una fila: selección de categoría, búsqueda,
    y alta de un archivo nuevo — recalculado en cada re-render, sin
    necesitar un watcher de filesystem) y desde `_aplicar_nuevo_archivo()`
    (para que "⟲ Reemplazar"/"🔗 Vincular" saquen el subrayado en el
    momento, sin tener que recargar la categoría a mano).

    Probado con `test_subrayado_sin_vinculo.py` (nuevo, dedicado): un
    ítem con archivo real en disco queda sin subrayar, uno con la ruta
    rota y uno sin ruta en absoluto quedan subrayados en las 5
    columnas por igual, vincular un ítem roto le saca el subrayado al
    instante, y reconstruir la categoría desde cero recalcula todo de
    nuevo sin depender de estado previo — + suite de regresión
    completa sin fallos nuevos (mismos 7 fallos preexistentes de
    siempre) + smoke test de arranque limpio. Falta que Santiago
    confirme que el subrayado se distingue bien a simple vista con su
    biblioteca real, sobre todo en filas ya coloreadas por género.

83. ~~Ventana 2 saltea ítems sin vinculación (mismo criterio que V1) +
    ícono de error en el salteado + fix real de "no puedo eliminar
    ítems sin vinculación" + buscador de duplicados~~ — pedido
    explícito, 4 partes: "a) En la ventana 2 apliquemos el mismo
    criterio que la ventana 1: si hay un ítem no vinculado, que no se
    detenga y que pase al que sigue debajo. b) A ese que pasó sin
    vinculación, lo deje marcado en vez con el icono 'ok', con una
    'x' roja de error. c) Revisá por qué no puedo eliminar de la
    biblioteca (ventana 3) item que NO esten vinculados... vuelven a
    aparecer. d) Incorporame en la ventana configuraciones, otro botón
    de búsqueda de duplicados en el explorador (ventana 3) por
    nombre, duración y tamaño con opción de elegir alguno de esos
    filtros incluso los 3 juntos. Menú contextual de mover o eliminar.
    Debo ver las rutas de categorias cuando aparezcan duplicados."

    **a+b) Ventana 2 (Emisión/Auxiliar) ahora saltea ítems sin
    vinculación, mismo criterio que Ventana 1**: hasta esta ronda,
    `GestorPlaylist` solo reaccionaba REACTIVAMENTE a un archivo
    faltante (vía `error_reproduccion` de `MotorAudio`, tras el
    intento real de reproducir) — si varios ítems rotos caían
    seguidos, `reintentos_maximos` se agotaba y el aire se cortaba
    entero, el mismo bug que Ventana 1 ya tenía corregido desde la
    ronda 66 (`_item_valido()`, chequeo proactivo con
    `os.path.exists()` antes de intentar reproducir nada). Portado a
    `core/gestor_emision.py`: `_fila_valida(fila)` (nuevo) hace el
    mismo chequeo proactivo y marca/desmarca la X roja de error EN EL
    MISMO momento en que evalúa cada fila; `_resolver_siguiente_fila_
    valida(fila_inicio, total)` (nuevo) es un bucle que avanza fila
    por fila hasta encontrar una reproducible, aplicando la MISMA
    lógica de fin de lista que ya tenían `_avanzar()`/
    `_iniciar_crossfade()` (refill del Musicalizador si hay un
    formato activo, si no "repetir al finalizar", si no detenerse) —
    con un tope defensivo (`total + 2` vueltas) para nunca colgarse
    ante una lista totalmente rota con "repetir" activo. Los TRES
    puntos de entrada que deciden "qué ítem sigue" ahora pasan por
    acá: `_avanzar()` y `_iniciar_crossfade()` (los dos caminos
    paralelos de siempre, ver "Cosas ya resueltas" — el chequeo se
    agregó a los DOS, no solo a uno) reemplazan su viejo bloque
    inline de fin-de-lista por un llamado a
    `_resolver_siguiente_fila_valida()`, y `reproducir_actual()`
    (Play manual) ahora valida el ítem armado ANTES de reproducirlo,
    saltando al próximo válido si hace falta — antes Play sobre un
    ítem roto simplemente lo intentaba igual. El ícono se implementa
    reusando `ROL_ITEM_CON_ERROR`/`icono_error()` de `gui/styles.py`
    (ya existentes desde la ronda de V1, genéricos, sin nada
    V1-específico) — `PanelReproductor.marcar_item_con_error_en_fila()`
    (nuevo) prende la X roja o, si no hay error, restaura el tilde
    verde de "ya reproducido" si el ítem lo tenía, o lo deja sin
    ícono. **Bug de delegación evitado de raíz, no atrapado después**
    (mismo patrón ya documentado muchas veces en este archivo): el
    método nuevo se delegó de una en `VentanaEmision` Y
    `VentanaAuxiliar` a la vez, antes de dar la ronda por terminada.

    **c) Bug real corregido — "no puedo eliminar ítems sin
    vinculación... vuelven a aparecer"**: causa de fondo en
    `gui/ventana_explorador.py` — `_eliminar_archivo()`/
    `_eliminar_registro_sin_confirmar()` ubicaban la categoría de
    origen de un ítem con `_buscar_categoria_de_ruta(ruta)`, que
    compara por `ruta` contra `ROL_ARCHIVOS` — con `ruta` VACÍA (un
    material nunca vinculado, exactamente el caso que Santiago estaba
    resolviendo a mano con "Vincular"), esa búsqueda no encuentra
    NADA: el ítem se sacaba de `tree_archivos` (visualmente
    desaparecía) pero JAMÁS se sacaba de la lista `ROL_ARCHIVOS`
    persistida de su categoría — al recargar la categoría (o
    reabrir la app), volvía a aparecer, tal cual describió Santiago.
    Corregido de raíz con un rol nuevo, `ROL_CATEGORIA_ORIGEN`
    (`Qt.ItemDataRole.UserRole + 22`): cada fila de `tree_archivos`
    ahora guarda una referencia DIRECTA al `QTreeWidgetItem` de su
    categoría de origen (seteada en `_agregar_fila_archivo()`, que
    ganó un parámetro obligatorio `item_categoria`) — nunca hay que
    re-derivar la categoría comparando por ruta, así que una ruta
    vacía deja de ser un caso especial roto. `_llenar_tree_archivos()`
    (el batcheador de la ronda de rendimiento) pasó a recibir tuplas
    `(registro, categoria)` en vez de una lista plana de registros —
    todos sus llamadores (`_on_categoria_seleccionada`, `_buscar`,
    `_ordenar_por_columna`) se actualizaron para armar esas tuplas.
    Con la categoría ya resuelta sin ambigüedad, `_eliminar_archivo()`/
    `_eliminar_registro_sin_confirmar()`/la rama "buscar" de
    `_ubicar_archivo()` se simplificaron para usar un helper nuevo
    compartido, `_quitar_registro_de_lista(registros, registro)`
    (función pura, sin Qt): filtra por `ruta` si el registro la tiene,
    o por `código+título` si no (el código es único DENTRO de una
    categoría) — la MISMA lógica que antes vivía duplicada en dos
    lugares, ahora en un solo sitio, reutilizada también por el
    buscador de duplicados del punto (d).

    **d) Buscador de duplicados (Configuración → Diagnóstico, botón
    nuevo "🧩 Buscar duplicados en el explorador")**: `VentanaExplorador.
    buscar_duplicados_biblioteca(por_nombre, por_duracion, por_tamano)`
    (nuevo) recorre TODA la biblioteca (`_para_cada_categoria`) y
    agrupa por la INTERSECCIÓN de los criterios tildados (combinables
    — con los 3 activos, dos registros solo cuentan como duplicados si
    coinciden en título, duración Y tamaño en bytes a la vez); un
    registro con algún dato faltante en un criterio activo (ej.
    `tamaño_bytes` no cacheado) se excluye de ESE agrupamiento —
    nunca junta "sin dato" con "sin dato", evitaría falsos positivos.
    Solo se devuelven grupos de 2+ (duplicados reales). Nuevo diálogo
    `gui/dialogo_duplicados.py` — 3 checkboxes de criterio + botón
    "🔎 Buscar duplicados", resultado agrupado en un árbol (un nodo por
    grupo, con la cantidad de coincidencias; hijos con Título/Categoría/
    Duración/Tamaño/Ruta) — pedido explícito "debo ver las rutas de
    categorías": cada fila muestra el camino completo
    (`ruta_de_categoria()`, "Padre > Hijo", ya existente desde el
    Musicalizador). Menú contextual sobre cada candidato: "📂 Mover a
    categoría..." (reusa `gui/dialogo_seleccionar_categoria.py`, ya
    existente, + `VentanaExplorador.mover_registro_a_otra_categoria()`
    nuevo — variante de `_mover_archivos_a_categoria()` que no depende
    de resolver la categoría de origen por ruta, ya que acá el
    registro y su categoría de origen vienen resueltos de antes) y
    "🗑 Eliminar registro de la biblioteca" (con confirmación siempre,
    `VentanaExplorador.eliminar_registro_de_categoria()` nuevo).
    **Distinción importante, aclarada en el propio código y pedida
    explícitamente por Santiago para el diálogo de "Ubicar" de una
    ronda anterior (no cambia acá, pero se reafirma para no
    confundir)**: "Eliminar" en ESTE diálogo borra el REGISTRO (la
    entrada de la biblioteca JSON), nunca el archivo físico — el
    concepto exactamente OPUESTO al "🗑 Eliminar" del diálogo de
    Vincular archivos perdidos (`gui/dialogo_vincular_archivo.py`),
    que borra el archivo real de la PC y nunca toca el JSON. Los dos
    conviven a propósito, cada uno con su alcance bien distinto —
    documentado en el docstring de cada diálogo para que quede claro
    de dónde se dispara cada cosa.

    Probado con `test_ronda_v2_skip_y_eliminar_c_duplicados.py`
    (nuevo, dedicado, cubre las 4 partes): Ventana 2 —
    `_fila_valida()` marca/desmarca la X correctamente,
    `reproducir_actual()` saltea un ítem armado roto y arranca en el
    siguiente real (marcándolo "ya reproducido"), `_avanzar()` desde
    el fin de la lista envuelve y saltea el roto sin detenerse,
    `_iniciar_crossfade()` nunca cruza hacia un ítem roto; Ventana 3 —
    un registro con `ruta=""` se elimina de la lista VISUAL Y de la
    PERSISTIDA (confirmado recargando la categoría, ya no reaparece);
    duplicados — agrupa por nombre solo, por nombre+duración
    (criterios más estrictos separan grupos), sin ningún criterio no
    agrupa nada, mover/eliminar un registro puntual funciona y el
    diálogo se puebla correctamente al buscar — + suite de regresión
    completa sin fallos nuevos (mismos 7 fallos preexistentes de
    siempre: `test_audio_only_y_buffer.py`, `test_confirmaciones.py`,
    `test_fade_in_declick_v1.py`, `test_log_git.py`,
    `test_ronda_ajustes_dinesat2.py`, `test_ronda_dinesat3.py`,
    `test_ventana3.py`) + smoke test de arranque limpio. **Nota de
    infraestructura de testing, no de la app**: el chequeo proactivo
    nuevo de Ventana 2 rompió varios scripts de regresión preexistentes
    que usaban rutas `/tmp/*.mp3` ficticias (nunca creadas en disco)
    como simple placeholder de "algún archivo" — confirmado uno por
    uno que ninguno probaba intencionalmente el camino de "archivo
    faltante" (eso lo prueban tests dedicados, con nombres explícitos
    tipo `no_existe_de_verdad_*`, que SÍ se dejaron sin crear a
    propósito) — se crearon como archivos vacíos reales en `/tmp` los
    que sí eran simples placeholders, mismo criterio ya usado en la
    ronda 66. **Sigue sin poder probarse con audio/VLC real** (como
    todo lo que toca el motor de reproducción): falta que Santiago
    confirme con su radio real que un archivo movido/borrado en
    Ventana 2 ahora se saltea solo (con la X roja) en vez de cortar el
    aire, y que el buscador de duplicados encuentra y permite resolver
    duplicados reales de su biblioteca.

84. ~~"Ubicar" archivos perdidos: Vincular ahora también toma el
    nombre del JSON automáticamente~~ — pedido explícito: "cuando
    vincule, automáticamente además también tome el nombre del
    archivo del JSON, me parece más práctico y rápido". Antes había
    que hacer DOS pasos (clic derecho → "✏ Tomar el nombre" sobre el
    candidato, y RECIÉN DESPUÉS "🔗 Vincular") — ahora Vincular hace
    las dos cosas de una sola vez. `gui/dialogo_vincular_archivo.py`:
    la lógica de renombrar el archivo EN DISCO al título del registro
    roto (respetando su extensión real) se extrajo a un único método
    compartido, `_renombrar_a_titulo_registro(item, avisar_si_falla)`
    — `_tomar_nombre()` (la acción manual del menú contextual) lo
    llama con `avisar_si_falla=True` (mismo comportamiento de siempre:
    avisa si el nombre ya existe o si el renombre falla); `_vincular()`
    lo llama PRIMERO, con `avisar_si_falla=False`, y usa la ruta que
    devuelve (la nueva si el renombre salió bien, la original si no)
    como el vínculo final — si el renombre falla por lo que sea (ya
    existe un archivo con ese nombre, permisos), el vínculo se hace
    igual con la ruta ORIGINAL, nunca se bloquea por un problema de
    nombre. "✏ Tomar el nombre" sigue disponible por separado en el
    menú contextual, para el caso de querer renombrar sin vincular
    todavía (ej. mientras se decide entre varios candidatos).

    Probado extendiendo `test_dialogo_vincular_archivo.py`: Vincular
    sobre un candidato real en disco confirma que el archivo queda
    renombrado al título del registro (extensión real preservada) y
    que la ruta devuelta es la nueva; un caso de colisión (ya existe
    un archivo con el nombre destino) confirma que Vincular sigue
    funcionando igual, usando la ruta ORIGINAL sin romperse — + suite
    de regresión completa sin fallos nuevos (mismos 7 fallos
    preexistentes de siempre: `test_audio_only_y_buffer.py`,
    `test_confirmaciones.py`, `test_fade_in_declick_v1.py`,
    `test_log_git.py`, `test_ronda_ajustes_dinesat2.py`,
    `test_ronda_dinesat3.py`, `test_ventana3.py`) + smoke test de
    arranque limpio. Falta que Santiago confirme en la práctica que
    vincular un archivo perdido deja el nombre del archivo en disco
    igual al título que tiene registrado, sin tener que hacer el paso
    de "Tomar el nombre" por separado.

85. ~~Ventana 3: edición masiva sobre selección múltiple — Editar
    información, Exportar, Vigencia (Eliminar ya lo tenía)~~ — pedido
    explícito: "en la ventana 3, cuando hago selección múltiple, me
    gustaria poder editar masivamente las siguientes opciones: Editar
    Información (todos, menos el nombre, poder darle la categoria),
    Exportar (exportar todos los archivos seleccionados), Vigencia
    (establecer una vigencia general para todos), Eliminar (Borrar de
    la base JSON los seleccionados previa confirmación)". De las 4,
    "Eliminar" ya admitía selección múltiple desde la ronda de
    persistencia de Ventana 3 (`_eliminar_archivo()`, con una sola
    confirmación para todo el lote) — se reconfirmó con un test, sin
    tocar código. Las otras 3 se extendieron esta ronda:

    - **Exportar en lote**: `_exportar_archivo(item)` se reemplazó por
      `_exportar_archivos(items: list)` — pide la carpeta destino UNA
      sola vez y copia cada archivo con su nombre real (basename),
      salteando sin romper el resto los que no tengan archivo (ej. un
      registro sin vincular) y avisando al final cuántos se copiaron
      de cuántos, con el detalle de errores si hubo alguno.
    - **Editar información en lote** (pedido explícito "todos, menos
      el nombre, poder darle la categoría"): nuevo diálogo
      `gui/dialogo_editar_informacion_masivo.py` — SIN campo de título
      (cada archivo conserva el suyo, a propósito), con un checkbox
      "Cambiar a" por cada campo (Artista/Género/Categoría): sin
      tildar, ese campo queda intacto en todos los seleccionados;
      tildado, se aplica el MISMO valor a todos de una (incluido dejar
      el Artista vacío a propósito, si se tilda con el campo en
      blanco). Nuevo `VentanaExplorador._editar_informacion_masivo(items)`.
    - **Vigencia en lote** (pedido explícito "establecer una vigencia
      general para todos"): reutiliza el mismo `DialogoVigencia` de
      siempre (ya genérico, sin cambios) — UN solo diálogo, aplicado
      igual a todos los seleccionados (a diferencia de Información,
      acá no hace falta un checkbox "cambiar o no": el pedido es fijar
      la MISMA vigencia para todo el lote, incluyendo dejarla sin
      restricción si no se tilda ninguna fecha). Nuevo
      `VentanaExplorador._editar_vigencia_masiva(items)`.

    **Bug real de fondo evitado de raíz en las ediciones nuevas (y
    corregido de paso en las dos versiones de UN solo archivo que ya
    existían)**: `_editar_informacion_archivo()`/`_editar_vigencia()`
    (single-ítem) ubicaban la categoría de un registro con
    `_buscar_categoria_de_ruta(ruta)` — la MISMA función cuyo problema
    con `ruta` vacía (archivo nunca vinculado) ya se había corregido
    para "Eliminar" en la ronda anterior (`ROL_CATEGORIA_ORIGEN`), pero
    acá había quedado sin tocar. Corregido en las CUATRO funciones
    (single y masivo, Información y Vigencia) usando siempre
    `item.data(0, ROL_CATEGORIA_ORIGEN)` — nunca vuelve a fallar
    silenciosamente ("No se encontró la categoría") sobre un archivo
    sin vincular. De paso, se agregó `_buscar_indice_registro()`
    (nuevo, función pura junto a `_quitar_registro_de_lista()`): mismo
    criterio de identidad (ruta si la tiene, código+título si no) pero
    para MUTAR un registro en su lugar dentro de la lista viva de la
    categoría, en vez de filtrarlo afuera — reemplaza a
    `_sincronizar_registro_en_categoria()` en estos cuatro caminos
    (esa función seguía comparando solo por ruta, con el mismo
    problema latente).

    Menú contextual: "📤 Exportar...", "✏ Editar información..." y
    "📅 Vigencia..." ahora quedan HABILITADAS con cualquier cantidad de
    seleccionados (antes solo con exactamente 1), con el conteo en el
    texto ("Exportar 3...", etc.) cuando hay selección múltiple.
    "⟲ Reemplazar...", "🎚 Editar audio" y "📍 Ubicar" siguen acotadas a
    UN solo archivo a la vez a propósito — cambiar el archivo de audio,
    abrir un editor externo, o buscar un archivo perdido puntual no
    son operaciones que tengan sentido aplicar en lote sin ambigüedad.

    Probado con `test_edicion_masiva_ventana3.py` (nuevo, dedicado, 18
    verificaciones): Exportar copia los archivos reales y saltea sin
    romper el que no tiene ruta; Editar información en lote mueve los
    3 registros a la categoría destino, deja el TÍTULO de cada uno
    intacto, aplica el artista tildado a los 3 (incluido el que nunca
    tuvo ruta) y NO toca el género (checkbox sin tildar); Vigencia en
    lote aplica la misma fecha de inicio/fin a los 3; Eliminar en lote
    pide confirmación UNA sola vez y saca los 3 de la vista Y de la
    biblioteca persistida; el menú contextual habilita Exportar/
    Información/Vigencia y mantiene deshabilitadas Reemplazar/Editar
    audio/Ubicar con 2+ seleccionados — + actualización de un test
    preexistente (`test_ronda_hth_update_preload_editar.py`, su ítem
    de prueba de "Editar información" no traía `ROL_CATEGORIA_ORIGEN`
    seteado, un requisito nuevo desde la ronda anterior que ese test
    nunca necesitó hasta ahora — no es una regresión, es el mismo tipo
    de actualización de fixture ya documentado en rondas previas) +
    suite de regresión completa sin fallos nuevos (mismos 7 fallos
    preexistentes de siempre: `test_audio_only_y_buffer.py`,
    `test_confirmaciones.py`, `test_fade_in_declick_v1.py`,
    `test_log_git.py`, `test_ronda_ajustes_dinesat2.py`,
    `test_ronda_dinesat3.py`, `test_ventana3.py`) + smoke test de
    arranque limpio. Falta que Santiago confirme en la práctica que la
    edición masiva de Información/Exportar/Vigencia se siente natural
    con selección múltiple real, y que "Editar información" en lote
    (con la categoría tildada) mueve todo lo esperado sin sorpresas.
86. ~~Se saca la descarga de YouTube (reemplazada por un botón "Bays")
    + buscador de duplicados AVANZADO con coincidencia aproximada en 3
    niveles de prioridad~~ — pedido explícito, dos partes en el mismo
    mensaje ("estamos casi sobre el final"):

    **a) YouTube afuera, botón "Bays" en su lugar**: `core/
    descargador_youtube.py` eliminado por completo (el módulo de
    `yt-dlp`, ronda 53) junto con toda su UI en Ventana 3 (el
    `QGroupBox` "⬇ Descargar de YouTube", el campo de URL, y los
    métodos `_descargar_de_youtube()`/`_dar_de_alta_descarga_youtube()`/
    `_obtener_o_crear_categoria_por_ruta()`) y la dependencia `yt-dlp`
    de `requirements.txt`. En su lugar, un `QGroupBox` nuevo
    "🧰 Herramientas" con dos botones: **"🎙 Bays"**
    (`VentanaExplorador._abrir_bays()`) — mismo patrón ya usado para
    `mhwaveedit`/los gestores de archivos con selección (`shutil.which`
    + `QProcess.startDetached`, sin ningún argumento) — solo lanza el
    comando `bays` ya instalado en la PC, sin ninguna otra integración
    con el programa; si no está instalado, avisa con un mensaje claro
    en vez de fallar en silencio. Y **"🧩 Buscar duplicados"** (ver
    abajo). El buscador SIMPLE de criterios exactos combinables
    (`gui/dialogo_duplicados.py`, ronda 83, accesible desde
    Configuración → Diagnóstico) NO se tocó — sigue existiendo como
    una opción más liviana, en paralelo al nuevo.

    **b) Buscador de duplicados AVANZADO — coincidencia APROXIMADA en
    3 niveles de prioridad** (pedido explícito, con las reglas exactas
    dadas por Santiago): a diferencia del buscador simple (coincidencia
    exacta por criterios combinables), este evalúa cada PAR de
    registros contra 3 niveles, del más estricto al más laxo, y se
    queda con el MEJOR que cumplan (nunca los evalúa en más de un
    nivel a la vez):
    - **Nivel 1**: nombre 100% + duración 100% + tamaño 100%.
    - **Nivel 2**: nombre 80%+ (similitud de texto) + duración 100%
      (exacta).
    - **Nivel 3**: nombre 50%+ (similitud de texto) + duración 90%+
      (similitud, no exacta).

    **Motor puro, sin Qt** (`core/buscador_duplicados.py`, mismo
    espíritu que `core/musicalizador.py`/`core/hth.py`):
    `similitud_nombres()` usa `difflib.SequenceMatcher` sobre el
    título normalizado (minúsculas, espacios colapsados);
    `duracion_a_segundos()`/`similitud_duracion()` parsean "HH:MM:SS"
    y comparan por proporción menor/mayor; `nivel_de_coincidencia()`
    aplica las 3 reglas en orden. `buscar_grupos_duplicados()` agrupa
    con **Union-Find**: dos registros que matchean en CUALQUIER nivel
    quedan en el MISMO grupo — transitivamente (A~B~C aunque A y C no
    matcheen directo entre sí), soportando de una el pedido explícito
    "pueden existir más de 2 archivos duplicados, la lista debe ser
    completa". `sugerir_indice_a_mantener()` es la heurística del modo
    en masa (ver abajo): prioriza el miembro con ruta vinculada +
    artista + tamaño cacheado (el más "completo"), con el primero como
    desempate estable.

    **Rendimiento — pensado para bibliotecas grandes desde el diseño**
    (ver rondas 76-78 de rendimiento con ~10-12 mil registros): en vez
    de comparar TODOS los pares (O(n²), inaceptable en el hardware
    modesto de Santiago), se ordenan los registros por duración y cada
    uno se compara solo contra una VENTANA de vecinos dentro del 90%
    de similitud de duración (el caso más laxo, nivel 3 — los niveles
    1 y 2, que exigen duración EXACTA, son un subconjunto de esa misma
    ventana, así que un solo recorrido cubre los 3). Dentro de la
    ventana, `similitud_nombres()` prueba DOS cotas superiores baratas
    antes de pagar el costo completo de `SequenceMatcher.ratio()`
    (cuadrático en el peor caso): una por longitud (O(1), sin
    construir nada) y `real_quick_ratio()` (O(n)) — si ninguna de las
    dos llega al umbral más bajo (0.5), la similitud real tampoco
    puede llegar (son cotas superiores garantizadas), así que se
    descarta el par sin calcular el ratio exacto. **Limitación de
    rendimiento CONOCIDA y documentada a propósito** (en el docstring
    del módulo): una biblioteca con MUCHOS temas agrupados en un rango
    de duración chico (frecuente en una radio real: cientos de
    canciones "de 3 minutos más o menos") puede tener una ventana
    ancha en esa zona y tardar un rato en esa franja — se priorizó
    CORRECCIÓN sobre velocidad extrema en el peor caso, ya que es una
    acción MANUAL y ocasional (mismo criterio que "Reanalizar
    biblioteca"), con cursor de espera y un `callback_progreso`
    opcional (`buscar_grupos_duplicados(entradas, callback_progreso=...)`)
    que la GUI usa para llamar `QApplication.processEvents()` cada 20
    ítems, así la ventana nunca se siente "colgada" mientras corre.

    **Flujo en la GUI** (`gui/dialogo_buscar_duplicados_avanzado.py` +
    orquestación en `VentanaExplorador`): el botón "🧩 Buscar
    duplicados" primero pregunta el ALCANCE
    (`_preguntar_alcance_duplicados()`, `QMessageBox` de 3 botones
    propios, mismo patrón que `_preguntar_que_hacer_con_archivo_perdido`)
    — **toda la base de datos** o **una categoría específica**
    (`gui/dialogo_seleccionar_categoria.py`, ya existente). Con una
    categoría elegida, se ofrece además el **bonus del modo automático
    en masa** (pedido explícito: "SOLO si eligió una categoría
    específica", nunca para toda la base de una) vía
    `_preguntar_modo_masa()`. `VentanaExplorador.
    buscar_duplicados_avanzado(item_categoria=None)` recorre el
    alcance elegido (toda la biblioteca vía `_para_cada_categoria()`,
    o una categoría + sus subcategorías, mismo patrón ya usado por
    `listar_registros_de_categoria()`) y arma los grupos con el motor.
    - **Revisión UNO POR UNO** (`DialogoRevisarGrupoDuplicado`,
      siempre disponible): un diálogo por grupo, secuencial — muestra
      TODOS los miembros con checkbox "Eliminar" (pre-tildado según
      `sugerir_indice_a_mantener()`, el resto queda implícitamente
      "mantenido"), botón **▶ Previo** (SIEMPRE la salida de
      Preescucha, nunca la Master que va al aire — mismo criterio que
      todo el resto de la app, `MotorAudio(id, aplicar_procesador=False)`),
      **✅ Aplicar y seguir** (con aviso si se tildó TODO el grupo,
      "no quedaría ninguno"), **⏭ Omitir este grupo** (código de
      resultado propio `SALTAR=2`, mismo patrón que
      `DialogoVincularArchivo`), y **Cancelar** (corta TODA la
      revisión, no solo ese grupo). `VentanaExplorador.
      _revisar_grupos_duplicados_uno_por_uno()` es el driver: itera
      los grupos, aplica lo tildado con `eliminar_registro_de_categoria()`
      (mismo método ya existente del buscador simple — "Eliminar"
      borra el REGISTRO, nunca el archivo físico, mismo criterio
      documentado desde la ronda 83) y termina con un reporte
      (`QMessageBox.information`: grupos con cambios, omitidos,
      archivos eliminados).
    - **MODO AUTOMÁTICO EN MASA** (`DialogoPlanMasivoDuplicados`,
      bonus solo-categoría): arma un PLAN completo de una — TODOS los
      grupos juntos en un árbol (nodo = grupo, hijos = miembros), cada
      uno con la MISMA sugerencia por defecto — y dos botones: **✅
      Aprobar plan completo** (aplica TODO lo tildado de una sola vez)
      o simplemente tildar/destildar cualquier ítem puntual ANTES de
      aprobar (satisface "drill down to edit plan per-item" sin una UI
      de "modo edición" separada — el propio árbol de checkboxes ES la
      edición). Mismo aviso de "grupo que quedaría vacío" que el flujo
      uno-por-uno, pero juntando TODOS los grupos afectados en un solo
      mensaje antes de aprobar. `VentanaExplorador.
      _ejecutar_modo_masa_duplicados()` aplica el plan aprobado y
      muestra el mismo tipo de reporte final.

    Probado con `test_buscador_duplicados_motor.py` (nuevo, motor
    puro: normalización/similitud de nombres y duración, los 3 niveles
    evaluados en orden correcto incluyendo el caso "duración exacta
    pero sin tamaño en ninguno de los dos, no puede ser nivel 1",
    agrupamiento por Union-Find transitivo con 3+ miembros y el nivel
    reportado es el MEJOR del grupo, `sugerir_indice_a_mantener()`, y
    2 pruebas de rendimiento — una con datos "realistas" de biblioteca
    de radio y otra deliberadamente adversarial — confirmando que el
    motor queda ACOTADO incluso en el peor caso, no que sea
    instantáneo) + `test_dialogo_buscar_duplicados_avanzado.py` (nuevo,
    construcción real de los 2 diálogos: checkboxes con la sugerencia
    correcta por defecto, `indices_a_eliminar()`/`plan_aprobado()`
    reflejan lo tildado, detección de "grupo que quedaría vacío",
    Previo/Detener degradan limpio sin libVLC) +
    `test_bays_y_duplicados_avanzado.py` (nuevo, integración GUI
    completa: YouTube 100% ausente —módulo, UI, dependencia—, "Bays"
    lanza el proceso encontrado y avisa si no está, el motor aplicado
    sobre el árbol real encuentra duplicados aunque estén en
    categorías/subcategorías distintas, alcance "toda"/categoría
    puntual, los 3 desenlaces del flujo uno-por-uno —Aplicar/Omitir/
    Cancelar—, el modo masa —Aprobar/Cancelar—, y el entry point
    `_buscar_duplicados_avanzado()` despachando al flujo correcto
    según la elección de alcance) + suite de regresión completa sin
    fallos nuevos (mismos 7 fallos preexistentes de siempre:
    `test_audio_only_y_buffer.py`, `test_confirmaciones.py`,
    `test_fade_in_declick_v1.py`, `test_log_git.py`,
    `test_ronda_ajustes_dinesat2.py`, `test_ronda_dinesat3.py`,
    `test_ventana3.py`) + smoke test de arranque limpio. **Sigue sin
    poder confirmarse con hardware/biblioteca real**: falta que
    Santiago confirme que "Bays" abre el programa esperado, y que
    pruebe el buscador de duplicados con su biblioteca real — en
    particular (1) si el nivel 3 (50% nombre + 90% duración) resulta
    demasiado laxo o demasiado estricto con sus nombres de archivo
    reales, (2) si el modo automático en masa sobre una categoría
    grande tarda un tiempo razonable, y (3) si la sugerencia por
    defecto de qué mantener (el más "completo": con ruta+artista+
    tamaño) coincide con su propio criterio la mayoría de las veces.
87. ~~"Veo que nunca funciona el recorte de silencio" — encontrado el
    bug de fondo: fallos SILENCIOSOS, nunca reportados~~ — pedido
    explícito de Santiago con la especificación completa de un
    sistema de "marcas de entrada y salida de reproducción" (no
    destructivo, registrado en la base JSON para MÚSICA, revisable
    desde Configuración, aplicado automáticamente al importar 1 o
    varios, y SIEMPRE respetado por Ventana 2/Emisión para el inicio y
    el fundido de salida) — auditando el código ANTES de programar
    nada nuevo, se confirmó que ESE sistema ya existe en su totalidad
    desde hace muchas rondas (`punto_inicio_ms`/`punto_fin_ms`/
    `ganancia_db`, calculados por `core/analizador_audio.py` y
    aplicados por `MotorAudio.reproducir()`/`_emitir_posicion()`,
    confirmado correctamente wireado en `core/gestor_emision.py` para
    Ventana 2) — así que en vez de reimplementar un sistema paralelo
    con el mismo riesgo de fallar en silencio, se buscó y corrigió la
    CAUSA REAL de "nunca funciona":

    **Bug real de fondo, el más importante de esta ronda — 2 fallos
    silenciosos encadenados**:
    1. `core/analizador_audio.py:analizar_audio()` (el motor que
       calcula las marcas) SOLO informaba un fallo con un `print()` a
       consola — invisible en el uso real, ya que la app se lanza
       desde el ícono de escritorio sin ninguna terminal a la vista.
       Si pydub o ffmpeg faltan (o cualquier otro error), el archivo
       se agregaba igual a la biblioteca con marcas "neutras"
       (`analizado=False`, sin recorte real) SIN QUE NADIE SE
       ENTERARA nunca.
    2. **El bug más grave**: `config/settings.py:reanalizar_biblioteca()`
       (el botón "🔄 Reanalizar biblioteca" de Configuración →
       Diagnóstico) contaba CUALQUIER intento como "reanalizado",
       nunca chequeaba si `analizar_audio()` realmente había logrado
       calcular algo (`analizado=True`) o había caído al fallback
       neutro — con el motor completamente roto (ej. sin ffmpeg
       instalado), el botón igual mostraba con total confianza "Listo:
       850 archivo(s) reanalizados", una mentira que le daba a Santiago
       la falsa sensación de que el problema ya estaba resuelto,
       cuando en realidad NINGÚN archivo había quedado con marcas
       reales. Esto explica con precisión el síntoma reportado: "nunca
       funciona", sin ningún error visible en ningún lado.

    **Corregido de raíz, en capas** (nunca confiar en una sola señal
    de que algo funcionó, mismo criterio ya aplicado varias veces en
    este proyecto para bugs de libVLC):
    - `analizar_audio()` ahora registra cada fallo en
      `log_aplicacion.txt` vía `registrar_error()` (import diferido,
      sin ciclo con `config/settings.py`) — con la ruta del archivo y
      el detalle exacto del error, diagnosticable desde Configuración
      → Diagnóstico → Ver log sin tener que reproducir el problema en
      vivo con Santiago.
    - `reanalizar_biblioteca()` cambió de devolver un simple conteo a
      un dict con desglose REAL: `{"total", "analizados", "fallidos",
      "musica_total", "musica_analizados"}` — el mensaje final en
      Configuración ahora es honesto: si hay fallos, `QMessageBox.warning`
      (no `information`) con el desglose completo y una sugerencia
      concreta; sin fallos, confirma cuántos quedaron con marcas reales
      de género Música específicamente (lo que le importa a Ventana 2).
    - **Nuevo botón "🩺 Verificar motor de análisis de audio"**
      (Configuración → Diagnóstico, siempre habilitado, no depende de
      tener la biblioteca cargada): `core.analizador_audio.
      verificar_motor_disponible()` hace una prueba REAL de punta a
      punta — genera un audio sintético en memoria (300ms de silencio
      + 1s de tono + 300ms de silencio, con `pydub.generators.Sine`,
      sin necesitar ningún archivo de la biblioteca), lo exporta a un
      WAV temporal, y confirma que `analizar_audio()` sobre ESE archivo
      da `analizado=True` — antes de chequear que `pydub` esté
      instalado y que el binario `ffmpeg` del sistema exista
      (`shutil.which`). Si algo falta, el mensaje dice EXACTAMENTE qué
      instalar (`pip install pydub` / `sudo apt install ffmpeg`), en
      vez de un fallo genérico.
    - **Chequeo automático al ABRIR la app** (`MainWindow.
      _verificar_motor_analisis_al_iniciar()`, diferido 3s, mismo
      criterio que la búsqueda de actualización — no competir con el
      arranque de la radio): si el motor está roto, un aviso NO MODAL
      (`show()`, nunca bloquea nada) avisa apenas se abre el programa
      — Santiago ya no tiene que pensar en ir a buscar un botón
      escondido para enterarse de que algo está mal; con el motor
      funcionando, no aparece nada (no se molesta en cada arranque).
    - **Ícono ⚠ visible por archivo, en Ventana 3** (pedido implícito
      de "hacerlo imposible de no notar"): `gui/styles.py:
      icono_sin_marcas_in_out()` (triángulo ámbar, mismo patrón de
      `QPainter` cacheado que `icono_reproducido()`/`icono_error()`) —
      `VentanaExplorador._actualizar_marcas_item()` lo prende sobre
      la columna Título de cualquier archivo de género Música con
      `analizado is False`, con un tooltip explicando por qué y a
      dónde ir a diagnosticarlo. Acotado a Música a propósito (el
      género que le importa a Ventana 2/Emisión) — Publicidad/
      Separador ya usan su propio criterio de corte estricto.
    - **Avisos al importar** (single y masivo): dar de alta UN archivo
      de Música con `analizado=False` dispara un `QMessageBox.warning`
      inmediato; importar un LOTE resume cuántos de cuántos fallaron
      en un solo aviso al final (no uno por archivo) — ambos apuntan
      al botón de verificación nuevo.

    **Confirmación de que el resto del sistema YA estaba bien
    implementado, sin necesitar ningún cambio** (auditado línea por
    línea antes de tocar nada, para no reimplementar algo que ya
    funcionaba): el registro en la base JSON para MUSICA ya ocurría en
    los 3 puntos de alta; "Reanalizar biblioteca" en Configuración ya
    existía (solo el reporte estaba roto); Ventana 2 ya respeta
    SIEMPRE `punto_inicio_ms` (seek al arrancar,
    `MotorAudio.reproducir()`) y `punto_fin_ms` (corte + disparo de
    crossfade, `_emitir_posicion()`/`restante_ms_cambio()`,
    confirmado wireado en `core/gestor_emision.py:_reproducir_fila()`/
    `_iniciar_crossfade()`); y el enfoque ya es 100% no destructivo
    (nunca edita el archivo de audio original, solo guarda marcas como
    metadata — documentado explícitamente en el propio
    `core/analizador_audio.py` desde su creación).

    Probado con `test_marcas_in_out.py` (nuevo, dedicado, con pydub Y
    ffmpeg REALES instalados en este sandbox para esta ronda —
    confirmando tanto el camino roto como el camino funcionando de
    punta a punta, no solo mockeado): `verificar_motor_disponible()`
    en sus 3 casos (sin pydub, con pydub pero sin ffmpeg, todo
    disponible con una prueba real de análisis); un fallo real de
    `analizar_audio()` queda en el log de la app; `reanalizar_biblioteca()`
    con el motor funcionando reporta el desglose correcto (incluido
    Música), y con el motor ROTO (simulado) confirma el bug ya
    corregido — CERO analizados de verdad, ya NUNCA se reporta como
    "reanalizado" un fallo; el ícono ⚠ aparece solo en Música sin
    marcas (nunca en Publicidad, nunca si sí tiene marcas); avisos
    correctos al dar de alta un archivo suelto y al importar un lote;
    el botón nuevo de Configuración siempre habilitado y con el
    mensaje correcto (éxito/fallo); el chequeo no-modal al arrancar
    dispara SOLO cuando el motor está roto — + actualización de un
    test preexistente (`test_ronda_dnd_reanalisis_ee.py`, asumía el
    tipo de retorno viejo de `reanalizar_biblioteca()` — int en vez de
    dict, no es una regresión, es el cambio de contrato de esta
    misma ronda) + suite de regresión completa sin fallos nuevos
    (mismos 7 fallos preexistentes de siempre: `test_audio_only_y_buffer.py`,
    `test_confirmaciones.py`, `test_fade_in_declick_v1.py`,
    `test_log_git.py`, `test_ronda_ajustes_dinesat2.py`,
    `test_ronda_dinesat3.py`, `test_ventana3.py`) + smoke test de
    arranque limpio. **Sigue sin poder confirmarse con la instalación
    real de Santiago** (la hipótesis de fondo — pydub/ffmpeg
    faltantes o rotos en su PC — no se puede verificar desde acá):
    falta que corra "🩺 Verificar motor de análisis de audio" (o
    simplemente reabra la app) y comparta EXACTAMENTE qué mensaje le
    da — recién con ese dato real se sabe si la causa era esta, y si
    corregirla (instalar lo que falte) resuelve el recorte de silencio
    de una vez.
88. ~~LA CAUSA DE FONDO real del "Falta instalar pydub" que no se
    iba: Python 3.13 sacó el módulo `audioop` de la librería estándar~~
    — Santiago corrió el diagnóstico de la ronda anterior y, tras
    instalar pydub/ffmpeg como se le indicó, seguía viendo EXACTAMENTE
    el mismo mensaje "Falta instalar pydub" — investigado con su log
    real (mismo criterio "ground truth de tu máquina real" ya usado
    para EasyEffects/PipeWire en su momento): `pip install -r
    requirements.txt` mostraba `pydub` como "already satisfied"
    (0.25.1, correctamente instalado) — el mensaje de diagnóstico
    estaba MINTIENDO por una razón distinta a la que decía.

    **Causa real, confirmada con el traceback real que pegó Santiago**:
    su Python es la versión 3.13 (`venv/bin/python3 -> /usr/bin/python3`,
    3.13.12) — Python 3.13 **eliminó el módulo `audioop`** de la
    librería estándar (PEP 594, deprecado desde 3.11); pydub (sin
    actualizarse desde 2021) todavía depende de él en
    `pydub/utils.py`, con un intento de `import audioop` y, si falla,
    un fallback a `import pyaudioop as audioop` — ninguno de los dos
    existe en su instalación, así que `import pydub` revienta con
    `ModuleNotFoundError: No module named 'pyaudioop'`. Como
    `ModuleNotFoundError` es subclase de `ImportError`, el `except
    ImportError` de `verificar_motor_disponible()` (ronda anterior) SÍ
    lo atrapaba — pero el código ASUMÍA que cualquier `ImportError` ahí
    significaba "pydub no está instalado", mostrando "Falta instalar
    pydub. pip install pydub" — instrucción que Santiago ya había
    seguido al pie de la letra, sin que cambiara nada, porque el
    paquete YA estaba instalado: el problema era una dependencia
    INTERNA de pydub (`audioop`), no pydub en sí.

    **Corregido distinguiendo los dos casos de verdad**, en vez de
    asumir uno solo: `verificar_motor_disponible()`
    (`core/analizador_audio.py`) ahora llama primero a
    `importlib.util.find_spec("pydub")` — confirma si el PAQUETE
    existe en disco SIN ejecutar su código (así nunca dispara el mismo
    error que se está diagnosticando) — y solo si el intento real de
    `import pydub` falla DESPUÉS de eso arma el mensaje:
    - Si `find_spec` no lo encontró: pydub genuinamente no está
      instalado → mensaje de siempre ("pip install pydub").
    - Si `find_spec` SÍ lo encontró pero el `import` real igual
      revienta: mensaje NUEVO, con el error real incluido
      (`{error}`, ej. "No module named 'pyaudioop'") y la causa
      probable explicada (Python 3.13+ sin `audioop`), con la
      instrucción correcta: `pip install audioop-lts` — el backport
      oficial de PyPI que repone ese módulo específicamente para
      Python 3.13+.
    - `requirements.txt` ganó `audioop-lts>=0.2.1; python_version >=
      "3.13"` — con marcador de versión de pip, así una instalación
      en Python < 3.13 (donde `audioop` todavía es parte de la
      librería estándar) directamente SALTEA esa línea sin instalar
      nada de más; confirmado contra el índice real de PyPI que el
      paquete existe con exactamente ese requisito de versión.

    Probado extendiendo `test_marcas_in_out.py`: caso "pydub NO
    instalado en absoluto" (mockeando `importlib.util.find_spec` para
    que no lo encuentre) sigue devolviendo el mensaje de siempre, SIN
    mencionar `audioop-lts`; caso NUEVO "pydub instalado pero el
    import revienta" (find_spec real -- lo encuentra porque
    genuinamente está instalado en este sandbox -- combinado con un
    `import` mockeado para fallar con el mismo error real de Santiago,
    `ModuleNotFoundError: No module named 'pyaudioop'`) confirma que el
    mensaje YA NO dice "pip install pydub", SÍ menciona `audioop-lts`
    como la causa/solución real, y conserva el detalle exacto del
    error para poder diagnosticar cualquier variante futura — + suite
    de regresión completa sin fallos nuevos (mismos 7 fallos
    preexistentes de siempre) + smoke test de arranque limpio.
    **Pendiente de confirmar con Santiago**: que corriendo `pip install
    audioop-lts` (con el venv activado) el diagnóstico pase a "Todo en
    orden", y que el recorte de silencio finalmente se escuche en la
    práctica — sería la primera confirmación real de que la CADENA
    COMPLETA (bug de reporte + causa real de Python 3.13) queda
    resuelta de punta a punta.
89. ~~Explorador: reanálisis de biblioteca como PROCESO APARTE (nunca
    más traba la app) + progreso gráfico en importación masiva +
    Ventana 1: variedad real de ítems Aleatorio entre bloques (batch
    de N + garantía dura de no-repetir dentro del mismo bloque)~~ —
    dos pedidos en el mismo mensaje:

    **a) Explorador: "tengo 9800 elementos... se trabó por obvias
    razones, necesitamos hacerlo con otro proceso aparte, que me
    indique el progreso"**: `config/settings.reanalizar_biblioteca()`
    corría TODO el reanálisis sincrónico en el hilo de la GUI, sin
    ningún `processEvents()` — con una biblioteca de miles de
    archivos, podía trabar la app ENTERA varios minutos sin ninguna
    señal de vida (ni barra, ni "está trabajando", nada). Nuevo
    `core/reanalizador_batch.py` (sin Qt, deliberadamente): la misma
    lógica de reanálisis (con el fix de "preservar marcas buenas" de
    la ronda 87) ahora corre en un **PROCESO PYTHON APARTE** — mismo
    patrón "nunca threading, siempre QProcess" ya establecido para
    EasyEffects/git/reinicio de la app. `config/settings.
    reanalizar_biblioteca()` quedó como un thin delegator a
    `core.reanalizador_batch.ejecutar_reanalisis()` (misma firma,
    mismo dict de stats — nada de la API pública cambió). El script
    corre de DOS formas: (1) como CLI suelto
    (`venv/bin/python3 -m core.reanalizador_batch`, con flags
    `--tolerancia-general/--tolerancia-v1/--umbral`) — pensado para el
    primer pase grande "por fuera" que pidió Santiago, con progreso
    real impreso en la terminal; (2) lanzado por la propia app
    (Configuración → "🔄 Reanalizar biblioteca") vía `QProcess`, que
    imprime líneas `PROGRESO hechos total`/`RESULTADO {json}` a
    stdout — `gui/ventana_configuracion.py:_leer_progreso_reanalisis()`
    las parsea en vivo (bufferizando por si `readyReadStandardOutput`
    entrega los datos partidos a mitad de línea) y actualiza una
    barra de progreso GRÁFICA real (`DialogoPreloadBiblioteca`,
    generalizado en la ronda 77 para la migración de duración al
    arrancar — reusado tal cual, sin duplicar el widget). El botón
    queda deshabilitado mientras corre; al terminar
    (`_al_terminar_reanalisis()`) se reactiva, se refresca el árbol
    del Explorador desde disco, y se muestra el MISMO desglose
    honesto de siempre (warning si hubo fallos reales, con el conteo
    de preservados; information si todo salió bien) — **con la app
    completamente RESPONSIVE durante todo el proceso**, a diferencia
    de antes. Guardado incremental cada 25 archivos (ya existía desde
    la ronda 87, se mantiene) — un Ctrl+C o un cierre a mitad de
    camino del proceso hijo pierde como mucho el último tramo, nunca
    todo el trabajo ya hecho.

    De paso, la importación MASIVA de archivos nuevos (`_importar_
    archivos_masivo()`, Ventana 3) — que ya tenía cursor de espera +
    `processEvents()` periódico desde la ronda 41 — ahora también
    muestra la MISMA barra de progreso gráfica (`DialogoPreloadBiblioteca`,
    "X / Y archivos") en vez de solo el cursor, actualizada en cada
    archivo procesado — pedido explícito de Santiago ("a medida que
    se incorporen nuevos archivos hacerlo con el programa, pero con
    un progreso, que me indique si se hacen o no"). Esta parte queda
    a propósito SINCRÓNICA (no un proceso aparte como el reanálisis
    completo) — es incremental, casi siempre un lote chico comparado
    con reanalizar TODA la biblioteca, y ya tenía el mismo tratamiento
    de "no threading, cursor + processEvents" que el resto de la app;
    lo que faltaba era el número visible, no la arquitectura.

    Sobre "me sale un ícono ahora en todos los archivos musicales" —
    investigado y explicado a Santiago: NO es un bug nuevo de esta
    ronda, es la CONSECUENCIA esperada de haber corrido un reanálisis
    con el motor roto (antes del fix de `audioop-lts`, ronda 88) sobre
    archivos que nunca habían pasado por el análisis de esta app
    (importados por otro medio) — el fix de "preservar marcas buenas"
    de la ronda 87 evita DESTRUIR marcas que ya eran buenas, pero no
    puede resucitar marcas que nunca llegaron a calcularse. Con
    `audioop-lts` instalado y el reanálisis ahora sin trabar la app,
    correrlo de nuevo debería resolver los íconos de una.

    **b) Ventana 1: "el sistema debe ir variando los ítem aleatorios
    entre bloques de hora... repite el mismo en el bloque de las 0 y
    todos los demás"**: se auditó a fondo TODA la cadena de
    persistencia y resolución de un ítem Aleatorio (`_resolver_item_
    aleatorio`, `rutas_recientes_en_historial`, `_guardar_estado_
    ahora`/`_restaurar_desde_disco`, `cargar_bloques`) sin encontrar
    ningún bug de "aplanado" (los ítems Aleatorio SIEMPRE se guardan
    y cargan como placeholders de categoría, nunca como un archivo
    fijo — la hipótesis propia de Santiago, "quedan guardados los item
    aleatorios para siempre", queda descartada por el código) — el
    mecanismo de no-repetir vía historial persistente, matemáticamente,
    ya daba round-robin correcto item a item. Aun así, se implementaron
    los dos pedidos explícitos, y ADEMÁS se reforzó el no-repetir con
    una garantía DURA e independiente de cualquier timing:
    - **Insertar N ítems Aleatorio de una** (pedido a, "2 o 3 o 4 o
      5"): `DialogoInsertarItemAleatorio` (Programador) ganó un
      `QSpinBox` "Cantidad de ítems a insertar" (1-20, default 1) —
      `VentanaProgramador._insertar_item_aleatorio()` inserta esa
      cantidad de nodos INDEPENDIENTES seguidos, uno después del otro.
      `DialogoItemMusicalizador` (tipo Aleatorio del Musicalizador
      Avanzado) ganó el mismo campo "Cantidad a agregar:" (oculto al
      EDITAR un ítem ya existente, solo tiene sentido al agregar) +
      `resultado_cantidad()` — `VentanaMusicalizador._añadir_item()`
      agrega esa cantidad de copias independientes (dicts distintos,
      nunca la misma referencia repetida). El Musicalizador YA tenía
      desde la ronda 31 la garantía de no repetir entre ítems
      Aleatorio de la MISMA pasada de generación (`rutas_a_evitar`) —
      no hizo falta tocar el motor ahí, solo la UI para no tener que
      clickear "＋ Añadir" varias veces a mano.
    - **Garantía DURA de no-repetir DENTRO del mismo bloque** (pedido
      b + el objetivo explícito: "no puede repetir la misma
      publicidad 2 veces en el mismo bloque, al menos que haya menos
      ítem en la categoría que la programada"): `GestorPublicidad`
      ganó `_rutas_usadas_aleatorio_en_bloque` (set en memoria) +
      `_bloque_para_no_repetir_aleatorio` (referencia al último
      bloque rastreado) — `_actualizar_bloque_para_no_repetir_aleatorio()`
      resetea el set apenas se detecta un bloque DISTINTO (comparado
      por identidad del `QTreeWidgetItem`, vía `item.parent()`), sin
      importar si el cruce fue por disparo automático de horario,
      avance continuo normal, o Play manual — un solo punto cubre los
      tres casos, mismo espíritu que `_marcar_siguiente_con_refill()`
      del Musicalizador (ronda 34c). `_resolver_item_aleatorio()`
      ahora UNE la exclusión de siempre (historial persistente) con
      este set nuevo antes de elegir — así, aunque por alguna razón el
      historial no reflejara a tiempo lo recién resuelto (nunca
      confiar en una sola capa, mismo criterio ya aplicado varias
      veces en este proyecto para bugs de timing), la garantía de "no
      repetir dentro del bloque" queda asegurada por un mecanismo
      propio, no solo por inferencia de timing. Mismo criterio de
      "nunca dejar hueco" de siempre: si la categoría tiene MENOS
      archivos que ítems Aleatorio programados en el bloque, al
      agotarse todos los distintos, `elegir_aleatorio_de_categoria()`
      ignora la exclusión (ya lo hacía) y recién ahí repite — nunca
      antes de agotar los demás, exactamente como pidió Santiago.

    Probado con `test_aleatorio_multiple_y_no_repetir_bloque.py`
    (nuevo, dedicado): el diálogo del Programador expone e inserta la
    cantidad pedida (5 nodos independientes, todos Aleatorio); el
    diálogo del Musicalizador expone `resultado_cantidad()` y agrega
    esa cantidad de copias independientes; un bloque con 4 ítems
    Aleatorio de una categoría de 4 archivos usa los 4 exactos, CERO
    repeticiones; un bloque con 5 ítems Aleatorio de una categoría de
    2 usa los 2 primeros sin repetir y recién el 3ro repite (nunca
    antes); cruzar a un bloque DISTINTO con la misma categoría de 1
    solo archivo no queda bloqueado por lo que sonó en el bloque
    anterior — + `test_reanalisis_async.py` (nuevo, dedicado: standalone
    CLI produce PROGRESO/RESULTADO parseable, `ejecutar_reanalisis()`
    preserva marcas buenas ante un fallo simulado, y la GUI real con un
    `QProcess` REAL corriendo `core/reanalizador_batch.py` de punta a
    punta — arranca deshabilitado, progresa, termina, refresca el
    Explorador, muestra el aviso final) + actualización de 2 tests
    preexistentes que asumían el reanálisis SINCRÓNICO viejo
    (`test_marcas_in_out.py`, con un archivo GENUINAMENTE roto en vez
    de mockear `analizar_audio()` en el proceso padre — el hijo no
    hereda ese monkeypatch; `test_item_aleatorio_v1.py`, `resultado()`
    del diálogo pasó de 2 a 3 elementos) + suite de regresión completa
    sin fallos nuevos (mismos 7 fallos preexistentes de siempre:
    `test_audio_only_y_buffer.py`, `test_confirmaciones.py`,
    `test_fade_in_declick_v1.py`, `test_log_git.py`,
    `test_ronda_ajustes_dinesat2.py`, `test_ronda_dinesat3.py`,
    `test_ventana3.py` — confirmado además que un fallo puntual de
    `test_volumen_robusto.py` visto en una corrida intermedia era
    flaky/no reproducible, ya documentado como tal desde la ronda 46,
    sin relación con este cambio: pasó limpio en 3 corridas aisladas
    siguientes) + smoke test de arranque limpio. **Sigue sin poder
    probarse con audio/VLC real ni con la biblioteca real de 9800
    elementos de Santiago**: falta que confirme (1) que reanalizar la
    biblioteca completa ya NO traba el programa y la barra de progreso
    se ve avanzar en vivo, (2) que tras instalar `audioop-lts` y
    reanalizar de nuevo, los íconos de aviso desaparecen de los
    archivos musicales que sí tenían audio válido, (3) que insertar
    varios ítems Aleatorio de una en el Programador/Musicalizador
    ahorra el trabajo de repetir el botón a mano, y (4) sobre todo,
    que con su biblioteca y categorías reales, los bloques horarios
    ahora se sienten realmente variados entre sí y dentro de cada uno
    — si TODAVÍA nota repetición constante después de esta ronda, el
    diagnóstico más probable pasaría a ser categorías demasiado chicas
    (pocos archivos de Publicidad/Separadores por categoría), no un
    bug de código.
90. ~~El recorte de silencio cortaba contenido REAL — umbral demasiado
    estricto + cero margen en Ventana 1~~ — Santiago probó la ronda
    del reanálisis async y reportó daño real: "los HTH de hora les
    recortó el comienzo, las publicidades no terminan, el fade de
    configuraciones para esta ventana no funciona, lo desactivé y sin
    embargo tampoco deja terminar los ítem... incluso hay canciones
    que las finaliza antes". Diagnóstico leyendo su configuración real
    (`config_general.json`): `umbral_silencio_dbfs: -40.0` +
    `tolerancia_silencio_v1_segundos: 0.0` (sin ningún margen de
    seguridad para Publicidad/Separador/HTH, "corte estricto" pedido
    en una ronda muy anterior).

    **Causa de fondo**: -40dBFS es un umbral bastante estricto — una
    consonante suave al empezar a hablar, una respiración, o la cola
    de reverberación/decay de un fundido musical pueden estar por
    debajo de -40dBFS y aun así ser parte real y audible del
    contenido. `detect_leading_silence` (que NUNCA mira el medio del
    tema, solo escanea desde cada extremo hacia adentro) clasificaba
    esas partes quietas como "silencio" y las recortaba — y con CERO
    margen de seguridad en Ventana 1 (`tolerancia_silencio_v1_segundos
    = 0.0`), el corte quedaba pegado EXACTO al punto que el detector
    marcaba, sin ningún colchón ante esa imprecisión: el corte caía
    ADENTRO del contenido audible real, no en el silencio de verdad.
    Esto explica los tres síntomas de una: el comienzo real de un HTH
    ("es la hora...") quedaba mordido, la cola real de una publicidad
    quedaba cortada antes de terminar de decir la última palabra, y
    (con la tolerancia general de Música de 2s en la entrada pero el
    tope duro `MARGEN_MAXIMO_SALIDA_MS` de solo 300ms en la salida,
    ver ronda 75) una cola de fundido musical más lenta que ese margen
    quedaba parcialmente cortada.

    **Sobre "desactivé el fade y tampoco deja terminar los ítems" —
    aclarado, no era un bug del fade**: `duracion_fade_out_v1_ms`
    (Configuración → Fade/Transiciones → Ventana 1) solo controla la
    RAMPA de volumen aplicada HASTA `punto_fin_ms` — nunca decide
    DÓNDE cae ese punto de corte. Con el punto de corte ya mordiendo
    contenido real (el bug de arriba), apagar el fade no cambia nada:
    el audio ya viene truncado ANTES de que cualquier fade tenga
    oportunidad de sonar. El fade era inocente, la causa real era el
    umbral+tolerancia del análisis.

    **Corregido, en `config/settings.py` (`CONFIG_POR_DEFECTO`) y
    `core/analizador_audio.py`**:
    - `umbral_silencio_dbfs`: `-40.0` → `-50.0` (más permisivo — hace
      falta un silencio más profundo/real para que el detector lo
      cuente; sigue sin tocar NUNCA el medio del tema, ver el propio
      docstring del módulo).
    - `tolerancia_silencio_v1_segundos`: `0.0` → `0.15` (150ms de
      colchón de seguridad para Publicidad/Separador/HTH — sigue
      sonando "bien pegado", muy por debajo de los 2s de Música, pero
      ya no queda pegado EXACTO al límite del detector sin ningún
      margen).
    - `MARGEN_MAXIMO_SALIDA_MS` (constante, no configurable desde la
      UI): `300` → `400` — colchón extra en la salida de Música, para
      no cortar una cola de fundido/decay que siga siendo audible un
      poco más allá de donde el detector marca "silencio".
    - `UMBRAL_SILENCIO_DBFS_DEFECTO` (fallback interno de
      `analizar_audio()` si se lo llama sin pasar el umbral): mismo
      cambio, `-40.0` → `-50.0`, por consistencia.

    **Importante — esto NO es retroactivo para su instalación real**:
    estos son los defaults de FÁBRICA (`CONFIG_POR_DEFECTO`), usados
    solo en una instalación NUEVA o si una clave falta del JSON — la
    `config_general.json` de Santiago YA tiene valores EXPLÍCITOS
    guardados (`-40.0`/`0.0`), que sobreviven sin tocarse a pesar de
    este cambio de código. Se le indicó en el chat, con los nombres
    EXACTOS de los campos, que tiene que ir a **Configuración →
    Reproducción y Automatización** y cambiar a mano: "Umbral de
    silencio (dBFS)" de -40 a -50, y "Tolerancia de silencio Ventana 1
    (segundos)" de 0.0 a 0.15 — y recién DESPUÉS de guardar, correr
    **Configuración → Diagnóstico → "🔄 Reanalizar biblioteca"** (ya
    async desde la ronda anterior, con barra de progreso — no traba
    la app) para que los ~9800 archivos ya importados se recalculen
    con los valores corregidos. Un archivo importado DE ACÁ EN MÁS
    (tras guardar la config nueva) ya usa los valores corregidos de
    forma automática, sin acción manual.

    Probado con un smoke test dedicado (audio sintético con pydub
    real — un HTH con un "attack" suave a -35dBFS antes del cuerpo, y
    una publicidad con una "cola" suave a -35dBFS antes del silencio
    real): confirmado que con la config VIEJA (-40/0.0) el corte queda
    pegado exacto al límite sin margen, y con la config NUEVA
    (-50/0.15) el attack y la cola quedan conservados con margen de
    sobra — + `py_compile` limpio + smoke test de arranque sin
    traceback. **No se pudo correr la suite de regresión de scripts
    de rondas anteriores** — ninguno de esos `test_*.py` está commiteado
    al repo (viven como scripts sueltos de sesiones de chat anteriores,
    nunca agregados a git); no hay ningún archivo `test_*.py` rastreado
    en este repositorio. **Sigue sin poder confirmarse con su
    biblioteca/hardware real**: falta que Santiago cambie los dos
    valores en Configuración, reanalice la biblioteca completa, y
    confirme que los HTH ya no pierden el comienzo, que las
    publicidades terminan de decir la última palabra, y que las
    canciones ya no cortan antes de su final real. Si con -50dBFS
    algo TODAVÍA se corta de más (umbral demasiado permisivo puede
    dejar ruido de fondo/hiss sin recortar en vez del problema
    contrario), el próximo ajuste sería subir el umbral más cerca de
    0 en pasos chicos (ej. -45) en vez de volver a -40.
91. ~~Bug real: reanálisis de biblioteca crasheaba a mitad de camino
    con `FileNotFoundError` en `biblioteca.json.tmp`~~ — Santiago
    corrió "🔄 Reanalizar biblioteca" (ronda 89/90) y reportó el
    traceback real: `os.replace(archivo_temporal, ruta)` fallaba con
    "No such file or directory: biblioteca.json.tmp -> biblioteca.json"
    a mitad del recorrido recursivo de categorías — el reanálisis
    seguía y terminaba igual (probablemente porque volvió a apretar el
    botón y esa segunda vuelta no pisó la misma ventana de carrera),
    pero la excepción sin atrapar quedaba visible como un error feo.

    **Causa de fondo — carrera real entre DOS procesos escribiendo el
    mismo archivo**: `_guardar_json_atomico()` (`config/settings.py`)
    usaba un nombre de archivo temporal FIJO (`"{ruta}.tmp"`) — hasta
    la ronda 89, biblioteca.json SIEMPRE lo escribía un único proceso
    (la app principal), así que ese nombre fijo nunca chocaba con
    nadie. Desde que el reanálisis corre en un PROCESO APARTE (ronda
    89, justamente para que "el programa siga respondiendo mientras
    tanto"), es totalmente esperable que Santiago siga navegando
    Ventana 3 (o cualquier otra acción que dispare
    `_guardar_biblioteca_debounced()`) MIENTRAS el proceso de
    reanálisis también está guardando cada 25 archivos — dos
    escrituras casi simultáneas al MISMO archivo temporal: si un
    proceso llega a `os.replace()` justo antes que el otro, el
    segundo se encuentra con que su propio `.tmp` "ya no está" (el
    primero se lo llevó al renombrarlo) y explota con
    `FileNotFoundError` — matando de raíz el reanálisis completo en
    curso (con `guardar_biblioteca()` llamada sin ningún `try/except`
    alrededor, la excepción se propagaba hasta `main()` y tiraba abajo
    todo el proceso, con exit code 1).

    **Corregido en dos capas** (nunca confiar en una sola, mismo
    criterio de siempre en este proyecto):
    - `_guardar_json_atomico()`: el archivo temporal ahora tiene un
      nombre ÚNICO por escritura (`tempfile.mkstemp()`, mismo
      directorio -> mismo filesystem, `os.replace()` sigue siendo
      atómico) — dos escrituras concurrentes de CUALQUIER origen ya
      nunca pueden pisarse el `.tmp` la una a la otra. Reproducido y
      confirmado con un smoke test real (8 procesos escribiendo el
      mismo archivo 30 veces cada uno, en simultáneo, con
      `multiprocessing`): con el código VIEJO, 7 de 8 procesos
      fallaban con el MISMO `FileNotFoundError`; con el fix, los 8
      terminan limpio.
    - `core/reanalizador_batch.py`: los guardados periódicos (cada 25
      archivos) y el final ahora pasan por
      `_guardar_sin_frenar_el_lote()` — si el guardado falla por
      CUALQUIER motivo (una carrera residual, disco lleno, lo que
      sea), se registra en el log y el reanálisis SIGUE (el próximo
      checkpoint vuelve a intentar guardar) en vez de perder en
      memoria el trabajo de miles de archivos ya procesados por un
      solo guardado fallido.

    Probado con `py_compile` limpio + el smoke test de concurrencia
    real descripto arriba (confirmado que reproduce el bug EXACTO
    contra el código viejo vía `git stash`, y que el fix lo elimina
    del todo) + smoke test de arranque de la app sin traceback. **No
    se pudo correr la suite de regresión de scripts de rondas
    anteriores** (ninguno está commiteado al repo, ver ronda 90).
    Falta que Santiago corra "Reanalizar biblioteca" de nuevo,
    idealmente mientras sigue usando Ventana 3 en paralelo (el
    escenario que disparó el bug), y confirme que ya no aparece
    ningún error a mitad de camino.
92. ~~Aplicar/Revertir análisis de silencio por ítem o lote (menú
    contextual) + botón global acotado a Música~~ — Santiago confirmó
    la dirección propuesta ("Sigamos así") y pidió el mecanismo
    completo: control manual y granular sobre CUÁLES archivos llevan
    el recorte de silencio/nivelado y cuáles no, más el ahorro de
    tiempo de acotar el reanálisis masivo solo a Música.

    - **Menú contextual de Ventana 3, dos acciones nuevas**
      (`gui/ventana_explorador.py`): "🔈 Aplicar análisis de
      silencio..." y "↩ Revertir análisis de silencio...", ambas
      habilitadas con 1 o más ítems seleccionados (mismo criterio que
      Exportar/Editar información/Vigencia) — el texto muestra la
      cantidad cuando hay selección múltiple.
      - **Aplicar** (`_aplicar_analisis_silencio`): corre
        `analizar_audio()` sobre cada seleccionado con los valores de
        tolerancia/umbral que están guardados AHORA MISMO en
        Configuración (`cargar_configuracion()` + `tolerancia_silencio_para_genero()`,
        exactamente igual que el motor masivo) — funciona con
        CUALQUIER género, a diferencia del botón global. Mismo
        criterio "nunca destruir una marca buena con un fallo nuevo"
        de `core/reanalizador_batch.py` (ronda 87): un archivo que ya
        tenía marcas reales y esta vuelta falla queda intacto. Un
        archivo sin ruta válida en disco se saltea y se cuenta aparte
        en el resumen final.
      - **Revertir** (`_revertir_analisis_silencio`): deja el/los
        ítems en las mismas marcas NEUTRAS de un archivo recién
        importado sin analizar (`punto_inicio_ms=0`, `punto_fin_ms=None`,
        `ganancia_db=0.0`, `analizado=False`) — el audio real nunca se
        toca (enfoque no destructivo de siempre), es 100% reversible
        aplicando el análisis de nuevo cuando se quiera.
      - Las dos refrescan `_actualizar_marcas_item()` en cada ítem
        tocado (el ícono ⚠ de "sin marcas", acotado a Música desde la
        ronda 87, aparece/desaparece al instante) y persisten con
        `_guardar_biblioteca_debounced()`.
    - **Botón global de Configuración acotado a Música** (pedido
      explícito: "que se aplica sólo a los que estén catalogados como
      música. Ahorrá tiempo e ítem a analizar"): `core/reanalizador_batch.py`
      (`_contar_elegibles()` y `_procesar_categoria()`) ahora
      SALTEAN cualquier registro cuyo `genero != "Musica"` — Publicidad/
      Separador/Pisador/Artística/HTH ya NUNCA pasan por el reanálisis
      MASIVO, tienen su propia vía manual (el menú contextual de
      arriba). Botón renombrado a "🔄 Reanalizar biblioteca — solo
      Música (recorte de silencio)", con el texto de confirmación y el
      diálogo de progreso actualizados para que quede explícito el
      alcance nuevo — evita que Santiago (o cualquiera) asuma que ese
      botón sigue tocando publicidades/HTH como antes.

    Probado con un smoke test dedicado (biblioteca aislada en un
    directorio temporal, 1 tema de Música + 2 publicidades con audio
    sintético real vía pydub): Aplicar en selección múltiple sobre
    las 2 publicidades deja las dos con marcas reales; el reanálisis
    GLOBAL sobre la misma biblioteca (con las 3 vueltas a marcas
    neutras a propósito) procesa exactamente 1 archivo (la Música) y
    NUNCA toca las publicidades; Revertir sobre la Música ya analizada
    la vuelve a marcas neutras; el menú contextual expone las 2
    acciones nuevas; los cambios quedan persistidos de verdad en
    `biblioteca.json` (releído de disco después de `flush_biblioteca_pendiente()`)
    — + `py_compile` limpio + smoke test de arranque de la app sin
    traceback. **No se pudo correr la suite de regresión de scripts de
    rondas anteriores** (ninguno está commiteado al repo, ver ronda
    90). Falta que Santiago confirme en su instalación real que el
    botón global ahora es más rápido (solo recorre Música), y que
    puede aplicar/revertir el análisis a mano sobre HTH/Publicidad/
    Separadores puntuales desde el menú contextual, tanto de a uno
    como en lote.
93. ~~Bug real de fondo encontrado en el log real que Santiago subió a
    `main`: 61 archivos de su biblioteca (105 líneas de error, algunos
    reintentados más de una vez) fallaban SIEMPRE el análisis de
    silencio con "Decoding failed. ffmpeg returned error code: 8" /
    "Unknown encoder 'pcm_s4le'"~~ — pedido: "Revisá el log que acabo
    de subir a Main." Investigado leyendo el propio código instalado
    de pydub (`pydub/audio_segment.py`), no adivinado: los 61 archivos
    (todos en `Storage 1/Audio High Resolution/000/`) están
    codificados en **IMA-ADPCM** (`Stream #0:0: Audio: adpcm_ima_wav`)
    — un formato WAV comprimido con pérdida, mitad del tamaño de un
    PCM normal. Al convertir CUALQUIER archivo, pydub le pregunta a
    `ffprobe` el `bits_per_sample` del stream y arma el encoder de
    SALIDA como `"pcm_s%dle" % bits_per_sample` — para IMA-ADPCM,
    ffprobe reporta **4 bits/muestra** (el ancho de la unidad
    COMPRIMIDA, no el PCM real ya decodificado), así que pydub termina
    pidiéndole a ffmpeg el encoder `pcm_s4le`, que **no existe** (ffmpeg
    no tiene PCM de 4 bits) — la conversión revienta SIEMPRE para
    cualquier archivo con este códec, sin importar el contenido ni el
    umbral/tolerancia configurados. Reproducido en el sandbox
    generando un WAV real y recodificándolo a `adpcm_ima_wav` con
    ffmpeg — mismo error exacto, carácter por carácter, que el log de
    Santiago.

    **Corregido con un fallback real, no un ajuste de configuración**
    (`core/analizador_audio.py`, `_cargar_audio()`, nuevo): si
    `AudioSegment.from_file(ruta)` falla, se decodifica el archivo a
    PCM de 16 bits con **ffmpeg DIRECTO** (`subprocess` propio, `-acodec
    pcm_s16le -f wav`, sin pasar por el auto-detect roto de pydub) a un
    WAV temporal, y recién ahí se lo entrega a pydub — el archivo
    original en la biblioteca de Santiago NUNCA se toca (mismo enfoque
    no destructivo de siempre). Si ffmpeg no está en el PATH, o la
    conversión manual también falla, se relanza el error ORIGINAL (no
    uno nuevo del segundo intento, más confuso) — así un archivo
    genuinamente corrupto/inexistente sigue degradando limpio a marcas
    neutras, exactamente como antes. Esto arregla de raíz CUALQUIER WAV
    ADPCM que Santiago tenga hoy o agregue en el futuro — no hace
    falta que él convierta los 61 archivos a mano.

    Sobre "quiero un verdadero aleatorio, sin repeticiones
    innecesarias": Santiago avisó que sigue probando el ítem Aleatorio
    (reforzado en la ronda 89 con no-repetir DURO dentro del mismo
    bloque + inserción de N de una) — sin un reporte concreto todavía,
    no se tocó nada de ese motor en esta ronda; queda a la espera de
    que aparezca un caso puntual de repetición para diagnosticar contra
    datos reales, mismo criterio de siempre en este proyecto (nunca
    tocar a ciegas un mecanismo que ya se auditó y no mostró bugs).

    Probado reproduciendo el bug EXACTO con un WAV sintético
    recodificado a IMA-ADPCM (`ffmpeg -acodec adpcm_ima_wav`):
    confirmado que fallaba idéntico al log real de Santiago antes del
    fix, y que con el fix aplicado `analizar_audio()` devuelve
    `analizado=True` con la duración y ganancia correctas — + un WAV
    PCM normal (camino sin cambios) y una ruta genuinamente inexistente
    (sigue degradando limpio, sin relanzar una excepción distinta) +
    `py_compile` de todo el proyecto + smoke test de arranque sin
    traceback. **No se pudo correr la suite de regresión de scripts de
    rondas anteriores** (ninguno está commiteado al repo, ver ronda
    90). Falta que Santiago corra "Reanalizar biblioteca — solo
    Música" (o "🔈 Aplicar análisis de silencio..." sobre esos 61
    puntuales si no son de género Música) y confirme que ya no aparece
    ningún error de "Decoding failed"/"pcm_s4le" para esos archivos.
94. ~~Nivelado de volumen automático por LOUDNESS real (LUFS/EBU R128),
    reemplaza el promedio dBFS simple, con techo de seguridad de pico
    y configuración manual~~ — pedido explícito: "en mhWaveEdit
    normalizo audio a mano, uno por uno, ¿se puede automático al
    importar/analizar? Dame opciones efectivas." Se propusieron 3
    opciones (mejorar el cálculo ya existente sin tocar archivos,
    sumar solo detección de pico, o reescribir el archivo físico como
    hace mhWaveEdit) — Santiago eligió la primera ("vamos con lo que
    proponés como opción 1... o dejame la configuración para
    establecerlo yo manualmente").

    **Motor** (`core/analizador_audio.py`, `_calcular_ganancia_db()`,
    nuevo): el nivelado que YA existía desde el principio del proyecto
    (`ganancia_db`, aplicado como ajuste de volumen al reproducir,
    nunca toca el archivo) usaba un simple promedio de amplitud
    (dBFS) — bueno para no tener un tema mucho más fuerte que otro en
    promedio, pero sin relación real con la sonoridad PERCIBIDA (un
    tema comprimido y uno con mucho rango dinámico pueden compartir
    el mismo dBFS promedio y sonar muy distinto), y sin ninguna
    protección contra saturación si el nivelado empuja fuerte un tema
    con picos altos. Reemplazado por:
    1. **Loudness real (LUFS, EBU R128)** vía `pyloudnorm` — mide
       sonoridad "gateada" (ignora tramos silenciosos/irrelevantes,
       pondera por percepción humana), el mismo estándar que usa la
       radiodifusión profesional. Conversión de samples de pydub a
       float `[-1, 1]` con el patrón estándar de la comunidad
       (`get_array_of_samples()` / `2**(8*sample_width-1)` — asume PCM
       entero con signo, siempre el caso acá ya que MP3/ADPCM/etc.
       siempre terminan decodificados a `pcm_s16le` antes de llegar,
       ver `_cargar_audio()`).
    2. **Fallback automático al cálculo VIEJO** (promedio dBFS) si
       `pyloudnorm`/`numpy` no están instalados, O si el clip es
       demasiado corto para una medición EBU R128 confiable (~400ms
       mínimo — caso típico: los clips de voz del Comando HTH) — nunca
       deja un archivo sin ganancia calculada por esto, degradación
       silenciosa y prolija, mismo criterio de siempre en este
       proyecto ante dependencias faltantes.
    3. **Techo de seguridad de PICO** (nuevo, cierra un hueco real que
       ni mhWaveEdit ni el cálculo viejo evitaban del todo): si la
       ganancia calculada (por cualquiera de los dos métodos)
       empujaría el pico del audio por encima de un techo configurado,
       se RECORTA la ganancia (nunca se sube) para que el pico
       resultante quede justo en el techo — un tema con promedio bajo
       pero algún pico alto no termina saturando al aplicarle un
       boost fuerte.
    Probado con audio sintético real (no simulado): tono flojo pide
    boost sin disparar el techo, tono ya fuerte pide atenuación (sin
    riesgo de saturar), clip <400ms cae al fallback dBFS con log claro
    del motivo, silencio total no rompe nada (ganancia 0), y un caso
    de boost fuerte sobre un clip con pico alto confirma que el techo
    SÍ recorta la ganancia para no saturar. **Bug real encontrado y
    corregido en el camino**: `pyloudnorm` devuelve `numpy.float64`
    (subclase de `float`, no rompe el guardado JSON pero mostraba feo
    en el log/UI) — normalizado a `float` nativo de Python antes de
    devolver.

    **Configuración manual** (pedido explícito, segunda mitad del
    pedido): dos campos nuevos en Configuración → Reproducción y
    Automatización — "Nivelado de volumen — objetivo de sonoridad" (en
    LUFS, default -16.0, mismo valor que ya usaba el cálculo viejo en
    dBFS, para no dar un salto de volumen brusco en una instalación
    existente) y "Nivelado de volumen — techo de seguridad de pico"
    (en dBFS, default -1.0). Nuevo helper compartido
    `config/settings.py:parametros_nivelado(config)` (mismo espíritu
    que `tolerancia_silencio_para_genero()`, ya existente) reusado en
    los **5 puntos** que llaman `analizar_audio()` — alta individual,
    importación masiva, reemplazar/vincular archivo (`_aplicar_nuevo_archivo`,
    compartido por los dos), "Aplicar análisis de silencio" (menú
    contextual, ronda 92) y el reanálisis global en proceso aparte
    (`core/reanalizador_batch.py`) — así el valor configurado se
    respeta en TODOS los caminos de análisis, no solo uno. Mismo
    aviso de siempre en el tooltip: cambiar el valor **no es
    retroactivo**, hay que reanalizar/aplicar de nuevo para que
    alcance a lo ya importado.

    **Diagnóstico** (`verificar_motor_disponible()`, Configuración →
    Diagnóstico → "🩺 Verificar motor de análisis de audio"): ahora
    informa también si `pyloudnorm` está disponible (`loudnorm_ok`) —
    si falta, el mensaje aclara que el nivelado sigue funcionando con
    el cálculo anterior (dBFS) pero es menos preciso, con la
    instrucción exacta para sumarlo (`pip install pyloudnorm numpy`).

    `requirements.txt` ganó `pyloudnorm>=0.2.0` + `numpy>=1.24.0`
    (scipy llega transitivo, como dependencia de pyloudnorm para los
    filtros de ponderación K-weighting de EBU R128) — instalado y
    confirmado en el venv de este entorno para poder probar con audio
    real. Probado con `py_compile` de todo el proyecto + smoke test de
    arranque sin traceback + round-trip completo de la UI de
    Configuración (cargar/editar/guardar los 2 campos nuevos, incluida
    una config VIEJA sin esas claves que se autocompleta sola vía
    `_fusionar_con_defecto`) + `analizar_audio()` de punta a punta
    usando el valor recién guardado en Configuración. **No se pudo
    correr la suite de regresión de scripts de rondas anteriores**
    (ninguno está commiteado al repo, ver ronda 90). Falta que Santiago
    (1) instale `pyloudnorm`/`numpy` en su venv real
    (`pip install -r requirements.txt`) y confirme con "Verificar motor
    de análisis de audio" que queda activo, y (2) reanalice/aplique de
    nuevo el análisis sobre algunos temas y confirme si el nivelado se
    siente más parejo entre temas que antes — sin tener que repetir a
    mano lo que hacía en mhWaveEdit.
95. ~~Ronda grande: Copiar entre categorías, Renombrar categoría con
    corrección de referencias, bug de colores al reiniciar, duplicados
    acotado a categoría, rediseño del Aleatorio de Ventana 1 (rotación
    persistida por categoría), FMT visible en Emisión, ciclo FMT por
    tiempo~~ — siete pedidos en un solo mensaje, con el motor de
    Aleatorio de Ventana 1 como el más grande y explicado con un
    diseño propio punto por punto.

    **a) Copiar entre categorías al arrastrar** (pedido explícito:
    "preguntar si deseo arrastrar o crear una copia... el archivo
    original permanece en su lugar, solo crea una idéntica entrada de
    JSON en la categoría de destino"): `_on_archivos_soltados_en_categoria`
    ahora SIEMPRE pregunta Mover/Copiar/Cancelar (`gui/ventana_explorador.py:
    _preguntar_mover_o_copiar()`, ya no gateado por
    `confirmar_antes_de_eliminar` — es una decisión real, no una
    confirmación). Nueva `_copiar_archivos_a_categoria()`: el registro
    ORIGINAL nunca se toca, se crea una entrada nueva e independiente
    en destino con los MISMOS metadatos pero un CÓDIGO propio
    correlativo (mismo criterio que cualquier alta nueva) — el mismo
    archivo físico queda reproducible desde las dos categorías. Señal
    nueva `archivo_copiado` (mismo patrón que `archivo_movido`).

    **b) Renombrar categoría, con corrección de referencias** (pedido
    explícito: "el sistema debe corregir todas las integraciones de
    rutas... para que no se rompa la lectura del programador,
    aleatorio, musicalizador"): botón "✏ Renombrar" nuevo junto a
    "✕ Eliminar". Las categorías se referencian por FUERA de la
    biblioteca en 3 archivos (`playlist_publicidad.json`,
    `programacion.json`, `musicalizador.json`) guardando el CAMINO DE
    NOMBRES desde la raíz, nunca una referencia viva — renombrar un
    tramo de ese camino sin más dejaba esas referencias apuntando a
    algo que ya no existe (`buscar_categoria_por_ruta()` devuelve
    `None`, el ítem se saltea en silencio para siempre). Nueva
    `config/settings.py:corregir_referencias_categoria_renombrada()`
    (+ `ruta_con_prefijo_reemplazado()`, helper compartido): migra los
    3 archivos reemplazando el PREFIJO viejo por el nuevo,
    preservando cualquier subcategoría más profunda
    ("Publicidad > Vieja > Sub" → "Publicidad > Nueva > Sub"). Además,
    nueva `VentanaPublicidad.corregir_categoria_aleatorio_en_vivo()`
    corrige el árbol de bloques que Ventana 1 tiene YA CARGADO EN
    MEMORIA (el que de verdad conduce la emisión en ese instante),
    conectada vía la señal nueva `categoria_renombrada` →
    `MainWindow._on_categoria_renombrada()` — sin esperar a un
    reinicio. Alcance deliberado: no se intenta parchear en caliente
    un Programador/Musicalizador que estuviera abierto en ese momento
    (ambos releen de disco al reabrirse, ya corregido).

    **c) Bug real corregido — los colores de género no se aplicaban al
    reiniciar** ("vengo cambiando el color de Música y al reiniciar
    vuelve el verde"): `VentanaExplorador.__init__` arrancaba siempre
    con la paleta de FÁBRICA (`dict(GENERO_COLORES)`) — la paleta
    guardada en Configuración recién se leía cuando se llamaba
    `repintar_colores_genero()`, y eso SOLO pasaba si el operador
    abría y guardaba Configuración en esa misma sesión. Corregido
    leyendo la config guardada ya en la construcción.

    **d) "Buscar duplicados" (Ventana 3) acotado SIEMPRE a una
    categoría** (pedido explícito, consecuencia directa de (a): "como
    ahora generamos ítems de JSON duplicados [con Copiar], la opción
    de buscar duplicados se debe aplicar por categoría específica y
    no por toda la base"): sacada la opción "Toda la base de datos" —
    `_buscar_duplicados_avanzado()` va DIRECTO a elegir una categoría
    (`_preguntar_alcance_duplicados()` eliminado). El buscador SIMPLE
    de Configuración → Diagnóstico (criterios exactos, ronda 83) no se
    tocó — el pedido fue puntual sobre "el botón de la ventana 3".

    **e) Rediseño del Aleatorio de Ventana 1 — el más grande**
    (pedido explícito, con diagnóstico propio de Santiago: "estoy
    escuchando las mismas 2 publicidades en todos los bloques...
    ¿será porque armé el bloque de las 00 horas y copié y pegué?" +
    una especificación propia punto por punto de cómo debería
    funcionar "si no está aplicada"): el no-repetir de antes
    (`rutas_recientes_en_historial`, una ventana de RECENCIA derivada
    del log de reproducción) funciona bien para Ventana 2 (~9000
    archivos de música — **a propósito, NO SE TOCÓ**, pedido explícito
    "esa ventana la dejaría como está") pero con categorías chicas de
    Publicidad/Separadores/Artísticas usadas en TODOS los bloques
    horarios del día no garantizaba variedad real entre un bloque y el
    siguiente. Nuevo motor puro `core/rotacion_categoria.py` (mismo
    espíritu que `core/musicalizador.py`, explorador duck-typed) con
    una ROTACIÓN SECUENCIAL persistida por categoría —
    `config/data/rotacion_categorias.json` — implementando los 4
    puntos que pidió Santiago:
    - (a) los candidatos se re-evalúan siempre EN VIVO (más estricto
      todavía que "cada hora": nunca una foto vieja).
    - (b) una posición separada POR CATEGORÍA — nunca mezclada entre
      categorías distintas ni con Música.
    - (c) recorre los archivos de la categoría hasta agotarlos, recién
      ahí vuelve a empezar. Decisión propia no preguntada
      explícitamente (documentada en el docstring del módulo): el
      ORDEN de cada vuelta se baraja una vez al empezarla (no un orden
      fijo alfabético repetido idéntico para siempre) — concilia la
      letra del pedido ("del ítem 1 al final, vuelve a empezar al
      agotarlos" — sí hay un orden fijo que se recorre completo antes
      de repetir) con que la función siga sintiéndose "aleatoria"
      (nombre de la función en toda la app).
    - (d) la posición avanza SOLO cuando el archivo elegido arranca a
      sonar DE VERDAD (nunca al quedar solo armado/en cola) — y
      sobrevive reinicios de la app y cambios de día calendario (nunca
      se resetea sola, solo al agotar la vuelta completa).
    `core/playlist_manager.py:_resolver_item_aleatorio()` reemplaza el
    llamado a `elegir_aleatorio_de_categoria()`/`rutas_recientes_en_historial`
    por `elegir_por_rotacion()` (peek puro, sin escribir a disco); el
    avance real (`marcar_reproducido_por_rotacion()`, sí persiste) se
    llama desde `_reproducir_item_aleatorio()` en el ÚNICO punto donde
    el ítem Aleatorio arranca a sonar de verdad (mismo lugar donde ya
    se llamaba `registrar_reproduccion()`). El guard de "no repetir
    DENTRO del mismo bloque" de la ronda 89
    (`_rutas_usadas_aleatorio_en_bloque`) se CONSERVÓ como segunda capa
    de seguridad sobre la misma rotación (mismo criterio de siempre:
    "nunca confiar en una sola capa de protección"), pasado ahora como
    `excluir_rutas` a `elegir_por_rotacion()`. El ítem Aleatorio del
    Auxiliar (menú contextual "🎲 Agregar ítem aleatorio...", ronda 42)
    es una función DISTINTA y no se tocó — sigue usando
    `elegir_aleatorio_de_categoria()`/historial, a propósito (es una
    inserción manual puntual del operador, no el ciclo automático de
    bloques horarios que motivó este rediseño).

    **f) FMT visible en el título de Emisión** (pedido explícito:
    "EMISIÓN - LATINO, no hace falta que salga FMT escrito"): nuevo
    `PanelReproductor.establecer_sufijo_titulo()` (agrega/saca un
    sufijo al `QGroupBox`, guardado como `self._grupo` — antes era una
    variable local, no sobrevivía a `_construir_ui()`). Nuevo callback
    `GestorPlaylist.al_cambiar_formato_activo` (avisado desde
    `iniciar_musicalizador()`/`detener_musicalizador()`), conectado en
    `MainWindow._inicializar_motores_audio()` a
    `VentanaEmision.establecer_sufijo_titulo()` — con una sincronización
    inicial explícita justo después de conectar (cubre el caso de una
    sesión restaurada con un FMT ya activo desde `_restaurar_desde_disco()`,
    que corre ANTES de que el callback exista).

    **g) Menú contextual en Emisión — agregar X minutos de un FMT sin
    borrar lo cargado** (pedido explícito: "como si hubiera pasado por
    el comando FMT de la ventana 1... sin eliminar lo que ya esté
    cargado"): nuevo ítem "🎵 Agregar ciclo FMT por tiempo..." en el
    menú contextual de Emisión (`PanelReproductor` ganó
    `permitir_ciclo_fmt: bool`, exclusivo de Ventana 2 — al revés del
    flag ya existente `permitir_agregar_item`, exclusivo del
    Auxiliar), abre `gui/dialogo_ciclo_fmt_por_tiempo.py` (formato +
    minutos, mismo patrón de "elegir de una lista ya creada" que
    `dialogo_insertar_comando_fmt.py`). Nuevo
    `GestorPlaylist.insertar_ciclo_fmt_por_tiempo(nombre_formato,
    minutos)`: a diferencia de `iniciar_musicalizador()` (que SIEMPRE
    limpia antes de generar), este AGREGA al final — llama a
    `generar_serie()` en bucle (sumando la duración real de cada ítem,
    parseada con `core.buscador_duplicados.duracion_a_segundos()`)
    hasta cubrir los minutos pedidos, con un techo duro
    (`LIMITE_ITEMS_CICLO_POR_TIEMPO = 500`) para nunca colgarse aunque
    el formato tenga ítems sin duración conocida. "Como si hubiera
    pasado por el Comando FMT" (pedido explícito): deja el formato
    como ACTIVO para el refill continuo de ahí en más, y lo graba como
    "último FMT" — la única diferencia real con el Comando FMT
    verdadero es que este no limpia lo ya cargado.

    Probado de punta a punta con dos scripts dedicados: **motor puro**
    de rotación (primera vuelta pasa por todos sin repetir, la 4ta
    elección de una categoría de 3 arranca vuelta nueva sin quedarse
    sin candidatos, la posición sobrevive una relectura de disco
    simulando un reinicio, categoría de 2 alterna sin repetir,
    categoría inexistente/sin explorador degrada a `None`, un archivo
    agregado después se suma solo a la rotación sin esperar vuelta
    nueva) + **integración real** con `GestorPublicidad`/`VentanaPublicidad`
    (un bloque de 4 ítems Aleatorio sobre una categoría de 4 usa los 4
    sin repetir dentro de sí mismo; con una categoría de 8 y 2 ítems
    por bloque, dos bloques horarios consecutivos —simulando el "copié
    y pegué" real de Santiago— **NUNCA se pisan entre sí**, el caso
    exacto que reportó) + colores de género aplicados desde la
    construcción sin sesión previa + copiar entre categorías (original
    intacto, copia con código propio, mismo archivo físico) +
    `_buscar_duplicados_avanzado` sin la opción de "toda la base" +
    renombrar categoría corrigiendo los 3 archivos persistidos
    (incluida una subcategoría más profunda) Y el árbol de Ventana 1
    ya cargado en memoria + título de Emisión alternando
    "EMISIÓN"/"EMISIÓN - Latino" al activar/desactivar un FMT real +
    ciclo FMT por tiempo insertado sin borrar un ítem ya cargado a
    mano, con el formato quedando activo/"último FMT" — + `py_compile`
    de todo el proyecto + smoke test de arranque limpio sin traceback.
    **No se pudo correr la suite de regresión de scripts de rondas
    anteriores** (ninguno está commiteado al repo, ver ronda 90).
    **Sigue sin poder probarse con audio/VLC real ni con la biblioteca
    real de Santiago**: falta que confirme (1) que Copiar entre
    categorías funciona como espera al arrastrar, (2) que Renombrar
    categoría no rompe un bloque/formato ya armado, (3) que los
    colores elegidos en Apariencia ahora sobreviven un reinicio real,
    (4) que Buscar duplicados pidiendo siempre una categoría no
    resulta incómodo, (5) — el más importante — que con SU biblioteca
    real, dos bloques horarios consecutivos (sobre todo los que armó
    copiando y pegando) ya no repiten las mismas publicidades/
    separadores, y que la variedad se sienta real a lo largo de todo
    un día, (6) que el título de Emisión muestre el FMT correcto en
    uso, y (7) que insertar un ciclo FMT por tiempo desde Emisión
    calcule una cantidad razonable de ítems para el tiempo pedido.
96. ~~Bug real: el HTH repetía "en punto en punto" (finalizo_item
    duplicado) + Ventana 3: jerarquía visual de 5 niveles + árbol ya
    no arranca todo expandido~~ — dos pedidos: "¿Por qué hay veces que
    la hora, cuando va al bloque horario, repite la hora en la parte
    final? Por ejemplo dice: 'es la hora veintitres, en punto en
    punto'... investigá si pasa por un error de carga, del buffer" +
    "en la ventana de Categorías suelo tener hasta 5 niveles... ¿qué
    podríamos implementar para otorgar una mejor e intuitiva
    visibilidad? colores, negrita, líneas... también sacar que todo el
    árbol se vea expandido, es molesto ver todo".

    **a) Bug real de fondo — `finalizo_item` (MotorAudio) podía
    emitirse DOS VECES para el mismo fin de reproducción**:
    `core/audio_engine.py` tiene DOS orígenes independientes que
    detectan "esta reproducción terminó" y cada uno emitía
    `finalizo_item` por su cuenta — (1) el tick de posición
    `_emitir_posicion()` (QTimer, hilo principal, conexión DIRECTA),
    que corta apenas `actual_ms >= punto_fin_ms` (el punto de recorte
    de silencio calculado por `core/analizador_audio.py`); y (2) el
    evento NATIVO de libVLC `MediaPlayerEndReached`
    (`_on_fin_reproduccion`, disparado desde un hilo INTERNO de
    libVLC — la entrega al slot del hilo principal queda ENCOLADA por
    Qt, así que puede procesarse recién más tarde, incluso después de
    que la primera detección ya arrancó el clip/ítem SIGUIENTE). Para
    un clip de duración normal esto casi nunca se nota (las dos
    detecciones caen separadas en el tiempo), pero para un clip CORTO
    con margen de silencio casi nulo — exactamente el caso de los
    clips de voz del Comando HTH, género de "corte estricto"
    (`tolerancia_silencio_v1_segundos`, cerca de 0) — ambas
    detecciones caen dentro de la misma ventana muy angosta, y las DOS
    emisiones de `finalizo_item` le llegan a
    `GestorPublicidad._on_fin_de_item()` para lo que en la práctica es
    UN SOLO fin de clip. Con la cola del Comando HTH ya en su último
    elemento (ej. "MINUTOS 00" — "en punto"), esa segunda emisión
    tardía volvía a evaluar "cola vacía" y disparaba otra vuelta de
    avance sobre el mismo estado, sonando como si el último clip se
    repitiera — "en punto en punto". Corregido con un guard de UNA
    SOLA VEZ por reproducción (`MotorAudio._fin_ya_emitido`,
    `_emitir_fin_una_vez()`): cada `reproducir()` nuevo reabre la
    ventana (`_fin_ya_emitido = False`); la PRIMERA detección de fin
    (venga de donde venga) emite la señal y cierra la ventana —
    cualquier detección posterior para ESA MISMA reproducción se
    ignora en silencio. Reemplaza los dos `self.finalizo_item.emit()`
    directos (en `_emitir_posicion()` y en `_on_fin_reproduccion()`)
    por `self._emitir_fin_una_vez()`. Este bug no era exclusivo del
    HTH — cualquier ítem corto de cualquier ventana (Publicidad/
    Separador, corte estricto) podía sufrir el mismo doble-avance,
    solo que con un clip de voz de 1-2 segundos es mucho más
    perceptible y reproducible.

    **b) Ventana 3 — jerarquía visual de 5 niveles**: `gui/ventana_explorador.py:
    _aplicar_estilo_por_nivel()` (ya existía desde una ronda anterior,
    PR #2 — negrita+MAYÚSCULAS para el nivel 1, negrita para el nivel
    2, nada para el resto) se reescribió como gradiente de 5 escalones
    (`_ESTILOS_POR_NIVEL`, tabla de negrita/cursiva/mayúsculas/color/
    tamaño por nivel, calculado por profundidad REAL de ancestros, no
    solo "es raíz o no"): nivel 1 negrita+MAYÚSCULAS+color naranja
    acento (`#e67e22`, mismo tono ya usado para el nombre de emisora/
    contorno del botón AUTOMÁTICO); nivel 2 negrita, texto normal;
    nivel 3 peso normal, color apenas más tenue; nivel 4 cursiva, más
    tenue todavía (`#9a9a9a`, ya usado como color de texto secundario
    en el resto de la app); nivel 5 en adelante cursiva + el tono más
    tenue de todos, tamaño de fuente 1pt más chico — a partir de ahí
    se repite el estilo del nivel 5 (no sigue aclarándose para
    siempre). Cada color se eligió para NUNCA chocar con otro
    significado ya establecido en la app (el celeste de selección
    `#5dade2`, el rojo/verde de estado de Ventana 1/2, los colores por
    género de `tree_archivos` — este es un árbol DISTINTO,
    `tree_categorias`). El texto REAL del ítem (lo que se persiste en
    `biblioteca.json`) nunca se toca — es solo pintado. Complementado
    con un bloque QSS nuevo (`gui/styles.py`,
    `QTreeWidget#tree_categorias::branch`) que dibuja líneas de
    conexión sutiles entre niveles (pedido explícito "líneas") — a
    propósito no es el mecanismo PRINCIPAL (la fidelidad de esta
    técnica vía pseudo-estados QSS depende del motor de estilo activo
    y no se puede verificar sin un display real), el gradiente de
    fuente/color es la señal confiable y ya confirmada por test.

    **c) El árbol ya NO arranca todo expandido — recuerda
    exactamente lo que el operador dejó abierto**: `expandAll()` (se
    llamaba SIEMPRE después de cargar la biblioteca) se reemplazó por
    `_restaurar_expansion_categorias()`, que reconstruye el estado de
    expansión ítem por ítem a partir de un set persistido
    (`ui_state.ini`, vía `gui/estado_ui.guardar_valor`/
    `restaurar_valor` — mismo mecanismo genérico que ya usa el
    Programador para "recordar la última categoría navegada", con la
    misma normalización de la trampa de QSettings ya documentada: una
    lista guardada de un solo elemento vuelve como string suelto, no
    como lista de 1). Cada categoría identificada por su camino de
    nombres completo (`ruta_de_categoria()`, ya existente, unido con
    " > " — mismo criterio que `core/rotacion_categoria.py`).
    `tree_categorias.itemExpanded`/`itemCollapsed` (conectados DESPUÉS
    de la carga inicial, para que restaurar el estado guardado no
    dispare guardados redundantes) actualizan el set y lo persisten en
    cada click del operador — así lo que se deja abierto/cerrado
    sobrevive cerrar y reabrir la aplicación. Una biblioteca nueva, o
    la primera vez que corre esta versión (sin nada guardado todavía),
    arranca TOTALMENTE colapsada (solo las categorías raíz visibles) —
    exactamente el pedido ("sacar que todo el árbol se vea expandido...
    es molesto ver todo"). El "reveal" puntual que ya existía al crear
    una subcategoría nueva (`padre.setExpanded(True)`, para mostrar de
    inmediato lo recién creado) no se tocó — sigue funcionando igual,
    independiente de este mecanismo de recordar el estado general.

    Probado con dos scripts dedicados: el fix del motor de audio
    (llamar `_emitir_fin_una_vez()` 3 veces seguidas simulando la
    doble detección real produce UNA sola emisión de `finalizo_item`;
    un `reproducir()` nuevo reabre la ventana y el próximo fin real sí
    emite) + la jerarquía visual (gradiente de negrita/cursiva/
    mayúsculas/color confirmado en los 5 niveles de un árbol real de
    prueba — Publicidad > Clientes > Supermercados > Ofertas > Verano
    — árbol nuevo arranca colapsado sin estado guardado, expandir/
    colapsar a mano persiste y se saca correctamente, y recargar la
    biblioteca con un estado guardado previo restaura EXACTAMENTE eso,
    ni más ni menos) — + `py_compile` de los 3 archivos tocados +
    smoke test de arranque completo de la app sin traceback. **No se
    pudo correr la suite de regresión de scripts de rondas anteriores**
    (ninguno está commiteado al repo, ver ronda 90). **Sigue sin poder
    probarse con audio/VLC real ni con la biblioteca real de
    Santiago**: falta que confirme (1) que el Comando HTH de HORA ya
    no repite "en punto" (ni ningún otro clip corto) al final, y (2)
    que la nueva jerarquía visual (colores/negrita/cursiva + líneas) y
    el árbol ya no arrancando expandido de punta a punta se sienten
    más intuitivos para navegar sus 5 niveles reales de categorías.
97. ~~Confirmación de Renombrar categoría (Musicalizador/Programador) +
    bug real: el triángulo de expandir desapareció (efecto secundario
    de las "líneas" de la ronda anterior)~~ — dos pedidos: "confirmame
    que si cambio el nombre de una categoria principal, la
    programación del Musicalizador y del programador no se ven
    afectadas... que al cambio efectúe una búsqueda en esas listas y
    actualice la ruta" + "me gustó lo que hiciste en Categorías y los 5
    niveles diferenciados, solamente agregá siempre 'el triángulo'
    para ser más intuitivo de que se debe hacer doble clic para
    desplegar hacia abajo (si hay otro nivel más)".

    **a) Confirmado con un test dedicado, sin necesitar cambios de
    código — `corregir_referencias_categoria_renombrada()` (ronda 95)
    YA cubre los 3 archivos**: se armó un escenario real (un formato
    de Musicalizador con un ítem "aleatorio" apuntando a
    `["Publicidad", "Bebidas"]` + un ítem "específico" con Pisador
    apuntando a la misma categoría, y una programación guardada de
    "Lunes" con un ítem Aleatorio de Ventana 1 apuntando también ahí)
    y se renombró "Publicidad" → "Comerciales" — los 3 quedaron
    corregidos a `["Comerciales", "Bebidas"]` (conservando la
    subcategoría "Bebidas" intacta), confirmado releyendo
    `musicalizador.json` y `programacion.json` de disco. Un
    "renombre" sin cambio real (mismo nombre) no toca nada. La
    respuesta corta para Santiago: **sí, renombrar una categoría
    principal (o cualquier subcategoría) corrige sola las 3 listas por
    fuera de la biblioteca** — Ventana 1 (`playlist_publicidad.json`,
    además parcheado EN VIVO en el árbol que conduce el aire en ese
    instante, sin esperar a un reinicio), el Musicalizador (ítems
    "aleatorio" y el Pisador de cualquier ítem) y el Programador
    (`programacion.json`, día de semana o fecha específica). Única
    salvedad: si el Programador o el Musicalizador YA estaban
    abiertos en pantalla en el momento del renombre, esa ventana en
    particular no se auto-refresca (lee de disco recién al abrirse) —
    cerrarla y volver a abrirla ya muestra la ruta corregida; esto no
    aplica a Ventana 1, que sí se actualiza en caliente.

    **b) Bug real de fondo — el triángulo de expandir/colapsar quedó
    invisible, causado por la propia ronda anterior**: las "líneas de
    conexión" QSS agregadas para las categorías de 5 niveles
    (`QTreeWidget#tree_categorias::branch:has-siblings:...`) tienen un
    efecto secundario real y conocido de Qt: en cuanto un stylesheet
    toca CUALQUIER pseudo-estado de `::branch`, el motor de estilo deja
    de dibujar el triángulo NATIVO de expandir/colapsar para los
    estados que ese QSS no cubre explícitamente — y esa ronda nunca
    cubrió `:closed`/`:open` (los estados que llevan el triángulo).
    Resultado: el triángulo quedaba invisible en la práctica, justo la
    señal que Santiago pidió reforzar. Corregido sacando el override de
    `::branch` por completo (`gui/styles.py`) — `tree_categorias`
    vuelve a usar el triángulo NATIVO del estilo activo (Fusion), que
    siempre se dibuja solo en cualquier ítem con hijos, sin depender de
    ningún asset propio — más `self.tree_categorias.setRootIsDecorated(True)`
    explícito en `gui/ventana_explorador.py` (ya era el default de Qt,
    pero ahora queda a prueba de que un cambio futuro de tema lo saque
    en silencio). La jerarquía visual de negrita/cursiva/color por
    nivel (`_aplicar_estilo_por_nivel`, sin cambios) sigue siendo la
    señal PRINCIPAL — el triángulo nativo es un refuerzo adicional,
    ahora garantizado en vez de una técnica QSS sin verificar.

    Probado con dos scripts dedicados (round-trip completo de renombrar
    categoría corrigiendo Musicalizador+Programador con datos reales +
    confirmación de que `rootIsDecorated()` es `True` y que el QSS ya
    no toca `::branch` de `tree_categorias`) + `py_compile` + smoke
    test de arranque completo sin traceback. **Sigue sin poder
    confirmarse visualmente con un display real**: falta que Santiago
    confirme que el triángulo ahora se ve siempre en las categorías con
    subniveles, y que el renombre de categoría se siente confiable con
    su Musicalizador/Programador reales.
98. ~~Pestaña Diagnóstico reorganizada + tema visual "Claro" (estilo
    Dinesat 9) implementado de punta a punta~~ — dos pedidos estéticos,
    con una captura real de Hardata Dinesat 9 (edición clásica) de
    referencia para el tema claro: "organizá mejor la pestaña
    Diagnóstico de Configuraciones, los botones muchas veces quedan
    largos y se tapan las letras, organizalo práctico, para que entre
    todo fácil" + "diseñá el tema 'Claro' te paso como es el Dinesat.
    Si podes hacer exactamente igual, sobre todo los colores...".

    **a) Diagnóstico reorganizado**: la pestaña había ido creciendo,
    ronda tras ronda (18 rondas distintas la tocaron desde que se creó
    el sistema de log), hasta acumular 8 botones y 8 párrafos
    explicativos siempre visibles, todo apilado en una sola columna
    angosta. Reescrita en 3 `QGroupBox` temáticos — "📋 Log de la
    aplicación" (Ver log/Subir a GitHub, en fila), "🎧 Historial y
    análisis de audio" (Ver historial/Verificar motor de audio/
    Reanalizar biblioteca, en grilla 2 columnas) y "🗂 Mantenimiento de
    biblioteca" (Duración faltante/Archivos perdidos/Duplicados, en
    grilla 2 columnas) — con los textos de botón ACORTADOS (ej. "🔄
    Reanalizar biblioteca — solo Música (recorte de silencio)" →
    "🔄 Reanalizar biblioteca (Música)") y el párrafo explicativo largo
    de cada uno movido a `setToolTip()` (aparece al pasar el mouse) en
    vez de ocupar espacio siempre. Toda la pestaña quedó envuelta en un
    `QScrollArea` (`setWidgetResizable(True)`) — si en una ronda futura
    se suma otro botón más, la pestaña scrollea en vez de volver a
    apretarse.

    **b) Tema "Claro" — implementado de punta a punta, no solo la
    entrada del combo**: el combo de Configuración → General ya tenía
    "Claro (próximamente)" desde hacía muchas rondas, pero nunca hubo
    ningún QSS asociado — `main.py` siempre aplicaba el único
    `QSS_APLICACION` (oscuro) sin importar el valor guardado. Refactor
    de fondo en `gui/styles.py`: la hoja de estilos, antes un f-string
    fijo armado a partir de constantes de módulo sueltas
    (`COLOR_FONDO_PRINCIPAL`, etc.), pasó a ser una FUNCIÓN
    `_generar_qss(paleta: dict)` que arma el QSS completo a partir de
    una paleta de colores de SUPERFICIE — así los dos temas comparten
    EXACTAMENTE los mismos selectores (imposible que uno se "olvide"
    de un selector que el otro sí tiene), y solo cambian los valores.
    `PALETA_OSCURA` (default, mismos valores de siempre, sin cambios
    visuales) y `PALETA_CLARA` (nueva) se generan una sola vez cada una
    (`QSS_APLICACION`/`QSS_APLICACION_CLARO`), y `qss_para_tema(tema)`
    es el punto de entrada nuevo que elige cuál aplicar.
    - **Colores de ESTADO/semánticos (rojo=reproduciendo, verde=
      siguiente, celeste=selección, naranja=armado) quedaron
      INTACTOS, iguales en los dos temas** — decisión de diseño
      explícita: son significado, no superficie (mismo criterio ya
      establecido en rondas anteriores: "los colores... es solo para
      identificarlos", y el propio Dinesat real usa el mismo rojo/
      verde en su tema claro y en el oscuro de la captura). Solo
      cambiaron los colores de fondo/panel/header/borde/texto/
      contadores/selección de árbol/botones genéricos.
    - **Paleta clara diseñada a partir de la captura real de Dinesat**:
      fondo general caqui/tan cálido (`#c7bb98`), título de cada panel
      (`QGroupBox::title`, que en esta app hace de "barra de título de
      ventana") en el mismo verde oscuro que los títulos de ventana de
      Dinesat (`#2e4a2e`, con texto blanco — antes usaba el color de
      texto general, que en el tema claro sería marrón oscuro sobre
      fondo YA oscuro, ilegible), listas en tono crema/tan
      (`#efe6c9`/`#e2d5ac` alternado), y los contadores
      "00:00:00"/"Ahora"/"Luego" imitando el display marrón oscuro con
      texto crema de la captura (`#3c2a25`/`#f2e6c9` — antes hardcoded
      `#101010`/`#f5f5f5`, ahora parte de la paleta).
    - **Bug real evitado de raíz, no encontrado después**: los botones
      de "identidad" con relleno saturado (Play/Stop/Fade-Stop/Cut/
      Play principal — verde/rojo/violeta/gris azulado) nunca tenían
      `color:` propio, heredaban el `color` genérico de `QWidget` —
      en el tema oscuro eso ya daba texto claro (funcionaba de
      casualidad), pero en el tema claro el texto general es marrón
      oscuro, lo que hubiera dejado esos 5 botones con texto oscuro
      sobre fondo oscuro, ILEGIBLE. Corregido agregando `color: white`
      explícito a los 5 ANTES de terminar la ronda, no como parche
      posterior — confirmado con un test que inspecciona el bloque QSS
      de cada uno.
    - `main.py`: el tema guardado se lee y se aplica ANTES de construir
      cualquier ventana (sin parpadeo oscuro→claro al abrir).
      `MainWindow._aplicar_configuracion_en_vivo()` (el mismo método
      que ya aplica en caliente nombre de emisora/volumen/dispositivo
      de salida) ahora también reaplica el tema — cambiarlo en
      Configuración y guardar lo aplica YA, sin reiniciar la app.
    - `EtiquetaMarquesina` (el sticker "Ahora"/"Luego") y los
      contadores de `lblTiempoTranscurrido`/`Restante` mantienen (o
      ahora comparten, en el caso de los contadores) el look de
      "display LCD oscuro" — deliberado, coincide con la propia
      captura de Dinesat, que también tiene un display oscuro
      insertado dentro de una ventana clara.

    Probado con 2 scripts dedicados: `qss_para_tema()` resuelve los 3
    casos (oscuro/claro/desconocido→oscuro), cada QSS generado usa
    ÚNICA Y EXCLUSIVAMENTE su propia paleta (sin mezclarse), los 4
    colores semánticos están presentes e idénticos en ambos temas, los
    5 botones de identidad tienen `color: white` explícito, el combo
    de Configuración ya no dice "próximamente", la pestaña Diagnóstico
    quedó organizada en exactamente 3 `QGroupBox` dentro de un
    `QScrollArea` con los 8 botones acortados (todos <40 caracteres,
    con la explicación completa movida al tooltip); + un segundo
    script que confirma el arranque real con el tema guardado en disco
    (simulando `main.py`) y el cambio EN VIVO desde
    `_aplicar_configuracion_en_vivo()` — + 2 capturas reales renderizadas
    offscreen (ventana principal completa y la pestaña Diagnóstico) en
    ambos temas para comparar visualmente antes de dar la ronda por
    terminada, enviadas a Santiago — + `py_compile` de los 4 archivos
    tocados (`gui/styles.py`, `main.py`, `gui/main_window.py`,
    `gui/ventana_configuracion.py`) + smoke test de arranque completo
    de la app sin traceback. **Sigue sin poder confirmarse con
    fidelidad total en un display real** (el sandbox no tiene el motor
    de fuentes/DPI exacto de la PC de Santiago, y los colores del
    screenshot de Dinesat se estimaron a ojo, no se pudieron samplear
    pixel a pixel): falta que Santiago confirme (1) que la pestaña
    Diagnóstico ahora entra cómoda sin textos tapados, y (2) que el
    tema Claro, una vez elegido en Configuración → General, se parece
    lo suficiente a su Dinesat real — si algún color puntual no
    convence (el verde de los títulos, el tono del caqui de fondo, el
    marrón de los contadores), son ajustes rápidos y acotados ahora que
    existe la paleta centralizada (`PALETA_CLARA` en `gui/styles.py`),
    sin tener que tocar la lógica de ningún widget.
99. ~~3 ajustes al tema Claro (letra de categorías ilegible, verde de
    más en la toolbar, muy caqui) + bug real de audio: "repite muy
    breve el inicio" en Pisadores y algunos ítems de Ventana 1~~ —
    pedido explícito tras probar la ronda anterior: "a) En las
    categorías, la letra sigue blanca y no se ve con el fondo claro.
    b) En los botones de arriba se ve un fondo verde. Sacarlo. c) No
    tan caqui, algo más claro, estilo plata" + un bug de audio nuevo,
    hermano del "en punto en punto" de una ronda anterior pero en el
    otro extremo del clip: "en pisadores sobre la ventana 2, incluso
    en algunos de la ventana 1, sucede al comienzo, como que repite
    muy breve el inicio".

    **a) Bug real — la jerarquía de colores por nivel de Ventana 3
    (ronda 96) nunca fue theme-aware**: `_ESTILOS_POR_NIVEL` (ahora
    `_ESTILOS_POR_NIVEL_OSCURO`) tenía colores blanco/gris claro
    hardcodeados, pensados solo para el fondo oscuro de siempre —
    invisibles contra el `tree_fondo` crema del tema Claro. Agregada
    `_ESTILOS_POR_NIVEL_CLARO` (misma progresión de negrita/cursiva/
    tamaño, pero con una escala de marrones oscuros en vez de grises
    claros) y `_aplicar_estilo_por_nivel()` elige la tabla según
    `self._tema_actual` (leído en `__init__`, mismo patrón ya
    establecido para `self._colores_genero`). Nuevo
    `VentanaExplorador.repintar_estilo_categorias()` (mismo criterio
    que `repintar_colores_genero()`, ya existente) recorre TODO el
    árbol de categorías reaplicando el estilo — llamado desde
    `MainWindow._aplicar_configuracion_en_vivo()` junto al resto de lo
    que ya se reaplica en caliente, así cambiar de tema y guardar
    corrige el color de las categorías sin reiniciar la app.

    **b) Bug real — la toolbar/menú/barra de estado usaban el mismo
    verde oscuro que el título de cada panel**: `gui/styles.py` tenía
    UNA sola clave (`fondo_header`) para dos conceptos DISTINTOS de la
    captura real de Dinesat — la barra de título de CADA ventana
    (verde oscuro, ej. "CONTACTO FM Emisión de publi...") y el chrome
    general de la app (toolbar/menú superior, gris CLARO en la
    captura real, nunca verde). Separado en dos claves nuevas:
    `chrome_fondo` (toolbar/menú/barra de estado — gris plata en el
    tema claro) y `header_columnas_fondo` (encabezado de columnas de
    las listas, un tostado medio propio). `fondo_header` quedó
    RESERVADO solo para `QGroupBox::title` (el título de cada panel —
    PROGRAMACIÓN/EMISIÓN/EXPLORADOR — que sí debe seguir verde, igual
    que Dinesat). De paso, el texto de `QMenuBar`/`QToolBar` pasó de
    `color: white` fijo a `color: {p['texto']}` (se ajusta solo al
    tono de `chrome_fondo`, oscuro o claro), y el de `QStatusBar`
    volvió de `white` (hardcodeado sin querer en la ronda anterior) a
    `texto_secundario` — el diseño ORIGINAL antes de este tema, ahora
    correctamente theme-aware. En el tema oscuro, `chrome_fondo`/
    `header_columnas_fondo` quedan con el MISMO valor que
    `fondo_header` de siempre (`#1f1f1f`) — cero cambio visual ahí,
    confirmado con un render de regresión.

    **c) Paleta clara re-calibrada, menos caqui, más "plata"**: los
    colores de fondo (`fondo_principal`/`fondo_panel`) pasaron de un
    khaki bastante saturado (`#c7bb98`/`#d6cba8`) a un beige-plata
    mucho más neutro y desaturado (`#d6d2c4`/`#e2ded0`) — el resto de
    la paleta (bordes, botones, hover) se recalibró en conjunto para
    mantener la cohesión visual. Los colores de estado (rojo/verde/
    celeste/naranja) y los contadores tipo display (marrón oscuro con
    texto crema) no se tocaron — no eran parte del pedido.

    **d) Bug real de audio — "repite muy breve el inicio" (Pisadores
    V2/Auxiliar, algunos ítems de V1)**: mismo mecanismo de fondo que
    "en punto en punto" (ronda 96), pero en el extremo OPUESTO del
    clip. `MotorAudio.reproducir()` SIEMPRE hacía un seek diferido
    (`_tras_arranque()`, ~150ms después de `play()`) a
    `punto_inicio_ms`, incluso cuando ese valor era `0` — el
    comentario original decía que hacía falta "incluso a 0ms" para
    garantizar el reinicio de posición al reproducir el mismo archivo
    dos veces seguidas. Pero ese reinicio YA lo garantiza el
    `self._player.stop()` que se ejecuta justo antes de `play()` (fix
    de una ronda mucho anterior, "el Pisador reusado deja de sonar") —
    el seek a 0ms del diferido era REDUNDANTE. El problema real: con
    `punto_inicio_ms == 0` (frecuente en Pisadores/stings cortos sin
    silencio de cabeza, y en cualquier ítem donde el análisis de
    silencio no encontró nada para recortar), el archivo YA estaba
    sonando correctamente desde el instante 0 durante esos ~150ms de
    espera — el `set_time(0)` del diferido, en vez de ser un no-op,
    REBOBINABA ese contenido ya reproducido de vuelta al principio,
    sonando como si el inicio se repitiera. Corregido: el seek ahora
    SOLO se hace si `punto_inicio_ms > 0` (hay un offset real que
    saltar) — con `0` no hay nada que "reiniciar", el archivo ya está
    en la posición correcta. De paso, se agregó un guard de
    generación (`_generacion_reproduccion`, mismo espíritu que
    `_fin_ya_emitido` de la ronda anterior) — protege contra un
    `_tras_arranque()` diferido de una llamada VIEJA que dispare
    después de que ya arrancó una reproducción NUEVA en el mismo motor
    (ej. un Pisador cancelado/reemplazado dentro de la ventana de
    150ms), que de otro modo corrompería la posición/volumen de la
    reproducción nueva. **Nota sobre la idea original de Santiago**
    ("que comience 500ms más tarde, si es posible"): un delay
    adicional NO hubiera resuelto esto — solo habría corrido el
    artefacto más tarde en el tiempo, sin eliminarlo (el `set_time(0)`
    seguiría rebobinando lo que sea que haya sonado mientras tanto).
    El fix real (saltear el seek redundante) elimina el problema de
    raíz sin agregar ninguna demora — Pisadores/ítems cortos siguen
    arrancando tan rápido como siempre.

    Probado con 3 scripts dedicados: (1) tema — toolbar/menú/status
    bar usan `chrome_fondo` (nunca el verde de `fondo_header`),
    `QGroupBox::title` sigue verde, el fondo general está desaturado
    (test de saturación RGB), tema oscuro con `chrome_fondo`/
    `header_columnas_fondo` idénticos a `fondo_header` (cero cambio);
    (2) categorías — nivel 2 en tema claro usa texto oscuro (antes
    casi blanco, ilegible), tema oscuro conserva el gradiente de
    siempre, `repintar_estilo_categorias()` actualiza un árbol ya
    construido al cambiar de tema en vivo; (3) audio — con un player
    VLC falso (mismo patrón que `test_volumen_robusto.py`):
    `punto_inicio_ms=0` ya NO dispara ningún `set_time()`,
    `punto_inicio_ms>0` sigue haciendo el seek real sin regresión, y
    un `reproducir()` viejo en vuelo no corrompe uno nuevo arrancado
    antes de que su diferido dispare — + 2 renders reales (tema claro
    con un árbol de 5 niveles de categoría visible, y tema oscuro,
    confirmado pixel a pixel que el header de columnas usa el color
    exacto de `header_columnas_fondo`) enviados a Santiago para
    comparar contra su pantalla real — + `py_compile` de los 3
    archivos tocados (`gui/styles.py`, `gui/ventana_explorador.py`,
    `core/audio_engine.py`, `gui/main_window.py`) + smoke test de
    arranque completo sin traceback. **Sigue sin poder confirmarse con
    audio/VLC real ni con fidelidad total de color en un display
    real**: falta que Santiago confirme (1) que la letra de las
    categorías ya se lee bien en el tema claro, (2) que la toolbar de
    arriba ya no se ve verde, (3) que el tono plata le resulta menos
    "caqui" que antes, y (4) — lo más importante — que los Pisadores de
    Ventana 2/Auxiliar y los ítems cortos de Ventana 1 ya no repiten
    el comienzo.
100. ~~3 pedidos tras salir al aire con más operadores: copiar
    archivos de dispositivos externos a la biblioteca, Copiar/Pegar
    en Ventana 2/Auxiliar, tamaño de fuente configurable por
    ventana~~ — pedido explícito, 3 puntos (a, c, d — sin "b" en la
    numeración de Santiago) apenas empezaron a operar con más gente:
    "ahi esta funcionando con los otros operadores y surgen los
    primeros detalles que me piden".

    **a) Archivo de un dispositivo externo (pendrive/celular)
    arrastrado a la biblioteca — ahora se COPIA a la carpeta real de
    la app, nunca queda dependiendo del dispositivo**: hasta esta
    ronda, arrastrar un archivo desde un pendrive/celular montado a
    Ventana 3 (alta individual o import masivo) guardaba la ruta TAL
    CUAL — si el operador después desconectaba el dispositivo, el
    material quedaba "perdido" (mismo síntoma que ya resolvían
    "Ubicar"/"Vincular" de rondas anteriores, pero evitable de raíz en
    vez de tener que reconciliarlo después). Nuevo
    `VentanaExplorador._copiar_a_biblioteca(ruta_origen, item_categoria,
    genero)` (`gui/ventana_explorador.py`): copia el archivo a la
    carpeta REAL y administrada de la app —
    `rutas.biblioteca_musical` si el género es "Musica", si no
    `rutas.biblioteca_publicidad` — dentro de la subcarpeta que
    refleja el camino de categorías (`ruta_de_categoria()`, ya
    existente), sanitizando el nombre de archivo (reusa
    `_sanitizar_nombre_archivo()` de `gui/dialogo_vincular_archivo.py`,
    import local para no crear un ciclo) y resolviendo colisiones de
    nombre con un sufijo numérico. Si el archivo YA estaba dentro de
    la carpeta administrada (ej. reimportar algo que ya se había
    copiado antes), no se copia de nuevo — se usa la ruta tal cual.
    Fail-open ante cualquier `OSError` (disco lleno, permisos, el
    pendrive se desconectó a mitad de copia): degrada devolviendo la
    ruta ORIGINAL sin romper el alta, mismo criterio de siempre en
    este proyecto ante operaciones de filesystem que pueden fallar.
    Llamado desde `_dar_de_alta_archivo()` (alta individual, justo
    después de confirmar el diálogo, antes de analizar el audio) y
    desde `_importar_archivos_masivo()` (import en lote, por archivo,
    antes de analizarlo) — el resto del flujo (análisis de silencio,
    persistencia) sigue exactamente igual sobre la ruta ya copiada,
    "haciendo el mismo proceso como si apretara el botón de agregar"
    tal cual pidió Santiago.

    **c) Copiar/Pegar en el menú contextual de Ventana 2 y Auxiliar
    (pedido explícito, aclarado por Santiago: "no sería duplicar el
    archivo físico sino duplicar el ítem")**: nuevo portapapeles
    PROPIO de cada `PanelReproductor` (`self._portapapeles`, una lista
    en memoria — Ventana 2 y el Auxiliar tienen cada uno el suyo, no
    se comparten). Dos métodos nuevos:
    - `_copiar_seleccionados(seleccionados)`: guarda los DATOS (nunca
      la referencia al `QTreeWidgetItem`, que puede desaparecer) de
      cada ítem de NIVEL SUPERIOR seleccionado — título/duración/
      código/ruta/análisis de audio, y si tiene un Pisador anidado,
      también sus datos (con el prefijo "↳ " y el sufijo " (Outro)"
      pelados del título guardado, para poder re-crearlo limpio al
      pegar vía `agregar_pisador()`).
    - `_pegar_despues_de(item_referencia)`: inserta una copia NUEVA e
      INDEPENDIENTE de cada ítem del portapapeles, en orden, arrancando
      justo debajo de `item_referencia` (o al final de la lista si no
      hay ninguna referencia) — el pegado nace SIEMPRE en estado
      normal (nunca hereda rojo/verde del ítem que se copió, aunque
      ese ítem estuviera sonando en el momento de copiarlo) y con su
      propio Pisador re-creado si correspondía.
    Menú contextual (`_mostrar_menu_contextual()`): "📋 Copiar" (solo
    aparece si hay algún ítem de nivel superior en la selección) y
    "📌 Pegar" (siempre visible, deshabilitado si el portapapeles está
    vacío) — el guard de apertura del menú se amplió para que también
    se abra con **nada seleccionado** si el portapapeles tiene algo
    (así se puede pegar al final de la lista haciendo click derecho en
    un espacio vacío). El punto de inserción al pegar es el ítem bajo
    el cursor del click derecho (o el último seleccionado, si el click
    fue sobre la selección existente) — mismo criterio ya usado por el
    resto de las acciones del menú contextual de este panel.

    **d) Tamaño de fuente configurable POR VENTANA (pedido explícito:
    "el monitor suele estar lejos y cuesta leer con el tamaño
    actual")**: nueva clave `apariencia.tamano_fuente_ventanas`
    (`config/settings.py`, dict `{"publicidad": 8, "emision": 8,
    "explorador": 8}` — 8pt es el tamaño de fábrica de siempre en
    `gui/styles.py`, así una instalación existente no "salta" de
    tamaño al actualizar) con 3 `QSpinBox` nuevos (rango 6-20pt) en
    Configuración → Apariencia, debajo de los colores por género —
    "Ventana 1 (Publicidad)", "Ventana 2 (Emisión / Auxiliar)" y
    "Ventana 3 (Explorador)". **Decisión de diseño explicada, no
    preguntada literalmente**: el Auxiliar comparte el valor de
    Emisión (no tiene selector propio) porque reutiliza EXACTAMENTE el
    mismo widget de lista (`PanelReproductor`/`tree_reproductor`) y no
    es una de "las 3 ventanas" que Santiago nombró (Publicidad/
    Emisión/Explorador) — mismo criterio ya usado en otras rondas para
    tratar al Auxiliar como una extensión de Ventana 2, no una cuarta
    ventana aparte. Nuevo `MainWindow._aplicar_tamano_fuente_ventanas()`:
    aplica `setStyleSheet(f"font-size: {n}pt;")` directo sobre cada
    `QTreeWidget` (`ventana_publicidad.tree`, `ventana_emision.tree`,
    `ventana_explorador.tree_archivos`/`tree_categorias`, y
    `_ventana_auxiliar.tree` si ya está abierto) — un stylesheet puesto
    a nivel de INSTANCIA siempre gana sobre la hoja de estilos general
    de la app para ese widget puntual, mismo mecanismo ya usado para
    aplicar color en caliente. Se llama en 3 momentos: al construir
    `MainWindow` (arranque, justo después de armar los paneles), desde
    `_aplicar_configuracion_en_vivo()` (guardar Configuración lo aplica
    YA, sin reiniciar — mismo patrón que nombre de emisora/tema/
    volumen) y al crear el Auxiliar por primera vez (`abrir_ventana_
    auxiliar()`, para que herede el tamaño de Emisión desde que se
    abre, no recién en el próximo guardado de Configuración).

    Probado con 4 scripts dedicados: **(a)** un script que simula
    categorías falsas + config con rutas temporales, confirmando que
    un archivo "externo" queda copiado dentro de la carpeta
    administrada con el nombre sanitizado, que reimportar algo ya
    copiado no lo duplica, y que colisiones de nombre se resuelven con
    sufijo; **(c)** copiar un ítem con Pisador y pegarlo en una
    posición intermedia (el original queda intacto, el pegado es un
    `QTreeWidgetItem` nuevo, nace en estado normal aunque el original
    estuviera "reproduciendo", el Pisador se re-crea), copiar selección
    múltiple, pegar con portapapeles vacío como no-op seguro, y — a
    nivel del propio menú contextual, interceptando `QMenu.addAction`
    para capturar la instancia real y pisarle el `exec()` de INSTANCIA
    (nunca de clase, ver la nota ya documentada sobre esta trampa de
    testing más abajo) — confirmado que el menú se abre con el
    portapapeles lleno aunque no haya nada seleccionado, y que elegir
    "Pegar"/"Copiar" dispara la lógica correcta de punta a punta;
    **(d)** round-trip de configuración (instalación nueva con los
    defaults, una config VIEJA sin la clave nueva autocompletándose sin
    romperse, guardar valores personalizados desde la UI real de
    Configuración) + una `MainWindow` REAL construida en offscreen
    confirmando que los 3 tamaños se aplican al arrancar, que el
    Auxiliar hereda el de Emisión al abrirse por primera vez, y que
    `_aplicar_configuracion_en_vivo()` reaplica los 3 en caliente
    (incluido el Auxiliar ya abierto) — + `py_compile` de los 5
    archivos tocados (`config/settings.py`, `gui/main_window.py`,
    `gui/panel_reproductor.py`, `gui/ventana_configuracion.py`,
    `gui/ventana_explorador.py`) + smoke test de arranque completo de
    la app sin traceback. **No se pudo correr la suite de regresión de
    scripts de rondas anteriores** (ninguno está commiteado al repo,
    ver ronda 90). **Sigue sin poder confirmarse con hardware/uso real
    con varios operadores a la vez**: falta que Santiago confirme (1)
    que arrastrar un archivo desde un pendrive/celular ya deja el
    material copiado en la PC (probarlo desconectando el dispositivo
    después y confirmando que sigue sonando), (2) que Copiar/Pegar en
    Ventana 2 y Auxiliar se siente natural para repetir una tanda en
    otro punto de la lista sin tener que volver a arrastrarla desde el
    Explorador, y (3) que los 3 tamaños de letra nuevos se leen bien de
    lejos con su monitor real, y que 6-20pt es un rango suficiente para
    lo que necesita (si hace falta más grande, es un simple cambio de
    rango en el `QSpinBox`).
101. ~~6 pedidos de operadores: sacar búsqueda de actualización al
    abrir, tamaño de fuente en TODOS los niveles de categoría, arranque
    siempre por Emisión (nunca un bloque vigente), click simple arma
    un bloque, ítem sacado del Explorador ya no suena — falta punto C
    (drag&drop, esperando aclaración de Santiago)~~ — seis pedidos en
    un solo mensaje (a, b, d, e, f — sin "c", pendiente de aclarar cuál
    ventana exactamente):

    **a) Sacar la búsqueda de actualización automática al abrir**
    (pedido explícito: "se actualizará solo por el menú
    configuraciones como está, no cuando abre el programa"): se sacó
    por completo el `QTimer.singleShot(2500, ...)` de
    `MainWindow.__init__` y los 3 métodos que solo existían para esa
    ruta (`_buscar_actualizacion_automatica`/
    `_on_resultado_busqueda_actualizacion`/`_preguntar_actualizar_ahora`,
    quedaban sin ningún otro llamador — código muerto, eliminado
    entero en vez de dejarlo sin usar). El botón manual de
    Configuración → Actualizaciones (`hay_actualizacion_disponible()`/
    `_aplicar_actualizacion()`, siempre fue un camino SEPARADO, propio
    de esa pestaña) queda exactamente igual, sin tocar nada. El
    mensaje "Verificando actualizaciones..." del splash de arranque
    (`main.py`) ya no tenía sentido (no cubre ninguna consulta de red
    real) — cambiado a "Cargando Auto-Radio Tuyú...".

    **b) Bug real corregido — el tamaño de fuente de Ventana 3 "solo
    hasta 3 niveles"**: la causa de fondo, encontrada auditando
    `_aplicar_estilo_por_nivel()` (la función que pinta negrita/
    cursiva/color/tamaño por nivel de categoría, ronda 96): partía de
    `fuente = item.font(0)` — el tamaño AMBIENTE del ítem en el
    instante exacto en que se llama, que depende pura y simplemente
    del ORDEN de ejecución. Como TODA la jerarquía de categorías se
    arma EAGER, dentro de `VentanaExplorador.__init__()` (que corre
    ANTES de que `MainWindow._aplicar_tamano_fuente_ventanas()` llegue
    a aplicar el tamaño configurado), cada nodo quedaba con un `QFont`
    YA EXPLÍCITO (tamaño ya resuelto contra el default de fábrica de
    8pt) desde el momento de su creación — y un `QFont` explícito, una
    vez asignado con `setFont()`, NUNCA vuelve a heredar del
    stylesheet del widget aunque este cambie después (a diferencia de
    un `QFont` "sin resolver", que sí cascadea). Corregido de raíz:
    `_aplicar_estilo_por_nivel()` ya NO lee nada ambiente — el tamaño
    de CADA nivel se calcula siempre desde un atributo propio,
    `self._tamano_fuente_categorias` (la fuente de verdad, cargada ya
    en `__init__` y actualizada por el método nuevo
    `establecer_tamano_fuente_categorias()`, que también repinta TODO
    el árbol). `MainWindow._aplicar_tamano_fuente_ventanas()` llama a
    este método nuevo en vez de un `setStyleSheet()` genérico para
    `tree_categorias` — el `setStyleSheet()` de `tree_archivos` (la
    lista de archivos, sin jerarquía de niveles) no tenía este
    problema y sigue igual, sin cambios.

    **d) Bug real de diseño corregido — al abrir, el Automático
    arrancaba un bloque de Publicidad "vigente" en vez de Emisión**
    (pedido explícito: "que comience emitiendo la música que está en
    la ventana 2, no la publicidad de la ventana 1... debe esperar SÍ
    O SÍ al bloque horario y hora especificada"): `SchedulerAutomatico.
    _arrancar_al_iniciar()` buscaba el "bloque vigente" (el de hora más
    tardía que ya pasó) y lo reproducía DE UNA si existía — con
    cualquier bloque horario ya pasado en el día (el caso más común),
    el arranque SIEMPRE terminaba en Publicidad, nunca en Emisión.
    Corregido sacando por completo esa búsqueda del arranque — ahora
    `_arrancar_al_iniciar()`, con Automático activo, llama SIEMPRE
    directo a `_reanudar_o_arrancar_emision()` — los bloques quedan
    esperando su hora real, disparados solo por `_tick()` cuando el
    reloj efectivamente la cruza, nunca de forma retroactiva. El
    comportamiento de "disparar el bloque vigente" NO desapareció del
    todo: sigue existiendo, sin cambios, para activar el Automático A
    MANO en pleno uso (`_on_automatico_cambiado`, pedido explícito de
    una ronda anterior con semántica distinta — una acción deliberada
    del operador, no un reinicio desatendido). El aviso "No se
    encontró Bloque Horario en este momento" (`_avisar_sin_bloque_horario`,
    `MainWindow`) y el callback `al_no_encontrar_bloque` quedaron sin
    ningún llamador — código muerto, eliminado entero (ya no tiene
    sentido: con la búsqueda de "vigente" sacada del arranque, "no
    encontrar un bloque vigente" pasó de ser el caso excepcional a ser
    SIEMPRE el resultado, así que avisarlo en cada arranque sería
    ruido, no una alerta real).

    **e) Un solo click sobre el título de un bloque lo arma en rojo**
    (pedido explícito: "cuando selecciono el bloque horario, permita
    pintarse de rojo... dejando atento a reproducir el primer ítem" —
    antes hacía falta doble click sobre el título): nuevo
    `VentanaPublicidad._on_click_item()`, conectado a
    `tree.itemClicked` — si el ítem clickeado es un nodo de bloque
    (`item.parent() is None`), reemite la MISMA señal `item_doble_click`
    que ya usa el doble click, reutilizando 100% la lógica ya existente
    en `GestorPublicidad._on_doble_click()` (que ya resuelve el primer
    ítem reproducible del bloque, saltando cualquiera marcado con
    error, y solo lo ARMA en rojo o lo ENCOLA en verde — nunca
    reproduce nada solo, ver ronda 68) — sin duplicar nada. Clickear
    una TANDA suelta (no el título de un bloque) sigue sin hacer nada
    por sí sola, sigue necesitando doble click/Enter como siempre —
    el chequeo `item.parent() is None` acota el cambio exclusivamente
    al título del bloque.

    **f) Bug real corregido — un archivo sacado de la biblioteca
    (Ventana 3) seguía reproduciéndose en Ventana 1/2 si el archivo
    físico seguía en disco** (pedido explícito, con un caso real: "se
    quitó del explorador un archivo que estaba programado... llegado
    la hora, lo reprodujo. Eso no debe ser así"): `GestorPublicidad.
    _item_valido()` / `GestorPlaylist._fila_valida()` (el chequeo
    proactivo de archivo faltante, ronda 66/83) solo verificaban
    `os.path.exists(ruta)` — pero ELIMINAR un registro del Explorador
    NO borra necesariamente el archivo físico (son dos cosas
    separadas, ver "Eliminar" vs. el "🗑" del diálogo de Vincular,
    rondas anteriores) — así que un archivo cuyo REGISTRO ya no existe
    en la biblioteca, pero cuyo archivo SÍ sigue en el disco, pasaba el
    chequeo de siempre sin problema y sonaba igual. Nuevo
    `VentanaExplorador.ruta_existe_en_biblioteca(ruta) -> bool` —
    CACHEADO (con ~10-12mil archivos reales, recorrer TODA la
    biblioteca en cada evaluación de cada ítem, en cada tick, hubiera
    sido un problema de rendimiento real, mismo tipo de bug ya resuelto
    en las rondas 76-78): la caché (`self._cache_rutas_biblioteca`, un
    `set`) se invalida en el ÚNICO par de choke points por los que pasa
    CUALQUIER alta/baja/movimiento de la biblioteca
    (`_guardar_biblioteca()`/`_guardar_biblioteca_debounced()`, más
    `recargar_biblioteca_desde_disco()`) — nunca en cada mutación
    individual por separado, así que el recorrido completo (costoso)
    solo se paga UNA vez tras un cambio real, nunca una vez por
    consulta. `_item_valido()`/`_fila_valida()` ahora exigen
    `os.path.exists(ruta)` Y `ruta_existe_en_biblioteca(ruta)` — un
    archivo sacado del Explorador se saltea de inmediato (mismo ícono
    de error X roja, mismo criterio "nunca romper la emisión" de
    siempre), sin importar si el archivo sigue físicamente en el
    disco. Aplicado por igual en Ventana 1 (`core/playlist_manager.py`)
    Y Ventana 2/Auxiliar (`core/gestor_emision.py`) — mismo criterio ya
    establecido en la ronda 83 de portar cada fix de robustez de V1 a
    V2 y viceversa.

    Probado con 2 scripts dedicados: **(a+b)** sin rastro de la
    búsqueda automática en `MainWindow.__init__` ni de los 3 métodos
    eliminados; los 5+ niveles de una jerarquía real de categorías
    (1 a 6) respetan el tamaño configurado (antes: niveles 2-4 podían
    quedar pegados al tamaño de fábrica sin importar la config),
    cambiar el tamaño en vivo repinta TODO el árbol ya construido;
    **(d+e+f)** con un bloque de hora YA PASADA (00:00:00) y Automático
    activo, `_arrancar_al_iniciar()` nunca dispara el bloque y siempre
    llama a `_reanudar_o_arrancar_emision()` exactamente una vez; un
    click sobre el título de un bloque arma su primer ítem en rojo,
    un click sobre una tanda suelta no hace nada; un ítem cuyo registro
    se saca de la biblioteca deja de ser válido en V1 Y V2 aunque el
    archivo real siga en disco, confirmado además que la caché de
    rutas NO recorre la biblioteca completa en 20 consultas seguidas
    sin cambios (solo la primera) — + `py_compile` de los 6 archivos
    tocados + smoke test de arranque completo sin traceback. **No se
    pudo correr la suite de regresión de scripts de rondas anteriores**
    (ninguno está commiteado al repo, ver ronda 90). **Sigue sin poder
    confirmarse con audio/hardware real ni con varios operadores a la
    vez**: falta que Santiago confirme (1) que ya no aparece ningún
    aviso de actualización al abrir, (2) que las categorías de nivel 4+
    se ven del tamaño correcto en su pantalla real, (3) que la radio
    arranca con música (Emisión) y no con publicidad al abrir el
    programa, incluso con un bloque horario de esa hora ya cargado,
    (4) que clickear un bloque horario lo arma en rojo de un vistazo, y
    (5) que un archivo sacado del Explorador ya no vuelve a sonar en
    ningún bloque programado.

**Punto C, aclarado y resuelto en la ronda siguiente — drag&drop
directo sobre la LISTA de archivos de Ventana 3**: la pregunta que
había quedado pendiente (a qué ventana/flujo se refería) se contestó
con precisión: "AL CARGAR ARCHIVOS AL PROGRAMA, actualmente solo
admite mediante el botón, no hay otra forma, deseo que se pueda cargar
nuevos ítem al programa arrastrando y soltando, sin importar el
origen (pen drive, carpeta del escritorio, usb externo, etc) luego sí,
abrir el diálogo para clasificar, uno solo o masiva, eso lo detectará
el programa". Investigado antes de tocar nada: el árbol de
CATEGORÍAS (`ArbolCategoriasConDrop`, columna izquierda) YA aceptaba
drops externos desde hacía muchas rondas — pero `tree_archivos` (la
LISTA de archivos de la derecha, `ArbolOrigenArrastre`, lo primero que
un operador intuitivamente prueba de arrastrar un archivo encima) era
`DragOnly` puro — únicamente ORIGEN de arrastre hacia otras ventanas,
nunca aceptaba nada soltado sobre ella. Ese hueco explica al pie de la
letra "solo admite mediante el botón" — probar a soltar un archivo
sobre la columna angosta de categorías nunca se le hubiera ocurrido al
operador.

Corregido en `gui/common_widgets.py`: `ArbolOrigenArrastre` pasó de
`DragOnly` a `DragDrop`, con `dragEnterEvent`/`dragMoveEvent`/
`dropEvent` propios (mismo patrón que el resto de los árboles de la
app — `event.source() is self` distingue "esto es un archivo externo"
de "esto soy yo mismo", aunque acá el segundo caso nunca debería
pasar de verdad porque `tree_archivos` no reordena sus propios ítems)
y una señal nueva, `archivos_soltados(lista_de_rutas)` — sin
`item_destino` (a diferencia de `ArbolConDrop`, acá no hay "sobre qué
ítem" cayó el drop; la interpretación siempre es "agregar a la
categoría actualmente seleccionada", el mismo criterio que ya usaba el
botón "＋ Agregar"). `VentanaExplorador` conecta esa señal a
`_on_archivos_soltados_en_lista()` (nuevo), que resuelve el destino
con `self._categoria_actual()` y delega en la MISMA
`_on_archivos_soltados_en_categoria()` que ya usaba el árbol de
categorías — sin duplicar nada de la lógica de detección "1 archivo ->
diálogo individual / 2+ -> diálogo masivo" ni la de "archivo ya
conocido de la biblioteca -> Mover/Copiar, archivo externo ->
Importar". Sin ninguna categoría seleccionada, avisa con un mensaje
claro ("Elegí primero una categoría a la izquierda...") en vez de
fallar. El resto del comportamiento de `ArbolOrigenArrastre` (ser
ORIGEN de arrastre hacia Ventana 1/2/Auxiliar, selección múltiple) no
se tocó.

Probado con `test_dnd_lista_archivos.py` (nuevo, dedicado): soltar 1
archivo externo sobre `tree_archivos` con una categoría ya
seleccionada dispara el alta individual sobre ESA categoría; soltar
2+ dispara el import masivo; un drop con `source()` igual al propio
árbol se ignora sin emitir nada; sin ninguna categoría seleccionada,
avisa en vez de romper — + `py_compile` de los 2 archivos tocados +
smoke test de arranque completo de la app sin traceback. **Sigue sin
poder confirmarse con hardware real** (arrastrar desde un gestor de
archivos real — Dolphin/Nautilus/PCManFM — mostrando un pendrive/USB
externo montado, cosa que el sandbox no tiene forma de simular de
punta a punta): falta que Santiago confirme que ahora puede arrastrar
un archivo desde cualquier origen directo sobre la lista de la
derecha (no solo sobre la columna de categorías) y que el diálogo de
clasificación se abre solo, individual o masivo según cuántos archivos
soltó de una vez.

102. ~~Botón azul "HORA/TEMP" manual en Ventana 2 (corte limpio, sin
    fade, pisando lo que suene) + botón AUTOMÁTICO con texto explícito
    y color distinguible del Stop~~ — dos pedidos:

    **A) Botón azul "HORA/TEMP" — reproduce manualmente HORA +
    TEMPERATURA, cortando limpio lo que esté sonando**: pedido
    explícito, "un botón color azul en los comandos de la ventana 2,
    donde pueda reproducirse la hora y la temperatura de manera
    manual. Debe salir limpia, sin fade ni nada. PISANDO lo que haya
    sonando." Nuevo botón "🕐 HORA/TEMP" (`objectName btnHthManual`,
    azul `#2980b9` — el MISMO tono que ya usa `COLOR_COMANDO` para los
    Comandos FMT/HTH del árbol de Ventana 1, consistente con ese
    significado ya establecido), 4to botón de la fila inferior de
    transporte de `PanelReproductor` (Pausa/Cut/Stop diferido/HORA-TEMP)
    — exclusivo de Ventana 2 vía un parámetro nuevo
    `permitir_hth_manual: bool`, mismo criterio ya usado para
    `permitir_ciclo_fmt` (la Auxiliar nunca lo recibe, ni siquiera
    re-exporta la señal `solicitud_hth_manual` en `VentanaAuxiliar`).

    **Motor** (`core/gestor_emision.py:reproducir_hth_manual()`):
    resuelve los clips de HORA y de TEMPERATURA por separado
    (`core.hth.resolver_comando_hth`, el MISMO motor puro ya usado por
    el Comando HTH real de Ventana 1 — "todo o nada" por comando: si
    HORA falla se saltea solo ESE, si TEMPERATURA falla se saltea solo
    ESA, si los DOS fallan no se reproduce nada) y los concatena (HORA
    primero, TEMPERATURA después). **Decisión de diseño explicada, no
    trivial**: en vez de PAUSAR el motor principal (que resumiría
    exactamente en la posición donde se cortó), se usa `detener()` de
    verdad — misma regla YA establecida en este archivo para cualquier
    handoff que después tiene que "volver limpio" (ver "Cosas ya
    resueltas" más abajo, "Nunca usar PAUSA para un handoff...") — y al
    agotarse la cola de clips se llama a `reproducir_actual()` (el
    MISMO camino ya probado del botón Play), así el ítem interrumpido
    arranca de nuevo desde el principio en vez de reanudar a mitad de
    canción con un mecanismo de pausa nuevo y frágil. Los clips suenan
    en un motor `MotorAudio` DEDICADO (`self.motor_anuncio_manual`,
    nunca el principal ni el del Pisador) — el corte del motor
    principal es inmediato (`motor.detener()`, sin ninguna rampa de
    volumen), y entre un clip y el siguiente tampoco hay ningún
    fundido (mismo criterio "sin fade ni nada" del pedido).

    **Bug real de generación evitado ANTES de llegar a Santiago,
    encontrado escribiendo el test** (mismo patrón `_generacion_pisador`
    ya documentado en este archivo, pero con una variante nueva): el
    slot `motor_anuncio_manual.finalizo_item` no recibe ningún
    argumento — si `_on_fin_clip_anuncio_manual()` releía
    `self._generacion_anuncio_manual` (el valor YA actualizado en ese
    instante) para pasárselo de vuelta a
    `_reproducir_siguiente_clip_anuncio_manual()`, la comparación de
    generación quedaba comparando un valor "contra sí mismo" — SIEMPRE
    coincidía, así que la protección contra interrupciones (Stop/Play/
    Cut mientras el anuncio está sonando) no protegía nada: un clip
    abandonado por un Stop de por medio igual seguía la cola vieja o
    reanudaba de más. Corregido guardando la generación VIGENTE en un
    atributo (`self._generacion_clip_actual_anuncio_manual`) justo
    ANTES de arrancar cada clip — `_on_fin_clip_anuncio_manual()` lee
    ESE valor capturado (el que tenía el clip que de verdad terminó),
    nunca el corriente. `_cancelar_anuncio_manual_en_curso()` (que
    vacía la cola, bumpea la generación y detiene
    `motor_anuncio_manual`) se llama al INICIO de `detener()`,
    `_pausar()`, `reproducir_actual()`, `_avanzar()` e
    `_iniciar_crossfade()` — cualquier otra acción del operador que
    tome control real de la reproducción mientras el anuncio suena lo
    cancela de raíz, sin dejarlo sonando de fondo ni con un "resume"
    diferido que pise lo que se acaba de hacer.

    Si no hay ningún clip resoluble (falta uno de voz, o no hay datos
    de clima todavía), NO se toca el motor principal para nada (nunca
    interrumpe si no hay nada para poner en su lugar) y se avisa por
    un callback nuevo (`al_fallar_hth_manual`, conectado en
    `MainWindow` a un mensaje de 6s en la barra de estado) — mismo
    criterio de siempre, GestorPlaylist no muestra diálogos por sí
    solo.

    **B) Botón AUTOMÁTICO: texto explícito + color distinguible de
    Stop**: pedido explícito, "que diga expresamente 'AUTO' y
    'MANUAL'... más distinguible en color que el botón de Stop, que se
    ubique mejor a simple vista" (el único botón AUTOMÁTICO de la app
    vive en Ventana 1/Publicidad, no "Ventana 3" como decía el pedido
    — corregido sin comentarios, es el mismo botón de siempre). El
    texto OFF pasó de la abreviatura "MAN" a "MANUAL" completo (ON
    sigue siendo "AUTO", ya era explícito). **Causa real del problema
    de color**: antes el botón era ROJO en los DOS estados — relleno
    rojo (`#e74c3c`) cuando ON, borde rojo (`COLOR_REPRODUCIENDO`,
    `#c0392b`) cuando OFF — al lado del botón Stop (también rojo,
    `#922b21`), desde lejos ("el monitor suele estar lejos", ya
    mencionado en una ronda mucho anterior sobre tamaño de fuente) las
    dos lecturas se confundían fácil, "dos botones rojos". Recoloreado
    a una familia dorado/ámbar EXCLUSIVA de este botón (`COLOR_AUTOMATICO_ON
    = "#f1c40f"` con borde `#b7950b`, `COLOR_AUTOMATICO_OFF = "#4a4a4a"`
    con borde `#8d6608`) — nunca rojo en ningún estado, así que ya no
    compite visualmente ni con Stop ni con el rojo de "reproduciendo".
    Fuente subida de 8pt (heredado de `btnTransporte`) a 9pt bold
    específico de este botón, para que pese un poco más a simple vista
    sin tener que moverlo de lugar (sigue emparejado con Stop en la
    fila superior, posición ya establecida en una ronda anterior a
    pedido explícito "más intuitivo y a la vista").

    Probado con `test_boton_hth_manual_y_automatico.py` (nuevo,
    dedicado): el botón dice "AUTO"/"MANUAL" sin abreviar; los 4
    colores nuevos del AUTOMÁTICO (fill+borde de los 2 estados)
    confirmados SIN ningún tono rojo compartido con Stop/COLOR_REPRODUCIENDO;
    el botón HORA/TEMP existe solo en Ventana 2, la Auxiliar ni
    siquiera re-exporta la señal; apretar el botón corta el motor
    principal YA (sin fade), encadena HORA→MINUTOS→TEMPERATURA en el
    motor dedicado sin volver a tocar el principal, y al agotar la
    cola retoma con `reproducir_actual()`; un Stop a mitad del anuncio
    invalida la cola vieja de verdad (confirmado con una señal de fin
    "tardía" simulando la condición de carrera real que motivó el fix
    de generación); sin clips resolubles no corta nada y avisa por el
    callback — + `py_compile` de los 6 archivos tocados + smoke test
    de arranque completo sin traceback. **Sigue sin poder probarse con
    audio/VLC real** (como todo lo que toca `core/audio_engine.py` —
    el sandbox no tiene libVLC): falta que Santiago confirme (1) que
    el botón AUTOMÁTICO ahora se distingue de un vistazo del Stop en
    su pantalla real, y (2) que apretar "HORA/TEMP" corta de verdad lo
    que estuviera sonando sin ningún fundido, se escucha el anuncio
    completo, y el tema interrumpido retoma normal al terminar (desde
    el principio, no a mitad — comportamiento elegido a propósito, ver
    la explicación de diseño arriba, avisar si en cambio esperaba que
    resumiera exactamente donde se cortó).

103. ~~LA CAUSA REAL de "no se puede arrastrar y soltar para cargar
    ítems" (ronda 101/102 no alcanzaba): el diálogo "＋ Agregar" es
    MODAL, bloquea el drag&drop hacia la ventana de atrás~~ — Santiago
    mandó un VIDEO REAL del operador ("a ver si con un video del
    operador entendés de una vez") mostrando el intento exacto: abre
    "＋ Agregar" (el diálogo nativo `QFileDialog.getOpenFileNames`),
    navega hasta la carpeta del archivo (`/home/radio/Escritorio/
    PUBLICIDADES DANIEL`), y trata de ARRASTRAR un archivo (`LOS
    AMIGOS LOCUTOR.mp3`) directo desde la lista del propio diálogo
    hacia la categoría ya seleccionada, visible detrás — el cursor
    muestra el ícono de "prohibido" (⊘) sobre el panel de destino.

    **Diagnóstico correcto, confirmado cuadro por cuadro del video**
    (`ffmpeg` instalado en el sandbox para extraer frames a 2fps y
    poder mirarlo, ya que el entorno no tenía reproductor de video):
    el DRAG se ve arrancar bien — Qt arma el pixmap de arrastre
    ("LOS AMIGOS LOCUTOR.mp3...") y lo sigue con el cursor — el
    problema NO es que el drop target esté mal armado (`tree_archivos`/
    `tree_categorias` YA aceptan drops externos desde la ronda
    anterior, 101) — es que **un diálogo MODAL bloquea CUALQUIER
    entrega de eventos a la ventana padre mientras está abierto**,
    incluido un evento de drag&drop, sin importar qué tan bien esté
    armado el drop target del otro lado — la ronda 101 solucionó el
    problema equivocado (asumió que el operador arrastraría desde un
    gestor de archivos EXTERNO ya abierto aparte, cuando en la
    práctica siempre usa el propio botón "＋ Agregar" de la app,
    que hasta ahora abría un diálogo bloqueante).

    **Corregido de raíz**: `VentanaExplorador._agregar_archivos()`
    (`gui/ventana_explorador.py`) reemplazó la llamada estática
    bloqueante `QFileDialog.getOpenFileNames()` por una INSTANCIA
    propia de `QFileDialog` con `setWindowModality(Qt.WindowModality.
    NonModal)` + `.show()` en vez de `.exec()` — MISMO diálogo, misma
    navegación, mismas columnas ("Look in:"/"Computer"/"radio",
    idéntico a lo que se ve en el video), CERO cambio visual para
    quien sigue eligiendo un archivo con un click + "Open" de toda la
    vida (ese flujo se conserva intacto, ahora disparado por la señal
    `filesSelected` en vez de por el valor de retorno de una llamada
    bloqueante, en `_on_archivos_elegidos_para_agregar()`). Con el
    diálogo ya NO bloqueante, el operador puede dejarlo abierto y
    arrastrar uno o varios archivos directo desde ahí hacia la
    categoría ya elegida a la izquierda, o hacia la lista de archivos
    de la derecha (mismo destino de siempre: la categoría actual) —
    reusa el 100% del mecanismo de drop ya construido en la ronda
    101, sin tocarlo. Guard nuevo (`self._dialogo_agregar_archivos`,
    con `WA_DeleteOnClose`): si el operador clickea "＋ Agregar" de
    nuevo mientras el diálogo ya está abierto, no se abre uno
    duplicado — se trae el existente al frente (`raise_()`/
    `activateWindow()`).

    Probado con `test_dialogo_agregar_no_modal.py` (nuevo, dedicado):
    el diálogo construido es `Qt.WindowModality.NonModal` y queda
    visible sin bloquear; clickear "＋ Agregar" con uno ya abierto no
    crea un segundo; elegir 1 archivo vía `filesSelected` (simulando
    el click en "Open") sigue disparando el alta individual sobre la
    categoría actual, elegir 2+ sigue disparando el import masivo —
    exactamente el mismo comportamiento de siempre; cerrar el diálogo
    y volver a abrir "＋ Agregar" crea uno nuevo sin problema — +
    `py_compile` + smoke test de arranque completo sin traceback.
    **Sigue sin poder confirmarse con hardware/OS real** (el sandbox
    no tiene forma de simular un drag&drop real entre ventanas del
    sistema operativo): falta que Santiago repita EXACTAMENTE la
    prueba del video — abrir "＋ Agregar", navegar hasta el archivo, y
    arrastrarlo hacia la categoría ya seleccionada — y confirme que
    esta vez el cursor ya no muestra "prohibido" y el archivo se
    agrega con normalidad (abriendo el diálogo de clasificación de
    siempre, individual o masivo según cuántos arrastró).

## Cosas ya resueltas que NO hay que "redescubrir"

- **Nunca usar PAUSA para un handoff entre dos motores/ventanas que
  después tiene que "volver limpio"** (bug real con audio real, ver
  roadmap ronda 36): `MotorAudio.esta_reproduciendo()` da `False` con
  el motor en pausa — cualquier guard tipo `if self.motor.
  esta_reproduciendo(): self.motor.detener()` en OTRO lugar del código
  (ej. `_limpiar_playlist_para_musicalizador()`) se salta el
  `detener()` pensando que ya no hay nada que parar, y el motor queda
  pausado en un ítem viejo que nadie toca — hasta que algo intenta
  "reanudar" (`motor.pausar()`, que alterna) y revive ese ítem viejo
  en vez de arrancar el contenido nuevo. Regla: para un handoff donde
  después hay que "empezar de cero" (no reanudar la MISMA posición),
  usar SIEMPRE `detener()` de verdad, nunca `pausar()` — aunque
  pausar parezca más elegante/menos disruptivo a primera vista.
- **Un guard de "generación" solo protege si el valor comparado se
  CAPTURA en el momento del despacho, no si se relee "en vivo" dentro
  del propio callback asíncrono** (bug evitado antes de llegar a
  Santiago, ronda 102, botón HORA/TEMP manual): con un slot SIN
  argumentos disparado por una señal asíncrona (ej.
  `MotorAudio.finalizo_item`), pasarle `self._generacion_actual` (el
  valor YA actualizado en ese instante) para comparar contra sí mismo
  más adelante es un no-op — SIEMPRE va a coincidir. El patrón
  correcto (ya usado antes para `_generacion_pisador`) es guardar la
  generación VIGENTE en un atributo aparte justo ANTES de despachar la
  operación async (ej. `self._generacion_clip_actual = generacion`
  antes de `motor.reproducir(...)`), y que el callback lea ESE valor
  capturado, nunca el corriente.
- El bug de Drag&Drop que no funcionaba (ver regla de oro arriba).
- **Un diálogo MODAL bloquea CUALQUIER entrega de eventos a la ventana
  detrás mientras está abierto — incluido un drag&drop, sin importar
  qué tan bien esté armado el drop target del otro lado** (bug real
  con video, ronda 103): `QFileDialog.getOpenFileNames()` (la versión
  estática/bloqueante) arma un diálogo modal — un drag iniciado DESDE
  ese mismo diálogo hacia la ventana padre (detrás) siempre muestra
  el cursor "prohibido", aunque el drop target de destino ya acepte
  drops externos perfectamente. **Regla**: si un operador reporta que
  "no puede arrastrar" hacia una ventana que tiene un diálogo modal
  propio abierto encima (de la MISMA app u otra), sospechar primero de
  la modalidad antes que del código del drop target — la solución
  suele ser volver ese diálogo puntual `Qt.WindowModality.NonModal`
  (`.show()` + señal `filesSelected`, en vez de `.exec()`/la llamada
  estática bloqueante), no tocar nada del lado que recibe el drop.
- **`MotorAudio.finalizo_item` podía emitirse DOS VECES para el mismo
  fin de reproducción** (bug real, ronda 96, "en punto en punto" del
  HTH): dos orígenes independientes detectan "esta reproducción
  terminó" — el tick de `_emitir_posicion()` (corte por
  `punto_fin_ms`, hilo principal, conexión directa) y el evento nativo
  `MediaPlayerEndReached` de libVLC (`_on_fin_reproduccion`, disparado
  desde un hilo INTERNO de libVLC, entregado al hilo principal vía una
  conexión Qt ENCOLADA que puede procesarse más tarde de lo esperado)
  — para un clip CORTO con margen de silencio casi nulo (como los
  clips de voz del HTH) ambas detecciones caen casi siempre dentro de
  la misma ventana de tiempo, así que las DOS emisiones le llegan al
  handler para lo que en la práctica es un solo fin real, duplicando
  cualquier avance de cola/playlist enganchado a esa señal. Corregido
  con un guard de una sola vez por reproducción
  (`MotorAudio._fin_ya_emitido`/`_emitir_fin_una_vez()`, reabierto en
  cada `reproducir()` nuevo). **Regla**: cualquier señal que combine
  un origen basado en TIMER (hilo principal, síncrono) con un origen
  basado en un EVENTO NATIVO de libVLC (hilo ajeno, entrega asíncrona)
  para detectar el mismo hecho es candidata a doble emisión — no
  asumir que "ya se manejó" en un origen alcanza para cubrir al otro;
  agregar un guard explícito de una sola vez por evento (generación/
  flag reabierto en cada intento nuevo), mismo espíritu que
  `_generacion_pisador`/`_generacion_pausa_emision` ya documentados
  más abajo.
- **Un seek "por las dudas" a la posición ACTUAL puede rebobinar
  contenido que ya sonó de verdad** (bug real, ronda 99, "repite muy
  breve el inicio" — hermano del bug de arriba, en el otro extremo del
  clip): `MotorAudio.reproducir()` hacía un `set_time(punto_inicio_ms)`
  diferido SIEMPRE, incluso con `punto_inicio_ms == 0` — la intención
  original era "garantizar" el reinicio de posición al reproducir el
  mismo archivo dos veces seguidas, pero ese reinicio YA lo garantiza
  el `stop()` que corre justo antes de cada `play()` (fix de una ronda
  mucho más vieja). Con el offset en 0, el archivo ya estaba sonando
  bien desde el instante 0 durante los ~150ms que tarda en dispararse
  el diferido — el seek "de garantía" terminaba rebobinando ese
  contenido YA reproducido de vuelta al principio, un rebobinado
  audible. **Regla**: un seek/reset "por las dudas" que se ejecuta
  SIEMPRE, sin chequear si de verdad hace falta, puede terminar
  deshaciendo trabajo real que ya ocurrió mientras tanto — antes de
  agregar una salvaguarda incondicional, preguntarse qué pasa si se
  ejecuta cuando YA NO hace falta.

- **El Pisador no sonaba porque faltaba una delegación** (ver nota
  completa en Ventana 2): cuando un wrapper (`VentanaEmision`/
  `VentanaAuxiliar`) delega métodos en `PanelReproductor`, hay que
  delegar TODOS los que el core (`GestorPlaylist`) necesita — un
  `hasattr()` defensivo puede tapar el faltante en silencio sin
  ningún error visible. Si algo "no pasa nada" sin traceback, primero
  sospechar de una delegación incompleta entre wrapper y panel.
- La columna que se tapaba al redimensionar (Stretch +
  minimumSectionSize).
- **Una ventana top-level SIN `setMinimumSize()` explícito hereda como
  piso real el `minimumSizeHint()` que calcula en cascada TODO su
  árbol de layouts** (ver roadmap ronda 56, "el maximizado se va de
  pantalla") — cualquier `QSplitter` con `setChildrenCollapsible(False)`
  en el medio (puesto para evitar un colapso accidental) hace que
  NINGÚN panel baje de su tamaño "cómodo" natural, y eso se propaga
  hacia arriba sin que se note hasta que alguien prueba en una
  pantalla más chica que esa suma. Regla para cualquier ventana
  principal nueva: setear siempre un `setMinimumSize()` explícito y
  chico (que entre en cualquier notebook real, ~900px de ancho o
  menos) — un mínimo explícito SIEMPRE gana sobre el `minimumSizeHint()`
  calculado, así que es la forma confiable de evitar este bug de
  raíz, en vez de perseguir cada widget interno que podría estar
  empujando el mínimo hacia arriba.
- **`_avanzar()` e `_iniciar_crossfade()` (Ventana 2) son dos caminos
  de avance PARALELOS que no comparten código** — `_avanzar()` corre
  cuando un ítem termina sin crossfade; `_iniciar_crossfade()` corre
  en la transición NATURAL cuando `crossfade_activado=True` (el modo
  real de producción de Santiago). Cualquier lógica nueva sobre "qué
  ítem sigue" (freno por hora, etc.) que solo se agregue a
  `_avanzar()` NUNCA se ejecuta en producción si el crossfade está
  prendido — hay que agregarla a los DOS lugares. Ya mordió una vez
  (el refill del FMT, ver roadmap ronda 33). **Para el refill del
  Musicalizador puntualmente, esto ya no aplica** desde la ronda 34:
  se centralizó en `GestorPlaylist._marcar_siguiente_con_refill()`,
  un envoltorio ÚNICO sobre `panel.marcar_siguiente()` que
  `_avanzar()`, `_iniciar_crossfade()` y `_asegurar_rojo_y_verde()`
  llaman por igual — un código nuevo que marca verde en Emisión ya no
  puede "olvidarse" del refill porque no hay forma de marcar verde sin
  pasar por ahí. Sigue siendo cierto que CUALQUIER OTRA lógica nueva
  sobre "qué ítem sigue" (no relacionada a marcar verde) todavía tiene
  que agregarse a mano en los dos lugares.
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
  **Segunda variante de la misma trampa, mordió de nuevo (ronda de
  rendimiento con bibliotecas grandes)**: no es solo la comparación
  por identidad — MUTAR un dict/lista que salió de `.data()` tampoco
  se refleja en lo que el ítem tiene guardado, a menos que se lo
  vuelva a escribir con `.setData()` a propósito. La "migración
  silenciosa" de duración de `_agregar_fila_archivo()` mutaba
  `registro["duracion"]` sobre una copia descartable leída de
  `item.data(0, ROL_ARCHIVOS)` — la migración nunca quedaba cacheada
  de verdad, se repetía (con su costo real de mutagen) cada vez que
  se volvía a leer esa categoría. **Regla ampliada**: cualquier
  código que LEA `.data()` de un rol custom con la intención de
  MUTAR lo leído (no solo comparar) tiene que volver a escribirlo con
  `.setData()` explícito para que la mutación persista — leer y
  mutar sin volver a escribir es un no-op silencioso sobre los datos
  reales, por más que la variable local parezca haber cambiado.
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
- **Escritura atómica con nombre de archivo temporal FIJO = bomba de
  tiempo en cuanto hay MÁS DE UN PROCESO que puede escribir el mismo
  archivo** (bug real, ronda 91): `_guardar_json_atomico()` usaba
  `"{ruta}.tmp"` como nombre de temporal — perfectamente seguro
  mientras solo la app principal escribiera cada archivo, pero en
  cuanto el reanálisis de biblioteca pasó a correr como PROCESO
  APARTE (ronda 89, a propósito para no trabar la GUI), dos escrituras
  casi simultáneas al mismo `.tmp` fijo hacían que el segundo
  `os.replace()` fallara con `FileNotFoundError` (el primero ya se
  había llevado el archivo temporal al renombrarlo) — tirando abajo
  el proceso entero. **Regla**: cualquier función de guardado atómico
  que un archivo pueda llegar a compartir entre dos procesos/hilos
  (ahora o en el futuro) necesita un nombre de temporal ÚNICO por
  escritura (`tempfile.mkstemp()` en el mismo directorio, nunca
  concatenar `.tmp` a secas) — el costo es cero y evita esta clase
  entera de bug de raíz, incluso si hoy parece "imposible" que dos
  escritores coincidan.
