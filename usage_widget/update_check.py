"""Checks GitHub Releases for a newer version than the one currently
running. No separate update server is needed -- GitHub's own "latest
release" API already tells us the current version, so this is just a
periodic GET + a version comparison.

Notification-only for now: this surfaces that an update exists (tray
notification + a menu item linking to the release page) rather than
silently downloading and swapping the running executable. Self-replacing
a running .exe needs real care (can't overwrite an open file on Windows,
needs a relaunch step, partial-download handling, ...) -- see
claude-usage-widget-plan.md section 13.3 for that follow-up.
"""

import re
from typing import Optional

import httpx

from usage_widget import __version__

_REPO = "KimGiJeong1101/claude-usage-widget"
_API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{_REPO}/releases/latest"


def _parse_version(text: str) -> tuple:
    """"v1.2.3" -> (1, 2, 3). Anything that doesn't look like a plain
    semantic version returns () so a weird/renamed tag fails safe (no
    update detected) instead of crashing."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text.strip())
    if not match:
        return ()
    return tuple(int(part) for part in match.groups())


def check_for_update() -> Optional[str]:
    """Returns the latest release's version string (e.g. "0.2.0") if it's
    newer than the version currently running, else None. Any failure
    (offline, GitHub API rate limit, unexpected response shape) also
    returns None, so a broken check can never surface as a false "update
    available"."""
    try:
        response = httpx.get(_API_URL, timeout=10, follow_redirects=True)
        response.raise_for_status()
        tag = response.json()["tag_name"]
    except Exception:
        return None

    latest = _parse_version(tag)
    current = _parse_version(__version__)
    if not latest or not current or latest <= current:
        return None
    return tag.lstrip("v")
