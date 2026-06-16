"""
Conversor y organizador por lotes de imagenes JPG, JPEG, WEBP y AVIF.

El script abre una interfaz grafica sencilla desde la que se puede seleccionar
una carpeta y procesar todas las imagenes compatibles que se encuentren
directamente en ella. El contenido de las subcarpetas no se recorre.

Antes de convertirlas, las imagenes se ordenan con el mismo criterio que el
renombrador numerico: primero por formato y, dentro de cada formato, por la
fecha interna de la imagen de mas antigua a mas reciente. Las imagenes sin fecha
interna se colocan al final y se ordenan por su nombre original. Despues reciben
nombres como "jpg_1.jpg", "webp_1.webp" o "avif_1.avif".

El programa crea dentro de la carpeta elegida una subcarpeta llamada
"Convertidas_PNG", donde guarda las conversiones con nombres como "jpg_1.png".
Tambien crea una carpeta para los originales de cada formato encontrado, por
ejemplo "Originales_JPG", "Originales_JPEG", "Originales_WEBP" y
"Originales_AVIF". Tras intentar la conversion, cada original renombrado se
mueve a su carpeta correspondiente.

La numeracion evita reemplazar archivos que ya existan tanto en las carpetas de
originales como en "Convertidas_PNG", por lo que las ejecuciones posteriores
utilizan el siguiente numero disponible.

Al finalizar, la interfaz indica cuantos archivos se convirtieron y cuantos
originales se organizaron. Si uno o varios archivos no pueden abrirse,
guardarse o moverse, el procesamiento continua con los demas y se muestra un
resumen con la cantidad de errores.

Dependencias:

- Python con Tkinter para la interfaz grafica.
- Pillow (PIL) para leer las imagenes y escribir los archivos PNG.
- pillow-avif-plugin para habilitar AVIF cuando la instalacion de Pillow no lo
  soporte por si sola.

La compatibilidad efectiva con cada formato depende de los codecs disponibles
en la version de Pillow instalada en el equipo.
"""

import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image

from RenombradorNumerico import crear_ruta_temporal, obtener_fecha_origen_imagen

try:
    # Soporte AVIF para Pillow cuando esta instalado `pillow-avif-plugin`.
    import pillow_avif  # type: ignore # noqa: F401
except Exception:
    pillow_avif = None


FORMATOS_COMPATIBLES = {
    ".jpg": "JPG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".avif": "AVIF",
}
NOMBRE_CARPETA_PNG = "Convertidas_PNG"
PREFIJO_CARPETA_ORIGINALES = "Originales_"


def convert_webp_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    with Image.open(input_path) as img:
        img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def convert_jpg_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    with Image.open(input_path) as img:
        img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def convert_avif_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    with Image.open(input_path) as img:
        img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def obtener_imagenes_compatibles(folder_path):
    imagenes = []

    for file_name in sorted(os.listdir(folder_path), key=str.lower):
        input_path = os.path.join(folder_path, file_name)
        if not os.path.isfile(input_path):
            continue

        extension = os.path.splitext(file_name)[1].lower()
        if extension not in FORMATOS_COMPATIBLES:
            continue

        fecha_origen = obtener_fecha_origen_imagen(input_path)
        imagenes.append(
            {
                "nombre_original": file_name,
                "ruta_original": input_path,
                "extension": extension,
                "fecha_origen": fecha_origen,
            }
        )

    tipos_encontrados = {imagen["extension"] for imagen in imagenes}
    varios_tipos = len(tipos_encontrados) >= 2

    if varios_tipos:
        imagenes.sort(
            key=lambda imagen: (
                imagen["extension"],
                imagen["fecha_origen"] is None,
                imagen["fecha_origen"] or datetime.max,
                imagen["nombre_original"].lower(),
            )
        )
    else:
        imagenes.sort(
            key=lambda imagen: (
                imagen["fecha_origen"] is None,
                imagen["fecha_origen"] or datetime.max,
                imagen["nombre_original"].lower(),
            )
        )

    return imagenes


