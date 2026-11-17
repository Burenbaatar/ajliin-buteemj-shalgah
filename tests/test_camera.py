"""Алхам 11. camera.py-ийн автомат тест. Бодит камер ХЭРЭГГҮЙ — камерыг FakeCapture-аар орлуулна.

Ажиллуулах (энэ хавтасны эх фолдероос):
    python -m unittest discover -s tests -v

Алхам 11-ийн checklist-тэй холбоо:
    3 удаа нээх/хаахад алдаа алга          → test_open_close_three_times
    Нүүргүй үед count=0                    → test_no_face_gives_zero
    Нүүртэй үед хүрээ гарч тоо өөрчлөгдөнө → test_face_box_and_count
    Камер салсан үед цонх гацахгүй         → test_camera_unplugged_stops_cleanly
"""
import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import camera  # noqa: E402


class FakeCapture:
    """cv2.VideoCapture-ийн орлуулга. ok=False бол камер эзлэгдсэн/салсан мэт кадр өгөхгүй."""

    def __init__(self, ok=True, frame=None):
        self.ok = ok
        self.frame = frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
        self.released = False

    def read(self):
        if self.ok:
            return True, self.frame.copy()
        return False, None

    def release(self):
        self.released = True


class FakeDetector:
    """CascadeClassifier-ийн орлуулга: үргэлж өгсөн хүрээнүүдийг "нүүр" гэж буцаана."""

    def __init__(self, faces):
        self.faces = faces

    def detectMultiScale(self, gray, **kwargs):  # noqa: N802 — OpenCV-ийн нэртэй ижил
        return self.faces


class CameraServiceTest(unittest.TestCase):
    def test_initial_state(self):
        cam = camera.CameraService()
        self.assertIsNone(cam.cap)
        self.assertIsNone(cam.detector)
        self.assertFalse(cam.running)

    def test_get_frame_before_start_returns_none(self):
        self.assertIsNone(camera.CameraService().get_frame())

    def test_stop_before_start_is_safe(self):
        cam = camera.CameraService()
        cam.stop()
        cam.stop()
        self.assertFalse(cam.running)

    def test_open_close_three_times(self):
        with mock.patch.object(camera, "open_camera", side_effect=lambda index: FakeCapture()) as opener:
            cam = camera.CameraService()
            for _ in range(3):
                self.assertTrue(cam.start(), cam.last_error)
                self.assertTrue(cam.start())  # Алхам 2.4: хоёр дахь start() шинэ камер нээхгүй
                self.assertIsNotNone(cam.get_frame())
                first_cap = cam.cap
                cam.stop()
                cam.stop()                    # Алхам 2.5: давхар stop() алдаа гаргахгүй
                self.assertTrue(first_cap.released)
                self.assertIsNone(cam.cap)
                self.assertFalse(cam.running)
            self.assertEqual(opener.call_count, 3)

    def test_no_face_gives_zero(self):
        with mock.patch.object(camera, "open_camera", return_value=FakeCapture()):
            cam = camera.CameraService()
            self.assertTrue(cam.start(), cam.last_error)
            frame, count = cam.get_frame()
            cam.stop()
        self.assertEqual(count, 0)
        self.assertEqual(frame.shape, (480, 640, 3))  # BGR, 3 суваг хэвээр

    def test_face_box_and_count(self):
        with mock.patch.object(camera, "open_camera", return_value=FakeCapture()):
            cam = camera.CameraService()
            self.assertTrue(cam.start(), cam.last_error)
            cam.detector = FakeDetector([(100, 50, 80, 80), (300, 200, 90, 90)])
            frame, count = cam.get_frame()
            cam.stop()
        self.assertEqual(count, 2)
        self.assertEqual(tuple(int(v) for v in frame[50, 100]), camera.BOX_COLOR)  # хүрээний булан ногоон

    def test_camera_missing(self):
        with mock.patch.object(camera, "open_camera", return_value=None):
            cam = camera.CameraService()
            self.assertFalse(cam.start())
            self.assertIn("Камер нээгдсэнгүй", cam.last_error)
            self.assertFalse(cam.running)

    def test_camera_busy_releases_and_explains(self):
        busy = FakeCapture(ok=False)
        with mock.patch.object(camera, "open_camera", return_value=busy):
            cam = camera.CameraService()
            self.assertFalse(cam.start())
        self.assertTrue(busy.released)  # эзлэгдсэн камерыг барьж үлдэхгүй
        self.assertIn("өөр", cam.last_error)

    def test_camera_unplugged_stops_cleanly(self):
        fake = FakeCapture()
        with mock.patch.object(camera, "open_camera", return_value=fake):
            cam = camera.CameraService()
            self.assertTrue(cam.start())
            fake.ok = False  # камер салсан
            for _ in range(camera.MAX_READ_FAILS - 1):
                self.assertIsNone(cam.get_frame())
                self.assertTrue(cam.running)  # ганц нэг кадр алдсанд шууд хаахгүй
            self.assertIsNone(cam.get_frame())
            self.assertFalse(cam.running)      # олон удаа дараалан алдвал өөрөө хаагдана
            self.assertTrue(fake.released)
            self.assertIn("ирэхээ больсон", cam.last_error)

    def test_mirror(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :10] = 255  # зүүн ирмэг цагаан
        with mock.patch.object(camera, "open_camera", return_value=FakeCapture(frame=frame)):
            cam = camera.CameraService()
            cam.start()
            mirrored, _ = cam.get_frame()
            cam.stop()
        self.assertEqual(int(mirrored[0, -1, 0]), 255)  # толин тусгалын дараа баруун ирмэг цагаан
        self.assertEqual(int(mirrored[0, 0, 0]), 0)

    def test_resize_keeps_ratio(self):
        big = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertEqual(camera.resize_keep_ratio(big, 640).shape, (360, 640, 3))
        small = np.zeros((480, 640, 3), dtype=np.uint8)
        self.assertIs(camera.resize_keep_ratio(small, 640), small)  # жижиг кадрыг хөндөхгүй

    def test_big_camera_frame_is_resized(self):
        big = np.zeros((720, 1280, 3), dtype=np.uint8)
        with mock.patch.object(camera, "open_camera", return_value=FakeCapture(frame=big)):
            cam = camera.CameraService(max_width=640)
            cam.start()
            frame, _ = cam.get_frame()
            cam.stop()
        self.assertEqual(frame.shape, (360, 640, 3))


class DetectorTest(unittest.TestCase):
    def test_xml_found_and_loaded(self):
        detector, path = camera.load_face_detector()
        self.assertFalse(detector.empty())
        self.assertTrue(path.endswith(camera.FACE_XML))

    def test_real_detector_finds_nothing_on_black_frame(self):
        detector, _ = camera.load_face_detector()
        cam = camera.CameraService()
        cam.detector = detector
        self.assertEqual(cam.detect_faces(np.zeros((480, 640, 3), dtype=np.uint8)), [])

    def test_memory_loader_works(self):
        """Кирилл замтай компьютер дээр ашиглагдах нөөц арга зөв ажиллаж байгаа эсэх."""
        path = camera.find_face_xml()
        self.assertFalse(camera._load_xml_from_memory(path).empty())


if __name__ == "__main__":
    unittest.main()
