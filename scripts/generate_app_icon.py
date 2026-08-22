"""Generates the app/window icon (installer/icon/*) from the same gradient
square + bar-chart mark already used as the logo in the popup headers
(usage_widget/assets/web/common.css .icon-chip, usage.html's SVG) -- reusing
it here keeps a single brand mark instead of inventing a second design for
the exe/installer icon.

Run manually when the mark needs to change:
    python scripts/generate_app_icon.py

Only produces the Windows .ico (Pillow can write multi-resolution .ico
directly). macOS's .icns is built in CI from the master PNG using the
platform's own sips/iconutil (see .github/workflows/release.yml) -- those
tools only exist on macOS, matching the project's no-local-Mac approach
(see claude-usage-widget-plan.md section 10.1).
"""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
RADIUS = int(SIZE * 0.22)
ACCENT = (59, 130, 246)  # --accent (#3b82f6)
ACCENT_2 = (139, 92, 246)  # --accent-2 (#8b5cf6)
OUT_DIR = Path(__file__).parent.parent / "installer" / "icon"


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_square() -> Image.Image:
    """135deg linear gradient (top-left -> bottom-right), matching the CSS
    `linear-gradient(135deg, var(--accent), var(--accent-2))` used on
    .icon-chip, clipped to a rounded square."""
    max_d = (SIZE - 1) * 2
    pixels = [_lerp(ACCENT, ACCENT_2, (x + y) / max_d) for y in range(SIZE) for x in range(SIZE)]
    gradient = Image.new("RGB", (SIZE, SIZE))
    gradient.putdata(pixels)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=255)

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask)
    return img


def _draw_round_cap_line(draw: ImageDraw.ImageDraw, p0: tuple, p1: tuple, width: float, fill: tuple) -> None:
    draw.line([p0, p1], fill=fill, width=round(width))
    r = width / 2
    for cx, cy in (p0, p1):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def _draw_bars(img: Image.Image) -> None:
    """The three ascending bars from the 24x24 SVG viewBox (usage.html's
    .icon-chip svg), scaled and centered onto the icon canvas."""
    padding = SIZE * 0.24
    content = SIZE - 2 * padding
    scale = content / 24
    stroke = 2.2 * scale

    def pt(vx: float, vy: float) -> tuple:
        return (padding + vx * scale, padding + vy * scale)

    draw = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    for vx, y_top in ((6, 14), (12, 8), (18, 4)):
        _draw_round_cap_line(draw, pt(vx, 20), pt(vx, y_top), stroke, white)


def build_master_icon() -> Image.Image:
    img = _gradient_square()
    _draw_bars(img)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    master = build_master_icon()

    png_path = OUT_DIR / "app_icon.png"
    master.save(png_path)

    ico_path = OUT_DIR / "ClaudeUsageWidget.ico"
    master.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
