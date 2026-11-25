import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema

from motores.renombrado import afijo, afijo_valido, nombre_con_afijos

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception as exc:  # pragma: no cover
    Observer = None
    FileSystemEventHandler = object
    _watchdog_import_error = str(exc)


def _group_to_index(group: str) -> int:
    """Convierte A, B, ..., Z, AA, AB... a indice 0-based."""
    group = group.strip().upper()
    if not group or not group.isalpha():
        raise ValueError("Grupo invalido")

    n = 0
    for ch in group:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _index_to_group(index: int) -> str:
    """Convierte indice 0-based a A, B, ..., Z, AA, AB..."""
    if index < 0:
        raise ValueError("Indice invalido")

    n = index + 1
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


class ImageGrouper:
    def __init__(self, folder_path: str, prefijo: str = "", sufijo: str = ""):
        self.folder_path = folder_path
        self.prefijo = afijo(prefijo)
        self.sufijo = afijo(sufijo)
        self.next_group_index = 0
        self.scan_existing_groups()

    def _nombre_visible(self, filename: str) -> str:
        base, extension = os.path.splitext(filename)
        if self.prefijo and base.startswith(self.prefijo):
            base = base[len(self.prefijo) :]
        if self.sufijo and base.endswith(self.sufijo):
            base = base[: -len(self.sufijo)]
        return f"{base}{extension}"

    def scan_existing_groups(self):
        """Escanea la carpeta para detectar grupos existentes."""
        max_index = -1
        for filename in os.listdir(self.folder_path):
            visible = self._nombre_visible(filename)
            if "_" not in visible:
                continue

            group = visible.split("_", 1)[0]
            if not group.isalpha():
                continue

            try:
                idx = _group_to_index(group)
            except Exception:
                continue

            if idx > max_index:
                max_index = idx

        self.next_group_index = max_index + 1

    def process_new_images(self):
        """Procesa imagenes nuevas sin grupo.

        Criterio: archivos .png cuyo nombre base sea numerico y no contenga '_' (ej: 001.png).

        Devuelve: cantidad renombrada.
        """
        new_images = []
        for nombre in os.listdir(self.folder_path):
            visible = self._nombre_visible(nombre)
            if (
                visible.lower().endswith(".png")
                and "_" not in visible
                and os.path.splitext(visible)[0].isdigit()
                and os.path.isfile(os.path.join(self.folder_path, nombre))
            ):
                new_images.append(nombre)

        if not new_images:
            return 0

        new_images.sort(key=lambda x: int(os.path.splitext(self._nombre_visible(x))[0]))

        group_char = _index_to_group(self.next_group_index)
        renamed = 0

        for filename in new_images:
            new_name = nombre_con_afijos(
                f"{group_char}_{filename}",
                self.prefijo,
                self.sufijo,
            )
            old_path = os.path.join(self.folder_path, filename)
            new_path = os.path.join(self.folder_path, new_name)

            try:
                os.rename(old_path, new_path)
                renamed += 1
                print(f"Renombrado: {filename} -> {new_name}")
            except Exception as exc:
                print(f"Error al renombrar {filename}: {exc}")

        self.next_group_index += 1
        return renamed

    @property
    def next_group_label(self) -> str:
        return _index_to_group(self.next_group_index)


class ImageHandler(FileSystemEventHandler):
    def __init__(self, grouper: ImageGrouper, on_batch_done=None):
        self.grouper = grouper
        self.on_batch_done = on_batch_done

    def on_created(self, event):
        if getattr(event, "is_directory", False):
            return
        if not str(getattr(event, "src_path", "")).lower().endswith(".png"):
            return

        # Esperar un momento para asegurar que el archivo este completamente escrito
        time.sleep(0.5)
        renamed = self.grouper.process_new_images()
        if self.on_batch_done is not None:
            try:
                self.on_batch_done(renamed)
            except Exception:
                pass


