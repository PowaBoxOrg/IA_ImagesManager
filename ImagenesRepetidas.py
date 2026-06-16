"""
Buscador y visor de imagenes duplicadas o visualmente similares.

El script abre una interfaz grafica para seleccionar una carpeta y definir un
umbral de similitud. Examina solamente los archivos de imagen ubicados
directamente en esa carpeta; no recorre subcarpetas. Para cada imagen genera un
hash perceptual pHash en escala de grises y lo compara con los grupos creados
previamente.

El umbral indica la distancia maxima permitida entre dos hashes:

- 0 exige hashes perceptuales identicos.
- Un valor mayor admite diferencias visuales progresivamente mas amplias.

Cada imagen se agrega al primer grupo cuyo hash representativo se encuentre
dentro del umbral. Despues se conservan solo los grupos que contienen al menos
dos imagenes y cuyos valores numericos, extraidos de los nombres de archivo,
tienen una diferencia mayor que RANGO_NUMERICO_MINIMO. Los nombres sin digitos
reciben el valor cero para este filtro.

Los resultados se muestran grupo por grupo en una ventana independiente. Las
imagenes se distribuyen en una cuadricula adaptable, se reducen manteniendo
completa su proporcion original y se recalculan cuando cambia el tamano de la
ventana. Si un grupo no cabe verticalmente, puede recorrerse mediante la barra
de desplazamiento o la rueda del raton. Los botones Anterior y Siguiente, asi
como las teclas de flecha, permiten cambiar de grupo.

La aplicacion es informativa: no elimina, mueve, renombra ni modifica las
imagenes. Los archivos que no puedan abrirse se omiten y el error se imprime en
el resumen final. El conteo y el calculo de hashes se ejecutan en segundo plano
y por lotes configurables para mantener activa la interfaz con carpetas muy
grandes. La busqueda de grupos similares usa un indice por distancia de Hamming
en lugar de comparar cada imagen con todos los grupos existentes.

Dependencias:

- Python con Tkinter para la interfaz grafica.
- Pillow (PIL) para abrir y mostrar las imagenes.
- imagehash para calcular y comparar los hashes perceptuales.

Si se inicia desde un entorno virtual donde falte alguna dependencia, el script
intenta relanzarse con el Python global asociado a ese entorno.

Formatos contemplados: PNG, JPG, JPEG, WEBP, BMP, GIF, TIF, TIFF y AVIF. La
compatibilidad efectiva depende de los formatos habilitados en Pillow.
"""

import importlib
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Iterator
from collections import defaultdict
from datetime import datetime
from tkinter import filedialog, messagebox, ttk


_error_relanzamiento = ""


def relanzar_con_python_global() -> bool:
    global _error_relanzamiento

    if Image is not None and imagehash is not None:
        return False
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        _error_relanzamiento = (
            "No se encontro el Python global asociado al entorno virtual."
        )
        return False

    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(
        os.path.abspath(sys.executable)
    ):
        return False

    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=os.environ.copy())
        return True
    except OSError as exc:
        _error_relanzamiento = f"No se pudo iniciar el Python global:\n{exc}"
        return False


try:
    imagehash = importlib.import_module("imagehash")
except Exception as exc:  # pragma: no cover
    imagehash = None
    _imagehash_import_error = str(exc)

try:
    from PIL import Image, ImageOps, ImageTk
except Exception as exc:  # pragma: no cover
    Image = None
    ImageOps = None
    ImageTk = None
    _pil_import_error = str(exc)


EXTENSIONES_VALIDAS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif")
RANGO_NUMERICO_MINIMO = 10  # solo mostrar grupos cuyo rango numerico sea > 10
ANCHO_TARJETA_OBJETIVO = 300
ALTO_MINIATURA_MAXIMO = 360
TAMANO_LOTE_PREDETERMINADO = 100
MAX_ERRORES_DETALLE = 100

