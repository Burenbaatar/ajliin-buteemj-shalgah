"""3-р гишүүн — камер ба нүүр илрүүлэлт. Хэн болохыг танихгүй, зураг хадгалахгүй."""
import cv2


class CameraService:
    def __init__(self, index=0):
        self.index = index
        self.capture = None
        # OpenCV кирилл үсэгтэй замаас файл нээж чаддаггүй тул XML-ийг Python-оор уншиж санах ойгоос өгнө
        with open(cv2.data.haarcascades + "haarcascade_frontalface_default.xml", encoding="utf-8") as file:
            storage = cv2.FileStorage(file.read(), cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
        self.detector = cv2.CascadeClassifier()
        self.detector.read(storage.getFirstTopLevelNode())

    def start(self):
        """Камер нээнэ. Амжилттай бол True."""
        self.capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)   # DSHOW — Windows дээр хурдан нээгдэнэ
        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.index)               # болохгүй бол OpenCV өөрөө сонгоно
        return self.capture.isOpened()

    def get_frame(self):
        """(BGR кадр, нүүрний тоо) буцаана. Кадр ирэхгүй бол None."""
        ok, frame = self.capture.read()
        if not ok:
            return None
        frame = cv2.flip(frame, 1)                                     # толин тусгал шиг
        faces = self.detector.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(60, 60))
        for x, y, w, h in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 0), 2)
        return frame, len(faces)

    def stop(self):
        self.capture.release()
