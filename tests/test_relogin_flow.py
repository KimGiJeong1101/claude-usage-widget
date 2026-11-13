"""main.py의 재로그인 흐름이 "원치 않는 로그인 창"을 띄우지 않는지 확인한다.

1. 사용자가 재로그인 창을 닫으면 _LoginCancelledError로 끝나야 하고,
   로그인 창을 한 번 더 띄우면 안 된다 (예전에는 닫자마자 또 떴다).
2. 로그아웃(일시정지) 상태에서는 세션이 없어도 로그인 창을 띄우면 안 된다
   (로그아웃 직후 백그라운드 갱신이 겹치거나, 고정해둔 사용량 팝업에서
   새로고침을 누른 경우).
"""

import pytest

from usage_widget import main
from usage_widget.fetcher import AccountInfo, SessionExpiredError


class _FakeIcon:
    icon = None
    title = None


@pytest.fixture
def fresh_state(monkeypatch):
    monkeypatch.setattr(main, "_logged_out", False)
    monkeypatch.setattr(main, "_latest_usage", None)
    monkeypatch.setattr(main, "_last_error", None)
    monkeypatch.setattr(main, "_account_info", None)
    monkeypatch.setattr(main, "_update_icon", lambda icon: None)
    monkeypatch.setattr(main, "push_usage_update", lambda usage: None)
    monkeypatch.setattr(main, "fetch_account_info", lambda: AccountInfo(email="someone@example.com"))


def _expired():
    raise SessionExpiredError("expired")


def test_closing_relogin_window_does_not_reopen_it(monkeypatch, fresh_state):
    login_calls = []
    monkeypatch.setattr(main, "fetch_usage", _expired)
    monkeypatch.setattr(main, "login_and_save_session", lambda: login_calls.append(1) or False)

    with pytest.raises(main._LoginCancelledError):
        main._fetch_with_relogin()

    assert len(login_calls) == 1, f"로그인 창이 {len(login_calls)}번 떴다"


def test_no_login_window_while_logged_out(monkeypatch, fresh_state):
    login_calls = []
    monkeypatch.setattr(main, "_logged_out", True)
    monkeypatch.setattr(main, "fetch_usage", _expired)
    monkeypatch.setattr(main, "login_and_save_session", lambda: login_calls.append(1) or True)

    with pytest.raises(SessionExpiredError):
        main._fetch_with_relogin()

    assert not login_calls, "로그아웃 상태인데 로그인 창이 떴다"


def test_manual_refresh_does_nothing_while_logged_out(monkeypatch, fresh_state):
    calls = []
    monkeypatch.setattr(main, "_logged_out", True)
    monkeypatch.setattr(main, "fetch_usage", lambda: calls.append("fetch"))
    monkeypatch.setattr(main, "login_and_save_session", lambda: calls.append("login") or True)

    assert main._manual_refresh(_FakeIcon()) is None
    assert not calls, f"로그아웃 상태에서 새로고침이 {calls}를 실행했다"


def test_manual_refresh_pauses_after_cancelled_login(monkeypatch, fresh_state):
    monkeypatch.setattr(main, "fetch_usage", _expired)
    monkeypatch.setattr(main, "login_and_save_session", lambda: False)

    assert main._manual_refresh(_FakeIcon()) is None
    assert main._logged_out is True, "로그인 창을 닫았는데 일시정지 상태로 안 바뀌었다"


def test_before_login_hook_runs_before_login_window(monkeypatch, fresh_state):
    order = []
    fetch_results = iter([_expired, lambda: "usage"])
    monkeypatch.setattr(main, "fetch_usage", lambda: next(fetch_results)())
    monkeypatch.setattr(main, "login_and_save_session", lambda: order.append("login") or True)

    result = main._fetch_with_relogin(before_login=lambda: order.append("close_splash"))

    assert result == "usage"
    assert order == ["close_splash", "login"], "스플래시가 로그인 창보다 먼저 닫히지 않았다"
