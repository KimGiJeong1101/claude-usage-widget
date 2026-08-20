"""Flyout shown when the tray icon is clicked, and the settings/account
windows reachable from the right-click menu."""

import math
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Optional

import sv_ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from usage_widget import autostart, fonts
from usage_widget.config import Config
from usage_widget.fetcher import UsageData
from usage_widget.tray_icon import DEFAULT_STYLE, STYLE_LABELS, color_for_percent

_MUTED_TEXT = "#8a8a8a"
_TEXT_PRIMARY = "#1c1e21"
_ACCENT = "#3b82f6"
_CARD_BORDER = "#e5e6e9"

_PANEL_BG = "#ffffff"
_PANEL_BORDER = "#e2e2e2"
_PANEL_RADIUS = 18
_KEY_COLOR = "#0a1a2a"  # arbitrary color used as the Windows "transparent" key
_FLYOUT_WIDTH = 344
_FLYOUT_HEIGHT = 372
_SETTINGS_WIDTH = 300
_SETTINGS_HEIGHT = 430
_ACCOUNT_WIDTH = 280
_ACCOUNT_HEIGHT = 280
_CURSOR_GAP = 24  # how far inside the flyout's near edge the cursor lands

_ASSET_FONT_DIR = Path(__file__).parent / "assets" / "fonts"


def _pil_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Loads a bundled font file directly (unlike usage_widget.fonts, which
    registers it with Windows for *tkinter* widgets to reference by name).
    Pillow reads the file itself and needs no OS registration, so this
    renders identically on every platform -- used for baking the percent
    number into the gradient ring image below, since it has to be part of
    that single bitmap for the text to land exactly centered in the ring."""
    return ImageFont.truetype(str(_ASSET_FONT_DIR / f"Pretendard-{name}.otf"), size)


def _render_ring_with_percent(percent: int, size: int = 100) -> ImageTk.PhotoImage:
    """A donut gauge in a flat severity color (green/yellow/red, same
    thresholds as the tray icon) with the percent number baked into its
    exact center."""
    clamped = min(max(percent, 0), 100)
    color = color_for_percent(clamped)
    thickness = max(int(size * 0.13), 8)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size / 2
    r_outer = size / 2 - 3
    r_inner = r_outer - thickness
    bbox = [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer]

    draw_full = ImageDraw.Draw(img)
    draw_full.ellipse(bbox, fill=(231, 233, 236, 255))

    sweep = 360 * clamped / 100
    if sweep > 0:
        draw_full.pieslice(bbox, start=-90, end=-90 + sweep, fill=color + (255,))
    draw_full.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=(0, 0, 0, 0))

    draw = ImageDraw.Draw(img)
    text = f"{clamped}%"
    text_font = _pil_font("Bold", int(size * 0.22))
    bbox = draw.textbbox((0, 0), text, font=text_font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - text_w / 2, cy - text_h / 2 - bbox[1]), text, font=text_font, fill=_TEXT_PRIMARY)

    return ImageTk.PhotoImage(img)

_IS_WINDOWS = sys.platform == "win32"

_hidden_root = None
_ttk_theme_applied = False


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


def _ensure_ttk_theme() -> None:
    """sv_ttk's theme is process-global (not per-window), but every popup
    that uses any ttk widget needs it applied at least once, or whichever
    one happens to open first gets the native (plain) ttk look instead."""
    global _ttk_theme_applied
    if not _ttk_theme_applied:
        sv_ttk.set_theme("light")
        _ttk_theme_applied = True


# Windows registers each weight of a multi-file font family (see
# usage_widget/fonts.py) as its own family name -- "Pretendard",
# "Pretendard Medium", "Pretendard SemiBold" -- rather than one family
# selectable by a numeric weight, which is all tkinter's simple
# (family, size, "bold"/"normal") font spec can address otherwise.
_FONT_WEIGHT_SUFFIX = {"regular": "", "medium": " Medium", "semibold": " SemiBold", "bold": ""}


def _font(size: int, weight: str = "regular") -> tuple:
    base = fonts.ensure_loaded()
    if not base:
        return ("", size, "bold" if weight == "bold" else "normal")
    suffix = _FONT_WEIGHT_SUFFIX.get(weight, "")
    tk_weight = "bold" if weight == "bold" else "normal"
    return (f"{base}{suffix}", size, tk_weight)


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


def _card_frame(parent: tk.Widget, width: int, height: int, radius: int = 18) -> tuple:
    """A rounded, bordered card (each usage row gets one) drawn the same
    way as the outer window panel -- a Canvas background plus an embedded
    Frame for the actual widget content."""
    canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0, bg=_PANEL_BG)
    _rounded_rect(canvas, 0, 0, width, height, radius, fill=_PANEL_BG, outline=_CARD_BORDER)
    content = tk.Frame(canvas, bg=_PANEL_BG)
    canvas.create_window(2, 2, window=content, anchor="nw", width=width - 4, height=height - 4)
    return canvas, content


_ICON_SIZE = 22
_ICON_RENDER_SCALE = 4  # draw big, downsample -- much smoother edges than drawing at 1x
_ICON_GAP = 6  # breathing room between adjacent header icons


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


def _render_settings_icon(color: str) -> ImageTk.PhotoImage:
    """Three horizontal sliders -- a common "settings" pictogram, and much
    easier to draw accurately with plain lines/circles than a gear."""
    size = _ICON_SIZE * _ICON_RENDER_SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = max(2, int(size * 0.08))
    knob_r = size * 0.08
    x0, x1 = size * 0.12, size * 0.88
    knob_x = [size * 0.35, size * 0.65, size * 0.45]
    for i, ky in enumerate([size * 0.22, size * 0.5, size * 0.78]):
        draw.line([x0, ky, x1, ky], fill=color, width=w)
        kx = knob_x[i]
        draw.ellipse([kx - knob_r, ky - knob_r, kx + knob_r, ky + knob_r], fill=color)
    return ImageTk.PhotoImage(img.resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS))


def _render_person_icon(color: str) -> ImageTk.PhotoImage:
    size = _ICON_SIZE * _ICON_RENDER_SCALE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = size / 2
    head_r = size * 0.19
    head_cy = size * 0.32
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=color)
    shoulder_r = size * 0.34
    shoulder_cy = size * 1.02
    draw.pieslice(
        [cx - shoulder_r, shoulder_cy - shoulder_r, cx + shoulder_r, shoulder_cy + shoulder_r],
        start=180, end=360, fill=color,
    )
    return ImageTk.PhotoImage(img.resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS))


def _icon_button(parent: tk.Widget, photo: ImageTk.PhotoImage, on_click) -> tk.Label:
    """A small icon button drawn as a bitmap (via Pillow) rather than a text
    glyph -- symbols like "X" and a refresh arrow aren't reliably present in
    every font, and rendered as blank/tofu boxes on some machines depending
    on the OS's fallback font. A bitmap always looks the same everywhere."""
    label = tk.Label(parent, image=photo, bg=_PANEL_BG, cursor="hand2", bd=0, padx=4, pady=4)
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


