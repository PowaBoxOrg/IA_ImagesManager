import os
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import defaultdict
from datetime import datetime

try:
    import imagehash
except Exception as exc:  # pragma: no cover
    imagehash = None
    _imagehash_import_error = str(exc)

try:
    from PIL import Image, ImageTk
except Exception as exc:  # pragma: no cover
    Image = None
    ImageTk = None
    _pil_import_error = str(exc)


EXTENSIONES_VALIDAS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif")
RANGO_NUMERICO_MINIMO = 10  # solo mostrar grupos cuyo rango numerico sea > 10


def obtener_valor_numerico(nombre: str) -> int:
    """Extrae el valor numerico del nombre del archivo."""
    partes = "".join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0


def encontrar_imagenes_duplicadas(carpeta: str, umbral_similitud: int = 5):
    """Encuentra imagenes duplicadas o similares (por pHash) dentro de una carpeta.

    `umbral_similitud` es la diferencia maxima permitida entre hashes.
    0 = identicas.

    Devuelve dict[hash, list[rutas]] filtrando solo grupos con rango numerico > RANGO_NUMERICO_MINIMO.
    """
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")
    if imagehash is None:
        raise RuntimeError(f"No se pudo importar imagehash. Detalle: {_imagehash_import_error}")

    # Almacenar hashes de imagenes
    hash_imagenes: dict[object, list[str]] = defaultdict(list)

    for nombre_archivo in os.listdir(carpeta):
        ruta_archivo = os.path.join(carpeta, nombre_archivo)

        if not os.path.isfile(ruta_archivo) or not nombre_archivo.lower().endswith(EXTENSIONES_VALIDAS):
            continue

        try:
            with Image.open(ruta_archivo) as img:
                img_gris = img.convert("L")
                hash_img = imagehash.phash(img_gris)

                # Agrupar por hashes similares
                encontrado = False
                for hash_existente in list(hash_imagenes.keys()):
                    if hash_img - hash_existente <= umbral_similitud:
                        hash_imagenes[hash_existente].append(ruta_archivo)
                        encontrado = True
                        break

                if not encontrado:
                    hash_imagenes[hash_img].append(ruta_archivo)
        except Exception as exc:
            print(f"Error al procesar {ruta_archivo}: {exc}")

    # Filtrar solo grupos con duplicados y rango numerico fuera de +/-10
    duplicados_filtrados: dict[object, list[str]] = {}
    for hash_img, rutas in hash_imagenes.items():
        if len(rutas) <= 1:
            continue

        valores_numericos = [obtener_valor_numerico(os.path.basename(ruta)) for ruta in rutas]
        min_valor = min(valores_numericos)
        max_valor = max(valores_numericos)

        if (max_valor - min_valor) > RANGO_NUMERICO_MINIMO:
            duplicados_filtrados[hash_img] = rutas

    return duplicados_filtrados


