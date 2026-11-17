"""2-р гишүүн — ажилтны бүртгэл ба JSON хадгалалт."""
import json
import os
import time


def get_data_dir():
    """Өгөгдлийн хавтас: %LOCALAPPDATA%/ProductivitySystem/data (.exe дотор биш)."""
    folder = os.path.join(os.environ.get("LOCALAPPDATA", "."), "ProductivitySystem", "data")
    os.makedirs(folder, exist_ok=True)
    return folder


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


def save_report(employee_id, report):
    save("reports", load("reports") + [dict(report, employee_id=employee_id)])
