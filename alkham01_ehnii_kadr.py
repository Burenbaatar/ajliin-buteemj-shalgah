"""Алхам 1. OpenCV-г шалгаж камерын эхний дүрсийг авах (GUI-ээс тусдаа туршилт).

Ажиллуулах:
    python alkham01_ehnii_kadr.py

Юу шалгах вэ:
    1) opencv-python суусан эсэх
    2) import cv2 амжилттай, хувилбар нь хэд вэ
    3) cv2.VideoCapture(0) — 0 гэдэг нь компьютерийн ҮНДСЭН камер (2 дахь камер бол 1)
    4) .isOpened() — камер үнэхээр нээгдсэн эсэх
    5) .read() нь (ret, frame) гэсэн ХОЁР утга буцаана
    6) frame нь NumPy массив, өнгө нь BGR (цэнхэр, ногоон, улаан) дараалалтай
    7) .release()-ээр хааж, ДАХИН нээж болж байгааг шалгана

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
    print('  Анхаар: энэ хувилбарт Haar cascade (Алхам 4) байхгүй. '
          'Суулгах: python -m pip install "opencv-python>=4.8,<5"')


def read_one_frame(attempt):
    """Камер нээж нэг кадр аваад хаана. Амжилттай бол True буцаана."""
    print(f"\n--- {attempt}-р нээлт ---")

    # 3) 0 = үндсэн камер. (camera.py дотор Windows дээр хурдан нээгддэг CAP_DSHOW-г ашигласан)
    cap = cv2.VideoCapture(0)

    # 4) Камер нээгдсэн эсэх
    if not cap.isOpened():
        print("Камер нээгдсэнгүй. Камер залгаатай эсэх, Windows-ийн "
              "Settings → Privacy & security → Camera зөвшөөрлийг шалгана уу.")
        cap.release()
        return False

    try:
        # 5) ret = уншиж чадсан эсэх (True/False), frame = зураг өөрөө (эсвэл None)
        ret, frame = cap.read()
        if not ret:
            print("Камер нээгдсэн ч кадр ирсэнгүй. Zoom, Teams зэрэг өөр програм "
                  "камерыг ашиглаж байгаа эсэхийг шалгана уу.")
            return False

        # 6) frame = NumPy массив: (өндөр, өргөн, 3 өнгөний суваг), дараалал нь BGR
        height, width, channels = frame.shape
        blue, green, red = frame[height // 2, width // 2]  # кадрын голын цэгийн өнгө
        print("ret =", ret)
        print("frame-ийн төрөл:", type(frame).__name__, "| нэг пикселийн утгын төрөл:", frame.dtype)
        print("Кадрын хэмжээ:", frame.shape, f"→ {width}×{height} пиксел, {channels} суваг")
        print(f"Голын цэгийн өнгө (B, G, R) = ({blue}, {green}, {red})")
        return True
    finally:
        cap.release()  # 7) камерыг заавал чөлөөлнө — алдаа гарсан ч finally ажиллана
        print("Камер хаагдлаа (release)")


# 7) Хааж дахин нээгээд дахин кадр авч чадаж байгааг шалгана
results = [read_one_frame(1), read_one_frame(2)]
if all(results):
    print("\nАМЖИЛТТАЙ: камер нээгдэж, кадр ирж, хаагдаад дахин нээгдлээ.")
    sys.exit(0)
print("\nТуршилт амжилтгүй — дээрх мессежийг уншина уу.")
sys.exit(1)
