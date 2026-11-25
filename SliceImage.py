import os
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema
from PIL import Image

from motores.renombrado import afijo, afijo_valido, nombre_con_afijos, nombre_pieza


def slice_image_to_tiles(
    image_path: str,
    output_dir: str,
    tile_size: int,
    prefix: str = "icon",
    sufijo: str = "",
):
    prefix = afijo(prefix) or "icon"
    sufijo = afijo(sufijo)
    if tile_size <= 0:
        raise ValueError("El tamano del tile debe ser mayor que 0.")

    img = Image.open(image_path)
    width, height = img.size

    os.makedirs(output_dir, exist_ok=True)

    cols = width // tile_size
    rows = height // tile_size

    saved = 0
    for row in range(rows):
        for col in range(cols):
            left = col * tile_size
            upper = row * tile_size
            right = left + tile_size
            lower = upper + tile_size
            tile = img.crop((left, upper, right, lower))
            nombre = nombre_con_afijos(nombre_pieza(image_path, prefix, row, col), "", sufijo)
            tile.save(os.path.join(output_dir, nombre))
            saved += 1

    return {
        "saved": saved,
        "rows": rows,
        "cols": cols,
        "width": width,
        "height": height,
    }


def main():
    root = tk.Tk()
    root.title("SliceImage (cortar en tiles)")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Imagen
    tk.Label(frame, text="Imagen:").grid(row=0, column=0, sticky="w")
    image_var = tk.StringVar()
    image_entry = tk.Entry(frame, textvariable=image_var, width=50)
    image_entry.grid(row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_imagen():
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imagenes", "*.png;*.jpg;*.jpeg;*.webp;*.avif;*.bmp;*.gif;*.tiff"),
                ("Todos", "*.*"),
            ],
        )
        if path:
            image_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_imagen).grid(row=1, column=2, pady=(4, 8))

    # Carpeta de salida
    tk.Label(frame, text="Salida:").grid(row=2, column=0, sticky="w")
    output_var = tk.StringVar()
    output_entry = tk.Entry(frame, textvariable=output_var, width=50)
    output_entry.grid(row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_salida():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if carpeta:
            output_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_salida).grid(row=3, column=2, pady=(4, 8))

    # Parametros
    tk.Label(frame, text="Tile (px):").grid(row=4, column=0, sticky="w")
    tile_var = tk.StringVar(value="32")
    tk.Entry(frame, textvariable=tile_var, width=12).grid(row=5, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Prefijo:").grid(row=4, column=1, sticky="w")
    prefix_var = tk.StringVar(value="icon")
    tk.Entry(
        frame,
        textvariable=prefix_var,
        width=16,
        ayuda="Texto de cada mosaico. Vacio: se usa icon.",
    ).grid(row=5, column=1, pady=(4, 8), sticky="w")
    tk.Label(frame, text="Sufijo:").grid(row=4, column=2, sticky="w")
    sufijo_var = tk.StringVar()
    tk.Entry(frame, textvariable=sufijo_var, width=16).grid(row=5, column=2, pady=(4, 8), sticky="w")

    def ejecutar_slice():
        image_path = image_var.get().strip()
        output_dir = output_var.get().strip()
        prefix = afijo(prefix_var.get()) or "icon"
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefix) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        if not image_path:
            messagebox.showwarning("Falta imagen", "Seleccione una imagen.")
            return
        if not os.path.isfile(image_path):
            messagebox.showerror("Ruta invalida", "La imagen no existe.")
            return

        if not output_dir:
            messagebox.showwarning("Falta salida", "Seleccione una carpeta de salida.")
            return

        try:
            tile_size = int(tile_var.get().strip())
        except Exception:
            messagebox.showerror("Dato invalido", "Tile (px) debe ser un numero entero.")
            return

        try:
            info = slice_image_to_tiles(image_path, output_dir, tile_size, prefix, sufijo)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        # Aviso si no calza exacto
        if info["width"] % tile_size != 0 or info["height"] % tile_size != 0:
            messagebox.showwarning(
                "Operacion completada (recorte)",
                f"Guardados: {info['saved']}\nGrid: {info['rows']}x{info['cols']}\n"
                "Nota: la imagen no es divisible exacto por el tile; se ignoro el sobrante.",
            )
            return

        messagebox.showinfo(
            "Operacion completada",
            f"Guardados: {info['saved']}\nGrid: {info['rows']}x{info['cols']}",
        )

    tk.Button(frame, text="Cortar", command=ejecutar_slice).grid(row=7, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
