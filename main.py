"""1-р гишүүн — Tkinter GUI. Нэвтрэхэд ажилтан эсвэл админы эрхээр өөр табууд нээгдэнэ.

Админ:   Ажилтнууд (шууд самбар), 7 хоног, Хэрэглэгчид, Хэлтэс, Тохиргоо. Админы компьютер сервер болно.
Ажилтан: админы серверт нэвтэрмэгц камер асаж, амьд хүн мөн эсэх, ажилтан өөрөө сууж байгаа эсэхийг шалгана.
         Өөрийн идэвхийн хэмжилт. 5 секунд тутам админы сервер рүү JSON-оор илгээнэ.
"""
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import cv2

import productivity as prod                 # 5-р гишүүн
import register as reg                      # 2-р гишүүн
from activity import ActivityTracker        # 4-р гишүүн
from camera import CameraService, FaceEnrollment, FaceMonitor, draw   # 3-р гишүүн

BOLD = ("Segoe UI", 12, "bold")
# Камерын төлөв → (хүрээний өнгө BGR, бичгийн өнгө)
CAMERA_COLORS = {"owner": ((0, 200, 0), "#1a7f37"), "unknown": ((0, 200, 0), "#1a7f37"),
                 "other": ((0, 0, 255), "#cf222e"), "fake": ((0, 0, 255), "#cf222e"),
                 "checking": ((0, 200, 255), "#9a6700"), "no_face": ((0, 200, 255), "#9a6700")}
# Камер ажиллаж байхад ажилтныг өөрийг нь баталгаажуулаагүй шалтгаан — тэр хугацаа ажилласанд тоологдохгүй,
# самбарт «Гарсан (…)». Камер ажиллахгүй үед (төлөв None) гар, хулганы хөдөлгөөнөөр л тооцно.
CAMERA_REASONS = {"other": "камерт өөр хүн", "no_face": "камерт хүн алга", "checking": "амьд хүн шалгаж байна",
                  "fake": "амьд хүн баталгаажаагүй", "unknown": "нүүр бүртгээгүй"}
COLORS ={"work": "green", "away": "red", "offline": "gray", "absent": "#c0392b"}
TILE_COLORS = {"Ажиллаж байна": "green", "Гарсан": "red", "Офлайн": "gray", "Хоцорсон": "#c05000",
               "Ирээгүй": "#c0392b"}
SETTING_LABELS = {"work_start": "Ажил эхлэх (ЦЦ:ММ)", "work_end": "Ажил дуусах (ЦЦ:ММ)",
                  "late_grace_min": "Хоцролтын хүлцэл (мин)", "away_after_sec": "«Гарсан» гэж үзэх (сек хөдөлгөөнгүй)",
                  "unproductive": "Бүтээмжгүй програм / сайт (таслалаар)"}
DAYS = ("Да", "Мя", "Лх", "Пү", "Ба", "Бя", "Ня")


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


def table(parent, columns, widths=None):
    tree = ttk.Treeview(parent, columns=columns, show="headings")
    for column in columns:
        tree.heading(column, text=column, anchor="w")
        tree.column(column, width=(widths or {}).get(column, 80), anchor="w")
    tree.pack(fill="both", expand=True)
    return tree


