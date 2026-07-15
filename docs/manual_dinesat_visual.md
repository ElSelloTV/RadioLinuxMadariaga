# Manual de usuario — Dinesat Visual (Hardata), v4.0.4.17

> Guardado en el repo a pedido explícito de Santiago ("Guardalo en la
> memoria de este proyecto") — es la referencia de diseño completa
> contra la que se compara esta app (`RadioLinuxMadariaga` / "Auto-Radio
> Tuyú"). Convertido de PDF a Markdown por Santiago con
> https://pdf2md.morethan.io/ y pegado tal cual en el chat.
>
> **Importante**: Dinesat Visual es un producto MUCHO más grande que lo
> que esta app se propone ser — incluye video/NDI, switcher de video,
> satélite/RS232, RDS, contestador telefónico SIP, VNC, server de
> backup, multi-emisora, etc. Todo eso está **explícitamente
> descartado** para este proyecto (ver CLAUDE.md, sección "Estudio del
> manual de Hardata Dinesat 9/Visual" y roadmap ronda 26) — Santiago
> fue	 explícito: esta app es para UNA sola emisora standalone, sin
> satelital/remoto, sin video. Este archivo se guarda completo como
> referencia de consulta, no como lista de funciones a implementar.
>
> Ver CLAUDE.md para qué partes de este manual ya se usaron o se están
> usando en el desarrollo (los comandos HTH de Hora/Clima, el
> Musicalizador Avanzado con comandos FMT, etc.).

---

[PDF To Markdown Converter](https://pdf2md.morethan.io/)

Última modificación: diciembre de 2018
Dinesat Visual
Audio and video management for radio stations
Manual de usuario

```
Versión 4.0. 4. 17
```

Índice

1. Novedades
   - 1.1. Características generales
   - 1.2. Introducción
   - 1.3. Planificación de la instalación
2. Instalación de Dinesat Visual
3. Licenciamiento
   - 3.1. Código de usuario
   - 3.2. Solicitud de renovación de Código de Usuario
   - 3.3. Cambiar el actual código de Usuario
4. Configuración de Dinesat Visual
   - 4.1. Menú Principal
   - 4.2. Emisoras
   - 4.3. Preferencias de la Terminal
   - 4.4. Herramientas web
   - 4.5. Ayuda
   - 4.6. Idiomas
   - 4.7 Buscar Actualizaciones
5. Entorno de trabajo
   - 5.1. Accesos Principales
   - 5.2. Explorador
   - 5.3. Emisión
   - 5.4. Edición
   - 5.5. Programación
   - 5.6. Más
   - 5.7. Cambio de usuario
6. Soporte Técnico
7. Apéndice

## 1. Novedades

Gestión de audio y video para cadenas de radio. Diseñado para emisoras pequeñas y medianas, Dinesat Visual genera una salida de video que puede usarse para TV o su publicación en la web y redes sociales con tecnología NDI.

### 1.1. Características generales

**Listas de reproducción con audio y video**
Soporta mezclar en el playlist materiales de audio y video. Mantiene todas las características de operación clásicas de una emisora de radio, incluyendo fades, crossfades y anuncios.

**Salida de video para tv y streaming**
Además de la clásica salida de audio, DINESAT VISUAL genera una salida de video que puede usarse para TV o su publicación en la web y redes sociales.

**Mezcla automática**
Mejor que un DJ en vivo. Detecta automáticamente el punto óptimo de mezcla entre los archivos de audio (música, artística) resultando en una transición suave y con niveles óptimos de sonido.

**Herramientas One-touch**
Avanzadas herramientas hacen de la administración de contenidos para emisión, una tarea fácil y eficiente con opciones de Play Over, Voice Over, Fade, Fade Over y Crossfade.

**Soporte RDS**
Muestra el nombre de la emisora, título e intérprete del tema musical y mensajes personalizados en la radio.

**Hora y estado del clima**
Con actualización meteorológica desde internet, emita la información de hora y clima con solo presionar un botón, o inclúyala en la programación.

**Musicalizador**
Permite crear fácilmente programación musical estableciendo criterios de selección tales como artista, género, ritmo, prioridad, año, etc.

**Acceso web**
Todas las soluciones de DINESAT VISUAL incorporan acceso web integrado, capaz de administrar usuarios de manera simple y generar reportes remotos de los contenidos emitidos. La compatibilidad ha sido verificada tanto para plataformas PC y MAC.

**Administracion de llamadas**
Atiende y graba las llamadas de los oyentes, mientras graba y administra las llamadas de los corresponsales a través de un sistema de comandos DTMF.

**Logger (grabación continua)**
El sistema puede realizar grabaciones continuas de una o varias señales. Puede ser utilizada como copia legal.

### 1.2. Introducción

Nos sentimos muy agradecidos por haber elegido a Dinesat Visual para administrar los contenidos de su emisora o cadena Radial.

Dinesat Visual es un completo sistema integral que le permitirá administrar de forma segura, fácil y flexible todos los contenidos multimedia.

Es un completo y poderoso sistema que permite gestionar y administrar todos los eslabones de una cadena radial con múltiples sistemas de distribución como Satélite, Internet o cualquier vínculo que soporte el protocolo TCP/IP. De esta manera se podrá generar los contenidos en un lugar físico y distribuir los contenidos a todos los eslabones de la cadena. Una vez emitido el contenido en cada eslabón, automáticamente el sistema envía la auditoria de lo emitido a la sede central. Permitiendo escuchar el contenido emitido, de esta forma se tiene absoluto control de la cadena radial.

La nueva tecnología ShotPlay, denomina al nuevo motor de audio que no solo permite el disparo instantáneo de sus audios y videos, sino que además incorpora soporte para tarjetas de Audio ASIO. Además, soporta múltiples formatos de audio (Wma, Flac, ogg, mp3, etc).

El sistema Dinesat Visual está basado en la tecnología Hardata SmartServer 4, esta tecnología le permitirá tener una completa seguridad en el control de sus contenidos. Incorpora la ventaja del almacenamiento distribuido, que permite el almacenamiento en múltiples storage.

Permite la integración con otros sistemas es decir brinda un conjunto de herramientas para el desarrollo de interfaces, para poder interactuar con otros sistemas de tráfico, de servicios web, etc.

Permite la administración desde la web. La administración de los usuarios se puede realizar desde un browser de internet (Microsoft Internet explorer, Mozilla Firefox, Google Crome) o también desde dispositivos móviles PDA, Tablet, etc.

### 1.3. Planificación de la instalación

Antes de realizar la instalación es conveniente realizar un esquema de la instalación y una descripción del flujo de trabajo. Esto permite una percepción total del funcionamiento de la emisora, permitiendo corregir cualquier problema. Antes de implementarlo. Luego se podrá utilizar este ejemplo para crear los grupos de usuarios y permisos correspondientes. Para realizar esta tarea se deberá consultar el manual de usuario de Hdx Remote Tools.

A modo de ejemplo, se describe un flujo de trabajo de una emisora de radio: Agencia de Publicidad/Cliente → Comercial → Administración de Ventas o Tráfico → (¿Se genera en la emisora? → Redacción Creativa) → Edición → Producción / Musicalización → Archivo / Emisión / News.

El departamento comercial recibe el material publicitario "Audio" y la correspondiente pauta publicitaria, la descripción de cuantas emisiones diarias debe tener cada publicidad, desde las agencias de publicidad o de los clientes directamente. Al recibir las publicidades desde un cliente directo, puede requerirse la creación de la publicidad completa, en este caso deberá interactuar con el sector de "Redacción creativa". En este sector se redacta la publicidad, se eligen las piezas musicales, efectos y estilo de la publicidad.

En el caso que el material de publicidad se reciba desde una agencia de publicidad (ya realizada, lista para importar), la pauta es programada en Dinesat Visual por el sector de administración de ventas o tráfico. El material de audio correspondiente es importado en el sistema por el área de edición.

La producción de los contenidos se realiza desde las áreas de Producción, Musicalización. Una vez emitidos los contenidos se produce el archivado de todo el material emitido. Luego este material podrá recuperarse para una futura necesidad o bien como método de control. En el área de archivo se podrán capturar la propia emisión o la de terceros, con el "grabador continuo" (tarjetas con sintonizadores de radio/TV, etc.).

## 2. Instalación de Dinesat Visual

*(Sección de instalación de Windows/SQL Server/dongle USB — no aplica a esta app, omitida en detalle. Ver manual original si hace falta.)*

## 3. Licenciamiento

*(Códigos de usuario, llaves físicas/virtuales, renovación — no aplica a esta app, que no tiene sistema de licenciamiento propio.)*

## 4. Configuración de Dinesat Visual

Por omisión el usuario es "Administrator" y tiene como contraseña "Supervisor".

### 4.1. Menú Principal

Botones principales de acceso a todas las herramientas de Dinesat Visual.

### 4.2. Emisoras

#### 4.2.1. General

Se pueden visualizar el detalle de todas las emisoras declaradas en el sistema (Dinesat soporta múltiples emisoras desde una misma instalación — **no aplica acá**, la app es para UNA sola emisora standalone). Al agregar una emisora se crean automáticamente las ventanas de Emisión y programación por cada una.

En la sección "Formatos" se puede seleccionar un formato musical predeterminado para automatizar la programación musical.

#### 4.2.2. Modo Automático

Configura cómo automatiza la emisión. Parámetros: Prioridad musical, Prioridad publicitaria, Entrada auxiliar, Satélite + Tonos y Satélite + RS232.

- **Música**: prioriza el contenido de "Emisión musical" — al llegar la hora del corte comercial, Dinesat reproduce hasta el FINAL el contenido en curso antes de pasar a publicidad (sin fade, corte directo al terminar).
- **Música + Fade**: igual que "Música" pero al llegar la hora del corte, hace un fade-out sobre el contenido de "Emisión de música" para darle prioridad a la publicidad — esta es la opción usada como referencia de diseño para el Ciclo Automático de esta app (bloque horario corta a Emisión con fundido).
- **Entrada auxiliar**: usa una señal de audio externa (entrada de línea) en vez de la ventana de Emisión musical — **no aplica**, esta app no tiene entrada de línea física configurada.
- **Satélite + Tonos / RS232 / Reemplazo de Música**: modos de cadena de emisoras con decodificador satelital — **explícitamente descartado** ("Satélite, Remoto, no me gusta", ver CLAUDE.md).
- **Validez del Bloque**: margen de tiempo (antes/después) para permitir que un bloque se emita aunque la programación de música no haya terminado/empezado exactamente a horario.
- **Entrada Auxiliar** (audio settings): nivel máximo/mínimo, "Cerrar Aux durante reproducción", Fade Out/In, Cross Fade — todo relativo a la entrada de línea física, no aplica.

### 4.3. Preferencias de la Terminal

Preferencias Globales (dispositivos de audio/video, clima, VNC, editores externos, extractor de CD, import/export, RDS, Virtual Tools) y Preferencias de Ventanas (una configuración de dispositivo de audio/fade por cada tipo de ventana: Asistente en vivo, Contestador SIP, Edición de Audio, Emisión Auxiliar, Emisión de Música, Emisión de Publicidad, Explorador, Grabador Continuo, Importador de materiales/programaciones, Lista en vivo, Programación de música/publicidad, Switcher de video, Voz superpuesta).

**4.3.1.3. Clima** (la sección relevante para FMT/HTH CLIMA):

> En la opción "Clima" se define la forma en que se actualizarán los
> datos meteorológicos, pueden ser de forma Manual, central
> meteorológica o automática a través de Internet. Desde la sección
> "Emisión" se debe seleccionar la categoría que contiene los
> materiales de audio, la cual debe tener grabadas todas las opciones
> meteorológicas (Ej: Materiales de audio con la hora, temperatura,
> humedad y sensación térmica). En la sección "Ciudad" se deberá
> especificar la ciudad, de la cual se quiere conocer los datos
> meteorológicos, para que el sistema importe automáticamente los
> datos desde Internet.
>
> En la sección "Unidades", se deberá seleccionar el sistema de
> unidades de medida deseado.
>
> En la sección "TOP", se podrá definir el uso del TOP horario. Es
> decir, la señal auditiva indicando las horas exactas "TOP 00" y cada
> 30 minutos "TOP 30".
>
> En la solapa Propiedades de Audio, se debera configurar el
> dispositivo de reproduccion por cual se emitiran los materiales del
> tipo Clima.

### 4.4. — 4.7. Herramientas web / Ayuda / Idiomas / Buscar Actualizaciones

*(No aplica — esta app no tiene acceso web ni sistema de licencias/actualizaciones online propio más allá del botón "Actualizar" vía git.)*

## 5. Entorno de trabajo

### 5.1. Accesos Principales

Botones del menú principal: Ordenar Ventanas, Explorer, Emisión (Publicidad/Música/Noticias/Auxiliar/Asistente en vivo/Clima/Voz Superpuesta), Edición, Programación, Más (Grabador Continuo/Contestador SIP/Importadores/Switcher/Monitor de video), Configuración.

### 5.2. Explorador

Ventana destinada a la administración de todo el contenido del sistema — importar materiales, administrar categorías, buscar, exportar, extraer de CD, propiedades de cada material.

#### 5.2.7. Creación de un Comando

> Los "Comandos" son instrucciones que le indican al sistema Dinesat
> Visual que debe realizar alguna acción. Los comandos que pueden ser
> insertados dentro de la programación de las ventanas de "Emisión de
> publicidad" o "Emisión musical". Existen comandos para emitir la
> Hora, Temperatura y Humedad, comandos para arrancar el sistema en
> modo automático o para modificarlo, comandos que seleccionan
> formatos musicales, etc.

**5.2.7.1 Creando un Comando**: Abrir Explorador → crear/usar una categoría del tipo "Comandos" → menú Archivo → Nuevo → Nuevo Comando → en el ítem "Material:" ingresar el nombre del comando (Ej: HORA).

**5.2.7.2. Creación de comandos FMT para formatos musicales** (⚠️ **distinto de HTH** — ver nota más abajo):

> También se pueden realizar comandos con los distinto formatos
> musicales existentes. De esta manera se podrá cambiar el estilo
> musical durante una programación automática.
> Ej: si se disponen de los siguientes formatos musicales ROCK, SALSA,
> TANGO. Se deberá crear un comando con el prefijo FMT. Por cada
> formato musical. Según el ejemplo anterior, cada comando debería ser
> `FMT ROCK`, `FMT SALSA`, `FMT TANGO`. Se debe tener en cuenta que
> SIEMPRE debe dejar un espacio entre el prefijo FMT y el nombre del
> formato existente. Y, por supuesto, NO se debe cometer ningún tipo
> de error ortográfico al escribir el nombre del formato.
>
> Nuevo comando `LOOP FMT NOMBRE_DEL_FORMATO`, éste comando funciona
> de la misma forma que los comandos FMT tradicionales pero con dos
> diferencias: (1) Establece un formato de video que funciona como una
> secuencia de segundo plano; (2) Se puede utilizar en cualquiera de
> las ventanas de aire, Aire 1 o Aire 2.

**5.2.7.3. Tabla de Comandos Dinesat Visual** (completa — la mayoría explícitamente fuera de alcance de esta app, remarcado abajo):

| Tipo de Comando | Detalle | Descripción |
|---|---|---|
| HTH HORA | TIME | Emite la hora actual en forma automática |
| HTH TEMPERATURA | TEMPERATURE | Emite la temperatura actual en forma automática |
| HTH HUMEDAD | HUMIDITY | Emite la humedad actual en forma automática |
| HTH TERMICA | TERMIC SENSATION | Emite la sensación térmica actual en forma automática |
| Emisión Automática | AUTO AIRE2 | Comienza la ejecución del modo automático Aire2 |
| Emisión Automática | AUTO AIRE2+FADE | Comienza la ejecución del modo automático Aire2 + Fade |
| Emisión Automática | AUTO AUX | Comienza la ejecución del modo automático Entrada Auxiliar |
| Emisión Automática | AUX FROM AUX | Comienza la ejecución del modo automático Entrada Auxiliar |
| Emisión Automática | AUX FROM LINE | Comienza la ejecución del modo automático Entrada por Línea |
| Emisión Automática | AUTO SAT+TONOS | *(satelital, descartado)* |
| Emisión Automática | AUTO SAT+RS232 | *(satelital, descartado)* |
| Emisión Automática | SUSPEND | Pasa al sistema al modo Automático Aire2 y luego suspende la emisión hasta el horario de la próxima tanda programada en Aire1 |
| Emisión Automática | **FMT xxxx** | **Selecciona el nuevo formato que seguirá la programación de Aire2 a partir de su ejecución** (xxxx = nombre del formato, en mayúsculas) |
| Emisión Automática | LOOP FMT xxxx | Formato en loop como secuencia de segundo plano de VIDEO — no aplica (app de solo audio) |
| Satelital | PLAY LOCAL / STOP LOCAL / SYNC / REC / PGM1 / PGM2 / FORCE SAT+RS232 / ROLLBACK AUTOMODE | *(todos satelitales, descartados)* |
| Consola | AEQ SWITCH OFF/1/2/3/4 | *(hardware de consola específico, no aplica)* |

> **Nota importante para este proyecto** (aclaración de Claude Code,
> no del manual): Santiago originalmente pidió esta función llamándola
> "FMT HORA" y "FMT CLIMA", pero según la tabla real de Dinesat el
> prefijo **`FMT`** es EXCLUSIVO de la selección de formato musical del
> Musicalizador Avanzado (ya implementado en esta app, ver roadmap
> ronda 28-30: `Comando FMT` → `iniciar_musicalizador()`). Los
> anuncios de hora/clima que Santiago describe son en realidad los
> comandos **`HTH`** (Hora/Temperatura/Humedad — la sigla completa es
> "HTH", ver secciones 5.3.5/5.3.5.1/5.3.5.2 más abajo), un tipo de
> comando SEPARADO del FMT. Falta confirmar con Santiago si esta
> distinción de nomenclatura le importa a la hora de nombrar la
> función nueva en esta app (¿la llamamos "Comando HTH" como Dinesat,
> o mantenemos su nombre informal "FMT HORA"/"FMT CLIMA" para no
> confundirlo respecto de lo que ya conoce?) — no se resolvió código
> todavía, queda para la ronda de preguntas.

#### 5.3.5 Clima (dentro de "5.3. Emisión")

> Dinesat Visual permite anunciar la hora, temperatura y la humedad de
> forma automática o manual. Si la emisora se encuentra en modo
> automático, sin operador, ni locutor, automáticamente puede
> programarse la emisión del HTH cuando el usuario lo desea y con los
> datos actualizados Hora, Temperatura y Humedad. De esta manera se
> percibe una sensación de la presencia de un locutor.
>
> Esta ventana toma los valores directamente de la central
> meteorológica configurada en algún puesto de trabajo de la Red. La
> actualización puede efectuarse también por medio de Internet.
>
> De forma manual se deberá presionar los botones de la ventana para
> poder emitir la hora, temperatura, humedad, sensación térmica.

**5.3.5.1. Como realizar los materiales de audio para Clima** (⭐ la sección clave — nomenclatura exacta de los archivos de voz):

> Todos los materiales de audio necesarios para el Clima deberán estar
> ubicados en una categoría de tipo **HTH**. En este caso el "Código"
> del material no es importante.
>
> En la solapa "HTH" de las propiedades del material, en la opción
> "Material:" se deberá ingresar la descripción de cada material de
> audio, el texto debe respetar la siguiente nomenclatura:
>
> - **Horas**: `HORA XX` (Ej.: `HORA 00`, `HORA 23`)
> - **Minutos**: `MINUTOS XX` (`MINUTOS 00`, `MINUTOS 59`)
> - **Grados**: `TEMPERATURA GRADOS XX` (Ej: `TEMPERATURA GRADOS 20`)
> - **Décimas**: `TEMPERATURA DECIMA XX` (Ej: `TEMPERATURA DECIMA 07`)
> - **Bajo cero**: `TEMPERATURA BAJO CERO` (Ej: `TEMPERATURA BAJO CERO 2`)
> - **Humedad**: `HUMEDAD XXX` (Ej: `HUMEDAD 045`)
>
> Cuando se requiera grabar un material que contenga el audio de las 3
> de la tarde se deberá ingresar: `HORA 15`

**5.3.5.2 Creación de los comandos HTH**:

> Estos comandos permiten automatizar la emisión de los datos del
> clima. Para ubicar los comandos para el HTH debe crear una categoría
> del tipo "Comandos". El código de los títulos no es importante. Sólo
> Hay que respetar la nomenclatura de los comandos como se indica:
>
> - El Comando Hora se llamará: `HORA`
> - El Comando Temperatura: `TEMPERATURA`
> - Y el Comando Humedad: `HUMEDAD`
>
> **Utilización de los comandos HTH**
> Para utilizar estos comandos simplemente se deberá abrir ventana
> "Explorador" seleccionar la categoría creada, del tipo Comandos, y
> se deberá elegir el comando deseado (HORA, TEMPERATURA o HUMEDAD)
> arrástrelo y suéltelo antes o después de cualquier audio dentro de
> las ventanas "Programación de Publicidad" o "Programación de
> Música". Si se desea utilizar sin realizar la programación
> correspondiente, se podrá arrastrar directamente a las ventanas de
> emisión.

⚠️ **Puntos que el manual NO aclara explícitamente** (quedan para
preguntarle a Santiago antes de programar — ver CLAUDE.md, sección de
FMT HORA/CLIMA pendiente):
- No hay una descripción textual de un material "intro" separado tipo
  "es la hora..." — es posible que ese audio exista simplemente como
  OTRO material más dentro de la misma categoría HTH, reproducido
  SIEMPRE antes que `HORA XX`/`MINUTOS XX` (el orden de concatenación
  no está descripto en el manual, ni cómo el motor sabe cuál
  reproducir primero — probablemente sea un orden fijo hardcodeado en
  el motor real de Dinesat: intro fijo → HORA XX → MINUTOS XX).
- La tabla de comandos solo documenta 3 comandos creables (HORA,
  TEMPERATURA, HUMEDAD) — no queda claro si un solo comando `HORA`
  dispara SOLO el anuncio de hora, o si existe algún comando combinado
  "clima completo" (temperatura + humedad + térmica en una sola
  tanda). Por la sección 5.3.5.2 parecen ser 3 comandos INDEPENDIENTES
  (cada uno se arrastra por separado a la programación).
- No se documenta si "TEMPERATURA BAJO CERO" reemplaza a
  "TEMPERATURA GRADOS" cuando la temperatura es negativa, o si se
  concatena ANTES de "TEMPERATURA GRADOS" (ej.: "bajo cero" + "dos"
  grados = "-2°"). El ejemplo `TEMPERATURA BAJO CERO 2` sugiere que es
  un material único por cada valor negativo (no una concatenación de
  dos clips), pero no está confirmado.
- Rango completo de temperatura, TOP horario (cada 30 min, "TOP 00"/
  "TOP 30" — mencionado en 4.3.1.3 pero no desarrollado en detalle en
  ninguna otra sección de este manual).

#### 5.3.1 — 5.3.4, 5.3.6. Otras ventanas de Emisión

- **5.3.1. Emisión de Publicidad**: pauta comercial completa, programable desde "Programación de publicidad". Botones: PGM/CUE, Anunciar (atenúa nivel), Reproducir y detener, Modo automático. Menú Archivo: Nueva Programación, Cargar Programación (con calendario), Nuevo/Editar/Duplicar Bloque, Desprogramar Material/erróneos, Propiedades.
- **5.3.2. Emisión de Música**: pauta musical o programa grabado en bloques, programable desde "Programación de música".
- **5.3.3. Emisión Auxiliar**: se comporta igual que cualquier ventana de emisión, pero al cerrarla se pierde el contenido (no se programa) — se permite abrir la cantidad de ventanas que se requieran. **Esta es la referencia directa de diseño de la Ventana Auxiliar de esta app** (ver CLAUDE.md roadmap ronda 38).
- **5.3.4. Asistente en vivo**: botonera de 25 botones por página (soundboard), privadas o grupales — **declinado por Santiago** (pausado, ver roadmap ronda 26).
- **5.3.6. Voz Superpuesta**: micrófono con atenuación automática del resto de las ventanas al presionar el botón — asiste al locutor sin consola de audio propia.

### 5.4. Edición — 5.4.1. Editor de Audio

Ediciones simples, marcas de Punch in/out, Mark in/out, Intro/Outro — ya replicado conceptualmente en `core/analizador_audio.py` de esta app (recorte de silencio + nivelado), aunque sin editor visual propio.

### 5.5. Programación

#### 5.5.1. Programación de Publicidad / 5.5.1.1 Crear un Bloque

Bloques horarios con descripción y "Hora de PGM"; se arrastran materiales desde el Explorador. Análogo directo a Ventana 1 de esta app.

#### 5.5.1.2 — 5.5.1.4. Importar programación (formatos TXT/CSV)

Formato de intercambio con software de tráfico externo — **no implementado en esta app** (no se pidió), documentado acá por completitud.

#### 5.5.2. Programación de Música / 5.5.2.1 Programando una pauta musical

> Dinesat Visual permite la generación de programaciones aleatorias,
> que facilitan la dificultosa tarea de programar música para su
> emisora. Dichas programaciones aleatorias, son realizadas por el
> "Musicalizador Avanzado", conforme a los "Formatos" creados y
> asignados para el día.

#### 5.5.2.2. Musicalizador Avanzado / 5.5.2.3. Crear un formato de musicalización

Ya implementado en esta app (roadmap ronda 28-31) con 3 tipos de ítem — comparación contra el original de Dinesat:

| Dinesat Visual | Esta app (`core/musicalizador.py`) |
|---|---|
| **Material Aleatorio**: categoría + criterios (Prioridad, Género, Ritmo, Artista, rango de años), "Permitir repetir cada XX Minutos" por artista, "Permitir repetir prioridad Alta/Media/Baja cada XX Minutos" | Tipo `aleatorio`: categoría + recursivo + no-repetir vía historial persistente (más simple, sin prioridad/ritmo/año — no implementado, ver abajo) |
| **Material específico**: un material fijo dentro del formato | Tipo `especifico` |
| **Subformato**: otro formato ya creado + duración | Tipo `subformato` |
| **Emisión** (por ítem): "No pisar" / "Pisar material musical con [categoría]" / "Anunciar material musical con [categoría de tipo Anuncio]" | Pisador Intro/Outro por categoría O archivo específico (sin el concepto separado de "Anuncio", ver roadmap 26 — Santiago pidió encarar Anuncio junto con el Musicalizador, con matices propios) |

**Criterios de descarte NO implementados en esta app todavía** (candidatos a pedir si Santiago los necesita): Orden, Prioridad, Ritmo, Género por ítem, "Permitir repetir cada XX Minutos" por ARTISTA (esta app solo evita repetir el mismo ARCHIVO, no el mismo artista), límites de repetición por prioridad de material.

#### 5.5.3. Grabar ANUNCIOS para canciones / 5.5.4. Identificación (Cuña) sobre INTRO/OUTRO

Concepto de "Anuncio" — cuña que se reproduce sobre la marca INTRO/OUTRO de un tema, ligada a un código de material específico o asignada por categoría en el Musicalizador. Distinto del "Pisador" de esta app (que es un archivo de género completo, no necesariamente ligado a UN tema específico) — Santiago pidió encarar esto explícitamente junto con una futura revisión del Musicalizador (ver roadmap ronda 26), todavía no implementado.

> Se deberá tener en cuenta que el anuncio finalizará 2 segundos antes
> de que termine el tiempo de INTRO/OUTRO, esto evitara que el
> intérprete comience a cantar sobre el anuncio. Se deberá evitar que
> el anuncio sea MAS largo que el INTRO/OUTRO de la canción. Si esto
> sucediese el anuncio no se reproduciría.

### 5.6. Más

Grabador Continuo, Contestador Telefónico SIP, Importador de programaciones/materiales, Switcher de video, Monitor de video — **todos explícitamente fuera de alcance** de esta app (ver CLAUDE.md, roadmap ronda 26: Grabador Continuo pausado hasta que Santiago conecte la consola por USB; el resto ni se planteó).

### 5.7. Cambio de usuario / 5.7.1. Bloqueo de la Terminal

Sistema multiusuario con login/bloqueo de terminal — **no aplica**, esta app es de un solo operador sin sistema de usuarios.

## 6. Soporte Técnico

*(Soporte comercial de Hardata — no aplica.)*

## 7. Apéndice

### 7.1. Ventanas de uso más frecuente

> Emisión de Publicidad, Emisión auxiliar 1, Emisión de música,
> Explorador, Asistente en vivo, Emisión Auxiliar 2 — las ventanas
> Emisión Auxiliar, Explorador y asistente en vivo se permiten abrir
> la cantidad deseada, cada una con dispositivo de reproducción
> independiente.

### 7.2. — 7.5. Hardware homologado / Instalación / Recomendaciones de Hardware / Redes de datos

*(Tarjetas de sonido AudioScience/Digigram/Sound Blaster, tarjetas seriales RS-232 Moxa, tarjetas telefónicas TAPI, central meteorológica Davis Weather Wizard, recomendaciones de UPS/tierra/cableado UTP Cat 5e — hardware específico de instalaciones profesionales grandes, no aplica al hardware modesto de Santiago; la central meteorológica Davis fue reemplazada en esta app por una consulta a Open-Meteo vía internet, más simple y sin hardware dedicado.)*
