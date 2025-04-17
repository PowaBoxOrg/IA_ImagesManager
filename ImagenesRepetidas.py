import os
import imagehash
from PIL import Image, ImageTk
from collections import defaultdict
import tkinter as tk
from tkinter import ttk
from datetime import datetime

def obtener_valor_numerico(nombre):
    """Extrae el valor numérico del nombre del archivo."""
    partes = ''.join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0

def encontrar_imagenes_duplicadas(carpeta, umbral_similitud=5):
    """
    Encuentra imágenes duplicadas o similares en una carpeta.
    
    Args:
        carpeta (str): Ruta de la carpeta con imágenes.
        umbral_similitud (int): Máxima diferencia permitida entre hashes (0 = idénticas).
    
    Returns:
        dict: Grupos de imágenes duplicadas (clave = hash, valor = lista de rutas).
    """
    # Almacenar hashes de imágenes
    hash_imagenes = defaultdict(list)
    
    # Recorrer archivos en la carpeta
    for nombre_archivo in os.listdir(carpeta):
        ruta_archivo = os.path.join(carpeta, nombre_archivo)
        
        # Verificar si es una imagen (soportamos formatos comunes)
        if not os.path.isfile(ruta_archivo) or not nombre_archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            continue
        
        try:
            # Abrir imagen y calcular hash perceptual (robusto a cambios de formato/tamaño)
            with Image.open(ruta_archivo) as img:
                # Convertir a escala de grises para normalizar
                img_gris = img.convert("L")
                # Calcular hash (pHash es bueno para comparaciones)
                hash_img = imagehash.phash(img_gris)
                
                # Agrupar imágenes con hashes similares
                encontrado = False
                for hash_existente in hash_imagenes:
                    if hash_img - hash_existente <= umbral_similitud:
                        hash_imagenes[hash_existente].append(ruta_archivo)
                        encontrado = True
                        break
                
                if not encontrado:
                    hash_imagenes[hash_img].append(ruta_archivo)
        except Exception as e:
            print(f"Error al procesar {ruta_archivo}: {e}")
    
    # Filtrar solo grupos con duplicados y rango de valores numéricos fuera de ±10
    duplicados_filtrados = {}
    for hash_img, rutas in hash_imagenes.items():
        if len(rutas) > 1:
            # Obtener los valores numéricos de los nombres
            valores_numericos = [obtener_valor_numerico(os.path.basename(ruta)) for ruta in rutas]
            min_valor = min(valores_numericos)
            max_valor = max(valores_numericos)
            
            # Verificar si el rango está fuera de ±10
            if max_valor - min_valor > 10:
                duplicados_filtrados[hash_img] = rutas

    return duplicados_filtrados

def mostrar_grupos_duplicados(duplicados):
    """
    Muestra los grupos de imágenes duplicadas en una ventana gráfica.
    
    Args:
        duplicados (dict): Grupos de imágenes duplicadas (clave = hash, valor = lista de rutas).
    """
    # Crear ventana principal
    ventana = tk.Tk()
    ventana.title("Grupos de Imágenes Duplicadas")
    ventana.geometry("800x600")
    
    # Variables para la navegación
    grupos = list(duplicados.items())
    total_grupos = len(grupos)
    indice_grupo = tk.IntVar(value=0)
    
    # Canvas para mostrar imágenes
    canvas = tk.Canvas(ventana)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Frame dentro del canvas
    frame_imagenes = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame_imagenes, anchor="nw")
    
    # Frame para la navegación
    frame_navegacion = tk.Frame(ventana)
    frame_navegacion.pack(fill=tk.X, side=tk.BOTTOM)
    
    def mostrar_grupo(indice):
        """Actualiza la ventana para mostrar un grupo específico."""
        for widget in frame_imagenes.winfo_children():
            widget.destroy()
        
        hash_img, rutas = grupos[indice]
        tk.Label(frame_imagenes, text=f"Grupo {indice + 1} de {total_grupos} (Hash: {hash_img})", font=("Arial", 14)).grid(row=0, column=0, columnspan=len(rutas), pady=10)
        
        for col, ruta in enumerate(rutas):
            # Mostrar imagen
            try:
                img = Image.open(ruta)
                
                # Ajustar tamaño de la imagen según el tamaño de la ventana
                ancho_canvas = canvas.winfo_width() or 800
                ancho_max = ancho_canvas // len(rutas) - 20
                img.thumbnail((ancho_max, ancho_max))
                
                img_tk = ImageTk.PhotoImage(img)
                panel = tk.Label(frame_imagenes, image=img_tk)
                panel.image = img_tk
                panel.grid(row=1, column=col, padx=10, pady=10)
                
                # Mostrar nombre de archivo
                nombre_archivo = os.path.basename(ruta)
                tk.Label(frame_imagenes, text=f"Nombre: {nombre_archivo}", font=("Arial", 10)).grid(row=2, column=col)
                
                # Mostrar fecha de creación
                fecha_creacion = datetime.fromtimestamp(os.path.getctime(ruta)).strftime('%Y-%m-%d %H:%M:%S')
                tk.Label(frame_imagenes, text=f"Fecha de creación: {fecha_creacion}", font=("Arial", 10)).grid(row=3, column=col)
            except Exception as e:
                tk.Label(frame_imagenes, text=f"Error al cargar {ruta}: {e}", fg="red").grid(row=1, column=col)
    
    def siguiente_grupo():
        """Muestra el siguiente grupo."""
        if indice_grupo.get() < total_grupos - 1:
            indice_grupo.set(indice_grupo.get() + 1)
            mostrar_grupo(indice_grupo.get())
    
    def anterior_grupo():
        """Muestra el grupo anterior."""
        if indice_grupo.get() > 0:
            indice_grupo.set(indice_grupo.get() - 1)
            mostrar_grupo(indice_grupo.get())
    
    # Botones de navegación
    btn_anterior = tk.Button(frame_navegacion, text="Anterior", command=anterior_grupo)
    btn_anterior.pack(side=tk.LEFT, padx=10, pady=10)
    
    btn_siguiente = tk.Button(frame_navegacion, text="Siguiente", command=siguiente_grupo)
    btn_siguiente.pack(side=tk.RIGHT, padx=10, pady=10)
    
    # Mostrar el primer grupo
    mostrar_grupo(indice_grupo.get())
    
    # Hacer que el canvas sea responsivo
    def ajustar_canvas(event):
        mostrar_grupo(indice_grupo.get())
    
    canvas.bind("<Configure>", ajustar_canvas)
    
    # Iniciar el loop de la ventana
    ventana.mainloop()

if __name__ == "__main__":
    carpeta = r"C:\Users\M\Pictures\IA\THM"  # Ruta fija
    umbral = 5  # Umbral de similitud predeterminado
    
    duplicados = encontrar_imagenes_duplicadas(carpeta, umbral)
    
    if not duplicados:
        print("✅ No se encontraron imágenes duplicadas.")
    else:
        print(f"🔍 Se encontraron {len(duplicados)} grupos de imágenes duplicadas/similares.")
        mostrar_grupos_duplicados(duplicados)