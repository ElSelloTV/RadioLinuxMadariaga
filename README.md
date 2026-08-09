# RadioLinuxMadariaga

> 🚧 **PROYECTO EN DESARROLLO.** Uso en producción bajo tu propio
> riesgo — puede haber cambios frecuentes y funciones incompletas.
>
> **Última actualización:** 2026-08-09

Automatización radial para Linux (simil Dinesat), en
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
RECOMENDADO:
Testeado y probado en Debian, sistema ultra-liviano con Sistema Operativo Q4SO,
a mi gusto la mejor distribución para PC casi nulo uso de recursos y absolutamente personalizable.

PROCESADOR:
Opcional — si querés procesar el aire de la FM (compresor,
ecualizador, limitador, etc.), instalá y configurá vos mismo
EasyEffects (o el procesador que prefieras) por fuera de esta app —
no hay ninguna integración ni control desde el programa, es 100%
independiente:

```bash
sudo apt install easyeffects
```
ALTERNATIVA RECOMENDADA: 
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

COMO UTILIZAR Y GRABAR PARA LA HORA Y CLIMA AUTOMÁTICO:

Cómo grabar y nombrar los clips
Se importan como cualquier archivo en Ventana 3 (Explorador), con género "HTH" — no es una categoría especial, es un género más del combo, buscable en cualquier categoría/subcategoría donde los archives. El título que le pongas al importar tiene que ser EXACTO (se compara normalizado a mayúsculas, así que da igual "Hora 14" o "HORA 14", pero el texto en sí tiene que coincidir):

Ya no hace falta grabar "INTRO HORA" — (Los clips de HORA XX ya traen la frase completa grabada, "es la hora catorce", así que el comando HORA concatena directo HORA XX + MINUTOS XX, nada más).

Cómo funciona cada comando al reproducirse
Son 3 comandos independientes — los insertás por separado en un bloque de Ventana 1 (o del Programador):

HORA: toma la hora real del sistema en el momento en que le toca sonar, y concatena HORA {hora} + MINUTOS {minuto}.

TEMPERATURA: redondeada a grados enteros (nunca decimales). Si es positiva/cero, un solo clip TEMPERATURA GRADOS XX. Si es negativa, concatena TEMPERATURA BAJO CERO + TEMPERATURA GRADOS {valor absoluto} — o sea, no hace falta grabar un clip por cada valor bajo cero, reutiliza el mismo de siempre.

HUMEDAD: un solo clip HUMEDAD XXX (3 dígitos, con cero a la izquierda si hace falta).

Regla de oro: todo o nada. Si falta CUALQUIER clip necesario (por ejemplo no grabaste HORA 03 todavía), o si no se pudo obtener el dato de clima, el comando se saltea completo, sin sonar nada — nunca un anuncio a medias o incoherente.

De dónde sale el dato de clima

Fuente: Open-Meteo, con las coordenadas que configures en Configuración → General (latitud-longitud). Desde la ronda del "breve silencio al leer el clima", esto se resuelve en segundo plano: la app consulta la API cada 15 minutos por su cuenta (más una vez al abrir) y guarda el resultado en una caché válida por 20 minutos — cuando el Comando HTH necesita el dato, lee directo de esa caché (instantáneo), nunca sale a la red en el momento del anuncio. Si la caché está vencida o vacía (recién abierta la app, antes del primer refresco), TEMPERATURA/HUMEDAD se saltean como cualquier clip faltante.
