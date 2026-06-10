import os
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


ProcesadorArchivo = Callable[[str], Any]
CallbackProgreso = Callable[[int, int, str], None]
CallbackCancelacion = Callable[[], bool]


@dataclass(frozen=True)
class AccionLote:
    nombre: str
    extensiones: tuple[str, ...]
    procesar_archivo: ProcesadorArchivo

    def __post_init__(self):
        extensiones = tuple(
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in self.extensiones
        )
        object.__setattr__(self, "extensiones", extensiones)

    def acepta(self, ruta_archivo: str) -> bool:
        extension = os.path.splitext(ruta_archivo)[1].lower()
        return extension in self.extensiones


@dataclass(frozen=True)
class ErrorLote:
    ruta_archivo: str
    mensaje: str


@dataclass
class ResultadoLote:
    total: int
    procesados: int = 0
    cancelado: bool = False
    resultados: list[tuple[str, Any]] = field(default_factory=list)
    errores: list[ErrorLote] = field(default_factory=list)


def buscar_archivos(
    carpeta: str,
    extensiones: Iterable[str],
    recursivo: bool = False,
) -> list[str]:
    extensiones_normalizadas = {
        extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        for extension in extensiones
    }

    archivos = []
    if recursivo:
        for directorio, carpetas, nombres in os.walk(carpeta):
            carpetas.sort(key=str.lower)
            for nombre in sorted(nombres, key=str.lower):
                ruta = os.path.join(directorio, nombre)
                if os.path.splitext(nombre)[1].lower() in extensiones_normalizadas:
                    archivos.append(ruta)
    else:
        for nombre in sorted(os.listdir(carpeta), key=str.lower):
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta) and os.path.splitext(nombre)[1].lower() in extensiones_normalizadas:
                archivos.append(ruta)

    return archivos


def ejecutar_accion_lote(
    accion: AccionLote,
    archivos: Iterable[str],
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
) -> ResultadoLote:
    lista_archivos = list(archivos)
    resultado = ResultadoLote(total=len(lista_archivos))

    for indice, ruta_archivo in enumerate(lista_archivos, start=1):
        if debe_cancelar is not None and debe_cancelar():
            resultado.cancelado = True
            break

        if al_progresar is not None:
            al_progresar(indice, resultado.total, ruta_archivo)

        try:
            valor = accion.procesar_archivo(ruta_archivo)
            resultado.resultados.append((ruta_archivo, valor))
            resultado.procesados += 1
        except Exception as exc:
            resultado.errores.append(
                ErrorLote(
                    ruta_archivo=ruta_archivo,
                    mensaje=str(exc),
                )
            )

    return resultado
