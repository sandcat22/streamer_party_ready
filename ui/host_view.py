"""
방장 (스트리머) 대시보드 뷰 (Host Room Dashboard)
- 실시간 참가자 명단 및 준비 완료(READY) 현황판
- 방 코드 복사, OBS 방송용 Always-on-Top 지원
- 팀 나누기, 무작위 추첨, 전체 레디 핑, 공지 전송 등 스트리머 특화 기능
- 변경된 게임명 및 공지사항 로컬 PC 영구 저장
"""

import random
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable, Optional

from network.mqtt_manager import PartyNetworkManager
from network.config_manager import load_config, update_config_field
from ui.theme import (
    COLOR_BG, COLOR_PANEL, COLOR_PANEL_LIGHT, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_TEXT_DARK,
    COLOR_CYAN, COLOR_READY, COLOR_WAIT, COLOR_DANGER,
    COLOR_PURPLE, COLOR_BLUE, COLOR_ORANGE,
    FONT_TITLE_LARGE, FONT_TITLE, FONT_SUBTITLE, FONT_BODY,
    FONT_BOLD, FONT_MONO, play_sound_async
)


class HostView(tk.Frame):
    def __init__(
        self,
        parent,
        net_manager: PartyNetworkManager,
        on_leave_room: Callable[[], None],
        toggle_always_on_top: Callable[[bool], None],
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.net = net_manager
        self.on_leave_room = on_leave_room
        self.toggle_always_on_top = toggle_always_on_top

        self.always_on_top_var = tk.BooleanVar(value=True)
        self.sound_enabled_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._bind_network_events()

    def _build_ui(self):
        # 1. 상단 메인 헤더 (방 코드 및 주요 지표)
        header = tk.Frame(self, bg=COLOR_PANEL, padx=16, pady=12, highlightbackground=COLOR_BORDER, highlightthickness=1)
        header.pack(fill=tk.X, padx=12, pady=(10, 8))

        # 윗줄: 방 코드 & 컨트롤
        h_row1 = tk.Frame(header, bg=COLOR_PANEL)
        h_row1.pack(fill=tk.X)

        tk.Label(h_row1, text="👑 방장 대시보드", font=FONT_TITLE, fg=COLOR_PURPLE, bg=COLOR_PANEL).pack(side=tk.LEFT)

        # 방 코드 뱃지 및 복사 버튼
        code_box = tk.Frame(h_row1, bg=COLOR_PANEL_LIGHT, padx=8, pady=3)
        code_box.pack(side=tk.LEFT, padx=16)

        tk.Label(code_box, text="방 코드:", font=FONT_BODY, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_LIGHT).pack(side=tk.LEFT)
        self.lbl_room_code = tk.Label(code_box, text=self.net.room_code or "", font=FONT_MONO, fg=COLOR_CYAN, bg=COLOR_PANEL_LIGHT)
        self.lbl_room_code.pack(side=tk.LEFT, padx=(4, 8))

        btn_copy = tk.Button(
            code_box,
            text="📋 코드 복사",
            font=FONT_BODY,
            bg=COLOR_CYAN,
            fg=COLOR_TEXT_DARK,
            activebackground="#80D8FF",
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self.copy_room_code
        )
        btn_copy.pack(side=tk.LEFT)

        # 우측 제어 (항상 위, 소리, 나가기)
        btn_leave = tk.Button(
            h_row1,
            text="방 종료 / 나가기",
            font=FONT_BODY,
            bg="#D32F2F",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            command=self._confirm_leave
        )
        btn_leave.pack(side=tk.RIGHT, padx=(8, 0))

        chk_top = tk.Checkbutton(
            h_row1,
            text="항상 위 (OBS/게임용)",
            variable=self.always_on_top_var,
            command=lambda: self.toggle_always_on_top(self.always_on_top_var.get()),
            font=FONT_BODY,
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_PANEL,
            selectcolor=COLOR_PANEL_LIGHT,
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_CYAN
        )
        chk_top.pack(side=tk.RIGHT, padx=6)

        chk_sound = tk.Checkbutton(
            h_row1,
            text="🔔 효과음",
            variable=self.sound_enabled_var,
            font=FONT_BODY,
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_PANEL,
            selectcolor=COLOR_PANEL_LIGHT,
            activebackground=COLOR_PANEL
        )
        chk_sound.pack(side=tk.RIGHT, padx=4)

        # 아랫줄: 게임명 및 현재 인원 현황
        h_row2 = tk.Frame(header, bg=COLOR_PANEL)
        h_row2.pack(fill=tk.X, pady=(10, 0))

        # 게임명 표시 및 변경 입력창
        tk.Label(h_row2, text="방이름 / 게임명 / 컨텐츠명:", font=FONT_BOLD, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL).pack(side=tk.LEFT)
        self.entry_game_name = tk.Entry(
            h_row2,
            font=FONT_BOLD,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            width=24
        )
        saved_game = self.net.room_info.get("game_name") or load_config().get("host_game_name", "")
        self.entry_game_name.insert(0, saved_game)
        self.entry_game_name.pack(side=tk.LEFT, padx=6, ipady=3)

        btn_update_game = tk.Button(
            h_row2,
            text="수정",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            padx=6,
            pady=1,
            command=self._update_game_name
        )
        btn_update_game.pack(side=tk.LEFT)

        # 인원수 & 레디 카운터
        self.lbl_player_count = tk.Label(
            h_row2,
            text="참가 인원: 0명 | 준비 완료: 0명",
            font=FONT_TITLE,
            fg=COLOR_READY,
            bg=COLOR_PANEL
        )
        self.lbl_player_count.pack(side=tk.RIGHT)

        # 2. 방장 공지사항 입력바
        notice_bar = tk.Frame(self, bg=COLOR_PANEL, padx=14, pady=6, highlightbackground=COLOR_BORDER, highlightthickness=1)
        notice_bar.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Label(notice_bar, text="📢 참가자 공지:", font=FONT_BOLD, fg=COLOR_WAIT, bg=COLOR_PANEL).pack(side=tk.LEFT)
        self.entry_notice = tk.Entry(
            notice_bar,
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT
        )
        saved_notice = self.net.room_info.get("notice") or load_config().get("host_notice", "참가자분들은 준비 완료 버튼을 눌러주세요!")
        self.entry_notice.insert(0, saved_notice)
        self.entry_notice.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, ipady=3)

        btn_notice = tk.Button(
            notice_bar,
            text="공지 전송",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_CYAN,
            relief=tk.FLAT,
            padx=10,
            command=self._send_notice
        )
        btn_notice.pack(side=tk.RIGHT)

        # 3. 중앙: 실시간 참가자 목록 테이블
        list_container = tk.Frame(self, bg=COLOR_PANEL, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        list_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        list_header = tk.Frame(list_container, bg=COLOR_PANEL)
        list_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(list_header, text="👥 실시간 참가자 목록", font=FONT_SUBTITLE, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(side=tk.LEFT)
        tk.Label(list_header, text="* 참가자가 [준비 완료]를 누르면 초록색으로 즉시 바뀝니다", font=FONT_BODY, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL).pack(side=tk.RIGHT)

        # Treeview 스타일 및 생성
        columns = ("status", "nickname", "client_id")
        self.tree = ttk.Treeview(list_container, columns=columns, show="headings", height=8, selectmode="browse")

        self.tree.heading("status", text="상태 (READY)")
        self.tree.heading("nickname", text="닉네임")
        self.tree.heading("client_id", text="고유 ID")

        self.tree.column("status", width=140, anchor="center")
        self.tree.column("nickname", width=260, anchor="w")
        self.tree.column("client_id", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 4. 하단: 방장 전용 도구 툴바 (추첨, 팀 나누기, 핑, 초기화, 강퇴)
        tools_frame = tk.Frame(self, bg=COLOR_PANEL, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        tools_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        # 왼쪽: 액션 버튼들
        btn_ping = tk.Button(
            tools_frame,
            text="🔔 전체 레디 요청",
            font=FONT_BOLD,
            bg=COLOR_CYAN,
            fg=COLOR_TEXT_DARK,
            activebackground="#80D8FF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._ping_all
        )
        btn_ping.pack(side=tk.LEFT, padx=3)

        btn_reset = tk.Button(
            tools_frame,
            text="🔄 레디 초기화",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._reset_ready
        )
        btn_reset.pack(side=tk.LEFT, padx=3)

        btn_teams = tk.Button(
            tools_frame,
            text="⚔️ 팀 나누기 (청팀/홍팀)",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_BLUE,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._divide_teams
        )
        btn_teams.pack(side=tk.LEFT, padx=3)

        btn_raffle = tk.Button(
            tools_frame,
            text="🎲 랜덤 1명 추첨",
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_ORANGE,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._pick_random
        )
        btn_raffle.pack(side=tk.LEFT, padx=3)

        # 오른쪽: 선택 강퇴 버튼
        btn_kick = tk.Button(
            tools_frame,
            text="🚫 선택 강퇴",
            font=FONT_BODY,
            bg="#3E1A1A",
            fg=COLOR_DANGER,
            activebackground="#B71C1C",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._kick_selected
        )
        btn_kick.pack(side=tk.RIGHT, padx=3)

    def _bind_network_events(self):
        self.net.on_player_list_changed = self._on_players_updated_threadsafe
        self.net.on_ready_event = self._on_ready_event_threadsafe
        self.net.on_room_info_changed = self._on_info_updated_threadsafe

    def copy_room_code(self):
        code = self.net.room_code or ""
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("복사 완료", f"방 코드 [{code}]가 클립보드에 복사되었습니다!\n시청자 채팅창이나 디스코드에 붙여넣어 주세요.")

    def _update_game_name(self):
        new_name = self.entry_game_name.get().strip()
        if new_name:
            self.net.update_game_name(new_name)
            update_config_field("host_game_name", new_name)
            messagebox.showinfo("변경 완료", f"게임명이 [{new_name}](으)로 갱신되었습니다.")

    def _send_notice(self):
        notice = self.entry_notice.get().strip()
        self.net.update_notice(notice)
        update_config_field("host_notice", notice)
        messagebox.showinfo("공지 전송", "참가자들에게 공지가 실시간 전송되었습니다.")

    def _ping_all(self):
        self.net.ping_all_ready()
        if self.sound_enabled_var.get():
            play_sound_async("ping")
        messagebox.showinfo("알림 전송", "모든 참가자 화면에 '준비해 주세요!' 알림을 보냈습니다.")

    def _reset_ready(self):
        self.net.reset_all_ready()
        messagebox.showinfo("초기화", "모든 참가자의 준비(READY) 상태가 초기화되었습니다.")

    def _kick_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("선택 필요", "강퇴할 참가자를 목록에서 클릭해 선택해 주세요.")
            return

        item = self.tree.item(selected[0])
        client_id = item['values'][2]
        nick = item['values'][1]

        if messagebox.askyesno("강퇴 확인", f"정말로 '{nick}' 님을 방에서 내보내시겠습니까?"):
            self.net.kick_player(str(client_id))

    def _divide_teams(self):
        players = list(self.net.players.values())
        if len(players) < 2:
            messagebox.showinfo("안내", "팀을 나누려면 최소 2명 이상의 참가자가 필요합니다.")
            return

        shuffled = [p['nickname'] for p in players]
        random.shuffle(shuffled)
        mid = len(shuffled) // 2

        team_a = shuffled[:mid]
        team_b = shuffled[mid:]

        msg = f"⚔️ [팀 나누기 결과]\n\n"
        msg += f"🔵 청팀 (A팀):\n" + "\n".join(f"  • {name}" for name in team_a) + "\n\n"
        msg += f"🔴 홍팀 (B팀):\n" + "\n".join(f"  • {name}" for name in team_b)

        messagebox.showinfo("팀 나누기 완료", msg)

    def _pick_random(self):
        players = list(self.net.players.values())
        if not players:
            messagebox.showinfo("안내", "추첨할 참가자가 없습니다.")
            return

        winner = random.choice(players)
        if self.sound_enabled_var.get():
            play_sound_async("ready")
        messagebox.showinfo("당첨자 발표!", f"🎉 당첨자: [{winner['nickname']}] 님 축하합니다!")

    def _confirm_leave(self):
        if messagebox.askyesno("방 종료", "방을 닫고 로비로 돌아가시겠습니까?"):
            self.net.leave_room()
            self.on_leave_room()

    # -------------------------------------------------------------
    # 스레드 안전 UI 갱신 콜백
    # -------------------------------------------------------------
    def _on_players_updated_threadsafe(self, players: dict):
        self.after(0, lambda: self._refresh_player_list(players))

    def _on_ready_event_threadsafe(self, player_id: str, nickname: str, is_ready: bool):
        # 방장은 참가자의 레디 소리를 듣지 않음 (시각적 목록만 갱신)
        pass

    def _on_info_updated_threadsafe(self, info: dict):
        self.after(0, lambda: self._refresh_room_info(info))

    def _refresh_player_list(self, players: dict):
        # 기존 목록 비우기
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_players = len(players)
        ready_count = 0

        # 레디 완료자 우선 정렬
        sorted_players = sorted(players.values(), key=lambda p: (not p.get("is_ready", False), p.get("nickname", "")))

        for p in sorted_players:
            is_ready = p.get("is_ready", False)
            if is_ready:
                ready_count += 1
                status_text = "🟢 READY (완료)"
            else:
                status_text = "⏳ 대기 중"

            self.tree.insert(
                "",
                tk.END,
                values=(status_text, p.get("nickname", "참가자"), p.get("client_id", ""))
            )

        max_allowed = self.net.room_info.get("max_players", 10)
        self.lbl_player_count.config(
            text=f"참가 인원: {total_players} / {max_allowed}명 | 준비 완료: {ready_count} / {total_players}명"
        )

    def _refresh_room_info(self, info: dict):
        current_entry = self.entry_game_name.get()
        new_game = info.get("game_name", "")
        if new_game and current_entry != new_game:
            self.entry_game_name.delete(0, tk.END)
            self.entry_game_name.insert(0, new_game)
