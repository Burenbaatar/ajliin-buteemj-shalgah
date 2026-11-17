"""Алхам 11. Туршилт ба код солилцоо — checklist-ийг нэг дор шалгана.

Ажиллуулах:
    python alkham11_turshilt.py               # автомат тест + бодит камер (нүүрээ хаах хэрэгтэй)
    python alkham11_turshilt.py --no-camera   # зөвхөн автомат тест (камергүй)

Checklist:
    [1] 3 удаа нээх/хаахад алдаа алга                  — тест + бодит камер 3 удаа
    [2] Нүүргүй үед count=0                            — тест + бодит камер (нүүрээ хаана)
    [3] Нүүртэй үед хүрээ гарч тоо өөрчлөгдөнө          — тест + бодит камер (камер руу харна)
    [4] Камер салсан/хаагдсан үед цонх гацахгүй         — CameraService тест + Tkinter цонхны тест
    [5] Бусад 4 гишүүний Python функцийг уншиж, нэг кодыг өөрөө өөрчилсөн — ГАРААР
"""
import os
import sys
import unittest

import cv2

from camera import CameraService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
USE_CAMERA = "--no-camera" not in sys.argv

# Checklist-ийн заалт бүрийг аль тестүүд батлах вэ
CHECKLIST_TESTS = {
    1: ["test_open_close_three_times", "test_stop_before_start_is_safe"],
    2: ["test_no_face_gives_zero", "test_real_detector_finds_nothing_on_black_frame"],
    3: ["test_face_box_and_count"],
    4: ["test_camera_unplugged_stops_cleanly", "test_camera_unplugged_window_does_not_freeze",
        "test_close_window_stops_camera", "test_camera_busy_releases_and_explains"],
}
CHECKLIST_NAMES = {
    1: "3 удаа нээх/хаахад алдаа алга",
    2: "Нүүргүй үед count=0",
    3: "Нүүртэй үед хүрээ гарч тоо өөрчлөгдөнө",
    4: "Камер салсан/хаагдсан үед цонх гацахгүй",
    5: "Бусад 4 гишүүний Python функцийг уншиж, нэг кодыг өөрөө өөрчилсөн",
}


CAMERA_TEST_MODULES = ["test_camera", "test_gui_holbolt"]  # бусад гишүүний тестийг энд оруулахгүй


def iter_tests(suite):
    """TestSuite дотор TestSuite байдаг тул бүх тестийг нэг жагсаалт болгож задална."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def run_unit_tests():
    """Камерын тестүүдийг ажиллуулаад ({тестийн_нэр: OK эсэх}, бүгд OK эсэх) буцаана."""
    print("=== Автомат тест (tests/test_camera.py, tests/test_gui_holbolt.py) ===")
    sys.path.insert(0, os.path.join(HERE, "tests"))
    suite = unittest.defaultTestLoader.loadTestsFromNames(CAMERA_TEST_MODULES)
    names = {test.id().split(".")[-1] for test in iter_tests(suite)}  # ажиллуулахаас ӨМНӨ цуглуулна
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    failed = {test.id().split(".")[-1] for test, _ in result.failures + result.errors}
    skipped = {test.id().split(".")[-1] for test, _ in result.skipped}
    return {name: (None if name in skipped else name not in failed) for name in names}, result.wasSuccessful()


def real_open_close_three_times():
    print("\n=== Бодит камер: 3 удаа нээх/хаах ===")
    camera = CameraService()
    for attempt in range(1, 4):
        if not camera.start():
            print(f"  {attempt}-р нээлт АМЖИЛТГҮЙ:", camera.last_error)
            return False
        result = camera.get_frame()
        camera.stop()
        camera.stop()  # давхар stop()
        if result is None or camera.running or camera.cap is not None:
            print(f"  {attempt}-р нээлт: кадр ирсэнгүй эсвэл зөв хаагдсангүй")
            return False
        print(f"  {attempt}-р нээлт OK — кадр {result[0].shape}, нүүр {result[1]}")
    return True


def real_face_and_no_face():
    """Алхам 6-ийн preview-г дахин ашиглана: нүүртэй (1+) ба нүүргүй (0) кадр хоёулаа гарах ёстой."""
    import alkham06_neg_odriin_turshilt as step6

    step6.AUTO = True            # асуулт асуухгүй, хоёулаа харагдвал өөрөө дуусна
    step6.PREVIEW_SECONDS = 20
    camera = CameraService()
    if not camera.start():
        print("  Алдаа:", camera.last_error)
        return False, False
    try:
        print("\n=== Бодит камер: нүүртэй / нүүргүй ===")
        face_frames = no_face_frames = 0
        original = camera.get_frame

        def counting_get_frame():  # preview-ийн кадр бүрийн тоог тоолно
            nonlocal face_frames, no_face_frames
            result = original()
            if result is not None:
                if result[1] > 0:
                    face_frames += 1
                else:
                    no_face_frames += 1
            return result

        camera.get_frame = counting_get_frame
        step6.check_3_preview(camera)
    finally:
        camera.stop()
        cv2.destroyAllWindows()
    return no_face_frames >= 3, face_frames >= 3


def mark(value):
    if value is None:
        return "[-] гараар   "
    return "[x] OK       " if value else "[ ] АМЖИЛТГҮЙ"


def main():
    tests, all_passed = run_unit_tests()

    real = {}
    if USE_CAMERA:
        real[1] = real_open_close_three_times()
        real[2], real[3] = real_face_and_no_face()

    print("\n========== Алхам 11-ийн үр дүн ==========")
    overall = all_passed
    for number in (1, 2, 3, 4):
        names = CHECKLIST_TESTS[number]
        test_ok = all(tests.get(name) is not False for name in names) and all(name in tests for name in names)
        ok = test_ok and real.get(number, True)
        overall = overall and ok
        source = f"тест {sum(1 for n in names if tests.get(n))}/{len(names)}"
        if number in real:
            source += ", бодит камер " + ("OK" if real[number] else "АМЖИЛТГҮЙ")
        print(mark(ok), CHECKLIST_NAMES[number], f"({source})")
    print(mark(None), CHECKLIST_NAMES[5])
    print("    → register.py, activity.py, productivity.py, main.py-г уншиж, нэг функцийг өөрчилж "
          "туршаад багийнханд тайлбарлана.")
    if not USE_CAMERA:
        print("\n(Бодит камерын туршилт алгасагдсан: --no-camera)")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
