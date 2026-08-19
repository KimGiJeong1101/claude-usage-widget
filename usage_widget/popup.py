"""Flyout shown when the tray icon is clicked, and the settings window
reachable from the right-click menu."""

import sys
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import sv_ttk

from usage_widget.config import Config
from usage_widget.fetcher import UsageData
from usage_widget.tray_icon import color_for_percent

_MUTED_TEXT = "#8a8a8a"
_TROUGH_COLOR = "#e0e0e0"
_BAR_HEIGHT = 10
_BAR_WIDTH = 240
_BAR_RADIUS = 5

_PANEL_BG = "#ffffff"
_PANEL_BORDER = "#d8d8d8"
_PANEL_RADIUS = 16
_KEY_COLOR = "#0a1a2a"  # arbitrary color used as the Windows "transparent" key
_FLYOUT_WIDTH = 300
_FLYOUT_HEIGHT = 232
_CURSOR_GAP = 12  # gap between the cursor and the flyout edge

_IS_WINDOWS = sys.platform == "win32"

_hidden_root = None


def _get_hidden_root() -> tk.Tk:
    """A single Tk interpreter for the whole app's lifetime. Popups are
    Toplevels of this root -- repeatedly creating brand-new tk.Tk()
    instances (one per popup open) is not reliably supported and can crash
    the process (observed: "Tcl_AsyncDelete: async handler deleted by the
    wrong thread") once a tray app opens/closes several of them over time."""
    global _hidden_root
    if _hidden_root is None or not _hidden_root.winfo_exists():
        _hidden_root = tk.Tk()
        _hidden_root.withdraw()
    return _hidden_root


def _rgb_to_hex(rgb: tuple) -> str:
    return "#%02x%02x%02x" % rgb


def _rounded_rect(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float, radius: float, **kwargs) -> None:
    points = [
        x0 + radius, y0,
        x1 - radius, y0,
        x1, y0,
        x1, y0 + radius,
        x1, y1 - radius,
        x1, y1,
        x1 - radius, y1,
        x0 + radius, y1,
        x0, y1,
        x0, y1 - radius,
        x0, y0 + radius,
        x0, y0,
    ]
    canvas.create_polygon(points, smooth=True, **kwargs)


def _progress_bar(parent: tk.Widget, percent: int) -> tk.Canvas:
    """Custom-drawn rounded progress bar, colored by severity. ttk's
    built-in Progressbar renders via theme-specific images/styling that
    doesn't reliably accept custom fill colors, so this draws directly on
    a Canvas instead."""
    canvas = tk.Canvas(
        parent, width=_BAR_WIDTH, height=_BAR_HEIGHT, highlightthickness=0, bg=_PANEL_BG
    )
    _rounded_rect(canvas, 0, 0, _BAR_WIDTH, _BAR_HEIGHT, _BAR_RADIUS, fill=_TROUGH_COLOR, outline="")
    clamped = min(max(percent, 0), 100)
    if clamped > 0:
        fill_width = max(_BAR_WIDTH * clamped / 100, _BAR_RADIUS * 2)
        _rounded_rect(
            canvas, 0, 0, fill_width, _BAR_HEIGHT, _BAR_RADIUS,
            fill=_rgb_to_hex(color_for_percent(percent)), outline="",
        )
    return canvas


