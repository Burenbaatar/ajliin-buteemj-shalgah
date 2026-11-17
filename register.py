"""2-р гишүүн — ажилтны бүртгэл, JSON хадгалалт ба админы JSON сервер."""
import hashlib
import json
import os
import socket
import time

PORT = 5050                                    # ажилтнууд админы компьютерийн энэ порт руу холбогдоно


def get_data_dir():
    """Өгөгдлийн хавтас: програмын хажууд байх data хавтас (.exe дотор биш, хаагаад нээсэн ч үлдэнэ)."""
    os.makedirs("data", exist_ok=True)
    return "data"


def load(name):
    """name.json-оос жагсаалт уншина. Файл байхгүй бол хоосон жагсаалт."""
    path = os.path.join(get_data_dir(), name + ".json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as file:
        return json.load(file)[name]


def save(name, items):
    with open(os.path.join(get_data_dir(), name + ".json"), "w", encoding="utf-8") as file:
        json.dump({name: items}, file, ensure_ascii=False, indent=2)


def list_employees():
    return load("employees")


def hash_text(text):
    """Нууц үг, кодыг буцааж тайлж болохгүй SHA-256 хэш болгоно — файлд зөвхөн хэш хадгална."""
    return hashlib.sha256(text.encode()).hexdigest()


def add_employee(name, code):
    """Шинэ ажилтан бүртгэнэ. Ийм нэртэй ажилтан байвал кодыг нь шинэчилнэ."""
    name = name.strip()
    if not name:
        raise ValueError("Ажилтны нэр хоосон байна.")
    if len(code) < 4:
        raise ValueError("Код дор хаяж 4 тэмдэгт байна.")
    employees = load("employees")
    found = [employee for employee in employees if employee["name"].casefold() == name.casefold()]
    if found:
        employee = found[0]
        employee["code"] = hash_text(code)
    else:
        employee = {"id": str(time.time_ns()), "name": name, "code": hash_text(code)}
        employees.append(employee)
    save("employees", employees)
    return employee


def delete_employee(employee_id):
    save("employees", [employee for employee in load("employees") if employee["id"] != employee_id])
    save("faces", [face for face in load("faces") if face["employee_id"] != employee_id])   # нүүрний хээг хамт устгана


def get_face(employee_id):
    """Ажилтны нүүрний хээ (128 тоо). Бүртгээгүй бол None."""
    return next((face["feature"] for face in load("faces") if face["employee_id"] == employee_id), None)


def save_face(employee_id, feature):
    """Зураг биш, зөвхөн нүүрний хээг (128 тоо) админы компьютерт хадгална. Нэг удаа л бүртгэнэ —
    ажилтан өөрийн нүүрийг өөр хүнийхээр солихоос сэргийлж, шинэчлэхийг зөвхөн админ зөвшөөрнө."""
    if employee_id not in [employee["id"] for employee in list_employees()]:
        raise ValueError("Ажилтан олдсонгүй.")
    if get_face(employee_id):
        raise ValueError("Нүүр аль хэдийн бүртгэгдсэн. Шинэчлэх бол админд хандана уу.")
    if not isinstance(feature, list) or len(feature) != 128 or \
            not all(isinstance(value, (int, float)) for value in feature):
        raise ValueError("Нүүрний хээ буруу.")
    save("faces", load("faces") + [{"employee_id": employee_id, "feature": [round(float(v), 5) for v in feature]}])


def delete_face(employee_id):
    """Админ ажилтны нүүрийг устгаснаар ажилтан дахин бүртгүүлэх боломжтой болно."""
    save("faces", [face for face in load("faces") if face["employee_id"] != employee_id])


def save_activity(employee_id, summary):
    save("activity", load("activity") + [dict(summary, employee_id=employee_id)])


def activities(employee_id):
    """Тухайн ажилтны бүх хэмжилтийн хураангуй (жагсаалт)."""
    return [item for item in load("activity") if item["employee_id"] == employee_id]


def save_pause(employee_id, reason):
    """Ажилтан түр зогсоосон шалтгааныг цагтай нь pauses.json-д хадгална."""
    employee = next((e for e in list_employees() if e["id"] == employee_id), None)
    if employee is None:
        raise ValueError("Ажилтан олдсонгүй.")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Шалтгаанаа бичнэ үү.")
    pause = {"employee_id": employee_id, "employee_name": employee["name"],
             "reason": reason.strip(), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save("pauses", load("pauses") + [pause])


def last_pause(employee_id):
    found = [item for item in load("pauses") if item["employee_id"] == employee_id]
    return found[-1] if found else {}


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
    """Ажилтны хүсэлт: нэр, кодоор нэвтрэх, нүүр бүртгүүлэх эсвэл идэвхийн хураангуй хадгалуулах."""
    if request["action"] == "login":           # бусдын мэдээлэл, кодыг ажилтанд илгээхгүй
        for e in list_employees():
            if e["name"].casefold() == request["name"].strip().casefold() and e.get("code") == hash_text(request["code"]):
                return {"id": e["id"], "name": e["name"], "face": get_face(e["id"])}   # камер харьцуулах хээ
        raise ValueError("Нэр эсвэл код буруу.")
    if request["action"] == "face":
        save_face(request["employee_id"], request["feature"])
        return {"ok": True}
    if request["action"] == "activity":
        if request["employee_id"] not in [e["id"] for e in list_employees()]:
            raise ValueError("Ажилтан олдсонгүй.")
        save_activity(request["employee_id"], request["summary"])
        return {"ok": True}
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
def ask(host, request):
    """Админы сервер рүү JSON хүсэлт илгээж хариу авна. Холбогдохгүй бол OSError."""
    with socket.create_connection((host, PORT), timeout=3) as conn:
        conn.sendall(json.dumps(request, ensure_ascii=False).encode())
        conn.shutdown(socket.SHUT_WR)          # «илгээж дууслаа» гэж мэдэгдэнэ
        result = json.loads(receive(conn))
    if "error" in result:
        raise ValueError(result["error"])
    return result
