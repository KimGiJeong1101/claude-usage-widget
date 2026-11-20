"""설정 팝업(assets/web/settings.html)을 실제 브라우저(Playwright의 Chromium)로
띄워서 화면 동작을 확인한다. pywebview 없이 돌리기 위해, Python 쪽 js_api 대신
가짜 window.pywebview.api를 페이지보다 먼저 넣고 pywebviewready를 직접 일으킨다.

Chromium이 필요하다: playwright install chromium
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

SETTINGS_PAGE = Path(__file__).parent.parent / "usage_widget" / "assets" / "web" / "settings.html"

# window.__saveShouldFail이 true면 save()가 실패한다(예: 레지스트리 권한 문제).
_FAKE_API = """
window.__saveShouldFail = false;
window.__saveCalls = 0;
window.pywebview = {
  api: {
    get_initial_data: async () => ({
      theme: "light",
      language: "ko",
      refresh_seconds: 60,
      tray_icon_style: "donut",
      style_labels: { donut: "도넛 게이지" },
      style_previews: {},
      language_options: { ko: "한국어", en: "English" },
      show_autostart: false,
      autostart_enabled: false,
    }),
    save: async () => {
      window.__saveCalls += 1;
      if (window.__saveShouldFail) throw new Error("registry access denied");
    },
    close: () => {},
    resize_by: () => {},
  },
};
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page()
    page.add_init_script(_FAKE_API)
    page.goto(SETTINGS_PAGE.as_uri())
    page.evaluate("window.dispatchEvent(new Event('pywebviewready'))")
    page.wait_for_function("document.querySelectorAll('#language-select option').length > 0")
    yield page
    page.close()


def _change_theme(page, theme):
    calls_before = page.evaluate("window.__saveCalls")
    page.select_option("#theme-select", theme)
    page.wait_for_function(f"window.__saveCalls > {calls_before}")


def test_failed_save_shows_failure_until_next_success(page):
    hint = page.locator("#autosave-hint")

    page.evaluate("window.__saveShouldFail = true")
    _change_theme(page, "dark")
    # 예전엔 저장이 실패해도 "바로 저장됩니다"가 그대로 남아 있었다.
    page.wait_for_function("document.getElementById('autosave-hint').classList.contains('failed')")
    assert hint.text_content() == "저장하지 못한 변경 사항이 있습니다. 다시 시도해 주세요."

    # 잠깐 떴다 사라지면 놓치므로, 다음 저장이 성공할 때까지 남아 있어야 한다.
    page.wait_for_timeout(1200)
    assert "failed" in hint.get_attribute("class")

    page.evaluate("window.__saveShouldFail = false")
    _change_theme(page, "light")
    page.wait_for_function("!document.getElementById('autosave-hint').classList.contains('failed')")
    assert hint.text_content() == "변경 사항은 바로 저장됩니다"


def test_failure_message_follows_language_change(page):
    page.evaluate("window.__saveShouldFail = true")
    page.select_option("#language-select", "en")
    page.wait_for_function("document.getElementById('autosave-hint').classList.contains('failed')")

    assert page.locator("#autosave-hint").text_content() == "Some changes couldn't be saved. Please try again."
