# 3-р гишүүн — `camera.py`: камер ба нүүр илрүүлэлт (Алхам 1–11)

Камерын кадрт **нүүр байгаа эсэхийг илрүүлж тоолно**, хэн болохыг **танихгүй**.
Камерын зургийг файлд хадгалахгүй. Нүүрний тоо нь ажлын бүтээмжийн хувьтай холбогдохгүй.

## Суулгах

```bash
python -m pip install -r requirements.txt
```

## Алхам бүр аль файлд байгаа вэ

| Алхам | Юу хийсэн | Файл | Ажиллуулах |
|---|---|---|---|
| 1 | OpenCV шалгаж эхний кадр авах, хааж дахин нээх | `alkham01_ehnii_kadr.py` | `python alkham01_ehnii_kadr.py` |
| 2 | `CameraService` класс, `cap / detector / running`, давхар `start()`/`stop()`-оос хамгаалах | `camera.py` | — |
| 3 | `cv2.flip(frame, 1)` толин тусгал, харьцааг хадгалж жижигрүүлэх, BGR хэвээр буцаах | `camera.py` | — |
| 4 | Haar cascade XML ачаалах, `.empty()` шалгах, саарал дүрс, `detectMultiScale`, хүрээ зурах | `camera.py` | — |
| 5 | `while True` байхгүй, `release()`, камер салсан/эзлэгдсэн үед ойлгомжтой алдаа | `camera.py` | — |
| 6 | Нэг өдрийн туршилт (5 зүйлийн checklist) бодит камер дээр | `alkham06_neg_odriin_turshilt.py` | `python alkham06_neg_odriin_turshilt.py` (асуултгүй: `--auto`) |
| 7 | API тохиролцоо: `start() -> bool`, `get_frame() -> (frame, count) \| None`, `stop()` | `camera.py` | `python camera.py` |
| 8 | Tkinter GUI-тэй холбох: `after()`, `ImageTk.PhotoImage`, `after_cancel()`, хаахад `stop()` | `alkham08_gui_holbolt.py` | `python alkham08_gui_holbolt.py` |
| 9 | Гэрэл, параметр, fps туршилт + тэмдэглэл | `alkham09_parametr_turshilt.py` | `python alkham09_parametr_turshilt.py` (автомат: `--auto`) |
| 10 | `.exe` бүтээж (`--collect-data cv2`) дотор нь XML, камер ажиллаж байгааг шалгах | `alkham10_exe_shalgah.py` | `python alkham10_exe_shalgah.py --auto` (гараар: `--gui`) |
| 11 | Checklist: автомат тест + бодит камер | `alkham11_turshilt.py`, `tests/test_camera.py`, `tests/test_gui_holbolt.py` | `python alkham11_turshilt.py` (камергүй: `--no-camera`) |

## 1-р гишүүнд (main.py): камерыг яаж холбох вэ

`alkham08_gui_holbolt.py` бол бүрэн жишээ. Гол санаа нь:

```python
from camera import CameraService
import cv2
from PIL import Image, ImageTk

camera = CameraService()          # GUI-д ганцхан объект
after_id = None

def start_camera():
    if camera.start():
        render_camera_frame()
    else:
        status_label.config(text=camera.last_error)   # ойлгомжтой монгол тайлбар

def render_camera_frame():
    global after_id, photo
    result = camera.get_frame()
    if result is None and not camera.running:          # камер салсан
        status_label.config(text=camera.last_error)
        return
    if result is not None:
        frame, count = result
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)   # BGR → RGB-г GUI хийнэ
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        video_label.config(image=photo)
        count_label.config(text=f"Илэрсэн нүүр: {count}")
    after_id = root.after(30, render_camera_frame)     # while True биш!

def stop_camera():
    global after_id
    if after_id is not None:
        root.after_cancel(after_id)
        after_id = None
    camera.stop()

root.protocol("WM_DELETE_WINDOW", lambda: (stop_camera(), root.destroy()))
```

## 5-р гишүүнд (build_exe.py)

PyInstaller-ийн командад заавал `"--collect-data", "cv2"` нэмнэ. Үгүй бол `.exe` дотор
`haarcascade_frontalface_default.xml` байхгүй болж "XML олдсонгүй" алдаа гарна.
`CameraDemo.exe --self-test` нь XML ачаалагдаж байвал exit code 0 буцаадаг.

