"""Tema oscuro compartido y descripciones al pasar el mouse."""

import ctypes
import re
import sys
import tkinter as tk
from tkinter import ttk

FONDO = "#1b1e24"
SUPERFICIE = "#232830"
TARJETA = "#2b313b"
CAMPO = "#15181d"
BORDE = "#3a4150"
TEXTO = "#e7e9ee"
TENUE = "#9aa3b2"
ACENTO = "#7aa2f7"
ACENTO_ACTIVO = "#95b6ff"
TINTA = "#12141a"
AMBAR = "#e0b070"
AMBAR_ACTIVO = "#ecc890"
PELIGRO = "#e06c75"
PELIGRO_ACTIVO = "#ea8b93"
BOTON = "#323844"
BOTON_ACTIVO = "#3e4658"
FUENTE = ("Segoe UI", 11)
FUENTE_TITULO = ("Segoe UI", 20, "bold")

_INSTALADO = False

PRIMARIOS = {
    "renombrar",
    "convertir",
    "cortar",
    "extraer frames",
    "extraer imagenes",
    "extraer frames",
    "guardar primer frame",
    "buscar duplicados",
    "ordenar",
    "exportar tramo",
    "buscar y mover duplicados",
    "abrir visualizador",
    "procesar ahora",
    "iniciar monitoreo",
    "corregir nombres",
    "mover y extraer imagenes",
    "comparar",
    "buscar",
    "analizar",
    "iniciar / pausar",
    "convertir a mp3",
    "convertir a mp4",
    "copiar a carpeta",
}

SECUNDARIOS = {
    "examinar",
    "cancelar",
    "detener",
    "detectar",
    "anterior",
    "siguiente",
    "ir",
    "copiar rutas",
    "guardar txt",
}