CallbackEvento = Callable[[str, dict], None]
CallbackCancelacion = Callable[[], bool]


class NodoHash:
    def __init__(self, hash_imagen, orden: int):
        self.hash_imagen = hash_imagen
        self.orden = orden
        self.hijos: dict[int, "NodoHash"] = {}


class IndiceHashes:
    def __init__(self):
        self.raiz: NodoHash | None = None

    def agregar(self, hash_imagen, orden: int):
        nuevo = NodoHash(hash_imagen, orden)
        if self.raiz is None:
            self.raiz = nuevo
            return

        actual = self.raiz
        while True:
            distancia = hash_imagen - actual.hash_imagen
            hijo = actual.hijos.get(distancia)
            if hijo is None:
                actual.hijos[distancia] = nuevo
                return
            actual = hijo

    def buscar(self, hash_imagen, distancia_maxima: int) -> NodoHash | None:
        if self.raiz is None:
            return None

        mejor = None
        pendientes = [self.raiz]
        while pendientes:
            actual = pendientes.pop()
            distancia = hash_imagen - actual.hash_imagen
            if distancia <= distancia_maxima and (
                mejor is None or actual.orden < mejor.orden
            ):
                mejor = actual

            minimo = distancia - distancia_maxima
            maximo = distancia + distancia_maxima
            pendientes.extend(
                hijo
                for distancia_hijo, hijo in actual.hijos.items()
                if minimo <= distancia_hijo <= maximo
            )

        return mejor


def obtener_valor_numerico(nombre: str) -> int:
    """Extrae el valor numerico del nombre del archivo."""
    partes = "".join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0


