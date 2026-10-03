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
import tempfile
from typing import Optional, Dict, Any, Callable

CURRENT_APP_VERSION = "1.0.3"


def cleanup_leftover_updater_files():
    """이전 버전에서 사용자 폴더에 남아있을 수 있는 _new.exe, updater.bat 등 임시 파일 자동 청소"""
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            exe_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

        for junk in ("StreamerPartyReady_new.exe", "updater.bat", "update.bat"):
            junk_path = os.path.join(exe_dir, junk)
            if os.path.exists(junk_path):
                try:
                    os.remove(junk_path)
                except Exception:
                    pass
    except Exception:
        pass


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
        """새 exe 파일을 임시 폴더에 안전하게 다운로드한 뒤 기존 파일을 교체하고 재실행"""
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

                # 사용자 폴더에 _new.exe나 updater.bat이 절대 노출되지 않도록 시스템 TEMP 폴더에 격리
                temp_dir = tempfile.mkdtemp(prefix="spr_update_")
                downloaded_exe = os.path.join(temp_dir, "StreamerPartyReady_download.exe")

                headers = {"User-Agent": "StreamerPartyReady-AutoUpdater"}
                req = urllib.request.Request(download_url, headers=headers)

                # 파일 다운로드 및 진행률 갱신
                with urllib.request.urlopen(req, timeout=40) as resp:
                    content_len_hdr = resp.headers.get("content-length")
                    total_size = int(content_len_hdr) if content_len_hdr and content_len_hdr.isdigit() else 0
                    downloaded = 0
                    chunk_size = 64 * 1024

                    with open(downloaded_exe, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size)

                # TEMP 폴더 내에 배치 스크립트 생성 (사용자 폴더에는 생성하지 않음)
                current_pid = os.getpid()
                updater_bat = os.path.join(temp_dir, "updater.bat")
                leftover_new = os.path.join(exe_dir, "StreamerPartyReady_new.exe")
                leftover_bat = os.path.join(exe_dir, "updater.bat")

                bat_script = f"""@echo off
chcp 65001 > nul
set _PYI_PARENT_PROCESS_LEVEL=
set _MEIPASS2=
set _PYI_SPLASH_IPC=
set PYTHONPATH=
set PYTHONHOME=

:: 1. 부모 프로세스 종료 대기 및 확실한 파일 락 해제 (ping 대기 - timeout 리디렉션 에러 방지)
taskkill /f /pid {current_pid} >nul 2>nul
ping 127.0.0.1 -n 2 > nul

:: 2. 사용자 폴더에 남아있을 수 있는 구버전 잔여 임시 파일 정리
del /f /q "{leftover_new}" >nul 2>nul
del /f /q "{leftover_bat}" >nul 2>nul

:: 3. 기존 실행 파일 삭제 및 최신 파일로 교체 (최대 15회 재시도)
set RETRY=0
:loop_del
del /f /q "{target_exe}" >nul 2>nul
if exist "{target_exe}" (
    set /a RETRY+=1
    if %RETRY% leq 15 (
        ping 127.0.0.1 -n 2 > nul
        goto loop_del
    )
)

move /y "{downloaded_exe}" "{target_exe}" >nul 2>nul
if not exist "{target_exe}" (
    copy /y "{downloaded_exe}" "{target_exe}" >nul 2>nul
)

:: 4. 업데이트된 최신 프로그램 정상 시작
cd /d "{exe_dir}"
start "" "{target_exe}"

:: 5. 시스템 TEMP 임시 폴더 자체 정리 (3초 후 완전 삭제)
ping 127.0.0.1 -n 3 > nul
(goto) 2>nul & rd /s /q "{temp_dir}"
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

                # 콘솔 창 깜빡임 없이(CREATE_NO_WINDOW) 백그라운드에서 조용히 실행 후 현재 프로세스 정상 종료
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(["cmd.exe", "/c", updater_bat], shell=False, env=clean_env, creationflags=CREATE_NO_WINDOW)
                time.sleep(0.5)
                os._exit(0)

            except Exception as e:
                if on_complete:
                    on_complete(False, f"업데이트 설치 실패: {e}")

        threading.Thread(target=_worker, daemon=True).start()
