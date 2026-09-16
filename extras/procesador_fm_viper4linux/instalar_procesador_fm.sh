#!/bin/bash
# --------------------------------------------------------------------
# instalar_procesador_fm.sh — Instala Viper4Linux (motor CLI, y
# opcionalmente su GUI) como procesador de audio para la salida FM.
#
# Totalmente OPCIONAL e INDEPENDIENTE de RadioLinuxMadariaga: no lo
# corre instalar.sh, no es una dependencia de la app, no hay ninguna
# integración ni control desde el programa. Es exactamente lo mismo
# que instalar EasyEffects "por fuera" (ver README principal) pero
# con Viper4Linux en vez de EasyEffects, para quien prefiera ese
# motor en particular (más liviano, menos funciones — ver
# extras/procesador_fm_viper4linux/README.md para comparación con
# EasyEffects y JDSP4Linux/JamesDSP, ambos más completos pero más
# pesados).
#
# Uso:
#   ./instalar_procesador_fm.sh              # instala solo el motor CLI (viper)
#   ./instalar_procesador_fm.sh --gui        # instala también la GUI (viper-gui)
#   ./instalar_procesador_fm.sh --systemd    # + deja "viper start" corriendo
#                                             #   SIEMPRE, solo con encender la PC
#                                             #   (nunca más un comando a mano)
# Los tres flags se pueden combinar (ej. --gui --systemd).
#
# El código fuente de Viper4Linux se compila desde la copia local en
# vendor/ (vendorizada dentro de este repo), NO desde GitHub — así
# esto sigue funcionando aunque el autor original borre sus repos.
# --------------------------------------------------------------------
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="$SCRIPT_DIR/vendor"
BUILD_GUI=0
INSTALAR_SYSTEMD=0

for arg in "$@"; do
    case "$arg" in
        --gui) BUILD_GUI=1 ;;
        --systemd) INSTALAR_SYSTEMD=1 ;;
        *) echo "Argumento desconocido: $arg (uso: --gui / --systemd)"; exit 1 ;;
    esac
done

if [ "$(uname -m)" != "x86_64" ]; then
    echo "Viper4Linux depende de una librería binaria propietaria solo"
    echo "para x86_64 (libviperfx_x64_linux.so). Esta máquina es"
    echo "$(uname -m) — no se puede instalar acá."
    exit 1
fi

if ! command -v apt >/dev/null 2>&1; then
    echo "Este instalador asume una distro basada en Debian/Ubuntu (apt)."
    exit 1
fi

echo "== Instalando dependencias de compilación =="
sudo apt install -y build-essential git cmake \
    libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev gstreamer1.0-tools

if [ "$BUILD_GUI" -eq 1 ]; then
    sudo apt install -y \
        libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev \
        gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-dev libpulse-dev \
        qtbase5-dev qtbase5-dev-tools qtmultimedia5-dev libqt5svg5-dev \
        libqt5core5a libqt5dbus5 libqt5gui5 libqt5multimedia5 libqt5svg5 \
        libqt5xml5 libqt5network5
fi

echo "== Compilando el plugin de GStreamer (gst-plugin-viperfx) =="
GST_PLUGINS_DIR="$(pkg-config --variable=pluginsdir gstreamer-1.0)"
if [ -z "$GST_PLUGINS_DIR" ]; then
    echo "No se pudo determinar el directorio de plugins de GStreamer."
    exit 1
fi

BUILD_TMP="$(mktemp -d)"
cp -r "$VENDOR_DIR/gst-plugin-viperfx" "$BUILD_TMP/"
cd "$BUILD_TMP/gst-plugin-viperfx"
# -Wno-error=incompatible-pointer-types: GCC 14+ (Debian trixie y más
# nuevo) trata este warning como error por defecto; el código de
# ViPER-FX es de antes de ese cambio. Inofensivo en GCC más viejos.
cmake -DCMAKE_C_FLAGS="-Wno-error=incompatible-pointer-types" . >/dev/null
make
sudo cp libgstviperfx.so "$GST_PLUGINS_DIR/"
cd - >/dev/null

echo "== Instalando la librería core de ViPER =="
sudo cp "$VENDOR_DIR/viperfx_core_binary/libviperfx_x64_linux.so" /lib/libviperfx.so

echo "== Verificando el plugin instalado =="
if ! gst-inspect-1.0 viperfx >/dev/null 2>&1; then
    echo "ADVERTENCIA: gst-inspect-1.0 viperfx no encontró el plugin."
    echo "Revisá que $GST_PLUGINS_DIR sea el path correcto en esta distro."
fi

