import os
import shutil
import stat
import tempfile
import threading
import tkinter as tk
import zipfile
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk
from typing import Callable


EXTENSIONES_IMAGEN = {
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
CARACTERES_INVALIDOS_WINDOWS = '<>:"/\\|?*'
NOMBRES_RESERVADOS_WINDOWS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{indice}" for indice in range(1, 10)),
    *(f"LPT{indice}" for indice in range(1, 10)),
}
LIMITE_INCIDENCIAS = 15

CallbackProgreso = Callable[[int, int, str], None]
CallbackCancelacion = Callable[[], bool]


@dataclass
class ArchivoZip:
    ruta: str
    imagenes: int


@dataclass
class Trabajo:
    imagenes: list[str] = field(default_factory=list)
    archivos_zip: list[ArchivoZip] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.imagenes) + sum(archivo.imagenes for archivo in self.archivos_zip)


@dataclass
class Resultado:
    carpetas_revisadas: int = 0
    imagenes_en_subcarpetas: int = 0
    archivos_zip: int = 0
    imagenes_en_zip: int = 0
    imagenes_movidas: int = 0
    imagenes_extraidas: int = 0
    nombres_ajustados: int = 0
    errores: int = 0
    cancelado: bool = False
    incidencias: list[str] = field(default_factory=list)

    def agregar_error(self, texto: str):
        self.errores += 1
        if len(self.incidencias) < LIMITE_INCIDENCIAS:
            self.incidencias.append(texto)


def es_imagen(nombre: str) -> bool:
    return os.path.splitext(nombre)[1].lower() in EXTENSIONES_IMAGEN


def es_miembro_regular(info: zipfile.ZipInfo) -> bool:
    if info.is_dir():
        return False

    tipo_unix = (info.external_attr >> 16) & 0o170000
    return tipo_unix != stat.S_IFLNK


def nombre_miembro_zip(info: zipfile.ZipInfo) -> str:
    nombre = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
    nombre = "".join(
        "_" if caracter in CARACTERES_INVALIDOS_WINDOWS or ord(caracter) < 32 else caracter
        for caracter in nombre
    )
    nombre = nombre.strip().rstrip(". ")
    base, extension = os.path.splitext(nombre)
    if base.upper() in NOMBRES_RESERVADOS_WINDOWS:
        nombre = f"_{base}{extension}"
    return nombre


def es_imagen_zip(info: zipfile.ZipInfo) -> bool:
    return es_miembro_regular(info) and es_imagen(nombre_miembro_zip(info))


def ruta_disponible(carpeta_destino: str, nombre_archivo: str) -> tuple[str, bool]:
    destino = os.path.join(carpeta_destino, nombre_archivo)
    if not os.path.lexists(destino):
        return destino, False

    base, extension = os.path.splitext(nombre_archivo)
    indice = 1
    while True:
        destino = os.path.join(carpeta_destino, f"{base}_{indice}{extension}")
        if not os.path.lexists(destino):
            return destino, True
        indice += 1


def ruta_normalizada(ruta: str) -> str:
    return os.path.normcase(os.path.abspath(ruta))


def rutas_iguales(ruta_a: str, ruta_b: str) -> bool:
    return ruta_normalizada(ruta_a) == ruta_normalizada(ruta_b)


def ruta_dentro_de(ruta: str, carpeta: str) -> bool:
    ruta_abs = ruta_normalizada(ruta)
    carpeta_abs = ruta_normalizada(carpeta)
    try:
        return os.path.commonpath([ruta_abs, carpeta_abs]) == carpeta_abs
    except ValueError:
        return False


