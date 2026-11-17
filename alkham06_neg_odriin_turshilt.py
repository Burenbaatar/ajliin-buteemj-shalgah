"""Алхам 6. Нэг өдрийн туршилт — бодит камер дээр checklist-ийг дарааллаар нь шалгана.

Ажиллуулах:
    python alkham06_neg_odriin_turshilt.py          # гараар: асуултад y/n гэж хариулна
    python alkham06_neg_odriin_turshilt.py --auto   # автомат: асуулт асуухгүй, 25 сек preview

Шалгах 5 зүйл:
    [1] Камер нээгдэнэ, нэг кадр авна.
    [2] Preview толин тусгалтай.
            гараар  — баруун гараа өргөөд дэлгэцийн баруун талд харагдаж байгааг y/n-ээр батална
            --auto  — get_frame()-ийн кадрыг түүхий кадр болон түүний толин тусгалтай харьцуулна
    [3] Нүүртэй үед хүрээ гарна, нүүргүй үед хүрээ алга.
            Preview дээр камер руу хараад, дараа нь нүүрээ гараараа хаана.
            Нүүртэй (1+) ба нүүргүй (0) кадр хоёулаа харагдвал OK.
    [4] Камер эзлэгдсэн байхад ойлгомжтой алдаа гарна.
            гараар  — Windows-ийн Camera аппыг нээгээд шалгана (s = алгасах)
            --auto  — камер нээлттэй байхад 2 дахь CameraService нээж үзнэ
    [5] stop() дараа дахин start() ажиллана.

Камерын зургийг файлд ХАДГАЛАХГҮЙ — зөвхөн дэлгэцэнд харуулна.
"""
import sys
import time

import cv2

from camera import CameraService, resize_keep_ratio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AUTO = "--auto" in sys.argv
PREVIEW_SECONDS = 25               # --auto үед preview хамгийн ихдээ хэдэн секунд
WINDOW = "Alkham 6 - q = duusgah"  # OpenCV цонхны гарчиг кирилл үсэг дэмждэггүй
results = {}
notes = []


def ask_yes_no(question):
    answer = input(question + " (y/n): ").strip().lower()
    return answer in ("y", "yes", "т", "тийм")


def check_1_open_and_read(camera):
    print("\n[1] Камер нээж нэг кадр авна...")
    if not camera.start():
        print("    Алдаа:", camera.last_error)
        return False
    result = camera.get_frame()
    if result is None:
        print("    Алдаа:", camera.last_error)
        return False
    frame, count = result
    print("    Кадрын хэмжээ:", frame.shape, "| нүүрний тоо:", count)
    return True


def check_2_mirror_auto(camera):
    """Түүхий кадр (raw)-ыг шууд камераас авч, get_frame()-ийн кадртай харьцуулна.

    get_frame() толин тусгал хийдэг бол flip(raw)-тай их төстэй, raw-тай бага төстэй байна.
    """
    print("\n[2] Толин тусгалыг автоматаар шалгана...")
    ok, raw = camera.cap.read()
    result = camera.get_frame()
    if not ok or result is None:
        print("    Кадр авч чадсангүй:", camera.last_error)
        return False
    frame = result[0]
    raw = resize_keep_ratio(raw, camera.max_width)
    diff_mirror = float(cv2.absdiff(frame, cv2.flip(raw, 1)).mean())  # бага = төстэй
    diff_same = float(cv2.absdiff(frame, raw).mean())
    print(f"    Толин тусгалтай ялгаа: {diff_mirror:.1f} | эргүүлээгүйтэй ялгаа: {diff_same:.1f}")
    if diff_mirror < diff_same * 0.9:
        print("    → get_frame() кадрыг толин тусгал болгожээ.")
        return True
    if diff_mirror < diff_same:
        notes.append("[2] Дүрс хэт тэгш хэмтэй тул ялгаа бага байна — гараар (y/n) давтан шалга.")
    return diff_mirror < diff_same


