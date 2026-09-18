# Bitácora de ajustes de audio — PC de aire (radio-tuyu)

Registro de lo que se cambió el 2026-09-18, por qué, y cómo revertir CADA
parte por separado si hace falta. Todo lo de acá es config del SISTEMA
OPERATIVO/Viper4Linux — nada de esto toca el código Python de esta app.

## El incidente real de hoy

Al activar el enrutado a Viper4Linux desde Configuración → Audio, el aire
se puso "robótico" y terminó en silencio total. Investigado en vivo con
Santiago, en la PC real, con dos causas reales encontradas y corregidas
por separado:

### Causa 1 — PipeWire cambiaba de frecuencia del grafo sobre la marcha

Sin fijar una frecuencia, PipeWire puede cambiar la frecuencia de reloj
de TODO el grafo de audio cuando un stream nuevo se conecta con una
frecuencia nativa distinta a la que el grafo ya está usando — eso se
escucha como un glitch/sonido raro en el instante del cambio, afectando
incluso lo que ya estaba sonando bien.

**Fix aplicado**: `~/.config/pipewire/pipewire.conf.d/99-radio-samplerate.conf`
```
context.properties = {
    default.clock.rate          = 48000
    default.clock.allowed-rates = [ 48000 ]
}
```
Se eligió 48000Hz porque tanto Silicon (la consola USB) como el null-sink
de Viper ya negociaban nativamente a esa frecuencia.

**Para revertir esto**:
```bash
rm ~/.config/pipewire/pipewire.conf.d/99-radio-samplerate.conf
systemctl --user restart pipewire pipewire-pulse wireplumber
```
Ojo: esto corta el audio un instante (todo lo que esté sonando en la PC,
no solo la radio) — hacerlo en un hueco tranquilo, nunca en medio de algo
al aire.

### Causa 2 — el compresor FET de Viper (`fetcomp`) se rompe, con parámetros técnicamente VÁLIDOS

Verificado contra el código fuente real del plugin
(`vendor/gst-plugin-viperfx/src/gstviperfx.c`): TODOS los valores que
tenía el preset de Santiago para `fetcomp_*` estaban dentro del rango
declarado por el propio plugin (0-100, "percent") — incluido
`fetcomp_ratio=0`, que resultó ser literalmente el valor de fábrica por
defecto del módulo, no un número inválido como se sospechó al principio.

Es decir: **no es un problema de un número mal puesto** — es una
inestabilidad real del módulo compresor de esta build/versión de
Viper4Linux, cuya lógica interna vive en una librería compilada aparte
(referenciada acá como `PARAM_HPFX_FETCOMP_*`), fuera del alcance de lo
que se puede auditar desde este código fuente. No se pudo confirmar la
causa exacta a nivel de código.

**Decisión tomada, explicada a Santiago**: dado que la prioridad explícita
es "que no suceda el silencio nunca más", y que `fetcomp_enable=false` es
el ÚNICO estado que quedó probado estable en varias rondas de prueba real
(incluso después de arreglar la frecuencia), se deja el compresor FET
APAGADO por ahora — el brillo/nivelado que pidió se logra con el EQ y el
limitador (ver abajo), módulos mucho más simples y sin ningún fallo
observado en las pruebas de hoy.

**Si en algún momento se quiere reintentar el compresor FET**: hacerlo en
una sesión de pruebas dedicada, fuera del aire, escuchando varios minutos
seguidos con distintos temas antes de confiar en que quedó estable — el
bug pudo no depender de los valores en sí, sino de algo más (duración de
la reproducción, algún estado interno acumulado, etc.) que no se llegó a
aislar del todo.

## Ajustes nuevos aplicados hoy (pedido explícito: "quiero brillo y
nivelador de salida... sonido de radio moderna")

Archivo: `~/.config/viper4linux/audio.conf`. Backup guardado ANTES de
tocar nada en `~/.config/viper4linux/audio.conf.backup-2026-09-18` (con
el compresor ya apagado, pero SIN el EQ ni el limitador nuevos — ese es
el punto exacto al que revertir si algo de esto da problema).

**EQ activado** (`eq_enable=true`), curva suave tipo "sonrisa" — valores
verificados contra el rango real del plugin (-1200 a +1200, equivalente
a ±12dB por banda; todo lo usado hoy queda muy por debajo del techo):

