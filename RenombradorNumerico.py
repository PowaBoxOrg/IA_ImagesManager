import argparse
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema
from datetime import datetime

from motores.archivos import mover_sin_conflicto
from motores.renombrado import (
    CambioNombre,
    afijo,
    afijo_valido,
    afijos_con_carpeta,
    aplicar_plan,
    clasificar_nomenclatura,
    reemplazar_en_nombre,
)

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    Image = None
    _pil_import_error = str(exc)


EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".avif")
ETIQUETAS_FECHA_EXIF = (
    36867,  # DateTimeOriginal
    36868,  # DateTimeDigitized
    306,    # DateTime
)
CLAVES_FECHA_INFO = (
    "DateTimeOriginal",
    "DateTimeDigitized",
    "DateTime",
    "date:create",
    "date:modify",
    "creation_time",
    "created",
    "Creation Time",
)


def es_imagen(nombre_archivo):
    return nombre_archivo.lower().endswith(EXTENSIONES_IMAGEN)


def extraer_fecha_de_texto(valor):
    if not valor:
        return None

    if isinstance(valor, bytes):
        try:
            valor = valor.decode("utf-8", errors="ignore")
        except Exception:
            return None

    texto = str(valor).strip().replace("\x00", "")
    patrones = (
        (r"\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}", "%Y:%m:%d %H:%M:%S"),
        (r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", None),
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
    )

    for patron, formato in patrones:
        coincidencia = re.search(patron, texto)
        if not coincidencia:
            continue

        fecha_texto = coincidencia.group(0).replace("T", " ")
        try:
            if formato is None:
                return datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(fecha_texto, formato)
        except ValueError:
            continue

    return None


def obtener_fecha_origen_imagen(ruta_archivo):
    if Image is None:
        return None

    try:
        with Image.open(ruta_archivo) as imagen:
            exif = imagen.getexif()
            for etiqueta in ETIQUETAS_FECHA_EXIF:
                fecha = extraer_fecha_de_texto(exif.get(etiqueta))
                if fecha is not None:
                    return fecha

            for clave in CLAVES_FECHA_INFO:
                fecha = extraer_fecha_de_texto(imagen.info.get(clave))
                if fecha is not None:
                    return fecha

            for valor in imagen.info.values():
                fecha = extraer_fecha_de_texto(valor)
                if fecha is not None:
                    return fecha
    except Exception:
        return None

    return None


def crear_ruta_temporal(directorio, indice, extension):
    intento = 0
    while True:
        sufijo = f"{indice}" if intento == 0 else f"{indice}_{intento}"
        ruta_temporal = os.path.join(directorio, f".__renombrador_tmp_{sufijo}{extension}")
        if not os.path.exists(ruta_temporal):
            return ruta_temporal
        intento += 1


def renombrar_por_fecha_origen(directorio, prefijo, inicio=1, sufijo=""):
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    # Obtener todos los archivos. Las carpetas quedan intactas.
    archivos = []
    for nombre_archivo in sorted(os.listdir(directorio), key=str.lower):
        ruta_archivo = os.path.join(directorio, nombre_archivo)
        if os.path.isfile(ruta_archivo) and not nombre_archivo.startswith(".__"):
            extension = os.path.splitext(nombre_archivo)[1]
            tipo_archivo = extension.lower()
            archivo_es_imagen = es_imagen(nombre_archivo)
            fecha_origen = obtener_fecha_origen_imagen(ruta_archivo) if archivo_es_imagen else None
            sin_fecha = fecha_origen is None
            fecha_orden = fecha_origen if fecha_origen is not None else datetime.max
            imagen_sin_fecha = archivo_es_imagen and sin_fecha
            archivos.append(
                (
                    tipo_archivo,
                    sin_fecha,
                    fecha_orden,
                    nombre_archivo.lower(),
                    nombre_archivo,
                    ruta_archivo,
                    extension,
                    imagen_sin_fecha,
                )
            )

    tipos_archivo = {tipo_archivo for tipo_archivo, *_ in archivos}
    varios_tipos = len(tipos_archivo) >= 2

    # Con varios formatos, agrupar primero por extension. Dentro de cada grupo,
    # las imagenes con fecha interna se ordenan de mas antigua a mas reciente.
    if varios_tipos:
        archivos.sort(key=lambda dato: (dato[0], dato[1], dato[2], dato[3]))
    else:
        archivos.sort(key=lambda dato: (dato[1], dato[2], dato[3]))

    temporales = []
    for indice, dato in enumerate(archivos):
        tipo_archivo, _, _, _, nombre_original, ruta_original, extension, imagen_sin_fecha = dato
        ruta_temporal = crear_ruta_temporal(directorio, indice, extension)
        os.rename(ruta_original, ruta_temporal)
        temporales.append(
            (
                tipo_archivo,
                nombre_original,
                ruta_temporal,
                extension,
                imagen_sin_fecha,
            )
        )

    etiquetas_tipo = {}
    for tipo_archivo, _, _, extension, _ in temporales:
        if tipo_archivo not in etiquetas_tipo:
            etiquetas_tipo[tipo_archivo] = extension[1:] if extension else "ARCHIVO"

    contadores = {tipo_archivo: inicio for tipo_archivo in tipos_archivo}
    indice = inicio
    for tipo_archivo, _, ruta_temporal, extension, _ in temporales:
        if varios_tipos:
            numero = contadores[tipo_archivo]
            base_nombre = f"{etiquetas_tipo[tipo_archivo]}_{numero}"
        else:
            numero = indice
            base_nombre = str(numero)

        nuevo_nombre = f"{prefijo}{base_nombre}{sufijo}{extension}"
        nueva_ruta = os.path.join(directorio, nuevo_nombre)

        # Evitar conflictos con carpetas que tengan el mismo nombre.
        while os.path.exists(nueva_ruta):
            numero += 1
            if varios_tipos:
                base_nombre = f"{etiquetas_tipo[tipo_archivo]}_{numero}"
            else:
                base_nombre = str(numero)
            nuevo_nombre = f"{prefijo}{base_nombre}{sufijo}{extension}"
            nueva_ruta = os.path.join(directorio, nuevo_nombre)

        os.rename(ruta_temporal, nueva_ruta)
        if varios_tipos:
            contadores[tipo_archivo] = numero + 1
        else:
            indice = numero + 1

    total_sin_fecha = sum(1 for *_, imagen_sin_fecha in archivos if imagen_sin_fecha)
    return len(archivos), total_sin_fecha


def aplicar_afijos_sin_repetir(nombre: str, prefijo: str, sufijo: str) -> str:
    """Agrega prefijo o sufijo solo si ese extremo aun no los tiene."""
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    base, extension = os.path.splitext(nombre)
    if prefijo and base.lower().startswith(prefijo.lower()):
        prefijo = ""
    if sufijo and base.lower().endswith(sufijo.lower()):
        sufijo = ""
    if not prefijo and not sufijo:
        return nombre
    return f"{prefijo}{base}{sufijo}{extension}"


def renombrar_conservando(directorio, prefijo="", sufijo=""):
    """Mantiene el nombre y solo agrega prefijo o sufijo.

    Devuelve (renombrados, omitido). Omitido es True si no habia nada que cambiar.
    """
    prefijo = afijo(prefijo)
    sufijo = afijo(sufijo)
    nombres = [
        nombre
        for nombre in sorted(os.listdir(directorio), key=str.lower)
        if os.path.isfile(os.path.join(directorio, nombre)) and not nombre.startswith(".__")
    ]
    if not nombres or (not prefijo and not sufijo):
        return 0, True

    cambios = []
    for nombre in nombres:
        nuevo = aplicar_afijos_sin_repetir(nombre, prefijo, sufijo)
        if nuevo != nombre:
            cambios.append((nombre, nuevo))
    if not cambios:
        return 0, True

    temporales = []
    try:
        for indice, (nombre, nuevo) in enumerate(cambios):
            origen = os.path.join(directorio, nombre)
            extension = os.path.splitext(nombre)[1]
            temporal = crear_ruta_temporal(directorio, indice, extension)
            os.rename(origen, temporal)
            temporales.append((temporal, origen, nuevo))
    except Exception:
        for temporal, origen, _nuevo in reversed(temporales):
            if os.path.exists(temporal) and not os.path.exists(origen):
                os.rename(temporal, origen)
        raise

    ocupados = {nombre.lower() for nombre in os.listdir(directorio)}
    for temporal, _origen, nuevo in temporales:
        base, extension = os.path.splitext(nuevo)
        candidato = nuevo
        extra = 1
        while candidato.lower() in ocupados:
            extra += 1
            candidato = f"{base}_{extra}{extension}"
        os.rename(temporal, os.path.join(directorio, candidato))
        ocupados.discard(os.path.basename(temporal).lower())
        ocupados.add(candidato.lower())
    return len(temporales), False


def directorios_objetivo(raiz: str, recursivo: bool) -> list[str]:
    """Carpetas cuyos archivos se van a renombrar. En subcarpetas, cada una aporta su nombre."""
    raiz = os.path.abspath(raiz)
    if not recursivo:
        return [raiz]

    encontrados = []
    for actual, subdirs, archivos in os.walk(raiz):
        subdirs[:] = sorted(subdirs, key=str.lower)
        if any(
            os.path.isfile(os.path.join(actual, nombre)) and not nombre.startswith(".__")
            for nombre in archivos
        ):
            encontrados.append(actual)
    return encontrados


MODOS_RENOMBRADO = ("numerico", "alfabetico", "conservar", "capturas", "reemplazar", "nomenclatura")
CARPETA_FUERA_DE_NORMA = "_sin_nomenclatura"


def nombres_de_carpeta(directorio: str) -> list[str]:
    return [
        nombre
        for nombre in sorted(os.listdir(directorio), key=str.lower)
        if os.path.isfile(os.path.join(directorio, nombre)) and not nombre.startswith(".__")
    ]


def renombrar_reemplazando(directorio, buscar, sustituir, ignorar_mayusculas, prefijo="", sufijo=""):
    """Sustituye texto en los nombres y luego aplica prefijo y sufijo."""
    cambios = []
    for nombre in nombres_de_carpeta(directorio):
        nuevo = reemplazar_en_nombre(nombre, buscar, sustituir, ignorar_mayusculas)
        if nuevo is None:
            continue
        nuevo = aplicar_afijos_sin_repetir(nuevo, prefijo, sufijo)
        if not afijo_valido(nuevo):
            raise ValueError(f"El nombre resultante no es valido: {nuevo}")
        if nuevo != nombre:
            cambios.append(
                CambioNombre(os.path.join(directorio, nombre), os.path.join(directorio, nuevo))
            )
    if not cambios:
        return 0
    return aplicar_plan(cambios)


def separar_nomenclatura(carpeta: str, recursivo: bool) -> None:
    """Muestra los nombres que no siguen la forma comun y puede apartarlos."""
    directorios = [
        directorio
        for directorio in directorios_objetivo(carpeta, recursivo)
        if os.path.basename(directorio).casefold() != CARPETA_FUERA_DE_NORMA.casefold()
    ]
    apartables = []
    sin_forma = []
    for directorio in directorios:
        patron, comunes, fuera = clasificar_nomenclatura(nombres_de_carpeta(directorio))
        if not fuera:
            continue
        if patron:
            apartables.append((directorio, comunes, fuera))
        else:
            sin_forma.append((directorio, fuera))

    if not apartables and not sin_forma:
        messagebox.showinfo(
            "Nomenclatura",
            "Todos los archivos siguen la forma comun de su carpeta.",
        )
        return

    lineas = []
    for directorio, comunes, fuera in apartables:
        lineas.append(
            f"{directorio}\n"
            f"Como el resto: {', '.join(comunes[:3])}\n"
            f"Distintos: {', '.join(fuera[:12])}"
        )
    for directorio, fuera in sin_forma:
        lineas.append(
            f"{directorio}\n"
            f"No hay una forma comun. Nombres: {', '.join(fuera[:12])}"
        )
    texto = "\n\n".join(lineas[:8])
    if not apartables:
        messagebox.showinfo("Fuera de nomenclatura", texto)
        return
    if not messagebox.askyesno(
        "Fuera de nomenclatura",
        texto + f"\n\nMover los distintos a {CARPETA_FUERA_DE_NORMA}?",
    ):
        return

    movidos = 0
    for directorio, _comunes, fuera in apartables:
        destino = os.path.join(directorio, CARPETA_FUERA_DE_NORMA)
        for nombre in fuera:
            mover_sin_conflicto(os.path.join(directorio, nombre), destino)
            movidos += 1
    messagebox.showinfo("Operacion completada", f"Archivos apartados: {movidos}.")


def modo_valido(modo: str | None) -> str:
    if modo in MODOS_RENOMBRADO:
        return modo
    return "numerico"


def construir_interfaz(modo: str = "numerico", mostrar: bool = True) -> tk.Tk:
    """Crea el renombrador. El modo alfabetico usa la funcion del script absorbido."""
    modo = modo_valido(modo)
    root = tk.Tk()
    root.withdraw()
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    modo_var = tk.StringVar(value=modo)
    ayuda_var = tk.StringVar()

    def actualizar_modo():
        if modo_var.get() == "alfabetico":
            root.title("Renombrador alfabetico")
            ayuda_var.set(
                "Asigna nombres a, b, c... segun la fecha de modificacion. "
                "Si hay varios formatos, crea una secuencia por extension."
            )
        elif modo_var.get() == "conservar":
            root.title("Renombrador")
            ayuda_var.set(
                "Conserva el nombre actual y solo agrega el prefijo, el sufijo "
                "o el nombre de la carpeta."
            )
        elif modo_var.get() == "capturas":
            root.title("Numero de capturas")
            ayuda_var.set(
                "En cada carpeta N_capturas antepone solo ese numero. "
                "No vuelve a marcarlo si ya empieza por el."
            )
        elif modo_var.get() == "reemplazar":
            root.title("Reemplazar texto")
            ayuda_var.set(
                "Sustituye un texto dentro del nombre. La extension no cambia. "
                "Dejar vacio el reemplazo borra ese texto."
            )
        elif modo_var.get() == "nomenclatura":
            root.title("Fuera de nomenclatura")
            ayuda_var.set(
                "En cada carpeta, la forma comun es la que mas archivos comparten, "
                "como 132.png frente a un nombre largo. Esos otros se pueden apartar."
            )
        else:
            root.title("Renombrador numerico")
            ayuda_var.set(
                "Ordena por la fecha interna de cada imagen y asigna numeros. "
                "Si hay varios formatos, crea una secuencia por extension."
            )
        modo_actual = modo_var.get()
        es_capturas = modo_actual == "capturas"
        es_norma = modo_actual == "nomenclatura"
        if modo_actual == "reemplazar":
            panel_reemplazo.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        elif panel_reemplazo.winfo_manager() == "grid":
            panel_reemplazo.grid_remove()
        if es_norma:
            if fila_afijos.winfo_manager() == "grid":
                fila_afijos.grid_remove()
        elif not fila_afijos.winfo_manager():
            fila_afijos.grid(row=3, column=0, columnspan=3, sticky="w")
        for control, opciones in (
            (etiqueta_marca, {"row": 6, "column": 0, "sticky": "w"}),
            (posiciones, {"row": 7, "column": 0, "columnspan": 3, "sticky": "w", "pady": (4, 4)}),
            (casilla_subcarpetas, {"row": 8, "column": 0, "columnspan": 3, "sticky": "w", "pady": (0, 8)}),
        ):
            ocultar = es_capturas or (es_norma and control is not casilla_subcarpetas)
            if ocultar:
                if control.winfo_manager() == "grid":
                    control.grid_remove()
            elif not control.winfo_manager():
                control.grid(**opciones)
        if es_capturas:
            boton_renombrar.config(text="Corregir nombres")
        elif es_norma:
            boton_renombrar.config(text="Buscar")
        else:
            boton_renombrar.config(text="Renombrar")

    tk.Label(frame, text="Modo:").grid(row=0, column=0, sticky="w")
    caja_modos = tk.Frame(frame)
    caja_modos.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 8))
    modos = tk.Frame(caja_modos)
    modos.pack(anchor="w")
    tk.Radiobutton(
        modos,
        text="Numerico por fecha",
        variable=modo_var,
        value="numerico",
        command=actualizar_modo,
    ).pack(side="left")
    tk.Radiobutton(
        modos,
        text="Alfabetico (a, b, c...)",
        variable=modo_var,
        value="alfabetico",
        command=actualizar_modo,
    ).pack(side="left", padx=(12, 0))
    tk.Radiobutton(
        modos,
        text="Conservar nombre",
        variable=modo_var,
        value="conservar",
        command=actualizar_modo,
    ).pack(side="left", padx=(12, 0))
    tk.Radiobutton(
        modos,
        text="Numero de capturas",
        variable=modo_var,
        value="capturas",
        command=actualizar_modo,
        ayuda=(
            "Usa el numero de cada carpeta N_capturas. "
            "No se combina con el nombre completo de la carpeta, para no marcarlo dos veces."
        ),
    ).pack(side="left", padx=(12, 0))
    modos_extra = tk.Frame(caja_modos)
    modos_extra.pack(anchor="w", pady=(6, 0))
    tk.Radiobutton(
        modos_extra,
        text="Reemplazar texto",
        variable=modo_var,
        value="reemplazar",
        command=actualizar_modo,
        ayuda="Cambia un trozo del nombre. La extension se queda igual.",
    ).pack(side="left")
    tk.Radiobutton(
        modos_extra,
        text="Fuera de nomenclatura",
        variable=modo_var,
        value="nomenclatura",
        command=actualizar_modo,
        ayuda=(
            "Busca archivos cuyo nombre no sigue la forma que usa la mayoria de la carpeta."
        ),
    ).pack(side="left", padx=(12, 0))
    tk.Label(frame, textvariable=ayuda_var, wraplength=460, justify="left").grid(
        row=2, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    fila_afijos = tk.Frame(frame)
    fila_afijos.grid(row=3, column=0, columnspan=3, sticky="w")
    tk.Label(fila_afijos, text="Prefijo:").grid(row=0, column=0, sticky="w")
    tk.Label(fila_afijos, text="Sufijo:").grid(row=0, column=1, sticky="w", padx=(8, 0))
    prefijo_var = tk.StringVar()
    sufijo_var = tk.StringVar()
    tk.Entry(fila_afijos, textvariable=prefijo_var, width=22).grid(row=1, column=0, sticky="w", pady=(4, 4))
    tk.Entry(fila_afijos, textvariable=sufijo_var, width=22).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 4))

    panel_reemplazo = tk.Frame(frame)
    buscar_var = tk.StringVar()
    sustituir_var = tk.StringVar()
    ignorar_var = tk.BooleanVar(value=True)
    tk.Label(panel_reemplazo, text="Buscar:").grid(row=0, column=0, sticky="w")
    tk.Label(panel_reemplazo, text="Reemplazar por:").grid(row=0, column=1, sticky="w", padx=(8, 0))
    tk.Entry(panel_reemplazo, textvariable=buscar_var, width=22).grid(row=1, column=0, sticky="w", pady=(4, 4))
    tk.Entry(panel_reemplazo, textvariable=sustituir_var, width=22).grid(
        row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 4)
    )
    tk.Checkbutton(
        panel_reemplazo,
        text="Ignorar mayusculas",
        variable=ignorar_var,
        ayuda="Encuentra el texto aunque no coincidan mayusculas y minusculas.",
    ).grid(row=2, column=0, columnspan=2, sticky="w")

    etiqueta_marca = tk.Label(frame, text="Nombre de la carpeta:")
    etiqueta_marca.grid(row=6, column=0, sticky="w")
    posicion_var = tk.StringVar(value="no")
    posiciones = tk.Frame(frame)
    posiciones.grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 4))
    tk.Radiobutton(posiciones, text="No usar", variable=posicion_var, value="no").pack(side="left")
    tk.Radiobutton(posiciones, text="Como prefijo", variable=posicion_var, value="prefijo").pack(
        side="left", padx=(12, 0)
    )
    tk.Radiobutton(posiciones, text="Como sufijo", variable=posicion_var, value="sufijo").pack(
        side="left", padx=(12, 0)
    )
    recursivo_var = tk.BooleanVar(value=False)
    casilla_subcarpetas = tk.Checkbutton(
        frame,
        text="Incluir subcarpetas (cada una usa su propio nombre)",
        variable=recursivo_var,
    )
    casilla_subcarpetas.grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 8))

    tk.Label(frame, text="Carpeta:").grid(row=10, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    entrada = tk.Entry(frame, textvariable=carpeta_var, width=50)
    entrada.grid(row=11, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory()
        if carpeta:
            carpeta_var.set(carpeta)

    def ejecutar_renombrado():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La ruta no existe.")
            return

        modo_actual = modo_var.get()
        prefijo = afijo(prefijo_var.get())
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefijo) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        if modo_actual == "capturas":
            from CorregirNombresCapturas import corregir_nombres, crear_resumen

            if not messagebox.askyesno(
                "Numero de capturas",
                "Se antepone el numero de cada carpeta N_capturas a sus imagenes.\n"
                "Si el archivo ya empieza por ese numero, se deja igual.",
            ):
                return
            try:
                resultado = corregir_nombres(carpeta, prefijo_extra=prefijo, sufijo_extra=sufijo)
            except Exception as exc:
                messagebox.showerror("Error", f"Ocurrio un error: {exc}")
                return
            messagebox.showinfo("Operacion completada", crear_resumen(resultado))
            return

        if modo_actual == "nomenclatura":
            separar_nomenclatura(carpeta, recursivo_var.get())
            return

        if modo_actual == "reemplazar":
            buscar = buscar_var.get()
            if not buscar.strip():
                messagebox.showwarning("Falta texto", "Escriba el texto que hay que buscar en el nombre.")
                return
            sustituir = sustituir_var.get()
            if not afijo_valido(sustituir):
                messagebox.showerror(
                    "Nombre invalido",
                    "El reemplazo contiene caracteres no permitidos en un nombre de archivo.",
                )
                return

        directorios = directorios_objetivo(carpeta, recursivo_var.get())
        if not directorios:
            messagebox.showinfo("Sin archivos", "No se encontraron archivos para renombrar.")
            return

        posicion = posicion_var.get()
        renombrados = 0
        sin_fecha = 0
        carpetas_omitidas = 0
        try:
            for directorio in directorios:
                prefijo_final, sufijo_final = afijos_con_carpeta(directorio, posicion, prefijo, sufijo)
                if modo_actual == "reemplazar":
                    renombrados += renombrar_reemplazando(
                        directorio,
                        buscar,
                        sustituir,
                        ignorar_var.get(),
                        prefijo_final,
                        sufijo_final,
                    )
                    continue
                if modo_actual == "alfabetico":
                    from RenombradorAlfabetico import renombrar_por_alfabeto

                    cantidad, omitido = renombrar_por_alfabeto(directorio, prefijo_final, sufijo_final)
                elif modo_actual == "conservar":
                    cantidad, omitido = renombrar_conservando(directorio, prefijo_final, sufijo_final)
                else:
                    cantidad, faltantes = renombrar_por_fecha_origen(directorio, prefijo_final, 1, sufijo_final)
                    omitido = False
                    sin_fecha += faltantes
                if omitido:
                    carpetas_omitidas += 1
                else:
                    renombrados += cantidad
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        if modo_actual in ("alfabetico", "conservar", "reemplazar") and renombrados == 0:
            messagebox.showinfo(
                "Sin cambios",
                "Los archivos ya tenian el nombre esperado.",
            )
            return

        if renombrados == 0:
            messagebox.showinfo("Sin archivos", "No se encontraron archivos para renombrar.")
            return

        mensaje = f"Renombrado finalizado. Archivos: {renombrados}."
        if carpetas_omitidas:
            mensaje += f"\nCarpetas que ya estaban listas: {carpetas_omitidas}."
        if sin_fecha:
            mensaje += f"\n\n{sin_fecha} imagen(es) no tenian fecha interna y se colocaron al final."
        messagebox.showinfo("Operacion completada", mensaje)

    tk.Button(frame, text="Examinar", command=seleccionar_carpeta).grid(row=11, column=2, pady=(4, 8))
    boton_renombrar = tk.Button(frame, text="Renombrar", command=ejecutar_renombrado)
    boton_renombrar.grid(row=12, column=0, columnspan=3, sticky="we")
    root.marca_carpeta = posiciones
    root.panel_reemplazo = panel_reemplazo
    root.fila_afijos = fila_afijos
    actualizar_modo()
    entrada.focus_set()
    root.modo_var = modo_var
    if mostrar:
        root.deiconify()
    return root


def main(modo: str = "numerico"):
    construir_interfaz(modo_valido(modo)).mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renombra los archivos de una carpeta.")
    parser.add_argument("--modo", choices=MODOS_RENOMBRADO, default="numerico")
    main(modo=parser.parse_args().modo)
