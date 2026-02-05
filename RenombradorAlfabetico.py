import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox


def generar_nombre_alfabetico(indice: int) -> str:
    """Genera un nombre alfabetico estilo columnas de Excel (a, b, ..., z, aa, ab, ...)."""
    nombre = ""
    while indice >= 0:
        nombre = chr(indice % 26 + 97) + nombre
        indice = indice // 26 - 1
    return nombre


def renombrar_por_alfabeto(directorio: str):
    """Renombra archivos alfabeticamente de forma inteligente.

    Solo renombra si:
    1) Hay archivos que no siguen el patron alfabetico (ej: 'a.jpg', 'b.png').
    2) Hay un hueco en la secuencia alfabetica (ej: existe 'a.jpg' y 'c.jpg', pero no 'b.jpg').

    Devuelve: (renamed_count, skipped)
    """
    # 1) Clasificar archivos
    archivos_alfabeticos = []
    archivos_no_alfabeticos = []

    patron_alfabetico = re.compile(r"^[a-z]+(\..+)$", re.IGNORECASE)

    for f in os.listdir(directorio):
        ruta = os.path.join(directorio, f)
        if os.path.isfile(ruta):
            if patron_alfabetico.match(f):
                archivos_alfabeticos.append(f)
            else:
                archivos_no_alfabeticos.append(f)

    # 2) Comprobar si hay huecos en la secuencia
    archivos_alfabeticos.sort(key=lambda f: (len(os.path.splitext(f)[0]), os.path.splitext(f)[0].lower()))

    hay_hueco = False
    for i, nombre_archivo in enumerate(archivos_alfabeticos):
        nombre_esperado_base = generar_nombre_alfabetico(i)
        nombre_actual_base = os.path.splitext(nombre_archivo)[0].lower()
        if nombre_actual_base != nombre_esperado_base:
            hay_hueco = True
            break

    # 3) Decidir si renombrar
    if not archivos_no_alfabeticos and not hay_hueco:
        print("Todos los archivos ya estan correctamente nombrados y en secuencia. No se necesita hacer nada.")
        return 0, True

    if archivos_no_alfabeticos:
        print(
            f"Se encontraron {len(archivos_no_alfabeticos)} archivos que no siguen el patron alfabetico. "
            "Se procedera a renombrar todo."
        )
    if hay_hueco:
        print("Se detecto un hueco en la secuencia. Se procedera a renombrar todo.")

    # 4) Renombrado completo: ordenar por antiguedad (mtime) y renombrar con temporales
    todos_los_archivos = [f for f in os.listdir(directorio) if os.path.isfile(os.path.join(directorio, f))]
    todos_los_archivos.sort(key=lambda f: os.path.getmtime(os.path.join(directorio, f)))

    # Renombrar a nombres temporales para evitar conflictos
    for i, nombre_original in enumerate(todos_los_archivos):
        ruta_original = os.path.join(directorio, nombre_original)
        extension = os.path.splitext(nombre_original)[1]
        nombre_temporal = f"__temp_{i}{extension}"
        os.rename(ruta_original, os.path.join(directorio, nombre_temporal))

    # Renombrar de temporal a final
    for i in range(len(todos_los_archivos)):
        extension = os.path.splitext(todos_los_archivos[i])[1]
        ruta_temporal = os.path.join(directorio, f"__temp_{i}{extension}")
        nuevo_nombre_final = generar_nombre_alfabetico(i) + extension
        ruta_final = os.path.join(directorio, nuevo_nombre_final)
        os.rename(ruta_temporal, ruta_final)
        print(f'Renombrado a: "{nuevo_nombre_final}"')

    return len(todos_los_archivos), False


def main():
    root = tk.Tk()
    root.title("Renombrador alfabetico")
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

        try:
            renamed_count, skipped = renombrar_por_alfabeto(carpeta)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error: {exc}")
            return

        if skipped:
            messagebox.showinfo("Sin cambios", "Los archivos ya estaban en orden alfabetico.")
            return

        messagebox.showinfo("Operacion completada", f"Renombrado finalizado. Archivos: {renamed_count}")

    boton_examinar = tk.Button(frame, text="Examinar", command=seleccionar_carpeta)
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    boton_ejecutar = tk.Button(frame, text="Renombrar", command=ejecutar_renombrado)
    boton_ejecutar.grid(row=2, column=0, columnspan=3, sticky="we")

    root.mainloop()


if __name__ == "__main__":
    main()