_ROW_CARD_HEIGHT = 132
_ROW_CARD_WIDTH = _FLYOUT_WIDTH - 44  # matches _new_panel's body padx (22 each side)
_RING_SIZE = 92


def _add_usage_row(
    parent: tk.Widget, row: int, title: str, percent: int, reset_at: Optional[datetime], pady=(0, 0)
) -> dict:
    card_canvas, content = _card_frame(parent, _ROW_CARD_WIDTH, _ROW_CARD_HEIGHT)
    card_canvas.grid(column=0, row=row, sticky="w", pady=pady)

    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(1, weight=1)

    tk.Label(content, text=title, font=_font(13, weight="semibold"), bg=_PANEL_BG, fg=_TEXT_PRIMARY).grid(
        column=0, row=0, sticky="nw", padx=(18, 0), pady=(16, 0)
    )
    reset_label = tk.Label(
        content, text=_reset_status_text(reset_at), font=_font(10), fg=_MUTED_TEXT, bg=_PANEL_BG
    )
    reset_label.grid(column=0, row=2, sticky="sw", padx=(18, 0), pady=(0, 16))

    ring_photo = _render_ring_with_percent(percent, size=_RING_SIZE)
    ring_label = tk.Label(content, image=ring_photo, bg=_PANEL_BG)
    ring_label.image = ring_photo  # keep a reference -- Tk doesn't, and would garbage-collect it
    ring_label.grid(column=1, row=0, rowspan=3, sticky="e", padx=(0, 18))

    return {"ring_label": ring_label, "reset_label": reset_label}


