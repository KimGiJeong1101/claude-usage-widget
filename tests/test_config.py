"""config.py의 저장/로드 관련 보장을 확인한다.

1. 저장은 임시 파일 + os.replace를 거치는 원자적 쓰기라서, 쓰고 난 뒤
   임시 파일이 남지 않고 값도 정확히 왕복돼야 한다 (2026-09-13 수정,
   notes 저장소 섹션 26.3 참고).
2. 알 수 없는 키가 섞인 config.json(예: 구버전이 최신 버전이 저장한
   파일을 읽는 경우)도 죽지 않고 알려진 필드만 골라서 읽어야 한다.
"""

from usage_widget import config as config_mod


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    fake_path = tmp_path / "config.json"
    monkeypatch.setattr(config_mod, "config_path", lambda: fake_path)

    cfg = config_mod.Config()
    cfg.refresh_seconds = 123
    cfg.usage_popup_opacity = 55
    cfg.save()

    assert fake_path.exists()
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert not leftovers, f"저장 후 임시 파일이 남아있다: {leftovers}"

    loaded = config_mod.Config.load()
    assert loaded.refresh_seconds == 123
    assert loaded.usage_popup_opacity == 55


def test_load_ignores_unknown_fields(tmp_path, monkeypatch):
    fake_path = tmp_path / "config.json"
    fake_path.write_text(
        '{"refresh_seconds": 42, "a_field_from_a_future_version": "???"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_mod, "config_path", lambda: fake_path)

    loaded = config_mod.Config.load()

    assert loaded.refresh_seconds == 42


def test_load_falls_back_to_defaults_on_corrupt_file(tmp_path, monkeypatch):
    fake_path = tmp_path / "config.json"
    fake_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(config_mod, "config_path", lambda: fake_path)

    loaded = config_mod.Config.load()

    assert loaded == config_mod.Config()


def test_settings_api_save_does_not_clobber_concurrently_saved_field(tmp_path, monkeypatch):
    """webui._SettingsApi.save()가 설정 팝업을 연 시점의 스냅샷을 그대로
    저장해버려서, 그 사이 다른 팝업(투명도 슬라이더 등)이 저장한 값을
    덮어쓰던 버그가 있었다 (2026-09-14 수정, notes 저장소 섹션 26.2
    참고). webui.py를 import하면 pywebview가 같이 로드되므로, 테스트
    환경에 pywebview가 설치돼 있어야 한다(프로젝트 기본 의존성이라 항상
    설치돼 있음)."""
    from usage_widget import webui

    fake_path = tmp_path / "config.json"
    monkeypatch.setattr(config_mod, "config_path", lambda: fake_path)
    # autostart.enable/disable은 실제 Windows 레지스트리를 건드리므로,
    # 테스트에서는 절대 실제로 호출되면 안 된다.
    monkeypatch.setattr(webui.autostart, "enable", lambda: (_ for _ in ()).throw(AssertionError("registry touched")))
    monkeypatch.setattr(webui.autostart, "disable", lambda: (_ for _ in ()).throw(AssertionError("registry touched")))
    monkeypatch.setattr(webui, "_IS_WINDOWS", False)  # autostart 분기 자체를 건너뛰게 함

    # 설정 팝업을 연 시점의 스냅샷
    snapshot = config_mod.Config.load()
    api = webui._SettingsApi(snapshot, on_saved=None, close_fn=lambda: None, resize_fn=lambda dw, dh: None)

    # 그 사이 사용량 팝업에서 투명도를 바꿔서 즉시 저장
    # (webui._UsageApi.set_opacity()가 실제로 하는 것과 동일한 패턴)
    live = config_mod.Config.load()
    live.usage_popup_opacity = 55
    live.save()

    # 설정 팝업에서 "저장" 클릭 -- 다른 필드만 바꾸는 의도
    api.save({"refresh_seconds": 999, "tray_icon_style": snapshot.tray_icon_style, "language": "ko"})

    final = config_mod.Config.load()
    assert final.usage_popup_opacity == 55, "다른 팝업이 저장한 값이 덮어써졌다"
    assert final.refresh_seconds == 999


def test_concurrent_modify_never_loses_a_field_or_corrupts_the_file(tmp_path, monkeypatch):
    """설정 팝업 저장과 투명도 저장처럼, 서로 다른 필드를 고치는 두 흐름이
    동시에 여러 번 겹쳐도 (1) 어느 쪽의 마지막 값도 사라지지 않고 (2)
    저장/읽기 중에 예외가 나지 않아야 한다. 예전에는 고정된 임시 파일 이름
    하나를 같이 쓰고 읽기~저장 사이에 락이 없어서, 값이 사라지거나 Windows
    에서 os.replace가 PermissionError로 실패할 수 있었다."""
    import threading

    fake_path = tmp_path / "config.json"
    monkeypatch.setattr(config_mod, "config_path", lambda: fake_path)
    config_mod.Config().save()

    errors = []

    def worker(field, values):
        try:
            for value in values:
                def mutate(cfg, value=value):
                    setattr(cfg, field, value)

                config_mod.Config.modify(mutate)
                config_mod.Config.load()  # 트레이 메뉴처럼 중간중간 읽기도 섞어줌
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("refresh_seconds", list(range(100, 150)))),
        threading.Thread(target=worker, args=("usage_popup_opacity", list(range(40, 90)))),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"동시 저장 중 예외 발생: {errors}"
    final = config_mod.Config.load()
    assert final.refresh_seconds == 149, "다른 스레드의 저장이 refresh_seconds 변경을 덮어썼다"
    assert final.usage_popup_opacity == 89, "다른 스레드의 저장이 투명도 변경을 덮어썼다"


def test_settings_save_without_autostart_value_does_not_touch_registry(tmp_path, monkeypatch):
    """설정 창은 값이 바뀔 때마다 바로 저장한다. 자동 실행 값이 함께 오지 않은
    저장(자동 실행 줄이 안 보이는 환경 등)에서 "값 없음"을 "끄기"로 받아들여
    레지스트리의 자동 실행 등록을 지워버리면 안 된다."""
    from usage_widget import webui

    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(webui, "_IS_WINDOWS", True)
    monkeypatch.setattr(webui, "_push_theme_to_open_popups", lambda theme: None)
    calls = []
    monkeypatch.setattr(webui.autostart, "enable", lambda: calls.append("enable"))
    monkeypatch.setattr(webui.autostart, "disable", lambda: calls.append("disable"))

    api = webui._SettingsApi(config_mod.Config.load(), on_saved=None, close_fn=lambda: None, resize_fn=lambda dw, dh: None)
    api.save({"theme": "dark", "language": "ko", "tray_icon_style": "donut", "refresh_seconds": 60})
    assert calls == [], "자동 실행 값이 없는 저장인데 레지스트리를 건드렸다"
    assert config_mod.Config.load().theme == "dark"

    api.save({"theme": "dark", "language": "ko", "tray_icon_style": "donut", "refresh_seconds": 60, "autostart": False})
    assert calls == ["disable"]
