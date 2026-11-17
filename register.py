"""2-р гишүүн — ажилтны бүртгэл ба JSON хадгалалт."""
import json
import os
import time


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


def add_employee(name):
    if not name.strip():
        raise ValueError("Ажилтны нэр хоосон байна.")
    employee = {"id": str(time.time_ns()), "name": name.strip()}
    save("employees", load("employees") + [employee])
    return employee


def delete_employee(employee_id):
    save("employees", [employee for employee in load("employees") if employee["id"] != employee_id])


def save_activity(employee_id, summary):
    save("activity", load("activity") + [dict(summary, employee_id=employee_id)])
