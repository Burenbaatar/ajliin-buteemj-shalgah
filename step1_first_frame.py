"""Алхам 1: OpenCV-г шалгаж камерын эхний кадрыг авах (GUI-ээс тусдаа туршилт).

Ажиллуулах (энэ хавтаснаас):
    python step1_first_frame.py

Алдаа гарвал traceback биш, ойлгомжтой мессеж хэвлээд дуусна.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows терминалд кирилл үсэг зөв гаргана

# 1) OpenCV суусан эсэх
try:
    import cv2
except ImportError:
    print('OpenCV суугаагүй байна. Суулгах: python -m pip install "opencv-python>=4.8,<5"')
    sys.exit(1)

# 2) Импорт амжилттай бол хувилбарыг хэвлэнэ
print("OpenCV хувилбар:", cv2.__version__)
if not hasattr(cv2, "CascadeClassifier"):
    print('  Анхаар: энэ хувилбарт Haar cascade (4-р алхам) байхгүй. '
          'Багаараа: python -m pip install "opencv-python>=4.8,<5"')


def read_one_frame(attempt):
    """Камер нээж нэг кадр аваад хаана. Амжилттай бол True."""
    print(f"\n--- {attempt}-р нээлт ---")
    cap = cv2.VideoCapture(0)  # 3) 0 = компьютерийн үндсэн камер (2 дахь камер бол 1)

    # 4) Камер үнэхээр нээгдсэн эсэх
    if not cap.isOpened():
        print("Камер нээгдсэнгүй. Камер залгаатай эсэх, Windows-ийн "
              "Settings → Privacy & security → Camera зөвшөөрлийг шалгана уу.")
        return False

    try:
        # 5) read() хоёр утга буцаана: ok = уншиж чадсан эсэх (True/False), frame = зураг
        ok, frame = cap.read()
        if not ok:
            print("Камер нээгдсэн ч кадр ирсэнгүй. Zoom, Teams зэрэг өөр програм "
                  "камерыг ашиглаж байгаа эсэхийг шалгана уу.")
            return False

        # 6) frame нь NumPy массив: (өндөр, өргөн, 3 өнгөний суваг), өнгө нь BGR дараалалтай
        height, width, channels = frame.shape
        blue, green, red = frame[height // 2, width // 2]  # голын цэгийн өнгө
        print("ok =", ok)
        print("frame төрөл:", type(frame).__name__, "| утгын төрөл:", frame.dtype)
        print("Кадрын хэмжээ:", frame.shape, f"→ {width}×{height} пиксел, {channels} суваг")
        print(f"Голын цэгийн өнгө (B, G, R): ({blue}, {green}, {red})")
        return True
    finally:
        cap.release()  # 7) камерыг заавал чөлөөлнө — алдаа гарсан ч finally ажиллана
        print("Камер хаагдлаа (release)")


# 7) Хааж дахин нээгээд дахин кадр авч чадаж байгааг шалгана
results = [read_one_frame(1), read_one_frame(2)]
if all(results):
    print("\nАмжилттай: камер нээгдэж, кадр ирж, хаагдаад дахин нээгдлээ.")
    sys.exit(0)
print("\nТуршилт амжилтгүй — дээрх мессежийг уншина уу.")
sys.exit(1)
