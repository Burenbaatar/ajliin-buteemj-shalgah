"""1-р гишүүн — Tkinter GUI. Нэвтрэхэд ажилтан эсвэл админы эрхээр өөр табууд нээгдэнэ.

Админ:   ажилтан бүртгэх, гүйцэтгэл оруулах, бүх хүний бүтээмж харах. Админы компьютер сервер болно.
Ажилтан: камер, өөрийн идэвхийн хэмжилт. Үр дүнг админы сервер рүү JSON-оор илгээнэ.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import cv2

import productivity as prod                 # 5-р гишүүн
import register as reg                      # 2-р гишүүн
from activity import ActivityTracker        # 4-р гишүүн
from camera import CameraService            # 3-р гишүүн

BOLD = ("Segoe UI", 12, "bold")


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


def table(parent, columns):
    tree = ttk.Treeview(parent, columns=columns, show="headings")
    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=100)                 # бүх багана цонхонд багтана
    tree.pack(fill="both", expand=True)
    return tree


class ProductivityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ажилтны бүтээмж")
        self.geometry("900x640")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.server = None             # админ нэвтэрсэн үед JSON сервер
        self.camera_service = None
        self.camera_job = None
        self.tracker = None            # идэвх хэмжиж байгаа үед ActivityTracker
        self.build_login()
        self.after(1000, self.tick)

    def show_error(self, text):
        messagebox.showerror("Алдаа", str(text), parent=self)

    # ---------------------------------------------------------- нэвтрэх
    def build_login(self):
        self.login = ttk.Frame(self, padding=20)
        self.login.pack(fill="x")
        ttk.Label(self.login, text="Ажилтан", font=BOLD).pack(anchor="w", pady=(0, 6))
        form = row(self.login)
        self.host_entry = entry(form, "Админы компьютер:", 20)
        self.host_entry.insert(0, "127.0.0.1")
        button(form, "Холбогдох", self.connect)
        form = row(self.login)
        ttk.Label(form, text="Нэр:").pack(side="left")
        self.login_combo = ttk.Combobox(form, state="readonly", width=25)
        self.login_combo.pack(side="left", padx=4)
        button(form, "Нэвтрэх", self.open_employee)
        ttk.Label(self.login, text="Админ", font=BOLD).pack(anchor="w", pady=(24, 6))
        form = row(self.login)
        self.password_entry = entry(form, "Нууц үг:", 20)
        self.password_entry.config(show="*")
        button(form, "Админаар нэвтрэх", self.open_admin)
        ttk.Label(self.login, foreground="gray", text="Анх нэвтрэхэд оруулсан нууц үг админы нууц үг болно.").pack(
            anchor="w")

    def connect(self):
        """Админы серверээс ажилтнуудын нэрсийг авна."""
        try:
            self.people = reg.ask(self.host_entry.get().strip(), {"action": "employees"})["employees"]
        except (OSError, ValueError) as error:
            return self.show_error(f"Админы компьютертэй холбогдсонгүй: {error}")
        self.login_combo["values"] = [person["name"] for person in self.people]
        if self.people:
            self.login_combo.current(0)

    def open_tabs(self, title, pages):
        """Нэвтрэх хэсгийг хаагаад тухайн эрхийн табуудыг нээнэ."""
        self.login.destroy()
        top = row(self)
        top.pack_configure(padx=10, pady=8)
        ttk.Label(top, text=title, font=BOLD).pack(side="left", padx=(0, 20))
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for name, build in pages:
            frame = ttk.Frame(tabs, padding=10)
            tabs.add(frame, text=name)
            build(frame)
        return top

    def open_employee(self):
        index = self.login_combo.current()
        if index < 0:
            return self.show_error("Эхлээд «Холбогдох» дараад нэрээ сонгоно уу.")
        self.me = self.people[index]
        self.host = self.host_entry.get().strip()
        self.open_tabs("Ажилтан: " + self.me["name"],
                       [("Камер", self.build_camera), ("Компьютерийн идэвх", self.build_activity)])

    def open_admin(self):
        password = self.password_entry.get()
        if not password:
            return self.show_error("Нууц үгээ бичнэ үү.")
        if not reg.check_password(password):
            return self.show_error("Нууц үг буруу.")
        try:
            self.server = reg.start_server()
        except OSError:
            return self.show_error("Сервер асаж чадсангүй. Админы програм аль хэдийн нээлттэй байж магадгүй.")
        top = self.open_tabs("Админ", [("Ажилтны бүртгэл", self.build_employee), ("Бүтээмж", self.build_productivity),
                                       ("Ажлын бүтээмж", self.build_overview)])
        ttk.Label(top, text="Ажилтан:").pack(side="left")
        self.emp_combo = ttk.Combobox(top, state="readonly", width=30)
        self.emp_combo.pack(side="left", padx=6)
        self.refresh_employees()
        self.overview_loop()
        self.serve_loop()

    def serve_loop(self):
        """0.1 сек тутам ажилтнуудын JSON хүсэлтэд хариулна."""
        self.after(100, self.serve_loop)
        reg.serve(self.server)

    # ---------------------------------------------------------- админ: ажилтны бүртгэл
    def selected_employee(self):
        index = self.emp_combo.current()
        return self.employees[index] if index >= 0 else None

    def build_employee(self, frame):
        form = row(frame)
        self.name_entry = entry(form, "Нэр:", 22)
        self.target_entry = entry(form, "Төлөвлөсөн даалгавар:", 6)
        button(form, "Бүртгэх", self.add_employee_ui)
        button(form, "Жагсаалт шинэчлэх", self.refresh_employees)
        button(form, "Устгах", self.delete_selected_ui)
        self.tree = table(frame, ("Нэр", "Төлөвлөсөн", "Дууссан"))

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
        self.refresh_overview()

    def delete_selected_ui(self):
        employee_id = self.tree.focus()
        if not employee_id:
            return self.show_error("Устгах ажилтнаа жагсаалтаас сонгоно уу.")
        if messagebox.askyesno("Устгах", "Сонгосон ажилтныг устгах уу?", parent=self):
            reg.delete_employee(employee_id)
            self.refresh_employees()

    # ---------------------------------------------------------- админ: бүтээмж
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
            report = prod.build_report(employee, reg.last_activity(employee["id"]))   # сүүлийн идэвх
            reg.save_report(employee["id"], report)
        except (ValueError, OSError) as error:
            return self.show_error(error)
        self.percent_label.config(text=f"{report['completion_rate']}%")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("1.0", prod.report_text(report))
        self.refresh_employees()

    # ---------------------------------------------------------- админ: ажлын бүтээмж (бүх ажилтан)
    def build_overview(self, frame):
        self.overview = table(frame, ("Нэр", "Төлөвлөсөн", "Дууссан", "Биелэлт %",
                                      "Сүүлийн идэвх (сек)", "Түр зогсох шалтгаан"))
        self.overview.column("Түр зогсох шалтгаан", width=250)

    def overview_loop(self):
        """5 секунд тутам шинэчилнэ — ажилтнуудын илгээсэн идэвх энд харагдана."""
        self.after(5000, self.overview_loop)
        self.refresh_overview()

    def refresh_overview(self):
        """Бүх ажилтны бүтээмжийг JSON-оос уншиж хүснэгтэд харуулна."""
        self.overview.delete(*self.overview.get_children())
        for emp in reg.list_employees():
            seconds = reg.last_activity(emp["id"]).get("total_seconds", 0)
            reason = reg.last_pause(emp["id"]).get("reason", "")
            self.overview.insert("", "end", values=(emp["name"], emp["target"], emp["completed"],
                                                    prod.calculate_completion(emp["target"], emp["completed"]),
                                                    f"{seconds:.0f}", reason))

    # ---------------------------------------------------------- ажилтан: камер
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

    # ---------------------------------------------------------- ажилтан: компьютерийн идэвх
    def build_activity(self, frame):
        ttk.Label(frame, wraplength=700, text="Хэмжилт зөвхөн «Хэмжилт эхлэх» дарсны дараа, зөвшөөрөлтэйгээр "
                  "эхэлнэ. Урд талын програм, танигдсан сайтын (YouTube, Facebook, Instagram, Gmail) нэр, "
                  "хугацааг л бүртгээд админ руу илгээнэ.").pack(anchor="w", pady=(0, 8))
        buttons = row(frame)
        button(buttons, "Хэмжилт эхлэх", self.start_activity)
        button(buttons, "Түр зогсоох", self.pause_activity)
        button(buttons, "Дуусгах", self.finish_activity)
        self.activity_label = ttk.Label(frame, text="Хэмжилт эхлээгүй.", font=("Segoe UI", 12))
        self.activity_label.pack(pady=10)
        self.usage_graph = tk.Canvas(frame, height=320, background="white")
        self.usage_graph.pack(fill="both", expand=True)

    def update_usage_graph(self, apps):
        """Програм, сайт тус бүрийн хугацааг хэвтээ баганаар зурна (хамгийн их 8)."""
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
        self.tracker = ActivityTracker()
        self.tracker.start()
        self.update_usage_graph({})

    def pause_activity(self):
        if self.tracker:
            reason = simpledialog.askstring("Түр зогсоох", "Ямар шалтгаанаар түр зогсоож байна вэ?", parent=self)
            if reason is None:
                return
            reason = reason.strip()
            if not reason:
                return self.show_error("Шалтгаанаа бичнэ үү.")
            try:
                reg.ask(self.host, {"action": "pause", "employee_id": self.me["id"], "reason": reason})
            except (ValueError, OSError) as error:
                return self.show_error(f"Админ руу илгээж чадсангүй: {error}")
            self.tracker.pause()
            self.activity_label.config(text=f"Түр зогсоосон — админд илгээлээ: {reason}")

    def finish_activity(self):
        """Хэмжилтийг дуусгаад хураангуйг админы сервер рүү илгээнэ."""
        if not self.tracker:
            return
        summary = self.tracker.stop()
        self.tracker = None
        self.update_usage_graph(summary["apps"])
        try:
            reg.ask(self.host, {"action": "activity", "employee_id": self.me["id"], "summary": summary})
        except (OSError, ValueError) as error:
            return self.show_error(f"Админ руу илгээж чадсангүй: {error}")
        self.activity_label.config(text=f"{summary['total_seconds']:.0f} сек — админ руу илгээлээ")

    def tick(self):
        """Секунд тутам идэвхийг хэмжиж харуулна."""
        self.after(1000, self.tick)
        if self.tracker:
            info = self.tracker.tick()
            self.activity_label.config(text=f"{info['app'] or '—'} · {info['total_seconds']:.0f} сек")
            self.update_usage_graph(self.tracker.apps)

    def on_close(self):
        if messagebox.askokcancel("Гарах", "Програмыг хаах уу?", parent=self):
            self.finish_activity()                     # хэмжиж байсан бол илгээнэ
            self.stop_camera()
            if self.server:
                self.server.close()
            self.destroy()


if __name__ == "__main__":
    ProductivityApp().mainloop()
