import os
from PIL import Image
import argparse

def extraer_frames_gif(ruta_gif, carpeta_salida, prefijo="frame"):
    """
    Extrae todos los frames de un archivo GIF y los guarda como PNG.
    
    Args:
        ruta_gif (str): Ruta del archivo GIF de entrada
        carpeta_salida (str): Carpeta donde se guardarán los frames PNG
        prefijo (str): Prefijo para los nombres de los archivos de salida
    """
    # Crear carpeta de salida si no existe
    os.makedirs(carpeta_salida, exist_ok=True)
    
    try:
        with Image.open(ruta_gif) as gif:
            print(f"Procesando: {os.path.basename(ruta_gif)} - {gif.n_frames} frames")
            
            for i in range(gif.n_frames):
                gif.seek(i)
                
                # Generar nombre de archivo de salida
                nombre_png = f"{prefijo}_{i:04d}.png"
                ruta_png = os.path.join(carpeta_salida, nombre_png)
                
                # Guardar frame como PNG
                gif.save(ruta_png, "PNG")
                print(f"Guardado: {nombre_png}")
                
    except Exception as e:
        print(f"Error al procesar {ruta_gif}: {e}")

def procesar_carpeta(carpeta_entrada, carpeta_salida):
    """
    Busca archivos GIF en una carpeta y extrae sus frames.
    
    Args:
        carpeta_entrada (str): Carpeta con archivos GIF
        carpeta_salida (str): Carpeta donde se guardarán los frames
    """
    # Contador de GIFs procesados
    total_gifs = 0
    
    # Recorrer archivos en la carpeta
    for archivo in os.listdir(carpeta_entrada):
        if archivo.lower().endswith('.gif'):
            ruta_gif = os.path.join(carpeta_entrada, archivo)
            
            # Crear subcarpeta para cada GIF
            nombre_base = os.path.splitext(archivo)[0]
            subcarpeta = os.path.join(carpeta_salida, nombre_base)
            
            extraer_frames_gif(ruta_gif, subcarpeta)
            total_gifs += 1
    
    print(f"\nProceso completado. {total_gifs} archivos GIF procesados.")

if __name__ == "__main__":
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(description='Extrae frames de GIFs a PNG')
    parser.add_argument('entrada', help='Carpeta con archivos GIF')
    parser.add_argument('salida', help='Carpeta de destino para los PNG')
    
    args = parser.parse_args()
    
    # Verificar si la carpeta de entrada existe
    if not os.path.isdir(args.entrada):
        print(f"Error: La carpeta de entrada '{args.entrada}' no existe")
        exit(1)
    
    # Procesar los GIFs
    procesar_carpeta(args.entrada, args.salida)