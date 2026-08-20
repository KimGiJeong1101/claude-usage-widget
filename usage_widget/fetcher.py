"""Periodic fetch of usage data using the saved session cookies.

claude.ai sits behind Cloudflare bot management that blocks plain HTTP
clients (httpx etc.) outright, even when they present valid session cookies
-- only requests that go through an actual browser's network stack pass.
Playwright's headless context.request does this without rendering the page
or running any of the SPA's JS, so it stays far lighter than a full page
load while still getting through Cloudflare.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from playwright.sync_api import sync_playwright

from usage_widget.paths import session_state_path

API_BASE = "https://claude.ai/api/organizations"
BOOTSTRAP_ENDPOINT = "https://claude.ai/edge-api/bootstrap?statsig_hashing_algorithm=djb2&growthbook_format=sdk"


class SessionExpiredError(Exception):
    """Raised when the saved cookies no longer work and re-login is needed."""


@dataclass
class UsageData:
    session_percent: int
    week_percent: int
    session_reset_at: Optional[datetime]
    week_reset_at: Optional[datetime]


def _parse_reset_at(iso_string: Optional[str]) -> Optional[datetime]:
    """Convert an API timestamp (UTC, e.g. "...+00:00") to a naive local
    datetime, matching the naive datetime.now() used elsewhere (popup.py).
    The API returns null for a window with no usage yet (e.g. right after
    a 5-hour session resets, before the next message is sent) -- that's
    passed through as None rather than a countdown."""
    if iso_string is None:
        return None
    return datetime.fromisoformat(iso_string).astimezone().replace(tzinfo=None)


def fetch_usage() -> UsageData:
    if not session_state_path().exists():
        raise SessionExpiredError("no saved session")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))

            orgs_response = context.request.get(API_BASE)
            if orgs_response.status != 200:
                raise SessionExpiredError(
                    f"organizations list returned {orgs_response.status}"
                )
            organizations = orgs_response.json()
            if not organizations:
                raise SessionExpiredError("no organizations returned for this account")
            org_id = organizations[0]["uuid"]

            usage_response = context.request.get(f"{API_BASE}/{org_id}/usage")
            if usage_response.status != 200:
                raise SessionExpiredError(
                    f"usage endpoint returned {usage_response.status}"
                )
            data = usage_response.json()
        finally:
            browser.close()

    return UsageData(
        session_percent=round(data["five_hour"]["utilization"]),
        week_percent=round(data["seven_day"]["utilization"]),
        session_reset_at=_parse_reset_at(data["five_hour"]["resets_at"]),
        week_reset_at=_parse_reset_at(data["seven_day"]["resets_at"]),
    )


def fetch_account_email() -> str:
    """The SPA's own initial-load endpoint, referenced in its bootstrap JS
    as apiPrefix + "/bootstrap" -- returns account info (among other
    things) including the email address of whoever the saved session
    belongs to, so the "switch account" dialog can show who's currently
    logged in."""
    if not session_state_path().exists():
        raise SessionExpiredError("no saved session")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))
            response = context.request.get(BOOTSTRAP_ENDPOINT)
            if response.status != 200:
                raise SessionExpiredError(f"bootstrap endpoint returned {response.status}")
            data = response.json()
        finally:
            browser.close()

    return data["account"]["email_address"]


def fetch_usage_mock() -> UsageData:
    """Fake data for developing the tray icon / popup without a saved
    session or network access."""
    from datetime import timedelta

    now = datetime.now()
    return UsageData(
        session_percent=42,
        week_percent=67,
        session_reset_at=now + timedelta(hours=2, minutes=15),
        week_reset_at=now + timedelta(days=3, hours=4),
    )
