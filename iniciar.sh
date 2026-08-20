#!/bin/bash
# --------------------------------------------------------------------
# iniciar.sh — Lanzador usado por el ícono de escritorio.
#
# No se llama a main.py directo desde el .desktop porque al arrancar
# desde un ícono no hay terminal visible: si algo falla (venv roto,
# falta una dependencia), el doble click "no hace nada" y no queda
# forma de saber por qué. Este script redirige toda la salida a un
# log y, si el proceso termina con error, muestra un aviso.
# --------------------------------------------------------------------

cd "$(dirname "$0")" || exit 1

mkdir -p config/data
LOG="config/data/log_lanzador.txt"

mostrar_aviso() {
    local titulo="$1"
    local mensaje="$2"
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="$titulo" --text="$mensaje" 2>/dev/null
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "$titulo" --error "$mensaje" 2>/dev/null
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "$titulo" "$mensaje" 2>/dev/null
    fi
}

# Pedido explícito ("necesito aislar la sesión remota y centrar todo
# en esta sesión Default"): Chrome Remote Desktop, en modo
# desatendido, crea en Linux una sesión X VIRTUAL propia -- distinta
# de la sesión física de la PC -- así que si algo intenta abrir la
# radio DESDE esa sesión remota (un autostart, o el mismo ícono del
# Escritorio, que es la misma carpeta para las dos sesiones), y le
# "gana de mano" a la sesión física en tomar el lock de instancia
# única (core/instancia_unica.py, que no distingue sesiones), la radio
# entera queda corriendo atada al audio de la sesión remota -- nunca
# llega a la consola real, sin ningún error visible. Cortado de raíz
# ACÁ, antes de competir por nada: si esta sesión no es la física
# esperada, ni siquiera se intenta arrancar Python. Mismo chequeo
# repetido en core/sesion_display.py (segunda capa, por si algo lanza
# main.py sin pasar por este script) -- si tu sesión física real
# tuviera otro número, es el único valor a cambiar, en los DOS lugares.
DISPLAY_FISICO_ESPERADO=":0"
DISPLAY_BASE="${DISPLAY%%.*}"  # ":0.0" -> ":0", por si el sistema reporta el número de pantalla
if [ "$DISPLAY_BASE" != "$DISPLAY_FISICO_ESPERADO" ]; then
    {
        echo "== $(date '+%Y-%m-%d %H:%M:%S') =="
        echo "BLOQUEADO: sesión gráfica distinta de la física esperada."
        echo "DISPLAY actual: ${DISPLAY:-(sin definir)} -- esperado: $DISPLAY_FISICO_ESPERADO"
    } >> "$LOG" 2>&1
    mostrar_aviso "RadioLinuxMadariaga" "Esta sesión gráfica no es la física de la radio (DISPLAY actual: ${DISPLAY:-sin definir}, esperado: $DISPLAY_FISICO_ESPERADO).

La radio solo puede correr en la sesión física de la PC -- abrirla desde una sesión remota (ej. Chrome Remote Desktop) haría que el audio nunca llegue al aire. Si estás conectado por escritorio remoto, usá la app satélite en vez de esto."
    exit 1
fi

{
    echo "== $(date '+%Y-%m-%d %H:%M:%S') =="

    if [ ! -x "venv/bin/python3" ]; then
        echo "ERROR: no se encontró venv/bin/python3."
        echo "Corré ./instalar.sh (o './instalar.sh' desde esta carpeta) para instalar el entorno."
        exit 1
    fi

    ./venv/bin/python3 main.py
} >> "$LOG" 2>&1

CODIGO=$?

if [ $CODIGO -ne 0 ]; then
    MENSAJE="RadioLinuxMadariaga se cerró con un error.
Revisá el log para más detalles:
$(pwd)/$LOG"
    mostrar_aviso "RadioLinuxMadariaga" "$MENSAJE"
fi

exit $CODIGO
