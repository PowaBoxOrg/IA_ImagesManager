"""
Buscador y visor de imagenes duplicadas o visualmente similares.

El script abre una interfaz grafica para seleccionar una carpeta y definir un
umbral de similitud (porcentaje). Examina solamente los archivos de imagen
ubicados directamente en esa carpeta; no recorre subcarpetas.

Para cada imagen genera una huella visual (miniatura 32x32 en escala de grises)
y mide la similitud como porcentaje respecto a la diferencia maxima posible de
pixeles (L1). Este metodo es adecuado para detectar conjuntos de imagenes
provenientes de videos, donde hay muchas imagenes muy parecidas entre si
(fotogramas consecutivos o cercanos).

La similitud minima indica el parecido requerido:

- 100 exige miniaturas visualmente identicas.
- Un valor menor (ej. 85) admite diferencias progresivas (cambios leves por
  movimiento, compresion o interpolacion de video).

Cada imagen se agrega al primer grupo cuyo representante este dentro del umbral
de similitud. Despues se conservan solo los grupos que contienen al menos dos
imagenes y cuyos valores numericos (del nombre de archivo) tienen diferencia
mayor que RANGO_NUMERICO_MINIMO.

Los resultados se muestran grupo por grupo en una ventana independiente con
cuadricula adaptable. La aplicacion es informativa (no modifica archivos).

El conteo y calculo de huellas se ejecutan en segundo plano por lotes. Se usa un
indice por distancia visual para evitar comparar contra todos los grupos.

Dependencias:

- Python con Tkinter para la interfaz grafica.
- Pillow (PIL) para abrir y mostrar las imagenes.

Si se inicia desde un entorno virtual donde falte alguna dependencia, el script
intenta relanzarse con el Python global asociado a ese entorno.

Formatos contemplados: PNG, JPG, JPEG, WEBP, BMP, GIF, TIF, TIFF y AVIF.
"""

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

import aplicacion.tema

from motores.imagenes import crear_huella_visual as _crear_huella_compartida
from motores.imagenes import distancia_visual as _distancia_visual_compartida


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

# Huella visual + similitud en porcentaje (sin dependencia imagehash)
TAMANO_HUELLA_VISUAL = (32, 32)
SIMILITUD_MINIMA_PREDETERMINADA = 85
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

    def buscar(self, huella: bytes, distancia_maxima: int) -> NodoHuella | None:
        if self.raiz is None:
            return None

        mejor = None
        pendientes = [self.raiz]
        while pendientes:
            actual = pendientes.pop()
            distancia = calcular_distancia_visual(huella, actual.huella)
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


def crear_huella_visual(imagen) -> bytes:
    """Genera huella visual compacta: miniatura gris 32x32 como bytes."""
    return _crear_huella_compartida(imagen, TAMANO_HUELLA_VISUAL)


def calcular_distancia_visual(huella_a: bytes, huella_b: bytes) -> int:
    """Suma de diferencias absolutas por pixel (0 .. DISTANCIA_VISUAL_MAXIMA)."""
    return _distancia_visual_compartida(huella_a, huella_b)


def similitud_a_distancia_maxima(similitud_min: int) -> int:
    """Convierte % similitud minima en distancia maxima permitida."""
    if similitud_min >= 100:
        return 0
    if similitud_min <= 0:
        return DISTANCIA_VISUAL_MAXIMA
    diff_max = 100 - similitud_min
    return round((diff_max / 100) * DISTANCIA_VISUAL_MAXIMA)


def distancia_visual_a_similitud(distancia: int) -> float:
    if DISTANCIA_VISUAL_MAXIMA == 0:
        return 0.0
    return 100.0 - (distancia / DISTANCIA_VISUAL_MAXIMA * 100)


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