def calcular_distribucion_visor(
    ancho: int,
    alto: int,
    total_imagenes: int,
):
    """Calcula columnas y limites de miniatura para el tamano disponible."""
    ancho = max(300, ancho)
    alto = max(240, alto)
    ancho_util = max(260, ancho - 24)
    columnas = max(1, ancho_util // ANCHO_TARJETA_OBJETIVO)
    columnas = min(max(1, total_imagenes), columnas)
    separacion = 12 * max(0, columnas - 1)
    ancho_tarjeta = max(220, (ancho_util - separacion) // columnas)
    filas = (max(1, total_imagenes) + columnas - 1) // columnas

    if filas == 1:
        alto_miniatura = max(
            160,
            min(ALTO_MINIATURA_MAXIMO, alto - 125),
        )
    else:
        alto_miniatura = max(
            160,
            min(300, int(alto * 0.48)),
        )

    return columnas, ancho_tarjeta, alto_miniatura


def iterar_imagenes(carpeta: str) -> Iterator[str]:
    with os.scandir(carpeta) as entradas:
        for entrada in entradas:
            try:
                if (
                    entrada.is_file(follow_symlinks=False)
                    and entrada.name.lower().endswith(EXTENSIONES_VALIDAS)
                ):
                    yield entrada.path
            except OSError:
                continue


def iterar_lotes(
    rutas: Iterator[str],
    tamano_lote: int,
) -> Iterator[list[str]]:
    lote = []
    for ruta in rutas:
        lote.append(ruta)
        if len(lote) >= tamano_lote:
            yield lote
            lote = []
    if lote:
        yield lote


def contar_imagenes(
    carpeta: str,
    tamano_lote: int,
    al_evento: CallbackEvento | None,
    debe_cancelar: CallbackCancelacion | None,
):
    total = 0
    revisados = 0
    with os.scandir(carpeta) as entradas:
        for entrada in entradas:
            if debe_cancelar is not None and debe_cancelar():
                return total, True

            revisados += 1
            try:
                if (
                    entrada.is_file(follow_symlinks=False)
                    and entrada.name.lower().endswith(EXTENSIONES_VALIDAS)
                ):
                    total += 1
            except OSError:
                pass

            if al_evento is not None and revisados % tamano_lote == 0:
                al_evento(
                    "conteo",
                    {
                        "archivos_revisados": revisados,
                        "imagenes": total,
                    },
                )

    if al_evento is not None:
        al_evento(
            "conteo",
            {
                "archivos_revisados": revisados,
                "imagenes": total,
            },
        )
    return total, False


def procesar_imagenes_duplicadas(
    carpeta: str,
    umbral_similitud: int = 5,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_evento: CallbackEvento | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")
    if imagehash is None:
        raise RuntimeError(f"No se pudo importar imagehash. Detalle: {_imagehash_import_error}")

    total, cancelado = contar_imagenes(
        carpeta,
        tamano_lote,
        al_evento,
        debe_cancelar,
    )
    resultado = {
        "duplicates": {},
        "total": total,
        "processed": 0,
        "groups_before_filter": 0,
        "errors": [],
        "error_count": 0,
        "cancelled": cancelado,
    }
    if cancelado or total == 0:
        return resultado

    hash_imagenes: dict[object, list[str]] = defaultdict(list)
    indice_hashes = IndiceHashes()
    procesadas = 0
    total_errores = 0
    errores: list[tuple[str, str]] = []
    cancelado = False

    for lote in iterar_lotes(iterar_imagenes(carpeta), tamano_lote):
        ultima_ruta = lote[-1]
        for ruta_archivo in lote:
            if debe_cancelar is not None and debe_cancelar():
                cancelado = True
                break

            procesadas += 1
            try:
                with Image.open(ruta_archivo) as img:
                    hash_img = imagehash.phash(img.convert("L"))

                coincidencia = indice_hashes.buscar(
                    hash_img,
                    umbral_similitud,
                )
                if coincidencia is None:
                    indice_hashes.agregar(hash_img, len(hash_imagenes))
                    hash_imagenes[hash_img].append(ruta_archivo)
                else:
                    hash_imagenes[coincidencia.hash_imagen].append(ruta_archivo)
            except Exception as exc:
                total_errores += 1
                if len(errores) < MAX_ERRORES_DETALLE:
                    errores.append((ruta_archivo, str(exc)))

        if al_evento is not None:
            al_evento(
                "hash",
                {
                    "processed": procesadas,
                    "total": total,
                    "groups": len(hash_imagenes),
                    "path": ultima_ruta,
                },
            )
        if cancelado:
            break

    duplicados_filtrados: dict[object, list[str]] = {}
    if not cancelado:
        for hash_img, rutas in hash_imagenes.items():
            if len(rutas) <= 1:
                continue

            valores = [
                obtener_valor_numerico(os.path.basename(ruta))
                for ruta in rutas
            ]
            if max(valores) - min(valores) > RANGO_NUMERICO_MINIMO:
                duplicados_filtrados[hash_img] = rutas

    resultado.update(
        duplicates=duplicados_filtrados,
        processed=procesadas,
        groups_before_filter=len(hash_imagenes),
        errors=errores,
        error_count=total_errores,
        cancelled=cancelado,
    )
    return resultado


def encontrar_imagenes_duplicadas(
    carpeta: str,
    umbral_similitud: int = 5,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
):
    """API compatible que devuelve solamente los grupos encontrados."""
    resultado = procesar_imagenes_duplicadas(
        carpeta,
        umbral_similitud,
        tamano_lote=tamano_lote,
    )
    return resultado["duplicates"]


def mostrar_grupos_duplicados(duplicados: dict):
    """Muestra los grupos en una cuadricula adaptable con desplazamiento."""
    if Image is None or ImageOps is None or ImageTk is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    ventana = tk.Toplevel()
    ventana.title("Grupos de imagenes duplicadas")
    ventana.geometry("1000x700")
    ventana.minsize(620, 420)
    ventana.configure(bg="#2e2e2e")
    ventana.rowconfigure(1, weight=1)
    ventana.columnconfigure(0, weight=1)

    grupos = list(duplicados.items())
    total_grupos = len(grupos)
    indice_grupo = tk.IntVar(value=0)
    referencias_imagenes: list[ImageTk.PhotoImage] = []

    cabecera_var = tk.StringVar()
    tk.Label(
        ventana,
        textvariable=cabecera_var,
        font=("Arial", 14, "bold"),
        bg="#2e2e2e",
        fg="#ffffff",
        anchor="w",
        padx=12,
        pady=10,
    ).grid(row=0, column=0, sticky="ew")

    frame_visor = tk.Frame(ventana, bg="#2e2e2e")
    frame_visor.grid(row=1, column=0, sticky="nsew")
    frame_visor.rowconfigure(0, weight=1)
    frame_visor.columnconfigure(0, weight=1)

    canvas = tk.Canvas(frame_visor, bg="#2e2e2e", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    scroll_vertical = tk.Scrollbar(
        frame_visor,
        orient="vertical",
        command=canvas.yview,
    )
    scroll_vertical.grid(row=0, column=1, sticky="ns")
    canvas.configure(yscrollcommand=scroll_vertical.set)

    frame_imagenes = tk.Frame(canvas, bg="#2e2e2e")
    ventana_canvas = canvas.create_window(
        (0, 0),
        window=frame_imagenes,
        anchor="nw",
    )

    frame_navegacion = tk.Frame(ventana, bg="#2e2e2e")
    frame_navegacion.grid(row=2, column=0, sticky="ew")
    frame_navegacion.columnconfigure(1, weight=1)

    columnas_configuradas = 0

    def actualizar_region_desplazamiento(posicion: float = 0.0):
        frame_imagenes.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox(ventana_canvas))
        canvas.yview_moveto(posicion)

    def renderizar_grupo(reiniciar_desplazamiento: bool = False):
        nonlocal columnas_configuradas
        posicion = 0.0 if reiniciar_desplazamiento else canvas.yview()[0]

        for widget in frame_imagenes.winfo_children():
            widget.destroy()
        referencias_imagenes.clear()

        _, rutas = grupos[indice_grupo.get()]
        columnas, ancho_tarjeta, alto_miniatura = calcular_distribucion_visor(
            canvas.winfo_width(),
            canvas.winfo_height(),
            len(rutas),
        )

        for columna in range(max(columnas_configuradas, columnas)):
            frame_imagenes.columnconfigure(columna, weight=0, uniform="")
        for columna in range(columnas):
            frame_imagenes.columnconfigure(
                columna,
                weight=1,
                uniform="tarjetas",
            )
        columnas_configuradas = columnas

        for indice_imagen, ruta in enumerate(rutas):
            fila = indice_imagen // columnas
            columna = indice_imagen % columnas
            tarjeta = tk.Frame(
                frame_imagenes,
                bg="#3a3a3a",
                bd=1,
                relief="solid",
                padx=10,
                pady=10,
            )
            tarjeta.grid(
                row=fila,
                column=columna,
                padx=6,
                pady=6,
                sticky="nsew",
            )

            try:
                with Image.open(ruta) as img:
                    img.seek(0)
                    imagen = ImageOps.exif_transpose(img).copy()
                    dimensiones = imagen.size

                imagen.thumbnail(
                    (max(100, ancho_tarjeta - 30), alto_miniatura),
                    Image.Resampling.LANCZOS,
                )
                img_tk = ImageTk.PhotoImage(imagen)
                referencias_imagenes.append(img_tk)

                panel = tk.Label(
                    tarjeta,
                    image=img_tk,
                    bg="#242424",
                    anchor="center",
                )
                panel.pack(fill="both", expand=True)

                nombre_archivo = os.path.basename(ruta)
                tk.Label(
                    tarjeta,
                    text=nombre_archivo,
                    font=("Arial", 10),
                    bg="#3a3a3a",
                    fg="#ffffff",
                    justify="center",
                    wraplength=max(180, ancho_tarjeta - 30),
                    pady=(8, 2),
                ).pack(fill="x")

                fecha_creacion = datetime.fromtimestamp(os.path.getctime(ruta)).strftime("%Y-%m-%d %H:%M:%S")
                tk.Label(
                    tarjeta,
                    text=(
                        f"Dimensiones: {dimensiones[0]} x {dimensiones[1]}\n"
                        f"Fecha: {fecha_creacion}"
                    ),
                    font=("Arial", 9),
                    bg="#3a3a3a",
                    fg="#d6d6d6",
                    justify="center",
                ).pack(fill="x")

            except Exception as exc:
                tk.Label(
                    tarjeta,
                    text=f"Error al cargar {ruta}: {exc}",
                    fg="red",
                    bg="#3a3a3a",
                    wraplength=max(180, ancho_tarjeta - 30),
                    justify="left",
                ).pack(fill="both", expand=True)

        ventana.after_idle(actualizar_region_desplazamiento, posicion)

    def actualizar_navegacion():
        indice = indice_grupo.get()
        hash_img, rutas = grupos[indice]
        cabecera_var.set(
            f"Grupo {indice + 1} de {total_grupos} | "
            f"{len(rutas)} imagen(es) | Hash: {hash_img}"
        )
        btn_anterior.config(state="normal" if indice > 0 else "disabled")
        btn_siguiente.config(
            state="normal" if indice < total_grupos - 1 else "disabled"
        )

    def mostrar_grupo(indice: int):
        indice_grupo.set(indice)
        actualizar_navegacion()
        renderizar_grupo(reiniciar_desplazamiento=True)

    def siguiente_grupo():
        if indice_grupo.get() < total_grupos - 1:
            mostrar_grupo(indice_grupo.get() + 1)

    def anterior_grupo():
        if indice_grupo.get() > 0:
            mostrar_grupo(indice_grupo.get() - 1)

    btn_anterior = tk.Button(
        frame_navegacion,
        text="Anterior",
        command=anterior_grupo,
        bg="#444444",
        fg="#ffffff",
    )
    btn_anterior.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    tk.Label(
        frame_navegacion,
        text="Use la rueda del raton para recorrer el grupo.",
        bg="#2e2e2e",
        fg="#c8c8c8",
    ).grid(row=0, column=1, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_navegacion,
        text="Siguiente",
        command=siguiente_grupo,
        bg="#444444",
        fg="#ffffff",
    )
    btn_siguiente.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    resize_after_id = None

    def ajustar_canvas(event):
        nonlocal resize_after_id
        canvas.itemconfigure(ventana_canvas, width=max(1, event.width))
        if resize_after_id is not None:
            ventana.after_cancel(resize_after_id)

        def redibujar():
            nonlocal resize_after_id
            resize_after_id = None
            if ventana.winfo_exists():
                renderizar_grupo(reiniciar_desplazamiento=False)

        resize_after_id = ventana.after(180, redibujar)

    canvas.bind("<Configure>", ajustar_canvas)

    def desplazar_rueda(event):
        if event.delta:
            canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    ventana.bind("<MouseWheel>", desplazar_rueda)
    ventana.bind("<Left>", lambda _event: anterior_grupo())
    ventana.bind("<Right>", lambda _event: siguiente_grupo())
    ventana.after_idle(mostrar_grupo, 0)


def main():
    root = tk.Tk()
    root.title("Imagenes repetidas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta:").grid(row=0, column=0, sticky="w")
    carpeta_var = tk.StringVar()
    carpeta_entry = tk.Entry(frame, textvariable=carpeta_var, width=56)
    carpeta_entry.grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta")
        if carpeta:
            carpeta_var.set(carpeta)

    boton_examinar = tk.Button(
        frame,
        text="Examinar",
        command=seleccionar_carpeta,
    )
    boton_examinar.grid(row=1, column=2, pady=(4, 8))

    tk.Label(frame, text="Umbral (0=identicas):").grid(row=2, column=0, sticky="w")
    umbral_var = tk.StringVar(value="15")
    umbral_entry = tk.Entry(frame, textvariable=umbral_var, width=12)
    umbral_entry.grid(row=3, column=0, pady=(4, 8), sticky="w")

    tk.Label(frame, text="Imagenes por lote:").grid(
        row=2,
        column=1,
        sticky="w",
    )
    lote_var = tk.StringVar(value=str(TAMANO_LOTE_PREDETERMINADO))
    lote_spinbox = tk.Spinbox(
        frame,
        from_=1,
        to=1000,
        textvariable=lote_var,
        width=12,
    )
    lote_spinbox.grid(row=3, column=1, pady=(4, 8), sticky="w")

    tk.Label(
        frame,
        text=(
            "Procesa en segundo plano y actualiza el progreso al terminar cada "
            f"lote. Solo muestra grupos con rango numerico > "
            f"{RANGO_NUMERICO_MINIMO} en el nombre."
        ),
        justify="left",
        wraplength=520,
    ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=500,
        mode="determinate",
    )
    barra.grid(row=5, column=0, columnspan=3, sticky="we", pady=(0, 6))

    estado_var = tk.StringVar(value="Seleccione una carpeta para comenzar.")
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=530,
    ).grid(row=6, column=0, columnspan=3, sticky="we", pady=(0, 8))

    botones = tk.Frame(frame)
    botones.grid(row=7, column=0, columnspan=3, sticky="we")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)

    boton_buscar = tk.Button(botones, text="Buscar duplicados")
    boton_buscar.grid(row=0, column=0, padx=(0, 4), sticky="we")

    cancelar_evento = threading.Event()
    mensajes: queue.Queue[tuple[str, object]] = queue.Queue()
    proceso_activo = False

    def cancelar():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        estado_var.set("Cancelando al terminar la imagen actual...")

    boton_cancelar = tk.Button(
        botones,
        text="Cancelar",
        state="disabled",
        command=cancelar,
    )
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    def configurar_controles(en_proceso: bool):
        estado = "disabled" if en_proceso else "normal"
        carpeta_entry.config(state=estado)
        umbral_entry.config(state=estado)
        lote_spinbox.config(state=estado)
        boton_examinar.config(state=estado)
        boton_buscar.config(state=estado)
        boton_cancelar.config(state="normal" if en_proceso else "disabled")

    def poner_barra_determinada():
        if str(barra.cget("mode")) != "determinate":
            barra.stop()
            barra.config(mode="determinate")

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La ruta no existe.")
            return

        try:
            umbral = int(umbral_var.get().strip())
            if umbral < 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Dato invalido", "El umbral debe ser un entero >= 0.")
            return

        try:
            tamano_lote = int(lote_var.get().strip())
            if not 1 <= tamano_lote <= 1000:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Lote invalido",
                "El tamano del lote debe ser un entero entre 1 y 1000.",
            )
            return

        nonlocal proceso_activo
        proceso_activo = True
        cancelar_evento.clear()
        progreso_var.set(0)
        barra.config(mode="indeterminate")
        barra.start(12)
        configurar_controles(True)
        estado_var.set("Contando imagenes compatibles...")

        def worker():
            try:
                resultado = procesar_imagenes_duplicadas(
                    carpeta,
                    umbral,
                    tamano_lote=tamano_lote,
                    al_evento=lambda tipo, datos: mensajes.put(
                        ("evento", (tipo, datos))
                    ),
                    debe_cancelar=cancelar_evento.is_set,
                )
                mensajes.put(("final", resultado))
            except Exception as exc:
                mensajes.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def manejar_evento(tipo: str, datos: dict):
        if tipo == "conteo":
            estado_var.set(
                f"Archivos revisados: {datos['archivos_revisados']} | "
                f"Imagenes encontradas: {datos['imagenes']}"
            )
        elif tipo == "hash":
            poner_barra_determinada()
            total = datos["total"]
            progreso_var.set(
                (datos["processed"] / total) * 100 if total else 100
            )
            estado_var.set(
                f"Procesando {datos['processed']} de {total} | "
                f"Grupos provisionales: {datos['groups']}\n"
                f"{os.path.basename(datos['path'])}"
            )

    def resumir_errores(
        errores: list[tuple[str, str]],
        total: int,
        limite: int = 6,
    ) -> str:
        lineas = [
            f"- {os.path.basename(ruta)}: {mensaje}"
            for ruta, mensaje in errores[:limite]
        ]
        restantes = total - len(lineas)
        if restantes > 0:
            lineas.append(f"- ... y {restantes} error(es) mas.")
        return "\n".join(lineas)

    def finalizar(resultado: dict):
        nonlocal proceso_activo
        proceso_activo = False
        barra.stop()
        poner_barra_determinada()
        configurar_controles(False)

        total = resultado["total"]
        procesadas = resultado["processed"]
        duplicados = resultado["duplicates"]
        total_errores = resultado["error_count"]
        resumen = (
            f"Imagenes encontradas: {total}\n"
            f"Imagenes procesadas: {procesadas}\n"
            f"Grupos mostrables: {len(duplicados)}\n"
            f"Errores: {total_errores}"
        )

        if resultado["cancelled"]:
            estado_var.set("Busqueda cancelada.")
            messagebox.showwarning("Busqueda cancelada", resumen)
            return

        progreso_var.set(100 if total else 0)
        if total == 0:
            estado_var.set("No se encontraron imagenes compatibles.")
            messagebox.showinfo(
                "Sin imagenes",
                "No se encontraron imagenes compatibles en la carpeta.",
            )
            return

        if not duplicados:
            estado_var.set("No se encontraron grupos duplicados o similares.")
            detalle = ""
            if total_errores:
                detalle = "\n\n" + resumir_errores(
                    resultado["errors"],
                    total_errores,
                )
            messagebox.showinfo("Sin duplicados", resumen + detalle)
            return

        estado_var.set("Busqueda completada. Abriendo el visor...")
        if total_errores:
            detalle = resumir_errores(resultado["errors"], total_errores)
            messagebox.showwarning(
                "Resultados con errores",
                f"{resumen}\n\n{detalle}\n\nSe abrira el visor.",
            )
        else:
            messagebox.showinfo(
                "Resultados",
                f"{resumen}\n\nSe abrira el visor.",
            )
        mostrar_grupos_duplicados(duplicados)
        estado_var.set("Busqueda completada.")

    def revisar_mensajes():
        try:
            while True:
                tipo, contenido = mensajes.get_nowait()
                if tipo == "evento":
                    nombre, datos = contenido
                    manejar_evento(nombre, datos)
                elif tipo == "final":
                    finalizar(contenido)
                elif tipo == "error":
                    nonlocal proceso_activo
                    proceso_activo = False
                    barra.stop()
                    poner_barra_determinada()
                    configurar_controles(False)
                    estado_var.set("No se pudo completar la busqueda.")
                    messagebox.showerror("Error", str(contenido))
        except queue.Empty:
            pass
        root.after(100, revisar_mensajes)

    def cerrar():
        if proceso_activo:
            confirmar = messagebox.askyesno(
                "Busqueda en curso",
                "Hay una busqueda activa. Desea cancelarla y cerrar?",
            )
            if not confirmar:
                return
            cancelar_evento.set()
        root.destroy()

    boton_buscar.config(command=ejecutar)
    root.protocol("WM_DELETE_WINDOW", cerrar)
    root.after(100, revisar_mensajes)
    carpeta_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
