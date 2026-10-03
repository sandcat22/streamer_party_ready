"""
초기 시작 화면 (Lobby / Mode Selection Screen)
- 방장 모드(방 만들기) 및 참가자 모드(방 입장) 선택
- 로비 방 코드 복사 및 새로고침 지원
- 로컬 PC 입력값 영구 저장 및 복원 연동
"""

import random
import string
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from network.config_manager import load_config, save_config, update_config_field
from network.updater import CURRENT_APP_VERSION
from ui.theme import (
    COLOR_BG, COLOR_PANEL, COLOR_PANEL_LIGHT, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_TEXT_DARK,
    COLOR_CYAN, COLOR_READY, COLOR_WAIT, COLOR_PURPLE,
    FONT_TITLE_LARGE, FONT_TITLE, FONT_SUBTITLE,
    FONT_BODY, FONT_BOLD, FONT_MONO
)


def generate_random_room_code(length: int = 4) -> str:
    """기본 4자리 영숫자 방 코드 생성 (예: A7X9)"""
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return "".join(random.choices(chars, k=length))


class WelcomeScreen(tk.Frame):
    def __init__(
        self,
        parent,
        on_create_room: Callable[[str, str, str, int], None],
        on_join_room: Callable[[str, str], None],
        on_check_update: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.on_create_room = on_create_room
        self.on_join_room = on_join_room
        self.on_check_update = on_check_update

        self.config = load_config()
        self._build_ui()

    def _build_ui(self):
        # 상단 타이틀
        header = tk.Frame(self, bg=COLOR_BG, pady=18)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🎮 스트리머 파티 매칭 & 레디 체커",
            font=FONT_TITLE_LARGE,
            fg=COLOR_CYAN,
            bg=COLOR_BG
        ).pack()

        tk.Label(
            header,
            text="방장이 게임을 열고, 참가자가 실시간으로 준비 완료(READY)를 누르는 시스템",
            font=FONT_BODY,
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG
        ).pack(pady=(4, 0))

        # 메인 카드 컨테이너 (좌: 방장 / 우: 참가자)
        cards_frame = tk.Frame(self, bg=COLOR_BG, padx=20)
        cards_frame.pack(fill=tk.BOTH, expand=True)

        # ---------------------------------------------------------
        # 1. 방장(스트리머) 카드
        # ---------------------------------------------------------
        host_card = tk.LabelFrame(
            cards_frame,
            text=" 👑 방장 (스트리머) 모드 ",
            font=FONT_TITLE,
            fg=COLOR_PURPLE,
            bg=COLOR_PANEL,
            padx=16,
            pady=16,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        host_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

        # 게임명 입력
        tk.Label(host_card, text="방이름 / 게임명 / 컨텐츠명", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(anchor="w")
        self.entry_game_name = tk.Entry(
            host_card,
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_game = self.config.get("host_game_name") or "오버워치 내전"
        self.entry_game_name.insert(0, saved_game)
        self.entry_game_name.pack(fill=tk.X, pady=(4, 12), ipady=6)

        # 방장 닉네임 입력
        tk.Label(host_card, text="방장 닉네임", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(anchor="w")
        self.entry_host_name = tk.Entry(
            host_card,
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_host = self.config.get("host_nickname") or "용봉탕"
        self.entry_host_name.insert(0, saved_host)
        self.entry_host_name.pack(fill=tk.X, pady=(4, 12), ipady=6)

        # 방 코드 & 최대 인원 가로 배치
        row_host = tk.Frame(host_card, bg=COLOR_PANEL)
        row_host.pack(fill=tk.X, pady=(0, 16))

        # 방 코드 영역
        col_code = tk.Frame(row_host, bg=COLOR_PANEL)
        col_code.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        code_title_row = tk.Frame(col_code, bg=COLOR_PANEL)
        code_title_row.pack(fill=tk.X)
        tk.Label(code_title_row, text="방 코드", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(side=tk.LEFT)

        # 방 코드 복사 버튼 (로비에서도 즉시 복사 가능)
        self.btn_lobby_copy = tk.Button(
            code_title_row,
            text="📋 복사",
            font=("Malgun Gothic", 8),
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_CYAN,
            relief=tk.FLAT,
            bd=0,
            padx=4,
            cursor="hand2",
            command=self._copy_host_code
        )
        self.btn_lobby_copy.pack(side=tk.RIGHT, padx=(2, 0))

        btn_regen = tk.Button(
            code_title_row,
            text="🎲 새 코드",
            font=("Malgun Gothic", 8),
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MUTED,
            relief=tk.FLAT,
            bd=0,
            padx=4,
            cursor="hand2",
            command=self._regenerate_host_code
        )
        btn_regen.pack(side=tk.RIGHT)

        self.entry_room_code = tk.Entry(
            col_code,
            font=FONT_MONO,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_CYAN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_room = self.config.get("host_room_code") or generate_random_room_code()
        self.entry_room_code.insert(0, saved_room)
        self.entry_room_code.pack(fill=tk.X, pady=(4, 0), ipady=6)

        # 인원수 제한
        col_max = tk.Frame(row_host, bg=COLOR_PANEL)
        col_max.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))

        max_title_row = tk.Frame(col_max, bg=COLOR_PANEL)
        max_title_row.pack(fill=tk.X)
        tk.Label(max_title_row, text="인원수 제한", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(side=tk.LEFT)
        tk.Label(max_title_row, text="(0 = 무제한)", font=FONT_BODY, fg=COLOR_WAIT, bg=COLOR_PANEL).pack(side=tk.RIGHT)

        self.entry_max_players = tk.Entry(
            col_max,
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_max = str(self.config.get("host_max_players", "0")).strip()
        saved_val = saved_max if saved_max.isdigit() else "0"
        self.entry_max_players.insert(0, saved_val)
        self.entry_max_players.pack(fill=tk.X, pady=(4, 0), ipady=6)

        # 방 생성 버튼
        btn_create = tk.Button(
            host_card,
            text="👑 방 만들기 & 대기 시작",
            font=FONT_BOLD,
            bg=COLOR_PURPLE,
            fg="#FFFFFF",
            activebackground="#D1C4E9",
            activeforeground=COLOR_TEXT_DARK,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._handle_create_room
        )
        btn_create.pack(fill=tk.X, pady=(10, 0), ipady=8)

        # ---------------------------------------------------------
        # 2. 참가자(시청자) 카드
        # ---------------------------------------------------------
        join_card = tk.LabelFrame(
            cards_frame,
            text=" 🙋 참가자 (시청자/지인) 모드 ",
            font=FONT_TITLE,
            fg=COLOR_READY,
            bg=COLOR_PANEL,
            padx=16,
            pady=16,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        join_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)

        # 닉네임 입력
        tk.Label(join_card, text="내 닉네임", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(anchor="w")
        self.entry_join_nick = tk.Entry(
            join_card,
            font=FONT_BODY,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_nick = self.config.get("participant_nickname") or f"참가자{random.randint(10, 99)}"
        self.entry_join_nick.insert(0, saved_nick)
        self.entry_join_nick.pack(fill=tk.X, pady=(4, 16), ipady=6)

        # 방 코드 입력
        tk.Label(join_card, text="입장할 방 코드 (방장에게 받은 코드)", font=FONT_BOLD, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL).pack(anchor="w")
        self.entry_join_code = tk.Entry(
            join_card,
            font=FONT_MONO,
            bg=COLOR_PANEL_LIGHT,
            fg=COLOR_READY,
            insertbackground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0
        )
        saved_join_code = self.config.get("participant_room_code") or ""
        self.entry_join_code.insert(0, saved_join_code)
        self.entry_join_code.pack(fill=tk.X, pady=(4, 24), ipady=6)

        tk.Label(
            join_card,
            text="💡 방장이 화면에 띄운 '방 코드'를 입력하면\n어디서든 즉시 접속되어 준비 완료를 누를 수 있습니다.\n* 입력한 값은 PC에 자동 저장됩니다.",
            font=FONT_BODY,
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL,
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        # 방 입장 버튼
        btn_join = tk.Button(
            join_card,
            text="⚡ 방 입장하기",
            font=FONT_BOLD,
            bg=COLOR_READY,
            fg=COLOR_TEXT_DARK,
            activebackground="#B9F6CA",
            activeforeground=COLOR_TEXT_DARK,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._handle_join_room
        )
        btn_join.pack(fill=tk.X, pady=(10, 0), ipady=8)



    def _copy_host_code(self):
        code = self.entry_room_code.get().strip()
        if code:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.btn_lobby_copy.config(text="✅ 복사됨!", fg=COLOR_READY)
            self.after(1500, lambda: self.btn_lobby_copy.config(text="📋 복사", fg=COLOR_CYAN))

    def _regenerate_host_code(self):
        new_code = generate_random_room_code()
        self.entry_room_code.delete(0, tk.END)
        self.entry_room_code.insert(0, new_code)

    def _handle_create_room(self):
        game_name = self.entry_game_name.get().strip()
        host_name = self.entry_host_name.get().strip() or "용봉탕"
        room_code = self.entry_room_code.get().strip()

        if not game_name:
            messagebox.showwarning("입력 필요", "방이름 / 게임명 / 컨텐츠명을 입력해 주세요.")
            return

        if not room_code:
            messagebox.showwarning("입력 필요", "방 코드를 입력해 주세요.")
            return

        max_input = self.entry_max_players.get().strip()
        try:
            max_players = int(max_input) if max_input else 0
        except ValueError:
            messagebox.showwarning("입력 확인", "인원수 제한에는 숫자만 입력해 주세요.\n(0을 입력하면 무제한으로 설정됩니다)")
            return

        if max_players < 0:
            max_players = 0

        # 입력값을 로컬 PC에 영구 저장
        save_config({
            "host_game_name": game_name,
            "host_nickname": host_name,
            "host_room_code": room_code,
            "host_max_players": str(max_players),
        })

        self.on_create_room(room_code, game_name, host_name, max_players)

    def _handle_join_room(self):
        nick = self.entry_join_nick.get().strip()
        code = self.entry_join_code.get().strip()

        if not nick:
            messagebox.showwarning("입력 필요", "닉네임을 입력해 주세요.")
            return

        if not code:
            messagebox.showwarning("입력 필요", "방 코드를 입력해 주세요.")
            return

        # 입력값을 로컬 PC에 영구 저장
        save_config({
            "participant_nickname": nick,
            "participant_room_code": code,
        })

        self.on_join_room(code, nick)
