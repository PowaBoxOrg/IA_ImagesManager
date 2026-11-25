"""Mueve los archivos de una carpeta a subcarpetas segun su extension."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema
from motores.archivos import mover_sin_conflicto
from motores.clasificar import CATEGORIAS, categoria_de


def archivos_a_ordenar(carpeta: str, recursivo: bool) -> list[str]:
    carpeta = os.path.abspath(carpeta)
    reservadas = {nombre.casefold() for nombre in CATEGORIAS}
    if not recursivo:
        return [
            os.path.join(carpeta, nombre)
            for nombre in os.listdir(carpeta)
            if os.path.isfile(os.path.join(carpeta, nombre))
        ]
    encontrados = []
    for actual, subdirs, nombres in os.walk(carpeta):
        subdirs[:] = [nombre for nombre in subdirs if nombre.casefold() not in reservadas]
        if os.path.basename(actual).casefold() in reservadas and actual != carpeta:
            continue
        for nombre in nombres:
            ruta = os.path.join(actual, nombre)
            if os.path.isfile(ruta):
                encontrados.append(ruta)
    return encontrados


def ordenar(carpeta: str, recursivo: bool) -> dict[str, int]:
    conteo = {categoria: 0 for categoria in CATEGORIAS}
    for ruta in archivos_a_ordenar(carpeta, recursivo):
        categoria = categoria_de(os.path.basename(ruta))
        destino = os.path.join(os.path.dirname(ruta), categoria)
        if os.path.normcase(os.path.dirname(ruta)) == os.path.normcase(destino):
            continue
        mover_sin_conflicto(ruta, destino)
        conteo[categoria] += 1
    return conteo


def main():
    root = tk.Tk()
    root.title("Ordenar por tipo")
    root.resizable(False, False)

    carpeta_var = tk.StringVar()
    recursivo_var = tk.BooleanVar(value=False)
    estado_var = tk.StringVar(value="Las imagenes, videos y audios pasan a su carpeta. El resto va a Otros.")

    def elegir():
        ruta = filedialog.askdirectory(title="Seleccionar carpeta")
        if ruta:
            carpeta_var.set(ruta)

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not os.path.isdir(carpeta):
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not messagebox.askyesno(
            "Ordenar archivos",
            "Se mueven los archivos a Imagenes, Video, Audio u Otros, dentro de la misma carpeta.",
        ):
            return
        try:
            conteo = ordenar(carpeta, recursivo_var.get())
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        total = sum(conteo.values())
        detalle = "\n".join(f"{categoria}: {cantidad}" for categoria, cantidad in conteo.items())
        estado_var.set(f"Archivos movidos: {total}.")
        messagebox.showinfo("Operacion completada", f"Archivos movidos: {total}.\n\n{detalle}")

    marco = tk.Frame(root, padx=12, pady=12)
    marco.pack()
    tk.Label(marco, text="Carpeta:").grid(row=0, column=0, sticky="w")
    tk.Entry(marco, textvariable=carpeta_var, width=52).grid(row=1, column=0, padx=(0, 8), pady=(4, 8), sticky="we")
    tk.Button(marco, text="Examinar", command=elegir).grid(row=1, column=1, pady=(4, 8))
    tk.Checkbutton(
        marco,
        text="Incluir subcarpetas",
        variable=recursivo_var,
        ayuda="Tambien ordena los archivos de las carpetas internas. No vuelve a entrar en Imagenes, Video, Audio ni Otros.",
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))
    tk.Button(marco, text="Ordenar", command=ejecutar).grid(row=3, column=0, columnspan=2, sticky="we")
    tk.Label(marco, textvariable=estado_var, wraplength=460, justify="left").grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(8, 0)
    )

    root.mainloop()


if __name__ == "__main__":
    main()
