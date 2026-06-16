"""
Busca carpetas vacias dentro de una carpeta seleccionada.

Una carpeta se considera vacia cuando contiene cero elementos inmediatos:
ningun archivo y ninguna subcarpeta. La carpeta raiz seleccionada no se incluye
en los resultados. La busqueda es recursiva y se ejecuta en segundo plano para
mantener activa la interfaz.

Despues de buscar, todas las carpetas encontradas pueden moverse a una carpeta
"carpetas vacías", creada dentro de la raiz seleccionada, o eliminarse
definitivamente. Al moverlas se conserva su ruta relativa para evitar conflictos
entre carpetas que tengan el mismo nombre.
"""

import os
import queue
import shutil
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk


CallbackProgreso = Callable[[int, int, str], None]
CallbackCancelacion = Callable[[], bool]
NOMBRE_CARPETA_DESTINO = "carpetas vacías"


def es_ruta_interna(ruta: str, carpeta_raiz: str) -> bool:
    try:
        return os.path.commonpath(
            [os.path.normcase(os.path.abspath(ruta)), os.path.normcase(carpeta_raiz)]
        ) == os.path.normcase(carpeta_raiz)
    except ValueError:
        return False


def encontrar_carpetas_vacias(
    carpeta_raiz: str,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    """Devuelve carpetas vacias, cantidad revisada, errores y cancelacion."""
    carpeta_raiz = os.path.abspath(carpeta_raiz)
    vacias: list[str] = []
    errores: list[tuple[str, str]] = []
    revisadas = 0
    cancelado = False

    def registrar_error(error: OSError):
        ruta = error.filename or carpeta_raiz
        errores.append((ruta, str(error)))

    for carpeta_actual, subcarpetas, archivos in os.walk(
        carpeta_raiz,
        topdown=True,
        onerror=registrar_error,
        followlinks=False,
    ):
        if debe_cancelar is not None and debe_cancelar():
            cancelado = True
            break

        if carpeta_actual == carpeta_raiz:
            subcarpetas[:] = [
                nombre
                for nombre in subcarpetas
                if nombre.casefold() != NOMBRE_CARPETA_DESTINO.casefold()
            ]

        subcarpetas.sort(key=str.lower)
        revisadas += 1

        if carpeta_actual != carpeta_raiz and not subcarpetas and not archivos:
            vacias.append(carpeta_actual)

        if al_progresar is not None and (revisadas % 25 == 0 or revisadas == 1):
            al_progresar(revisadas, len(vacias), carpeta_actual)

    vacias.sort(key=str.lower)
    return {
        "empty_folders": vacias,
        "scanned": revisadas,
        "errors": errores,
        "cancelled": cancelado,
    }


def mover_carpetas_vacias(
    carpetas: list[str],
    carpeta_raiz: str,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    carpeta_raiz = os.path.abspath(carpeta_raiz)
    carpeta_destino = os.path.join(carpeta_raiz, NOMBRE_CARPETA_DESTINO)
    movidas: list[str] = []
    errores: list[tuple[str, str]] = []
    cancelado = False

    if carpetas:
        os.makedirs(carpeta_destino, exist_ok=True)

    for indice, ruta in enumerate(carpetas, start=1):
        if debe_cancelar is not None and debe_cancelar():
            cancelado = True
            break

        ruta = os.path.abspath(ruta)
        try:
            if not es_ruta_interna(ruta, carpeta_raiz) or ruta == carpeta_raiz:
                raise ValueError("La carpeta no pertenece a la raiz seleccionada.")
            if not os.path.isdir(ruta):
                raise FileNotFoundError("La carpeta ya no existe.")
            if os.listdir(ruta):
                raise OSError("La carpeta ya no esta vacia.")

            ruta_relativa = os.path.relpath(ruta, carpeta_raiz)
            destino = os.path.join(carpeta_destino, ruta_relativa)
            if os.path.exists(destino):
                raise FileExistsError(f"Ya existe el destino: {destino}")

            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.move(ruta, destino)
            movidas.append(ruta)
        except Exception as exc:
            errores.append((ruta, str(exc)))

        if al_progresar is not None:
            al_progresar(indice, len(carpetas), ruta)

    return {
        "processed": movidas,
        "errors": errores,
        "cancelled": cancelado,
        "destination": carpeta_destino,
    }


def eliminar_carpetas_vacias(
    carpetas: list[str],
    carpeta_raiz: str,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    carpeta_raiz = os.path.abspath(carpeta_raiz)
    eliminadas: list[str] = []
    errores: list[tuple[str, str]] = []
    cancelado = False

    for indice, ruta in enumerate(carpetas, start=1):
        if debe_cancelar is not None and debe_cancelar():
            cancelado = True
            break

        ruta = os.path.abspath(ruta)
        try:
            if not es_ruta_interna(ruta, carpeta_raiz) or ruta == carpeta_raiz:
                raise ValueError("La carpeta no pertenece a la raiz seleccionada.")
            os.rmdir(ruta)
            eliminadas.append(ruta)
        except Exception as exc:
            errores.append((ruta, str(exc)))

        if al_progresar is not None:
            al_progresar(indice, len(carpetas), ruta)

    return {
        "processed": eliminadas,
        "errors": errores,
        "cancelled": cancelado,
    }


def main():
    root = tk.Tk()
    root.title("Encontrar carpetas vacias")
    root.geometry("780x540")
    root.minsize(620, 420)

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(5, weight=1)

    ttk.Label(frame, text="Carpeta raiz:").grid(row=0, column=0, sticky="w")

    carpeta_var = tk.StringVar()
    carpeta_entry = ttk.Entry(frame, textvariable=carpeta_var)
    carpeta_entry.grid(row=1, column=0, padx=(0, 8), pady=(4, 10), sticky="ew")

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta raiz")
        if carpeta:
            carpeta_var.set(carpeta)

    boton_examinar = ttk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=1, pady=(4, 10), sticky="ew")

    progreso = ttk.Progressbar(frame, mode="indeterminate")
    progreso.grid(row=2, column=0, columnspan=2, sticky="ew")

    estado_var = tk.StringVar(
        value="Seleccione una carpeta para buscar directorios con 0 elementos."
    )
    ttk.Label(
        frame,
        textvariable=estado_var,
        anchor="w",
        justify="left",
    ).grid(row=3, column=0, columnspan=2, pady=(8, 8), sticky="ew")

    ttk.Label(frame, text="Carpetas con 0 elementos:").grid(
        row=4,
        column=0,
        columnspan=2,
        sticky="w",
    )

    resultado_frame = ttk.Frame(frame)
    resultado_frame.grid(row=5, column=0, columnspan=2, sticky="nsew")
    resultado_frame.columnconfigure(0, weight=1)
    resultado_frame.rowconfigure(0, weight=1)

    lista = tk.Listbox(resultado_frame, selectmode="extended")
    lista.grid(row=0, column=0, sticky="nsew")

    scroll_y = ttk.Scrollbar(resultado_frame, orient="vertical", command=lista.yview)
    scroll_y.grid(row=0, column=1, sticky="ns")
    lista.config(yscrollcommand=scroll_y.set)

    scroll_x = ttk.Scrollbar(resultado_frame, orient="horizontal", command=lista.xview)
    scroll_x.grid(row=1, column=0, sticky="ew")
    lista.config(xscrollcommand=scroll_x.set)

    botones = ttk.Frame(frame)
    botones.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="ew")
    for columna in range(3):
        botones.columnconfigure(columna, weight=1)

    mensajes: queue.Queue[tuple[str, object]] = queue.Queue()
    cancelar_evento = threading.Event()
    proceso_activo = False
    ultimo_resultado: list[str] = []
    ultima_raiz = ""
    operacion_actual = ""

    def configurar_controles(en_proceso: bool):
        estado = "disabled" if en_proceso else "normal"
        carpeta_entry.config(state=estado)
        boton_examinar.config(state=estado)
        boton_buscar.config(state=estado)
        boton_cancelar.config(state="normal" if en_proceso else "disabled")
        estado_acciones = (
            "normal" if not en_proceso and ultimo_resultado else "disabled"
        )
        boton_mover.config(state=estado_acciones)
        boton_eliminar.config(state=estado_acciones)

    def buscar():
        nonlocal proceso_activo, ultima_raiz, operacion_actual
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta raiz.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta seleccionada no existe.")
            return

        lista.delete(0, tk.END)
        ultimo_resultado.clear()
        ultima_raiz = os.path.abspath(carpeta)
        cancelar_evento.clear()
        proceso_activo = True
        operacion_actual = "busqueda"
        configurar_controles(True)
        progreso.start(12)
        estado_var.set("Iniciando busqueda recursiva...")

        def informar(revisadas: int, encontradas: int, ruta: str):
            mensajes.put(("progreso", (revisadas, encontradas, ruta)))

        def worker():
            try:
                resultado = encontrar_carpetas_vacias(
                    carpeta,
                    al_progresar=informar,
                    debe_cancelar=cancelar_evento.is_set,
                )
                mensajes.put(("final", resultado))
            except Exception as exc:
                mensajes.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def cancelar():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        mensajes_cancelacion = {
            "busqueda": "Cancelando la busqueda...",
            "mover": "Cancelando el movimiento...",
            "eliminar": "Cancelando la eliminacion...",
        }
        estado_var.set(
            mensajes_cancelacion.get(operacion_actual, "Cancelando la operacion...")
        )

    def copiar_resultados():
        if not ultimo_resultado:
            messagebox.showinfo("Sin resultados", "No hay rutas para copiar.")
            return

        root.clipboard_clear()
        root.clipboard_append("\n".join(ultimo_resultado))
        root.update()
        estado_var.set(f"Se copiaron {len(ultimo_resultado)} rutas al portapapeles.")

    def guardar_resultados():
        if not ultimo_resultado:
            messagebox.showinfo("Sin resultados", "No hay rutas para guardar.")
            return

        destino = filedialog.asksaveasfilename(
            title="Guardar lista de carpetas vacias",
            defaultextension=".txt",
            filetypes=(("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")),
            initialfile="carpetas_vacias.txt",
        )
        if not destino:
            return

        try:
            with open(destino, "w", encoding="utf-8") as archivo:
                archivo.write("\n".join(ultimo_resultado))
                archivo.write("\n")
        except OSError as exc:
            messagebox.showerror("Error al guardar", str(exc))
            return

        estado_var.set(f"Resultados guardados en: {destino}")

    def actualizar_lista():
        lista.delete(0, tk.END)
        for carpeta in ultimo_resultado:
            lista.insert(tk.END, carpeta)

    def iniciar_accion(accion: str):
        nonlocal proceso_activo, operacion_actual
        if not ultimo_resultado:
            messagebox.showinfo(
                "Sin resultados",
                "Primero busque carpetas vacias.",
            )
            return

        cantidad = len(ultimo_resultado)
        if accion == "mover":
            confirmado = messagebox.askyesno(
                "Mover carpetas vacias",
                f"Se moveran {cantidad} carpeta(s) a:\n\n"
                f"{os.path.join(ultima_raiz, NOMBRE_CARPETA_DESTINO)}\n\n"
                "Se conservara la estructura relativa. ¿Desea continuar?",
            )
        else:
            confirmado = messagebox.askyesno(
                "Eliminar carpetas vacias",
                f"Se eliminaran definitivamente {cantidad} carpeta(s) vacia(s).\n\n"
                "Esta accion no se puede deshacer. ¿Desea continuar?",
                icon="warning",
            )

        if not confirmado:
            return

        rutas = list(ultimo_resultado)
        cancelar_evento.clear()
        proceso_activo = True
        operacion_actual = accion
        configurar_controles(True)
        progreso.start(12)
        estado_var.set(
            "Preparando el movimiento..."
            if accion == "mover"
            else "Preparando la eliminacion..."
        )

        def informar(procesadas: int, total: int, ruta: str):
            mensajes.put(
                ("accion_progreso", (accion, procesadas, total, ruta))
            )

        def worker():
            try:
                funcion = (
                    mover_carpetas_vacias
                    if accion == "mover"
                    else eliminar_carpetas_vacias
                )
                resultado = funcion(
                    rutas,
                    ultima_raiz,
                    al_progresar=informar,
                    debe_cancelar=cancelar_evento.is_set,
                )
                resultado["action"] = accion
                mensajes.put(("accion_final", resultado))
            except Exception as exc:
                mensajes.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    boton_buscar = ttk.Button(botones, text="Buscar", command=buscar)
    boton_buscar.grid(row=0, column=0, padx=(0, 4), pady=(0, 4), sticky="ew")

    boton_cancelar = ttk.Button(
        botones,
        text="Cancelar",
        command=cancelar,
        state="disabled",
    )
    boton_cancelar.grid(row=0, column=1, padx=4, pady=(0, 4), sticky="ew")

    ttk.Button(botones, text="Copiar rutas", command=copiar_resultados).grid(
        row=0,
        column=2,
        padx=(4, 0),
        pady=(0, 4),
        sticky="ew",
    )
    ttk.Button(botones, text="Guardar TXT", command=guardar_resultados).grid(
        row=1,
        column=0,
        padx=(0, 4),
        pady=(4, 0),
        sticky="ew",
    )

    boton_mover = ttk.Button(
        botones,
        text="Mover todas",
        command=lambda: iniciar_accion("mover"),
        state="disabled",
    )
    boton_mover.grid(row=1, column=1, padx=4, pady=(4, 0), sticky="ew")

    boton_eliminar = ttk.Button(
        botones,
        text="Eliminar todas",
        command=lambda: iniciar_accion("eliminar"),
        state="disabled",
    )
    boton_eliminar.grid(
        row=1,
        column=2,
        padx=(4, 0),
        pady=(4, 0),
        sticky="ew",
    )

    def finalizar(resultado: dict):
        nonlocal proceso_activo, operacion_actual
        proceso_activo = False
        operacion_actual = ""
        progreso.stop()

        ultimo_resultado.extend(resultado["empty_folders"])
        actualizar_lista()
        configurar_controles(False)

        resumen = (
            f"Carpetas revisadas: {resultado['scanned']} | "
            f"Vacias: {len(ultimo_resultado)} | "
            f"Errores: {len(resultado['errors'])}"
        )
        if resultado["cancelled"]:
            estado_var.set(f"Busqueda cancelada. {resumen}")
        else:
            estado_var.set(f"Busqueda terminada. {resumen}")

        if resultado["errors"]:
            primeros = "\n".join(
                f"- {ruta}: {error}"
                for ruta, error in resultado["errors"][:5]
            )
            messagebox.showwarning(
                "Busqueda completada con errores",
                f"{resumen}\n\n{primeros}",
            )

    def finalizar_accion(resultado: dict):
        nonlocal proceso_activo, operacion_actual
        proceso_activo = False
        operacion_actual = ""
        progreso.stop()

        procesadas = set(resultado["processed"])
        ultimo_resultado[:] = [
            ruta for ruta in ultimo_resultado if ruta not in procesadas
        ]
        actualizar_lista()
        configurar_controles(False)

        accion = resultado["action"]
        verbo = "movidas" if accion == "mover" else "eliminadas"
        resumen = (
            f"Carpetas {verbo}: {len(procesadas)} | "
            f"Errores: {len(resultado['errors'])} | "
            f"Pendientes: {len(ultimo_resultado)}"
        )

        if resultado["cancelled"]:
            estado_var.set(f"Accion cancelada. {resumen}")
        else:
            estado_var.set(f"Accion terminada. {resumen}")

        if resultado["errors"]:
            primeros = "\n".join(
                f"- {ruta}: {error}"
                for ruta, error in resultado["errors"][:5]
            )
            messagebox.showwarning(
                "Accion completada con errores",
                f"{resumen}\n\n{primeros}",
            )
        elif not resultado["cancelled"]:
            detalle = ""
            if accion == "mover":
                detalle = f"\n\nDestino:\n{resultado['destination']}"
            messagebox.showinfo("Accion completada", resumen + detalle)

    def revisar_mensajes():
        try:
            while True:
                tipo, contenido = mensajes.get_nowait()
                if tipo == "progreso":
                    revisadas, encontradas, ruta = contenido
                    estado_var.set(
                        f"Revisadas: {revisadas} | Vacias: {encontradas}\n{ruta}"
                    )
                elif tipo == "accion_progreso":
                    accion, procesadas, total, ruta = contenido
                    verbo = "Moviendo" if accion == "mover" else "Eliminando"
                    estado_var.set(
                        f"{verbo}: {procesadas} de {total}\n{ruta}"
                    )
                elif tipo == "final":
                    finalizar(contenido)
                elif tipo == "accion_final":
                    finalizar_accion(contenido)
                elif tipo == "error":
                    nonlocal proceso_activo, operacion_actual
                    proceso_activo = False
                    operacion_actual = ""
                    progreso.stop()
                    configurar_controles(False)
                    estado_var.set("La busqueda no pudo completarse.")
                    messagebox.showerror("Error", str(contenido))
        except queue.Empty:
            pass

        root.after(100, revisar_mensajes)

    def cerrar():
        if proceso_activo:
            cancelar_evento.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cerrar)
    root.after(100, revisar_mensajes)
    carpeta_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
