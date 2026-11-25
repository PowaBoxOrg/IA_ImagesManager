import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema

from motores.renombrado import nombre_multimedia


_error_relanzamiento = ""

# Limite superior del rango (segundos), intervalo entre capturas (segundos).
# El ultimo rango no tiene limite superior.
RANGOS_CAPTURA = (
    (95.0, 1.0),    # R1: 0:00 a 1:35
    (155.0, 3.0),   # R2: mas de 1:35 a 2:35
    (310.0, 10.0),  # R3: mas de 2:35 a 5:10
    (635.0, 30.0),  # R4: mas de 5:10 a 10:35
    (1235.0, 60.0),  # R5: mas de 10:35 a 20:35
    (1835.0, 60.0),  # R6: mas de 20:35 a 30:35
    (3600.0, 60.0),  # R7: mas de 30:35 a 1 hora
    (float("inf"), 60.0),  # R8: 1 hora o mas
)

# Cantidad objetivo predeterminada para cada rango. Conserva aproximadamente
# la densidad de los intervalos originales cerca del limite de cada rango.
CANTIDADES_CAPTURA = (95, 52, 31, 22, 20, 30, 60, 60)


def calcular_plan_capturas(
    duracion_segundos: float,
    cantidades: tuple[int, ...] | list[int] | None = None,
) -> tuple[int, float, float]:
    """Devuelve (rango, intervalo, imagenes_por_segundo) para una duracion.

    La densidad o ratio se calcula como 1 / intervalo. Por ejemplo, un
    intervalo de 10 segundos equivale a 0.1 imagenes por segundo.
    """
    if duracion_segundos < 0:
        raise ValueError("La duracion no puede ser negativa.")

    if cantidades is not None:
        if len(cantidades) != len(RANGOS_CAPTURA):
            raise ValueError("Debe indicar una cantidad para cada rango.")
        if any(cantidad <= 0 for cantidad in cantidades):
            raise ValueError("Las cantidades de capturas deben ser mayores que cero.")

    for rango, (limite, intervalo_predeterminado) in enumerate(RANGOS_CAPTURA, start=1):
        if duracion_segundos <= limite:
            if cantidades is None:
                intervalo = intervalo_predeterminado
            else:
                intervalo = duracion_segundos / cantidades[rango - 1]
                if intervalo <= 0:
                    intervalo = intervalo_predeterminado
            return rango, intervalo, 1.0 / intervalo

    raise RuntimeError("No se pudo determinar el rango de captura.")


def relanzar_con_python_global() -> bool:
    global _error_relanzamiento

    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        _error_relanzamiento = "No se encontro el Python global asociado al entorno virtual."
        return False

    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(os.path.abspath(sys.executable)):
        return False

    entorno = os.environ.copy()
    entorno["MP4_A_IMAGENES_PYTHON_GLOBAL"] = "1"
    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]

    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=entorno)
        return True
    except OSError as exc:
        _error_relanzamiento = f"No se pudo iniciar el Python global:\n{exc}"
        return False


try:
    import cv2
except Exception as exc:  # pragma: no cover
    cv2 = None
    _cv2_import_error = str(exc)


def crear_carpeta_salida(ruta_video: str) -> str:
    directorio = os.path.dirname(ruta_video)
    nombre_video = os.path.splitext(os.path.basename(ruta_video))[0]
    carpeta_base = os.path.join(directorio, f"{nombre_video}_capturas")

    indice = 1
    while True:
        carpeta = carpeta_base if indice == 1 else f"{carpeta_base}_{indice}"
        try:
            os.makedirs(carpeta)
            return carpeta
        except FileExistsError:
            indice += 1


def extraer_capturas(
    ruta_video: str,
    intervalo: float | None,
    cantidades: tuple[int, ...] | list[int] | None = None,
):
    if cv2 is None:
        raise RuntimeError(f"OpenCV (cv2) no disponible. Detalle: {_cv2_import_error}")

    video = cv2.VideoCapture(ruta_video)
    if not video.isOpened():
        raise RuntimeError("No se pudo abrir el video.")

    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps <= 0 or total_frames <= 0:
        video.release()
        raise RuntimeError("No se pudo obtener la duracion del video.")

    duracion = total_frames / fps
    limite_capturas = None
    if intervalo is None:
        rango, intervalo, _ratio = calcular_plan_capturas(duracion, cantidades)
        if cantidades is not None:
            limite_capturas = cantidades[rango - 1]
    elif intervalo <= 0:
        video.release()
        raise ValueError("El intervalo debe ser mayor que cero.")

    carpeta_salida = crear_carpeta_salida(ruta_video)
    tiempo = 0.0
    total = 0

    try:
        while tiempo < duracion and (
            limite_capturas is None or total < limite_capturas
        ):
            video.set(cv2.CAP_PROP_POS_MSEC, tiempo * 1000.0)
            leido, imagen = video.read()
            if not leido:
                break

            total += 1
            ruta_imagen = os.path.join(
                carpeta_salida,
                nombre_multimedia(ruta_video, "captura", total, ".jpg"),
            )
            guardada = cv2.imwrite(
                ruta_imagen,
                imagen,
                [cv2.IMWRITE_JPEG_QUALITY, 95],
            )
            if not guardada:
                raise RuntimeError(f"No se pudo guardar la imagen:\n{ruta_imagen}")

            tiempo += intervalo
    except Exception:
        raise
    finally:
        video.release()

    if total == 0:
        try:
            os.rmdir(carpeta_salida)
        except OSError:
            pass
        raise RuntimeError("No se pudo extraer ninguna imagen del video.")

    return carpeta_salida, total


def main():
    """Abre la ventana unificada en el modo de un solo video."""
    from MP4_a_Imagenes_Carpeta import main as main_unificado

    main_unificado(modo="archivo")


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