def _update_usage_row(refs: dict, percent: int, reset_at: Optional[datetime]) -> None:
    ring_photo = _render_ring_with_percent(percent, size=_RING_SIZE)
    refs["ring_label"].config(image=ring_photo)
    refs["ring_label"].image = ring_photo
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
    title: str,
    width: int,
    height: int,
    *,
    position: str = "cursor",
    close_on_leave: bool = False,
    icon_photo: Optional[ImageTk.PhotoImage] = None,
) -> tuple:
    """A borderless, rounded, always-on-top panel -- similar to Windows' own
    volume/network flyouts -- rather than a plain dialog with a native
    (OS-drawn) title bar. Used for the usage flyout (anchored near the
    click, auto-closes on pointer leave) and the settings/account windows
    (centered, stay open so they're usable while interacting)."""
    _ensure_ttk_theme()

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
    header.grid(column=0, row=0, sticky="ew", padx=22, pady=(18, 6))
    title_column = 0
    if icon_photo is not None:
        icon_label = tk.Label(header, image=icon_photo, bg=_PANEL_BG)
        icon_label.image = icon_photo  # keep a reference -- Tk doesn't, and would garbage-collect it
        icon_label.grid(column=0, row=0, sticky="w", padx=(0, 8))
        title_column = 1
    header.grid_columnconfigure(title_column, weight=1)
    title_label = tk.Label(header, text=title, font=_font(14, weight="semibold"), bg=_PANEL_BG, fg=_TEXT_PRIMARY)
    title_label.grid(column=title_column, row=0, sticky="w")
    close_btn = _icon_button(header, _render_close_icon(_MUTED_TEXT), window.destroy)
    close_btn.grid(column=10, row=0, sticky="e", padx=(_ICON_GAP, 0))
    # bind dragging to the frame AND the title label -- the label only
    # occupies its own text width (sticky="w", not stretched), but that's
    # exactly where someone would naturally try to grab the window by, so
    # it needs its own binding rather than relying on clicks landing on
    # bare header background around it.
    _make_draggable(header, window)
    _make_draggable(title_label, window)

    body = tk.Frame(panel, bg=_PANEL_BG)
    body.grid(column=0, row=1, sticky="nsew", padx=22, pady=(8, 20))

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
    week_refs = _add_usage_row(
        body, 1, "주간", usage.week_percent, usage.week_reset_at, pady=(12, 0)
    )

    def toggle_pin() -> None:
        close_on_leave_active["value"] = not close_on_leave_active["value"]
        pinned = not close_on_leave_active["value"]
        photo = _render_pin_icon("#4a9eff" if pinned else _MUTED_TEXT, filled=pinned)
        pin_btn.config(image=photo)
        pin_btn.image = photo

    pin_btn = _icon_button(header, _render_pin_icon(_MUTED_TEXT, filled=False), toggle_pin)
    pin_btn.grid(column=1, row=0, sticky="e", padx=(_ICON_GAP, 0))

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
        refresh_btn.grid(column=2, row=0, sticky="e", padx=(_ICON_GAP, 0))

    window.wait_window()


def show_account_popup(email: Optional[str], is_logged_out: bool, on_switch, on_logout) -> None:
    """Confirms which account is currently active before doing anything
    disruptive -- both buttons clear the saved session, so showing this
    first (rather than acting immediately on a menu click) avoids an
    accidental click force-logging someone out with no warning."""
    window, _header, body, _close_active = _new_panel(
        "계정", _ACCOUNT_WIDTH, _ACCOUNT_HEIGHT, position="center",
        icon_photo=_render_person_icon(_TEXT_PRIMARY),
    )
    card_width = _ACCOUNT_WIDTH - 44

    card_canvas, card = _card_frame(body, card_width, 78)
    card_canvas.grid(column=0, row=0, sticky="ew")

    status_label = "현재 상태" if is_logged_out else "현재 로그인"
    status_value = "로그아웃됨" if is_logged_out else (email or "확인 중...")
    tk.Label(card, text=status_label, font=_font(10, weight="medium"), fg=_MUTED_TEXT, bg=_PANEL_BG).grid(
        column=0, row=0, sticky="w", padx=18, pady=(14, 0)
    )
    tk.Label(
        card, text=status_value, font=_font(12, weight="semibold"), fg=_TEXT_PRIMARY, bg=_PANEL_BG,
        wraplength=card_width - 36, justify="left",
    ).grid(column=0, row=1, sticky="w", padx=18, pady=(2, 14))

    def switch_and_close():
        window.destroy()
        on_switch()

    switch_label = "로그인" if is_logged_out else "계정 변경"
    ttk.Button(body, text=switch_label, command=switch_and_close, style="Accent.TButton").grid(
        column=0, row=1, sticky="ew", pady=(16, 0), ipady=4
    )

    if not is_logged_out:
        def logout_and_close():
            window.destroy()
            on_logout()

        ttk.Button(body, text="로그아웃", command=logout_and_close).grid(
            column=0, row=2, sticky="ew", pady=(10, 0), ipady=4
        )

    window.wait_window()


