import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aplicacion.tema

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


def leer_secuencia(texto: str) -> list[tuple[int, int]]:
    """Lee una coordenada por linea, como '120, 340' o '120 340'."""
    puntos = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if "," in linea:
            partes = [parte.strip() for parte in linea.split(",") if parte.strip()]
        else:
            partes = linea.split()
        if len(partes) != 2:
            raise ValueError(f"Coordenada invalida: {linea}")
        puntos.append((int(float(partes[0])), int(float(partes[1]))))
    return puntos


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

    destino_var = tk.StringVar(value="cursor")
    x_var = tk.StringVar(value="0")
    y_var = tk.StringVar(value="0")
    repeticiones_var = tk.StringVar(value="")

    tk.Label(frame, text="Destino:").grid(row=4, column=0, sticky="w")
    destinos = tk.Frame(frame)
    destinos.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 4))
    tk.Radiobutton(
        destinos,
        text="Cursor",
        variable=destino_var,
        value="cursor",
        command=lambda: mostrar_destino(),
        ayuda="Clic donde este el puntero en ese momento.",
    ).pack(side="left")
    tk.Radiobutton(
        destinos,
        text="Punto fijo",
        variable=destino_var,
        value="punto",
        command=lambda: mostrar_destino(),
        ayuda="Siempre el mismo pixel, aunque el puntero se mueva.",
    ).pack(side="left", padx=(12, 0))
    tk.Radiobutton(
        destinos,
        text="Secuencia",
        variable=destino_var,
        value="secuencia",
        command=lambda: mostrar_destino(),
        ayuda="Recorre los puntos de la lista, uno por clic, y vuelve a empezar.",
    ).pack(side="left", padx=(12, 0))

    fila_punto = tk.Frame(frame)
    tk.Label(fila_punto, text="X:").pack(side="left")
    tk.Entry(fila_punto, textvariable=x_var, width=8).pack(side="left", padx=(6, 12))
    tk.Label(fila_punto, text="Y:").pack(side="left")
    tk.Entry(fila_punto, textvariable=y_var, width=8).pack(side="left", padx=(6, 0))

    fila_secuencia = tk.Frame(frame)
    tk.Label(fila_secuencia, text="Puntos (x, y), uno por linea:").pack(anchor="w")
    secuencia_texto = tk.Text(fila_secuencia, width=36, height=5)
    secuencia_texto.pack(fill="x", pady=(4, 0))

    tk.Label(frame, text="Repeticiones (vacio = sin limite):").grid(row=8, column=0, columnspan=2, sticky="w")
    tk.Entry(frame, textvariable=repeticiones_var, width=12).grid(row=9, column=0, sticky="w", pady=(4, 8))

    tk.Label(frame, textvariable=status_var).grid(row=10, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def parse_delay_seconds() -> float:
        try:
            ms = float(delay_ms_var.get().strip())
        except Exception:
            raise ValueError("Delay (ms) debe ser un numero.")

        if ms < 0:
            raise ValueError("Delay (ms) debe ser >= 0.")
        return ms / 1000.0

    hechos = {"n": 0}

    def punto_del_clic():
        destino = destino_var.get()
        if destino == "punto":
            return int(float(x_var.get().strip())), int(float(y_var.get().strip()))
        if destino == "secuencia":
            puntos = leer_secuencia(secuencia_texto.get("1.0", "end"))
            if not puntos:
                raise ValueError("La secuencia no tiene puntos.")
            punto = puntos[hechos["n"] % len(puntos)]
            return punto
        return None

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
                        punto = punto_del_clic()
                        if punto is None:
                            pyautogui.click(button=button_var.get())
                        else:
                            pyautogui.click(punto[0], punto[1], button=button_var.get())
                        hechos["n"] += 1
                        limite = repeticiones_var.get().strip()
                        if limite and hechos["n"] >= int(limite):
                            running_event.clear()
                            root.after(0, actualizar_status)
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

    def mostrar_destino():
        if fila_punto.winfo_manager() == "grid":
            fila_punto.grid_remove()
        if fila_secuencia.winfo_manager() == "grid":
            fila_secuencia.grid_remove()
        if destino_var.get() == "punto":
            fila_punto.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 8))
        elif destino_var.get() == "secuencia":
            fila_secuencia.grid(row=7, column=0, columnspan=3, sticky="we", pady=(0, 8))

    def toggle_running():
        if running_event.is_set():
            running_event.clear()
        else:
            hechos["n"] = 0
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
            if destino_var.get() == "punto":
                int(float(x_var.get().strip()))
                int(float(y_var.get().strip()))
            elif destino_var.get() == "secuencia" and not leer_secuencia(secuencia_texto.get("1.0", "end")):
                raise ValueError("Escriba al menos un punto, por ejemplo 120, 340.")
            limite = repeticiones_var.get().strip()
            if limite and int(limite) <= 0:
                raise ValueError("Las repeticiones deben ser un entero mayor que 0, o vacio.")
        except Exception as exc:
            messagebox.showerror("Dato invalido", str(exc))
            return

        toggle_running()

    btn_toggle = tk.Button(frame, text="Iniciar / Pausar", command=validar_deps_y_arrancar)
    btn_toggle.grid(row=11, column=0, columnspan=3, sticky="we")
    mostrar_destino()

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
