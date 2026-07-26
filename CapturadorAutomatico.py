"""Captura imagenes de una carpeta usando intervalos segun cada duracion."""

import os
import subprocess
import sys

from MP4_a_Imagenes_Carpeta import main


def relanzar_con_python_global() -> bool:
    """Usa el Python global cuando el entorno virtual no dispone de OpenCV."""
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        return False
    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(
        os.path.abspath(sys.executable)
    ):
        return False

    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=os.environ.copy())
        return True
    except OSError:
        return False


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main(automatico=True)
