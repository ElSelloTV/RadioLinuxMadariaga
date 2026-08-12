"""
satelite/utilidades.py
--------------------------------------------------------
Helpers chicos compartidos por los diálogos de la app satélite —
sin Qt más allá del combo que arman, para no repetir la misma lógica
de armado de combo indentado en cada diálogo nuevo (Subir archivo,
Programador remoto, Musicalizador remoto).
--------------------------------------------------------
"""

NOMBRES_DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
ETIQUETAS_DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def poblar_combo_categorias(combo, categorias: list):
    """`categorias` es la lista PLANA que devuelve
    `ClienteControlRemoto.listar_categorias()`
    (`[{"ruta": [...], "nivel": N}, ...]`) — arma un combo indentado
    por nivel, con `itemData` = la ruta completa (list[str])."""
    combo.clear()
    for categoria in categorias:
        sangria = "    " * max(0, categoria["nivel"] - 1)
        combo.addItem(f"{sangria}{categoria['ruta'][-1]}", categoria["ruta"])
