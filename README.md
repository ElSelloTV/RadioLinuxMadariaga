# RadioLinuxMadariaga

> 🚧 **PROYECTO EN DESARROLLO.** Uso en producción bajo tu propio
> riesgo — puede haber cambios frecuentes y funciones incompletas.
>
> **Última actualización:** 2026-07-16

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
ecualizador, limitador, etc.) desde el ícono "🎚 FM" del toolbar:

```bash
sudo apt install easyeffects
```

Sin EasyEffects instalado, ese botón simplemente avisa que no está
disponible — el resto de la app funciona igual.

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