def _format_remaining(reset_at: datetime) -> str:
    delta = reset_at - datetime.now()
    total_minutes = max(int(delta.total_seconds()) // 60, 0)
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    if days:
        return f"{days}일 {hours}시간 후"
    return f"{hours}시간 {minutes}분 후"


def _add_usage_row(parent: tk.Widget, row: int, title: str, percent: int, reset_at: datetime) -> None:
    tk.Label(parent, text=title, font=("", 11, "bold"), bg=_PANEL_BG).grid(
        column=0, row=row, sticky="w"
    )
    tk.Label(parent, text=f"{percent}%", font=("", 11, "bold"), bg=_PANEL_BG).grid(
        column=1, row=row, sticky="e"
    )
    _progress_bar(parent, percent).grid(
        column=0, row=row + 1, columnspan=2, sticky="ew", pady=(8, 4)
    )
    tk.Label(
        parent,
        text=f"리셋까지 {_format_remaining(reset_at)}",
        fg=_MUTED_TEXT,
        bg=_PANEL_BG,
    ).grid(column=0, row=row + 2, columnspan=2, sticky="w")


def _make_draggable(handle: tk.Widget, window: tk.Toplevel) -> None:
    origin = {"x": 0, "y": 0}

    def start(event):
        origin["x"], origin["y"] = event.x, event.y

    def move(event):
        x = window.winfo_x() + event.x - origin["x"]
        y = window.winfo_y() + event.y - origin["y"]
        window.geometry(f"+{x}+{y}")

    handle.bind("<ButtonPress-1>", start)
    handle.bind("<B1-Motion>", move)


def _close_when_pointer_leaves(window: tk.Toplevel, grace_ms: int = 600, poll_ms: int = 150) -> None:
    """Polls the actual OS cursor position rather than relying on Tk
    Enter/Leave events, which fire per-child-widget (e.g. moving from the
    canvas onto an embedded label counts as "leaving" the canvas) and would
    otherwise close the flyout while the pointer is still over it."""

    def check():
        if not window.winfo_exists():
            return
        x, y = window.winfo_pointerx(), window.winfo_pointery()
        left, top = window.winfo_rootx(), window.winfo_rooty()
        if left <= x <= left + window.winfo_width() and top <= y <= top + window.winfo_height():
            window.after(poll_ms, check)
        else:
            window.destroy()

    window.after(grace_ms, check)


def _position_near_cursor(window: tk.Toplevel, width: int, height: int) -> None:
    """Anchors the flyout near the click position, opening away from
    whichever screen edge the cursor is closest to. The taskbar/dock (and
    so the tray icon that was just clicked) can sit on any edge of the
    screen depending on the user's own setup, so anchoring to the cursor
    rather than a hardcoded corner keeps this correct for everyone."""
    cursor_x, cursor_y = window.winfo_pointerx(), window.winfo_pointery()
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()

    if cursor_y > screen_h / 2:
        y = cursor_y - height - _CURSOR_GAP
    else:
        y = cursor_y + _CURSOR_GAP

    if cursor_x > screen_w / 2:
        x = cursor_x - width + 24
    else:
        x = cursor_x - 24

    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    window.geometry(f"{width}x{height}+{x}+{y}")


def _new_flyout(title: str, width: int, height: int) -> tuple:
    """A borderless, rounded, always-on-top flyout anchored above the tray
    area at the bottom-right of the screen -- similar to Windows' own
    volume/network flyouts -- rather than a plain dialog with a native
    (OS-drawn) title bar. Closes automatically once the pointer leaves it."""
    window = tk.Toplevel(_get_hidden_root())
    window.overrideredirect(True)
    window.attributes("-topmost", True)

    if _IS_WINDOWS:
        # "-transparentcolor" is a Windows-only Tk attribute -- it lets the
        # 4 square corners outside the rounded rect show the real desktop
        # through. Elsewhere, fall back to a plain (square-cornered) panel.
        window.configure(bg=_KEY_COLOR)
        window.attributes("-transparentcolor", _KEY_COLOR)
        canvas_bg = _KEY_COLOR
    else:
        window.configure(bg=_PANEL_BG)
        canvas_bg = _PANEL_BG

    canvas = tk.Canvas(window, width=width, height=height, highlightthickness=0, bg=canvas_bg)
    canvas.pack(fill="both", expand=True)
    _rounded_rect(canvas, 0, 0, width, height, _PANEL_RADIUS, fill=_PANEL_BG, outline=_PANEL_BORDER)

    panel = tk.Frame(canvas, bg=_PANEL_BG)
    canvas.create_window(2, 2, window=panel, anchor="nw", width=width - 4, height=height - 4)

    header = tk.Frame(panel, bg=_PANEL_BG)
    header.grid(column=0, row=0, sticky="ew", padx=18, pady=(14, 6))
    header.grid_columnconfigure(0, weight=1)
    tk.Label(header, text=title, font=("", 11, "bold"), bg=_PANEL_BG).grid(column=0, row=0, sticky="w")
    close_btn = tk.Label(header, text="✕", font=("", 10), bg=_PANEL_BG, fg=_MUTED_TEXT, cursor="hand2")
    close_btn.grid(column=1, row=0, sticky="e")
    close_btn.bind("<Button-1>", lambda e: window.destroy())
    _make_draggable(header, window)

    body = tk.Frame(panel, bg=_PANEL_BG)
    body.grid(column=0, row=1, sticky="nsew", padx=18)

    _position_near_cursor(window, width, height)

    _close_when_pointer_leaves(window)
    window.after(50, lambda: (window.focus_force(), window.lift()))
    return window, body


def show_usage_popup(usage: UsageData) -> None:
    window, body = _new_flyout("Claude 사용량", _FLYOUT_WIDTH, _FLYOUT_HEIGHT)

    _add_usage_row(body, 0, "세션 (5시간)", usage.session_percent, usage.session_reset_at)
    tk.Frame(body, height=18, bg=_PANEL_BG).grid(row=3, column=0)
    _add_usage_row(body, 4, "주간", usage.week_percent, usage.week_reset_at)

    window.wait_window()


def show_settings_popup() -> None:
    config = Config.load()
    window = tk.Toplevel(_get_hidden_root())
    window.title("설정")
    window.resizable(False, False)
    sv_ttk.set_theme("light")
    frame = ttk.Frame(window, padding=20)
    frame.grid()

    ttk.Label(frame, text="갱신 주기 (분)").grid(column=0, row=0, sticky="w")
    interval_var = tk.IntVar(value=config.refresh_minutes)
    ttk.Entry(frame, textvariable=interval_var, width=6).grid(column=1, row=0, padx=(12, 0))

    def on_save():
        config.refresh_minutes = interval_var.get()
        config.save()
        # TODO: re-register the OS scheduler task (schtasks / launchd)
        # with the new interval -- see plan doc section 5.
        window.destroy()

    ttk.Button(frame, text="저장", command=on_save).grid(column=0, row=1, columnspan=2, pady=(16, 0))

    window.wait_window()
