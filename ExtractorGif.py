import os
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema

from motores.renombrado import afijo, afijo_valido, nombre_con_afijos, nombre_multimedia

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    Image = None
    _pil_import_error = str(exc)


def extraer_frames_gif(ruta_gif: str, carpeta_salida: str, prefijo: str = "frame", sufijo: str = ""):
    """Extrae todos los frames de un GIF y los guarda como PNG.

    Devuelve: (frames_guardados, error_str|"")
    """
    prefijo = afijo(prefijo) or "frame"
    sufijo = afijo(sufijo)
    if Image is None:
        return 0, f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}"

    os.makedirs(carpeta_salida, exist_ok=True)

    try:
        with Image.open(ruta_gif) as gif:
            n_frames = getattr(gif, "n_frames", 1)
            print(f"Procesando: {os.path.basename(ruta_gif)} - {n_frames} frames")

            saved = 0
            for i in range(n_frames):
                try:
                    gif.seek(i)
                except Exception:
                    # Algunos GIFs pueden fallar al seek; cortamos aqui.
                    break

                nombre_png = nombre_con_afijos(
                    nombre_multimedia(ruta_gif, prefijo, i + 1, ".png"),
                    "",
                    sufijo,
                )
                ruta_png = os.path.join(carpeta_salida, nombre_png)
                gif.save(ruta_png, "PNG")
                saved += 1
                print(f"Guardado: {nombre_png}")

            return saved, ""

    except Exception as exc:
        err = str(exc)
        print(f"Error al procesar {ruta_gif}: {err}")
        return 0, err


def procesar_carpeta(carpeta_entrada: str, carpeta_salida: str, prefijo: str = "frame", sufijo: str = ""):
    """Busca GIFs en una carpeta y extrae frames a subcarpetas por archivo."""
    total_gifs = 0
    total_frames = 0
    errors = []

    for archivo in os.listdir(carpeta_entrada):
        if not archivo.lower().endswith(".gif"):
            continue

        ruta_gif = os.path.join(carpeta_entrada, archivo)
        if not os.path.isfile(ruta_gif):
            continue

        nombre_base = os.path.splitext(archivo)[0]
        subcarpeta = os.path.join(carpeta_salida, nombre_base)

        frames, err = extraer_frames_gif(ruta_gif, subcarpeta, prefijo, sufijo)
        total_gifs += 1
        total_frames += frames
        if err:
            errors.append((archivo, err))

    print(f"\nProceso completado. {total_gifs} GIF(s) procesados.")
    return {"gifs": total_gifs, "frames": total_frames, "errors": errors}


def main():
    root = tk.Tk()
    root.title("Extractor GIF -> PNG")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    modo_var = tk.StringVar(value="carpeta")  # 'archivo' | 'carpeta'

    tk.Label(frame, text="Modo:").grid(row=0, column=0, sticky="w")
    modos = tk.Frame(frame)
    modos.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 8))
    tk.Radiobutton(modos, text="Carpeta", variable=modo_var, value="carpeta").pack(side="left")
    tk.Radiobutton(modos, text="Archivo", variable=modo_var, value="archivo").pack(side="left", padx=(12, 0))

    # Entrada
    tk.Label(frame, text="Entrada:").grid(row=2, column=0, sticky="w")
    entrada_var = tk.StringVar()
    tk.Entry(frame, textvariable=entrada_var, width=50).grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_entrada():
        if modo_var.get() == "archivo":
            path = filedialog.askopenfilename(
                title="Seleccionar GIF",
                filetypes=[("GIF", "*.gif"), ("Todos", "*.*")],
            )
            if path:
                entrada_var.set(path)
                # Sugerir salida si esta vacia
                if not salida_var.get().strip():
                    base = os.path.splitext(os.path.basename(path))[0]
                    salida_var.set(os.path.join(os.path.dirname(path), base))
        else:
            path = filedialog.askdirectory(title="Seleccionar carpeta con GIFs")
            if path:
                entrada_var.set(path)
                if not salida_var.get().strip():
                    salida_var.set(path + "_frames")

    tk.Button(frame, text="Examinar", command=seleccionar_entrada).grid(row=3, column=2, pady=(4, 8))

    # Salida
    tk.Label(frame, text="Salida:").grid(row=4, column=0, sticky="w")
    salida_var = tk.StringVar()
    tk.Entry(frame, textvariable=salida_var, width=50).grid(
        row=5, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_salida():
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            salida_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_salida).grid(row=5, column=2, pady=(4, 8))

    # Prefijo
    tk.Label(frame, text="Prefijo:").grid(row=6, column=0, sticky="w")
    tk.Label(frame, text="Sufijo:").grid(row=6, column=1, sticky="w")
    prefijo_var = tk.StringVar(value="frame")
    sufijo_var = tk.StringVar()
    tk.Entry(
        frame,
        textvariable=prefijo_var,
        width=20,
        ayuda="Texto delante de cada frame. Vacio: se usa frame.",
    ).grid(row=7, column=0, pady=(4, 8), sticky="w")
    tk.Entry(frame, textvariable=sufijo_var, width=20).grid(row=7, column=1, pady=(4, 8), sticky="w")

    def ejecutar():
        if Image is None:
            messagebox.showerror("Pillow no disponible", f"No se pudo importar Pillow (PIL).\n\n{_pil_import_error}")
            return

        modo = modo_var.get()
        entrada = entrada_var.get().strip()
        salida = salida_var.get().strip()
        prefijo = afijo(prefijo_var.get()) or "frame"
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefijo) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        if not entrada:
            messagebox.showwarning("Falta entrada", "Seleccione una entrada.")
            return
        if not salida:
            messagebox.showwarning("Falta salida", "Seleccione una carpeta de salida.")
            return

        if modo == "archivo":
            if not os.path.isfile(entrada) or not entrada.lower().endswith(".gif"):
                messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .gif existente.")
                return

            # Para archivo, si salida no existe la creamos como carpeta
            os.makedirs(salida, exist_ok=True)
            frames, err = extraer_frames_gif(entrada, salida, prefijo, sufijo)
            if err:
                messagebox.showerror("Error", f"No se pudo extraer frames.\n\n{err}")
                return

            messagebox.showinfo("Operacion completada", f"Frames guardados: {frames}")
            return

        # modo carpeta
        if not os.path.isdir(entrada):
            messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
            return

        os.makedirs(salida, exist_ok=True)
        info = procesar_carpeta(entrada, salida, prefijo, sufijo)
        if info["gifs"] == 0:
            messagebox.showinfo("Sin GIFs", "No se encontraron .gif en la carpeta.")
            return

        if info["errors"]:
            messagebox.showwarning(
                "Extraccion parcial",
                f"GIFs: {info['gifs']}\nFrames: {info['frames']}\nErrores: {len(info['errors'])}",
            )
            return

        messagebox.showinfo(
            "Operacion completada",
            f"GIFs: {info['gifs']}\nFrames: {info['frames']}",
        )

    tk.Button(frame, text="Extraer frames", command=ejecutar).grid(row=9, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
