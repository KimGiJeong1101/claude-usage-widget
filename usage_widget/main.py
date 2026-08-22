"""Entry point: tray icon that stays resident, background refresh thread,
and popups for details / settings on click.

Threading: pywebview needs a window to exist before webview.start() (run on
the main thread) will run its native event loop; pystray runs on its own
background thread. Popup-opening callbacks are still wrapped in a small
daemon thread rather than calling webui.show_*_popup directly from
pystray's callback -- pystray's Win32 backend invokes menu callbacks from a
low-level native message-loop context, and tkinter's blocking calls used to
crash the process when called from there (see git history); pywebview's
window creation hasn't shown that problem in testing, but the wrapping
costs nothing and removes any doubt.
"""

import threading
import time
import webbrowser
from typing import Optional

import pystray

from usage_widget import __version__
from usage_widget.auth import has_saved_session, login_and_save_session
from usage_widget.config import Config
from usage_widget.fetcher import SessionExpiredError, UsageData, fetch_account_email, fetch_usage
from usage_widget.paths import session_state_path
from usage_widget.self_update import apply_update, can_self_update, cleanup_stale_update_files
from usage_widget.tray_icon import build_icon_image
from usage_widget.update_check import RELEASES_URL, check_for_update
from usage_widget.webui import (
    init_gui,
    push_usage_update,
    run_gui_loop,
    shutdown_gui,
    show_account_popup,
    show_settings_popup,
    show_usage_popup,
)

_TOOLTIP = "Claude 사용량"
_UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60

_update_available_version: Optional[str] = None
_update_notified_versions: set = set()

_latest_usage = None
_last_error = None
_account_email = None
_logged_out = False  # True after an explicit "로그아웃": stays paused (no
# fetch attempts, no auto re-login) until the user acts via "계정 변경".


def _update_icon(icon: pystray.Icon) -> None:
    """Reflects the current usage percent and, if the last fetch failed or
    the user is logged out, a note in the tray tooltip -- otherwise a dead
    background thread (e.g. after a declined re-login) would leave the icon
    frozen on stale data with no visible sign anything is wrong."""
    if _logged_out:
        icon.icon = build_icon_image(0, 0, style=Config.load().tray_icon_style, logged_out=True)
        icon.title = f"{_TOOLTIP} (로그아웃됨)"
        return
    style = Config.load().tray_icon_style
    icon.icon = build_icon_image(_latest_usage.session_percent, _latest_usage.week_percent, style=style)
    label = f"{_TOOLTIP} ({_latest_usage.session_percent}%)"
    icon.title = label if _last_error is None else f"{label} (갱신 실패, 재시도 중)"


def _fetch_with_relogin():
    """Raises whatever fetch_usage() raises if re-login doesn't fix it --
    callers are responsible for catching this so a single bad fetch (a
    network blip, a declined re-login, claude.ai changing its API shape)
    can't silently kill the refresh loop or leave the popup stuck."""
    try:
        return fetch_usage()
    except SessionExpiredError:
        login_and_save_session()
        if not has_saved_session():
            raise  # the user closed the login window without logging in
        return fetch_usage()


def _refresh_account_email() -> None:
    """Best-effort -- the email is only shown in the account dialog, so a
    failure here shouldn't affect usage fetching at all."""
    global _account_email
    try:
        _account_email = fetch_account_email()
    except Exception:
        _account_email = None


def _refresh_loop(icon: pystray.Icon) -> None:
    global _latest_usage, _last_error
    while True:
        config = Config.load()
        if not _logged_out:
            try:
                _latest_usage = _fetch_with_relogin()
                _last_error = None
                push_usage_update(_latest_usage)
            except Exception as exc:
                _last_error = str(exc)
            _update_icon(icon)
        time.sleep(config.refresh_seconds)


def _manual_refresh(icon: pystray.Icon) -> Optional[UsageData]:
    """Fetches fresh usage data and returns it (None on failure). Safe to
    block here: pywebview already dispatches js_api calls like this one off
    its own UI thread, so the popup doesn't freeze while this runs."""
    global _latest_usage, _last_error
    try:
        _latest_usage = _fetch_with_relogin()
        _last_error = None
        _update_icon(icon)
        push_usage_update(_latest_usage)
        return _latest_usage
    except Exception as exc:
        _last_error = str(exc)
        _update_icon(icon)
        return None


def _do_logout(icon: pystray.Icon) -> None:
    global _logged_out, _account_email
    session_state_path().unlink(missing_ok=True)
    _logged_out = True
    _account_email = None
    _update_icon(icon)


def _do_switch_account(icon: pystray.Icon) -> None:
    """Clears the saved session and immediately opens a fresh login window.
    Runs on a worker thread, same as manual refresh --
    login_and_save_session() blocks until the user finishes (or closes) the
    browser window, which would otherwise freeze pystray's message loop for
    however long that takes."""

    def worker():
        global _latest_usage, _last_error, _logged_out
        session_state_path().unlink(missing_ok=True)
        try:
            login_and_save_session()
            _latest_usage = _fetch_with_relogin()
            _last_error = None
            _logged_out = False
            _refresh_account_email()
        except Exception as exc:
            _last_error = str(exc)
            _logged_out = True  # didn't complete -- stay paused, don't nag
        _update_icon(icon)

    threading.Thread(target=worker, daemon=True).start()


def _show_account_dialog(icon: pystray.Icon) -> None:
    show_account_popup(
        _account_email,
        _logged_out,
        on_switch=lambda: _do_switch_account(icon),
        on_logout=lambda: _do_logout(icon),
    )