def renombrar_imagenes_por_formato(folder_path, imagenes, output_dir):
    temporales = []

    try:
        for indice, imagen in enumerate(imagenes):
            ruta_temporal = crear_ruta_temporal(
                folder_path,
                indice,
                imagen["extension"],
            )
            os.rename(imagen["ruta_original"], ruta_temporal)
            imagen["ruta_temporal"] = ruta_temporal
            temporales.append(imagen)
    except Exception:
        for imagen in reversed(temporales):
            if os.path.exists(imagen["ruta_temporal"]):
                os.rename(imagen["ruta_temporal"], imagen["ruta_original"])
        raise

    contadores = {extension: 1 for extension in FORMATOS_COMPATIBLES}
    renombradas = []

    try:
        for imagen in temporales:
            extension = imagen["extension"]
            etiqueta = extension[1:]
            carpeta_originales = os.path.join(
                folder_path,
                f"{PREFIJO_CARPETA_ORIGINALES}{FORMATOS_COMPATIBLES[extension]}",
            )
            os.makedirs(carpeta_originales, exist_ok=True)

            numero = contadores[extension]
            while True:
                nombre_nuevo = f"{etiqueta}_{numero}{extension}"
                nombre_png = f"{etiqueta}_{numero}.png"
                ruta_renombrada = os.path.join(folder_path, nombre_nuevo)
                ruta_original_destino = os.path.join(carpeta_originales, nombre_nuevo)
                ruta_png = os.path.join(output_dir, nombre_png)

                if not any(
                    os.path.exists(ruta)
                    for ruta in (ruta_renombrada, ruta_original_destino, ruta_png)
                ):
                    break
                numero += 1

            os.rename(imagen["ruta_temporal"], ruta_renombrada)
            contadores[extension] = numero + 1
            imagen.update(
                {
                    "nombre_nuevo": nombre_nuevo,
                    "ruta_renombrada": ruta_renombrada,
                    "ruta_original_destino": ruta_original_destino,
                    "ruta_png": ruta_png,
                }
            )
            renombradas.append(imagen)
    except Exception:
        for imagen in reversed(imagenes):
            ruta_actual = imagen.get("ruta_renombrada", imagen.get("ruta_temporal"))
            if ruta_actual and os.path.exists(ruta_actual):
                os.rename(ruta_actual, imagen["ruta_original"])
        raise

    return renombradas


def convertir_imagen(input_path, output_path, extension):
    if extension in (".jpg", ".jpeg"):
        convert_jpg_to_png(input_path, output_path)
    elif extension == ".webp":
        convert_webp_to_png(input_path, output_path)
    elif extension == ".avif":
        convert_avif_to_png(input_path, output_path)


def convert_folder_images_to_png(folder_path):
    converted = 0
    organized = 0
    errors = []

    output_dir = os.path.join(folder_path, NOMBRE_CARPETA_PNG)
    os.makedirs(output_dir, exist_ok=True)

    imagenes = obtener_imagenes_compatibles(folder_path)
    renombradas = renombrar_imagenes_por_formato(folder_path, imagenes, output_dir)

    for imagen in renombradas:
        try:
            convertir_imagen(
                imagen["ruta_renombrada"],
                imagen["ruta_png"],
                imagen["extension"],
            )
            converted += 1
        except Exception as exc:
            if imagen["extension"] == ".avif" and pillow_avif is None:
                detalle = (
                    "AVIF no soportado en esta instalacion. "
                    "Instala `pillow-avif-plugin` y reintenta."
                )
            else:
                detalle = str(exc)
            errors.append((imagen["nombre_nuevo"], f"Conversion: {detalle}"))

        try:
            os.rename(imagen["ruta_renombrada"], imagen["ruta_original_destino"])
            organized += 1
        except Exception as exc:
            errors.append(
                (
                    imagen["nombre_nuevo"],
                    f"No se pudo mover el original: {exc}",
                )
            )

    return converted, organized, errors


def main():
    root = tk.Tk()
    root.title("Img2Img (JPG/WEBP/AVIF a PNG)")
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

    def ejecutar_conversion():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La ruta no existe.")
            return

        try:
            converted, organized, errors = convert_folder_images_to_png(carpeta)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        if converted == 0 and organized == 0 and not errors:
            messagebox.showinfo(
                "Sin imagenes",
                "No se encontraron imagenes JPG, JPEG, WEBP o AVIF para procesar.",
            )
            return

        if errors:
            # Mostramos un resumen corto para no saturar el cuadro de dialogo.
            messagebox.showwarning(
                "Conversion parcial",
                f"Convertidos: {converted}\n"
                f"Originales organizados: {organized}\n"
                f"Errores: {len(errors)}",
            )
            return

        messagebox.showinfo(
            "Operacion completada",
            f"Convertidos: {converted}\n"
            f"Originales organizados: {organized}\n"
            f"PNG guardados en: {NOMBRE_CARPETA_PNG}",
        )

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    boton_ejecutar = tk.Button(frame, text="Convertir", command=ejecutar_conversion)
    boton_ejecutar.grid(row=2, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
