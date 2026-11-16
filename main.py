"""1-р гишүүн — үндсэн програм: ажилтны цонх, tray, админы самбар. Бусад 4 модулийг энд холбоно.

    python main.py                # цонхтой
    python main.py --background   # цонхгүй, зөвхөн tray (компьютер асахад ингэж эхэлнэ)
    python main.py --admin        # энэ компьютерийг админых болгох (сервер + самбар)
"""
import json
import socket
import sys
import threading
import tkinter as tk
import winreg
from datetime import timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import cv2
import pystray
from PIL import Image, ImageDraw, ImageTk

import productivity as prod
import register as reg
from activity import ActivityTracker
from camera import CameraService

COLORS = {"working": "green", "away": "red", "paused": "orange"}
CAMERA_TEXT = {"ok": "OK", "none": "олдсонгүй", "blocked": "⚠ таглагдсан", "static": "⚠ хөдөлгөөнгүй нүүр"}
NOTICE = ("Энэ програм камераар таныг компьютерийн өмнө байгаа эсэхийг шалгаж, идэвхтэй аппын нэр, "
          "ажилласан хугацааг бүртгэнэ. Камерын зураг, дэлгэц, товчлуур хадгалахгүй.")
SETTING_LABELS = {"work_start": "Ажил эхлэх (ЦЦ:ММ)", "work_end": "Ажил дуусах", "lunch_start": "Цайны цаг эхлэх",
                  "lunch_end": "Цайны цаг дуусах", "workdays": "Ажлын өдрүүд (1=Даваа ... 7=Ням)",
                  "late_grace_min": "Хоцролтын хүлцэл (мин)", "away_grace_sec": "Гарсан гэж үзэх (сек)",
                  "productive_apps": "Бүтээмжтэй аппууд (таслалаар)"}


def single_instance():
    """Програм давхар ажиллахаас сэргийлнэ: портыг эзэлж чадвал анхных нь."""
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", reg.PORT + 1))
        return lock
    except OSError:
        return None


def set_autostart(on):
    """Компьютер асахад --background горимоор эхлэх (Windows-ийн Run бүртгэл)."""
    if getattr(sys, "frozen", False):                   # .exe болгосон үед
        command = f'"{sys.executable}" --background'
    else:                                               # pythonw.exe — консол цонхгүй
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        command = f'"{pythonw}" "{Path(__file__).resolve()}" --background'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_SET_VALUE)
    if on:
        winreg.SetValueEx(key, "ProductivitySystem", 0, winreg.REG_SZ, command)
    else:
        try:
            winreg.DeleteValue(key, "ProductivitySystem")
        except FileNotFoundError:
            pass
    key.Close()


def first_run(config):
    """Анх нээхэд: нэр, админы компьютер, зөвшөөрөл. Зөвшөөрөхгүй бол програм ажиллахгүй."""
    window = tk.Tk()
    window.title("Ажлын бүтээмж — бүртгүүлэх")
    name = tk.StringVar()
    server = tk.StringVar(value=config["server"])
    autostart = tk.BooleanVar(value=True)
    agree = tk.BooleanVar()
    ttk.Label(window, text=NOTICE, wraplength=380).grid(row=0, column=0, columnspan=2, padx=10, pady=10)
    ttk.Label(window, text="Таны нэр:").grid(row=1, column=0, sticky="w", padx=10)
    ttk.Entry(window, textvariable=name, width=30).grid(row=1, column=1, padx=10, pady=3)
    ttk.Label(window, text="Админы компьютер:").grid(row=2, column=0, sticky="w", padx=10)
    ttk.Entry(window, textvariable=server, width=30).grid(row=2, column=1, padx=10, pady=3)
    ttk.Checkbutton(window, text="Компьютер асахад автоматаар эхлэх", variable=autostart).grid(
        row=3, column=0, columnspan=2, sticky="w", padx=10)
    ttk.Checkbutton(window, text="Дээрхийг уншсан, зөвшөөрч байна", variable=agree).grid(
        row=4, column=0, columnspan=2, sticky="w", padx=10)

    def start():
        if not name.get().strip():
            messagebox.showerror("Алдаа", "Нэрээ бичнэ үү.", parent=window)
        elif not agree.get():
            messagebox.showerror("Алдаа", "Зөвшөөрөөгүй бол програм ажиллахгүй.", parent=window)
        else:
            config["name"] = name.get().strip()
            config["server"] = server.get().strip() or "127.0.0.1"
            config["autostart"] = autostart.get()
            config["consent"] = True
            reg.save_config(config)
            window.destroy()

    ttk.Button(window, text="Эхлэх", command=start).grid(row=5, column=0, columnspan=2, pady=10)
    window.mainloop()
    return config["consent"]


