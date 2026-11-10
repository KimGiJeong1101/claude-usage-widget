"""한도 표시 이름과 80%/90% 알림 동작을 확인한다.

알림은 한도마다, 단계(80/90)마다 한 번만 떠야 하고, 사용량이 다시
내려가면(= 리셋) 다음에 또 넘을 때 다시 떠야 한다. 매 갱신(기본 60초)마다
같은 알림이 반복되면 쓸 수가 없다.
"""

import pytest

from usage_widget import main
from usage_widget.fetcher import LimitInfo, UsageData
from usage_widget.webui import _usage_popup_height, limit_label


class _FakeIcon:
    def __init__(self):
        self.notifications = []

    def notify(self, message, title):
        self.notifications.append((title, message))


def _usage(**percents):
    limits = [LimitInfo(kind, percent, None, model="Fable" if kind == "weekly_scoped" else None)
              for kind, percent in percents.items()]
    return UsageData(session_percent=percents.get("session", 0), week_percent=percents.get("weekly_all", 0), limits=limits)


@pytest.fixture(autouse=True)
def fresh_alert_state(monkeypatch):
    monkeypatch.setattr(main, "_limit_alert_levels", {})


def test_alert_fires_once_per_threshold_and_again_after_reset():
    icon = _FakeIcon()

    main._notify_limit_thresholds(icon, _usage(session=50, weekly_all=10))
    assert icon.notifications == [], "80% 미만인데 알림이 떴다"

    main._notify_limit_thresholds(icon, _usage(session=82, weekly_all=10))
    main._notify_limit_thresholds(icon, _usage(session=85, weekly_all=10))
    assert len(icon.notifications) == 1, "같은 80% 단계에서 알림이 반복됐다"

    main._notify_limit_thresholds(icon, _usage(session=91, weekly_all=10))
    assert len(icon.notifications) == 2, "90%를 넘었는데 알림이 안 떴다"

    main._notify_limit_thresholds(icon, _usage(session=3, weekly_all=10))  # 세션 리셋
    main._notify_limit_thresholds(icon, _usage(session=81, weekly_all=10))
    assert len(icon.notifications) == 3, "리셋 후 다시 80%를 넘었는데 알림이 안 떴다"


def test_each_limit_is_tracked_separately():
    icon = _FakeIcon()
    main._notify_limit_thresholds(icon, _usage(session=10, weekly_all=10, weekly_scoped=88))
    assert len(icon.notifications) == 1
    assert "Fable" in icon.notifications[0][1]


def test_notify_failure_never_breaks_refresh():
    class _BrokenIcon:
        def notify(self, *_):
            raise RuntimeError("tray not ready")

    main._notify_limit_thresholds(_BrokenIcon(), _usage(session=95))  # 예외가 밖으로 나오면 안 됨


def test_limit_labels():
    assert limit_label(LimitInfo("session", 0, None), "ko") == "세션 (5시간)"
    assert limit_label(LimitInfo("weekly_all", 0, None), "en") == "Weekly (all models)"
    assert limit_label(LimitInfo("weekly_scoped", 0, None, model="Fable"), "ko") == "주간 (Fable)"
    assert limit_label(LimitInfo("something_new", 0, None), "ko") == "기타 한도"


def test_popup_height_grows_with_limit_count():
    assert _usage_popup_height(3) - _usage_popup_height(2) == _usage_popup_height(2) - _usage_popup_height(1)
    assert _usage_popup_height(3) < 340, "한도 3개짜리 팝업이 예전 2개짜리(340px)보다 커졌다"
