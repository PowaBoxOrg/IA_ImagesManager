import os
import subprocess
import sys
import tempfile
import unittest

from motores.archivos import ruta_dentro_de, ruta_disponible, rutas_iguales
from motores.imagenes import distancia_visual, similitud_visual
from motores.lotes import AccionLote, buscar_archivos, ejecutar_accion_lote
from motores.renombrado import (
    CambioNombre,
    afijo,
    afijo_valido,
    afijos_con_carpeta,
    aplicar_plan,
    indice_nombre,
    nombre_con_afijos,
    nombre_multimedia,
    nombre_pieza,
    nombre_seguro,
    validar_plan,
)
from aplicacion.catalogo import HERRAMIENTAS, SECCIONES


class MotoresTest(unittest.TestCase):
    def test_catalogo_apunta_a_scripts_existentes(self):
        raiz = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(SECCIONES)
        self.assertEqual(SECCIONES, ("Imagenes", "Multimedia", "Archivos"))
        vistos = set()
        for herramienta in HERRAMIENTAS:
            self.assertTrue(os.path.isfile(os.path.join(raiz, herramienta.script)), herramienta.script)
            self.assertEqual(len(herramienta.secciones), 1)
            self.assertTrue(set(herramienta.secciones).issubset(SECCIONES))
            self.assertNotIn(herramienta.script, vistos)
            vistos.add(herramienta.script)

    def test_lotes_filtran_extension_y_reportan_error(self):
        with tempfile.TemporaryDirectory() as carpeta:
            jpg = os.path.join(carpeta, "b.JPG")
            png = os.path.join(carpeta, "a.png")
            txt = os.path.join(carpeta, "c.txt")
            for ruta in (jpg, png, txt):
                open(ruta, "w", encoding="utf-8").close()
            self.assertEqual(buscar_archivos(carpeta, ("png", ".jpg")), [png, jpg])
            accion = AccionLote("prueba", (".png",), lambda ruta: os.path.basename(ruta))
            resultado = ejecutar_accion_lote(accion, [png])
            self.assertEqual(resultado.procesados, 1)
            self.assertEqual(resultado.resultados[0][1], "a.png")

    def test_rutas_y_nombre_disponible(self):
        with tempfile.TemporaryDirectory() as carpeta:
            existente = os.path.join(carpeta, "foto.png")
            open(existente, "w", encoding="utf-8").close()
            self.assertTrue(rutas_iguales(existente, existente))
            self.assertTrue(ruta_dentro_de(existente, carpeta))
            self.assertEqual(ruta_disponible(carpeta, "foto.png"), os.path.join(carpeta, "foto_1.png"))

    def test_similitud_visual(self):
        negro = bytes([0, 0, 0, 0])
        blanco = bytes([255, 255, 255, 255])
        self.assertEqual(distancia_visual(negro, blanco), 1020)
        self.assertEqual(similitud_visual(negro, negro), 100.0)
        self.assertEqual(similitud_visual(negro, blanco), 0.0)

    def test_plan_renombrado_intercambia_sin_colision(self):
        with tempfile.TemporaryDirectory() as carpeta:
            a = os.path.join(carpeta, "a.txt")
            b = os.path.join(carpeta, "b.txt")
            with open(a, "w", encoding="utf-8") as archivo:
                archivo.write("A")
            with open(b, "w", encoding="utf-8") as archivo:
                archivo.write("B")
            cambios = [CambioNombre(a, b), CambioNombre(b, a)]
            validar_plan(cambios)
            self.assertEqual(aplicar_plan(cambios), 2)
            with open(a, encoding="utf-8") as archivo:
                self.assertEqual(archivo.read(), "B")
            with open(b, encoding="utf-8") as archivo:
                self.assertEqual(archivo.read(), "A")

    def test_afijo_vacio_conserva_el_nombre_generado(self):
        from CorregirNombresCapturas import crear_nombre_destino
        from RenombradorAlfabetico import renombrar_por_alfabeto
        from RenombradorNumerico import renombrar_por_fecha_origen

        self.assertEqual(afijo("   "), "")
        self.assertEqual(nombre_con_afijos("a.jpg", " \t", " "), "a.jpg")
        self.assertEqual(nombre_con_afijos("a.jpg", "pre_", "_x"), "pre_a_x.jpg")
        self.assertFalse(afijo_valido("a/b"))
        self.assertEqual(crear_nombre_destino("captura.jpg", "27", " ", " "), "27_captura.jpg")
        self.assertEqual(crear_nombre_destino("5_captura_0001.jpg", "27"), "27_captura_0001.jpg")
        self.assertIsNone(crear_nombre_destino("27_captura.jpg", "27"))
        self.assertIsNone(crear_nombre_destino("27_capturas_a.jpg", "27"))
        self.assertEqual(
            crear_nombre_destino("27_captura.jpg", "27", "pre_", "_x"),
            "pre_27_captura_x.jpg",
        )

        with tempfile.TemporaryDirectory() as carpeta:
            for nombre in ("b.txt", "a.txt"):
                open(os.path.join(carpeta, nombre), "w", encoding="utf-8").close()
            renombrar_por_fecha_origen(carpeta, "  ", 1, " ")
            self.assertEqual(sorted(os.listdir(carpeta)), ["1.txt", "2.txt"])

        with tempfile.TemporaryDirectory() as carpeta:
            open(os.path.join(carpeta, "z.txt"), "w", encoding="utf-8").close()
            renombrar_por_alfabeto(carpeta, "pre_", "_ok")
            self.assertEqual(os.listdir(carpeta), ["pre_a_ok.txt"])
            _total, omitido = renombrar_por_alfabeto(carpeta, "pre_", "_ok")
            self.assertTrue(omitido)
            self.assertEqual(os.listdir(carpeta), ["pre_a_ok.txt"])

    def test_nombres_compartidos_y_marca_de_carpeta(self):
        from RenombradorNumerico import directorios_objetivo, renombrar_conservando, renombrar_por_fecha_origen

        self.assertEqual(nombre_seguro("a:b"), "a_b")
        self.assertEqual(nombre_seguro("CON"), "_CON")
        self.assertEqual(indice_nombre(1, "jpg"), "jpg_000001")
        self.assertEqual(
            nombre_multimedia("Mi Video.mp4", "captura", 1, ".jpg"),
            "Mi Video_captura_000001.jpg",
        )
        self.assertEqual(nombre_pieza(r"C:\fotos\icono.png", "icon", 0, 1), "icono_icon_00_01.png")
        self.assertEqual(afijos_con_carpeta(r"C:\clips\videoA", "no", "pre_", "_x"), ("pre_", "_x"))
        self.assertEqual(
            afijos_con_carpeta(r"C:\clips\videoA", "prefijo", "pre_", "_x"),
            ("videoA_pre_", "_x"),
        )
        self.assertEqual(afijos_con_carpeta(r"C:\clips\videoA", "sufijo"), ("", "_videoA"))

        with tempfile.TemporaryDirectory() as raiz:
            for video in ("videoA", "videoB"):
                carpeta = os.path.join(raiz, video)
                os.makedirs(carpeta)
                for nombre in ("captura0001.png", "captura0002.png"):
                    open(os.path.join(carpeta, nombre), "w", encoding="utf-8").close()
            for directorio in directorios_objetivo(raiz, True):
                prefijo, sufijo = afijos_con_carpeta(directorio, "prefijo")
                renombrar_conservando(directorio, prefijo, sufijo)
            self.assertEqual(
                sorted(os.listdir(os.path.join(raiz, "videoA"))),
                ["videoA_captura0001.png", "videoA_captura0002.png"],
            )
            self.assertEqual(
                sorted(os.listdir(os.path.join(raiz, "videoB"))),
                ["videoB_captura0001.png", "videoB_captura0002.png"],
            )
            for directorio in directorios_objetivo(raiz, True):
                prefijo, sufijo = afijos_con_carpeta(directorio, "prefijo")
                _cantidad, omitido = renombrar_conservando(directorio, prefijo, sufijo)
                self.assertTrue(omitido)

        with tempfile.TemporaryDirectory() as raiz:
            carpeta = os.path.join(raiz, "videoA")
            os.makedirs(carpeta)
            open(os.path.join(carpeta, "captura0001.png"), "w", encoding="utf-8").close()
            prefijo, sufijo = afijos_con_carpeta(carpeta, "sufijo", "pre_")
            renombrar_conservando(carpeta, prefijo, sufijo)
            self.assertEqual(os.listdir(carpeta), ["pre_captura0001_videoA.png"])

        with tempfile.TemporaryDirectory() as raiz:
            carpeta = os.path.join(raiz, "videoA")
            os.makedirs(carpeta)
            open(os.path.join(carpeta, "z.txt"), "w", encoding="utf-8").close()
            prefijo, sufijo = afijos_con_carpeta(carpeta, "prefijo")
            renombrar_por_fecha_origen(carpeta, prefijo, 1, sufijo)
            self.assertEqual(os.listdir(carpeta), ["videoA_1.txt"])

    def test_catalogo_ofrece_las_funciones_absorbidas(self):
        raiz = os.path.dirname(os.path.dirname(__file__))
        por_script = {herramienta.script: herramienta for herramienta in HERRAMIENTAS}
        for conservado in (
            "MP4_a_Imagenes.py",
            "CapturadorAutomatico.py",
            "Video_a_Frames.py",
            "RenombradorAlfabetico.py",
            "mkv2mp3.py",
            "CorregirNombresCapturas.py",
            "MP4_a_MP3.py",
            "MP4_MKV.py",
            "mp4_a_gif_ffmpeg.py",
            "mp4tomp3.py",
        ):
            self.assertNotIn(conservado, por_script)
            self.assertTrue(os.path.isfile(os.path.join(raiz, conservado)), conservado)

        video = por_script["MP4_a_Imagenes_Carpeta.py"]
        self.assertEqual(
            [opcion.argumentos for opcion in video.opciones],
            [
                ("--modo", "archivo"),
                ("--modo", "carpeta"),
                ("--modo", "automatico"),
                ("--modo", "frames"),
                ("--modo", "primer-frame"),
            ],
        )
        self.assertEqual(
            [opcion.argumentos for opcion in por_script["RenombradorNumerico.py"].opciones],
            [
                ("--modo", "numerico"),
                ("--modo", "alfabetico"),
                ("--modo", "conservar"),
                ("--modo", "capturas"),
                ("--modo", "reemplazar"),
                ("--modo", "nomenclatura"),
            ],
        )
        self.assertIn("ConvertidorFormato.py", por_script)
        self.assertEqual(por_script["ConvertidorFormato.py"].opciones, ())

    def test_modos_de_extraccion_y_renombrado(self):
        from MP4_a_Imagenes_Carpeta import interpretar_modo
        from RenombradorNumerico import modo_valido
        from ConvertidorFormato import salidas_de
        from MP4_a_MP3 import motor_audio

        self.assertEqual(interpretar_modo(["--modo", "frames"]), "frames")
        self.assertEqual(interpretar_modo(["--automatico"]), "automatico")
        self.assertEqual(interpretar_modo(automatico=True), "automatico")
        self.assertEqual(interpretar_modo(["--modo", "desconocido"]), "carpeta")
        self.assertEqual(modo_valido("alfabetico"), "alfabetico")
        self.assertEqual(modo_valido("conservar"), "conservar")
        self.assertEqual(modo_valido("capturas"), "capturas")
        self.assertEqual(modo_valido("reemplazar"), "reemplazar")
        self.assertEqual(modo_valido("nomenclatura"), "nomenclatura")
        self.assertEqual(modo_valido("otro"), "numerico")
        self.assertEqual(motor_audio("moviepy"), "moviepy")
        self.assertEqual(motor_audio("otro"), "ffmpeg")
        self.assertEqual(salidas_de("mp4"), ("mp3", "mkv", "gif"))
        self.assertEqual(salidas_de("mkv"), ("mp3",))
        self.assertEqual(salidas_de("mp3"), ("mp4",))
        self.assertEqual(salidas_de("avi"), ("mp3",))

    def test_nomenclatura_reemplazo_duplicados_y_carpetas(self):
        from EncontrarCarpetasVacias import encontrar_carpetas_vacias, eliminar_carpetas_vacias
        from Otros.Autoclicker import leer_secuencia
        from encontrar_loop import punto_de_corte
        from motores.clasificar import categoria_de
        from motores.duplicados import grupos_exactos
        from motores.renombrado import clasificar_nomenclatura, reemplazar_en_nombre

        patron, comunes, fuera = clasificar_nomenclatura(
            ["132.png", "138.png", "139.png", "132ds23f23ef.webp"]
        )
        self.assertEqual(patron, "#.png")
        self.assertEqual(comunes, ["132.png", "138.png", "139.png"])
        self.assertEqual(fuera, ["132ds23f23ef.webp"])
        self.assertEqual(clasificar_nomenclatura(["a.png", "b.png", "1.jpg", "2.jpg"])[0], "")
        self.assertIsNone(reemplazar_en_nombre("132.png", "ds", ""))
        self.assertEqual(reemplazar_en_nombre("132ds23.png", "ds23", ""), "132.png")
        self.assertEqual(reemplazar_en_nombre("Foto.PNG", "foto", "img", True), "img.PNG")

        self.assertEqual(punto_de_corte({"candidates": [(40, 1.0), (10, 2.0)], "best_frame": 40}), 10)
        self.assertEqual(punto_de_corte({"candidates": [], "best_frame": 8}), 8)
        self.assertEqual(punto_de_corte({"candidates": [], "best_frame": -1}), -1)
        self.assertEqual(leer_secuencia("120, 340\n10 20\n"), [(120, 340), (10, 20)])
        self.assertEqual(categoria_de("clip.MP4"), "Video")
        self.assertEqual(categoria_de("nota.txt"), "Otros")

        with tempfile.TemporaryDirectory() as carpeta:
            iguales_a = os.path.join(carpeta, "a.bin")
            iguales_b = os.path.join(carpeta, "b.bin")
            distinto = os.path.join(carpeta, "c.bin")
            for ruta, contenido in ((iguales_a, b"mismo"), (iguales_b, b"mismo"), (distinto, b"otro")):
                with open(ruta, "wb") as archivo:
                    archivo.write(contenido)
            grupos, errores = grupos_exactos([iguales_a, iguales_b, distinto])
            self.assertEqual(errores, [])
            self.assertEqual(len(grupos), 1)
            self.assertEqual(set(grupos[0]), {iguales_a, iguales_b})

            vacia = os.path.join(carpeta, "vacia")
            solo_sistema = os.path.join(carpeta, "solo_sistema")
            con_archivo = os.path.join(carpeta, "con_archivo")
            os.makedirs(vacia)
            os.makedirs(solo_sistema)
            os.makedirs(con_archivo)
            open(os.path.join(solo_sistema, "Thumbs.db"), "wb").close()
            open(os.path.join(con_archivo, "desktop.ini"), "wb").close()
            open(os.path.join(con_archivo, "nota.txt"), "w", encoding="utf-8").close()
            halladas = encontrar_carpetas_vacias(carpeta)["empty_folders"]
            self.assertIn(os.path.abspath(vacia), halladas)
            self.assertIn(os.path.abspath(solo_sistema), halladas)
            self.assertNotIn(os.path.abspath(con_archivo), halladas)
            eliminadas = eliminar_carpetas_vacias([os.path.abspath(solo_sistema)], carpeta)["processed"]
            self.assertEqual(eliminadas, [os.path.abspath(solo_sistema)])
            self.assertFalse(os.path.isdir(solo_sistema))

    def test_cli_de_frames_sigue_disponible(self):
        raiz = os.path.dirname(os.path.dirname(__file__))
        resultado = subprocess.run(
            [sys.executable, os.path.join(raiz, "Video_a_Frames.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("--solo-primer-frame", resultado.stdout)

    def test_tema_oscuro_y_descripciones(self):
        import tkinter as tk

        from tkinter import ttk

        from aplicacion.tema import ACENTO, AYUDAS, BOTON, CAMPO, FONDO, aplicar_marco, ayuda_de

        raiz = tk.Tk()
        raiz.withdraw()
        try:
            self.assertEqual(raiz.cget("bg"), FONDO)
            self.assertTrue(aplicar_marco(raiz))
            examinar = tk.Button(raiz, text="Examinar")
            renombrar = tk.Button(raiz, text="Renombrar")
            estado = tk.BooleanVar(raiz, value=False)
            casilla = tk.Checkbutton(raiz, text="Incluir subcarpetas", variable=estado)
            self.assertEqual(examinar.cget("bg"), BOTON)
            self.assertEqual(renombrar.cget("bg"), ACENTO)
            self.assertEqual(casilla.cget("bg"), FONDO)
            self.assertEqual(casilla.cget("selectcolor"), FONDO)
            self.assertEqual(int(casilla.cget("indicatoron")), 0)
            self.assertNotEqual(casilla.cget("image"), casilla.cget("selectimage"))
            casilla.invoke()
            self.assertTrue(estado.get())
            casilla.invoke()
            self.assertFalse(estado.get())
            modo = tk.StringVar(raiz, value="numerico")
            elegido = tk.Radiobutton(raiz, text="Numerico por fecha", variable=modo, value="numerico")
            otro = tk.Radiobutton(raiz, text="Alfabetico (a, b, c...)", variable=modo, value="alfabetico")
            self.assertEqual(int(elegido.cget("indicatoron")), 0)
            self.assertEqual(elegido.cget("selectcolor"), FONDO)
            self.assertNotEqual(elegido.cget("image"), elegido.cget("selectimage"))
            otro.invoke()
            self.assertEqual(modo.get(), "alfabetico")
            self.assertEqual(ayuda_de(casilla), AYUDAS["Incluir subcarpetas"])
            self.assertIn("carpeta", ayuda_de(examinar).lower())
            self.assertGreaterEqual(int(renombrar.cget("pady")), 8)
            tk.Label(raiz, text="Prefijo:").grid(row=0, column=0)
            campo = tk.Entry(raiz)
            campo.grid(row=1, column=0)
            self.assertIn("delante", ayuda_de(campo).lower())
            casilla_giro = tk.Spinbox(raiz, from_=1, to=10)
            self.assertEqual(casilla_giro.cget("bg"), CAMPO)
            estilo = ttk.Style(raiz)
            relleno = dict(estilo.map("TNotebook.Tab")["padding"])
            self.assertEqual(relleno["selected"], relleno["!selected"])
        finally:
            raiz.destroy()

    def test_ventanas_muestran_las_opciones_absorbidas(self):
        import tkinter as tk

        from MP4_a_Imagenes_Carpeta import construir_interfaz as video
        from MP4_a_MP3 import _FFMPEG_CACHE, construir_interfaz as audio
        from RenombradorNumerico import construir_interfaz as renombrador
        from aplicacion.tema import ayuda_de
        import MP4_a_MP3

        def _radio(ventana, texto):
            pendientes = [ventana]
            while pendientes:
                actual = pendientes.pop()
                for hijo in actual.winfo_children():
                    pendientes.append(hijo)
                    if isinstance(hijo, tk.Radiobutton) and hijo.cget("text") == texto:
                        return hijo
            self.fail(texto)

        ventanas = []
        try:
            try:
                extraccion = video("automatico", mostrar=False)
            except tk.TclError as exc:
                self.skipTest(str(exc))
            ventanas.append(extraccion)
            self.assertEqual(extraccion.modo_var.get(), "automatico")
            self.assertTrue(extraccion.panel_cantidades.grid_info())
            self.assertFalse(extraccion.panel_intervalo.grid_info())
            self.assertTrue(extraccion.casilla_recursivo.grid_info())

            frames = video("primer-frame", mostrar=False)
            ventanas.append(frames)
            self.assertFalse(frames.casilla_recursivo.grid_info())
            self.assertIn("PNG", ayuda_de(_radio(frames, "Solo el primer frame")))
            self.assertEqual(frames.boton_extraer.cget("text"), "Guardar primer frame")

            nombres = renombrador("alfabetico", mostrar=False)
            ventanas.append(nombres)
            self.assertEqual(nombres.modo_var.get(), "alfabetico")
            self.assertEqual(nombres.title(), "Renombrador alfabetico")
            self.assertEqual(nombres.marca_carpeta.winfo_manager(), "grid")

            capturas = renombrador("capturas", mostrar=False)
            ventanas.append(capturas)
            self.assertEqual(capturas.title(), "Numero de capturas")
            self.assertEqual(capturas.marca_carpeta.winfo_manager(), "")

            reemplazo = renombrador("reemplazar", mostrar=False)
            ventanas.append(reemplazo)
            self.assertEqual(reemplazo.panel_reemplazo.winfo_manager(), "grid")
            self.assertEqual(reemplazo.fila_afijos.winfo_manager(), "grid")

            norma = renombrador("nomenclatura", mostrar=False)
            ventanas.append(norma)
            self.assertEqual(norma.title(), "Fuera de nomenclatura")
            self.assertEqual(norma.fila_afijos.winfo_manager(), "")
            self.assertEqual(norma.panel_reemplazo.winfo_manager(), "")
            self.assertEqual(norma.marca_carpeta.winfo_manager(), "")

            MP4_a_MP3._FFMPEG_CACHE = _FFMPEG_CACHE or "ffmpeg"
            moviepy = audio("moviepy", mostrar=False)
            ventanas.append(moviepy)
            self.assertEqual(moviepy.motor_var.get(), "moviepy")
            self.assertEqual(moviepy.frame_opciones.winfo_manager(), "")
            self.assertEqual(moviepy.title(), "Video -> MP3 (MoviePy)")

            ffmpeg = audio("ffmpeg", mostrar=False)
            ventanas.append(ffmpeg)
            self.assertEqual(ffmpeg.frame_opciones.winfo_manager(), "pack")
            self.assertEqual(ffmpeg.etiqueta_ffmpeg.winfo_manager(), "pack")

            from ConvertidorFormato import construir_interfaz as convertir

            formato = convertir(mostrar=False)
            ventanas.append(formato)
            self.assertEqual(formato.entrada_fmt.get(), "mp4")
            self.assertEqual(formato.salida_fmt.get(), "mp3")
            self.assertEqual(formato.paneles["mp3"].winfo_manager(), "grid")
            self.assertEqual(formato.paneles["gif"].winfo_manager(), "")
            self.assertEqual(formato.paneles["mkv"].winfo_manager(), "")
            self.assertEqual(formato.fila_bitrate.winfo_manager(), "pack")

            formato.radios_salida["gif"].invoke()
            self.assertEqual(formato.salida_fmt.get(), "gif")
            self.assertEqual(formato.paneles["gif"].winfo_manager(), "grid")
            self.assertEqual(formato.paneles["mp3"].winfo_manager(), "")

            formato.radios_entrada["mkv"].invoke()
            self.assertEqual(formato.salida_fmt.get(), "mp3")
            self.assertEqual(formato.radios_salida["gif"].winfo_manager(), "")
            self.assertEqual(formato.paneles["mp3"].winfo_manager(), "grid")

            formato.radios_entrada["mp3"].invoke()
            self.assertEqual(formato.salida_fmt.get(), "mp4")
            self.assertEqual(formato.paneles["audio"].winfo_manager(), "grid")
            self.assertEqual(formato.paneles["mp3"].winfo_manager(), "")
            self.assertEqual(formato.radios_salida["mkv"].winfo_manager(), "")

            formato.radios_entrada["mp4"].invoke()
            formato.radios_salida["mp3"].invoke()
            self.assertEqual(formato.fila_bitrate.winfo_manager(), "pack")
            formato.radio_moviepy.invoke()
            self.assertEqual(formato.motor_var.get(), "moviepy")
            self.assertEqual(formato.fila_bitrate.winfo_manager(), "")
            self.assertEqual(formato.fila_ffmpeg.winfo_manager(), "")
        finally:
            for ventana in ventanas:
                ventana.destroy()


if __name__ == "__main__":
    unittest.main()