AYUDAS = {
    "Examinar": "Abre un cuadro para elegir el archivo o la carpeta.",
    "Cancelar": "Detiene la operacion en curso.",
    "Detener": "Detiene el monitoreo. Lo ya renombrado se conserva.",
    "Detectar": "Busca FFmpeg en el sistema y rellena la ruta.",
    "Renombrar": "Aplica el modo, el prefijo, el sufijo y la marca de carpeta.",
    "Convertir": "Ejecuta la conversion con los datos de esta ventana.",
    "Cortar": "Recorta la imagen en mosaicos del tamano indicado.",
    "Extraer frames": "Guarda cada frame con el nombre del archivo de origen.",
    "Extraer imagenes": "Empieza la extraccion con el modo elegido.",
    "Guardar primer frame": "Guarda solo la primera imagen del video.",
    "Buscar duplicados": "Recorre la carpeta y agrupa imagenes parecidas.",
    "Buscar y mover duplicados": "Busca copias parecidas y las mueve a la carpeta destino.",
    "Abrir visualizador": "Abre las imagenes para revisarlas y copiarlas.",
    "Procesar ahora": "Agrupa de inmediato las imagenes nuevas de la carpeta.",
    "Iniciar monitoreo": "Vigila la carpeta y agrupa las imagenes que aparezcan.",
    "Corregir nombres": "Antepone a cada archivo el numero de la carpeta de capturas donde esta.",
    "Mover y extraer imagenes": "Junta las imagenes sueltas y las que estan dentro de ZIP.",
    "Comparar": "Compara la carpeta de referencia con la otra.",
    "Buscar": "Busca carpetas que no contienen ningun elemento.",
    "Analizar": "Recorre el video en busca de un frame parecido al primero.",
    "Iniciar / Pausar": "Empieza o pausa los clics automaticos.",
    "Convertir a MP3": "Extrae el audio del video y lo guarda como MP3.",
    "Convertir a MP4": "Crea un video con el audio y un fondo negro.",
    "Copiar a carpeta": "Copia la imagen visible a la carpeta alta o baja, segun su tamano.",
    "Copiar rutas": "Copia al portapapeles las rutas que se ven en la lista.",
    "Guardar TXT": "Guarda la lista de rutas en un archivo de texto.",
    "Mover todas": "Mueve todas las carpetas vacias encontradas a una carpeta que elijas.",
    "Eliminar todas": "Elimina todas las carpetas vacias de la lista. No se puede deshacer.",
    "Anterior": "Muestra el elemento anterior.",
    "Siguiente": "Muestra el elemento siguiente.",
    "Ir": "Salta a la imagen con el numero escrito.",
    "Solo primera": "Marca solo la primera imagen del grupo para conservarla.",
    "Todas": "Marca todas las imagenes del grupo para conservarlas.",
    "Ninguna": "Quita la marca de todas las imagenes del grupo.",
    "Invertir": "Invierte cuales imagenes del grupo estan marcadas.",
    "Mantener": "Conserva esta imagen. Las que no marques se pueden quitar del grupo.",
    "Numerico por fecha": "Ordena por la fecha interna y asigna 1, 2, 3...",
    "Alfabetico (a, b, c...)": "Ordena por fecha de modificacion y asigna a, b, c...",
    "Conservar nombre": "No cambia el nombre: solo agrega prefijo, sufijo o la carpeta.",
    "Numero de capturas": (
        "Antepone el numero de cada carpeta de capturas. "
        "No lo repite si el archivo ya empieza por ese numero."
    ),
    "Reemplazar texto": "Cambia un trozo del nombre. La extension se queda igual.",
    "Fuera de nomenclatura": "Busca nombres que no siguen la forma que usa la mayoria de esa carpeta.",
    "Ignorar mayusculas": "Encuentra el texto aunque no coincidan mayusculas y minusculas.",
    "Buscar:": "Texto que se quita o se cambia dentro del nombre.",
    "Reemplazar por:": "Texto que ocupa el lugar del buscado. Vacio: ese trozo se borra.",
    "Cursor": "Clic donde este el puntero en ese momento.",
    "Punto fijo": "Siempre el mismo pixel, aunque el puntero se mueva.",
    "Secuencia": "Recorre los puntos de la lista, uno por clic, y vuelve a empezar.",
    "Tecla": "Repite una tecla. Por ejemplo space, e o f5.",
    "Texto": "Escribe el mismo texto cada vez que pasa la espera.",
    "No usar": "El nombre de la carpeta no se agrega al archivo.",
    "Como prefijo": "Antepone el nombre de la carpeta: Carpeta_archivo.ext.",
    "Como sufijo": "Agrega el nombre de la carpeta al final: archivo_Carpeta.ext.",
    "Incluir subcarpetas (cada una usa su propio nombre)": (
        "Entra en cada subcarpeta y usa el nombre de esa carpeta, no el de la raiz."
    ),
    "Incluir subcarpetas": "Tambien procesa los videos que estan dentro de subcarpetas.",
    "Revisar subcarpetas (recursivo)": "Tambien abre las imagenes que estan en subcarpetas.",
    "Revisar subcarpetas": "La busqueda entra en las carpetas internas.",
    "Habilitar hotkey": "La tecla escrita funciona aunque esta ventana no este activa.",
    "Un video, cada N segundos": "De un solo video, guarda un frame cada ciertos segundos.",
    "Carpeta, cada N segundos": "Repite el intervalo en cada video de la carpeta.",
    "Carpeta, densidad segun duracion": "Calcula cuantas capturas tomar segun lo que dura cada video.",
    "Todos los frames": "Guarda cada frame decodificado, en orden.",
    "Solo el primer frame": "Guarda una sola imagen, la primera del video.",
    "Archivo": "Trabaja con un solo archivo.",
    "Carpeta": "Trabaja con todos los archivos compatibles de una carpeta.",
    "FFmpeg (archivo o carpeta)": "Usa FFmpeg. Sirve para un archivo o para una carpeta.",
    "MoviePy (un archivo)": "Usa MoviePy. Solo convierte un archivo de video.",
    "Usar la carpeta revisada como carpeta padre": "Las imagenes suben a la misma carpeta que elegiste revisar.",
    "Prefijo": "Texto que se pone delante del nombre. Vacio o solo espacios: no se agrega.",
    "Sufijo": "Texto que se pone antes de la extension. Vacio o solo espacios: no se agrega.",
    "Prefijo adicional:": "Se suma al nombre que la herramienta ya iba a usar. Vacio: no cambia nada.",
    "Sufijo adicional:": "Se agrega al final del nombre, antes de la extension. Vacio: no cambia nada.",
    "Carpeta:": "Carpeta sobre la que trabaja la herramienta.",
    "Carpeta a revisar:": "Carpeta de la que se sacan las imagenes y los ZIP.",
    "Carpeta fuente:": "Carpeta donde se buscan las imagenes parecidas.",
    "Carpeta original:": "Carpeta de referencia. Sus imagenes no se mueven.",
    "Carpeta raiz:": "Aqui empieza la busqueda de carpetas vacias.",
    "Carpeta a monitorear:": "Carpeta cuyas imagenes nuevas se agrupan.",
    "Carpeta origen:": "Carpeta con las imagenes que vas a revisar.",
    "Entrada:": "Archivo o carpeta de origen.",
    "Salida:": "Donde se guardan los archivos generados.",
    "Imagen:": "Imagen que se va a recortar o convertir.",
    "Video:": "Video que se va a analizar.",
    "Entrada video:": "Video del que se extrae el audio.",
    "Archivo de video:": "Video del que se extrae el audio.",
    "Salida MP3:": "Ruta del MP3 que se va a crear.",
    "Carpeta de guardado:": "Carpeta donde se guardan los MP3.",
    "Archivo MP3:": "Audio que se va a convertir en video.",
    "Guardar como MP4:": "Ruta del video que se va a crear.",
    "FFmpeg:": "Programa FFmpeg. Puedes detectarlo o elegirlo.",
    "Bitrate:": "Calidad del audio, por ejemplo 192k.",
    "Frecuencia:": "Frecuencia de muestreo, por ejemplo 44100.",
    "Resolucion:": "Tamano del video, por ejemplo 1280x720.",
    "FPS:": "Cuadros por segundo del GIF. Por ejemplo 12.",
    "Resize (w:h):": "Ancho:alto del GIF. 320:-1 calcula el alto y mantiene la proporcion.",
    "Tile (px):": "Lado de cada mosaico, en pixeles.",
    "Video codec:": "Codec de video. Por ejemplo copy, h264 o hevc.",
    "Audio codec:": "Codec de audio. Por ejemplo copy, aac o ac3.",
    "Delay (ms):": "Milisegundos entre un clic y el siguiente.",
    "Boton:": "Boton del mouse que se pulsa.",
    "Hotkey (global):": "Tecla que inicia o pausa los clics aunque esta ventana no este activa.",
    "Skip frames:": "Cuantos frames saltar antes de comparar.",
    "Threshold (MSE):": "Que tan parecidos deben ser dos frames para contar como bucle.",
    "Similitud mínima (%):": "De 0 a 100. Un valor alto solo agrupa imagenes casi iguales.",
    "Imagenes por lote:": "Cuantas imagenes se comparan a la vez.",
    "Umbral alto (px):": (
        "Si la altura de la imagen es menor que este numero, la copia va a la carpeta baja. "
        "Si llega o lo supera, va a la carpeta alta."
    ),
    "Destino (>= umbral) [vacío = 0_ALTO]:": (
        "Carpeta para las imagenes que alcanzan el umbral. Vacia: se crea 0_ALTO dentro del origen."
    ),
    "Destino (< umbral) [vacío = 0_BAJO]:": (
        "Carpeta para las imagenes mas bajas que el umbral. Vacia: se crea 0_BAJO dentro del origen."
    ),
    "Capturar un frame cada N segundos:": "Segundos entre capturas. Admite decimales, por ejemplo 0.5, 2.5 o 10.",
    "Tamanos:": "Resoluciones que se incluyen en el icono.",
    "Nombre de la carpeta:": "Puede anteponerse o agregarse al nombre de cada archivo.",
    "Destino de las imagenes:": "Elige si se usa la carpeta revisada u otra carpeta.",
}


