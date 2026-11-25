"""Clasifica archivos por el tipo de su extension."""

import os


CATEGORIAS = ("Imagenes", "Video", "Audio", "Otros")
EXTENSIONES = {
    "Imagenes": {
        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".ico", ".avif",
    },
    "Video": {
        ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".mpg", ".mpeg",
    },
    "Audio": {
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
    },
}


def categoria_de(nombre: str) -> str:
    extension = os.path.splitext(nombre)[1].lower()
    for categoria in ("Imagenes", "Video", "Audio"):
        if extension in EXTENSIONES[categoria]:
            return categoria
    return "Otros"
