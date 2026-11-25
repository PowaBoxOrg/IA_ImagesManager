"""Grupos de archivos con el mismo contenido."""

import hashlib
import os
from collections import defaultdict


def huella_archivo(ruta: str) -> str:
    resumen = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        while True:
            bloque = archivo.read(1024 * 1024)
            if not bloque:
                break
            resumen.update(bloque)
    return resumen.hexdigest()


def grupos_exactos(rutas: list[str]) -> tuple[list[list[str]], list[tuple[str, str]]]:
    """Agrupa rutas con el mismo tamano y la misma huella.

    Los archivos de tamano unico no se leen. El primer elemento de cada grupo
    queda como el que se conserva.
    """
    por_tamano: dict[int, list[str]] = defaultdict(list)
    errores: list[tuple[str, str]] = []
    for ruta in rutas:
        try:
            por_tamano[os.path.getsize(ruta)].append(ruta)
        except OSError as exc:
            errores.append((ruta, str(exc)))

    grupos: list[list[str]] = []
    for candidatas in por_tamano.values():
        if len(candidatas) < 2:
            continue
        por_huella: dict[str, list[str]] = defaultdict(list)
        for ruta in candidatas:
            try:
                por_huella[huella_archivo(ruta)].append(ruta)
            except OSError as exc:
                errores.append((ruta, str(exc)))
        for miembros in por_huella.values():
            if len(miembros) > 1:
                grupos.append(sorted(miembros, key=str.lower))
    grupos.sort(key=lambda grupo: grupo[0].lower())
    return grupos, errores
