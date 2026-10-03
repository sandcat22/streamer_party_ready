"""
스트리머 파티 매칭 & 레디 체커 (Streamer Party Ready)
메인 실행 진입점 (Entry Point)
"""

import os
import sys
import ctypes
import multiprocessing
import tkinter as tk

# 고해상도(HiDPI / 4K) 디스플레이에서 폰트 및 UI 선명도 유지
try:
    if os.name == 'nt':
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Windows 10/11 시스템 및 창 전역 강제 다크모드 선언 (uxtheme ordinal 135: ForceDark)
try:
    if sys.platform == "win32":
        uxtheme = ctypes.windll.uxtheme
        set_app_mode = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int)((135, uxtheme))
        set_app_mode(2)  # 2: ForceDark
except Exception:
    pass

# 프로젝트 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from ui.main_window import PartyReadyApp
from network.updater import cleanup_leftover_updater_files


def main():
    # 이전 업데이트 잔여 임시 파일(_new.exe, updater.bat 등) 자동 청소
    cleanup_leftover_updater_files()

    root = tk.Tk()

    # 아이콘 적용
    icon_path = os.path.join(CURRENT_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    app = PartyReadyApp(root)
    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
