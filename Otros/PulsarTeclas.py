"""Repite una tecla o un texto con una espera, al estilo del autoclicker."""

import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aplicacion.tema

try:
    import keyboard
except Exception as exc:  # pragma: no cover
    keyboard = None
    _keyboard_import_error = str(exc)


def main():
    root = tk.Tk()
    root.title("Pulsar teclas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    running_event = threading.Event()
    stop_event = threading.Event()
    hotkey_id = None
    hechos = {"n": 0}

    modo_var = tk.StringVar(value="tecla")
    tecla_var = tk.StringVar(value="space")
    texto_var = tk.StringVar()
    delay_var = tk.StringVar(value="100")
    repeticiones_var = tk.StringVar(value="")
    hotkey_var = tk.StringVar(value="F8")
    use_hotkey_var = tk.BooleanVar(value=False)
    status_var = tk.StringVar(value="Estado: DESACTIVADO")

    def delay_segundos() -> float:
        ms = float(delay_var.get().strip())
        if ms < 0:
            raise ValueError("La espera no puede ser negativa.")
        return ms / 1000.0

    def enviar():
        if keyboard is None:
            return
        if modo_var.get() == "texto":
            texto = texto_var.get()
            if texto:
                keyboard.write(texto)
            return
        tecla = tecla_var.get().strip()
        if tecla:
            keyboard.send(tecla)

    def bucle():
        while not stop_event.is_set():
            if not running_event.is_set():
                time.sleep(0.01)
                continue
            try:
                espera = delay_segundos()
                enviar()
                hechos["n"] += 1
                limite = repeticiones_var.get().strip()
                if limite and hechos["n"] >= int(limite):
                    running_event.clear()
                    root.after(0, actualizar_status)
            except Exception:
                espera = 0.1
            time.sleep(espera if espera > 0 else 0.01)

    threading.Thread(target=bucle, daemon=True).start()

    def actualizar_status():
        status_var.set("Estado: ACTIVADO" if running_event.is_set() else "Estado: DESACTIVADO")

    def alternar():
        if running_event.is_set():
            running_event.clear()
        else:
            hechos["n"] = 0
            running_event.set()
        actualizar_status()

    def registrar_hotkey():
        nonlocal hotkey_id
        if keyboard is None:
            messagebox.showerror("keyboard no disponible", f"No se pudo importar keyboard.\n\n{_keyboard_import_error}")
            use_hotkey_var.set(False)
            return
        try:
            if hotkey_id is not None:
                keyboard.remove_hotkey(hotkey_id)
                hotkey_id = None
        except Exception:
            hotkey_id = None
        if not use_hotkey_var.get():
            return
        tecla = hotkey_var.get().strip()
        if not tecla:
            use_hotkey_var.set(False)
            return
        try:
            hotkey_id = keyboard.add_hotkey(tecla, alternar)
        except Exception as exc:
            messagebox.showerror("No se pudo registrar", str(exc))
            use_hotkey_var.set(False)

    def iniciar():
        if keyboard is None:
            messagebox.showerror("keyboard no disponible", f"No se pudo importar keyboard.\n\n{_keyboard_import_error}")
            return
        try:
            delay_segundos()
            if modo_var.get() == "tecla" and not tecla_var.get().strip():
                raise ValueError("Escriba la tecla, por ejemplo space o e.")
            if modo_var.get() == "texto" and not texto_var.get():
                raise ValueError("Escriba el texto que se va a repetir.")
            limite = repeticiones_var.get().strip()
            if limite and int(limite) <= 0:
                raise ValueError("Las repeticiones deben ser un entero mayor que 0, o vacio.")
        except Exception as exc:
            messagebox.showerror("Dato invalido", str(exc))
            return
        alternar()

    tk.Label(frame, text="Accion:").grid(row=0, column=0, sticky="w")
    acciones = tk.Frame(frame)
    acciones.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 8))
    tk.Radiobutton(
        acciones,
        text="Tecla",
        variable=modo_var,
        value="tecla",
        ayuda="Repite una tecla. Por ejemplo space, e o f5.",
    ).pack(side="left")
    tk.Radiobutton(
        acciones,
        text="Texto",
        variable=modo_var,
        value="texto",
        ayuda="Escribe el mismo texto cada vez que pasa la espera.",
    ).pack(side="left", padx=(12, 0))

    tk.Label(frame, text="Tecla:").grid(row=2, column=0, sticky="w")
    tk.Entry(frame, textvariable=tecla_var, width=18).grid(row=3, column=0, sticky="w", pady=(4, 8))
    tk.Label(frame, text="Texto:").grid(row=2, column=1, sticky="w")
    tk.Entry(frame, textvariable=texto_var, width=28).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(4, 8))

    tk.Label(frame, text="Espera (ms):").grid(row=4, column=0, sticky="w")
    tk.Entry(frame, textvariable=delay_var, width=12).grid(row=5, column=0, sticky="w", pady=(4, 8))
    tk.Label(frame, text="Repeticiones (vacio = sin limite):").grid(row=4, column=1, sticky="w")
    tk.Entry(frame, textvariable=repeticiones_var, width=12).grid(row=5, column=1, sticky="w", padx=(8, 0), pady=(4, 8))

    tk.Label(frame, text="Hotkey (global):").grid(row=6, column=0, sticky="w")
    tk.Entry(frame, textvariable=hotkey_var, width=12).grid(row=7, column=0, sticky="w", pady=(4, 8))
    casilla = tk.Checkbutton(frame, text="Habilitar hotkey", variable=use_hotkey_var)
    casilla.grid(row=7, column=1, sticky="w")
    use_hotkey_var.trace_add("write", lambda *_args: registrar_hotkey())

    tk.Label(frame, textvariable=status_var).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 8))
    tk.Button(frame, text="Iniciar / Pausar", command=iniciar).grid(row=9, column=0, columnspan=2, sticky="we")

    def cerrar():
        nonlocal hotkey_id
        running_event.clear()
        stop_event.set()
        if keyboard is not None and hotkey_id is not None:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except Exception:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cerrar)
    root.mainloop()


if __name__ == "__main__":
    main()
