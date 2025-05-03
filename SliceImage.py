from PIL import Image
import os

# Cargar la imagen
img = Image.open("C:/Users/M/Desktop/AssetsTest/AssetsTest/Ability/BoxesBeGoneIconSetReOpened.png")
width, height = img.size

tile_size = 32
output_dir = "C:/Users/M/Desktop/AssetsTest/AssetsTest/Ability"
os.makedirs(output_dir, exist_ok=True)

cols = width // tile_size
rows = height // tile_size

for row in range(rows):
    for col in range(cols):
        left = col * tile_size
        upper = row * tile_size
        right = left + tile_size
        lower = upper + tile_size
        tile = img.crop((left, upper, right, lower))
        tile.save(os.path.join(output_dir, f"icon_{row}_{col}.png"))
