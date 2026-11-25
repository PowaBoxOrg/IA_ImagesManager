import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema

from motores.ffmpeg import ejecutar as ejecutar_ffmpeg
from motores.ffmpeg import ffmpeg_disponible


def convertir_mp4_a_mkv(archivo_mp4: str, archivo_mkv: str, codec_video: str = "copy", codec_audio: str = "copy"):
    """Convierte un archivo MP4 a MKV usando FFmpeg."""
    comando = [
        "-i",
        archivo_mp4,
        "-c:v",
        codec_video,
        "-c:a",
        codec_audio,
        "-y",  # sobrescribir si existe
        archivo_mkv,
    ]

    try:
        resultado = ejecutar_ffmpeg(comando)
        if not resultado.correcto:
            raise RuntimeError(resultado.error)
        print(f"Conversion exitosa: {archivo_mp4} -> {archivo_mkv}")
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


def procesar_carpeta(carpeta_entrada: str, carpeta_salida: str, codec_video: str = "copy", codec_audio: str = "copy"):
    """Procesa todos los MP4 en una carpeta y los convierte a MKV."""
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
        ruta_mkv = os.path.join(carpeta_salida, f"{nombre_base}.mkv")

        success, err = convertir_mp4_a_mkv(ruta_mp4, ruta_mkv, codec_video, codec_audio)
        if success:
            ok += 1
        else:
            errors.append((archivo, err))

    return {"total": total, "ok": ok, "errors": errors}


def main():
    root = tk.Tk()
    root.title("MP4 -> MKV (FFmpeg)")
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

    def seleccionar_entrada():
        if modo_var.get() == "archivo":
            path = filedialog.askopenfilename(
                title="Seleccionar MP4",
                filetypes=[("Video MP4", "*.mp4"), ("Todos", "*.*")],
            )
        else:
            path = filedialog.askdirectory(title="Seleccionar carpeta de MP4")

        if path:
            entrada_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_entrada).grid(row=3, column=2, pady=(4, 8))

    # Salida
    tk.Label(frame, text="Salida:").grid(row=4, column=0, sticky="w")
    salida_var = tk.StringVar()
    salida_entry = tk.Entry(frame, textvariable=salida_var, width=50)
    salida_entry.grid(row=5, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_salida():
        if modo_var.get() == "archivo":
            path = filedialog.asksaveasfilename(
                title="Guardar como",
                defaultextension=".mkv",
                filetypes=[("Video MKV", "*.mkv"), ("Todos", "*.*")],
            )
        else:
            path = filedialog.askdirectory(title="Seleccionar carpeta de salida")

        if path:
            salida_var.set(path)

    tk.Button(frame, text="Examinar", command=seleccionar_salida).grid(row=5, column=2, pady=(4, 8))

    # Codecs
    tk.Label(frame, text="Video codec:").grid(row=6, column=0, sticky="w")
    video_codec_var = tk.StringVar(value="copy")
    tk.Entry(frame, textvariable=video_codec_var, width=16).grid(row=7, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Audio codec:").grid(row=6, column=1, sticky="w")
    audio_codec_var = tk.StringVar(value="copy")
    tk.Entry(frame, textvariable=audio_codec_var, width=16).grid(row=7, column=1, pady=(4, 8), sticky="w")

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
        codec_video = video_codec_var.get().strip() or "copy"
        codec_audio = audio_codec_var.get().strip() or "copy"

        if not entrada:
            messagebox.showwarning("Falta entrada", "Seleccione una entrada.")
            return
        if not salida:
            messagebox.showwarning("Falta salida", "Seleccione una salida.")
            return

        if modo == "archivo":
            if not os.path.isfile(entrada) or not entrada.lower().endswith(".mp4"):
                messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .mp4 existente.")
                return

            if not salida.lower().endswith(".mkv"):
                salida = salida + ".mkv"
                salida_var.set(salida)

            ok, err = convertir_mp4_a_mkv(entrada, salida, codec_video, codec_audio)
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

            info = procesar_carpeta(entrada, salida, codec_video, codec_audio)
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
