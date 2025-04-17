import os
import shutil
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox

def mostrar_imagen(indice):
    """Muestra la imagen actual y su información."""
    for widget in frame_imagen.winfo_children():
        widget.destroy()

    ruta_imagen = imagenes[indice]
    try:
        # Cargar imagen
        img = Image.open(ruta_imagen)
        ancho, alto = img.size

        # Ajustar tamaño de la imagen para que quepa en el canvas
        img.thumbnail((600, 600))
        img_tk = ImageTk.PhotoImage(img)

        # Mostrar imagen
        panel = tk.Label(frame_imagen, image=img_tk, bg="#2e2e2e")
        panel.image = img_tk
        panel.pack()

        # Actualizar resolución y contador
        lbl_resolucion.config(text=f"Resolución: {ancho}x{alto}")
        lbl_contador.config(text=f"Imagen {indice + 1} de {len(imagenes)}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar la imagen: {e}")

def siguiente_imagen():
    """Muestra la siguiente imagen."""
    global indice_actual
    if indice_actual < len(imagenes) - 1:
        indice_actual += 1
        mostrar_imagen(indice_actual)

def anterior_imagen():
    """Muestra la imagen anterior."""
    global indice_actual
    if indice_actual > 0:
        indice_actual -= 1
        mostrar_imagen(indice_actual)

def copiar_imagen():
    """Copia la imagen actual a la carpeta B o C según su resolución."""
    ruta_imagen = imagenes[indice_actual]
    try:
        # Obtener resolución de la imagen
        with Image.open(ruta_imagen) as img:
            _, alto = img.size

        # Determinar carpeta de destino
        if alto < 480:
            destino = carpeta_c
        else:
            destino = carpeta_b

        # Copiar imagen
        shutil.copy(ruta_imagen, destino)
        messagebox.showinfo("Éxito", f"Imagen copiada a {destino}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo copiar la imagen: {e}")

if __name__ == "__main__":
    # Configuración
    carpeta_a = r"C:\Users\M\Pictures\IA\THM\THMorg\F"  # Carpeta de origen
    carpeta_b = r"C:\Users\M\Pictures\IA\THM\THM Training Data\THM_ds_FluxD"  # Carpeta destino para imágenes >= 480p
    carpeta_c = r"C:\Users\M\Pictures\IA\THM\THM Training Data\THM_ds_FluxF"  # Carpeta destino para imágenes < 480p

    # Obtener lista de imágenes
    imagenes = [
        os.path.join(carpeta_a, f)
        for f in os.listdir(carpeta_a)
        if os.path.isfile(os.path.join(carpeta_a, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ]

    if not imagenes:
        print("No se encontraron imágenes en la carpeta A.")
        exit()

    # Variables de navegación
    indice_actual = 0

    # Crear ventana principal
    ventana = tk.Tk()
    ventana.title("Visualizador de Imágenes")
    ventana.geometry("800x600")
    ventana.configure(bg="#2e2e2e")

    # Frame para la imagen
    frame_imagen = tk.Frame(ventana, bg="#2e2e2e")
    frame_imagen.pack(expand=True, fill=tk.BOTH)

    # Frame para la barra inferior
    frame_barra = tk.Frame(ventana, bg="#444444")
    frame_barra.pack(fill=tk.X, side=tk.BOTTOM)

    # Botones de navegación
    btn_anterior = tk.Button(
        frame_barra,
        text="Anterior",
        command=anterior_imagen,
        bg="#555555",
        fg="#ffffff"
    )
    btn_anterior.pack(side=tk.LEFT, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_barra,
        text="Siguiente",
        command=siguiente_imagen,
        bg="#555555",
        fg="#ffffff"
    )
    btn_siguiente.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón de copiar
    btn_copiar = tk.Button(
        frame_barra,
        text="Copiar a carpeta",
        command=copiar_imagen,
        bg="#555555",
        fg="#ffffff"
    )
    btn_copiar.pack(side=tk.LEFT, padx=10, pady=10)

    # Etiqueta de resolución
    lbl_resolucion = tk.Label(
        frame_barra,
        text="Resolución: ",
        font=("Arial", 12),
        bg="#444444",
        fg="#ffffff"
    )
    lbl_resolucion.pack(side=tk.RIGHT, padx=10)

    # Contador de imágenes
    lbl_contador = tk.Label(
        frame_barra,
        text="",
        font=("Arial", 12),
        bg="#444444",
        fg="#ffffff"
    )
    lbl_contador.pack(side=tk.RIGHT, padx=10)

    # Mostrar la primera imagen
    mostrar_imagen(indice_actual)

    # Iniciar el loop de la ventana
    ventana.mainloop()