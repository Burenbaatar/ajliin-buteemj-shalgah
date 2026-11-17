"""Бүтээмж тооцоолж, тайланг уншихад ойлгомжтой текст болгон бэлтгэнэ.

Энэ модуль Tkinter ашиглахгүй, JSON файлд мэдээлэл хадгалахгүй.
JSON хадгалалтыг register.py хариуцах бөгөөд энд энгийн Python dict бэлтгэнэ.
"""

from datetime import datetime
import math
from typing import Any


def calculate_completion(target: int, completed: int) -> float:
    """Төлөвлөсөн ажлаас дуусгасан ажлын биелэлтийн хувийг тооцоолж буцаана."""
    if not isinstance(target, int) or isinstance(target, bool):
        raise ValueError("Төлөвлөсөн ажил бүхэл тоо байх ёстой")
    if not isinstance(completed, int) or isinstance(completed, bool):
        raise ValueError("Дууссан ажил бүхэл тоо байх ёстой")
    if target <= 0:
        raise ValueError("Төлөвлөсөн ажил 0-ээс их байх ёстой")
    if completed < 0 or completed > target:
        raise ValueError("Дууссан ажил 0-ээс target хүртэл байна")
    return round(completed / target * 100, 1)


def _nonnegative_seconds(value: Any) -> float:
    """Хугацааны тоон утгыг хязгаартай, сөрөг биш секунд болгон хувиргана."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    seconds = float(value)
    if not math.isfinite(seconds) or seconds < 0:
        return 0.0
    return round(seconds, 1)


def build_report(employee: dict, activity_summary: dict) -> dict:
    """Тайлангийн dict үүсгэнэ; register.py файлд хадгалах үүрэгтэй."""
    if not isinstance(employee, dict):
        raise ValueError("Ажилтны мэдээлэл dict байх ёстой")
    if not isinstance(activity_summary, dict):
        activity_summary = {}

    target = employee.get("target")
    completed = employee.get("completed")
    completion_rate = calculate_completion(target, completed)

    report = {
        "employee_id": employee.get("id", ""),
        "name": str(employee.get("name", "Нэргүй ажилтан")),
        "target": target,
        "completed": completed,
        "completion_rate": completion_rate,
        "activity_seconds": _nonnegative_seconds(
            activity_summary.get("total_seconds", 0)
        ),
        "date": datetime.now().isoformat(timespec="seconds"),
    }
    apps = activity_summary.get("apps", [])
    if isinstance(apps, (list, dict)):
        report["apps"] = apps
    else:
        report["apps"] = []
    return report


def report_text(report: dict) -> str:
    """Тайланг Tkinter-ийн Label эсвэл Text-д харуулах текст болгоно."""
    if not isinstance(report, dict):
        report = {}

    name = str(report.get("name") or "Нэргүй ажилтан")
    target = report.get("target", "—")
    completed = report.get("completed", "—")
    rate = report.get("completion_rate")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(float(rate)):
        rate_text = "Тооцоолоогүй"
    else:
        rate_text = f"{rate:.1f}%"

    seconds = _nonnegative_seconds(report.get("activity_seconds", 0))
    minutes = seconds / 60
    return (
        f"Ажилтан: {name}\n"
        f"Даалгавар: {completed} / {target}\n"
        f"Биелэлт: {rate_text}\n"
        f"Зөвшөөрсөн аппын идэвхтэй хугацаа: {seconds:.1f} секунд "
        f"({minutes:.1f} минут)\n"
        f"Тайлангийн огноо: {report.get('date', '—')}"
    )
