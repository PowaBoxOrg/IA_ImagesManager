import os
import subprocess
import argparse

def convertir_mp4_a_gif(archivo_mp4, archivo_gif, fps=15, resize="640:-1"):
    """
    Convierte MP4 a GIF usando FFmpeg directamente
    """
    try:
        # Comando FFmpeg para la conversión
        comando = [
            'ffmpeg',
            '-i', archivo_mp4,
            '-vf', f'fps={fps},scale={resize}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
            '-loop', '0',
            archivo_gif
        ]
        
        # Ejecutar el comando
        subprocess.run(comando, check=True)
        print(f"Conversión exitosa: {archivo_mp4} → {archivo_gif}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir {archivo_mp4}: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

def procesar_carpeta(carpeta_entrada, carpeta_salida, fps=15, resize="640:-1"):
    """
    Procesa todos los MP4 en una carpeta
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    total_convertidos = 0
    
    for archivo in os.listdir(carpeta_entrada):
        if archivo.lower().endswith('.mp4'):
            ruta_mp4 = os.path.join(carpeta_entrada, archivo)
            nombre_base = os.path.splitext(archivo)[0]
            ruta_gif = os.path.join(carpeta_salida, f"{nombre_base}.gif")
            
            convertir_mp4_a_gif(ruta_mp4, ruta_gif, fps, resize)
            total_convertidos += 1
    
    print(f"\nProceso completado. {total_convertidos} archivos convertidos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convierte MP4 a GIF con FFmpeg')
    parser.add_argument('entrada', help='Archivo MP4 o carpeta con MP4s')
    parser.add_argument('salida', help='Archivo GIF de salida o carpeta destino')
    parser.add_argument('--fps', type=int, default=15, help='FPS del GIF (default: 15)')
    parser.add_argument('--resize', default="640:-1", help='Tamaño (ej: "320:-1" para ancho 320)')
    
    args = parser.parse_args()
    
    if os.path.isfile(args.entrada) and args.entrada.lower().endswith('.mp4'):
        convertir_mp4_a_gif(args.entrada, args.salida, args.fps, args.resize)
    elif os.path.isdir(args.entrada):
        procesar_carpeta(args.entrada, args.salida, args.fps, args.resize)
    else:
        print("Error: Entrada no válida. Debe ser un archivo MP4 o carpeta con MP4s.")

        """
        # Para un solo archivo:
        python mp4_a_gif_ffmpeg.py video.mp4 animacion.gif --fps 10 --resize "320:-1"

        # Para una carpeta:
        python mp4_a_gif_ffmpeg.py carpeta_mp4/ carpeta_gifs/ --fps 12
        """