echo "== Instalando configuración y CLI =="
mkdir -p "$HOME/.config"
if [ -d "$HOME/.config/viper4linux" ]; then
    echo "Ya existe ~/.config/viper4linux — no se pisa (dejo tu config como está)."
else
    cp -r "$VENDOR_DIR/Viper4Linux/viper4linux" "$HOME/.config/"
fi

sudo cp "$VENDOR_DIR/Viper4Linux/viper" /usr/local/bin/viper
sudo chmod 755 /usr/local/bin/viper

# devices.conf.santiago: si esta carpeta trae un archivo con el
# dispositivo de audio REAL ya confirmado (caso de Santiago, consola
# Silicon por USB — ver README), se copia solo, así "viper start"
# apunta SIEMPRE a ese dispositivo en vez de confiar en cuál sea "el
# default" del sistema en el momento del arranque (más frágil). Si el
# operador ya tiene su propio devices.conf armado, nunca se pisa.
if [ -f "$SCRIPT_DIR/devices.conf.santiago" ] && [ ! -f "$HOME/.config/viper4linux/devices.conf" ]; then
    cp "$SCRIPT_DIR/devices.conf.santiago" "$HOME/.config/viper4linux/devices.conf"
    echo "Copiado devices.conf con el dispositivo de audio ya confirmado."
fi

if [ "$INSTALAR_SYSTEMD" -eq 1 ]; then
    echo "== Instalando servicio systemd --user (viper4linux.service) =="
    mkdir -p "$HOME/.config/systemd/user"
    cp "$SCRIPT_DIR/viper4linux.service" "$HOME/.config/systemd/user/viper4linux.service"
    systemctl --user daemon-reload
    systemctl --user enable --now viper4linux.service
    # loginctl linger: sin esto, el servicio --user se apaga solo en
    # cuanto la sesión gráfica cierra sesión (aunque la PC siga
    # prendida) — con linger, arranca junto con el sistema, ANTES de
    # que Santiago inicie sesión siquiera. Requiere sudo (afecta a
    # nivel de systemd-logind, no algo que un usuario común pueda
    # activarse a sí mismo).
    sudo loginctl enable-linger "$USER" 2>/dev/null || \
        echo "ADVERTENCIA: no se pudo activar 'linger' para $USER -- el" \
             "servicio va a arrancar solo, pero recién cuando inicies sesión."
fi

if [ "$BUILD_GUI" -eq 1 ]; then
    echo "== Compilando la GUI (Viper4Linux-GUI) =="
    cp -r "$VENDOR_DIR/Viper4Linux-GUI" "$BUILD_TMP/"
    cd "$BUILD_TMP/Viper4Linux-GUI"
    qmake V4L_Frontend.pro >/dev/null
    make
    sudo cp V4L_Frontend /usr/local/bin/viper-gui
    sudo chmod 755 /usr/local/bin/viper-gui
    sudo cp viper.png /usr/share/pixmaps/viper-gui.png
    sudo tee /usr/share/applications/viper-gui.desktop >/dev/null <<'EOT'
[Desktop Entry]
Name=Viper4Linux
GenericName=Equalizer
Comment=User Interface for Viper4Linux
Keywords=equalizer
Categories=AudioVideo;Audio;
Exec=viper-gui
Icon=viper-gui
StartupNotify=false
Terminal=false
Type=Application
EOT
    cd - >/dev/null
fi

rm -rf "$BUILD_TMP"

echo ""
echo "== Listo =="
echo "Configurá ~/.config/viper4linux/audio.conf a gusto (o usá viper-gui"
echo "si lo instalaste con --gui)."
echo ""
if [ "$INSTALAR_SYSTEMD" -eq 1 ]; then
    echo "Instalado con --systemd: Viper4Linux ya está corriendo AHORA MISMO"
    echo "y va a arrancar solo cada vez que se prenda la PC, sin necesitar"
    echo "ningún comando a mano nunca más."
    echo ""
    echo "IMPORTANTE: hay que correr 'systemctl --user restart viper4linux'"
    echo "después de cada cambio de ~/.config/viper4linux/audio.conf — el"
    echo "motor no relee el archivo en caliente."
else
    echo "Arrancá/reiniciá con:"
    echo "  viper start   |  viper restart  |  viper stop  |  viper status"
    echo ""
    echo "IMPORTANTE: hay que correr 'viper restart' después de cada cambio"
    echo "de configuración — el motor no relee el archivo en caliente."
    echo ""
    echo "Para que arranque SOLO con la PC, sin correr nada a mano nunca"
    echo "más, volvé a correr este instalador agregando --systemd."
fi
