"""auth.py의 login_and_save_session()이 가진 두 가지 보장을 확인한다.

1. 여러 스레드가 동시에 불러도, 실제 로그인용 브라우저는 딱 한 번만
   뜬다 (2026-09-30 전까지는 "로그인 창이 2개 뜬다"는 버그가 있었음 —
   notes 저장소 섹션 26.1).
2. 세션 파일이 이미 있어도 그 내용이 낡았으면(세션 만료/거부) 재로그인이
   실제로 실행돼야 한다. 섹션 26.1의 수정이 "파일이 있으면 무조건
   스킵"으로 짜여 있어서 이 보장이 깨졌던 회귀가 있었다 (2026-09-30
   수정, notes 저장소 섹션 28 참고) — 이 테스트가 그 회귀를 다시 잡아준다.
"""

import threading
from pathlib import Path

from usage_widget import auth

_launch_count_lock = threading.Lock()


class _FakePage:
    def goto(self, url):
        pass


class _FakeContext:
    """첫 확인 때는 로그인 전(쿠키 없음), 그 다음부터는 로그인 완료 상태를
    흉내낸다."""

    def __init__(self):
        self._checked_once = False

    def cookies(self):
        if not self._checked_once:
            self._checked_once = True
            return []
        return [{"name": "sessionKey"}]

    def new_page(self):
        return _FakePage()

    def storage_state(self, path):
        Path(path).write_text('{"fresh": true}')


class _FakeBrowser:
    def new_context(self, viewport=None):
        return _FakeContext()

    def close(self):
        pass


def _make_fake_chromium(launch_counter):
    class _FakeChromium:
        def launch(self, headless, channel, args=None):
            with _launch_count_lock:
                launch_counter[0] += 1
            return _FakeBrowser()

    return _FakeChromium()


def _make_fake_playwright(launch_counter):
    chromium = _make_fake_chromium(launch_counter)

    class _FakePlaywright:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    _FakePlaywright.chromium = chromium
    return _FakePlaywright


def test_concurrent_logins_open_only_one_browser(tmp_path, monkeypatch):
    session_file = tmp_path / "session_state.json"
    launch_counter = [0]

    monkeypatch.setattr(auth, "sync_playwright", _make_fake_playwright(launch_counter))
    monkeypatch.setattr(auth, "session_state_path", lambda: session_file)

    threads = [threading.Thread(target=auth.login_and_save_session) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert launch_counter[0] == 1, f"로그인 브라우저가 여러 번 떴다 (launch_count={launch_counter[0]})"


def test_stale_session_file_still_triggers_relogin(tmp_path, monkeypatch):
    session_file = tmp_path / "session_state.json"
    session_file.write_text('{"stale": true}')  # 예전에 만들어진, 지금은 거부당하는 낡은 세션
    launch_counter = [0]

    monkeypatch.setattr(auth, "sync_playwright", _make_fake_playwright(launch_counter))
    monkeypatch.setattr(auth, "session_state_path", lambda: session_file)

    auth.login_and_save_session()

    assert launch_counter[0] == 1, "낡은 세션 파일이 있을 때 재로그인이 스킵됐다 (회귀)"
    assert "fresh" in session_file.read_text(), "세션 파일이 새로 갱신되지 않았다"
