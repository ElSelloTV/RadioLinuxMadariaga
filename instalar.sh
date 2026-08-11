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

# Bug real reportado: si falta "git" en el sistema, bash tira un error
# críptico en la línea del "git clone" ("git: orden no encontrada") sin
# decir qué paquete instalar — indistinguible para alguien que recién
# arranca de "el script está roto". Se chequea ACÁ, antes de intentar
# nada, con un mensaje claro y el comando exacto para resolverlo.
if ! command -v git >/dev/null 2>&1; then
    echo ""
    echo "ERROR: falta instalar 'git' en este sistema (necesario para"
    echo "descargar/actualizar el repositorio). Instalalo con:"
    echo ""
    echo "  sudo apt install -y git"
    echo ""
    echo "y volvé a correr este instalador."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "ERROR: falta instalar 'python3' en este sistema. Instalalo con:"
    echo ""
    echo "  sudo apt install -y python3"
    echo ""
    echo "y volvé a correr este instalador."
    exit 1
fi

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

# Mismo criterio que el chequeo de git/python3 de arriba: si falta el
# paquete "python3-venv" del sistema, `python3 -m venv` puede fallar en
# silencio (o crear una carpeta venv/ incompleta, sin pip adentro) —
# confirmado ACÁ, antes de que el próximo paso falle con un error de
# "no such file or directory" igual de críptico.
if [ ! -x "venv/bin/pip" ]; then
    # El nombre del paquete real en Debian/Ubuntu suele ser específico
    # de la versión (ej. "python3.13-venv", no un genérico "python3-venv"
    # a secas) — se calcula acá para dar el comando EXACTO, igual que ya
    # hace el propio mensaje de error de Python en este caso.
    VERSION_PYTHON="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    PAQUETE_VENV="python3-venv"
    [ -n "$VERSION_PYTHON" ] && PAQUETE_VENV="python3-venv python${VERSION_PYTHON}-venv"
    echo ""
    echo "ERROR: el entorno virtual se creó incompleto (falta venv/bin/pip)."
    echo "Normalmente esto pasa si falta el paquete de Python 'venv' del"
    echo "sistema. Instalalo con:"
    echo ""
    echo "  sudo apt install -y $PAQUETE_VENV"
    echo ""
    echo "y volvé a correr este instalador (podés borrar la carpeta 'venv'"
    echo "incompleta antes, con: rm -rf $CARPETA_DESTINO/venv)."
    exit 1
fi

echo "Instalando dependencias de Python..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

echo ""
echo "Dependencias del sistema necesarias (instalar aparte si falta alguna):"
echo "  sudo apt install vlc libvlc-dev ffmpeg"
echo ""

echo "Instalando lanzadores de escritorio..."
chmod +x "$CARPETA_DESTINO/iniciar.sh"
chmod +x "$CARPETA_DESTINO/iniciar_satelite.sh"

mkdir -p "$HOME/.local/share/applications"

# Carpeta de escritorio real: xdg-user-dir respeta el idioma del
# sistema (en Q4OS en español es "Escritorio", no "Desktop").
CARPETA_ESCRITORIO="$(xdg-user-dir DESKTOP 2>/dev/null)"
if [ -z "$CARPETA_ESCRITORIO" ]; then
    if [ -d "$HOME/Escritorio" ]; then
        CARPETA_ESCRITORIO="$HOME/Escritorio"
    elif [ -d "$HOME/Desktop" ]; then
        CARPETA_ESCRITORIO="$HOME/Desktop"
    fi
fi

# Instala UN .desktop (el programa principal o la app satélite) tanto
# en el menú de aplicaciones como, si existe, en el escritorio real —
# pedido explícito para la satélite: "necesito un ícono de escritorio,
# nada de comando por consola", mismo tratamiento que ya tenía el
# programa principal.
instalar_lanzador() {
    NOMBRE_ARCHIVO="$1"
    sed "s#/home/santiago/RadioLinuxMadariaga#$CARPETA_DESTINO#g" \
        "$CARPETA_DESTINO/assets/$NOMBRE_ARCHIVO" \
        > "$HOME/.local/share/applications/$NOMBRE_ARCHIVO"
    chmod +x "$HOME/.local/share/applications/$NOMBRE_ARCHIVO"

    if [ -n "$CARPETA_ESCRITORIO" ] && [ -d "$CARPETA_ESCRITORIO" ]; then
        cp "$HOME/.local/share/applications/$NOMBRE_ARCHIVO" "$CARPETA_ESCRITORIO/"
        chmod +x "$CARPETA_ESCRITORIO/$NOMBRE_ARCHIVO"
        # Algunos entornos (GNOME/Nautilus) no muestran el ícono como
        # ejecutable hasta que se marca "confiable".
        command -v gio >/dev/null 2>&1 && gio set "$CARPETA_ESCRITORIO/$NOMBRE_ARCHIVO" "metadata::trusted" true 2>/dev/null
    fi
}

instalar_lanzador "radiolinuxmadariaga.desktop"
instalar_lanzador "radiolinuxmadariaga_satelite.desktop"

if [ -n "$CARPETA_ESCRITORIO" ] && [ -d "$CARPETA_ESCRITORIO" ]; then
    echo "Íconos copiados a: $CARPETA_ESCRITORIO"
else
    echo "Aviso: no se encontró una carpeta de Escritorio — los íconos"
    echo "quedaron instalados en el menú de aplicaciones igual."
fi

echo ""
echo "== Listo =="
echo "Carpeta de instalación: $CARPETA_DESTINO"
echo "Para iniciar manualmente:"
echo "  cd $CARPETA_DESTINO && source venv/bin/activate && python3 main.py"
echo "También podés usar el ícono del escritorio, o el botón"
echo "'Actualizar' dentro de Configuración > Actualizaciones."
