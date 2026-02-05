import os
import shutil
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


EXTENSIONES_VALIDAS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp", ".avif")


def obtener_valor_numerico(nombre: str) -> int:
    partes = "".join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0


def construir_hash_dict(carpeta_fuente: str):
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")
    if imagehash is None:
        raise RuntimeError(f"No se pudo importar imagehash. Detalle: {_imagehash_import_error}")

    hash_dict: dict[str, list[str]] = {}
    scanned = 0
    errors: list[tuple[str, str]] = []

    for root, _, files in os.walk(carpeta_fuente):
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
                    key = str(hash_img)
                    hash_dict.setdefault(key, []).append(path)
            except Exception as exc:
                errors.append((path, str(exc)))

    return hash_dict, scanned, errors


def mover_duplicados(hash_dict: dict[str, list[str]], carpeta_destino: str):
    os.makedirs(carpeta_destino, exist_ok=True)

    moved = 0
    dup_groups = 0
    errors: list[tuple[str, str]] = []

    for _, paths in hash_dict.items():
        if len(paths) <= 1:
            continue

        dup_groups += 1

        # Mantener el de menor valor numerico en el nombre; mover el resto.
        paths.sort(key=lambda p: obtener_valor_numerico(os.path.basename(p)))
        duplicados = paths[1:]

        for dup_path in duplicados:
            try:
                nombre_archivo = os.path.basename(dup_path)
                destino = os.path.join(carpeta_destino, nombre_archivo)

                # Evitar conflictos de nombre en destino
                contador = 1
                while os.path.exists(destino):
                    nombre, ext = os.path.splitext(nombre_archivo)
                    nuevo_nombre = f"{nombre}_{contador}{ext}"
                    destino = os.path.join(carpeta_destino, nuevo_nombre)
                    contador += 1

                shutil.move(dup_path, destino)
                moved += 1
                print(f"Movido: {dup_path} -> {destino}")
            except Exception as exc:
                errors.append((dup_path, str(exc)))

    return {"moved": moved, "groups": dup_groups, "errors": errors}


def main():
    root = tk.Tk()
    root.title("Mover imagenes repetidas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Carpeta fuente
    tk.Label(frame, text="Carpeta fuente:").grid(row=0, column=0, sticky="w")
    fuente_var = tk.StringVar()
    tk.Entry(frame, textvariable=fuente_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_fuente():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta fuente")
        if carpeta:
            fuente_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_fuente).grid(row=1, column=2, pady=(4, 8))

    # Carpeta destino
    tk.Label(frame, text="Carpeta destino:").grid(row=2, column=0, sticky="w")
    destino_var = tk.StringVar()
    tk.Entry(frame, textvariable=destino_var, width=50).grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_destino():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta destino")
        if carpeta:
            destino_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_destino).grid(row=3, column=2, pady=(4, 8))

    nota = (
        "Detecta duplicados por pHash y mueve los repetidos a la carpeta destino, "
        "manteniendo en la fuente el archivo con menor valor numerico en el nombre."  # ej: 001.png < 010.png
    )
    tk.Label(frame, text=nota, justify="left", wraplength=460).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def ejecutar():
        fuente = fuente_var.get().strip()
        destino = destino_var.get().strip()

        if not fuente:
            messagebox.showwarning("Falta fuente", "Seleccione una carpeta fuente.")
            return
        if not os.path.isdir(fuente):
            messagebox.showerror("Ruta invalida", "La carpeta fuente no existe.")
            return

        if not destino:
            messagebox.showwarning("Falta destino", "Seleccione una carpeta destino.")
            return

        fuente_abs = os.path.abspath(fuente)
        destino_abs = os.path.abspath(destino)
        if fuente_abs == destino_abs:
            messagebox.showerror("Destino invalido", "La carpeta destino no puede ser la misma que la fuente.")
            return

        try:
            hash_dict, scanned, scan_errors = construir_hash_dict(fuente_abs)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error al escanear:\n\n{exc}")
            return

        resultado = mover_duplicados(hash_dict, destino_abs)
        moved = resultado["moved"]
        groups = resultado["groups"]
        move_errors = resultado["errors"]

        if scanned == 0:
            messagebox.showinfo("Sin imagenes", "No se encontraron imagenes para procesar.")
            return

        total_errors = len(scan_errors) + len(move_errors)
        if moved == 0 and groups == 0:
            if total_errors:
                messagebox.showwarning(
                    "Sin duplicados (con errores)",
                    f"Imagenes analizadas: {scanned}\nErrores: {total_errors}",
                )
            else:
                messagebox.showinfo("Sin duplicados", f"Imagenes analizadas: {scanned}\nNo se detectaron duplicados.")
            return

        if total_errors:
            messagebox.showwarning(
                "Operacion completada (con errores)",
                f"Imagenes analizadas: {scanned}\nGrupos duplicados: {groups}\nMovidos: {moved}\nErrores: {total_errors}",
            )
            return

        messagebox.showinfo(
            "Operacion completada",
            f"Imagenes analizadas: {scanned}\nGrupos duplicados: {groups}\nMovidos: {moved}",
        )

    tk.Button(frame, text="Buscar y mover duplicados", command=ejecutar).grid(
        row=5, column=0, columnspan=3, sticky="we"
    )

    root.mainloop()


if __name__ == "__main__":
    main()
