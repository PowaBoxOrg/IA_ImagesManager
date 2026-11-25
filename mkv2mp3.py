"""Abre el conversor de video a MP3 en el modo MoviePy.

El nombre del archivo se conserva para los accesos existentes. La ventana
unificada tambien ofrece FFmpeg, que convierte MKV, MP4, AVI y otros videos.
"""


def main() -> None:
    from MP4_a_MP3 import main as main_unificado

    main_unificado(motor="moviepy")


if __name__ == "__main__":
    main()
