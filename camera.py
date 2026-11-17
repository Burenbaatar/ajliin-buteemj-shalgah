"""3-р гишүүн — камер: нүүр илрүүлэх, амьд хүн эсэхийг шалгах, ажилтныг таних.
Зураг, бичлэг хадгалахгүй. Ажилтны нүүрнээс зөвхөн 128 тооны «хээ» гаргаж register.py-д өгнө."""
import os
import random
import sys
import time

import cv2
import numpy as np

# .exe үед файлууд түр хавтаст (sys._MEIPASS) задардаг, python main.py үед энэ файлын хажууд байна
MODELS = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "models")
DETECTOR = "face_detection_yunet_2023mar.onnx"      # нүүр + нүд, хамар, ам (YuNet)
RECOGNIZER = "face_recognition_sface_2021dec.onnx"  # нүүрний 128 тооны хээ (SFace)
SAME_PERSON = 0.363        # SFace: cosine ижил төстэй байдал үүнээс их бол нэг хүн (OpenCV-ийн зөвлөмж)
TURN, CENTER = 0.1, 0.05   # толгой эргүүлсэн / буцаж шууд харсан гэж үзэх хамрын зөрүү (нүдний зайгаар)
SAME_POSE = 0.1            # толгой эхний байрлалдаа байна гэж үзэх цэгүүдийн зөрүү (нүдний зайгаар)
MIN_EYE_DISTANCE = 40      # нүдний зай үүнээс бага (хүн хол) бол нүдийг найдвартай харахгүй тул шалгахгүй
CLOSED_FRAMES = 3          # нүдээ дор хаяж 3 кадр (~0.3 сек) дараалан аньсан байх ёстой
CHECK_SECONDS = 25         # амьд хүн шалгалт 25 сек-д дуусахгүй бол амжилтгүй
RECHECK_SECONDS = 600      # 10 минут тутам амьд хүн эсэхийг дахин шалгана
AWAY_SECONDS = 5           # хүн 5 сек-ээс удаан алга болоод буцаж ирвэл дахин шалгана
FAIL_SECONDS = 3           # амжилтгүй болсны дараа 3 сек хүлээгээд дахин шалгана


def load_model(name):
    """OpenCV кирилл үсэгтэй замаас файл нээж чаддаггүй тул Python-оор уншиж санах ойгоос өгнө."""
    with open(os.path.join(MODELS, name), "rb") as file:
        return np.frombuffer(file.read(), np.uint8)


