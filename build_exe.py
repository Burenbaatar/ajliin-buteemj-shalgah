"""5-р гишүүн — main.py-г нэг ProductivitySystem.exe болгоно. Ажиллуулах: python build_exe.py"""
import PyInstaller.__main__

PyInstaller.__main__.run(["main.py", "--onefile", "--windowed", "--name", "ProductivitySystem",
                          "--collect-data", "cv2"])   # cv2 — нүүр илрүүлэх XML-ийг .exe-д хамт хийнэ