def admin_setup(config):
    """--admin: энэ компьютер сервер ажиллуулж, нууц үгтэй самбартай болно."""
    root = tk.Tk()
    root.withdraw()
    password = simpledialog.askstring("Админ", "Самбарын нууц үг:", show="*", parent=root)
    if password:
        config["admin"] = True
        config["password"] = reg.hash_password(password)
        reg.save_config(config)
        messagebox.showinfo("Админ", f"Боллоо. Ажилтнууд \"Админы компьютер\" талбарт {socket.gethostname()} "
                                     "гэж бичнэ. Windows firewall асуувал Allow дарна уу.", parent=root)
    root.destroy()


def dot(color):
    """Tray-д харуулах өнгөт дугуй зураг."""
    image = Image.new("RGBA", (64, 64))
    ImageDraw.Draw(image).ellipse((6, 6, 58, 58), fill=color)
    return image


def make_table(tabs, title, columns):
    """Notebook-д шинэ таб нэмээд түүн дотор хүснэгт (Treeview) үүсгэнэ."""
    frame = ttk.Frame(tabs)
    tabs.add(frame, text=title)
    table = ttk.Treeview(frame, columns=columns, show="headings")
    for column in columns:
        table.heading(column, text=column)
        table.column(column, width=100)
    table.pack(fill="both", expand=True)
    return table


