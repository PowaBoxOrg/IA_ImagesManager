import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageTk
except Exception as exc:  # pragma: no cover
    Image = None
    ImageTk = None
    _pil_import_error = str(exc)


EXTENSIONES_VALIDAS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif")


def obtener_valor_numerico(nombre: str) -> int:
    """Extrae el valor numerico del nombre del archivo (primer numero encontrado)."""
    partes = re.findall(r"\d+", nombre)
    return int(partes[0]) if partes else 0


def listar_imagenes(carpeta_a: str):
    imagenes = [
        os.path.join(carpeta_a, f)
        for f in os.listdir(carpeta_a)
        if os.path.isfile(os.path.join(carpeta_a, f)) and f.lower().endswith(EXTENSIONES_VALIDAS)
    ]
    imagenes.sort(key=lambda x: obtener_valor_numerico(os.path.basename(x)))
    return imagenes


def copiar_sin_conflicto(ruta_src: str, carpeta_destino: str) -> str:
    """Copia `ruta_src` a `carpeta_destino` evitando sobrescribir (agrega _1, _2, ...)."""
    nombre_archivo = os.path.basename(ruta_src)
    destino = os.path.join(carpeta_destino, nombre_archivo)

    contador = 1
    while os.path.exists(destino):
        nombre, ext = os.path.splitext(nombre_archivo)
        destino = os.path.join(carpeta_destino, f"{nombre}_{contador}{ext}")
        contador += 1

    shutil.copy(ruta_src, destino)
    return destino


def abrir_visualizador(carpeta_a: str, carpeta_b: str, carpeta_c: str, umbral_alto: int):
    if Image is None or ImageTk is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    imagenes = listar_imagenes(carpeta_a)
    if not imagenes:
        raise RuntimeError("No se encontraron imagenes en la carpeta de origen.")

    indice_actual = 0

    ventana = tk.Toplevel()
    ventana.title("Copiador/Visualizador de imagenes")

    screen_height = ventana.winfo_screenheight()
    ventana.geometry(f"800x{screen_height}")
    ventana.configure(bg="#2e2e2e")

    frame_imagen = tk.Frame(ventana, bg="#2e2e2e")
    frame_imagen.pack(expand=True, fill=tk.BOTH)

    frame_barra = tk.Frame(ventana, bg="#444444")
    frame_barra.pack(fill=tk.X, side=tk.BOTTOM)

    lbl_resolucion = tk.Label(
        frame_barra,
        text="Resolucion: ",
        font=("Arial", 12),
        bg="#444444",
        fg="#ffffff",
    )
    lbl_resolucion.pack(side=tk.RIGHT, padx=10)

    lbl_contador = tk.Label(
        frame_barra,
        text="",
        font=("Arial", 12),
        bg="#444444",
        fg="#ffffff",
    )
    lbl_contador.pack(side=tk.RIGHT, padx=10)

    tk.Label(
        frame_barra,
        text="Ir a imagen:",
        font=("Arial", 12),
        bg="#444444",
        fg="#ffffff",
    ).pack(side=tk.LEFT, padx=10)

    entry_salto = tk.Entry(frame_barra, font=("Arial", 12), width=6)
    entry_salto.pack(side=tk.LEFT, padx=5)

    def mostrar_imagen(indice: int):
        for widget in frame_imagen.winfo_children():
            widget.destroy()

        ruta_imagen = imagenes[indice]
        try:
            img = Image.open(ruta_imagen)
            ancho_original, alto_original = img.size

            ancho_frame = frame_imagen.winfo_width()
            alto_frame = frame_imagen.winfo_height()
            if ancho_frame == 0 or alto_frame == 0:
                ancho_frame, alto_frame = 800, screen_height - 100

            img.thumbnail((ancho_frame, alto_frame))
            img_tk = ImageTk.PhotoImage(img)

            panel = tk.Label(frame_imagen, image=img_tk, bg="#2e2e2e")
            panel.image = img_tk
            panel.pack(expand=True)

            lbl_resolucion.config(text=f"Resolucion: {ancho_original}x{alto_original}")
            lbl_contador.config(text=f"Imagen {indice + 1} de {len(imagenes)}")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo cargar la imagen: {exc}")

    def siguiente_imagen(_event=None):
        nonlocal indice_actual
        if indice_actual < len(imagenes) - 1:
            indice_actual += 1
            mostrar_imagen(indice_actual)

    def anterior_imagen(_event=None):
        nonlocal indice_actual
        if indice_actual > 0:
            indice_actual -= 1
            mostrar_imagen(indice_actual)

    def copiar_imagen():
        ruta_imagen = imagenes[indice_actual]
        try:
            with Image.open(ruta_imagen) as img:
                _, alto = img.size

            destino_dir = carpeta_c if alto < umbral_alto else carpeta_b
            os.makedirs(destino_dir, exist_ok=True)

            destino = copiar_sin_conflicto(ruta_imagen, destino_dir)
            print(f"Copiado: {ruta_imagen} -> {destino}")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo copiar la imagen: {exc}")

    def saltar_a_imagen(_event=None):
        nonlocal indice_actual
        try:
            indice = int(entry_salto.get().strip()) - 1
            if 0 <= indice < len(imagenes):
                indice_actual = indice
                mostrar_imagen(indice_actual)
                frame_imagen.focus_set()
            else:
                messagebox.showwarning("Indice invalido", f"Ingrese un numero entre 1 y {len(imagenes)}.")
        except ValueError:
            messagebox.showerror("Error", "Por favor, ingrese un numero valido.")

    btn_anterior = tk.Button(
        frame_barra,
        text="Anterior",
        command=anterior_imagen,
        bg="#555555",
        fg="#ffffff",
    )
    btn_anterior.pack(side=tk.LEFT, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_barra,
        text="Siguiente",
        command=siguiente_imagen,
        bg="#555555",
        fg="#ffffff",
    )
    btn_siguiente.pack(side=tk.LEFT, padx=10, pady=10)

    btn_copiar = tk.Button(
        frame_barra,
        text="Copiar a carpeta",
        command=copiar_imagen,
        bg="#555555",
        fg="#ffffff",
    )
    btn_copiar.pack(side=tk.LEFT, padx=10, pady=10)

    btn_salto = tk.Button(
        frame_barra,
        text="Ir",
        command=saltar_a_imagen,
        bg="#555555",
        fg="#ffffff",
    )
    btn_salto.pack(side=tk.LEFT, padx=5)

    entry_salto.bind("<Return>", saltar_a_imagen)

    ventana.bind("<Right>", siguiente_imagen)
    ventana.bind("<Left>", anterior_imagen)
    ventana.bind("d", siguiente_imagen)
    ventana.bind("a", anterior_imagen)
    ventana.bind("+", lambda _event: copiar_imagen())

    mostrar_imagen(indice_actual)


