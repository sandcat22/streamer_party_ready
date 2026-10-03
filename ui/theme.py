"""
UI 테마, 색상 팔레트 및 오디오 유틸리티
- 프리미엄 딥 다크 게이밍 스타일 (치지직 / 스팀 / 트레이더스 무드)
- 윈도우 OS 타이틀바 강제 다크모드 (Immersive Dark Mode 20/19)
- 일관된 다크모드 ttk 위젯 스타일링
- 윈도우 시스템 사운드를 활용한 무설치 효과음
"""

import sys
import ctypes
import threading
from tkinter import ttk
try:
    import winsound
except ImportError:
    winsound = None

# 프리미엄 딥 다크 색상 팔레트
COLOR_BG = "#0D1117"            # 최상위 윈도우 배경 (Deep Obsidian)
COLOR_PANEL = "#161B26"         # 주요 카드 및 패널 배경
COLOR_PANEL_LIGHT = "#1F2637"   # 입력창 및 호버 배경
COLOR_BORDER = "#283145"        # 구분선 및 얇은 테두리

COLOR_TEXT_MAIN = "#F0F6FC"     # 선명한 고대비 흰색 텍스트
COLOR_TEXT_MUTED = "#8B949E"    # 보조 설명 텍스트
COLOR_TEXT_DARK = "#0D1117"     # 밝은 버튼 내부 어두운 텍스트

# 상태 및 악센트 색상
COLOR_CYAN = "#00E5FF"          # 네온 시안
COLOR_READY = "#00E676"         # 준비 완료 (네온 민트 그린)
COLOR_WAIT = "#FFB300"          # 대기 중 (골든 앰버)
COLOR_DANGER = "#FF5252"        # 경고 / 위험 (레드)
COLOR_PURPLE = "#B388FF"        # 방장 테마 (라벤더 퍼플)
COLOR_BLUE = "#448AFF"          # A팀 (청팀)
COLOR_ORANGE = "#FF9100"        # B팀 (홍팀)

# 우측 하단 업데이트 뱃지 전용 색상 (사용자 스크린샷 일치)
COLOR_BADGE_OLD_BG = "#2E2405"     # 구버전 노란 뱃지 배경
COLOR_BADGE_OLD_FG = "#FFD600"     # 구버전 노란 텍스트
COLOR_BADGE_OLD_BORDER = "#665200" # 구버전 노란 테두리

COLOR_BADGE_NEW_BG = "#131C18"     # 최신버전 뱃지 배경
COLOR_BADGE_NEW_FG = "#00E676"     # 최신버전 뱃지 텍스트
COLOR_BADGE_NEW_BORDER = "#1E382B" # 최신버전 뱃지 테두리

COLOR_BTN_UPDATE_BG = "#00E5FF"    # 빠른 업데이트 버튼 (네온 시안)
COLOR_BTN_UPDATE_FG = "#0A0E14"    # 버튼 글자색
COLOR_BTN_UPDATE_HOVER = "#80D8FF" # 버튼 호버

# 폰트
FONT_TITLE_LARGE = ("Malgun Gothic", 16, "bold")
FONT_TITLE = ("Malgun Gothic", 12, "bold")
FONT_SUBTITLE = ("Malgun Gothic", 10, "bold")
FONT_BODY = ("Malgun Gothic", 9)
FONT_BOLD = ("Malgun Gothic", 9, "bold")
FONT_BADGE = ("Malgun Gothic", 8, "bold")
FONT_READY_BIG = ("Malgun Gothic", 15, "bold")
FONT_MONO = ("Consolas", 11, "bold")


