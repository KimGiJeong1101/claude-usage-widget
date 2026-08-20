"""Flyout shown when the tray icon is clicked, and the settings window
reachable from the right-click menu."""

import math
import sys
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Optional

import sv_ttk
from PIL import Image, ImageDraw, ImageTk

from usage_widget import fonts
from usage_widget.config import Config
from usage_widget.fetcher import UsageData
from usage_widget.tray_icon import color_for_percent

_MUTED_TEXT = "#8a8a8a"
_TROUGH_COLOR = "#e4e4e4"
_BAR_HEIGHT = 12
_BAR_WIDTH = 280
_BAR_RADIUS = 6

_PANEL_BG = "#ffffff"
_PANEL_BORDER = "#d8d8d8"
_DIVIDER = "#ececec"
_PANEL_RADIUS = 16
_KEY_COLOR = "#0a1a2a"  # arbitrary color used as the Windows "transparent" key
_FLYOUT_WIDTH = 320
_FLYOUT_HEIGHT = 260
_SETTINGS_WIDTH = 280
_SETTINGS_HEIGHT = 190
_CURSOR_GAP = 24  # how far inside the flyout's near edge the cursor lands

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


def get_gui_root() -> tk.Tk:
    """Public accessor so main.py can create this root up front on its own
    dedicated GUI thread, and marshal pystray menu callbacks onto that
    thread via root.after(0, ...) instead of calling tkinter directly from
    pystray's own callback thread. pystray's Win32 backend invokes menu
    callbacks from a low-level native message-loop context, not a normal
    Python thread -- calling a long blocking tkinter operation (wait_window)
    directly from there crashed the process ("PyEval_RestoreThread: ... but
    the GIL is released")."""
    return _get_hidden_root()


def _font(size: int, bold: bool = False) -> tuple:
    family = fonts.ensure_loaded()
    return (family, size, "bold" if bold else "normal")


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


def _draw_progress_fill(canvas: tk.Canvas, percent: int) -> None:
    canvas.delete("all")
    _rounded_rect(canvas, 0, 0, _BAR_WIDTH, _BAR_HEIGHT, _BAR_RADIUS, fill=_TROUGH_COLOR, outline="")
    clamped = min(max(percent, 0), 100)
    if clamped > 0:
        fill_width = max(_BAR_WIDTH * clamped / 100, _BAR_RADIUS * 2)
        _rounded_rect(
            canvas, 0, 0, fill_width, _BAR_HEIGHT, _BAR_RADIUS,
            fill=_rgb_to_hex(color_for_percent(percent)), outline="",
        )


def _progress_bar(parent: tk.Widget, percent: int) -> tk.Canvas:
    """Custom-drawn rounded progress bar, colored by severity. ttk's
    built-in Progressbar renders via theme-specific images/styling that
    doesn't reliably accept custom fill colors, so this draws directly on
    a Canvas instead."""
    canvas = tk.Canvas(
        parent, width=_BAR_WIDTH, height=_BAR_HEIGHT, highlightthickness=0, bg=_PANEL_BG
    )
    _draw_progress_fill(canvas, percent)
    return canvas


def _divider(parent: tk.Widget) -> tk.Frame:
    return tk.Frame(parent, height=1, bg=_DIVIDER)


_ICON_SIZE = 22
_ICON_RENDER_SCALE = 4  # draw big, downsample -- much smoother edges than drawing at 1x


def _render_close_icon(color: str) -> ImageTk.PhotoImage:
    size = _ICON_SIZE * _ICON_RENDER_SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    r = size * 0.28
    w = max(2, int(size * 0.09))
    draw.line([cx - r, cy - r, cx + r, cy + r], fill=color, width=w)
    draw.line([cx - r, cy + r, cx + r, cy - r], fill=color, width=w)
    return ImageTk.PhotoImage(img.resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS))


