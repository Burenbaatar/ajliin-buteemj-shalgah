import csv
import ctypes
import os
import sys
import time
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk
from ctypes import wintypes


POLL_INTERVAL_MS = 1000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def foreground_process_name():
    if sys.platform != "win32":
        raise OSError("Энэ програм зөвхөн Windows дээр ажиллана.")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    )
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = (
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    window = user32.GetForegroundWindow()
    if not window:
        raise ctypes.WinError(ctypes.get_last_error())

    process_id = wintypes.DWORD()
    if not user32.GetWindowThreadProcessId(window, ctypes.byref(process_id)):
        raise ctypes.WinError(ctypes.get_last_error())
    if process_id.value == os.getpid():
        return None

    process = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value
    )
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        image_path = ctypes.create_unicode_buffer(32768)
        path_length = wintypes.DWORD(len(image_path))
        if not kernel32.QueryFullProcessImageNameW(
            process, 0, image_path, ctypes.byref(path_length)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return os.path.basename(image_path.value)
    finally:
        kernel32.CloseHandle(process)


def timestamp_now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class ActivityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Компьютерийн хэрэглээний хураангуй")
        self.root.resizable(False, False)

        self.started_at = None
        self.ended_at = None
        self.last_sample_at = None
        self.last_process = None
        self.process_seconds = {}
        self.running = False
        self.finished = False
        self.after_id = None

        frame = ttk.Frame(root, padding=16)
        frame.grid()

        ttk.Label(
            frame,
            text=(
                "Зөвхөн хэмжилт эхэлсний дараа урд талын програмын нэр, "
                "идэвхтэй секундийг бүртгэнэ.\n"
                "Товчлуур, нууц үг, чат/вебийн агуулга, дэлгэцийн зураг "
                "цуглуулахгүй.\n"
                "Хугацааг time.monotonic()-оор хэмжинэ: системийн цаг "
                "өөрчлөгдсөн ч хугацаа тогтвортой."
            ),
            justify="left",
            wraplength=480,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        self.status_var = tk.StringVar(value="Хэмжилт эхлээгүй.")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.start_button = ttk.Button(
            frame, text="Хэмжилт эхлэх", command=self.start_or_resume
        )
        self.start_button.grid(row=2, column=0, padx=(0, 6), sticky="ew")
        self.pause_button = ttk.Button(
            frame, text="Түр зогсоох", command=self.pause, state="disabled"
        )
        self.pause_button.grid(row=2, column=1, padx=6, sticky="ew")
        self.finish_button = ttk.Button(
            frame, text="Дуусгах", command=self.finish, state="disabled"
        )
        self.finish_button.grid(row=2, column=2, padx=(6, 0), sticky="ew")

        self.summary = tk.Text(frame, width=62, height=10, state="disabled")
        self.summary.grid(row=3, column=0, columnspan=3, pady=(12, 0))

        if sys.platform != "win32":
            self.status_var.set("Энэ програм зөвхөн Windows дээр ажиллана.")
            self.start_button.configure(state="disabled")

    def start_or_resume(self):
        if self.finished:
            return

        now = time.monotonic()
        try:
            process_name = foreground_process_name()
        except OSError as error:
            messagebox.showerror("Хэмжилт эхэлсэнгүй", str(error), parent=self.root)
            return

        if self.started_at is None:
            self.started_at = timestamp_now()

        self.last_sample_at = now
        self.last_process = process_name
        self.running = True
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.finish_button.configure(state="normal")
        if process_name is None:
            self.status_var.set("Таны энэ цонх урд талд байна; одоогоор бүртгэлгүй.")
        else:
            self.status_var.set("Хэмжиж байна. Идэвхтэй програм: " + process_name)
        self._schedule_sample()

    def _schedule_sample(self):
        self.after_id = self.root.after(POLL_INTERVAL_MS, self._sample)

    def _sample(self):
        now = time.monotonic()
        self._record_elapsed(now)
        try:
            self.last_process = foreground_process_name()
        except OSError as error:
            self._stop_after_error(error)
            return

        self.last_sample_at = now
        if self.last_process is None:
            self.status_var.set("Таны энэ цонх урд талд байна; одоогоор бүртгэлгүй.")
        else:
            self.status_var.set("Хэмжиж байна. Идэвхтэй програм: " + self.last_process)
        self._schedule_sample()

    def _record_elapsed(self, now):
        if self.last_sample_at is not None and self.last_process is not None:
            elapsed = max(0.0, now - self.last_sample_at)
            self.process_seconds[self.last_process] = (
                self.process_seconds.get(self.last_process, 0.0) + elapsed
            )
        self.last_sample_at = now

    def pause(self):
        if not self.running:
            return
        self._record_elapsed(time.monotonic())
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.start_button.configure(text="Үргэлжлүүлэх", state="normal")
        self.pause_button.configure(state="disabled")
        self.status_var.set("Түр зогсоосон. Энэ хугацаанд бүртгэл хийгдэхгүй.")

    def finish(self):
        if self.finished or self.started_at is None:
            return
        if self.running:
            self._record_elapsed(time.monotonic())
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.running = False
        self.finished = True
        self.ended_at = timestamp_now()
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.finish_button.configure(state="disabled")
        self.status_var.set("Хэмжилт дууссан.")
        self._show_summary()

        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Хураангуй CSV файлыг хадгалах",
            defaultextension=".csv",
            filetypes=(("CSV файл", "*.csv"),),
            initialfile="activity_summary.csv",
        )
        if not path:
            messagebox.showinfo(
                "Хадгалаагүй",
                "Хураангуйг цонхонд харуулсан боловч файлд хадгалсангүй.",
                parent=self.root,
            )
            return

        try:
            self._save_csv(path)
        except OSError as error:
            messagebox.showerror("Файл хадгалж чадсангүй", str(error), parent=self.root)
            return
        messagebox.showinfo("Хадгаллаа", "Хураангуй хадгалагдлаа:\n" + path, parent=self.root)

    def _show_summary(self):
        lines = [
            "Эхэлсэн: " + self.started_at,
            "Дууссан: " + self.ended_at,
            "",
        ]
        if self.process_seconds:
            lines.extend(
                "{} — {:.1f} секунд".format(name, seconds)
                for name, seconds in sorted(
                    self.process_seconds.items(), key=lambda item: item[1], reverse=True
                )
            )
        else:
            lines.append("Хэмжигдсэн идэвхтэй хугацаа алга.")
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", "\n".join(lines))
        self.summary.configure(state="disabled")

    def _save_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                (
                    "process_name",
                    "active_seconds",
                    "measurement_started_at",
                    "measurement_ended_at",
                )
            )
            for name, seconds in sorted(self.process_seconds.items()):
                writer.writerow(
                    (name, round(seconds, 1), self.started_at, self.ended_at)
                )
            if not self.process_seconds:
                writer.writerow(("", 0, self.started_at, self.ended_at))

    def _stop_after_error(self, error):
        self.running = False
        self.finished = True
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.finish_button.configure(state="disabled")
        self.status_var.set("Алдааны улмаас хэмжилт зогссон.")
        messagebox.showerror(
            "Хэмжилтийн алдаа",
            "Урд талын програмын нэрийг уншиж чадсангүй. Хэмжилт зогслоо:\n"
            + str(error),
            parent=self.root,
        )


if __name__ == "__main__":
    root = tk.Tk()
    ActivityApp(root)
    root.mainloop()
