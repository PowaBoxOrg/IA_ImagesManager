"""Localizacion y ejecucion uniforme de FFmpeg."""

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoComando:
    correcto: bool
    error: str = ""


def resolver_ffmpeg(ruta_preferida: str = "") -> str:
    candidatos = [ruta_preferida, "ffmpeg"]
    carpeta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidatos.extend((
        os.path.join(carpeta_proyecto, "ffmpeg.exe"),
        os.path.join(carpeta_proyecto, "ffmpeg", "bin", "ffmpeg.exe"),
    ))
    for candidato in candidatos:
        candidato = (candidato or "").strip().strip('"')
        if not candidato:
            continue
        encontrado = shutil.which(candidato) or (candidato if os.path.isfile(candidato) else "")
        if encontrado:
            try:
                subprocess.run([encontrado, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return encontrado
            except (OSError, subprocess.SubprocessError):
                pass
    try:
        import imageio_ffmpeg
        encontrado = imageio_ffmpeg.get_ffmpeg_exe()
        if encontrado and os.path.isfile(encontrado):
            return encontrado
    except Exception:
        pass
    return ""


def ffmpeg_disponible(ruta_preferida: str = "") -> bool:
    return bool(resolver_ffmpeg(ruta_preferida))


def ejecutar(argumentos: list[str], ruta_ffmpeg: str = "") -> ResultadoComando:
    ejecutable = resolver_ffmpeg(ruta_ffmpeg)
    if not ejecutable:
        return ResultadoComando(False, "FFmpeg no esta disponible.")
    try:
        subprocess.run([ejecutable, *argumentos], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return ResultadoComando(True)
    except subprocess.CalledProcessError as exc:
        return ResultadoComando(False, (exc.stderr or str(exc)).strip())
    except OSError as exc:
        return ResultadoComando(False, str(exc))

