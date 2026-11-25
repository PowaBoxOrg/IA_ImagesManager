"""
Comparador de imagenes repetidas entre dos carpetas.

Este script abre una interfaz grafica sencilla en la que se deben seleccionar
dos ubicaciones:

1. La carpeta original, que contiene las imagenes que se toman como referencia.
2. La carpeta reservada "0_IMAGENES_REPETIDAS", cuyas imagenes se buscan
   dentro de la carpeta original.

El programa recorre ambas carpetas y todas sus subcarpetas, abre los archivos
con extensiones de imagen compatibles y crea para cada uno una huella visual:
una miniatura en escala de grises normalizada. Compara el parecido usando
diferencia de pixeles convertida a porcentaje de similitud. Este metodo es
adecuado para capturas de video, donde hay muchas imagenes que se parecen entre
si (fotogramas cercanos).

La coincidencia usa un porcentaje minimo de similitud:

- 100 exige miniaturas visualmente identicas.
- Valores menores (ej. 85-92) permiten mas variacion tipica de video.

Al finalizar informa conteos, coincidencias y una vista previa (hasta 30).
Para cada repetida reporta la original mas parecida que cumpla el umbral.

El script es informativo solamente. La interfaz procesa en lotes.

Dependencias:

- Python con Tkinter para la interfaz grafica.
- Pillow (PIL) para abrir y leer las imagenes.

Si se inicia desde un entorno virtual donde falte alguna dependencia, el script
intenta relanzarse con el Python global asociado a ese entorno.

Formatos contemplados: JPG, JPEG, PNG, BMP, GIF, TIFF, TIF, WEBP y AVIF.
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Iterator
from tkinter import filedialog, messagebox, ttk

import aplicacion.tema
from motores.imagenes import crear_huella_visual as _crear_huella_compartida
from motores.imagenes import distancia_visual as _distancia_visual_compartida
from motores.archivos import rutas_iguales as _rutas_iguales_compartida


_error_relanzamiento = ""


def relanzar_con_python_global() -> bool:
    global _error_relanzamiento

    if Image is not None:
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
    from PIL import Image
except Exception as exc:  # pragma: no cover
    Image = None
    _pil_import_error = str(exc)


EXTENSIONES_VALIDAS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".avif")
NOMBRE_CARPETA_REPETIDAS = "0_IMAGENES_REPETIDAS"
TAMANO_HUELLA_VISUAL = (32, 32)
SIMILITUD_MINIMA_PREDETERMINADA = 88
SIMILITUD_MINIMA_MAXIMA = 100
TAMANO_LOTE_PREDETERMINADO = 100
MAX_ERRORES_DETALLE = 200
PIXEL_MAXIMO = 255
DISTANCIA_VISUAL_MAXIMA = (
    TAMANO_HUELLA_VISUAL[0] * TAMANO_HUELLA_VISUAL[1] * PIXEL_MAXIMO
)

CallbackEvento = Callable[[str, dict], None]
CallbackCancelacion = Callable[[], bool]


class NodoHuella:
    def __init__(self, huella: bytes, orden: int):
        self.huella = huella
        self.orden = orden
        self.hijos: dict[int, "NodoHuella"] = {}


class IndiceHuellas:
    def __init__(self):
        self.raiz: NodoHuella | None = None

    def agregar(self, huella: bytes, orden: int):
        nuevo = NodoHuella(huella, orden)
        if self.raiz is None:
            self.raiz = nuevo
            return

        actual = self.raiz
        while True:
            distancia = calcular_distancia_visual(huella, actual.huella)
            hijo = actual.hijos.get(distancia)
            if hijo is None:
                actual.hijos[distancia] = nuevo
                return
            actual = hijo

    def buscar(
        self,
        huella: bytes,
        distancia_maxima: int,
    ) -> NodoHuella | None:
        if self.raiz is None:
            return None

        mejor = None
        mejor_distancia = None
        pendientes = [self.raiz]
        while pendientes:
            actual = pendientes.pop()
            distancia = calcular_distancia_visual(huella, actual.huella)
            if distancia <= distancia_maxima and (
                mejor is None
                or distancia < mejor_distancia
                or (distancia == mejor_distancia and actual.orden < mejor.orden)
            ):
                mejor = actual
                mejor_distancia = distancia

            minimo = distancia - distancia_maxima
            maximo = distancia + distancia_maxima
            pendientes.extend(
                hijo
                for distancia_hijo, hijo in actual.hijos.items()
                if minimo <= distancia_hijo <= maximo
            )

        return mejor


def rutas_iguales(ruta_a: str, ruta_b: str) -> bool:
    return _rutas_iguales_compartida(ruta_a, ruta_b)


def resolver_carpeta_repetidas(
    carpeta_original: str,
    carpeta_seleccionada: str = "",
) -> str:
    base = os.path.abspath(carpeta_seleccionada or carpeta_original)
    if os.path.basename(base).casefold() == NOMBRE_CARPETA_REPETIDAS.casefold():
        repetidas = base
    else:
        repetidas = os.path.join(base, NOMBRE_CARPETA_REPETIDAS)

    if rutas_iguales(repetidas, carpeta_original):
        raise ValueError("La carpeta de repetidas no puede ser la carpeta original.")
    return repetidas


def excluir_carpeta(
    carpeta_actual: str,
    subcarpetas: list[str],
    carpeta_excluida: str | None,
):
    if not carpeta_excluida:
        return
    subcarpetas[:] = [
        nombre
        for nombre in subcarpetas
        if not rutas_iguales(
            os.path.join(carpeta_actual, nombre),
            carpeta_excluida,
        )
    ]


def iterar_imagenes(
    carpeta: str,
    carpeta_excluida: str | None = None,
) -> Iterator[str]:
    for directorio, subcarpetas, archivos in os.walk(carpeta):
        excluir_carpeta(directorio, subcarpetas, carpeta_excluida)
        subcarpetas.sort(key=str.lower)
        for nombre in sorted(archivos, key=str.lower):
            if not nombre.lower().endswith(EXTENSIONES_VALIDAS):
                continue
            ruta = os.path.join(directorio, nombre)
            if os.path.isfile(ruta):
                yield ruta


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


def crear_huella_visual(imagen) -> bytes:
    return _crear_huella_compartida(imagen, TAMANO_HUELLA_VISUAL)


def calcular_distancia_visual(
    huella_a: bytes,
    huella_b: bytes,
) -> int:
    return _distancia_visual_compartida(huella_a, huella_b)


def distancia_visual_a_porcentaje(distancia: int) -> float:
    if DISTANCIA_VISUAL_MAXIMA == 0:
        return 0.0
    return (distancia / DISTANCIA_VISUAL_MAXIMA) * 100


def contar_imagenes(
    carpeta: str,
    carpeta_excluida: str | None = None,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_progresar: Callable[[int, int, str], None] | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    total = 0
    carpetas = 0
    ultima_ruta = carpeta

    for directorio, subcarpetas, archivos in os.walk(carpeta):
        excluir_carpeta(directorio, subcarpetas, carpeta_excluida)
        if debe_cancelar is not None and debe_cancelar():
            return total, carpetas, True

        subcarpetas.sort(key=str.lower)
        carpetas += 1
        ultima_ruta = directorio
        total += sum(
            1
            for nombre in archivos
            if nombre.lower().endswith(EXTENSIONES_VALIDAS)
            and os.path.isfile(os.path.join(directorio, nombre))
        )

        if al_progresar is not None and carpetas % tamano_lote == 0:
            al_progresar(total, carpetas, directorio)

    if al_progresar is not None:
        al_progresar(total, carpetas, ultima_ruta)
    return total, carpetas, False


def obtener_huellas(
    carpeta: str,
    total: int,
    carpeta_excluida: str | None = None,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_progresar: Callable[[int, int, str], None] | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    huellas: list[tuple[bytes, str]] = []
    scanned = 0
    errors: list[tuple[str, str]] = []
    total_errors = 0
    cancelado = False
    rutas = iterar_imagenes(carpeta, carpeta_excluida)

    for lote in iterar_lotes(rutas, tamano_lote):
        ultima_ruta = lote[-1]
        for ruta in lote:
            if debe_cancelar is not None and debe_cancelar():
                cancelado = True
                break

            scanned += 1
            try:
                with Image.open(ruta) as imagen:
                    huellas.append((crear_huella_visual(imagen), ruta))
            except Exception as exc:
                total_errors += 1
                if len(errors) < MAX_ERRORES_DETALLE:
                    errors.append((ruta, str(exc)))

        if al_progresar is not None:
            al_progresar(scanned, total, ultima_ruta)
        if cancelado:
            break

    return huellas, scanned, errors, total_errors, cancelado


def ordenar_por_nombre_numerico(item):
    # item: (huella, path)
    nombre = os.path.basename(item[1])
    partes = "".join(filter(str.isdigit, nombre))
    if partes.isdigit():
        return 0, int(partes), nombre.lower()
    return 1, 0, nombre.lower()


def crear_indice_huellas(huellas: list[tuple[bytes, str]]):
    indice = IndiceHuellas()
    rutas = {}
    for orden, (huella, ruta) in enumerate(huellas):
        indice.agregar(huella, orden)
        rutas[orden] = ruta
    return indice, rutas


def comparar_carpetas(
    carpeta_original: str,
    carpeta_repetidas: str,
    similitud_minima: int = SIMILITUD_MINIMA_PREDETERMINADA,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_evento: CallbackEvento | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    if not 0 <= similitud_minima <= 100:
        raise ValueError("La similitud minima debe estar entre 0 y 100.")

    def emitir(tipo: str, **datos):
        if al_evento is not None:
            al_evento(tipo, datos)

    total_orig, carpetas_orig, cancelado = contar_imagenes(
        carpeta_original,
        carpeta_excluida=carpeta_repetidas,
        tamano_lote=tamano_lote,
        al_progresar=lambda imagenes, carpetas, ruta: emitir(
            "conteo",
            fase="original",
            imagenes=imagenes,
            carpetas=carpetas,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )
    resultado = {
        "orig_count": 0,
        "rep_count": 0,
        "scanned_orig": 0,
        "scanned_rep": 0,
        "folders_orig": carpetas_orig,
        "folders_rep": 0,
        "errors": [],
        "error_count": 0,
        "matches": [],
        "cancelled": cancelado,
        "cancel_phase": "conteo_original" if cancelado else "",
        "repeated_folder": carpeta_repetidas,
        "similitud_minima": similitud_minima,
        "method": "similitud_porcentaje_huella",
    }
    if cancelado:
        return resultado

    total_rep, carpetas_rep, cancelado = contar_imagenes(
        carpeta_repetidas,
        tamano_lote=tamano_lote,
        al_progresar=lambda imagenes, carpetas, ruta: emitir(
            "conteo",
            fase="repetidas",
            imagenes=imagenes,
            carpetas=carpetas,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )
    resultado["folders_rep"] = carpetas_rep
    if cancelado:
        resultado.update(cancelled=True, cancel_phase="conteo_repetidas")
        return resultado

    total_global = total_orig + total_rep
    huellas_original, scanned_orig, errors_orig, count_orig, cancelado = obtener_huellas(
        carpeta_original,
        total_orig,
        carpeta_excluida=carpeta_repetidas,
        tamano_lote=tamano_lote,
        al_progresar=lambda procesadas, total, ruta: emitir(
            "huella",
            fase="original",
            procesadas=procesadas,
            total=total,
            global_procesadas=procesadas,
            global_total=total_global,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )
    resultado.update(
        orig_count=len(huellas_original),
        scanned_orig=scanned_orig,
        errors=errors_orig,
        error_count=count_orig,
        cancelled=cancelado,
        cancel_phase="huella_original" if cancelado else "",
    )
    if cancelado:
        return resultado

    huellas_repetidas, scanned_rep, errors_rep, count_rep, cancelado = obtener_huellas(
        carpeta_repetidas,
        total_rep,
        tamano_lote=tamano_lote,
        al_progresar=lambda procesadas, total, ruta: emitir(
            "huella",
            fase="repetidas",
            procesadas=procesadas,
            total=total,
            global_procesadas=total_orig + procesadas,
            global_total=total_global,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )
    resultado.update(
        rep_count=len(huellas_repetidas),
        scanned_rep=scanned_rep,
        errors=errors_orig + errors_rep,
        error_count=count_orig + count_rep,
        cancelled=cancelado,
        cancel_phase="huella_repetidas" if cancelado else "",
    )
    if cancelado:
        return resultado

    huellas_repetidas_ordenadas = sorted(
        huellas_repetidas,
        key=ordenar_por_nombre_numerico,
    )
    indice_original, rutas_original = crear_indice_huellas(huellas_original)
    distancia_maxima = round(((100 - similitud_minima) / 100) * DISTANCIA_VISUAL_MAXIMA)

    coincidencias = []
    for huella_rep, ruta_rep in huellas_repetidas_ordenadas:
        nodo = indice_original.buscar(huella_rep, distancia_maxima)
        if nodo is not None:
            distancia = calcular_distancia_visual(huella_rep, nodo.huella)
            diferencia = distancia_visual_a_porcentaje(distancia)
            similitud = 100 - diferencia
            coincidencias.append(
                (ruta_rep, rutas_original[nodo.orden], diferencia, similitud)
            )

    resultado["matches"] = coincidencias
    return resultado


def main():
    root = tk.Tk()
    root.title("Comparar repetidos (2 carpetas)")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(frame, text="Carpeta original:").grid(row=0, column=0, sticky="w")
    orig_var = tk.StringVar()
    orig_entry = tk.Entry(frame, textvariable=orig_var, width=58)
    orig_entry.grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_orig():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta original")
        if carpeta:
            orig_var.set(carpeta)
            if not rep_var.get().strip():
                rep_var.set(os.path.join(carpeta, NOMBRE_CARPETA_REPETIDAS))

    boton_orig = tk.Button(frame, text="Examinar", command=sel_orig)
    boton_orig.grid(row=1, column=2, pady=(4, 8))

    tk.Label(
        frame,
        text=f"Carpeta repetidas ({NOMBRE_CARPETA_REPETIDAS}):",
    ).grid(row=2, column=0, sticky="w")
    rep_var = tk.StringVar()
    rep_entry = tk.Entry(
        frame,
        textvariable=rep_var,
        width=58,
        ayuda=(
            f"Carpeta donde se comparan las copias. "
            f"Si queda dentro de la original, se excluye de la busqueda. "
            f"Vacia: se usa {NOMBRE_CARPETA_REPETIDAS}."
        ),
    )
    rep_entry.grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def sel_rep():
        carpeta = filedialog.askdirectory(
            title="Seleccionar carpeta repetidas o carpeta contenedora"
        )
        if carpeta:
            origen = orig_var.get().strip() or carpeta
            rep_var.set(resolver_carpeta_repetidas(origen, carpeta))

    boton_rep = tk.Button(frame, text="Examinar", command=sel_rep)
    boton_rep.grid(row=3, column=2, pady=(4, 8))

    tk.Label(frame, text="Similitud mínima (%):").grid(
        row=4,
        column=0,
        sticky="w",
    )
    umbral_var = tk.StringVar(value=str(SIMILITUD_MINIMA_PREDETERMINADA))
    umbral_spinbox = tk.Spinbox(
        frame,
        from_=0,
        to=SIMILITUD_MINIMA_MAXIMA,
        textvariable=umbral_var,
        width=12,
    )
    umbral_spinbox.grid(row=5, column=0, sticky="w", pady=(4, 8))

    tk.Label(frame, text="Imagenes por lote:").grid(row=4, column=1, sticky="w")
    lote_var = tk.StringVar(value=str(TAMANO_LOTE_PREDETERMINADO))
    lote_spinbox = tk.Spinbox(
        frame,
        from_=1,
        to=1000,
        textvariable=lote_var,
        width=12,
    )
    lote_spinbox.grid(row=5, column=1, sticky="w", pady=(4, 8))

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=510,
        mode="determinate",
    )
    barra.grid(row=7, column=0, columnspan=3, sticky="we", pady=(0, 6))

    estado_var = tk.StringVar(value="Seleccione las carpetas para comenzar.")
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=540,
    ).grid(row=8, column=0, columnspan=3, sticky="we", pady=(0, 8))

    resumen_var = tk.StringVar(value="")
    tk.Label(frame, textvariable=resumen_var, justify="left", wraplength=540).grid(
        row=9, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    botones = tk.Frame(frame)
    botones.grid(row=10, column=0, columnspan=3, sticky="we")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)

    boton_comparar = tk.Button(botones, text="Comparar")
    boton_comparar.grid(row=0, column=0, padx=(0, 4), sticky="we")

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
        command=cancelar,
        state="disabled",
    )
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    def configurar_controles(en_proceso: bool):
        estado = "disabled" if en_proceso else "normal"
        orig_entry.config(state=estado)
        rep_entry.config(state=estado)
        umbral_spinbox.config(state=estado)
        lote_spinbox.config(state=estado)
        boton_orig.config(state=estado)
        boton_rep.config(state=estado)
        boton_comparar.config(state=estado)
        boton_cancelar.config(state="normal" if en_proceso else "disabled")

    def poner_barra_determinada():
        if str(barra.cget("mode")) != "determinate":
            barra.stop()
            barra.config(mode="determinate")

    def validar_dependencias() -> bool:
        if Image is None:
            detalle = (
                "No se pudo importar Pillow (PIL).\n\n"
                f"Interprete:\n{sys.executable}\n\n"
                f"Detalle:\n{_pil_import_error}"
            )
            if _error_relanzamiento:
                detalle += f"\n\n{_error_relanzamiento}"
            messagebox.showerror("Pillow no disponible", detalle)
            return False
        return True

    def ejecutar():
        if not validar_dependencias():
            return
        carpeta_original = orig_var.get().strip()
        if not carpeta_original:
            messagebox.showwarning("Falta carpeta", "Seleccione la carpeta original.")
            return
        if not os.path.isdir(carpeta_original):
            messagebox.showerror("Ruta invalida", "La carpeta original no existe.")
            return

        carpeta_original = os.path.abspath(carpeta_original)
        try:
            carpeta_repetidas = resolver_carpeta_repetidas(
                carpeta_original,
                rep_var.get().strip(),
            )
            os.makedirs(carpeta_repetidas, exist_ok=True)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Carpeta repetidas invalida", str(exc))
            return
        rep_var.set(carpeta_repetidas)

        try:
            similitud = int(umbral_var.get().strip())
            if not 0 <= similitud <= 100:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Similitud invalida",
                "La similitud minima debe ser un entero entre 0 y 100.",
            )
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
        resumen_var.set("")
        progreso_var.set(0)
        barra.config(mode="indeterminate")
        barra.start(12)
        configurar_controles(True)
        estado_var.set("Contando imagenes por carpetas...")

        def worker():
            try:
                info = comparar_carpetas(
                    carpeta_original,
                    carpeta_repetidas,
                    similitud_minima=similitud,
                    tamano_lote=tamano_lote,
                    al_evento=lambda tipo, datos: mensajes.put(
                        ("evento", (tipo, datos))
                    ),
                    debe_cancelar=cancelar_evento.is_set,
                )
                mensajes.put(("final", info))
            except Exception as exc:
                mensajes.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def finalizar(info: dict):
        nonlocal proceso_activo
        proceso_activo = False
        barra.stop()
        poner_barra_determinada()
        configurar_controles(False)

        matches = info["matches"]
        total_errors = info["error_count"]
        resumen = (
            f"Original (huellas): {info['orig_count']} (imagenes leidas: {info['scanned_orig']})\n"
            f"Repetidas (huellas): {info['rep_count']} (imagenes leidas: {info['scanned_rep']})\n"
            f"Similitud minima: {info.get('similitud_minima', '?')}%\n"
            f"Coincidencias: {len(matches)}\n"
            f"Errores: {total_errors}"
        )
        resumen_var.set(resumen)

        if info["cancelled"]:
            estado_var.set("Comparacion cancelada.")
            messagebox.showwarning("Comparacion cancelada", resumen)
            return

        progreso_var.set(100)
        if not matches:
            estado_var.set("No se encontraron coincidencias.")
            if total_errors:
                messagebox.showwarning("Sin coincidencias", f"No se encontraron coincidencias.\n\n{resumen}")
            else:
                messagebox.showinfo("Sin coincidencias", f"No se encontraron coincidencias.\n\n{resumen}")
            return

        preview_lines = [
            f"{os.path.basename(r)} -> {os.path.basename(o)} "
            f"(diferencia: {d:.2f}%, similitud: {s:.2f}%)"
            for (r, o, d, s) in matches[:30]
        ]
        preview = "\n".join(preview_lines)
        if len(matches) > 30:
            preview += f"\n... (+{len(matches) - 30} mas)"

        estado_var.set("Comparacion completada.")
        if total_errors:
            messagebox.showwarning("Coincidencias encontradas", f"{resumen}\n\nPrimeras coincidencias:\n{preview}")
        else:
            messagebox.showinfo("Coincidencias encontradas", f"{resumen}\n\nPrimeras coincidencias:\n{preview}")

    def manejar_evento(tipo: str, datos: dict):
        if tipo == "conteo":
            fase = "original" if datos["fase"] == "original" else "repetidas"
            estado_var.set(
                f"Contando carpeta {fase}: {datos['imagenes']} imagen(es), "
                f"{datos['carpetas']} carpeta(s)."
            )
        elif tipo == "huella":
            poner_barra_determinada()
            total = datos["global_total"]
            progreso_var.set(
                (datos["global_procesadas"] / total) * 100 if total else 100
            )
            estado_var.set(
                f"Calculando huellas visuales de {datos['fase']}: "
                f"{datos['procesadas']} de {datos['total']}\n"
                f"{os.path.basename(datos['ruta'])}"
            )

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
                    estado_var.set("No se pudo completar la comparacion.")
                    messagebox.showerror("Error", str(contenido))
        except queue.Empty:
            pass
        root.after(100, revisar_mensajes)

    def cerrar():
        if proceso_activo:
            confirmar = messagebox.askyesno(
                "Comparacion en curso",
                "Hay una comparacion activa. Desea cancelarla y cerrar?",
            )
            if not confirmar:
                return
            cancelar_evento.set()
        root.destroy()

    boton_comparar.config(command=ejecutar)
    root.protocol("WM_DELETE_WINDOW", cerrar)
    root.after(100, revisar_mensajes)
    orig_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
