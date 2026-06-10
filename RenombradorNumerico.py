import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

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


def renombrar_por_fecha_origen(directorio, prefijo, inicio=1):
    # Obtener todos los archivos. Las carpetas quedan intactas.
    archivos = []
    for nombre_archivo in sorted(os.listdir(directorio), key=str.lower):
        ruta_archivo = os.path.join(directorio, nombre_archivo)
        if os.path.isfile(ruta_archivo):
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

        nuevo_nombre = f"{prefijo}{base_nombre}{extension}"
        nueva_ruta = os.path.join(directorio, nuevo_nombre)

        # Evitar conflictos con carpetas que tengan el mismo nombre.
        while os.path.exists(nueva_ruta):
            numero += 1
            if varios_tipos:
                base_nombre = f"{etiquetas_tipo[tipo_archivo]}_{numero}"
            else:
                base_nombre = str(numero)
            nuevo_nombre = f"{prefijo}{base_nombre}{extension}"
            nueva_ruta = os.path.join(directorio, nuevo_nombre)

        os.rename(ruta_temporal, nueva_ruta)
        if varios_tipos:
            contadores[tipo_archivo] = numero + 1
        else:
            indice = numero + 1

    total_sin_fecha = sum(1 for *_, imagen_sin_fecha in archivos if imagen_sin_fecha)
    return len(archivos), total_sin_fecha


def main():
    root = tk.Tk()
    root.title("Renombrador numerico")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta:").grid(row=0, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    entrada = tk.Entry(frame, textvariable=carpeta_var, width=50)
    entrada.grid(row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

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

        prefijo = ""
        inicio = 1
        try:
            total, sin_fecha = renombrar_por_fecha_origen(carpeta, prefijo, inicio)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        if total == 0:
            messagebox.showinfo("Sin archivos", "No se encontraron archivos para renombrar.")
            return

        mensaje = "Renombrado finalizado."
        if sin_fecha:
            mensaje += f"\n\n{sin_fecha} imagen(es) no tenian fecha interna y se colocaron al final."

        messagebox.showinfo("Operacion completada", mensaje)

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    boton_ejecutar = tk.Button(frame, text="Renombrar", command=ejecutar_renombrado)
    boton_ejecutar.grid(row=2, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
