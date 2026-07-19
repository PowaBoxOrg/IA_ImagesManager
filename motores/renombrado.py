"""Planificacion y aplicacion reversible de renombrados."""

import os
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CambioNombre:
    origen: str
    destino: str

    @property
    def requiere_cambio(self) -> bool:
        return os.path.normcase(os.path.abspath(self.origen)) != os.path.normcase(os.path.abspath(self.destino))


def validar_plan(cambios: list[CambioNombre]) -> None:
    origenes = {os.path.normcase(os.path.abspath(c.origen)) for c in cambios}
    destinos: set[str] = set()
    for cambio in cambios:
        destino = os.path.normcase(os.path.abspath(cambio.destino))
        if destino in destinos:
            raise ValueError(f"Destino repetido: {cambio.destino}")
        destinos.add(destino)
        if os.path.exists(cambio.destino) and destino not in origenes:
            raise FileExistsError(cambio.destino)


def aplicar_plan(cambios: list[CambioNombre]) -> int:
    efectivos = [c for c in cambios if c.requiere_cambio]
    validar_plan(efectivos)
    temporales: list[tuple[str, str, str]] = []
    try:
        for cambio in efectivos:
            temporal = os.path.join(os.path.dirname(cambio.origen), f".__iam_{uuid.uuid4().hex}.tmp")
            os.replace(cambio.origen, temporal)
            temporales.append((temporal, cambio.origen, cambio.destino))
        for temporal, _, destino in temporales:
            os.replace(temporal, destino)
        return len(efectivos)
    except Exception:
        for temporal, origen, destino in reversed(temporales):
            if os.path.exists(temporal):
                os.replace(temporal, origen)
            elif os.path.exists(destino) and not os.path.exists(origen):
                os.replace(destino, origen)
        raise

