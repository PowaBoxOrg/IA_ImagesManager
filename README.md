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
archivos se identifican antes de abrirse. Si una herramienta reune varias
funciones, el modo se elige dentro de su ventana. La lista se desplaza si no
cabe en la ventana.

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
- `motores.video`: extraccion secuencial de todos los frames de un video.

## Extraer imagenes de un video

En Multimedia o Imagen, **Video a imagenes** ofrece cinco opciones:

- un video, capturando un frame cada N segundos;
- una carpeta de videos, con el mismo intervalo;
- una carpeta, ajustando la cantidad de capturas a la duracion;
- todos los frames del video;
- solo el primer frame.

Esas opciones tambien estan dentro de la ventana. Los scripts anteriores siguen
abriendo el modo que les correspondia. Para extraer frames desde la terminal:

```powershell
python Video_a_Frames.py "C:\ruta\al\video.mp4"
```

Sin una ruta, abre la ventana en **Todos los frames del video**. Informa los
FPS que reporta el decodificador y guarda un PNG por cada frame, en orden, en
una carpeta `<nombre>_frames` junto al archivo. Cada archivo se llama
`<nombre>_frame_000001.png`, con el nombre completo del video, para que se
puedan juntar capturas de varios videos sin que choquen. Si la carpeta ya
existe, crea otra con sufijo numerico para conservar las capturas anteriores.
En videos con tasa variable, los FPS reportados pueden ser nominales o
promedio; la extraccion lee todos los frames decodificados igualmente.
Requiere `opencv-python`.

Las capturas por intervalo usan el mismo patron:
`<nombre>_captura_000001.jpg`, dentro de `<nombre>_capturas`. Los frames de un
GIF quedan `<nombre>_frame_000001.png` y los mosaicos
`<nombre>_icon_00_00.png`.

La opcion **Solo el primer frame** crea una unica imagen
`<nombre>_primer_000001.png` junto al video, sin crear una carpeta. Si ya
existe, se agrega un sufijo numerico para no sobrescribirla. En la terminal,
`--solo-primer-frame` hace lo mismo: con una ruta guarda ese frame y sin ruta
abre la ventana en esa opcion.

## Compatibilidad y reemplazos

- `MP4_a_Imagenes.py` abre el modo de un solo video. `MP4_a_Imagenes_Carpeta.py`
  abre el de carpeta. `CapturadorAutomatico.py` abre la densidad por duracion.
  `Video_a_Frames.py` conserva la extraccion por terminal y, sin ruta, abre el
  modo de frames o el de primer frame.
- **Renombrar archivos** incluye el modo numerico, el alfabetico y conservar
  el nombre. Puede anteponer o agregar el nombre de la carpeta que contiene
  cada archivo; con subcarpetas, `videoA\\captura0001.png` y
  `videoB\\captura0001.png` pasan a `videoA_captura0001.png` y
  `videoB_captura0001.png`. `RenombradorAlfabetico.py` abre el modo alfabetico.
- `MP4_a_MP3.py` extrae audio con FFmpeg (archivo o carpeta) o con MoviePy
  (un archivo, la funcion que antes hacia `mkv2mp3.py`).
- `mp4tomp3.py` se muestra en el catalogo como **MP3 a MP4**; el nombre del
  archivo se mantiene para no romper accesos existentes.

## Pruebas

```powershell
python -m unittest discover -v
python -m compileall -q .
```
