"""5-р гишүүн — гүйцэтгэлийн хувь ба тайлан."""
import time


def calculate_completion(target, completed):
    if target <= 0 or not 0 <= completed <= target:
        raise ValueError("Гүйцэтгэл 0-ээс төлөвлөсөн тоо хүртэл байна.")
    return round(completed / target * 100, 1)


def build_report(employee, activity_summary):
    return {"name": employee["name"], "target": employee["target"], "completed": employee["completed"],
            "completion_rate": calculate_completion(employee["target"], employee["completed"]),
            "activity_seconds": activity_summary.get("total_seconds", 0),
            "date": time.strftime("%Y-%m-%d %H:%M")}


def report_text(report):
    return (f"Ажилтан: {report['name']}\n"
            f"Даалгавар: {report['completed']} / {report['target']}\n"
            f"Биелэлт: {report['completion_rate']}%\n"
            f"Идэвхтэй хугацаа: {report['activity_seconds']:.0f} сек\n"
            f"Огноо: {report['date']}")
