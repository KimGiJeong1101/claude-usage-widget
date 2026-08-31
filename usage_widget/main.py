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

from usage_widget import __version__, i18n, single_instance
from usage_widget.auth import has_saved_session, login_and_save_session
from usage_widget.config import Config
from usage_widget.fetcher import SessionExpiredError, UsageData, fetch_account_email, fetch_usage
from usage_widget.paths import session_state_path
from usage_widget.self_update import apply_update, can_self_update, cleanup_stale_update_files
from usage_widget.tray_icon import build_icon_image
from usage_widget.update_check import RELEASES_URL, check_for_update
from usage_widget.webui import (
    close_splash,
    init_gui,
    push_usage_update,
    run_gui_loop,
    shutdown_gui,
    show_account_popup,
    show_settings_popup,
    show_splash,
    show_usage_popup,
)

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
    config = Config.load()
    lang = config.language
    base = i18n.t("tray.tooltip_base", lang)
    if _logged_out:
        icon.icon = build_icon_image(0, 0, style=config.tray_icon_style, logged_out=True)
        icon.title = f"{base} ({i18n.t('tray.tooltip_logged_out', lang)})"
        return
    icon.icon = build_icon_image(_latest_usage.session_percent, _latest_usage.week_percent, style=config.tray_icon_style)
    label = f"{base} ({_latest_usage.session_percent}%)"
    icon.title = label if _last_error is None else f"{label} ({i18n.t('tray.tooltip_error', lang)})"


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
    def on_saved():
        _update_icon(icon)
        # _update_icon only repaints the icon image/tooltip -- the menu
        # labels (열기/설정/계정/종료, all language-dependent callables now)
        # otherwise wouldn't be re-evaluated until something else happened
        # to call update_menu() next (e.g. the 6-hour update-check loop),
        # which made a language change look like it "hadn't taken" yet.
        icon.update_menu()

    threading.Thread(target=lambda: show_settings_popup(on_saved=on_saved), daemon=True).start()


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
    lang = Config.load().language
    if _update_in_progress:
        return i18n.t("update.applying", lang)
    if _update_checking:
        return i18n.t("update.checking", lang)
    if _update_available_version is not None:
        label = i18n.t("update.action_now", lang) if can_self_update() else i18n.t("update.action_download", lang)
        return i18n.t("update.new_version", lang, version=_update_available_version, label=label)
    return i18n.t("update.current_version", lang, version=__version__)


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
        lang = Config.load().language
        try:
            icon.notify(i18n.t("notify.update_downloading", lang), i18n.t("notify.update_title", lang))
            apply_update()
        except Exception as exc:
            _update_in_progress = False
            icon.update_menu()
            icon.notify(
                i18n.t("notify.update_failed_msg", lang, error=exc), i18n.t("notify.update_failed_title", lang)
            )
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
        lang = Config.load().language
        version = check_for_update()
        _update_checking = False
        if version is None:
            icon.update_menu()
            icon.notify(i18n.t("notify.up_to_date_msg", lang, version=__version__), i18n.t("notify.check_title", lang))
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
            lang = Config.load().language
            action = (
                i18n.t("notify.new_version_action_self", lang)
                if can_self_update()
                else i18n.t("notify.new_version_action_download", lang)
            )
            try:
                icon.notify(
                    i18n.t("notify.new_version_available_msg", lang, version=version, action=action),
                    i18n.t("notify.new_version_available_title", lang),
                )
            except Exception:
                pass
        icon.update_menu()
        time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)


def _announce_started(icon: pystray.Icon) -> None:
    """pystray's setup= callback: fires once the icon has actually been
    added to the tray, not just constructed -- calling icon.notify() any
    earlier isn't guaranteed to work since the OS-level tray entry it
    attaches the balloon/toast to wouldn't exist yet. A brief toast instead
    of forcing a pinned popup open on every launch (see
    claude-usage-widget-plan.md's discussion of this trade-off) -- someone
    who launched without watching the taskbar still gets a clear "yes, it's
    running" signal, without a window they now have to deal with."""
    icon.visible = True
    try:
        lang = Config.load().language
        icon.notify(i18n.t("notify.started_msg", lang), i18n.t("tray.tooltip_base", lang))
    except Exception:
        pass


def _run_tray(icon: pystray.Icon) -> None:
    threading.Thread(target=_refresh_loop, args=(icon,), daemon=True).start()
    threading.Thread(target=_update_check_loop, args=(icon,), daemon=True).start()
    icon.run(setup=_announce_started)


def _build_menu() -> pystray.Menu:
    """Labels are callables (re-evaluated by pystray each time the menu is
    displayed) rather than plain strings, so a language change in Settings
    shows up the next time someone right-clicks the tray icon without
    needing an explicit refresh."""
    return pystray.Menu(
        pystray.MenuItem(lambda item: i18n.t("tray.open", Config.load().language), _on_open, default=True),
        pystray.MenuItem(lambda item: i18n.t("tray.settings", Config.load().language), _on_settings),
        pystray.MenuItem(lambda item: i18n.t("tray.account", Config.load().language), _on_switch_account),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_update_menu_text, _on_update_click, enabled=_update_menu_enabled),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: i18n.t("tray.quit", Config.load().language), _on_quit),
    )


def run() -> None:
    """Startup used to block the main thread on the login check and first
    usage fetch *before* pywebview's event loop (run_gui_loop) even
    started -- so there was no window of any kind on screen during that
    gap, and no way to tell the app hadn't just silently failed to launch.
    Now the splash goes up first, the slow part moves to a background
    thread, and run_gui_loop() starts immediately so that splash actually
    renders (webview.create_window()/destroy() are documented safe to call
    off the main thread -- see webui.py's module docstring)."""
    global _latest_usage
    if not single_instance.acquire():
        # Another instance already holds the lock -- launching one exe
        # twice (a habitual double-click, autostart racing a manual
        # launch) used to spawn a fully independent second process, each
        # with its own tray icon and its own PyInstaller onefile temp
        # extraction directory contending with the other's. Exiting
        # quietly here is the whole fix: the already-running instance is
        # unaffected and still reachable from its own tray icon.
        return
    cleanup_stale_update_files()

    init_gui()
    lang = Config.load().language
    splash = show_splash(lang)

    def bootstrap():
        global _latest_usage
        try:
            if not has_saved_session():
                # A full external Chrome window is about to open for
                # login -- no reason for the tiny splash to linger under it.
                close_splash(splash)
                login_and_save_session()
            _latest_usage = _fetch_with_relogin()
            _refresh_account_email()
        except Exception:
            close_splash(splash)
            shutdown_gui()
            raise
        close_splash(splash)

        icon = pystray.Icon(
            "claude-usage-widget",
            build_icon_image(
                _latest_usage.session_percent, _latest_usage.week_percent, style=Config.load().tray_icon_style
            ),
            i18n.t("tray.tooltip_base", Config.load().language),
            _build_menu(),
        )
        _run_tray(icon)

    threading.Thread(target=bootstrap, daemon=True).start()
    run_gui_loop()


if __name__ == "__main__":
    run()
