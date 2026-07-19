"""Catalogo declarativo de herramientas y pertenencias multiples."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    script: str
    descripcion: str
    secciones: tuple[str, ...]
    peligrosa: bool = False


SECCIONES = (
    "Duplicados",
    "Organizacion",
    "Renombrado",
    "Multimedia",
    "Imagen",
    "Otros",
)

HERRAMIENTAS = (
    Herramienta("Buscar imagenes similares", "ImagenesRepetidas.py", "Encuentra y muestra grupos similares en una carpeta.", ("Duplicados",)),
    Herramienta("Mover duplicados", "ImagenesRepetidasMover.py", "Detecta duplicados perceptuales y mueve las copias.", ("Duplicados", "Organizacion"), True),
    Herramienta("Comparar dos carpetas", "CompararRepetidos_2Carpetas.py", "Compara una carpeta de referencia con otra.", ("Duplicados",)),
    Herramienta("Clasificar por dimensiones", "CopiadorImagenes.py", "Visor que copia imagenes a categorias alta y baja.", ("Organizacion", "Imagen")),
    Herramienta("Aplanar imagenes y ZIP", "MoverImagenesACarpetaPadre.py", "Mueve o extrae imagenes a una carpeta comun.", ("Organizacion", "Renombrado"), True),
    Herramienta("Carpetas vacias", "EncontrarCarpetasVacias.py", "Busca, mueve o elimina carpetas vacias.", ("Organizacion",), True),
    Herramienta("Agrupar nuevas imagenes", "Agrupador.py", "Agrupa y monitorea imagenes con nombres alfabeticos.", ("Organizacion", "Renombrado"), True),
    Herramienta("Renombrado numerico", "RenombradorNumerico.py", "Ordena por fecha interna y asigna numeros.", ("Renombrado",), True),
    Herramienta("Renombrado alfabetico", "RenombradorAlfabetico.py", "Asigna secuencias a, b, ..., aa.", ("Renombrado",), True),
    Herramienta("Corregir nombres de capturas", "CorregirNombresCapturas.py", "Aplica el prefijo de cada carpeta de capturas.", ("Renombrado",), True),
    Herramienta("Convertir imagenes a PNG", "img2img.py", "Convierte por lotes y organiza originales.", ("Imagen", "Organizacion", "Renombrado"), True),
    Herramienta("Crear icono ICO", "img2ico.py", "Genera un ICO con multiples resoluciones.", ("Imagen",)),
    Herramienta("Cortar imagen en tiles", "SliceImage.py", "Divide una imagen en mosaicos cuadrados.", ("Imagen",)),
    Herramienta("Extraer frames de GIF", "ExtractorGif.py", "Extrae frames PNG de uno o varios GIF.", ("Imagen", "Multimedia")),
    Herramienta("Video a imagenes", "MP4_a_Imagenes.py", "Extrae capturas de un video a intervalos.", ("Multimedia", "Imagen")),
    Herramienta("Carpeta de videos a imagenes", "MP4_a_Imagenes_Carpeta.py", "Procesa varios MP4 por lotes.", ("Multimedia", "Imagen")),
    Herramienta("Video a MP3", "MP4_a_MP3.py", "Extrae audio de archivos o carpetas de videos.", ("Multimedia",)),
    Herramienta("MP4 a MKV", "MP4_MKV.py", "Cambia el contenedor o codecs de video y audio.", ("Multimedia",)),
    Herramienta("MP4 a GIF", "mp4_a_gif_ffmpeg.py", "Crea GIF optimizado mediante FFmpeg.", ("Multimedia", "Imagen")),
    Herramienta("MP3 a MP4", "mp4tomp3.py", "Crea video con fondo negro a partir de audio.", ("Multimedia",)),
    Herramienta("Encontrar punto de loop", "encontrar_loop.py", "Compara frames para localizar un posible bucle.", ("Multimedia",)),
    Herramienta("Autoclicker", "Otros/Autoclicker.py", "Utilidad independiente de clic automatico.", ("Otros",)),
)


def herramientas_de(seccion: str) -> tuple[Herramienta, ...]:
    return tuple(h for h in HERRAMIENTAS if seccion in h.secciones)

