"""Draws the small status icon shown in the Windows tray / macOS menu bar."""

from PIL import Image, ImageDraw

SIZE = 64

GREEN = (52, 168, 83)
YELLOW = (251, 188, 5)
RED = (234, 67, 53)


def _color_for_percent(percent: int) -> tuple:
    if percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def build_icon_image(percent: int) -> Image.Image:
    """Colored ring + percent number, so the general status is readable
    at a glance without opening the popup."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = _color_for_percent(percent)
    margin = 4
    draw.ellipse(
        [margin, margin, SIZE - margin, SIZE - margin],
        outline=color,
        width=6,
    )

    text = str(min(percent, 99))
    bbox = draw.textbbox((0, 0), text)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((SIZE - text_w) / 2, (SIZE - text_h) / 2 - bbox[1]),
        text,
        fill=color,
    )
    return img
