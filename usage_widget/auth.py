"""One-time browser login. Saves the resulting session cookies so that
later refreshes can use plain HTTP requests instead of a full browser
(see fetcher.py and section 4 of the plan doc).
"""

import time

from playwright.sync_api import sync_playwright

from usage_widget.paths import session_state_path

USAGE_URL = "https://claude.ai/settings/usage"
SESSION_COOKIE_NAME = "sessionKey"


def _has_session_cookie(context) -> bool:
    return any(c["name"] == SESSION_COOKIE_NAME for c in context.cookies())


def login_and_save_session() -> None:
    """Open a real browser window for the user to log in to claude.ai,
    then persist cookies/localStorage to session_state_path()."""
    with sync_playwright() as p:
        # Use the real installed Chrome (not Playwright's bundled "Chrome
        # for Testing" build) -- claude.ai's bot-check challenge otherwise
        # loops indefinitely against the Testing build's fingerprint.
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()
        page.goto(USAGE_URL)

        # claude.ai sets a "sessionKey" cookie once login succeeds. Poll for
        # it instead of matching on URL, since goto(USAGE_URL) already makes
        # the URL match itself regardless of login state, and the SPA may
        # bounce through several intermediate pages during login.
        try:
            while not _has_session_cookie(context):
                time.sleep(1)
        except Exception:
            return  # browser was closed before login completed

        # Login may land elsewhere (e.g. the chat home page) rather than
        # back on Settings > Usage, so navigate there explicitly. goto()
        # already waits for the "load" event -- claude.ai keeps background
        # requests (websockets, polling) going indefinitely, so waiting for
        # "networkidle" on top of that would just time out.
        page.goto(USAGE_URL)

        context.storage_state(path=str(session_state_path()))
        browser.close()


def has_saved_session() -> bool:
    return session_state_path().exists()
