import os
import re
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import aplicacion.tema

from motores.renombrado import afijo, afijo_valido, nombre_con_afijos, nombre_con_numero_carpeta


PATRON_CARPETA = re.compile(r"^(\d+)_capturas$", re.IGNORECASE)
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
NUMERO_MINIMO = 1
NUMERO_MAXIMO = 1999
LIMITE_INCIDENCIAS = 12


@dataclass
class CarpetaCapturas:
    ruta: str
    prefijo: str


@dataclass
class Resultado:
    carpetas: int = 0
    imagenes: int = 0
    renombrados: int = 0
    ya_correctos: int = 0
    ignorados: int = 0
    conflictos: int = 0
    errores: int = 0
    incidencias: list[str] = field(default_factory=list)

    def agregar_incidencia(self, texto: str):
        if len(self.incidencias) < LIMITE_INCIDENCIAS:
            self.incidencias.append(texto)


def obtener_prefijo_carpeta(nombre_carpeta: str) -> str | None:
    coincidencia = PATRON_CARPETA.fullmatch(nombre_carpeta)
    if not coincidencia:
        return None

    numero = int(coincidencia.group(1))
    if not NUMERO_MINIMO <= numero <= NUMERO_MAXIMO:
        return None

    return str(numero)


def es_imagen(nombre_archivo: str) -> bool:
    return os.path.splitext(nombre_archivo)[1].lower() in EXTENSIONES_IMAGEN


def crear_nombre_destino(
    nombre_archivo: str,
    prefijo: str,
    prefijo_extra: str = "",
    sufijo_extra: str = "",
) -> str | None:
    corregido = nombre_con_numero_carpeta(nombre_archivo, prefijo) or nombre_archivo
    final = nombre_con_afijos(corregido, prefijo_extra, sufijo_extra)
    if final == nombre_archivo:
        return None
    return final


def encontrar_carpetas(carpeta_raiz: str, resultado: Resultado) -> list[CarpetaCapturas]:
    carpetas = []

    def registrar_error(error: OSError):
        resultado.errores += 1
        resultado.agregar_incidencia(f"Error al explorar: {error}")

    for directorio, _, _ in os.walk(carpeta_raiz, onerror=registrar_error):
        prefijo = obtener_prefijo_carpeta(os.path.basename(directorio))
        if prefijo is not None:
            carpetas.append(CarpetaCapturas(directorio, prefijo))

    carpetas.sort(key=lambda carpeta: (int(carpeta.prefijo), carpeta.ruta.lower()))
    return carpetas


def renombrar_carpeta(
    carpeta: CarpetaCapturas,
    resultado: Resultado,
    prefijo_extra: str = "",
    sufijo_extra: str = "",
):
    try:
        with os.scandir(carpeta.ruta) as iterador:
            entradas = sorted(iterador, key=lambda entrada: entrada.name.lower())
    except OSError as exc:
        resultado.errores += 1
        resultado.agregar_incidencia(
            f"{os.path.basename(carpeta.ruta)}: no se pudo abrir ({exc})"
        )
        return

    for entrada in entradas:
        try:
            if not entrada.is_file(follow_symlinks=False):
                continue
        except OSError as exc:
            resultado.errores += 1
            resultado.agregar_incidencia(f"{entrada.path}: {exc}")
            continue

        if not es_imagen(entrada.name):
            resultado.ignorados += 1
            continue

        resultado.imagenes += 1
        nombre_destino = crear_nombre_destino(
            entrada.name,
            carpeta.prefijo,
            prefijo_extra,
            sufijo_extra,
        )
        if nombre_destino is None:
            resultado.ya_correctos += 1
            continue

        ruta_destino = os.path.join(carpeta.ruta, nombre_destino)
        if os.path.lexists(ruta_destino):
            resultado.conflictos += 1
            resultado.agregar_incidencia(
                f"Conflicto: {entrada.name} -> {nombre_destino}"
            )
            continue

        try:
            os.rename(entrada.path, ruta_destino)
            resultado.renombrados += 1
        except OSError as exc:
            resultado.errores += 1
            resultado.agregar_incidencia(
                f"Error: {entrada.name} -> {nombre_destino} ({exc})"
            )


def corregir_nombres(
    carpeta_raiz: str,
    al_progresar: Callable[[int, int, str], None] | None = None,
    prefijo_extra: str = "",
    sufijo_extra: str = "",
) -> Resultado:
    prefijo_extra = afijo(prefijo_extra)
    sufijo_extra = afijo(sufijo_extra)
    resultado = Resultado()
    carpetas = encontrar_carpetas(carpeta_raiz, resultado)
    resultado.carpetas = len(carpetas)

    for indice, carpeta in enumerate(carpetas, start=1):
        if al_progresar is not None:
            al_progresar(indice, len(carpetas), carpeta.ruta)
        renombrar_carpeta(carpeta, resultado, prefijo_extra, sufijo_extra)

    return resultado


def crear_resumen(resultado: Resultado) -> str:
    lineas = [
        f"Carpetas encontradas: {resultado.carpetas}",
        f"Imagenes encontradas: {resultado.imagenes}",
        f"Archivos renombrados: {resultado.renombrados}",
        f"Ya tenian el prefijo correcto: {resultado.ya_correctos}",
        f"Archivos no imagen ignorados: {resultado.ignorados}",
        f"Conflictos sin modificar: {resultado.conflictos}",
        f"Errores: {resultado.errores}",
    ]

    if resultado.incidencias:
        lineas.append("")
        lineas.append("Primeras incidencias:")
        lineas.extend(f"- {incidencia}" for incidencia in resultado.incidencias)

    return "\n".join(lineas)