def fill(tree, rows):
    """Хүснэгтийг цэвэрлээд шинэ мөрүүдээр дүүргэнэ."""
    tree.delete(*tree.get_children())
    for values in rows:
        tree.insert("", "end", values=values)


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
        self.monitor = None            # FaceMonitor: амьд хүн мөн эсэх, хэн суусан
        self.enrollment = None         # нүүр бүртгэж байгаа үед FaceEnrollment
        self.last_check = None         # шинэ амьд хүн шалгалт эхэлснийг мэдэхийн тулд
        self.camera_state = None       # FaceMonitor-ийн сүүлийн төлөв; None = камер ажиллахгүй (кадр ирэхгүй)
        self.pending = []              # админ руу хараахан илгээгдээгүй өсөлтүүд
        self.pause_reason = ""
        self.seconds = 0
        self.retry_at = 0              # админ холбогдохгүй бол энэ хүртэл дахин оролдохгүй
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
            return self.show_error(f"Админы компьютертэй ({self.host}, порт {reg.PORT}) холбогдсонгүй. Шалгах зүйл:\n"
                                   "1. Админы програм нээлттэй, админаар нэвтэрсэн эсэх.\n"
                                   "2. «Админы компьютер» талбарт админы цонхны дээд талд бичигдсэн IP хаяг байгаа эсэх "
                                   "(127.0.0.1 нь зөвхөн нэг компьютер дээр ажиллана).\n"
                                   "3. Хоёр компьютер нэг сүлжээнд (Wi-Fi) байгаа эсэх.\n"
                                   "4. Админы компьютерийн Windows Firewall ProductivitySystem-д зөвшөөрөл өгсөн эсэх.")
        except ValueError as error:                    # бүртгэлгүй нэр, код буруу г.м.
            return self.show_error(error)
        self.open_tabs("Ажилтан: " + self.me["name"],
                       [("Камер", self.build_camera), ("Компьютерийн идэвх", self.build_activity)])
        self.start_watching()                          # серверт холбогдмогц камер шууд ажиллана

    def open_admin(self):
        password = self.password_entry.get()
        if not password:
            return self.show_error("Нууц үгээ бичнэ үү.")
        try:
            correct = reg.check_password(password)
        except OSError as error:
            return self.show_error(f"Өгөгдлийн хавтсанд бичиж чадсангүй: {error}\n"
                                   "Програмыг Documents гэх мэт өөрийн хавтсанд хуулж ажиллуулна уу.")
        if not correct:
            return self.show_error("Нууц үг буруу.\nЭнэ компьютерийн админы нууц үг энд хадгалагдсан:\n"
                                   f"{reg.get_data_dir()}\\admin.json\n"
                                   "Мартсан бол тэр файлыг устгаад шинэ нууц үгээр нэвтэрнэ.")
        try:
            self.server = reg.start_server()
        except OSError:
            return self.show_error("Сервер асаж чадсангүй. Энэ компьютер дээр админы програм аль хэдийн "
                                   "нээлттэй байж магадгүй.")
        self.geometry("1420x700")
        top = self.open_tabs("Админ", [("Ажилтнууд", self.build_board), ("7 хоног", self.build_week),
                                       ("Хэрэглэгчид", self.build_employee), ("Хэлтэс", self.build_departments),
                                       ("Тохиргоо", self.build_settings)])
        ttk.Label(top, foreground="#1a5fb4", text=f"Ажилтнууд «Админы компьютер» талбарт: {reg.my_address()}   ·   "
                  f"Өгөгдөл: {reg.get_data_dir()}").pack(side="left")
        self.refresh_employees()
        self.board_loop()
        self.serve_loop()

    def serve_loop(self):
        """0.1 сек тутам ажилтнуудын JSON хүсэлтэд хариулна."""
        self.after(100, self.serve_loop)
        reg.serve(self.server)

    # ---------------------------------------------------------- админ: Ажилтнууд (шууд самбар)
    def build_board(self, frame):
        boxes = row(frame)
        self.tiles = {}
        for name in prod.TILES:
            box = tk.Frame(boxes, background="white", highlightthickness=1, highlightbackground="#d0d0d0",
                           padx=12, pady=6)
            box.pack(side="left", padx=(0, 8))
            tk.Label(box, text=name, background="white", foreground="gray").pack(anchor="w")
            self.tiles[name] = tk.Label(box, text="0", background="white", font=("Segoe UI", 18, "bold"),
                                        foreground=TILE_COLORS.get(name, "black"))
            self.tiles[name].pack(anchor="w")
        ttk.Label(frame, foreground="gray", wraplength=1380, text="Мөр дээр давхар дарвал тухайн ажилтны өнөөдрийн "
                  "бүх програм, хуудас, хулганы байршлыг харна. 5 секунд тутам шинэчлэгдэнэ. «Ажилласан» — камер "
                  "ажилтныг өөрийг нь баталгаажуулсан (камер ажиллахгүй бол гар, хулгана хөдөлсөн) хугацаа. "
                  "«Өөр хүн» — камерт бүртгэлтэй "
                  "ажилтны оронд өөр хүн суусан, «Баталгаажаагүй» — амьд хүн гэдэг нь батлагдаагүй хугацаа."
                  ).pack(anchor="w", pady=(0, 6))
        self.board = table(frame, prod.COLUMNS, {"Ажилтан": 170, "Одоо": 210, "Одоогийн апп": 220,
                                                 "Ирсэн – Явсан": 100, "Өдрийн явц": 200, "Баталгаажаагүй": 100})
        for status, color in COLORS.items():
            self.board.tag_configure(status, foreground=color)
        self.board.bind("<Double-1>", self.show_detail)

    def board_loop(self):
        self.after(5000, self.board_loop)
        self.refresh_board()

    def refresh_board(self):
        """Ажилтнууд, Хэлтэс, 7 хоног табуудыг JSON болон шууд төлөвөөс шинэчилнэ."""
        settings, employees = reg.load_settings(), reg.list_employees()
        records = reg.day_records(time.strftime("%Y-%m-%d"))
        rows = [prod.row_for(e, records.get(e["id"]), reg.live_status(e["id"]), settings, time.time())
                for e in employees]
        self.board.delete(*self.board.get_children())
        for employee, line in zip(employees, rows):
            self.board.insert("", "end", iid=employee["id"], values=line["values"], tags=(line["status"],))
        for name, value in prod.tiles(rows).items():
            self.tiles[name].config(text=value)
        fill(self.departments, prod.department_rows(employees, rows))
        monday = time.time() - time.localtime().tm_wday * 86400
        week = [reg.day_records(time.strftime("%Y-%m-%d", time.localtime(monday + i * 86400))) for i in range(7)]
        fill(self.week, [prod.week_row(e, week) for e in employees])

    def show_detail(self, event):
        """Давхар дарсан ажилтны өнөөдрийн бүх програм, хуудас, хулгана, нээлттэй програм, түр зогсолт."""
        employee_id = self.board.focus()
        if not employee_id:
            return
        name = next(e["name"] for e in reg.list_employees() if e["id"] == employee_id)
        record = reg.day_records(time.strftime("%Y-%m-%d")).get(employee_id, {})
        window = tk.Toplevel(self)
        window.title("Дэлгэрэнгүй — " + name)
        window.geometry("850x500")
        tree = table(window, ("Хаана", "Програм / хуудас", "Хугацаа"), {"Хаана": 110, "Програм / хуудас": 600})
        for label, key in (("Урд талд", "apps"), ("Хулгана дээр", "mouse")):
            for title, seconds in sorted(record.get(key, {}).items(), key=lambda item: -item[1]):
                tree.insert("", "end", values=(label, title, prod.duration(seconds)))
        for app in record.get("open", []):
            tree.insert("", "end", values=("Нээлттэй", app, ""))
        for pause in reg.pauses_today(employee_id):
            tree.insert("", "end", values=("Түр зогссон", pause["reason"], pause["time"][11:16]))

    # ---------------------------------------------------------- админ: 7 хоног, хэлтэс
    def build_week(self, frame):
        ttk.Label(frame, foreground="gray", text="Энэ 7 хоногийн өдөр бүрийн ажилласан цаг.").pack(anchor="w")
        self.week = table(frame, ("Ажилтан",) + DAYS + ("Нийт",), {"Ажилтан": 200})

    def build_departments(self, frame):
        self.departments = table(frame, ("Хэлтэс", "Хүн", "Ажиллаж байна", "Нийт ажилласан", "Дундаж бүтээмж"),
                                 {"Хэлтэс": 200, "Ажиллаж байна": 120, "Нийт ажилласан": 120, "Дундаж бүтээмж": 120})

    # ---------------------------------------------------------- админ: Хэрэглэгчид
    def build_employee(self, frame):
        form = row(frame)
        self.name_entry = entry(form, "Нэр:", 22)
        self.department_entry = entry(form, "Хэлтэс:", 18)
        self.code_entry = entry(form, "Код:", 8)
        button(form, "Бүртгэх", self.add_employee_ui)
        button(form, "Жагсаалт шинэчлэх", self.refresh_employees)
        button(form, "Устгах", self.delete_selected_ui)
        button(form, "Нүүр устгах", self.delete_face_ui)
        ttk.Label(frame, foreground="gray", text="Ажилтан нэр, кодоороо нэвтэрнэ. Байгаа нэрийг дахин бүртгэвэл "
                  "хэлтэс, код нь шинэчлэгдэнэ. Ажилтан нүүрээ нэг л удаа бүртгүүлнэ — шинэчлэх бол «Нүүр устгах» "
                  "дарна.").pack(anchor="w", pady=(0, 6))
        self.tree = table(frame, ("Нэр", "Хэлтэс", "Код", "Нүүр"), {"Нэр": 250, "Хэлтэс": 250})

    def add_employee_ui(self):
        try:
            reg.add_employee(self.name_entry.get(), self.code_entry.get(), self.department_entry.get())
        except (ValueError, OSError) as error:
            return self.show_error(error)
        for field in (self.name_entry, self.department_entry, self.code_entry):
            field.delete(0, "end")
        self.refresh_employees()

    def refresh_employees(self):
        self.tree.delete(*self.tree.get_children())
        for emp in reg.list_employees():
            self.tree.insert("", "end", iid=emp["id"], values=(emp["name"], emp.get("department", ""),
                                                               "байгаа" if emp.get("code") else "алга",
                                                               "бүртгэсэн" if reg.get_face(emp["id"]) else "—"))
        self.refresh_board()

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

    # ---------------------------------------------------------- админ: Тохиргоо
    def build_settings(self, frame):
        settings = reg.load_settings()
        self.setting_fields = {}
        for key, text in SETTING_LABELS.items():
            form = row(frame)
            ttk.Label(form, text=text, width=36).pack(side="left")
            field = ttk.Entry(form, width=50)
            field.pack(side="left")
            value = settings[key]
            field.insert(0, ", ".join(value) if isinstance(value, list) else str(value))
            self.setting_fields[key] = field
        button(row(frame), "Хадгалах", self.save_settings_ui)

    def save_settings_ui(self):
        get = {key: field.get().strip() for key, field in self.setting_fields.items()}
        try:
            settings = {"work_start": get["work_start"], "work_end": get["work_end"],
                        "late_grace_min": int(get["late_grace_min"]), "away_after_sec": int(get["away_after_sec"]),
                        "unproductive": [word.strip() for word in get["unproductive"].split(",") if word.strip()]}
            prod.to_minutes(settings["work_start"])     # ЦЦ:ММ хэлбэртэй эсэхийг шалгана
            prod.to_minutes(settings["work_end"])
        except ValueError:
            return self.show_error("Цагийг ЦЦ:ММ, тоог бүхэл тоогоор бичнэ үү.")
        reg.save_settings(settings)
        messagebox.showinfo("Тохиргоо", "Хадгаллаа. Ажилтнуудад 5 секундын дотор хүрнэ.", parent=self)
        self.refresh_board()

    # ---------------------------------------------------------- ажилтан: камер
    def build_camera(self, frame):
        buttons = row(frame)
        button(buttons, "Камер нээх", lambda: self.start_watching(quiet=False))
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

    def start_watching(self, quiet=True):
        """Камер асааж, амьд хүн мөн эсэх, бүртгэлтэй ажилтан өөрөө сууж байгаа эсэхийг шалгаж эхэлнэ.
        Хугацааг зөвхөн хэмжилт явагдаж байх үед тоолно."""
        self.start_camera(quiet)
        if self.camera_service and self.monitor is None:
            self.monitor = FaceMonitor(self.me.get("face"))
            self.last_check = None

    def start_camera(self, quiet=False):
        """quiet=True (автоматаар асаахад) бол алдааны цонх гаргахгүй, камерын табд бичнэ."""
        if self.camera_service:                        # аль хэдийн нээлттэй
            return
        self.camera_service = CameraService()
        if not self.camera_service.start():
            self.camera_service = None
            message = "Камер нээгдсэнгүй. Камер залгаатай, өөр програм ашиглаагүй эсэхийг шалгана уу."
            if quiet:                                  # камергүй үед гар, хулганы хөдөлгөөнөөр тооцно
                return self.face_label.config(text=message + " Камер ажиллахгүй үед ажилласан хугацааг гар, "
                                              "хулганы хөдөлгөөнөөр тооцно.", foreground="#9a6700")
            return self.show_error(message)
        self.render_camera_frame()

    def render_camera_frame(self):
        result = self.camera_service.get_frame()
        if result:
            frame, faces = result
            state, text, check = "no_face" if not len(faces) else "owner", f"Илэрсэн нүүр: {len(faces)}", None
            self.camera_state = "checking"             # нүүр бүртгэлийн үед баталгаажаагүй гэж үзнэ
            if self.enrollment:
                state, text, check = "checking", *self.enroll_step(frame, faces)
            elif self.monitor:
                counting = self.tracker is not None and self.tracker.running
                state, text = self.monitor.update(self.camera_service, frame, faces, counting)
                self.camera_state = state
                check = self.monitor.check
                if check is not None and check is not self.last_check:   # шинэ шалгалт эхэллээ
                    self.bring_to_front()
                self.last_check = check
            box, color = CAMERA_COLORS[state]
            draw(frame, faces, box, check.step if check else None)
            frame = cv2.resize(frame, (480, 360))
            photo = tk.PhotoImage(data=cv2.imencode(".ppm", frame)[1].tobytes())   # OpenCV кадр → Tkinter зураг
            self.video_label.config(image=photo)
            self.video_label.image = photo             # устахгүйн тулд хадгална
            self.face_label.config(text=text, foreground=color)
        else:                                          # кадр ирэхгүй (камер салсан г.м.) — камер ажиллахгүй
            self.camera_state = None
            self.face_label.config(text="Камераас кадр ирэхгүй байна. Ажилласан хугацааг гар, хулганы "
                                        "хөдөлгөөнөөр тооцно.", foreground="#9a6700")
        self.camera_job = self.after(60, self.render_camera_frame)

    def enroll_face_ui(self):
        if self.me.get("face"):
            return self.show_error("Нүүр аль хэдийн бүртгэгдсэн. Шинэчлэх бол админд хандана уу.")
        self.start_watching(quiet=False)
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
            self.camera_state = None
            self.video_label.config(image="")
            self.face_label.config(text="Камер хаалттай. Зураг хадгалахгүй.", foreground="")

    # ---------------------------------------------------------- ажилтан: компьютерийн идэвх
    def build_activity(self, frame):
        ttk.Label(frame, wraplength=1000, text="Хэмжилт зөвхөн «Хэмжилт эхлэх» дарсны дараа, зөвшөөрөлтэйгээр "
                  "эхэлнэ. Урд талын болон хулганы доорх цонхны програм, гарчиг (браузерын хуудасны гарчиг), "
                  "нээлттэй програмууд, гар/хулгана хөдөлсөн эсэхийг бүртгэж 5 секунд тутам админ руу илгээнэ. "
                  "Товчлуурын даралт, дэлгэцийн зураг, хуудасны агуулга авахгүй. Камер админы серверт нэвтэрмэгц "
                  "асаж, амьд хүн мөн эсэх, бүртгэлтэй ажилтан өөрөө сууж байгаа эсэхийг шалгана. Камер ажиллаж "
                  "байвал ажилласан хугацаа зөвхөн камер таныг баталгаажуулсан үед тоологдоно. Камер ажиллахгүй бол "
                  "гар, хулганы хөдөлгөөнөөр тооцно. Хэмжилтийн үеэр камер хаагдахгүй."
                  ).pack(anchor="w", pady=(0, 8))
        buttons = row(frame)
        button(buttons, "Хэмжилт эхлэх", self.start_activity)
        button(buttons, "Түр зогсоох", self.pause_activity)
        button(buttons, "Дуусгах", self.finish_activity)
        self.activity_label = ttk.Label(frame, text="Хэмжилт эхлээгүй.", font=("Segoe UI", 11), wraplength=1000)
        self.activity_label.pack(anchor="w", pady=(4, 2))
        self.open_label = ttk.Label(frame, foreground="gray", wraplength=1000)
        self.open_label.pack(anchor="w", pady=(0, 6))
        self.usage_graph = tk.Canvas(frame, height=300, background="white")
        self.usage_graph.pack(fill="both", expand=True)

    def update_usage_graph(self, apps):
        """Програм, хуудас тус бүрийн хугацааг хэвтээ баганаар зурна (хамгийн их 8)."""
        self.usage_graph.delete("all")
        items = sorted(apps.items(), key=lambda item: item[1], reverse=True)[:8]
        maximum = max((seconds for _, seconds in items), default=0) or 1   # 0-д хуваахаас сэргийлнэ
        for index, (name, seconds) in enumerate(items):
            y = 18 + index * 34
            self.usage_graph.create_text(8, y + 10, text=name if len(name) <= 38 else name[:37] + "…", anchor="w")
            width = 380 * seconds / maximum
            self.usage_graph.create_rectangle(290, y, 290 + width, y + 20, fill="#4a90d9", outline="")
            self.usage_graph.create_text(760, y + 10, text=prod.duration(seconds), anchor="e")

    def start_activity(self):
        if self.tracker:                               # түр зогсоосон хэмжилтийг үргэлжлүүлнэ
            self.pause_reason = ""
            self.tracker.resume()
        else:
            self.tracker = ActivityTracker()
            self.tracker.start()
            self.update_usage_graph({})
            if self.monitor:
                self.monitor.reset()                   # камерын хугацаа энэ хэмжилтээс тоологдоно
        self.start_watching()                          # камерыг хаасан эсвэл нэвтрэхэд нээгдээгүй бол дахин асаана

    def pause_activity(self):
        """Түр зогсоохдоо шалтгаан асууж админ руу илгээнэ."""
        if self.tracker and not self.tracker.paused:  # хэмжиж байгаа үед л (аль хэдийн зогссон бол асуухгүй)
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
            self.pause_reason = reason
            self.activity_label.config(text=f"Түр зогсоосон — админд илгээлээ: {reason}")

    def finish_activity(self):
        """Хэмжилтийг дуусгаад сүүлийн өсөлтийг илгээнэ. Админы самбарт «Офлайн» болно."""
        if not self.tracker:
            return
        summary = self.tracker.stop()
        self.send_live("offline")
        self.tracker = None
        self.update_usage_graph(summary["apps"])
        self.activity_label.config(text=f"Хэмжилт дууслаа: {summary['total_seconds']:.0f} сек ажилласан.")

    def send_live(self, status=None):
        """Шууд төлөв болон сүүлд илгээснээс хойших өсөлтийг админ руу илгээнэ (0.5 сек л хүлээнэ)."""
        tracker = self.tracker
        delta = tracker.take_delta()
        if self.monitor:                               # камерын шалгалт: хэн хэдэн секунд суусан
            delta["camera"] = self.monitor.summary()
            self.monitor.reset()
        self.pending.append(delta)
        request = {"action": "live", "employee_id": self.me["id"], "computer": os.environ.get("COMPUTERNAME", ""),
                   "status": status or tracker.status, "app": tracker.app, "mouse": tracker.mouse_on,
                   "open": tracker.open, "reason": self.away_reason(), "deltas": self.pending}
        try:
            answer = reg.ask(self.host, request, timeout=0.5)
            tracker.away_after = answer["settings"]["away_after_sec"]     # админы тохиргоо
        except OSError:                                # админ холбогдохгүй — 30 сек дараа хамт илгээнэ
            self.retry_at = time.time() + 30
            return
        except ValueError:
            pass                                       # сервер хүлээж аваагүй (жишээ нь ажилтан устсан)
        self.pending = []

    def away_reason(self):
        """Админы самбарт «Гарсан (…)» гэж харагдах шалтгаан: түр зогсоосон эсвэл камер баталгаажуулаагүй."""
        if self.tracker.paused:
            return self.pause_reason
        return "" if self.tracker.verified else CAMERA_REASONS.get(self.camera_state, "")

    def tick(self):
        """Секунд тутам идэвхийг хэмжиж харуулна, 5 секунд тутам админ руу илгээнэ."""
        self.after(1000, self.tick)
        if not self.tracker:
            return
        # Камер ажиллаж байвал зөвхөн ажилтан өөрөө сууж байхад, ажиллахгүй бол гар, хулганаар л ажилласан гэж тоолно
        self.tracker.verified = self.camera_state in ("owner", None)
        info = self.tracker.tick()
        self.seconds += 1
        if self.seconds % 5 == 0 and time.time() >= self.retry_at:
            self.send_live()
        self.open_label.config(text="Нээлттэй програмууд: " + ", ".join(info["open"]))
        if not self.tracker.paused:                    # түр зогсоосон бичгийг дарахгүй
            if info["status"] == "work":
                state = "Ажиллаж байна" + (" (камер ажиллахгүй — гар, хулганаар тооцож байна)"
                                           if self.camera_state is None else "")
            elif not self.tracker.verified:
                state = f"Тоологдохгүй байна ({self.away_reason()}) — камер таныг баталгаажуулаагүй"
            else:
                state = "Гарсан (гар, хулгана хөдлөөгүй)"
            camera = f"\nКамер: {self.face_label.cget('text')}" if self.monitor else ""
            self.activity_label.config(text=f"{state} · {info['total_seconds']:.0f} сек\nУрд: {info['app']}\n"
                                            f"Хулгана: {info['mouse']}{camera}")
            self.update_usage_graph(self.tracker.apps)

    def on_close(self):
        if messagebox.askokcancel("Гарах", "Програмыг хаах уу?", parent=self):
            self.finish_activity()                     # хэмжиж байсан бол сүүлийн өсөлтийг илгээнэ
            self.stop_camera()
            if self.server:
                self.server.close()
            self.destroy()


if __name__ == "__main__":
    ProductivityApp().mainloop()
