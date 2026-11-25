import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import aplicacion.tema

from motores.lotes import AccionLote, buscar_archivos, ejecutar_accion_lote
from motores.video import extraer_todos_los_frames


def relanzar_con_python_global() -> bool:
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        return False

    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(os.path.abspath(sys.executable)):
        return False

    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=os.environ.copy())
        return True
    except OSError:
        return False


def crear_accion(
    intervalo: float | None,
    cantidades: tuple[int, ...] | list[int] | None = None,
) -> AccionLote:
    import MP4_a_Imagenes

    if MP4_a_Imagenes.cv2 is None:
        raise RuntimeError(
            "OpenCV (cv2) no esta disponible en el interprete actual.\n\n"
            f"Interprete:\n{sys.executable}\n\n"
            f"Detalle:\n{MP4_a_Imagenes._cv2_import_error}"
        )

    return AccionLote(
        nombre="MP4 a imagenes",
        extensiones=(".mp4",),
        procesar_archivo=lambda ruta: MP4_a_Imagenes.extraer_capturas(
            ruta, intervalo, cantidades
        ),
    )


def resumen_errores(errores, limite: int = 8) -> str:
    lineas = []
    for error in errores[:limite]:
        lineas.append(f"- {os.path.basename(error.ruta_archivo)}: {error.mensaje}")

    restantes = len(errores) - limite
    if restantes > 0:
        lineas.append(f"- ... y {restantes} error(es) mas.")

    return "\n".join(lineas)


MODOS_EXTRACCION = ("archivo", "carpeta", "automatico", "frames", "primer-frame")
MODOS_DE_ARCHIVO = {"archivo", "frames", "primer-frame"}
MENSAJES_MODO = {
    "archivo": "Seleccione un video MP4.",
    "carpeta": "Seleccione una carpeta para comenzar.",
    "automatico": "Seleccione una carpeta para comenzar.",
    "frames": "Seleccione un video para extraer todos sus frames.",
    "primer-frame": "Seleccione un video para guardar el primer frame.",
}
AYUDA_MODO = {
    "frames": (
        "Guarda cada frame como PNG, en orden, dentro de una carpeta nueva junto al video. "
        "Informa los FPS que reporta el decodificador."
    ),
    "primer-frame": (
        "Guarda una sola imagen PNG junto al video, sin crear una carpeta. "
        "Si ya existe, agrega un sufijo numerico."
    ),
}


def interpretar_modo(
    argv: list[str] | None = None,
    automatico: bool = False,
    modo: str | None = None,
) -> str:
    """Resuelve el modo de extraccion a partir de argumentos o de un valor directo."""
    if argv:
        indice = 0
        while indice < len(argv):
            if argv[indice] == "--modo" and indice + 1 < len(argv):
                modo = argv[indice + 1]
                indice += 2
            elif argv[indice] == "--automatico":
                modo = "automatico"
                indice += 1
            else:
                indice += 1
    if modo in MODOS_EXTRACCION:
        return modo
    return "automatico" if automatico else "carpeta"


def _ocultar(widget: tk.Widget) -> None:
    if widget.winfo_manager() == "grid":
        widget.grid_remove()


