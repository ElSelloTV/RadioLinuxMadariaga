#!/bin/bash
# --------------------------------------------------------------------
# instalar.sh — Instala (o actualiza) RadioLinuxMadariaga desde GitHub
# directamente en la carpeta home del usuario.
#
# Uso (primera instalación, desde cualquier carpeta):
#   curl -fsSL https://raw.githubusercontent.com/ElSelloTV/RadioLinuxMadariaga/main/instalar.sh | bash
#
# O si ya tenés el repo clonado:
#   cd ~/RadioLinuxMadariaga && ./instalar.sh
#
# Es seguro correrlo de nuevo: si la carpeta ya existe y es un clon
# git, actualiza (git pull) en vez de volver a clonar.
# --------------------------------------------------------------------
set -e

REPO_URL="https://github.com/ElSelloTV/RadioLinuxMadariaga"
CARPETA_DESTINO="$HOME/RadioLinuxMadariaga"

echo "== RadioLinuxMadariaga — instalación/actualización =="

if [ -d "$CARPETA_DESTINO/.git" ]; then
    echo "Ya existe una instalación en $CARPETA_DESTINO — actualizando..."
    git -C "$CARPETA_DESTINO" pull --ff-only
else
    echo "Clonando repositorio en $CARPETA_DESTINO..."
    git clone "$REPO_URL" "$CARPETA_DESTINO"
fi

cd "$CARPETA_DESTINO"

echo "Creando entorno virtual (si no existe)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "Instalando dependencias de Python..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

echo ""
echo "Dependencias del sistema necesarias (instalar aparte si falta alguna):"
echo "  sudo apt install vlc libvlc-dev ffmpeg"
echo ""

echo "Instalando lanzador de escritorio..."
mkdir -p "$HOME/.local/share/applications"
sed "s#/home/santiago/RadioLinuxMadariaga#$CARPETA_DESTINO#g" \
    "$CARPETA_DESTINO/assets/radiolinuxmadariaga.desktop" \
    > "$HOME/.local/share/applications/radiolinuxmadariaga.desktop"
chmod +x "$HOME/.local/share/applications/radiolinuxmadariaga.desktop"

if [ -d "$HOME/Desktop" ]; then
    cp "$HOME/.local/share/applications/radiolinuxmadariaga.desktop" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/radiolinuxmadariaga.desktop"
fi

echo ""
echo "== Listo =="
echo "Carpeta de instalación: $CARPETA_DESTINO"
echo "Para iniciar manualmente:"
echo "  cd $CARPETA_DESTINO && source venv/bin/activate && python3 main.py"
echo "También podés usar el ícono del escritorio, o el botón"
echo "'Actualizar' dentro de Configuración > Actualizaciones."