def mostrar_grupos_duplicados(duplicados: dict):
    """Muestra los grupos de imagenes duplicadas en una ventana grafica (tema oscuro)."""
    if Image is None or ImageTk is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    ventana = tk.Toplevel()
    ventana.title("Grupos de imagenes duplicadas")
    ventana.geometry("900x650")
    ventana.configure(bg="#2e2e2e")

    grupos = list(duplicados.items())
    total_grupos = len(grupos)
    indice_grupo = tk.IntVar(value=0)

    canvas = tk.Canvas(ventana, bg="#2e2e2e", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    frame_imagenes = tk.Frame(canvas, bg="#2e2e2e")
    canvas.create_window((0, 0), window=frame_imagenes, anchor="nw")

    frame_navegacion = tk.Frame(ventana, bg="#2e2e2e")
    frame_navegacion.pack(fill=tk.X, side=tk.BOTTOM)

    def mostrar_grupo(indice: int):
        for widget in frame_imagenes.winfo_children():
            widget.destroy()

        hash_img, rutas = grupos[indice]
        tk.Label(
            frame_imagenes,
            text=f"Grupo {indice + 1} de {total_grupos} (Hash: {hash_img})",
            font=("Arial", 14),
            bg="#2e2e2e",
            fg="#ffffff",
        ).grid(row=0, column=0, columnspan=max(1, len(rutas)), pady=10)

        ancho_canvas = canvas.winfo_width() or 900
        ancho_max = max(120, ancho_canvas // max(1, len(rutas)) - 20)

        for col, ruta in enumerate(rutas):
            try:
                with Image.open(ruta) as img:
                    img_copy = img.copy()

                img_copy.thumbnail((ancho_max, ancho_max))
                img_tk = ImageTk.PhotoImage(img_copy)

                panel = tk.Label(frame_imagenes, image=img_tk, bg="#2e2e2e")
                panel.image = img_tk
                panel.grid(row=1, column=col, padx=10, pady=10)

                nombre_archivo = os.path.basename(ruta)
                tk.Label(
                    frame_imagenes,
                    text=f"Nombre: {nombre_archivo}",
                    font=("Arial", 10),
                    bg="#2e2e2e",
                    fg="#ffffff",
                ).grid(row=2, column=col)

                fecha_creacion = datetime.fromtimestamp(os.path.getctime(ruta)).strftime("%Y-%m-%d %H:%M:%S")
                tk.Label(
                    frame_imagenes,
                    text=f"Fecha de creacion: {fecha_creacion}",
                    font=("Arial", 10),
                    bg="#2e2e2e",
                    fg="#ffffff",
                ).grid(row=3, column=col)

            except Exception as exc:
                tk.Label(
                    frame_imagenes,
                    text=f"Error al cargar {ruta}: {exc}",
                    fg="red",
                    bg="#2e2e2e",
                    wraplength=ancho_max,
                    justify="left",
                ).grid(row=1, column=col, padx=10, pady=10)

        frame_imagenes.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def siguiente_grupo():
        if indice_grupo.get() < total_grupos - 1:
            indice_grupo.set(indice_grupo.get() + 1)
            mostrar_grupo(indice_grupo.get())

    def anterior_grupo():
        if indice_grupo.get() > 0:
            indice_grupo.set(indice_grupo.get() - 1)
            mostrar_grupo(indice_grupo.get())

    btn_anterior = tk.Button(
        frame_navegacion,
        text="Anterior",
        command=anterior_grupo,
        bg="#444444",
        fg="#ffffff",
    )
    btn_anterior.pack(side=tk.LEFT, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_navegacion,
        text="Siguiente",
        command=siguiente_grupo,
        bg="#444444",
        fg="#ffffff",
    )
    btn_siguiente.pack(side=tk.RIGHT, padx=10, pady=10)

    mostrar_grupo(indice_grupo.get())

    resize_after_id = None

    def ajustar_canvas(_event):
        nonlocal resize_after_id
        if resize_after_id is not None:
            ventana.after_cancel(resize_after_id)
        resize_after_id = ventana.after(150, lambda: mostrar_grupo(indice_grupo.get()))

    canvas.bind("<Configure>", ajustar_canvas)


def main():
    root = tk.Tk()
    root.title("Imagenes repetidas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta:").grid(row=0, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    tk.Entry(frame, textvariable=carpeta_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta")
        if carpeta:
            carpeta_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_carpeta).grid(row=1, column=2, pady=(4, 8))

    tk.Label(frame, text="Umbral (0=identicas):").grid(row=2, column=0, sticky="w")
    umbral_var = tk.StringVar(value="15")
    tk.Entry(frame, textvariable=umbral_var, width=12).grid(row=3, column=0, pady=(4, 8), sticky="w")

    tk.Label(
        frame,
        text=f"Nota: solo muestra grupos con rango numerico > {RANGO_NUMERICO_MINIMO} en el nombre.",
        justify="left",
        wraplength=460,
    ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La ruta no existe.")
            return

        try:
            umbral = int(umbral_var.get().strip())
            if umbral < 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "El umbral debe ser un entero >= 0.")
            return

        try:
            duplicados = encontrar_imagenes_duplicadas(carpeta, umbral)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}")
            return

        if not duplicados:
            messagebox.showinfo("Sin duplicados", "No se encontraron imagenes duplicadas/similares.")
            return

        messagebox.showinfo("Resultados", f"Se encontraron {len(duplicados)} grupos. Se abrira el visor.")
        mostrar_grupos_duplicados(duplicados)

    tk.Button(frame, text="Buscar duplicados", command=ejecutar).grid(row=5, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
