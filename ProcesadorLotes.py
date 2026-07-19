"""Compatibilidad con el nombre historico del procesador por lotes."""

from motores.lotes import (  # noqa: F401
    AccionLote,
    CallbackCancelacion,
    CallbackProgreso,
    ErrorLote,
    ProcesadorArchivo,
    ResultadoLote,
    buscar_archivos,
    ejecutar_accion_lote,
)

__all__ = [
    "AccionLote", "CallbackCancelacion", "CallbackProgreso", "ErrorLote",
    "ProcesadorArchivo", "ResultadoLote", "buscar_archivos", "ejecutar_accion_lote",
]
