"""Windows-only: registers/unregisters this app to launch automatically
when the user logs in, via the per-user Registry Run key (no admin rights
needed, unlike HKEY_LOCAL_MACHINE). macOS support (a launchd agent or Login
Items entry) isn't implemented yet -- see claude-usage-widget-plan.md.
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
        # a PyInstaller build -- sys.executable *is* the app itself
        return f'"{sys.executable}"'
    # Running from source (dev use only; not the supported autostart path).
    # sys.executable here is the console python.exe, which would otherwise
    # flash a cmd window open on every login -- pythonw.exe (same install,
    # no console subsystem) is the windowed equivalent.
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


def disable() -> None:
    if not _IS_WINDOWS:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
