# Procesador de audio FM — Viper4Linux (opcional)

Esto **no es parte de RadioLinuxMadariaga**. La app es 100%
independiente del procesamiento de audio de la salida FM (ver
sección "Instalación" del README principal) — esta carpeta es solo
un instalador aparte, para quien quiera procesar el aire
(compresor/limitador/EQ/realce) y prefiera algo liviano.

## Por qué está acá

[Viper4Linux](https://github.com/Audio4Linux/Viper4Linux) +
[su GUI](https://github.com/Audio4Linux/Viper4Linux-GUI) no tienen
paquete para Debian/Ubuntu — hay que compilarlos a mano. El código
fuente de ambos (y sus dependencias, `gst-plugin-viperfx` y la
librería propietaria `viperfx_core_binary`) está vendorizado en
`vendor/` para que esto siga funcionando aunque el autor original
borre esos repos de GitHub el día de mañana.

## Instalación

```bash
cd extras/procesador_fm_viper4linux
./instalar_procesador_fm.sh                # solo el motor (CLI: viper start/stop/restart/status)
./instalar_procesador_fm.sh --gui          # + interfaz gráfica (viper-gui)
./instalar_procesador_fm.sh --systemd      # + queda corriendo SOLO con prender la PC
```

Los tres flags se pueden combinar (ej. `--gui --systemd`, lo
recomendado para dejarlo andando de forma permanente y poder
retocarlo con una interfaz gráfica de vez en cuando).

Solo x86_64 (la librería core es un binario propietario sin fuente,
compilado solo para esa arquitectura) y solo distros basadas en
Debian/Ubuntu (usa `apt`).

## Cómo lo toma esta app — nada que armar a mano

`viper start` (el propio script de Viper4Linux) crea SOLO un sink
virtual de PipeWire llamado **`viper`**, migra el audio que esté
sonando hacia ahí, y arranca su propio pipeline de procesamiento que
lee de `viper.monitor` y escribe a la salida real — **no hace falta
crear ningún sink a mano con `pactl` ni nada parecido**, eso lo
resuelve el propio comando `viper start` de punta a punta.

En RadioLinuxMadariaga, alcanza con: **Configuración → Audio →
Viper4Linux (procesador externo, opcional)** → tildar "Activado" y
dejar el sink en `viper` (el valor de fábrica, ya precargado — el
nombre fijo que usa el instalador). Con eso, la app manda TODO el
audio del aire (Publicidad, Emisión, Auxiliar, Pisador, HORA/TEMP)
a ese sink — la Preescucha (▶ Previo del Explorador y de los
Programadores) queda deliberadamente afuera, sigue saliendo directo
por los parlantes de monitoreo de la PC, sin procesar.

Con `--systemd` (recomendado, ver más abajo) ni siquiera hace falta
correr `viper start` — ya queda corriendo antes de que la radio
misma arranque.

### Dispositivo de salida fijo (recomendado)

Por defecto, `viper start` apunta la salida procesada a lo que sea
que el sistema reporte como "sink por defecto" en el momento exacto
en que arranca — funciona, pero es un poco frágil (puede cambiar si
se conecta/desconecta otro dispositivo de audio antes de arrancar).
Para fijarlo siempre al MISMO dispositivo real, sin ambigüedad, se
puede crear `~/.config/viper4linux/devices.conf` con una línea:

```
desc="Consola Silicon (USB)" location=alsa_output.usb-MV-SILICON_MVSilicon_USB_Audio_20190808-00.analog-stereo
```

(el nombre exacto de `location=` sale de `pactl list sinks short`).
Si esta carpeta trae un archivo `devices.conf.santiago` con el
dispositivo ya confirmado, el instalador lo copia solo la primera
vez (sin pisar uno que ya exista).

## Arrancar solo con la PC (`--systemd`)

`./instalar_procesador_fm.sh --systemd` instala un servicio
`systemd --user` (`viper4linux.service`) que corre `viper start`
apenas arranca la sesión, y `viper stop` al cerrarla — así Viper4Linux
queda procesando el aire siempre, sin que haga falta acordarse de
correr ningún comando después de cada reinicio de la PC. El
instalador también activa `loginctl enable-linger` para ese usuario,
así el servicio arranca junto con el sistema operativo, incluso antes
de iniciar sesión gráfica (necesita `sudo` para ese paso puntual —
es lo único de esta instalación que lo pide).

Comandos útiles con systemd instalado:

```bash
systemctl --user status viper4linux    # ¿está corriendo?
systemctl --user restart viper4linux   # aplicar un cambio de audio.conf
systemctl --user stop viper4linux      # apagarlo (no arranca de nuevo hasta el próximo boot)
```

Sin `--systemd`, se maneja a mano con `viper start`/`stop`/`restart`
(ver más abajo) — pero hay que acordarse de correrlo después de cada
reinicio de la PC.

## Qué incluye Viper4Linux

Más completo de lo que parece a primera vista — el motor real
(`audio.conf`) trae: **ecualizador de 10 bandas**, exciter de
armónicos (realce de brillo/agudos — lo más parecido a lo que suele
llamarse "brillo" en consolas de radio), AGC (nivelador automático de
volumen, para que un tema grabado más bajito no se sienta más flojo
que otro), compresor tipo FET (el mismo concepto que un compresor de
broadcast — threshold/ratio/attack/release), limitador (evita
saturación en los picos), ensanchado estéreo, realce de graves
("virtual bass"), claridad de voz, y reverb — todo editable en
`~/.config/viper4linux/audio.conf` (a mano, ver el `.template` en
`vendor/Viper4Linux/viper4linux/` para la lista completa de
parámetros) o con `viper-gui` si se instaló con `--gui`.

## Alternativas, si esto no te alcanza

Si necesitás más (convolver, AutoEQ, motor de scripting de efectos),
las alternativas más completas son bastante más pesadas en recursos:

| | Viper4Linux (motor) | EasyEffects | JDSP4Linux / JamesDSP |
|---|---|---|---|
| RAM en uso | ~18 MB | variable según cadena | ~110 MB+ (Qt6/QML) |
| Instalación | compilar a mano (~1 MB instalado) | `apt install easyeffects` | Flatpak, ~1,7 GB de runtimes (KDE Platform, Mesa, etc.) |
| Integración PipeWire | filter nativo vía GStreamer | nativa | nativa |
| Funciones | EQ 10 bandas, exciter, AGC, compresor FET, limitador, virtual bass, realce estéreo | LADSPA/LV2 completo, EQ, muchos plugins | Convolver, AutoEQ, scripting, más completo |

Instalación de las alternativas (por fuera de este script, cada una
con su propio instalador):

```bash
sudo apt install easyeffects
# o
flatpak install flathub me.timschneeberger.jdsp4linux
```

## Uso manual (sin `--systemd`)

```bash
viper start      # arranca el procesamiento
viper restart     # obligatorio después de cambiar cualquier parámetro
viper stop
viper status
```

El motor arranca como un único proceso `gst-launch-1.0` con los
parámetros fijos al iniciar — por eso hace falta `viper restart`
(o `systemctl --user restart viper4linux` con `--systemd`) después
de cada cambio, nunca relee el archivo en caliente.
