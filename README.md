# IA Images Manager

Coleccion de herramientas graficas para comparar, organizar, renombrar y
convertir imagenes, audio y video.

## Interfaz unificada

Ejecuta:

```powershell
python -m aplicacion.principal
```

La ventana principal organiza las herramientas en Duplicados, Organizacion,
Renombrado, Multimedia, Imagen y Otros. Algunas aparecen en mas de una seccion
porque participan en varios flujos. Las operaciones que pueden modificar
archivos se identifican antes de abrirse.

Los scripts historicos siguen funcionando directamente. La interfaz principal
los abre como procesos separados para conservar su comportamiento, sus hilos y
sus ventanas durante la migracion.

## Arquitectura

- `aplicacion/`: catalogo e infraestructura de la interfaz principal.
- `motores/`: logica reutilizable sin Tkinter.
- `tests/`: pruebas de rutas, lotes, similitud, renombrado y catalogo.
- `ProcesadorLotes.py`: adaptador compatible; la implementacion vive ahora en
  `motores/lotes.py`.

Motores disponibles:

- `motores.archivos`: rutas, pertenencia y nombres sin conflicto.
- `motores.ffmpeg`: localizacion y ejecucion uniforme de FFmpeg.
- `motores.imagenes`: extensiones y huellas de similitud visual.
- `motores.lotes`: busqueda, progreso, cancelacion y errores por archivo.
- `motores.renombrado`: validacion y aplicacion reversible de planes.

## Compatibilidad y reemplazos

- `MP4_a_Imagenes.py` y `MP4_a_Imagenes_Carpeta.py` permanecen disponibles para
  archivo individual y carpeta, respectivamente.
- `MP4_a_MP3.py` es el conversor recomendado de video a audio.
- `mkv2mp3.py` se conserva como alternativa heredada basada en MoviePy.
- `mp4tomp3.py` se muestra correctamente en el catalogo como **MP3 a MP4**; el
  nombre del archivo se mantiene para no romper accesos existentes.

## Pruebas

```powershell
python -m unittest discover -v
python -m compileall -q .
```
