"""Ejecucion comun de operaciones sobre colecciones de archivos."""

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
        normalizadas = tuple(e.lower() if e.startswith(".") else f".{e.lower()}" for e in self.extensiones)
        object.__setattr__(self, "extensiones", normalizadas)

    def acepta(self, ruta_archivo: str) -> bool:
        return os.path.splitext(ruta_archivo)[1].lower() in self.extensiones


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


def buscar_archivos(carpeta: str, extensiones: Iterable[str], recursivo: bool = False) -> list[str]:
    validas = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensiones}
    archivos: list[str] = []
    if recursivo:
        for directorio, carpetas, nombres in os.walk(carpeta):
            carpetas.sort(key=str.casefold)
            for nombre in sorted(nombres, key=str.casefold):
                if os.path.splitext(nombre)[1].lower() in validas:
                    archivos.append(os.path.join(directorio, nombre))
    else:
        for nombre in sorted(os.listdir(carpeta), key=str.casefold):
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta) and os.path.splitext(nombre)[1].lower() in validas:
                archivos.append(ruta)
    return archivos


def ejecutar_accion_lote(
    accion: AccionLote,
    archivos: Iterable[str],
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
) -> ResultadoLote:
    lista = list(archivos)
    resultado = ResultadoLote(total=len(lista))
    for indice, ruta in enumerate(lista, start=1):
        if debe_cancelar is not None and debe_cancelar():
            resultado.cancelado = True
            break
        if al_progresar is not None:
            al_progresar(indice, resultado.total, ruta)
        try:
            resultado.resultados.append((ruta, accion.procesar_archivo(ruta)))
            resultado.procesados += 1
        except Exception as exc:
            resultado.errores.append(ErrorLote(ruta, str(exc)))
    return resultado

