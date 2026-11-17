"""5-р гишүүн — main.py-г нэг ProductivitySystem.exe болгоно. Ажиллуулах: python build_exe.py"""
import os

import PyInstaller.__main__

PyInstaller.__main__.run(["main.py", "--onefile", "--windowed", "--name", "ProductivitySystem",
                          "--add-data", f"models{os.pathsep}models",    # нүүр илрүүлэх, таних 2 загвар
                          "--collect-data", "cv2"])                     # нээлттэй нүд илрүүлэх XML
