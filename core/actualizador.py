"""
core/actualizador.py
--------------------------------------------------------
Actualiza la aplicación desde el repositorio de GitHub:
    https://github.com/ElSelloTV/RadioLinuxMadariaga

No depende de ninguna librería nueva: usa el binario `git` del
sistema vía subprocess. Requiere que la carpeta de la app sea un
clon git real (ver README.md / instalar.sh) — si no lo es, avisa
en vez de romper algo.

Flujo:
    1) hay_actualizacion_disponible() -> hace `git fetch` y compara
       el commit local contra origin/main (o master), sin tocar
       nada todavía.
    2) aplicar_actualizacion() -> hace `git pull --ff-only`. Al ser
       fast-forward-only, nunca pisa cambios locales sin avisar:
       si el pull no puede hacerse limpio, devuelve error en vez de
       forzar nada.
    3) reiniciar_aplicacion(app, script="main.py") -> lanza una copia
       nueva del proceso (python <script>) y cierra la app actual —
       el mismo checkout git sirve tanto para `main.py` (la radio)
       como para `satelite_main.py` (la app satélite, ver
       satelite/dialogo_actualizaciones.py), cada una reabriéndose a
       sí misma.
--------------------------------------------------------
"""

import os
import sys
import subprocess
from datetime import datetime

REPO_URL = "https://github.com/ElSelloTV/RadioLinuxMadariaga"


def _raiz_app() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def es_instalacion_git() -> bool:
    return os.path.isdir(os.path.join(_raiz_app(), ".git"))


