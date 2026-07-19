import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from motores.lotes import AccionLote, buscar_archivos, ejecutar_accion_lote


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


def crear_accion(intervalo: float) -> AccionLote:
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
        procesar_archivo=lambda ruta: MP4_a_Imagenes.extraer_capturas(ruta, intervalo),
    )


def resumen_errores(errores, limite: int = 8) -> str:
    lineas = []
    for error in errores[:limite]:
        lineas.append(f"- {os.path.basename(error.ruta_archivo)}: {error.mensaje}")

    restantes = len(errores) - limite
    if restantes > 0:
        lineas.append(f"- ... y {restantes} error(es) mas.")

    return "\n".join(lineas)


def main():
    root = tk.Tk()
    root.title("MP4 -> Imagenes por carpeta")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta con videos MP4:").grid(row=0, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    carpeta_entry = tk.Entry(frame, textvariable=carpeta_var, width=58)
    carpeta_entry.grid(
        row=1,
        column=0,
        columnspan=2,
        padx=(0, 6),
        pady=(4, 8),
        sticky="we",
    )

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con videos MP4")
        if carpeta:
            carpeta_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_carpeta).grid(
        row=1,
        column=2,
        pady=(4, 8),
    )

    tk.Label(frame, text="Capturar un frame cada N segundos:").grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="w",
    )
    intervalo_var = tk.StringVar(value="5")
    intervalo_entry = tk.Entry(frame, textvariable=intervalo_var, width=12)
    intervalo_entry.grid(row=3, column=0, pady=(4, 8), sticky="w")

    recursivo_var = tk.BooleanVar(value=False)
    tk.Checkbutton(
        frame,
        text="Incluir subcarpetas",
        variable=recursivo_var,
    ).grid(row=3, column=1, columnspan=2, sticky="w", pady=(4, 8))

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=470,
    )
    barra.grid(row=4, column=0, columnspan=3, sticky="we", pady=(0, 6))

    estado_var = tk.StringVar(value="Seleccione una carpeta para comenzar.")
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=500,
    ).grid(row=5, column=0, columnspan=3, sticky="we", pady=(0, 8))

    botones = tk.Frame(frame)
    botones.grid(row=6, column=0, columnspan=3, sticky="we")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)

    boton_ejecutar = tk.Button(botones, text="Extraer imagenes")
    boton_ejecutar.grid(row=0, column=0, padx=(0, 4), sticky="we")

    cancelar_evento = threading.Event()

    def solicitar_cancelacion():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        estado_var.set("Cancelando al terminar el video actual...")

    boton_cancelar = tk.Button(
        botones,
        text="Cancelar",
        state="disabled",
        command=solicitar_cancelacion,
    )
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    def actualizar_progreso(indice: int, total: int, ruta_archivo: str):
        porcentaje = ((indice - 1) / total) * 100 if total else 0

        def actualizar():
            progreso_var.set(porcentaje)
            estado_var.set(
                f"Procesando {indice} de {total}:\n{os.path.basename(ruta_archivo)}"
            )

        root.after(0, actualizar)

    def finalizar(resultado):
        boton_ejecutar.config(state="normal")
        boton_cancelar.config(state="disabled")

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
            detalle = resumen_errores(resultado.errores)
            messagebox.showwarning(
                "Proceso completado con errores",
                f"{mensaje}\n\n{detalle}",
            )
        else:
            progreso_var.set(100)
            estado_var.set("Todos los videos fueron procesados.")
            messagebox.showinfo("Operacion completada", mensaje)

    def finalizar_error(error: str):
        boton_ejecutar.config(state="normal")
        boton_cancelar.config(state="disabled")
        estado_var.set("No se pudo iniciar el procesamiento.")
        messagebox.showerror("Error", error)

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta no existe.")
            return

        try:
            intervalo = float(intervalo_var.get().strip().replace(",", "."))
            if intervalo <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Dato invalido", "N debe ser un numero mayor que 0.")
            return

        try:
            accion = crear_accion(intervalo)
            archivos = buscar_archivos(
                carpeta,
                accion.extensiones,
                recursivo=recursivo_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo preparar la accion.\n\n{exc}")
            return

        if not archivos:
            messagebox.showinfo("Sin videos", "No se encontraron archivos MP4.")
            return

        cancelar_evento.clear()
        progreso_var.set(0)
        boton_ejecutar.config(state="disabled")
        boton_cancelar.config(state="normal")
        estado_var.set(f"Preparando {len(archivos)} video(s)...")

        def worker():
            try:
                resultado = ejecutar_accion_lote(
                    accion,
                    archivos,
                    al_progresar=actualizar_progreso,
                    debe_cancelar=cancelar_evento.is_set,
                )
                root.after(0, finalizar, resultado)
            except Exception as exc:
                error = str(exc)
                root.after(0, finalizar_error, error)

        threading.Thread(target=worker, daemon=True).start()

    boton_ejecutar.config(command=ejecutar)
    carpeta_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
