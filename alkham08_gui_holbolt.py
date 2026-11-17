"""Алхам 8. camera.py-г Tkinter GUI-тэй холбож ажиллуулах.

1-р гишүүн main.py-д камерыг яг ийм загвараар холбоно:
    • "Камер асаах" товч → CameraService.start()                        (8.1)
    • render_camera_frame() нэг кадр аваад ImageTk.PhotoImage болгон зурна (8.2)
    • root.after(30, ...)-аар дахин дуудна — while True байхгүй тул цонх гацахгүй
    • "Гацаагүйг шалгах" товч — камер ажиллаж байхад дарахад тоо нэмэгдэх ёстой (8.3)
    • Цонх хаахад stop() автоматаар дуудагдана                           (8.4)
    • after_cancel() — хаасны дараа камерын callback ажиллахгүй          (8.5)

Ажиллуулах:
    python alkham08_gui_holbolt.py
    python alkham08_gui_holbolt.py --self-test   # зөвхөн XML ачаалагдах эсэх (камергүй, .exe шалгахад)
    python alkham08_gui_holbolt.py --auto-demo r.json  # камер өөрөө асаж 6 сек ажиллаад хаагдана
"""
import sys
import tkinter as tk

import cv2
from PIL import Image, ImageTk

from camera import CameraService, load_face_detector

FRAME_DELAY_MS = 30            # ~30 кадр/сек
PREVIEW_W, PREVIEW_H = 640, 480


class CameraDemoApp:
    def __init__(self, root):
        self.root = root
        self.camera = CameraService()  # Алхам 7.4: GUI-д ганцхан CameraService объект
        self.after_id = None           # Алхам 8.5: after()-ийн буцаасан дугаар (цуцлахад хэрэгтэй)
        self.photo = None              # PhotoImage-д заавал нэр өгч хадгална, үгүй бол дүрс алга болно
        self.clicks = 0
        self.frames_drawn = 0          # хэдэн кадр зурсан (--auto-demo тайланд)
        self.max_faces = 0

        root.title("Камер ба нүүр илрүүлэлт — 3-р гишүүн")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)  # Алхам 8.4: X товч → on_close()

        # Камерын дүрсийг тогтмол пикселийн хэмжээтэй хүрээн дотор харуулна
        video_box = tk.Frame(root, width=PREVIEW_W, height=PREVIEW_H, bg="black")
        video_box.pack_propagate(False)
        video_box.pack(padx=10, pady=(10, 5))
        self.video = tk.Label(video_box, text="Камер унтраалттай", bg="black", fg="white",
                              font=("Segoe UI", 14))
        self.video.pack(fill="both", expand=True)

        self.count_var = tk.StringVar(value="Илэрсэн нүүр: —")
        tk.Label(root, textvariable=self.count_var, font=("Segoe UI", 13, "bold")).pack()

        buttons = tk.Frame(root)
        buttons.pack(pady=5)
        self.start_btn = tk.Button(buttons, text="Камер асаах", width=16, command=self.start_camera)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = tk.Button(buttons, text="Камер унтраах", width=16, command=self.stop_camera,
                                  state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        self.click_btn = tk.Button(buttons, text="Гацаагүйг шалгах (0)", width=20, command=self.on_click)
        self.click_btn.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Бэлэн. Камерын зургийг хадгалахгүй, нүүрийг танихгүй.")
        tk.Label(root, textvariable=self.status_var, wraplength=PREVIEW_W, justify="left",
                 fg="#444").pack(padx=10, pady=(0, 10), anchor="w")

    # ---------------------------------------------------------------- товчнууд
    def start_camera(self):
        if self.camera.running:
            return  # давхар дарсан ч хоёр дахь давталт эхлүүлэхгүй
        self.status_var.set("Камер нээж байна...")
        self.start_btn.configure(state="disabled")
        self.root.update_idletasks()  # мессежийг камер нээхээс ӨМНӨ дэлгэцэнд гаргана

        if not self.camera.start():
            self.show_camera_off("Алдаа: " + self.camera.last_error)
            return
        self.stop_btn.configure(state="normal")
        self.status_var.set("Камер ажиллаж байна. XML: " + self.camera.xml_path)
        self.render_camera_frame()

    def stop_camera(self, message="Камер унтарлаа."):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)  # Алхам 8.5: хүлээгдэж буй callback-ийг цуцална
            self.after_id = None
        self.camera.stop()
        self.show_camera_off(message)

    def on_click(self):
        self.clicks += 1
        self.click_btn.configure(text=f"Гацаагүйг шалгах ({self.clicks})")

    def on_close(self):
        self.stop_camera()  # Алхам 8.4: цонх хаахад камер заавал хаагдана
        self.root.destroy()

    # ---------------------------------------------------------------- кадр зурах
    def render_camera_frame(self):
        """Нэг кадр аваад зурна, дараа нь after()-аар өөрийгөө дахин дуудна."""
        self.after_id = None
        result = self.camera.get_frame()

        if result is None:
            if not self.camera.running:  # камер салсан → CameraService өөрөө хаагдсан
                self.show_camera_off("Алдаа: " + self.camera.last_error)
                return
            # нэг кадр алдсан төдий — дараагийн кадрыг хүлээнэ
        else:
            frame, count = result
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Алхам 3.4: OpenCV BGR → Tkinter RGB
            self.photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.video.configure(image=self.photo, text="")
            self.count_var.set(f"Илэрсэн нүүр: {count}")
            self.frames_drawn += 1
            self.max_faces = max(self.max_faces, count)

        self.after_id = self.root.after(FRAME_DELAY_MS, self.render_camera_frame)

    def show_camera_off(self, message):
        self.photo = None
        self.video.configure(image="", text="Камер унтраалттай")
        self.count_var.set("Илэрсэн нүүр: —")
        self.status_var.set(message)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


