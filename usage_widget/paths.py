"""설정 파일과 로그인 세션 파일을 어디에 저장할지 정하는 곳.

Windows/macOS/Linux마다 "사용자 데이터를 저장하기에 적절한 폴더" 위치가
다른데, 이 파일 하나만 보면 OS가 뭐든 상관없이 항상 같은 방식으로 경로를
구할 수 있다."""

from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "ClaudeUsageWidget"
APP_AUTHOR = "ClaudeUsageWidget"


def data_dir() -> Path:
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def session_state_path() -> Path:
    """로그인할 때 Playwright(브라우저 자동화 도구)가 저장해준 로그인 세션
    정보(쿠키 등)가 담긴 파일의 경로."""
    return data_dir() / "session_state.json"