def _clave_ayuda(etiqueta: str) -> str:
    limpia = etiqueta.strip()
    if limpia in AYUDAS:
        return AYUDAS[limpia]
    sin_puntos = limpia.rstrip(":").strip()
    if sin_puntos in AYUDAS:
        return AYUDAS[sin_puntos]
    if re.match(r"R\d+", sin_puntos):
        return f"{sin_puntos}. Cantidad de capturas para los videos de esta duracion."
    return ""


def ayuda_de(widget) -> str:
    """Texto de la descripcion asociada al control, o vacio."""
    fuente = getattr(widget, "_ayuda_fuente", None)
    if callable(fuente):
        try:
            return str(fuente() or "").strip()
        except tk.TclError:
            return ""
    if isinstance(fuente, str):
        return fuente
    return str(getattr(widget, "_ayuda", "") or "")


class _Ayuda:
    def __init__(self, widget, texto: str):
        self.widget = widget
        self._fuente = texto
        self.tip = None
        self._trabajo = None
        widget._ayuda_fuente = texto
        if not callable(texto):
            widget._ayuda = texto
        widget.bind("<Enter>", self._programar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<ButtonPress>", self._ocultar, add="+")
        widget.bind("<Destroy>", self._ocultar, add="+")

    def _programar(self, _evento=None):
        self._cancelar()
        try:
            self._trabajo = self.widget.after(420, self._mostrar)
        except tk.TclError:
            self._trabajo = None

    def _cancelar(self):
        if self._trabajo is not None:
            try:
                self.widget.after_cancel(self._trabajo)
            except tk.TclError:
                pass
            self._trabajo = None

    def _texto_actual(self) -> str:
        if callable(self._fuente):
            try:
                texto = str(self._fuente() or "").strip()
            except tk.TclError:
                texto = ""
            self.widget._ayuda = texto
            return texto
        return str(self._fuente or "")

    def _mostrar(self):
        self._trabajo = None
        texto = self._texto_actual()
        if self.tip is not None or not texto:
            return
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 8
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except tk.TclError:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        try:
            tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        marco = tk.Frame(tip, bg=BORDE, padx=1, pady=1)
        marco.pack()
        tk.Label(
            marco,
            text=texto,
            bg="#11141a",
            fg=TEXTO,
            font=("Segoe UI", 10),
            padx=12,
            pady=8,
            wraplength=340,
            justify="left",
        ).pack()
        tip.update_idletasks()
        ancho = tip.winfo_width()
        alto = tip.winfo_height()
        pantalla_ancho = tip.winfo_screenwidth()
        pantalla_alto = tip.winfo_screenheight()
        if x + ancho > pantalla_ancho - 8:
            x = max(8, pantalla_ancho - ancho - 8)
        if y + alto > pantalla_alto - 8:
            y = max(8, self.widget.winfo_rooty() - alto - 8)
        tip.wm_geometry(f"+{x}+{y}")
        self.tip = tip

    def _ocultar(self, _evento=None):
        self._cancelar()
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


def _texto(widget) -> str:
    try:
        return str(widget.cget("text") or "").strip()
    except tk.TclError:
        return ""


def _descripcion(widget, explicita: str | None = None) -> str:
    if explicita:
        return explicita.strip()
    texto = _texto(widget)
    if texto in AYUDAS:
        return AYUDAS[texto]
    if re.fullmatch(r"\d+x\d+", texto):
        return f"Incluye la resolucion {texto} en el archivo ICO."
    if isinstance(widget, (tk.Checkbutton, ttk.Checkbutton)) and texto:
        return f"Activa o desactiva: {texto}."
    if isinstance(widget, (tk.Radiobutton, ttk.Radiobutton)) and texto:
        return f"Elige esta forma de trabajar: {texto}."
    if isinstance(widget, (tk.Button, ttk.Button)) and texto:
        return f"Ejecuta esta accion: {texto}."
    return ""


def _asignar_ayuda(widget, explicita: str | None = None):
    if getattr(widget, "_ayuda", None):
        return
    texto = _descripcion(widget, explicita)
    if texto:
        _Ayuda(widget, texto)


def _estilo_boton_clasico(widget, explicito: bool):
    if explicito:
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        return
    texto = _texto(widget).lower()
    if not texto:
        return
    if texto.startswith("eliminar") or "🗑" in _texto(widget):
        normal, activo, tinta = PELIGRO, PELIGRO_ACTIVO, TINTA
    elif texto == "mover todas":
        normal, activo, tinta = AMBAR, AMBAR_ACTIVO, TINTA
    elif texto in PRIMARIOS or texto.startswith("abrir"):
        normal, activo, tinta = ACENTO, ACENTO_ACTIVO, TINTA
    else:
        normal, activo, tinta = BOTON, BOTON_ACTIVO, TEXTO
    widget.configure(
        bg=normal,
        fg=tinta,
        activebackground=activo,
        activeforeground=tinta,
        disabledforeground=TENUE,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        padx=18 if normal == ACENTO else 14,
        pady=9 if normal == ACENTO else 7,
        font=FUENTE,
    )
    widget._tema_normal = normal
    widget._tema_activo = activo

    def entrar(_evento, control=widget):
        if str(control.cget("state")) != "disabled":
            control.configure(bg=control._tema_activo)

    def salir(_evento, control=widget):
        if str(control.cget("state")) != "disabled":
            control.configure(bg=control._tema_normal)

    widget.bind("<Enter>", entrar, add="+")
    widget.bind("<Leave>", salir, add="+")


def _estilo_boton_ttk(widget, estilo_explicito: bool):
    if estilo_explicito:
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        return
    texto = _texto(widget).lower()
    if texto.startswith("eliminar"):
        estilo = "Danger.TButton"
    elif texto == "mover todas":
        estilo = "Caution.TButton"
    elif texto in PRIMARIOS or texto.startswith("abrir"):
        estilo = "Accent.TButton"
    else:
        estilo = "TButton"
    try:
        widget.configure(style=estilo, cursor="hand2")
    except tk.TclError:
        pass


_MOLDE_MARCA = (
    "................",
    "................",
    "................",
    "...........##...",
    "..........##....",
    ".........##.....",
    "..##....##......",
    "...##..##.......",
    "....####........",
    ".....##.........",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
)


def _lado_casilla(widget) -> int:
    try:
        escala = float(widget.tk.call("tk", "scaling"))
    except (tk.TclError, TypeError, ValueError):
        escala = 96 / 72
    return max(16, round(16 * escala / (96 / 72)))


def _dibujar_casilla(master, lado: int, marcada: bool) -> tk.PhotoImage:
    imagen = tk.PhotoImage(master=master, width=lado, height=lado)
    borde = ACENTO if marcada else "#8b93a7"
    relleno = ACENTO if marcada else CAMPO
    imagen.put(borde, to=(0, 0, lado, lado))
    if lado > 2:
        imagen.put(relleno, to=(1, 1, lado - 1, lado - 1))
    if not marcada:
        return imagen
    n = len(_MOLDE_MARCA)
    for y, fila in enumerate(_MOLDE_MARCA):
        for x, celda in enumerate(fila):
            if celda != "#":
                continue
            x0 = round(x * lado / n)
            y0 = round(y * lado / n)
            x1 = min(lado, max(x0 + 1, round((x + 1) * lado / n)))
            y1 = min(lado, max(y0 + 1, round((y + 1) * lado / n)))
            imagen.put(TINTA, to=(x0, y0, x1, y1))
    return imagen


def _dibujar_radio(master, lado: int, marcado: bool) -> tk.PhotoImage:
    imagen = tk.PhotoImage(master=master, width=lado, height=lado)
    centro = (lado - 1) / 2
    radio = lado / 2 - 0.6
    grosor = max(1.4, lado * 0.11)
    punto = lado * 0.26
    anillo = ACENTO if marcado else "#8b93a7"
    for y in range(lado):
        for x in range(lado):
            distancia = ((x - centro) ** 2 + (y - centro) ** 2) ** 0.5
            if marcado and distancia <= punto:
                imagen.put(ACENTO, to=(x, y, x + 1, y + 1))
            elif radio - grosor <= distancia <= radio:
                imagen.put(anillo, to=(x, y, x + 1, y + 1))
    return imagen


def _imagen_casilla(widget, marcada: bool) -> tk.PhotoImage:
    raiz = widget.winfo_toplevel()
    lado = _lado_casilla(widget)
    cache = getattr(raiz, "_casillas_tema", None)
    if cache is None:
        cache = {}
        raiz._casillas_tema = cache
    clave = (lado, marcada)
    imagen = cache.get(clave)
    if imagen is None:
        imagen = _dibujar_casilla(raiz, lado, marcada)
        cache[clave] = imagen
    return imagen


def _estilo_casilla(widget, explicito: bool):
    try:
        if widget.cget("image"):
            widget.configure(cursor="hand2")
            return
    except tk.TclError:
        return
    try:
        fondo = widget.cget("bg") if explicito else FONDO
        tinta = widget.cget("fg") if explicito else TEXTO
    except tk.TclError:
        fondo, tinta = FONDO, TEXTO
    apagada = _imagen_casilla(widget, False)
    encendida = _imagen_casilla(widget, True)
    widget.configure(
        indicatoron=False,
        image=apagada,
        selectimage=encendida,
        compound="left",
        selectcolor=fondo,
        bg=fondo,
        fg=tinta,
        activebackground=fondo,
        activeforeground=tinta,
        highlightthickness=0,
        bd=0,
        relief="flat",
        offrelief="flat",
        overrelief="flat",
        cursor="hand2",
        padx=2,
        pady=1,
    )
    widget._casilla_imagenes = (apagada, encendida)


def _imagen_radio(widget, marcado: bool) -> tk.PhotoImage:
    raiz = widget.winfo_toplevel()
    lado = _lado_casilla(widget)
    cache = getattr(raiz, "_radios_tema", None)
    if cache is None:
        cache = {}
        raiz._radios_tema = cache
    imagen = cache.get((lado, marcado))
    if imagen is None:
        imagen = _dibujar_radio(raiz, lado, marcado)
        cache[(lado, marcado)] = imagen
    return imagen


def _estilo_radio(widget, explicito: bool):
    try:
        if widget.cget("image"):
            widget.configure(cursor="hand2")
            return
    except tk.TclError:
        return
    try:
        fondo = widget.cget("bg") if explicito else FONDO
        tinta = widget.cget("fg") if explicito else TEXTO
    except tk.TclError:
        fondo, tinta = FONDO, TEXTO
    apagado = _imagen_radio(widget, False)
    encendido = _imagen_radio(widget, True)
    widget.configure(
        indicatoron=False,
        image=apagado,
        selectimage=encendido,
        compound="left",
        selectcolor=fondo,
        bg=fondo,
        fg=tinta,
        activebackground=fondo,
        activeforeground=tinta,
        highlightthickness=0,
        bd=0,
        relief="flat",
        offrelief="flat",
        overrelief="flat",
        cursor="hand2",
        padx=2,
        pady=1,
    )
    widget._radio_imagenes = (apagado, encendido)


def _parche_tk(clase, estilizar):
    original = clase.__init__

    def __init__(self, master=None, cnf=None, **kw):
        cnf = dict(cnf or {})
        ayuda = cnf.pop("ayuda", None)
        ayuda = kw.pop("ayuda", ayuda)
        explicito = any(clave in kw or clave in cnf for clave in ("bg", "background"))
        original(self, master, cnf, **kw)
        if estilizar is not None:
            estilizar(self, explicito)
        _asignar_ayuda(self, ayuda)

    clase.__init__ = __init__


def _parche_ttk(clase, estilizar=None):
    original = clase.__init__

    def __init__(self, master=None, **kw):
        ayuda = kw.pop("ayuda", None)
        estilo_explicito = "style" in kw
        original(self, master, **kw)
        if estilizar is not None:
            estilizar(self, estilo_explicito)
        _asignar_ayuda(self, ayuda)

    clase.__init__ = __init__


def _texto_etiqueta(etiqueta) -> str:
    texto = _texto(etiqueta)
    if texto:
        return texto
    try:
        variable = etiqueta.cget("textvariable")
    except tk.TclError:
        return ""
    if not variable:
        return ""
    try:
        return str(etiqueta.tk.globalgetvar(variable)).strip()
    except tk.TclError:
        return ""


def _etiqueta_cercana(entrada) -> str:
    try:
        info = entrada.grid_info()
    except tk.TclError:
        info = {}
    if info:
        fila = int(info.get("row", 0))
        columna = int(info.get("column", 0))
        for hermano in entrada.master.grid_slaves():
            if hermano is entrada or not isinstance(hermano, (tk.Label, ttk.Label)):
                continue
            try:
                otro = hermano.grid_info()
            except tk.TclError:
                continue
            misma_columna = int(otro.get("column", 0)) == columna and int(otro.get("row", -1)) == fila - 1
            misma_fila = int(otro.get("row", -1)) == fila and int(otro.get("column", -1)) == columna - 1
            if misma_columna or misma_fila:
                texto = _texto_etiqueta(hermano)
                if texto:
                    return texto
        return ""
    try:
        hermanos = list(entrada.master.pack_slaves())
    except tk.TclError:
        return ""
    if entrada not in hermanos:
        return ""
    indice = hermanos.index(entrada)
    for hermano in reversed(hermanos[:indice]):
        if isinstance(hermano, (tk.Label, ttk.Label)):
            texto = _texto_etiqueta(hermano)
            if texto:
                return texto
    return ""


def _texto_campo(widget) -> str:
    fija = getattr(widget, "_ayuda_fija", None)
    if fija:
        return str(fija).strip()
    etiqueta = _etiqueta_cercana(widget)
    conocida = _clave_ayuda(etiqueta)
    if conocida:
        return conocida
    if etiqueta:
        return f"{etiqueta.rstrip(':').strip()}. Escribe el valor o elige la ruta con Examinar."
    return "Escribe o pega el valor."


def _preparar_campo(widget, ayuda: str | None):
    if ayuda:
        widget._ayuda_fija = ayuda.strip()
    if getattr(widget, "_ayuda_fuente", None):
        return
    _Ayuda(widget, lambda control=widget: _texto_campo(control))


def _parche_campo_tk(clase):
    original = clase.__init__

    def __init__(self, master=None, cnf=None, **kw):
        cnf = dict(cnf or {})
        ayuda = cnf.pop("ayuda", None)
        ayuda = kw.pop("ayuda", ayuda)
        original(self, master, cnf, **kw)
        _preparar_campo(self, ayuda)

    clase.__init__ = __init__


def _parche_campo_ttk(clase):
    original = clase.__init__

    def __init__(self, master=None, **kw):
        ayuda = kw.pop("ayuda", None)
        original(self, master, **kw)
        _preparar_campo(self, ayuda)

    clase.__init__ = __init__


def _decorar_ventana(raiz):
    pendientes = [raiz]
    while pendientes:
        actual = pendientes.pop()
        try:
            hijos = actual.winfo_children()
        except tk.TclError:
            continue
        for hijo in hijos:
            pendientes.append(hijo)
            if getattr(hijo, "_ayuda", None) or getattr(hijo, "_ayuda_fuente", None):
                continue
            if isinstance(hijo, (tk.Entry, ttk.Entry, tk.Spinbox, ttk.Spinbox)):
                if not getattr(hijo, "_ayuda_fuente", None):
                    _Ayuda(hijo, lambda control=hijo: _texto_campo(control))
            elif isinstance(hijo, tk.Listbox):
                _Ayuda(hijo, "Resultados. Puedes seleccionar una o varias filas.")
            elif isinstance(hijo, ttk.Progressbar):
                _Ayuda(hijo, "Avance de la operacion en curso.")
            elif isinstance(hijo, (tk.OptionMenu, tk.Menubutton)):
                _asignar_ayuda(hijo)


def _opciones(raiz: tk.Tk):
    opciones = {
        "*Background": FONDO,
        "*Foreground": TEXTO,
        "*Font": "{Segoe UI} 11",
        "*insertBackground": TEXTO,
        "*selectBackground": ACENTO,
        "*selectForeground": TINTA,
        "*troughColor": CAMPO,
        "*highlightBackground": FONDO,
        "*highlightColor": ACENTO,
        "*highlightThickness": 1,
        "*Entry.Background": CAMPO,
        "*Entry.Foreground": TEXTO,
        "*Entry.relief": "flat",
        "*Entry.borderWidth": 0,
        "*Entry.highlightThickness": 1,
        "*Entry.highlightBackground": BORDE,
        "*Entry.highlightColor": ACENTO,
        "*Entry.insertBackground": TEXTO,
        "*Spinbox.Background": CAMPO,
        "*Spinbox.Foreground": TEXTO,
        "*Spinbox.buttonBackground": BOTON,
        "*Spinbox.insertBackground": TEXTO,
        "*Spinbox.readonlyBackground": CAMPO,
        "*Spinbox.selectBackground": ACENTO,
        "*Spinbox.selectForeground": TINTA,
        "*Spinbox.relief": "flat",
        "*Spinbox.highlightThickness": 1,
        "*Spinbox.highlightBackground": BORDE,
        "*Spinbox.highlightColor": ACENTO,
        "*Scale.Background": FONDO,
        "*Scale.Foreground": TEXTO,
        "*Scale.troughColor": CAMPO,
        "*Scale.activeBackground": ACENTO,
        "*Scale.highlightThickness": 0,
        "*Scale.sliderRelief": "flat",
        "*Text.Background": CAMPO,
        "*Text.Foreground": TEXTO,
        "*Text.insertBackground": TEXTO,
        "*Listbox.Background": CAMPO,
        "*Listbox.Foreground": TEXTO,
        "*Listbox.relief": "flat",
        "*Listbox.borderWidth": 0,
        "*Listbox.selectBackground": ACENTO,
        "*Listbox.selectForeground": TINTA,
        "*Checkbutton.Background": FONDO,
        "*Checkbutton.Foreground": TEXTO,
        "*Checkbutton.activeBackground": FONDO,
        "*Checkbutton.activeForeground": TEXTO,
        "*Checkbutton.selectColor": FONDO,
        "*Checkbutton.font": "{Segoe UI} 11",
        "*Checkbutton.cursor": "hand2",
        "*Radiobutton.Background": FONDO,
        "*Radiobutton.Foreground": TEXTO,
        "*Radiobutton.activeBackground": TARJETA,
        "*Radiobutton.activeForeground": TEXTO,
        "*Radiobutton.font": "{Segoe UI} 11",
        "*Radiobutton.cursor": "hand2",
        "*Label.Background": FONDO,
        "*Label.Foreground": TEXTO,
        "*Label.font": "{Segoe UI} 11",
        "*Frame.Background": FONDO,
        "*Canvas.Background": FONDO,
        "*Menubutton.Background": BOTON,
        "*Menubutton.Foreground": TEXTO,
        "*Menubutton.relief": "flat",
        "*Menubutton.highlightThickness": 0,
        "*Menubutton.font": "{Segoe UI} 11",
        "*Menu.Background": TARJETA,
        "*Menu.Foreground": TEXTO,
        "*Menu.activeBackground": ACENTO,
        "*Menu.activeForeground": TINTA,
        "*Menu.font": "{Segoe UI} 11",
        "*Button.font": "{Segoe UI} 11",
        "*Button.cursor": "hand2",
        "*Button.relief": "flat",
        "*Button.padX": 14,
        "*Button.padY": 7,
    }
    for patron, valor in opciones.items():
        raiz.option_add(patron, valor)


def _estilo_ttk():
    estilo = ttk.Style()
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    estilo.configure(".", background=FONDO, foreground=TEXTO, font=FUENTE)
    estilo.configure("TFrame", background=FONDO)
    estilo.configure("TLabel", background=FONDO, foreground=TEXTO, font=FUENTE)
    estilo.configure("Muted.TLabel", background=FONDO, foreground=TENUE, font=FUENTE)
    estilo.configure("Title.TLabel", background=FONDO, foreground=TEXTO, font=FUENTE_TITULO)
    estilo.configure(
        "TLabelframe",
        background=FONDO,
        foreground=TENUE,
        bordercolor=BORDE,
        lightcolor=BORDE,
        darkcolor=BORDE,
        relief="solid",
    )
    estilo.configure("TLabelframe.Label", background=FONDO, foreground=TEXTO, font=("Segoe UI", 12, "bold"))
    estilo.configure(
        "TButton",
        background=BOTON,
        foreground=TEXTO,
        font=FUENTE,
        padding=(14, 8),
        borderwidth=0,
        focusthickness=0,
        focuscolor=BOTON,
        relief="flat",
    )
    estilo.map(
        "TButton",
        background=[("disabled", SUPERFICIE), ("pressed", BOTON_ACTIVO), ("active", BOTON_ACTIVO)],
        foreground=[("disabled", TENUE)],
    )
    for nombre, fondo, activo in (
        ("Accent.TButton", ACENTO, ACENTO_ACTIVO),
        ("Caution.TButton", AMBAR, AMBAR_ACTIVO),
        ("Danger.TButton", PELIGRO, PELIGRO_ACTIVO),
    ):
        estilo.configure(
            nombre,
            background=fondo,
            foreground=TINTA,
            font=FUENTE,
            padding=(18, 10),
            borderwidth=0,
            focusthickness=0,
            focuscolor=fondo,
            relief="flat",
        )
        estilo.map(
            nombre,
            background=[("disabled", SUPERFICIE), ("pressed", activo), ("active", activo)],
            foreground=[("disabled", TENUE), ("!disabled", TINTA)],
        )
    estilo.configure(
        "TCheckbutton",
        background=FONDO,
        foreground=TEXTO,
        font=FUENTE,
        indicatormargin=8,
        indicatorsize=16,
    )
    estilo.map(
        "TCheckbutton",
        background=[("active", FONDO)],
        indicatorcolor=[("selected", ACENTO), ("!selected", CAMPO)],
        foreground=[("disabled", TENUE)],
    )
    estilo.configure("TRadiobutton", background=FONDO, foreground=TEXTO, font=FUENTE, indicatorsize=14)
    estilo.map(
        "TRadiobutton",
        background=[("active", FONDO)],
        indicatorcolor=[("selected", ACENTO), ("!selected", CAMPO)],
        foreground=[("disabled", TENUE)],
    )
    estilo.configure(
        "TEntry",
        fieldbackground=CAMPO,
        foreground=TEXTO,
        insertcolor=TEXTO,
        bordercolor=BORDE,
        lightcolor=BORDE,
        darkcolor=BORDE,
        padding=6,
    )
    estilo.map("TEntry", bordercolor=[("focus", ACENTO)])
    estilo.configure(
        "TSpinbox",
        fieldbackground=CAMPO,
        foreground=TEXTO,
        insertcolor=TEXTO,
        arrowcolor=TEXTO,
        background=BOTON,
        bordercolor=BORDE,
        lightcolor=BORDE,
        darkcolor=BORDE,
        padding=4,
    )
    estilo.configure(
        "TNotebook",
        background=FONDO,
        borderwidth=0,
        bordercolor=FONDO,
        lightcolor=FONDO,
        darkcolor=FONDO,
        tabmargins=(0, 0, 0, 0),
    )
    estilo.configure(
        "TNotebook.Tab",
        background=SUPERFICIE,
        foreground=TENUE,
        padding=(16, 8, 16, 8),
        font=FUENTE,
        borderwidth=0,
        bordercolor=SUPERFICIE,
        lightcolor=SUPERFICIE,
        darkcolor=SUPERFICIE,
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", TARJETA), ("active", BOTON)],
        lightcolor=[("selected", TARJETA), ("!selected", SUPERFICIE)],
        darkcolor=[("selected", TARJETA), ("!selected", SUPERFICIE)],
        bordercolor=[("selected", TARJETA), ("!selected", SUPERFICIE)],
        foreground=[("selected", TEXTO), ("active", TEXTO)],
        padding=[("selected", (16, 8, 16, 8)), ("!selected", (16, 8, 16, 8))],
        expand=[("selected", (0, 0, 0, 0))],
    )
    estilo.layout(
        "TNotebook.Tab",
        [
            (
                "Notebook.tab",
                {
                    "sticky": "nswe",
                    "children": [
                        (
                            "Notebook.padding",
                            {
                                "sticky": "nswe",
                                "children": [("Notebook.label", {"sticky": "nswe"})],
                            },
                        )
                    ],
                },
            )
        ],
    )
    estilo.configure(
        "TProgressbar",
        background=ACENTO,
        troughcolor=CAMPO,
        borderwidth=0,
        thickness=8,
        lightcolor=ACENTO,
        darkcolor=ACENTO,
    )
    for orientacion in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        estilo.configure(
            orientacion,
            background=BOTON,
            troughcolor=FONDO,
            bordercolor=FONDO,
            arrowcolor=TENUE,
            lightcolor=BOTON,
            darkcolor=BOTON,
            borderwidth=0,
            arrowsize=12,
        )
        estilo.map(orientacion, background=[("active", BOTON_ACTIVO)])
    estilo.configure("TSeparator", background=BORDE)


def _colorref(hexadecimal: str) -> int:
    rojo = int(hexadecimal[1:3], 16)
    verde = int(hexadecimal[3:5], 16)
    azul = int(hexadecimal[5:7], 16)
    return (azul << 16) | (verde << 8) | rojo


def _hwnd_marco(raiz: tk.Misc):
    if sys.platform != "win32":
        return None
    try:
        raiz.update_idletasks()
        ventana = int(raiz.winfo_id())
    except (tk.TclError, ValueError):
        return None
    usuario = ctypes.windll.user32
    usuario.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    usuario.GetAncestor.restype = ctypes.c_void_p
    hwnd = usuario.GetAncestor(ventana, 2)
    return hwnd or ventana


def aplicar_marco(raiz: tk.Misc) -> bool:
    """Pinta de negro la barra superior nativa de Windows."""
    hwnd = _hwnd_marco(raiz)
    if not hwnd:
        return False
    try:
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
    except (AttributeError, OSError):
        return False

    def atributo(codigo: int, valor: int) -> int:
        dato = ctypes.c_int(valor)
        return int(dwm.DwmSetWindowAttribute(hwnd, codigo, ctypes.byref(dato), ctypes.sizeof(dato)))

    oscuro = atributo(20, 1)
    if oscuro != 0:
        oscuro = atributo(19, 1)
    negro = _colorref("#000000")
    texto = _colorref(TEXTO)
    borde = atributo(34, negro)
    titulo = atributo(35, negro)
    atributo(36, texto)
    try:
        if raiz.winfo_viewable():
            usuario = ctypes.windll.user32
            usuario.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
            ]
            usuario.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
    except tk.TclError:
        pass
    return oscuro == 0 or borde == 0 or titulo == 0


