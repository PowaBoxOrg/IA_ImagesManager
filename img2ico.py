import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox


def convertir_a_ico(ruta_entrada: str, ruta_salida: str | None = None, tamanos=(16, 24, 32, 48, 64, 128, 256)):
    """Convierte una imagen a .ico con multiples resoluciones."""
    try:
        if ruta_salida is None:
            ruta_salida = os.path.splitext(ruta_entrada)[0] + ".ico"

        with Image.open(ruta_entrada) as img:
            # ICO suele requerir RGBA para manejar transparencia de forma consistente.
            img = img.convert("RGBA")

            imagenes = []
            for size in tamanos:
                img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
                imagenes.append(img_resized)

            imagenes[0].save(
                ruta_salida,
                format="ICO",
                sizes=[(size, size) for size in tamanos],
                append_images=imagenes[1:],
            )

        return True, ruta_salida
    except Exception as exc:
        return False, str(exc)


def main():
    root = tk.Tk()
    root.title("Img2Ico")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Entrada
    tk.Label(frame, text="Imagen:").grid(row=0, column=0, sticky="w")
    entrada_var = tk.StringVar()
    entrada_entry = tk.Entry(frame, textvariable=entrada_var, width=50)
    entrada_entry.grid(row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_imagen():
        tipos_imagen = [
            ("Imagenes", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.gif;*.webp;*.avif"),
            ("Todos", "*.*"),
        ]
        archivo = filedialog.askopenfilename(title="Seleccionar imagen", filetypes=tipos_imagen)
        if archivo:
            entrada_var.set(archivo)
            # Sugerir salida automaticamente si esta vacia
            if not salida_var.get().strip():
                salida_var.set(os.path.splitext(archivo)[0] + ".ico")

    tk.Button(frame, text="Examinar", command=seleccionar_imagen).grid(row=1, column=2, pady=(4, 8))

    # Salida
    tk.Label(frame, text="Salida (.ico):").grid(row=2, column=0, sticky="w")
    salida_var = tk.StringVar()
    salida_entry = tk.Entry(frame, textvariable=salida_var, width=50)
    salida_entry.grid(row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_salida():
        path = filedialog.asksaveasfilename(
            title="Guardar icono como",
            defaultextension=".ico",
            filetypes=[("Icono", "*.ico"), ("Todos", "*.*")],
        )
        if path:
            salida_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_salida).grid(row=3, column=2, pady=(4, 8))

    # Tamanos
    tk.Label(frame, text="Tamanos:").grid(row=4, column=0, sticky="w")

    size_specs = [(16, "16x16"), (24, "24x24"), (32, "32x32"), (48, "48x48"), (64, "64x64"), (128, "128x128"), (256, "256x256")]
    size_vars = []

    sizes_frame = tk.Frame(frame)
    sizes_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 8))

    for i, (size, label) in enumerate(size_specs):
        var = tk.BooleanVar(value=True)
        size_vars.append((var, size))
        tk.Checkbutton(sizes_frame, text=label, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=5)

    def iniciar_conversion():
        ruta_entrada = entrada_var.get().strip()
        ruta_salida = salida_var.get().strip() or None

        if not ruta_entrada:
            messagebox.showwarning("Falta imagen", "Seleccione una imagen de entrada.")
            return
        if not os.path.isfile(ruta_entrada):
            messagebox.showerror("Ruta invalida", "La imagen no existe.")
            return

        tamanos = [size for (var, size) in size_vars if var.get()]
        if not tamanos:
            messagebox.showwarning("Faltan tamanos", "Seleccione al menos un tamano.")
            return

        if ruta_salida is not None and not ruta_salida.lower().endswith(".ico"):
            ruta_salida = ruta_salida + ".ico"
            salida_var.set(ruta_salida)

        exito, resultado = convertir_a_ico(ruta_entrada, ruta_salida, tuple(tamanos))
        if exito:
            messagebox.showinfo("Operacion completada", f"Icono creado:\n{resultado}")
        else:
            messagebox.showerror("Error", f"No se pudo crear el icono:\n{resultado}")

    tk.Button(frame, text="Convertir", command=iniciar_conversion).grid(row=6, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