def check_3_preview(camera):
    """Preview цонх харуулна. Нүүртэй (1+) ба нүүргүй (0) кадр хоёулаа гарсан эсэхийг тэмдэглэнэ."""
    print("\n[3] Preview цонх нээгдлээ:")
    print("    • Камер руу хар — нүүрэн дээр ногоон хүрээ гарах ёстой.")
    print("    • Нүүрээ гараараа 2–3 секунд хаа — хүрээ алга болох ёстой.")
    if AUTO:
        print(f"    • Хоёулаа харагдвал өөрөө дуусна (хамгийн ихдээ {PREVIEW_SECONDS} сек).")
    else:
        print("    • БАРУУН гараа өргө — дэлгэцийн БАРУУН талд харагдах ёстой.")
        print("    • Дууссан бол цонхон дээр q эсвэл Esc дар.")

    seen_face = seen_no_face = False
    face_frames = no_face_frames = 0
    started = time.time()
    both_seen_at = None

    while camera.running:
        result = camera.get_frame()
        if result is None:
            if not camera.running:
                print("    Алдаа:", camera.last_error)
                break
            cv2.waitKey(30)
            continue
        frame, count = result
        if count > 0:
            face_frames += 1
            seen_face = face_frames >= 3        # ганц нэг санамсаргүй кадрыг тоохгүй
        else:
            no_face_frames += 1
            seen_no_face = no_face_frames >= 3

        left = PREVIEW_SECONDS - (time.time() - started)
        if not seen_face:
            hint = "1) Kamer ruu khar"
        elif not seen_no_face:
            hint = "2) Nuuree garaaraa khaa"
        else:
            hint = "OK! (q = duusgah)"
        lines = [f"Faces: {count}   face: {'YES' if seen_face else 'no'}   "
                 f"no-face: {'YES' if seen_no_face else 'no'}", hint + (f"   {left:.0f}s" if AUTO else "")]
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 54), (0, 0, 0), -1)
        for i, text in enumerate(lines):
            cv2.putText(frame, text, (8, 21 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow(WINDOW, frame)

        key = cv2.waitKey(30) & 0xFF  # ~30 кадр/сек. Энэ while зөвхөн туршилтад, GUI дээр after()
        if key in (ord("q"), 27):
            break
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            break  # цонхны X товч
        if AUTO:
            if seen_face and seen_no_face:
                both_seen_at = both_seen_at or time.time()
                if time.time() - both_seen_at > 1.5:
                    break
            if left <= 0:
                break
    cv2.destroyAllWindows()

    print(f"    Нүүртэй кадр: {face_frames}, нүүргүй кадр: {no_face_frames}")
    return seen_face and seen_no_face


def check_4_busy_auto(camera):
    print("\n[4] Камер нээлттэй байхад 2 дахь CameraService нээж үзнэ...")
    other = CameraService()
    opened = other.start()
    message = other.last_error
    other.stop()
    if opened:
        print("    2 дахь нь ч нээгдлээ — энэ компьютерт Windows нэг камерыг олон програмд зэрэг өгдөг.")
        notes.append("[4] Энэ камер хуваалцагддаг тул 'эзлэгдсэн' алдаа гарахгүй нь хэвийн. "
                     "Алдааны мессежийг tests/test_camera.py (test_camera_busy_releases_and_explains) шалгадаг.")
        return None
    print("    Гарсан мессеж:", message)
    return bool(message)


def check_4_busy_manual():
    print("\n[4] Камер эзлэгдсэн үеийн алдаа.")
    print("    Windows-ийн Camera апп (эсвэл Zoom/Teams)-ыг нээж камерыг асаа.")
    answer = input("    Бэлэн бол Enter, алгасах бол s: ").strip().lower()
    if answer == "s":
        return None
    other = CameraService()
    opened = other.start()
    other.stop()
    if opened:
        print("    Камер нээгдчихлээ — Windows зарим камерыг 2 програмд зэрэг өгдөг.")
        print("    Энэ тохиолдолд алдаа гарахгүй нь хэвийн.")
        input("    Camera аппыг хаагаад Enter дар: ")
        return None
    print("    Гарсан мессеж:", other.last_error)
    ok = bool(other.last_error)
    input("    Одоо Camera аппыг хаагаад Enter дар: ")
    return ok


def check_5_restart(camera):
    print("\n[5] stop() → start() дахин ажиллах эсэх...")
    camera.stop()
    camera.stop()  # давхар stop() алдаа гаргах ёсгүй
    if camera.cap is not None or camera.running:
        return False
    if not camera.start():
        print("    Алдаа:", camera.last_error)
        return False
    ok = camera.get_frame() is not None
    camera.stop()
    print("    Дахин нээгдэж кадр ирлээ." if ok else "    Дахин нээгдсэн ч кадр ирсэнгүй.")
    return ok


def mark(value):
    if value is None:
        return "[-] алгассан "
    return "[x] OK       " if value else "[ ] АМЖИЛТГҮЙ"


def main():
    print("Алхам 6 —", "автомат горим (--auto)" if AUTO else "гарын горим")
    camera = CameraService()
    try:
        results["1. Камер нээгдэнэ, нэг кадр авна"] = check_1_open_and_read(camera)
        if not results["1. Камер нээгдэнэ, нэг кадр авна"]:
            print("\nКамер нээгдэхгүй тул бусад туршилтыг хийх боломжгүй.")
            return 1

        if AUTO:
            results["2. Preview толин тусгалтай"] = check_2_mirror_auto(camera)
            results["3. Нүүртэй үед хүрээ, нүүргүй үед алга"] = check_3_preview(camera)
            results["4. Камер эзлэгдсэн үед ойлгомжтой алдаа"] = check_4_busy_auto(camera)
        else:
            faces_ok = check_3_preview(camera)
            results["2. Preview толин тусгалтай"] = ask_yes_no(
                "[2] Баруун гар чинь дэлгэцийн баруун талд харагдсан уу?")
            results["3. Нүүртэй үед хүрээ, нүүргүй үед алга"] = faces_ok
            camera.stop()
            results["4. Камер эзлэгдсэн үед ойлгомжтой алдаа"] = check_4_busy_manual()

        results["5. stop() дараа дахин start() ажиллана"] = check_5_restart(camera)
    finally:
        camera.stop()
        cv2.destroyAllWindows()

    print("\n========== Алхам 6-ийн үр дүн ==========")
    for name, value in results.items():
        print(mark(value), name)
    for note in notes:
        print("Тэмдэглэл:", note)
    return 0 if all(v is not False for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
