import os
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    Image = None
    _pil_import_error = str(exc)

try:
    import imagehash
except Exception as exc:  # pragma: no cover
    imagehash = None
    _imagehash_import_error = str(exc)


EXTENSIONES_VALIDAS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".avif")


def obtener_hashes(carpeta: str):
    """Obtiene hashes pHash de todas las imagenes en una carpeta.

    Devuelve: (hashes, scanned, errors)
    - hashes: dict[str_hash, path]
    """
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")
    if imagehash is None:
        raise RuntimeError(f"No se pudo importar imagehash. Detalle: {_imagehash_import_error}")

    hashes: dict[str, str] = {}
    scanned = 0
    errors: list[tuple[str, str]] = []

    for root, _, files in os.walk(carpeta):
        for filename in files:
            if not filename.lower().endswith(EXTENSIONES_VALIDAS):
                continue

            path = os.path.join(root, filename)
            if not os.path.isfile(path):
                continue

            scanned += 1
            try:
                with Image.open(path) as img:
                    hash_img = imagehash.phash(img)
                    hashes[str(hash_img)] = path
            except Exception as exc:
                errors.append((path, str(exc)))

    return hashes, scanned, errors


def ordenar_por_nombre_numerico(item):
    # item: (hash, path)
    nombre = os.path.basename(item[1])
    partes = "".join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else nombre.lower()


def comparar_carpetas(carpeta_original: str, carpeta_repetidas: str):
    hashes_original, scanned_orig, errors_orig = obtener_hashes(carpeta_original)
    hashes_repetidas, scanned_rep, errors_rep = obtener_hashes(carpeta_repetidas)

    hashes_repetidas_ordenados = dict(sorted(hashes_repetidas.items(), key=ordenar_por_nombre_numerico))

    coincidencias = []
    for hash_val, ruta_rep in hashes_repetidas_ordenados.items():
        ruta_orig = hashes_original.get(hash_val)
        if ruta_orig:
            coincidencias.append((ruta_rep, ruta_orig))

    return {
        "orig_count": len(hashes_original),
        "rep_count": len(hashes_repetidas),
        "scanned_orig": scanned_orig,
        "scanned_rep": scanned_rep,
        "errors": errors_orig + errors_rep,
        "matches": coincidencias,
    }


def main():
    root = tk.Tk()
    root.title("Comparar repetidos (2 carpetas)")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Carpeta original
    tk.Label(frame, text="Carpeta original:").grid(row=0, column=0, sticky="w")
    orig_var = tk.StringVar()
    tk.Entry(frame, textvariable=orig_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_orig():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta original")
        if carpeta:
            orig_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=sel_orig).grid(row=1, column=2, pady=(4, 8))

    # Carpeta repetidas
    tk.Label(frame, text="Carpeta repetidas:").grid(row=2, column=0, sticky="w")
    rep_var = tk.StringVar()
    tk.Entry(frame, textvariable=rep_var, width=50).grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_rep():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta repetidas")
        if carpeta:
            rep_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=sel_rep).grid(row=3, column=2, pady=(4, 8))

    # Resultado (resumen)
    resumen_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=resumen_var, justify="left", wraplength=460).grid(
        row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    def ejecutar():
        if Image is None:
            messagebox.showerror("Pillow no disponible", f"No se pudo importar Pillow (PIL).\n\n{_pil_import_error}")
            return
        if imagehash is None:
            messagebox.showerror("imagehash no disponible", f"No se pudo importar imagehash.\n\n{_imagehash_import_error}")
            return

        carpeta_original = orig_var.get().strip()
        carpeta_repetidas = rep_var.get().strip()

        if not carpeta_original:
            messagebox.showwarning("Falta carpeta", "Seleccione la carpeta original.")
            return
        if not os.path.isdir(carpeta_original):
            messagebox.showerror("Ruta invalida", "La carpeta original no existe.")
            return

        if not carpeta_repetidas:
            messagebox.showwarning("Falta carpeta", "Seleccione la carpeta de repetidas.")
            return
        if not os.path.isdir(carpeta_repetidas):
            messagebox.showerror("Ruta invalida", "La carpeta de repetidas no existe.")
            return

        if os.path.abspath(carpeta_original) == os.path.abspath(carpeta_repetidas):
            messagebox.showerror("Carpetas invalidas", "Las carpetas no pueden ser la misma.")
            return

        try:
            info = comparar_carpetas(carpeta_original, carpeta_repetidas)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}")
            return

        matches = info["matches"]
        errors = info["errors"]

        resumen = (
            f"Original (hashes): {info['orig_count']} (imagenes leidas: {info['scanned_orig']})\n"
            f"Repetidas (hashes): {info['rep_count']} (imagenes leidas: {info['scanned_rep']})\n"
            f"Coincidencias: {len(matches)}\n"
            f"Errores: {len(errors)}"
        )
        resumen_var.set(resumen)

        if not matches:
            if errors:
                messagebox.showwarning("Sin coincidencias", f"No se encontraron coincidencias.\n\n{resumen}")
            else:
                messagebox.showinfo("Sin coincidencias", f"No se encontraron coincidencias.\n\n{resumen}")
            return

        # Mostrar un preview en dialogo (sin saturar)
        preview_lines = [f"{os.path.basename(r)} -> {os.path.basename(o)}" for (r, o) in matches[:30]]
        preview = "\n".join(preview_lines)
        if len(matches) > 30:
            preview += f"\n... (+{len(matches) - 30} mas)"

        if errors:
            messagebox.showwarning("Coincidencias encontradas", f"{resumen}\n\nPrimeras coincidencias:\n{preview}")
        else:
            messagebox.showinfo("Coincidencias encontradas", f"{resumen}\n\nPrimeras coincidencias:\n{preview}")

    tk.Button(frame, text="Comparar", command=ejecutar).grid(row=5, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
