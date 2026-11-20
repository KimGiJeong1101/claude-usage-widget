"""main.py의 시작할 때 첫 사용량 조회(_initial_fetch)를 확인한다.

1. 세션이 없으면 로그인부터 하고, 로그인 창을 닫으면 _LoginCancelledError로 끝난다.
2. 일시적인 오류(네트워크 미연결, 5xx 등)는 간격을 두고 다시 시도한다 -- 예전엔
   한 번만 실패해도 앱이 "실행할 수 없습니다"를 띄우고 꺼졌다(자동 시작 직후
   Wi-Fi가 아직 안 붙은 경우 등).
3. 로그인 창을 닫은 경우는 다시 시도하지 않는다(로그인 창이 또 뜨면 안 된다).
"""

import pytest

from usage_widget import main
from usage_widget.fetcher import AccountInfo, SessionExpiredError, UsageData


@pytest.fixture
def fresh_state(monkeypatch):
    monkeypatch.setattr(main, "_logged_out", False)
    monkeypatch.setattr(main, "_account_info", None)
    monkeypatch.setattr(main, "close_splash", lambda splash: None)
    monkeypatch.setattr(main, "fetch_account_info", lambda: AccountInfo(email="someone@example.com"))
    monkeypatch.setattr(main, "_STARTUP_RETRY_DELAYS", (0, 0, 0, 0))


def _fetch_sequence(*results):
    """부를 때마다 results를 차례로 돌려준다. 예외 객체면 던진다."""
    calls = []

    def fetch():
        result = results[len(calls)]
        calls.append(1)
        if isinstance(result, Exception):
            raise result
        return result

    return fetch, calls


def test_logs_in_first_when_no_saved_session(monkeypatch, fresh_state):
    usage = UsageData(session_percent=10, week_percent=20)
    login_calls = []
    monkeypatch.setattr(main, "has_saved_session", lambda: False)
    monkeypatch.setattr(main, "login_and_save_session", lambda: login_calls.append(1) or True)
    monkeypatch.setattr(main, "fetch_usage", lambda: usage)

    assert main._initial_fetch(splash=None) is usage
    assert len(login_calls) == 1


def test_closing_login_window_raises_login_cancelled(monkeypatch, fresh_state):
    monkeypatch.setattr(main, "has_saved_session", lambda: False)
    monkeypatch.setattr(main, "login_and_save_session", lambda: False)

    with pytest.raises(main._LoginCancelledError):
        main._initial_fetch(splash=None)


def test_transient_error_is_retried(monkeypatch, fresh_state):
    usage = UsageData(session_percent=10, week_percent=20)
    fetch, calls = _fetch_sequence(RuntimeError("usage endpoint returned 503"), usage)
    monkeypatch.setattr(main, "has_saved_session", lambda: True)
    monkeypatch.setattr(main, "fetch_usage", fetch)

    assert main._initial_fetch(splash=None) is usage
    assert len(calls) == 2


def test_gives_up_after_five_attempts(monkeypatch, fresh_state):
    error = RuntimeError("usage endpoint returned 503")
    fetch, calls = _fetch_sequence(*([error] * 5))
    monkeypatch.setattr(main, "has_saved_session", lambda: True)
    monkeypatch.setattr(main, "fetch_usage", fetch)

    with pytest.raises(RuntimeError):
        main._initial_fetch(splash=None)
    assert len(calls) == 5


def test_closing_relogin_window_is_not_retried(monkeypatch, fresh_state):
    login_calls = []
    fetch, _ = _fetch_sequence(*([SessionExpiredError("expired")] * 5))
    monkeypatch.setattr(main, "has_saved_session", lambda: True)
    monkeypatch.setattr(main, "fetch_usage", fetch)
    monkeypatch.setattr(main, "login_and_save_session", lambda: login_calls.append(1) or False)

    with pytest.raises(main._LoginCancelledError):
        main._initial_fetch(splash=None)
    assert len(login_calls) == 1, f"로그인 창이 {len(login_calls)}번 떴다"
