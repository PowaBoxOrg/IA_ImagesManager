"""Planificacion y aplicacion reversible de renombrados."""

import os
import re
import uuid
from dataclasses import dataclass

CARACTERES_INVALIDOS = set('<>:"/\\|?*')
DIGITOS_SECUENCIA = 6
PATRON_PREFIJO_CAPTURA = re.compile(r"^\d+_(captura(?:[_ -].*)?)$", re.IGNORECASE)
NOMBRES_RESERVADOS = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def afijo(valor: str | None) -> str:
    """Normaliza un prefijo o sufijo. Vacio o solo espacios no altera el nombre."""
    if valor is None:
        return ""
    return str(valor).strip()


def afijo_valido(valor: str) -> bool:
    return not any(caracter in CARACTERES_INVALIDOS or ord(caracter) < 32 for caracter in valor)


def nombre_con_numero_carpeta(nombre_archivo: str, numero: str | None) -> str | None:
    """Antepone el numero de una carpeta de capturas una sola vez.

    Si el archivo ya empieza por ese numero, no cambia.
    Si empieza por otro numero y luego 'captura', sustituye ese numero.
    """
    numero = afijo(numero)
    if not numero:
        return None
    if nombre_archivo.lower().startswith(f"{numero.lower()}_"):
        return None
    coincidencia = PATRON_PREFIJO_CAPTURA.fullmatch(nombre_archivo)
    if coincidencia:
        return f"{numero}_{coincidencia.group(1)}"
    return f"{numero}_{nombre_archivo}"


def nombre_con_afijos(nombre: str, prefijo: str = "", sufijo: str = "") -> str:
    """Antepone el prefijo y agrega el sufijo antes de la extension."""
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    if not prefijo and not sufijo:
        return nombre
    base, extension = os.path.splitext(nombre)
    return f"{prefijo}{base}{sufijo}{extension}"


def nombre_seguro(texto: str | None) -> str:
    """Convierte un titulo o nombre de carpeta en un fragmento de archivo."""
    if texto is None:
        return ""
    limpio = "".join(
        "_" if caracter in CARACTERES_INVALIDOS or ord(caracter) < 32 else caracter
        for caracter in str(texto)
    ).strip(" .")
    if not limpio:
        return ""
    if limpio.split(".", 1)[0].upper() in NOMBRES_RESERVADOS:
        return f"_{limpio}"
    return limpio


def indice_nombre(numero: int, etiqueta: str = "", digitos: int = DIGITOS_SECUENCIA) -> str:
    """Numero de ancho fijo. Con etiqueta queda etiqueta_000001."""
    texto = f"{int(numero):0{digitos}d}"
    etiqueta = nombre_seguro(afijo(etiqueta))
    if etiqueta:
        return f"{etiqueta}_{texto}"
    return texto


def nombre_multimedia(
    origen: str,
    rol: str,
    indice: int,
    extension: str,
    digitos: int = DIGITOS_SECUENCIA,
) -> str:
    """Nombre unico entre fuentes: Origen_rol_000001.ext."""
    if not str(extension).startswith("."):
        extension = f".{extension}"
    origen_seguro = nombre_seguro(os.path.splitext(os.path.basename(str(origen or "")))[0])
    rol_seguro = nombre_seguro(rol) or "archivo"
    numero = f"{int(indice):0{digitos}d}"
    if origen_seguro:
        return f"{origen_seguro}_{rol_seguro}_{numero}{extension}"
    return f"{rol_seguro}_{numero}{extension}"


def nombre_pieza(origen: str, rol: str, fila: int, columna: int, extension: str = ".png") -> str:
    """Pieza de un mosaico: Origen_rol_00_00.ext."""
    if not str(extension).startswith("."):
        extension = f".{extension}"
    origen_seguro = nombre_seguro(os.path.splitext(os.path.basename(str(origen or "")))[0])
    rol_seguro = nombre_seguro(rol) or "pieza"
    cuerpo = f"{rol_seguro}_{int(fila):02d}_{int(columna):02d}"
    if origen_seguro:
        return f"{origen_seguro}_{cuerpo}{extension}"
    return f"{cuerpo}{extension}"


def afijos_con_carpeta(
    directorio: str,
    posicion: str,
    prefijo: str = "",
    sufijo: str = "",
) -> tuple[str, str]:
    """Pone el nombre de la carpeta por fuera del prefijo y el sufijo manuales."""
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    if posicion not in ("prefijo", "sufijo"):
        return prefijo, sufijo
    marca = nombre_seguro(os.path.basename(os.path.abspath(directorio)))
    if not marca:
        return prefijo, sufijo
    if posicion == "prefijo":
        return f"{marca}_{prefijo}", sufijo
    return prefijo, f"{sufijo}_{marca}"


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


def patron_nomenclatura(nombre: str) -> str:
    """Reduce un nombre a su forma: numeros a #, letras a A y la extension en minusculas."""
    base, extension = os.path.splitext(nombre)
    forma = []
    anterior = ""
    for caracter in base:
        if caracter.isdigit():
            tipo = "#"
        elif caracter.isalpha():
            tipo = "A"
        else:
            tipo = caracter
        if tipo in "#A" and tipo == anterior:
            continue
        forma.append(tipo)
        anterior = tipo
    return f"{''.join(forma)}{extension.lower()}"


def clasificar_nomenclatura(nombres: list[str]) -> tuple[str, list[str], list[str]]:
    """Separa la forma compartida de los archivos que no la siguen.

    La forma comun es la que aparece mas veces que cualquier otra.
    Si hay empate, no hay nomenclatura definida y la lista de fuera incluye a todos.
    Un archivo solo no esta fuera de norma.
    """
    if not nombres:
        return "", [], []
    grupos: dict[str, list[str]] = {}
    for nombre in nombres:
        grupos.setdefault(patron_nomenclatura(nombre), []).append(nombre)
    orden = sorted(grupos.items(), key=lambda item: (-len(item[1]), item[0]))
    patron, comunes = orden[0]
    if len(orden) > 1 and len(comunes) == len(orden[1][1]):
        return "", [], list(nombres)
    fuera = [nombre for otro, miembros in orden[1:] for nombre in miembros]
    return patron, list(comunes), fuera


def reemplazar_en_nombre(
    nombre: str,
    buscar: str,
    sustituir: str = "",
    ignorar_mayusculas: bool = False,
) -> str | None:
    """Sustituye texto en el nombre, sin tocar la extension. None si no cambia."""
    buscar = buscar or ""
    if not buscar:
        return None
    base, extension = os.path.splitext(nombre)
    if ignorar_mayusculas:
        coincidencia = re.search(re.escape(buscar), base, re.IGNORECASE)
        if coincidencia is None:
            return None
        nueva_base = re.sub(re.escape(buscar), lambda _coincidencia: sustituir, base, flags=re.IGNORECASE)
    else:
        if buscar not in base:
            return None
        nueva_base = base.replace(buscar, sustituir)
    nueva_base = nueva_base.strip(" .")
    if not nueva_base or nueva_base in (".", ".."):
        return None
    nuevo = f"{nueva_base}{extension}"
    if nuevo == nombre:
        return None
    return nuevo


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

