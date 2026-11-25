import os

from motores.renombrado import afijo


def generar_nombre_alfabetico(indice: int) -> str:
    """Genera un nombre alfabetico estilo columnas de Excel (a, b, ..., z, aa, ab, ...)."""
    nombre = ""
    while indice >= 0:
        nombre = chr(indice % 26 + 97) + nombre
        indice = indice // 26 - 1
    return nombre


def crear_ruta_temporal(directorio: str, indice: int, extension: str) -> str:
    intento = 0
    while True:
        sufijo = f"{indice}" if intento == 0 else f"{indice}_{intento}"
        nombre = f".__renombrador_alfabetico_tmp_{sufijo}{extension}"
        ruta = os.path.join(directorio, nombre)
        if not os.path.exists(ruta):
            return ruta
        intento += 1


def archivos_en_secuencia(
    archivos: list[dict],
    varios_tipos: bool,
    prefijo: str = "",
    sufijo: str = "",
) -> bool:
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    grupos = {}
    for archivo in archivos:
        grupos.setdefault(archivo["tipo"], []).append(archivo)

    for tipo, archivos_tipo in grupos.items():
        etiqueta = tipo[1:] if tipo else "archivo"
        nombres_actuales = {archivo["nombre"].lower() for archivo in archivos_tipo}
        nombres_esperados = set()

        for indice in range(len(archivos_tipo)):
            nombre_alfabetico = generar_nombre_alfabetico(indice)
            if varios_tipos:
                base = f"{etiqueta}_{nombre_alfabetico}"
            else:
                base = nombre_alfabetico
            nombres_esperados.add(f"{prefijo}{base}{sufijo}{tipo}".lower())

        if nombres_actuales != nombres_esperados:
            return False

    return True


def renombrar_por_alfabeto(directorio: str, prefijo: str = "", sufijo: str = ""):
    """Renombra archivos con una secuencia alfabetica.

    Si existe un solo formato, usa a.jpg, b.jpg, c.jpg...
    Si existen varios, crea una secuencia independiente para cada formato:
    jpg_a.jpg, jpg_b.jpg, png_a.png, png_b.png...
    El prefijo y el sufijo se agregan a ese nombre. Vacios, no lo cambian.

    Devuelve: (renamed_count, skipped)
    """
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    archivos = []
    for nombre in sorted(os.listdir(directorio), key=str.lower):
        ruta = os.path.join(directorio, nombre)
        if not os.path.isfile(ruta) or nombre.startswith(".__"):
            continue

        extension = os.path.splitext(nombre)[1]
        archivos.append(
            {
                "nombre": nombre,
                "ruta": ruta,
                "extension": extension,
                "tipo": extension.lower(),
                "antiguedad": os.path.getmtime(ruta),
            }
        )

    tipos_archivo = {archivo["tipo"] for archivo in archivos}
    varios_tipos = len(tipos_archivo) >= 2

    if archivos_en_secuencia(archivos, varios_tipos, prefijo, sufijo):
        print(
            "Todos los archivos ya estan correctamente nombrados y en secuencia. "
            "No se necesita hacer nada."
        )
        return 0, True

    print("Los archivos no siguen la secuencia esperada. Se procedera a renombrar todo.")

    if varios_tipos:
        archivos.sort(
            key=lambda archivo: (
                archivo["tipo"],
                archivo["antiguedad"],
                archivo["nombre"].lower(),
            )
        )
    else:
        archivos.sort(
            key=lambda archivo: (
                archivo["antiguedad"],
                archivo["nombre"].lower(),
            )
        )

    temporales = []
    try:
        for indice, archivo in enumerate(archivos):
            ruta_temporal = crear_ruta_temporal(
                directorio,
                indice,
                archivo["extension"],
            )
            os.rename(archivo["ruta"], ruta_temporal)
            archivo["ruta_temporal"] = ruta_temporal
            temporales.append(archivo)
    except Exception:
        for archivo in reversed(temporales):
            if os.path.exists(archivo["ruta_temporal"]):
                os.rename(archivo["ruta_temporal"], archivo["ruta"])
        raise

    etiquetas_tipo = {}
    for archivo in archivos:
        if archivo["tipo"] not in etiquetas_tipo:
            etiquetas_tipo[archivo["tipo"]] = (
                archivo["extension"][1:] if archivo["extension"] else "archivo"
            )

    contadores = {tipo: 0 for tipo in tipos_archivo}
    indice_general = 0

    for archivo in archivos:
        tipo = archivo["tipo"]
        extension = archivo["extension"]

        if varios_tipos:
            indice = contadores[tipo]
            base = f"{etiquetas_tipo[tipo]}_{generar_nombre_alfabetico(indice)}"
        else:
            indice = indice_general
            base = generar_nombre_alfabetico(indice)

        ruta_final = os.path.join(directorio, f"{prefijo}{base}{sufijo}{extension}")
        while os.path.exists(ruta_final):
            indice += 1
            if varios_tipos:
                base = f"{etiquetas_tipo[tipo]}_{generar_nombre_alfabetico(indice)}"
            else:
                base = generar_nombre_alfabetico(indice)
            ruta_final = os.path.join(directorio, f"{prefijo}{base}{sufijo}{extension}")

        nuevo_nombre_final = os.path.basename(ruta_final)
        os.rename(archivo["ruta_temporal"], ruta_final)
        print(f'Renombrado a: "{nuevo_nombre_final}"')

        if varios_tipos:
            contadores[tipo] = indice + 1
        else:
            indice_general = indice + 1

    return len(archivos), False


def main():
    """Abre el renombrador unificado en modo alfabetico."""
    from RenombradorNumerico import main as main_unificado

    main_unificado(modo="alfabetico")


if __name__ == "__main__":
    main()