def explorar(
    carpeta_raiz: str,
    resultado: Resultado,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
    carpeta_omitida: str | None = None,
) -> Trabajo:
    carpeta_raiz = os.path.abspath(carpeta_raiz)
    carpeta_omitida_abs = None
    if carpeta_omitida is not None and not rutas_iguales(carpeta_raiz, carpeta_omitida):
        carpeta_omitida_abs = ruta_normalizada(carpeta_omitida)
    trabajo = Trabajo()

    def registrar_error(error: OSError):
        ruta = error.filename or carpeta_raiz
        resultado.agregar_error(f"No se pudo explorar {ruta}: {error}")

    for directorio, subcarpetas, archivos in os.walk(
        carpeta_raiz,
        topdown=True,
        onerror=registrar_error,
        followlinks=False,
    ):
        if debe_cancelar is not None and debe_cancelar():
            resultado.cancelado = True
            break

        if carpeta_omitida_abs is not None:
            directorio_abs = ruta_normalizada(directorio)
            if directorio_abs == carpeta_omitida_abs:
                subcarpetas[:] = []
                continue
            subcarpetas[:] = [
                nombre
                for nombre in subcarpetas
                if ruta_normalizada(os.path.join(directorio, nombre))
                != carpeta_omitida_abs
            ]

        subcarpetas.sort(key=str.lower)
        archivos.sort(key=str.lower)
        resultado.carpetas_revisadas += 1

        for nombre in archivos:
            ruta = os.path.join(directorio, nombre)
            if os.path.islink(ruta):
                continue

            if directorio != carpeta_raiz and es_imagen(nombre):
                trabajo.imagenes.append(ruta)
                continue

            if os.path.splitext(nombre)[1].lower() != ".zip":
                continue

            try:
                with zipfile.ZipFile(ruta) as archivo_zip:
                    cantidad = sum(
                        1 for info in archivo_zip.infolist() if es_imagen_zip(info)
                    )
                trabajo.archivos_zip.append(ArchivoZip(ruta, cantidad))
            except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
                resultado.agregar_error(f"ZIP no legible {ruta}: {exc}")

        if al_progresar is not None and (
            resultado.carpetas_revisadas == 1
            or resultado.carpetas_revisadas % 25 == 0
        ):
            al_progresar(
                resultado.carpetas_revisadas,
                0,
                f"Explorando: {directorio}",
            )

    trabajo.imagenes.sort(key=str.lower)
    trabajo.archivos_zip.sort(key=lambda archivo: archivo.ruta.lower())
    resultado.imagenes_en_subcarpetas = len(trabajo.imagenes)
    resultado.archivos_zip = len(trabajo.archivos_zip)
    resultado.imagenes_en_zip = sum(
        archivo.imagenes for archivo in trabajo.archivos_zip
    )
    return trabajo


def mover_imagen(
    ruta_origen: str,
    carpeta_destino: str,
    resultado: Resultado,
):
    nombre = os.path.basename(ruta_origen)
    ruta_destino, ajustado = ruta_disponible(carpeta_destino, nombre)

    try:
        shutil.move(ruta_origen, ruta_destino)
        resultado.imagenes_movidas += 1
        if ajustado:
            resultado.nombres_ajustados += 1
    except (OSError, shutil.Error) as exc:
        resultado.agregar_error(f"No se pudo mover {ruta_origen}: {exc}")


def extraer_miembro_zip(
    archivo_zip: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    carpeta_destino: str,
    resultado: Resultado,
):
    nombre = nombre_miembro_zip(info)
    if not nombre:
        resultado.agregar_error(
            f"Nombre de imagen invalido en {archivo_zip.filename}: {info.filename}"
        )
        return

    ruta_destino, ajustado = ruta_disponible(carpeta_destino, nombre)
    descriptor, ruta_temporal = tempfile.mkstemp(
        prefix=".__extraer_zip_",
        suffix=os.path.splitext(nombre)[1],
        dir=carpeta_destino,
    )
    os.close(descriptor)

    try:
        with archivo_zip.open(info) as origen, open(ruta_temporal, "wb") as destino:
            shutil.copyfileobj(origen, destino, length=1024 * 1024)
        os.replace(ruta_temporal, ruta_destino)
        resultado.imagenes_extraidas += 1
        if ajustado:
            resultado.nombres_ajustados += 1
    except (
        OSError,
        EOFError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
    ) as exc:
        try:
            os.remove(ruta_temporal)
        except OSError:
            pass
        resultado.agregar_error(
            f"No se pudo extraer {info.filename} de {archivo_zip.filename}: {exc}"
        )


