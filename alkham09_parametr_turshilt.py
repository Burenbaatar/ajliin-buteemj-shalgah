"""Алхам 9. Гэрэл, хүрээ, нөөцийн шалгалт.

Ажиллуулах:
    python alkham09_parametr_turshilt.py          # гараар: гулсуураар параметр өөрчилнө
    python alkham09_parametr_turshilt.py --auto   # автомат: параметрийг НЭГ НЭГЭЭР нь өөрчилж хэмжинэ

--auto горим (~45 сек, камер руу хараад тайван суух хэрэгтэй):
    • Суурь тохиргооноос (1.1 / 5 / 60 / 640 / equalize) нэг л параметрийг өөрчилж хэмжинэ (9.2)
    • minNeighbors-ийг бууруулахад хуурамч нүүр нэмэгдэх эсэхийг харна (9.3)
    • Бүдэг гэрлийг дуурайна: кадрын гэрлийг 50%, 25% болгож бууруулна (9.1)
    • Камерын нягтрал 640×480 ↔ 1280×720, жижигрүүлсэн/жижигрүүлээгүй fps-ийг харьцуулна (9.4)
    • Үр дүнг хүснэгтээр хэвлээд alkham09_temdeglel.txt-д бичнэ

Гарын горимын гулсуурууд:
    scale x100  — scaleFactor × 100  (110 = 1.10). Бага → нарийн хайна, гэхдээ удаан.
    neighbors   — minNeighbors. Бага → илүү олон нүүр олно, гэхдээ ХУУРАМЧ нүүр нэмэгдэнэ.
    minSize     — үүнээс жижиг (пиксел) нүүрийг тоохгүй.
    width       — кадрын дээд өргөн. Бага → хурдан.
    equalize    — 1 = саарал дүрсийг тодосгоно (бүдэг гэрэлд тусална).
Товч: h = 640×480 ↔ 1280×720, s = тэмдэглэх, q / Esc = гарах

Хүснэгтийн баганууд:
    fps        — секундэд хэдэн кадр харуулсан (камер өөрөө ~30-аас ихгүй өгдөг)
    илрүүлэх   — нэг кадр дээр detectMultiScale хэдэн миллисекунд зарцуулсан (бага = хөнгөн)
    ихэвчлэн   — хамгийн олон давтагдсан нүүрний тоо
    тогтвортой — кадруудын хэдэн хувьд яг тэр тоо гарсан бэ (Haar төгс биш — 9.5)
    гэрэл      — кадрын дундаж гэрэлтэлт 0 (хар) … 255 (цагаан)

Камерын зургийг хадгалахгүй — тэмдэглэлд зөвхөн тоо бичигдэнэ.
"""
import os
import sys
import time
from collections import Counter, deque
from datetime import datetime

import cv2

from camera import CameraService, draw_faces, resize_keep_ratio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AUTO = "--auto" in sys.argv
WINDOW = "Alkham 9 - parameter test (q = garah)"
NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alkham09_temdeglel.txt")
FRAMES_PER_TEST = 40

BASE = {"scale_factor": 1.1, "min_neighbors": 5, "min_size": (60, 60), "max_width": 640, "equalize": True}

# (Монгол нэр, суурь тохиргооноос юуг өөрчлөх, гэрлийн хувь, камер 1280×720 эсэх)
AUTO_TESTS = [
    ("суурь тохиргоо",               {},                                1.0,  False),
    ("scaleFactor = 1.05",           {"scale_factor": 1.05},            1.0,  False),
    ("scaleFactor = 1.2",            {"scale_factor": 1.2},             1.0,  False),
    ("scaleFactor = 1.3",            {"scale_factor": 1.3},             1.0,  False),
    ("minNeighbors = 2",             {"min_neighbors": 2},              1.0,  False),
    ("minNeighbors = 3",             {"min_neighbors": 3},              1.0,  False),
    ("minNeighbors = 8",             {"min_neighbors": 8},              1.0,  False),
    ("minSize = 30",                 {"min_size": (30, 30)},            1.0,  False),
    ("minSize = 120",                {"min_size": (120, 120)},          1.0,  False),
    ("equalize = унтраасан",         {"equalize": False},               1.0,  False),
    ("width = 320",                  {"max_width": 320},                1.0,  False),
    ("бүдэг гэрэл 50%",              {},                                0.5,  False),
    ("бүдэг 50%, equalize унтраасан", {"equalize": False},              0.5,  False),
    ("бүдэг гэрэл 25%",              {},                                0.25, False),
    ("бүдэг 25%, equalize унтраасан", {"equalize": False},              0.25, False),
    ("1280×720 → 640 жижигрүүлсэн",  {},                                1.0,  True),
    ("1280×720 жижигрүүлээгүй",      {"max_width": 1280},               1.0,  True),
]


