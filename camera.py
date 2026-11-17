"""camera.py — 3-р гишүүн: OpenCV камер ба нүүр илрүүлэлт.

Энэ модуль камерын кадрт НҮҮР БАЙГАА ЭСЭХИЙГ илрүүлж тоолно. Хэн болохыг ТАНИХГҮЙ.
Камерын зургийг файлд хадгалахгүй: кадр санах ойд боловсруулагдаад шууд GUI-д очно.
Нүүрний тоо нь ажлын бүтээмжийн хувьтай холбогдохгүй (зөвхөн камерын мэдээлэл).

Багийн тохирсон API (Алхам 7):
    CameraService.start() -> bool              # True = камер нээгдсэн
    CameraService.get_frame() -> tuple | None  # (OpenCV BGR кадр, нүүрний тоо) эсвэл None
    CameraService.stop() -> None               # камер хаана, дараа нь start() дахин ажиллана

main.py-аас ашиглах:
    from camera import CameraService

    camera = CameraService()          # GUI-д ганцхан объект үүсгэнэ
    if not camera.start():
        print(camera.last_error)      # яагаад нээгдээгүйг ойлгомжтой тайлбарлана
    result = camera.get_frame()       # root.after(30, ...)-аар дахин дахин дуудна
    camera.stop()

Алгоритм: камер нээх → кадр авах → толин тусгал → саарал болгох → detectMultiScale
          → хүрээ зурах → нүүрний тоо буцаах → (GUI-ийн after()-аар) дараагийн кадр.

Шууд шалгах:
    python camera.py      # нэг кадр аваад кадрын хэмжээ, нүүрний тоог хэвлэнэ
"""
import os
import sys

import cv2

FACE_XML = "haarcascade_frontalface_default.xml"  # OpenCV 4.x-тэй хамт ирдэг файл
BOX_COLOR = (0, 200, 0)  # OpenCV өнгийг BGR дарааллаар бичдэг → (0, 200, 0) = ногоон
MAX_READ_FAILS = 15      # дараалан 15 кадр (~0.5 сек) ирэхгүй бол камер салсан гэж үзнэ


# ------------------------------------------------------------------ Алхам 4: XML ачаалах
def find_face_xml():
    """Нүүр илрүүлэх XML файлын замыг олно. Олдохгүй бол None.

    Хайх дараалал:
      1) cv2.data.haarcascades — pip-ээр суулгасан OpenCV-ийн data хавтас
      2) .exe дотор бол PyInstaller задалсан хавтас: sys._MEIPASS/cv2/data  (Алхам 10)
      3) camera.py-тэй нэг хавтаст хуулсан XML (нөөц арга)
    """
    folders = []
    if hasattr(cv2, "data"):
        folders.append(cv2.data.haarcascades)
    bundle = getattr(sys, "_MEIPASS", None)  # зөвхөн .exe дотор байдаг
    if bundle:
        folders.append(os.path.join(bundle, "cv2", "data"))
    folders.append(os.path.dirname(os.path.abspath(__file__)))

    for folder in folders:
        path = os.path.join(folder, FACE_XML)
        if os.path.isfile(path):
            return path
    return None