# ------------------------------------------------------------------ ажилтны цонх
class App(tk.Tk):
    def __init__(self, config, background):
        super().__init__()
        self.config_data = config
        self.title("Ажлын бүтээмж")
        self.geometry("520x620")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)          # ✕ дарвал tray руу нуугдана

        # Бусад гишүүдийн модулиудыг холбох
        self.clock = prod.Clock()                                  # 5-р гишүүн
        self.settings = dict(prod.DEFAULT_SETTINGS, **config["settings"])
        self.camera = CameraService(config["camera_index"])        # 3-р гишүүн
        self.camera.start()
        today = reg.load_day(self.clock.now().date().isoformat())  # 2-р гишүүн
        self.tracker = ActivityTracker(self.camera, self.clock, today, self.settings)   # 4-р гишүүн
        self.server = reg.start_server(self.clock) if config["admin"] else None
        self.connected = None                                      # админы компьютертэй холбогдсон уу
        self.seconds = 0
        self.tray_color = "green"

        self.build()
        self.tray = pystray.Icon("ProductivitySystem", dot("green"), "Ажлын бүтээмж", pystray.Menu(
            pystray.MenuItem("Нээх", self.from_tray(self.show), default=True),
            pystray.MenuItem("Зогсоох / Үргэлжлүүлэх", self.from_tray(self.toggle_pause)),
            pystray.MenuItem("Програмыг хаах", self.from_tray(self.quit_app))))
        self.tray.run_detached()
        if background:
            self.withdraw()
        self.after(1000, self.loop)
        self.after(200, self.show_frame)

    def build(self):
        ttk.Label(self, text=self.config_data["name"], font=("Segoe UI", 14, "bold")).pack(pady=8)
        self.status = tk.Label(self, font=("Segoe UI", 12, "bold"), fg="white", width=20)
        self.status.pack()
        self.info = ttk.Label(self, justify="center")
        self.info.pack(pady=6)
        self.apps = ttk.Treeview(self, columns=("time", "app"), show="headings", height=8)
        self.apps.heading("time", text="Хугацаа")
        self.apps.heading("app", text="Апп / сайт (өнөөдөр)")
        self.apps.column("time", width=80)
        self.apps.pack(fill="both", expand=True, padx=10)
        buttons = ttk.Frame(self)
        buttons.pack(pady=6)
        self.pause_button = ttk.Button(buttons, text="Зогсоох", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=3)
        ttk.Button(buttons, text="Камер харах", command=self.toggle_preview).pack(side="left", padx=3)
        if self.config_data["admin"]:
            ttk.Button(buttons, text="Самбар", command=self.open_dashboard).pack(side="left", padx=3)
        tk.Button(buttons, text="Програмаас гарах", bg="red", fg="white", command=self.quit_app).pack(
            side="left", padx=3)
        self.video = ttk.Label(self, compound="top")
        self.video.pack()
        ttk.Label(self, text=NOTICE, wraplength=480, foreground="gray").pack(pady=6)

    def from_tray(self, function):
        """Tray өөр thread-д ажилладаг тул функцийг цонхны thread дээр дуудна."""
        return lambda: self.after(0, function)

    def state(self):
        return "paused" if self.tracker.paused else self.tracker.status

    # -------------------------------------------------------------- секунд тутам
    def loop(self):
        self.after(1000, self.loop)
        today = self.clock.now().date().isoformat()
        if today != self.tracker.day["date"]:                      # шөнө дунд — шинэ өдөр
            reg.save_day(self.tracker.day)
            self.tracker.new_day(reg.load_day(today))
        old_state = self.state()
        self.tracker.tick()
        self.show_state()
        self.seconds += 1
        if self.seconds % 30 == 0:                                 # 30 сек тутам хадгална
            reg.save_day(self.tracker.day)
        if self.seconds % 60 == 1 or self.state() != old_state:    # минут тутам, төлөв солигдоход илгээнэ
            self.send()

    def show_state(self):
        tracker = self.tracker
        state = self.state()
        self.status.config(text=prod.STATUS_TEXT[state], bg=COLORS[state])
        server = {None: "...", True: "холбогдсон", False: "холбогдоогүй"}[self.connected]
        self.info.config(text=f"Ажилласан: {prod.fmt(tracker.day['work'])}     "
                              f"Гарсан: {prod.fmt(tracker.day['away'])}\n"
                              f"Одоогийн апп: {tracker.app or '—'}\n"
                              f"Камер: {CAMERA_TEXT[self.camera.state]}     Админ руу: {server}")
        self.apps.delete(*self.apps.get_children())
        for app, seconds in sorted(tracker.day["apps"].items(), key=lambda item: -item[1]):
            self.apps.insert("", "end", values=(prod.fmt(seconds), app))
        self.pause_button.config(text="Үргэлжлүүлэх" if tracker.paused else "Зогсоох")
        if COLORS[state] != self.tray_color:                       # tray дүрсний өнгө
            self.tray_color = COLORS[state]
            self.tray.icon = dot(self.tray_color)

    # -------------------------------------------------------------- админ руу илгээх
    def send(self, offline=False):
        """Өнөөдрийн бүртгэлийг админы компьютер руу илгээнэ (арын thread-д — цонх гацахгүй)."""
        live = {"status": "offline" if offline else self.state(), "app": self.tracker.app}
        data = {"uid": reg.make_uid(), "name": self.config_data["name"], "day": self.tracker.day, "live": live}
        text = json.dumps(data, ensure_ascii=False)                # яг одоогийн хуулбар
        if offline:
            reg.push(self.config_data["server"], text)
        else:
            threading.Thread(target=self.send_thread, args=(text,), daemon=True).start()

    def send_thread(self, text):
        answer = reg.push(self.config_data["server"], text)
        try:
            self.after(0, self.got_answer, answer)
        except RuntimeError:                                       # цонх аль хэдийн хаагдсан
            pass

    def got_answer(self, answer):
        self.connected = answer is not None
        if answer and "settings" in answer:
            self.clock.sync(answer["time"])                        # админы цаг = зөв цаг
            self.settings.update(answer["settings"])               # админы тохиргоо
            if self.config_data["settings"] != answer["settings"]:
                self.config_data["settings"] = answer["settings"]
                reg.save_config(self.config_data)

    # -------------------------------------------------------------- товчнууд
    def toggle_pause(self):
        self.tracker.set_paused(not self.tracker.paused)
        self.show_state()
        self.send()

    def toggle_preview(self):
        self.camera.preview = not self.camera.preview
        if not self.camera.preview:
            self.video.config(image="", text="")

    def show_frame(self):
        """«Камер харах» асаалттай үед 0.2 сек тутам камерын дүрсийг харуулна."""
        self.after(200, self.show_frame)
        result = self.camera.get_frame()
        if self.camera.preview and result:
            frame, faces = result
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)                  # OpenCV BGR → RGB
            self.photo = ImageTk.PhotoImage(Image.fromarray(rgb).resize((320, 240)))
            self.video.config(image=self.photo, text=f"Нүүр: {faces}")    # self.photo — устахгүйн тулд

    def open_dashboard(self):
        password = simpledialog.askstring("Самбар", "Админ нууц үг:", show="*", parent=self)
        if password is None:
            return
        if reg.hash_password(password) != self.config_data["password"]:
            messagebox.showerror("Самбар", "Нууц үг буруу.", parent=self)
            return
        Dashboard(self)

    def show(self):
        self.deiconify()
        self.lift()

    def quit_app(self):
        if not messagebox.askyesno("Гарах", "Програмыг бүрэн хаах уу? Цаг бүртгэхгүй болно.", parent=self):
            return
        reg.save_day(self.tracker.day)
        self.send(offline=True)                                    # самбарт "Офлайн" болно
        self.camera.stop()
        self.tray.stop()
        if self.server:
            self.server.shutdown()
        self.destroy()