## Алхам 11. Туршилт ба код солилцоо

- [x] 3 удаа нээх/хаахад алдаа алга — `test_open_close_three_times`
- [x] Нүүргүй үед `count=0` — `test_no_face_gives_zero`
- [x] Нүүртэй үед хүрээ гарч тоо өөрчлөгдөнө — `test_face_box_and_count`
- [x] Камер салсан/хаагдсан үед цонх гацахгүй — `test_camera_unplugged_stops_cleanly`, `test_camera_unplugged_window_does_not_freeze`
- [ ] Бусад 4 гишүүний Python функцийг уншиж, нэг кодыг өөрөө өөрчилсөн — **гараар хийнэ**

## Багшид үзүүлэх (V хэсэг)

**Демо:** `python alkham08_gui_holbolt.py` (эсвэл `dist/CameraDemo.exe`) → Камер асаах → хүрээ гарна →
баруун гараа өргөж толин тусгалыг үзүүлнэ → Камер унтраах → дахин асаах.

**Алгоритм:** Камер нээх → кадр авах → толин тусгал → grayscale → `detectMultiScale` → хүрээ зурах →
нүүрний тоо буцаах → `after(30)` → дараагийн кадр.

**Багшийн асуултад бэлдэх хариулт:**

| Асуулт | Хариулт |
|---|---|
| OpenCV гэж юу вэ? | Зураг, видео боловсруулах нээлттэй сан. Камер нээх, кадр унших, өнгө хөрвүүлэх, нүүр хайх зэрэг бэлэн функцтэй. |
| `ret, frame` яагаад хоёр утгатай вэ? | `ret` (True/False) — кадр уншиж чадсан эсэх; `frame` — зураг өөрөө (NumPy массив). Камер салсан үед `ret=False`, `frame=None` болдог тул эхлээд `ret`-ийг шалгадаг. |
| `flip(frame, 1)` юу вэ? | Кадрыг зүүн/баруунаар эргүүлж толин тусгал болгоно. `0` бол дээш/доош, `-1` бол хоёулаа. |
| BGR ба GRAYSCALE ялгаа? | BGR — 3 суваг (цэнхэр, ногоон, улаан), OpenCV-ийн өнгөний дараалал. Grayscale — 1 суваг, зөвхөн гэрлийн хэмжээ. Haar зөвхөн гэрэл/сүүдрийн хэв маяг хардаг тул саарал дүрс хангалттай бөгөөд 3 дахин бага өгөгдөлтэй. |
| `detectMultiScale` яаж ажилладаг вэ? | Сургасан XML загварын дагуу кадрыг жижиг цонхоор гүйлгэж "нүүр шиг" гэрэл-сүүдрийн хэв маягийг хайна. Кадрыг `scaleFactor` (1.1 = 10%)-аар дахин дахин жижигрүүлж янз бүрийн хэмжээний нүүр олно. `minNeighbors` — ойролцоо хэдэн таарц байвал нүүр гэж үзэх, `minSize` — хамгийн жижиг нүүр. Үр дүн нь `(x, y, w, h)` жагсаалт. |
| Нүүр илрүүлэх ба таних ялгаа? | **Илрүүлэх** — "кадрт нүүр байна уу, хаана байна" (бидний хийсэн). **Таних** — "энэ хэн бэ" (хийгээгүй). Тиймээс өөр хүнийг ажилтан гэж тооцох, хувь хүний мэдээлэл хадгалах зүйл байхгүй. |
| Яагаад `while True` бичээгүй вэ? | Tkinter нэг урсгалд ажилладаг. `get_frame()` дотор хязгааргүй давталт байвал цонх гацна. Иймд GUI `after(30)`-аар 30 мс тутамд нэг кадр авдаг. |
| Haar яагаад заримдаа алддаг вэ? | Хажуу тийш эргэсэн, бүдэг гэрэлтэй, хэт ойр/хол нүүрийг алдаж, заримдаа нүүр биш зүйлийг нүүр гэж үздэг. Алхам 9-ийн тэмдэглэлд үүнийг ил тод бичсэн. |

## Нууцлал

Камерыг зөвхөн мэдэгдсэн, зөвшөөрөлтэй demo орчинд туршина. Камерын дүрс, нүүрийн зургийг
автоматаар хадгалахгүй (`alkham09_temdeglel.txt`-д зөвхөн тоо, параметр бичигдэнэ).
