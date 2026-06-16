import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox


_error_relanzamiento = ""


def relanzar_con_python_global() -> bool:
    global _error_relanzamiento

    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        _error_relanzamiento = "No se encontro el Python global asociado al entorno virtual."
        return False

    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(os.path.abspath(sys.executable)):
        return False

    entorno = os.environ.copy()
    entorno["MP4_A_IMAGENES_PYTHON_GLOBAL"] = "1"
    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]

    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=entorno)
        return True
    except OSError as exc:
        _error_relanzamiento = f"No se pudo iniciar el Python global:\n{exc}"
        return False


try:
    import cv2
except Exception as exc:  # pragma: no cover
    cv2 = None
    _cv2_import_error = str(exc)


def crear_carpeta_salida(ruta_video: str) -> str:
    directorio = os.path.dirname(ruta_video)
    nombre_video = os.path.splitext(os.path.basename(ruta_video))[0]
    carpeta_base = os.path.join(directorio, f"{nombre_video}_capturas")

    indice = 1
    while True:
        carpeta = carpeta_base if indice == 1 else f"{carpeta_base}_{indice}"
        try:
            os.makedirs(carpeta)
            return carpeta
        except FileExistsError:
            indice += 1


def extraer_capturas(ruta_video: str, intervalo: float):
    if cv2 is None:
        raise RuntimeError(f"OpenCV (cv2) no disponible. Detalle: {_cv2_import_error}")

    nombre_video = os.path.splitext(os.path.basename(ruta_video))[0]
    sufijo_video = nombre_video[:5]

    video = cv2.VideoCapture(ruta_video)
    if not video.isOpened():
        raise RuntimeError("No se pudo abrir el video.")

    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps <= 0 or total_frames <= 0:
        video.release()
        raise RuntimeError("No se pudo obtener la duracion del video.")

    duracion = total_frames / fps
    carpeta_salida = crear_carpeta_salida(ruta_video)
    tiempo = 0.0
    total = 0

    try:
        while tiempo < duracion:
            video.set(cv2.CAP_PROP_POS_MSEC, tiempo * 1000.0)
            leido, imagen = video.read()
            if not leido:
                break

            total += 1
            ruta_imagen = os.path.join(
                carpeta_salida,
                f"captura_{total:06d}_{sufijo_video}.jpg",
            )
            guardada = cv2.imwrite(
                ruta_imagen,
                imagen,
                [cv2.IMWRITE_JPEG_QUALITY, 95],
            )
            if not guardada:
                raise RuntimeError(f"No se pudo guardar la imagen:\n{ruta_imagen}")

            tiempo += intervalo
    except Exception:
        raise
    finally:
        video.release()

    if total == 0:
        try:
            os.rmdir(carpeta_salida)
        except OSError:
            pass
        raise RuntimeError("No se pudo extraer ninguna imagen del video.")

    return carpeta_salida, total


def main():
    root = tk.Tk()
    root.title("MP4 -> Imagenes")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Video MP4:").grid(row=0, column=0, sticky="w")
    video_var = tk.StringVar()
    tk.Entry(frame, textvariable=video_var, width=50).grid(
        row=1,
        column=0,
        columnspan=2,
        padx=(0, 6),
        pady=(4, 8),
        sticky="we",
    )

    def seleccionar_video():
        ruta = filedialog.askopenfilename(
            title="Seleccionar video MP4",
            filetypes=[("Video MP4", "*.mp4"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            video_var.set(ruta)

    tk.Button(frame, text="Examinar", command=seleccionar_video).grid(
        row=1,
        column=2,
        pady=(4, 8),
    )

    tk.Label(frame, text="Capturar un frame cada N segundos:").grid(
        row=2,
        column=0,
        columnspan=3,
        sticky="w",
    )
    intervalo_var = tk.StringVar(value="5")
    intervalo_entry = tk.Entry(frame, textvariable=intervalo_var, width=12)
    intervalo_entry.grid(row=3, column=0, pady=(4, 4), sticky="w")

    tk.Label(
        frame,
        text="Se permiten decimales, por ejemplo: 0.5, 2.5 o 10.",
    ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

    estado_var = tk.StringVar()
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        wraplength=460,
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))

    boton_extraer = tk.Button(frame, text="Extraer imagenes")
    boton_extraer.grid(row=6, column=0, columnspan=3, sticky="we")

    def finalizar_exito(carpeta_salida: str, total: int):
        boton_extraer.config(state="normal")
        estado_var.set(f"Imagenes generadas: {total}")
        messagebox.showinfo(
            "Operacion completada",
            f"Imagenes generadas: {total}\n\nGuardadas en:\n{carpeta_salida}",
        )

    def finalizar_error(error: str):
        boton_extraer.config(state="normal")
        estado_var.set("")
        messagebox.showerror(
            "Error",
            f"No se pudieron extraer las imagenes.\n\n{error}",
        )

    def ejecutar():
        ruta_video = video_var.get().strip()
        if not ruta_video:
            messagebox.showwarning("Falta video", "Seleccione un archivo de video.")
            return
        if not os.path.isfile(ruta_video):
            messagebox.showerror("Ruta invalida", "El archivo de video no existe.")
            return
        if not ruta_video.lower().endswith(".mp4"):
            messagebox.showerror("Archivo invalido", "Seleccione un archivo con extension .mp4.")
            return

        try:
            intervalo = float(intervalo_var.get().strip().replace(",", "."))
            if intervalo <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Dato invalido",
                "N debe ser un numero mayor que 0.",
            )
            return

        if cv2 is None:
            detalle = (
                f"No se pudo importar OpenCV (cv2).\n\n"
                f"Interprete actual:\n{sys.executable}\n\n"
                f"Detalle:\n{_cv2_import_error}"
            )
            if _error_relanzamiento:
                detalle += f"\n\n{_error_relanzamiento}"
            messagebox.showerror(
                "OpenCV no disponible",
                detalle,
            )
            return

        boton_extraer.config(state="disabled")
        estado_var.set("Extrayendo imagenes... Esto puede tardar segun la duracion del video.")

        def worker():
            try:
                carpeta_salida, total = extraer_capturas(ruta_video, intervalo)
                root.after(
                    0,
                    lambda: finalizar_exito(carpeta_salida, total),
                )
            except Exception as exc:
                error = str(exc)
                root.after(0, lambda: finalizar_error(error))

        threading.Thread(target=worker, daemon=True).start()

    boton_extraer.config(command=ejecutar)
    intervalo_entry.focus_set()

    root.mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
