"""Draws the small status icon shown in the Windows tray / macOS menu bar.

Tray icons are rendered at very small real sizes (commonly 16-22px), where
thin rings and small text become an illegible blur -- confirmed by testing.
Several styles are offered (selectable in Settings) since people disagree on
which tradeoff they want between "exact number" and "reads at a glance."
All of them only show the session (5-hour) percentage, since it resets far
more often than the weekly figure and is the one worth a glance without
opening the popup -- the weekly number is one click away in the popup.

Every style outlines its shape (see OUTLINE/OUTLINE_WIDTH) so it stays
legible against a taskbar/menu-bar background of any color -- a plain fill
color can otherwise vanish against a similarly-colored background.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 64

GREEN = (52, 168, 83)
YELLOW = (251, 188, 5)
RED = (234, 67, 53)
TRACK = (222, 222, 222)
OUTLINE = (90, 90, 90)
# Outline widths here are drawn at the 64px source size; real tray icons
# render at ~16-22px, so anything much thinner than this all but disappears
# after the downscale (e.g. a 2px source outline becomes ~0.5px -- invisible).
OUTLINE_WIDTH = 7

_FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "Pretendard-Bold.otf"


def color_for_percent(percent: int) -> tuple:
    if percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def _build_donut(session_percent: int, week_percent: int) -> Image.Image:
    """Thick donut gauge, filled clockwise from the top -- a bold filled
    wedge (not a thin outline) still reads as "roughly how full" at real
    tray size."""
    margin, thickness = 3, 28
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = [margin, margin, SIZE - margin, SIZE - margin]
    draw.ellipse(bbox, fill=TRACK)

    clamped = min(max(session_percent, 0), 100)
    if clamped > 0:
        end_angle = -90 + 360 * clamped / 100
        draw.pieslice(bbox, start=-90, end=end_angle, fill=color_for_percent(session_percent))

    inner = margin + thickness
    inner_bbox = [inner, inner, SIZE - inner, SIZE - inner]
    draw.ellipse(inner_bbox, fill=(0, 0, 0, 0))

    draw.ellipse(bbox, outline=OUTLINE, width=OUTLINE_WIDTH)
    draw.ellipse(inner_bbox, outline=OUTLINE, width=OUTLINE_WIDTH)

    return img


def _build_bar(session_percent: int, week_percent: int) -> Image.Image:
    """A single vertical bar, filled bottom-up."""
    bar_width, margin, radius = 30, 4, 6
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    left = (SIZE - bar_width) // 2
    right = left + bar_width
    top, bottom = margin, SIZE - margin
    draw.rounded_rectangle([left, top, right, bottom], radius=radius, fill=TRACK, outline=OUTLINE, width=4)

    height = bottom - top
    clamped = min(max(session_percent, 0), 100)
    fill_height = height * clamped / 100
    if fill_height > 0:
        draw.rounded_rectangle(
            [left, bottom - fill_height, right, bottom], radius=radius, fill=color_for_percent(session_percent)
        )

    return img


def _build_battery(session_percent: int, week_percent: int) -> Image.Image:
    """A battery-style gauge (rounded body + a small nub), filled left to
    right -- a familiar "how much is left" metaphor."""
    body_w, body_h = 46, 30
    x0, y0 = (SIZE - body_w) // 2, (SIZE - body_h) // 2
    x1, y1 = x0 + body_w, y0 + body_h
    nub_w, nub_h = 6, 14

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=6, outline=OUTLINE, width=5, fill=TRACK)
    draw.rounded_rectangle(
        [x1 - 2, y0 + (body_h - nub_h) // 2, x1 + nub_w, y0 + (body_h - nub_h) // 2 + nub_h],
        radius=3,
        fill=OUTLINE,
    )

    clamped = min(max(session_percent, 0), 100)
    pad = 6
    fill_width = (body_w - pad * 2) * clamped / 100
    if fill_width > 0:
        draw.rounded_rectangle(
            [x0 + pad, y0 + pad, x0 + pad + fill_width, y1 - pad], radius=3, fill=color_for_percent(session_percent)
        )

    return img


def _build_liquid(session_percent: int, week_percent: int) -> Image.Image:
    """A circle that fills like a liquid gauge, rising from the bottom."""
    margin = 3
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = [margin, margin, SIZE - margin, SIZE - margin]
    draw.ellipse(bbox, fill=TRACK)

    clamped = min(max(session_percent, 0), 100)
    fill_top = SIZE - margin - (SIZE - 2 * margin) * clamped / 100

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse(bbox, fill=255)
    fill_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(fill_layer).rectangle([0, fill_top, SIZE, SIZE], fill=color_for_percent(session_percent))
    img.paste(fill_layer, (0, 0), Image.composite(fill_layer, img, mask).split()[3])

    draw.ellipse(bbox, outline=OUTLINE, width=6)
    return img


def _build_big_number(session_percent: int, week_percent: int) -> Image.Image:
    """A solid severity-colored square with the percent number filling most
    of it -- legible at real tray size specifically because the number is
    large relative to the icon, unlike a small number next to a ring."""
    margin = 4
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = color_for_percent(session_percent)
    draw.rounded_rectangle([margin, margin, SIZE - margin, SIZE - margin], radius=16, fill=color, outline=OUTLINE, width=3)

    text = str(min(max(session_percent, 0), 99))
    font = ImageFont.truetype(str(_FONT_PATH), 34)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_color = (40, 40, 30) if color == YELLOW else (255, 255, 255)
    draw.text(((SIZE - text_w) / 2, (SIZE - text_h) / 2 - bbox[1]), text, font=font, fill=text_color)

    return img


STYLES = {
    "donut": _build_donut,
    "battery": _build_battery,
    "bar": _build_bar,
    "big_number": _build_big_number,
    "liquid": _build_liquid,
}
STYLE_LABELS = {
    "donut": "도넛 게이지",
    "battery": "배터리",
    "bar": "막대",
    "big_number": "숫자",
    "liquid": "원형 채움",
}
DEFAULT_STYLE = "donut"


LOGGED_OUT_COLOR = (150, 150, 150)


def _build_logged_out(style: str) -> Image.Image:
    """The chosen style's shape, but with every severity color (green/
    yellow/red) replaced by a neutral gray -- a colored reading would look
    like a real usage percentage, which would be misleading while logged
    out and not actually being tracked."""
    builder = STYLES.get(style, STYLES[DEFAULT_STYLE])
    img = builder(50, 50).convert("RGBA")
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if (r, g, b) in (GREEN, YELLOW, RED):
                pixels[x, y] = (*LOGGED_OUT_COLOR, a)
    return img


def build_icon_image(
    session_percent: int, week_percent: int, style: str = DEFAULT_STYLE, logged_out: bool = False
) -> Image.Image:
    if logged_out:
        return _build_logged_out(style)
    builder = STYLES.get(style, STYLES[DEFAULT_STYLE])
    return builder(session_percent, week_percent)
