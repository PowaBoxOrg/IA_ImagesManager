import os
from PIL import Image
import imagehash

# Rutas a las carpetas
carpeta_original = r"C:\Users\M\Pictures\IA\THM"
carpeta_repetidas = r"C:\Users\M\Pictures\IA\THMrep"

# Extensiones válidas
extensiones_validas = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')

# Función para obtener hashes de una carpeta
def obtener_hashes(carpeta):
    hashes = {}
    for root, _, files in os.walk(carpeta):
        for filename in files:
            if filename.lower().endswith(extensiones_validas):
                path = os.path.join(root, filename)
                try:
                    with Image.open(path) as img:
                        hash_img = imagehash.phash(img)
                        hashes[str(hash_img)] = path
                except Exception as e:
                    print(f"Error al procesar {path}: {e}")
    return hashes

# Obtener hashes
hashes_original = obtener_hashes(carpeta_original)
hashes_repetidas = obtener_hashes(carpeta_repetidas)

# Contadores
print(f"THM: {len(hashes_repetidas)} | THMrep: {len(hashes_original)}")

# Ordenar los archivos de la carpeta de repetidas por nombre numéricamente (si es posible)
def ordenar_por_nombre_numerico(item):
    nombre = os.path.basename(item[1])
    # Extraer la parte numérica del nombre si existe
    partes = ''.join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else nombre.lower()

hashes_repetidas_ordenados = dict(sorted(hashes_repetidas.items(), key=ordenar_por_nombre_numerico))

# Comparación
print("\nComparación de duplicados:")
coincidencias = 0
for hash_val, ruta_rep in hashes_repetidas_ordenados.items():
    ruta_orig = hashes_original.get(hash_val)
    if ruta_orig:
        print(f"{os.path.basename(ruta_rep)} → {os.path.basename(ruta_orig)}")
        coincidencias += 1

print(f"\nTotal de coincidencias encontradas: {coincidencias}")
