import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
from moviepy import VideoFileClip

def seleccionar_archivo():
    """Abre el explorador para seleccionar el archivo .mkv"""
    ruta_archivo = filedialog.askopenfilename(
        title="Seleccionar video",
        filetypes=[("Archivos de video", "*.mkv *.mp4 *.avi"), ("Todos los archivos", "*.*")]
    )
    if ruta_archivo:
        entrada_archivo.delete(0, tk.END)
        entrada_archivo.insert(0, ruta_archivo)

def seleccionar_carpeta():
    """Abre el explorador para seleccionar la carpeta de destino"""
    ruta_carpeta = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
    if ruta_carpeta:
        entrada_carpeta.delete(0, tk.END)
        entrada_carpeta.insert(0, ruta_carpeta)

def iniciar_conversion():
    """Valida los campos y lanza la conversión en un hilo separado"""
    archivo_origen = entrada_archivo.get()
    carpeta_destino = entrada_carpeta.get()

    if not archivo_origen or not carpeta_destino:
        messagebox.showwarning("Faltan datos", "Por favor selecciona el archivo de origen y la carpeta de destino.")
        return

    if not os.path.exists(archivo_origen):
        messagebox.showerror("Error", "El archivo de origen no existe.")
        return

    # Deshabilitar el botón mientras trabaja
    boton_convertir.config(state=tk.DISABLED, text="Convirtiendo... (Por favor espera)")
    
    # Iniciar hilo secundario para no congelar la interfaz
    hilo = threading.Thread(target=ejecutar_conversion, args=(archivo_origen, carpeta_destino))
    hilo.start()

def ejecutar_conversion(archivo_origen, carpeta_destino):
    """Lógica principal de conversión usando MoviePy"""
    try:
        # Extraer el nombre original del archivo para nombrar el MP3
        nombre_base = os.path.splitext(os.path.basename(archivo_origen))[0]
        ruta_salida = os.path.join(carpeta_destino, f"{nombre_base}.mp3")

        # Proceso de conversión
        video = VideoFileClip(archivo_origen)
        video.audio.write_audiofile(ruta_salida, logger=None)
        video.close()

        # Mostrar mensaje de éxito
        messagebox.showinfo("Completado", f"✅ Conversión exitosa.\n\nArchivo guardado en:\n{ruta_salida}")
        
    except Exception as e:
        messagebox.showerror("Error de conversión", f"Ocurrió un error:\n{str(e)}")
        
    finally:
        # Restaurar el botón a su estado normal
        boton_convertir.config(state=tk.NORMAL, text="Convertir a MP3")

# ==========================================
# CONFIGURACIÓN DE LA INTERFAZ GRÁFICA (GUI)
# ==========================================
ventana = tk.Tk()
ventana.title("Conversor de Video a MP3")
ventana.geometry("550x220")
ventana.resizable(False, False)
ventana.config(padx=20, pady=20)

# --- Fila 1: Archivo de origen ---
tk.Label(ventana, text="Archivo de video (.mkv):", font=("Arial", 10, "bold")).pack(anchor="w")
frame_origen = tk.Frame(ventana)
frame_origen.pack(fill="x", pady=(0, 15))

entrada_archivo = tk.Entry(frame_origen, width=50)
entrada_archivo.pack(side="left", fill="x", expand=True, padx=(0, 10))

boton_examinar_archivo = tk.Button(frame_origen, text="Examinar...", command=seleccionar_archivo)
boton_examinar_archivo.pack(side="right")

# --- Fila 2: Carpeta de destino ---
tk.Label(ventana, text="Carpeta de guardado:", font=("Arial", 10, "bold")).pack(anchor="w")
frame_destino = tk.Frame(ventana)
frame_destino.pack(fill="x", pady=(0, 20))

entrada_carpeta = tk.Entry(frame_destino, width=50)
entrada_carpeta.pack(side="left", fill="x", expand=True, padx=(0, 10))

boton_examinar_carpeta = tk.Button(frame_destino, text="Examinar...", command=seleccionar_carpeta)
boton_examinar_carpeta.pack(side="right")

# --- Fila 3: Botón de Conversión ---
boton_convertir = tk.Button(ventana, text="Convertir a MP3", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=iniciar_conversion)
boton_convertir.pack(fill="x", pady=(10, 0))

# Iniciar la aplicación
ventana.mainloop()