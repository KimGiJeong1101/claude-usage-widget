"""tray_icon.py의 스타일 목록이 바뀌어도(스타일 추가/삭제) 기존 사용자의
설정이 깨지지 않는지 확인한다.

"원형 채움"(liquid) 스타일을 빼고 "이중 막대"(dual_bar)를 넣으면서, 예전에
liquid를 골라둔 사람의 config.json에는 그 값이 그대로 남아있다 -- 이런
값으로도 에러 없이 기본 스타일로 그려져야 한다.
"""

from usage_widget import i18n
from usage_widget.tray_icon import DEFAULT_STYLE, STYLES, build_icon_image


def test_every_style_renders_normal_and_logged_out():
    for style in STYLES:
        for percent in (0, 50, 100):
            build_icon_image(percent, percent, style=style)
        build_icon_image(0, 0, style=style, logged_out=True)


def test_removed_style_falls_back_to_default():
    assert "liquid" not in STYLES
    fallback = build_icon_image(42, 10, style="liquid")
    expected = build_icon_image(42, 10, style=DEFAULT_STYLE)
    assert fallback.tobytes() == expected.tobytes()


def test_every_style_has_a_label_in_every_language():
    for lang in i18n.LANGUAGE_NAMES:
        assert set(i18n.tray_style_labels(lang)) == set(STYLES), f"{lang} 스타일 이름 목록이 STYLES와 다르다"


def test_dual_bar_reflects_week_percent():
    """이중 막대만 주간 사용량을 반영한다 -- 주간 값이 달라지면 그림도 달라져야 한다."""
    low_week = build_icon_image(30, 10, style="dual_bar")
    high_week = build_icon_image(30, 95, style="dual_bar")
    assert low_week.tobytes() != high_week.tobytes()
