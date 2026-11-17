"""1-р гишүүн — Tkinter GUI. Нэвтрэхэд ажилтан эсвэл админы эрхээр өөр табууд нээгдэнэ.

Админ:   ажилтан бүртгэх, бүх хүний програм, сайтын хугацаа, түр зогсоосон шалтгаан, камерын шалгалтыг харах.
         Админы компьютер сервер болно.
Ажилтан: камер (амьд хүн мөн эсэх, ажилтан өөрөө сууж байгаа эсэх), өөрийн идэвхийн хэмжилт.
         Үр дүнг админы сервер рүү JSON-оор илгээнэ.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import cv2

import productivity as prod                 # 5-р гишүүн
import register as reg                      # 2-р гишүүн
from activity import SITES, ActivityTracker # 4-р гишүүн
from camera import CameraService, FaceEnrollment, FaceMonitor, draw   # 3-р гишүүн

BOLD = ("Segoe UI", 12, "bold")
# Камерын төлөв → (хүрээний өнгө BGR, бичгийн өнгө)
COLORS = {"owner": ((0, 200, 0), "#1a7f37"), "unknown": ((0, 200, 0), "#1a7f37"),
          "other": ((0, 0, 255), "#cf222e"), "fake": ((0, 0, 255), "#cf222e"),
          "checking": ((0, 200, 255), "#9a6700"), "no_face": ((0, 200, 255), "#9a6700")}


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
        self.geometry("1100x680")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.server = None             # админ нэвтэрсэн үед JSON сервер
        self.camera_service = None
        self.camera_job = None
        self.tracker = None            # идэвх хэмжиж байгаа үед ActivityTracker
        self.monitor = None            # хэмжилтийн үед FaceMonitor: амьд хүн мөн эсэх, хэн суусан
        self.enrollment = None         # нүүр бүртгэж байгаа үед FaceEnrollment
        self.last_check = None         # шинэ амьд хүн шалгалт эхэлснийг мэдэхийн тулд
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
        form = row(self.login)
        self.login_name = entry(form, "Нэр:", 20)
        self.login_code = entry(form, "Код:", 10)
        self.login_code.config(show="*")
        button(form, "Нэвтрэх", self.open_employee)
        ttk.Label(self.login, foreground="gray", text="Нэр, кодыг админ бүртгэхдээ өгнө. Админы програм "
                  "асаалттай байх ёстой.").pack(anchor="w")
        ttk.Label(self.login, text="Админ", font=BOLD).pack(anchor="w", pady=(24, 6))
        form = row(self.login)
        self.password_entry = entry(form, "Нууц үг:", 20)
        self.password_entry.config(show="*")
        button(form, "Админаар нэвтрэх", self.open_admin)
        ttk.Label(self.login, foreground="gray", text="Анх нэвтрэхэд оруулсан нууц үг админы нууц үг болно.").pack(
            anchor="w")

    def open_tabs(self, title, pages):
        """Нэвтрэх хэсгийг хаагаад тухайн эрхийн табуудыг нээнэ."""
        self.login.destroy()
        top = row(self)
        top.pack_configure(padx=10, pady=8)
        ttk.Label(top, text=title, font=BOLD).pack(side="left", padx=(0, 20))
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for name, build in pages:
            frame = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(frame, text=name)
            build(frame)
            if name == "Камер":
                self.camera_tab = frame
        return top

    def open_employee(self):
        """Нэр, кодыг админы сервер шалгана. Зөв бол ажилтны табууд нээгдэнэ."""
        self.host = self.host_entry.get().strip()
        request = {"action": "login", "name": self.login_name.get(), "code": self.login_code.get()}
        try:
            self.me = reg.ask(self.host, request)      # {"id", "name", "face": нүүрний хээ эсвэл None}
        except OSError:
            return self.show_error("Админы компьютертэй холбогдсонгүй. Админ нэвтэрсэн эсэх, хаягийг шалгана уу.")
        except ValueError as error:                    # нэр эсвэл код буруу
            return self.show_error(error)
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
        self.open_tabs("Админ", [("Ажилтны бүртгэл", self.build_employee), ("Ажлын бүтээмж", self.build_overview)])
        self.refresh_employees()
        self.overview_loop()
        self.serve_loop()

    def serve_loop(self):
        """0.1 сек тутам ажилтнуудын JSON хүсэлтэд хариулна."""
        self.after(100, self.serve_loop)
        reg.serve(self.server)

    # ---------------------------------------------------------- админ: ажилтны бүртгэл
    def build_employee(self, frame):
        form = row(frame)
        self.name_entry = entry(form, "Нэр:", 22)
        self.code_entry = entry(form, "Код:", 8)
        button(form, "Бүртгэх", self.add_employee_ui)
        button(form, "Жагсаалт шинэчлэх", self.refresh_employees)
        button(form, "Устгах", self.delete_selected_ui)
        button(form, "Нүүр устгах", self.delete_face_ui)
        ttk.Label(frame, foreground="gray", text="Ажилтан нэр, кодоороо нэвтэрнэ. Байгаа нэрийг дахин бүртгэвэл "
                  "код нь шинэчлэгдэнэ. Ажилтан нүүрээ нэг л удаа бүртгүүлнэ — шинэчлэх бол «Нүүр устгах» дарна."
                  ).pack(anchor="w", pady=(0, 6))
        self.tree = table(frame, ("Нэр", "Код", "Нүүр"))

    def add_employee_ui(self):
        try:
            reg.add_employee(self.name_entry.get(), self.code_entry.get())
        except (ValueError, OSError) as error:
            return self.show_error(error)
        self.name_entry.delete(0, "end")
        self.code_entry.delete(0, "end")
        self.refresh_employees()

    def refresh_employees(self):
        self.tree.delete(*self.tree.get_children())
        for emp in reg.list_employees():
            self.tree.insert("", "end", iid=emp["id"], values=(emp["name"], "байгаа" if emp.get("code") else "алга",
                                                              "бүртгэсэн" if reg.get_face(emp["id"]) else "—"))
        self.refresh_overview()

    def delete_selected_ui(self):
        employee_id = self.tree.focus()
        if not employee_id:
            return self.show_error("Устгах ажилтнаа жагсаалтаас сонгоно уу.")
        if messagebox.askyesno("Устгах", "Сонгосон ажилтныг устгах уу?", parent=self):
            reg.delete_employee(employee_id)
            self.refresh_employees()

    def delete_face_ui(self):
        employee_id = self.tree.focus()
        if not employee_id:
            return self.show_error("Ажилтнаа жагсаалтаас сонгоно уу.")
        if messagebox.askyesno("Нүүр устгах", "Сонгосон ажилтны нүүрийг устгах уу? Ажилтан дараа нь дахин "
                               "бүртгүүлэх боломжтой болно.", parent=self):
            reg.delete_face(employee_id)
            self.refresh_employees()

    # ---------------------------------------------------------- админ: ажлын бүтээмж (бүх ажилтан)
    def build_overview(self, frame):
        ttk.Label(frame, foreground="gray", wraplength=1000, text="Ажилтан бүрийн бүх хэмжилтийн нийлбэр. YouTube, "
                  "Facebook, Instagram, Gmail нь браузерын идэвхтэй таб дээр байсан хугацаа. «Өөр хүн» — камерт "
                  "бүртгэлтэй ажилтны оронд өөр хүн суусан хугацаа. «Баталгаажаагүй» — амьд хүн (зураг, бичлэг биш) "
                  "гэдэг нь батлагдаагүй хугацаа.").pack(anchor="w", pady=(0, 6))
        self.overview = table(frame, ("Нэр", "Нийт") + SITES + ("Хамгийн их програм", "Түр зогсох шалтгаан",
                                                                 "Өөр хүн", "Баталгаажаагүй"))
        self.overview.column("Түр зогсох шалтгаан", width=150)

    def overview_loop(self):
        """5 секунд тутам шинэчилнэ — ажилтнуудын илгээсэн идэвх энд харагдана."""
        self.after(5000, self.overview_loop)
        self.refresh_overview()

    def refresh_overview(self):
        """Ажилтан бүрийн програм, 4 сайт, камерын хугацааг JSON-оос уншиж хүснэгтэд харуулна."""
        self.overview.delete(*self.overview.get_children())
        for emp in reg.list_employees():
            summaries = reg.activities(emp["id"])
            apps = prod.total_apps(summaries)
            sites = [prod.minutes(seconds) for seconds in prod.site_times(apps).values()]
            reason = reg.last_pause(emp["id"]).get("reason", "")
            camera = prod.camera_totals(summaries)
            checks = [prod.minutes(camera[name]) if camera else "—" for name in ("other_seconds", "unverified_seconds")]
            self.overview.insert("", "end", values=[emp["name"], prod.minutes(sum(apps.values()))] + sites
                                 + [prod.top_app(apps), reason] + checks)

    # ---------------------------------------------------------- ажилтан: камер
    def build_camera(self, frame):
        buttons = row(frame)
        button(buttons, "Камер нээх", self.start_camera)
        button(buttons, "Камер хаах", self.close_camera_ui)
        button(buttons, "Нүүр бүртгэх", self.enroll_face_ui)
        face = "бүртгэсэн" if self.me.get("face") else "бүртгээгүй — «Нүүр бүртгэх» дарна уу"
        self.face_status = ttk.Label(frame, foreground="gray", text=f"Нүүр: {face}")
        self.face_status.pack(anchor="w")
        self.face_label = ttk.Label(frame, text="Камер хаалттай. Зураг хадгалахгүй.", font=("Segoe UI", 13),
                                    wraplength=1000)
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
            state, text, check = "no_face" if not len(faces) else "owner", f"Илэрсэн нүүр: {len(faces)}", None
            if self.enrollment:
                state, text, check = "checking", *self.enroll_step(frame, faces)
            elif self.monitor:
                counting = self.tracker is not None and self.tracker.running
                state, text = self.monitor.update(self.camera_service, frame, faces, counting)
                check = self.monitor.check
                if check is not None and check is not self.last_check:   # шинэ шалгалт эхэллээ
                    self.bring_to_front()
                self.last_check = check
            box, color = COLORS[state]
            draw(frame, faces, box, check.step if check else None)
            frame = cv2.resize(frame, (480, 360))
            photo = tk.PhotoImage(data=cv2.imencode(".ppm", frame)[1].tobytes())   # OpenCV кадр → Tkinter зураг
            self.video_label.config(image=photo)
            self.video_label.image = photo             # устахгүйн тулд хадгална
            self.face_label.config(text=text, foreground=color)
        self.camera_job = self.after(60, self.render_camera_frame)

    def enroll_face_ui(self):
        if self.me.get("face"):
            return self.show_error("Нүүр аль хэдийн бүртгэгдсэн. Шинэчлэх бол админд хандана уу.")
        self.start_camera()
        if self.camera_service:
            self.enrollment = FaceEnrollment()

    def enroll_step(self, frame, faces):
        """Нүүр бүртгэлийн нэг алхам. Хээ гарвал админы сервер рүү илгээнэ. (тайлбар, шалгалт) буцаана."""
        enrollment = self.enrollment
        feature, text = enrollment.update(self.camera_service, frame, faces)
        if feature is not None:
            self.enrollment = None
            feature = [float(value) for value in feature.ravel()]
            try:
                reg.ask(self.host, {"action": "face", "employee_id": self.me["id"], "feature": feature})
            except (OSError, ValueError) as error:
                self.after_idle(self.show_error, f"Нүүрийг админ руу илгээж чадсангүй: {error}")
                return "Нүүр бүртгэгдсэнгүй", None
            self.me["face"] = feature
            if self.monitor:
                self.monitor.set_owner(feature)        # хэмжилт явагдаж байвал шууд ашиглана
            self.face_status.config(text="Нүүр: бүртгэсэн")
            self.after_idle(messagebox.showinfo, "Нүүр бүртгэл", "Нүүр бүртгэгдлээ.")
        return text, enrollment.check

    def bring_to_front(self):
        """Амьд хүн шалгалт эхлэхэд цонхыг урд гаргаж, камерын табыг нээнэ."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(500, self.attributes, "-topmost", False)
        self.tabs.select(self.camera_tab)
        self.bell()

    def close_camera_ui(self):
        if self.tracker:
            return self.show_error("Хэмжилт явагдаж байхад камер хаах боломжгүй. «Дуусгах» дарна уу.")
        self.stop_camera()

    def stop_camera(self):
        if self.camera_service:
            self.after_cancel(self.camera_job)
            self.camera_service.stop()
            self.camera_service = None
            self.enrollment = None
            self.video_label.config(image="")
            self.face_label.config(text="Камер хаалттай. Зураг хадгалахгүй.", foreground="")

    # ---------------------------------------------------------- ажилтан: компьютерийн идэвх
    def build_activity(self, frame):
        ttk.Label(frame, wraplength=1000, text="Хэмжилт зөвхөн «Хэмжилт эхлэх» дарсны дараа, зөвшөөрөлтэйгээр "
                  "эхэлнэ. Урд талын програм, танигдсан сайтын (YouTube, Facebook, Instagram, Gmail) нэр, "
                  "хугацааг л бүртгээд админ руу илгээнэ. Камер хэмжилттэй хамт асаж, амьд хүн мөн эсэх, "
                  "бүртгэлтэй ажилтан өөрөө сууж байгаа эсэхийг шалгана. «Дуусгах» дарахад унтарна."
                  ).pack(anchor="w", pady=(0, 8))
        buttons = row(frame)
        button(buttons, "Хэмжилт эхлэх", self.start_activity)
        button(buttons, "Түр зогсоох", self.pause_activity)
        button(buttons, "Дуусгах", self.finish_activity)
        self.activity_label = ttk.Label(frame, text="Хэмжилт эхлээгүй.", font=("Segoe UI", 12), wraplength=1000)
        self.activity_label.pack(pady=10)
        self.usage_graph = tk.Canvas(frame, height=320, background="white")
        self.usage_graph.pack(fill="both", expand=True)

    def update_usage_graph(self, apps):
        """Програм, сайт тус бүрийн хугацааг хэвтээ баганаар зурна (хамгийн их 8)."""
        self.usage_graph.delete("all")
        items = sorted(apps.items(), key=lambda item: item[1], reverse=True)[:8]
        maximum = max((seconds for _, seconds in items), default=0) or 1   # 0-д хуваахаас сэргийлнэ
        for index, (name, seconds) in enumerate(items):
            y = 18 + index * 36
            self.usage_graph.create_text(8, y + 10, text=name, anchor="w")
            width = 480 * seconds / maximum
            self.usage_graph.create_rectangle(190, y, 190 + width, y + 20, fill="#4a90d9", outline="")
            value = f"{seconds:.0f} сек" if seconds < 60 else f"{seconds / 60:.1f} мин"
            self.usage_graph.create_text(680, y + 10, text=value, anchor="e")

    def start_activity(self):
        if self.tracker:                               # түр зогсоосон хэмжилтийг үргэлжлүүлнэ
            self.tracker.resume()
        else:
            self.tracker = ActivityTracker()
            self.tracker.start()
            self.update_usage_graph({})
        self.start_camera()                            # камер хэмжилттэй хамт автоматаар асна
        if self.camera_service and self.monitor is None:
            self.monitor = FaceMonitor(self.me.get("face"))
            self.last_check = None

    def pause_activity(self):
        """Түр зогсоохдоо шалтгаан асууж админ руу илгээнэ."""
        if self.tracker and self.tracker.running:     # хэмжиж байгаа үед л (аль хэдийн зогссон бол асуухгүй)
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
        """Хэмжилтийг дуусгаад хураангуйг (камерын шалгалттай нь) админы сервер рүү илгээнэ."""
        if not self.tracker:
            return
        summary = self.tracker.stop()
        self.tracker = None
        if self.monitor:
            summary["camera"] = self.monitor.summary()   # хэн хэдэн секунд суусан
            self.monitor = None
        self.stop_camera()                             # хэмжилт дуусахад камер хамт унтарна
        self.update_usage_graph(summary["apps"])
        try:
            reg.ask(self.host, {"action": "activity", "employee_id": self.me["id"], "summary": summary})
        except (OSError, ValueError) as error:
            return self.show_error(f"Админ руу илгээж чадсангүй: {error}")
        self.activity_label.config(text=f"{summary['total_seconds']:.0f} сек — админ руу илгээлээ")

    def tick(self):
        """Секунд тутам идэвхийг хэмжиж харуулна."""
        self.after(1000, self.tick)
        if self.tracker and self.tracker.running:      # түр зогсоосон үед бичгийг дарахгүй
            info = self.tracker.tick()
            camera = f"\nКамер: {self.face_label.cget('text')}" if self.monitor else ""
            self.activity_label.config(text=f"{info['app'] or '—'} · {info['total_seconds']:.0f} сек{camera}")
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
