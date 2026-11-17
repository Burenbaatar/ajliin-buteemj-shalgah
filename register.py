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


def add_employee(name, target):
    if not name.strip():
        raise ValueError("Ажилтны нэр хоосон байна.")
    if target <= 0:
        raise ValueError("Төлөвлөсөн даалгавар 0-ээс их байх ёстой.")
    employee = {"id": str(time.time_ns()), "name": name.strip(), "target": target, "completed": 0}
    save("employees", load("employees") + [employee])
    return employee


def update_progress(employee_id, completed):
    employees = load("employees")
    for employee in employees:
        if employee["id"] == employee_id:
            if not 0 <= completed <= employee["target"]:
                raise ValueError("Гүйцэтгэл 0-ээс төлөвлөсөн тоо хүртэл байна.")
            employee["completed"] = completed
            save("employees", employees)
            return employee
    raise ValueError("Ажилтан олдсонгүй.")


def delete_employee(employee_id):
    save("employees", [employee for employee in load("employees") if employee["id"] != employee_id])


def save_activity(employee_id, summary):
    save("activity", load("activity") + [dict(summary, employee_id=employee_id)])


def save_pause(employee_id, reason):
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


def last_activity(employee_id):
    """Ажилтны хамгийн сүүлийн идэвхийн хураангуй. Байхгүй бол хоосон dict."""
    found = [item for item in load("activity") if item["employee_id"] == employee_id]
    return found[-1] if found else {}


def save_report(employee_id, report):
    save("reports", load("reports") + [dict(report, employee_id=employee_id)])


# ---------------------------------------------------------------- админы эрх
def check_password(password):
    """Админы нууц үгийг шалгана. Анх оруулсан нууц үг хадгалагдана — файлд зөвхөн хэш нь бичигдэнэ."""
    hashed = hashlib.sha256(password.encode()).hexdigest()
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
    """Ажилтны хүсэлт: нэрсийн жагсаалт авах эсвэл идэвхийн хураангуй хадгалуулах."""
    if request["action"] == "employees":       # бусдын даалгавар, хувийг ажилтанд илгээхгүй
        return {"employees": [{"id": e["id"], "name": e["name"]} for e in list_employees()]}
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
