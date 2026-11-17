"""5-р гишүүн — идэвхийн хураангуй: програм, сайт тус бүрт зарцуулсан хугацаа."""
from activity import SITES


def total_apps(summaries):
    """Олон хэмжилтийн програм, сайтын хугацааг нэгтгэнэ: {"Code.exe": 60.0, "chrome.exe - YouTube": 30.0}."""
    apps = {}
    for summary in summaries:
        for name, seconds in summary.get("apps", {}).items():
            apps[name] = apps.get(name, 0) + seconds
    return apps


def site_times(apps):
    """4 сайт тус бүрийн нийт хугацаа: {"YouTube": 30.0, "Facebook": 0, ...}."""
    return {site: sum(seconds for name, seconds in apps.items() if name.endswith(" - " + site)) for site in SITES}


def top_app(apps):
    """Хамгийн их хугацаа зарцуулсан програм эсвэл сайт."""
    return max(apps, key=apps.get) if apps else "—"


def minutes(seconds):
    return f"{seconds / 60:.1f} мин"
