"""
Detector y organizador de imagenes repetidas en una carpeta.

Este script proporciona una interfaz grafica para seleccionar una carpeta
fuente y una carpeta destino. Su finalidad es localizar imagenes duplicadas
dentro de la fuente y mover las copias sobrantes al destino, dejando una sola
imagen de cada grupo en su ubicacion original.

La carpeta fuente se recorre de forma recursiva, por lo que tambien se analizan
las imagenes guardadas en sus subcarpetas. Cada archivo compatible se abre con
Pillow y se representa mediante un hash perceptual pHash calculado por la
biblioteca imagehash. Este tipo de hash compara el contenido visual en lugar del
nombre o los bytes del archivo. El programa agrupa como duplicadas solamente las
imagenes cuyos valores pHash son exactamente iguales; no utiliza un umbral para
detectar imagenes meramente parecidas.

Cuando un grupo contiene dos o mas imagenes, sus rutas se ordenan usando el
valor formado por todos los digitos presentes en el nombre del archivo. La
imagen con el valor numerico menor se conserva en la carpeta fuente y todas las
demas se mueven a la carpeta destino. Por ejemplo, entre 001.png y 010.png se
conserva 001.png. Un nombre sin digitos recibe el valor cero, por lo que puede
tener prioridad sobre nombres numericos. Si varias imagenes tienen el mismo
valor, el archivo conservado dependera del orden en que el sistema haya
recorrido las carpetas.

Todos los duplicados se colocan directamente en una carpeta reservada llamada
"0_IMAGENES_REPETIDAS", sin reproducir la estructura de subcarpetas de la
fuente. El usuario puede seleccionar esa carpeta o una carpeta contenedora; en
el segundo caso, el programa crea dentro el destino reservado. Si el destino
esta dentro de la fuente, se excluye por completo del conteo y del calculo de
hashes. Si ya existe alli un archivo con el mismo nombre, el programa evita
sobrescribirlo agregando un sufijo numerico: nombre_1.png, nombre_2.png, etc.

El conteo, el calculo de hashes y los movimientos se ejecutan en segundo plano
para mantener activa la interfaz. Las rutas se consumen en lotes pequenos y las
imagenes se abren de una en una, de modo que solo una imagen permanece cargada
en memoria durante el calculo. La ventana permite seguir el progreso y cancelar
el trabajo. Si se cancela durante el movimiento, los archivos trasladados hasta
ese momento permanecen en el destino.

Al terminar, la aplicacion muestra la cantidad de imagenes analizadas, grupos
duplicados detectados, archivos movidos y errores encontrados. Los movimientos
realizados tambien se imprimen en la consola. Los archivos que no puedan
abrirse o moverse se registran como errores y el procesamiento continua con los
demas.

IMPORTANTE: esta herramienta modifica la ubicacion real de los archivos. Al
pulsar "Buscar y mover duplicados", los duplicados se trasladan inmediatamente
y no existe una funcion automatica para deshacer la operacion. Conviene revisar
cuidadosamente las carpetas elegidas y disponer de una copia de seguridad cuando
las imagenes sean importantes.

Dependencias:

- Python con Tkinter para la interfaz grafica.
- Pillow (PIL) para abrir las imagenes.
- imagehash para calcular los hashes perceptuales.

Si se inicia desde un entorno virtual, el script intenta relanzarse
automaticamente con el Python global asociado para utilizar las dependencias
instaladas en ese interprete.

Formatos contemplados: JPG, JPEG, PNG, BMP, GIF, TIFF, WEBP y AVIF. La
compatibilidad efectiva con algunos formatos depende de la version y
configuracion de Pillow instalada en el equipo.
"""

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Iterator
from tkinter import filedialog, messagebox, ttk


