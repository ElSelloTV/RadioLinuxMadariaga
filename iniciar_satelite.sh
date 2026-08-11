#!/bin/bash
# --------------------------------------------------------------------
# iniciar_satelite.sh — Lanzador usado por el ícono de escritorio de
# la app satélite de control remoto (ver satelite_main.py y
# core/servidor_control_remoto.py) — pedido explícito: "necesito un
# ícono de escritorio. Nada de comando por consola".
#
# Mismo patrón que iniciar.sh: no se llama a satelite_main.py directo
# desde el .desktop porque al arrancar desde un ícono no hay terminal
# visible — si algo falla (venv roto, falta una dependencia), el
# doble click "no hace nada" y no queda forma de saber por qué. Este
# script redirige toda la salida a un log propio y, si el proceso
# termina con error, muestra un aviso gráfico.
#
# Reusa el MISMO venv del programa principal (misma carpeta del
# repo) — la satélite es parte de este mismo checkout, no necesita
# un entorno aparte.
# --------------------------------------------------------------------

cd "$(dirname "$0")" || exit 1

mkdir -p config/data
LOG="config/data/log_lanzador_satelite.txt"

{
    echo "== $(date '+%Y-%m-%d %H:%M:%S') =="

    if [ ! -x "venv/bin/python3" ]; then
        echo "ERROR: no se encontró venv/bin/python3."
        echo "Corré ./instalar.sh (o './instalar.sh' desde esta carpeta) para instalar el entorno."
        exit 1
    fi

    ./venv/bin/python3 satelite_main.py
} >> "$LOG" 2>&1

CODIGO=$?

if [ $CODIGO -ne 0 ]; then
    MENSAJE="Remoto Radio se cerró con un error.
Revisá el log para más detalles:
$(pwd)/$LOG"

    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Remoto Radio" --text="$MENSAJE" 2>/dev/null
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Remoto Radio" --error "$MENSAJE" 2>/dev/null
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "Remoto Radio - Error" "$MENSAJE" 2>/dev/null
    fi
fi

exit $CODIGO
