"""Punto de entrada de la interfaz unificada."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from aplicacion.catalogo import SECCIONES, Herramienta, herramientas_de


CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lanzar(herramienta: Herramienta) -> None:
    ruta = os.path.join(CARPETA_PROYECTO, herramienta.script)
    if not os.path.isfile(ruta):
        messagebox.showerror("Herramienta no disponible", f"No se encontro:\n{ruta}")
        return
    if herramienta.peligrosa and not messagebox.askyesno(
        "Operacion sobre archivos",
        "Esta herramienta puede renombrar, mover o eliminar archivos.\n\n"
        "La ventana que se abrira pedira sus propias confirmaciones. ¿Continuar?",
    ):
        return
    try:
        subprocess.Popen([sys.executable, ruta], cwd=CARPETA_PROYECTO)
    except OSError as exc:
        messagebox.showerror("No se pudo abrir", str(exc))


def main() -> None:
    root = tk.Tk()
    root.title("IA Images Manager")
    root.geometry("820x610")
    root.minsize(700, 480)

    encabezado = ttk.Frame(root, padding=(16, 14, 16, 8))
    encabezado.pack(fill="x")
    ttk.Label(encabezado, text="IA Images Manager", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        encabezado,
        text="Herramientas agrupadas por tarea. Una herramienta puede aparecer en varias secciones.",
    ).pack(anchor="w", pady=(3, 0))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=14, pady=(4, 14))

    for seccion in SECCIONES:
        pagina = ttk.Frame(notebook, padding=12)
        notebook.add(pagina, text=seccion)
        pagina.columnconfigure(0, weight=1)
        for fila, herramienta in enumerate(herramientas_de(seccion)):
            tarjeta = ttk.LabelFrame(pagina, text=herramienta.nombre, padding=10)
            tarjeta.grid(row=fila, column=0, sticky="ew", pady=(0, 8))
            tarjeta.columnconfigure(0, weight=1)
            ttk.Label(tarjeta, text=herramienta.descripcion, wraplength=590).grid(row=0, column=0, sticky="w")
            texto = "Abrir (modifica archivos)" if herramienta.peligrosa else "Abrir"
            ttk.Button(tarjeta, text=texto, command=lambda h=herramienta: lanzar(h)).grid(row=0, column=1, padx=(12, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