def _load_xml_from_memory(path):
    """XML-ийг Python-оор уншаад OpenCV-д санах ойгоос өгнө.

    OpenCV өөрөө кирилл үсэгтэй замаас (жишээ нь C:\\Users\\Бат\\...) файл нээж чаддаггүй.
    Python-ийн open() харин чаддаг тул ийм тохиолдолд энэ аргаар ачаална.
    """
    with open(path, encoding="utf-8") as f:
        xml_text = f.read()
    storage = cv2.FileStorage(xml_text, cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
    detector = cv2.CascadeClassifier()
    detector.read(storage.getFirstTopLevelNode())
    storage.release()
    return detector


def load_face_detector():
    """Haar cascade нүүр илрүүлэгч үүсгэнэ. Буцаах утга: (detector, xml_зам).

    XML олдохгүй эсвэл ачаалагдахгүй бол ойлгомжтой тайлбартай RuntimeError өгнө.
    """
    if not hasattr(cv2, "CascadeClassifier"):
        raise RuntimeError("Энэ OpenCV хувилбарт Haar cascade байхгүй (OpenCV " + cv2.__version__ + ").\n"
                           'Засах: python -m pip install "opencv-python>=4.8,<5"')

    path = find_face_xml()  # 4.1
    if path is None:
        raise RuntimeError("Нүүр илрүүлэх XML (" + FACE_XML + ") олдсонгүй.\n"
                           ".exe бол PyInstaller-т --collect-data cv2 нэмж дахин багцална уу.")

    try:
        detector = cv2.CascadeClassifier(path)  # 4.2
    except cv2.error:
        detector = cv2.CascadeClassifier()
    if detector.empty():  # 4.3: empty() == True → XML ачаалагдаагүй
        detector = _load_xml_from_memory(path)
    if detector.empty():
        raise RuntimeError("Нүүр илрүүлэх XML олдсон ч ачаалагдсангүй: " + path)
    return detector, path


# ------------------------------------------------------------------ Алхам 1, 5: камер нээх
def open_camera(index=0):
    """Камер нээгээд cv2.VideoCapture буцаана. Нээгдэхгүй бол None.

    Windows дээр эхлээд DirectShow (CAP_DSHOW)-оор нээнэ — илүү хурдан нээгддэг.
    Болохгүй бол OpenCV-ийн өөрийн сонгосон аргаар (CAP_ANY) дахин оролдоно.
    """
    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            return cap
        cap.release()
    return None


# ------------------------------------------------------------------ Алхам 3: кадр бэлдэх
def resize_keep_ratio(frame, max_width):
    """Кадр max_width-ээс өргөн бол өндөр/өргөний харьцааг ХАДГАЛЖ жижигрүүлнэ.

    Өргөн, өндрийг ижил хувиар багасгадаг тул дүрс сунгагдаж гажихгүй.
    Жижиг кадрыг томруулахгүй, огт хөндөхгүй.
    """
    height, width = frame.shape[:2]
    if not max_width or width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)


def draw_faces(frame, faces):
    """Алхам 4.6: илэрсэн нүүр бүрийн (x, y, w, h) хүрээг ногоон тэгш өнцөгтөөр зурна."""
    for x, y, w, h in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), BOX_COLOR, 2)


