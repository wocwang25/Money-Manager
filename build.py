"""
Build script: đóng gói app thành 1 file .exe duy nhất chạy trên Windows.
Chạy: python build.py
Kết quả: dist/ChiTieu.exe
"""

import subprocess
import sys
import os

APP_NAME = "MoneyManager"
MAIN_SCRIPT = "chi_tieu_app.py"

# Tìm đường dẫn customtkinter để include
import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--name", APP_NAME,
    "--onefile",                        # Gói tất cả vào 1 file .exe duy nhất
    "--windowed",                       # Không hiện cửa sổ console
    "--add-data", f"{ctk_path};customtkinter/",  # Include customtkinter assets
    "--add-data", "app_icon.ico;.",     # Include icon file
    "--hidden-import", "customtkinter",
    "--icon", "app_icon.ico",           # Icon cho file .exe
    MAIN_SCRIPT,
]

print("=" * 60)
print("  ĐÓNG GÓI APP CHI TIÊU → EXE (single file)")
print("=" * 60)
print(f"  Command: {' '.join(cmd)}")
print()

subprocess.run(cmd, check=True)

print()
print("=" * 60)
print(f"  ✅ BUILD XONG!")
print(f"  📁 File: dist/{APP_NAME}.exe")
print(f"  🚀 Chạy: dist/{APP_NAME}.exe")
print()
print(f"  Chỉ cần copy file dist/{APP_NAME}.exe là dùng được!")
print(f"  Đặt cùng thư mục với file CSV và config JSON.")
print("=" * 60)
