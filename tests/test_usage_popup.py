"""사용량 팝업이 한 화면 안에서 언어를 섞지 않는지 확인한다.

팝업의 언어는 열 때 정해진다(제목, "마지막 갱신", 리셋 문구 모두). 예전엔 열어 둔
채 설정에서 언어를 바꾸면, 자동 갱신(push_usage_update)이 보내는 한도 이름만 설정
파일의 새 언어로 가서 한 화면에 두 언어가 섞였다.

pywebview 창은 가짜로 바꾼다 -- 가짜 창 방식은 test_focus_or_create.py와 같다.
"""

import json

import pytest

from usage_widget import config as config_mod
from usage_widget import webui
from usage_widget.fetcher import LimitInfo, UsageData


class _FakeEvent:
    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler):
        self._handlers.append(handler)
        return self

    def fire(self):
        for handler in list(self._handlers):
            handler()


class _FakeEvents:
    def __init__(self):
        self.closed = _FakeEvent()


class _FakeWindow:
    def __init__(self):
        self.events = _FakeEvents()
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


def _save_language(lang):
    config = config_mod.Config.load()
    config.language = lang
    config.save()


@pytest.fixture
def usage_popup(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(webui, "_position_near_tray", lambda width, height: (0, 0, False))
    monkeypatch.setattr(webui, "_apply_initial_opacity", lambda window, opacity: None)
    window = _FakeWindow()
    monkeypatch.setattr(webui, "_new_window", lambda *args, **kwargs: window)
    yield window
    window.events.closed.fire()  # 싱글턴 등록을 풀어 다른 테스트에 영향이 없게 한다


def _pushed_labels(window):
    script = window.scripts[-1]
    data = json.loads(script[script.index("__pushUsage(") + len("__pushUsage(") : -1])
    return [limit["label"] for limit in data["limits"]]


def test_auto_refresh_keeps_language_popup_was_opened_with(usage_popup):
    usage = UsageData(session_percent=10, week_percent=20, limits=[LimitInfo("session", 10, None)])
    _save_language("ko")
    webui.show_usage_popup(usage)

    _save_language("en")
    webui.push_usage_update(usage)

    assert _pushed_labels(usage_popup) == ["세션 (5시간)"]
