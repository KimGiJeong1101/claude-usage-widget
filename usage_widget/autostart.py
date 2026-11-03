"""Windows 전용: "PC 켤 때 자동 실행" 기능을 켜고 끄는 파일.

Windows 레지스트리(설정값을 저장해두는 시스템 DB 같은 것)의 "현재 사용자
전용" Run 키에 등록/해제하는 방식이라, 관리자 권한이 필요 없다(만약
HKEY_LOCAL_MACHINE이라는 "컴퓨터 전체 공용" 위치를 썼다면 관리자 권한이
필요했을 것). macOS용(launchd 에이전트나 로그인 항목 등록)은 아직
구현하지 않았다 -- 자세한 내용은 private notes 저장소의 기획 메모 참고.
"""

import sys
from pathlib import Path

APP_NAME = "ClaudeUsageWidget"
_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import winreg


def _command() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller로 빌드된 exe라면, sys.executable이 곧 이 프로그램
        # 자기 자신의 경로다.
        return f'"{sys.executable}"'
    # 소스 코드로 직접 실행 중인 경우 (개발용일 뿐, 정식으로 지원하는
    # 자동실행 방식은 아님). 이때 sys.executable은 콘솔 창이 같이 뜨는
    # python.exe라서, 그대로 쓰면 PC 켤 때마다 까만 콘솔 창이 잠깐 반짝
    # 나타난다. pythonw.exe(같은 설치본인데 콘솔 창이 없는 버전)를 대신
    # 쓰면 이 문제가 없다.
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else python_exe
    return f'"{exe}" -m usage_widget.main'


def is_enabled() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    if not _IS_WINDOWS:
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())


def refresh_registered_path() -> None:
    """자동 시작이 켜져 있으면, 등록된 실행 경로를 지금 실행 중인 exe의
    경로로 다시 맞춰준다. 포터블 버전은 사용자가 exe를 다른 폴더로 옮길 수
    있는데, 그러면 레지스트리에는 옛날 경로가 남아서 설정 화면의 체크박스는
    켜져 있는데 실제로는 PC를 켜도 아무것도 실행되지 않았다.

    배포용 exe로 실행 중일 때만 한다 -- 소스로 실행 중일 때 이걸 하면,
    개발자 PC에서 exe용으로 켜둔 자동 시작이 "python -m ..." 명령으로
    슬쩍 바뀌어버린다. "되면 좋고 안 돼도 그만"인 작업이라 실패는 무시한다."""
    if not _IS_WINDOWS or not getattr(sys, "frozen", False):
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            current, _ = winreg.QueryValueEx(key, APP_NAME)
    except OSError:
        return  # 자동 시작이 꺼져 있음
    if current != _command():
        try:
            enable()
        except OSError:
            pass


def disable() -> None:
    if not _IS_WINDOWS:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
