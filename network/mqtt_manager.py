"""
실시간 스트리머 파티 네트워크 매니저 (MQTT 기반 무설정 P2P/중계 통신)
- 포트포워딩, 외부 IP 노출 없이 방 코드 하나로 실시간 통신
- 방장 공지, 참가자 목록, 실시간 준비 상태(READY) 동기화
"""

import json
import time
import uuid
import threading
from typing import Dict, Any, Callable, Optional
import paho.mqtt.client as mqtt

# 공용 무료 고성능 MQTT 브로커
DEFAULT_BROKER = "broker.hivemq.com"
FALLBACK_BROKER = "broker.emqx.io"
BROKER_PORT = 1883


class PartyNetworkManager:
    def __init__(self):
        self.client_id = f"sp_{uuid.uuid4().hex[:8]}"
        self.room_code: Optional[str] = None
        self.is_host = False
        self.my_nickname = ""
        self.is_ready = False
        self.connected = False

        # 방 정보 및 참가자 상태 저장소
        self.room_info: Dict[str, Any] = {
            "game_name": "대기 중",
            "host_name": "방장",
            "max_players": 10,
            "notice": ""
        }
        self.players: Dict[str, Dict[str, Any]] = {}

        # UI 콜백 이벤트 리스너
        self.on_room_info_changed: Optional[Callable[[dict], None]] = None
        self.on_player_list_changed: Optional[Callable[[dict], None]] = None
        self.on_ready_event: Optional[Callable[[str, str, bool], None]] = None
        self.on_host_command_received: Optional[Callable[[dict], None]] = None
        self.on_connection_changed: Optional[Callable[[bool, str], None]] = None

        # MQTT 클라이언트 초기화
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start_connection(self):
        """백그라운드에서 브로커 연결 시작"""
        def _connect_thread():
            try:
                self.client.connect(DEFAULT_BROKER, BROKER_PORT, keepalive=30)
                self.client.loop_start()
            except Exception as e:
                print(f"기본 브로커 연결 실패, 대체 브로커 시도: {e}")
                try:
                    self.client.connect(FALLBACK_BROKER, BROKER_PORT, keepalive=30)
                    self.client.loop_start()
                except Exception as e2:
                    if self.on_connection_changed:
                        self.on_connection_changed(False, f"연결 실패: {e2}")

        threading.Thread(target=_connect_thread, daemon=True).start()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self.connected = True
        if self.on_connection_changed:
            self.on_connection_changed(True, "서버 연결됨")

        # 방에 참여 중인 상태라면 재구독
        if self.room_code:
            self._subscribe_room_topics()
            if self.is_host:
                self.publish_room_info()
            else:
                self.send_my_status(is_online=True)

    def _on_disconnect(self, client, userdata, disconnect_flags, rc=None, properties=None):
        self.connected = False
        if self.on_connection_changed:
            self.on_connection_changed(False, "서버 연결 끊김 (재접속 시도 중)")

    def _topic_prefix(self) -> str:
        if not self.room_code:
            return "streamer_ready_v1/NONE"
        return f"streamer_ready_v1/{self.room_code.upper()}"

    def _subscribe_room_topics(self):
        if not self.room_code or not self.connected:
            return
        prefix = self._topic_prefix()
        # 와일드카드(#)로 방의 모든 메시지(info, player/+, control) 일괄 구독
        self.client.subscribe(f"{prefix}/#", qos=1)

    # -------------------------------------------------------------
    # 방장(Host) 전용 기능
    # -------------------------------------------------------------
    def create_room(self, room_code: str, game_name: str, host_name: str = "방장", max_players: int = 10):
        """방 생성 및 초기화"""
        self.room_code = room_code.upper()
        self.is_host = True
        self.my_nickname = host_name
        self.players.clear()

        self.room_info = {
            "game_name": game_name,
            "host_name": host_name,
            "max_players": max_players,
            "notice": "참가자분들은 준비 완료 버튼을 눌러주세요!"
        }

        self._subscribe_room_topics()
        self.publish_room_info()

    def publish_room_info(self):
        """방 정보를 모든 참가자에게 브로드캐스트 (Retain=True로 신규 입장자 즉시 수신)"""
        if not self.room_code or not self.connected:
            return
        topic = f"{self._topic_prefix()}/info"
        payload = json.dumps(self.room_info, ensure_ascii=False)
        self.client.publish(topic, payload, qos=1, retain=True)

    def update_game_name(self, new_game_name: str):
        self.room_info["game_name"] = new_game_name
        self.publish_room_info()

    def update_notice(self, new_notice: str):
        self.room_info["notice"] = new_notice
        self.publish_room_info()

    def kick_player(self, target_client_id: str):
        """특정 참가자 강퇴"""
        if not self.is_host or not self.room_code:
            return
        cmd = {"action": "kick", "target_id": target_client_id}
        self.client.publish(f"{self._topic_prefix()}/control", json.dumps(cmd), qos=1)
        if target_client_id in self.players:
            del self.players[target_client_id]
            if self.on_player_list_changed:
                self.on_player_list_changed(self.players)

    def ping_all_ready(self):
        """모든 참가자에게 레디 요청 알림 전송"""
        if not self.room_code:
            return
        cmd = {"action": "ping_ready", "time": time.time()}
        self.client.publish(f"{self._topic_prefix()}/control", json.dumps(cmd), qos=1)

    def reset_all_ready(self):
        """모든 참가자의 준비 상태 일괄 초기화"""
        if not self.room_code:
            return
        cmd = {"action": "reset_ready"}
        self.client.publish(f"{self._topic_prefix()}/control", json.dumps(cmd), qos=1)
        for p in self.players.values():
            p["is_ready"] = False
        if self.on_player_list_changed:
            self.on_player_list_changed(self.players)

    # -------------------------------------------------------------
    # 참가자(Participant) 전용 기능
    # -------------------------------------------------------------
    def join_room(self, room_code: str, nickname: str):
        """방 입장"""
        self.room_code = room_code.upper()
        self.is_host = False
        self.my_nickname = nickname
        self.is_ready = False
        self.players.clear()

        self._subscribe_room_topics()
        self.send_my_status(is_online=True)

    def set_ready(self, is_ready: bool):
        """준비 완료 / 준비 취소 상태 변경"""
        self.is_ready = is_ready
        self.send_my_status(is_online=True)

    def send_my_status(self, is_online: bool = True):
        """내 상태 브로드캐스트"""
        if not self.room_code or not self.connected:
            return
        topic = f"{self._topic_prefix()}/player/{self.client_id}"
        payload = {
            "client_id": self.client_id,
            "nickname": self.my_nickname,
            "is_ready": self.is_ready,
            "is_online": is_online,
            "updated_at": time.time()
        }
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=True)

    def leave_room(self):
        """방 퇴장"""
        if self.room_code:
            if not self.is_host:
                self.send_my_status(is_online=False)
            prefix = self._topic_prefix()
            self.client.unsubscribe(f"{prefix}/#")
            self.room_code = None
            self.players.clear()

    # -------------------------------------------------------------
    # 메시지 수신 및 파싱
    # -------------------------------------------------------------
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception:
            return

        prefix = self._topic_prefix()

        # 1. 방 정보 수신
        if topic == f"{prefix}/info":
            self.room_info.update(payload)
            if self.on_room_info_changed:
                self.on_room_info_changed(self.room_info)

        # 2. 플레이어 상태 수신
        elif topic.startswith(f"{prefix}/player/"):
            p_id = payload.get("client_id")
            if not p_id:
                return

            is_online = payload.get("is_online", True)
            if not is_online:
                # 퇴장한 경우 목록에서 제거
                if p_id in self.players:
                    del self.players[p_id]
                    if self.on_player_list_changed:
                        self.on_player_list_changed(self.players)
            else:
                old_ready = self.players.get(p_id, {}).get("is_ready", False)
                new_ready = payload.get("is_ready", False)

                self.players[p_id] = payload
                if self.on_player_list_changed:
                    self.on_player_list_changed(self.players)

                # 레디 상태가 변경되었을 때 이벤트 발생 (효과음용)
                if old_ready != new_ready and self.on_ready_event:
                    self.on_ready_event(p_id, payload.get("nickname", "참가자"), new_ready)

        # 3. 제어 명령 수신 (강퇴, 전체 핑 등)
        elif topic == f"{prefix}/control":
            action = payload.get("action")
            if action == "kick" and payload.get("target_id") == self.client_id:
                # 본인이 강퇴당한 경우
                self.leave_room()
                if self.on_host_command_received:
                    self.on_host_command_received({"action": "kicked"})
            elif action == "reset_ready":
                if not self.is_host:
                    self.is_ready = False
                    self.send_my_status(is_online=True)
            elif action == "ping_ready":
                if self.on_host_command_received:
                    self.on_host_command_received({"action": "ping_ready"})
