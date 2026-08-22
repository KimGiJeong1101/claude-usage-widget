"""Popup windows (usage / settings / account), rendered with pywebview
instead of tkinter -- the HTML/CSS/JS layer lives in
usage_widget/assets/web/*.html, this module is just the Python side of the
bridge (window creation, positioning, and the js_api objects each page
calls into).

Threading: pywebview requires at least one window to exist before
webview.start() is called, and that call blocks the thread it's called
from -- the same shape tkinter's hidden-root + mainloop() had. Unlike
tkinter, pywebview's create_window()/destroy() are documented as safe to
call from any thread (verified: a background thread creating a window
while webview.start() blocks the main thread does not crash), so pystray's
menu callbacks can open popups directly without marshaling through
root.after(...).
"""

import ctypes
import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import webview

from usage_widget import autostart
from usage_widget.config import Config
from usage_widget.fetcher import UsageData
from usage_widget.tray_icon import DEFAULT_STYLE, STYLE_LABELS

_ASSET_DIR = Path(__file__).parent / "assets" / "web"
_IS_WINDOWS = sys.platform == "win32"

_root_window: Optional[webview.Window] = None


def init_gui() -> None:
    """Creates the hidden window pywebview needs to exist before start()
    will run. Kept alive for the app's whole lifetime; destroying it (see
    shutdown_gui) is what makes the underlying native loop actually exit,
    since the windows toolkit backing pywebview quits once its last window
    closes."""
    global _root_window
    if _root_window is None:
        _root_window = webview.create_window("root", html="<html></html>", hidden=True)


def run_gui_loop() -> None:
    webview.start()


def shutdown_gui() -> None:
    if _root_window is not None:
        _root_window.destroy()


def _screen_size() -> Optional[tuple]:
    if not _IS_WINDOWS:
        return None
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _cursor_pos() -> Optional[tuple]:
    if not _IS_WINDOWS:
        return None

    class _Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = _Point()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _position_near_cursor(width: int, height: int) -> tuple:
    """Anchors a popup near the click position, opening away from whichever
    screen edge the cursor is closest to -- same reasoning as the old
    tkinter flyout: it has to land under the cursor immediately since it
    closes as soon as the pointer leaves it. Falls back to pywebview's own
    default placement (None, None) on platforms this hasn't been
    implemented for yet (non-Windows)."""
    cursor = _cursor_pos()
    screen = _screen_size()
    if cursor is None or screen is None:
        return None, None
    cursor_x, cursor_y = cursor
    screen_w, screen_h = screen
    gap = 24

    y = cursor_y - height + gap if cursor_y > screen_h / 2 else cursor_y - gap
    x = cursor_x - width + gap if cursor_x > screen_w / 2 else cursor_x - gap
    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    return int(x), int(y)


def _position_centered(width: int, height: int) -> tuple:
    screen = _screen_size()
    if screen is None:
        return None, None
    screen_w, screen_h = screen
    return int((screen_w - width) / 2), int((screen_h - height) / 2)


_destroy_lock = threading.Lock()


def _safe_destroy(window: webview.Window) -> None:
    """Destroys a window at most once -- close_fn can end up called twice in
    quick succession in some flows (e.g. a fast double-click), and this
    makes the second call a no-op rather than a race."""
    with _destroy_lock:
        if getattr(window, "_uw_destroyed", False):
            return
        window._uw_destroyed = True
    try:
        window.destroy()
    except Exception:
        pass


_PANEL_RADIUS = 20  # must match --radius in common.css


def _round_corners(window: webview.Window, radius: int = _PANEL_RADIUS) -> None:
    """Clips the native window to a rounded-rect region via the Win32 API.

    pywebview's transparent=True on Windows only makes the *page's own*
    background see-through (so CSS can show the Form's BackColor through
    it) -- it does not give the native window itself real per-pixel OS
    transparency. The corners outside our CSS border-radius were still
    part of the opaque rectangular window, which showed up as a visible
    square-cornered glitch behind the rounded panel. Clipping the actual
    window region removes those corners at the OS level instead of trying
    to make them transparent, which also means transparent=True can be
    dropped -- and pywebview only applies its native drop shadow when
    transparent is False, so this gets a real shadow as a side effect.

    The region has to be sized/read in *physical* pixels, not the logical
    width/height passed to create_window: pywebview scales a window's
    actual native Size by the monitor's DPI factor internally (a 360x400
    window is a real ~450x500 win32 window at 125% scaling), and using the
    unscaled logical size here left the clip region smaller than the real
    window -- an unclipped, still-square sliver on any display over 100%
    scaling. Reading window.native.Size (and scaling the radius the same
    way) at apply-time avoids having to duplicate pywebview's own scale
    calculation."""
    if not _IS_WINDOWS:
        return

    def apply():
        try:
            hwnd = window.native.Handle.ToInt32()
            scale = ctypes.windll.user32.GetDpiForWindow(hwnd) / 96.0
            w, h = window.native.Size.Width, window.native.Size.Height
            r = int(radius * scale)
            region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r * 2, r * 2)
            ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
        except Exception:
            pass

    window.events.shown += apply


