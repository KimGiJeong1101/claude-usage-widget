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

_latest_usage = None


def _refresh_loop(icon: pystray.Icon) -> None:
    global _latest_usage
    while True:
        config = Config.load()
        try:
            _latest_usage = fetch_usage()
        except SessionExpiredError:
            login_and_save_session()
            _latest_usage = fetch_usage()
        icon.icon = build_icon_image(_latest_usage.session_percent)
        time.sleep(config.refresh_seconds)


def _on_open(icon: pystray.Icon, item) -> None:
    get_gui_root().after(0, lambda: show_usage_popup(_latest_usage))


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

    try:
        _latest_usage = fetch_usage()
    except SessionExpiredError:
        login_and_save_session()
        _latest_usage = fetch_usage()

    menu = pystray.Menu(
        pystray.MenuItem("열기", _on_open, default=True),
        pystray.MenuItem("설정", _on_settings),
        pystray.MenuItem("종료", _on_quit),
    )
    icon = pystray.Icon(
        "claude-usage-widget",
        build_icon_image(_latest_usage.session_percent),
        "Claude 사용량",
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