def ejecutar_trabajo(
    carpeta_destino: str,
    trabajo: Trabajo,
    resultado: Resultado,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
) -> Resultado:
    procesadas = 0
    total = trabajo.total

    for ruta in trabajo.imagenes:
        if debe_cancelar is not None and debe_cancelar():
            resultado.cancelado = True
            return resultado

        mover_imagen(ruta, carpeta_destino, resultado)
        procesadas += 1
        if al_progresar is not None:
            al_progresar(procesadas, total, ruta)

    for archivo in trabajo.archivos_zip:
        if debe_cancelar is not None and debe_cancelar():
            resultado.cancelado = True
            return resultado

        try:
            with zipfile.ZipFile(archivo.ruta) as contenido:
                for info in contenido.infolist():
                    if not es_imagen_zip(info):
                        continue
                    if debe_cancelar is not None and debe_cancelar():
                        resultado.cancelado = True
                        return resultado

                    extraer_miembro_zip(contenido, info, carpeta_destino, resultado)
                    procesadas += 1
                    if al_progresar is not None:
                        al_progresar(
                            procesadas,
                            total,
                            f"{archivo.ruta} -> {info.filename}",
                        )
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            resultado.agregar_error(
                f"No se pudo procesar el ZIP {archivo.ruta}: {exc}"
            )
            procesadas += archivo.imagenes
            if al_progresar is not None:
                al_progresar(procesadas, total, archivo.ruta)

    return resultado


def aplanar_imagenes(
    carpeta_raiz: str,
    carpeta_destino: str | None = None,
    al_progresar: CallbackProgreso | None = None,
    debe_cancelar: CallbackCancelacion | None = None,
) -> Resultado:
    carpeta_raiz = os.path.abspath(carpeta_raiz)
    carpeta_destino = os.path.abspath(carpeta_destino or carpeta_raiz)
    if not os.path.isdir(carpeta_destino):
        raise FileNotFoundError(f"La carpeta destino no existe: {carpeta_destino}")

    carpeta_omitida = None
    if not rutas_iguales(carpeta_raiz, carpeta_destino) and ruta_dentro_de(
        carpeta_destino,
        carpeta_raiz,
    ):
        carpeta_omitida = carpeta_destino

    resultado = Resultado()
    trabajo = explorar(
        carpeta_raiz,
        resultado,
        al_progresar=al_progresar,
        debe_cancelar=debe_cancelar,
        carpeta_omitida=carpeta_omitida,
    )
    if resultado.cancelado:
        return resultado

    return ejecutar_trabajo(
        carpeta_destino,
        trabajo,
        resultado,
        al_progresar=al_progresar,
        debe_cancelar=debe_cancelar,
    )


def crear_resumen(resultado: Resultado) -> str:
    lineas = [
        f"Carpetas revisadas: {resultado.carpetas_revisadas}",
        f"Imagenes encontradas en subcarpetas: {resultado.imagenes_en_subcarpetas}",
        f"Archivos ZIP encontrados: {resultado.archivos_zip}",
        f"Imagenes encontradas dentro de ZIP: {resultado.imagenes_en_zip}",
        f"Imagenes movidas: {resultado.imagenes_movidas}",
        f"Imagenes extraidas de ZIP: {resultado.imagenes_extraidas}",
        f"Nombres ajustados por coincidencia: {resultado.nombres_ajustados}",
        f"Errores: {resultado.errores}",
    ]

    if resultado.incidencias:
        lineas.append("")
        lineas.append("Primeras incidencias:")
        lineas.extend(f"- {incidencia}" for incidencia in resultado.incidencias)

    return "\n".join(lineas)