| Banda | Valor | ~dB  | Rol |
|-------|-------|------|-----|
| 1     | 150   | +1.5 | graves — un poco de cuerpo/punch |
| 2     | 100   | +1.0 | graves |
| 3     | 0     | 0    | sin tocar |
| 4     | -50   | -0.5 | mids bajos — leve recorte para claridad |
| 5     | -50   | -0.5 | mids — leve recorte, cuida la voz |
| 6     | 0     | 0    | sin tocar |
| 7     | 150   | +1.5 | presencia |
| 8     | 250   | +2.5 | brillo |
| 9     | 250   | +2.5 | brillo/aire |
| 10    | 200   | +2.0 | aire/sparkle, un poco menos que 8-9 para no ensuciar |

**Limitador de salida** (`lim_threshold`): de `100` (prácticamente
inerte, solo protegía contra saturación total) a `88` — ahora actúa como
un nivelador real, agarrando picos con margen antes del techo absoluto,
sin ser agresivo.

**AGC**: sin cambios — ya estaba dentro de rango válido
(`agc_ratio=126`, `agc_volume=143`, `agc_maxgain=444`, todos dentro de
sus rangos reales) y fue la única parte de la cadena que nunca falló en
ninguna prueba de hoy. Sigue siendo el "nivelador" principal.

**Para revertir SOLO estos ajustes nuevos** (volver al estado de recién
después de apagar el compresor, sin EQ ni limitador nuevo):
```bash
cp ~/.config/viper4linux/audio.conf.backup-2026-09-18 ~/.config/viper4linux/audio.conf
viper stop && viper start   # o: systemctl --user restart viper4linux.service, si ya está con systemd
```

## Arranque automático (systemd)

Antes había que correr `viper start` a mano cada vez que se prendía la
PC. Ahora arranca solo, vía `~/.config/systemd/user/viper4linux.service`
(copiado desde `extras/procesador_fm_viper4linux/viper4linux.service` de
este mismo repo), habilitado con:
```bash
systemctl --user enable --now viper4linux.service
sudo loginctl enable-linger radio
```

**Para revertir esto** (volver a arrancarlo a mano):
```bash
systemctl --user disable --now viper4linux.service
rm ~/.config/systemd/user/viper4linux.service
systemctl --user daemon-reload
sudo loginctl disable-linger radio   # opcional, solo si no se quiere más lingering
```
Después de esto, hay que volver a correr `viper start` a mano en cada
arranque, como se hacía antes de hoy.

## Botones nuevos en Configuración → Audio (pedido explícito, "sin
tanto trabajo")

Después de reactivar el compresor, Santiago pidió una forma de comparar
con/sin efectos en caliente y de llegar rápido a los controles reales
de Viper, SIN reconstruir un panel de sliders adentro del programa de
radio (ese camino ya se descartó varias veces en este proyecto — ver
rondas 37-55 y 69-78 de CLAUDE.md). Alcance deliberadamente chico,
`core/viper4linux_control.py`:

- **"🎛 Abrir editor de Viper4Linux..."** — lanza `viper-gui` (la
  interfaz nativa, se instala con `./instalar_procesador_fm.sh --gui`).
  Ahí viven los controles reales — EQ, compresor, limitador, AGC,
  presets — hechos por los propios desarrolladores de Viper.
- **"🔇 Alternar bypass (con/sin efectos)"** — prende/apaga TODA la
  cadena de Viper en caliente, sin reiniciar el servicio ni tocar
  `audio.conf`, vía la interfaz D-Bus real que el propio plugin expone
  (confirmada en el código fuente vendorizado,
  `vendor/gst-plugin-viperfx/src/dbus-interface.c`: bus de sesión,
  `me.noahbliss.ViperFx`, propiedad `fx_enable`).

Ninguno de los dos botones escribe ningún valor de DSP desde Python —
el primero abre una herramienta externa, el segundo solo prende/apaga
el interruptor global que el plugin ya expone.

## Prueba pendiente — ¿alcanza `module-stream-restore` solo, sin el
enrutador de la app? (para la noche, con la radio cortada)

Santiago sigue con dudas sobre la robustez del enrutado propio de esta
app (`core/audio_engine.py:EnrutadorPactl`) y quiere ver si PipeWire ya
resuelve esto solo, por su cuenta — confirmado que
`module-stream-restore` (memoria de a qué sink va cada app, ya activo
en este PipeWire/pipewire-pulse, visto en un `pactl list sink-inputs`
real de hoy: `module-stream-restore.id = "sink-input-by-application-
name:gst-launch-1.0"`) es un mecanismo REAL del sistema operativo para
esto, no algo para instalar.

**Descartados, con evidencia concreta, dos atajos que Santiago propuso
antes de esta prueba** (ver el resto de la conversación de hoy para el
detalle completo):
- Apagar el enrutador propio + Device de Viper en "Automático": el
  propio script `viper` (`vendor/Viper4Linux/viper`) se choca consigo
  mismo al reiniciarse en ese modo ("Something is very wrong (Target
  is same as our vipersink name)") — confirmado en el código fuente.
  Device de Viper QUEDA FIJO EN SILICON, no tocar esto nunca.
