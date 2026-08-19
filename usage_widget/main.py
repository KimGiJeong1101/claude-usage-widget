"""Entry point: tray icon that stays resident, background refresh thread,
and popups for details / settings on click.

Threading: the hidden Tk root's mainloop() runs on the main thread; pystray
runs on its own background thread. pystray's Win32 backend invokes menu
callbacks from a low-level native message-loop context, not a normal Python
thread -- calling tkinter directly from there (e.g. wait_window()) crashed
the process, so callbacks only ever marshal work onto the GUI thread via
root.after(0, ...).
"""

import threading
import time

import pystray

from usage_widget.auth import has_saved_session, login_and_save_session
from usage_widget.config import Config
from usage_widget.fetcher import SessionExpiredError, fetch_usage
from usage_widget.popup import get_gui_root, show_settings_popup, show_usage_popup
from usage_widget.tray_icon import build_icon_image

_TOOLTIP = "Claude 사용량"

_latest_usage = None
_last_error = None


def _update_icon(icon: pystray.Icon) -> None:
    """Reflects the current usage percent and, if the last fetch failed,
    a failure note in the tray tooltip -- otherwise a dead background
    thread (e.g. after a declined re-login) would leave the icon frozen
    on stale data with no visible sign anything is wrong."""
    icon.icon = build_icon_image(_latest_usage.session_percent)
    icon.title = _TOOLTIP if _last_error is None else f"{_TOOLTIP} (갱신 실패, 재시도 중)"


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


def _refresh_loop(icon: pystray.Icon) -> None:
    global _latest_usage, _last_error
    while True:
        config = Config.load()
        try:
            _latest_usage = _fetch_with_relogin()
            _last_error = None
        except Exception as exc:
            _last_error = str(exc)
        _update_icon(icon)
        time.sleep(config.refresh_seconds)


def _manual_refresh(icon: pystray.Icon, on_done) -> None:
    """Fetches fresh usage data on a background thread (fetch_usage() can
    take a couple of seconds -- launches a headless browser) and marshals
    the result back onto the GUI thread, so clicking refresh never freezes
    the popup. on_done receives None (instead of hanging forever) if the
    fetch fails."""

    def worker():
        global _latest_usage, _last_error
        try:
            _latest_usage = _fetch_with_relogin()
            _last_error = None
            _update_icon(icon)
            get_gui_root().after(0, lambda: on_done(_latest_usage))
        except Exception as exc:
            _last_error = str(exc)
            _update_icon(icon)
            get_gui_root().after(0, lambda: on_done(None))

    threading.Thread(target=worker, daemon=True).start()


def _on_open(icon: pystray.Icon, item) -> None:
    get_gui_root().after(
        0, lambda: show_usage_popup(_latest_usage, on_refresh=lambda on_done: _manual_refresh(icon, on_done))
    )


def _on_settings(icon: pystray.Icon, item) -> None:
    get_gui_root().after(0, show_settings_popup)


def _on_quit(icon: pystray.Icon, item) -> None:
    icon.stop()
    root = get_gui_root()
    root.after(0, root.destroy)


def _run_tray(icon: pystray.Icon) -> None:
    threading.Thread(target=_refresh_loop, args=(icon,), daemon=True).start()
    icon.run()


def run() -> None:
    global _latest_usage
    if not has_saved_session():
        login_and_save_session()

    _latest_usage = _fetch_with_relogin()

    menu = pystray.Menu(
        pystray.MenuItem("열기", _on_open, default=True),
        pystray.MenuItem("설정", _on_settings),
        pystray.MenuItem("종료", _on_quit),
    )
    icon = pystray.Icon(
        "claude-usage-widget",
        build_icon_image(_latest_usage.session_percent),
        _TOOLTIP,
        menu,
    )

    # Create the hidden GUI root up front, on this (main) thread, before the
    # pystray thread starts -- otherwise a pystray callback could end up
    # creating it lazily on the wrong thread.
    root = get_gui_root()
    threading.Thread(target=_run_tray, args=(icon,), daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    run()
