"""자동 업데이트에서 "새 파일로 바꿔치기"가 실패했을 때를 확인한다.

업데이트 배치 스크립트(self_update._RELAUNCH_SCRIPT)는 새 파일(X.new.exe)을 원래
자리로 옮긴 뒤 다시 실행한다. 옮기기가 실패하면(예: 백신이 새 파일을 잡고 있음)
옛 exe가 그대로 다시 실행되고, 새 파일은 남는다. 예전엔 다음 시작 때 그 파일을
조용히 지우고 "실행됐습니다" 알림만 띄워서, 사용자는 업데이트된 줄 알았다.

빌드된 exe인 것처럼 꾸미고, exe 경로는 임시 폴더로 바꾼다.
"""

import pytest

from usage_widget import config as config_mod
from usage_widget import i18n, main, self_update


class _FakeIcon:
    visible = False

    def __init__(self):
        self.notifications = []

    def notify(self, message, title):
        self.notifications.append(message)


@pytest.fixture
def frozen_exe(monkeypatch, tmp_path):
    exe = tmp_path / "ClaudeUsageWidget.exe"
    exe.write_bytes(b"old")
    monkeypatch.setattr(self_update, "is_frozen", lambda: True)
    monkeypatch.setattr(self_update, "_current_exe_path", lambda: exe)
    return exe


def test_cleanup_reports_leftover_new_exe(frozen_exe):
    staged = frozen_exe.with_name("ClaudeUsageWidget.new.exe")
    staged.write_bytes(b"new")

    assert self_update.cleanup_stale_update_files() is True
    assert not staged.exists()


def test_cleanup_reports_nothing_when_no_leftover(frozen_exe):
    assert self_update.cleanup_stale_update_files() is False


@pytest.mark.parametrize(
    "update_failed, expected_key",
    [(False, "notify.started_msg"), (True, "notify.update_apply_failed_msg")],
)
def test_started_notification_tells_when_update_was_not_applied(monkeypatch, tmp_path, update_failed, expected_key):
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(main, "_previous_update_failed", update_failed)
    icon = _FakeIcon()

    main._announce_started(icon)

    assert icon.notifications == [i18n.t(expected_key, "ko")]
