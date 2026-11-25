import argparse
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema


BITRATE_PREDETERMINADO = "192k"
FRECUENCIA_PREDETERMINADA = "44100"
EXTENSIONES_VIDEO = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".mpg",
    ".mpeg",
)
PATRON_ARCHIVOS_VIDEO = " ".join(f"*{extension}" for extension in EXTENSIONES_VIDEO)
TEXTO_EXTENSIONES_VIDEO = ", ".join(EXTENSIONES_VIDEO)
_FFMPEG_CACHE = ""
_FFMPEG_ERROR = ""


def en_entorno_virtual() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _normalizar_ruta_ffmpeg(ruta: str) -> str:
    ruta = (ruta or "").strip().strip('"')
    if not ruta:
        return ""

    encontrada = shutil.which(ruta)
    if encontrada:
        return encontrada

    if os.path.isfile(ruta):
        return ruta

    if os.name == "nt" and not ruta.lower().endswith(".exe"):
        ruta_exe = ruta + ".exe"
        if os.path.isfile(ruta_exe):
            return ruta_exe

    return ruta


def _probar_ffmpeg(ruta: str):
    try:
        subprocess.run(
            [ruta, "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _candidatos_ffmpeg():
    variables = ("FFMPEG_BINARY", "FFMPEG_PATH", "IMAGEIO_FFMPEG_EXE")
    for variable in variables:
        valor = os.environ.get(variable, "").strip()
        if valor:
            yield valor

    yield "ffmpeg"

    carpeta_script = os.path.dirname(os.path.abspath(__file__))
    for carpeta in (
        carpeta_script,
        os.path.join(carpeta_script, "bin"),
        os.path.join(carpeta_script, "ffmpeg"),
        os.path.join(carpeta_script, "ffmpeg", "bin"),
    ):
        yield os.path.join(carpeta, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")

    prefijos_python = [sys.prefix, getattr(sys, "base_prefix", sys.prefix)]
    for prefijo in prefijos_python:
        yield os.path.join(prefijo, "Scripts", "ffmpeg.exe")
        yield os.path.join(prefijo, "bin", "ffmpeg")
        yield os.path.join(prefijo, "Library", "bin", "ffmpeg.exe")

    if os.name == "nt":
        rutas_windows = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ]
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
        if local_appdata:
            rutas_windows.append(os.path.join(local_appdata, "Microsoft", "WinGet", "Links", "ffmpeg.exe"))
        if program_files:
            rutas_windows.append(os.path.join(program_files, "ffmpeg", "bin", "ffmpeg.exe"))
        if program_files_x86:
            rutas_windows.append(os.path.join(program_files_x86, "ffmpeg", "bin", "ffmpeg.exe"))
        for ruta in rutas_windows:
            yield ruta

    try:
        import imageio_ffmpeg

        yield imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass


def resolver_ffmpeg(ruta_preferida: str = "") -> str:
    global _FFMPEG_CACHE, _FFMPEG_ERROR

    errores = []
    candidatos = []
    if ruta_preferida:
        candidatos.append(ruta_preferida)
    elif _FFMPEG_CACHE:
        candidatos.append(_FFMPEG_CACHE)
    candidatos.extend(_candidatos_ffmpeg())

    vistos = set()
    for candidato in candidatos:
        ruta = _normalizar_ruta_ffmpeg(candidato)
        if not ruta:
            continue

        clave = os.path.normcase(os.path.abspath(ruta)) if os.path.isabs(ruta) else ruta.lower()
        if clave in vistos:
            continue
        vistos.add(clave)

        ok, error = _probar_ffmpeg(ruta)
        if ok:
            _FFMPEG_CACHE = ruta
            _FFMPEG_ERROR = ""
            return ruta
        errores.append(f"{ruta}: {error}")

    _FFMPEG_ERROR = "\n".join(errores[-5:])
    return ""


def mensaje_ffmpeg_no_disponible(ruta_preferida: str = "") -> str:
    partes = ["No se pudo encontrar o ejecutar FFmpeg."]

    if ruta_preferida:
        partes.append(f"Ruta indicada:\n{ruta_preferida}")

    if en_entorno_virtual():
        partes.append(
            "El script se esta ejecutando dentro de un entorno virtual.\n\n"
            f"Python actual:\n{sys.executable}\n\n"
            f"Python base:\n{getattr(sys, '_base_executable', sys.executable)}"
        )

    partes.append(
        "Puedes seleccionar manualmente ffmpeg.exe en el campo FFmpeg, ponerlo junto al script, "
        "ponerlo en .venv\\Scripts, o definir la variable FFMPEG_BINARY."
    )

    if _FFMPEG_ERROR:
        partes.append(f"Ultimos intentos:\n{_FFMPEG_ERROR}")

    return "\n\n".join(partes)


def ffmpeg_disponible(ruta_preferida: str = "") -> bool:
    return bool(resolver_ffmpeg(ruta_preferida))


def es_video_soportado(ruta: str) -> bool:
    return ruta.lower().endswith(EXTENSIONES_VIDEO)


def ruta_salida_por_defecto(ruta_video: str) -> str:
    nombre_base, _ = os.path.splitext(ruta_video)
    return nombre_base + ".mp3"


def validar_bitrate(bitrate: str) -> bool:
    if not bitrate:
        return False
    valor = bitrate.strip().lower()
    if not valor.endswith("k"):
        return False
    numero = valor[:-1]
    return numero.isdigit() and int(numero) > 0


def validar_frecuencia(frecuencia: str) -> bool:
    return frecuencia.isdigit() and int(frecuencia) > 0


def convertir_video_a_mp3(
    archivo_video: str,
    archivo_mp3: str,
    bitrate: str = BITRATE_PREDETERMINADO,
    frecuencia: str = FRECUENCIA_PREDETERMINADA,
    ffmpeg_binario: str = "",
):
    """Extrae el audio de un video y lo guarda como MP3 usando FFmpeg."""
    ffmpeg_binario = resolver_ffmpeg(ffmpeg_binario)
    if not ffmpeg_binario:
        return False, mensaje_ffmpeg_no_disponible()

    comando = [
        ffmpeg_binario,
        "-i",
        archivo_video,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        frecuencia,
        "-y",
        archivo_mp3,
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


def convertir_mp4_a_mp3(
    archivo_mp4: str,
    archivo_mp3: str,
    bitrate: str = BITRATE_PREDETERMINADO,
    frecuencia: str = FRECUENCIA_PREDETERMINADA,
):
    return convertir_video_a_mp3(archivo_mp4, archivo_mp3, bitrate, frecuencia)


MOTORES_AUDIO = ("ffmpeg", "moviepy")


def motor_audio(motor: str | None) -> str:
    if motor in MOTORES_AUDIO:
        return motor
    return "ffmpeg"


def convertir_con_moviepy(archivo_video: str, archivo_mp3: str):
    """Extrae el audio con MoviePy, el camino que antes ofrecia mkv2mp3.py."""
    try:
        try:
            from moviepy import VideoFileClip
        except ImportError:
            from moviepy.editor import VideoFileClip
    except ImportError as exc:
        return False, f"MoviePy no esta instalado.\n\n{exc}"

    video = None
    try:
        video = VideoFileClip(archivo_video)
        if video.audio is None:
            return False, "El video no contiene pista de audio."
        video.audio.write_audiofile(archivo_mp3, logger=None)
        return True, ""
    except Exception as exc:
        return False, str(exc)
    finally:
        if video is not None:
            video.close()


def procesar_carpeta(
    carpeta_entrada: str,
    carpeta_salida: str,
    bitrate: str = BITRATE_PREDETERMINADO,
    frecuencia: str = FRECUENCIA_PREDETERMINADA,
    ffmpeg_binario: str = "",
):
    """Convierte todos los videos soportados de una carpeta a MP3."""
    os.makedirs(carpeta_salida, exist_ok=True)

    total = 0
    ok = 0
    errores = []

    for archivo in os.listdir(carpeta_entrada):
        if not es_video_soportado(archivo):
            continue

        total += 1
        ruta_video = os.path.join(carpeta_entrada, archivo)
        nombre_base = os.path.splitext(archivo)[0]
        ruta_mp3 = os.path.join(carpeta_salida, f"{nombre_base}.mp3")

        convertido, error = convertir_video_a_mp3(ruta_video, ruta_mp3, bitrate, frecuencia, ffmpeg_binario)
        if convertido:
            ok += 1
        else:
            errores.append((archivo, error))

    return {"total": total, "ok": ok, "errores": errores}


def construir_interfaz(motor: str = "ffmpeg", mostrar: bool = True) -> tk.Tk:
    motor = motor_audio(motor)
    ventana = tk.Tk()
    ventana.withdraw()
    ventana.title("Video -> MP3 (FFmpeg)")
    ventana.resizable(False, False)
    ventana.config(padx=16, pady=16)

    modo_var = tk.StringVar(value="archivo")
    motor_var = tk.StringVar(value=motor)
    entrada_var = tk.StringVar()
    salida_var = tk.StringVar()
    bitrate_var = tk.StringVar(value=BITRATE_PREDETERMINADO)
    frecuencia_var = tk.StringVar(value=FRECUENCIA_PREDETERMINADA)
    ffmpeg_var = tk.StringVar(value=_FFMPEG_CACHE)
    estado_var = tk.StringVar(value="Seleccione un video o una carpeta.")

    def actualizar_salida_automatica(ruta: str):
        if not ruta or salida_var.get().strip():
            return
        if motor_var.get() == "moviepy":
            salida_var.set(os.path.dirname(ruta))
        elif modo_var.get() == "archivo":
            salida_var.set(ruta_salida_por_defecto(ruta))
        else:
            salida_var.set(ruta + "_mp3")

    def seleccionar_entrada():
        if motor_var.get() == "moviepy" or modo_var.get() == "archivo":
            tipos = (
                [
                    ("Videos", "*.mkv *.mp4 *.avi"),
                    ("Videos soportados", PATRON_ARCHIVOS_VIDEO),
                    ("Todos los archivos", "*.*"),
                ]
                if motor_var.get() == "moviepy"
                else [
                    ("Videos soportados", PATRON_ARCHIVOS_VIDEO),
                    ("Video MP4", "*.mp4"),
                    ("Video MKV", "*.mkv"),
                    ("Todos los archivos", "*.*"),
                ]
            )
            ruta = filedialog.askopenfilename(title="Seleccionar video", filetypes=tipos)
        else:
            ruta = filedialog.askdirectory(title="Seleccionar carpeta con videos")

        if ruta:
            entrada_var.set(ruta)
            actualizar_salida_automatica(ruta)
            estado_var.set("Entrada lista para convertir.")

    def seleccionar_salida():
        ruta_actual = salida_var.get().strip()

        if motor_var.get() != "moviepy" and modo_var.get() == "archivo":
            nombre_inicial = os.path.basename(ruta_actual) if ruta_actual else "salida.mp3"
            carpeta_inicial = os.path.dirname(ruta_actual) if ruta_actual else os.getcwd()
            ruta = filedialog.asksaveasfilename(
                title="Guardar MP3 como",
                initialdir=carpeta_inicial,
                initialfile=nombre_inicial,
                defaultextension=".mp3",
                filetypes=[("Audio MP3", "*.mp3"), ("Todos los archivos", "*.*")],
            )
        else:
            ruta = filedialog.askdirectory(title="Seleccionar carpeta de salida")

        if ruta:
            salida_var.set(ruta)

    def seleccionar_ffmpeg():
        ruta_actual = ffmpeg_var.get().strip()
        carpeta_inicial = os.path.dirname(ruta_actual) if ruta_actual else os.getcwd()

        ruta = filedialog.askopenfilename(
            title="Seleccionar ffmpeg",
            initialdir=carpeta_inicial,
            filetypes=[
                ("FFmpeg", "ffmpeg.exe ffmpeg"),
                ("Ejecutables", "*.exe"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if ruta:
            ffmpeg_var.set(ruta)

    def detectar_ffmpeg():
        ruta = resolver_ffmpeg()
        if ruta:
            ffmpeg_var.set(ruta)
            estado_var.set("FFmpeg detectado.")
        else:
            messagebox.showerror("FFmpeg no disponible", mensaje_ffmpeg_no_disponible())

    def cambiar_modo():
        entrada_var.set("")
        salida_var.set("")
        if modo_var.get() == "archivo":
            estado_var.set("Seleccione un video.")
        else:
            estado_var.set("Seleccione una carpeta con videos.")

    def finalizar_conversion(ok: bool, mensaje: str, detalle: str = ""):
        boton_convertir.config(state=tk.NORMAL, text="Convertir a MP3")

        if ok:
            estado_var.set(mensaje)
            messagebox.showinfo("Operacion completada", detalle or mensaje)
        else:
            estado_var.set("No se pudo completar la conversion.")
            messagebox.showerror("Error de conversion", detalle or mensaje)

    def ejecutar_archivo(ruta_video: str, ruta_mp3: str, bitrate: str, frecuencia: str, ffmpeg_binario: str):
        ok, error = convertir_video_a_mp3(ruta_video, ruta_mp3, bitrate, frecuencia, ffmpeg_binario)
        if ok:
            ventana.after(
                0,
                finalizar_conversion,
                True,
                "Conversion completada.",
                f"Archivo guardado en:\n{ruta_mp3}",
            )
        else:
            ventana.after(
                0,
                finalizar_conversion,
                False,
                "Error de conversion.",
                f"No se pudo convertir el archivo.\n\n{error}",
            )

    def ejecutar_carpeta(
        carpeta_entrada: str,
        carpeta_salida: str,
        bitrate: str,
        frecuencia: str,
        ffmpeg_binario: str,
    ):
        info = procesar_carpeta(carpeta_entrada, carpeta_salida, bitrate, frecuencia, ffmpeg_binario)

        if info["total"] == 0:
            ventana.after(
                0,
                finalizar_conversion,
                True,
                "No se encontraron videos soportados.",
                f"No se encontraron videos soportados ({TEXTO_EXTENSIONES_VIDEO}) en la carpeta seleccionada.",
            )
            return

        if info["errores"]:
            ventana.after(
                0,
                finalizar_conversion,
                False,
                "Conversion parcial.",
                (
                    f"Convertidos: {info['ok']} de {info['total']}\n"
                    f"Errores: {len(info['errores'])}\n\n"
                    f"Salida:\n{carpeta_salida}"
                ),
            )
            return

        ventana.after(
            0,
            finalizar_conversion,
            True,
            f"Convertidos: {info['ok']} de {info['total']}.",
            f"Convertidos: {info['ok']} de {info['total']}\n\nGuardados en:\n{carpeta_salida}",
        )

    def ejecutar_moviepy(ruta_video: str, ruta_mp3: str):
        ok, error = convertir_con_moviepy(ruta_video, ruta_mp3)
        if ok:
            ventana.after(
                0,
                finalizar_conversion,
                True,
                "Conversion completada.",
                f"Archivo guardado en:\n{ruta_mp3}",
            )
        else:
            ventana.after(
                0,
                finalizar_conversion,
                False,
                "Error de conversion.",
                f"No se pudo convertir el archivo.\n\n{error}",
            )

    def iniciar_conversion():
        modo = modo_var.get()
        entrada = entrada_var.get().strip()
        salida = salida_var.get().strip()
        bitrate = bitrate_var.get().strip().lower() or BITRATE_PREDETERMINADO
        frecuencia = frecuencia_var.get().strip() or FRECUENCIA_PREDETERMINADA

        if not entrada:
            messagebox.showwarning("Falta entrada", "Seleccione una entrada.")
            return
        if not salida:
            messagebox.showwarning("Falta salida", "Seleccione una salida.")
            return

        if motor_var.get() == "moviepy":
            if not os.path.isfile(entrada):
                messagebox.showerror("Entrada invalida", "El archivo de video no existe.")
                return
            if not es_video_soportado(entrada):
                messagebox.showerror(
                    "Entrada invalida",
                    f"Seleccione un video soportado ({TEXTO_EXTENSIONES_VIDEO}).",
                )
                return
            if not os.path.isdir(salida):
                messagebox.showerror(
                    "Salida invalida",
                    "Seleccione una carpeta de guardado existente.",
                )
                return
            nombre = os.path.splitext(os.path.basename(entrada))[0]
            ruta_mp3 = os.path.join(salida, f"{nombre}.mp3")
            trabajo = threading.Thread(
                target=ejecutar_moviepy,
                args=(entrada, ruta_mp3),
                daemon=True,
            )
            boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
            estado_var.set("Convirtiendo con MoviePy, por favor espere...")
            trabajo.start()
            return

        if not validar_bitrate(bitrate):
            messagebox.showerror("Bitrate invalido", "Use un bitrate como 128k, 192k o 320k.")
            return
        if not validar_frecuencia(frecuencia):
            messagebox.showerror("Frecuencia invalida", "Use una frecuencia numerica, por ejemplo 44100.")
            return
        ffmpeg_binario = resolver_ffmpeg(ffmpeg_var.get().strip())
        if not ffmpeg_binario:
            messagebox.showerror("FFmpeg no disponible", mensaje_ffmpeg_no_disponible(ffmpeg_var.get().strip()))
            return
        ffmpeg_var.set(ffmpeg_binario)

        if modo == "archivo":
            if not os.path.isfile(entrada):
                messagebox.showerror("Entrada invalida", "El archivo de video no existe.")
                return
            if not es_video_soportado(entrada):
                messagebox.showerror(
                    "Entrada invalida",
                    f"Seleccione un video soportado ({TEXTO_EXTENSIONES_VIDEO}).",
                )
                return
            if not salida.lower().endswith(".mp3"):
                salida += ".mp3"
                salida_var.set(salida)

            destino_padre = os.path.dirname(salida)
            if destino_padre:
                os.makedirs(destino_padre, exist_ok=True)

            trabajo = threading.Thread(
                target=ejecutar_archivo,
                args=(entrada, salida, bitrate, frecuencia, ffmpeg_binario),
                daemon=True,
            )
        else:
            if not os.path.isdir(entrada):
                messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
                return
            if os.path.isfile(salida):
                messagebox.showerror("Salida invalida", "Para modo carpeta, la salida debe ser una carpeta.")
                return

            trabajo = threading.Thread(
                target=ejecutar_carpeta,
                args=(entrada, salida, bitrate, frecuencia, ffmpeg_binario),
                daemon=True,
            )

        boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
        estado_var.set("Convirtiendo, por favor espere...")
        trabajo.start()

    etiqueta_modo = tk.Label(ventana, text="Modo:")
    frame_modo = tk.Frame(ventana)
    tk.Radiobutton(
        frame_modo,
        text="Archivo",
        variable=modo_var,
        value="archivo",
        command=cambiar_modo,
    ).pack(side="left")
    radio_carpeta = tk.Radiobutton(
        frame_modo,
        text="Carpeta",
        variable=modo_var,
        value="carpeta",
        command=cambiar_modo,
    )
    radio_carpeta.pack(side="left", padx=(12, 0))

    etiqueta_motor = tk.Label(ventana, text="Motor:")
    frame_motor = tk.Frame(ventana)
    tk.Radiobutton(
        frame_motor,
        text="FFmpeg (archivo o carpeta)",
        variable=motor_var,
        value="ffmpeg",
        command=lambda: al_cambiar_motor(),
    ).pack(side="left")
    tk.Radiobutton(
        frame_motor,
        text="MoviePy (un archivo)",
        variable=motor_var,
        value="moviepy",
        command=lambda: al_cambiar_motor(),
    ).pack(side="left", padx=(12, 0))

    etiqueta_entrada = tk.Label(ventana, text="Entrada video:")
    frame_entrada = tk.Frame(ventana)
    tk.Entry(frame_entrada, textvariable=entrada_var, width=60).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(frame_entrada, text="Examinar", command=seleccionar_entrada).pack(side="right")

    etiqueta_salida = tk.Label(ventana, text="Salida MP3:")
    frame_salida = tk.Frame(ventana)
    tk.Entry(frame_salida, textvariable=salida_var, width=60).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(frame_salida, text="Examinar", command=seleccionar_salida).pack(side="right")

    frame_opciones = tk.Frame(ventana)
    tk.Label(frame_opciones, text="Bitrate:").pack(side="left")
    tk.Entry(frame_opciones, textvariable=bitrate_var, width=10).pack(side="left", padx=(8, 18))
    tk.Label(frame_opciones, text="Frecuencia:").pack(side="left")
    tk.Entry(frame_opciones, textvariable=frecuencia_var, width=10).pack(side="left", padx=(8, 0))

    etiqueta_ffmpeg = tk.Label(ventana, text="FFmpeg:")
    frame_ffmpeg = tk.Frame(ventana)
    tk.Entry(frame_ffmpeg, textvariable=ffmpeg_var, width=52).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(frame_ffmpeg, text="Detectar", command=detectar_ffmpeg).pack(side="left", padx=(0, 8))
    tk.Button(frame_ffmpeg, text="Examinar", command=seleccionar_ffmpeg).pack(side="right")

    boton_convertir = tk.Button(
        ventana,
        text="Convertir a MP3",
        command=iniciar_conversion,
    )
    etiqueta_estado = tk.Label(ventana, textvariable=estado_var, anchor="w", justify="left")

    bloques = (
        etiqueta_modo,
        frame_modo,
        etiqueta_motor,
        frame_motor,
        etiqueta_entrada,
        frame_entrada,
        etiqueta_salida,
        frame_salida,
        frame_opciones,
        etiqueta_ffmpeg,
        frame_ffmpeg,
        boton_convertir,
        etiqueta_estado,
    )

    def colocar():
        es_moviepy = motor_var.get() == "moviepy"
        if es_moviepy and modo_var.get() != "archivo":
            modo_var.set("archivo")
        radio_carpeta.config(state=tk.DISABLED if es_moviepy else tk.NORMAL)
        if not es_moviepy and not ffmpeg_var.get().strip():
            detectado = resolver_ffmpeg()
            if detectado:
                ffmpeg_var.set(detectado)
        visibles = [
            etiqueta_modo,
            frame_modo,
            etiqueta_motor,
            frame_motor,
            etiqueta_entrada,
            frame_entrada,
            etiqueta_salida,
            frame_salida,
        ]
        if not es_moviepy:
            visibles.extend((frame_opciones, etiqueta_ffmpeg, frame_ffmpeg))
        visibles.extend((boton_convertir, etiqueta_estado))
        for bloque in bloques:
            if bloque.winfo_manager() == "pack":
                bloque.pack_forget()
        for bloque in visibles:
            bloque.pack(fill="x", pady=(0, 8))
        if es_moviepy:
            ventana.title("Video -> MP3 (MoviePy)")
            etiqueta_entrada.config(text="Archivo de video:")
            etiqueta_salida.config(text="Carpeta de guardado:")
            estado_var.set("Seleccione un video y la carpeta donde guardar el MP3.")
        else:
            ventana.title("Video -> MP3 (FFmpeg)")
            etiqueta_entrada.config(text="Entrada video:")
            etiqueta_salida.config(text="Salida MP3:")
            estado_var.set("Seleccione un video o una carpeta.")

    def al_cambiar_motor():
        entrada_var.set("")
        salida_var.set("")
        colocar()

    colocar()
    ventana.motor_var = motor_var
    ventana.frame_opciones = frame_opciones
    ventana.etiqueta_ffmpeg = etiqueta_ffmpeg
    if mostrar:
        ventana.deiconify()
    return ventana


def main(motor: str = "ffmpeg"):
    construir_interfaz(motor_audio(motor)).mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae el audio de un video a MP3.")
    parser.add_argument("--motor", choices=MOTORES_AUDIO, default="ffmpeg")
    main(motor=parser.parse_args().motor)