def main():
    root = tk.Tk()
    root.title("Corregir nombres de capturas")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()

    tk.Label(
        frame,
        text="Carpeta con las subcarpetas de capturas:",
    ).grid(row=0, column=0, columnspan=3, sticky="w")

    carpeta_var = tk.StringVar()
    entrada = tk.Entry(
        frame,
        textvariable=carpeta_var,
        width=62,
        ayuda=(
            "A cada archivo se le antepone el numero de la carpeta donde esta. "
            "Una imagen dentro de 27_capturas pasa a empezar por 27_."
        ),
    )
    entrada.grid(
        row=1,
        column=0,
        columnspan=2,
        padx=(0, 6),
        pady=(4, 8),
        sticky="we",
    )

    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory(
            title="Seleccionar carpeta con las subcarpetas de capturas"
        )
        if carpeta:
            carpeta_var.set(carpeta)

    tk.Button(frame, text="Examinar", command=seleccionar_carpeta).grid(
        row=1,
        column=2,
        pady=(4, 8),
    )

    tk.Label(frame, text="Prefijo adicional:").grid(row=3, column=0, sticky="w")
    tk.Label(frame, text="Sufijo adicional:").grid(row=3, column=1, sticky="w")
    prefijo_var = tk.StringVar()
    sufijo_var = tk.StringVar()
    tk.Entry(frame, textvariable=prefijo_var, width=24).grid(row=4, column=0, sticky="w", pady=(4, 8))
    tk.Entry(frame, textvariable=sufijo_var, width=24).grid(row=4, column=1, sticky="w", pady=(4, 8))

    progreso_var = tk.DoubleVar(value=0)
    barra = ttk.Progressbar(
        frame,
        variable=progreso_var,
        maximum=100,
        length=500,
    )
    barra.grid(row=6, column=0, columnspan=3, sticky="we", pady=(0, 6))

    estado_var = tk.StringVar(value="Seleccione la carpeta principal.")
    tk.Label(
        frame,
        textvariable=estado_var,
        justify="left",
        anchor="w",
        wraplength=520,
    ).grid(row=7, column=0, columnspan=3, sticky="we", pady=(0, 8))

    boton_renombrar = tk.Button(frame, text="Corregir nombres")
    boton_renombrar.grid(row=8, column=0, columnspan=3, sticky="we")

    def actualizar_progreso(indice: int, total: int, ruta: str):
        porcentaje = ((indice - 1) / total) * 100 if total else 0

        def actualizar():
            progreso_var.set(porcentaje)
            estado_var.set(
                f"Procesando carpeta {indice} de {total}:\n"
                f"{os.path.basename(ruta)}"
            )

        root.after(0, actualizar)

    def finalizar(resultado: Resultado):
        boton_renombrar.config(state="normal")
        progreso_var.set(100 if resultado.carpetas else 0)
        resumen = crear_resumen(resultado)

        if resultado.carpetas == 0:
            estado_var.set("No se encontraron carpetas con el formato N_capturas.")
            messagebox.showinfo("Sin carpetas compatibles", resumen)
        elif resultado.conflictos or resultado.errores:
            estado_var.set("Proceso terminado con incidencias.")
            messagebox.showwarning("Proceso terminado", resumen)
        else:
            estado_var.set("Todos los nombres fueron revisados correctamente.")
            messagebox.showinfo("Operacion completada", resumen)

    def finalizar_error(error: str):
        boton_renombrar.config(state="normal")
        estado_var.set("No se pudo completar el proceso.")
        messagebox.showerror("Error", error)

    def ejecutar():
        carpeta = carpeta_var.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta carpeta", "Seleccione una carpeta.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror("Ruta invalida", "La carpeta seleccionada no existe.")
            return

        prefijo_extra = afijo(prefijo_var.get())
        sufijo_extra = afijo(sufijo_var.get())
        if not afijo_valido(prefijo_extra) or not afijo_valido(sufijo_extra):
            messagebox.showerror(
                "Nombre invalido",
                "El prefijo o el sufijo contiene caracteres no permitidos en un nombre de archivo.",
            )
            return

        confirmar = messagebox.askyesno(
            "Confirmar renombrado",
            (
                "Se buscaran carpetas llamadas N_capturas, desde "
                f"{NUMERO_MINIMO}_capturas hasta {NUMERO_MAXIMO}_capturas.\n\n"
                "A cada imagen se le antepondra el numero de su carpeta.\n"
                "Los archivos existentes nunca se sobrescribiran.\n\n"
                "Desea continuar?"
            ),
        )
        if not confirmar:
            return

        boton_renombrar.config(state="disabled")
        progreso_var.set(0)
        estado_var.set("Buscando carpetas compatibles...")

        def worker():
            try:
                resultado = corregir_nombres(
                    carpeta,
                    actualizar_progreso,
                    prefijo_extra,
                    sufijo_extra,
                )
                root.after(0, finalizar, resultado)
            except Exception as exc:
                root.after(0, finalizar_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    boton_renombrar.config(command=ejecutar)
    entrada.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
