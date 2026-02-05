import threading
import time
import tkinter as tk
from tkinter import messagebox

try:
    import pyautogui
except Exception as exc:  # pragma: no cover
    pyautogui = None
    _pyautogui_import_error = str(exc)

try:
    import keyboard
except Exception as exc:  # pragma: no cover
    keyboard = None
    _keyboard_import_error = str(exc)


def main():
    root = tk.Tk()
    root.title("Autoclicker")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Estado
    running_event = threading.Event()
    stop_event = threading.Event()
    hotkey_id = None

    status_var = tk.StringVar(value="Estado: DESACTIVADO")

    # Configuracion
    tk.Label(frame, text="Delay (ms):").grid(row=0, column=0, sticky="w")
    delay_ms_var = tk.StringVar(value="10")
    tk.Entry(frame, textvariable=delay_ms_var, width=12).grid(row=1, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Boton:").grid(row=0, column=1, sticky="w")
    button_var = tk.StringVar(value="left")
    tk.OptionMenu(frame, button_var, "left", "right").grid(row=1, column=1, pady=(2, 8), sticky="w")

    tk.Label(frame, text="Hotkey (global):").grid(row=2, column=0, sticky="w")
    hotkey_var = tk.StringVar(value="F6")
    tk.Entry(frame, textvariable=hotkey_var, width=12).grid(row=3, column=0, pady=(4, 8), sticky="w")

    use_hotkey_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Habilitar hotkey", variable=use_hotkey_var).grid(row=3, column=1, sticky="w")

    tk.Label(frame, textvariable=status_var).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

    tk.Label(
        frame,
        text=(
            "Tips: el hotkey es global (funciona fuera de la ventana).\n"
            "En Windows, `keyboard` puede requerir permisos.\n"
            "Para detener rapido, desactiva con el boton o cierra la ventana."
        ),
        justify="left",
        wraplength=460,
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def parse_delay_seconds() -> float:
        try:
            ms = float(delay_ms_var.get().strip())
        except Exception:
            raise ValueError("Delay (ms) debe ser un numero.")

        if ms < 0:
            raise ValueError("Delay (ms) debe ser >= 0.")
        return ms / 1000.0

    def click_loop():
        # Nota: el delay se lee en cada ciclo para permitir ajustar en caliente.
        while not stop_event.is_set():
            if running_event.is_set():
                try:
                    delay_s = parse_delay_seconds()
                except Exception:
                    delay_s = 0.01

                if pyautogui is not None:
                    try:
                        pyautogui.click(button=button_var.get())
                    except Exception:
                        # Si pyautogui falla, evitamos matar el hilo.
                        pass

                if delay_s > 0:
                    time.sleep(delay_s)
                else:
                    # Evitar consumir 100% CPU si el usuario pone 0.
                    time.sleep(0.0005)
            else:
                time.sleep(0.01)

    thread = threading.Thread(target=click_loop, daemon=True)
    thread.start()

    def actualizar_status():
        status_var.set("Estado: ACTIVADO" if running_event.is_set() else "Estado: DESACTIVADO")

    def toggle_running():
        if running_event.is_set():
            running_event.clear()
        else:
            running_event.set()
        actualizar_status()

    def registrar_hotkey():
        nonlocal hotkey_id

        if keyboard is None:
            messagebox.showerror(
                "keyboard no disponible",
                f"No se pudo importar `keyboard`.\n\n{_keyboard_import_error}",
            )
            use_hotkey_var.set(False)
            return

        # Eliminar anterior si existia
        try:
            if hotkey_id is not None:
                keyboard.remove_hotkey(hotkey_id)
                hotkey_id = None
        except Exception:
            hotkey_id = None

        if not use_hotkey_var.get():
            return

        key = hotkey_var.get().strip()
        if not key:
            messagebox.showwarning("Falta hotkey", "Ingrese una hotkey (ej: F6).")
            use_hotkey_var.set(False)
            return

        try:
            hotkey_id = keyboard.add_hotkey(key, toggle_running)
        except Exception as exc:
            messagebox.showerror(
                "No se pudo registrar",
                f"No se pudo registrar la hotkey global.\n\n{exc}",
            )
            use_hotkey_var.set(False)
            hotkey_id = None
            return

    def on_use_hotkey_changed(*_args):
        registrar_hotkey()

    use_hotkey_var.trace_add("write", on_use_hotkey_changed)

    def on_hotkey_changed(*_args):
        # Si esta habilitado, re-registramos para aplicar el cambio.
        if use_hotkey_var.get():
            registrar_hotkey()

    hotkey_var.trace_add("write", on_hotkey_changed)

    def validar_deps_y_arrancar():
        if pyautogui is None:
            messagebox.showerror(
                "pyautogui no disponible",
                f"No se pudo importar `pyautogui`.\n\n{_pyautogui_import_error}",
            )
            return

        # Intentar leer delay para validar el dato
        try:
            parse_delay_seconds()
        except Exception as exc:
            messagebox.showerror("Dato invalido", str(exc))
            return

        toggle_running()

    btn_toggle = tk.Button(frame, text="Iniciar / Pausar", command=validar_deps_y_arrancar)
    btn_toggle.grid(row=6, column=0, columnspan=3, sticky="we")

    def on_close():
        nonlocal hotkey_id
        try:
            running_event.clear()
            stop_event.set()
            if keyboard is not None and hotkey_id is not None:
                try:
                    keyboard.remove_hotkey(hotkey_id)
                except Exception:
                    pass
                hotkey_id = None
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
