import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import string

class ImageGrouper:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.existing_groups = set()
        self.next_group_char = 'A'
        self.scan_existing_groups()
        
    def scan_existing_groups(self):
        """Escanea la carpeta para detectar grupos existentes"""
        for filename in os.listdir(self.folder_path):
            if '_' in filename:
                group_char = filename.split('_')[0]
                if group_char.isalpha() and len(group_char) == 1:
                    self.existing_groups.add(group_char.upper())
        
        # Determinar la siguiente letra de grupo disponible
        if self.existing_groups:
            last_group = sorted(self.existing_groups)[-1]
            self.next_group_char = chr(ord(last_group) + 1)
            if self.next_group_char > 'Z':
                self.next_group_char = 'AA'  # Para manejar más de 26 grupos
        else:
            self.next_group_char = 'A'
    
    def process_new_images(self):
        """Procesa imágenes nuevas sin grupo"""
        new_images = [
            f for f in os.listdir(self.folder_path) 
            if f.endswith('.png') and '_' not in f and f.split('.')[0].isdigit()
        ]
        
        if not new_images:
            return
        
        # Ordenar imágenes numéricamente
        new_images.sort(key=lambda x: int(x.split('.')[0]))
        
        # Asignar grupo a las nuevas imágenes
        group_char = self.next_group_char
        self.existing_groups.add(group_char)
        
        for filename in new_images:
            new_name = f"{group_char}_{filename}"
            old_path = os.path.join(self.folder_path, filename)
            new_path = os.path.join(self.folder_path, new_name)
            
            try:
                os.rename(old_path, new_path)
                print(f"Renombrado: {filename} → {new_name}")
            except Exception as e:
                print(f"Error al renombrar {filename}: {e}")
        
        # Actualizar siguiente letra de grupo
        if group_char == 'Z':
            self.next_group_char = 'AA'
        elif group_char == 'ZZ':
            print("¡Se han agotado todas las letras de grupo!")
        else:
            self.next_group_char = chr(ord(group_char) + 1)

class ImageHandler(FileSystemEventHandler):
    def __init__(self, grouper):
        self.grouper = grouper
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.png'):
            # Esperar un breve momento para asegurar que el archivo esté completamente escrito
            time.sleep(0.5)
            self.grouper.process_new_images()

def main():
    folder_to_watch = r"C:\Users\M\Pictures\IA\AD\Agrupadas"  # Cambia esto por tu ruta
    grouper = ImageGrouper(folder_to_watch)
    
    # Procesar cualquier imagen existente al inicio
    grouper.process_new_images()
    
    # Configurar el observador
    event_handler = ImageHandler(grouper)
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    
    print(f"Monitoreando carpeta: {folder_to_watch}")
    print("Presiona Ctrl+C para detener...")
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()