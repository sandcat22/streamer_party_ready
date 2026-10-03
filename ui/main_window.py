"""
메인 윈도우 컨트롤러 (Main Window Controller)
- 로비 화면, 방장 화면, 참가자 화면 간의 전환 및 수명 주기 관리
- 하단 통합 상태바 & 우측 하단 버전 뱃지/빠른 업데이트 버튼 (거상 트레이더스 스타일)
- 윈도우 OS 타이틀바 강제 다크모드 적용
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any

from network.mqtt_manager import PartyNetworkManager
from network.config_manager import load_config
from network.updater import AutoUpdater, CURRENT_APP_VERSION
from ui.welcome_screen import WelcomeScreen
from ui.host_view import HostView
from ui.participant_view import ParticipantView
from ui.theme import (
    COLOR_BG, COLOR_PANEL, COLOR_PANEL_LIGHT, COLOR_CYAN,
    COLOR_READY, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_TEXT_DARK,
    COLOR_BADGE_OLD_BG, COLOR_BADGE_OLD_FG, COLOR_BADGE_OLD_BORDER,
    COLOR_BADGE_NEW_BG, COLOR_BADGE_NEW_FG, COLOR_BADGE_NEW_BORDER,
    COLOR_BTN_UPDATE_BG, COLOR_BTN_UPDATE_FG, COLOR_BTN_UPDATE_HOVER,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BOLD, FONT_BADGE,
    apply_forced_dark_mode
)


class PartyReadyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("스트리머 파티 매칭 & 레디 체커 (Streamer Party Ready)")
        self.root.geometry("660x720")
        self.root.minsize(600, 620)
        self.root.configure(bg=COLOR_BG)

        # 윈도우 OS 타이틀바 및 위젯 강제 다크모드 적용
        apply_forced_dark_mode(self.root)

        # 설정 불러오기
        self.config = load_config()

        # 네트워크 매니저 초기화 및 백그라운드 연결
        self.net = PartyNetworkManager()
        self.net.start_connection()

        # GitHub 자동 업데이터 초기화
        repo_name = self.config.get("github_repo", "sandcat22/streamer_party_ready")
        self.updater = AutoUpdater(repo_name=repo_name)
        self.current_update_info: Optional[Dict[str, Any]] = None

        self.current_view: Optional[tk.Frame] = None

        # 상단 콘텐츠 영역 & 하단 통합 상태바 레이아웃 구성
        self._build_main_layout()

        # 창 닫기 이벤트 바인딩
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 초기 시작 화면 띄우기
        self.show_welcome_screen()

        # 1초 후 백그라운드에서 GitHub 업데이트 확인 (조용히 확인)
        self.root.after(1000, lambda: self.check_updates_async(manual=False))

    def _build_main_layout(self):
        """메인 콘텐츠 프레임과 하단 일체형 상태바 구성"""
        # 1. 화면 전환용 콘텐츠 프레임
        self.content_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 하단 일체형 상태바 (다크 게이밍 스타일)
        self.footer_bar = tk.Frame(
            self.root,
            bg="#090D13",
            padx=14,
            pady=7,
            highlightbackground="#1E2638",
            highlightthickness=1
        )
        self.footer_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 하단 왼쪽: 서버 상태 표시
        footer_left = tk.Frame(self.footer_bar, bg="#090D13")
        footer_left.pack(side=tk.LEFT)

        self.lbl_status_dot = tk.Label(
            footer_left,
            text="●",
            font=("Malgun Gothic", 9),
            fg="#00E676",
            bg="#090D13"
        )
        self.lbl_status_dot.pack(side=tk.LEFT, padx=(0, 5))

        self.lbl_server_status = tk.Label(
            footer_left,
            text="서버 연결됨  |  실시간 레디 시스템 가동 중",
            font=FONT_BODY,
            fg="#8B949E",
            bg="#090D13"
        )
        self.lbl_server_status.pack(side=tk.LEFT)

        # 하단 오른쪽: 버전 뱃지 및 업데이트 액션 버튼 (스크린샷 스타일 완벽 일치)
        self.footer_right = tk.Frame(self.footer_bar, bg="#090D13")
        self.footer_right.pack(side=tk.RIGHT)

        # 버전 상태 뱃지 (기본: 최신버전)
        self.badge_version = tk.Label(
            self.footer_right,
            text=f"v{CURRENT_APP_VERSION} 최신버전",
            font=FONT_BADGE,
            bg=COLOR_BADGE_NEW_BG,
            fg=COLOR_BADGE_NEW_FG,
            padx=8,
            pady=2,
            highlightbackground=COLOR_BADGE_NEW_BORDER,
            highlightthickness=1
        )
        self.badge_version.pack(side=tk.LEFT, padx=(0, 8))

        # 업데이트 액션 버튼 (기본: 수동 확인 버튼)
        self.btn_update_action = tk.Button(
            self.footer_right,
            text="🔄 업데이트 확인",
            font=FONT_BODY,
            bg="#161B26",
            fg="#00E5FF",
            activebackground="#1F2637",
            activeforeground="#80D8FF",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.check_updates_async(manual=True)
        )
        self.btn_update_action.pack(side=tk.LEFT)

    def show_welcome_screen(self):
        """로비 (모드 선택) 화면 표시"""
        self._switch_view(
            WelcomeScreen(
                self.content_frame,
                on_create_room=self.show_host_screen,
                on_join_room=self.show_participant_screen
            )
        )
        self.root.title("스트리머 파티 매칭 & 레디 체커")
        self.lbl_server_status.config(text="서버 연결됨  |  로비 대기 중 (방 생성 또는 입장)")
        self.set_always_on_top(False)

    def show_host_screen(self, room_code: str, game_name: str, host_name: str, max_players: int):
        """방장 화면으로 전환"""
        self.net.create_room(room_code, game_name, host_name, max_players)
        self._switch_view(
            HostView(
                self.content_frame,
                net_manager=self.net,
                on_leave_room=self.show_welcome_screen,
                toggle_always_on_top=self.set_always_on_top
            )
        )
        self.root.title(f"[방장] {game_name} - 방 코드: {room_code}")
        self.lbl_server_status.config(text=f"방 개설 완료  |  방 코드: {room_code}  |  참가자 대기 중")
        self.set_always_on_top(True)

    def show_participant_screen(self, room_code: str, nickname: str):
        """참가자 화면으로 전환"""
        self.net.join_room(room_code, nickname)
        self._switch_view(
            ParticipantView(
                self.content_frame,
                net_manager=self.net,
                on_leave_room=self.show_welcome_screen
            )
        )
        self.root.title(f"[참가자] {nickname} - 방 코드: {room_code}")
        self.lbl_server_status.config(text=f"방 접속 완료  |  방 코드: {room_code}  |  닉네임: {nickname}")
        self.set_always_on_top(False)

    def set_always_on_top(self, enabled: bool):
        self.root.attributes("-topmost", enabled)

    def _switch_view(self, new_view: tk.Frame):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = new_view
        self.current_view.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------
    # 자동 업데이트 기능 (GitHub 연동 및 우측 하단 트레이더스 스타일 뱃지/버튼)
    # -------------------------------------------------------------
    def check_updates_async(self, manual: bool = False):
        """백그라운드에서 GitHub 업데이트 확인"""
        def _on_result(info: Optional[Dict[str, Any]]):
            self.root.after(0, lambda: self._handle_update_check_result(info, manual))

        self.updater.check_for_update_async(_on_result)

    def _handle_update_check_result(self, info: Optional[Dict[str, Any]], manual: bool):
        if info and info.get("has_update"):
            self.current_update_info = info
            self._apply_update_available_ui(info)
            if manual:
                messagebox.showinfo(
                    "새 버전 발견",
                    f"🎉 새로운 버전({info.get('latest_version')})이 출시되었습니다!\n\n"
                    f"우측 하단의 [⚡ 빠른 업데이트] 버튼을 눌러 바로 자동 설치할 수 있습니다."
                )
        else:
            self._apply_latest_version_ui()
            if manual:
                messagebox.showinfo(
                    "최신 버전",
                    f"현재 최신 버전(v{CURRENT_APP_VERSION})을 사용하고 있습니다."
                )

    def _apply_update_available_ui(self, info: Dict[str, Any]):
        """새 버전 발견 시 우측 하단을 [ v1.x.x 구버전 ] [ ⚡ 빠른 업데이트 ] 로 전환"""
        latest_ver = info.get("latest_version", "")

        # 1. 노란색 구버전 뱃지
        self.badge_version.config(
            text=f"v{CURRENT_APP_VERSION} 구버전",
            bg=COLOR_BADGE_OLD_BG,
            fg=COLOR_BADGE_OLD_FG,
            highlightbackground=COLOR_BADGE_OLD_BORDER
        )

        # 2. 산뜻한 네온 시안의 [ ⚡ 빠른 업데이트 ] 버튼
        self.btn_update_action.config(
            text="⚡ 빠른 업데이트",
            bg=COLOR_BTN_UPDATE_BG,
            fg=COLOR_BTN_UPDATE_FG,
            activebackground=COLOR_BTN_UPDATE_HOVER,
            activeforeground=COLOR_BTN_UPDATE_FG,
            font=FONT_BOLD,
            padx=10,
            pady=3,
            command=lambda: self._prompt_auto_update(info)
        )

    def _apply_latest_version_ui(self):
        """최신 버전 상태일 때의 UI"""
        self.badge_version.config(
            text=f"v{CURRENT_APP_VERSION} 최신버전",
            bg=COLOR_BADGE_NEW_BG,
            fg=COLOR_BADGE_NEW_FG,
            highlightbackground=COLOR_BADGE_NEW_BORDER
        )
        self.btn_update_action.config(
            text="🔄 업데이트 확인",
            bg="#161B26",
            fg="#00E5FF",
            activebackground="#1F2637",
            activeforeground="#80D8FF",
            font=FONT_BODY,
            padx=8,
            pady=2,
            command=lambda: self.check_updates_async(manual=True)
        )

    def _prompt_auto_update(self, info: Dict[str, Any]):
        """업데이트 확인 팝업 및 자동 다운로드 진행 창 열기"""
        latest_ver = info.get("latest_version", "")
        notes = info.get("release_notes", "기능 개선 및 버그 수정")

        msg = (
            f"새로운 버전이 준비되었습니다!\n\n"
            f"• 현재 버전: v{CURRENT_APP_VERSION}\n"
            f"• 최신 버전: {latest_ver}\n\n"
            f"[업데이트 내역]\n{notes}\n\n"
            f"지금 최신 버전을 자동으로 다운로드하여 설치하고 재시작하시겠습니까?"
        )

        if not messagebox.askyesno("자동 업데이트", msg):
            return

        dl_url = info.get("download_url")
        if not dl_url:
            messagebox.showerror("오류", "다운로드 파일 주소를 찾을 수 없습니다.")
            return

        self._start_download_modal(dl_url, latest_ver)

    def _start_download_modal(self, download_url: str, latest_version: str):
        """다운로드 진행률 모달 창 표시 및 교체 스크립트 실행"""
        modal = tk.Toplevel(self.root)
        modal.title("자동 업데이트 진행 중")
        modal.geometry("420x180")
        modal.configure(bg=COLOR_PANEL)
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.grab_set()

        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 90
            modal.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        tk.Label(
            modal,
            text=f"📥 최신 버전({latest_version}) 다운로드 중...",
            font=FONT_SUBTITLE,
            fg=COLOR_CYAN,
            bg=COLOR_PANEL
        ).pack(pady=(20, 10))

        prog_bar = ttk.Progressbar(modal, orient="horizontal", length=360, mode="determinate")
        prog_bar.pack(pady=5)

        lbl_status = tk.Label(
            modal,
            text="GitHub 서버에 연결하고 있습니다...",
            font=FONT_BODY,
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL
        )
        lbl_status.pack(pady=(5, 10))

        def _on_progress(downloaded: int, total: int):
            def _update():
                if total > 0:
                    pct = int((downloaded / total) * 100)
                    prog_bar["value"] = pct
                    mb_cur = downloaded / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    lbl_status.config(text=f"{mb_cur:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
                else:
                    mb_cur = downloaded / (1024 * 1024)
                    lbl_status.config(text=f"{mb_cur:.1f} MB 다운로드 중...")
            self.root.after(0, _update)

        def _on_complete(success: bool, msg: str):
            def _update_result():
                if success:
                    lbl_status.config(text="다운로드 완료! 프로그램을 교체하고 재시작합니다...", fg=COLOR_READY)
                else:
                    modal.destroy()
                    messagebox.showerror("업데이트 오류", msg)
            self.root.after(0, _update_result)

        # 백그라운드 다운로드 & 교체 스왑 스크립트 실행
        self.updater.download_and_install_update(
            download_url=download_url,
            progress_callback=_on_progress,
            on_complete=_on_complete
        )

    def _on_close(self):
        if self.net.room_code:
            self.net.leave_room()
        try:
            self.net.client.disconnect()
            self.net.client.loop_stop()
        except Exception:
            pass
        self.root.destroy()
