from PIL import Image
import os

def convert_webp_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"
    
    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print(f"Convertido: {input_path} → {output_path}")

def convert_jpg_to_png(input_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"
    
    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print(f"Convertido: {input_path} → {output_path}")

def convert_folder_images_to_png(folder_path):
    for file_name in os.listdir(folder_path):
        input_path = os.path.join(folder_path, file_name)
        if file_name.lower().endswith(".jpg") or file_name.lower().endswith(".jpeg"):
            output_path = os.path.splitext(input_path)[0] + ".png"
            convert_jpg_to_png(input_path, output_path)
        elif file_name.lower().endswith(".webp"):
            output_path = os.path.splitext(input_path)[0] + ".png"
            convert_webp_to_png(input_path, output_path)

# Ejemplo de uso:
folder_path = r"C:\Users\M\Pictures\IA\ZzzAD\JPG"  # Ruta absoluta
convert_folder_images_to_png(folder_path)