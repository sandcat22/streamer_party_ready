"""
GitHub 기반 자동 업데이트 모듈 (Auto Updater)
- GitHub Releases API 및 version.json을 통한 최신 버전 감지
- 새 버전 감지 시 우측 하단에 업데이트 알림 버튼 노출
- 원클릭 자동 다운로드 및 무중단 재실행(스왑 배치 스크립트) 지원
- PyInstaller 보안 검증(Parent Process Validation) 충돌 방지 환경변수 정제
"""

import os
import sys
import json
import time
import urllib.request
import subprocess
import threading
from typing import Optional, Dict, Any, Callable

CURRENT_APP_VERSION = "1.0.1"


def parse_version(v_str: str) -> tuple:
    """'v1.0.2' 또는 '1.0.2' 형태의 버전을 숫자 튜플 (1, 0, 2)로 파싱"""
    clean = v_str.strip().lstrip("vV")
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


class AutoUpdater:
    def __init__(self, repo_name: str = "sandcat22/streamer_party_ready"):
        self.repo_name = repo_name
        self.current_version = CURRENT_APP_VERSION
        self.update_info: Optional[Dict[str, Any]] = None

    def check_for_update_async(self, on_result: Callable[[Optional[Dict[str, Any]]], None]):
        """백그라운드 스레드에서 깃허브 최신 릴리즈 확인"""
        def _worker():
            info = self.check_for_update()
            self.update_info = info
            if on_result:
                on_result(info)

        threading.Thread(target=_worker, daemon=True).start()

    def check_for_update(self) -> Optional[Dict[str, Any]]:
        """
        GitHub Releases API 및 Raw version.json을 순차적으로 확인
        """
        headers = {
            "User-Agent": "StreamerPartyReady-AutoUpdater",
            "Accept": "application/vnd.github.v3+json"
        }

        # 1. GitHub Releases API 확인
        api_url = f"https://api.github.com/repos/{self.repo_name}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag = data.get("tag_name", "")
                    if tag and parse_version(tag) > parse_version(self.current_version):
                        exe_url = None
                        for asset in data.get("assets", []):
                            if asset.get("name", "").lower().endswith(".exe"):
                                exe_url = asset.get("browser_download_url")
                                break

                        if not exe_url and data.get("assets"):
                            exe_url = data["assets"][0].get("browser_download_url")

                        if exe_url:
                            return {
                                "has_update": True,
                                "latest_version": tag,
                                "current_version": self.current_version,
                                "download_url": exe_url,
                                "release_notes": data.get("body") or "새로운 버전이 업데이트되었습니다.",
                            }
        except Exception:
            pass

        # 2. Raw version.json 확인 (API 제한 방지 백업)
        raw_url = f"https://raw.githubusercontent.com/{self.repo_name}/main/version.json"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "StreamerPartyReady-AutoUpdater"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    ver = data.get("version", "")
                    dl_url = data.get("download_url", "")
                    if ver and parse_version(ver) > parse_version(self.current_version) and dl_url:
                        return {
                            "has_update": True,
                            "latest_version": ver,
                            "current_version": self.current_version,
                            "download_url": dl_url,
                            "release_notes": data.get("notes") or "새 버전이 릴리즈되었습니다.",
                        }
        except Exception:
            pass

        return None

    def download_and_install_update(
        self,
        download_url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ):
        """새 exe 파일을 다운로드한 뒤 배치 스크립트로 교체 및 재실행"""
        def _worker():
            try:
                # 현재 실행 파일의 실제 경로 확인
                if getattr(sys, 'frozen', False):
                    target_exe = os.path.abspath(sys.executable)
                    exe_dir = os.path.dirname(target_exe)
                else:
                    # 개발(스크립트) 모드 시 dist 폴더의 실행 파일 지정
                    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    exe_dir = os.path.join(current_dir, "dist")
                    os.makedirs(exe_dir, exist_ok=True)
                    target_exe = os.path.join(exe_dir, "StreamerPartyReady.exe")

                new_exe = os.path.join(exe_dir, "StreamerPartyReady_new.exe")

                headers = {"User-Agent": "StreamerPartyReady-AutoUpdater"}
                req = urllib.request.Request(download_url, headers=headers)

                # 파일 다운로드 및 진행률 갱신
                with urllib.request.urlopen(req, timeout=40) as resp:
                    content_len_hdr = resp.headers.get("content-length")
                    total_size = int(content_len_hdr) if content_len_hdr and content_len_hdr.isdigit() else 0
                    downloaded = 0
                    chunk_size = 64 * 1024

                    with open(new_exe, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size)

                # 교체용 Windows 배치 파일 생성
                updater_bat = os.path.join(exe_dir, "updater.bat")
                bat_script = f"""@echo off
chcp 65001 > nul
set _PYI_PARENT_PROCESS_LEVEL=
set _MEIPASS2=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

timeout /t 1 /nobreak > nul

:retry
del "{target_exe}" >nul 2>nul
if exist "{target_exe}" (
    timeout /t 1 /nobreak > nul
    goto retry
)

move /y "{new_exe}" "{target_exe}" >nul 2>nul

start "" "{target_exe}"
timeout /t 3 /nobreak > nul

(goto) 2>nul & del "%~f0"
"""
                with open(updater_bat, "w", encoding="utf-8") as f:
                    f.write(bat_script)

                if on_complete:
                    on_complete(True, "다운로드 완료! 프로그램을 재시작합니다.")

                # PyInstaller 자식 프로세스 플래그를 정제하여 새로운 루트 프로세스로 실행되도록 보장
                clean_env = os.environ.copy()
                for key in list(clean_env.keys()):
                    if key.startswith("_PYI_") or key.startswith("_MEI") or key in ("PYTHONPATH", "PYTHONHOME"):
                        clean_env.pop(key, None)

                # 업데이터 배치 스크립트 실행 후 현재 프로세스 정상 종료
                subprocess.Popen(["cmd.exe", "/c", updater_bat], shell=True, env=clean_env)
                time.sleep(0.5)
                os._exit(0)

            except Exception as e:
                if on_complete:
                    on_complete(False, f"업데이트 설치 실패: {e}")

        threading.Thread(target=_worker, daemon=True).start()