def main():
    root = tk.Tk()
    root.title("Agrupador (watch folder)")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta a monitorear:").grid(row=0, column=0, sticky="w")
    folder_var = tk.StringVar()
    tk.Entry(frame, textvariable=folder_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta")
        if carpeta:
            folder_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_carpeta).grid(row=1, column=2, pady=(4, 8))

    tk.Label(frame, text="Prefijo:").grid(row=2, column=0, sticky="w")
    tk.Label(frame, text="Sufijo:").grid(row=2, column=1, sticky="w")
    prefijo_var = tk.StringVar()
    sufijo_var = tk.StringVar()
    entrada_prefijo = tk.Entry(frame, textvariable=prefijo_var, width=18)
    entrada_prefijo.grid(row=3, column=0, sticky="w", pady=(4, 8))
    entrada_sufijo = tk.Entry(frame, textvariable=sufijo_var, width=18)
    entrada_sufijo.grid(row=3, column=1, sticky="w", pady=(4, 8))

    status_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=status_var, justify="left", wraplength=460).grid(
        row=5, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    observer = None
    grouper = None
    running = False

    def set_status(text: str):
        status_var.set(text)

    def actualizar_estado_inicial():
        carpeta = folder_var.get().strip()
        if carpeta and os.path.isdir(carpeta):
            try:
                g = ImageGrouper(carpeta, prefijo_var.get(), sufijo_var.get())
                set_status(f"Listo. Siguiente grupo: {g.next_group_label}")
            except Exception:
                set_status("")
        else:
            set_status("")

    def on_batch_done(renamed: int):
        # Se llama desde el thread del watchdog; sincronizamos con Tk.
        def _ui():
            nonlocal grouper
            if grouper is None:
                return
            if renamed:
                set_status(f"Renombradas: {renamed}. Siguiente grupo: {grouper.next_group_label}")
            else:
                set_status(f"Sin cambios. Siguiente grupo: {grouper.next_group_label}")

        root.after(0, _ui)

    def procesar_ahora():
        nonlocal grouper

        carpeta = folder_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta no existe.")
            return

        prefijo = afijo(prefijo_var.get())
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefijo) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        try:
            if (
                grouper is None
                or grouper.folder_path != carpeta
                or grouper.prefijo != prefijo
                or grouper.sufijo != sufijo
            ):
                grouper = ImageGrouper(carpeta, prefijo, sufijo)
            renamed = grouper.process_new_images()
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}")
            return

        if renamed:
            messagebox.showinfo("Operacion completada", f"Renombradas: {renamed}\nSiguiente grupo: {grouper.next_group_label}")
        else:
            messagebox.showinfo("Sin cambios", f"No habia imagenes nuevas.\nSiguiente grupo: {grouper.next_group_label}")

        set_status(f"Listo. Siguiente grupo: {grouper.next_group_label}")

    def iniciar():
        nonlocal observer, grouper, running

        if Observer is None:
            messagebox.showerror(
                "watchdog no disponible",
                f"No se pudo importar watchdog.\n\n{_watchdog_import_error}",
            )
            return

        carpeta = folder_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta no existe.")
            return

        if running:
            return

        prefijo = afijo(prefijo_var.get())
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefijo) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        try:
            grouper = ImageGrouper(carpeta, prefijo, sufijo)
            # Procesar lo pendiente al iniciar
            grouper.process_new_images()

            event_handler = ImageHandler(grouper, on_batch_done=on_batch_done)
            observer = Observer()
            observer.schedule(event_handler, carpeta, recursive=False)
            observer.start()

            running = True
            btn_iniciar.config(state="disabled")
            btn_detener.config(state="normal")
            btn_procesar.config(state="disabled")
            entrada_prefijo.config(state="disabled")
            entrada_sufijo.config(state="disabled")
            set_status(f"Monitoreando... Siguiente grupo: {grouper.next_group_label}")

        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo iniciar el observador:\n\n{exc}")

    def detener():
        nonlocal observer, running

        if not running:
            return

        try:
            if observer is not None:
                observer.stop()

                # join puede bloquear; lo hacemos en background.
                def _join():
                    try:
                        observer.join(timeout=5)
                    except Exception:
                        pass

                threading.Thread(target=_join, daemon=True).start()

        finally:
            observer = None
            running = False
            btn_iniciar.config(state="normal")
            btn_detener.config(state="disabled")
            btn_procesar.config(state="normal")
            entrada_prefijo.config(state="normal")
            entrada_sufijo.config(state="normal")
            actualizar_estado_inicial()

    btn_procesar = tk.Button(frame, text="Procesar ahora", command=procesar_ahora)
    btn_procesar.grid(row=6, column=0, columnspan=3, sticky="we")

    btn_iniciar = tk.Button(frame, text="Iniciar monitoreo", command=iniciar)
    btn_iniciar.grid(row=7, column=0, columnspan=2, sticky="we", pady=(8, 0))

    btn_detener = tk.Button(frame, text="Detener", command=detener, state="disabled")
    btn_detener.grid(row=7, column=2, sticky="we", pady=(8, 0))

    def on_close():
        try:
            detener()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Actualizar status al cambiar carpeta manualmente
    def _on_folder_change(*_args):
        if not running:
            actualizar_estado_inicial()

    folder_var.trace_add("write", _on_folder_change)

    root.mainloop()


if __name__ == "__main__":
    main()