def relanzar_con_python_global() -> bool:
    """Relanza el script fuera del entorno virtual cuando sea posible."""
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False

    python_global = getattr(sys, "_base_executable", "")
    if not python_global or not os.path.isfile(python_global):
        return False

    if os.path.normcase(os.path.abspath(python_global)) == os.path.normcase(os.path.abspath(sys.executable)):
        return False

    comando = [python_global, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        subprocess.Popen(comando, cwd=os.getcwd(), env=os.environ.copy())
        return True
    except OSError:
        return False


try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    Image = None
    _pil_import_error = str(exc)

try:
    import imagehash
except Exception as exc:  # pragma: no cover
    imagehash = None
    _imagehash_import_error = str(exc)


EXTENSIONES_VALIDAS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp", ".avif")
NOMBRE_CARPETA_REPETIDAS = "0_IMAGENES_REPETIDAS"
TAMANO_LOTE_PREDETERMINADO = 100
MAX_ERRORES_DETALLE = 200

CallbackConteo = Callable[[int, int, str], None]
CallbackProgreso = Callable[[int, int, str], None]
CallbackCancelacion = Callable[[], bool]
CallbackEvento = Callable[[str, dict], None]


def obtener_valor_numerico(nombre: str) -> int:
    partes = "".join(filter(str.isdigit, nombre))
    return int(partes) if partes.isdigit() else 0


def rutas_iguales(ruta_a: str, ruta_b: str) -> bool:
    return os.path.normcase(os.path.abspath(ruta_a)) == os.path.normcase(
        os.path.abspath(ruta_b)
    )


def resolver_carpeta_destino(
    carpeta_fuente: str,
    carpeta_seleccionada: str = "",
) -> str:
    base = os.path.abspath(carpeta_seleccionada or carpeta_fuente)
    if os.path.basename(base).casefold() == NOMBRE_CARPETA_REPETIDAS.casefold():
        destino = base
    else:
        destino = os.path.join(base, NOMBRE_CARPETA_REPETIDAS)

    if rutas_iguales(destino, carpeta_fuente):
        raise ValueError("La carpeta destino no puede ser la misma que la fuente.")
    return destino


def excluir_destino(
    carpeta_actual: str,
    subcarpetas: list[str],
    carpeta_destino: str,
):
    subcarpetas[:] = [
        nombre
        for nombre in subcarpetas
        if not rutas_iguales(
            os.path.join(carpeta_actual, nombre),
            carpeta_destino,
        )
    ]


def iterar_imagenes(
    carpeta_fuente: str,
    carpeta_destino: str,
) -> Iterator[str]:
    """Entrega rutas de imagen una a una, sin cargar todo el arbol en memoria."""
    for root, carpetas, archivos in os.walk(carpeta_fuente):
        excluir_destino(root, carpetas, carpeta_destino)
        carpetas.sort(key=str.lower)
        for filename in sorted(archivos, key=str.lower):
            if not filename.lower().endswith(EXTENSIONES_VALIDAS):
                continue

            path = os.path.join(root, filename)
            if os.path.isfile(path):
                yield path


def iterar_lotes(rutas: Iterator[str], tamano_lote: int) -> Iterator[list[str]]:
    lote: list[str] = []
    for ruta in rutas:
        lote.append(ruta)
        if len(lote) >= tamano_lote:
            yield lote
            lote = []

    if lote:
        yield lote


def contar_imagenes(
    carpeta_fuente: str,
    carpeta_destino: str,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_progresar: CallbackConteo | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    total = 0
    carpetas_revisadas = 0
    ultima_ruta = carpeta_fuente

    for root, carpetas, archivos in os.walk(carpeta_fuente):
        excluir_destino(root, carpetas, carpeta_destino)
        if debe_cancelar is not None and debe_cancelar():
            return total, carpetas_revisadas, True

        carpetas.sort(key=str.lower)
        carpetas_revisadas += 1
        ultima_ruta = root

        for filename in archivos:
            if filename.lower().endswith(EXTENSIONES_VALIDAS):
                path = os.path.join(root, filename)
                if os.path.isfile(path):
                    total += 1

        if al_progresar is not None and carpetas_revisadas % tamano_lote == 0:
            al_progresar(total, carpetas_revisadas, root)

    if al_progresar is not None:
        al_progresar(total, carpetas_revisadas, ultima_ruta)

    return total, carpetas_revisadas, False


def construir_hash_dict(
    carpeta_fuente: str,
    carpeta_destino: str,
    total: int,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    if Image is None:
        raise RuntimeError(f"No se pudo importar Pillow (PIL). Detalle: {_pil_import_error}")
    if imagehash is None:
        raise RuntimeError(f"No se pudo importar imagehash. Detalle: {_imagehash_import_error}")

    hash_dict: dict[str, list[str]] = {}
    scanned = 0
    errors: list[tuple[str, str]] = []
    total_errors = 0
    cancelado = False

    rutas = iterar_imagenes(carpeta_fuente, carpeta_destino)
    for lote in iterar_lotes(rutas, tamano_lote):
        ultima_ruta = lote[-1]
        for path in lote:
            if debe_cancelar is not None and debe_cancelar():
                cancelado = True
                break

            scanned += 1
            try:
                with Image.open(path) as img:
                    hash_img = imagehash.phash(img)
                    key = str(hash_img)
                    hash_dict.setdefault(key, []).append(path)
            except Exception as exc:
                total_errors += 1
                if len(errors) < MAX_ERRORES_DETALLE:
                    errors.append((path, str(exc)))

        if al_progresar is not None:
            al_progresar(scanned, total, ultima_ruta)
        if cancelado:
            break

    return hash_dict, scanned, errors, total_errors, cancelado


def mover_duplicados(
    hash_dict: dict[str, list[str]],
    carpeta_destino: str,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    os.makedirs(carpeta_destino, exist_ok=True)

    moved = 0
    grupos = [paths for paths in hash_dict.values() if len(paths) > 1]
    dup_groups = len(grupos)
    total_duplicados = sum(len(paths) - 1 for paths in grupos)
    procesados = 0
    errors: list[tuple[str, str]] = []
    total_errors = 0
    cancelado = False

    for paths in grupos:
        # Mantener el de menor valor numerico en el nombre; mover el resto.
        paths.sort(key=lambda p: obtener_valor_numerico(os.path.basename(p)))

        for dup_path in paths[1:]:
            if debe_cancelar is not None and debe_cancelar():
                cancelado = True
                break

            try:
                nombre_archivo = os.path.basename(dup_path)
                destino = os.path.join(carpeta_destino, nombre_archivo)

                # Evitar conflictos de nombre en destino
                contador = 1
                while os.path.exists(destino):
                    nombre, ext = os.path.splitext(nombre_archivo)
                    nuevo_nombre = f"{nombre}_{contador}{ext}"
                    destino = os.path.join(carpeta_destino, nuevo_nombre)
                    contador += 1

                shutil.move(dup_path, destino)
                moved += 1
            except Exception as exc:
                total_errors += 1
                if len(errors) < MAX_ERRORES_DETALLE:
                    errors.append((dup_path, str(exc)))

            procesados += 1
            if al_progresar is not None and (
                procesados % tamano_lote == 0 or procesados == total_duplicados
            ):
                al_progresar(procesados, total_duplicados, dup_path)

        if cancelado:
            break

    return {
        "moved": moved,
        "groups": dup_groups,
        "errors": errors,
        "error_count": total_errors,
        "total_duplicates": total_duplicados,
        "cancelled": cancelado,
    }


def procesar_carpeta_por_lotes(
    carpeta_fuente: str,
    carpeta_destino: str,
    tamano_lote: int = TAMANO_LOTE_PREDETERMINADO,
    al_evento: CallbackEvento | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
):
    def emitir(tipo: str, **datos):
        if al_evento is not None:
            al_evento(tipo, datos)

    total, carpetas, cancelado = contar_imagenes(
        carpeta_fuente,
        carpeta_destino,
        tamano_lote=tamano_lote,
        al_progresar=lambda imagenes, revisadas, ruta: emitir(
            "conteo",
            imagenes=imagenes,
            carpetas=revisadas,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )

    resultado_base = {
        "total": total,
        "scanned": 0,
        "folders": carpetas,
        "groups": 0,
        "moved": 0,
        "errors": [],
        "error_count": 0,
        "cancelled": cancelado,
        "cancel_phase": "conteo" if cancelado else "",
        "destination": carpeta_destino,
    }
    if cancelado or total == 0:
        return resultado_base

    hash_dict, scanned, scan_errors, scan_error_count, cancelado = construir_hash_dict(
        carpeta_fuente,
        carpeta_destino,
        total,
        tamano_lote=tamano_lote,
        al_progresar=lambda procesadas, encontradas, ruta: emitir(
            "hash",
            procesadas=procesadas,
            total=encontradas,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )

    resultado_base.update(
        scanned=scanned,
        errors=scan_errors,
        error_count=scan_error_count,
        cancelled=cancelado,
        cancel_phase="hash" if cancelado else "",
    )
    if cancelado:
        return resultado_base

    movimiento = mover_duplicados(
        hash_dict,
        carpeta_destino,
        tamano_lote=tamano_lote,
        al_progresar=lambda procesados, duplicados, ruta: emitir(
            "movimiento",
            procesados=procesados,
            total=duplicados,
            ruta=ruta,
        ),
        debe_cancelar=debe_cancelar,
    )
    resultado_base.update(
        groups=movimiento["groups"],
        moved=movimiento["moved"],
        errors=scan_errors + movimiento["errors"],
        error_count=scan_error_count + movimiento["error_count"],
        cancelled=movimiento["cancelled"],
        cancel_phase="movimiento" if movimiento["cancelled"] else "",
    )

    return resultado_base


def main():
    root = tk.Tk()
    root.title("Mover imagenes repetidas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    # Carpeta fuente
    tk.Label(frame, text="Carpeta fuente:").grid(row=0, column=0, sticky="w")
    fuente_var = tk.StringVar()
    fuente_entry = tk.Entry(frame, textvariable=fuente_var, width=50)
    fuente_entry.grid(
        row=1, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_fuente():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta fuente")
        if carpeta:
            fuente_var.set(carpeta)
            if not destino_var.get().strip():
                destino_var.set(
                    os.path.join(carpeta, NOMBRE_CARPETA_REPETIDAS)
                )

    boton_fuente = tk.Button(frame, text="Examinar", command=seleccionar_fuente)
    boton_fuente.grid(row=1, column=2, pady=(4, 8))

    # Carpeta destino
    tk.Label(
        frame,
        text=f"Destino reservado ({NOMBRE_CARPETA_REPETIDAS}):",
    ).grid(row=2, column=0, sticky="w")
    destino_var = tk.StringVar()
    destino_entry = tk.Entry(frame, textvariable=destino_var, width=50)
    destino_entry.grid(
        row=3, column=0, columnspan=2, padx=(0, 6), pady=(4, 8), sticky="we"
    )

    def seleccionar_destino():
        carpeta = filedialog.askdirectory(
            title="Seleccionar destino reservado o carpeta contenedora"
        )
        if carpeta:
            destino_var.set(
                resolver_carpeta_destino(fuente_var.get().strip(), carpeta)
            )

    boton_destino = tk.Button(frame, text="Examinar", command=seleccionar_destino)
    boton_destino.grid(row=3, column=2, pady=(4, 8))

    tk.Label(frame, text="Imagenes por lote:").grid(row=4, column=0, sticky="w")
    lote_var = tk.StringVar(value=str(TAMANO_LOTE_PREDETERMINADO))
    lote_spinbox = tk.Spinbox(
        frame,
        from_=1,
        to=500,
        textvariable=lote_var,
        width=10,
    )
    lote_spinbox.grid(row=5, column=0, sticky="w", pady=(4, 8))

    nota = (
        "Procesa en segundo plano y por lotes. El destino puede estar dentro "
        "de la fuente porque se excluye del analisis. Si el campo queda vacio, "
        f"se creara {NOMBRE_CARPETA_REPETIDAS} dentro de la fuente."
    )
    tk.Label(frame, text=nota, justify="left", wraplength=460).grid(
        row=6,
        column=0,
        columnspan=3,
        sticky="w",
        pady=(0, 8),
    )

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=470,
        mode="determinate",
    )
    barra.grid(row=7, column=0, columnspan=3, sticky="we", pady=(0, 6))

    estado_var = tk.StringVar(value="Seleccione las carpetas para comenzar.")
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=500,
    ).grid(row=8, column=0, columnspan=3, sticky="we", pady=(0, 8))

    botones = tk.Frame(frame)
    botones.grid(row=9, column=0, columnspan=3, sticky="we")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)

    boton_ejecutar = tk.Button(botones, text="Buscar y mover duplicados")
    boton_ejecutar.grid(row=0, column=0, padx=(0, 4), sticky="we")

    cancelar_evento = threading.Event()
    mensajes: queue.Queue[tuple[str, object]] = queue.Queue()
    proceso_activo = False

    def solicitar_cancelacion():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        estado_var.set("Cancelando al terminar la imagen actual...")

    boton_cancelar = tk.Button(
        botones,
        text="Cancelar",
        state="disabled",
        command=solicitar_cancelacion,
    )
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="we")

    def configurar_controles(en_proceso: bool):
        estado = "disabled" if en_proceso else "normal"
        fuente_entry.config(state=estado)
        destino_entry.config(state=estado)
        lote_spinbox.config(state=estado)
        boton_fuente.config(state=estado)
        boton_destino.config(state=estado)
        boton_ejecutar.config(state=estado)
        boton_cancelar.config(state="normal" if en_proceso else "disabled")

    def poner_barra_determinada():
        if str(barra.cget("mode")) != "determinate":
            barra.stop()
            barra.config(mode="determinate")

    def resumir_errores(errores: list[tuple[str, str]], total: int, limite: int = 6) -> str:
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
        scanned = resultado["scanned"]
        moved = resultado["moved"]
        groups = resultado["groups"]
        total_errors = resultado["error_count"]

        if total == 0 and not resultado["cancelled"]:
            progreso_var.set(0)
            estado_var.set("No se encontraron imagenes compatibles.")
            messagebox.showinfo("Sin imagenes", "No se encontraron imagenes para procesar.")
            return

        resumen = (
            f"Carpetas revisadas: {resultado['folders']}\n"
            f"Imagenes encontradas: {total}\n"
            f"Imagenes analizadas: {scanned}\n"
            f"Grupos duplicados: {groups}\n"
            f"Archivos movidos: {moved}\n"
            f"Errores: {total_errors}\n"
            f"Destino: {resultado['destination']}"
        )

        if resultado["cancelled"]:
            estado_var.set("Proceso cancelado.")
            detalle = ""
            if resultado["cancel_phase"] == "movimiento" and moved:
                detalle = "\n\nLos archivos ya movidos permanecen en el destino."
            messagebox.showwarning("Proceso cancelado", resumen + detalle)
            return

        progreso_var.set(100)
        if total_errors:
            estado_var.set("Proceso completado con errores.")
            detalle = resumir_errores(resultado["errors"], total_errors)
            messagebox.showwarning(
                "Operacion completada con errores",
                f"{resumen}\n\n{detalle}",
            )
        elif groups == 0:
            estado_var.set("No se detectaron duplicados.")
            messagebox.showinfo("Sin duplicados", resumen)
        else:
            estado_var.set("Proceso completado.")
            messagebox.showinfo("Operacion completada", resumen)

    def manejar_evento(tipo: str, datos: dict):
        if tipo == "conteo":
            estado_var.set(
                f"Revisando carpetas: {datos['carpetas']}\n"
                f"Imagenes encontradas hasta ahora: {datos['imagenes']}"
            )
        elif tipo == "hash":
            poner_barra_determinada()
            total = datos["total"]
            progreso_var.set((datos["procesadas"] / total) * 100 if total else 0)
            estado_var.set(
                f"Calculando hashes: {datos['procesadas']} de {total}\n"
                f"{os.path.basename(datos['ruta'])}"
            )
        elif tipo == "movimiento":
            poner_barra_determinada()
            total = datos["total"]
            progreso_var.set((datos["procesados"] / total) * 100 if total else 100)
            estado_var.set(
                f"Moviendo duplicados: {datos['procesados']} de {total}\n"
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
                    estado_var.set("No se pudo completar el procesamiento.")
                    messagebox.showerror("Error", str(contenido))
        except queue.Empty:
            pass
        root.after(100, revisar_mensajes)

    def ejecutar():
        fuente = fuente_var.get().strip()
        destino = destino_var.get().strip()

        if not fuente:
            messagebox.showwarning("Falta fuente", "Seleccione una carpeta fuente.")
            return
        if not os.path.isdir(fuente):
            messagebox.showerror("Ruta invalida", "La carpeta fuente no existe.")
            return

        fuente_abs = os.path.abspath(fuente)
        try:
            destino_abs = resolver_carpeta_destino(fuente_abs, destino)
        except ValueError as exc:
            messagebox.showerror(
                "Destino invalido",
                str(exc),
            )
            return
        destino_var.set(destino_abs)

        try:
            tamano_lote = int(lote_var.get().strip())
            if not 1 <= tamano_lote <= 500:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Lote invalido",
                "El tamano del lote debe ser un entero entre 1 y 500.",
            )
            return

        confirmado = messagebox.askyesno(
            "Confirmar movimiento",
            (
                f"Los duplicados se moveran a:\n\n{destino_abs}\n\n"
                "Esta carpeta se excluira del analisis aunque este dentro "
                "de la carpeta fuente.\n\n"
                "Desea continuar?"
            ),
        )
        if not confirmado:
            return

        nonlocal proceso_activo
        proceso_activo = True
        cancelar_evento.clear()
        progreso_var.set(0)
        barra.config(mode="indeterminate")
        barra.start(12)
        configurar_controles(True)
        estado_var.set("Iniciando el conteo recursivo de imagenes...")

        def worker():
            try:
                resultado = procesar_carpeta_por_lotes(
                    fuente_abs,
                    destino_abs,
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

    def cerrar():
        if proceso_activo:
            cerrar_ahora = messagebox.askyesno(
                "Proceso en curso",
                "Hay un proceso activo. ¿Desea cancelarlo y cerrar la ventana?",
            )
            if not cerrar_ahora:
                return
            cancelar_evento.set()
        root.destroy()

    boton_ejecutar.config(command=ejecutar)
    root.protocol("WM_DELETE_WINDOW", cerrar)
    root.after(100, revisar_mensajes)
    fuente_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    if not relanzar_con_python_global():
        main()
