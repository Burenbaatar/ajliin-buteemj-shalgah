"""PyInstaller ашиглан Windows-ийн GUI програмыг багцална.

Нэг EXE файл үүсгэхдээ ``python build_exe.py`` командыг ажиллуулна.
Эхний туршилтын хавтас хэлбэрийн багцад ``--onedir`` сонголтыг хэрэглэнэ.
Энэ скриптийг Windows үйлдлийн систем дээр ажиллуулах шаардлагатай.
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    # Хуучин Windows консол дээр Монгол тэмдэгт зөв гарах кодчиллыг тохируулна.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="ProductivitySystem програмыг багцлах")
    build_type = parser.add_mutually_exclusive_group()
    build_type.add_argument(
        "--onefile",
        dest="onefile",
        action="store_true",
        help="Нэг EXE файл үүсгэх (анхдагч)",
    )
    build_type.add_argument(
        "--onedir",
        dest="onefile",
        action="store_false",
        help="Эхний туршилтад зориулсан хавтас хэлбэрийн багц үүсгэх",
    )
    parser.set_defaults(onefile=True)
    args = parser.parse_args()

    entrypoint = ROOT / "main.py"
    if not entrypoint.is_file():
        parser.error(f"Үндсэн програмын файл олдсонгүй: {entrypoint}")

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if args.onefile else "--onedir",
        "--windowed",
        "--name",
        "ProductivitySystem",
        "--collect-data",
        "cv2",
        str(entrypoint),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
