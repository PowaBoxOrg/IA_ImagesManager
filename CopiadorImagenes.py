import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

import aplicacion.tema

from motores.archivos import rutas_iguales as _rutas_iguales_compartida
from motores.renombrado import afijo, afijo_valido, nombre_con_afijos

try:
    from PIL import Image, ImageTk
except Exception as exc:  # pragma: no cover
    Image = None
    ImageTk = None
    _pil_import_error = str(exc)


EXTENSIONES_VALIDAS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif")

NOMBRE_CARPETA_ALTO = "0_ALTO"
NOMBRE_CARPETA_BAJO = "0_BAJO"


def obtener_valor_numerico(nombre: str) -> int:
    """Extrae el valor numerico del nombre del archivo (primer numero encontrado)."""
    partes = re.findall(r"\d+", nombre)
    return int(partes[0]) if partes else 0


def listar_imagenes(carpeta_a: str, recursivo: bool = False):
    """Lista imágenes. Si recursivo=True, recorre también subcarpetas."""
    if not recursivo:
        imagenes = [
            os.path.join(carpeta_a, f)
            for f in os.listdir(carpeta_a)
            if os.path.isfile(os.path.join(carpeta_a, f)) and f.lower().endswith(EXTENSIONES_VALIDAS)
        ]
    else:
        imagenes = []
        for root, _, archivos in os.walk(carpeta_a):
            for f in archivos:
                if f.lower().endswith(EXTENSIONES_VALIDAS):
                    imagenes.append(os.path.join(root, f))
    imagenes.sort(key=lambda x: obtener_valor_numerico(os.path.basename(x)))
    return imagenes


def copiar_sin_conflicto(
    ruta_src: str,
    carpeta_destino: str,
    prefijo: str = "",
    sufijo: str = "",
) -> str:
    """Copia `ruta_src` a `carpeta_destino` evitando sobrescribir (agrega _1, _2, ...)."""
    nombre_archivo = nombre_con_afijos(os.path.basename(ruta_src), prefijo, sufijo)
    destino = os.path.join(carpeta_destino, nombre_archivo)

    contador = 1
    while os.path.exists(destino):
        nombre, ext = os.path.splitext(nombre_archivo)
        destino = os.path.join(carpeta_destino, f"{nombre}_{contador}{ext}")
        contador += 1

    shutil.copy(ruta_src, destino)
    return destino


def rutas_iguales(ruta_a: str, ruta_b: str) -> bool:
    return _rutas_iguales_compartida(ruta_a, ruta_b)


def resolver_carpeta_destino(
    carpeta_origen: str,
    carpeta_seleccionada: str = "",
    nombre_default: str = "",
) -> str:
    """Devuelve la carpeta destino. Si no se da seleccionada, usa nombre_default dentro del origen."""
    base = os.path.abspath(carpeta_seleccionada or carpeta_origen)
    if nombre_default and os.path.basename(base).casefold() == nombre_default.casefold():
        return base
    if nombre_default:
        return os.path.join(base, nombre_default)
    return base


