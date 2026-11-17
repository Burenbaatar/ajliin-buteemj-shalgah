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


def save_activity(employee_id, summary):
    save("activity", load("activity") + [dict(summary, employee_id=employee_id)])


def activities(employee_id):
    """Тухайн ажилтны бүх хэмжилтийн хураангуй (жагсаалт)."""
    return [item for item in load("activity") if item["employee_id"] == employee_id]


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
    """Ажилтны хүсэлт: нэр, кодоор нэвтрэх эсвэл идэвхийн хураангуй хадгалуулах."""
    if request["action"] == "login":           # бусдын мэдээлэл, кодыг ажилтанд илгээхгүй
        for e in list_employees():
            if e["name"].casefold() == request["name"].strip().casefold() and e.get("code") == hash_text(request["code"]):
                return {"id": e["id"], "name": e["name"]}
        raise ValueError("Нэр эсвэл код буруу.")
    if request["action"] == "activity":
        if request["employee_id"] not in [e["id"] for e in list_employees()]:
            raise ValueError("Ажилтан олдсонгүй.")
        save_activity(request["employee_id"], request["summary"])
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
