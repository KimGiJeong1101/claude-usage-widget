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
    assert [(l.kind, l.percent, l.resets_at) for l in usage.limits] == [("session", 0, None), ("weekly_all", 0, None)]


def test_limits_list_is_read_as_is_including_model_scoped_limits(tmp_path, monkeypatch):
    """claude.ai는 "limits" 목록에 계정별로 한도를 몇 개든 담아준다 (2026-11-10
    실제 응답 기준: 세션 / 주간 전체 / 특정 모델(Fable) 전용 주간). 고정된
    두 개만 읽던 예전 방식으로는 모델 전용 한도가 안 보였다."""
    payload = {
        "five_hour": {"utilization": 4.0, "resets_at": "2026-11-10T16:39:59.654542+00:00"},
        "seven_day": {"utilization": 25.0, "resets_at": "2026-11-15T15:59:59.654563+00:00"},
        "limits": [
            {"kind": "session", "percent": 4, "resets_at": "2026-11-10T16:39:59.654542+00:00", "scope": None, "is_active": False},
            {"kind": "weekly_all", "percent": 25, "resets_at": "2026-11-15T15:59:59.654563+00:00", "scope": None, "is_active": True},
            {
                "kind": "weekly_scoped",
                "percent": 9,
                "resets_at": "2026-11-15T15:59:59.654880+00:00",
                "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None},
                "is_active": False,
            },
            "이상한 항목 하나 -- 이것 때문에 전체가 실패하면 안 됨",
        ],
    }
    _install_fake_playwright(monkeypatch, tmp_path, usage_payload=payload)
    usage = fetcher.fetch_usage()

    assert usage.session_percent == 4
    assert usage.week_percent == 25
    assert [(l.kind, l.percent, l.model, l.is_active) for l in usage.limits] == [
        ("session", 4, None, False),
        ("weekly_all", 25, None, True),
        ("weekly_scoped", 9, "Fable", False),
    ]
    assert all(l.resets_at is not None for l in usage.limits)
