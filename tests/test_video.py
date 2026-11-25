"""Prueba de extremo a extremo para la extraccion de cada frame."""

import os
import tempfile
import unittest

from motores.video import extraer_todos_los_frames

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


@unittest.skipIf(cv2 is None, "OpenCV no esta instalado")
class ExtraccionFramesTest(unittest.TestCase):
    def test_extrae_cada_frame_y_no_sobrescribe_extracciones_anteriores(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_video = os.path.join(carpeta, "video.avi")
            escritor = cv2.VideoWriter(
                ruta_video, cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (32, 24)
            )
            if not escritor.isOpened():
                self.skipTest("El codec MJPG no esta disponible")
            try:
                for valor in (20, 70, 120, 170):
                    escritor.write(np.full((24, 32, 3), valor, dtype=np.uint8))
            finally:
                escritor.release()

            avances = []
            fps_informados = []
            resultado = extraer_todos_los_frames(
                ruta_video, progreso=avances.append, fps_detectados=fps_informados.append
            )
            self.assertAlmostEqual(resultado.fps, 12.0, delta=0.1)
            self.assertEqual(fps_informados, [resultado.fps])
            self.assertEqual(resultado.total, 4)
            self.assertEqual(avances, [4])
            self.assertEqual(
                sorted(os.listdir(resultado.carpeta)),
                [f"video_frame_{indice:06d}.png" for indice in range(1, 5)],
            )
            primero = cv2.imread(os.path.join(resultado.carpeta, "video_frame_000001.png"))
            ultimo = cv2.imread(os.path.join(resultado.carpeta, "video_frame_000004.png"))
            self.assertIsNotNone(primero)
            self.assertIsNotNone(ultimo)
            self.assertGreater(float(ultimo.mean()), float(primero.mean()) + 100)

            segunda = extraer_todos_los_frames(ruta_video)
            self.assertEqual(segunda.total, 4)
            self.assertNotEqual(segunda.carpeta, resultado.carpeta)
            self.assertTrue(os.path.isfile(os.path.join(resultado.carpeta, "video_frame_000001.png")))

            solo_primero = extraer_todos_los_frames(ruta_video, solo_primer_frame=True)
            self.assertEqual(solo_primero.total, 1)
            self.assertFalse(solo_primero.cancelado)
            self.assertEqual(solo_primero.carpeta, "")
            self.assertEqual(
                solo_primero.archivo, os.path.join(carpeta, "video_primer_000001.png")
            )
            self.assertFalse(os.path.exists(os.path.join(carpeta, "video_frames_3")))
            imagen_primera = cv2.imread(solo_primero.archivo)
            self.assertAlmostEqual(float(imagen_primera.mean()), float(primero.mean()), delta=2)

            otro_primero = extraer_todos_los_frames(ruta_video, solo_primer_frame=True)
            self.assertEqual(
                otro_primero.archivo, os.path.join(carpeta, "video_primer_000001_2.png")
            )
            self.assertTrue(os.path.isfile(solo_primero.archivo))

            consultas = [0]

            def cancelar_despues_de_dos() -> bool:
                consultas[0] += 1
                return consultas[0] > 2

            parcial = extraer_todos_los_frames(ruta_video, cancelar=cancelar_despues_de_dos)
            self.assertTrue(parcial.cancelado)
            self.assertEqual(parcial.total, 2)
            self.assertEqual(len(os.listdir(parcial.carpeta)), 2)


if __name__ == "__main__":
    unittest.main()
