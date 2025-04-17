import os
import imagehash
from PIL import Image
from collections import defaultdict

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

if __name__ == "__main__":
    carpeta = r"C:\Users\M\Pictures\IA\THM"  # Ruta fija
    umbral = 5  # Umbral de similitud predeterminado
    
    duplicados = encontrar_imagenes_duplicadas(carpeta, umbral)
    
    if not duplicados:
        print("✅ No se encontraron imágenes duplicadas.")
    else:
        print(f"🔍 Se encontraron {len(duplicados)} grupos de imágenes duplicadas/similares:")
        for i, (hash_img, rutas) in enumerate(duplicados.items(), start=1):
            print(f"\nGrupo {i} (Hash: {hash_img}):")
            for ruta in rutas:
                print(f"  - {ruta}")