import os
import tempfile
import unittest

from motores.archivos import ruta_dentro_de, ruta_disponible, rutas_iguales
from motores.imagenes import distancia_visual, similitud_visual
from motores.lotes import AccionLote, buscar_archivos, ejecutar_accion_lote
from motores.renombrado import CambioNombre, aplicar_plan, validar_plan
from aplicacion.catalogo import HERRAMIENTAS, SECCIONES


class MotoresTest(unittest.TestCase):
    def test_catalogo_apunta_a_scripts_existentes(self):
        raiz = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(SECCIONES)
        for herramienta in HERRAMIENTAS:
            self.assertTrue(os.path.isfile(os.path.join(raiz, herramienta.script)), herramienta.script)
            self.assertTrue(set(herramienta.secciones).issubset(SECCIONES))

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


if __name__ == "__main__":
    unittest.main()