def _marco_si_aplica(raiz: tk.Misc):
    try:
        if not raiz.winfo_exists() or raiz.overrideredirect():
            return
    except tk.TclError:
        return
    aplicar_marco(raiz)


def _programar_marco(raiz: tk.Misc):
    def aplicar(_evento=None, ventana=raiz):
        _marco_si_aplica(ventana)

    aplicar()
    try:
        raiz.bind("<Map>", aplicar, add="+")
        raiz.after(0, aplicar)
        raiz.after(80, aplicar)
    except tk.TclError:
        pass


def _configurar_raiz(raiz: tk.Tk):
    raiz.configure(bg=FONDO)
    _opciones(raiz)
    _estilo_ttk()
    _programar_marco(raiz)
    raiz.after_idle(lambda: _decorar_ventana(raiz))


def instalar():
    """Hace que cada ventana nueva use el tema oscuro."""
    global _INSTALADO
    if _INSTALADO:
        return
    _INSTALADO = True
    original = tk.Tk.__init__

    def __init__(self, *args, **kwargs):
        original(self, *args, **kwargs)
        _configurar_raiz(self)

    tk.Tk.__init__ = __init__
    toplevel = tk.Toplevel.__init__

    def toplevel_init(self, *args, **kwargs):
        toplevel(self, *args, **kwargs)
        self.after_idle(lambda ventana=self: _marco_si_aplica(ventana))
        self.bind("<Map>", lambda _evento, ventana=self: _marco_si_aplica(ventana), add="+")

    tk.Toplevel.__init__ = toplevel_init
    _parche_tk(tk.Button, _estilo_boton_clasico)
    _parche_tk(tk.Checkbutton, _estilo_casilla)
    _parche_tk(tk.Radiobutton, _estilo_radio)
    _parche_ttk(ttk.Button, _estilo_boton_ttk)
    _parche_ttk(ttk.Checkbutton)
    _parche_ttk(ttk.Radiobutton)
    _parche_campo_tk(tk.Entry)
    _parche_campo_tk(tk.Spinbox)
    _parche_campo_ttk(ttk.Entry)
    _parche_campo_ttk(ttk.Spinbox)


instalar()