def iterar_imagenes(carpeta: str, recursivo: bool = False) -> Iterator[str]:
    if not recursivo:
        try:
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
        except OSError:
            return
    else:
        for raiz, _, archivos in os.walk(carpeta, onerror=lambda e: None):
            for nombre in archivos:
                if nombre.lower().endswith(EXTENSIONES_VALIDAS):
                    yield os.path.join(raiz, nombre)


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
    recursivo: bool = False,
):
    total = 0
    revisados = 0

    def _emit_event():
        if al_evento is not None and revisados % tamano_lote == 0:
            al_evento("conteo", {"archivos_revisados": revisados, "imagenes": total})

    if not recursivo:
        try:
            with os.scandir(carpeta) as entradas:
                for entrada in entradas:
                    if debe_cancelar and debe_cancelar(): return total, True
                    revisados += 1
                    try:
                        if (entrada.is_file(follow_symlinks=False) and
                                entrada.name.lower().endswith(EXTENSIONES_VALIDAS)):
                            total += 1
                    except OSError:
                        pass
                    _emit_event()
        except OSError:
            pass
    else:
        for raiz, dirs, archivos in os.walk(carpeta, topdown=True, onerror=lambda e: None):
            items_a_procesar = dirs + archivos
            for nombre in items_a_procesar:
                if debe_cancelar and debe_cancelar():
                    if al_evento: al_evento("conteo", {"archivos_revisados": revisados, "imagenes": total})
                    return total, True
                
                revisados += 1
                if nombre.lower().endswith(EXTENSIONES_VALIDAS):
                    try:
                        # Necesario para no contar carpetas con extensiones de imagen
                        if os.path.isfile(os.path.join(raiz, nombre)):
                            total += 1
                    except OSError:
                        pass
                _emit_event()

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
    similitud_minima: int = SIMILITUD_MINIMA_PREDETERMINADA,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    recursivo: bool = False,
    al_evento: CallbackEvento | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    total, cancelado = contar_imagenes(
        carpeta,
        tamano_lote,
        al_evento,
        debe_cancelar,
        recursivo=recursivo,
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

    huellas_por_grupo: dict[bytes, list[str]] = defaultdict(list)
    indice = IndiceHuellas()
    procesadas = 0
    total_errores = 0
    errores: list[tuple[str, str]] = []
    cancelado = False

    distancia_maxima = similitud_a_distancia_maxima(similitud_minima)

    for lote in iterar_lotes(iterar_imagenes(carpeta, recursivo=recursivo), tamano_lote):
        ultima_ruta = lote[-1]
        for ruta_archivo in lote:
            if debe_cancelar is not None and debe_cancelar():
                cancelado = True
                break

            procesadas += 1
            try:
                with Image.open(ruta_archivo) as img:
                    huella = crear_huella_visual(img)

                coincidencia = indice.buscar(huella, distancia_maxima)
                if coincidencia is None:
                    indice.agregar(huella, len(huellas_por_grupo))
                    huellas_por_grupo[huella].append(ruta_archivo)
                else:
                    huellas_por_grupo[coincidencia.huella].append(ruta_archivo)
            except Exception as exc:
                total_errores += 1
                if len(errores) < MAX_ERRORES_DETALLE:
                    errores.append((ruta_archivo, str(exc)))

        if al_evento is not None:
            al_evento(
                "huella",
                {
                    "processed": procesadas,
                    "total": total,
                    "groups": len(huellas_por_grupo),
                    "path": ultima_ruta,
                },
            )
        if cancelado:
            break

    duplicados_filtrados: dict[bytes, list[str]] = {}
    if not cancelado:
        for huella, rutas in huellas_por_grupo.items():
            if len(rutas) <= 1:
                continue

            valores = [
                obtener_valor_numerico(os.path.basename(ruta))
                for ruta in rutas
            ]
            if max(valores) - min(valores) > RANGO_NUMERICO_MINIMO:
                duplicados_filtrados[huella] = rutas

    resultado.update(
        duplicates=duplicados_filtrados,
        processed=procesadas,
        groups_before_filter=len(huellas_por_grupo),
        errors=errores,
        error_count=total_errores,
        cancelled=cancelado,
    )
    return resultado


def encontrar_imagenes_duplicadas(
    carpeta: str,
    similitud_minima: int = SIMILITUD_MINIMA_PREDETERMINADA,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
):
    """API compatible que devuelve solamente los grupos encontrados."""
    resultado = procesar_imagenes_duplicadas(
        carpeta,
        similitud_minima,
        tamano_lote=tamano_lote,
    )
    return resultado["duplicates"]


def mostrar_grupos_duplicados(duplicados: dict):
    """Muestra los grupos en una cuadricula adaptable con desplazamiento.

    Soporta selección de imágenes:
    - Cada tarjeta tiene un checkbox "Mantener".
    - Por defecto solo la primera imagen del grupo está marcada.
    - Botones rápidos para cambiar la selección.
    - "Eliminar las NO seleccionadas de este grupo" borra del disco las imágenes
      no marcadas (debe quedar al menos una).
    - Botón "Eliminar TODO el grupo" permite borrar todas las imágenes del grupo
      actual (útil cuando todo el conjunto es indeseado).
    - Para grupos grandes (cientos de imágenes de video) se usa carga perezosa:
      solo se decodifican y muestran las miniaturas de las tarjetas visibles + un buffer.
      Esto evita que a partir de ~400 imágenes dejen de cargarse visualmente.
    - Útil para limpiar conjuntos de fotogramas muy parecidos de video.
    """
    if Image is None or ImageOps is None or ImageTk is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")

    ventana = tk.Toplevel()
    ventana.title("Grupos de imagenes duplicadas")
    ventana.geometry("1000x700")
    ventana.minsize(620, 420)
    ventana.configure(bg="#1b1e24")
    ventana.rowconfigure(1, weight=1)
    ventana.rowconfigure(3, weight=0)
    ventana.columnconfigure(0, weight=1)

    grupos = list(duplicados.items())
    total_grupos_var = tk.IntVar(value=len(grupos))
    indice_grupo = tk.IntVar(value=0)
    referencias_imagenes: list[ImageTk.PhotoImage] = []

    MAX_IMAGENES_SUBGRUPO = 480

    # Seccionar grupos grandes en subgrupos
    expanded_grupos = []
    sub_info = []  # Almacena (id_grupo_principal, num_subgrupo, total_subgrupos)
    main_id = 0
    for key, paths in grupos:
        paths = list(paths)
        if len(paths) <= MAX_IMAGENES_SUBGRUPO:
            expanded_grupos.append([key, paths])
            sub_info.append((main_id, 1, 1))
        else:
            chunks = [
                paths[i : i + MAX_IMAGENES_SUBGRUPO]
                for i in range(0, len(paths), MAX_IMAGENES_SUBGRUPO)
            ]
            total_subgrupos = len(chunks)
            for i, chunk in enumerate(chunks):
                expanded_grupos.append([key, chunk])
                sub_info.append((main_id, i + 1, total_subgrupos))
        main_id += 1
    grupos = expanded_grupos
    # sub_info es paralelo a grupos

    loaded_photos: dict[str, ImageTk.PhotoImage] = {}

    # Estado de selección por ruta (se mantiene entre re-renders del mismo grupo)
    selecciones: dict[str, tk.BooleanVar] = {}

    cabecera_var = tk.StringVar()
    tk.Label(
        ventana,
        textvariable=cabecera_var,
        font=("Arial", 14, "bold"),
        bg="#1b1e24",
        fg="#ffffff",
        anchor="w",
        padx=12,
        pady=10,
    ).grid(row=0, column=0, sticky="ew")

    frame_visor = tk.Frame(ventana, bg="#1b1e24")
    frame_visor.grid(row=1, column=0, sticky="nsew")
    frame_visor.rowconfigure(0, weight=1)
    frame_visor.columnconfigure(0, weight=1)

    canvas = tk.Canvas(frame_visor, bg="#1b1e24", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    scroll_vertical = tk.Scrollbar(
        frame_visor,
        orient="vertical",
        command=canvas.yview,
    )
    scroll_vertical.grid(row=0, column=1, sticky="ns")
    canvas.configure(yscrollcommand=scroll_vertical.set)

    # Cuando el usuario hace scroll, cargamos las imágenes que entran en vista
    def _on_scroll(*args):
        canvas.yview(*args)
        try:
            frame_imagenes.update_idletasks()
        except Exception:
            pass
        # No necesitamos recargar widgets (se crean todos al renderizar, <=480)
        # Solo asegurar la región de scroll si es necesario
        ventana.after(50, lambda: actualizar_region_desplazamiento(canvas.yview()[0] if canvas.winfo_exists() else 0))

    scroll_vertical.config(command=_on_scroll)

    frame_imagenes = tk.Frame(canvas, bg="#1b1e24")
    ventana_canvas = canvas.create_window(
        (0, 0),
        window=frame_imagenes,
        anchor="nw",
    )

    frame_navegacion = tk.Frame(ventana, bg="#1b1e24")
    frame_navegacion.grid(row=2, column=0, sticky="ew")
    frame_navegacion.columnconfigure(1, weight=1)

    columnas_configuradas = 0
    last_render_width = 0
    last_render_height = 0

    def actualizar_region_desplazamiento(posicion: float = 0.0):
        frame_imagenes.update_idletasks()
        try:
            # Asegurar que el tamaño del contenido dentro del canvas esté correcto
            req_h = frame_imagenes.winfo_reqheight()
            canvas.itemconfigure(ventana_canvas, height=max(1, req_h))
        except Exception:
            pass
        canvas.configure(scrollregion=canvas.bbox(ventana_canvas))
        canvas.yview_moveto(posicion)

    def reset_selecciones(rutas: list[str]):
        """Inicializa selecciones para un grupo nuevo: por defecto solo la primera."""
        selecciones.clear()
        for i, ruta in enumerate(rutas):
            selecciones[ruta] = tk.BooleanVar(value=(i == 0))

    def seleccionar_solo_primera():
        idx = indice_grupo.get()
        if idx >= len(grupos):
            return
        key, rutas = grupos[idx]
        for i, ruta in enumerate(rutas):
            if ruta in selecciones:
                selecciones[ruta].set(i == 0)

    def seleccionar_todas():
        for var in selecciones.values():
            var.set(True)

    def seleccionar_ninguna():
        for var in selecciones.values():
            var.set(False)

    def invertir_seleccion():
        for var in selecciones.values():
            var.set(not var.get())

    def eliminar_no_seleccionadas():
        """Elimina del disco las imágenes del grupo actual que NO estén seleccionadas para mantener."""
        idx = indice_grupo.get()
        if idx >= len(grupos):
            return
        key, rutas = grupos[idx]
        if len(rutas) <= 1:
            # check if more in chain
            has_more = False
            if idx < len(sub_info):
                curr_main = sub_info[idx][0]
                for j in range(idx+1, len(grupos)):
                    if sub_info[j][0] == curr_main and len(grupos[j][1]) > 0:
                        has_more = True
                        break
            if not has_more:
                messagebox.showinfo("Información", "El grupo tiene una sola imagen. Nada que eliminar.")
                return

        a_mantener = [r for r in rutas if r in selecciones and selecciones[r].get()]
        a_eliminar = [r for r in rutas if not (r in selecciones and selecciones[r].get())]

        if not a_eliminar:
            messagebox.showinfo("Nada que eliminar", "Todas las imágenes están marcadas para mantener.")
            return
        if not a_mantener:
            messagebox.showwarning("Acción inválida", "Debes mantener al menos una imagen del grupo.")
            return

        # Confirmación con preview
        preview = "\n".join(f"  • {os.path.basename(p)}" for p in a_eliminar[:10])
        if len(a_eliminar) > 10:
            preview += f"\n  ... (+{len(a_eliminar) - 10} más)"
        msg = (f"¿Eliminar {len(a_eliminar)} imagen(es) del grupo actual?\n\n"
               f"Se mantendrán: {len(a_mantener)}\n\n"
               f"Archivos que se BORRARÁN:\n{preview}\n\n"
               "Esta acción es PERMANENTE.")
        if not messagebox.askyesno("Confirmar eliminación", msg, icon="warning"):
            return

        eliminados = 0
        errores: list[str] = []
        for ruta in a_eliminar:
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
                eliminados += 1
            except Exception as exc:
                errores.append(f"{os.path.basename(ruta)}: {exc}")

        # Actualizar la lista del subgrupo (muta)
        rutas[:] = a_mantener

        # Si hay espacio, mover imágenes de subgrupos siguientes (Nb) hacia el actual (Na).
        if idx < len(sub_info):
            id_grupo_principal_actual = sub_info[idx][0]
            while len(rutas) < MAX_IMAGENES_SUBGRUPO:
                siguiente_idx = idx + 1
                # Asegurar que el siguiente subgrupo existe y pertenece al mismo grupo principal
                if (siguiente_idx < len(grupos) and
                    siguiente_idx < len(sub_info) and
                    sub_info[siguiente_idx][0] == id_grupo_principal_actual):

                    rutas_siguientes = grupos[siguiente_idx][1]
                    espacio_disponible = MAX_IMAGENES_SUBGRUPO - len(rutas)
                    cantidad_a_mover = min(espacio_disponible, len(rutas_siguientes))

                    if cantidad_a_mover > 0:
                        rutas.extend(rutas_siguientes[:cantidad_a_mover])
                        del rutas_siguientes[:cantidad_a_mover]

                        if not rutas_siguientes:
                            grupos.pop(siguiente_idx)
                            sub_info.pop(siguiente_idx)
                            # El total de grupos se actualizará al refrescar
                    else:
                        break  # No hay nada que mover
                else:
                    break  # No hay más subgrupos contiguos del mismo grupo principal

        # Limpiar selecciones: kept True, pulled False
        selecciones.clear()
        for ruta in rutas:
            selecciones[ruta] = tk.BooleanVar(value=False)
        for ruta in a_mantener:
            if ruta in selecciones:
                selecciones[ruta] = tk.BooleanVar(value=True)

        if len(rutas) <= 1:
            # check if more in the chain for this main
            has_more = False
            if idx < len(sub_info):
                curr_main = sub_info[idx][0]
                for j in range(idx, len(grupos)):
                    if j < len(sub_info) and sub_info[j][0] == curr_main and len(grupos[j][1]) > 0:
                        has_more = True
                        break
            if not has_more:
                grupos.pop(idx)
                if idx < len(sub_info):
                    sub_info.pop(idx)
                total_grupos_var.set(len(grupos))
                if not grupos:
                    messagebox.showinfo(
                        "Grupos limpiados",
                        f"Se eliminaron {eliminados} imágenes.\nNo quedan grupos con múltiples imágenes."
                    )
                    ventana.destroy()
                    return
                nuevo_idx = min(idx, len(grupos) - 1)
                mostrar_grupo(nuevo_idx)
                return

        # Refrescar el grupo actual
        actualizar_navegacion()
        renderizar_grupo(reiniciar_desplazamiento=True)

        if errores:
            detalle = "\n".join(errores[:5])
            messagebox.showwarning(
                "Eliminación parcial",
                f"Se eliminaron {eliminados} imágenes.\nErrores:\n{detalle}"
            )
        else:
            messagebox.showinfo("Eliminación completada", f"Se eliminaron {eliminados} imágenes.")

    def eliminar_grupo_completo():
        """Elimina TODAS las imágenes del grupo actual (subgrupo) del disco y quita el subgrupo del visor."""
        idx = indice_grupo.get()
        if idx >= len(grupos):
            return
        key, rutas = grupos[idx]
        if not rutas:
            grupos.pop(idx)
            if idx < len(sub_info):
                sub_info.pop(idx)
            total_grupos_var.set(len(grupos))
            selecciones.clear()
            if not grupos:
                ventana.destroy()
                return
            nuevo_idx = min(idx, len(grupos) - 1)
            mostrar_grupo(nuevo_idx)
            return

        preview = "\n".join(f"  • {os.path.basename(p)}" for p in rutas[:10])
        if len(rutas) > 10:
            preview += f"\n  ... (+{len(rutas) - 10} más)"

        msg = (
            f"⚠️ ¿ELIMINAR **TODAS** las {len(rutas)} imágenes de este subgrupo?\n\n"
            f"Archivos que se borrarán:\n{preview}\n\n"
            "Esta acción es PERMANENTE. Se eliminará el subgrupo completo."
        )
        if not messagebox.askyesno("Eliminar TODO el grupo", msg, icon="warning"):
            return

        eliminados = 0
        errores: list[str] = []
        for ruta in list(rutas):
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
                eliminados += 1
            except Exception as exc:
                errores.append(f"{os.path.basename(ruta)}: {exc}")

        # Quitar el subgrupo del visor
        grupos.pop(idx)
        if idx < len(sub_info):
            sub_info.pop(idx)
        total_grupos_var.set(len(grupos))
        selecciones.clear()

        if not grupos:
            messagebox.showinfo(
                "Grupo eliminado",
                f"Se eliminaron {eliminados} imágenes.\nNo quedan más grupos."
            )
            ventana.destroy()
            return

        nuevo_idx = min(idx, len(grupos) - 1)
        mostrar_grupo(nuevo_idx)

        if errores:
            detalle = "\n".join(errores[:5])
            messagebox.showwarning(
                "Eliminación parcial",
                f"Se eliminaron {eliminados} imágenes.\nAlgunos errores:\n{detalle}"
            )
        else:
            messagebox.showinfo("Grupo eliminado", f"Se eliminaron las {eliminados} imágenes del grupo.")

    def _load_one(info: dict):
        """Carga una sola miniatura si no está cargada todavía."""
        ruta = info["ruta"]
        if ruta in loaded_photos:
            return
        lbl = info.get("image_label")
        size = info.get("thumb_size", (260, 220))
        try:
            with Image.open(ruta) as img:
                img.seek(0)
                imagen = ImageOps.exif_transpose(img).copy()
            imagen.thumbnail(size, Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(imagen)
            loaded_photos[ruta] = img_tk
            if lbl and lbl.winfo_exists():
                lbl.configure(image=img_tk, text="")
            container = info.get("img_container")
            if container and container.winfo_exists():
                container.update_idletasks()
            fr = info.get("frame")
            if fr and fr.winfo_exists():
                fr.update_idletasks()
        except Exception as exc:
            if lbl and lbl.winfo_exists():
                lbl.configure(text=f"Error\n{str(exc)[:25]}")

    def renderizar_grupo(reiniciar_desplazamiento: bool = False):
        nonlocal columnas_configuradas, last_render_width, last_render_height
        last_render_width = canvas.winfo_width()
        last_render_height = canvas.winfo_height()

        for widget in frame_imagenes.winfo_children():
            widget.destroy()
        referencias_imagenes.clear()
        loaded_photos.clear()

        idx_actual = indice_grupo.get()
        if idx_actual >= len(grupos):
            return

        key, rutas = grupos[idx_actual]
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

        # Configurar filas
        num_filas = (len(rutas) + columnas - 1) // columnas
        for r in range(num_filas):
            frame_imagenes.rowconfigure(r, weight=0, minsize=80)

        for indice_imagen, ruta in enumerate(rutas):
            fila = indice_imagen // columnas
            columna = indice_imagen % columnas
            tarjeta = tk.Frame(
                frame_imagenes,
                bg="#2b313b",
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
                # Contenedor reservado para evitar que la imagen se recorte a barra superior
                img_container = tk.Frame(
                    tarjeta,
                    bg="#15181d",
                    height=alto_miniatura,
                    width=max(100, ancho_tarjeta - 30),
                )
                img_container.pack(fill="x", pady=(0, 4))
                img_container.pack_propagate(False)

                # Cargar la miniatura aquí (dentro del límite de 480)
                with Image.open(ruta) as img:
                    img.seek(0)
                    imagen = ImageOps.exif_transpose(img).copy()
                imagen.thumbnail(
                    (max(100, ancho_tarjeta - 30), alto_miniatura),
                    Image.Resampling.LANCZOS,
                )
                img_tk = ImageTk.PhotoImage(imagen)
                referencias_imagenes.append(img_tk)

                image_label = tk.Label(
                    img_container,
                    image=img_tk,
                    bg="#15181d",
                    anchor="center",
                )
                image_label.pack(fill="both", expand=True)

                nombre_archivo = os.path.basename(ruta)
                tk.Label(
                    tarjeta,
                    text=nombre_archivo,
                    font=("Segoe UI", 11),
                    bg="#2b313b",
                    fg="#e7e9ee",
                    justify="center",
                    wraplength=max(180, ancho_tarjeta - 30),
                ).pack(fill="x", pady=(0, 2))

                fecha_creacion = datetime.fromtimestamp(os.path.getctime(ruta)).strftime("%Y-%m-%d %H:%M:%S")
                tk.Label(
                    tarjeta,
                    text=f"Fecha: {fecha_creacion}",
                    font=("Segoe UI", 10),
                    bg="#2b313b",
                    fg="#c5cad3",
                    justify="center",
                ).pack(fill="x")

                # Checkbox de selección "Mantener"
                var = selecciones.get(ruta)
                if var is None:
                    var = tk.BooleanVar(value=(indice_imagen == 0))
                    selecciones[ruta] = var
                chk = tk.Checkbutton(
                    tarjeta,
                    text="Mantener",
                    variable=var,
                    bg="#2b313b",
                    fg="#9dcea0",
                    selectcolor="#d7dde8",
                    activebackground="#2b313b",
                    activeforeground="#e7e9ee",
                    font=("Segoe UI", 11),
                )
                chk.pack(fill="x", pady=(2, 0))

            except Exception as exc:
                tk.Label(
                    tarjeta,
                    text=f"Error al cargar {ruta}: {exc}",
                    fg="#e06c75",
                    bg="#2b313b",
                    wraplength=max(180, ancho_tarjeta - 30),
                    justify="left",
                ).pack(fill="both", expand=True)

        # Forzar tamaño del canvas window para contenido alto
        try:
            frame_imagenes.update_idletasks()
            req_w = frame_imagenes.winfo_reqwidth()
            req_h = frame_imagenes.winfo_reqheight()
            canvas.itemconfigure(ventana_canvas, width=max(1, req_w), height=max(1, req_h))
        except Exception:
            pass

        actualizar_region_desplazamiento(0.0 if reiniciar_desplazamiento else canvas.yview()[0])

    def actualizar_navegacion():
        indice = indice_grupo.get()
        if indice >= len(grupos):
            return

        key, rutas = grupos[indice]
        total_subgrupos_en_visor = total_grupos_var.get()
        n_imagenes = len(rutas)

        if indice < len(sub_info):
            main_id, sub_num, total_subs = sub_info[indice]
            # El título del visor indica el subgrupo actual
            ventana.title(f"Grupo {main_id + 1} (Subgrupo {sub_num}/{total_subs}) - ImagenesRepetidas")
            cabecera_var.set(
                f"Grupo {main_id + 1} - Subgrupo {sub_num} de {total_subs} | {n_imagenes} imagen(es)"
            )
        else: # Fallback por si sub_info no estuviera sincronizado
            ventana.title(f"Grupo {indice + 1} - ImagenesRepetidas")
            cabecera_var.set(
                f"Grupo {indice + 1} | {n_imagenes} imagen(es)"
            )

        btn_anterior.config(state="normal" if indice > 0 else "disabled")
        btn_siguiente.config(
            state="normal" if indice < total_subgrupos_en_visor - 1 else "disabled"
        )

    def mostrar_grupo(indice: int):
        indice_grupo.set(indice)
        key, rutas = grupos[indice]
        reset_selecciones(rutas)
        actualizar_navegacion()
        renderizar_grupo(reiniciar_desplazamiento=True)

    def siguiente_grupo():
        total = total_grupos_var.get()
        if indice_grupo.get() < total - 1:
            mostrar_grupo(indice_grupo.get() + 1)

    def anterior_grupo():
        if indice_grupo.get() > 0:
            mostrar_grupo(indice_grupo.get() - 1)

    btn_anterior = tk.Button(
        frame_navegacion,
        text="Anterior",
        command=anterior_grupo,
    )
    btn_anterior.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    tk.Label(
        frame_navegacion,
        text="Use la rueda del raton para recorrer el grupo.",
        bg="#1b1e24",
        fg="#9aa3b2",
    ).grid(row=0, column=1, padx=10, pady=10)

    btn_siguiente = tk.Button(
        frame_navegacion,
        text="Siguiente",
        command=siguiente_grupo,
    )
    btn_siguiente.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    # === Barra de acciones de selección y eliminación ===
    frame_seleccion = tk.Frame(ventana, bg="#1b1e24")
    frame_seleccion.grid(row=3, column=0, sticky="ew", padx=8, pady=(2, 8))

    tk.Button(
        frame_seleccion,
        text="Solo primera",
        command=seleccionar_solo_primera,
        width=14,
    ).grid(row=0, column=0, padx=3, pady=2)

    tk.Button(
        frame_seleccion,
        text="Todas",
        command=seleccionar_todas,
        width=10,
    ).grid(row=0, column=1, padx=3, pady=2)

    tk.Button(
        frame_seleccion,
        text="Ninguna",
        command=seleccionar_ninguna,
        width=10,
    ).grid(row=0, column=2, padx=3, pady=2)

    tk.Button(
        frame_seleccion,
        text="Invertir",
        command=invertir_seleccion,
        width=10,
    ).grid(row=0, column=3, padx=3, pady=2)

    btn_eliminar = tk.Button(
        frame_seleccion,
        text="🗑 Eliminar las NO seleccionadas de este grupo",
        command=eliminar_no_seleccionadas,
        width=36,
    )
    btn_eliminar.grid(row=0, column=4, padx=(10, 3), pady=2)

    btn_eliminar_todo = tk.Button(
        frame_seleccion,
        text="🗑 Eliminar TODO el grupo",
        command=eliminar_grupo_completo,
        width=22,
    )
    btn_eliminar_todo.grid(row=0, column=5, padx=(3, 4), pady=2)

    tk.Label(
        frame_seleccion,
        text="Marca las que quieres conservar y usa «Eliminar las NO seleccionadas», o pulsa «Eliminar TODO el grupo» para borrar todas las del grupo actual.",
        bg="#1b1e24",
        fg="#e7b4b8",
        font=("Segoe UI", 10),
    ).grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=(2, 0))

    resize_after_id = None

    def ajustar_canvas(event):
        nonlocal resize_after_id
        canvas.itemconfigure(ventana_canvas, width=max(1, event.width))
        if resize_after_id is not None:
            ventana.after_cancel(resize_after_id)

        def redibujar():
            nonlocal resize_after_id, last_render_width, last_render_height
            resize_after_id = None
            if not ventana.winfo_exists():
                return
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            # Evitar rebuilds completos en cambios pequeños o durante maximize (varios eventos de resize)
            # Solo full rebuild si el cambio es significativo (evita empalmes y layouts rotos)
            if abs(w - last_render_width) < 40 and abs(h - last_render_height) < 40:
                # small change: no full reload needed
                actualizar_region_desplazamiento( canvas.yview()[0] if canvas.winfo_exists() else 0 )
                return
            last_render_width = w
            last_render_height = h
            renderizar_grupo(reiniciar_desplazamiento=False)

        resize_after_id = ventana.after(250, redibujar)  # debounce un poco más largo para maximize

    canvas.bind("<Configure>", ajustar_canvas)

    def desplazar_rueda(event):
        if event.delta:
            canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        try:
            frame_imagenes.update_idletasks()
        except Exception:
            pass
        # No necesitamos recargar widgets (se crean todos al renderizar, <=480)
        # Solo asegurar la región de scroll si es necesario
        ventana.after(50, lambda: actualizar_region_desplazamiento(canvas.yview()[0] if canvas.winfo_exists() else 0))
        return "break"

    ventana.bind("<MouseWheel>", desplazar_rueda)
    ventana.bind("<Left>", lambda _event: anterior_grupo())
    ventana.bind("<Right>", lambda _event: siguiente_grupo())
    ventana.bind("<Delete>", lambda _event: eliminar_no_seleccionadas())
    ventana.bind("<d>", lambda _event: eliminar_no_seleccionadas())
    ventana.bind("<Shift-Delete>", lambda _event: eliminar_grupo_completo())
    ventana.bind("<Control-Delete>", lambda _event: eliminar_grupo_completo())

    def _try_maximize(win):
        # Para mejor usabilidad con grupos grandes, abrimos maximizado.
        # Llamado con delay para que el render inicial termine antes de resize adicional.
        try:
            win.state('zoomed')
        except Exception:
            try:
                win.attributes('-zoomed', True)
            except Exception:
                pass

    ventana.after(150, lambda: _try_maximize(ventana))
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

    tk.Label(frame, text="Similitud mínima (%):").grid(row=2, column=0, sticky="w")
    umbral_var = tk.StringVar(value=str(SIMILITUD_MINIMA_PREDETERMINADA))
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

    subcarpetas_var = tk.BooleanVar(value=False)
    subcarpetas_check = tk.Checkbutton(
        frame, text="Revisar subcarpetas", variable=subcarpetas_var
    )
    subcarpetas_check.grid(row=3, column=2, padx=(8, 0), pady=(4, 8), sticky="w")

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
        subcarpetas_check.config(state=estado)
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
            similitud = int(umbral_var.get().strip())
            if not 0 <= similitud <= 100:
                raise ValueError()
        except Exception:
            messagebox.showerror(
                "Dato invalido",
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
        
        recursivo = subcarpetas_var.get()

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
                    similitud,
                    tamano_lote=tamano_lote,
                    recursivo=recursivo,
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
        elif tipo == "huella":
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
