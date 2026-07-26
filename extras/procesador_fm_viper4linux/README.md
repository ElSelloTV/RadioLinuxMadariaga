# Procesador de audio FM — Viper4Linux (opcional)

Esto **no es parte de RadioLinuxMadariaga**. La app es 100%
independiente del procesamiento de audio de la salida FM (ver
sección "Instalación" del README principal) — esta carpeta es solo
un instalador aparte, para quien quiera procesar el aire
(compresor/limitador/realce) y prefiera algo liviano.

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
./instalar_procesador_fm.sh          # solo el motor (CLI: viper start/stop/restart/status)
./instalar_procesador_fm.sh --gui    # motor + interfaz gráfica (viper-gui)
```

Solo x86_64 (la librería core es un binario propietario sin fuente,
compilado solo para esa arquitectura) y solo distros basadas en
Debian/Ubuntu (usa `apt`).

## Alternativas, si esto no te alcanza

Viper4Linux es liviano pero básico. Si necesitás más (convolver,
AutoEQ, motor de scripting de efectos), las alternativas más
completas son bastante más pesadas en recursos:

| | Viper4Linux (motor) | EasyEffects | JDSP4Linux / JamesDSP |
|---|---|---|---|
| RAM en uso | ~18 MB | variable según cadena | ~110 MB+ (Qt6/QML) |
| Instalación | compilar a mano (~1 MB instalado) | `apt install easyeffects` | Flatpak, ~1,7 GB de runtimes (KDE Platform, Mesa, etc.) |
| Integración PipeWire | filter nativo vía GStreamer | nativa | nativa |
| Funciones | compresor/limitador/AGC básicos, sin EQ | LADSPA/LV2 completo, EQ, muchos plugins | Convolver, AutoEQ, scripting, más completo |

Instalación de las alternativas (por fuera de este script, cada una
con su propio instalador):

```bash
sudo apt install easyeffects
# o
flatpak install flathub me.timschneeberger.jdsp4linux
```

## Uso

```bash
viper start      # arranca el procesamiento
viper restart     # obligatorio después de cambiar cualquier parámetro
viper stop
viper status
```

Configuración en `~/.config/viper4linux/audio.conf` (a mano o con
`viper-gui` si se instaló con `--gui`). El motor arranca como un
único proceso `gst-launch-1.0` con los parámetros fijos al iniciar —
por eso hace falta `viper restart` después de cada cambio, no relee
el archivo en caliente.
