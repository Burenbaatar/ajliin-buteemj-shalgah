"""1-р гишүүн — Tkinter GUI. Бусад 4 гишүүний модулийг нэг цонхонд холбоно."""
import tkinter as tk
from tkinter import ttk, messagebox

import cv2

import productivity as prod                 # 5-р гишүүн
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
        self.title("Ажилтны бүтээмж")
        self.geometry("900x640")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.employees = []            # register.py-ээс уншсан ажилтнууд
        self.camera_service = None
        self.camera_job = None
        self.tracker = None            # идэвх хэмжиж байгаа үед ActivityTracker
        self.summaries = {}            # ажилтны id → идэвхийн хураангуй

        top = row(self)
        top.pack_configure(padx=10, pady=8)
        ttk.Label(top, text="Ажилтан:").pack(side="left")
        self.emp_combo = ttk.Combobox(top, state="readonly", width=30)
        self.emp_combo.pack(side="left", padx=6)

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for title, build in (("Ажилтны бүртгэл", self.build_employee), ("Камер", self.build_camera),
                             ("Компьютерийн идэвх", self.build_activity), ("Бүтээмж", self.build_productivity)):
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
        self.target_entry = entry(form, "Төлөвлөсөн даалгавар:", 6)
        button(form, "Бүртгэх", self.add_employee_ui)
        button(form, "Жагсаалт шинэчлэх", self.refresh_employees)
        button(form, "Устгах", self.delete_selected_ui)
        self.tree = ttk.Treeview(frame, columns=("Нэр", "Төлөвлөсөн", "Дууссан"), show="headings")
        for column in self.tree["columns"]:
            self.tree.heading(column, text=column)
        self.tree.pack(fill="both", expand=True)

    def add_employee_ui(self):
        target = self.target_entry.get()
        if not target.isdigit():
            return self.show_error("Төлөвлөсөн даалгаврыг тоогоор бичнэ үү.")
        try:
            reg.add_employee(self.name_entry.get(), int(target))
        except (ValueError, OSError) as error:
            return self.show_error(error)
        self.name_entry.delete(0, "end")
        self.target_entry.delete(0, "end")
        self.refresh_employees()

    def refresh_employees(self):
        self.employees = reg.list_employees()
        self.tree.delete(*self.tree.get_children())
        for emp in self.employees:
            self.tree.insert("", "end", iid=emp["id"], values=(emp["name"], emp["target"], emp["completed"]))
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

    def start_activity(self):
        if self.tracker:                               # түр зогсоосон хэмжилтийг үргэлжлүүлнэ
            return self.tracker.resume()
        self.activity_employee = self.selected_employee()
        if self.activity_employee is None:
            return self.show_error("Дээрээс ажилтан сонгоно уу.")
        self.tracker = ActivityTracker()
        self.tracker.start()

    def pause_activity(self):
        if self.tracker:
            self.tracker.pause()

    def finish_activity(self):
        if not self.tracker:
            return
        summary = self.tracker.stop()
        self.tracker = None
        self.summaries[self.activity_employee["id"]] = summary
        reg.save_activity(self.activity_employee["id"], summary)
        self.activity_label.config(text=f"{self.activity_employee['name']}: {summary['total_seconds']:.0f} сек — хадгаллаа")

    def tick(self):
        """Секунд тутам идэвхийг хэмжиж харуулна."""
        self.after(1000, self.tick)
        if self.tracker:
            info = self.tracker.tick()
            self.activity_label.config(text=f"{self.activity_employee['name']}: {info['app'] or '—'} · "
                                            f"{info['total_seconds']:.0f} сек")

    # ---------------------------------------------------------- 4. Бүтээмж
    def build_productivity(self, frame):
        form = row(frame)
        self.completed_entry = entry(form, "Гүйцэтгэсэн даалгавар:", 6)
        button(form, "Хувь бодох", self.calculate_ui)
        self.percent_label = ttk.Label(frame, text="—", font=("Segoe UI", 32, "bold"))
        self.percent_label.pack(pady=10)
        self.report_box = tk.Text(frame, height=10)
        self.report_box.pack(fill="both", expand=True)

    def calculate_ui(self):
        employee = self.selected_employee()
        completed = self.completed_entry.get()
        if employee is None or not completed.isdigit():
            return self.show_error("Ажилтан сонгоод гүйцэтгэсэн даалгаврыг тоогоор бичнэ үү.")
        try:
            employee = reg.update_progress(employee["id"], int(completed))
            report = prod.build_report(employee, self.summaries.get(employee["id"], {}))
            reg.save_report(employee["id"], report)
        except (ValueError, OSError) as error:
            return self.show_error(error)
        self.percent_label.config(text=f"{report['completion_rate']}%")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("1.0", prod.report_text(report))
        self.refresh_employees()

    def on_close(self):
        if messagebox.askokcancel("Гарах", "Програмыг хаах уу?", parent=self):
            self.finish_activity()                     # хэмжиж байсан бол хадгална
            self.stop_camera()
            self.destroy()


if __name__ == "__main__":
    ProductivityApp().mainloop()
