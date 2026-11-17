"""4-р гишүүн — зөвшөөрөлтэй идэвхийн хэмжилт: урд талын програмын нэр ба хугацаа."""
import ctypes
import os
import time


def active_app():
    """Урд талын цонх аль програмынх болохыг Windows-оос асууна (жишээ нь Code.exe).
    Програмын нэр болон танигдсан сайтын нэрийг уншина; хуудасны агуулга авахгүй."""
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process = kernel32.OpenProcess(0x1000, False, pid.value)          # 0x1000 = зөвхөн нэр унших эрх
    path, size = ctypes.create_unicode_buffer(260), ctypes.c_ulong(260)
    kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size))
    kernel32.CloseHandle(process)
    app = os.path.basename(path.value) or "тодорхойгүй"
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title, len(title))
    title = title.value.casefold()
    for site in ("YouTube", "Facebook", "Instagram", "Gmail"):
        if site.casefold() in title:
            return f"{app} - {site}"
    return app


class ActivityTracker:
    def __init__(self):
        self.apps = {}          # програмын нэр → секунд
        self.app = None         # одоо урд талд байгаа програм
        self.last = None        # сүүлд хэмжсэн мөч; None = хэмжихгүй (зогссон)

    def start(self):
        self.last = time.monotonic()      # monotonic — компьютерийн цагийг өөрчилсөн ч зөв хэмжинэ

    def resume(self):
        self.start()

    def pause(self):
        self.tick()
        self.last = None

    def tick(self):
        """Секунд тутам дуудна: өнгөрсөн хугацааг урд талын програмд нэмнэ."""
        if self.last is not None:
            now = time.monotonic()
            self.app = active_app()
            self.apps[self.app] = self.apps.get(self.app, 0) + now - self.last
            self.last = now
        return {"app": self.app, "total_seconds": sum(self.apps.values())}

    def stop(self):
        self.pause()
        return {"total_seconds": round(sum(self.apps.values()), 1),
                "apps": {name: round(seconds, 1) for name, seconds in self.apps.items()}}
