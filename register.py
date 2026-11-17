
import os
import json
import uuid
from pathlib import Path
from datetime import datetime


# JSON өгөгдөл хадгалах хавтас
def get_data_dir() -> Path:
    local_app_data = os.environ.get(
        "LOCALAPPDATA",
        str(Path.home())
    )

    data_dir = Path(local_app_data) / "ProductivitySystem" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


# JSON файл унших
def load_json(filename: str, default: dict) -> dict:
    file_path = get_data_dir() / filename

    if not file_path.exists():
        return default.copy()

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("JSON өгөгдлийн бүтэц буруу байна.")

        return data

    except json.JSONDecodeError as error:
        raise ValueError(
            f"{filename} файл гэмтсэн байна: {error}"
        )


# JSON файлд аюулгүй хадгалах
def save_json(filename: str, data: dict) -> None:
    file_path = get_data_dir() / filename
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, file_path)

    finally:
        if temp_path.exists():
            temp_path.unlink()


# Бүх ажилтны мэдээлэл авах
def list_employees() -> list:
    data = load_json("employees.json", {"employees": []})
    return data.get("employees", [])


# Шинэ ажилтан бүртгэх
def add_employee(name: str, target: int) -> dict:
    name = name.strip()

    if not name:
        raise ValueError("Ажилтны нэр хоосон байж болохгүй.")

    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        raise ValueError("Зорилтот даалгаврын тоо 0-ээс их бүхэл тоо байх ёстой.")

    data = load_json("employees.json", {"employees": []})

    employee = {
        "id": str(uuid.uuid4()),
        "name": name,
        "target": target,
        "completed": 0,
        "created_at": datetime.now().isoformat()
    }

    data["employees"].append(employee)
    save_json("employees.json", data)

    return employee


# Ажилтны гүйцэтгэлийг шинэчлэх
def update_progress(employee_id: str, completed: int) -> dict:
    data = load_json("employees.json", {"employees": []})

    for employee in data["employees"]:
        if employee["id"] == employee_id:

            if isinstance(completed, bool) or not isinstance(completed, int):
                raise ValueError("Гүйцэтгэсэн даалгавар бүхэл тоо байх ёстой.")

            if completed < 0 or completed > employee["target"]:
                raise ValueError("Гүйцэтгэлийн утга зорилтот хэмжээнээс хэтэрч болохгүй.")

            employee["completed"] = completed
            save_json("employees.json", data)

            return employee

    raise ValueError("Ийм ID-тай ажилтан олдсонгүй.")


# Ажилтан устгах
def delete_employee(employee_id: str) -> bool:
    data = load_json("employees.json", {"employees": []})

    old_count = len(data["employees"])

    data["employees"] = [
        employee
        for employee in data["employees"]
        if employee["id"] != employee_id
    ]

    if len(data["employees"]) == old_count:
        return False

    save_json("employees.json", data)
    return True


# Үйл ажиллагааны мэдээлэл хадгалах
def save_activity(employee_id: str, summary: dict) -> None:
    data = load_json("activity.json", {"sessions": []})

    session = {
        "employee_id": employee_id,
        "summary": summary,
        "saved_at": datetime.now().isoformat()
    }

    data["sessions"].append(session)
    save_json("activity.json", data)


# Тайлан хадгалах
def save_report(employee_id: str, report: dict) -> None:
    required_fields = [
        "date",
        "completion_rate",
        "target",
        "completed"
    ]

    for field in required_fields:
        if field not in report:
            raise ValueError(f"Тайланд '{field}' талбар дутуу байна.")

    data = load_json("reports.json", {"reports": []})

    report_data = {
        "employee_id": employee_id,
        **report
    }

    data["reports"].append(report_data)
    save_json("reports.json", data)
