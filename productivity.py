"""5-р гишүүн — идэвхийн хураангуй: програм, сайт тус бүрт зарцуулсан хугацаа, камерын шалгалт."""
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


def camera_totals(summaries):
    """Олон хэмжилтийн камерын хураангуйг нэгтгэнэ: {"other_seconds": 12.0, "unverified_seconds": 5.0, ...}.
    Камер ажиллаагүй хэмжилтүүд тооцогдохгүй. Нэг ч камертай хэмжилт байхгүй бол хоосон dict."""
    totals = {}
    for summary in summaries:
        for name, value in (summary.get("camera") or {}).items():
            totals[name] = totals.get(name, 0) + value
    return totals


def minutes(seconds):
    return f"{seconds / 60:.1f} мин"
