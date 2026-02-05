import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

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
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.next_group_index = 0
        self.scan_existing_groups()

    def scan_existing_groups(self):
        """Escanea la carpeta para detectar grupos existentes."""
        max_index = -1
        for filename in os.listdir(self.folder_path):
            if "_" not in filename:
                continue

            group = filename.split("_", 1)[0]
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
        new_images = [
            f
            for f in os.listdir(self.folder_path)
            if f.lower().endswith(".png") and "_" not in f and os.path.splitext(f)[0].isdigit()
        ]

        if not new_images:
            return 0

        new_images.sort(key=lambda x: int(os.path.splitext(x)[0]))

        group_char = _index_to_group(self.next_group_index)
        renamed = 0

        for filename in new_images:
            new_name = f"{group_char}_{filename}"
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

    status_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=status_var, justify="left", wraplength=460).grid(
        row=2, column=0, columnspan=3, sticky="w", pady=(0, 8)
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
                g = ImageGrouper(carpeta)
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

        try:
            if grouper is None or grouper.folder_path != carpeta:
                grouper = ImageGrouper(carpeta)
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

        try:
            grouper = ImageGrouper(carpeta)
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
            actualizar_estado_inicial()

    btn_procesar = tk.Button(frame, text="Procesar ahora", command=procesar_ahora)
    btn_procesar.grid(row=3, column=0, columnspan=3, sticky="we")

    btn_iniciar = tk.Button(frame, text="Iniciar monitoreo", command=iniciar)
    btn_iniciar.grid(row=4, column=0, columnspan=2, sticky="we", pady=(8, 0))

    btn_detener = tk.Button(frame, text="Detener", command=detener, state="disabled")
    btn_detener.grid(row=4, column=2, sticky="we", pady=(8, 0))

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