def show_settings_popup(on_saved=None) -> None:
    """on_saved, if given, is called right after a successful save -- lets
    main.py refresh the tray icon immediately instead of waiting for the
    next scheduled tick (up to refresh_seconds later)."""
    config = Config.load()
    window, _header, body, _close_active = _new_panel(
        "설정", _SETTINGS_WIDTH, _SETTINGS_HEIGHT, position="center",
        icon_photo=_render_settings_icon(_TEXT_PRIMARY),
    )
    card_width = _SETTINGS_WIDTH - 44

    interval_card_canvas, interval_card = _card_frame(body, card_width, 112)
    interval_card_canvas.grid(column=0, row=0, sticky="ew")
    interval_card.grid_columnconfigure(0, weight=1)

    tk.Label(interval_card, text="갱신 주기", font=_font(12, weight="semibold"), bg=_PANEL_BG, fg=_TEXT_PRIMARY).grid(
        column=0, row=0, columnspan=2, sticky="w", padx=18, pady=(14, 0)
    )
    entry_row = tk.Frame(interval_card, bg=_PANEL_BG)
    entry_row.grid(column=0, row=1, columnspan=2, sticky="w", padx=18, pady=(8, 4))
    interval_var = tk.IntVar(value=config.refresh_seconds)
    ttk.Entry(entry_row, textvariable=interval_var, width=8, font=_font(11)).grid(column=0, row=0, ipady=2)
    tk.Label(entry_row, text="초", font=_font(11), bg=_PANEL_BG, fg=_TEXT_PRIMARY).grid(column=1, row=0, padx=(10, 0))
    tk.Label(
        interval_card, text="예: 900초 = 15분", font=_font(9), fg=_MUTED_TEXT, bg=_PANEL_BG
    ).grid(column=0, row=2, columnspan=2, sticky="w", padx=18, pady=(0, 14))

    style_card_height = 150 if sys.platform == "win32" else 100
    style_card_canvas, style_card = _card_frame(body, card_width, style_card_height)
    style_card_canvas.grid(column=0, row=1, sticky="ew", pady=(14, 0))
    style_card.grid_columnconfigure(0, weight=1)

    tk.Label(
        style_card, text="트레이 아이콘 스타일", font=_font(12, weight="semibold"), bg=_PANEL_BG, fg=_TEXT_PRIMARY
    ).grid(column=0, row=0, sticky="w", padx=18, pady=(14, 0))
    label_by_style = STYLE_LABELS
    style_by_label = {label: style for style, label in STYLE_LABELS.items()}
    style_var = tk.StringVar(value=label_by_style.get(config.tray_icon_style, label_by_style[DEFAULT_STYLE]))
    ttk.Combobox(
        style_card, textvariable=style_var, values=list(STYLE_LABELS.values()), state="readonly", font=_font(10)
    ).grid(column=0, row=1, sticky="ew", padx=18, pady=(8, 0), ipady=2)

    autostart_var = tk.BooleanVar(value=autostart.is_enabled())
    if sys.platform == "win32":
        ttk.Checkbutton(
            style_card, text="PC 시작 시 자동 실행", variable=autostart_var
        ).grid(column=0, row=2, sticky="w", padx=18, pady=(14, 14))
    else:
        tk.Frame(style_card, height=14, bg=_PANEL_BG).grid(column=0, row=2)

    def on_save():
        config.refresh_seconds = interval_var.get()
        config.tray_icon_style = style_by_label.get(style_var.get(), DEFAULT_STYLE)
        config.save()
        if autostart_var.get():
            autostart.enable()
        else:
            autostart.disable()
        window.destroy()
        if on_saved is not None:
            on_saved()

    ttk.Button(body, text="저장", command=on_save, style="Accent.TButton").grid(
        column=0, row=2, sticky="ew", pady=(16, 0), ipady=4
    )

    window.wait_window()
