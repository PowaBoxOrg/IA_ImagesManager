"""Agrupa archivos identicos por su contenido, no por su aspecto."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema
from motores.archivos import mover_sin_conflicto
from motores.duplicados import grupos_exactos


CARPETA_COPIAS = "0_DUPLICADOS_EXACTOS"


def archivos_de(carpeta: str, recursivo: bool) -> list[str]:
    carpeta = os.path.abspath(carpeta)
    encontrados = []
    if not recursivo:
        for nombre in os.listdir(carpeta):
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta):
                encontrados.append(ruta)
        return encontrados
    for actual, subdirs, nombres in os.walk(carpeta):
        subdirs[:] = [
            nombre
            for nombre in subdirs
            if nombre.casefold() != CARPETA_COPIAS.casefold()
        ]
        for nombre in nombres:
            ruta = os.path.join(actual, nombre)
            if os.path.isfile(ruta):
                encontrados.append(ruta)
    return encontrados


def main():
    root = tk.Tk()
    root.title("Duplicados exactos")
    root.geometry("760x520")

    carpeta_var = tk.StringVar()
    recursivo_var = tk.BooleanVar(value=True)
    estado_var = tk.StringVar(value="Elija una carpeta.")
    grupos: list[list[str]] = []

    def elegir():
        ruta = filedialog.askdirectory(title="Seleccionar carpeta")
        if ruta:
            carpeta_var.set(ruta)

    def mostrar(nuevos: list[list[str]], errores: list[tuple[str, str]]):
        nonlocal grupos
        grupos = nuevos
        lista.delete(0, "end")
        for grupo in nuevos:
            lista.insert("end", f"{len(grupo)} iguales: " + " | ".join(os.path.basename(ruta) for ruta in grupo[:6]))
        if not nuevos:
            estado_var.set("No hay archivos con el mismo contenido.")
        else:
            copias = sum(len(grupo) - 1 for grupo in nuevos)
            estado_var.set(f"Grupos: {len(nuevos)}. Copias que se pueden apartar: {copias}.")
        if errores:
            estado_var.set(estado_var.get() + f" No se pudieron leer: {len(errores)}.")
        boton_buscar.config(state="normal")
        boton_mover.config(state="normal" if nuevos else "disabled")

    def buscar():
        carpeta = carpeta_var.get().strip()
        if not os.path.isdir(carpeta):
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        boton_buscar.config(state="disabled")
        estado_var.set("Comparando contenido...")

        def trabajo():
            try:
                nuevos, errores = grupos_exactos(archivos_de(carpeta, recursivo_var.get()))
            except Exception as exc:
                root.after(0, lambda: messagebox.showerror("Error", str(exc)))
                root.after(0, lambda: boton_buscar.config(state="normal"))
                return
            root.after(0, lambda: mostrar(nuevos, errores))

        threading.Thread(target=trabajo, daemon=True).start()

    def mover():
        if not grupos:
            return
        copias = sum(len(grupo) - 1 for grupo in grupos)
        if not messagebox.askyesno(
            "Mover copias",
            f"Se conserva el primer archivo de cada grupo y se mueven {copias} copias a {CARPETA_COPIAS}.",
        ):
            return
        movidos = 0
        for grupo in grupos:
            destino = os.path.join(os.path.dirname(grupo[0]), CARPETA_COPIAS)
            for ruta in grupo[1:]:
                if os.path.isfile(ruta):
                    mover_sin_conflicto(ruta, destino)
                    movidos += 1
        messagebox.showinfo("Operacion completada", f"Copias apartadas: {movidos}.")
        buscar()

    marco = tk.Frame(root, padx=12, pady=12)
    marco.pack(fill="both", expand=True)
    tk.Label(marco, text="Carpeta:").pack(anchor="w")
    fila = tk.Frame(marco)
    fila.pack(fill="x", pady=(4, 8))
    tk.Entry(fila, textvariable=carpeta_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(fila, text="Examinar", command=elegir).pack(side="right")
    tk.Checkbutton(
        marco,
        text="Incluir subcarpetas",
        variable=recursivo_var,
        ayuda="Tambien compara los archivos que estan dentro de subcarpetas.",
    ).pack(anchor="w", pady=(0, 8))
    botones = tk.Frame(marco)
    botones.pack(fill="x", pady=(0, 8))
    boton_buscar = tk.Button(botones, text="Buscar duplicados", command=buscar)
    boton_buscar.pack(side="left", fill="x", expand=True)
    boton_mover = tk.Button(botones, text="Mover copias", command=mover, state="disabled")
    boton_mover.pack(side="left", fill="x", expand=True, padx=(8, 0))
    lista = tk.Listbox(marco)
    lista.pack(fill="both", expand=True, pady=(0, 8))
    tk.Label(marco, textvariable=estado_var, anchor="w", justify="left").pack(fill="x")

    root.mainloop()


if __name__ == "__main__":
    main()
