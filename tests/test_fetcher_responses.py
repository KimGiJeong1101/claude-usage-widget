"""fetcher.py가 claude.ai 응답을 어떻게 해석하는지 확인한다.

1. 401/403만 "세션 만료"(= 로그인 창을 띄워야 함)로 보고, 서버 장애(5xx)나
   요청 횟수 제한(429) 같은 일시적인 오류는 일반 오류로 처리해야 한다.
   예전에는 200이 아니면 전부 세션 만료로 봐서, claude.ai가 잠깐만
   불안정해도 멀쩡한 세션을 두고 로그인 창이 떴다.
2. 사용량 응답에서 구간 자체가 null이어도 죽지 않아야 한다.
"""

import pytest

from usage_widget import fetcher


class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def json(self):
        return self._payload


def _install_fake_playwright(monkeypatch, tmp_path, orgs_status=200, usage_status=200, usage_payload=None):
    if usage_payload is None:
        usage_payload = {
            "five_hour": {"utilization": 17, "resets_at": None},
            "seven_day": {"utilization": 82, "resets_at": None},
        }

    class _FakeRequestContext:
        def get(self, url):
            if "usage" in url:
                return _FakeResponse(usage_status, usage_payload)
            return _FakeResponse(orgs_status, [{"uuid": "org-1"}])

    class _FakeContext:
        request = _FakeRequestContext()

    class _FakeBrowser:
        def new_context(self, storage_state):
            return _FakeContext()

        def close(self):
            pass

    class _FakeChromium:
        def launch(self, headless, channel):
            return _FakeBrowser()

    class _FakePlaywright:
        chromium = _FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    session_file = tmp_path / "session_state.json"
    session_file.write_text("{}")
    monkeypatch.setattr(fetcher, "sync_playwright", lambda: _FakePlaywright())
    monkeypatch.setattr(fetcher, "session_state_path", lambda: session_file)


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failures_are_session_expired(tmp_path, monkeypatch, status):
    _install_fake_playwright(monkeypatch, tmp_path, orgs_status=status)
    with pytest.raises(fetcher.SessionExpiredError):
        fetcher.fetch_usage()


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_server_errors_are_not_session_expired(tmp_path, monkeypatch, status):
    _install_fake_playwright(monkeypatch, tmp_path, usage_status=status)
    with pytest.raises(Exception) as exc_info:
        fetcher.fetch_usage()
    assert not isinstance(exc_info.value, fetcher.SessionExpiredError), (
        f"{status} 응답을 세션 만료로 취급했다 (로그인 창이 불필요하게 뜸)"
    )


def test_null_usage_windows_do_not_crash(tmp_path, monkeypatch):
    _install_fake_playwright(monkeypatch, tmp_path, usage_payload={"five_hour": None, "seven_day": None})
    usage = fetcher.fetch_usage()
    assert usage.session_percent == 0
    assert usage.week_percent == 0
    assert usage.session_reset_at is None
    assert usage.week_reset_at is None
