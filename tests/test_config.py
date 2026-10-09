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
    tmp_file = fake_path.with_suffix(fake_path.suffix + ".tmp")
    assert not tmp_file.exists(), "저장 후 임시 파일이 남아있다"

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
