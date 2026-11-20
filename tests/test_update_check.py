"""업데이트 확인(update_check.check_for_update)과 트레이 메뉴의 수동 확인을 확인한다.

실제 인터넷 요청은 하지 않는다 -- httpx.get을 가짜로 바꾼다.
"""

from types import SimpleNamespace

import httpx
import pytest

from usage_widget import config as config_mod
from usage_widget import i18n, main, update_check


class _FakeResponse:
    def __init__(self, tag):
        self._tag = tag

    def raise_for_status(self):
        pass

    def json(self):
        return {"tag_name": self._tag}


def _network_down(*args, **kwargs):
    raise httpx.ConnectError("network is unreachable")


class _FakeIcon:
    def __init__(self):
        self.notifications = []

    def update_menu(self):
        pass

    def notify(self, message, title):
        self.notifications.append(message)


class _SyncThread:
    """worker 스레드를 바로 그 자리에서 실행해, 결과를 테스트가 곧바로 볼 수 있게 한다."""

    def __init__(self, target, daemon=None):
        self._target = target

    def start(self):
        self._target()


@pytest.fixture
def manual_check_state(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(main, "threading", SimpleNamespace(Thread=_SyncThread))
    monkeypatch.setattr(main, "_update_available_version", None)
    monkeypatch.setattr(main, "_update_in_progress", False)
    monkeypatch.setattr(main, "_update_checking", False)
    monkeypatch.setattr(main, "_update_notified_versions", set())


def test_returns_newer_version(monkeypatch):
    monkeypatch.setattr(update_check, "__version__", "0.3.17")
    monkeypatch.setattr(update_check.httpx, "get", lambda *a, **k: _FakeResponse("v0.4.0"))

    assert update_check.check_for_update() == "0.4.0"


def test_returns_none_when_already_latest(monkeypatch):
    monkeypatch.setattr(update_check, "__version__", "0.3.17")
    monkeypatch.setattr(update_check.httpx, "get", lambda *a, **k: _FakeResponse("v0.3.17"))

    assert update_check.check_for_update() is None


def test_network_error_is_raised(monkeypatch):
    # 실패를 None("최신 버전")으로 바꾸면, 부르는 쪽이 "확인 실패"를 알 수 없다.
    monkeypatch.setattr(update_check.httpx, "get", _network_down)

    with pytest.raises(httpx.ConnectError):
        update_check.check_for_update()


def test_manual_check_failure_says_check_failed(monkeypatch, manual_check_state):
    monkeypatch.setattr(update_check.httpx, "get", _network_down)
    icon = _FakeIcon()

    main._on_update_click(icon, item=None)

    assert icon.notifications == [i18n.t("notify.check_failed_msg", "ko")]
    assert main._update_checking is False, "메뉴가 '업데이트 확인 중...'에 멈춰 있다"


def test_manual_check_up_to_date(monkeypatch, manual_check_state):
    monkeypatch.setattr(update_check, "__version__", "0.3.17")
    monkeypatch.setattr(update_check.httpx, "get", lambda *a, **k: _FakeResponse("v0.3.17"))
    icon = _FakeIcon()

    main._on_update_click(icon, item=None)

    assert icon.notifications == [i18n.t("notify.up_to_date_msg", "ko", version=main.__version__)]
