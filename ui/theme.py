"""
UI 테마, 색상 팔레트 및 오디오 유틸리티
- 다크 게이밍 스타일 (디스코드 / 스팀 / 치지직 무드)
- 윈도우 시스템 사운드를 활용한 무설치 효과음
"""

import sys
import threading
try:
    import winsound
except ImportError:
    winsound = None

# 색상 팔레트
COLOR_BG = "#13141C"            # 메인 배경
COLOR_PANEL = "#1C1D29"         # 카드 및 패널 배경
COLOR_PANEL_LIGHT = "#252737"   # 입력창 및 호버 배경
COLOR_BORDER = "#323548"        # 구분선 및 테두리

COLOR_TEXT_MAIN = "#FFFFFF"     # 기본 텍스트 흰색
COLOR_TEXT_MUTED = "#9C9DB5"    # 보조 설명 텍스트
COLOR_TEXT_DARK = "#12131A"

# 상태 및 악센트 색상
COLOR_CYAN = "#00E5FF"          # 주요 브랜드 액센트
COLOR_READY = "#00E676"         # 준비 완료 (네온 그린)
COLOR_WAIT = "#FFB300"          # 대기 중 (앰버 옐로우)
COLOR_DANGER = "#FF5252"        # 강퇴 / 위험 (레드)
COLOR_PURPLE = "#B388FF"        # 방장 테마
COLOR_BLUE = "#448AFF"          # A팀 (청팀)
COLOR_ORANGE = "#FF9100"        # B팀 (홍팀)

# 폰트
FONT_TITLE_LARGE = ("Malgun Gothic", 16, "bold")
FONT_TITLE = ("Malgun Gothic", 13, "bold")
FONT_SUBTITLE = ("Malgun Gothic", 10, "bold")
FONT_BODY = ("Malgun Gothic", 9)
FONT_BOLD = ("Malgun Gothic", 9, "bold")
FONT_READY_BIG = ("Malgun Gothic", 15, "bold")
FONT_MONO = ("Consolas", 11, "bold")


def play_sound_async(sound_type: str = "ready"):
    """윈도우 기본 고음질 시스템 알림음 재생 (기계음 Beep 제거)"""
    if winsound is None:
        return

    def _worker():
        try:
            if sound_type == "ready":
                # 부드러운 윈도우 알림음 (띵동)
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
