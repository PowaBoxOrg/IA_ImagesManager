from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    # Soporte AVIF para Pillow cuando esta instalado `pillow-avif-plugin`.
    import pillow_avif  # type: ignore # noqa: F401
except Exception:
    pillow_avif = None


def convert_webp_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def convert_jpg_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def convert_avif_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"

    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print(f"Convertido: {input_path} -> {output_path}")


def convert_folder_images_to_png(folder_path):
    converted = 0
    errors = []

    for file_name in os.listdir(folder_path):
        input_path = os.path.join(folder_path, file_name)
        if not os.path.isfile(input_path):
            continue

        lower_name = file_name.lower()
        output_path = os.path.splitext(input_path)[0] + ".png"

        if lower_name.endswith((".jpg", ".jpeg")):
            try:
                convert_jpg_to_png(input_path, output_path)
                converted += 1
            except Exception as exc:
                errors.append((file_name, str(exc)))

        elif lower_name.endswith(".webp"):
            try:
                convert_webp_to_png(input_path, output_path)
                converted += 1
            except Exception as exc:
                errors.append((file_name, str(exc)))

        elif lower_name.endswith(".avif"):
            try:
                convert_avif_to_png(input_path, output_path)
                converted += 1
            except Exception as exc:
                if pillow_avif is None:
                    errors.append(
                        (
                            file_name,
                            "AVIF no soportado en esta instalacion. Instala `pillow-avif-plugin` y reintenta.",
                        )
                    )
                else:
                    errors.append((file_name, str(exc)))

    return converted, errors


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
            converted, errors = convert_folder_images_to_png(carpeta)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        if errors:
            # Mostramos un resumen corto para no saturar el cuadro de dialogo.
            messagebox.showwarning(
                "Conversion parcial",
                f"Convertidos: {converted}\nErrores: {len(errors)}",
            )
            return

        messagebox.showinfo(
            "Operacion completada",
            f"Convertidos: {converted}",
        )

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    boton_ejecutar = tk.Button(frame, text="Convertir", command=ejecutar_conversion)
    boton_ejecutar.grid(row=2, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
