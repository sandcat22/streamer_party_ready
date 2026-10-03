"""
로컬 설정 저장 및 불러오기 모듈 (Config Manager)
- PC에 방이름/게임명, 닉네임, 방 코드 등 입력값을 영구 저장
- AppData 폴더에 config.json 형식으로 안전하게 보관
"""

import os
import json
from typing import Dict, Any

APP_NAME = "StreamerPartyReady"
CONFIG_FILE_NAME = "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "host_game_name": "오버워치 내전",
    "host_nickname": "용봉탕",
    "host_room_code": "",
    "host_max_players": "0",
    "host_notice": "참가자분들은 준비 완료 버튼을 눌러주세요!",
    "participant_nickname": "",
    "participant_room_code": "",
    "github_repo": "sandcat22/streamer_party_ready",
}


def get_config_dir() -> str:
    """AppData 또는 사용자 홈 디렉토리 내 설정 폴더 경로 반환"""
    app_data = os.getenv("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")
    target_dir = os.path.join(app_data, APP_NAME)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def get_config_path() -> str:
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)


def load_config() -> Dict[str, Any]:
    """저장된 설정 파일 읽기 (없으면 기본값 반환)"""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return dict(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 기본값 누락 방지 병합
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
    except Exception as e:
        print(f"설정 파일 읽기 실패: {e}")
        return dict(DEFAULT_CONFIG)


def save_config(config_data: Dict[str, Any]):
    """설정 데이터를 로컬 파일에 저장"""
    config_path = get_config_path()
    try:
        current = load_config()
        current.update(config_data)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"설정 파일 저장 실패: {e}")


def update_config_field(key: str, value: Any):
    """단일 설정값 갱신"""
    save_config({key: value})
