import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import cv2
except Exception as exc:  # pragma: no cover
    cv2 = None
    _cv2_import_error = str(exc)

try:
    import numpy as np
except Exception as exc:  # pragma: no cover
    np = None
    _np_import_error = str(exc)


def encontrar_loop(video_path: str, skip_frames: int = 30, threshold: float = 10.0):
    """Busca un punto donde el video vuelve a parecerse al primer frame.

    Metodo: compara cada frame (desde `skip_frames`) contra el primer frame usando MSE.

    Devuelve dict con:
    - best_frame: frame index (1-based contando frames leidos luego del primero)
    - min_error: MSE minimo encontrado
    - candidates: lista de (frame, error) para errores < threshold
    """
    if cv2 is None:
        raise RuntimeError(f"OpenCV (cv2) no disponible. Detalle: {_cv2_import_error}")
    if np is None:
        raise RuntimeError(f"NumPy no disponible. Detalle: {_np_import_error}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el video.")

    ret, frame_referencia = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError("No se pudo leer el primer frame del video.")

    frame_ref_gray = cv2.cvtColor(frame_referencia, cv2.COLOR_BGR2GRAY)

    frame_count = 0
    min_error = float("inf")
    mejor_frame = -1
    candidates = []

    while True:
        ret, frame_actual = cap.read()
        if not ret:
            break

        frame_count += 1

        if frame_count < skip_frames:
            continue

        frame_act_gray = cv2.cvtColor(frame_actual, cv2.COLOR_BGR2GRAY)

        diff = frame_ref_gray.astype("float") - frame_act_gray.astype("float")
        err = float(np.mean(diff * diff))

        if err < threshold:
            candidates.append((frame_count, err))

        if err < min_error:
            min_error = err
            mejor_frame = frame_count

    cap.release()

    return {
        "best_frame": mejor_frame,
        "min_error": min_error,
        "candidates": candidates,
        "frames_checked": frame_count,
    }


def main():
    root = tk.Tk()
    root.title("Encontrar loop (video)")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Video:").grid(row=0, column=0, sticky="w")
    video_var = tk.StringVar()
    tk.Entry(frame, textvariable=video_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_video():
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[
                ("Videos", "*.mp4;*.mkv;*.avi;*.mov;*.webm"),
                ("Todos", "*.*"),
            ],
        )
        if path:
            video_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_video).grid(row=1, column=2, pady=(4, 8))

    tk.Label(frame, text="Skip frames:").grid(row=2, column=0, sticky="w")
    skip_var = tk.StringVar(value="30")
    tk.Entry(frame, textvariable=skip_var, width=12).grid(row=3, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Threshold (MSE):").grid(row=2, column=1, sticky="w")
    thr_var = tk.StringVar(value="10.0")
    tk.Entry(frame, textvariable=thr_var, width=12).grid(row=3, column=1, pady=(4, 8), sticky="w")

    status_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=status_var, justify="left", wraplength=460).grid(
        row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    boton = tk.Button(frame, text="Analizar")
    boton.grid(row=5, column=0, columnspan=3, sticky="we")

    def ejecutar_bg():
        video_path = video_var.get().strip()
        if not video_path:
            messagebox.showwarning("Falta video", "Seleccione un video.")
            return
        if not os.path.isfile(video_path):
            messagebox.showerror("Ruta invalida", "El archivo de video no existe.")
            return

        try:
            skip_frames = int(skip_var.get().strip())
            if skip_frames < 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "Skip frames debe ser un entero >= 0.")
            return

        try:
            threshold = float(thr_var.get().strip())
            if threshold < 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "Threshold debe ser un numero >= 0.")
            return

        def worker():
            try:
                status_var.set("Analizando... (puede tardar segun el largo del video)")
                result = encontrar_loop(video_path, skip_frames=skip_frames, threshold=threshold)

                best_frame = result["best_frame"]
                min_error = result["min_error"]
                candidates = result["candidates"]

                # Resumen corto para el usuario
                lines = [
                    f"Mejor frame: {best_frame}",
                    f"Min error: {min_error:.4f}",
                    f"Candidatos (< {threshold}): {len(candidates)}",
                ]
                status_var.set("\n".join(lines))

                # Mostrar algunos candidatos en el dialogo sin saturar
                preview = "\n".join([f"Frame {f}: {e:.4f}" for (f, e) in candidates[:10]])
                if preview:
                    msg = f"{lines[0]}\n{lines[1]}\n\nPrimeros candidatos:\n{preview}"
                else:
                    msg = f"{lines[0]}\n{lines[1]}\n\nNo se encontraron candidatos bajo el threshold." 

                root.after(0, lambda: messagebox.showinfo("Resultado", msg))

            except Exception as exc:
                root.after(0, lambda: messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}"))
            finally:
                root.after(0, lambda: boton.config(state="normal"))

        boton.config(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

    boton.config(command=ejecutar_bg)

    root.mainloop()


if __name__ == "__main__":
    main()
