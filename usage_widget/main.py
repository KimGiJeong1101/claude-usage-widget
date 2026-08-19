"""Entry point: tray icon that stays resident, background refresh thread,
and popups for details / settings on click."""

import threading
import time

import pystray

from usage_widget.auth import has_saved_session, login_and_save_session
from usage_widget.config import Config
from usage_widget.fetcher import SessionExpiredError, fetch_usage
from usage_widget.popup import show_settings_popup, show_usage_popup
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
        icon.icon = build_icon_image(max(_latest_usage.session_percent, _latest_usage.week_percent))
        time.sleep(config.refresh_minutes * 60)


def _on_open(icon: pystray.Icon, item) -> None:
    show_usage_popup(_latest_usage)


def _on_settings(icon: pystray.Icon, item) -> None:
    show_settings_popup()


def _on_quit(icon: pystray.Icon, item) -> None:
    icon.stop()


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

    threading.Thread(target=_refresh_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    run()
