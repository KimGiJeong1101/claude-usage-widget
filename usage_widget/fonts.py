"""Loads the bundled Pretendard font (SIL OFL, see assets/fonts/LICENSE) so
UI labels can reference it by name, without requiring it to be installed
system-wide.

Only implemented for Windows: AddFontResourceEx with FR_PRIVATE registers
the font files for this process only (no admin rights, no system-wide
install). There's no equivalent one-line trick on macOS (would need
CoreText's CTFontManagerRegisterFontsForURL via pyobjc, untested here) --
elsewhere this silently no-ops and callers fall back to the OS default font.
"""

import ctypes
import sys
from pathlib import Path

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FAMILY = "Pretendard"

_FR_PRIVATE = 0x10

_loaded = False


def ensure_loaded() -> str:
    """Returns the font family name to use in tkinter font specs -- either
    "Pretendard" if it was (or already is) successfully registered, or ""
    (meaning: let tkinter pick its own default) otherwise."""
    global _loaded
    if sys.platform != "win32":
        return ""

    if not _loaded:
        for font_file in FONT_DIR.glob("*.otf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(font_file), _FR_PRIVATE, 0)
        _loaded = True

    return FAMILY
