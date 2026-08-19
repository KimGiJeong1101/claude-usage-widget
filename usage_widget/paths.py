"""OS-independent locations for config and saved login session data."""

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
    """Playwright storage_state (cookies) captured at login time."""
    return data_dir() / "session_state.json"