def self_test():
    """Камер нээхгүйгээр зөвхөн нүүр илрүүлэх XML ачаалагдаж байгааг шалгана.

    .exe (--windowed) консолгүй тул үр дүнг exit code-оор өгнө: 0 = OK, 1 = алдаа.
    """
    try:
        _, path = load_face_detector()
    except Exception as error:  # noqa: BLE001 — .exe дотор ямар ч алдааг exit code болгоно
        if sys.stdout:
            print("XML АЛДАА:", error)
        return 1
    if sys.stdout:
        print("XML OK:", path)
    return 0


def auto_demo(result_path, seconds=6):
    """Хүн оролцохгүйгээр GUI-г турших (.exe шалгахад): камер өөрөө асаж, seconds секунд
    ажиллаад цонх өөрөө хаагдана. Үр дүнг result_path JSON файлд бичнэ.

    Цонх гацаагүйг батлах: 200 мс тутамд "Гацаагүйг шалгах" товчийг after()-аар дарна.
    Камерын кадр GUI-г гацааж байвал эдгээр товч дарах үйлдэл хоцорч, тоо нь цөөрнө.
    """
    import json

    root = tk.Tk()
    app = CameraDemoApp(root)
    bundle_dir = getattr(sys, "_MEIPASS", "")
    report = {"frozen": bool(getattr(sys, "frozen", False)), "bundle_dir": bundle_dir}

    def press_button():
        app.on_click()
        root.after(200, press_button)

    def begin():
        app.start_camera()
        report["started"] = app.camera.running
        report["error"] = app.camera.last_error
        report["xml_path"] = app.camera.xml_path
        report["xml_inside_exe"] = bool(bundle_dir) and app.camera.xml_path.startswith(bundle_dir)
        press_button()
        root.after(seconds * 1000, finish)

    def finish():
        report["seconds"] = seconds
        report["frames_drawn"] = app.frames_drawn
        report["fps"] = round(app.frames_drawn / seconds, 1)
        report["max_faces"] = app.max_faces
        report["button_clicks"] = app.clicks
        report["button_clicks_expected"] = seconds * 1000 // 200
        app.on_close()  # Алхам 8.4: stop() + destroy()
        report["camera_released"] = app.camera.cap is None and not app.camera.running

    root.after(300, begin)
    root.mainloop()
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if report.get("started") and report.get("frames_drawn", 0) > 0 else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()
    if "--auto-demo" in sys.argv:
        position = sys.argv.index("--auto-demo")
        if position + 1 >= len(sys.argv):
            return 2  # үр дүн бичих файлын зам өгөөгүй
        return auto_demo(sys.argv[position + 1])
    root = tk.Tk()
    CameraDemoApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
