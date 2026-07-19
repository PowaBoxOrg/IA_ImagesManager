import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

from motores.ffmpeg import ejecutar as ejecutar_ffmpeg
from motores.ffmpeg import ffmpeg_disponible


def _validar_resize(resize: str) -> bool:
    # Formato esperado: "640:-1" (ancho:alto) donde cada parte es int.
    if ":" not in resize:
        return False
    a, b = resize.split(":", 1)
    try:
        int(a.strip())
        int(b.strip())
        return True
    except Exception:
        return False


def convertir_mp4_a_gif(archivo_mp4: str, archivo_gif: str, fps: int = 15, resize: str = "640:-1"):
    """Convierte MP4 a GIF usando FFmpeg (palettegen/paletteuse)."""
    filtro = (
        f"fps={fps},scale={resize}:flags=lanczos,split[s0][s1];"
        "[s0]palettegen[p];"
        "[s1][p]paletteuse"
    )

    comando = [
        "-i",
        archivo_mp4,
        "-vf",
        filtro,
        "-loop",
        "0",
        "-y",  # sobrescribir si existe
        archivo_gif,
    ]

    try:
        resultado = ejecutar_ffmpeg(comando)
        if not resultado.correcto:
            raise RuntimeError(resultado.error)
        print(f"Conversion exitosa: {archivo_mp4} -> {archivo_gif}")
        return True, ""
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip()
        if not err:
            err = str(exc)
        print(f"Error al convertir {archivo_mp4}: {err}")
        return False, err
    except Exception as exc:
        print(f"Error inesperado: {exc}")
        return False, str(exc)


def procesar_carpeta(carpeta_entrada: str, carpeta_salida: str, fps: int = 15, resize: str = "640:-1"):
    """Procesa todos los MP4 en una carpeta y los convierte a GIF."""
    os.makedirs(carpeta_salida, exist_ok=True)

    total = 0
    ok = 0
    errors = []

    for archivo in os.listdir(carpeta_entrada):
        if not archivo.lower().endswith(".mp4"):
            continue

        total += 1
        ruta_mp4 = os.path.join(carpeta_entrada, archivo)
        nombre_base = os.path.splitext(archivo)[0]
        ruta_gif = os.path.join(carpeta_salida, f"{nombre_base}.gif")

        success, err = convertir_mp4_a_gif(ruta_mp4, ruta_gif, fps, resize)
        if success:
            ok += 1
        else:
            errors.append((archivo, err))

    return {"total": total, "ok": ok, "errors": errors}


def main():
    root = tk.Tk()
    root.title("MP4 -> GIF (FFmpeg)")
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
    entrada_entry = tk.Entry(frame, textvariable=entrada_var, width=50)
    entrada_entry.grid(row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    # Salida
    tk.Label(frame, text="Salida:").grid(row=4, column=0, sticky="w")
    salida_var = tk.StringVar()
    salida_entry = tk.Entry(frame, textvariable=salida_var, width=50)
    salida_entry.grid(row=5, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_entrada():
        if modo_var.get() == "archivo":
            path = filedialog.askopenfilename(
                title="Seleccionar MP4",
                filetypes=[("Video MP4", "*.mp4"), ("Todos", "*.*")],
            )
            if path:
                entrada_var.set(path)
                if not salida_var.get().strip():
                    base, _ = os.path.splitext(path)
                    salida_var.set(base + ".gif")
        else:
            path = filedialog.askdirectory(title="Seleccionar carpeta de MP4")
            if path:
                entrada_var.set(path)
                if not salida_var.get().strip():
                    salida_var.set(path + "_gifs")

    def seleccionar_salida():
        if modo_var.get() == "archivo":
            path = filedialog.asksaveasfilename(
                title="Guardar GIF como",
                defaultextension=".gif",
                filetypes=[("GIF", "*.gif"), ("Todos", "*.*")],
            )
        else:
            path = filedialog.askdirectory(title="Seleccionar carpeta de salida")

        if path:
            salida_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_entrada).grid(row=3, column=2, pady=(4, 8))
    tk.Button(frame, text="Examinar", command=seleccionar_salida).grid(row=5, column=2, pady=(4, 8))

    # Parametros
    tk.Label(frame, text="FPS:").grid(row=6, column=0, sticky="w")
    fps_var = tk.StringVar(value="15")
    tk.Entry(frame, textvariable=fps_var, width=12).grid(row=7, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Resize (w:h):").grid(row=6, column=1, sticky="w")
    resize_var = tk.StringVar(value="640:-1")
    tk.Entry(frame, textvariable=resize_var, width=20).grid(row=7, column=1, pady=(4, 8), sticky="w")

    tk.Label(frame, text='Ej: FPS 12 | Resize "320:-1" (alto automatico)').grid(
        row=8, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    def ejecutar():
        if not ffmpeg_disponible():
            messagebox.showerror(
                "FFmpeg no disponible",
                "FFmpeg no esta instalado o no esta en el PATH.\n\nInstalalo y reintenta.",
            )
            return

        modo = modo_var.get()
        entrada = entrada_var.get().strip()
        salida = salida_var.get().strip()

        if not entrada:
            messagebox.showwarning("Falta entrada", "Seleccione una entrada.")
            return
        if not salida:
            messagebox.showwarning("Falta salida", "Seleccione una salida.")
            return

        try:
            fps = int(fps_var.get().strip())
            if fps <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "FPS debe ser un numero entero mayor que 0.")
            return

        resize = resize_var.get().strip() or "640:-1"
        if not _validar_resize(resize):
            messagebox.showerror("Dato invalido", "Resize debe tener formato w:h, por ejemplo 640:-1")
            return

        if modo == "archivo":
            if not os.path.isfile(entrada) or not entrada.lower().endswith(".mp4"):
                messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .mp4 existente.")
                return

            if not salida.lower().endswith(".gif"):
                salida = salida + ".gif"
                salida_var.set(salida)

            ok, err = convertir_mp4_a_gif(entrada, salida, fps, resize)
            if ok:
                messagebox.showinfo("Operacion completada", "Conversion finalizada.")
            else:
                messagebox.showerror("Error", f"No se pudo convertir.\n\n{err}")

        else:
            if not os.path.isdir(entrada):
                messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
                return
            if os.path.isfile(salida):
                messagebox.showerror("Salida invalida", "Para modo carpeta, la salida debe ser una carpeta.")
                return

            info = procesar_carpeta(entrada, salida, fps, resize)
            if info["total"] == 0:
                messagebox.showinfo("Sin archivos", "No se encontraron .mp4 en la carpeta.")
                return

            if info["errors"]:
                messagebox.showwarning(
                    "Conversion parcial",
                    f"Convertidos: {info['ok']} de {info['total']}\nErrores: {len(info['errors'])}",
                )
                return

            messagebox.showinfo(
                "Operacion completada",
                f"Convertidos: {info['ok']} de {info['total']}",
            )

    tk.Button(frame, text="Convertir", command=ejecutar).grid(row=9, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