def _ejecutar_git(*args, timeout=30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", _raiz_app(), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def commit_actual() -> str:
    if not es_instalacion_git():
        return "—"
    resultado = _ejecutar_git("rev-parse", "--short", "HEAD")
    return resultado.stdout.strip() if resultado.returncode == 0 else "—"


def _rama_remota_disponible() -> str | None:
    """Detecta contra qué rama remota hay que comparar/actualizar
    HEAD. Primero intenta el upstream REAL configurado para la rama
    actual (`git rev-parse @{u}`) — así funciona sea cual sea la rama
    que esté efectivamente checkouteada (main en una instalación
    normal, o una rama de feature mientras se prueba algo puntual en
    vivo, como durante una sesión de trabajo con Claude Code). Si no
    hay upstream configurado (clon nuevo sin tracking), cae a buscar
    'main' u 'origin/master' como antes."""
    resultado = _ejecutar_git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if resultado.returncode == 0:
        upstream = resultado.stdout.strip()
        if upstream.startswith("origin/"):
            return upstream[len("origin/"):]

    for rama in ("main", "master"):
        resultado = _ejecutar_git("rev-parse", "--verify", f"origin/{rama}")
        if resultado.returncode == 0:
            return rama
    return None


def _evaluar_version(local: str, remoto: str, rama: str) -> tuple[bool, str]:
    """Decide si hay una actualización REAL para traer — no alcanza
    con `local != remoto`: si el local está ADELANTE o DIVERGIDO de la
    rama remota (ej. ya se hizo `git pull` a mano desde otra rama, o
    el checkout quedó sobre una rama de feature ya adelantada respecto
    de origin/main), un `git pull --ff-only` ahí es un no-op que
    "tiene éxito" sin cambiar nada — informar `True` en ese caso deja
    al operador en un bucle infinito real: actualiza, reinicia, y
    vuelve a decir "hay actualización" porque nada cambió nunca. Solo
    cuenta como actualización real si origin/{rama} es descendiente
    directo de HEAD (fast-forward genuino posible)."""
    if local == remoto:
        return False, "Ya tenés la última versión instalada."

    es_ancestro = _ejecutar_git("merge-base", "--is-ancestor", "HEAD", f"origin/{rama}")
    if es_ancestro.returncode == 0:
        return True, "Hay una actualización disponible en GitHub."

    return False, "Ya tenés la última versión instalada."


def hay_actualizacion_disponible() -> tuple[bool, str]:
    """Consulta si hay una versión más nueva en GitHub, SIN aplicar
    nada todavía. Devuelve (hay_actualizacion, mensaje_para_mostrar)."""
    if not es_instalacion_git():
        return False, (
            "Esta copia no es una instalación por git, así que no se puede "
            "buscar actualizaciones automáticamente. Instalá desde GitHub "
            f"({REPO_URL}) para habilitar esta función."
        )

    try:
        resultado_fetch = _ejecutar_git("fetch", "origin")
        if resultado_fetch.returncode != 0:
            return False, f"No se pudo contactar GitHub: {resultado_fetch.stderr.strip()}"

        rama = _rama_remota_disponible()
        if rama is None:
            return False, "No se encontró la rama remota (main/master) en el repositorio."

        local = _ejecutar_git("rev-parse", "HEAD").stdout.strip()
        remoto = _ejecutar_git("rev-parse", f"origin/{rama}").stdout.strip()

        if not local or not remoto:
            return False, "No se pudo determinar la versión actual o la remota."

        return _evaluar_version(local, remoto, rama)

    except (subprocess.TimeoutExpired, OSError) as error:
        return False, f"Error consultando actualizaciones: {error}"


def buscar_actualizacion_async(callback):
    """Versión NO BLOQUEANTE de hay_actualizacion_disponible() — pedido
    explícito ("no debe impedir la reproducción inmediata y con
    automático activado"): el único paso lento de verdad (git fetch,
    va por red) corre en un QProcess asíncrono en vez de un
    subprocess.run() sincrónico — así nunca congela el hilo principal
    (ni la radio, que corre en ese mismo hilo/event loop) mientras
    espera a GitHub, sin necesidad de un QThread (mismo estilo
    deliberadamente simple del resto de la app: QProcess async, ya
    usado en EasyEffects/reiniciar_aplicacion). Las comparaciones
    posteriores (rev-parse local vs. remoto) son lecturas de disco
    casi instantáneas, así que esas sí se resuelven en el callback sin
    volver a salir a red.

    `callback(hay_actualizacion: bool, mensaje: str)` se llama UNA
    sola vez, siempre (éxito o error). Devuelve el QProcess en curso —
    el LLAMADOR tiene que guardar esa referencia en un atributo propio
    mientras dure, o Python lo recolecta a mitad de camino y el
    callback nunca llega a dispararse."""
    if not es_instalacion_git():
        callback(False, (
            "Esta copia no es una instalación por git, así que no se puede "
            "buscar actualizaciones automáticamente. Instalá desde GitHub "
            f"({REPO_URL}) para habilitar esta función."
        ))
        return None

    from PySide6.QtCore import QProcess

    proceso = QProcess()
    proceso.setProgram("git")
    proceso.setArguments(["-C", _raiz_app(), "fetch", "origin"])

    def _al_terminar(codigo_salida, _estado_salida):
        if codigo_salida != 0:
            error = bytes(proceso.readAllStandardError()).decode("utf-8", errors="replace").strip()
            callback(False, f"No se pudo contactar GitHub: {error}")
            return
        try:
            rama = _rama_remota_disponible()
            if rama is None:
                callback(False, "No se encontró la rama remota (main/master) en el repositorio.")
                return
            local = _ejecutar_git("rev-parse", "HEAD").stdout.strip()
            remoto = _ejecutar_git("rev-parse", f"origin/{rama}").stdout.strip()
            if not local or not remoto:
                callback(False, "No se pudo determinar la versión actual o la remota.")
                return
            hay_actualizacion, mensaje = _evaluar_version(local, remoto, rama)
            callback(hay_actualizacion, mensaje)
        except (subprocess.TimeoutExpired, OSError) as error:
            callback(False, f"Error consultando actualizaciones: {error}")

    def _al_fallar_arranque(_error):
        callback(False, "No se pudo iniciar git para buscar actualizaciones.")

    proceso.finished.connect(_al_terminar)
    proceso.errorOccurred.connect(_al_fallar_arranque)
    proceso.start()
    return proceso


def aplicar_actualizacion() -> tuple[bool, str]:
    """Descarga y aplica la actualización (git pull --ff-only).
    Devuelve (éxito, mensaje)."""
    if not es_instalacion_git():
        return False, "Esta copia no es una instalación por git."

    try:
        rama = _rama_remota_disponible() or "main"
        resultado = _ejecutar_git("pull", "--ff-only", "origin", rama, timeout=120)
        if resultado.returncode != 0:
            return False, (
                "No se pudo actualizar automáticamente (probablemente hay cambios "
                f"locales sin confirmar). Detalle: {resultado.stderr.strip()}"
            )
        return True, "Actualización aplicada correctamente."

    except (subprocess.TimeoutExpired, OSError) as error:
        return False, f"Error aplicando la actualización: {error}"


def subir_log_a_git(ruta_log: str) -> tuple[bool, str]:
    """Sube el archivo de log a la rama actual del repositorio (git
    add + commit + push) — SOLO a pedido manual del operador desde
    Configuración → Diagnóstico, nunca automático en cada cierre.
    config/data/*.txt está en .gitignore a propósito (los datos de
    cada instalación no se versionan solos); acá se usa `git add -f`
    para saltear ESE ignore puntualmente, solo cuando el operador lo
    pide de forma explícita. Devuelve (éxito, mensaje)."""
    if not es_instalacion_git():
        return False, "Esta copia no es una instalación por git."
    if not os.path.isfile(ruta_log):
        return False, "Todavía no se generó ningún log en esta instalación."

    try:
        rama_actual = _ejecutar_git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if not rama_actual or rama_actual == "HEAD":
            return False, "No se pudo determinar la rama actual del repositorio."

        ruta_relativa = os.path.relpath(ruta_log, _raiz_app())

        resultado_add = _ejecutar_git("add", "-f", ruta_relativa)
        if resultado_add.returncode != 0:
            return False, f"No se pudo agregar el log: {resultado_add.stderr.strip()}"

        resultado_status = _ejecutar_git("status", "--porcelain", "--", ruta_relativa)
        if not resultado_status.stdout.strip():
            return True, "El log ya estaba actualizado en el repositorio (sin cambios nuevos)."

        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resultado_commit = _ejecutar_git("commit", "-m", f"Log de la aplicación ({marca_tiempo})")
        if resultado_commit.returncode != 0:
            return False, f"No se pudo confirmar el commit: {resultado_commit.stderr.strip()}"

        resultado_push = _ejecutar_git("push", "origin", rama_actual, timeout=60)
        if resultado_push.returncode != 0:
            return False, (
                "El log se guardó en un commit local, pero no se pudo subir a "
                f"GitHub (revisá conexión/credenciales): {resultado_push.stderr.strip()}"
            )

        return True, f"Log subido correctamente a la rama '{rama_actual}'."

    except (subprocess.TimeoutExpired, OSError) as error:
        return False, f"Error subiendo el log: {error}"


def reiniciar_aplicacion(app, script: str = "main.py"):
    """Lanza una copia nueva de la app (python <script>) y cierra
    ésta. `app` es la instancia de QApplication en curso. `script`
    default "main.py" (la radio) — la app satélite pasa
    "satelite_main.py" acá (pedido explícito: "agregale también en
    Configuraciones, la opción de actualizar el programa por GitHub,
    aunque reinicie la APP, no importa" — mismo mecanismo, pero tiene
    que reabrirse A SÍ MISMA, nunca la radio).

    closeAllWindows() antes de quit() es a propósito: app.quit() solo
    corta el event loop SIN pasar por closeEvent, y ahí se perdía el
    guardado de layout (splitters/columnas/geometría) en cada reinicio
    por actualización. La ventana principal ya fue avisada con
    preparar_cierre_por_actualizacion() para no repreguntar por la
    emisión en curso durante este cierre."""
    from PySide6.QtCore import QProcess

    python = sys.executable
    ruta_script = os.path.join(_raiz_app(), script)
    QProcess.startDetached(python, [ruta_script])
    app.closeAllWindows()
    app.quit()


# ------------------------------------------------------------------
# Lanzadores de escritorio — pedido explícito: "necesito un ícono de
# escritorio. Nada de comando por consola". `instalar.sh` ya sabe
# instalarlos/refrescarlos, pero solo corre cuando alguien lo llama a
# mano desde una terminal — el botón "Actualizar" de Configuración
# (el camino que Santiago usa siempre, "actualicé por el programa
# como siempre") SOLO hace `git pull`, nunca corre `instalar.sh`, así
# que un ícono nuevo (o uno que cambió de contenido) nunca llegaba a
# instalarse solo. Esta función replica en Python el mismo mecanismo
# de `instalar.sh` (mismo par de .desktop, mismo reemplazo de ruta,
# misma carpeta de Escritorio real vía xdg-user-dir) para poder
# llamarla SOLA al arrancar cualquiera de los dos puntos de entrada
# (main.py / satelite_main.py) — idempotente y silenciosa: si ya
# está todo instalado y al día, sobreescribe sin más; si algo falla
# (sin permisos, sin carpeta de Escritorio), nunca rompe el arranque.
# ------------------------------------------------------------------
_LANZADORES_DESKTOP = (
    ("radiolinuxmadariaga.desktop", "iniciar.sh"),
    ("radiolinuxmadariaga_satelite.desktop", "iniciar_satelite.sh"),
)


def _carpeta_escritorio_real() -> str | None:
    try:
        resultado = subprocess.run(
            ["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=3,
        )
        candidata = resultado.stdout.strip()
        if candidata and os.path.isdir(candidata):
            return candidata
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
    for nombre in ("Escritorio", "Desktop"):
        candidata = os.path.join(os.path.expanduser("~"), nombre)
        if os.path.isdir(candidata):
            return candidata
    return None


def asegurar_lanzadores_escritorio() -> None:
    raiz = _raiz_app()
    if not os.path.isdir(os.path.join(raiz, "assets")):
        return  # checkout parcial/roto -- no hay nada de dónde copiar

    carpeta_menu = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    carpeta_escritorio = _carpeta_escritorio_real()

    for nombre_desktop, nombre_script in _LANZADORES_DESKTOP:
        script = os.path.join(raiz, nombre_script)
        if os.path.isfile(script):
            try:
                os.chmod(script, 0o755)
            except OSError:
                pass

        plantilla = os.path.join(raiz, "assets", nombre_desktop)
        if not os.path.isfile(plantilla):
            continue
        try:
            with open(plantilla, "r", encoding="utf-8") as f:
                contenido = f.read()
        except OSError:
            continue
        contenido = contenido.replace("/home/santiago/RadioLinuxMadariaga", raiz)

        for carpeta_destino in (carpeta_menu, carpeta_escritorio):
            if not carpeta_destino:
                continue
            try:
                os.makedirs(carpeta_destino, exist_ok=True)
                ruta_destino = os.path.join(carpeta_destino, nombre_desktop)
                with open(ruta_destino, "w", encoding="utf-8") as f:
                    f.write(contenido)
                os.chmod(ruta_destino, 0o755)
                if carpeta_destino == carpeta_escritorio:
                    # Algunos entornos (GNOME/Nautilus) no muestran el
                    # ícono como ejecutable hasta que se marca
                    # "confiable" -- best-effort, sin romper nada si
                    # `gio` no está instalado.
                    try:
                        subprocess.run(
                            ["gio", "set", ruta_destino, "metadata::trusted", "true"],
                            capture_output=True, timeout=3,
                        )
                    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
                        pass
            except OSError:
                pass


# ------------------------------------------------------------------
# Mantenimiento diario automático (pedido explícito: "Como la radio se
# detiene a las 00 horas todos los dias, programemos que a las 2am
# todos los dias haga una 'depuración'... cargue el LOG en GitHub")
# -- mismo criterio ya establecido arriba para los lanzadores de
# escritorio: cualquier setup a nivel de sistema operativo (acá, una
# entrada de crontab) tiene que instalarse SOLO desde Python en el
# arranque de la app, porque el botón "Actualizar" de Configuración
# (el único camino real que usa Santiago) nunca corre `instalar.sh` ni
# ningún script a mano -- documentar "agregá esto al crontab" no
# sirve, en la práctica eso nunca se ejecuta.
# ------------------------------------------------------------------
_MARCA_CRON_MANTENIMIENTO = "radio-tuyu-mantenimiento-diario"


def asegurar_tarea_cron_mantenimiento() -> None:
    """Instala/refresca, de forma idempotente, una entrada de crontab
    que corre `core/mantenimiento_diario.py` todos los días a las 2am
    -- mismo espíritu que `asegurar_lanzadores_escritorio()` más
    arriba: silenciosa (nunca rompe el arranque de la radio si algo
    falla -- sin `crontab` instalado, sin el servicio de cron activo,
    sin permisos, lo que sea) y auto-corrige sola si la ruta de
    instalación cambió (ej. se movió el checkout a otra carpeta).
    Idempotente: si la entrada ya está instalada tal cual, no vuelve a
    tocar el crontab en cada arranque."""
    raiz = _raiz_app()
    script = os.path.join(raiz, "core", "mantenimiento_diario.py")
    if not os.path.isfile(script):
        return  # checkout parcial/roto -- no hay nada que programar

    # Log de "bootstrap" separado del log interno de la app (mismo
    # criterio que iniciar.sh -> log_lanzador.txt): si algo falla ANTES
    # de que el script llegue a importar config.settings (python
    # equivocado, checkout roto), esto es lo único que queda para
    # diagnosticarlo -- el log interno (log_aplicacion.txt, el que se
    # sube a GitHub) sigue siendo donde quedan las 3 tareas en sí.
    log_bootstrap = os.path.join(raiz, "config", "data", "log_cron_mantenimiento.txt")
    linea_nueva = (
        f"0 2 * * * {sys.executable} {script} >> {log_bootstrap} 2>&1 "
        f"# {_MARCA_CRON_MANTENIMIENTO}"
    )

    try:
        resultado = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        # "no crontab for <usuario>" sale con returncode != 0 -- se
        # trata igual que un crontab vacío (el stdout ya viene vacío
        # en ese caso), es el único motivo real por el que `-l` falla
        # en la práctica si el comando SÍ existe.
        actual = resultado.stdout or ""
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return  # sin `crontab` disponible en este sistema -- degradar limpio

    lineas_actuales = [linea for linea in actual.splitlines() if linea.strip()]
    if linea_nueva in lineas_actuales:
        return  # ya estaba instalada tal cual -- nada que tocar

    lineas_nuevas = [linea for linea in lineas_actuales if _MARCA_CRON_MANTENIMIENTO not in linea]
    lineas_nuevas.append(linea_nueva)
    contenido_nuevo = "\n".join(lineas_nuevas) + "\n"

    try:
        os.makedirs(os.path.dirname(log_bootstrap), exist_ok=True)
    except OSError:
        pass

    try:
        subprocess.run(
            ["crontab", "-"], input=contenido_nuevo, text=True, capture_output=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
