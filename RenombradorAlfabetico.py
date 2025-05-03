import os

def generar_nombre_alfabetico(indice):
    """Genera un nombre alfabético estilo columnas de Excel (a, b, ..., z, aa, ab, ...)"""
    nombre = ""
    while indice >= 0:
        nombre = chr(indice % 26 + 97) + nombre
        indice = indice // 26 - 1
    return nombre

def renombrar_por_alfabeto(directorio):
    """Renombra los archivos en un directorio con nombres alfabéticos."""
    # Obtener lista de archivos
    archivos = [f for f in os.listdir(directorio) if os.path.isfile(os.path.join(directorio, f))]
    
    # Renombrar archivos con nombres alfabéticos
    for indice, nombre_original in enumerate(archivos):
        ruta_original = os.path.join(directorio, nombre_original)
        extension = os.path.splitext(nombre_original)[1]  # Conservar extensión (.jpg, .png, etc.)
        nuevo_nombre = generar_nombre_alfabetico(indice) + extension
        nueva_ruta = os.path.join(directorio, nuevo_nombre)
        
        # Evitar sobrescribir archivos existentes
        while os.path.exists(nueva_ruta):
            indice += 1
            nuevo_nombre = generar_nombre_alfabetico(indice) + extension
            nueva_ruta = os.path.join(directorio, nuevo_nombre)
        
        os.rename(ruta_original, nueva_ruta)
        print(f'Renombrado: "{nombre_original}" -> "{nuevo_nombre}"')

if __name__ == "__main__":
    # Configuración
    carpeta = r"C:\Users\M\Pictures\IA\ZzzAD"  # Ruta fija
    renombrar_por_alfabeto(carpeta)