# ------------------------------------------------------------------ Алхам 2: класс
class CameraService:
    """Камерын нээлттэй/хаалттай төлөвийг нэг объект дотор хадгална.

    Яагаад класс вэ? Камер (self.cap), илрүүлэгч (self.detector), нээлттэй эсэх
    (self.running) гэсэн төлвүүд нэг дор байх тул GUI-тэй найдвартай холбогдоно.

    get_frame() ГАНЦ кадр авдаг — дотор нь while True байхгүй (Алхам 5).
    Давталтыг GUI өөрөө root.after(30, ...)-аар хийнэ, тэгэхгүй бол Tkinter цонх гацна.
    """

    def __init__(self, camera_index=0, max_width=640, mirror=True):
        # Алхам 2.2: төлөвийн хувьсагчид
        self.cap = None        # cv2.VideoCapture (камер хаалттай үед None)
        self.detector = None   # cv2.CascadeClassifier (анх start() хийхэд нэг удаа ачаална)
        self.running = False   # камер нээлттэй эсэх

        self.camera_index = camera_index  # 0 = үндсэн камер
        self.max_width = max_width        # үүнээс өргөн кадрыг жижигрүүлнэ (fps хамгаална)
        self.mirror = mirror              # True = толин тусгал шиг харуулна
        self.last_error = ""              # сүүлийн алдааны тайлбар — GUI-д харуулна
        self.xml_path = ""                # ачаалсан XML-ийн зам (.exe шалгахад хэрэгтэй)
        self.read_fails = 0               # дараалан хэдэн кадр уншиж чадаагүй вэ

        # Алхам 9: detectMultiScale-ийн параметрүүд (туршиж өөрчилж болно)
        self.scale_factor = 1.1   # алхам бүрт кадрыг 10%-иар жижигрүүлж янз бүрийн хэмжээний нүүр хайна
        self.min_neighbors = 5    # ойролцоо 5+ таарц байвал л нүүр гэж үзнэ (хуурамчийг багасгана)
        self.min_size = (60, 60)  # 60×60 пикселээс жижиг зүйлийг тоохгүй
        self.equalize = True      # саарал дүрсийг тодосгох — бүдэг гэрэлд тусална

    def start(self) -> bool:
        """Камер нээнэ. Амжилттай бол True, болохгүй бол False (шалтгаан нь self.last_error-д)."""
        if self.running:
            return True  # Алхам 2.4: аль хэдийн нээлттэй → давхар камер нээхгүй
        self.last_error = ""

        if self.detector is None:
            try:
                self.detector, self.xml_path = load_face_detector()
            except (RuntimeError, OSError, cv2.error) as error:
                self.last_error = str(error)
                return False

        cap = open_camera(self.camera_index)
        if cap is None:  # Алхам 5.5: зөвшөөрөлгүй/камергүй үед ойлгомжтой тайлбар
            self.last_error = ("Камер нээгдсэнгүй. Камер залгаатай эсэх, Windows-ийн "
                               "Settings → Privacy & security → Camera зөвшөөрлийг шалгана уу.")
            return False

        # Туршилтын кадр: өөр програм камерыг эзэлсэн үед нээгдсэн мэт боловч кадр ирдэггүй.
        if not self._can_read(cap):
            cap.release()
            self.last_error = ("Камер нээгдсэн ч кадр ирсэнгүй. Zoom, Teams, Camera зэрэг өөр "
                               "програм камерыг ашиглаж байгаа эсэхийг шалгаад хаана уу.")
            return False

        self.cap = cap
        self.running = True
        self.read_fails = 0
        return True

    @staticmethod
    def _can_read(cap, tries=5):
        """Камер нээгдсэний дараа эхний хэдэн кадрын аль нэг нь ирж байгаа эсэх."""
        for _ in range(tries):
            ok, frame = cap.read()
            if ok and frame is not None:
                return True
        return False

    def get_frame(self):
        """Нэг кадр авч (кадр, нүүрний тоо) буцаана. Кадр ирэхгүй бол None.

        Кадр нь BGR өнгөтэй NumPy массив. Tkinter-т харуулахын тулд RGB болгох нь
        1-р гишүүний (main.py) ажил (Алхам 3.4).
        Дараалан MAX_READ_FAILS удаа кадр ирэхгүй бол камер салсан гэж үзээд
        өөрөө stop() хийнэ — GUI нь camera.running-г шалгаад алдааг харуулна.
        """
        if not self.running or self.cap is None:
            return None

        try:
            ok, frame = self.cap.read()  # ok = уншиж чадсан эсэх, frame = зураг өөрөө
        except cv2.error:
            ok, frame = False, None
        if not ok or frame is None:  # Алхам 3.3, 5.4: амжилтгүй бол None
            self.read_fails += 1
            self.last_error = "Камераас кадр уншиж чадсангүй."
            if self.read_fails >= MAX_READ_FAILS:
                self.stop()
                self.last_error = ("Камераас кадр ирэхээ больсон тул камерыг хаалаа "
                                   "(камер салсан эсвэл өөр програм эзэлсэн байж магадгүй).")
            return None
        self.read_fails = 0
        self.last_error = ""

        if self.mirror:
            frame = cv2.flip(frame, 1)  # Алхам 3.1: 1 = зүүн/баруунаар эргүүлнэ (толин тусгал)
        frame = resize_keep_ratio(frame, self.max_width)  # Алхам 3.2

        faces = self.detect_faces(frame)
        draw_faces(frame, faces)
        return frame, len(faces)  # Алхам 4.7

    def detect_faces(self, frame):
        """Алхам 4.4–4.5: кадр дээрх нүүр бүрийн (x, y, w, h) жагсаалт. Нүүргүй бол []."""
        if self.detector is None:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Haar зөвхөн гэрэл/сүүдэр хардаг → саарал
        if self.equalize:
            gray = cv2.equalizeHist(gray)
        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
        )
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]

    def stop(self) -> None:
        """Камерыг хаана. Хэдэн ч удаа дуудсан алдаа гаргахгүй (Алхам 2.5).

        Дараа нь start() дахин ажиллахад бэлэн төлөв үлдээнэ (Алхам 7.3).
        Илрүүлэгчийг (self.detector) устгахгүй — дараагийн start() хурдан болно.
        """
        if self.cap is not None:
            self.cap.release()  # Алхам 5.3: камерыг чөлөөлнө → бусад програм дахин нээж чадна
        self.cap = None
        self.running = False
        self.read_fails = 0


# ------------------------------------------------------------------ Шууд турших
def main():
    """python camera.py → нэг кадр аваад үр дүнг хэвлэнэ. Амжилттай бол 0, алдаатай бол 1."""
    camera = CameraService()
    if not camera.start():
        print("Алдаа:", camera.last_error)
        return 1
    try:
        result = camera.get_frame()
    finally:
        camera.stop()  # алдаа гарсан ч камерыг заавал хаана
    if result is None:
        print("Алдаа:", camera.last_error)
        return 1
    frame, count = result
    print("OpenCV", cv2.__version__)
    print("XML:", camera.xml_path)
    print("Кадрын хэмжээ (өндөр, өргөн, суваг):", frame.shape)
    print("Нүүрний тоо:", count)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows терминалд кирилл үсэг зөв гаргана
    sys.exit(main())
