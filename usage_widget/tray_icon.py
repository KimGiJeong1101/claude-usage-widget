"""Draws the small status icon shown in the Windows tray / macOS menu bar.

Tray icons are rendered at very small real sizes (commonly 16x16), where
thin rings and text become an illegible blur. A pair of filled bars (like a
tiny battery gauge) stays readable at that size because it's a bold filled
region rather than a fine stroke or glyph -- see the fill height for
magnitude and the color for severity.
"""

from PIL import Image, ImageDraw

SIZE = 64
BAR_WIDTH = 22
BAR_GAP = 6
MARGIN = 4
CORNER_RADIUS = 4

GREEN = (52, 168, 83)
YELLOW = (251, 188, 5)
RED = (234, 67, 53)
TRACK = (210, 210, 210)


def color_for_percent(percent: int) -> tuple:
    if percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def build_icon_image(session_percent: int, week_percent: int) -> Image.Image:
    """Two bars side by side (session, week), each filled bottom-up by its
    own percentage and colored by its own severity."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    total_width = BAR_WIDTH * 2 + BAR_GAP
    x0 = (SIZE - total_width) // 2
    top = MARGIN
    bottom = SIZE - MARGIN
    height = bottom - top

    for i, percent in enumerate((session_percent, week_percent)):
        bar_left = x0 + i * (BAR_WIDTH + BAR_GAP)
        bar_right = bar_left + BAR_WIDTH
        draw.rounded_rectangle(
            [bar_left, top, bar_right, bottom], radius=CORNER_RADIUS, fill=TRACK
        )
        fill_height = height * min(max(percent, 0), 100) / 100
        if fill_height > 0:
            draw.rounded_rectangle(
                [bar_left, bottom - fill_height, bar_right, bottom],
                radius=CORNER_RADIUS,
                fill=color_for_percent(percent),
            )

    return img