def construir_interfaz(modo: str = "carpeta", mostrar: bool = True) -> tk.Tk:
    """Crea la ventana de extraccion. Los modos absorbidos se eligen con los radios."""
    modo = interpretar_modo(modo=modo)
    root = tk.Tk()
    root.withdraw()
    root.title("Video a imagenes")
    root.resizable(False, True)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)

    tk.Label(frame, text="Modo:").grid(row=0, column=0, columnspan=3, sticky="w")
    modos = tk.Frame(frame)
    modos.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 8))
    modo_var = tk.StringVar(value=modo)
    radios = []
    for texto, valor in (
        ("Un video, cada N segundos", "archivo"),
        ("Carpeta, cada N segundos", "carpeta"),
        ("Carpeta, densidad segun duracion", "automatico"),
        ("Todos los frames", "frames"),
        ("Solo el primer frame", "primer-frame"),
    ):
        radio = tk.Radiobutton(
            modos,
            text=texto,
            variable=modo_var,
            value=valor,
            ayuda=AYUDA_MODO.get(valor),
        )
        radio.pack(anchor="w")
        radios.append(radio)

    etiqueta_ruta = tk.StringVar()
    tk.Label(frame, textvariable=etiqueta_ruta).grid(row=2, column=0, columnspan=3, sticky="w")
    ruta_var = tk.StringVar()
    entrada = tk.Entry(frame, textvariable=ruta_var, width=58)
    entrada.grid(row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_ruta():
        actual = modo_var.get()
        if actual in MODOS_DE_ARCHIVO:
            if actual == "archivo":
                tipos = [("Video MP4", "*.mp4"), ("Todos los archivos", "*.*")]
                titulo = "Seleccionar video MP4"
            else:
                tipos = [
                    ("Videos", "*.mp4 *.mkv *.avi *.mov *.webm"),
                    ("Todos los archivos", "*.*"),
                ]
                titulo = "Seleccionar video"
            ruta = filedialog.askopenfilename(title=titulo, filetypes=tipos)
        else:
            ruta = filedialog.askdirectory(title="Seleccionar carpeta con videos MP4")
        if ruta:
            ruta_var.set(ruta)

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_ruta)
    boton_examinar.grid(row=3, column=2, pady=(4, 8))

    marco_intervalo = tk.Frame(frame)
    tk.Label(marco_intervalo, text="Capturar un frame cada N segundos:").pack(anchor="w")
    intervalo_var = tk.StringVar(value="5")
    tk.Entry(marco_intervalo, textvariable=intervalo_var, width=12).pack(anchor="w", pady=(4, 8))

    import MP4_a_Imagenes

    marco_cantidades = tk.Frame(frame)
    tk.Label(
        marco_cantidades,
        text="Cantidad objetivo de capturas según la duración:",
        justify="left",
    ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
    nombres_rangos = (
        "R1  ≤ 1:35",
        "R2  ≤ 2:35",
        "R3  ≤ 5:10",
        "R4  ≤ 10:35",
        "R5  ≤ 20:35",
        "R6  ≤ 30:35",
        "R7  < 1 hora",
        "R8  ≥ 1 hora",
    )
    cantidad_vars = []
    for fila, (nombre, valor) in enumerate(
        zip(nombres_rangos, MP4_a_Imagenes.CANTIDADES_CAPTURA),
        start=1,
    ):
        variable = tk.IntVar(value=valor)
        cantidad_vars.append(variable)
        tk.Label(marco_cantidades, text=nombre, width=12, anchor="w").grid(row=fila, column=0, sticky="w")
        tk.Scale(
            marco_cantidades,
            from_=1,
            to=300,
            orient="horizontal",
            variable=variable,
            showvalue=False,
            length=310,
        ).grid(row=fila, column=1, sticky="we")
        tk.Spinbox(marco_cantidades, from_=1, to=9999, textvariable=variable, width=7).grid(
            row=fila, column=2, padx=(8, 0)
        )

    recursivo_var = tk.BooleanVar(value=False)
    casilla_recursivo = tk.Checkbutton(frame, text="Incluir subcarpetas", variable=recursivo_var)

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(frame, variable=progreso_var, maximum=100, length=470)
    barra.grid(row=6, column=0, columnspan=3, sticky="we", pady=(0, 6))
    estado_var = tk.StringVar()
    tk.Label(frame, textvariable=estado_var, justify="left", anchor="w", wraplength=500).grid(
        row=7, column=0, columnspan=3, sticky="we", pady=(0, 8)
    )

    botones = tk.Frame(frame)
    botones.grid(row=8, column=0, columnspan=3, sticky="we")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)
    boton_ejecutar = tk.Button(botones, text="Extraer imagenes")
    boton_ejecutar.grid(row=0, column=0, padx=(0, 4), sticky="we")
    boton_cancelar = tk.Button(botones, text="Cancelar", state="disabled")
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    cancelar_evento = threading.Event()
    viva = [True]
    procesando = [False]
    modo_previo = [modo]

    def aplicar_visibilidad():
        actual = modo_var.get()
        _ocultar(marco_intervalo)
        _ocultar(marco_cantidades)
        _ocultar(casilla_recursivo)
        if actual in ("archivo", "carpeta"):
            marco_intervalo.grid(row=4, column=0, columnspan=3, sticky="we", pady=(0, 8))
        elif actual == "automatico":
            marco_cantidades.grid(row=4, column=0, columnspan=3, sticky="we", pady=(0, 8))
        if actual in ("carpeta", "automatico"):
            casilla_recursivo.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))
            etiqueta_ruta.set("Carpeta con videos MP4:")
        elif actual == "archivo":
            etiqueta_ruta.set("Video MP4:")
        else:
            etiqueta_ruta.set("Video:")
        if actual == "primer-frame":
            boton_ejecutar.config(text="Guardar primer frame")
        elif actual == "frames":
            boton_ejecutar.config(text="Extraer frames")
        else:
            boton_ejecutar.config(text="Extraer imagenes")
        if actual == "archivo":
            _ocultar(boton_cancelar)
        elif boton_cancelar.winfo_manager() != "grid":
            boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    def cambiar_modo():
        nuevo = modo_var.get()
        if (nuevo in MODOS_DE_ARCHIVO) != (modo_previo[0] in MODOS_DE_ARCHIVO):
            ruta_var.set("")
        modo_previo[0] = nuevo
        aplicar_visibilidad()
        if not procesando[0]:
            estado_var.set(MENSAJES_MODO[nuevo])
            progreso_var.set(0)

    for radio in radios:
        radio.config(command=cambiar_modo)

    def solicitar_cancelacion():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        if modo_var.get() in ("frames", "primer-frame"):
            estado_var.set("Cancelando la extraccion...")
        else:
            estado_var.set("Cancelando al terminar el video actual...")

    boton_cancelar.config(command=solicitar_cancelacion)

    def en_ui(callback):
        if viva[0]:
            root.after(0, callback)

    def restaurar_controles():
        procesando[0] = False
        if str(barra.cget("mode")) == "indeterminate":
            barra.stop()
            barra.config(mode="determinate")
        boton_ejecutar.config(state="normal")
        boton_cancelar.config(state="disabled")
        entrada.config(state="normal")
        boton_examinar.config(state="normal")
        for radio in radios:
            radio.config(state="normal")
        aplicar_visibilidad()

    def iniciar_espera(permite_cancelar: bool, indeterminado: bool, texto: str):
        cancelar_evento.clear()
        procesando[0] = True
        boton_ejecutar.config(state="disabled")
        entrada.config(state="disabled")
        boton_examinar.config(state="disabled")
        for radio in radios:
            radio.config(state="disabled")
        boton_cancelar.config(state="normal" if permite_cancelar else "disabled")
        estado_var.set(texto)
        if indeterminado:
            barra.config(mode="indeterminate")
            barra.start(15)
        else:
            progreso_var.set(0)

    def finalizar_archivo(carpeta_salida: str, total: int):
        if not viva[0]:
            return
        restaurar_controles()
        estado_var.set(f"Imagenes generadas: {total}")
        progreso_var.set(100)
        messagebox.showinfo(
            "Operacion completada",
            f"Imagenes generadas: {total}\n\nGuardadas en:\n{carpeta_salida}",
        )

    def finalizar_lote(resultado):
        if not viva[0]:
            return
        restaurar_controles()
        completados = resultado.procesados + len(resultado.errores)
        porcentaje = (completados / resultado.total) * 100 if resultado.total else 0
        progreso_var.set(porcentaje)
        mensaje = (
            f"Videos encontrados: {resultado.total}\n"
            f"Procesados correctamente: {resultado.procesados}\n"
            f"Errores: {len(resultado.errores)}"
        )
        if resultado.cancelado:
            estado_var.set("Proceso cancelado.")
            messagebox.showwarning("Proceso cancelado", mensaje)
        elif resultado.errores:
            estado_var.set("Proceso completado con errores.")
            messagebox.showwarning(
                "Proceso completado con errores",
                f"{mensaje}\n\n{resumen_errores(resultado.errores)}",
            )
        else:
            progreso_var.set(100)
            estado_var.set("Todos los videos fueron procesados.")
            messagebox.showinfo("Operacion completada", mensaje)

    def finalizar_frames(resultado):
        if not viva[0]:
            return
        restaurar_controles()
        destino = (
            f"Imagen: {resultado.archivo}"
            if resultado.archivo
            else f"Carpeta: {resultado.carpeta or '(ninguna)'}"
        )
        mensaje = (
            f"FPS del video: {resultado.fps:.3f}\n"
            f"Frames guardados: {resultado.total}\n"
            f"{destino}"
        )
        estado_var.set(mensaje)
        progreso_var.set(100)
        titulo = "Extraccion cancelada" if resultado.cancelado else "Extraccion completada"
        messagebox.showinfo(titulo, mensaje)

    def finalizar_error(error: str):
        if not viva[0]:
            return
        restaurar_controles()
        estado_var.set("No se pudo completar la extraccion.")
        messagebox.showerror("Error", error)

    def actualizar_progreso(indice: int, total: int, ruta_archivo: str):
        porcentaje = ((indice - 1) / total) * 100 if total else 0

        def actualizar():
            if not viva[0]:
                return
            progreso_var.set(porcentaje)
            estado_var.set(f"Procesando {indice} de {total}:\n{os.path.basename(ruta_archivo)}")

        en_ui(actualizar)

    def leer_intervalo() -> float:
        try:
            intervalo = float(intervalo_var.get().strip().replace(",", "."))
            if intervalo <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("N debe ser un numero mayor que 0.") from None
        return intervalo

    def leer_cantidades() -> tuple[int, ...]:
        try:
            cantidades = tuple(variable.get() for variable in cantidad_vars)
            if any(cantidad <= 0 for cantidad in cantidades):
                raise ValueError
        except (ValueError, tk.TclError):
            raise ValueError("Cada rango debe tener una cantidad entera mayor que 0.") from None
        return cantidades

    def ejecutar():
        if procesando[0]:
            return
        actual = modo_var.get()
        ruta = ruta_var.get().strip().strip('"')
        if actual in MODOS_DE_ARCHIVO:
            if not os.path.isfile(ruta):
                messagebox.showerror("Ruta invalida", "Seleccione un archivo de video existente.")
                return
        elif not os.path.isdir(ruta):
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta existente.")
            return

        if actual == "archivo" and not ruta.lower().endswith(".mp4"):
            messagebox.showerror("Archivo invalido", "Seleccione un archivo con extension .mp4.")
            return

        try:
            if actual in ("archivo", "carpeta"):
                intervalo = leer_intervalo()
                cantidades = None
            elif actual == "automatico":
                intervalo = None
                cantidades = leer_cantidades()
            else:
                intervalo = None
                cantidades = None
        except ValueError as exc:
            messagebox.showerror("Dato invalido", str(exc))
            return

        if actual in ("carpeta", "automatico"):
            try:
                accion = crear_accion(intervalo, cantidades)
                archivos = buscar_archivos(ruta, accion.extensiones, recursivo=recursivo_var.get())
            except Exception as exc:
                messagebox.showerror("Error", f"No se pudo preparar la accion.\n\n{exc}")
                return
            if not archivos:
                messagebox.showinfo("Sin videos", "No se encontraron archivos MP4.")
                return
            iniciar_espera(True, False, f"Preparando {len(archivos)} video(s)...")

            def worker_lote():
                try:
                    resultado = ejecutar_accion_lote(
                        accion,
                        archivos,
                        al_progresar=actualizar_progreso,
                        debe_cancelar=cancelar_evento.is_set,
                    )
                    en_ui(lambda: finalizar_lote(resultado))
                except Exception as exc:
                    texto = str(exc)
                    en_ui(lambda: finalizar_error(texto))

            threading.Thread(target=worker_lote, daemon=True).start()
            return

        if actual == "archivo":
            iniciar_espera(False, True, "Extrayendo imagenes... Esto puede tardar segun la duracion del video.")

            def worker_archivo():
                try:
                    carpeta_salida, total = MP4_a_Imagenes.extraer_capturas(ruta, intervalo)
                    en_ui(lambda: finalizar_archivo(carpeta_salida, total))
                except Exception as exc:
                    texto = str(exc)
                    en_ui(lambda: finalizar_error(texto))

            threading.Thread(target=worker_archivo, daemon=True).start()
            return

        iniciar_espera(True, True, "Leyendo el video y extrayendo frames...")
        solo_primero = actual == "primer-frame"
        fps_actual = [0.0]

        def worker_frames():
            try:
                def mostrar_fps(fps: float):
                    fps_actual[0] = fps
                    en_ui(lambda: estado_var.set(f"FPS del video: {fps:.3f}. Extrayendo frames..."))

                def al_progresar(total: int):
                    en_ui(lambda: estado_var.set(f"FPS: {fps_actual[0]:.3f} | Frames guardados: {total}"))

                resultado = extraer_todos_los_frames(
                    ruta,
                    progreso=al_progresar,
                    cancelar=cancelar_evento.is_set,
                    fps_detectados=mostrar_fps,
                    solo_primer_frame=solo_primero,
                )
                en_ui(lambda: finalizar_frames(resultado))
            except Exception as exc:
                texto = str(exc)
                en_ui(lambda: finalizar_error(texto))

        threading.Thread(target=worker_frames, daemon=True).start()

    def cerrar():
        viva[0] = False
        cancelar_evento.set()
        root.destroy()

    boton_ejecutar.config(command=ejecutar)
    root.protocol("WM_DELETE_WINDOW", cerrar)
    aplicar_visibilidad()
    estado_var.set(MENSAJES_MODO[modo_var.get()])
    entrada.focus_set()

    root.modo_var = modo_var
    root.panel_intervalo = marco_intervalo
    root.panel_cantidades = marco_cantidades
    root.casilla_recursivo = casilla_recursivo
    root.boton_extraer = boton_ejecutar

    if mostrar:
        root.deiconify()
    return root


def main(automatico: bool = False, modo: str | None = None):
    construir_interfaz(interpretar_modo(automatico=automatico, modo=modo)).mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main(modo=interpretar_modo(sys.argv[1:]))