def _render_refresh_icon(color: str) -> ImageTk.PhotoImage:
    size = _ICON_SIZE * _ICON_RENDER_SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    r = size * 0.34
    w = max(2, int(size * 0.09))
    end_deg = 250
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=-40, end=end_deg, fill=color, width=w)
    angle = math.radians(end_deg)
    tip_x, tip_y = cx + r * math.cos(angle), cy + r * math.sin(angle)
    ah = size * 0.16
    draw.polygon(
        [(tip_x, tip_y), (tip_x - ah, tip_y - ah * 0.3), (tip_x - ah * 0.2, tip_y + ah)],
        fill=color,
    )
    return ImageTk.PhotoImage(img.resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS))


def _render_pin_icon(color: str, filled: bool) -> ImageTk.PhotoImage:
    """Filled = pinned (stays open once the pointer leaves); outline = the
    default hover-to-preview behavior."""
    size = _ICON_SIZE * _ICON_RENDER_SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = size / 2
    head_cy = size * 0.38
    head_r = size * 0.22
    tip_y = size * 0.88
    w = max(2, int(size * 0.09))
    if filled:
        draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=color)
        draw.polygon(
            [(cx - head_r * 0.55, head_cy + head_r * 0.6), (cx + head_r * 0.55, head_cy + head_r * 0.6), (cx, tip_y)],
            fill=color,
        )
    else:
        draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], outline=color, width=w)
        draw.line([cx, head_cy + head_r, cx, tip_y], fill=color, width=w)
    return ImageTk.PhotoImage(img.resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS))


def _icon_button(parent: tk.Widget, photo: ImageTk.PhotoImage, on_click) -> tk.Label:
    """A small icon button drawn as a bitmap (via Pillow) rather than a text
    glyph -- symbols like "X" and a refresh arrow aren't reliably present in
    every font, and rendered as blank/tofu boxes on some machines depending
    on the OS's fallback font. A bitmap always looks the same everywhere."""
    label = tk.Label(parent, image=photo, bg=_PANEL_BG, cursor="hand2", bd=0, padx=6, pady=4)
    label.image = photo  # keep a reference -- Tk doesn't, and would garbage-collect it
    label.bind("<Button-1>", lambda e: on_click())
    return label


