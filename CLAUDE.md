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

Opcional — control de EasyEffects (procesamiento de audio de la FM,
ver roadmap ronda 37):

```bash
sudo apt install easyeffects
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