# pywebview's WinForms backend sets Form.Size *before* switching
# FormBorderStyle to frameless (see winforms.py: Size is assigned near the
# top of the window-init method, FormBorderStyle = None happens later).
# WinForms preserves ClientSize across a border-style change, so the
# window ends up permanently smaller than requested once the (now absent)
# border/caption chrome is subtracted -- confirmed by testing at multiple
# requested sizes: reliably a fixed 16px narrower and 39px shorter (this
# matches typical Windows non-client metrics: ~8px left+right resize
# border, ~31px caption + top border). Only verified at 100% DPI scaling;
# since border metrics do generally scale with DPI, this fixed pixel
# fudge may be slightly off at other scale factors, but should still land
# much closer than not compensating at all. Padding the requested size by
# this amount up front makes the *actual* resulting window match the size
# the CSS layout was designed for, instead of quietly clipping content in
# a smaller-than-expected window.
_WINFORMS_SIZE_FUDGE = (16, 39)


def _new_window(title: str, page: str, js_api, width: int, height: int, position: tuple) -> webview.Window:
    """Popups are independent -- usage/settings/account can all be open at
    the same time, each closed on its own."""
    x, y = position
    create_width, create_height = width, height
    if _IS_WINDOWS:
        create_width += _WINFORMS_SIZE_FUDGE[0]
        create_height += _WINFORMS_SIZE_FUDGE[1]
    window = webview.create_window(
        title,
        url=str(_ASSET_DIR / page),
        js_api=js_api,
        width=create_width,
        height=create_height,
        x=x,
        y=y,
        frameless=True,
        easy_drag=True,
        # shadow=True (when transparent=False) makes pywebview call
        # DwmExtendFrameIntoClientArea + DwmSetWindowAttribute to get a
        # native drop shadow -- but that second call forces DWM to draw
        # its own default non-client window frame back on, which fights
        # with our SetWindowRgn corner clip and showed up as a stray
        # dashed border, worst around the top edge, especially once the
        # window gets focus. Not worth it -- staying without a native
        # shadow keeps the rounded clip clean.
        shadow=False,
        on_top=True,
        resizable=False,
        # Windows gets real rounded corners via _round_corners() below
        # instead (see its docstring for why transparent=True isn't
        # reliable there). Other platforms haven't been verified yet, so
        # this keeps their previous behavior.
        transparent=not _IS_WINDOWS,
    )
    _round_corners(window)
    return window