def abrir_visualizador(
    carpeta_a: str,
    carpeta_b: str,
    carpeta_c: str,
    umbral_alto: int,
    recursivo: bool = False,
    prefijo: str = "",
    sufijo: str = "",
):
    if Image is None or ImageTk is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    imagenes = listar_imagenes(carpeta_a, recursivo=recursivo)
    if not imagenes:
        raise RuntimeError("No se encontraron imagenes en la carpeta de origen.")

    indice_actual = 0

    ventana = tk.Toplevel()
    ventana.title("Copiador/Visualizador de imagenes")

    screen_height = ventana.winfo_screenheight()
    ventana.geometry(f"800x{screen_height}")
    ventana.minsize(800, 400)
    ventana.resizable(True, True)
    ventana.configure(bg="#1b1e24")

    frame_imagen = tk.Frame(ventana, bg="#1b1e24")
    frame_imagen.pack(expand=True, fill=tk.BOTH)

    # Usamos Canvas en lugar de Label para mostrar la imagen.
    # Esto evita que el tamaño de la imagen afecte el tamaño de la ventana
    # y previene el achicamiento progresivo de la barra inferior.
    canvas = tk.Canvas(frame_imagen, bg="#1b1e24", highlightthickness=0)
    canvas.pack(expand=True, fill=tk.BOTH)

    frame_barra = tk.Frame(ventana, bg="#232830")
    frame_barra.pack(fill=tk.X, side=tk.BOTTOM)

    lbl_resolucion = tk.Label(
        frame_barra,
        text="Resolucion: ",
        font=("Segoe UI", 12),
        bg="#232830",
        fg="#e7e9ee",
    )
    lbl_resolucion.pack(side=tk.RIGHT, padx=10)

    lbl_contador = tk.Label(
        frame_barra,
        text="",
        font=("Segoe UI", 12),
        bg="#232830",
        fg="#e7e9ee",
    )
    lbl_contador.pack(side=tk.RIGHT, padx=10)

    tk.Label(
        frame_barra,
        text="Ir a imagen:",
        font=("Segoe UI", 12),
        bg="#232830",
        fg="#e7e9ee",
    ).pack(side=tk.LEFT, padx=10)

    entry_salto = tk.Entry(frame_barra, font=("Segoe UI", 12), width=6)
    entry_salto.pack(side=tk.LEFT, padx=5)

    def mostrar_imagen(indice: int):
        canvas.delete("all")

        ruta_imagen = imagenes[indice]
        try:
            img = Image.open(ruta_imagen)
            ancho_original, alto_original = img.size

            # Forzar actualización del layout antes de medir el área disponible
            canvas.update_idletasks()
            frame_barra.update_idletasks()
            ancho_frame = canvas.winfo_width()
            alto_frame = canvas.winfo_height()

            if ancho_frame <= 10 or alto_frame <= 10:
                # Fallback más robusto usando el tamaño de la ventana menos la barra
                ventana.update_idletasks()
                bar_h = frame_barra.winfo_height() or 60
                ancho_frame = ventana.winfo_width() or 800
                alto_frame = max(300, (ventana.winfo_height() or screen_height) - bar_h - 10)

            img.thumbnail((ancho_frame, alto_frame))

            img_tk = ImageTk.PhotoImage(img)

            # Dibujamos la imagen centrada en el canvas.
            # El canvas mantiene el tamaño del área, el cambio de imagen no altera
            # el tamaño pedido por la ventana → la barra inferior no se achica.
            cx = ancho_frame // 2
            cy = alto_frame // 2
            canvas.create_image(cx, cy, image=img_tk, anchor=tk.CENTER)
            canvas.image = img_tk  # mantener referencia para que no sea recolectada

            # Re-afirmamos el tamaño de la ventana tras cada cambio de imagen.
            # Esto impide que Tk reduzca el alto de la ventana (y por tanto la barra)
            # cuando la nueva imagen tiene dimensiones diferentes.
            ventana.update_idletasks()
            ww = ventana.winfo_width()
            hh = ventana.winfo_height()
            if ww > 50 and hh > 50:
                ventana.geometry(f"{ww}x{hh}")

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

            destino = copiar_sin_conflicto(ruta_imagen, destino_dir, prefijo, sufijo)
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
        ayuda="Muestra la imagen anterior. Atajo: A o flecha izquierda.",
    )
    btn_anterior.pack(side=tk.LEFT, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_barra,
        text="Siguiente",
        command=siguiente_imagen,
        ayuda="Muestra la imagen siguiente. Atajo: D o flecha derecha.",
    )
    btn_siguiente.pack(side=tk.LEFT, padx=10, pady=10)

    btn_copiar = tk.Button(
        frame_barra,
        text="Copiar a carpeta",
        command=copiar_imagen,
        ayuda="Copia la imagen visible a la carpeta alta o baja, segun su altura. Atajo: +.",
    )
    btn_copiar.pack(side=tk.LEFT, padx=10, pady=10)

    btn_salto = tk.Button(
        frame_barra,
        text="Ir",
        command=saltar_a_imagen,
    )
    btn_salto.pack(side=tk.LEFT, padx=5)

    entry_salto.bind("<Return>", saltar_a_imagen)

    ventana.bind("<Right>", siguiente_imagen)
    ventana.bind("<Left>", anterior_imagen)
    ventana.bind("d", siguiente_imagen)
    ventana.bind("a", anterior_imagen)
    ventana.bind("+", lambda _event: copiar_imagen())

    # Asegurar que los frames y el canvas tengan su tamaño real antes de mostrar
    ventana.update_idletasks()
    mostrar_imagen(indice_actual)

    # Fijamos el tamaño actual tras la primera imagen para evitar encogimiento posterior
    ventana.update_idletasks()
    w = ventana.winfo_width()
    h = ventana.winfo_height()
    if w > 50 and h > 50:
        ventana.geometry(f"{w}x{h}")


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
            if not dest_b_var.get().strip():
                dest_b_var.set(os.path.join(carpeta, NOMBRE_CARPETA_ALTO))
            if not dest_c_var.get().strip():
                dest_c_var.set(os.path.join(carpeta, NOMBRE_CARPETA_BAJO))

    tk.Button(frame, text="Examinar", command=sel_origen).grid(row=1, column=2, pady=(4, 8))

    # Destino >= umbral
    tk.Label(frame, text="Destino (>= umbral) [vacío = 0_ALTO]:").grid(row=2, column=0, sticky="w")
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
    tk.Label(frame, text="Destino (< umbral) [vacío = 0_BAJO]:").grid(row=4, column=0, sticky="w")
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

    # Switch para recorrer subcarpetas
    recursivo_var = tk.BooleanVar(value=False)
    tk.Checkbutton(
        frame,
        text="Revisar subcarpetas (recursivo)",
        variable=recursivo_var,
    ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 4))

    tk.Label(frame, text="Prefijo:").grid(row=9, column=0, sticky="w")
    tk.Label(frame, text="Sufijo:").grid(row=9, column=1, sticky="w")
    prefijo_var = tk.StringVar()
    sufijo_var = tk.StringVar()
    tk.Entry(frame, textvariable=prefijo_var, width=18).grid(row=10, column=0, sticky="w", pady=(4, 8))
    tk.Entry(frame, textvariable=sufijo_var, width=18).grid(row=10, column=1, sticky="w", pady=(4, 8))

    def ejecutar():
        if Image is None or ImageTk is None:
            messagebox.showerror("Pillow no disponible", f"No se pudo importar Pillow (PIL).\n\n{_pil_import_error}")
            return

        origen = origen_var.get().strip()
        dest_b = dest_b_var.get().strip()
        dest_c = dest_c_var.get().strip()
        recursivo = recursivo_var.get()

        if not origen:
            messagebox.showwarning("Falta origen", "Seleccione una carpeta origen.")
            return
        if not os.path.isdir(origen):
            messagebox.showerror("Ruta invalida", "La carpeta origen no existe.")
            return

        # Asignar carpetas default si no se proporcionó nombre (siguiendo patrón de otros scripts)
        if not dest_b:
            dest_b = resolver_carpeta_destino(origen, "", NOMBRE_CARPETA_ALTO)
        if not dest_c:
            dest_c = resolver_carpeta_destino(origen, "", NOMBRE_CARPETA_BAJO)

        dest_b_var.set(dest_b)
        dest_c_var.set(dest_c)

        if rutas_iguales(dest_b, dest_c):
            messagebox.showwarning(
                "Destinos invalidos", "Las dos carpetas de destino no pueden ser la misma."
            )
            return

        try:
            umbral = int(umbral_var.get().strip())
            if umbral <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "El umbral debe ser un entero mayor que 0.")
            return

        prefijo = afijo(prefijo_var.get())
        sufijo = afijo(sufijo_var.get())
        if not afijo_valido(prefijo) or not afijo_valido(sufijo):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        # Creamos destinos (si no existen)
        try:
            os.makedirs(dest_b, exist_ok=True)
            os.makedirs(dest_c, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudieron crear/verificar carpetas destino:\n\n{exc}")
            return

        try:
            abrir_visualizador(
                origen,
                dest_b,
                dest_c,
                umbral,
                recursivo=recursivo,
                prefijo=prefijo,
                sufijo=sufijo,
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Ocurrio un error:\n\n{exc}")

    tk.Button(frame, text="Abrir visualizador", command=ejecutar).grid(
        row=13, column=0, columnspan=3, sticky="we"
    )

    root.mainloop()


if __name__ == "__main__":
    main()
