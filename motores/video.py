"""Extraccion secuencial de todos los frames de un video."""

import math
import os
from dataclasses import dataclass
from typing import Callable

from motores.renombrado import nombre_con_afijos, nombre_multimedia


@dataclass(frozen=True)
class ResultadoFrames:
    carpeta: str
    fps: float
    total: int
    cancelado: bool = False
    archivo: str = ""


def crear_carpeta_frames(ruta_video: str) -> str:
    """Crea una carpeta nueva junto al video sin sobrescribir extracciones previas."""
    base = os.path.splitext(os.path.basename(ruta_video))[0]
    carpeta_base = os.path.join(os.path.dirname(os.path.abspath(ruta_video)), f"{base}_frames")
    indice = 1
    while True:
        carpeta = carpeta_base if indice == 1 else f"{carpeta_base}_{indice}"
        try:
            os.makedirs(carpeta)
            return carpeta
        except FileExistsError:
            indice += 1


def guardar_primer_frame(ruta_video: str, datos_png: bytes) -> str:
    """Guarda el primer frame junto al video sin sobrescribir otro archivo."""
    directorio = os.path.dirname(os.path.abspath(ruta_video))
    nombre = nombre_multimedia(ruta_video, "primer", 1, ".png")
    indice = 1
    while True:
        candidato = nombre if indice == 1 else nombre_con_afijos(nombre, "", f"_{indice}")
        ruta_imagen = os.path.join(directorio, candidato)
        try:
            with open(ruta_imagen, "xb") as archivo:
                archivo.write(datos_png)
            return ruta_imagen
        except FileExistsError:
            indice += 1


def extraer_todos_los_frames(
    ruta_video: str,
    progreso: Callable[[int], None] | None = None,
    cancelar: Callable[[], bool] | None = None,
    fps_detectados: Callable[[float], None] | None = None,
    solo_primer_frame: bool = False,
) -> ResultadoFrames:
    """Guarda los frames en orden, o solo el primero, sin remuestreo.

    Los FPS son los informados por el decodificador; en videos de tasa variable
    representan una tasa nominal o promedio, no la cadencia de cada frame.
    """
    if not os.path.isfile(ruta_video):
        raise FileNotFoundError(f"No existe el video: {ruta_video}")

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV no esta disponible. Instala opencv-python.") from exc

    video = cv2.VideoCapture(ruta_video)
    if not video.isOpened():
        video.release()
        raise RuntimeError(f"No se pudo abrir el video: {ruta_video}")

    carpeta = ""
    archivo_primero = ""
    total = 0
    try:
        fps = float(video.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0:
            raise RuntimeError("No se pudo determinar la tasa de FPS del video.")
        if fps_detectados is not None:
            fps_detectados(fps)

        if not solo_primer_frame:
            carpeta = crear_carpeta_frames(ruta_video)
        cancelado = False
        while True:
            if cancelar is not None and cancelar():
                cancelado = True
                break

            leido, frame = video.read()
            if not leido:
                break

            codificado, imagen = cv2.imencode(".png", frame)
            if not codificado:
                raise RuntimeError(f"No se pudo codificar el frame {total + 1}.")

            if solo_primer_frame:
                archivo_primero = guardar_primer_frame(ruta_video, imagen.tobytes())
            else:
                ruta_imagen = os.path.join(
                    carpeta, nombre_multimedia(ruta_video, "frame", total + 1, ".png")
                )
                with open(ruta_imagen, "xb") as archivo:
                    archivo.write(imagen.tobytes())
            total += 1
            if progreso is not None and total % 100 == 0:
                progreso(total)
            if solo_primer_frame:
                break

        if total == 0:
            if carpeta:
                os.rmdir(carpeta)
                carpeta = ""
            if not cancelado:
                raise RuntimeError("El video no contiene frames legibles.")

        if progreso is not None:
            progreso(total)
        return ResultadoFrames(carpeta, fps, total, cancelado, archivo_primero)
    except Exception as exc:
        if total:
            raise RuntimeError(
                f"{exc}\nSe guardaron {total} frames en: {archivo_primero or carpeta}"
            ) from exc
        if carpeta:
            os.rmdir(carpeta)
        raise
    finally:
        video.release()