# ------------------------------------------------------------------ админы самбар
class Dashboard(tk.Toplevel):
    """Ажилтнууд, 7 хоног, Хэрэглэгчид, Тохиргоо. 5 секунд тутам шинэчилнэ."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Самбар (админ)")
        self.geometry("1200x600")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.job = None
        self.rows = []

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Өдөр:").pack(side="left")
        today = app.clock.now().date()
        self.day = ttk.Combobox(top, state="readonly", width=12,
                                values=[(today - timedelta(days=i)).isoformat() for i in range(30)])
        self.day.current(0)
        self.day.bind("<<ComboboxSelected>>", self.refresh)
        self.day.pack(side="left", padx=4)
        ttk.Button(top, text="CSV хадгалах", command=self.save_csv).pack(side="left")
        ttk.Label(top, text="  Мөр дээр давхар дарвал дэлгэрэнгүй", foreground="gray").pack(side="left")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=4)
        self.people = make_table(tabs, "Ажилтнууд", prod.COLUMNS)
        self.people.bind("<Double-1>", self.show_detail)
        self.week = make_table(tabs, "7 хоног", ["Нэр", "0", "1", "2", "3", "4", "5", "6"])
        self.users = make_table(tabs, "Хэрэглэгчид", ["ID", "Нэр", "Хэлтэс"])
        self.users.bind("<<TreeviewSelect>>", self.pick_user)
        self.user_form(self.users.master)
        self.settings_tab(tabs)
        self.load_users()
        self.refresh()

    def destroy(self):
        if self.job:
            self.after_cancel(self.job)                            # 5 сек тутмын шинэчлэлийг зогсооно
        super().destroy()

    def refresh(self, event=None):
        """Хүснэгтүүдийг серверийн JSON файлуудаас дахин уншина."""
        if self.job:
            self.after_cancel(self.job)
        day = self.day.get()
        settings = reg.load_settings()
        now, now_ts = self.app.clock.now(), self.app.clock.timestamp()
        week = prod.week_days(day)
        for i, d in enumerate(week):
            self.week.heading(str(i), text=d[5:])
        self.rows = []
        self.people.delete(*self.people.get_children())
        self.week.delete(*self.week.get_children())
        for uid, user in reg.list_users().items():
            if user.get("deleted") or user["created"] > day:
                continue
            row = prod.person_row(user, reg.load_person_day(uid, day), reg.load_live(uid), settings, day, now, now_ts)
            self.rows.append(row)
            self.people.insert("", "end", iid=uid, values=list(row.values()))
            cells = [prod.week_cell(reg.load_person_day(uid, d), settings, d, now) if d >= user["created"] else ""
                     for d in week]
            self.week.insert("", "end", values=[user["name"]] + cells)
        self.job = self.after(5000, self.refresh)

    def show_detail(self, event):
        uid = self.people.focus()
        if not uid:
            return
        day = self.day.get()
        text = prod.report_text(reg.list_users()[uid], reg.load_person_day(uid, day), reg.load_settings(),
                                day, self.app.clock.now())
        window = tk.Toplevel(self)
        window.title("Дэлгэрэнгүй")
        box = tk.Text(window, width=80, height=30, font=("Consolas", 10))
        box.pack(fill="both", expand=True)
        box.insert("1.0", text)

    def save_csv(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"butemj_{self.day.get()}.csv")
        if path:
            prod.export_csv(path, self.rows)
            messagebox.showinfo("CSV", "Хадгаллаа.", parent=self)

    # -------------------------------------------------------------- хэрэглэгчид
    def user_form(self, frame):
        form = ttk.Frame(frame)
        form.pack(fill="x", pady=6)
        self.user_name = tk.StringVar()
        self.user_department = tk.StringVar()
        ttk.Label(form, text="Нэр:").pack(side="left")
        ttk.Entry(form, textvariable=self.user_name, width=25).pack(side="left", padx=4)
        ttk.Label(form, text="Хэлтэс:").pack(side="left")
        ttk.Entry(form, textvariable=self.user_department, width=25).pack(side="left", padx=4)
        ttk.Button(form, text="Хадгалах", command=self.save_user).pack(side="left", padx=4)
        ttk.Button(form, text="Устгах", command=self.delete_user).pack(side="left")

    def load_users(self):
        self.users.delete(*self.users.get_children())
        for uid, user in reg.list_users().items():
            if not user.get("deleted"):
                self.users.insert("", "end", iid=uid, values=(uid, user["name"], user["department"]))

    def pick_user(self, event):
        user = reg.list_users().get(self.users.focus())
        if user:
            self.user_name.set(user["name"])
            self.user_department.set(user["department"])

    def save_user(self):
        uid = self.users.focus()
        if not uid or not self.user_name.get().strip():
            messagebox.showerror("Алдаа", "Хэрэглэгч сонгоод нэрийг бичнэ үү.", parent=self)
            return
        reg.update_user(uid, self.user_name.get().strip(), self.user_department.get().strip())
        self.load_users()
        self.refresh()

    def delete_user(self):
        uid = self.users.focus()
        if uid and messagebox.askyesno("Устгах", f"{uid}-ийн бүх түүхийг устгах уу?", parent=self):
            reg.delete_user(uid)
            self.load_users()
            self.refresh()

    # -------------------------------------------------------------- тохиргоо
    def settings_tab(self, tabs):
        frame = ttk.Frame(tabs, padding=10)
        tabs.add(frame, text="Тохиргоо")
        settings = reg.load_settings()
        self.fields = {}
        for row, (key, label) in enumerate(SETTING_LABELS.items()):
            value = settings[key]
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            self.fields[key] = tk.StringVar(value=str(value))
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(frame, textvariable=self.fields[key], width=60).grid(row=row, column=1, padx=6)
        ttk.Button(frame, text="Хадгалах", command=self.save_settings).grid(row=len(SETTING_LABELS), column=1,
                                                                            sticky="w", pady=8)

    def save_settings(self):
        try:
            settings = prod.parse_settings({key: var.get() for key, var in self.fields.items()})
        except ValueError:
            messagebox.showerror("Алдаа", "Цагийг ЦЦ:ММ, тоог бүхэл тоогоор бичнэ үү.", parent=self)
            return
        reg.save_settings(settings)
        self.app.settings.update(settings)
        messagebox.showinfo("Тохиргоо", "Хадгаллаа. Ажилтнуудын компьютерт 1 минутын дотор хүчинтэй болно.",
                            parent=self)


def main():
    config = reg.load_config()
    if "--admin" in sys.argv:
        admin_setup(config)
    lock = single_instance()
    if lock is None:                                               # аль хэдийн ажиллаж байна
        if "--background" not in sys.argv:
            tk.Tk().withdraw()
            messagebox.showinfo("Ажлын бүтээмж", "Програм аль хэдийн ажиллаж байна (tray дүрсийг дарна уу).")
        return
    if not config["consent"] and not first_run(config):
        return
    set_autostart(config["autostart"])
    try:
        app = App(config, "--background" in sys.argv)
    except (RuntimeError, OSError) as error:                       # камерын сан буруу, порт эзлэгдсэн г.м.
        messagebox.showerror("Ажлын бүтээмж", str(error))
        return
    app.mainloop()


if __name__ == "__main__":
    main()
