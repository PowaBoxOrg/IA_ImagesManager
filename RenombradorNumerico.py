import os
from datetime import datetime

def generar_nombre_alfabetico(indice):
    """Genera un nombre alfabético estilo columnas de Excel (a, b, ..., z, aa, ab, ...)"""
    nombre = ""
    while indice >= 0:
        nombre = chr(indice % 26 + 97) + nombre
        indice = indice // 26 - 1
    return nombre

def renombrar_por_alfabeto(directorio):
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
        #print(f'Renombrado: "{nombre_original}" -> "{nuevo_nombre}"')

def renombrar_por_fecha(directorio, prefijo, inicio=1):
    # Obtener lista de archivos con sus fechas de creación
    archivos = []
    for nombre_archivo in os.listdir(directorio):
        ruta_archivo = os.path.join(directorio, nombre_archivo)
        if os.path.isfile(ruta_archivo):  # Solo archivos, no carpetas
            fecha_creacion = os.path.getctime(ruta_archivo)
            archivos.append((fecha_creacion, nombre_archivo, ruta_archivo))
    
    # Ordenar archivos por fecha de creación (más antiguo primero)
    archivos.sort()
    
    # Renombrar archivos numéricamente
    indice = inicio
    for fecha, nombre_original, ruta_original in archivos:
        extension = os.path.splitext(nombre_original)[1]  # Conservar extensión (.jpg, .png, etc.)
        nuevo_nombre = f"{prefijo}{indice}{extension}"
        nueva_ruta = os.path.join(directorio, nuevo_nombre)
        
        # Evitar sobrescribir archivos existentes
        while os.path.exists(nueva_ruta):
            indice += 1
            nuevo_nombre = f"{prefijo}{indice}{extension}"
            nueva_ruta = os.path.join(directorio, nuevo_nombre)
        
        os.rename(ruta_original, nueva_ruta)
        indice += 1
        #print(f'Renombrado: "{nombre_original}" -> "{nuevo_nombre}"')

if __name__ == "__main__":
    # Configuración
    carpeta = r"C:\Users\M\Pictures\IA\THM\THMorg\F"  # Ruta fija
    
    # Paso 1: Renombrar con nombres alfabéticos
    renombrar_por_alfabeto(carpeta)
    
    # Paso 2: Renombrar numéricamente
    prefijo = "F_"  # Prefijo opcional (puede ser "" para solo números)
    inicio = 1  # Número inicial para el renombrado
    renombrar_por_fecha(carpeta, prefijo, inicio)