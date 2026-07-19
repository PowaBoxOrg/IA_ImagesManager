"""Operaciones seguras y consistentes con rutas y nombres."""

import os
import shutil


def ruta_normalizada(ruta: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(ruta)))


def rutas_iguales(ruta_a: str, ruta_b: str) -> bool:
    return ruta_normalizada(ruta_a) == ruta_normalizada(ruta_b)


def ruta_dentro_de(ruta: str, carpeta: str) -> bool:
    try:
        return os.path.commonpath([ruta_normalizada(ruta), ruta_normalizada(carpeta)]) == ruta_normalizada(carpeta)
    except ValueError:
        return False


def ruta_disponible(carpeta: str, nombre: str) -> str:
    base, extension = os.path.splitext(nombre)
    candidata = os.path.join(carpeta, nombre)
    indice = 1
    while os.path.exists(candidata):
        candidata = os.path.join(carpeta, f"{base}_{indice}{extension}")
        indice += 1
    return candidata


def copiar_sin_conflicto(origen: str, carpeta_destino: str) -> str:
    os.makedirs(carpeta_destino, exist_ok=True)
    destino = ruta_disponible(carpeta_destino, os.path.basename(origen))
    shutil.copy2(origen, destino)
    return destino


def mover_sin_conflicto(origen: str, carpeta_destino: str) -> str:
    os.makedirs(carpeta_destino, exist_ok=True)
    return shutil.move(origen, ruta_disponible(carpeta_destino, os.path.basename(origen)))

