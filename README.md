# RadioLinuxMadariaga

> 🚧 **PROYECTO EN DESARROLLO.** Uso en producción bajo tu propio
> riesgo — puede haber cambios frecuentes y funciones incompletas.
>
> **Última actualización:** 2026-07-26

Automatización radial para Linux (clon funcional de Dinesat 9), en
Python + PySide6 + VLC. Publicidad, música y explorador de medios,
con motor de reproducción real, análisis de audio y programación
horaria.

Repositorio: https://github.com/ElSelloTV/RadioLinuxMadariaga

## Instalación (primera vez)

```bash
curl -fsSL https://raw.githubusercontent.com/ElSelloTV/RadioLinuxMadariaga/main/instalar.sh | bash
```

Esto clona el repo en `~/RadioLinuxMadariaga`, crea el entorno
virtual, instala las dependencias de Python y deja el ícono de
escritorio listo.

Dependencias del sistema (aparte, una sola vez):

```bash
sudo apt install vlc libvlc-dev ffmpeg
```

Opcional — si querés procesar el aire de la FM (compresor,
ecualizador, limitador, etc.), instalá y configurá vos mismo
EasyEffects (o el procesador que prefieras) por fuera de esta app —
no hay ninguna integración ni control desde el programa, es 100%
independiente:

```bash
sudo apt install easyeffects
```

Alternativa más liviana a EasyEffects: `extras/procesador_fm_viper4linux/`
trae un instalador aparte para Viper4Linux (motor + GUI opcional,
compilado desde fuente vendorizada en este repo). Menos funciones que
EasyEffects, pero ocupa muchísimo menos — ver ese README para
comparación de recursos, y para alternativas todavía más completas
(y pesadas) como JDSP4Linux/JamesDSP. Tampoco tiene ninguna
integración con esta app.

Esta app sí nivela el volumen de cada tema al importarlo (para que no
haya diferencia de volumen entre canción y canción), sin depender de
EasyEffects ni de ningún procesador externo — ver
`core/analizador_audio.py`.

## Actualizar

Dos formas, cualquiera de las dos hace lo mismo (`git pull`):

- Desde la app: **Herramientas → Preferencias generales... →
  pestaña "Actualizaciones" → Buscar actualización → Actualizar y
  reiniciar**. Descarga los cambios y reinicia la app sola.
- Desde la terminal:
  ```bash
  cd ~/RadioLinuxMadariaga && ./instalar.sh
  ```

## Ejecutar manualmente

```bash
cd ~/RadioLinuxMadariaga
source venv/bin/activate
python3 main.py
```

## Estructura del proyecto

```
RadioLinuxMadariaga/
├── main.py              # punto de entrada
├── instalar.sh           # instalación/actualización automática
├── gui/                  # interfaz (PySide6) — sin lógica de audio
├── core/                 # motor de audio, playlists, análisis, actualizador
├── config/                # configuración y persistencia (JSON)
└── assets/                # ícono y lanzador de escritorio
```

## Desarrollo con Claude Code

Este repo está pensado para trabajarse con [Claude
Code](https://docs.claude.com) apuntando directamente a
`~/RadioLinuxMadariaga`: editá, corré y probá los cambios ahí mismo,
y hacé `git commit` / `git push` cuando quede lo que buscabas. Así
las actualizaciones quedan disponibles al toque para cualquier
instalación (incluida la tuya, vía el botón "Actualizar").