- Apagar el enrutador propio + Device de Viper fijo en Silicon: sin
  enrutador, el audio de la radio va directo a Silicon, sin pasar por
  Viper para nada — cero procesamiento, no es una alternativa real.

**El test real, para esta noche** — objetivo: ver si PipeWire, por su
cuenta, mantiene el audio de la radio yendo a `viper` sin que
`EnrutadorPactl` tenga que intervenir. Importante: esto NO reemplaza el
enrutador propio si funciona -- se deja como capa ADICIONAL de
resguardo, nunca como sustituto (mismo criterio de "nunca una sola
protección" de todo hoy).

**0. Chequeo de seguridad ANTES de tocar nada** (pregunta real de
Santiago, confirmada en el código): la Preescucha
(`audio["dispositivo_preescucha"]`, `gui/main_window.py` líneas
914/1611) resuelve su dispositivo COMPLETAMENTE APARTE de
`dispositivo_master_efectivo()` -- cambiar "Salida Master" nunca la
toca. El ÚNICO riesgo real sería que "Salida Preescucha" estuviera
configurada como "Predeterminada del sistema" -- ahí SÍ podría caer en
Viper junto con todo lo demás, ya que Viper se declara a sí mismo
"default" del sistema al arrancar. Confirmado con el log real de hoy
que esto está bien (`audio_output_device_set(None, 'alsa_output.pci-
0000_00_14.2.analog-stereo')`, dispositivo explícito, los parlantes
internos) -- pero de todas formas, antes de arrancar la prueba: ir a
Configuración → Audio → "Salida Preescucha" y confirmar a ojo que
sigue diciendo el dispositivo específico, NO "Predeterminada del
sistema".

1. Con la config actual (toggle de Viper activo, Salida Master =
   Silicon explícito), confirmar que suena bien por `viper` como
   siempre (línea base).
2. En Configuración → Audio: cambiar **"Salida Master"** (el campo de
   arriba, NO el de Viper4Linux) a **"Predeterminada del sistema"** —
   Y **destildar** el checkbox de Viper4Linux. Guardar. (Con esto el
   programa deja de pedir CUALQUIER dispositivo explícito -- condición
   necesaria para que la memoria de PipeWire tenga alguna chance de
   actuar; apagar solo el toggle, sin este cambio, siempre vuelve a
   Silicon directo sin darle a stream-restore ninguna oportunidad.)
3. Forzar un tema nuevo (Cut) y revisar:
   ```bash
   pactl list sink-inputs short
   ```
   ¿Cae solo en `viper`, o en Silicon directo?
4. Si cae en Silicon: "enseñarle" la asociación a mano una vez —
   ```bash
   pactl list sink-inputs short   # anotar el id del stream de la radio
   pactl move-sink-input <ID> viper
   ```
   — y RECIÉN AHÍ forzar OTRO tema nuevo (Cut). ¿El siguiente stream ya
   cae solo en `viper`, sin repetir el `move-sink-input` a mano?
5. **El test decisivo**: cerrar y volver a abrir el programa de radio
   completo (no solo un tema nuevo) — ¿la memoria sobrevive un
   reinicio del proceso? Es la única forma de confiar en esto de
   verdad para el uso real.
6. **Si funciona confiable** (sobrevive el punto 5): se puede dejar
   "Salida Master = Predeterminada del sistema" + toggle de Viper
   apagado como config final, con PipeWire haciendo el enrutado solo
   — pero el Device de Viper SIGUE fijo en Silicon siempre (nunca
   Automático, por el bug ya confirmado).
7. **Si NO funciona confiable** (no sobrevive el reinicio, o cae en
   Silicon sin procesar en algún momento): volver a la config de
   siempre (toggle de Viper activo, Salida Master = Silicon explícito)
   — ya sabremos que lo intentamos con evidencia real, sin dejarlo
   como duda abierta.

## Lo que NO se tocó hoy

- **Crossfade** (Fade In/Out de Ventana 2, Configuración → Fade/
  Transiciones) — pedido explícito de Santiago de no activarlo todavía,
  hasta confirmar que Viper4Linux quedó estable un buen rato. Sigue en
  40ms/80ms.
- El enrutado del programa a Viper (checkbox de Configuración → Audio,
  `dispositivo_master_efectivo()` en `config/settings.py`) — sin cambios
  de código en esta ronda, todo lo de hoy fue configuración externa
  (PipeWire, Viper4Linux), no del programa de radio en sí.
