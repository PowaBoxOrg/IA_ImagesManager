"""Una ventana para las conversiones de formato de multimedia."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import aplicacion.tema
from MP4_MKV import convertir_mp4_a_mkv
from MP4_MKV import procesar_carpeta as carpeta_a_mkv
from MP4_a_MP3 import BITRATE_PREDETERMINADO
from MP4_a_MP3 import FRECUENCIA_PREDETERMINADA
from MP4_a_MP3 import convertir_con_moviepy
from MP4_a_MP3 import convertir_video_a_mp3
from MP4_a_MP3 import mensaje_ffmpeg_no_disponible
from MP4_a_MP3 import resolver_ffmpeg
from MP4_a_MP3 import validar_bitrate
from MP4_a_MP3 import validar_frecuencia
from motores.ffmpeg import ffmpeg_disponible
from mp4_a_gif_ffmpeg import _validar_resize
from mp4_a_gif_ffmpeg import convertir_mp4_a_gif
from mp4_a_gif_ffmpeg import procesar_carpeta as carpeta_a_gif
from mp4tomp3 import DEFAULT_RESOLUTION
from mp4tomp3 import convertir_mp3_a_mp4
from mp4tomp3 import resolucion_valida


FORMATOS_ENTRADA = (
    ("mp4", "MP4", ".mp4"),
    ("mkv", "MKV", ".mkv"),
    ("avi", "AVI", ".avi"),
    ("mov", "MOV", ".mov"),
    ("webm", "WEBM", ".webm"),
    ("flv", "FLV", ".flv"),
    ("wmv", "WMV", ".wmv"),
    ("m4v", "M4V", ".m4v"),
    ("mpg", "MPG", ".mpg"),
    ("mpeg", "MPEG", ".mpeg"),
    ("mp3", "MP3", ".mp3"),
)
FORMATOS_SALIDA = (
    ("mp3", "MP3", ".mp3"),
    ("mkv", "MKV", ".mkv"),
    ("gif", "GIF", ".gif"),
    ("mp4", "MP4", ".mp4"),
)
ENTRADA_POR_CLAVE = {clave: (texto, extension) for clave, texto, extension in FORMATOS_ENTRADA}
SALIDA_POR_CLAVE = {clave: (texto, extension) for clave, texto, extension in FORMATOS_SALIDA}


def salidas_de(entrada: str) -> tuple[str, ...]:
    """Formatos de salida que esta entrada ya sabe producir."""
    if entrada == "mp3":
        return ("mp4",)
    if entrada == "mp4":
        return ("mp3", "mkv", "gif")
    if entrada in ENTRADA_POR_CLAVE:
        return ("mp3",)
    return ("mp3",)


def panel_de(entrada: str, salida: str) -> str:
    if entrada == "mp3":
        return "audio"
    return salida


def construir_interfaz(mostrar: bool = True) -> tk.Tk:
    ventana = tk.Tk()
    ventana.withdraw()
    ventana.title("Convertir formato")
    ventana.geometry("860x640")
    ventana.minsize(760, 560)

    entrada_fmt = tk.StringVar(ventana, "mp4")
    salida_fmt = tk.StringVar(ventana, "mp3")
    entrada_ruta = tk.StringVar(ventana)
    salida_ruta = tk.StringVar(ventana)
    estado_var = tk.StringVar(ventana, "Elija el formato de entrada y el de salida.")
    motor_var = tk.StringVar(ventana, "ffmpeg")
    modo_mp3 = tk.StringVar(ventana, "archivo")
    modo_mkv = tk.StringVar(ventana, "archivo")
    modo_gif = tk.StringVar(ventana, "archivo")
    bitrate_var = tk.StringVar(ventana, BITRATE_PREDETERMINADO)
    frecuencia_var = tk.StringVar(ventana, FRECUENCIA_PREDETERMINADA)
    ffmpeg_var = tk.StringVar(ventana)
    video_codec_var = tk.StringVar(ventana, "copy")
    audio_codec_var = tk.StringVar(ventana, "copy")
    fps_var = tk.StringVar(ventana, "15")
    resize_var = tk.StringVar(ventana, "640:-1")
    resolucion_var = tk.StringVar(ventana, DEFAULT_RESOLUTION)

    marco = tk.Frame(ventana, padx=16, pady=16)
    marco.pack(fill="both", expand=True)
    pie = tk.Frame(marco)
    pie.pack(side="bottom", fill="x")

    columnas = ttk.Frame(marco)
    columnas.pack(fill="x")
    columnas.columnconfigure(0, weight=1, uniform="formatos")
    columnas.columnconfigure(1, weight=1, uniform="formatos")
    columna_entrada = ttk.LabelFrame(columnas, text="Formato de entrada", padding=(12, 8))
    columna_salida = ttk.LabelFrame(columnas, text="Formato de salida", padding=(12, 8))
    columna_entrada.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    columna_salida.grid(row=0, column=1, sticky="nsew")

    radios_entrada = {}
    radios_salida = {}

    def ayuda_entrada(clave: str) -> str:
        texto, extension = ENTRADA_POR_CLAVE[clave]
        if clave == "mp3":
            return "Audio MP3. La salida disponible es un MP4 con fondo negro."
        if clave == "mp4":
            return "Video MP4. Puede salir como MP3, MKV o GIF."
        return f"Video {texto}. De este formato se extrae el audio a MP3."

    def ayuda_salida(clave: str) -> str:
        if clave == "mp3":
            return "Extrae el audio y lo guarda como MP3."
        if clave == "mkv":
            return "Pasa un MP4 a contenedor MKV. Puedes elegir los codecs."
        if clave == "gif":
            return "Crea un GIF animado a partir de un MP4."
        return "Crea un MP4 con fondo negro a partir del MP3."

    for indice, (clave, texto, _extension) in enumerate(FORMATOS_ENTRADA):
        radio = tk.Radiobutton(
            columna_entrada,
            text=texto,
            variable=entrada_fmt,
            value=clave,
            ayuda=ayuda_entrada(clave),
            command=lambda: al_cambiar_formato(),
        )
        radio.grid(row=indice // 2, column=indice % 2, sticky="w", padx=(0, 16), pady=1)
        radios_entrada[clave] = radio

    for clave, texto, _extension in FORMATOS_SALIDA:
        radio = tk.Radiobutton(
            columna_salida,
            text=texto,
            variable=salida_fmt,
            value=clave,
            ayuda=ayuda_salida(clave),
            command=lambda: al_cambiar_formato(),
        )
        radios_salida[clave] = radio

    contenedor = tk.Frame(marco)
    contenedor.pack(fill="x", pady=(14, 0))
    contenedor.columnconfigure(0, weight=1)

    panel_mp3 = tk.Frame(contenedor)
    panel_mkv = tk.Frame(contenedor)
    panel_gif = tk.Frame(contenedor)
    panel_audio = tk.Frame(contenedor)
    paneles = {"mp3": panel_mp3, "mkv": panel_mkv, "gif": panel_gif, "audio": panel_audio}

    fila_motor = tk.Frame(panel_mp3)
    tk.Label(fila_motor, text="Motor:").pack(side="left")
    tk.Radiobutton(
        fila_motor,
        text="FFmpeg (archivo o carpeta)",
        variable=motor_var,
        value="ffmpeg",
        command=lambda: al_cambiar_detalle(),
    ).pack(side="left", padx=(8, 0))
    radio_moviepy = tk.Radiobutton(
        fila_motor,
        text="MoviePy (un archivo)",
        variable=motor_var,
        value="moviepy",
        command=lambda: al_cambiar_detalle(),
    )
    radio_moviepy.pack(side="left", padx=(12, 0))

    fila_modo_mp3 = tk.Frame(panel_mp3)
    tk.Label(fila_modo_mp3, text="Origen:").pack(side="left")
    tk.Radiobutton(
        fila_modo_mp3,
        text="Archivo",
        variable=modo_mp3,
        value="archivo",
        command=lambda: al_cambiar_detalle(),
    ).pack(side="left", padx=(8, 0))
    radio_carpeta_mp3 = tk.Radiobutton(
        fila_modo_mp3,
        text="Carpeta",
        variable=modo_mp3,
        value="carpeta",
        command=lambda: al_cambiar_detalle(),
    )
    radio_carpeta_mp3.pack(side="left", padx=(12, 0))

    fila_bitrate = tk.Frame(panel_mp3)
    tk.Label(fila_bitrate, text="Bitrate:").pack(side="left")
    tk.Entry(fila_bitrate, textvariable=bitrate_var, width=10).pack(side="left", padx=(8, 18))
    tk.Label(fila_bitrate, text="Frecuencia:").pack(side="left")
    tk.Entry(fila_bitrate, textvariable=frecuencia_var, width=10).pack(side="left", padx=(8, 0))

    fila_ffmpeg = tk.Frame(panel_mp3)
    tk.Label(fila_ffmpeg, text="FFmpeg:").pack(side="left")
    tk.Entry(fila_ffmpeg, textvariable=ffmpeg_var, width=36).pack(side="left", fill="x", expand=True, padx=(8, 8))
    tk.Button(fila_ffmpeg, text="Detectar", command=lambda: detectar_ffmpeg()).pack(side="left", padx=(0, 8))
    tk.Button(fila_ffmpeg, text="Examinar", command=lambda: examinar_ffmpeg()).pack(side="left")

    def fila_modo(panel, variable):
        fila = tk.Frame(panel)
        tk.Label(fila, text="Origen:").pack(side="left")
        tk.Radiobutton(
            fila, text="Archivo", variable=variable, value="archivo", command=lambda: al_cambiar_detalle()
        ).pack(side="left", padx=(8, 0))
        tk.Radiobutton(
            fila, text="Carpeta", variable=variable, value="carpeta", command=lambda: al_cambiar_detalle()
        ).pack(side="left", padx=(12, 0))
        return fila

    fila_modo(panel_mkv, modo_mkv).pack(anchor="w", pady=(0, 8))
    fila_codecs = tk.Frame(panel_mkv)
    fila_codecs.pack(anchor="w")
    tk.Label(fila_codecs, text="Video codec:").pack(side="left")
    tk.Entry(fila_codecs, textvariable=video_codec_var, width=12).pack(side="left", padx=(8, 18))
    tk.Label(fila_codecs, text="Audio codec:").pack(side="left")
    tk.Entry(fila_codecs, textvariable=audio_codec_var, width=12).pack(side="left", padx=(8, 0))

    fila_modo(panel_gif, modo_gif).pack(anchor="w", pady=(0, 8))
    fila_gif = tk.Frame(panel_gif)
    fila_gif.pack(anchor="w")
    tk.Label(fila_gif, text="FPS:").pack(side="left")
    tk.Entry(fila_gif, textvariable=fps_var, width=8).pack(side="left", padx=(8, 18))
    tk.Label(fila_gif, text="Resize (w:h):").pack(side="left")
    tk.Entry(fila_gif, textvariable=resize_var, width=12).pack(side="left", padx=(8, 0))

    fila_resolucion = tk.Frame(panel_audio)
    fila_resolucion.pack(anchor="w")
    tk.Label(fila_resolucion, text="Resolucion:").pack(side="left")
    tk.Entry(fila_resolucion, textvariable=resolucion_var, width=12).pack(side="left", padx=(8, 0))

    rutas = tk.Frame(marco)
    rutas.pack(fill="x", pady=(14, 0))
    etiqueta_entrada = tk.Label(rutas, text="Archivo de entrada:")
    etiqueta_entrada.pack(anchor="w")
    fila_entrada = tk.Frame(rutas)
    fila_entrada.pack(fill="x", pady=(4, 8))
    tk.Entry(fila_entrada, textvariable=entrada_ruta).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(fila_entrada, text="Examinar", command=lambda: elegir_entrada()).pack(side="right")
    etiqueta_salida = tk.Label(rutas, text="Archivo de salida:")
    etiqueta_salida.pack(anchor="w")
    fila_salida = tk.Frame(rutas)
    fila_salida.pack(fill="x", pady=(4, 8))
    tk.Entry(fila_salida, textvariable=salida_ruta).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(fila_salida, text="Examinar", command=lambda: elegir_salida()).pack(side="right")

    boton_convertir = tk.Button(pie, text="Convertir", command=lambda: iniciar())
    boton_convertir.pack(fill="x", pady=(8, 8))
    tk.Label(pie, textvariable=estado_var, anchor="w", justify="left").pack(fill="x")

    def extension_entrada() -> str:
        return ENTRADA_POR_CLAVE[entrada_fmt.get()][1]

    def extension_salida() -> str:
        return SALIDA_POR_CLAVE[salida_fmt.get()][1]

    def es_moviepy() -> bool:
        return panel_de(entrada_fmt.get(), salida_fmt.get()) == "mp3" and motor_var.get() == "moviepy"

    def modo_actual() -> str:
        panel = panel_de(entrada_fmt.get(), salida_fmt.get())
        if panel == "mp3":
            return modo_mp3.get()
        if panel == "mkv":
            return modo_mkv.get()
        if panel == "gif":
            return modo_gif.get()
        return "archivo"

    def entrada_es_carpeta() -> bool:
        return modo_actual() == "carpeta" and not es_moviepy()

    def salida_es_carpeta() -> bool:
        return entrada_es_carpeta() or es_moviepy()

    def mostrar_panel(clave: str):
        for nombre, panel in paneles.items():
            if nombre == clave:
                panel.grid(row=0, column=0, sticky="ew")
            elif panel.winfo_manager():
                panel.grid_remove()

    def colocar_audio_video():
        es_py = motor_var.get() == "moviepy"
        if es_py and modo_mp3.get() != "archivo":
            modo_mp3.set("archivo")
        radio_carpeta_mp3.config(state=tk.DISABLED if es_py else tk.NORMAL)
        if not es_py and not ffmpeg_var.get().strip():
            detectado = resolver_ffmpeg()
            if detectado:
                ffmpeg_var.set(detectado)
        bloques = (fila_motor, fila_modo_mp3, fila_bitrate, fila_ffmpeg)
        for bloque in bloques:
            if bloque.winfo_manager() == "pack":
                bloque.pack_forget()
        visibles = [fila_motor, fila_modo_mp3]
        if not es_py:
            visibles.extend((fila_bitrate, fila_ffmpeg))
        for bloque in visibles:
            bloque.pack(fill="x", anchor="w", pady=(0, 8))

    def refrescar():
        validas = salidas_de(entrada_fmt.get())
        if salida_fmt.get() not in validas:
            salida_fmt.set(validas[0])
            validas = salidas_de(entrada_fmt.get())
        for clave, _texto, _extension in FORMATOS_SALIDA:
            radio = radios_salida[clave]
            if radio.winfo_manager():
                radio.pack_forget()
        for clave, _texto, _extension in FORMATOS_SALIDA:
            if clave in validas:
                radios_salida[clave].pack(anchor="w", pady=1)
        clave_panel = panel_de(entrada_fmt.get(), salida_fmt.get())
        mostrar_panel(clave_panel)
        if clave_panel == "mp3":
            colocar_audio_video()
        if entrada_es_carpeta():
            etiqueta_entrada.config(text="Carpeta de entrada:")
        else:
            etiqueta_entrada.config(text="Archivo de entrada:")
        if salida_es_carpeta():
            etiqueta_salida.config(text="Carpeta de salida:")
        else:
            etiqueta_salida.config(text="Archivo de salida:")
        texto_entrada, _extension = ENTRADA_POR_CLAVE[entrada_fmt.get()]
        texto_salida, _extension = SALIDA_POR_CLAVE[salida_fmt.get()]
        estado_var.set(f"{texto_entrada} a {texto_salida}.")

    def limpiar_rutas():
        entrada_ruta.set("")
        salida_ruta.set("")

    def al_cambiar_formato():
        limpiar_rutas()
        refrescar()

    def al_cambiar_detalle():
        limpiar_rutas()
        refrescar()

    def sugerir_salida(origen: str):
        if salida_ruta.get().strip() or not origen:
            return
        if salida_es_carpeta():
            if entrada_es_carpeta():
                salida_ruta.set(origen + "_" + salida_fmt.get())
            else:
                salida_ruta.set(os.path.dirname(origen))
            return
        base, _extension = os.path.splitext(origen)
        salida_ruta.set(base + extension_salida())

    def elegir_entrada():
        if entrada_es_carpeta():
            ruta = filedialog.askdirectory(title="Seleccionar carpeta de entrada")
        else:
            _texto, extension = ENTRADA_POR_CLAVE[entrada_fmt.get()]
            ruta = filedialog.askopenfilename(
                title="Seleccionar entrada",
                filetypes=[(f"Archivo {extension}", f"*{extension}"), ("Todos los archivos", "*.*")],
            )
        if ruta:
            entrada_ruta.set(ruta)
            sugerir_salida(ruta)
            estado_var.set("Entrada lista para convertir.")

    def elegir_salida():
        if salida_es_carpeta():
            ruta = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        else:
            extension = extension_salida()
            actual = salida_ruta.get().strip()
            ruta = filedialog.asksaveasfilename(
                title="Guardar como",
                initialdir=os.path.dirname(actual) if actual else os.getcwd(),
                initialfile=os.path.basename(actual) if actual else "salida" + extension,
                defaultextension=extension,
                filetypes=[(f"Archivo {extension}", f"*{extension}"), ("Todos los archivos", "*.*")],
            )
        if ruta:
            salida_ruta.set(ruta)

    def detectar_ffmpeg():
        ruta = resolver_ffmpeg()
        if ruta:
            ffmpeg_var.set(ruta)
            estado_var.set("FFmpeg detectado.")
        else:
            messagebox.showerror("FFmpeg no disponible", mensaje_ffmpeg_no_disponible())

    def examinar_ffmpeg():
        actual = ffmpeg_var.get().strip()
        ruta = filedialog.askopenfilename(
            title="Seleccionar ffmpeg",
            initialdir=os.path.dirname(actual) if actual else os.getcwd(),
            filetypes=[("FFmpeg", "ffmpeg.exe ffmpeg"), ("Ejecutables", "*.exe"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            ffmpeg_var.set(ruta)

    def terminar(correcto: bool, titulo: str, detalle: str):
        def aplicar():
            boton_convertir.config(state=tk.NORMAL, text="Convertir")
            estado_var.set(titulo if correcto else "No se pudo completar la conversion.")
            if correcto:
                messagebox.showinfo(titulo, detalle)
            else:
                messagebox.showerror(titulo, detalle)

        ventana.after(0, aplicar)

    def terminar_lote(info: dict, carpeta: str, clave_errores: str):
        errores = info.get(clave_errores) or []
        if info["total"] == 0:
            terminar(True, "Sin archivos", "No se encontraron archivos de ese formato en la carpeta.")
            return
        if errores:
            terminar(
                False,
                "Conversion parcial",
                f"Convertidos: {info['ok']} de {info['total']}\nErrores: {len(errores)}\n\nSalida:\n{carpeta}",
            )
            return
        terminar(True, "Operacion completada", f"Convertidos: {info['ok']} de {info['total']}\n\nGuardados en:\n{carpeta}")

    def convertir_carpeta_mp3(
        carpeta_entrada: str,
        carpeta_salida: str,
        extension: str,
        bitrate: str,
        frecuencia: str,
        binario: str,
    ):
        os.makedirs(carpeta_salida, exist_ok=True)
        total = 0
        correctos = 0
        errores = []
        for nombre in os.listdir(carpeta_entrada):
            if not nombre.lower().endswith(extension):
                continue
            total += 1
            origen = os.path.join(carpeta_entrada, nombre)
            destino = os.path.join(carpeta_salida, os.path.splitext(nombre)[0] + ".mp3")
            convertido, error = convertir_video_a_mp3(origen, destino, bitrate, frecuencia, binario)
            if convertido:
                correctos += 1
            else:
                errores.append((nombre, error))
        terminar_lote({"total": total, "ok": correctos, "errores": errores}, carpeta_salida, "errores")

    def exigir_ffmpeg() -> bool:
        if ffmpeg_disponible():
            return True
        messagebox.showerror(
            "FFmpeg no disponible",
            "FFmpeg no esta instalado o no esta en el PATH.\n\nInstalalo y reintenta.",
        )
        return False

    def iniciar():
        entrada = entrada_fmt.get()
        salida = salida_fmt.get()
        if salida not in salidas_de(entrada):
            messagebox.showwarning("Combinacion no disponible", "Elija una salida compatible con la entrada.")
            return
        origen = entrada_ruta.get().strip()
        destino = salida_ruta.get().strip()
        if not origen:
            messagebox.showwarning("Falta entrada", "Seleccione una entrada.")
            return
        if not destino:
            messagebox.showwarning("Falta salida", "Seleccione una salida.")
            return

        extension = extension_entrada()
        panel = panel_de(entrada, salida)

        if panel == "audio":
            resolucion = resolucion_var.get().strip() or DEFAULT_RESOLUTION
            if not os.path.isfile(origen) or not origen.lower().endswith(".mp3"):
                messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .mp3 existente.")
                return
            if not destino.lower().endswith(".mp4"):
                destino += ".mp4"
                salida_ruta.set(destino)
            if not resolucion_valida(resolucion):
                messagebox.showerror("Resolucion invalida", "Use el formato anchoxalto, por ejemplo 1280x720.")
                return
            if not exigir_ffmpeg():
                return
            padre = os.path.dirname(destino)
            if padre:
                os.makedirs(padre, exist_ok=True)

            def trabajo_audio():
                ok, error = convertir_mp3_a_mp4(origen, destino, resolucion)
                if ok:
                    terminar(True, "Operacion completada", f"Archivo guardado en:\n{destino}")
                else:
                    terminar(False, "Error de conversion", f"No se pudo convertir el archivo.\n\n{error}")

            boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
            estado_var.set("Convirtiendo, por favor espere...")
            threading.Thread(target=trabajo_audio, daemon=True).start()
            return

        if panel == "mp3" and es_moviepy():
            if not os.path.isfile(origen) or not origen.lower().endswith(extension):
                messagebox.showerror("Entrada invalida", f"La entrada debe ser un archivo {extension} existente.")
                return
            if not os.path.isdir(destino):
                messagebox.showerror("Salida invalida", "Seleccione una carpeta de guardado existente.")
                return
            ruta_mp3 = os.path.join(destino, os.path.splitext(os.path.basename(origen))[0] + ".mp3")

            def trabajo_moviepy():
                ok, error = convertir_con_moviepy(origen, ruta_mp3)
                if ok:
                    terminar(True, "Operacion completada", f"Archivo guardado en:\n{ruta_mp3}")
                else:
                    terminar(False, "Error de conversion", f"No se pudo convertir el archivo.\n\n{error}")

            boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
            estado_var.set("Convirtiendo con MoviePy, por favor espere...")
            threading.Thread(target=trabajo_moviepy, daemon=True).start()
            return

        if panel == "mp3":
            bitrate = bitrate_var.get().strip().lower() or BITRATE_PREDETERMINADO
            frecuencia = frecuencia_var.get().strip() or FRECUENCIA_PREDETERMINADA
            if not validar_bitrate(bitrate):
                messagebox.showerror("Bitrate invalido", "Use un bitrate como 128k, 192k o 320k.")
                return
            if not validar_frecuencia(frecuencia):
                messagebox.showerror("Frecuencia invalida", "Use una frecuencia numerica, por ejemplo 44100.")
                return
            binario = resolver_ffmpeg(ffmpeg_var.get().strip())
            if not binario:
                messagebox.showerror("FFmpeg no disponible", mensaje_ffmpeg_no_disponible(ffmpeg_var.get().strip()))
                return
            ffmpeg_var.set(binario)
            if modo_mp3.get() == "archivo":
                if not os.path.isfile(origen) or not origen.lower().endswith(extension):
                    messagebox.showerror("Entrada invalida", f"La entrada debe ser un archivo {extension} existente.")
                    return
                if not destino.lower().endswith(".mp3"):
                    destino += ".mp3"
                    salida_ruta.set(destino)
                padre = os.path.dirname(destino)
                if padre:
                    os.makedirs(padre, exist_ok=True)

                def trabajo_archivo():
                    ok, error = convertir_video_a_mp3(origen, destino, bitrate, frecuencia, binario)
                    if ok:
                        terminar(True, "Operacion completada", f"Archivo guardado en:\n{destino}")
                    else:
                        terminar(False, "Error de conversion", f"No se pudo convertir el archivo.\n\n{error}")

                objetivo = trabajo_archivo
            else:
                if not os.path.isdir(origen):
                    messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
                    return
                if os.path.isfile(destino):
                    messagebox.showerror("Salida invalida", "Para una carpeta, la salida debe ser una carpeta.")
                    return

                def trabajo_carpeta():
                    convertir_carpeta_mp3(origen, destino, extension, bitrate, frecuencia, binario)

                objetivo = trabajo_carpeta
            boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
            estado_var.set("Convirtiendo, por favor espere...")
            threading.Thread(target=objetivo, daemon=True).start()
            return

        if panel == "gif":
            try:
                fps = int(fps_var.get().strip())
                if fps <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Dato invalido", "FPS debe ser un numero entero mayor que 0.")
                return
            resize = resize_var.get().strip() or "640:-1"
            if not _validar_resize(resize):
                messagebox.showerror("Dato invalido", "Resize debe tener formato w:h, por ejemplo 640:-1.")
                return
            if not exigir_ffmpeg():
                return
            if modo_gif.get() == "archivo":
                if not os.path.isfile(origen) or not origen.lower().endswith(".mp4"):
                    messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .mp4 existente.")
                    return
                if not destino.lower().endswith(".gif"):
                    destino += ".gif"
                    salida_ruta.set(destino)

                def trabajo_gif():
                    ok, error = convertir_mp4_a_gif(origen, destino, fps, resize)
                    if ok:
                        terminar(True, "Operacion completada", "Conversion finalizada.")
                    else:
                        terminar(False, "Error", f"No se pudo convertir.\n\n{error}")

                objetivo = trabajo_gif
            else:
                if not os.path.isdir(origen):
                    messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
                    return
                if os.path.isfile(destino):
                    messagebox.showerror("Salida invalida", "Para una carpeta, la salida debe ser una carpeta.")
                    return

                def trabajo_gif_carpeta():
                    terminar_lote(carpeta_a_gif(origen, destino, fps, resize), destino, "errors")

                objetivo = trabajo_gif_carpeta
            boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
            estado_var.set("Convirtiendo, por favor espere...")
            threading.Thread(target=objetivo, daemon=True).start()
            return

        codec_video = video_codec_var.get().strip() or "copy"
        codec_audio = audio_codec_var.get().strip() or "copy"
        if not exigir_ffmpeg():
            return
        if modo_mkv.get() == "archivo":
            if not os.path.isfile(origen) or not origen.lower().endswith(".mp4"):
                messagebox.showerror("Entrada invalida", "La entrada debe ser un archivo .mp4 existente.")
                return
            if not destino.lower().endswith(".mkv"):
                destino += ".mkv"
                salida_ruta.set(destino)

            def trabajo_mkv():
                ok, error = convertir_mp4_a_mkv(origen, destino, codec_video, codec_audio)
                if ok:
                    terminar(True, "Operacion completada", "Conversion finalizada.")
                else:
                    terminar(False, "Error", f"No se pudo convertir.\n\n{error}")

            objetivo = trabajo_mkv
        else:
            if not os.path.isdir(origen):
                messagebox.showerror("Entrada invalida", "La entrada debe ser una carpeta existente.")
                return
            if os.path.isfile(destino):
                messagebox.showerror("Salida invalida", "Para una carpeta, la salida debe ser una carpeta.")
                return

            def trabajo_mkv_carpeta():
                terminar_lote(carpeta_a_mkv(origen, destino, codec_video, codec_audio), destino, "errors")

            objetivo = trabajo_mkv_carpeta
        boton_convertir.config(state=tk.DISABLED, text="Convirtiendo...")
        estado_var.set("Convirtiendo, por favor espere...")
        threading.Thread(target=objetivo, daemon=True).start()

    refrescar()
    ventana.entrada_fmt = entrada_fmt
    ventana.salida_fmt = salida_fmt
    ventana.paneles = paneles
    ventana.radios_entrada = radios_entrada
    ventana.radios_salida = radios_salida
    ventana.fila_bitrate = fila_bitrate
    ventana.fila_ffmpeg = fila_ffmpeg
    ventana.motor_var = motor_var
    ventana.radio_moviepy = radio_moviepy
    ventana.refrescar = refrescar
    if mostrar:
        ventana.deiconify()
    return ventana


def main():
    construir_interfaz().mainloop()


if __name__ == "__main__":
    main()