def main():
    root = tk.Tk()
    root.title("Mover y extraer imagenes")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=12)
    frame.pack()
    frame.columnconfigure(0, weight=1)

    ttk.Label(
        frame,
        text="Carpeta a revisar:",
    ).grid(row=0, column=0, columnspan=2, sticky="w")

    carpeta_var = tk.StringVar()
    entrada_origen = ttk.Entry(frame, textvariable=carpeta_var, width=66)
    entrada_origen.grid(row=1, column=0, padx=(0, 8), pady=(4, 10), sticky="ew")

    def seleccionar_carpeta_origen():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta a revisar")
        if carpeta:
            carpeta_var.set(carpeta)

    boton_examinar_origen = ttk.Button(
        frame,
        text="Examinar",
        command=seleccionar_carpeta_origen,
    )
    boton_examinar_origen.grid(row=1, column=1, pady=(4, 10), sticky="ew")

    ttk.Label(
        frame,
        text="Destino de las imagenes:",
    ).grid(row=2, column=0, columnspan=2, sticky="w")

    modo_destino_var = tk.StringVar(value="padre")
    carpeta_destino_var = tk.StringVar()

    def actualizar_modo_destino():
        estado = "normal" if modo_destino_var.get() == "personalizada" else "disabled"
        entrada_destino.config(state=estado)
        boton_examinar_destino.config(state=estado)

    radio_padre = ttk.Radiobutton(
        frame,
        text="Usar la carpeta revisada como carpeta padre",
        variable=modo_destino_var,
        value="padre",
        command=actualizar_modo_destino,
    )
    radio_padre.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

    radio_personalizada = ttk.Radiobutton(
        frame,
        text="Seleccionar otra carpeta destino",
        variable=modo_destino_var,
        value="personalizada",
        command=actualizar_modo_destino,
    )
    radio_personalizada.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))

    entrada_destino = ttk.Entry(frame, textvariable=carpeta_destino_var, width=66)
    entrada_destino.grid(row=5, column=0, padx=(0, 8), pady=(4, 10), sticky="ew")

    def seleccionar_carpeta_destino():
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta destino")
        if carpeta:
            carpeta_destino_var.set(carpeta)

    boton_examinar_destino = ttk.Button(
        frame,
        text="Examinar",
        command=seleccionar_carpeta_destino,
    )
    boton_examinar_destino.grid(row=5, column=1, pady=(4, 10), sticky="ew")
    actualizar_modo_destino()

    ttk.Label(
        frame,
        text=(
            "Se revisaran las subcarpetas de la carpeta origen.\n"
            "Las imagenes se moveran al destino elegido y tambien se extraeran alli los .zip.\n"
            "Las carpetas y los ZIP originales no se eliminan. No se sobrescriben archivos."
        ),
        justify="left",
    ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 10))

    progreso_var = tk.DoubleVar(value=0)
    progreso = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=530,
    )
    progreso.grid(row=7, column=0, columnspan=2, sticky="ew")

    estado_var = tk.StringVar(value="Seleccione la carpeta a revisar.")
    ttk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=550,
    ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 10))

    botones = ttk.Frame(frame)
    botones.grid(row=9, column=0, columnspan=2, sticky="ew")
    botones.columnconfigure(0, weight=1)
    botones.columnconfigure(1, weight=1)

    cancelar_evento = threading.Event()

    def configurar_controles(en_proceso: bool):
        estado = "disabled" if en_proceso else "normal"
        entrada_origen.config(state=estado)
        boton_examinar_origen.config(state=estado)
        radio_padre.config(state=estado)
        radio_personalizada.config(state=estado)
        if en_proceso:
            entrada_destino.config(state="disabled")
            boton_examinar_destino.config(state="disabled")
        else:
            actualizar_modo_destino()
        boton_ejecutar.config(state=estado)
        boton_cancelar.config(state="normal" if en_proceso else "disabled")

    def cancelar():
        cancelar_evento.set()
        boton_cancelar.config(state="disabled")
        estado_var.set("Cancelando al terminar el archivo actual...")

    def actualizar_progreso(procesadas: int, total: int, detalle: str):
        def actualizar():
            if total:
                progreso_var.set((procesadas / total) * 100)
                estado_var.set(
                    f"Procesando {procesadas} de {total}:\n{detalle}"
                )
            else:
                estado_var.set(detalle)

        root.after(0, actualizar)

    def finalizar(resultado: Resultado):
        configurar_controles(False)
        resumen = crear_resumen(resultado)

        if resultado.cancelado:
            estado_var.set("Proceso cancelado.")
            messagebox.showwarning("Proceso cancelado", resumen)
        elif resultado.errores:
            progreso_var.set(100)
            estado_var.set("Proceso terminado con incidencias.")
            messagebox.showwarning("Proceso terminado", resumen)
        else:
            progreso_var.set(100)
            estado_var.set("Todas las imagenes fueron procesadas.")
            messagebox.showinfo("Operacion completada", resumen)

    def finalizar_error(error: str):
        configurar_controles(False)
        estado_var.set("No se pudo completar el proceso.")
        messagebox.showerror("Error", error)

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta a revisar.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta a revisar no existe.")
            return

        destino = carpeta
        if modo_destino_var.get() == "personalizada":
            destino = carpeta_destino_var.get().strip()
            if not destino:
                messagebox.showwarning(
                    "Falta destino",
                    "Seleccione una carpeta destino.",
                )
                return
            if not os.path.isdir(destino):
                messagebox.showerror(
                    "Ruta invalida",
                    "La carpeta destino seleccionada no existe.",
                )
                return

        carpeta_abs = os.path.abspath(carpeta)
        destino_abs = os.path.abspath(destino)
        nota_destino = ""
        if not rutas_iguales(carpeta_abs, destino_abs) and ruta_dentro_de(
            destino_abs,
            carpeta_abs,
        ):
            nota_destino = (
                "\nLa carpeta destino esta dentro de la carpeta revisada; "
                "se omitira durante la exploracion."
            )

        confirmado = messagebox.askyesno(
            "Confirmar movimiento",
            (
                "Se revisaran las subcarpetas de:\n\n"
                f"{carpeta_abs}\n\n"
                "Las imagenes encontradas se moveran a:\n\n"
                f"{destino_abs}\n\n"
                "Tambien se extraeran las imagenes de los archivos .zip.\n"
                "Las coincidencias de nombre recibiran un sufijo numerico.\n"
                "Las carpetas y los ZIP no se eliminaran."
                f"{nota_destino}\n\n"
                "Desea continuar?"
            ),
        )
        if not confirmado:
            return

        cancelar_evento.clear()
        progreso_var.set(0)
        configurar_controles(True)
        estado_var.set("Explorando carpetas y archivos ZIP...")

        def worker():
            try:
                resultado = aplanar_imagenes(
                    carpeta,
                    carpeta_destino=destino,
                    al_progresar=actualizar_progreso,
                    debe_cancelar=cancelar_evento.is_set,
                )
                root.after(0, finalizar, resultado)
            except Exception as exc:
                root.after(0, finalizar_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    boton_ejecutar = ttk.Button(
        botones,
        text="Mover y extraer imagenes",
        command=ejecutar,
    )
    boton_ejecutar.grid(row=0, column=0, padx=(0, 4), sticky="ew")

    boton_cancelar = ttk.Button(
        botones,
        text="Cancelar",
        command=cancelar,
        state="disabled",
    )
    boton_cancelar.grid(row=0, column=1, padx=(4, 0), sticky="ew")

    entrada_origen.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
