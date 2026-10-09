"""webui.py의 _focus_or_create()가 지키는 두 가지를 확인한다.

1. 같은 종류(key)의 팝업은 한 번에 하나만 생긴다 -- 이미 열려있으면
   create()를 또 부르지 않고 기존 창을 앞으로 가져온다.
2. 창이 닫혔을 때(closed 이벤트) 싱글턴 등록이 제대로 풀려서, 다시
   create()를 부를 수 있게 된다.

참고: _unregister 등록을 락을 놓기 *전에* 하도록 고친 수정(2026-09-14,
notes 저장소 섹션 26.4)은 창이 생성 직후 극단적으로 빨리 닫히는
마이크로초 단위의 경쟁 상태를 막는 것인데, 이 테스트처럼 스레드 없이
한 스레드에서 순서대로 호출하는 방식으로는 그 타이밍 자체를 재현할 수
없다 -- 그래서 이 테스트는 등록 순서가 아니라 "최종적으로 등록/해제가
올바르게 동작하는지"만 검증한다."""

import uuid

from usage_widget import webui


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
        self.shown = 0

    def show(self):
        self.shown += 1


def _unique_key():
    return f"test-{uuid.uuid4().hex}"


def test_second_call_reuses_existing_window_instead_of_creating_new_one():
    key = _unique_key()
    created = []

    def create():
        window = _FakeWindow()
        created.append(window)
        return window

    webui._focus_or_create(key, create)
    webui._focus_or_create(key, create)

    assert len(created) == 1, "같은 키로 두 번 불렀는데 창이 두 번 생성됐다"
    assert created[0].shown == 1, "기존 창의 show()가 호출되지 않았다"


def test_closing_the_window_unregisters_it_so_a_new_one_can_be_created():
    key = _unique_key()
    created = []

    def create():
        window = _FakeWindow()
        created.append(window)
        return window

    webui._focus_or_create(key, create)
    assert len(created) == 1

    created[0].events.closed.fire()  # 사용자가 창을 닫음

    webui._focus_or_create(key, create)
    assert len(created) == 2, "창을 닫은 뒤에도 새 창이 다시 생성되지 않았다"
