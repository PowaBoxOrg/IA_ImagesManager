"""Punto de entrada de la interfaz unificada."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import aplicacion.tema
from aplicacion.catalogo import SECCIONES, Herramienta, herramientas_de


CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lanzar(herramienta: Herramienta, argumentos: tuple[str, ...] = ()) -> None:
    ruta = os.path.join(CARPETA_PROYECTO, herramienta.script)
    if not os.path.isfile(ruta):
        messagebox.showerror("Herramienta no disponible", f"No se encontro:\n{ruta}")
        return
    try:
        subprocess.Popen([sys.executable, ruta, *argumentos], cwd=CARPETA_PROYECTO)
    except OSError as exc:
        messagebox.showerror("No se pudo abrir", str(exc))


def _agregar_herramienta(pagina: ttk.Frame, fila: int, herramienta: Herramienta) -> None:
    tarjeta = ttk.LabelFrame(pagina, text=herramienta.nombre, padding=(14, 12))
    tarjeta.grid(row=fila, column=0, sticky="ew", pady=(0, 10))
    tarjeta.columnconfigure(0, weight=1)
    ttk.Label(tarjeta, text=herramienta.descripcion, wraplength=640, justify="left").grid(
        row=0, column=0, sticky="ew"
    )
    texto = "Abrir (modifica archivos)" if herramienta.peligrosa else "Abrir"
    estilo = "Caution.TButton" if herramienta.peligrosa else "Accent.TButton"
    ttk.Button(
        tarjeta,
        text=texto,
        style=estilo,
        ayuda=f"{herramienta.descripcion} Abre la herramienta en su ventana.",
        command=lambda h=herramienta: lanzar(h),
    ).grid(row=0, column=1, padx=(16, 0), sticky="e")


def _pagina_desplazable(notebook: ttk.Notebook) -> tuple[ttk.Frame, ttk.Frame]:
    contenedor = ttk.Frame(notebook)
    canvas = tk.Canvas(
        contenedor,
        highlightthickness=0,
        borderwidth=0,
        background=aplicacion.tema.FONDO,
    )
    barra = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
    pagina = ttk.Frame(canvas, padding=12)
    ventana = canvas.create_window((0, 0), window=pagina, anchor="nw")

    def ajustar_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def ajustar_ancho(event):
        canvas.itemconfigure(ventana, width=event.width)

    pagina.bind("<Configure>", ajustar_region)
    canvas.bind("<Configure>", ajustar_ancho)
    canvas.configure(yscrollcommand=barra.set)
    canvas.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    contenedor._canvas_scroll = canvas
    return contenedor, pagina


def main() -> None:
    root = tk.Tk()
    root.title("IA Images Manager")
    root.geometry("880x680")
    root.minsize(720, 520)

    encabezado = ttk.Frame(root, padding=(20, 18, 20, 10))
    encabezado.pack(fill="x")
    ttk.Label(encabezado, text="IA Images Manager", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        encabezado,
        text="Tres grupos. Cada herramienta aparece una sola vez.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(4, 0))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=16, pady=(6, 16))

    for seccion in SECCIONES:
        contenedor, pagina = _pagina_desplazable(notebook)
        notebook.add(contenedor, text=seccion)
        pagina.columnconfigure(0, weight=1)
        for fila, herramienta in enumerate(herramientas_de(seccion)):
            _agregar_herramienta(pagina, fila, herramienta)

    def al_rueda(event):
        if not event.delta:
            return
        try:
            actual = notebook.nametowidget(notebook.select())
        except tk.TclError:
            return
        canvas = getattr(actual, "_canvas_scroll", None)
        if canvas is None:
            return
        x = actual.winfo_rootx()
        y = actual.winfo_rooty()
        if not (x <= event.x_root <= x + actual.winfo_width() and y <= event.y_root <= y + actual.winfo_height()):
            return
        canvas.yview_scroll(int(-event.delta / 120), "units")

    root.bind_all("<MouseWheel>", al_rueda)
    root.mainloop()


if __name__ == "__main__":
    main()
