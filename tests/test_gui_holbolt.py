"""Алхам 11. GUI (alkham08_gui_holbolt.py) + camera.py холболтын тест.

Бодит камер хэрэггүй — камерыг FakeCapture-аар орлуулна. Гэхдээ жинхэнэ Tkinter цонх
2 секунд орчим нээгдэж хаагдана (дэлгэцгүй орчинд тестүүд алгасагдана).

Ажиллуулах (энэ хавтасны эх фолдероос):
    python -m unittest discover -s tests -v
"""
import os
import sys
import tkinter as tk
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import alkham08_gui_holbolt as gui  # noqa: E402
import camera  # noqa: E402


class FakeCapture:
    """good_frames кадр өгсний дараа камер салсан мэт кадр өгөхөө болино (None бол хэзээ ч салахгүй)."""

    def __init__(self, good_frames=None):
        self.good_frames = good_frames
        self.reads = 0
        self.released = False

    def read(self):
        self.reads += 1
        if self.good_frames is not None and self.reads > self.good_frames:
            return False, None
        return True, np.zeros((480, 640, 3), dtype=np.uint8)

    def release(self):
        self.released = True


class GuiCameraTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("Дэлгэц байхгүй тул GUI тест алгаслаа")
        self.app = gui.CameraDemoApp(self.root)

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass  # on_close() аль хэдийн устгасан

    def run_for(self, milliseconds, click_every=50):
        """Цонхыг milliseconds хугацаанд ажиллуулна. Энэ хооронд товчийг тогтмол дарна."""
        pending = {}

        def press():
            self.app.on_click()
            pending["id"] = self.root.after(click_every, press)
        pending["id"] = self.root.after(click_every, press)
        self.root.after(milliseconds, self.root.quit)
        self.root.mainloop()
        self.root.after_cancel(pending["id"])  # дараагийн тестийн цонхонд үлдэж ажиллахгүйн тулд
        return milliseconds // click_every

    def test_camera_unplugged_window_does_not_freeze(self):
        fake = FakeCapture(good_frames=20)  # 20 кадрын дараа "камер салсан"
        with mock.patch.object(camera, "open_camera", return_value=fake):
            self.app.start_camera()
            self.assertTrue(self.app.camera.running)
            expected_clicks = self.run_for(2000)

        self.assertGreater(self.app.frames_drawn, 0)                # салахаас өмнө кадр зурсан
        self.assertFalse(self.app.camera.running)                   # салсны дараа өөрөө хаагдсан
        self.assertTrue(fake.released)
        self.assertIsNone(self.app.after_id)                        # кадрын давталт зогссон
        self.assertIn("ирэхээ больсон", self.app.status_var.get())  # ойлгомжтой алдаа харагдсан
        self.assertEqual(str(self.app.start_btn.cget("state")), "normal")  # дахин асааж болно
        self.assertGreaterEqual(self.app.clicks, expected_clicks * 0.8)    # цонх гацаагүй

    def test_close_window_stops_camera(self):
        fake = FakeCapture()
        with mock.patch.object(camera, "open_camera", return_value=fake):
            self.app.start_camera()
            self.root.after(300, self.app.on_close)  # X товч дарсантай адил
            self.root.mainloop()
        self.assertTrue(fake.released)
        self.assertIsNone(self.app.camera.cap)
        self.assertIsNone(self.app.after_id)

    def test_double_start_opens_one_camera(self):
        with mock.patch.object(camera, "open_camera", side_effect=lambda index: FakeCapture()) as opener:
            self.app.start_camera()
            self.app.start_camera()  # давхар дарсан
            self.run_for(300)
            self.app.stop_camera()
        self.assertEqual(opener.call_count, 1)

    def test_camera_missing_shows_error(self):
        with mock.patch.object(camera, "open_camera", return_value=None):
            self.app.start_camera()
        self.assertFalse(self.app.camera.running)
        self.assertIn("Камер нээгдсэнгүй", self.app.status_var.get())
        self.assertEqual(str(self.app.start_btn.cget("state")), "normal")


if __name__ == "__main__":
    unittest.main()