def main():
    root = tk.Tk()
    root.title("Copiador de imagenes")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Origen
    tk.Label(frame, text="Carpeta origen:").grid(row=0, column=0, sticky="w")
    origen_var = tk.StringVar()
    tk.Entry(frame, textvariable=origen_var, width=50).grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_origen():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta origen")
        if carpeta:
            origen_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=sel_origen).grid(row=1, column=2, pady=(4, 8))

    # Destino >= umbral
    tk.Label(frame, text="Destino (>= umbral):").grid(row=2, column=0, sticky="w")
    dest_b_var = tk.StringVar()
    tk.Entry(frame, textvariable=dest_b_var, width=50).grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_dest_b():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta destino (>= umbral)")
        if carpeta:
            dest_b_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=sel_dest_b).grid(row=3, column=2, pady=(4, 8))

    # Destino < umbral
    tk.Label(frame, text="Destino (< umbral):").grid(row=4, column=0, sticky="w")
    dest_c_var = tk.StringVar()
    tk.Entry(frame, textvariable=dest_c_var, width=50).grid(
        row=5, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_dest_c():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta destino (< umbral)")
        if carpeta:
            dest_c_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=sel_dest_c).grid(row=5, column=2, pady=(4, 8))

    # Umbral
    tk.Label(frame, text="Umbral alto (px):").grid(row=6, column=0, sticky="w")
    umbral_var = tk.StringVar(value="480")
    tk.Entry(frame, textvariable=umbral_var, width=12).grid(row=7, column=0, pady=(4, 8), sticky="w")

    tk.Label(
        frame,
        text='Regla: si la altura de la imagen es < umbral va a "Destino (< umbral)", si no va a "Destino (>= umbral)".\nTeclas: A/Izq anterior, D/Der siguiente, + copiar.',
        justify="left",
        wraplength=460,
    ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def ejecutar():
        if Image is None or ImageTk is None:
            messagebox.showerror("Pillow no disponible", f"No se pudo importar Pillow (PIL).\n\n{_pil_import_error}")
            return

        origen = origen_var.get().strip()
        dest_b = dest_b_var.get().strip()
        dest_c = dest_c_var.get().strip()

        if not origen:
            messagebox.showwarning("Falta origen", "Seleccione una carpeta origen.")
            return
        if not os.path.isdir(origen):
            messagebox.showerror("Ruta invalida", "La carpeta origen no existe.")
            return

        if not dest_b:
            messagebox.showwarning("Falta destino", "Seleccione la carpeta destino (>= umbral).")
            return
        if not dest_c:
            messagebox.showwarning("Falta destino", "Seleccione la carpeta destino (< umbral).")
            return

        try:
            umbral = int(umbral_var.get().strip())
            if umbral <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "El umbral debe ser un entero mayor que 0.")
            return

        # Creamos destinos (si no existen)
        try:
            os.makedirs(dest_b, exist_ok=True)
            os.makedirs(dest_c, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudieron crear/verificar carpetas destino:\n\n{exc}")
            return

        try:
            abrir_visualizador(origen, dest_b, dest_c, umbral)
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}")

    tk.Button(frame, text="Abrir visualizador", command=ejecutar).grid(
        row=9, column=0, columnspan=3, sticky="we"
    )

    root.mainloop()


if __name__ == "__main__":
    main()
