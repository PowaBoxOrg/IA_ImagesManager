import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox


DEFAULT_RESOLUTION = "1280x720"


def ffmpeg_disponible() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except Exception:
        return False


def resolucion_valida(resolucion: str) -> bool:
    return bool(re.fullmatch(r"[1-9]\d*x[1-9]\d*", resolucion.strip()))


def ruta_salida_por_defecto(ruta_mp3: str) -> str:
    nombre_base, _ = os.path.splitext(ruta_mp3)
    return nombre_base + ".mp4"


def convertir_mp3_a_mp4(ruta_mp3: str, ruta_mp4: str, resolucion: str = DEFAULT_RESOLUTION):
    """Convierte un MP3 a MP4 con fondo negro usando FFmpeg."""
    comando = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={resolucion}:r=30",
        "-i",
        ruta_mp3,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-movflags",
        "+faststart",
        "-y",
        ruta_mp4,
    ]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, ""
    except subprocess.CalledProcessError as exc:
        error = (exc.stderr or "").strip()
        if not error:
            error = str(exc)
        return False, error
    except Exception as exc:
        return False, str(exc)


def main():
    ventana = tk.Tk()
    ventana.title("MP3 -> MP4")
    ventana.geometry("620x250")
    ventana.resizable(False, False)
    ventana.config(padx=16, pady=16)

    archivo_var = tk.StringVar()
    salida_var = tk.StringVar()
    resolucion_var = tk.StringVar(value=DEFAULT_RESOLUTION)
    estado_var = tk.StringVar(value="Seleccione un archivo MP3 para convertir.")

    def seleccionar_archivo():
        ruta = filedialog.askopenfilename(
            title="Seleccionar MP3",
            filetypes=[("Audio MP3", "*.mp3"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            archivo_var.set(ruta)
            salida_var.set(ruta_salida_por_defecto(ruta))
            estado_var.set("Archivo listo para convertir.")

    def seleccionar_salida():
        ruta_inicial = salida_var.get().strip()
        nombre_inicial = os.path.basename(ruta_inicial) if ruta_inicial else "salida.mp4"
        carpeta_inicial = os.path.dirname(ruta_inicial) if ruta_inicial else os.getcwd()

        ruta = filedialog.asksaveasfilename(
            title="Guardar MP4 como",
            initialdir=carpeta_inicial,
            initialfile=nombre_inicial,
            defaultextension=".mp4",
            filetypes=[("Video MP4", "*.mp4"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            salida_var.set(ruta)

    def finalizar_conversion(ok: bool, mensaje: str, ruta_salida: str):
        boton_convertir.config(state=tk.NORMAL, text="Convertir a MP4")

        if ok:
            estado_var.set("Conversion completada.")
            messagebox.showinfo("Operacion completada", f"Archivo guardado en:\n{ruta_salida}")
        else:
            estado_var.set("No se pudo completar la conversion.")
            messagebox.showerror("Error de conversion", f"No se pudo convertir el archivo.\n\n{mensaje}")

    def ejecutar_conversion(ruta_mp3: str, ruta_mp4: str, resolucion: str):
        ok, mensaje = convertir_mp3_a_mp4(ruta_mp3, ruta_mp4, resolucion)
        ventana.after(0, finalizar_conversion, ok, mensaje, ruta_mp4)

    def iniciar_conversion():
        ruta_mp3 = archivo_var.get().strip()
        ruta_mp4 = salida_var.get().strip()
        resolucion = resolucion_var.get().strip() or DEFAULT_RESOLUTION

        if not ruta_mp3:
            messagebox.showwarning("Falta archivo", "Seleccione un archivo MP3.")
            return
        if not os.path.isfile(ruta_mp3):
            messagebox.showerror("Archivo invalido", "El archivo seleccionado no existe.")
            return
        if not ruta_mp3.lower().endswith(".mp3"):
            messagebox.showerror("Archivo invalido", "Seleccione un archivo con extension .mp3.")
            return
        if not ruta_mp4:
            messagebox.showwarning("Falta salida", "Seleccione donde guardar el MP4.")
            return
        if not ruta_mp4.lower().endswith(".mp4"):
            ruta_mp4 += ".mp4"
            salida_var.set(ruta_mp4)
        if not resolucion_valida(resolucion):
            messagebox.showerror("Resolucion invalida", "Use el formato anchoxalto, por ejemplo 1280x720.")
            return
        if not ffmpeg_disponible():
            messagebox.showerror(
                "FFmpeg no disponible",
                "FFmpeg no esta instalado o no esta en el PATH.\n\nInstalalo y reintenta.",
            )
            return

        boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
        estado_var.set("Convirtiendo, por favor espere...")

        hilo = threading.Thread(
            target=ejecutar_conversion,
            args=(ruta_mp3, ruta_mp4, resolucion),
            daemon=True,
        )
        hilo.start()

    tk.Label(ventana, text="Archivo MP3:").pack(anchor="w")
    frame_archivo = tk.Frame(ventana)
    frame_archivo.pack(fill="x", pady=(4, 10))
    tk.Entry(frame_archivo, textvariable=archivo_var, width=60).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(frame_archivo, text="Examinar", command=seleccionar_archivo).pack(side="right")

    tk.Label(ventana, text="Guardar como MP4:").pack(anchor="w")
    frame_salida = tk.Frame(ventana)
    frame_salida.pack(fill="x", pady=(4, 10))
    tk.Entry(frame_salida, textvariable=salida_var, width=60).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(frame_salida, text="Examinar", command=seleccionar_salida).pack(side="right")

    frame_opciones = tk.Frame(ventana)
    frame_opciones.pack(fill="x", pady=(0, 12))
    tk.Label(frame_opciones, text="Resolucion:").pack(side="left")
    tk.Entry(frame_opciones, textvariable=resolucion_var, width=12).pack(side="left", padx=(8, 0))

    boton_convertir = tk.Button(
        ventana,
        text="Convertir a MP4",
        command=iniciar_conversion,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 11, "bold"),
    )
    boton_convertir.pack(fill="x", pady=(4, 10))

    tk.Label(ventana, textvariable=estado_var, anchor="w").pack(fill="x")

    ventana.mainloop()


if __name__ == "__main__":
    main()
