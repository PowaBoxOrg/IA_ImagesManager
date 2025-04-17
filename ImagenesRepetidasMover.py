import os
import shutil
from PIL import Image
import imagehash
from collections import defaultdict

# Rutas
carpeta_fuente = r"C:\Users\M\Pictures\IA\THM"
carpeta_destino = r"C:\Users\M\Pictures\IA\THMrep"

# Crear carpeta destino si no existe
os.makedirs(carpeta_destino, exist_ok=True)

# Diccionario para agrupar por hash
hash_dict = defaultdict(list)

# Extensiones válidas
extensiones_validas = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')

# Recorrer imágenes y calcular hash
for root, _, files in os.walk(carpeta_fuente):
    for filename in files:
        if filename.lower().endswith(extensiones_validas):
            path = os.path.join(root, filename)
            try:
                with Image.open(path) as img:
                    hash_img = imagehash.phash(img)
                    hash_dict[str(hash_img)].append(path)
            except Exception as e:
                print(f"Error al procesar {path}: {e}")

# Función para extraer el valor numérico del nombre del archivo
def obtener_valor_numerico(nombre):
    partes = ''.join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0

# Mover duplicados (manteniendo el de menor valor numérico en la fuente)
for hash_val, paths in hash_dict.items():
    if len(paths) > 1:
        # Ordenar las rutas por el valor numérico del nombre del archivo
        paths.sort(key=lambda p: obtener_valor_numerico(os.path.basename(p)))

        # Mantener la primera (de menor valor numérico), mover el resto
        originales = paths[1:]  # Excluir el primero (el de menor valor numérico)
        for dup_path in originales:
            try:
                nombre_archivo = os.path.basename(dup_path)
                destino = os.path.join(carpeta_destino, nombre_archivo)

                # Si ya existe un archivo con ese nombre, renombrar para evitar conflictos
                contador = 1
                while os.path.exists(destino):
                    nombre, ext = os.path.splitext(nombre_archivo)
                    nuevo_nombre = f"{nombre}_{contador}{ext}"
                    destino = os.path.join(carpeta_destino, nuevo_nombre)
                    contador += 1

                shutil.move(dup_path, destino)
                print(f"Movido: {dup_path} → {destino}")
            except Exception as e:
                print(f"Error al mover {dup_path}: {e}")
