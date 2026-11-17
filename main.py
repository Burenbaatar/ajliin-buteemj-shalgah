"""1-р гишүүн — Tkinter GUI. Бусад 4 гишүүний модулийг нэг цонхонд холбоно."""
import tkinter as tk
from tkinter import ttk, messagebox

import cv2

import register as reg                      # 2-р гишүүн
from activity import ActivityTracker        # 4-р гишүүн
from camera import CameraService            # 3-р гишүүн


def row(parent):
    """Элементүүдийг нэг мөрөнд зүүнээс баруун тийш байрлуулах хүрээ."""
    frame = ttk.Frame(parent)
    frame.pack(anchor="w", pady=(0, 8))
    return frame


def button(parent, text, command):
    ttk.Button(parent, text=text, command=command).pack(side="left", padx=4)


def entry(parent, text, width):
    ttk.Label(parent, text=text).pack(side="left")
    field = ttk.Entry(parent, width=width)
    field.pack(side="left", padx=4)
    return field


class ProductivityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ажилтны идэвх")
        self.geometry("900x640")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.employees = []            # register.py-ээс уншсан ажилтнууд
        self.camera_service = None
        self.camera_job = None
        self.tracker = None            # идэвх хэмжиж байгаа үед ActivityTracker

        top = row(self)
        top.pack_configure(padx=10, pady=8)
        ttk.Label(top, text="Ажилтан:").pack(side="left")
        self.emp_combo = ttk.Combobox(top, state="readonly", width=30)
        self.emp_combo.pack(side="left", padx=6)

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for title, build in (("Ажилтны бүртгэл", self.build_employee), ("Камер", self.build_camera),
                             ("Компьютерийн идэвх", self.build_activity)):
            frame = ttk.Frame(tabs, padding=10)
            tabs.add(frame, text=title)
            build(frame)

        self.refresh_employees()
        self.after(1000, self.tick)

    def show_error(self, text):
        messagebox.showerror("Алдаа", str(text), parent=self)

    def selected_employee(self):
        index = self.emp_combo.current()
        return self.employees[index] if index >= 0 else None

    # ---------------------------------------------------------- 1. Ажилтны бүртгэл
    def build_employee(self, frame):
        form = row(frame)
        self.name_entry = entry(form, "Нэр:", 22)
        button(form, "Бүртгэх", self.add_employee_ui)
        button(form, "Жагсаалт шинэчлэх", self.refresh_employees)
        button(form, "Устгах", self.delete_selected_ui)
        self.tree = ttk.Treeview(frame, columns=("Нэр",), show="headings")
        for column in self.tree["columns"]:
            self.tree.heading(column, text=column)
        self.tree.pack(fill="both", expand=True)

    def add_employee_ui(self):
        try:
            reg.add_employee(self.name_entry.get())
        except (ValueError, OSError) as error:
            return self.show_error(error)
        self.name_entry.delete(0, "end")
        self.refresh_employees()

    def refresh_employees(self):
        self.employees = reg.list_employees()
        self.tree.delete(*self.tree.get_children())
        for emp in self.employees:
            self.tree.insert("", "end", iid=emp["id"], values=(emp["name"],))
        self.emp_combo["values"] = [emp["name"] for emp in self.employees]
        if self.emp_combo.current() < 0:               # сонгосон ажилтан байхгүй бол эхнийхийг сонгоно
            self.emp_combo.set(self.employees[0]["name"] if self.employees else "")

    def delete_selected_ui(self):
        employee_id = self.tree.focus()
        if not employee_id:
            return self.show_error("Устгах ажилтнаа жагсаалтаас сонгоно уу.")
        if messagebox.askyesno("Устгах", "Сонгосон ажилтныг устгах уу?", parent=self):
            reg.delete_employee(employee_id)
            self.refresh_employees()

    # ---------------------------------------------------------- 2. Камер
    def build_camera(self, frame):
        buttons = row(frame)
        button(buttons, "Камер нээх", self.start_camera)
        button(buttons, "Камер хаах", self.stop_camera)
        self.face_label = ttk.Label(frame, text="Камер хаалттай. Зураг хадгалахгүй.")
        self.face_label.pack()
        self.video_label = ttk.Label(frame)
        self.video_label.pack(pady=8)

    def start_camera(self):
        if self.camera_service:                        # аль хэдийн нээлттэй
            return
        self.camera_service = CameraService()
        if not self.camera_service.start():
            self.camera_service = None
            return self.show_error("Камер нээгдсэнгүй. Камер залгаатай, өөр програм ашиглаагүй эсэхийг шалгана уу.")
        self.render_camera_frame()

    def render_camera_frame(self):
        result = self.camera_service.get_frame()
        if result:
            frame, faces = result
            frame = cv2.resize(frame, (480, 360))
            photo = tk.PhotoImage(data=cv2.imencode(".ppm", frame)[1].tobytes())   # OpenCV кадр → Tkinter зураг
            self.video_label.config(image=photo)
            self.video_label.image = photo             # устахгүйн тулд хадгална
            self.face_label.config(text=f"Илэрсэн нүүр: {faces}")
        self.camera_job = self.after(60, self.render_camera_frame)

    def stop_camera(self):
        if self.camera_service:
            self.after_cancel(self.camera_job)
            self.camera_service.stop()
            self.camera_service = None
            self.video_label.config(image="")
            self.face_label.config(text="Камер хаалттай. Зураг хадгалахгүй.")

    # ---------------------------------------------------------- 3. Компьютерийн идэвх
    def build_activity(self, frame):
        ttk.Label(frame, wraplength=700, text="Хэмжилт зөвхөн «Хэмжилт эхлэх» дарсны дараа, зөвшөөрөлтэйгээр "
                  "эхэлнэ. Урд талын програмын нэр, хугацааг л бүртгэнэ.").pack(anchor="w", pady=(0, 8))
        buttons = row(frame)
        button(buttons, "Хэмжилт эхлэх", self.start_activity)
        button(buttons, "Түр зогсоох", self.pause_activity)
        button(buttons, "Дуусгах", self.finish_activity)
        self.activity_label = ttk.Label(frame, text="Хэмжилт эхлээгүй.", font=("Segoe UI", 12))
        self.activity_label.pack(pady=10)
        self.usage_graph = tk.Canvas(frame, height=320, background="white")
        self.usage_graph.pack(fill="both", expand=True)

    def update_usage_graph(self, apps):
        self.usage_graph.delete("all")
        items = sorted(apps.items(), key=lambda item: item[1], reverse=True)[:8]
        maximum = max((seconds for _, seconds in items), default=1)
        for index, (name, seconds) in enumerate(items):
            y = 18 + index * 36
            self.usage_graph.create_text(8, y + 10, text=name, anchor="w")
            width = 480 * seconds / maximum
            self.usage_graph.create_rectangle(190, y, 190 + width, y + 20, fill="#4a90d9", outline="")
            value = f"{seconds:.0f} сек" if seconds < 60 else f"{seconds / 60:.1f} мин"
            self.usage_graph.create_text(680, y + 10, text=value, anchor="e")

    def start_activity(self):
        if self.tracker:                               # түр зогсоосон хэмжилтийг үргэлжлүүлнэ
            return self.tracker.resume()
        self.activity_employee = self.selected_employee()
        if self.activity_employee is None:
            return self.show_error("Дээрээс ажилтан сонгоно уу.")
        self.tracker = ActivityTracker()
        self.tracker.start()
        self.update_usage_graph({})

    def pause_activity(self):
        if self.tracker:
            self.tracker.pause()

    def finish_activity(self):
        if not self.tracker:
            return
        summary = self.tracker.stop()
        self.tracker = None
        reg.save_activity(self.activity_employee["id"], summary)
        self.update_usage_graph(summary["apps"])
        self.activity_label.config(text=f"{self.activity_employee['name']}: {summary['total_seconds']:.0f} сек — хадгаллаа")

    def tick(self):
        """Секунд тутам идэвхийг хэмжиж харуулна."""
        self.after(1000, self.tick)
        if self.tracker:
            info = self.tracker.tick()
            self.activity_label.config(text=f"{self.activity_employee['name']}: {info['app'] or '—'} · "
                                            f"{info['total_seconds']:.0f} сек")
            self.update_usage_graph(self.tracker.apps)

    def on_close(self):
        if messagebox.askokcancel("Гарах", "Програмыг хаах уу?", parent=self):
            self.finish_activity()                     # хэмжиж байсан бол хадгална
            self.stop_camera()
            self.destroy()


if __name__ == "__main__":
    ProductivityApp().mainloop()
