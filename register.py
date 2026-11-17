"""2-р гишүүн — ажилтны бүртгэл, JSON хадгалалт ба админы JSON сервер."""
import hashlib
import json
import os
import socket
import sys
import time

PORT = 5050                                    # ажилтнууд админы компьютерийн энэ порт руу холбогдоно
LIVE = {}                                      # ажилтны id → шууд төлөв (зөвхөн санах ойд, файлд биш)
DEFAULT_SETTINGS = {"work_start": "09:00", "work_end": "18:00", "late_grace_min": 5, "away_after_sec": 60,
                    "unproductive": ["YouTube", "Facebook", "Instagram"]}


def get_data_dir():
    """Өгөгдлийн хавтас: програмын (main.py эсвэл .exe) хажууд байх data хавтас.
    Програмыг хаанаас ч нээсэн ижил хавтсыг ашиглана. .exe дотор биш тул хаагаад нээсэн ч үлдэнэ."""
    folder = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "data")
    os.makedirs(folder, exist_ok=True)
    return folder


def my_address():
    """Энэ компьютерийн дотоод сүлжээний IP хаяг — ажилтнууд «Админы компьютер» талбарт үүнийг бичнэ."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))     # UDP: юу ч илгээхгүй, аль сүлжээгээр гарахыг л асууна
            return probe.getsockname()[0]
    except OSError:
        return socket.gethostname()


def load(name):
    """name.json-оос өгөгдөл уншина. Файл байхгүй бол хоосон жагсаалт."""
    path = os.path.join(get_data_dir(), name + ".json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as file:
        return json.load(file)[name]


def save(name, items):
    with open(os.path.join(get_data_dir(), name + ".json"), "w", encoding="utf-8") as file:
        json.dump({name: items}, file, ensure_ascii=False, indent=2)


def load_settings():
    return dict(DEFAULT_SETTINGS, **(load("settings") or {}))


def save_settings(settings):
    save("settings", settings)


# ---------------------------------------------------------------- ажилтан
def list_employees():
    return load("employees")


def hash_text(text):
    """Нууц үг, кодыг буцааж тайлж болохгүй SHA-256 хэш болгоно — файлд зөвхөн хэш хадгална."""
    return hashlib.sha256(text.encode()).hexdigest()


def add_employee(name, code, department=""):
    """Шинэ ажилтан бүртгэнэ. Ийм нэртэй ажилтан байвал код, хэлтсийг нь шинэчилнэ."""
    name = name.strip()
    if not name:
        raise ValueError("Ажилтны нэр хоосон байна.")
    if len(code) < 4:
        raise ValueError("Код дор хаяж 4 тэмдэгт байна.")
    employees = load("employees")
    found = [employee for employee in employees if employee["name"].casefold() == name.casefold()]
    if found:
        employee = found[0]
    else:
        employee = {"id": str(time.time_ns()), "name": name}
        employees.append(employee)
    employee["code"], employee["department"] = hash_text(code), department.strip()
    save("employees", employees)
    return employee


def delete_employee(employee_id):
    save("employees", [employee for employee in load("employees") if employee["id"] != employee_id])
    delete_face(employee_id)                                    # нүүрний хээг хамт устгана


def get_face(employee_id):
    """Ажилтны нүүрний хээ (128 тоо). Бүртгээгүй бол None."""
    return next((face["feature"] for face in load("faces") if face["employee_id"] == employee_id), None)


def save_face(employee_id, feature):
    """Зураг биш, зөвхөн нүүрний хээг (128 тоо) админы компьютерт хадгална. Нэг удаа л бүртгэнэ —
    ажилтан өөрийн нүүрийг өөр хүнийхээр солихоос сэргийлж, шинэчлэхийг зөвхөн админ зөвшөөрнө."""
    find_employee(employee_id)
    if get_face(employee_id):
        raise ValueError("Нүүр аль хэдийн бүртгэгдсэн. Шинэчлэх бол админд хандана уу.")
    if not isinstance(feature, list) or len(feature) != 128 or \
            not all(isinstance(value, (int, float)) for value in feature):
        raise ValueError("Нүүрний хээ буруу.")
    save("faces", load("faces") + [{"employee_id": employee_id, "feature": [round(float(v), 5) for v in feature]}])


def delete_face(employee_id):
    """Админ ажилтны нүүрийг устгаснаар ажилтан дахин бүртгүүлэх боломжтой болно."""
    save("faces", [face for face in load("faces") if face["employee_id"] != employee_id])


def find_employee(employee_id):
    employee = next((e for e in list_employees() if e["id"] == employee_id), None)
    if employee is None:
        raise ValueError("Ажилтан олдсонгүй.")
    return employee


# ---------------------------------------------------------------- өдрийн бичлэг ба шууд төлөв
def day_records(date):
    """Тухайн өдрийн бүх ажилтны бичлэг: {ажилтны id: бичлэг}. date = "2026-11-17"."""
    return {record["employee_id"]: record for record in load("day-" + date)}


def save_day_delta(employee_id, computer, open_apps, delta):
    """Ажилтны илгээсэн өсөлтийг өнөөдрийн бичлэгт нэмнэ (data/day-ОООО-СС-ӨӨ.json)."""
    date = time.strftime("%Y-%m-%d")
    records = day_records(date)
    record = records.setdefault(employee_id, {"employee_id": employee_id, "work": 0, "away": 0,
                                              "apps": {}, "mouse": {}, "minutes": {}})
    record["computer"], record["open"] = computer, open_apps
    record["work"] += delta["work"]
    record["away"] += delta["away"]
    for key in ("apps", "mouse"):
        for name, seconds in delta[key].items():
            record[key][name] = record[key].get(name, 0) + seconds
    for minute, status in delta["minutes"].items():
        if status == "work" or minute not in record["minutes"]:
            record["minutes"][minute] = status
    for name, value in delta.get("camera", {}).items():        # камерын шалгалт: өөрөө, өөр хүн, хүн алга...
        record.setdefault("camera", {})[name] = record.get("camera", {}).get(name, 0) + value
    save("day-" + date, list(records.values()))


def live_status(employee_id):
    """Ажилтны шууд төлөв. 30 секунд мэдээлэл ирээгүй бол None (офлайн)."""
    live = LIVE.get(employee_id)
    return live if live and time.time() - live["time"] < 30 else None


def save_pause(employee_id, reason):
    """Ажилтан түр зогсоосон шалтгааныг цагтай нь pauses.json-д хадгална."""
    employee = find_employee(employee_id)
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Шалтгаанаа бичнэ үү.")
    pause = {"employee_id": employee_id, "employee_name": employee["name"],
             "reason": reason.strip(), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save("pauses", load("pauses") + [pause])


def pauses_today(employee_id):
    today = time.strftime("%Y-%m-%d")
    return [item for item in load("pauses") if item["employee_id"] == employee_id and item["time"].startswith(today)]


# ---------------------------------------------------------------- админы эрх
def check_password(password):
    """Админы нууц үгийг шалгана. Анх оруулсан нууц үг хадгалагдана — файлд зөвхөн хэш нь бичигдэнэ."""
    hashed = hash_text(password)
    saved = load("admin")
    if not saved:
        save("admin", [hashed])
        return True
    return saved[0] == hashed


# ---------------------------------------------------------------- JSON сервер (админы компьютер)
def start_server():
    """Админы компьютер дээр сервер нээнэ."""
    server = socket.socket()
    server.bind(("0.0.0.0", PORT))
    server.listen()
    server.setblocking(False)                  # хүсэлт байхгүй үед хүлээхгүй — цонх гацахгүй
    return server


def serve(server):
    """Ирсэн хүсэлт бүрт JSON хариу өгнө. main.py үүнийг 0.1 сек тутам дуудна."""
    while True:
        try:
            conn, _ = server.accept()
        except BlockingIOError:                # хүлээж буй хүсэлт алга
            return
        with conn:
            try:
                conn.settimeout(3)
                conn.sendall(json.dumps(answer(conn), ensure_ascii=False).encode())
            except OSError:                    # ажилтны компьютер холболтоо тасалсан
                pass


def answer(conn):
    try:
        return handle(json.loads(receive(conn)))
    except (ValueError, KeyError) as error:
        return {"error": str(error)}


def handle(request):
    """Ажилтны хүсэлт: нэвтрэх, нүүр бүртгүүлэх, шууд төлөв + өсөлт илгээх, түр зогсоосон шалтгаан."""
    if request["action"] == "login":           # бусдын мэдээлэл, кодыг ажилтанд илгээхгүй
        name = request["name"].strip()
        found = [e for e in list_employees() if e["name"].casefold() == name.casefold()]
        if not found:
            raise ValueError(f"«{name}» нэртэй ажилтан энэ админы бүртгэлд алга. Админ «Хэрэглэгчид» таб дээр бүртгэнэ.")
        if not found[0].get("code"):
            raise ValueError("Танд код өгөөгүй байна. Админ таны нэрийг кодтой нь дахин бүртгэнэ.")
        if found[0]["code"] != hash_text(request["code"]):
            raise ValueError("Код буруу.")
        return {"id": found[0]["id"], "name": found[0]["name"], "face": get_face(found[0]["id"])}   # камер харьцуулах хээ
    if request["action"] == "face":
        save_face(request["employee_id"], request["feature"])
        return {"ok": True}
    if request["action"] == "live":
        find_employee(request["employee_id"])
        for delta in request["deltas"]:
            save_day_delta(request["employee_id"], request["computer"], request["open"], delta)
        LIVE[request["employee_id"]] = {key: request[key] for key in ("status", "app", "mouse", "reason")}
        LIVE[request["employee_id"]]["time"] = time.time()
        return {"settings": load_settings()}    # ажилтан «гарсан» гэж үзэх хугацааг эндээс мэднэ
    if request["action"] == "pause":
        save_pause(request["employee_id"], request["reason"])
        return {"ok": True}
    raise ValueError("Үл мэдэгдэх хүсэлт.")


def receive(conn):
    """Нөгөө тал илгээж дуустал бүх өгөгдлийг уншина."""
    data = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            return data.decode()
        data += chunk


# ---------------------------------------------------------------- клиент (ажилтны компьютер)
def ask(host, request, timeout=3):
    """Админы сервер рүү JSON хүсэлт илгээж хариу авна. Холбогдохгүй бол OSError."""
    with socket.create_connection((host, PORT), timeout=timeout) as conn:
        conn.sendall(json.dumps(request, ensure_ascii=False).encode())
        conn.shutdown(socket.SHUT_WR)          # «илгээж дууслаа» гэж мэдэгдэнэ
        result = json.loads(receive(conn))
    if "error" in result:
        raise ValueError(result["error"])
    return result
