"""
참가자 (시청자/지인) 뷰 (Participant Ready Screen)
- 방장이 지정한 게임명 및 실시간 공지 확인
- 직관적인 대형 [준비 완료(READY)] 토글 버튼
- 현재 방의 다른 참가자 현황 확인
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any

from network.mqtt_manager import PartyNetworkManager
from ui.theme import (
    COLOR_BG, COLOR_PANEL, COLOR_PANEL_LIGHT, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_TEXT_DARK,
    COLOR_CYAN, COLOR_READY, COLOR_WAIT, COLOR_DANGER,
    FONT_TITLE_LARGE, FONT_TITLE, FONT_SUBTITLE, FONT_BODY,
    FONT_BOLD, FONT_READY_BIG, FONT_MONO, play_sound_async
)


class ParticipantView(tk.Frame):
    def __init__(
        self,
        parent,
        net_manager: PartyNetworkManager,
        on_leave_room: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.net = net_manager
        self.on_leave_room = on_leave_room

        self._build_ui()
        self._bind_network_events()

    def _build_ui(self):
        # 1. 상단 정보 헤더 (게임명 및 방 정보)
        header = tk.Frame(self, bg=COLOR_PANEL, padx=16, pady=12, highlightbackground=COLOR_BORDER, highlightthickness=1)
        header.pack(fill=tk.X, padx=12, pady=(10, 8))

        top_row = tk.Frame(header, bg=COLOR_PANEL)
        top_row.pack(fill=tk.X)

        tk.Label(top_row, text="🙋 참가자 모드", font=FONT_TITLE, fg=COLOR_READY, bg=COLOR_PANEL).pack(side=tk.LEFT)

        # 방 코드 & 내 닉네임 뱃지
        badge = tk.Frame(top_row, bg=COLOR_PANEL_LIGHT, padx=8, pady=3)
        badge.pack(side=tk.LEFT, padx=14)
        tk.Label(badge, text=f"방 코드: {self.net.room_code} | 내 닉네임: {self.net.my_nickname}", font=FONT_BOLD, fg=COLOR_CYAN, bg=COLOR_PANEL_LIGHT).pack()

        # 나가기 버튼
        btn_leave = tk.Button(
            top_row,
            text="방 나가기",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            command=self._confirm_leave
        )
        btn_leave.pack(side=tk.RIGHT)

        # 게임명 배너
        game_box = tk.Frame(header, bg=COLOR_PANEL_LIGHT, padx=12, pady=8)
        game_box.pack(fill=tk.X, pady=(10, 0))

        tk.Label(game_box, text="방이름 / 게임명 / 컨텐츠명:", font=FONT_BODY, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_LIGHT).pack(anchor="w")
        self.lbl_game_name = tk.Label(
            game_box,
            text=self.net.room_info.get("game_name", "대기 중"),
            font=FONT_TITLE_LARGE,
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_PANEL_LIGHT
        )
        self.lbl_game_name.pack(anchor="w", pady=(2, 0))

        # 2. 방장 공지사항 영역
        self.notice_box = tk.Frame(self, bg="#2A2415", padx=12, pady=6, highlightbackground=COLOR_WAIT, highlightthickness=1)
        self.notice_box.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.lbl_notice = tk.Label(
            self.notice_box,
            text=f"📢 방장 공지: {self.net.room_info.get('notice', '준비되면 아래 버튼을 눌러주세요!')}",
            font=FONT_BOLD,
            fg="#FFE082",
            bg="#2A2415",
            anchor="w"
        )
        self.lbl_notice.pack(fill=tk.X)

        # 3. 메인 READY 액션 영역 (초대형 버튼)
        action_card = tk.Frame(self, bg=COLOR_PANEL, padx=20, pady=24, highlightbackground=COLOR_BORDER, highlightthickness=1)
        action_card.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.lbl_status_desc = tk.Label(
            action_card,
            text="아직 준비되지 않았습니다. 게임 준비가 끝나면 아래 버튼을 눌러주세요!",
            font=FONT_SUBTITLE,
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL
        )
        self.lbl_status_desc.pack(pady=(0, 16))

        # 초대형 레디 토글 버튼
        self.btn_ready = tk.Button(
            action_card,
            text="⚡ 준비 완료 (READY)",
            font=FONT_READY_BIG,
            bg=COLOR_WAIT,
            fg=COLOR_TEXT_DARK,
            activebackground="#FFE082",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            height=2,
            command=self._toggle_ready
        )
        self.btn_ready.pack(fill=tk.X, ipady=10)

        # 4. 방의 다른 참가자 명단 현황
        list_container = tk.Frame(self, bg=COLOR_PANEL, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        list_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        list_header = tk.Frame(list_container, bg=COLOR_PANEL)
        list_header.pack(fill=tk.X, pady=(0, 6))

        self.lbl_list_title = tk.Label(
            list_header,
            text="👥 현재 방 참가자 현황 (0명)",
            font=FONT_SUBTITLE,
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_PANEL
        )
        self.lbl_list_title.pack(side=tk.LEFT)

        columns = ("status", "nickname")
        self.tree = ttk.Treeview(list_container, columns=columns, show="headings", height=6)
        self.tree.heading("status", text="준비 상태")
        self.tree.heading("nickname", text="닉네임")

        self.tree.column("status", width=140, anchor="center")
        self.tree.column("nickname", width=340, anchor="w")

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_network_events(self):
        self.net.on_player_list_changed = self._on_players_updated_threadsafe
        self.net.on_room_info_changed = self._on_info_updated_threadsafe
        self.net.on_host_command_received = self._on_command_threadsafe

    def _toggle_ready(self):
        new_ready = not self.net.is_ready
        self.net.set_ready(new_ready)

        play_sound_async("ready" if new_ready else "cancel")
        self._update_ready_button_ui(new_ready)

    def _update_ready_button_ui(self, is_ready: bool):
        if is_ready:
            self.btn_ready.config(
                text="✅ 준비 완료되었습니다! (클릭하여 취소)",
                bg=COLOR_READY,
                fg=COLOR_TEXT_DARK,
                activebackground="#B9F6CA"
            )
            self.lbl_status_desc.config(
                text="방장에게 준비 완료 상태가 전송되었습니다. 게임 시작을 기다리세요!",
                fg=COLOR_READY
            )
        else:
            self.btn_ready.config(
                text="⚡ 준비 완료 (READY)",
                bg=COLOR_WAIT,
                fg=COLOR_TEXT_DARK,
                activebackground="#FFE082"
            )
            self.lbl_status_desc.config(
                text="아직 준비되지 않았습니다. 게임 준비가 끝나면 버튼을 눌러주세요!",
                fg=COLOR_TEXT_MUTED
            )

    def _confirm_leave(self):
        if messagebox.askyesno("퇴장 확인", "방에서 나가시겠습니까?"):
            self.net.leave_room()
            self.on_leave_room()

    # -------------------------------------------------------------
    # 스레드 안전 UI 갱신 콜백
    # -------------------------------------------------------------
    def _on_players_updated_threadsafe(self, players: dict):
        self.after(0, lambda: self._refresh_player_list(players))

    def _on_info_updated_threadsafe(self, info: dict):
        self.after(0, lambda: self._refresh_room_info(info))

    def _on_command_threadsafe(self, cmd: dict):
        action = cmd.get("action")
        if action == "kicked":
            self.after(0, self._handle_kicked)
        elif action == "ping_ready":
            self.after(0, self._handle_ping)

    def _handle_kicked(self):
        messagebox.showwarning("퇴장 알림", "방장에 의해 방에서 퇴장 처리되었습니다.")
        self.on_leave_room()

    def _handle_ping(self):
        play_sound_async("ping")
        messagebox.showinfo("🔔 방장 알림", "방장님이 모든 참가자에게 [준비 완료]를 요청했습니다!")

    def _refresh_player_list(self, players: dict):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_players = len(players)
        ready_count = sum(1 for p in players.values() if p.get("is_ready", False))

        self.lbl_list_title.config(
            text=f"👥 현재 방 참가자 현황 (총 {total_players}명 중 {ready_count}명 준비 완료)"
        )

        for p in players.values():
            is_ready = p.get("is_ready", False)
            status_text = "🟢 READY (완료)" if is_ready else "⏳ 대기 중"
            nick = p.get("nickname", "참가자")
            if p.get("client_id") == self.net.client_id:
                nick += " (나)"

            self.tree.insert("", tk.END, values=(status_text, nick))

    def _refresh_room_info(self, info: dict):
        game = info.get("game_name", "대기 중")
        notice = info.get("notice", "")
        self.lbl_game_name.config(text=game)
        self.lbl_notice.config(text=f"📢 방장 공지: {notice}")
