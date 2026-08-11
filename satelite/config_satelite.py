"""
satelite/config_satelite.py
--------------------------------------------------------
Configuración propia de la app satélite (host/puerto/token para
conectarse al servidor de control remoto de la radio) — guardada
APARTE de config_general.json, porque esta app corre bajo OTRO
usuario del sistema (la sesión que ve Escritorio Remoto de Chrome),
sin acceso al home del usuario Radio.
--------------------------------------------------------
"""
import json
import os

RUTA_CONFIG = os.path.join(os.path.expanduser("~"), ".auto_radio_tuyu_satelite.json")

CONFIG_POR_DEFECTO = {
    "host": "127.0.0.1",
    "puerto": 8765,
    "token": "",
}


def cargar_config_satelite() -> dict:
    try:
        with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
            datos = json.load(f)
        config = dict(CONFIG_POR_DEFECTO)
        if isinstance(datos, dict):
            config.update({clave: valor for clave, valor in datos.items() if clave in CONFIG_POR_DEFECTO})
        return config
    except (OSError, ValueError):
        return dict(CONFIG_POR_DEFECTO)


def guardar_config_satelite(config: dict):
    try:
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
