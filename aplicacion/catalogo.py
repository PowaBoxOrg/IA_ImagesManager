"""Catalogo declarativo de herramientas y pertenencias multiples."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Opcion:
    """Manera de abrir una herramienta que absorbe a otra del mismo tipo."""

    nombre: str
    argumentos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    script: str
    descripcion: str
    secciones: tuple[str, ...]
    peligrosa: bool = False
    opciones: tuple[Opcion, ...] = ()


SECCIONES = (
    "Imagenes",
    "Multimedia",
    "Archivos",
)

HERRAMIENTAS = (
    Herramienta("Buscar imagenes similares", "ImagenesRepetidas.py", "Encuentra y muestra grupos similares en una carpeta.", ("Imagenes",)),
    Herramienta("Mover duplicados", "ImagenesRepetidasMover.py", "Detecta duplicados perceptuales y mueve las copias.", ("Imagenes",), True),
    Herramienta("Comparar dos carpetas", "CompararRepetidos_2Carpetas.py", "Compara una carpeta de referencia con otra.", ("Imagenes",)),
    Herramienta("Clasificar por dimensiones", "CopiadorImagenes.py", "Visor que copia imagenes a categorias alta y baja.", ("Imagenes",)),
    Herramienta("Convertir imagenes a PNG", "img2img.py", "Convierte por lotes y organiza originales.", ("Imagenes",), True),
    Herramienta("Crear icono ICO", "img2ico.py", "Genera un ICO con multiples resoluciones.", ("Imagenes",)),
    Herramienta("Cortar imagen en tiles", "SliceImage.py", "Divide una imagen en mosaicos cuadrados.", ("Imagenes",)),
    Herramienta("Extraer frames de GIF", "ExtractorGif.py", "Extrae frames PNG de uno o varios GIF.", ("Imagenes",)),
    Herramienta(
        "Video a imagenes",
        "MP4_a_Imagenes_Carpeta.py",
        "Extrae capturas por intervalo, por duracion o frame a frame.",
        ("Multimedia",),
        opciones=(
            Opcion("Un video, cada N segundos", ("--modo", "archivo")),
            Opcion("Carpeta de videos, cada N segundos", ("--modo", "carpeta")),
            Opcion("Carpeta, densidad segun duracion", ("--modo", "automatico")),
            Opcion("Todos los frames del video", ("--modo", "frames")),
            Opcion("Solo el primer frame", ("--modo", "primer-frame")),
        ),
    ),
    Herramienta(
        "Convertir formato",
        "ConvertidorFormato.py",
        "Elige el formato de entrada y el de salida. Cada combinacion muestra solo sus opciones.",
        ("Multimedia",),
    ),
    Herramienta("Encontrar punto de loop", "encontrar_loop.py", "Compara frames para localizar un posible bucle.", ("Multimedia",)),
    Herramienta("Aplanar imagenes y ZIP", "MoverImagenesACarpetaPadre.py", "Mueve o extrae imagenes a una carpeta comun.", ("Archivos",), True),
    Herramienta("Carpetas vacias", "EncontrarCarpetasVacias.py", "Busca, mueve o elimina carpetas vacias.", ("Archivos",), True),
    Herramienta("Agrupar nuevas imagenes", "Agrupador.py", "Agrupa y monitorea imagenes con nombres alfabeticos.", ("Archivos",), True),
    Herramienta(
        "Renombrar archivos",
        "RenombradorNumerico.py",
        "Numeros, letras, el nombre actual, capturas, reemplazo de texto o nombres fuera de la forma comun.",
        ("Archivos",),
        True,
        (
            Opcion("Numerico por fecha interna", ("--modo", "numerico")),
            Opcion("Alfabetico (a, b, ..., aa)", ("--modo", "alfabetico")),
            Opcion("Conservar nombre", ("--modo", "conservar")),
            Opcion("Numero de la carpeta de capturas", ("--modo", "capturas")),
            Opcion("Reemplazar texto del nombre", ("--modo", "reemplazar")),
            Opcion("Nombres fuera de la forma comun", ("--modo", "nomenclatura")),
        ),
    ),
    Herramienta("Duplicados exactos", "DuplicadosExactos.py", "Agrupa archivos con el mismo contenido y aparta las copias.", ("Archivos",), True),
    Herramienta("Ordenar por tipo", "OrdenarPorTipo.py", "Separa imagenes, video, audio y el resto en subcarpetas.", ("Archivos",), True),
    Herramienta("Autoclicker", "Otros/Autoclicker.py", "Clic automatico en el cursor, en un punto o en una secuencia.", ("Archivos",)),
    Herramienta("Pulsar teclas", "Otros/PulsarTeclas.py", "Repite una tecla o un texto con una espera.", ("Archivos",)),
)


def herramientas_de(seccion: str) -> tuple[Herramienta, ...]:
    return tuple(h for h in HERRAMIENTAS if seccion in h.secciones)
