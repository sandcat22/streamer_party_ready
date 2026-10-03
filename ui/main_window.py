"""
메인 윈도우 컨트롤러 (Main Window Controller)
- 로비 화면, 방장 화면, 참가자 화면 간의 전환 및 수명 주기 관리
- GitHub 자동 업데이트 감지 및 우측 하단 플로팅 업데이트 버튼 표시
- 원클릭 자동 설치 & 무중단 재실행 관리
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
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BOLD
)


class PartyReadyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("스트리머 파티 매칭 & 레디 체커 (Streamer Party Ready)")
        self.root.geometry("640x720")
        self.root.minsize(580, 600)
        self.root.configure(bg=COLOR_BG)

        # 설정 불러오기
        self.config = load_config()

        # 네트워크 매니저 초기화 및 백그라운드 연결
        self.net = PartyNetworkManager()
        self.net.start_connection()

        # GitHub 자동 업데이터 초기화
        repo_name = self.config.get("github_repo", "sandcat22/streamer_party_ready")
        self.updater = AutoUpdater(repo_name=repo_name)
        self.update_btn: Optional[tk.Button] = None
        self.current_update_info: Optional[Dict[str, Any]] = None

        self.current_view: Optional[tk.Frame] = None

        # 창 닫기 이벤트 바인딩
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 초기 시작 화면 띄우기
        self.show_welcome_screen()

        # 실행 시 백그라운드에서 GitHub 업데이트 확인 (조용히 확인)
        self.root.after(1500, lambda: self.check_updates_async(manual=False))

    def show_welcome_screen(self):
        """로비 (모드 선택) 화면 표시"""
        self._switch_view(
            WelcomeScreen(
                self.root,
                on_create_room=self.show_host_screen,
                on_join_room=self.show_participant_screen,
                on_check_update=lambda: self.check_updates_async(manual=True)
            )
        )
        self.root.title("스트리머 파티 매칭 & 레디 체커")
        self.set_always_on_top(False)

    def show_host_screen(self, room_code: str, game_name: str, host_name: str, max_players: int):
        """방장 화면으로 전환"""
        self.net.create_room(room_code, game_name, host_name, max_players)
        self._switch_view(
            HostView(
                self.root,
                net_manager=self.net,
                on_leave_room=self.show_welcome_screen,
                toggle_always_on_top=self.set_always_on_top
            )
        )
        self.root.title(f"[방장] {game_name} - 방 코드: {room_code}")
        self.set_always_on_top(True)

    def show_participant_screen(self, room_code: str, nickname: str):
        """참가자 화면으로 전환"""
        self.net.join_room(room_code, nickname)
        self._switch_view(
            ParticipantView(
                self.root,
                net_manager=self.net,
                on_leave_room=self.show_welcome_screen
            )
        )
        self.root.title(f"[참가자] {nickname} - 방 코드: {room_code}")
        self.set_always_on_top(False)

    def set_always_on_top(self, enabled: bool):
        self.root.attributes("-topmost", enabled)

    def _switch_view(self, new_view: tk.Frame):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = new_view
        self.current_view.pack(fill=tk.BOTH, expand=True)

        # 화면 전환 시에도 우측 하단 업데이트 버튼이 가려지지 않도록 최상단으로 올림
        if self.update_btn and self.update_btn.winfo_exists():
            self.update_btn.lift()

    # -------------------------------------------------------------
    # 자동 업데이트 기능 (GitHub 연동 및 우측 하단 알림 버튼)
    # -------------------------------------------------------------
    def check_updates_async(self, manual: bool = False):
        """백그라운드에서 GitHub 업데이트 확인"""
        def _on_result(info: Optional[Dict[str, Any]]):
            self.root.after(0, lambda: self._handle_update_check_result(info, manual))

        self.updater.check_for_update_async(_on_result)

    def _handle_update_check_result(self, info: Optional[Dict[str, Any]], manual: bool):
        if info and info.get("has_update"):
            self.current_update_info = info
            self._render_floating_update_button(info)
            if manual:
                messagebox.showinfo(
                    "새 버전 발견",
                    f"🎉 새로운 버전({info.get('latest_version')})이 출시되었습니다!\n\n"
                    f"우측 하단의 [⚡ 새 버전 업데이트] 버튼을 눌러 바로 자동 설치할 수 있습니다."
                )
        else:
            if manual:
                messagebox.showinfo(
                    "업데이트 확인",
                    f"현재 최신 버전(v{CURRENT_APP_VERSION})을 사용하고 있습니다."
                )

    def _render_floating_update_button(self, info: Dict[str, Any]):
        """프로그램 우측 하단에 눈에 띄는 업데이트 버튼 생성"""
        if self.update_btn and self.update_btn.winfo_exists():
            self.update_btn.destroy()

        ver = info.get("latest_version", "")
        self.update_btn = tk.Button(
            self.root,
            text=f"⚡ 새 버전({ver}) 업데이트",
            font=FONT_BOLD,
            bg="#00E676",
            fg="#121212",
            activebackground="#69F0AE",
            activeforeground="#121212",
            relief=tk.RAISED,
            bd=2,
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: self._prompt_auto_update(info)
        )
        # 프로그램 우측 하단 모서리에 고정 배치
        self.update_btn.place(relx=1.0, rely=1.0, x=-16, y=-16, anchor="se")
        self.update_btn.lift()

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

        # 메인 윈도우 중앙에 배치
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