def _on_open(icon: pystray.Icon, item) -> None:
    if _logged_out:
        threading.Thread(target=lambda: _show_account_dialog(icon), daemon=True).start()
        return
    threading.Thread(
        target=lambda: show_usage_popup(_latest_usage, on_refresh=lambda: _manual_refresh(icon)),
        daemon=True,
    ).start()


def _on_settings(icon: pystray.Icon, item) -> None:
    threading.Thread(
        target=lambda: show_settings_popup(on_saved=lambda: _update_icon(icon)), daemon=True
    ).start()


def _on_switch_account(icon: pystray.Icon, item) -> None:
    threading.Thread(target=lambda: _show_account_dialog(icon), daemon=True).start()


def _on_quit(icon: pystray.Icon, item) -> None:
    icon.stop()
    shutdown_gui()


_update_in_progress = False
_update_checking = False


def _update_menu_text(item) -> str:
    """Always visible (not just when an update happens to be known about)
    so there's a permanent, predictable place to see the running version
    and check on demand, instead of a menu item that appears/disappears
    depending on background-check timing."""
    if _update_in_progress:
        return "업데이트 적용 중..."
    if _update_checking:
        return "업데이트 확인 중..."
    if _update_available_version is not None:
        label = "지금 업데이트" if can_self_update() else "다운로드"
        return f"새 버전 있음 (v{_update_available_version}) — {label}"
    return f"현재 버전: v{__version__}"


def _update_menu_enabled(item) -> bool:
    return not _update_in_progress and not _update_checking


def _start_update(icon: pystray.Icon) -> None:
    """Downloads/applies the update (Windows) or just opens the releases
    page (everywhere else). Assumes _update_available_version is already
    set -- callers check for/report "already latest" themselves before
    reaching this."""
    if not can_self_update():
        webbrowser.open(RELEASES_URL)
        return

    global _update_in_progress
    _update_in_progress = True
    icon.update_menu()

    def worker():
        global _update_in_progress
        try:
            icon.notify("새 버전을 받는 중입니다...", "업데이트")
            apply_update()
        except Exception as exc:
            _update_in_progress = False
            icon.update_menu()
            icon.notify(f"업데이트에 실패했습니다: {exc}", "잠시 후 다시 시도해주세요")
            return
        # apply_update() only staged the download and spawned a detached
        # helper that's waiting on *this* process's PID to exit -- this
        # process still has to actually shut itself down, same as the
        # "종료" menu item, or the helper waits forever.
        icon.stop()
        shutdown_gui()

    threading.Thread(target=worker, daemon=True).start()


def _on_update_click(icon: pystray.Icon, item) -> None:
    global _update_available_version, _update_checking

    if _update_in_progress or _update_checking:
        return

    if _update_available_version is not None:
        # Already known (from the periodic loop or an earlier manual
        # check) -- go straight to applying/downloading it.
        _start_update(icon)
        return

    # Nothing known yet: this click itself *is* the "check now" action,
    # rather than waiting for the next periodic check.
    _update_checking = True
    icon.update_menu()

    def worker():
        global _update_available_version, _update_checking
        version = check_for_update()
        _update_checking = False
        if version is None:
            icon.update_menu()
            icon.notify(f"현재 최신 버전입니다 (v{__version__})", "업데이트 확인")
            return
        _update_available_version = version
        _update_notified_versions.add(version)  # skip the periodic loop's own popup for this version
        icon.update_menu()
        _start_update(icon)

    threading.Thread(target=worker, daemon=True).start()


def _update_check_loop(icon: pystray.Icon) -> None:
    """Runs independently of the usage refresh loop -- checking for a new
    release has nothing to do with how often the user wants usage numbers
    refreshed, so it isn't tied to config.refresh_seconds."""
    global _update_available_version
    while True:
        version = check_for_update()
        _update_available_version = version
        if version is not None and version not in _update_notified_versions:
            _update_notified_versions.add(version)
            action = "우클릭 메뉴에서 바로 적용할 수 있어요" if can_self_update() else "우클릭 메뉴에서 다운로드하세요"
            try:
                icon.notify(f"Claude Usage Widget v{version} — {action}", "새 버전이 나왔어요")
            except Exception:
                pass
        icon.update_menu()
        time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)


def _run_tray(icon: pystray.Icon) -> None:
    threading.Thread(target=_refresh_loop, args=(icon,), daemon=True).start()
    threading.Thread(target=_update_check_loop, args=(icon,), daemon=True).start()
    icon.run()


def run() -> None:
    global _latest_usage
    cleanup_stale_update_files()
    if not has_saved_session():
        login_and_save_session()

    _latest_usage = _fetch_with_relogin()
    _refresh_account_email()

    menu = pystray.Menu(
        pystray.MenuItem("열기", _on_open, default=True),
        pystray.MenuItem("설정", _on_settings),
        pystray.MenuItem("계정", _on_switch_account),
        pystray.MenuItem(_update_menu_text, _on_update_click, enabled=_update_menu_enabled),
        pystray.MenuItem("종료", _on_quit),
    )
    icon = pystray.Icon(
        "claude-usage-widget",
        build_icon_image(
            _latest_usage.session_percent, _latest_usage.week_percent, style=Config.load().tray_icon_style
        ),
        _TOOLTIP,
        menu,
    )

    # Create the hidden root window up front, on this (main) thread, before
    # the pystray thread starts -- pywebview requires at least one window to
    # exist before run_gui_loop() (webview.start()) will run.
    init_gui()
    threading.Thread(target=_run_tray, args=(icon,), daemon=True).start()
    run_gui_loop()


if __name__ == "__main__":
    run()