def _reset_status_text(reset_at: Optional[datetime]) -> str:
    """The API returns no reset time for a window with no usage yet (e.g.
    right after a 5-hour session resets, before the next message is
    sent)."""
    if reset_at is None:
        return "아직 사용 시작 전"
    delta = reset_at - datetime.now()
    total_minutes = max(int(delta.total_seconds()) // 60, 0)
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    if days:
        return f"리셋까지 {days}일 {hours}시간 후"
    return f"리셋까지 {hours}시간 {minutes}분 후"


def _box_closer(box: list) -> Callable[[], None]:
    """Returns a close callback that destroys whatever window later gets
    appended to box. A plain closure over a local list -- not an attribute
    on the js_api object -- so js_api.close() can reach the window without
    the js_api object itself ever holding a reference back to it (see
    _UsageApi's docstring for why that reference cycle matters)."""
    return lambda: box and _safe_destroy(box[0])


def _usage_to_dict(usage: UsageData) -> dict:
    return {
        "session": {
            "percent": usage.session_percent,
            "reset_text": _reset_status_text(usage.session_reset_at),
        },
        "week": {
            "percent": usage.week_percent,
            "reset_text": _reset_status_text(usage.week_reset_at),
        },
    }


class _UsageApi:
    """close_fn is a plain closure, not a reference to the Window itself --
    the js_api object must never hold an attribute pointing back to the
    webview.Window that holds it. That reference cycle (window -> js_api ->
    window) reliably wedged the WinForms/EdgeChromium backend during
    testing: some internal reflection walks the js_api's attributes and
    recurses forever once it loops back to the window
    (`window.native.AccessibilityObject.Bounds.Empty.Empty...`, a maximum
    recursion crash that hangs the GUI thread). A closure captured in a
    local variable isn't reachable via a plain attribute walk, so it
    doesn't create that cycle."""

    def __init__(
        self,
        usage: UsageData,
        refresh_fn: Optional[Callable[[], Optional[UsageData]]],
        close_fn: Callable[[], None],
    ):
        self._usage = usage
        self._refresh_fn = refresh_fn
        self._close_fn = close_fn

    def get_initial_data(self) -> dict:
        return _usage_to_dict(self._usage)

    def refresh(self) -> Optional[dict]:
        if self._refresh_fn is None:
            return None
        new_usage = self._refresh_fn()
        if new_usage is None:
            return None
        self._usage = new_usage
        return _usage_to_dict(new_usage)

    def close(self) -> None:
        self._close_fn()


_singleton_windows: dict = {}
_singleton_lock = threading.Lock()


def _focus_or_create(key: str, create: Callable[[], webview.Window]) -> None:
    """Ensures at most one popup of a given kind (`key`) is open at a time.
    Without this, clicking the tray icon (or a menu item) again while its
    popup was already open spawned a second overlapping copy instead of
    just bringing the existing one forward."""
    with _singleton_lock:
        existing = _singleton_windows.get(key)
        if existing is None:
            window = create()
            _singleton_windows[key] = window
    if existing is not None:
        try:
            existing.show()
        except Exception:
            pass
        return

    def _unregister():
        with _singleton_lock:
            if _singleton_windows.get(key) is window:
                del _singleton_windows[key]

    window.events.closed += _unregister


def push_usage_update(usage: UsageData) -> None:
    """Called by main.py after each successful background fetch so an
    already-open usage popup reflects it immediately, instead of only on
    the next manual refresh click."""
    with _singleton_lock:
        window = _singleton_windows.get("usage")
    if window is None:
        return
    data = json.dumps(_usage_to_dict(usage))
    try:
        window.evaluate_js(f"window.__pushUsage && window.__pushUsage({data})")
    except Exception:
        pass


def show_usage_popup(usage: UsageData, on_refresh: Optional[Callable[[], Optional[UsageData]]] = None) -> None:
    """on_refresh, if given, is called with no arguments when the refresh
    button is clicked and is expected to block until fresh data is ready,
    returning the new UsageData (or None on failure) -- safe to block here
    because pywebview already runs js_api calls off its own UI thread."""

    def create() -> webview.Window:
        box: list = []
        api = _UsageApi(usage, on_refresh, _box_closer(box))
        width, height = 360, 400
        window = _new_window("Claude 사용량", "usage.html", api, width, height, _position_near_cursor(width, height))
        box.append(window)
        return window

    _focus_or_create("usage", create)


class _SettingsApi:
    def __init__(self, config: Config, on_saved: Optional[Callable[[], None]], close_fn: Callable[[], None]):
        self._config = config
        self._on_saved = on_saved
        self._close_fn = close_fn

    def get_initial_data(self) -> dict:
        return {
            "refresh_seconds": self._config.refresh_seconds,
            "tray_icon_style": self._config.tray_icon_style,
            "style_labels": STYLE_LABELS,
            "show_autostart": _IS_WINDOWS,
            "autostart_enabled": autostart.is_enabled() if _IS_WINDOWS else False,
        }

    def save(self, payload: dict) -> None:
        try:
            self._config.refresh_seconds = max(5, int(payload.get("refresh_seconds", self._config.refresh_seconds)))
        except (TypeError, ValueError):
            pass
        self._config.tray_icon_style = payload.get("tray_icon_style") or DEFAULT_STYLE
        self._config.save()
        if _IS_WINDOWS:
            if payload.get("autostart"):
                autostart.enable()
            else:
                autostart.disable()
        if self._on_saved is not None:
            self._on_saved()

    def close(self) -> None:
        self._close_fn()


def show_settings_popup(on_saved: Optional[Callable[[], None]] = None) -> None:
    """on_saved, if given, is called right after a successful save -- lets
    main.py refresh the tray icon immediately instead of waiting for the
    next scheduled tick."""

    def create() -> webview.Window:
        config = Config.load()
        box: list = []
        api = _SettingsApi(config, on_saved, _box_closer(box))
        width, height = 340, 440
        window = _new_window("설정", "settings.html", api, width, height, _position_centered(width, height))
        box.append(window)
        return window

    _focus_or_create("settings", create)


class _AccountApi:
    def __init__(
        self, email: Optional[str], is_logged_out: bool, on_switch: Callable, on_logout: Callable,
        close_fn: Callable[[], None],
    ):
        self._email = email
        self._is_logged_out = is_logged_out
        self._on_switch = on_switch
        self._on_logout = on_logout
        self._close_fn = close_fn

    def get_initial_data(self) -> dict:
        return {"email": self._email, "is_logged_out": self._is_logged_out}

    def switch_account(self) -> None:
        self._on_switch()

    def logout(self) -> None:
        self._on_logout()

    def close(self) -> None:
        self._close_fn()


def show_account_popup(email: Optional[str], is_logged_out: bool, on_switch: Callable, on_logout: Callable) -> None:
    """Confirms which account is currently active before doing anything
    disruptive -- both buttons clear the saved session, so showing this
    first (rather than acting immediately on a menu click) avoids an
    accidental click force-logging someone out with no warning."""

    def create() -> webview.Window:
        box: list = []
        api = _AccountApi(email, is_logged_out, on_switch, on_logout, _box_closer(box))
        width, height = 320, 300
        window = _new_window("계정", "account.html", api, width, height, _position_centered(width, height))
        box.append(window)
        return window

    _focus_or_create("account", create)