def load_cascade(name):
    """OpenCV-д хамт ирдэг Haar cascade-ийг мөн адил санах ойгоос уншина."""
    with open(cv2.data.haarcascades + name, encoding="utf-8") as file:
        storage = cv2.FileStorage(file.read(), cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
    cascade = cv2.CascadeClassifier()
    cascade.read(storage.getFirstTopLevelNode())
    return cascade


def points(face):
    """Нүүрний 5 цэг: 2 нүд, хамар, амны 2 булан."""
    return face[4:14].reshape(5, 2).astype(np.float32)


def eye_distance(face):
    return max(float(np.linalg.norm(face[6:8] - face[4:6])), 1.0)


def parallax(ref, face):
    """Толгой ref кадраас хойш хэр эргэсэн: сөрөг = зүүн, эерэг = баруун (толин тусгал кадр, нүдний зайгаар).
    Нүд, амны 4 цэг бараг нэг хавтгайд, хамар урагш цухуйсан. 4 цэгээр хавтгайн хөдөлгөөнийг тооцоод хамар
    хаана байх ёстойг таамаглана — толгой эргэхэд хамар таамагласан газраасаа эргэсэн зүг рүүгээ зөрнө."""
    src, dst = points(ref), points(face)
    plane = [0, 1, 3, 4]
    predicted = cv2.perspectiveTransform(src[2].reshape(1, 1, 2),
                                         cv2.getPerspectiveTransform(src[plane], dst[plane]))[0, 0]
    axis = dst[1] - dst[0] if dst[1][0] >= dst[0][0] else dst[0] - dst[1]   # нүдний шугам, зүүнээс баруун тийш
    return float(np.dot(dst[2] - predicted, axis) / max(np.dot(axis, axis), 1))


def pose_change(ref, face):
    """Толгойн байрлал ref-ээс хэр өөрчлөгдсөн (шилжих, томрохыг тооцохгүй). 0 = яг ижил."""
    matrix = cv2.estimateAffinePartial2D(points(ref), points(face), method=cv2.LMEDS)[0]
    if matrix is None:
        return 1.0
    moved = cv2.transform(points(ref).reshape(-1, 1, 2), matrix).reshape(-1, 2) - points(face)
    return float(np.sqrt((moved ** 2).sum(axis=1).mean())) / eye_distance(face)


def largest(faces):
    """Хамгийн том нүүр — компьютерийн өмнө суусан хүн."""
    return max(faces, key=lambda face: face[2] * face[3]) if len(faces) else None


def draw(frame, faces, color, step=None):
    """Нүүрийг хүрээлж, толгой эргүүлэх чиглэлийг сумаар зурна (OpenCV кирилл бичиж чаддаггүй)."""
    for x, y, w, h in faces[:, :4].astype(int):
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    if step in ("left", "right"):
        width = frame.shape[1]
        left, right = (width // 2 - width // 6, 40), (width // 2 + width // 6, 40)
        cv2.arrowedLine(frame, *((right, left) if step == "left" else (left, right)), (0, 220, 255), 6, tipLength=0.3)


class CameraService:
    def __init__(self, index=0):
        self.index = index
        self.capture = None
        empty = np.array([], np.uint8)
        try:                                   # OpenCV 4.11+: санах ойгоос — кирилл үсэгтэй замтай ч ажиллана
            self.detector = cv2.FaceDetectorYN.create("onnx", load_model(DETECTOR), empty, (320, 320), 0.8)
            self.recognizer = cv2.FaceRecognizerSF.create("onnx", load_model(RECOGNIZER), empty)
        except (cv2.error, TypeError):         # OpenCV 4.8–4.10: санах ойгоос уншиж чаддаггүй — файлын замаар
            self.detector = cv2.FaceDetectorYN.create(os.path.join(MODELS, DETECTOR), "", (320, 320), 0.8)
            self.recognizer = cv2.FaceRecognizerSF.create(os.path.join(MODELS, RECOGNIZER), "")
        self.eye_detector = load_cascade("haarcascade_eye.xml")                    # зөвхөн НЭЭЛТТЭЙ нүд олдог

    def start(self):
        """Камер нээнэ. Кадр бодитоор уншиж чадвал True.
        Зарим зөөврийн компьютер дээр DSHOW «нээгдсэн» гэх боловч кадр өгдөггүй, заримд нь MSMF л ажилладаг,
        0-р камер нь Windows Hello-ийн IR камер байж болно — тиймээс хэд хэдэн хослолыг туршина."""
        for index in dict.fromkeys((self.index, 0, 1)):               # давхардалгүй дараалал
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                capture = cv2.VideoCapture(index, backend)
                if capture.isOpened() and any(capture.read()[0] for _ in range(5)):   # эхний кадр хоосон ирж болно
                    self.capture, self.index = capture, index
                    return True
                capture.release()
        return False

    def get_frame(self):
        """(BGR кадр, нүүрнүүд) буцаана. Кадр ирэхгүй бол None.
        Нүүр бүр 15 тоо: x, y, өргөн, өндөр, 5 цэг (2 нүд, хамар, амны 2 булан), итгэл."""
        ok, frame = self.capture.read()
        if not ok:
            return None
        frame = cv2.flip(frame, 1)                                     # толин тусгал шиг
        self.detector.setInputSize((frame.shape[1], frame.shape[0]))
        faces = self.detector.detect(frame)[1]
        return frame, faces if faces is not None else np.empty((0, 15), np.float32)

    def feature(self, frame, face):
        """Нүүрний 128 тооны хээ. Зураг биш — үүнээс нүүрийг сэргээж чадахгүй."""
        return self.recognizer.feature(self.recognizer.alignCrop(frame, face)).copy()

    def open_eyes(self, frame, face):
        """Нээлттэй нүдний тоо (0–2). Нүд бүрийн орчмыг 64×64 болгоод нээлттэй нүд хайна."""
        gray, radius, found = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), int(eye_distance(face) * 0.45), 0
        for x, y in face[4:8].reshape(2, 2).astype(int):
            area = gray[max(y - radius, 0):y + radius, max(x - radius, 0):x + radius]
            if area.size:
                found += len(self.eye_detector.detectMultiScale(cv2.resize(area, (64, 64)), 1.1, 3,
                                                                minSize=(20, 20))) > 0
        return found

    def similarity(self, frame, face, owner):
        return self.recognizer.match(self.feature(frame, face), owner, cv2.FaceRecognizerSF_FR_COSINE)

    def stop(self):
        self.capture.release()


class LivenessCheck:
    """Амьд хүн эсэх: нүдээ аниад нээх, санамсаргүй дарааллаар толгой эргүүлэхийг хүснэ.
    Зураг нүдээ аньж чадахгүй. Урьдчилан бичсэн бичлэг санамсаргүй дарааллыг мэдэхгүй тул буруу тийш эргэнэ."""
    TEXT = {"center": "Камер руу шууд харна уу", "left": "Толгойгоо ← ЗҮҮН тийш эргүүлнэ үү",
            "right": "Толгойгоо БАРУУН → тийш эргүүлнэ үү", "blink": "Нүдээ 1 секунд аниад нээнэ үү"}

    def __init__(self):
        actions = random.choices(["left", "right"], k=2)
        actions.insert(random.randint(0, 2), "blink")                 # нүд аних алхам санамсаргүй байрлалд
        self.steps = ["center"]
        for action in actions:
            self.steps += [action] if action == "blink" else [action, "center"]
        self.total = len(self.steps)
        self.deadline = time.monotonic() + CHECK_SECONDS
        self.samples, self.reference = [], None                       # эхлэлийн толгойн байрлал
        self.turn, self.closed, self.too_far = 0.0, 0, False

    @property
    def step(self):
        return self.steps[0] if self.steps else None

    def instruction(self):
        text = "Камерт ойртож сууна уу" if self.too_far else self.TEXT[self.step]
        return f"Амьд хүн эсэхийг шалгаж байна ({self.total - len(self.steps) + 1}/{self.total}): {text}"

    def update(self, camera, frame, face):
        """'pending', 'passed' эсвэл 'failed' (хугацаа дууссан эсвэл буруу тийш эргүүлсэн)."""
        if not self.steps:
            return "passed"
        if face is None:
            return "pending"
        if time.monotonic() > self.deadline:
            return "failed"
        self.too_far = eye_distance(face) < MIN_EYE_DISTANCE
        if self.too_far:
            return "pending"
        if self.reference is None:                                    # 1-р алхам: 2 нүд нээлттэй 5 кадрын дундаж
            if camera.open_eyes(frame, face) == 2:
                self.samples.append(face)
            if len(self.samples) == 5:
                self.reference = np.mean(self.samples, axis=0)
                self.steps.pop(0)
            return "pending"
        self.turn = (self.turn + parallax(self.reference, face)) / 2   # 2 кадраар дундажилж санамсаргүй алдааг арилгана
        step = self.step
        if step in ("left", "right"):
            turn = self.turn if step == "right" else -self.turn
            if turn < -TURN:
                return "failed"                                       # буруу тийш — бичлэг байж магадгүй
            if turn > TURN:
                self.steps.pop(0)
        elif step == "center":
            if abs(self.turn) < CENTER:
                self.steps.pop(0)
        elif pose_change(self.reference, face) > SAME_POSE:
            self.closed = 0                                           # толгой хөдөлсөн — зураг хөдөлгөсөн байж магадгүй
        elif camera.open_eyes(frame, face) == 0:
            self.closed += 1                                          # толгой хөдлөөгүй, хоёр нүд аньсан
        else:
            if self.closed >= CLOSED_FRAMES:                          # хэдэн кадр аньсны дараа нээлээ
                self.steps.pop(0)
            self.closed = 0
        return "pending" if self.steps else "passed"


class FaceEnrollment:
    """Нүүр бүртгэл: эхлээд амьд хүн эсэхийг шалгаад, дараа нь шууд харсан 5 кадрын хээг дундажлана."""

    def __init__(self):
        self.check, self.features = LivenessCheck(), []

    def update(self, camera, frame, faces):
        """(хээ эсвэл None, тайлбар) буцаана. Хээ буцаавал бүртгэл дууссан."""
        if len(faces) != 1:
            return None, "Нүүр бүртгэл: кадрт яг нэг хүн байх ёстой"
        if self.check:
            result = self.check.update(camera, frame, faces[0])
            if result == "failed":
                self.check = LivenessCheck()
            if result != "passed":
                return None, "Нүүр бүртгэл — " + self.check.instruction()
            self.check = None
        self.features.append(camera.feature(frame, faces[0]))
        if len(self.features) < 5:
            return None, "Нүүр бүртгэл: камер руу шууд харна уу..."
        return np.mean(self.features, axis=0), "Нүүр бүртгэгдлээ"


class FaceMonitor:
    """Хэмжилтийн үеэр кадр бүрийг шалгаж, компьютерийн өмнө хэн хэдэн секунд суусныг тоолно."""
    TEXT = {"no_face": "Компьютерийн өмнө хүн алга",
            "fake": "Амьд хүн баталгаажсангүй (заавар биелсэнгүй) — зураг эсвэл бичлэг байж магадгүй. Дахин шалгана...",
            "unknown": "Амьд хүн ✓ · Нүүр бүртгээгүй тул хэн болохыг шалгах боломжгүй",
            "owner": "Амьд хүн ✓ · Бүртгэлтэй ажилтан ✓",
            "other": "АНХААР: Компьютерийн өмнө өөр хүн суусан байна!"}

    def __init__(self, owner):
        now = time.monotonic()
        self.set_owner(owner)
        self.check, self.failed_at, self.verified_at = LivenessCheck(), None, now
        self.face_seen = self.last = now
        self.matches, self.frames, self.failures = [], 0, 0
        self.seconds = {"owner": 0.0, "other": 0.0, "no_face": 0.0, "unverified": 0.0}

    def set_owner(self, owner):
        """Бүртгэсэн нүүрний хээ (128 тоо). None = бүртгээгүй."""
        self.owner = None if owner is None else np.array(owner, np.float32).reshape(1, -1)

    def update(self, camera, frame, faces, counting):
        """(төлөв, тайлбар) буцаана. counting=False бол (түр зогсоосон үед) хугацаа тоолохгүй."""
        now, face = time.monotonic(), largest(faces)
        if face is not None:
            if now - self.face_seen > AWAY_SECONDS:                   # хүн буцаж ирлээ — солигдсон байж магадгүй
                self.start_check()
            self.face_seen = now
        if (self.failed_at and now - self.failed_at > FAIL_SECONDS) or \
           (not self.check and not self.failed_at and now - self.verified_at > RECHECK_SECONDS):
            self.start_check()
        if self.check:
            result = self.check.update(camera, frame, face)
            if result == "passed":
                self.check, self.verified_at, self.matches = None, now, []
            elif result == "failed":
                self.check, self.failed_at = None, now
                self.failures += 1
        state = self.state(camera, frame, face)
        if counting:
            self.seconds[state if state in self.seconds else "unverified"] += min(now - self.last, 1)
        self.last = now
        return state, self.check.instruction() if state == "checking" else self.TEXT[state]

    def start_check(self):
        self.check, self.failed_at = LivenessCheck(), None

    def state(self, camera, frame, face):
        if face is None:
            return "no_face"
        if self.failed_at:
            return "fake"
        if self.check:
            return "checking"
        if self.owner is None:
            return "unknown"
        self.frames += 1
        if self.frames % 5 == 1 or not self.matches:                  # секундэд ~3 удаа таних нь хангалттай
            self.matches = (self.matches + [camera.similarity(frame, face, self.owner) >= SAME_PERSON])[-5:]
        return "owner" if sum(self.matches) * 2 > len(self.matches) else "other"   # сүүлийн 5-ын олонх

    def summary(self):
        return dict({name + "_seconds": round(seconds, 1) for name, seconds in self.seconds.items()},
                    liveness_failures=self.failures)

    def reset(self):
        """Дараагийн хэмжилтэд зориулж тоолуурыг тэглэнэ. Шалгалт, таних нь тасралтгүй үргэлжилнэ."""
        self.seconds = dict.fromkeys(self.seconds, 0.0)
        self.failures = 0
