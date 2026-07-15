"""
core/hth.py
--------------------------------------------------------
Motor puro (sin Qt — mismo espíritu que core/musicalizador.py) del
Comando HTH (Hora-Temperatura-Humedad, terminología real de Dinesat —
ver docs/manual_dinesat_visual.md 5.2.7.3/5.3.5/5.3.5.1/5.3.5.2 y la
nota de nomenclatura en CLAUDE.md; Santiago originalmente lo pidió
llamándolo "FMT HORA"/"FMT CLIMA", pero confirmó vía AskUserQuestion
usar el nombre real "Comando HTH").

Resuelve, para cada uno de los 3 comandos (HORA / TEMPERATURA /
HUMEDAD, confirmados como comandos INDEPENDIENTES — no uno combinado),
la lista ORDENADA de rutas de archivo a concatenar. Nunca tira
excepción: si falta CUALQUIER clip necesario, o si no se pudo obtener
el dato de clima (ver core/clima_meteo.py), devuelve None — pedido
explícito de Santiago ("Saltea todo el comando, sin sonar nada") para
no dejar un anuncio a medias/incoherente al aire.

Nomenclatura EXACTA de los materiales (deben existir con género "HTH"
— confirmado, "Categoría dedicada en el Explorador" — en la biblioteca
del Explorador; el título es el que se compara, no importa en qué
categoría/subcategoría estén archivados ni las mayúsculas/espacios de
más, se normaliza al comparar):

    INTRO HORA                              (clip fijo, "Es la hora...")
    HORA 00 .. HORA 23
    MINUTOS 00 .. MINUTOS 59
    TEMPERATURA GRADOS 00 .. TEMPERATURA GRADOS 50   (valor absoluto)
    TEMPERATURA BAJO CERO                    (clip fijo, prefijo)
    HUMEDAD 000 .. HUMEDAD 100               (3 dígitos)

Decisiones confirmadas con Santiago (AskUserQuestion, ver CLAUDE.md):
- El manual de Dinesat no documenta un clip de intro para la hora —
  se agrega "INTRO HORA" como clip fijo propio de esta app.
- Sin décimas: la temperatura se redondea a grados enteros (no hace
  falta grabar TEMPERATURA DECIMA).
- Bajo cero = prefijo fijo "TEMPERATURA BAJO CERO" + reutiliza el
  mismo clip de TEMPERATURA GRADOS XX del valor absoluto (no hace
  falta grabar un clip completo por cada valor negativo).
--------------------------------------------------------
"""

from datetime import datetime

from config.settings import cargar_configuracion
from core.clima_meteo import obtener_clima

GENERO_HTH = "HTH"
TIPO_COMANDO_HTH = "HTH"
PARAMETROS_HTH = ("HORA", "TEMPERATURA", "HUMEDAD")


def _normalizar(texto: str) -> str:
    return " ".join((texto or "").strip().upper().split())


def _buscar_clip(explorador, titulo_exacto: str) -> str | None:
    """Busca, entre TODOS los materiales de género HTH (sin importar
    en qué categoría estén archivados), el que tenga el título exacto
    pedido (normalizado). None si no existe o si no hay `explorador`."""
    if explorador is None:
        return None
    objetivo = _normalizar(titulo_exacto)
    for registro in explorador.listar_registros_por_genero(GENERO_HTH):
        if _normalizar(registro.get("titulo")) == objetivo:
            ruta = registro.get("ruta")
            if ruta:
                return ruta
    return None


def _resolver_lista(explorador, titulos: list) -> list | None:
    """Resuelve una lista de títulos a rutas; None si falta
    CUALQUIERA de ellos — todo o nada, nunca un anuncio a medias."""
    rutas = []
    for titulo in titulos:
        ruta = _buscar_clip(explorador, titulo)
        if ruta is None:
            return None
        rutas.append(ruta)
    return rutas


def resolver_clips_hora(explorador, hora: int, minuto: int) -> list | None:
    return _resolver_lista(explorador, [
        "INTRO HORA",
        f"HORA {hora:02d}",
        f"MINUTOS {minuto:02d}",
    ])


def resolver_clips_temperatura(explorador, temperatura_c: int) -> list | None:
    if temperatura_c < 0:
        return _resolver_lista(explorador, [
            "TEMPERATURA BAJO CERO",
            f"TEMPERATURA GRADOS {abs(temperatura_c):02d}",
        ])
    return _resolver_lista(explorador, [f"TEMPERATURA GRADOS {temperatura_c:02d}"])


def resolver_clips_humedad(explorador, humedad_pct: int) -> list | None:
    humedad_pct = max(0, min(100, round(humedad_pct)))
    return _resolver_lista(explorador, [f"HUMEDAD {humedad_pct:03d}"])


def resolver_comando_hth(explorador, parametro: str, ahora=None, clima=None) -> list | None:
    """Punto de entrada único usado por GestorPublicidad
    (core/playlist_manager.py). `parametro` es "HORA"/"TEMPERATURA"/
    "HUMEDAD" (el tipo de comando real es siempre "HTH", ver
    TIPO_COMANDO_HTH). `ahora` (datetime) y `clima` (dict ya resuelto)
    son inyectables para tests — en producción se resuelven solos
    (hora real del sistema / core.clima_meteo.obtener_clima() con las
    coordenadas configuradas)."""
    if parametro == "HORA":
        momento = ahora or datetime.now()
        return resolver_clips_hora(explorador, momento.hour, momento.minute)

    if parametro in ("TEMPERATURA", "HUMEDAD"):
        datos = clima
        if datos is None:
            config = cargar_configuracion()
            seccion_clima = config.get("clima", {})
            datos = obtener_clima(
                seccion_clima.get("latitud"), seccion_clima.get("longitud"),
            )
        if datos is None:
            return None
        if parametro == "TEMPERATURA":
            return resolver_clips_temperatura(explorador, datos["temperatura"])
        return resolver_clips_humedad(explorador, datos["humedad"])

    return None