def apply_forced_dark_mode(root):
    """윈도우 OS 타이틀바 및 모든 위젯에 완벽한 강제 다크모드 적용"""
    if sys.platform == "win32":
        try:
            # 1. uxtheme의 SetPreferredAppMode(2: ForceDark) 호출
            try:
                uxtheme = ctypes.windll.uxtheme
                set_app_mode = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int)((135, uxtheme))
                set_app_mode(2)
            except Exception:
                pass

            root.update_idletasks()

            def _apply_titlebar_dark():
                try:
                    try:
                        frame_hex = root.wm_frame()
                        hwnd = int(frame_hex, 16) if frame_hex else 0
                    except Exception:
                        hwnd = 0

                    if not hwnd:
                        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()

                    if hwnd:
                        # 다크 모드 윈도우 컨트롤 테마 적용
                        try:
                            ctypes.windll.uxtheme.SetWindowTheme(hwnd, "DarkMode_Explorer", None)
                        except Exception:
                            pass

                        # Windows 11 전용 타이틀바 색상 (#0D1117 = 0x0017110D, 텍스트 흰색 = 0x00FFFFFF)
                        try:
                            cap_color = ctypes.c_int(0x0017110D)
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cap_color), ctypes.sizeof(cap_color))
                            text_color = ctypes.c_int(0x00FFFFFF)
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
                        except Exception:
                            pass

                        # Windows 10/11 Immersive Dark Mode 강제 (20, 구버전 19)
                        # Windows 10에서는 c_int(1) (BOOL TRUE)이어야 안정적으로 적용됨
                        for attr in (20, 19):
                            try:
                                val = ctypes.c_int(1)
                                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
                                if res == 0:
                                    break
                            except Exception:
                                pass

                        # DWM 프레임 강제 재페인팅 (SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
                        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
                except Exception:
                    pass

            _apply_titlebar_dark()
            # 윈도우가 화면에 완전히 매핑된 후에도 타이틀바가 유지되도록 보장
            root.after(50, _apply_titlebar_dark)
        except Exception:
            pass

    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # Treeview (참가자 명단 테이블) 다크 스타일
    style.configure(
        "Treeview",
        background="#161B26",
        foreground="#F0F6FC",
        fieldbackground="#161B26",
        bordercolor="#283145",
        lightcolor="#283145",
        darkcolor="#283145",
        rowheight=28,
        font=("Malgun Gothic", 9)
    )
    style.map(
        "Treeview",
        background=[('selected', '#1F2E45')],
        foreground=[('selected', '#00E5FF')]
    )
    style.configure(
        "Treeview.Heading",
        background="#1F2637",
        foreground="#8B949E",
        bordercolor="#283145",
        relief="flat",
        font=("Malgun Gothic", 9, "bold")
    )
    # Combobox 다크 스타일
    style.configure(
        "TCombobox",
        fieldbackground="#1F2637",
        background="#1F2637",
        foreground="#F0F6FC",
        arrowcolor="#00E5FF",
        bordercolor="#283145",
        darkcolor="#1F2637",
        lightcolor="#1F2637"
    )
    style.map(
        "TCombobox",
        fieldbackground=[('readonly', '#1F2637')],
        selectbackground=[('readonly', '#1F2637')],
        selectforeground=[('readonly', '#F0F6FC')]
    )
    # Scrollbar 다크 스타일
    style.configure(
        "Vertical.TScrollbar",
        background="#283145",
        troughcolor="#0D1117",
        bordercolor="#0D1117",
        arrowcolor="#8B949E"
    )
    # Progressbar 다크 스타일
    style.configure(
        "Horizontal.TProgressbar",
        background="#00E5FF",
        troughcolor="#1F2637",
        bordercolor="#283145"
    )


def play_sound_async(sound_type: str = "ready"):
    """윈도우 기본 고음질 시스템 알림음 재생 (기계음 Beep 제거)"""
    if winsound is None:
        return

    def _worker():
        try:
            if sound_type == "ready":
                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS)
            elif sound_type == "join":
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            elif sound_type == "ping":
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
            elif sound_type == "cancel":
                winsound.PlaySound("SystemDefault", winsound.SND_ALIAS)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()
