"""fetcher.py의 browser_launch_lock이 headless Chrome 실행을 실제로
직렬화하는지 확인한다.

배경: 자동갱신 스레드(60초 주기)와 수동 새로고침이 동시에 headless
Chrome을 띄우면, 사양이 낮은 PC에서 리소스 경쟁으로 새로고침이 가끔
이유 없이 실패하는 버그가 있었다 (2026-09-13 수정, notes 저장소 섹션
25 참고). 이 테스트는 그 수정이 유지되는지 지킨다."""

import threading
import time

from usage_widget import fetcher

_concurrent_count = 0
_max_concurrent = 0
_counter_lock = threading.Lock()


class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def json(self):
        return self._payload


class _FakeRequestContext:
    def get(self, url):
        global _concurrent_count, _max_concurrent
        with _counter_lock:
            _concurrent_count += 1
            _max_concurrent = max(_max_concurrent, _concurrent_count)
        time.sleep(0.1)  # headless Chrome의 네트워크 요청 시간을 흉내
        with _counter_lock:
            _concurrent_count -= 1
        if "usage" in url:
            return _FakeResponse(
                200,
                {
                    "five_hour": {"utilization": 17, "resets_at": None},
                    "seven_day": {"utilization": 82, "resets_at": None},
                },
            )
        return _FakeResponse(200, [{"uuid": "org-1"}])


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


def test_fetch_usage_calls_never_overlap(tmp_path, monkeypatch):
    global _concurrent_count, _max_concurrent
    _concurrent_count = 0
    _max_concurrent = 0

    session_file = tmp_path / "session_state.json"
    session_file.write_text("{}")

    monkeypatch.setattr(fetcher, "sync_playwright", lambda: _FakePlaywright())
    monkeypatch.setattr(fetcher, "session_state_path", lambda: session_file)

    threads = [threading.Thread(target=fetcher.fetch_usage) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert _max_concurrent == 1, "fetch_usage() 호출들이 동시에 겹쳤다 (락이 안 먹힘)"
