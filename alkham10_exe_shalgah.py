"""Алхам 10. .exe дотор XML болон камер ажиллаж байгааг шалгах.

Ажиллуулах:
    python alkham10_exe_shalgah.py            # .exe бүтээгээд XML-ийг шалгана
    python alkham10_exe_shalgah.py --auto     # + .exe-д камер өөрөө асаж 6 сек ажиллаад хаагдана
    python alkham10_exe_shalgah.py --gui      # + .exe-г нээнэ, та өөрөө товч дарж туршаад хаана

Юу хийх вэ:
    10.1 PyInstaller --collect-data cv2 -аар alkham08_gui_holbolt.py-г dist/CameraDemo.exe болгоно
         (camera.py эсвэл alkham08_gui_holbolt.py өөрчлөгдсөн үед л дахин бүтээнэ)
    10.3 CameraDemo.exe --self-test → .exe дотор нүүр илрүүлэх XML ачаалагдаж байгааг батална
    10.2 --auto / --gui: .exe дотор камер нээгдэж, кадр зурагдаж байгааг батална
    10.4 .exe хаагдсаны дараа камер бусад програмд чөлөөтэй эсэхийг Python-оор нээж шалгана
    10.5 Камер бол бодит төхөөрөмж: .exe дангаараа камерыг орлохгүй.

5-р гишүүний build_exe.py (ProductivitySystem.exe)-д ч мөн "--collect-data", "cv2" байх ёстой.
"""
import json
import os
import subprocess
import sys
import tempfile

from camera import CameraService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "CameraDemo"
EXE_PATH = os.path.join(HERE, "dist", APP_NAME + ".exe")
SOURCES = ["alkham08_gui_holbolt.py", "camera.py"]


def exe_is_fresh():
    """.exe байгаа бөгөөд эх кодуудаас хойш бүтээгдсэн бол True."""
    if not os.path.isfile(EXE_PATH):
        return False
    exe_time = os.path.getmtime(EXE_PATH)
    return all(os.path.getmtime(os.path.join(HERE, name)) < exe_time for name in SOURCES)


def build_exe():
    if exe_is_fresh():
        print("[10.1] .exe эх кодоос шинэ байна — дахин бүтээхгүй:", EXE_PATH)
        return True
    print("[10.1] PyInstaller-ээр .exe бүтээж байна (1–3 минут)...")
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile", "--windowed",
        "--name", APP_NAME,
        "--collect-data", "cv2",       # ← haarcascade XML-ийг .exe дотор оруулдаг гол сонголт
        "alkham08_gui_holbolt.py",
    ]
    print("     ", " ".join(command[1:]))
    done = subprocess.run(command, cwd=HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0 or not os.path.isfile(EXE_PATH):
        print(done.stderr[-3000:])
        print("БҮТЭЭЛТ АМЖИЛТГҮЙ. PyInstaller суусан эсэх: python -m pip install pyinstaller")
        return False
    size_mb = os.path.getsize(EXE_PATH) / 1024 / 1024
    print(f"      OK: {EXE_PATH} ({size_mb:.0f} MB)")
    return True


def check_xml_inside_exe():
    print("[10.3] .exe дотор нүүр илрүүлэх XML ачаалагдаж байгаа эсэх...")
    done = subprocess.run([EXE_PATH, "--self-test"], timeout=120)
    if done.returncode == 0:
        print("      OK: .exe дотор XML олдож, CascadeClassifier ачаалагдлаа.")
        return True
    print("      АЛДАА: .exe дотор XML олдсонгүй. --collect-data cv2 байгаа эсэх, "
          "cv2.data.haarcascades замыг шалгана уу.")
    return False


def check_camera_auto():
    print("[10.2] CameraDemo.exe --auto-demo: камер өөрөө асаж 6 сек ажиллаад хаагдана...")
    handle, result_path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    try:
        subprocess.run([EXE_PATH, "--auto-demo", result_path], timeout=120)
        with open(result_path, encoding="utf-8") as f:
            text = f.read()
    finally:
        os.remove(result_path)
    if not text:
        print("      АЛДАА: .exe үр дүн бичсэнгүй (эхлэхдээ унасан байж магадгүй).")
        return False
    report = json.loads(text)

    if not report.get("started"):
        print("      АЛДАА: .exe дотор камер нээгдсэнгүй:", report.get("error"))
        return False
    print("      Камер нээгдлээ. XML:", report["xml_path"])
    print("      XML .exe-ийн задалсан хавтаснаас ачаалагдсан уу:",
          "ТИЙМ" if report["xml_inside_exe"] else "ҮГҮЙ (компьютерийн OpenCV-оос ачаалсан)")
    print(f"      Зурсан кадр: {report['frames_drawn']} ({report['fps']} fps), "
          f"хамгийн олон нүүр: {report['max_faces']}")
    clicks, expected = report["button_clicks"], report["button_clicks_expected"]
    responsive = clicks >= expected * 0.8
    print(f"      Цонх гацаагүй эсэх: товч {clicks}/{expected} удаа дарагдсан →",
          "гацаагүй" if responsive else "ГАЦСАН")
    print("      Цонх хаахад camera.stop() дуудагдсан:", "ТИЙМ" if report["camera_released"] else "ҮГҮЙ")
    return (report["frames_drawn"] > 0 and report["xml_inside_exe"]
            and responsive and report["camera_released"])


def check_camera_gui():
    print("[10.2] CameraDemo.exe нээгдлээ: 'Камер асаах' дарж, нүүрэн дээр хүрээ гарч байгааг шалга.")
    print("       Дууссан бол цонхоо X товчоор хаа...")
    subprocess.run([EXE_PATH])  # цонх хаагдтал хүлээнэ
    return True


def check_camera_free():
    print("[10.4] .exe хаагдсаны дараа камер бусад програмд чөлөөтэй эсэх...")
    camera = CameraService()
    free = camera.start()
    camera.stop()
    if free:
        print("      OK: камер Python-оос дахин нээгдлээ — .exe камераа зөв чөлөөлжээ.")
    else:
        print("      АЛДАА:", camera.last_error)
    return free


def main():
    results = {"10.1 .exe бүтээгдсэн": build_exe()}
    if results["10.1 .exe бүтээгдсэн"]:
        results["10.3 .exe дотор XML ачаалагдсан"] = check_xml_inside_exe()
        if "--auto" in sys.argv:
            results["10.2 .exe дотор камер ажиллаж, цонх гацаагүй"] = check_camera_auto()
        elif "--gui" in sys.argv:
            results["10.2 .exe дотор камер ажилласан (нүдээр)"] = check_camera_gui()
        if "--auto" in sys.argv or "--gui" in sys.argv:
            results["10.4 .exe хаасны дараа камер чөлөөтэй"] = check_camera_free()

    print("\n========== Алхам 10-ын үр дүн ==========")
    for name, ok in results.items():
        print("[x] OK " if ok else "[ ] АМЖИЛТГҮЙ ", name)
    print("[i]    10.5 Камер бол бодит төхөөрөмж — .exe-г камергүй компьютерт нээвэл "
          "'Камер нээгдсэнгүй' гэсэн ойлгомжтой алдаа гарна.")
    if "--auto" not in sys.argv and "--gui" not in sys.argv and all(results.values()):
        print("\nКамерыг .exe дотор турших: python alkham10_exe_shalgah.py --auto  (эсвэл --gui)")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
