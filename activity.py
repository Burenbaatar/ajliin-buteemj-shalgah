"""4-р гишүүн — зөвшөөрөлтэй идэвхийн хэмжилт.

Секунд тутам: урд талын цонх, хулганы доорх цонх (програм + гарчиг), нээлттэй програмууд,
гар/хулгана хөдөлсөн эсэх. Товчлуурын даралт, дэлгэцийн зураг, хуудасны агуулга авахгүй.
"""
import ctypes
import os
import time

user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
BROWSERS = ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def app_name(hwnd):
    """Цонх аль програмынх болохыг (жишээ нь chrome.exe) Windows-оос асууна."""
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process = kernel32.OpenProcess(0x1000, False, pid.value)          # 0x1000 = зөвхөн нэр унших эрх
    path, size = ctypes.create_unicode_buffer(260), ctypes.c_ulong(260)
    kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size))
    kernel32.CloseHandle(process)
    return os.path.basename(path.value) or "тодорхойгүй"


def clean_title(app, title):
    """Браузерын гарчгийн төгсгөлийн «- Google Chrome», «— Mozilla Firefox» гэх мэтийг хасна."""
    end = max(title.rfind(" - "), title.rfind(" — "))           # хамгийн сүүлийн тусгаарлагч
    return title[:end] if app.lower() in BROWSERS and end > 0 else title


def window_name(hwnd):
    """«програм - гарчиг»: chrome.exe - Lofi music - YouTube, WINWORD.EXE - Тайлан.docx - Word."""
    app = app_name(hwnd)
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title, 512)
    title = clean_title(app, title.value)[:100]
    return f"{app} - {title}" if title else app


def active_app():
    """Урд талд (ажиллаж) байгаа цонх."""
    return window_name(user32.GetForegroundWindow())


def mouse_app():
    """Хулганы заагч аль цонхон дээр байгааг уншина. Хулганыг хөдөлгөхгүй."""
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return window_name(user32.GetAncestor(user32.WindowFromPoint(point), 2))   # 2 = үндсэн цонх


def open_apps():
    """Одоо цонхтой ажиллаж байгаа бүх програм (ард байгаа нь ч орно)."""
    found = set()

    def add(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
            found.add(app_name(hwnd))
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(add), 0)
    return sorted(found)


def idle_seconds():
    """Гар, хулгана сүүлд хөдөлснөөс хойш хэдэн секунд болсон бэ."""
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    user32.GetLastInputInfo(ctypes.byref(info))
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000


def empty_delta():
    """Админ руу илгээх өсөлт: ажилласан/гарсан секунд, апп, хулгана, минут бүрийн төлөв."""
    return {"work": 0, "away": 0, "apps": {}, "mouse": {}, "minutes": {}}


class ActivityTracker:
    def __init__(self):
        self.away_after = 60    # гар, хулгана ийм секунд хөдлөөгүй бол «гарсан» (админы тохиргооноос шинэчлэгдэнэ)
        self.apps = {}          # энэ хэмжилтэд урд талд байсан цонх → секунд (граф)
        self.app = self.mouse_on = None
        self.open = []
        self.status = "away"
        self.paused = False
        self.verified = True    # False бол ажилласан гэж тоолохгүй (камер ажилтныг өөрийг нь баталгаажуулаагүй)
        self.last = None        # сүүлд хэмжсэн мөч; None = хэмжихгүй
        self.delta = empty_delta()

    def start(self):
        self.last = time.monotonic()      # monotonic — компьютерийн цагийг өөрчилсөн ч зөв хэмжинэ
        self.paused = False

    def resume(self):
        self.paused = False

    @property
    def running(self):
        """Яг одоо хэмжиж байна уу (түр зогсоогоогүй). Камер хугацааг зөвхөн энэ үед тоолно."""
        return self.last is not None and not self.paused

    def pause(self):
        self.paused = True                # түр зогссон хугацаа «гарсан» болж тоологдоно

    def tick(self):
        """Секунд тутам: өнгөрсөн хугацааг төлөвт нь, ажиллаж байсан бол цонхонд нь нэмнэ."""
        if self.last is not None:
            now = time.monotonic()
            spent, self.last = now - self.last, now
            self.app, self.mouse_on, self.open = active_app(), mouse_app(), open_apps()
            working = not self.paused and idle_seconds() < self.away_after and self.verified
            self.status = "work" if working else "away"
            self.delta[self.status] += spent
            minute = time.strftime("%H:%M")
            if working or minute not in self.delta["minutes"]:
                self.delta["minutes"][minute] = self.status
            if working:
                for totals, name in ((self.apps, self.app), (self.delta["apps"], self.app),
                                     (self.delta["mouse"], self.mouse_on)):
                    totals[name] = totals.get(name, 0) + spent
        return {"app": self.app, "mouse": self.mouse_on, "open": self.open, "status": self.status,
                "total_seconds": sum(self.apps.values())}

    def take_delta(self):
        """Сүүлд авснаас хойших өсөлтийг буцааж, шинээр тоолж эхэлнэ."""
        delta, self.delta = self.delta, empty_delta()
        return delta

    def stop(self):
        self.tick()
        self.last = None
        return {"total_seconds": round(sum(self.apps.values()), 1),
                "apps": {name: round(seconds, 1) for name, seconds in self.apps.items()}}
