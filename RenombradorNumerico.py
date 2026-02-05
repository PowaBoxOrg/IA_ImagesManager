import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime


def generar_nombre_alfabetico(indice):
    """Genera un nombre alfabetico estilo columnas de Excel (a, b, ..., z, aa, ab, ...)"""
    nombre = ""
    while indice >= 0:
        nombre = chr(indice % 26 + 97) + nombre
        indice = indice // 26 - 1
    return nombre


def renombrar_por_alfabeto(directorio):
    # Obtener lista de archivos
    archivos = [f for f in os.listdir(directorio) if os.path.isfile(os.path.join(directorio, f))]

    # Renombrar archivos con nombres alfabeticos
    for indice, nombre_original in enumerate(archivos):
        ruta_original = os.path.join(directorio, nombre_original)
        extension = os.path.splitext(nombre_original)[1]  # Conservar extension (.jpg, .png, etc.)
        nuevo_nombre = generar_nombre_alfabetico(indice) + extension
        nueva_ruta = os.path.join(directorio, nuevo_nombre)

        # Evitar sobrescribir archivos existentes
        while os.path.exists(nueva_ruta):
            indice += 1
            nuevo_nombre = generar_nombre_alfabetico(indice) + extension
            nueva_ruta = os.path.join(directorio, nuevo_nombre)

        os.rename(ruta_original, nueva_ruta)


def renombrar_por_fecha(directorio, prefijo, inicio=1):
    # Obtener lista de archivos con sus fechas de creacion
    archivos = []
    for nombre_archivo in os.listdir(directorio):
        ruta_archivo = os.path.join(directorio, nombre_archivo)
        if os.path.isfile(ruta_archivo):  # Solo archivos, no carpetas
            fecha_creacion = os.path.getctime(ruta_archivo)
            archivos.append((fecha_creacion, nombre_archivo, ruta_archivo))

    # Ordenar archivos por fecha de creacion (mas antiguo primero)
    archivos.sort()

    # Renombrar archivos numericamente
    indice = inicio
    for fecha, nombre_original, ruta_original in archivos:
        extension = os.path.splitext(nombre_original)[1]  # Conservar extension (.jpg, .png, etc.)
        nuevo_nombre = f"{prefijo}{indice}{extension}"
        nueva_ruta = os.path.join(directorio, nuevo_nombre)

        # Evitar sobrescribir archivos existentes
        while os.path.exists(nueva_ruta):
            indice += 1
            nuevo_nombre = f"{prefijo}{indice}{extension}"
            nueva_ruta = os.path.join(directorio, nuevo_nombre)

        os.rename(ruta_original, nueva_ruta)
        indice += 1


def main():
    root = tk.Tk()
    root.title("Renombrador numerico")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta:").grid(row=0, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    entrada = tk.Entry(frame, textvariable=carpeta_var, width=50)
    entrada.grid(row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we")

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory()
        if carpeta:
            carpeta_var.set(carpeta)

    def ejecutar_renombrado():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La ruta no existe.")
            return

        prefijo = ""
        inicio = 1
        try:
            renombrar_por_alfabeto(carpeta)
            renombrar_por_fecha(carpeta, prefijo, inicio)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        messagebox.showinfo("Operacion completada", "Renombrado finalizado.")

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    boton_ejecutar = tk.Button(frame, text="Renombrar", command=ejecutar_renombrado)
    boton_ejecutar.grid(row=2, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
