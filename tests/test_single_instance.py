"""single_instance가 "이미 실행 중"을 정확히 판단하는지 확인한다.

Hyper-V/WSL2/Docker가 깔린 Windows PC는 포트 대역을 통째로 예약해서, 이
앱이 쓰는 포트의 bind가 "이미 사용 중"이 아닌 "권한 없음"으로 실패할 수
있다. 예전에는 이것도 "이미 실행 중"으로 착각해서 앱이 아예 안 켜졌다.
"""

import errno

from usage_widget import single_instance


class _FailingSocket:
    def __init__(self, err):
        self._err = err

    def bind(self, addr):
        raise OSError(self._err, "simulated bind failure")

    def close(self):
        pass


def test_reserved_port_is_not_treated_as_already_running(monkeypatch):
    monkeypatch.setattr(single_instance.socket, "socket", lambda *a: _FailingSocket(errno.EACCES))
    assert single_instance._acquire_port() is True


def test_port_in_use_is_treated_as_already_running(monkeypatch):
    monkeypatch.setattr(single_instance.socket, "socket", lambda *a: _FailingSocket(errno.EADDRINUSE))
    assert single_instance._acquire_port() is False