def _reset_status_text(reset_at: Optional[datetime]) -> str:
    """The API returns no reset time for a window with no usage yet (e.g.
    right after a 5-hour session resets, before the next message is sent)."""
    if reset_at is None:
        return "아직 사용 시작 전"
    delta = reset_at - datetime.now()
    total_minutes = max(int(delta.total_seconds()) // 60, 0)
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    if days:
        return f"리셋까지 {days}일 {hours}시간 후"
    return f"리셋까지 {hours}시간 {minutes}분 후"


def _add_usage_row(parent: tk.Widget, row: int, title: str, percent: int, reset_at: Optional[datetime]) -> dict:
    percent_color = _rgb_to_hex(color_for_percent(percent))

    tk.Label(parent, text=title, font=_font(12, bold=True), bg=_PANEL_BG).grid(
        column=0, row=row, sticky="w"
    )
    percent_label = tk.Label(parent, text=f"{percent}%", font=_font(16, bold=True), bg=_PANEL_BG, fg=percent_color)
    percent_label.grid(column=1, row=row, sticky="e")
    bar_canvas = _progress_bar(parent, percent)
    bar_canvas.grid(column=0, row=row + 1, columnspan=2, sticky="ew", pady=(10, 6))
    reset_label = tk.Label(
        parent,
        text=_reset_status_text(reset_at),
        font=_font(10),
        fg=_MUTED_TEXT,
        bg=_PANEL_BG,
    )
    reset_label.grid(column=0, row=row + 2, columnspan=2, sticky="w")

    return {"percent_label": percent_label, "bar_canvas": bar_canvas, "reset_label": reset_label}


def _update_usage_row(refs: dict, percent: int, reset_at: Optional[datetime]) -> None:
    refs["percent_label"].config(text=f"{percent}%", fg=_rgb_to_hex(color_for_percent(percent)))
    _draw_progress_fill(refs["bar_canvas"], percent)
    refs["reset_label"].config(text=_reset_status_text(reset_at))


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


def _close_when_pointer_leaves(
    window: tk.Toplevel, active: dict, grace_ms: int = 600, poll_ms: int = 150
) -> None:
    """Polls the actual OS cursor position rather than relying on Tk
    Enter/Leave events, which fire per-child-widget (e.g. moving from the
    canvas onto an embedded label counts as "leaving" the canvas) and would
    otherwise close the flyout while the pointer is still over it.

    active["value"] can be flipped to False (the pin button does this) to
    pause this entirely -- the poll keeps running so it resumes correctly
    if unpinned later, it just skips the close check while paused."""

    def check():
        if not window.winfo_exists():
            return
        if active["value"]:
            x, y = window.winfo_pointerx(), window.winfo_pointery()
            left, top = window.winfo_rootx(), window.winfo_rooty()
            if not (left <= x <= left + window.winfo_width() and top <= y <= top + window.winfo_height()):
                window.destroy()
                return
        window.after(poll_ms, check)

    window.after(grace_ms, check)


def _position_near_cursor(window: tk.Toplevel, width: int, height: int) -> None:
    """Anchors the flyout near the click position, opening away from
    whichever screen edge the cursor is closest to. The taskbar/dock (and
    so the tray icon that was just clicked) can sit on any edge of the
    screen depending on the user's own setup, so anchoring to the cursor
    rather than a hardcoded corner keeps this correct for everyone."""
    cursor_x, cursor_y = window.winfo_pointerx(), window.winfo_pointery()
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()

    # The cursor must land INSIDE the window the moment it opens -- it
    # auto-closes once the pointer leaves it, so if the window were placed
    # just outside the cursor (a gap instead of an overlap) it would look
    # like it vanishes instantly unless the mouse is moved there right away.
    if cursor_y > screen_h / 2:
        y = cursor_y - height + _CURSOR_GAP
    else:
        y = cursor_y - _CURSOR_GAP

    if cursor_x > screen_w / 2:
        x = cursor_x - width + _CURSOR_GAP
    else:
        x = cursor_x - _CURSOR_GAP

    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    window.geometry(f"{width}x{height}+{x}+{y}")


def _position_centered(window: tk.Toplevel, width: int, height: int) -> None:
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def _new_panel(
    title: str, width: int, height: int, *, position: str = "cursor", close_on_leave: bool = False
) -> tuple:
    """A borderless, rounded, always-on-top panel -- similar to Windows' own
    volume/network flyouts -- rather than a plain dialog with a native
    (OS-drawn) title bar. Used for both the usage flyout (anchored near the
    click, auto-closes on pointer leave) and the settings window (centered,
    stays open so it's usable while filling in the form)."""
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
    header.grid(column=0, row=0, sticky="ew", padx=20, pady=(16, 4))
    header.grid_columnconfigure(0, weight=1)
    tk.Label(header, text=title, font=_font(13, bold=True), bg=_PANEL_BG).grid(column=0, row=0, sticky="w")
    close_btn = _icon_button(header, _render_close_icon(_MUTED_TEXT), window.destroy)
    close_btn.grid(column=10, row=0, sticky="e")
    _make_draggable(header, window)

    body = tk.Frame(panel, bg=_PANEL_BG)
    body.grid(column=0, row=1, sticky="nsew", padx=20, pady=(10, 16))

    if position == "cursor":
        _position_near_cursor(window, width, height)
    else:
        _position_centered(window, width, height)

    close_on_leave_active = {"value": True} if close_on_leave else None
    if close_on_leave_active is not None:
        _close_when_pointer_leaves(window, close_on_leave_active)
    window.after(50, lambda: (window.focus_force(), window.lift()))
    return window, header, body, close_on_leave_active


def show_usage_popup(usage: UsageData, on_refresh=None) -> None:
    """on_refresh, if given, is called as on_refresh(on_done) when the
    refresh button is clicked -- it's expected to fetch fresh data in the
    background and call on_done(new_usage) from the GUI thread once ready
    (see main.py's _manual_refresh), so this never blocks the window."""
    window, header, body, close_on_leave_active = _new_panel(
        "Claude 사용량", _FLYOUT_WIDTH, _FLYOUT_HEIGHT, position="cursor", close_on_leave=True
    )

    session_refs = _add_usage_row(body, 0, "세션 (5시간)", usage.session_percent, usage.session_reset_at)
    _divider(body).grid(row=3, column=0, columnspan=2, sticky="ew", pady=16)
    week_refs = _add_usage_row(body, 4, "주간", usage.week_percent, usage.week_reset_at)

    def toggle_pin() -> None:
        close_on_leave_active["value"] = not close_on_leave_active["value"]
        pinned = not close_on_leave_active["value"]
        photo = _render_pin_icon("#4a9eff" if pinned else _MUTED_TEXT, filled=pinned)
        pin_btn.config(image=photo)
        pin_btn.image = photo

    pin_btn = _icon_button(header, _render_pin_icon(_MUTED_TEXT, filled=False), toggle_pin)
    pin_btn.grid(column=1, row=0, sticky="e")

    if on_refresh is not None:
        def set_refresh_color(color: str) -> None:
            photo = _render_refresh_icon(color)
            refresh_btn.config(image=photo)
            refresh_btn.image = photo

        def on_done(new_usage: UsageData | None) -> None:
            if not window.winfo_exists():
                return
            if new_usage is None:
                # briefly flash red so a failed refresh doesn't look like
                # nothing happened, then settle back to the normal look
                set_refresh_color("#e04b4b")
                window.after(
                    1500,
                    lambda: set_refresh_color(_MUTED_TEXT) if window.winfo_exists() else None,
                )
                return
            _update_usage_row(session_refs, new_usage.session_percent, new_usage.session_reset_at)
            _update_usage_row(week_refs, new_usage.week_percent, new_usage.week_reset_at)
            set_refresh_color(_MUTED_TEXT)

        def do_refresh() -> None:
            set_refresh_color("#c0c0c0")
            on_refresh(on_done)

        refresh_btn = _icon_button(header, _render_refresh_icon(_MUTED_TEXT), do_refresh)
        refresh_btn.grid(column=2, row=0, sticky="e")

    window.wait_window()


def show_settings_popup() -> None:
    config = Config.load()
    sv_ttk.set_theme("light")
    window, _header, body, _close_active = _new_panel("설정", _SETTINGS_WIDTH, _SETTINGS_HEIGHT, position="center")

    tk.Label(body, text="갱신 주기", font=_font(12, bold=True), bg=_PANEL_BG).grid(
        column=0, row=0, columnspan=2, sticky="w"
    )

    entry_row = tk.Frame(body, bg=_PANEL_BG)
    entry_row.grid(column=0, row=1, columnspan=2, sticky="w", pady=(10, 4))
    interval_var = tk.IntVar(value=config.refresh_seconds)
    ttk.Entry(entry_row, textvariable=interval_var, width=8, font=_font(11)).grid(column=0, row=0)
    tk.Label(entry_row, text="초", font=_font(11), bg=_PANEL_BG).grid(column=1, row=0, padx=(8, 0))

    tk.Label(
        body, text="예: 900초 = 15분", font=_font(9), fg=_MUTED_TEXT, bg=_PANEL_BG
    ).grid(column=0, row=2, columnspan=2, sticky="w")

    def on_save():
        config.refresh_seconds = interval_var.get()
        config.save()
        # TODO: re-register the OS scheduler task (schtasks / launchd)
        # with the new interval -- see plan doc section 5.
        window.destroy()

    ttk.Button(body, text="저장", command=on_save).grid(
        column=0, row=3, columnspan=2, sticky="ew", pady=(16, 0)
    )

    window.wait_window()