# ---------------------------------------------------------------- туслах функцууд
def stability(history):
    """(тогтвортой хувь, хамгийн олон давтагдсан нүүрний тоо)."""
    if not history:
        return 0.0, 0
    most_common, times = Counter(history).most_common(1)[0]
    return times / len(history) * 100, most_common


def apply_settings(camera, settings):
    for name, value in settings.items():
        setattr(camera, name, value)


def set_resolution(camera, high_res):
    """Камерын нягтралыг солиод бодит нягтралыг буцаана."""
    width, height = (1280, 720) if high_res else (640, 480)
    camera.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    for _ in range(5):  # нягтрал солисны дараах эхний кадрууд муу байж болно
        camera.cap.read()
    return int(camera.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(camera.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


def grab(camera, light=1.0):
    """get_frame()-тэй ижил алхмууд. Илрүүлэлтийн хугацааг тусад нь хэмжих, гэрэл
    бүдгэрүүлэхийн тулд задалж бичсэн. Буцаах: (кадр, нүүрний тоо, илрүүлэх_мс) эсвэл None."""
    ok, frame = camera.cap.read()
    if not ok or frame is None:
        return None
    if camera.mirror:
        frame = cv2.flip(frame, 1)
    frame = resize_keep_ratio(frame, camera.max_width)
    if light < 1.0:
        frame = cv2.convertScaleAbs(frame, alpha=light)  # пиксел бүрийг light-аар үржүүлж бүдгэрүүлнэ
    started = time.perf_counter()
    faces = camera.detect_faces(frame)
    detect_ms = (time.perf_counter() - started) * 1000
    draw_faces(frame, faces)
    return frame, len(faces), detect_ms


def brightness(frame):
    return float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())


def draw_info(frame, lines):
    height = 22 * len(lines) + 8
    cv2.rectangle(frame, (0, 0), (frame.shape[1], height), (0, 0, 0), -1)
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (8, 20 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)


def settings_text(camera, light, high_res):
    """Дэлгэц дээр гаргах латин бичвэр (cv2.putText кирилл зурж чаддаггүй)."""
    return (f"scale={camera.scale_factor:.2f} neighbors={camera.min_neighbors} "
            f"minSize={camera.min_size[0]} width={camera.max_width} eq={int(camera.equalize)} "
            f"light={int(light * 100)}% cam={'1280x720' if high_res else '640x480'}")


# ---------------------------------------------------------------- автомат горим
def measure(camera, light, high_res, title):
    """FRAMES_PER_TEST кадр аваад дундаж үзүүлэлтүүдийг буцаана. q дарвал None."""
    counts, detect_times, lights = [], [], []
    started = time.perf_counter()
    while len(counts) < FRAMES_PER_TEST:
        result = grab(camera, light)
        if result is None:
            if cv2.waitKey(30) & 0xFF in (ord("q"), 27):
                return None
            continue
        frame, count, detect_ms = result
        counts.append(count)
        detect_times.append(detect_ms)
        lights.append(brightness(frame))

        draw_info(frame, [title, settings_text(camera, light, high_res),
                          f"Faces: {count}   (kamer ruu kharj taivan suuna uu)"])
        cv2.imshow(WINDOW, frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            return None
    elapsed = time.perf_counter() - started
    stable, usual = stability(counts)
    return {
        "fps": len(counts) / elapsed,
        "detect_ms": sum(detect_times) / len(detect_times),
        "usual": usual,
        "stable": stable,
        "light": sum(lights) / len(lights),
        "counts": counts,
    }


def warm_up(camera, frames, message):
    """Хэмжихээс өмнө хэдэн кадрыг хаяна: камерын гэрэл тохируулга, OpenCV-ийн эхний
    удаан дуудлага зэрэг нь эхний хэмжилтийг буруу болгохгүйн тулд."""
    for _ in range(frames):
        result = grab(camera)
        if result is not None:
            draw_info(result[0], [message])
            cv2.imshow(WINDOW, result[0])
        cv2.waitKey(1)


def remark(row, base):
    """Суурь тохиргоотой харьцуулсан товч дүгнэлт."""
    words = []
    if row["usual"] != base["usual"]:
        words.append(f"нүүрний тоо {base['usual']}→{row['usual']}")
    extra = sum(1 for count in row["counts"] if count > base["usual"])
    if extra >= max(2, FRAMES_PER_TEST * 0.05):  # 5%-иас олон кадрт илүү нүүр
        words.append(f"{extra} кадрт илүү нүүр (хуурамч)")
    if row["stable"] < base["stable"] - 15:
        words.append("тогтворгүй болсон")
    if row["detect_ms"] > base["detect_ms"] * 1.5:
        words.append("илрүүлэлт удааширсан")
    elif row["detect_ms"] < base["detect_ms"] * 0.67:
        words.append("илрүүлэлт хурдассан")
    if row["fps"] < base["fps"] * 0.75:
        words.append("fps буурсан")
    return ", ".join(words) or "сууриас ялгаагүй"


def run_auto(camera):
    print(f"Автомат туршилт: {len(AUTO_TESTS)} тохиргоо × {FRAMES_PER_TEST} кадр. "
          "Камер руу хараад тайван сууна уу (q = зогсоох).\n")
    rows = []
    high_res = False
    apply_settings(camera, BASE)
    warm_up(camera, 20, "Warm up... kamer ruu kharna uu")
    for index, (name, changes, light, hd) in enumerate(AUTO_TESTS, start=1):
        if hd != high_res:
            high_res = hd
            real_w, real_h = set_resolution(camera, high_res)
            print(f"    (камерын нягтрал → {real_w}×{real_h})")
            warm_up(camera, 20, "Resolution changed - warm up...")  # камер гэрлээ дахин тохируулна
        apply_settings(camera, {**BASE, **changes})  # суурь + ганц өөрчлөлт
        row = measure(camera, light, high_res, f"Test {index}/{len(AUTO_TESTS)}")
        if row is None:
            print("Хэрэглэгч зогсоолоо.")
            break
        row["name"] = name
        rows.append(row)
        print(f"  {index:>2}. {name:<31} fps {row['fps']:5.1f} | илрүүлэх {row['detect_ms']:5.1f} мс | "
              f"ихэвчлэн {row['usual']} | тогтвортой {row['stable']:3.0f}% | гэрэл {row['light']:5.1f}")
    cv2.destroyAllWindows()
    if not rows:
        return

    base = rows[0]
    lines = [f"=== Автомат туршилт {datetime.now():%Y-%m-%d %H:%M:%S} "
             f"(OpenCV {cv2.__version__}, {FRAMES_PER_TEST} кадр/тохиргоо) ==="]
    header = f"{'Тохиргоо':<31} {'fps':>5} {'илрүүлэх':>9} {'ихэвчлэн':>8} {'тогтвортой':>10} {'гэрэл':>6}  Дүгнэлт"
    lines.append(header)
    for row in rows:
        lines.append(f"{row['name']:<31} {row['fps']:5.1f} {row['detect_ms']:6.1f} мс {row['usual']:>8} "
                     f"{row['stable']:9.0f}% {row['light']:6.1f}  "
                     f"{'(харьцуулах суурь)' if row is base else remark(row, base)}")

    print("\n" + "\n".join(lines))
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")
    print("\nТэмдэглэлд бичлээ:", NOTES_FILE)


# ---------------------------------------------------------------- гарын горим
def read_trackbars():
    """Гулсуурын утгуудыг уншаад зөвшөөрөгдөх хязгаарт барина."""
    return {
        "scale_factor": max(101, cv2.getTrackbarPos("scale x100", WINDOW)) / 100,  # 1.0 бол дуусахгүй
        "min_neighbors": max(1, cv2.getTrackbarPos("neighbors", WINDOW)),
        "min_size": (max(20, cv2.getTrackbarPos("minSize", WINDOW)),) * 2,
        "max_width": max(160, cv2.getTrackbarPos("width", WINDOW)),
        "equalize": cv2.getTrackbarPos("equalize", WINDOW) == 1,
    }


def save_note(camera, fps, history, lights, high_res):
    try:
        light = input("Гэрлийн нөхцөл (жишээ: энгийн / бүдэг / цонхны эсрэг): ").strip() or "-"
    except EOFError:  # терминалгүй ажиллуулсан үед
        light = "-"
    stable, usual = stability(history)
    avg_light = sum(lights) / len(lights) if lights else 0
    line = (f"{datetime.now():%Y-%m-%d %H:%M:%S} | гэрэл={light} ({avg_light:.0f}/255) | "
            f"{settings_text(camera, 1.0, high_res)} | fps={fps:.1f} | "
            f"ихэвчлэн {usual} нүүр, тогтвортой {stable:.0f}%")
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("Тэмдэглэлд бичлээ:", line)


def run_manual(camera):
    cv2.createTrackbar("scale x100", WINDOW, 110, 150, lambda _: None)
    cv2.createTrackbar("neighbors", WINDOW, 5, 15, lambda _: None)
    cv2.createTrackbar("minSize", WINDOW, 60, 200, lambda _: None)
    cv2.createTrackbar("width", WINDOW, 640, 1280, lambda _: None)
    cv2.createTrackbar("equalize", WINDOW, 1, 1, lambda _: None)
    print("Гулсуураар параметрээ НЭГ НЭГЭЭР нь өөрчил. s = тэмдэглэх, h = нягтрал солих, q/Esc = гарах")

    history = deque(maxlen=30)  # сүүлийн 30 кадрын нүүрний тоо
    lights = deque(maxlen=30)
    fps = 0.0
    high_res = False
    last_time = time.perf_counter()

    while camera.running:  # туршилтын давталт — GUI дээр after() ашиглана
        apply_settings(camera, read_trackbars())
        result = grab(camera)
        if result is None:
            if cv2.waitKey(30) & 0xFF in (ord("q"), 27):
                break
            continue
        frame, count, detect_ms = result
        history.append(count)
        lights.append(brightness(frame))

        now = time.perf_counter()
        instant_fps = 1 / max(now - last_time, 1e-6)
        fps = instant_fps if fps == 0 else 0.9 * fps + 0.1 * instant_fps  # жигд дундаж
        last_time = now

        stable, usual = stability(history)
        draw_info(frame, [
            f"Faces: {count}   usual: {usual}   stable: {stable:.0f}%   fps: {fps:.1f}   detect: {detect_ms:.0f}ms",
            settings_text(camera, 1.0, high_res),
        ])
        cv2.imshow(WINDOW, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("s"):
            save_note(camera, fps, history, lights, high_res)
        if key == ord("h"):
            high_res = not high_res
            real_w, real_h = set_resolution(camera, high_res)
            print(f"Камерын нягтрал: {real_w}×{real_h}")
            history.clear()
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            break


def main():
    camera = CameraService(max_width=640)
    if not camera.start():
        print("Алдаа:", camera.last_error)
        return 1
    cv2.namedWindow(WINDOW)
    try:
        if AUTO:
            run_auto(camera)
        else:
            run_manual(camera)
    finally:
        camera.stop()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
