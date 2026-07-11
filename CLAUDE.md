# CLAUDE.md — Contexto del proyecto para Claude Code

Este archivo se lee automáticamente cada vez que Claude Code arranca en
esta carpeta. Es el resumen de todo lo construido hasta ahora en
conversación con Santiago vía claude.ai, para que Code retome sin
tener que redescubrir nada.

## Qué es esto

**RadioLinuxMadariaga**: automatización radial para Linux, clon
funcional de Dinesat 9. Python + PySide6 (GUI) + python-vlc (audio) +
pydub/ffmpeg (análisis de audio) + JSON/QSettings (persistencia).
Repo: https://github.com/ElSelloTV/RadioLinuxMadariaga

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
  playlist_manager.py         # GestorPlaylist / GestorPublicidad / GestorExplorador
  analizador_audio.py         # recorte de silencios + nivelado (pydub/ffmpeg)
  actualizador.py             # git fetch/pull + reinicio de la app

config/
  settings.py                 # config general (JSON) + programaciones (JSON)
  data/                        # generado en runtime, NO se versiona (.gitignore)

assets/
  radiolinuxmadariaga.desktop # lanzador de escritorio
  icono.png                    # ícono placeholder (Santiago lo va a cambiar)

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
Árbol de bloques horarios (bloque -> tandas). Botón AUTOMÁTICO
(rojo=ON). Contadores de tiempo arriba, controles Play/Pausa/Stop/
Siguiente debajo del tiempo, lista al final. Doble click: si el
reproductor está detenido, arranca desde ahí (rojo); si está sonando,
no interrumpe. `GestorPublicidad` en `playlist_manager.py` maneja todo
esto y el salto en cascada si un ítem falla.

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

### Ventana 2 — Emisión + Ventana Auxiliar
Ambas son un envoltorio delgado sobre `PanelReproductor`
(`gui/panel_reproductor.py`) — la misma clase de UI, reutilizada por
composición. Rojo = sonando, verde = próximo. Doble click: detenido =
arranca ahí; sonando = marca como "siguiente" sin interrumpir.
`GestorPlaylist` maneja avance normal, avance manual, y cascada de
errores (reintentos configurables antes de rendirse), respetando
"repetir lista al finalizar" de Configuración.

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
existe todavía, se cargan las categorías demo y se persisten como
base inicial (`_cargar_biblioteca_inicial`).

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
  columnas Título/Artista/Género/Código, coloreadas por género:
  Música=verde, Publicidad=amarillo, Separador=naranja,
  Pisador=violeta, Artística=azul (`gui/styles.py:GENERO_COLORES`).
- **Drag&Drop interno**: arrastrar de la columna derecha a una
  categoría de la izquierda MUEVE el archivo (con toda su metadata)
  entre categorías. Implementado en
  `_on_archivo_soltado_en_categoria` en `ventana_explorador.py`.
- **Drag&Drop externo**: de ahí hacia Ventana 1, 2, Auxiliar y
  Programador (agrega el archivo a esas listas).
- Al agregar un archivo se abre `DialogoAgregarArchivo`: elegir
  categoría (combo jerárquico con sangría), nombre editorial (puede
  diferir del archivo fuente), artista, género. El código correlativo
  se calcula solo: prefijo por género (`GENERO_PREFIJOS_CODIGO`) +
  número correlativo **dentro de esa categoría específica**.
- Menú contextual (botón derecho): Importar, Exportar, Reemplazar,
  Eliminar, Editar (abre el editor de audio predeterminado del
  sistema vía `QDesktopServices`; si no hay ninguno asociado, ofrece
  elegir un ejecutable a mano).
- Botones Play/Stop de preescucha (`GestorExplorador`).
- Columnas: última columna en modo `Stretch` + `setMinimumSectionSize`
  para que nunca quede tapada al redimensionar (ver
  `configurar_columnas_ajustables` en `common_widgets.py`) — esto fue
  un bug reportado explícitamente por Santiago y ya está resuelto.

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
General (confirmaciones, reloj, tema), **Actualizaciones** (ver
abajo). Todo persiste en `config/data/config_general.json`.
Deliberadamente **sin nada de satelital/RDS** — Santiago fue
explícito en que no lo necesita.

### Actualizador (`core/actualizador.py`)
`git fetch` + comparar HEAD local contra `origin/main` (o `master`),
`git pull --ff-only` para aplicar, y reinicio del proceso
(`QProcess.startDetached` + `app.quit()`). Si la carpeta no es un
clon git real, se deshabilita solo con un mensaje claro en vez de
fallar. Botón en Configuración → pestaña Actualizaciones.

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

## Cosas ya resueltas que NO hay que "redescubrir"

- El bug de Drag&Drop que no funcionaba (ver regla de oro arriba).
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
