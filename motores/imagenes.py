"""Tipos y calculos visuales compartidos."""

EXTENSIONES_IMAGEN = (
    ".avif", ".bmp", ".gif", ".heic", ".heif", ".jpeg", ".jpg",
    ".png", ".tif", ".tiff", ".webp",
)
TAMANO_HUELLA = (32, 32)


def es_imagen(ruta: str) -> bool:
    return ruta.lower().endswith(EXTENSIONES_IMAGEN)


def crear_huella_visual(imagen, tamano: tuple[int, int] = TAMANO_HUELLA) -> bytes:
    tipo = type(imagen)
    modulo = __import__(tipo.__module__.split(".")[0], fromlist=["Image"])
    image_api = getattr(modulo, "Image", modulo)
    remuestreo = getattr(getattr(image_api, "Resampling", image_api), "LANCZOS")
    return imagen.convert("L").resize(tamano, remuestreo).tobytes()


def distancia_visual(huella_a: bytes, huella_b: bytes) -> int:
    if len(huella_a) != len(huella_b):
        raise ValueError("Las huellas visuales tienen tamanos diferentes.")
    return sum(abs(a - b) for a, b in zip(huella_a, huella_b))


def similitud_visual(huella_a: bytes, huella_b: bytes) -> float:
    if not huella_a:
        return 100.0
    return max(0.0, 100.0 * (1.0 - distancia_visual(huella_a, huella_b) / (len(huella_a) * 255)))
