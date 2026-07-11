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

    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="RadioLinuxMadariaga" --text="$MENSAJE" 2>/dev/null
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "RadioLinuxMadariaga" --error "$MENSAJE" 2>/dev/null
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "RadioLinuxMadariaga - Error" "$MENSAJE" 2>/dev/null
    fi
fi

exit $CODIGO
