"""Muestra los FPS de un video y guarda todos sus frames o solo el primero.

Sin una ruta, abre la ventana unificada de video a imagenes en el modo
correspondiente. Con una ruta, extrae desde la terminal como antes.
"""

import argparse
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from motores.video import ResultadoFrames, extraer_todos_los_frames


def relanzar_si_falta_opencv(modo_grafico: bool) -> int | None:
    """Usa el Python global si el entorno virtual de la app no tiene OpenCV."""
    try:
        import cv2  # noqa: F401

        return None
    except ImportError:
        pass

    python_global = getattr(sys, "_base_executable", "")
    if (
        sys.prefix == getattr(sys, "base_prefix", sys.prefix)
        or not python_global
        or not os.path.isfile(python_global)
        or os.path.normcase(os.path.abspath(python_global))
        == os.path.normcase(os.path.abspath(sys.executable))
    ):
        return None

    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        if modo_grafico:
            subprocess.Popen(comando, cwd=os.getcwd())
            return 0
        return subprocess.run(comando, check=False).returncode
    except OSError:
        return None


def main_grafico(solo_primer_frame: bool = False) -> None:
    """Abre la ventana unificada en el modo de frames o de primer frame."""
    from MP4_a_Imagenes_Carpeta import main as main_unificado

    main_unificado(modo="primer-frame" if solo_primer_frame else "frames")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detecta los FPS y guarda todos los frames o solo el primero como PNG."
    )
    parser.add_argument("video", nargs="?", help="Ruta del video; sin ruta abre la ventana grafica")
    parser.add_argument(
        "--solo-primer-frame",
        action="store_true",
        help="Guarda solo el primer frame del video",
    )
    args = parser.parse_args()

    relanzado = relanzar_si_falta_opencv(modo_grafico=args.video is None)
    if relanzado is not None:
        return relanzado

    if args.video is None:
        main_grafico(solo_primer_frame=args.solo_primer_frame)
        return 0

    try:
        resultado = extraer_todos_los_frames(
            args.video,
            fps_detectados=lambda fps: print(f"FPS del video: {fps:.3f}", flush=True),
            solo_primer_frame=args.solo_primer_frame,
        )
    except (OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Frames guardados: {resultado.total}")
    if resultado.archivo:
        print(f"Imagen: {resultado.archivo}")
    else:
        print(f"Carpeta: {resultado.carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
