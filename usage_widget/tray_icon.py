"""Draws the small status icon shown in the Windows tray / macOS menu bar.

Tray icons are rendered at very small real sizes (commonly 16-22px), where
thin rings and text become an illegible blur -- confirmed by testing both
here. A thick donut gauge (a bold filled wedge, not a thin outline or a
glyph) still reads as "roughly how full" at that size via the color/track
ratio, even though it can't carry an exact number the way the popup does.
Shows the session (5-hour) usage, since it resets far more often than the
weekly figure and is the one worth a glance without opening the popup.
"""

from PIL import Image, ImageDraw

SIZE = 64
MARGIN = 3
THICKNESS = 28

GREEN = (52, 168, 83)
YELLOW = (251, 188, 5)
RED = (234, 67, 53)
TRACK = (222, 222, 222)


def color_for_percent(percent: int) -> tuple:
    if percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def build_icon_image(session_percent: int) -> Image.Image:
    """A thick donut gauge, filled clockwise from the top by the session
    usage percentage and colored by its severity."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = [MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN]
    draw.ellipse(bbox, fill=TRACK)

    clamped = min(max(session_percent, 0), 100)
    if clamped > 0:
        end_angle = -90 + 360 * clamped / 100
        draw.pieslice(bbox, start=-90, end=end_angle, fill=color_for_percent(session_percent))

    inner = MARGIN + THICKNESS
    draw.ellipse([inner, inner, SIZE - inner, SIZE - inner], fill=(0, 0, 0, 0))

    return img
